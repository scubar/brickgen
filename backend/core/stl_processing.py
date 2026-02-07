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
        self.orienter = STLOrienter(strategy=settings.orientation_strategy)
    
    def get_or_convert_stl(self, ldraw_id: str, bypass_cache: bool = False, 
                          scale_factor: float = 16.67, auto_orient: bool = True) -> Optional[Path]:
        """Get cached STL or convert from LDraw using LDView.
        
        Args:
            ldraw_id: LDraw part ID (e.g., "3005", "3001")
            bypass_cache: If True, reconvert even if cached
            scale_factor: Scale factor for millimeter conversion (default 16.67)
            auto_orient: If True, automatically orient for optimal printing
        
        Returns:
            Path to STL file or None if conversion fails
        """
        if not ldraw_id:
            logger.warning("No LDraw ID provided")
            return None
        
        # Cache key includes orientation flag
        cache_suffix = "_oriented" if auto_orient else ""
        stl_path = self.cache_dir / f"{ldraw_id}{cache_suffix}.stl"
        
        # Check cache first (unless bypassing)
        if stl_path.exists() and not bypass_cache:
            logger.debug(f"Using cached STL for {ldraw_id}")
            return stl_path
        
        # Convert using LDView
        logger.info(f"Converting {ldraw_id} with LDView (scale={scale_factor}, orient={auto_orient})...")
        if self.converter.convert_to_stl(ldraw_id, stl_path, scale_factor=scale_factor):
            # Apply orientation optimization if requested
            if auto_orient:
                logger.info(f"Optimizing orientation for {ldraw_id}...")
                if not self.orienter.optimize_orientation(stl_path):
                    logger.warning(f"Orientation optimization failed for {ldraw_id}, using default")
            
            return stl_path
        
        logger.warning(f"Failed to convert {ldraw_id} to STL")
        return None
    
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
