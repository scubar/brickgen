"""Generation routes for creating 3MF files."""
import asyncio
import logging
import queue
import threading
import uuid
import zipfile
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from backend.models.schemas import GenerateRequest, JobProgress, JobStatus
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
_job_progress_lock = threading.Lock()

# Only one generation job may run at a time. Set when a job is started, cleared when it ends.
_running_job_id: Optional[str] = None

# WebSocket: job_id -> list of connected WebSockets. Progress updates are pushed via _progress_queue.
# All access to _ws_subscribers is protected by the asyncio lock returned by _get_ws_lock().
_ws_subscribers: Dict[str, List[Any]] = {}
_ws_subscribers_lock: Optional[asyncio.Lock] = None
_ws_subscribers_lock_guard = threading.Lock()
_progress_queue: queue.Queue = queue.Queue(maxsize=1000)


def _get_ws_lock() -> asyncio.Lock:
    """Return the shared asyncio lock for _ws_subscribers. Uses a threading.Lock so that
    concurrent first access from multiple coroutines creates only one asyncio.Lock."""
    global _ws_subscribers_lock
    with _ws_subscribers_lock_guard:
        if _ws_subscribers_lock is None:
            _ws_subscribers_lock = asyncio.Lock()
        return _ws_subscribers_lock

# Circuit breaker for broadcast task: max consecutive errors before terminating
_BROADCAST_MAX_CONSECUTIVE_ERRORS = 10
_BROADCAST_ERROR_DELAY_SECONDS = 1.0


def is_any_job_running() -> bool:
    """Return True if a generation job is currently running (slot claimed)."""
    with _job_progress_lock:
        return _running_job_id is not None


def is_job_running(job_id: str) -> bool:
    """Return True if the given job is currently running."""
    with _job_progress_lock:
        return _running_job_id == job_id


def claim_job_slot(job_id: str) -> bool:
    """If no job is running, set _running_job_id to job_id and return True. Otherwise return False."""
    global _running_job_id
    with _job_progress_lock:
        if _running_job_id is not None:
            return False
        _running_job_id = job_id
        return True


def get_job_progress_overlay(job_id: str) -> Optional[Dict[str, Any]]:
    """Return overlay dict (status, progress, error_message, log) for a running job, or None."""
    with _job_progress_lock:
        entry = _job_progress.get(job_id)
        if not entry:
            return None
        return {
            "status": entry["status"],
            "progress": entry["progress"],
            "error_message": entry.get("error_message"),
            "log": entry.get("log"),
        }


def last_log_line(full_log: Optional[str]) -> Optional[str]:
    """Return only the latest log line for API responses (smaller poll payload)."""
    if not full_log or not full_log.strip():
        return None
    lines = [ln.strip() for ln in full_log.splitlines() if ln.strip()]
    return lines[-1] if lines else full_log.strip()


def _set_job_progress(job_id: str, *, status: Optional[str] = None, progress: Optional[int] = None,
                      error_message: Optional[str] = None, log: Optional[str] = None) -> None:
    """Update in-memory progress (no DB commit). Also enqueues payload for WebSocket broadcast."""
    with _job_progress_lock:
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
        payload = {
            "status": entry["status"],
            "progress": entry["progress"],
            "error_message": entry.get("error_message"),
            "log": last_log_line(entry.get("log")),
        }
    try:
        _progress_queue.put_nowait((job_id, payload))
    except queue.Full:
        logger.warning(f"Progress queue is full (maxsize={_progress_queue.maxsize}), dropping update for job {job_id}. "
                      "This may indicate broadcast_progress_task has fallen behind.")


def _remove_job_progress(job_id: str) -> None:
    """Remove job from in-memory store and release the single-job slot (call when job completes or fails)."""
    global _running_job_id
    with _job_progress_lock:
        _job_progress.pop(job_id, None)
        if _running_job_id == job_id:
            _running_job_id = None


