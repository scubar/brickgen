"""LDraw part search and index management API routes."""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.database import get_db, LDrawPartIndex
from backend.auth import get_current_user
from backend.api.integrations.ldraw import build_ldraw_part_index, search_ldraw_part_index

logger = logging.getLogger(__name__)
router = APIRouter()


class LDrawPartResult(BaseModel):
    part_num: str
    description: Optional[str] = None


class LDrawIndexStatus(BaseModel):
    indexed_count: int
    message: str


@router.get("/ldraw-parts/search", response_model=List[LDrawPartResult])
async def search_ldraw_parts(
    q: str = Query(..., min_length=1, description="Search term (part number or description)"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Search the local LDraw part index by part number or description.

    If the index is empty the search returns an empty list; call POST
    /api/ldraw-parts/index to populate it first.
    """
    results = search_ldraw_part_index(db, q, limit=limit)
    return [LDrawPartResult(**r) for r in results]


@router.post("/ldraw-parts/index", response_model=LDrawIndexStatus)
async def rebuild_ldraw_index(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """(Re-)build the LDraw part index by scanning the local parts directory.

    Safe to call repeatedly; clears the existing index before re-indexing.
    """
    # Clear existing index
    db.query(LDrawPartIndex).delete()
    db.commit()
    count = build_ldraw_part_index(db)
    return LDrawIndexStatus(indexed_count=count, message=f"Indexed {count} parts from local LDraw library")


@router.get("/ldraw-parts/index/status", response_model=LDrawIndexStatus)
async def get_ldraw_index_status(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Return the current number of indexed LDraw parts."""
    count = db.query(LDrawPartIndex).count()
    return LDrawIndexStatus(indexed_count=count, message=f"{count} parts in index")
