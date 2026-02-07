"""Rebrickable API client for fetching LEGO parts inventory."""
import logging
from typing import List, Dict, Optional
import aiohttp
from backend.config import settings

logger = logging.getLogger(__name__)


class RebrickableClient:
    """Client for Rebrickable API v3."""
    
    BASE_URL = "https://rebrickable.com/api/v3/lego"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.rebrickable_api_key
    
    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make request to Rebrickable API."""
        url = f"{self.BASE_URL}/{endpoint}"
        headers = {
            "Authorization": f"key {self.api_key}"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params or {}) as response:
                response.raise_for_status()
                return await response.json()
    
    async def search_sets(self, query: str, page: int = 1, page_size: int = 20) -> List[Dict]:
        """Search for LEGO sets by name or number.
        
        Args:
            query: Search term (set name or number)
            page: Page number (1-indexed)
            page_size: Results per page
        
        Returns:
            List of sets matching the query
        """
        try:
            params = {
                "search": query,
                "page": page,
                "page_size": page_size
            }
            
            result = await self._make_request("sets/", params)
            sets = result.get("results", [])
            
            return [{
                "set_num": s.get("set_num", ""),
                "name": s.get("name", ""),
                "year": s.get("year"),
                "theme": str(s.get("theme_id", "")),  # Theme ID as string for compatibility
                "subtheme": None,  # Rebrickable doesn't have subtheme in search
                "pieces": s.get("num_parts"),
                "image_url": s.get("set_img_url")
            } for s in sets]
            
        except Exception as e:
            logger.error(f"Error searching sets: {e}")
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
            
            all_parts = []
            page = 1
            page_size = 1000
            
            while True:
                params = {
                    "page": page,
                    "page_size": page_size
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
            
            return all_parts
            
        except Exception as e:
            logger.error(f"Error getting parts for set {set_num}: {e}")
            raise
    
    async def get_part_info(self, part_num: str) -> Optional[Dict]:
        """Get detailed information about a specific part."""
        try:
            result = await self._make_request(f"parts/{part_num}")
            
            return {
                "part_num": result.get("part_num", ""),
                "name": result.get("name", ""),
                "part_cat_id": result.get("part_cat_id"),
                "part_material": result.get("part_material", "")
            }
            
        except Exception as e:
            logger.error(f"Error getting part info for {part_num}: {e}")
            return None
