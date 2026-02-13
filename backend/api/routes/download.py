"""Download routes for generated files."""
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from backend.database import get_db, Job
from backend.config import settings
from backend.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/download/{job_id}")
async def download_3mf(
    job_id: str, 
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Download generated 3MF file."""
    job = db.query(Job).filter(Job.id == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != "completed":
        raise HTTPException(status_code=400, detail=f"Job status is {job.status}, not completed")
    
    if not job.output_file:
        raise HTTPException(status_code=404, detail="Output file not found")
    
    file_path = settings.output_dir / job.output_file
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Output file does not exist")
    
    # Determine filename and media type based on file extension
    safe_set_num = job.set_num.replace("/", "-").replace("\\", "-")
    file_ext = file_path.suffix
    
    if file_ext == ".zip":
        download_name = f"{safe_set_num}_stls.zip"
        media_type = "application/zip"
    elif file_ext == ".3mf":
        download_name = f"{safe_set_num}.3mf"
        media_type = "application/vnd.ms-package.3dmanufacturing-3dmodel+xml"
    else:
        download_name = f"{safe_set_num}{file_ext}"
        media_type = "application/octet-stream"
    
    return FileResponse(
        path=file_path,
        filename=download_name,
        media_type=media_type
    )
