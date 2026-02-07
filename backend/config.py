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
    
    # STL Scale Factor (multiplier for LDraw coordinates)
    stl_scale_factor: float = 16.67
    
    # STL Orientation Settings
    auto_orient_enabled: bool = True
    orientation_strategy: str = "studs_up"  # "studs_up", "flat", "minimize_supports", "original"
    
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
