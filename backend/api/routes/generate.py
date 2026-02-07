"""Generation routes for creating 3MF files."""
import logging
import uuid
import asyncio
import zipfile
from pathlib import Path
from typing import List
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from backend.models.schemas import GenerateRequest, JobStatus
from backend.api.integrations.rebrickable import RebrickableClient
from backend.api.integrations.ldraw import LDrawManager
from backend.core.stl_processing import STLConverter
from backend.core.threemf_generator import ThreeMFGenerator
from backend.database import get_db, Job, CachedParts
from backend.config import settings
import json
from datetime import datetime
import shutil

logger = logging.getLogger(__name__)
router = APIRouter()


async def process_generation(
    job_id: str,
    set_num: str,
    plate_width: int,
    plate_depth: int,
    bypass_cache: bool = False,
    generate_3mf: bool = True
):
    """Background task to generate 3MF file."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # Create new database session for background task
    engine = create_engine(
        f"sqlite:///{settings.database_path}",
        connect_args={"check_same_thread": False}
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return
        
        job.status = "processing"
        job.progress = 5
        db.commit()
        
        # Step 1: Ensure LDraw library exists
        logger.info(f"Job {job_id}: Checking LDraw library")
        ldraw_manager = LDrawManager()
        if not await ldraw_manager.ensure_library_exists():
            job.status = "failed"
            job.error_message = "Failed to download LDraw library"
            db.commit()
            return
        
        job.progress = 10
        db.commit()
        
        # Step 2: Get parts list from Rebrickable
        logger.info(f"Job {job_id}: Fetching parts list for set {set_num}")
        rebrickable = RebrickableClient()
        parts = await rebrickable.get_set_parts(set_num)
        
        if not parts:
            job.status = "failed"
            job.error_message = f"No parts found for set {set_num}"
            db.commit()
            return
        
        # Filter out spare parts
        parts = [p for p in parts if not p.get('is_spare', False)]
        
        logger.info(f"Job {job_id}: Found {len(parts)} parts")
        job.progress = 20
        db.commit()
        
        # Step 3: Convert parts to STL using LDView
        logger.info(f"Job {job_id}: Converting parts to STL with LDView")
        converter = STLConverter()
        
        # Use global scale factor and orientation settings
        scale_factor = settings.stl_scale_factor
        auto_orient = settings.auto_orient_enabled
        logger.info(f"Using scale factor {scale_factor:.2f}x, auto_orient={auto_orient}, strategy={settings.orientation_strategy}")
        
        stl_files = []  # Store (stl_path, ldraw_id) tuples
        converted_count = 0
        total_parts = sum(p['quantity'] for p in parts)
        
        for part in parts:
            ldraw_id = part.get('ldraw_id')
            part_num = part['part_num']
            quantity = part['quantity']
            
            # Skip if no LDraw ID
            if not ldraw_id:
                logger.warning(f"No LDraw ID for part {part_num}, skipping")
                continue
            
            # Convert to STL using LDView
            stl_path = converter.get_or_convert_stl(
                ldraw_id, 
                bypass_cache=bypass_cache, 
                scale_factor=scale_factor,
                auto_orient=auto_orient
            )
            
            if stl_path and stl_path.exists():
                # Add multiple entries for quantity (will be numbered in ZIP)
                for _ in range(quantity):
                    stl_files.append((stl_path, ldraw_id))
                    converted_count += 1
            else:
                logger.warning(f"Failed to convert {ldraw_id} (part {part_num}) to STL")
            
            # Update progress
            progress = 20 + int((converted_count / total_parts) * 50)
            job.progress = min(progress, 70)
            db.commit()
        
        if not stl_files:
            job.status = "failed"
            job.error_message = "No parts could be converted to STL"
            db.commit()
            return
        
        logger.info(f"Job {job_id}: Converted {len(stl_files)} part instances")
        job.progress = 75
        db.commit()
        
        # Step 4: Try to generate 3MF if requested, fallback to ZIP
        output_filename = None
        
        if generate_3mf:
            logger.info(f"Job {job_id}: Attempting 3MF generation")
            job.progress = 80
            db.commit()
            
            try:
                # Prepare parts list for 3MF generator (group by unique STL)
                unique_parts = {}
                for stl_path, ldraw_id in stl_files:
                    if stl_path not in unique_parts:
                        unique_parts[stl_path] = {'ldraw_id': ldraw_id, 'quantity': 0}
                    unique_parts[stl_path]['quantity'] += 1
                
                parts_for_3mf = [(path, info['ldraw_id'], info['quantity']) 
                                for path, info in unique_parts.items()]
                
                # Generate 3MF
                threemf_gen = ThreeMFGenerator(part_spacing=settings.part_spacing)
                threemf_filename = f"{job_id}.3mf"
                threemf_path = settings.output_dir / threemf_filename
                
                if threemf_gen.generate_3mf(parts_for_3mf, plate_width, plate_depth, threemf_path):
                    logger.info(f"Job {job_id}: Successfully created 3MF file")
                    output_filename = threemf_filename
                    job.progress = 95
                    db.commit()
                else:
                    logger.warning(f"Job {job_id}: 3MF generation failed, falling back to ZIP")
                    generate_3mf = False  # Fallback to ZIP
            
            except Exception as e:
                logger.error(f"Job {job_id}: 3MF generation error: {e}")
                generate_3mf = False  # Fallback to ZIP
        
        # Fallback to ZIP if 3MF not requested or failed
        if not generate_3mf or output_filename is None:
            logger.info(f"Job {job_id}: Creating ZIP file")
            zip_filename = f"{job_id}.zip"
            zip_path = settings.output_dir / zip_filename
            
            try:
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    # Track part counts for duplicate naming
                    part_counts = {}
                    
                    for stl_path, ldraw_id in stl_files:
                        # Increment counter for this part
                        if ldraw_id not in part_counts:
                            part_counts[ldraw_id] = 0
                        part_counts[ldraw_id] += 1
                        
                        # Name with counter: 3007_1.stl, 3007_2.stl, etc.
                        zip_name = f"{ldraw_id}_{part_counts[ldraw_id]}.stl"
                        zipf.write(stl_path, zip_name)
                
                logger.info(f"Job {job_id}: Created ZIP with {len(stl_files)} STL files")
                output_filename = zip_filename
                job.progress = 95
                db.commit()
                
            except Exception as e:
                logger.error(f"Job {job_id}: Failed to create ZIP: {e}")
                job.status = "failed"
                job.error_message = f"Failed to create output file: {str(e)}"
                db.commit()
                return
        
        # Complete the job
        job.status = "completed"
        job.progress = 100
        job.output_file = output_filename
        db.commit()
        
        logger.info(f"Job {job_id}: Completed successfully with {output_filename}")
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = "failed"
            job.error_message = str(e)
            db.commit()
    
    finally:
        db.close()


@router.post("/generate", response_model=JobStatus)
async def generate_3mf(
    request: GenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Generate 3MF file for a LEGO set."""
    try:
        # Create new job
        job_id = str(uuid.uuid4())
        
        job = Job(
            id=job_id,
            set_num=request.set_num,
            status="pending",
            progress=0,
            plate_width=request.plate_width,
            plate_depth=request.plate_depth
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        
        # Start background task
        background_tasks.add_task(
            process_generation,
            job_id,
            request.set_num,
            request.plate_width,
            request.plate_depth,
            request.bypass_cache,
            request.generate_3mf
        )
        
        return JobStatus(
            job_id=job.id,
            set_num=job.set_num,
            status=job.status,
            progress=job.progress,
            error_message=job.error_message,
            output_file=job.output_file,
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
    
    return JobStatus(
        job_id=job.id,
        set_num=job.set_num,
        status=job.status,
        progress=job.progress,
        error_message=job.error_message,
        output_file=job.output_file,
        created_at=job.created_at,
        updated_at=job.updated_at
    )
