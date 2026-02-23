"""Projects and jobs workflow routes."""
import logging
import uuid
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session
from backend.database import get_db, Project, Job, ProjectPart
from backend.auth import get_current_user
from backend.config import settings
from backend.version import __version__
from backend.core.job_progress import get_job_progress_overlay, last_log_line, claim_job_slot, release_job_slot
from backend.api.routes.generate import start_generation
import json

logger = logging.getLogger(__name__)
router = APIRouter()


class ProjectCreate(BaseModel):
    set_num: Optional[str] = None  # None for custom projects
    name: str = Field(..., min_length=1)
    is_custom: bool = False

    @model_validator(mode="after")
    def set_num_required_for_non_custom(self):
        if not self.is_custom and not self.set_num:
            raise ValueError("set_num is required for non-custom projects")
        return self


class ProjectResponse(BaseModel):
    id: str
    set_num: Optional[str] = None
    name: str
    set_name: Optional[str] = None
    image_url: Optional[str] = None
    is_custom: bool = False
    created_at: str
    existing_project_for_set: Optional[bool] = None  # True if another project with same set exists


class ProjectPartCreate(BaseModel):
    part_num: str = Field(..., min_length=1)
    quantity: int = Field(default=1, ge=1, le=9999)
    color: Optional[str] = None
    color_rgb: Optional[str] = None


class ProjectPartUpdate(BaseModel):
    quantity: int = Field(..., ge=1, le=9999)


class ProjectPartResponse(BaseModel):
    id: str
    project_id: str
    part_num: str
    quantity: int
    color: Optional[str] = None
    color_rgb: Optional[str] = None


class JobCreateBody(BaseModel):
    """Body for creating a job under a project. At least one of generate_3mf or generate_stl must be True."""
    plate_width: int = Field(default=220, ge=100, le=2000)
    plate_depth: int = Field(default=220, ge=100, le=2000)
    plate_height: int = Field(default=250, ge=100, le=2000)  # stored for reference; placement algo uses only width/depth
    bypass_cache: bool = False
    generate_3mf: bool = True
    generate_stl: bool = True
    per_part_rotation: Optional[dict] = None  # ldraw_id -> {x, y, z} in degrees
    scale_factor: Optional[float] = Field(None, ge=0.01, le=10.0)  # user scale (1.0 = normal)

    @model_validator(mode="after")
    def at_least_one_output(self):
        if not self.generate_3mf and not self.generate_stl:
            raise ValueError("At least one of generate_3mf or generate_stl must be True")
        return self


class JobResponse(BaseModel):
    job_id: str
    set_num: str
    status: str
    progress: int
    error_message: Optional[str] = None
    output_file: Optional[str] = None
    brickgen_version: Optional[str] = None
    log: Optional[str] = None
    created_at: str
    updated_at: str


@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects(db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)):
    """List all projects."""
    rows = db.query(Project).order_by(Project.updated_at.desc()).all()
    return [
        ProjectResponse(
            id=p.id,
            set_num=p.set_num,
            name=p.name,
            set_name=p.set_name,
            image_url=p.image_url,
            is_custom=bool(p.is_custom),
            created_at=p.created_at.isoformat() if p.created_at else ""
        )
        for p in rows
    ]


