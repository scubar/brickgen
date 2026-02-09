"""LDraw library manager and STL converter."""
import logging
import asyncio
import re
from pathlib import Path
from typing import Optional
import aiohttp
import zipfile
import io
from backend.config import settings

logger = logging.getLogger(__name__)

LDRAW_VERSION_FILE = ".ldraw_version"
LDRAW_UPDATES_URL = "https://library.ldraw.org/updates?latest"
PARTS_UPDATE_PATTERN = re.compile(r"Parts Update\s+(\d{4}-\d{2})", re.IGNORECASE)


class LDrawManager:
    """Manages LDraw parts library and conversions."""
    
    LDRAW_COMPLETE_URL = "https://library.ldraw.org/library/updates/complete.zip"
    
    def __init__(self, library_path: Optional[Path] = None):
        self.library_path = library_path or settings.ldraw_library_path
        self.parts_dir = self.library_path / "parts"
        self.p_dir = self.library_path / "p"
    
    async def _fetch_library_version(self) -> Optional[str]:
        """Fetch current LDraw library release version from library.ldraw.org (e.g. 2025-10)."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(LDRAW_UPDATES_URL) as response:
                    response.raise_for_status()
                    text = await response.text()
            m = PARTS_UPDATE_PATTERN.search(text)
            return m.group(1) if m else None
        except Exception as e:
            logger.warning(f"Could not fetch LDraw library version: {e}")
            return None
    
    async def ensure_library_exists(self) -> bool:
        """Check if LDraw library exists, download if not."""
        if self.parts_dir.exists() and any(self.parts_dir.glob("*.dat")):
            logger.info("LDraw library already exists")
            return True
        
        logger.info("LDraw library not found, downloading...")
        return await self.download_library()
    
    async def download_library(self) -> bool:
        """Download and extract LDraw complete library."""
        try:
            self.library_path.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Downloading LDraw library from {self.LDRAW_COMPLETE_URL}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.LDRAW_COMPLETE_URL) as response:
                    response.raise_for_status()
                    
                    # Read the entire zip file into memory
                    zip_data = await response.read()
                    logger.info(f"Downloaded {len(zip_data)} bytes")
                    
                    # Extract in a thread to avoid blocking
                    await asyncio.to_thread(self._extract_zip, zip_data)
            
            # Record library version from updates page (e.g. 2025-10)
            version = await self._fetch_library_version()
            if version:
                version_file = self.library_path / LDRAW_VERSION_FILE
                version_file.write_text(version, encoding="utf-8")
                logger.info(f"LDraw library version recorded: {version}")
            
            logger.info("LDraw library downloaded and extracted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error downloading LDraw library: {e}")
            return False
    
    def _extract_zip(self, zip_data: bytes):
        """Extract zip file synchronously."""
        import shutil
        temp_extract = self.library_path / "temp_extract"
        temp_extract.mkdir(exist_ok=True)
        
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            zf.extractall(temp_extract)
        
        # LDraw complete.zip extracts to ldraw/ subdirectory
        # Move contents up one level if needed
        extracted_ldraw = temp_extract / "ldraw"
        if extracted_ldraw.exists():
            # Move all contents from temp_extract/ldraw/ to library_path/
            for item in extracted_ldraw.iterdir():
                dest = self.library_path / item.name
                if dest.exists():
                    if dest.is_dir():
                        shutil.rmtree(dest)
                    else:
                        dest.unlink()
                shutil.move(str(item), str(dest))
            # Clean up temp directory
            shutil.rmtree(temp_extract)
        else:
            # If no nested ldraw/, just move everything
            for item in temp_extract.iterdir():
                shutil.move(str(item), str(self.library_path / item.name))
            temp_extract.rmdir()
    
    def find_part_file(self, part_num: str) -> Optional[Path]:
        """Find LDraw .dat file for a given part number.
        
        Args:
            part_num: Part number (e.g., "3001" for 2x4 brick)
        
        Returns:
            Path to .dat file or None if not found
        """
        # Clean part number (remove color codes, etc.)
        clean_num = part_num.replace(".dat", "").strip()
        
        # Try different naming conventions
        possible_names = [
            f"{clean_num}.dat",
            f"{clean_num.lower()}.dat",
            f"{clean_num}a.dat",  # Some parts have letter suffixes
        ]
        
        for name in possible_names:
            part_path = self.parts_dir / name
            if part_path.exists():
                return part_path
        
        logger.warning(f"Part file not found for {part_num}")
        return None
    
    def get_library_stats(self) -> dict:
        """Get statistics about the LDraw library."""
        if not self.parts_dir.exists():
            return {"exists": False, "part_count": 0}
        
        part_count = len(list(self.parts_dir.glob("*.dat")))
        version = None
        version_file = self.library_path / LDRAW_VERSION_FILE
        if version_file.exists():
            try:
                version = version_file.read_text(encoding="utf-8").strip() or None
            except Exception:
                pass
        
        return {
            "exists": True,
            "part_count": part_count,
            "path": str(self.library_path),
            "version": version,
        }
