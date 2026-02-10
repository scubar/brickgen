"""Generation routes for creating 3MF files."""
import asyncio
import logging
import threading
import uuid
import zipfile
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from backend.models.schemas import GenerateRequest, JobStatus
from backend.api.integrations.rebrickable import RebrickableClient
from backend.api.integrations.ldraw import LDrawManager
from backend.core.stl_processing import STLConverter
from backend.core.threemf_generator import ThreeMFGenerator
from backend.database import get_db, Job, Project
from backend.api.routes.settings import sync_config_from_db
from backend.config import settings
from backend.version import __version__
import json
from datetime import datetime
import shutil

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory job progress (single-process). Key: job_id. Value: status, progress, error_message, log.
# Multi-worker deployments would not share this store.
_job_progress: Dict[str, Dict[str, Any]] = {}


def get_job_progress_overlay(job_id: str) -> Optional[Dict[str, Any]]:
    """Return overlay dict (status, progress, error_message, log) for a running job, or None."""
    entry = _job_progress.get(job_id)
    if not entry:
        return None
    return {
        "status": entry["status"],
        "progress": entry["progress"],
        "error_message": entry.get("error_message"),
        "log": entry.get("log"),
    }


def _set_job_progress(job_id: str, *, status: Optional[str] = None, progress: Optional[int] = None,
                      error_message: Optional[str] = None, log: Optional[str] = None) -> None:
    """Update in-memory progress (no DB commit)."""
    if job_id not in _job_progress:
        _job_progress[job_id] = {
            "status": "processing",
            "progress": 0,
            "error_message": None,
            "log": None,
        }
    entry = _job_progress[job_id]
    if status is not None:
        entry["status"] = status
    if progress is not None:
        entry["progress"] = progress
    if error_message is not None:
        entry["error_message"] = error_message
    if log is not None:
        entry["log"] = log


def _remove_job_progress(job_id: str) -> None:
    """Remove job from in-memory store (call when job completes or fails)."""
    _job_progress.pop(job_id, None)


def _start_generation_thread(
    job_id: str,
    set_num: str,
    plate_width: int,
    plate_depth: int,
    plate_height: int,
    bypass_cache: bool = False,
    generate_3mf: bool = True,
    generate_stl: bool = True,
) -> None:
    """Run process_generation in a separate thread so the request returns immediately.
    The server's event loop is not blocked, so job creation and polling respond right away.
    """
    def _run() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                process_generation(
                    job_id, set_num, plate_width, plate_depth, plate_height,
                    bypass_cache, generate_3mf, generate_stl,
                )
            )
        finally:
            loop.close()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()


