"""Pydantic schemas for API request/response models."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, model_validator


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
    cached_at: Optional[str] = None  # ISO timestamp when set was cached (if from cache)


class PartInfo(BaseModel):
    """Individual part information."""
    part_num: str
    name: str
    quantity: int
    color: Optional[str] = None


class GenerateRequest(BaseModel):
    """Request to generate output; at least one of generate_3mf or generate_stl must be True."""
    set_num: str
    plate_width: int = Field(default=220, ge=100, le=2000)
    plate_depth: int = Field(default=220, ge=100, le=2000)
    bypass_cache: bool = Field(default=False)
    generate_3mf: bool = Field(default=True)
    generate_stl: bool = Field(default=True)
    project_id: Optional[str] = None

    @model_validator(mode="after")
    def at_least_one_output(self):
        if not self.generate_3mf and not self.generate_stl:
            raise ValueError("At least one of generate_3mf or generate_stl must be True")
        return self


class JobStatus(BaseModel):
    """Job status response."""
    job_id: str
    set_num: str
    status: str  # pending, processing, completed, failed
    progress: int
    error_message: Optional[str] = None
    output_file: Optional[str] = None
    brickgen_version: Optional[str] = None
    log: Optional[str] = None  # job run log (warnings, skipped parts)
    created_at: datetime
    updated_at: datetime


class SettingsResponse(BaseModel):
    """Application settings."""
    default_plate_width: int
    default_plate_depth: int
    default_plate_height: int
    part_spacing: int
    stl_scale_factor: float
    rotation_enabled: bool
    rotation_x: float
    rotation_y: float
    rotation_z: float
    default_orientation_match_preview: bool = True
    auto_generate_part_previews: bool = True


class SettingsUpdate(BaseModel):
    """Update application settings."""
    default_plate_width: Optional[int] = Field(None, ge=100, le=2000)
    default_plate_depth: Optional[int] = Field(None, ge=100, le=2000)
    default_plate_height: Optional[int] = Field(None, ge=100, le=2000)
    part_spacing: Optional[int] = Field(None, ge=1, le=10)
    stl_scale_factor: Optional[float] = Field(None, ge=0.01, le=100.0)
    rotation_enabled: Optional[bool] = None
    rotation_x: Optional[float] = None
    rotation_y: Optional[float] = None
    rotation_z: Optional[float] = None
    default_orientation_match_preview: Optional[bool] = None
    auto_generate_part_previews: Optional[bool] = None


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
    version: Optional[str] = None