@router.post("/projects", response_model=ProjectResponse)
async def create_project(data: ProjectCreate, db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)):
    """Create a project. For set-based projects, provide set_num; for custom projects set is_custom=true."""
    if data.is_custom:
        project_id = str(uuid.uuid4())
        project = Project(
            id=project_id,
            set_num=None,
            name=data.name.strip(),
            set_name=None,
            image_url=None,
            is_custom=True,
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        return ProjectResponse(
            id=project.id,
            set_num=project.set_num,
            name=project.name,
            set_name=project.set_name,
            image_url=project.image_url,
            is_custom=True,
            created_at=project.created_at.isoformat() if project.created_at else "",
        )

    # Resolve set display info from cache
    from backend.core.api_cache import DbApiCache
    from backend.api.integrations.rebrickable import CACHE_KEY_SET

    set_num = data.set_num
    if "-" not in set_num:
        set_num_with_ver = f"{set_num}-1"
    else:
        set_num_with_ver = set_num
    cache = DbApiCache(db)
    cached = cache.get(f"{CACHE_KEY_SET}{set_num_with_ver}") or cache.get(f"{CACHE_KEY_SET}{set_num}")
    set_name = cached.get("name", set_num) if cached else set_num
    image_url = cached.get("image_url") if cached else None

    existing_for_set = db.query(Project).filter(Project.set_num == set_num_with_ver).first() is not None
    if not existing_for_set and set_num != set_num_with_ver:
        existing_for_set = db.query(Project).filter(Project.set_num == set_num).first() is not None

    project_id = str(uuid.uuid4())
    project = Project(
        id=project_id,
        set_num=set_num_with_ver,
        name=data.name.strip(),
        set_name=set_name,
        image_url=image_url,
        is_custom=False,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    return ProjectResponse(
        id=project.id,
        set_num=project.set_num,
        name=project.name,
        set_name=project.set_name,
        image_url=project.image_url,
        is_custom=False,
        created_at=project.created_at.isoformat() if project.created_at else "",
        existing_project_for_set=existing_for_set
    )


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)):
    """Get a project by ID."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse(
        id=project.id,
        set_num=project.set_num,
        name=project.name,
        set_name=project.set_name,
        image_url=project.image_url,
        is_custom=bool(project.is_custom),
        created_at=project.created_at.isoformat() if project.created_at else ""
    )


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str, db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)):
    """Delete a project and all its jobs and job output files."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    jobs = db.query(Job).filter(Job.project_id == project_id).all()
    for job in jobs:
        if job.output_file:
            path = settings.output_dir / job.output_file
            if path.exists():
                try:
                    path.unlink()
                except Exception as e:
                    logger.warning(f"Could not delete job file {job.output_file}: {e}")

    db.query(Job).filter(Job.project_id == project_id).delete()
    db.query(ProjectPart).filter(ProjectPart.project_id == project_id).delete()
    db.delete(project)
    db.commit()
    return {"message": f"Project {project_id} and its jobs/files deleted"}