async def process_generation(
    job_id: str,
    set_num: str,
    plate_width: int,
    plate_depth: int,
    plate_height: int,
    bypass_cache: bool = False,
    generate_3mf: bool = True,
    generate_stl: bool = True
):
    """Background task to generate output. At least one of generate_3mf or generate_stl must be True.
    When generate_stl is True, STLs are placed in a subdirectory 'stls' in the export (ZIP).
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # Create new database session for background task
    engine = create_engine(
        f"sqlite:///{settings.database_path}",
        connect_args={"check_same_thread": False}
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    job_log = []
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return
        db.commit()  # release read transaction so polling/other requests can use the DB
        _set_job_progress(job_id, status="processing", progress=5)
        
        # Step 1: Ensure LDraw library exists
        logger.info(f"Job {job_id}: Checking LDraw library")
        ldraw_manager = LDrawManager()
        if not await ldraw_manager.ensure_library_exists():
            log_str = "\n".join(job_log) if job_log else None
            _set_job_progress(job_id, status="failed", error_message="Failed to download LDraw library", log=log_str)
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = "failed"
                job.error_message = "Failed to download LDraw library"
                job.log = log_str
                db.commit()
            _remove_job_progress(job_id)
            return
        
        _set_job_progress(job_id, progress=10)
        
        # Step 2: Get parts list from Rebrickable (use cache to avoid repeat API calls)
        logger.info(f"Job {job_id}: Fetching parts list for set {set_num}")
        from backend.core.api_cache import DbApiCache
        cache = DbApiCache(db)
        rebrickable = RebrickableClient(cache=cache)
        parts = await rebrickable.get_set_parts(set_num)
        db.commit()  # release so polling can read while we do STL work
        if not parts:
            log_str = "\n".join(job_log) if job_log else None
            _set_job_progress(job_id, status="failed", error_message=f"No parts found for set {set_num}", log=log_str)
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = "failed"
                job.error_message = f"No parts found for set {set_num}"
                job.log = log_str
                db.commit()
            _remove_job_progress(job_id)
            return
        
        # Filter out spare parts
        parts = [p for p in parts if not p.get('is_spare', False)]
        
        logger.info(f"Job {job_id}: Found {len(parts)} parts")
        _set_job_progress(job_id, progress=20)
        
        # Per-part rotation and per-job scale/rotation from job settings
        try:
            s = json.loads(job.settings) if job.settings else {}
            per_part_rotation = s.get("per_part_rotation") or {}
            scale_factor = s.get("scale_factor")
            if scale_factor is None:
                scale_factor = settings.stl_scale_factor
            rot_enabled = s.get("rotation_enabled")
            if rot_enabled is None:
                rot_enabled = settings.rotation_enabled
            rx = s.get("rotation_x", settings.rotation_x)
            ry = s.get("rotation_y", settings.rotation_y)
            rz = s.get("rotation_z", settings.rotation_z)
        except Exception:
            per_part_rotation = {}
            scale_factor = settings.stl_scale_factor
            rot_enabled = settings.rotation_enabled
            rx, ry, rz = settings.rotation_x, settings.rotation_y, settings.rotation_z

        # Step 3: Convert parts to STL using LDView (user scale 1.0 → backend 10)
        scale_factor = float(scale_factor)
        scale_factor_backend = scale_factor * 10.0
        sync_config_from_db(db)  # use persisted LDView settings for conversion
        db.commit()  # release so polling can read during STL conversion loop
        logger.info(f"Job {job_id}: Converting parts to STL with LDView")
        converter = STLConverter()
        logger.info(f"Using scale factor {scale_factor} (backend {scale_factor_backend}), rotation_enabled={rot_enabled} (X={rx}, Y={ry}, Z={rz}), per_part_rotation keys={len(per_part_rotation)}")

        stl_files = []
        converted_count = 0
        total_parts = sum(p['quantity'] for p in parts)

        for part in parts:
            ldraw_id = part.get('ldraw_id')
            part_num = part['part_num']
            quantity = part['quantity']

            if not ldraw_id:
                line = f"No LDraw ID for part {part_num}, skipping"
                logger.warning(line)
                job_log.append(line)
                continue

            # Use per-part rotation if set, else global, else "match preview" default (X=-90 so STL matches LDView preview)
            pr = per_part_rotation.get(ldraw_id)
            if pr is not None and isinstance(pr, dict):
                use_rot = True
                px = float(pr.get("x", 0))
                py = float(pr.get("y", 0))
                pz = float(pr.get("z", 0))
            elif rot_enabled:
                use_rot = True
                px, py, pz = rx, ry, rz
            elif getattr(settings, 'default_orientation_match_preview', True):
                use_rot = True
                px, py, pz = -90.0, 0.0, 0.0
            else:
                use_rot = False
                px, py, pz = 0.0, 0.0, 0.0

            stl_path = converter.get_or_convert_stl(
                ldraw_id,
                bypass_cache=bypass_cache,
                scale_factor=scale_factor_backend,
                rotation_enabled=use_rot,
                rotation_x=px, rotation_y=py, rotation_z=pz,
                db=db,
            )
            
            if stl_path and stl_path.exists():
                color_rgb = part.get("color_rgb")
                for _ in range(quantity):
                    stl_files.append((stl_path, ldraw_id, color_rgb))
                    converted_count += 1
            else:
                line = f"Failed to convert {ldraw_id} (part {part_num}) to STL"
                logger.warning(line)
                job_log.append(line)
            
            # Update progress (in-memory only)
            progress = 20 + int((converted_count / total_parts) * 50)
            _set_job_progress(job_id, progress=min(progress, 70))
            db.commit()  # release after each part so polling/other requests are not blocked
        if not stl_files:
            log_str = "\n".join(job_log) if job_log else None
            _set_job_progress(job_id, status="failed", error_message="No parts could be converted to STL", log=log_str)
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = "failed"
                job.error_message = "No parts could be converted to STL"
                job.log = log_str
                db.commit()
            _remove_job_progress(job_id)
            return
        
        logger.info(f"Job {job_id}: Converted {len(stl_files)} part instances")
        _set_job_progress(job_id, progress=75)
        
        # Step 4: Build output per options (3MF and/or STL; STLs go in stls/ subdir when in ZIP)
        output_filename = None
        need_zip = generate_stl or (generate_3mf and generate_stl)
        threemf_path = settings.output_dir / f"{job_id}.3mf"

        if generate_3mf:
            logger.info(f"Job {job_id}: Generating 3MF")
            _set_job_progress(job_id, progress=80)
            try:
                unique_parts = {}
                for stl_path, ldraw_id, color_rgb in stl_files:
                    if stl_path not in unique_parts:
                        unique_parts[stl_path] = {'ldraw_id': ldraw_id, 'quantity': 0, 'color_rgb': color_rgb}
                    unique_parts[stl_path]['quantity'] += 1
                parts_for_3mf = [
                    (path, info['ldraw_id'], info['quantity'], info.get('color_rgb'))
                    for path, info in unique_parts.items()
                ]
                threemf_gen = ThreeMFGenerator(part_spacing=settings.part_spacing)
                if not threemf_gen.generate_3mf(parts_for_3mf, plate_width, plate_depth, plate_height, threemf_path):
                    raise RuntimeError("3MF generation returned False")
            except Exception as e:
                logger.error(f"Job {job_id}: 3MF generation error: {e}")
                if not generate_stl:
                    log_str = "\n".join(job_log) if job_log else None
                    _set_job_progress(job_id, status="failed", error_message=str(e), log=log_str)
                    job = db.query(Job).filter(Job.id == job_id).first()
                    if job:
                        job.status = "failed"
                        job.error_message = str(e)
                        job.log = log_str
                        db.commit()
                    _remove_job_progress(job_id)
                    return
                generate_3mf = False

        if need_zip:
            logger.info(f"Job {job_id}: Creating ZIP (3MF={generate_3mf}, STL in stls/={generate_stl})")
            zip_filename = f"{job_id}.zip"
            zip_path = settings.output_dir / zip_filename
            try:
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    if generate_3mf and threemf_path.exists():
                        zipf.write(threemf_path, f"{job_id}.3mf")
                    if generate_stl:
                        part_counts = {}
                        for stl_path, ldraw_id, _ in stl_files:
                            if ldraw_id not in part_counts:
                                part_counts[ldraw_id] = 0
                            part_counts[ldraw_id] += 1
                            zip_name = f"stls/{ldraw_id}_{part_counts[ldraw_id]}.stl"
                            zipf.write(stl_path, zip_name)
                output_filename = zip_filename
                if generate_3mf and threemf_path.exists():
                    try:
                        threemf_path.unlink()
                    except OSError:
                        pass
            except Exception as e:
                logger.error(f"Job {job_id}: Failed to create ZIP: {e}")
                log_str = "\n".join(job_log) if job_log else None
                _set_job_progress(job_id, status="failed", error_message=str(e), log=log_str)
                job = db.query(Job).filter(Job.id == job_id).first()
                if job:
                    job.status = "failed"
                    job.error_message = str(e)
                    job.log = log_str
                    db.commit()
                _remove_job_progress(job_id)
                return
        else:
            output_filename = f"{job_id}.3mf"

        _set_job_progress(job_id, progress=95)

        # Complete the job: single DB commit with final state
        log_str = "\n".join(job_log) if job_log else None
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = "completed"
            job.progress = 100
            job.output_file = output_filename
            job.log = log_str
            db.commit()
        _remove_job_progress(job_id)
        
        logger.info(f"Job {job_id}: Completed successfully with {output_filename}")
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        log_str = "\n".join(job_log) if job_log else None
        _set_job_progress(job_id, status="failed", error_message=str(e), log=log_str)
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = "failed"
            job.error_message = str(e)
            job.log = log_str
            db.commit()
        _remove_job_progress(job_id)
    
    finally:
        db.close()


@router.post("/generate", response_model=JobStatus)
async def generate_3mf(
    request: GenerateRequest,
    db: Session = Depends(get_db)
):
    """Generate 3MF file for a LEGO set."""
    try:
        job_id = str(uuid.uuid4())
        settings_obj = {
            "plate_width": request.plate_width,
            "plate_depth": request.plate_depth,
            "plate_height": request.plate_height,
            "bypass_cache": request.bypass_cache,
            "generate_3mf": request.generate_3mf,
            "generate_stl": request.generate_stl,
        }
        if request.scale_factor is not None:
            settings_obj["scale_factor"] = float(request.scale_factor)
        settings_json = json.dumps(settings_obj)

        job = Job(
            id=job_id,
            set_num=request.set_num,
            status="pending",
            progress=0,
            plate_width=request.plate_width,
            plate_depth=request.plate_depth,
            plate_height=request.plate_height,
            brickgen_version=__version__,
            project_id=request.project_id,
            settings=settings_json
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        _start_generation_thread(
            job_id,
            request.set_num,
            request.plate_width,
            request.plate_depth,
            request.plate_height,
            request.bypass_cache,
            request.generate_3mf,
            request.generate_stl,
        )

        return JobStatus(
            job_id=job.id,
            set_num=job.set_num,
            status=job.status,
            progress=job.progress,
            error_message=job.error_message,
            output_file=job.output_file,
            brickgen_version=job.brickgen_version,
            log=None,
            created_at=job.created_at,
            updated_at=job.updated_at
        )

    except Exception as e:
        logger.error(f"Error creating generation job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """Get status of a generation job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    overlay = get_job_progress_overlay(job_id)
    if overlay:
        return JobStatus(
            job_id=job.id,
            set_num=job.set_num,
            status=overlay["status"],
            progress=overlay["progress"],
            error_message=overlay.get("error_message"),
            output_file=job.output_file,
            brickgen_version=job.brickgen_version,
            log=overlay.get("log"),
            created_at=job.created_at,
            updated_at=job.updated_at
        )
    return JobStatus(
        job_id=job.id,
        set_num=job.set_num,
        status=job.status,
        progress=job.progress,
        error_message=job.error_message,
        output_file=job.output_file,
        brickgen_version=job.brickgen_version,
        log=job.log,
        created_at=job.created_at,
        updated_at=job.updated_at
    )


