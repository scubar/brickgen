"""Configuration management for BrickGen application."""
from pathlib import Path
from pydantic import ConfigDict, Field, field_validator
from pydantic_settings import BaseSettings

VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

# Resolve .env path relative to project root (parent of backend/) so the API key
# is loaded consistently regardless of current working directory (e.g. running
# from project root vs backend/ or via Docker WORKDIR).
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Keys (loaded from REBRICKABLE_API_KEY in .env or environment)
    rebrickable_api_key: str = Field(default="", validation_alias="REBRICKABLE_API_KEY")
    
    # Logging (LOG_LEVEL: DEBUG, INFO, WARNING, ERROR, CRITICAL)
    log_level: str = "INFO"

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, v: str) -> str:
        if not v or not isinstance(v, str):
            return "INFO"
        level = v.strip().upper()
        return level if level in VALID_LOG_LEVELS else "INFO"
    
    # Build Plate Defaults
    default_plate_width: int = 220
    default_plate_depth: int = 220
    default_plate_height: int = 250
    part_spacing: int = 2
    
    # STL Scale Factor (user-facing): 1.0 = normal (10 mm per LDraw unit). Backend multiplies by 10 for LDView.
    # LDView exports in cm; backend uses stl_scale_factor * 10 so 1.0 → 10 (mm). Calibration: 3034, 3404.
    stl_scale_factor: float = 1.0

    @property
    def stl_scale_factor_backend(self) -> float:
        """Scale value for LDView/STL (user value * 10)."""
        return self.stl_scale_factor * 10.0
    
    # STL Rotation: absolute degrees (X, Y, Z) when enabled
    rotation_enabled: bool = False
    rotation_x: float = 0.0
    rotation_y: float = 0.0
    rotation_z: float = 0.0
    # When True, apply X=-90° to STLs when rotation is off so orientation matches LDView preview (studs up)
    default_orientation_match_preview: bool = True

    # Part previews: when True, frontend may request preview images (lazy) for parts
    auto_generate_part_previews: bool = True

    # LDView quality settings (CLI -SettingName=value). Affect STL export and/or part preview PNG.
    # Geometry / model
    ldview_allow_primitive_substitution: bool = True
    ldview_use_quality_studs: bool = True  # 0=low (faster), 1=high
    ldview_curve_quality: int = 2  # 1-12
    ldview_seams: bool = False
    ldview_seam_width: int = 0  # 0-500 (100× UI 0.00-5.00)
    ldview_bfc: bool = True
    ldview_bounding_boxes_only: bool = False
    # Edge lines / wireframe (mainly preview)
    ldview_show_highlight_lines: bool = False
    ldview_polygon_offset: bool = True
    ldview_edge_thickness: float = 0.0  # 0-5 (0=1px)
    ldview_line_smoothing: bool = False
    ldview_black_highlights: bool = False
    ldview_conditional_highlights: bool = False
    ldview_wireframe: bool = False
    ldview_wireframe_thickness: float = 0.0  # 0-5
    ldview_remove_hidden_lines: bool = False
    # Primitives / textures
    ldview_texture_studs: bool = True
    ldview_texmaps: bool = True
    ldview_hi_res_primitives: bool = False
    ldview_texture_filter_type: int = 9987  # 9984=Nearest, 9985=Bilinear, 9987=Trilinear
    ldview_aniso_level: int = 0
    ldview_texture_offset_factor: float = 5.0  # 1-10
    # Effects
    ldview_lighting: bool = True
    ldview_use_quality_lighting: bool = False
    ldview_use_specular: bool = True
    ldview_subdued_lighting: bool = False
    ldview_perform_smoothing: bool = True
    ldview_use_flat_shading: bool = False
    ldview_antialias: int = 0  # 0=none, 2=2x, 4=4x, 5=4x Enhanced
    ldview_process_ldconfig: bool = True
    ldview_sort_transparent: bool = True
    ldview_use_stipple: bool = False
    # Memory (0=Low, 1=Medium, 2=High)
    ldview_memory_usage: int = 2

    # Paths
    ldraw_library_path: Path = Path("/app/data/ldraw")
    cache_dir: Path = Path("/app/cache")
    database_path: Path = Path("/app/database/brickgen.db")
    output_dir: Path = Path("/app/cache/outputs")
    
    # API Settings
    api_prefix: str = "/api"
    cors_origins: list = ["*"]
    
    # Job Settings
    max_job_age_hours: int = 24

    model_config = ConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

# Ensure directories exist
settings.cache_dir.mkdir(parents=True, exist_ok=True)
settings.output_dir.mkdir(parents=True, exist_ok=True)
settings.database_path.parent.mkdir(parents=True, exist_ok=True)