@router.get("/projects/{project_id}/jobs", response_model=List[JobResponse])
async def list_project_jobs(project_id: str, db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)):
    """List jobs for a project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    jobs = db.query(Job).filter(Job.project_id == project_id).order_by(Job.created_at.desc()).all()
    result = []
    for j in jobs:
        overlay = get_job_progress_overlay(j.id)
        if overlay:
            result.append(JobResponse(
                job_id=j.id,
                set_num=j.set_num,
                status=overlay["status"],
                progress=overlay["progress"],
                error_message=overlay.get("error_message"),
                output_file=j.output_file,
                brickgen_version=j.brickgen_version,
                log=last_log_line(overlay.get("log")),
                created_at=j.created_at.isoformat() if j.created_at else "",
                updated_at=j.updated_at.isoformat() if j.updated_at else ""
            ))
        else:
            result.append(JobResponse(
                job_id=j.id,
                set_num=j.set_num,
                status=j.status,
                progress=j.progress,
                error_message=j.error_message,
                output_file=j.output_file,
                brickgen_version=j.brickgen_version,
                log=j.log,
                created_at=j.created_at.isoformat() if j.created_at else "",
                updated_at=j.updated_at.isoformat() if j.updated_at else ""
            ))
    return result


@router.post("/projects/{project_id}/jobs", response_model=JobResponse)
async def create_project_job(
    project_id: str,
    body: JobCreateBody,
    db: Session = Depends(get_db)
):
    """Create a new job for a project (same set, stored settings)."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.is_custom:
        # Custom projects require at least one part
        part_count = db.query(ProjectPart).filter(ProjectPart.project_id == project_id).count()
        if part_count == 0:
            raise HTTPException(status_code=422, detail="Custom project has no parts. Add parts before generating.")

    job_id = str(uuid.uuid4())
    if not claim_job_slot(job_id):
        raise HTTPException(
            status_code=409,
            detail="Another generation job is already running. Only one job can run at a time.",
        )
    try:
        settings_obj = {
            "plate_width": body.plate_width,
            "plate_depth": body.plate_depth,
            "plate_height": body.plate_height,
            "bypass_cache": body.bypass_cache,
            "generate_3mf": body.generate_3mf,
            "generate_stl": body.generate_stl,
            "per_part_rotation": body.per_part_rotation or {},
            "is_custom": bool(project.is_custom),
        }
        if body.scale_factor is not None:
            settings_obj["scale_factor"] = float(body.scale_factor)
        settings_json = json.dumps(settings_obj)

        # For custom projects use a placeholder set_num
        set_num_for_job = project.set_num or f"custom:{project_id}"

        job = Job(
            id=job_id,
            project_id=project_id,
            set_num=set_num_for_job,
            status="pending",
            progress=0,
            plate_width=body.plate_width,
            plate_depth=body.plate_depth,
            plate_height=body.plate_height,
            brickgen_version=__version__,
            settings=settings_json
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        if project.is_custom:
            from backend.api.routes.generate import start_generation_custom
            # Gather parts from project_parts table
            project_parts = db.query(ProjectPart).filter(ProjectPart.project_id == project_id).all()
            parts_data = [
                {
                    "part_num": pp.part_num,
                    "ldraw_id": pp.part_num,
                    "quantity": pp.quantity,
                    "color": pp.color,
                    "color_rgb": pp.color_rgb,
                    "is_spare": False,
                }
                for pp in project_parts
            ]
            start_generation_custom(
                job_id,
                parts_data,
                body.plate_width,
                body.plate_depth,
                body.plate_height,
                body.bypass_cache,
                body.generate_3mf,
                body.generate_stl,
            )
        else:
            start_generation(
                job_id,
                project.set_num,
                body.plate_width,
                body.plate_depth,
                body.plate_height,
                body.bypass_cache,
                body.generate_3mf,
                body.generate_stl,
            )

        return JobResponse(
            job_id=job.id,
            set_num=job.set_num,
            status=job.status,
            progress=job.progress,
            error_message=job.error_message,
            output_file=job.output_file,
            brickgen_version=job.brickgen_version,
            created_at=job.created_at.isoformat() if job.created_at else "",
            updated_at=job.updated_at.isoformat() if job.updated_at else ""
        )
    except Exception:
        db.rollback()
        release_job_slot(job_id)
        raise


# ── Custom project part management ──────────────────────────────────────────

@router.get("/projects/{project_id}/parts", response_model=List[ProjectPartResponse])
async def list_project_parts(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """List parts added to a custom project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    parts = db.query(ProjectPart).filter(ProjectPart.project_id == project_id).all()
    return [
        ProjectPartResponse(
            id=pp.id,
            project_id=pp.project_id,
            part_num=pp.part_num,
            quantity=pp.quantity,
            color=pp.color,
            color_rgb=pp.color_rgb,
        )
        for pp in parts
    ]


@router.post("/projects/{project_id}/parts", response_model=ProjectPartResponse)
async def add_project_part(
    project_id: str,
    body: ProjectPartCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Add a part to a custom project. If the part already exists its quantity is increased."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.is_custom:
        raise HTTPException(status_code=400, detail="Parts can only be added to custom projects")

    part_num = body.part_num.strip().lower()
    # Merge if same part_num already present
    existing = db.query(ProjectPart).filter(
        ProjectPart.project_id == project_id,
        ProjectPart.part_num == part_num,
    ).first()
    if existing:
        existing.quantity += body.quantity
        db.commit()
        db.refresh(existing)
        return ProjectPartResponse(
            id=existing.id,
            project_id=existing.project_id,
            part_num=existing.part_num,
            quantity=existing.quantity,
            color=existing.color,
            color_rgb=existing.color_rgb,
        )

    pp = ProjectPart(
        id=str(uuid.uuid4()),
        project_id=project_id,
        part_num=part_num,
        quantity=body.quantity,
        color=body.color,
        color_rgb=body.color_rgb,
    )
    db.add(pp)
    db.commit()
    db.refresh(pp)
    return ProjectPartResponse(
        id=pp.id,
        project_id=pp.project_id,
        part_num=pp.part_num,
        quantity=pp.quantity,
        color=pp.color,
        color_rgb=pp.color_rgb,
    )


@router.patch("/projects/{project_id}/parts/{part_id}", response_model=ProjectPartResponse)
async def update_project_part(
    project_id: str,
    part_id: str,
    body: ProjectPartUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Update the quantity of a part in a custom project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    pp = db.query(ProjectPart).filter(
        ProjectPart.id == part_id, ProjectPart.project_id == project_id
    ).first()
    if not pp:
        raise HTTPException(status_code=404, detail="Part not found in project")
    pp.quantity = body.quantity
    db.commit()
    db.refresh(pp)
    return ProjectPartResponse(
        id=pp.id,
        project_id=pp.project_id,
        part_num=pp.part_num,
        quantity=pp.quantity,
        color=pp.color,
        color_rgb=pp.color_rgb,
    )


@router.delete("/projects/{project_id}/parts/{part_id}")
async def remove_project_part(
    project_id: str,
    part_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Remove a part from a custom project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    pp = db.query(ProjectPart).filter(
        ProjectPart.id == part_id, ProjectPart.project_id == project_id
    ).first()
    if not pp:
        raise HTTPException(status_code=404, detail="Part not found in project")
    db.delete(pp)
    db.commit()
    return {"message": f"Part {part_id} removed from project {project_id}"}