@router.delete("/jobs/files")
async def clear_all_job_files(db: Session = Depends(get_db)):
    """Remove all job output files from disk (e.g. from settings). Job records are kept."""
    jobs = db.query(Job).filter(Job.output_file.isnot(None)).all()
    deleted = 0
    for job in jobs:
        path = settings.output_dir / job.output_file
        if path.exists():
            path.unlink()
            deleted += 1
        job.output_file = None
    db.commit()
    return {"message": f"Deleted {deleted} job output files", "deleted_count": deleted}


@router.delete("/jobs/{job_id}/files")
async def delete_job_files(job_id: str, db: Session = Depends(get_db)):
    """Remove the output file for a job from disk. Job record is kept."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    out_file = job.output_file
    if not out_file:
        return {"message": "Job has no output file", "deleted": False}
    path = settings.output_dir / out_file
    deleted = path.exists()
    if deleted:
        path.unlink()
    job.output_file = None
    db.commit()
    return {"message": f"Deleted {out_file}" if deleted else "File was already missing", "deleted": deleted}


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str, db: Session = Depends(get_db)):
    """Delete a job record and its output file (if any)."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.output_file:
        path = settings.output_dir / job.output_file
        if path.exists():
            try:
                path.unlink()
            except Exception as e:
                logger.warning(f"Could not delete job file {job.output_file}: {e}")
    db.delete(job)
    db.commit()
    return {"message": f"Job {job_id} deleted"}


