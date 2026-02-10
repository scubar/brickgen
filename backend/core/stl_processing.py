"""STL processing and conversion using LDView."""
import logging
from pathlib import Path
from typing import Optional, TYPE_CHECKING
from backend.config import settings
from backend.core.ldview_converter import LDViewConverter, get_ldview_quality_key
from backend.core.stl_orientation import STLOrienter

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _cache_filename(
    part_num: str,
    scale: float,
    rotation_enabled: bool,
    rotation_x: float,
    rotation_y: float,
    rotation_z: float,
    quality_key: str,
) -> str:
    """Build cache filename stem. Omit segments when 0 or false to keep names short."""
    parts = [part_num]
    if scale != 0:
        parts.append(f"scale{int(round(scale))}")
    if rotation_enabled:
        parts.append("rotation1")
    if rotation_x != 0:
        parts.append(f"rotationX{int(round(rotation_x))}")
    if rotation_y != 0:
        parts.append(f"rotationY{int(round(rotation_y))}")
    if rotation_z != 0:
        parts.append(f"rotationZ{int(round(rotation_z))}")
    if quality_key:
        parts.append(f"q{quality_key}")
    return "_".join(parts)


class STLConverter:
    """High-level STL conversion with caching using LDView."""

    def __init__(self):
        self.cache_dir = settings.cache_dir / "stl_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.converter = LDViewConverter(settings.ldraw_library_path)
        self.orienter = STLOrienter()

    def _rotation_suffix(self, rotation_enabled: bool, rx: float, ry: float, rz: float) -> str:
        """Cache suffix so different rotations get different cached files (legacy/compat)."""
        if not rotation_enabled or (rx == 0 and ry == 0 and rz == 0):
            return ""
        return f"_r{rx:.0f}_{ry:.0f}_{rz:.0f}"

    def get_or_convert_stl(
        self,
        ldraw_id: str,
        bypass_cache: bool = False,
        scale_factor: float = 10.0,
        rotation_enabled: bool = False,
        rotation_x: float = 0.0,
        rotation_y: float = 0.0,
        rotation_z: float = 0.0,
        db: Optional["Session"] = None,
    ) -> Optional[Path]:
        """Get cached STL or convert from LDraw. When db is provided, lookups are DB-first; if DB row exists but file is missing, regenerate at expected path."""
        if not ldraw_id:
            logger.warning("No LDraw ID provided")
            return None

        quality_key = get_ldview_quality_key()
        stem = _cache_filename(
            ldraw_id, scale_factor, rotation_enabled, rotation_x, rotation_y, rotation_z, quality_key
        )
        stl_path = self.cache_dir / f"{stem}.stl"

        if db is not None and not bypass_cache:
            from backend.database import STLCache

            row = (
                db.query(STLCache)
                .filter(
                    STLCache.part_num == ldraw_id,
                    STLCache.scale == scale_factor,
                    STLCache.rotation_enabled == rotation_enabled,
                    STLCache.rotation_x == rotation_x,
                    STLCache.rotation_y == rotation_y,
                    STLCache.rotation_z == rotation_z,
                    STLCache.quality_key == quality_key,
                )
                .first()
            )
            if row is not None:
                path = Path(row.file_path)
                if path.exists():
                    logger.debug(f"Using cached STL for {ldraw_id} from DB")
                    return path
                # File missing: regenerate at expected path
                logger.info(f"STL cache DB hit but file missing for {ldraw_id}, regenerating at {stl_path}")
            # No row or file missing: fall through to convert and then insert/update
        elif stl_path.exists() and not bypass_cache:
            logger.debug(f"Using cached STL for {ldraw_id} (filesystem)")
            return stl_path

        rot_detail = f", rotation=({rotation_x}, {rotation_y}, {rotation_z})" if rotation_enabled else ""
        logger.info(
            f"Converting {ldraw_id} with LDView (scale={scale_factor}, rotation_enabled={rotation_enabled}{rot_detail}, quality_key={quality_key})..."
        )
        if not self.converter.convert_to_stl(ldraw_id, stl_path, scale_factor=scale_factor):
            logger.warning(f"Failed to convert {ldraw_id} to STL")
            return None

        if rotation_enabled and (rotation_x != 0 or rotation_y != 0 or rotation_z != 0):
            logger.info(
                f"Applying rotation for {ldraw_id} (X={rotation_x}, Y={rotation_y}, Z={rotation_z})..."
            )
            if not self.orienter.apply_absolute_rotation(
                stl_path, rotation_x, rotation_y, rotation_z
            ):
                logger.warning(f"Rotation failed for {ldraw_id}, using unconverted orientation")

        if db is not None:
            from backend.database import STLCache

            file_size = stl_path.stat().st_size if stl_path.exists() else 0
            row = (
                db.query(STLCache)
                .filter(
                    STLCache.part_num == ldraw_id,
                    STLCache.scale == scale_factor,
                    STLCache.rotation_enabled == rotation_enabled,
                    STLCache.rotation_x == rotation_x,
                    STLCache.rotation_y == rotation_y,
                    STLCache.rotation_z == rotation_z,
                    STLCache.quality_key == quality_key,
                )
                .first()
            )
            if row is not None:
                row.file_path = str(stl_path)
                row.file_size = file_size
                db.commit()
            else:
                entry = STLCache(
                    part_num=ldraw_id,
                    file_path=str(stl_path),
                    file_size=file_size,
                    rotation_enabled=rotation_enabled,
                    rotation_x=rotation_x,
                    rotation_y=rotation_y,
                    rotation_z=rotation_z,
                    scale=scale_factor,
                    quality_key=quality_key,
                )
                db.add(entry)
                db.commit()

        return stl_path
    
    def get_cache_stats(self) -> dict:
        """Get statistics about the STL cache.
        
        Returns:
            Dictionary with count and total size
        """
        stl_files = list(self.cache_dir.glob("*.stl"))
        total_size = sum(f.stat().st_size for f in stl_files)
        
        return {
            "count": len(stl_files),
            "total_size_mb": total_size / (1024 * 1024),
            "cache_dir": str(self.cache_dir)
        }
    
    def clear_cache(self, db: Optional["Session"] = None) -> int:
        """Clear all cached STL files. When db is provided, also delete all STLCache rows.

        Returns:
            Number of files deleted
        """
        if db is not None:
            from backend.database import STLCache
            deleted_rows = db.query(STLCache).delete()
            db.commit()
            logger.info(f"Cleared {deleted_rows} STL cache rows from DB")

        stl_files = list(self.cache_dir.glob("*.stl"))
        count = 0
        for stl_file in stl_files:
            try:
                stl_file.unlink()
                count += 1
            except Exception as e:
                logger.error(f"Failed to delete {stl_file}: {e}")

        logger.info(f"Cleared {count} STL files from cache")
        return count
