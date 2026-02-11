"""Projects and jobs workflow routes."""
import logging
import uuid
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session
from backend.database import get_db, Project, Job
from backend.config import settings
from backend.version import __version__
from backend.api.routes.generate import get_job_progress_overlay, _last_log_line, _start_generation_thread, _claim_job_slot
import json

logger = logging.getLogger(__name__)
router = APIRouter()


class ProjectCreate(BaseModel):
    set_num: str
    name: str = Field(..., min_length=1)


class ProjectResponse(BaseModel):
    id: str
    set_num: str
    name: str
    set_name: Optional[str] = None
    image_url: Optional[str] = None
    created_at: str
    existing_project_for_set: Optional[bool] = None  # True if another project with same set exists


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
async def list_projects(db: Session = Depends(get_db)):
    """List all projects."""
    rows = db.query(Project).order_by(Project.updated_at.desc()).all()
    return [
        ProjectResponse(
            id=p.id,
            set_num=p.set_num,
            name=p.name,
            set_name=p.set_name,
            image_url=p.image_url,
            created_at=p.created_at.isoformat() if p.created_at else ""
        )
        for p in rows
    ]


@router.post("/projects", response_model=ProjectResponse)
async def create_project(data: ProjectCreate, db: Session = Depends(get_db)):
    """Create a project for a set. Optionally warn if another project references the same set."""
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
        image_url=image_url
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
        created_at=project.created_at.isoformat() if project.created_at else "",
        existing_project_for_set=existing_for_set
    )


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: Session = Depends(get_db)):
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
        created_at=project.created_at.isoformat() if project.created_at else ""
    )


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str, db: Session = Depends(get_db)):
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
    db.delete(project)
    db.commit()
    return {"message": f"Project {project_id} and its jobs/files deleted"}


@router.get("/projects/{project_id}/jobs", response_model=List[JobResponse])
async def list_project_jobs(project_id: str, db: Session = Depends(get_db)):
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
                log=_last_log_line(overlay.get("log")),
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

    job_id = str(uuid.uuid4())
    if not _claim_job_slot(job_id):
        raise HTTPException(
            status_code=409,
            detail="Another generation job is already running. Only one job can run at a time.",
        )
    settings_obj = {
        "plate_width": body.plate_width,
        "plate_depth": body.plate_depth,
        "plate_height": body.plate_height,
        "bypass_cache": body.bypass_cache,
        "generate_3mf": body.generate_3mf,
        "generate_stl": body.generate_stl,
        "per_part_rotation": body.per_part_rotation or {},
    }
    if body.scale_factor is not None:
        settings_obj["scale_factor"] = float(body.scale_factor)
    settings_json = json.dumps(settings_obj)

    job = Job(
        id=job_id,
        project_id=project_id,
        set_num=project.set_num,
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

    _start_generation_thread(
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
