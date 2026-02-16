"""Settings routes."""
import logging
import os
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from sqlalchemy import text, func
from sqlalchemy.orm import Session
from backend.models.schemas import (
    SettingsResponse,
    SettingsUpdate,
    CacheStats,
    LDrawCacheStats,
    DatabaseInfo,
    MigrationInfo,
)
from backend.config import settings
from backend.core.stl_processing import STLConverter
from backend.api.integrations.ldraw import LDrawManager
from backend.database import get_db, ApiCache, engine
from backend.auth import get_current_user
from backend.database import Project, Job, SearchHistory
from backend.database import STLCache, AppSettings
from backend.core.api_cache import DbApiCache

logger = logging.getLogger(__name__)
router = APIRouter()


class ApiKeyUpdate(BaseModel):
    """Update API key."""
    api_key: str


def _get_bool(row, attr: str, default: bool) -> bool:
    v = getattr(row, attr, None)
    return bool(v) if v is not None else default


def _get_float(row, attr: str, default: float) -> float:
    v = getattr(row, attr, None)
    return float(v) if v is not None else default


def _get_int(row, attr: str, default: int) -> int:
    v = getattr(row, attr, None)
    return int(v) if v is not None else default


def _row_to_response(row: AppSettings) -> SettingsResponse:
    """Build SettingsResponse from AppSettings row."""
    return SettingsResponse(
        default_plate_width=row.default_plate_width or 220,
        default_plate_depth=row.default_plate_depth or 220,
        default_plate_height=row.default_plate_height or 250,
        part_spacing=row.part_spacing or 2,
        stl_scale_factor=float(row.stl_scale_factor if row.stl_scale_factor is not None else 1.0),
        rotation_enabled=bool(row.rotation_enabled),
        rotation_x=float(row.rotation_x if row.rotation_x is not None else 0.0),
        rotation_y=float(row.rotation_y if row.rotation_y is not None else 0.0),
        rotation_z=float(row.rotation_z if row.rotation_z is not None else 0.0),
        default_orientation_match_preview=_get_bool(row, "default_orientation_match_preview", True),
        auto_generate_part_previews=_get_bool(row, "auto_generate_part_previews", True),
        ldview_allow_primitive_substitution=_get_bool(row, "ldview_allow_primitive_substitution", True),
        ldview_use_quality_studs=_get_bool(row, "ldview_use_quality_studs", True),
        ldview_curve_quality=_get_int(row, "ldview_curve_quality", 2),
        ldview_seams=_get_bool(row, "ldview_seams", False),
        ldview_seam_width=_get_int(row, "ldview_seam_width", 0),
        ldview_bfc=_get_bool(row, "ldview_bfc", True),
        ldview_bounding_boxes_only=_get_bool(row, "ldview_bounding_boxes_only", False),
        ldview_show_highlight_lines=_get_bool(row, "ldview_show_highlight_lines", False),
        ldview_polygon_offset=_get_bool(row, "ldview_polygon_offset", True),
        ldview_edge_thickness=_get_float(row, "ldview_edge_thickness", 0.0),
        ldview_line_smoothing=_get_bool(row, "ldview_line_smoothing", False),
        ldview_black_highlights=_get_bool(row, "ldview_black_highlights", False),
        ldview_conditional_highlights=_get_bool(row, "ldview_conditional_highlights", False),
        ldview_wireframe=_get_bool(row, "ldview_wireframe", False),
        ldview_wireframe_thickness=_get_float(row, "ldview_wireframe_thickness", 0.0),
        ldview_remove_hidden_lines=_get_bool(row, "ldview_remove_hidden_lines", False),
        ldview_texture_studs=_get_bool(row, "ldview_texture_studs", True),
        ldview_texmaps=_get_bool(row, "ldview_texmaps", True),
        ldview_hi_res_primitives=_get_bool(row, "ldview_hi_res_primitives", False),
        ldview_texture_filter_type=_get_int(row, "ldview_texture_filter_type", 9987),
        ldview_aniso_level=_get_int(row, "ldview_aniso_level", 0),
        ldview_texture_offset_factor=_get_float(row, "ldview_texture_offset_factor", 5.0),
        ldview_lighting=_get_bool(row, "ldview_lighting", True),
        ldview_use_quality_lighting=_get_bool(row, "ldview_use_quality_lighting", False),
        ldview_use_specular=_get_bool(row, "ldview_use_specular", True),
        ldview_subdued_lighting=_get_bool(row, "ldview_subdued_lighting", False),
        ldview_perform_smoothing=_get_bool(row, "ldview_perform_smoothing", True),
        ldview_use_flat_shading=_get_bool(row, "ldview_use_flat_shading", False),
        ldview_antialias=_get_int(row, "ldview_antialias", 0),
        ldview_process_ldconfig=_get_bool(row, "ldview_process_ldconfig", True),
        ldview_sort_transparent=_get_bool(row, "ldview_sort_transparent", True),
        ldview_use_stipple=_get_bool(row, "ldview_use_stipple", False),
        ldview_memory_usage=_get_int(row, "ldview_memory_usage", 2),
    )


