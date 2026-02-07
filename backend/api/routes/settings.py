"""Settings routes."""
import logging
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.models.schemas import SettingsResponse, SettingsUpdate, CacheStats, LDrawCacheStats
from backend.config import settings
from backend.core.stl_processing import STLConverter
from backend.api.integrations.ldraw import LDrawManager

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
        auto_orient_enabled=settings.auto_orient_enabled,
        orientation_strategy=settings.orientation_strategy
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
    
    if update.auto_orient_enabled is not None:
        settings.auto_orient_enabled = update.auto_orient_enabled
    
    if update.orientation_strategy is not None:
        if update.orientation_strategy in ["studs_up", "flat", "minimize_supports", "original"]:
            # Clear cache if orientation strategy changes
            if update.orientation_strategy != settings.orientation_strategy:
                logger.info(f"Orientation strategy changed, clearing STL cache")
                try:
                    converter = STLConverter()
                    deleted_count = converter.clear_cache()
                    cache_cleared = True
                    logger.info(f"Cleared {deleted_count} STL files due to orientation change")
                except Exception as e:
                    logger.error(f"Failed to clear cache after orientation change: {e}")
            
            settings.orientation_strategy = update.orientation_strategy
    
    return {
        "settings": SettingsResponse(
            default_plate_width=settings.default_plate_width,
            default_plate_depth=settings.default_plate_depth,
            default_plate_height=settings.default_plate_height,
            part_spacing=settings.part_spacing,
            stl_scale_factor=settings.stl_scale_factor,
            auto_orient_enabled=settings.auto_orient_enabled,
            orientation_strategy=settings.orientation_strategy
        ),
        "cache_cleared": cache_cleared
    }


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
