"""Database models and session management."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, Float, UniqueConstraint, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from backend.config import settings

Base = declarative_base()


class Project(Base):
    """User-created project linked to a set (can have many jobs)."""
    __tablename__ = "projects"

    id = Column(String, primary_key=True)  # UUID
    set_num = Column(String, index=True)
    name = Column(String)  # user-defined project name
    set_name = Column(String, nullable=True)  # from set data for display
    image_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CachedSet(Base):
    """Cache for LEGO set metadata from Brickset."""
    __tablename__ = "cached_sets"
    
    id = Column(Integer, primary_key=True)
    set_num = Column(String, unique=True, index=True)
    name = Column(String)
    year = Column(Integer)
    theme = Column(String)
    subtheme = Column(String)
    pieces = Column(Integer)
    image_url = Column(String)
    data = Column(Text)  # JSON blob
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CachedParts(Base):
    """Cache for parts inventory from Rebrickable."""
    __tablename__ = "cached_parts"
    
    id = Column(Integer, primary_key=True)
    set_num = Column(String, index=True)
    parts_data = Column(Text)  # JSON blob of parts list
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Job(Base):
    """Track 3MF generation jobs."""
    __tablename__ = "jobs"

    id = Column(String, primary_key=True)  # UUID
    project_id = Column(String, ForeignKey("projects.id"), nullable=True, index=True)  # optional during migration
    set_num = Column(String)
    status = Column(String)  # pending, processing, completed, failed
    progress = Column(Integer, default=0)  # 0-100
    plate_width = Column(Integer)
    plate_depth = Column(Integer)
    plate_height = Column(Integer, nullable=True)  # stored for reference; placement uses only width/depth
    error_message = Column(Text, nullable=True)
    output_file = Column(String, nullable=True)
    brickgen_version = Column(String, nullable=True)  # version when job was created/run
    settings = Column(Text, nullable=True)  # JSON: plate_width, plate_depth, scale_factor, rotation_*, etc.
    log = Column(Text, nullable=True)  # job run log (warnings, e.g. skipped parts)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SearchHistory(Base):
    """User search history for suggest."""
    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True)
    query = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AppSettings(Base):
    """Single-row table for persisted app settings (non-sensitive; env-only: API key, paths)."""
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, default=1)
    default_plate_width = Column(Integer, default=220)
    default_plate_depth = Column(Integer, default=220)
    default_plate_height = Column(Integer, default=250)
    part_spacing = Column(Integer, default=2)
    stl_scale_factor = Column(Float, default=1.0)
    rotation_enabled = Column(Boolean, default=False)
    rotation_x = Column(Float, default=0.0)
    rotation_y = Column(Float, default=0.0)
    rotation_z = Column(Float, default=0.0)
    default_orientation_match_preview = Column(Boolean, default=True)
    auto_generate_part_previews = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class STLCache(Base):
    """Cache for converted STL files. Key: (part_num, scale, rotation_enabled, rotation_x, rotation_y, rotation_z)."""
    __tablename__ = "stl_cache"
    __table_args__ = (
        UniqueConstraint(
            "part_num", "scale", "rotation_enabled",
            "rotation_x", "rotation_y", "rotation_z",
            name="uq_stl_cache_key"
        ),
    )

    id = Column(Integer, primary_key=True)
    part_num = Column(String, index=True)
    file_path = Column(String)
    file_size = Column(Integer)
    rotation_enabled = Column(Boolean, default=False)
    rotation_x = Column(Float, default=0.0)
    rotation_y = Column(Float, default=0.0)
    rotation_z = Column(Float, default=0.0)
    scale = Column(Float, default=10.0)
    created_at = Column(DateTime, default=datetime.utcnow)


# Database setup
engine = create_engine(
    f"sqlite:///{settings.database_path}",
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Run database migrations (Alembic). Tables are created/updated by migrations."""
    from pathlib import Path
    from alembic import command
    from alembic.config import Config

    # Run from project root so script_location resolves
    project_root = Path(__file__).resolve().parent.parent
    alembic_cfg = Config(str(project_root / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(project_root / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{settings.database_path}")
    command.upgrade(alembic_cfg, "head")


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