def sync_config_from_db(db: Session) -> None:
    """Load app settings from DB and sync into in-memory config. Call before STL/preview conversion so LDView uses persisted settings."""
    row = db.query(AppSettings).filter(AppSettings.id == 1).first()
    if row is not None:
        _sync_config_from_row(row)
        logger.debug("Synced in-memory config from app_settings (LDView/STL will use persisted values)")


def _sync_config_from_row(row: AppSettings) -> None:
    """Update in-memory config from DB row so the rest of the app uses current values."""
    settings.default_plate_width = row.default_plate_width or 220
    settings.default_plate_depth = row.default_plate_depth or 220
    settings.default_plate_height = row.default_plate_height or 250
    settings.part_spacing = row.part_spacing or 2
    settings.stl_scale_factor = float(row.stl_scale_factor if row.stl_scale_factor is not None else 1.0)
    settings.rotation_enabled = bool(row.rotation_enabled)
    settings.rotation_x = float(row.rotation_x if row.rotation_x is not None else 0.0)
    settings.rotation_y = float(row.rotation_y if row.rotation_y is not None else 0.0)
    settings.rotation_z = float(row.rotation_z if row.rotation_z is not None else 0.0)
    settings.default_orientation_match_preview = _get_bool(row, "default_orientation_match_preview", True)
    settings.auto_generate_part_previews = _get_bool(row, "auto_generate_part_previews", True)
    for attr in (
        "ldview_allow_primitive_substitution", "ldview_use_quality_studs", "ldview_curve_quality",
        "ldview_seams", "ldview_seam_width", "ldview_bfc", "ldview_bounding_boxes_only",
        "ldview_show_highlight_lines", "ldview_polygon_offset", "ldview_edge_thickness",
        "ldview_line_smoothing", "ldview_black_highlights", "ldview_conditional_highlights",
        "ldview_wireframe", "ldview_wireframe_thickness", "ldview_remove_hidden_lines",
        "ldview_texture_studs", "ldview_texmaps", "ldview_hi_res_primitives",
        "ldview_texture_filter_type", "ldview_aniso_level", "ldview_texture_offset_factor",
        "ldview_lighting", "ldview_use_quality_lighting", "ldview_use_specular",
        "ldview_subdued_lighting", "ldview_perform_smoothing", "ldview_use_flat_shading",
        "ldview_antialias", "ldview_process_ldconfig", "ldview_sort_transparent",
        "ldview_use_stipple", "ldview_memory_usage",
    ):
        if hasattr(row, attr):
            v = getattr(row, attr)
            if v is not None and hasattr(settings, attr):
                if isinstance(v, bool):
                    setattr(settings, attr, bool(v))
                elif isinstance(v, float):
                    setattr(settings, attr, float(v))
                else:
                    setattr(settings, attr, int(v) if isinstance(getattr(settings, attr), int) else v)


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)):
    """Get current application settings from the database (falls back to config defaults if no row).
    When a row exists, in-memory config is synced so the rest of the app uses persisted values."""
    row = db.query(AppSettings).filter(AppSettings.id == 1).first()
    if row is not None:
        _sync_config_from_row(row)
        return _row_to_response(row)
    return SettingsResponse(
        default_plate_width=settings.default_plate_width,
        default_plate_depth=settings.default_plate_depth,
        default_plate_height=settings.default_plate_height,
        part_spacing=settings.part_spacing,
        stl_scale_factor=float(settings.stl_scale_factor),
        rotation_enabled=settings.rotation_enabled,
        rotation_x=float(settings.rotation_x),
        rotation_y=float(settings.rotation_y),
        rotation_z=float(settings.rotation_z),
        default_orientation_match_preview=settings.default_orientation_match_preview,
        auto_generate_part_previews=settings.auto_generate_part_previews,
        ldview_allow_primitive_substitution=getattr(settings, "ldview_allow_primitive_substitution", True),
        ldview_use_quality_studs=getattr(settings, "ldview_use_quality_studs", True),
        ldview_curve_quality=getattr(settings, "ldview_curve_quality", 2),
        ldview_seams=getattr(settings, "ldview_seams", False),
        ldview_seam_width=getattr(settings, "ldview_seam_width", 0),
        ldview_bfc=getattr(settings, "ldview_bfc", True),
        ldview_bounding_boxes_only=getattr(settings, "ldview_bounding_boxes_only", False),
        ldview_show_highlight_lines=getattr(settings, "ldview_show_highlight_lines", False),
        ldview_polygon_offset=getattr(settings, "ldview_polygon_offset", True),
        ldview_edge_thickness=getattr(settings, "ldview_edge_thickness", 0.0),
        ldview_line_smoothing=getattr(settings, "ldview_line_smoothing", False),
        ldview_black_highlights=getattr(settings, "ldview_black_highlights", False),
        ldview_conditional_highlights=getattr(settings, "ldview_conditional_highlights", False),
        ldview_wireframe=getattr(settings, "ldview_wireframe", False),
        ldview_wireframe_thickness=getattr(settings, "ldview_wireframe_thickness", 0.0),
        ldview_remove_hidden_lines=getattr(settings, "ldview_remove_hidden_lines", False),
        ldview_texture_studs=getattr(settings, "ldview_texture_studs", True),
        ldview_texmaps=getattr(settings, "ldview_texmaps", True),
        ldview_hi_res_primitives=getattr(settings, "ldview_hi_res_primitives", False),
        ldview_texture_filter_type=getattr(settings, "ldview_texture_filter_type", 9987),
        ldview_aniso_level=getattr(settings, "ldview_aniso_level", 0),
        ldview_texture_offset_factor=getattr(settings, "ldview_texture_offset_factor", 5.0),
        ldview_lighting=getattr(settings, "ldview_lighting", True),
        ldview_use_quality_lighting=getattr(settings, "ldview_use_quality_lighting", False),
        ldview_use_specular=getattr(settings, "ldview_use_specular", True),
        ldview_subdued_lighting=getattr(settings, "ldview_subdued_lighting", False),
        ldview_perform_smoothing=getattr(settings, "ldview_perform_smoothing", True),
        ldview_use_flat_shading=getattr(settings, "ldview_use_flat_shading", False),
        ldview_antialias=getattr(settings, "ldview_antialias", 0),
        ldview_process_ldconfig=getattr(settings, "ldview_process_ldconfig", True),
        ldview_sort_transparent=getattr(settings, "ldview_sort_transparent", True),
        ldview_use_stipple=getattr(settings, "ldview_use_stipple", False),
        ldview_memory_usage=getattr(settings, "ldview_memory_usage", 2),
    )