@router.post("/jobs/{job_id}/rerun", response_model=JobStatus)
async def rerun_job(
    job_id: str,
    db: Session = Depends(get_db)
):
    """Re-run a job with the same stored settings. Creates a new job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    try:
        s = json.loads(job.settings) if job.settings else {}
    except Exception:
        s = {}
    plate_width = s.get("plate_width", job.plate_width or 220)
    plate_depth = s.get("plate_depth", job.plate_depth or 220)
    plate_height = s.get("plate_height", job.plate_height or 250)
    bypass_cache = s.get("bypass_cache", False)
    generate_3mf = s.get("generate_3mf", True)
    generate_stl = s.get("generate_stl", True)

    new_job_id = str(uuid.uuid4())
    new_job = Job(
        id=new_job_id,
        set_num=job.set_num,
        status="pending",
        progress=0,
        plate_width=plate_width,
        plate_depth=plate_depth,
        plate_height=plate_height,
        brickgen_version=__version__,
        project_id=job.project_id,
        settings=job.settings
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    _start_generation_thread(
        new_job_id,
        job.set_num,
        plate_width,
        plate_depth,
        plate_height,
        bypass_cache,
        generate_3mf,
        generate_stl,
    )

    return JobStatus(
        job_id=new_job.id,
        set_num=new_job.set_num,
        status=new_job.status,
        progress=new_job.progress,
        error_message=new_job.error_message,
        output_file=new_job.output_file,
        brickgen_version=new_job.brickgen_version,
        log=new_job.log,
        created_at=new_job.created_at,
        updated_at=new_job.updated_at
    )
