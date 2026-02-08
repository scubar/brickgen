"""Settings routes."""
import logging
import os
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.models.schemas import SettingsResponse, SettingsUpdate, CacheStats, LDrawCacheStats
from backend.config import settings
from backend.core.stl_processing import STLConverter
from backend.api.integrations.ldraw import LDrawManager
from backend.database import get_db, CachedSet, CachedParts

logger = logging.getLogger(__name__)
router = APIRouter()


class ApiKeyUpdate(BaseModel):
    """Update API key."""
    api_key: str


@router.get("/settings", response_model=SettingsResponse)
async def get_settings():
    """Get current application settings."""
    return SettingsResponse(
        default_plate_width=settings.default_plate_width,
        default_plate_depth=settings.default_plate_depth,
        default_plate_height=settings.default_plate_height,
        part_spacing=settings.part_spacing,
        stl_scale_factor=settings.stl_scale_factor,
        rotation_enabled=settings.rotation_enabled,
        rotation_x=settings.rotation_x,
        rotation_y=settings.rotation_y,
        rotation_z=settings.rotation_z,
        default_orientation_match_preview=settings.default_orientation_match_preview,
        auto_generate_part_previews=settings.auto_generate_part_previews
    )


@router.post("/settings")
async def update_settings(update: SettingsUpdate):
    """Update application settings.
    
    Note: This updates runtime settings only, not persisted.
    For production, consider using a database or config file.
    
    If stl_scale_factor is changed, STL cache is automatically cleared.
    """
    cache_cleared = False
    
    # Check if STL scale is being changed
    if update.stl_scale_factor is not None and update.stl_scale_factor != settings.stl_scale_factor:
        logger.info(f"STL scale changed from {settings.stl_scale_factor} to {update.stl_scale_factor}, clearing STL cache")
        settings.stl_scale_factor = update.stl_scale_factor
        
        # Clear STL cache since scaling has changed
        try:
            converter = STLConverter()
            deleted_count = converter.clear_cache()
            cache_cleared = True
            logger.info(f"Cleared {deleted_count} STL files due to scale change")
        except Exception as e:
            logger.error(f"Failed to clear cache after scale change: {e}")
    
    if update.default_plate_width is not None:
        settings.default_plate_width = update.default_plate_width
    
    if update.default_plate_depth is not None:
        settings.default_plate_depth = update.default_plate_depth
    
    if update.default_plate_height is not None:
        settings.default_plate_height = update.default_plate_height
    
    if update.part_spacing is not None:
        settings.part_spacing = update.part_spacing
    
    if update.rotation_enabled is not None:
        if update.rotation_enabled != settings.rotation_enabled:
            try:
                converter = STLConverter()
                deleted_count = converter.clear_cache()
                cache_cleared = True
                logger.info(f"Cleared {deleted_count} STL files due to rotation change")
            except Exception as e:
                logger.error(f"Failed to clear cache after rotation change: {e}")
        settings.rotation_enabled = update.rotation_enabled
    if update.rotation_x is not None:
        settings.rotation_x = update.rotation_x
    if update.rotation_y is not None:
        settings.rotation_y = update.rotation_y
    if update.rotation_z is not None:
        settings.rotation_z = update.rotation_z
    if update.default_orientation_match_preview is not None:
        if update.default_orientation_match_preview != settings.default_orientation_match_preview:
            try:
                converter = STLConverter()
                deleted_count = converter.clear_cache()
                cache_cleared = True
                logger.info(f"Cleared {deleted_count} STL files due to default orientation change")
            except Exception as e:
                logger.error(f"Failed to clear cache after default orientation change: {e}")
        settings.default_orientation_match_preview = update.default_orientation_match_preview
    if update.auto_generate_part_previews is not None:
        settings.auto_generate_part_previews = update.auto_generate_part_previews

    return {
        "settings": SettingsResponse(
            default_plate_width=settings.default_plate_width,
            default_plate_depth=settings.default_plate_depth,
            default_plate_height=settings.default_plate_height,
            part_spacing=settings.part_spacing,
            stl_scale_factor=settings.stl_scale_factor,
            rotation_enabled=settings.rotation_enabled,
            rotation_x=settings.rotation_x,
            rotation_y=settings.rotation_y,
            rotation_z=settings.rotation_z,
            default_orientation_match_preview=settings.default_orientation_match_preview,
            auto_generate_part_previews=settings.auto_generate_part_previews
        ),
        "cache_cleared": cache_cleared
    }


class CachedSetSummary(BaseModel):
    """Cached set summary for Rebrickable cache list."""
    set_num: str
    name: str
    cached_at: str  # updated_at ISO format
    image_url: Optional[str] = None