def _validate_ldview_ranges(update: SettingsUpdate) -> None:
    """Raise HTTPException if any LDView numeric field is out of range."""
    if update.ldview_curve_quality is not None and not (1 <= update.ldview_curve_quality <= 12):
        raise HTTPException(status_code=400, detail="ldview_curve_quality must be between 1 and 12")
    if update.ldview_seam_width is not None and not (0 <= update.ldview_seam_width <= 500):
        raise HTTPException(status_code=400, detail="ldview_seam_width must be between 0 and 500")
    if update.ldview_edge_thickness is not None and not (0 <= update.ldview_edge_thickness <= 5):
        raise HTTPException(status_code=400, detail="ldview_edge_thickness must be between 0 and 5")
    if update.ldview_wireframe_thickness is not None and not (0 <= update.ldview_wireframe_thickness <= 5):
        raise HTTPException(status_code=400, detail="ldview_wireframe_thickness must be between 0 and 5")
    if update.ldview_antialias is not None and update.ldview_antialias < 0:
        raise HTTPException(status_code=400, detail="ldview_antialias must be >= 0")
    if update.ldview_texture_offset_factor is not None and not (1 <= update.ldview_texture_offset_factor <= 10):
        raise HTTPException(status_code=400, detail="ldview_texture_offset_factor must be between 1 and 10")
    if update.ldview_memory_usage is not None and update.ldview_memory_usage not in (0, 1, 2):
        raise HTTPException(status_code=400, detail="ldview_memory_usage must be 0 (Low), 1 (Medium), or 2 (High)")
    if update.ldview_texture_filter_type is not None and update.ldview_texture_filter_type not in (9984, 9985, 9987):
        raise HTTPException(status_code=400, detail="ldview_texture_filter_type must be 9984, 9985, or 9987")
    if update.ldview_aniso_level is not None and update.ldview_aniso_level < 0:
        raise HTTPException(status_code=400, detail="ldview_aniso_level must be >= 0")


