"""Rebrickable API client for fetching LEGO parts inventory."""
import logging
import os
from typing import List, Dict, Optional, TYPE_CHECKING
import aiohttp
from backend.config import settings

if TYPE_CHECKING:
    from backend.core.api_cache import ApiCacheBackend

logger = logging.getLogger(__name__)

# Cache key prefixes for Rebrickable responses
CACHE_KEY_SET = "rebrickable:set:"
CACHE_KEY_SET_INDEX = "rebrickable:set_index"
CACHE_KEY_SET_PARTS = "rebrickable:set_parts:"
CACHE_KEY_PART_INFO = "rebrickable:part_info:"


def _resolve_api_key(override: Optional[str] = None) -> str:
    """Resolve API key: explicit override > settings (from .env/config) > REBRICKABLE_API_KEY env."""
    if override and override.strip():
        return override.strip()
    key = (settings.rebrickable_api_key or "").strip()
    if key:
        return key
    return (os.environ.get("REBRICKABLE_API_KEY") or "").strip()


class RebrickableClient:
    """Client for Rebrickable API v3. Optional cache reduces API calls and rate-limit risk."""
    
    BASE_URL = "https://rebrickable.com/api/v3/lego"
    
    def __init__(self, api_key: Optional[str] = None, cache: Optional["ApiCacheBackend"] = None):
        self.api_key = _resolve_api_key(api_key)
        self.cache = cache
    
    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make request to Rebrickable API."""
        url = f"{self.BASE_URL}/{endpoint}"
        headers = {
            "Authorization": f"key {self.api_key}"
        }

        auth_preview = f"key {'(set)' if self.api_key else '(empty)'}"
        logger.info(f"Rebrickable request: {url} {params}, auth: {auth_preview}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params or {}) as response:
                response.raise_for_status()
                return await response.json()
    
    async def search_sets(self, query: str, page: int = 1, page_size: int = 20) -> Dict:
        """Search for LEGO sets by name or number.
        
        Returns:
            Dict with results (list), count, next (page or None), previous (page or None)
        """
        try:
            params = {
                "search": query,
                "page": page,
                "page_size": page_size
            }
            result = await self._make_request("sets/", params)
            sets = result.get("results", [])
            count = result.get("count", len(sets))
            next_url = result.get("next")
            previous_url = result.get("previous")
            next_page = page + 1 if next_url else None
            prev_page = page - 1 if previous_url and page > 1 else None

            return {
                "results": [{
                    "set_num": s.get("set_num", ""),
                    "name": s.get("name", ""),
                    "year": s.get("year"),
                    "theme": str(s.get("theme_id", "")),
                    "subtheme": None,
                    "pieces": s.get("num_parts"),
                    "image_url": s.get("set_img_url")
                } for s in sets],
                "count": count,
                "next": next_page,
                "previous": prev_page,
                "page": page,
                "page_size": page_size
            }
        except Exception as e:
            logger.error(f"Errors searching sets: {e}")
            raise
    
    async def get_set_parts(self, set_num: str) -> List[Dict]:
        """Get parts inventory for a specific set.
        
        Args:
            set_num: Set number (e.g., "75192-1")
        
        Returns:
            List of parts with quantity, part number, color, etc.
        """
        try:
            # Ensure set number has version suffix
            if "-" not in set_num:
                set_num = f"{set_num}-1"
            
            cache_key = f"{CACHE_KEY_SET_PARTS}{set_num}"
            if self.cache:
                cached = self.cache.get(cache_key)
                if cached is not None:
                    logger.debug("Rebrickable set_parts cache hit: %s", set_num)
                    return cached
            
            all_parts = []
            page = 1
            page_size = 1000
            
            while True:
                params = {
                    "page": page,
                    "page_size": page_size,
                    "inc_color_details": 0
                }
                
                result = await self._make_request(f"sets/{set_num}/parts", params)
                parts = result.get("results", [])
                
                for part in parts:
                    part_data = part.get("part", {})
                    color_data = part.get("color", {})
                    external_ids = part_data.get("external_ids", {})
                    ldraw_ids = external_ids.get("LDraw", [])
                    
                    all_parts.append({
                        "part_num": part_data.get("part_num", ""),
                        "name": part_data.get("name", ""),
                        "quantity": part.get("quantity", 1),
                        "color": color_data.get("name", ""),
                        "color_rgb": color_data.get("rgb", ""),
                        "ldraw_id": ldraw_ids[0] if ldraw_ids else None,  # Extract LDraw ID
                        "is_spare": part.get("is_spare", False)
                    })
                
                # Check if there are more pages
                if not result.get("next"):
                    break
                
                page += 1
            
            if self.cache:
                self.cache.set(cache_key, all_parts)
            return all_parts
            
        except Exception as e:
            logger.error(f"Error getting parts for set {set_num}: {e}")
            raise
    
    async def get_part_info(self, part_num: str) -> Optional[Dict]:
        """Get detailed information about a specific part."""
        try:
            cache_key = f"{CACHE_KEY_PART_INFO}{part_num}"
            if self.cache:
                cached = self.cache.get(cache_key)
                if cached is not None:
                    logger.debug("Rebrickable part_info cache hit: %s", part_num)
                    return cached
            
            result = await self._make_request(f"parts/{part_num}")
            info = {
                "part_num": result.get("part_num", ""),
                "name": result.get("name", ""),
                "part_cat_id": result.get("part_cat_id"),
                "part_material": result.get("part_material", "")
            }
            if self.cache:
                self.cache.set(cache_key, info)
            return info
            
        except Exception as e:
            logger.error(f"Error getting part info for {part_num}: {e}")
            return None
