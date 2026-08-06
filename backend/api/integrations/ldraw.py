"""LDraw library manager and STL converter."""
import logging
import asyncio
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
import aiohttp
import zipfile
import io
from backend.config import settings

logger = logging.getLogger(__name__)

LDRAW_VERSION_FILE = ".ldraw_version"
LDRAW_UPDATES_URL = "https://library.ldraw.org/updates?latest"
PARTS_UPDATE_PATTERN = re.compile(r"Parts Update\s+(\d{4}-\d{2})", re.IGNORECASE)


def _parse_dat_description(path: Path) -> Optional[str]:
    """Return the description from the first line of an LDraw .dat file.

    LDraw .dat files start with a line like:
        0 Brick  2 x  4
    where '0' is the line type and the rest is the description.
    """
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                line = raw.strip()
                if not line:
                    continue
                # LDraw line type 0 = meta/comment; first such line is the description.
                # Skip pure meta-keywords: comment markers (//) and file references (FILE).
                _SKIP_PREFIXES = ("//", "FILE", "!LDRAW_ORG", "!LICENSE", "!CATEGORY", "!KEYWORDS", "!HISTORY")
                parts = line.split(None, 1)
                if parts and parts[0] == "0" and len(parts) > 1:
                    desc = parts[1].strip()
                    if desc and not any(desc.startswith(p) for p in _SKIP_PREFIXES):
                        return desc
                break
    except Exception:
        pass
    return None


def build_ldraw_part_index(db, parts_dir: Optional[Path] = None) -> int:
    """Scan the LDraw parts directory and populate the ldraw_part_index table.

    Returns the number of parts indexed.
    """
    from backend.database import LDrawPartIndex

    if parts_dir is None:
        parts_dir = settings.ldraw_library_path / "parts"

    if not parts_dir.exists():
        logger.warning(f"LDraw parts directory not found: {parts_dir}")
        return 0

    now = datetime.utcnow()
    count = 0

    for dat_file in sorted(parts_dir.glob("*.dat")):
        part_num = dat_file.stem.lower()
        description = _parse_dat_description(dat_file)
        # Upsert: update description if part already indexed
        existing = db.query(LDrawPartIndex).filter(LDrawPartIndex.part_num == part_num).first()
        if existing:
            existing.description = description
            existing.indexed_at = now
        else:
            db.add(LDrawPartIndex(part_num=part_num, description=description, indexed_at=now))
        count += 1
        if count % 500 == 0:
            db.flush()

    db.commit()
    logger.info(f"Indexed {count} LDraw parts")
    return count


def search_ldraw_part_index(db, query: str, limit: int = 20) -> List[Dict]:
    """Search the ldraw_part_index table by part_num or description.

    Returns a list of dicts with 'part_num' and 'description'.
    """
    from backend.database import LDrawPartIndex
    from sqlalchemy import or_

    q = query.strip().lower()
    if not q:
        return []

    rows = (
        db.query(LDrawPartIndex)
        .filter(
            or_(
                LDrawPartIndex.part_num.ilike(f"%{q}%"),
                LDrawPartIndex.description.ilike(f"%{q}%"),
            )
        )
        .limit(limit)
        .all()
    )
    return [{"part_num": r.part_num, "description": r.description} for r in rows]


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