@router.post("/settings")
async def update_settings(update: SettingsUpdate, db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)):
    """Update application settings. Persists to database and syncs in-memory config.

    If rotation, default_orientation_match_preview, or any LDView quality setting is changed, STL cache is cleared.
    """
    _validate_ldview_ranges(update)
    cache_cleared = False
    converter = STLConverter()

    # Load current from DB (or create default row if missing)
    row = db.query(AppSettings).filter(AppSettings.id == 1).first()
    if row is None:
        row = AppSettings(id=1)
        db.add(row)
        db.commit()
        db.refresh(row)

    # Capture previous values for cache-clear logic (use current in-memory or row)
    prev_rotation = getattr(row, "rotation_enabled", False)
    prev_orientation = getattr(row, "default_orientation_match_preview", True)

    # Check if any LDView setting is being updated (clear cache once for any ldview change)
    ldview_attrs = [
        "ldview_allow_primitive_substitution", "ldview_use_quality_studs", "ldview_curve_quality",
        "ldview_seams", "ldview_seam_width", "ldview_bfc", "ldview_bounding_boxes_only",
        "ldview_show_highlight_lines", "ldview_polygon_offset", "ldview_edge_thickness",
        "ldview_line_smoothing", "ldview_black_highlights", "ldview_conditional_highlights",
        "ldview_wireframe", "ldview_wireframe_thickness", "ldview_remove_hidden_lines",
        "ldview_texture_studs", "ldview_texmaps", "ldview_hi_res_primitives",
        "ldview_texture_filter_type", "ldview_aniso_level", "ldview_texture_offset_factor",
        "ldview_lighting", "ldview_use_quality_lighting", "ldview_use_specular",
        "ldview_subdued_lighting", "ldview_perform_smoothing", "ldview_use_flat_shading",
        "ldview_antialias", "ldview_process_ldconfig", "ldview_sort_transparent",
        "ldview_use_stipple", "ldview_memory_usage",
    ]
    any_ldview_update = any(getattr(update, a, None) is not None for a in ldview_attrs)

    # Apply updates to row (persist to DB)
    if update.default_plate_width is not None:
        row.default_plate_width = update.default_plate_width
    if update.default_plate_depth is not None:
        row.default_plate_depth = update.default_plate_depth
    if update.default_plate_height is not None:
        row.default_plate_height = update.default_plate_height
    if update.part_spacing is not None:
        row.part_spacing = update.part_spacing
    if update.stl_scale_factor is not None:
        row.stl_scale_factor = float(update.stl_scale_factor)
    if update.rotation_enabled is not None:
        if update.rotation_enabled != prev_rotation:
            try:
                deleted_count = converter.clear_cache(db=db)
                cache_cleared = True
                logger.info(f"Cleared {deleted_count} STL files due to rotation change")
            except Exception as e:
                logger.error(f"Failed to clear cache after rotation change: {e}")
        row.rotation_enabled = update.rotation_enabled
    if update.rotation_x is not None:
        row.rotation_x = update.rotation_x
    if update.rotation_y is not None:
        row.rotation_y = update.rotation_y
    if update.rotation_z is not None:
        row.rotation_z = update.rotation_z
    if update.default_orientation_match_preview is not None:
        if update.default_orientation_match_preview != prev_orientation:
            try:
                deleted_count = converter.clear_cache(db=db)
                cache_cleared = True
                logger.info(f"Cleared {deleted_count} STL files due to default orientation change")
            except Exception as e:
                logger.error(f"Failed to clear cache after default orientation change: {e}")
        row.default_orientation_match_preview = update.default_orientation_match_preview
    if update.auto_generate_part_previews is not None:
        row.auto_generate_part_previews = update.auto_generate_part_previews

    for attr in ldview_attrs:
        v = getattr(update, attr, None)
        if v is not None and hasattr(row, attr):
            setattr(row, attr, v)

    if any_ldview_update and not cache_cleared:
        try:
            deleted_count = converter.clear_cache(db=db)
            cache_cleared = True
            logger.info(f"Cleared {deleted_count} STL files due to LDView quality setting change")
        except Exception as e:
            logger.error(f"Failed to clear cache after LDView setting change: {e}")

    db.commit()
    db.refresh(row)

    # Sync in-memory config so the rest of the app uses new values immediately
    _sync_config_from_row(row)

    return {
        "settings": _row_to_response(row),
        "cache_cleared": cache_cleared,
    }


