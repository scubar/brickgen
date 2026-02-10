"""Settings routes."""
import logging
import os
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from sqlalchemy import text
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
from backend.database import get_db, CachedSet, CachedParts, engine
from backend.database import Project, Job, SearchHistory
from backend.database import STLCache, AppSettings

logger = logging.getLogger(__name__)
router = APIRouter()


class ApiKeyUpdate(BaseModel):
    """Update API key."""
    api_key: str


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
        default_orientation_match_preview=bool(row.default_orientation_match_preview if row.default_orientation_match_preview is not None else True),
        auto_generate_part_previews=bool(row.auto_generate_part_previews if row.auto_generate_part_previews is not None else True),
    )


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
    settings.default_orientation_match_preview = bool(row.default_orientation_match_preview if row.default_orientation_match_preview is not None else True)
    settings.auto_generate_part_previews = bool(row.auto_generate_part_previews if row.auto_generate_part_previews is not None else True)


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(db: Session = Depends(get_db)):
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
    )


@router.post("/settings")
async def update_settings(update: SettingsUpdate, db: Session = Depends(get_db)):
    """Update application settings. Persists to database and syncs in-memory config.

    If rotation or default_orientation_match_preview is changed, STL cache is cleared (files + DB).
    """
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
async def clear_cache(db: Session = Depends(get_db)):
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
async def get_database_info(db: Session = Depends(get_db)):
    """Return database path, applied migrations, and row counts per table."""
    from alembic.script import ScriptDirectory

    database_path = str(settings.database_path)
    table_counts = {}
    tables = [
        ("projects", Project),
        ("cached_sets", CachedSet),
        ("cached_parts", CachedParts),
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
        except Exception:
            pass

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
