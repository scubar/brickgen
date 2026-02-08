"""Configuration management for BrickGen application."""
import os
from pathlib import Path
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
    
    # STL Scale Factor: LDView exports STL in centimeters; multiply by 10 to get mm.
    # Calibration baseline: part 3034 (Plate 2x8) = 16×64×3.2 mm, part 3404 (Brick 2x4) = 16×32×9.6 mm.
    stl_scale_factor: float = 10.0
    
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
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Ensure directories exist
settings.cache_dir.mkdir(parents=True, exist_ok=True)
settings.output_dir.mkdir(parents=True, exist_ok=True)
settings.database_path.parent.mkdir(parents=True, exist_ok=True)
