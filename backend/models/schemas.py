"""Pydantic schemas for API request/response models."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class SetSearchResult(BaseModel):
    """LEGO set search result."""
    set_num: str
    name: str
    year: Optional[int] = None
    theme: Optional[str] = None
    subtheme: Optional[str] = None
    pieces: Optional[int] = None
    image_url: Optional[str] = None


class SetDetail(SetSearchResult):
    """Detailed LEGO set information."""
    parts_count: Optional[int] = None


class PartInfo(BaseModel):
    """Individual part information."""
    part_num: str
    name: str
    quantity: int
    color: Optional[str] = None


class GenerateRequest(BaseModel):
    """Request to generate ZIP file."""
    set_num: str
    plate_width: int = Field(default=220, ge=100, le=2000)
    plate_depth: int = Field(default=220, ge=100, le=2000)
    bypass_cache: bool = Field(default=False)
    generate_3mf: bool = Field(default=True)


class JobStatus(BaseModel):
    """Job status response."""
    job_id: str
    set_num: str
    status: str  # pending, processing, completed, failed
    progress: int
    error_message: Optional[str] = None
    output_file: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class SettingsResponse(BaseModel):
    """Application settings."""
    default_plate_width: int
    default_plate_depth: int
    default_plate_height: int
    part_spacing: int
    stl_scale_factor: float
    auto_orient_enabled: bool
    orientation_strategy: str


class SettingsUpdate(BaseModel):
    """Update application settings."""
    default_plate_width: Optional[int] = Field(None, ge=100, le=2000)
    default_plate_depth: Optional[int] = Field(None, ge=100, le=2000)
    default_plate_height: Optional[int] = Field(None, ge=100, le=2000)
    part_spacing: Optional[int] = Field(None, ge=1, le=10)
    stl_scale_factor: Optional[float] = Field(None, ge=1.0, le=100.0)
    auto_orient_enabled: Optional[bool] = None
    orientation_strategy: Optional[str] = None


class CacheStats(BaseModel):
    """Cache statistics."""
    stl_count: int
    total_size_mb: float
    cache_dir: str


class LDrawCacheStats(BaseModel):
    """LDraw library cache statistics."""
    exists: bool
    part_count: int
    total_size_mb: float
    library_path: str
