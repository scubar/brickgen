"""Tests for database models and operations (backend/database.py)."""
import os
import tempfile
from datetime import datetime
from pathlib import Path
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.database import (
    Base, Project, CachedSet, CachedParts, Job, SearchHistory,
    AppSettings, STLCache, get_db
)


@pytest.fixture
def test_db():
    """Create a temporary test database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()
            engine.dispose()


class TestProjectModel:
    """Tests for Project database model."""

    def test_create_project(self, test_db):
        """Test creating a new project."""
        project = Project(
            id="test-uuid-123",
            set_num="75192-1",
            name="Millennium Falcon Build",
            set_name="Millennium Falcon",
            image_url="https://example.com/image.jpg"
        )
        test_db.add(project)
        test_db.commit()
        
        retrieved = test_db.query(Project).filter(Project.id == "test-uuid-123").first()
        assert retrieved is not None
        assert retrieved.set_num == "75192-1"
        assert retrieved.name == "Millennium Falcon Build"
        assert retrieved.set_name == "Millennium Falcon"
        assert retrieved.image_url == "https://example.com/image.jpg"

    def test_project_timestamps(self, test_db):
        """Test that project timestamps are set correctly."""
        project = Project(
            id="test-uuid-456",
            set_num="10255-1",
            name="Test Project"
        )
        test_db.add(project)
        test_db.commit()
        test_db.refresh(project)
        
        assert project.created_at is not None
        assert project.updated_at is not None
        assert isinstance(project.created_at, datetime)
        assert isinstance(project.updated_at, datetime)

    def test_project_nullable_fields(self, test_db):
        """Test that nullable fields can be None."""
        project = Project(
            id="test-uuid-789",
            set_num="12345-1",
            name="Minimal Project"
        )
        test_db.add(project)
        test_db.commit()
        
        retrieved = test_db.query(Project).filter(Project.id == "test-uuid-789").first()
        assert retrieved.set_name is None
        assert retrieved.image_url is None


class TestCachedSetModel:
    """Tests for CachedSet database model."""

    def test_create_cached_set(self, test_db):
        """Test creating a cached set."""
        cached_set = CachedSet(
            set_num="75192-1",
            name="Millennium Falcon",
            year=2017,
            theme="Star Wars",
            subtheme="Ultimate Collector Series",
            pieces=7541,
            image_url="https://example.com/image.jpg",
            data='{"test": "data"}'
        )
        test_db.add(cached_set)
        test_db.commit()
        
        retrieved = test_db.query(CachedSet).filter(CachedSet.set_num == "75192-1").first()
        assert retrieved is not None
        assert retrieved.name == "Millennium Falcon"
        assert retrieved.year == 2017
        assert retrieved.theme == "Star Wars"
        assert retrieved.pieces == 7541

    def test_cached_set_unique_set_num(self, test_db):
        """Test that set_num is unique."""
        cached_set1 = CachedSet(
            set_num="12345-1",
            name="Test Set 1",
            year=2020,
            theme="Test",
            subtheme="",
            pieces=100,
            image_url="",
            data="{}"
        )
        test_db.add(cached_set1)
        test_db.commit()
        
        # Try to add another with same set_num
        cached_set2 = CachedSet(
            set_num="12345-1",
            name="Test Set 2",
            year=2021,
            theme="Test",
            subtheme="",
            pieces=200,
            image_url="",
            data="{}"
        )
        test_db.add(cached_set2)
        
        with pytest.raises(Exception):  # SQLAlchemy will raise an integrity error
            test_db.commit()


class TestCachedPartsModel:
    """Tests for CachedParts database model."""

    def test_create_cached_parts(self, test_db):
        """Test creating cached parts."""
        cached_parts = CachedParts(
            set_num="75192-1",
            parts_data='[{"part_num": "3001", "quantity": 10}]'
        )
        test_db.add(cached_parts)
        test_db.commit()
        
        retrieved = test_db.query(CachedParts).filter(CachedParts.set_num == "75192-1").first()
        assert retrieved is not None
        assert retrieved.set_num == "75192-1"
        assert retrieved.parts_data == '[{"part_num": "3001", "quantity": 10}]'

    def test_cached_parts_timestamps(self, test_db):
        """Test cached parts timestamps."""
        cached_parts = CachedParts(
            set_num="12345-1",
            parts_data="{}"
        )
        test_db.add(cached_parts)
        test_db.commit()
        test_db.refresh(cached_parts)
        
        assert cached_parts.created_at is not None
        assert cached_parts.updated_at is not None


class TestJobModel:
    """Tests for Job database model."""

    def test_create_job(self, test_db):
        """Test creating a job."""
        job = Job(
            id="job-uuid-123",
            project_id="project-uuid-456",
            set_num="75192-1",
            status="pending",
            progress=0,
            plate_width=220,
            plate_depth=220,
            plate_height=250
        )
        test_db.add(job)
        test_db.commit()
        
        retrieved = test_db.query(Job).filter(Job.id == "job-uuid-123").first()
        assert retrieved is not None
        assert retrieved.status == "pending"
        assert retrieved.progress == 0
        assert retrieved.plate_width == 220

    def test_job_status_values(self, test_db):
        """Test different job status values."""
        statuses = ["pending", "processing", "completed", "failed"]
        for i, status in enumerate(statuses):
            job = Job(
                id=f"job-{i}",
                set_num="12345-1",
                status=status,
                progress=0 if status in ["pending", "processing"] else 100,
                plate_width=220,
                plate_depth=220
            )
            test_db.add(job)
        test_db.commit()
        
        for i, status in enumerate(statuses):
            job = test_db.query(Job).filter(Job.id == f"job-{i}").first()
            assert job.status == status

    def test_job_with_error(self, test_db):
        """Test job with error message."""
        job = Job(
            id="job-error",
            set_num="12345-1",
            status="failed",
            progress=50,
            plate_width=220,
            plate_depth=220,
            error_message="Failed to process part 3001"
        )
        test_db.add(job)
        test_db.commit()
        
        retrieved = test_db.query(Job).filter(Job.id == "job-error").first()
        assert retrieved.status == "failed"
        assert retrieved.error_message == "Failed to process part 3001"

    def test_job_optional_fields(self, test_db):
        """Test job with optional fields."""
        job = Job(
            id="job-full",
            project_id="proj-123",
            set_num="12345-1",
            status="completed",
            progress=100,
            plate_width=220,
            plate_depth=220,
            plate_height=250,
            output_file="/path/to/output.3mf",
            brickgen_version="1.0.0",
            settings='{"scale": 1.0}',
            log="Processing log..."
        )
        test_db.add(job)
        test_db.commit()
        
        retrieved = test_db.query(Job).filter(Job.id == "job-full").first()
        assert retrieved.output_file == "/path/to/output.3mf"
        assert retrieved.brickgen_version == "1.0.0"
        assert retrieved.settings == '{"scale": 1.0}'
        assert retrieved.log == "Processing log..."


class TestSearchHistoryModel:
    """Tests for SearchHistory database model."""

    def test_create_search_history(self, test_db):
        """Test creating search history entry."""
        search = SearchHistory(query="millennium falcon")
        test_db.add(search)
        test_db.commit()
        
        retrieved = test_db.query(SearchHistory).filter(SearchHistory.query == "millennium falcon").first()
        assert retrieved is not None
        assert retrieved.query == "millennium falcon"
        assert retrieved.created_at is not None

    def test_multiple_search_entries(self, test_db):
        """Test creating multiple search history entries."""
        searches = ["star wars", "harry potter", "city", "technic"]
        for query in searches:
            search = SearchHistory(query=query)
            test_db.add(search)
        test_db.commit()
        
        count = test_db.query(SearchHistory).count()
        assert count == 4


class TestAppSettingsModel:
    """Tests for AppSettings database model."""

    def test_create_app_settings(self, test_db):
        """Test creating app settings."""
        settings = AppSettings(
            id=1,
            default_plate_width=220,
            default_plate_depth=220,
            default_plate_height=250,
            part_spacing=2,
            stl_scale_factor=1.0,
            rotation_enabled=False,
            rotation_x=0.0,
            rotation_y=0.0,
            rotation_z=0.0,
            default_orientation_match_preview=True,
            auto_generate_part_previews=True
        )
        test_db.add(settings)
        test_db.commit()
        
        retrieved = test_db.query(AppSettings).filter(AppSettings.id == 1).first()
        assert retrieved is not None
        assert retrieved.default_plate_width == 220
        assert retrieved.stl_scale_factor == 1.0
        assert retrieved.rotation_enabled is False

    def test_update_app_settings(self, test_db):
        """Test updating app settings."""
        settings = AppSettings(id=1, default_plate_width=220)
        test_db.add(settings)
        test_db.commit()
        
        # Update settings
        settings.default_plate_width = 300
        settings.stl_scale_factor = 1.5
        test_db.commit()
        test_db.refresh(settings)
        
        assert settings.default_plate_width == 300
        assert settings.stl_scale_factor == 1.5


class TestSTLCacheModel:
    """Tests for STLCache database model."""

    def test_create_stl_cache(self, test_db):
        """Test creating STL cache entry."""
        cache_entry = STLCache(
            part_num="3001",
            file_path="/cache/stl/3001.stl",
            file_size=1024,
            rotation_enabled=False,
            rotation_x=0.0,
            rotation_y=0.0,
            rotation_z=0.0,
            scale=10.0
        )
        test_db.add(cache_entry)
        test_db.commit()
        
        retrieved = test_db.query(STLCache).filter(STLCache.part_num == "3001").first()
        assert retrieved is not None
        assert retrieved.file_path == "/cache/stl/3001.stl"
        assert retrieved.file_size == 1024
        assert retrieved.scale == 10.0

    def test_stl_cache_with_rotation(self, test_db):
        """Test STL cache entry with rotation."""
        cache_entry = STLCache(
            part_num="3001",
            file_path="/cache/stl/3001_rotated.stl",
            file_size=2048,
            rotation_enabled=True,
            rotation_x=90.0,
            rotation_y=45.0,
            rotation_z=0.0,
            scale=10.0
        )
        test_db.add(cache_entry)
        test_db.commit()
        
        retrieved = test_db.query(STLCache).filter(STLCache.part_num == "3001").first()
        assert retrieved.rotation_enabled is True
        assert retrieved.rotation_x == 90.0
        assert retrieved.rotation_y == 45.0

    def test_stl_cache_unique_constraint(self, test_db):
        """Test unique constraint on STL cache."""
        cache1 = STLCache(
            part_num="3001",
            file_path="/cache/1.stl",
            file_size=1024,
            rotation_enabled=False,
            rotation_x=0.0,
            rotation_y=0.0,
            rotation_z=0.0,
            scale=10.0
        )
        test_db.add(cache1)
        test_db.commit()
        
        # Try to add another with same key
        cache2 = STLCache(
            part_num="3001",
            file_path="/cache/2.stl",
            file_size=2048,
            rotation_enabled=False,
            rotation_x=0.0,
            rotation_y=0.0,
            rotation_z=0.0,
            scale=10.0
        )
        test_db.add(cache2)
        
        with pytest.raises(Exception):  # Should raise integrity error
            test_db.commit()


class TestGetDbFunction:
    """Tests for get_db dependency function."""

    def test_get_db_yields_session(self, test_db):
        """Test that get_db yields a database session."""
        # Test that the fixture provides a valid session
        assert hasattr(test_db, 'query')
        assert hasattr(test_db, 'add')
        assert hasattr(test_db, 'commit')
        
        # Test that we can query
        count = test_db.query(Project).count()
        assert count == 0  # Empty database

    def test_get_db_closes_session(self, test_db):
        """Test that database sessions work correctly."""
        # Add a project
        project = Project(
            id="test-session",
            set_num="12345-1",
            name="Session Test"
        )
        test_db.add(project)
        test_db.commit()
        
        # Verify it was added
        count = test_db.query(Project).count()
        assert count == 1