async def broadcast_progress_task() -> None:
    """Background task: drain _progress_queue and send payload to all WebSocket subscribers for that job.
    
    Implements a circuit breaker pattern: after _BROADCAST_MAX_CONSECUTIVE_ERRORS consecutive
    exceptions in message processing, the task terminates. The error counter resets after each
    successful message broadcast (i.e., after queue.get_nowait() succeeds and all WebSocket
    sends complete without raising to the outer except block).
    """
    consecutive_errors = 0
    
    while True:
        try:
            try:
                job_id, payload = _progress_queue.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.05)
                continue
            async with _get_ws_lock():
                subscribers = list(_ws_subscribers.get(job_id, []))
            for ws in subscribers:
                try:
                    await ws.send_json(payload)
                except Exception:
                    async with _get_ws_lock():
                        try:
                            if job_id in _ws_subscribers:
                                _ws_subscribers[job_id].remove(ws)
                        except (KeyError, ValueError):
                            pass
            await asyncio.sleep(0)
            consecutive_errors = 0
        except asyncio.CancelledError:
            logger.debug("WebSocket broadcast task received cancellation")
            raise
        except Exception as e:
            consecutive_errors += 1
            logger.error(
                f"Unexpected error in WebSocket broadcast task (error {consecutive_errors}/{_BROADCAST_MAX_CONSECUTIVE_ERRORS}): {e}",
                exc_info=True
            )
            if consecutive_errors >= _BROADCAST_MAX_CONSECUTIVE_ERRORS:
                logger.critical(
                    f"WebSocket broadcast task encountered {_BROADCAST_MAX_CONSECUTIVE_ERRORS} consecutive errors. Terminating task."
                )
                raise
            await asyncio.sleep(_BROADCAST_ERROR_DELAY_SECONDS)


