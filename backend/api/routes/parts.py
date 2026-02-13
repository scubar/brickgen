"""Part preview and part-related API."""
import logging
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import FileResponse
from backend.config import settings
from backend.core.ldview_converter import LDViewConverter, get_ldview_quality_key
from backend.core.stl_processing import STLConverter
from backend.core.stl_render import render_stl_to_png
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.auth import get_current_user
from backend.api.routes.settings import sync_config_from_db

logger = logging.getLogger(__name__)
router = APIRouter()

PREVIEW_SIZE_DEFAULT = 512
PREVIEW_SIZE_MAX = 1024


def _rotation_suffix(rx: float, ry: float, rz: float) -> str:
    """Cache suffix for rotation; empty when all zero."""
    if rx == 0 and ry == 0 and rz == 0:
        return ""
    return f"_r{float(rx):.0f}_{float(ry):.0f}_{float(rz):.0f}"


@router.get("/parts/preview/{ldraw_id}")
async def get_part_preview(
    ldraw_id: str,
    size: int = Query(PREVIEW_SIZE_DEFAULT, ge=64, le=PREVIEW_SIZE_MAX, description="Image width/height in pixels"),
    rotation_x: float = Query(0.0, description="Rotation X degrees"),
    rotation_y: float = Query(0.0, description="Rotation Y degrees"),
    rotation_z: float = Query(0.0, description="Rotation Z degrees"),
    color: Optional[str] = Query(None, description="Hex color for part (e.g. FF5500); used when rendering rotated preview"),
    db: Session = Depends(get_db),
):
    """Return a PNG preview image for an LDraw part. With rotation params, preview shows the part with that rotation applied. Cached per size and rotation."""
    sync_config_from_db(db)  # use persisted LDView settings for preview/STL
    if not ldraw_id or not ldraw_id.replace("-", "").replace("_", "").replace(".", "").isalnum():
        raise HTTPException(status_code=400, detail="Invalid part ID")
    ldraw_id = ldraw_id.strip().lower()
    cache_dir = Path(settings.cache_dir) / "preview_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    rot_suffix = _rotation_suffix(rotation_x, rotation_y, rotation_z)
    hex_color = None
    if color and isinstance(color, str) and color.strip():
        c = color.strip().lstrip("#")
        if len(c) == 6 and all(x in "0123456789abcdefABCDEF" for x in c):
            hex_color = f"#{c}"
    color_suffix = f"_c{hex_color.lstrip('#')}" if hex_color else ""
    quality_key = get_ldview_quality_key()
    preview_path = cache_dir / f"{ldraw_id}_{size}{rot_suffix}{color_suffix}_q{quality_key}.png"
    if preview_path.exists():
        return FileResponse(str(preview_path), media_type="image/png")

    use_rotation = rotation_x != 0 or rotation_y != 0 or rotation_z != 0
    use_stl_render = use_rotation or hex_color
    if use_stl_render:
        stl_converter = STLConverter()
        stl_path = stl_converter.get_or_convert_stl(
            ldraw_id,
            bypass_cache=False,
            scale_factor=getattr(settings, "stl_scale_factor_backend", 10.0),
            rotation_enabled=use_rotation,
            rotation_x=rotation_x,
            rotation_y=rotation_y,
            rotation_z=rotation_z,
        )
        if not stl_path or not stl_path.exists():
            raise HTTPException(status_code=404, detail=f"Preview not available for part {ldraw_id}")
        if not render_stl_to_png(stl_path, preview_path, size=size, face_color=hex_color):
            raise HTTPException(status_code=500, detail="Failed to render preview")
        return FileResponse(str(preview_path), media_type="image/png")

    converter = LDViewConverter(settings.ldraw_library_path)
    if not converter.export_snapshot(ldraw_id, preview_path, width=size, height=size):
        raise HTTPException(status_code=404, detail=f"Preview not available for part {ldraw_id}")
    return FileResponse(str(preview_path), media_type="image/png")


def _parse_preview_filename(stem: str) -> dict:
    """Parse preview cache filename stem to ldraw_id, size, rotation, quality_key. E.g. 3005_256_qabc12 or 3005_512_r-90_0_0_cff5500_qabc12."""
    import re
    m = re.match(r"^(.+?)_(\d+)(_r(-?\d+)_(-?\d+)_(-?\d+))?(_c[0-9a-fA-F]+)?(_q[0-9a-f]+)?$", stem)
    if not m:
        return {}
    ldraw_id, size_str = m.group(1), m.group(2)
    rx = int(m.group(4)) if m.group(4) is not None else 0
    ry = int(m.group(5)) if m.group(5) is not None else 0
    rz = int(m.group(6)) if m.group(6) is not None else 0
    q_suffix = m.group(8)  # _q{hex} or None
    quality_key = q_suffix[2:] if q_suffix else ""
    return {"ldraw_id": ldraw_id, "size": int(size_str), "rotation_x": rx, "rotation_y": ry, "rotation_z": rz, "quality_key": quality_key}


@router.get("/parts/preview-cache/list")
async def list_preview_cache():
    """List cached part preview entries (filename stems) for the cache manager."""
    cache_dir = Path(settings.cache_dir) / "preview_cache"
    if not cache_dir.exists():
        return {"count": 0, "items": []}
    items = []
    seen = set()
    for f in sorted(cache_dir.glob("*.png")):
        parsed = _parse_preview_filename(f.stem)
        if parsed:
            key = (parsed["ldraw_id"], parsed["size"], parsed["rotation_x"], parsed["rotation_y"], parsed["rotation_z"], parsed.get("quality_key", ""))
            if key not in seen:
                seen.add(key)
                items.append(parsed)
    return {"count": len(items), "items": items}


@router.delete("/parts/preview-cache")
async def clear_preview_cache():
    """Delete all cached part preview images."""
    cache_dir = Path(settings.cache_dir) / "preview_cache"
    if not cache_dir.exists():
        return {"message": "Preview cache is empty", "deleted_count": 0}
    deleted = 0
    for f in cache_dir.glob("*.png"):
        try:
            f.unlink()
            deleted += 1
        except OSError as e:
            logger.warning(f"Could not delete {f}: {e}")
    return {"message": f"Cleared {deleted} preview image(s)", "deleted_count": deleted}
