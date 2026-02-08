"""Search routes for LEGO sets."""
import logging
from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.models.schemas import SetSearchResult, SetDetail
from backend.api.integrations.rebrickable import RebrickableClient
from backend.database import get_db, CachedSet, CachedParts, SearchHistory
from datetime import datetime
import json

logger = logging.getLogger(__name__)
router = APIRouter()


class SearchResponse(BaseModel):
    results: List[SetSearchResult]
    count: int
    page: int
    page_size: int
    next: Optional[int] = None
    previous: Optional[int] = None


class SuggestItem(BaseModel):
    set_num: str
    name: str


@router.get("/search", response_model=SearchResponse)
async def search_sets(
    query: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Search for LEGO sets by name or number. Returns paginated results."""
    try:
        client = RebrickableClient()
        data = await client.search_sets(query, page, page_size)
        results = data["results"]

        for result in results:
            existing = db.query(CachedSet).filter(CachedSet.set_num == result["set_num"]).first()
            if existing:
                existing.data = json.dumps(result)
                existing.name = result.get("name", "")
                existing.year = result.get("year")
                existing.theme = result.get("theme")
                existing.subtheme = result.get("subtheme")
                existing.pieces = result.get("pieces")
                existing.image_url = result.get("image_url")
            else:
                cached = CachedSet(
                    set_num=result["set_num"],
                    name=result.get("name", ""),
                    year=result.get("year"),
                    theme=result.get("theme"),
                    subtheme=result.get("subtheme"),
                    pieces=result.get("pieces"),
                    image_url=result.get("image_url"),
                    data=json.dumps(result)
                )
                db.add(cached)

        # Record search history
        hist = SearchHistory(query=query.strip().lower())
        db.add(hist)
        db.commit()

        return SearchResponse(
            results=[SetSearchResult(**r) for r in results],
            count=data.get("count", len(results)),
            page=data.get("page", page),
            page_size=data.get("page_size", page_size),
            next=data.get("next"),
            previous=data.get("previous")
        )
    except Exception as e:
        logger.error(f"Error searching sets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/suggest", response_model=List[SuggestItem])
async def search_suggest(
    q: str = Query("", min_length=0),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Predictive search from cache and search history only (no Rebrickable call)."""
    if not q or not q.strip():
        return []
    q = q.strip().lower()
    out = []
    seen = set()

    # From CachedSet: name or set_num contains q
    cached = db.query(CachedSet).filter(
        (CachedSet.name.ilike(f"%{q}%")) | (CachedSet.set_num.ilike(f"%{q}%"))
    ).limit(limit).all()
    for r in cached:
        key = (r.set_num, r.name or "")
        if key not in seen:
            seen.add(key)
            out.append(SuggestItem(set_num=r.set_num, name=r.name or ""))

    # From search history: queries that start with or contain q
    hist = db.query(SearchHistory.query).filter(
        SearchHistory.query.ilike(f"%{q}%")
    ).distinct().limit(limit).all()
    for (h,) in hist:
        if h and (h, h) not in seen and len(out) < limit:
            # May not have set_num; only add if we have a CachedSet match for this query
            c = db.query(CachedSet).filter(
                (CachedSet.name.ilike(f"%{h}%")) | (CachedSet.set_num.ilike(f"%{h}%"))
            ).first()
            if c and ((c.set_num, c.name or "") not in seen):
                seen.add((c.set_num, c.name or ""))
                out.append(SuggestItem(set_num=c.set_num, name=c.name or ""))

    return out[:limit]


@router.get("/search/history", response_model=List[str])
async def get_search_history(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Return recent search queries (newest first)."""
    rows = db.query(SearchHistory.query).order_by(
        SearchHistory.created_at.desc()
    ).distinct().limit(limit * 2).all()
    seen = set()
    out = []
    for (q,) in rows:
        if q and q not in seen and len(out) < limit:
            seen.add(q)
            out.append(q)
    return out


@router.delete("/search/history")
async def clear_search_history_item(
    query: str = Query(..., description="Exact query to remove"),
    db: Session = Depends(get_db)
):
    """Remove one search history entry (by exact query)."""
    db.query(SearchHistory).filter(SearchHistory.query == query).delete()
    db.commit()
    return {"message": f"Removed '{query}' from history"}


@router.delete("/search/history/clear")
async def clear_all_search_history(db: Session = Depends(get_db)):
    """Clear all search history entries."""
    count = db.query(SearchHistory).count()
    db.query(SearchHistory).delete()
    db.commit()
    return {"message": f"Cleared {count} search history entry(ies)", "deleted_count": count}


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
            
            cached_at = cached.updated_at.isoformat() if cached.updated_at else None
            return SetDetail(**data, parts_count=parts_count, cached_at=cached_at)
        
        # Fetch from Rebrickable
        rebrickable_client = RebrickableClient()
        data = await rebrickable_client.search_sets(set_num, page=1, page_size=1)
        search_results = data.get("results", [])
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
