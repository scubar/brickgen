"""Search routes for LEGO sets."""
import logging
from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.models.schemas import SetSearchResult, SetDetail
from backend.api.integrations.rebrickable import RebrickableClient, CACHE_KEY_SET, CACHE_KEY_SET_INDEX
from backend.database import get_db, SearchHistory
from backend.core.api_cache import DbApiCache
from backend.auth import get_current_user
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


def _query_looks_like_set_number(q: str) -> bool:
    """True if q is non-empty, starts with a digit, and contains only digits and dashes."""
    q = q.strip()
    return bool(q) and q[0].isdigit() and all(c.isdigit() or c == "-" for c in q)


def _update_set_index(cache: DbApiCache, set_num: str, name: str) -> None:
    """Add or update set_num/name in the set index used for suggest."""
    index = cache.get(CACHE_KEY_SET_INDEX) or []
    index = [x for x in index if x.get("set_num") != set_num]
    index.append({"set_num": set_num, "name": name or ""})
    cache.set(CACHE_KEY_SET_INDEX, index)


def _remove_set_from_index(cache: DbApiCache, set_num: str) -> None:
    """Remove set_num from the set index."""
    index = cache.get(CACHE_KEY_SET_INDEX) or []
    index = [x for x in index if x.get("set_num") != set_num]
    cache.set(CACHE_KEY_SET_INDEX, index)


@router.get("/search", response_model=SearchResponse)
async def search_sets(
    query: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Search for LEGO sets by name or number. Returns paginated results."""
    try:
        q = query.strip()
        cache = DbApiCache(db)
        # When query looks like a set number, try cache first to avoid API call
        if _query_looks_like_set_number(q):
            prefix = f"{CACHE_KEY_SET}{q}"
            total = DbApiCache.count_by_prefix(db, prefix)
            if total >= 1:
                keys = DbApiCache.list_keys(db, prefix, limit=page_size, offset=(page - 1) * page_size)
                results = []
                for key in keys:
                    val = cache.get(key)
                    if val:
                        results.append(SetSearchResult(
                            set_num=val.get("set_num", ""),
                            name=val.get("name", ""),
                            year=val.get("year"),
                            theme=val.get("theme"),
                            subtheme=val.get("subtheme"),
                            pieces=val.get("pieces"),
                            image_url=val.get("image_url"),
                        ))
                next_page = page + 1 if page * page_size < total else None
                previous_page = page - 1 if page > 1 else None
                hist = SearchHistory(query=q.lower())
                db.add(hist)
                db.commit()
                return SearchResponse(
                    results=results,
                    count=total,
                    page=page,
                    page_size=page_size,
                    next=next_page,
                    previous=previous_page,
                )

        client = RebrickableClient()
        data = await client.search_sets(query, page, page_size)
        results = data["results"]

        for result in results:
            set_num = result["set_num"]
            cache.set(f"{CACHE_KEY_SET}{set_num}", result)
            _update_set_index(cache, set_num, result.get("name", ""))

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
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Predictive search from cache and search history only (no Rebrickable call)."""
    if not q or not q.strip():
        return []
    q = q.strip().lower()
    out = []
    seen = set()
    cache = DbApiCache(db)

    # From set index: name or set_num contains q
    index = cache.get(CACHE_KEY_SET_INDEX) or []
    for entry in index:
        set_num = entry.get("set_num", "")
        name = (entry.get("name") or "").lower()
        if q in name or q in set_num.lower():
            key = (set_num, entry.get("name") or "")
            if key not in seen:
                seen.add(key)
                out.append(SuggestItem(set_num=set_num, name=entry.get("name") or ""))

    # From search history: queries that start with or contain q
    hist = db.query(SearchHistory.query).filter(
        SearchHistory.query.ilike(f"%{q}%")
    ).distinct().limit(limit).all()
    for (h,) in hist:
        if h and (h, h) not in seen and len(out) < limit:
            # Only add if we have a cached set matching this query
            for entry in index:
                set_num = entry.get("set_num", "")
                name = (entry.get("name") or "").lower()
                if h in name or h in set_num.lower():
                    key = (set_num, entry.get("name") or "")
                    if key not in seen:
                        seen.add(key)
                        out.append(SuggestItem(set_num=set_num, name=entry.get("name") or ""))
                    break

    return out[:limit]


@router.get("/search/history", response_model=List[str])
async def get_search_history(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
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
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Remove one search history entry (by exact query)."""
    db.query(SearchHistory).filter(SearchHistory.query == query).delete()
    db.commit()
    return {"message": f"Removed '{query}' from history"}


@router.delete("/search/history/clear")
async def clear_all_search_history(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Clear all search history entries."""
    count = db.query(SearchHistory).count()
    db.query(SearchHistory).delete()
    db.commit()
    return {"message": f"Cleared {count} search history entry(ies)", "deleted_count": count}


@router.get("/sets/{set_num}", response_model=SetDetail)
async def get_set_detail(
    set_num: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Get detailed information about a specific set."""
    try:
        cache = DbApiCache(db)
        # Normalize set_num for cache key (version suffix)
        lookup_num = set_num if "-" in set_num else f"{set_num}-1"
        cached = cache.get(f"{CACHE_KEY_SET}{set_num}") or cache.get(f"{CACHE_KEY_SET}{lookup_num}")

        if cached:
            # Parts count: use cache-backed client so we don't hit API if parts were already fetched
            rebrickable = RebrickableClient(cache=cache)
            try:
                parts = await rebrickable.get_set_parts(set_num)
                parts_count = len(parts)
            except Exception:
                parts_count = cached.get("pieces")
            cached_at = cached.get("cached_at")
            return SetDetail(
                set_num=cached.get("set_num", ""),
                name=cached.get("name", ""),
                year=cached.get("year"),
                theme=cached.get("theme"),
                subtheme=cached.get("subtheme"),
                pieces=cached.get("pieces"),
                image_url=cached.get("image_url"),
                parts_count=parts_count,
                cached_at=cached_at,
            )

        # Fetch from Rebrickable (with cache to avoid repeat calls)
        rebrickable_client = RebrickableClient(cache=cache)
        data = await rebrickable_client.search_sets(set_num, page=1, page_size=1)
        search_results = data.get("results", [])
        if not search_results:
            raise HTTPException(status_code=404, detail="Set not found")
        result = search_results[0]

        try:
            parts = await rebrickable_client.get_set_parts(set_num)
            parts_count = len(parts)
        except Exception:
            parts_count = result.get("pieces")

        # Cache the result (include cached_at for response)
        result["cached_at"] = datetime.utcnow().isoformat()
        cache.set(f"{CACHE_KEY_SET}{result['set_num']}", result)
        _update_set_index(cache, result["set_num"], result.get("name", ""))

        return SetDetail(**{k: v for k, v in result.items() if k != "cached_at"}, parts_count=parts_count, cached_at=result["cached_at"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting set detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sets/{set_num}/parts")
async def get_set_parts(
    set_num: str, 
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
) -> List[Dict]:
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
        
        cache = DbApiCache(db)
        client = RebrickableClient(cache=cache)
        parts = await client.get_set_parts(set_num)
        parts = [p for p in parts if not p.get("is_spare", False)]
        return parts
        
    except Exception as e:
        logger.error(f"Error getting parts for set {set_num}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
