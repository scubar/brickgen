"""Pydantic schemas for API request/response models."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, model_validator, field_validator


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


class GenerateRequest(BaseModel):
    """Request to generate output; at least one of generate_3mf or generate_stl must be True."""
    set_num: str
    plate_width: int = Field(default=220, ge=100, le=2000)
    plate_depth: int = Field(default=220, ge=100, le=2000)
    plate_height: int = Field(default=250, ge=100, le=2000)
    bypass_cache: bool = Field(default=False)
    generate_3mf: bool = Field(default=True)
    generate_stl: bool = Field(default=True)
    project_id: Optional[str] = None
    scale_factor: Optional[float] = Field(None, ge=0.01, le=10.0)  # user scale (1.0 = normal); backend multiplies by 10

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


class JobProgress(BaseModel):
    """In-memory progress for a running job (no DB). Returned by GET /jobs/{id}/progress."""
    status: str
    progress: int
    error_message: Optional[str] = None
    log: Optional[str] = None  # latest log line only


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
    # LDView quality
    ldview_allow_primitive_substitution: bool = True
    ldview_use_quality_studs: bool = True
    ldview_curve_quality: int = 2
    ldview_seams: bool = False
    ldview_seam_width: int = 0
    ldview_bfc: bool = True
    ldview_bounding_boxes_only: bool = False
    ldview_show_highlight_lines: bool = False
    ldview_polygon_offset: bool = True
    ldview_edge_thickness: float = 0.0
    ldview_line_smoothing: bool = False
    ldview_black_highlights: bool = False
    ldview_conditional_highlights: bool = False
    ldview_wireframe: bool = False
    ldview_wireframe_thickness: float = 0.0
    ldview_remove_hidden_lines: bool = False
    ldview_texture_studs: bool = True
    ldview_texmaps: bool = True
    ldview_hi_res_primitives: bool = False
    ldview_texture_filter_type: int = 9987
    ldview_aniso_level: int = 0
    ldview_texture_offset_factor: float = 5.0
    ldview_lighting: bool = True
    ldview_use_quality_lighting: bool = False
    ldview_use_specular: bool = True
    ldview_subdued_lighting: bool = False
    ldview_perform_smoothing: bool = True
    ldview_use_flat_shading: bool = False
    ldview_antialias: int = 0
    ldview_process_ldconfig: bool = True
    ldview_sort_transparent: bool = True
    ldview_use_stipple: bool = False
    ldview_memory_usage: int = 2

    @field_validator("stl_scale_factor", mode="before")
    @classmethod
    def coerce_scale_float(cls, v):
        """Ensure scale is always float (e.g. 1.0 not 1)."""
        return float(v) if v is not None else 1.0

    @field_validator("rotation_x", "rotation_y", "rotation_z", mode="before")
    @classmethod
    def coerce_rotation_float(cls, v):
        """Ensure rotation values are always float."""
        return float(v) if v is not None else 0.0


class SettingsUpdate(BaseModel):
    """Update application settings."""
    default_plate_width: Optional[int] = Field(None, ge=100, le=2000)
    default_plate_depth: Optional[int] = Field(None, ge=100, le=2000)
    default_plate_height: Optional[int] = Field(None, ge=100, le=2000)
    part_spacing: Optional[int] = Field(None, ge=1, le=10)
    stl_scale_factor: Optional[float] = Field(None, ge=0.01, le=10.0)  # user scale (1.0 = normal)
    rotation_enabled: Optional[bool] = None
    rotation_x: Optional[float] = None
    rotation_y: Optional[float] = None
    rotation_z: Optional[float] = None
    default_orientation_match_preview: Optional[bool] = None
    auto_generate_part_previews: Optional[bool] = None
    # LDView quality (optional; validated in route for ranges)
    ldview_allow_primitive_substitution: Optional[bool] = None
    ldview_use_quality_studs: Optional[bool] = None
    ldview_curve_quality: Optional[int] = None
    ldview_seams: Optional[bool] = None
    ldview_seam_width: Optional[int] = None
    ldview_bfc: Optional[bool] = None
    ldview_bounding_boxes_only: Optional[bool] = None
    ldview_show_highlight_lines: Optional[bool] = None
    ldview_polygon_offset: Optional[bool] = None
    ldview_edge_thickness: Optional[float] = None
    ldview_line_smoothing: Optional[bool] = None
    ldview_black_highlights: Optional[bool] = None
    ldview_conditional_highlights: Optional[bool] = None
    ldview_wireframe: Optional[bool] = None
    ldview_wireframe_thickness: Optional[float] = None
    ldview_remove_hidden_lines: Optional[bool] = None
    ldview_texture_studs: Optional[bool] = None
    ldview_texmaps: Optional[bool] = None
    ldview_hi_res_primitives: Optional[bool] = None
    ldview_texture_filter_type: Optional[int] = None
    ldview_aniso_level: Optional[int] = None
    ldview_texture_offset_factor: Optional[float] = None
    ldview_lighting: Optional[bool] = None
    ldview_use_quality_lighting: Optional[bool] = None
    ldview_use_specular: Optional[bool] = None
    ldview_subdued_lighting: Optional[bool] = None
    ldview_perform_smoothing: Optional[bool] = None
    ldview_use_flat_shading: Optional[bool] = None
    ldview_antialias: Optional[int] = None
    ldview_process_ldconfig: Optional[bool] = None
    ldview_sort_transparent: Optional[bool] = None
    ldview_use_stipple: Optional[bool] = None
    ldview_memory_usage: Optional[int] = None


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


class MigrationInfo(BaseModel):
    """Single migration revision info."""
    revision_id: str
    description: str
    applied: bool


class DatabaseInfo(BaseModel):
    """Database path, migrations, and table row counts."""
    database_path: str
    current_revision: Optional[str] = None
    migrations: List[MigrationInfo]
    table_counts: dict  # table name -> row count
