"""Database models and session management."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, create_engine
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


class STLCache(Base):
    """Cache for converted STL files."""
    __tablename__ = "stl_cache"

    id = Column(Integer, primary_key=True)
    part_num = Column(String, unique=True, index=True)
    file_path = Column(String)
    file_size = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)


# Database setup
engine = create_engine(
    f"sqlite:///{settings.database_path}",
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables and run migrations."""
    Base.metadata.create_all(bind=engine)
    # Add new columns to jobs if missing (migration)
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    if "jobs" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("jobs")}
        with engine.connect() as conn:
            if "brickgen_version" not in cols:
                conn.execute(text("ALTER TABLE jobs ADD COLUMN brickgen_version VARCHAR"))
                conn.commit()
            if "settings" not in cols:
                conn.execute(text("ALTER TABLE jobs ADD COLUMN settings TEXT"))
                conn.commit()
            if "project_id" not in cols:
                conn.execute(text("ALTER TABLE jobs ADD COLUMN project_id VARCHAR"))
                conn.commit()
            if "log" not in cols:
                conn.execute(text("ALTER TABLE jobs ADD COLUMN log TEXT"))
                conn.commit()


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
