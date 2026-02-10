"""Configuration management for BrickGen application."""
import os
from pathlib import Path
from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Keys
    rebrickable_api_key: str = ""
    
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

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()

# Ensure directories exist
settings.cache_dir.mkdir(parents=True, exist_ok=True)
settings.output_dir.mkdir(parents=True, exist_ok=True)
settings.database_path.parent.mkdir(parents=True, exist_ok=True)