class RebrickableCacheList(BaseModel):
    """Paginated list of cached sets."""
    results: List[CachedSetSummary]
    count: int
    page: int
    page_size: int
    next: Optional[int] = None  # next page number or null
    previous: Optional[int] = None  # previous page number or null


@router.get("/cache/rebrickable", response_model=RebrickableCacheList)
async def list_cached_sets(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page")
):
    """List cached sets (Rebrickable cache) with set_num, name, cached_at. Paginated."""
    q = db.query(CachedSet).order_by(CachedSet.updated_at.desc())
    count = q.count()
    offset = (page - 1) * page_size
    rows = q.offset(offset).limit(page_size).all()
    total_pages = (count + page_size - 1) // page_size if page_size else 0
    return RebrickableCacheList(
        results=[
            CachedSetSummary(
                set_num=r.set_num,
                name=r.name or "",
                cached_at=r.updated_at.isoformat() if r.updated_at else "",
                image_url=r.image_url
            )
            for r in rows
        ],
        count=count,
        page=page,
        page_size=page_size,
        next=page + 1 if page < total_pages else None,
        previous=page - 1 if page > 1 else None
    )


@router.delete("/cache/rebrickable")
async def clear_rebrickable_cache(
    set_num: Optional[str] = Query(None, description="If set, clear only this set; otherwise clear all"),
    db: Session = Depends(get_db)
):
    """Clear Rebrickable cache: all cached sets (and their parts) or a single set."""
    if set_num:
        deleted_sets = db.query(CachedSet).filter(CachedSet.set_num == set_num).delete()
        deleted_parts = db.query(CachedParts).filter(CachedParts.set_num == set_num).delete()
        db.commit()
        return {"message": f"Cleared cache for set {set_num}", "sets": deleted_sets, "parts": deleted_parts}
    else:
        deleted_sets = db.query(CachedSet).delete()
        deleted_parts = db.query(CachedParts).delete()
        db.commit()
        return {"message": "Cleared all Rebrickable cache", "sets": deleted_sets, "parts": deleted_parts}


@router.get("/cache/stats", response_model=CacheStats)
async def get_cache_stats():
    """Get STL cache statistics."""
    try:
        converter = STLConverter()
        stats = converter.get_cache_stats()
        
        return CacheStats(
            stl_count=stats['count'],
            total_size_mb=stats['total_size_mb'],
            cache_dir=stats['cache_dir']
        )
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cache/clear")
async def clear_cache():
    """Clear all cached STL files."""
    try:
        converter = STLConverter()
        deleted_count = converter.clear_cache()
        
        return {
            "message": f"Cleared {deleted_count} STL files from cache",
            "deleted_count": deleted_count
        }
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ldraw/stats", response_model=LDrawCacheStats)
async def get_ldraw_stats():
    """Get LDraw library statistics."""
    try:
        manager = LDrawManager()
        stats = manager.get_library_stats()
        
        # Calculate total size if library exists
        total_size_mb = 0.0
        if stats['exists']:
            import os
            for root, dirs, files in os.walk(manager.library_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    if os.path.exists(file_path):
                        total_size_mb += os.path.getsize(file_path)
            total_size_mb = total_size_mb / (1024 * 1024)
        
        return LDrawCacheStats(
            exists=stats['exists'],
            part_count=stats['part_count'],
            total_size_mb=total_size_mb,
            library_path=stats.get('path', str(manager.library_path))
        )
    except Exception as e:
        logger.error(f"Error getting LDraw stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/ldraw/clear")
async def clear_ldraw():
    """Clear LDraw library (will be re-downloaded on next use)."""
    try:
        import shutil
        manager = LDrawManager()
        
        if not manager.library_path.exists():
            return {
                "message": "LDraw library does not exist",
                "deleted": False
            }
        
        # Delete the entire library directory
        shutil.rmtree(manager.library_path)
        logger.info(f"Deleted LDraw library at {manager.library_path}")
        
        return {
            "message": "LDraw library cleared successfully. It will be re-downloaded on next generation.",
            "deleted": True
        }
    except Exception as e:
        logger.error(f"Error clearing LDraw library: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/settings/api-key")
async def update_api_key(update: ApiKeyUpdate):
    """Update Rebrickable API key.
    
    Note: This updates the runtime setting only. For persistent changes,
    update the REBRICKABLE_API_KEY environment variable.
    """
    try:
        if not update.api_key or not update.api_key.strip():
            raise HTTPException(status_code=400, detail="API key cannot be empty")
        
        # Update runtime setting
        settings.rebrickable_api_key = update.api_key.strip()
        logger.info("Rebrickable API key updated")
        
        return {
            "message": "API key updated successfully",
            "success": True
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))