class CachedSetSummary(BaseModel):
    """Cached set summary for Rebrickable cache list."""
    set_num: str
    name: str
    cached_at: str  # updated_at ISO format
    image_url: Optional[str] = None
    year: Optional[int] = None
    pieces: Optional[int] = None


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
    page_size: int = Query(10, ge=1, le=100, description="Items per page (pagination after this many)")
):
    """List cached sets (Rebrickable cache) with set_num, name, cached_at. Paginated (default 10 per page)."""
    import json as _json
    prefix = "rebrickable:set:"
    q = db.query(ApiCache).filter(ApiCache.key.like(f"{prefix}%")).order_by(ApiCache.updated_at.desc())
    count = q.count()
    offset = (page - 1) * page_size
    rows = q.offset(offset).limit(page_size).all()
    total_pages = (count + page_size - 1) // page_size if page_size else 0
    results = []
    for r in rows:
        set_num = r.key[len(prefix):] if r.key.startswith(prefix) else r.key
        try:
            data = _json.loads(r.value) if isinstance(r.value, str) else r.value
            name = (data.get("name") or "")
            image_url = data.get("image_url")
            year = data.get("year")
            pieces = data.get("pieces")
        except (TypeError, ValueError):
            name = ""
            image_url = year = pieces = None
        results.append(CachedSetSummary(
            set_num=set_num,
            name=name,
            cached_at=r.updated_at.isoformat() if r.updated_at else "",
            image_url=image_url,
            year=year,
            pieces=pieces,
        ))
    return RebrickableCacheList(
        results=results,
        count=count,
        page=page,
        page_size=page_size,
        next=page + 1 if page < total_pages else None,
        previous=page - 1 if page > 1 else None,
    )


@router.get("/cache/rebrickable/random", response_model=List[CachedSetSummary])
async def list_random_cached_sets(
    db: Session = Depends(get_db),
    limit: int = Query(15, ge=1, le=50, description="Number of random cached sets to return (configurable)"),
):
    """Return a random sample of cached sets. For display on the main Search page."""
    import json as _json
    prefix = "rebrickable:set:"
    q = (
        db.query(ApiCache)
        .filter(ApiCache.key.like(f"{prefix}%"))
        .order_by(func.random())
        .limit(limit)
    )
    rows = q.all()
    results = []
    for r in rows:
        set_num = r.key[len(prefix):] if r.key.startswith(prefix) else r.key
        try:
            data = _json.loads(r.value) if isinstance(r.value, str) else r.value
            name = (data.get("name") or "")
            image_url = data.get("image_url")
            year = data.get("year")
            pieces = data.get("pieces")
        except (TypeError, ValueError):
            name = ""
            image_url = year = pieces = None
        results.append(CachedSetSummary(
            set_num=set_num,
            name=name,
            cached_at=r.updated_at.isoformat() if r.updated_at else "",
            image_url=image_url,
            year=year,
            pieces=pieces,
        ))
    return results


