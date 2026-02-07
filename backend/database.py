"""Database models and session management."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from backend.config import settings

Base = declarative_base()


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
    set_num = Column(String)
    status = Column(String)  # pending, processing, completed, failed
    progress = Column(Integer, default=0)  # 0-100
    plate_width = Column(Integer)
    plate_depth = Column(Integer)
    error_message = Column(Text, nullable=True)
    output_file = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


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
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
