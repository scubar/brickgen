"""STL processing and conversion using LDView."""
import logging
from pathlib import Path
from typing import Optional
from backend.config import settings
from backend.core.ldview_converter import LDViewConverter
from backend.core.stl_orientation import STLOrienter

logger = logging.getLogger(__name__)


class STLConverter:
    """High-level STL conversion with caching using LDView."""
    
    def __init__(self):
        self.cache_dir = settings.cache_dir / "stl_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.converter = LDViewConverter(settings.ldraw_library_path)
        self.orienter = STLOrienter()

    def _rotation_suffix(self, rotation_enabled: bool, rx: float, ry: float, rz: float) -> str:
        """Cache suffix so different rotations get different cached files."""
        if not rotation_enabled or (rx == 0 and ry == 0 and rz == 0):
            return ""
        return f"_r{rx:.0f}_{ry:.0f}_{rz:.0f}"

    def get_or_convert_stl(self, ldraw_id: str, bypass_cache: bool = False,
                          scale_factor: float = 10.0, rotation_enabled: bool = False,
                          rotation_x: float = 0.0, rotation_y: float = 0.0, rotation_z: float = 0.0) -> Optional[Path]:
        """Get cached STL or convert from LDraw using LDView.
        
        Args:
            ldraw_id: LDraw part ID (e.g., "3005", "3001")
            bypass_cache: If True, reconvert even if cached
            scale_factor: Scale factor (default 10 = LDView cm to mm; calibration: 3034, 3404)
            rotation_enabled: If True, apply absolute rotation
            rotation_x, rotation_y, rotation_z: Rotation in degrees
        """
        if not ldraw_id:
            logger.warning("No LDraw ID provided")
            return None

        rot_suffix = self._rotation_suffix(rotation_enabled, rotation_x, rotation_y, rotation_z)
        stl_path = self.cache_dir / f"{ldraw_id}{rot_suffix}.stl"

        if stl_path.exists() and not bypass_cache:
            logger.debug(f"Using cached STL for {ldraw_id}")
            return stl_path

        logger.info(f"Converting {ldraw_id} with LDView (scale={scale_factor}, rotation={rotation_enabled})...")
        if not self.converter.convert_to_stl(ldraw_id, stl_path, scale_factor=scale_factor):
            logger.warning(f"Failed to convert {ldraw_id} to STL")
            return None

        if rotation_enabled and (rotation_x != 0 or rotation_y != 0 or rotation_z != 0):
            logger.info(f"Applying rotation for {ldraw_id} (X={rotation_x}, Y={rotation_y}, Z={rotation_z})...")
            if not self.orienter.apply_absolute_rotation(stl_path, rotation_x, rotation_y, rotation_z):
                logger.warning(f"Rotation failed for {ldraw_id}, using unconverted orientation")

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
    
    def clear_cache(self) -> int:
        """Clear all cached STL files.
        
        Returns:
            Number of files deleted
        """
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