def start_generation_thread(
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
        # Persist "processing" at start so GET /jobs/{id} is correct even without the in-memory overlay (restart/multi-worker).
        job.status = "processing"
        job.progress = 0
        db.commit()
        job_log.append("Checking LDraw library...")
        _set_job_progress(job_id, status="processing", progress=5, log="\n".join(job_log))
        
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
        
        job_log.append("Fetching parts list...")
        _set_job_progress(job_id, progress=10, log="\n".join(job_log))
        
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
        total_parts = len(parts)
        total_instances = sum(p['quantity'] for p in parts)

        for part_index, part in enumerate(parts):
            ldraw_id = part.get('ldraw_id')
            part_num = part['part_num']
            quantity = part['quantity']

            job_log.append(f"Converting part {part_index + 1}/{total_parts}: {ldraw_id or part_num}")

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
            
            progress = 20 + int((converted_count / total_instances) * 50) if total_instances else 20
            _set_job_progress(job_id, progress=min(progress, 70), log="\n".join(job_log))
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
        job_log.append("Building output (3MF / ZIP)...")
        _set_job_progress(job_id, progress=75, log="\n".join(job_log))
        
        # Step 4: Build output per options (3MF and/or STL; STLs go in stls/ subdir when in ZIP)
        output_filename = None
        need_zip = generate_stl or (generate_3mf and generate_stl)
        threemf_path = settings.output_dir / f"{job_id}.3mf"

        if generate_3mf:
            logger.info(f"Job {job_id}: Generating 3MF")
            job_log.append("Generating 3MF...")
            _set_job_progress(job_id, progress=80, log="\n".join(job_log))
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
            # Log total size of files to zip so the user sees why this phase can take a while
            num_files = (1 if (generate_3mf and threemf_path.exists()) else 0) + (len(stl_files) if generate_stl else 0)
            total_bytes = 0
            if generate_3mf and threemf_path.exists():
                total_bytes += threemf_path.stat().st_size
            for stl_path, _, _ in stl_files:
                if stl_path.exists():
                    total_bytes += stl_path.stat().st_size
            size_mb = total_bytes / (1024 * 1024)
            size_str = f"{size_mb:.1f} MB" if size_mb >= 0.01 else f"{total_bytes} B"
            job_log.append(f"Creating ZIP: {num_files} files ({size_str})...")
            _set_job_progress(job_id, progress=82, log="\n".join(job_log))
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
                # Log final ZIP size and compression ratio
                zip_size = zip_path.stat().st_size
                zip_mb = zip_size / (1024 * 1024)
                zip_size_str = f"{zip_mb:.1f} MB" if zip_mb >= 0.01 else f"{zip_size} B"
                if total_bytes > 0:
                    reduction = (1 - zip_size / total_bytes) * 100
                    job_log.append(f"ZIP created: {zip_size_str} ({reduction:.0f}% reduction)")
                else:
                    job_log.append(f"ZIP created: {zip_size_str}")
                _set_job_progress(job_id, progress=90, log="\n".join(job_log))
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

        job_log.append("Finalizing...")
        _set_job_progress(job_id, progress=95, log="\n".join(job_log))

        # Complete the job: single DB commit with final state
        log_str = "\n".join(job_log) if job_log else None
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = "completed"
            job.progress = 100
            job.output_file = output_filename
            job.log = log_str
            db.commit()
        # Push final state to WebSocket clients before removing overlay (so UI updates without refresh)
        _set_job_progress(job_id, status="completed", progress=100, log=log_str)

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
        _remove_job_progress(job_id)
        db.close()


@router.post("/generate", response_model=JobStatus)
async def generate_3mf(
    request: GenerateRequest,
    db: Session = Depends(get_db)
):
    """Generate 3MF file for a LEGO set."""
    try:
        job_id = str(uuid.uuid4())
        if not claim_job_slot(job_id):
            raise HTTPException(
                status_code=409,
                detail="Another generation job is already running. Only one job can run at a time.",
            )
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

        start_generation_thread(
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


@router.get("/jobs/{job_id}/progress", response_model=JobProgress)
async def get_job_progress(job_id: str):
    """Get in-memory progress for a running job only. No database access. Returns 404 if job is not in progress."""
    overlay = get_job_progress_overlay(job_id)
    if not overlay:
        raise HTTPException(status_code=404, detail="Job not in progress")
    return JobProgress(
        status=overlay["status"],
        progress=overlay["progress"],
        error_message=overlay.get("error_message"),
        log=last_log_line(overlay.get("log")),
    )


@router.websocket("/jobs/{job_id}/ws")
async def websocket_job_progress(websocket: WebSocket, job_id: str):
    """Stream job progress over WebSocket. Server pushes updates when progress changes. No DB access."""
    await websocket.accept()
    async with _get_ws_lock():
        if job_id not in _ws_subscribers:
            _ws_subscribers[job_id] = []
        _ws_subscribers[job_id].append(websocket)
    overlay = get_job_progress_overlay(job_id)
    if overlay:
        try:
            await websocket.send_json({
                "status": overlay["status"],
                "progress": overlay["progress"],
                "error_message": overlay.get("error_message"),
                "log": last_log_line(overlay.get("log")),
            })
        except Exception:
            pass
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        async with _get_ws_lock():
            if job_id in _ws_subscribers:
                try:
                    _ws_subscribers[job_id].remove(websocket)
                except ValueError:
                    pass
                if not _ws_subscribers[job_id]:
                    del _ws_subscribers[job_id]


@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """Get full job record from the database. For live progress of a running job, use GET /jobs/{id}/progress instead."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
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
    if is_job_running(job_id):
        raise HTTPException(
            status_code=409,
            detail="Cannot delete job output while the job is running.",
        )
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
    if is_job_running(job_id):
        raise HTTPException(
            status_code=409,
            detail="Cannot delete job while it is running.",
        )
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
    if not claim_job_slot(new_job_id):
        raise HTTPException(
            status_code=409,
            detail="Another generation job is already running. Only one job can run at a time.",
        )
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

    start_generation_thread(
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
