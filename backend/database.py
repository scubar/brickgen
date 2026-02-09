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

    # stl_cache: add rotation/scale columns if missing; then recreate table for composite unique
    if "stl_cache" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("stl_cache")}
        new_cols = ("rotation_enabled", "rotation_x", "rotation_y", "rotation_z", "scale")
        added_any = False
        with engine.connect() as conn:
            for col in new_cols:
                if col not in cols:
                    if col == "rotation_enabled":
                        conn.execute(text("ALTER TABLE stl_cache ADD COLUMN rotation_enabled BOOLEAN DEFAULT 0"))
                    elif col in ("rotation_x", "rotation_y", "rotation_z", "scale"):
                        default = 10.0 if col == "scale" else 0.0
                        conn.execute(text(f"ALTER TABLE stl_cache ADD COLUMN {col} FLOAT DEFAULT {default}"))
                    else:
                        conn.execute(text(f"ALTER TABLE stl_cache ADD COLUMN {col} FLOAT DEFAULT 0"))
                    conn.commit()
                    added_any = True
            if added_any:
                # Recreate table so we can have composite unique (SQLite cannot add constraint via ALTER)
                conn.execute(text("""
                    CREATE TABLE stl_cache_new (
                        id INTEGER NOT NULL PRIMARY KEY,
                        part_num VARCHAR,
                        file_path VARCHAR,
                        file_size INTEGER,
                        rotation_enabled BOOLEAN DEFAULT 0,
                        rotation_x FLOAT DEFAULT 0,
                        rotation_y FLOAT DEFAULT 0,
                        rotation_z FLOAT DEFAULT 0,
                        scale FLOAT DEFAULT 10,
                        created_at DATETIME,
                        UNIQUE(part_num, scale, rotation_enabled, rotation_x, rotation_y, rotation_z)
                    )
                """))
                conn.execute(text("""
                    INSERT INTO stl_cache_new (id, part_num, file_path, file_size, rotation_enabled, rotation_x, rotation_y, rotation_z, scale, created_at)
                    SELECT id, part_num, file_path, file_size,
                           COALESCE(rotation_enabled, 0), COALESCE(rotation_x, 0), COALESCE(rotation_y, 0), COALESCE(rotation_z, 0), COALESCE(scale, 10), created_at
                    FROM stl_cache
                """))
                conn.execute(text("DROP TABLE stl_cache"))
                conn.execute(text("ALTER TABLE stl_cache_new RENAME TO stl_cache"))
                conn.commit()


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