@router.delete("/cache/rebrickable")
async def clear_rebrickable_cache(
    set_num: Optional[str] = Query(None, description="If set, clear only this set; otherwise clear all"),
    db: Session = Depends(get_db)
):
    """Clear Rebrickable cache: all cached sets (and their parts) or a single set."""
    from backend.api.integrations.rebrickable import CACHE_KEY_SET, CACHE_KEY_SET_INDEX, CACHE_KEY_SET_PARTS

    if set_num:
        norm = set_num if "-" in set_num else f"{set_num}-1"
        keys_to_delete = [
            f"{CACHE_KEY_SET}{set_num}",
            f"{CACHE_KEY_SET}{norm}",
            f"{CACHE_KEY_SET_PARTS}{set_num}",
            f"{CACHE_KEY_SET_PARTS}{norm}",
        ]
        deleted_api = DbApiCache.delete_keys(db, keys_to_delete)
        # Remove set from set index (used by suggest)
        cache = DbApiCache(db)
        index = cache.get(CACHE_KEY_SET_INDEX) or []
        index = [x for x in index if x.get("set_num") not in (set_num, norm)]
        cache.set(CACHE_KEY_SET_INDEX, index)
        return {"message": f"Cleared cache for set {set_num}", "api_cache": deleted_api}
    else:
        deleted_api = DbApiCache.delete_by_prefix(db, "rebrickable:")
        return {"message": "Cleared all Rebrickable cache", "api_cache": deleted_api}


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
async def clear_cache(db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)):
    """Clear all cached STL files and STL cache DB rows."""
    try:
        converter = STLConverter()
        deleted_count = converter.clear_cache(db=db)
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
            library_path=stats.get('path', str(manager.library_path)),
            version=stats.get('version'),
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


@router.post("/ldraw/download")
async def download_ldraw():
    """Download LDraw library on demand (~40MB). Required for part previews and STL generation."""
    try:
        manager = LDrawManager()
        if manager.get_library_stats().get("exists"):
            return {
                "success": True,
                "message": "LDraw library already exists.",
            }
        ok = await manager.download_library()
        if not ok:
            raise HTTPException(status_code=500, detail="Failed to download LDraw library.")
        return {
            "success": True,
            "message": "LDraw library downloaded successfully.",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading LDraw library: {e}")
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


def _get_applied_revision_ids(script_dir, current_id: Optional[str]) -> set:
    """Return set of revision ids that are applied (from base to current)."""
    if not current_id:
        return set()
    applied = set()
    rev = script_dir.get_revision(current_id)
    while rev:
        applied.add(rev.revision)
        down = rev.down_revision
        rev = script_dir.get_revision(down) if down else None
        if down and isinstance(down, (list, tuple)):
            rev = script_dir.get_revision(down[0]) if down else None
    return applied


@router.get("/settings/database", response_model=DatabaseInfo)
async def get_database_info(db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)):
    """Return database path, applied migrations, and row counts per table."""
    from alembic.script import ScriptDirectory

    database_path = str(settings.database_path)
    table_counts = {}
    tables = [
        ("projects", Project),
        ("api_cache", ApiCache),
        ("jobs", Job),
        ("search_history", SearchHistory),
        ("app_settings", AppSettings),
        ("stl_cache", STLCache),
    ]
    for _name, model in tables:
        try:
            table_counts[model.__tablename__] = db.query(model).count()
        except Exception:
            table_counts[model.__tablename__] = 0

    current_revision = None
    with engine.connect() as conn:
        try:
            r = conn.execute(text("SELECT version_num FROM alembic_version"))
            row = r.fetchone()
            if row:
                current_revision = row[0]
        except Exception as e:
            # Log so we can see why the read failed (missing table, locked DB, wrong path, etc.)
            logger.warning("Could not read alembic_version: %s", e, exc_info=False)

    # __file__ is backend/api/routes/settings.py -> backend is parent.parent.parent, project root is parent.parent.parent.parent
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    script_location = project_root / "alembic"
    script_dir = ScriptDirectory(str(script_location))
    applied_ids = _get_applied_revision_ids(script_dir, current_revision)

    migrations = []
    for rev in script_dir.walk_revisions(base="base", head="head"):
        doc = (rev.doc or "").strip() or rev.revision
        migrations.append(
            MigrationInfo(
                revision_id=rev.revision,
                description=doc.split("\n")[0] if doc else rev.revision,
                applied=rev.revision in applied_ids,
            )
        )
    # Order so applied (oldest first) then pending
    migrations.reverse()

    return DatabaseInfo(
        database_path=database_path,
        current_revision=current_revision,
        migrations=migrations,
        table_counts=table_counts,
    )
