"""Search routes for LEGO sets."""
import logging
from typing import List, Dict
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from backend.models.schemas import SetSearchResult, SetDetail
from backend.api.integrations.rebrickable import RebrickableClient
from backend.database import get_db, CachedSet, CachedParts
from datetime import datetime
import json

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/search", response_model=List[SetSearchResult])
async def search_sets(
    query: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Search for LEGO sets by name or number."""
    try:
        client = RebrickableClient()
        results = await client.search_sets(query, page, page_size)
        
        # Cache results
        for result in results:
            existing = db.query(CachedSet).filter(
                CachedSet.set_num == result['set_num']
            ).first()
            
            if existing:
                existing.data = json.dumps(result)
                existing.name = result.get('name', '')
                existing.year = result.get('year')
                existing.theme = result.get('theme')
                existing.subtheme = result.get('subtheme')
                existing.pieces = result.get('pieces')
                existing.image_url = result.get('image_url')
            else:
                cached = CachedSet(
                    set_num=result['set_num'],
                    name=result.get('name', ''),
                    year=result.get('year'),
                    theme=result.get('theme'),
                    subtheme=result.get('subtheme'),
                    pieces=result.get('pieces'),
                    image_url=result.get('image_url'),
                    data=json.dumps(result)
                )
                db.add(cached)
        
        db.commit()
        
        return [SetSearchResult(**r) for r in results]
        
    except Exception as e:
        logger.error(f"Error searching sets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sets/{set_num}", response_model=SetDetail)
async def get_set_detail(
    set_num: str,
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific set."""
    try:
        # Check cache first
        cached = db.query(CachedSet).filter(CachedSet.set_num == set_num).first()
        
        if cached:
            data = json.loads(cached.data)
            # Get parts count from Rebrickable if available
            rebrickable = RebrickableClient()
            try:
                parts = await rebrickable.get_set_parts(set_num)
                parts_count = len(parts)
            except:
                parts_count = cached.pieces
            
            return SetDetail(**data, parts_count=parts_count)
        
        # Fetch from Rebrickable
        rebrickable_client = RebrickableClient()
        
        # Try to get set details from search endpoint
        search_results = await rebrickable_client.search_sets(set_num, page_size=1)
        
        if not search_results:
            raise HTTPException(status_code=404, detail="Set not found")
        
        result = search_results[0]
        
        # Get parts count from Rebrickable (use same client)
        try:
            parts = await rebrickable_client.get_set_parts(set_num)
            parts_count = len(parts)
        except:
            parts_count = result.get('pieces')
        
        # Cache the result
        cached = CachedSet(
            set_num=result['set_num'],
            name=result.get('name', ''),
            year=result.get('year'),
            theme=result.get('theme'),
            subtheme=result.get('subtheme'),
            pieces=result.get('pieces'),
            image_url=result.get('image_url'),
            data=json.dumps(result)
        )
        db.add(cached)
        db.commit()
        
        return SetDetail(**result, parts_count=parts_count)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting set detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sets/{set_num}/parts")
async def get_set_parts(set_num: str, db: Session = Depends(get_db)) -> List[Dict]:
    """Get parts list for a specific set.
    
    Args:
        set_num: Set number (e.g., "3219-1")
        db: Database session
    
    Returns:
        List of parts with details including color information
    """
    try:
        # Ensure set number has version suffix
        if "-" not in set_num:
            set_num = f"{set_num}-1"
        
        # Check cache first
        cached_parts = db.query(CachedParts).filter(
            CachedParts.set_num == set_num
        ).first()
        
        if cached_parts:
            logger.info(f"Using cached parts for set {set_num}")
            return json.loads(cached_parts.parts_data)
        
        # Fetch from Rebrickable
        logger.info(f"Fetching parts for set {set_num} from Rebrickable")
        client = RebrickableClient()
        parts = await client.get_set_parts(set_num)
        
        # Filter out spare parts
        parts = [p for p in parts if not p.get('is_spare', False)]
        
        # Cache the result
        cached_entry = CachedParts(
            set_num=set_num,
            parts_data=json.dumps(parts),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(cached_entry)
        db.commit()
        
        logger.info(f"Cached {len(parts)} parts for set {set_num}")
        return parts
        
    except Exception as e:
        logger.error(f"Error getting parts for set {set_num}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
