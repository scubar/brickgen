"""Tests for settings API routes (backend/api/routes/settings.py)."""
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base, AppSettings, CachedSet, CachedParts, STLCache, get_db
from backend.api.routes.settings import router, _row_to_response, _sync_config_from_row
from backend.config import settings as app_settings


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


@pytest.fixture
def test_app(test_db):
    """Create a test FastAPI app with the settings router."""
    app = FastAPI()
    app.include_router(router)
    
    # Override the get_db dependency
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    return app


@pytest.fixture
def client(test_app):
    """Create a test client."""
    return TestClient(test_app)


class TestGetSettings:
    """Tests for GET /settings endpoint."""

    def test_get_settings_default_when_no_db_row(self, client):
        """Test getting settings returns defaults when no DB row exists."""
        response = client.get("/settings")
        assert response.status_code == 200
        
        data = response.json()
        assert data["default_plate_width"] == 220
        assert data["default_plate_depth"] == 220
        assert data["default_plate_height"] == 250
        assert data["part_spacing"] == 2
        assert data["stl_scale_factor"] == 1.0
        assert data["rotation_enabled"] is False
        assert data["rotation_x"] == 0.0
        assert data["default_orientation_match_preview"] is True
        assert data["auto_generate_part_previews"] is True

    def test_get_settings_from_db_row(self, client, test_db):
        """Test getting settings from database row."""
        # Create a settings row
        settings_row = AppSettings(
            id=1,
            default_plate_width=300,
            default_plate_depth=250,
            default_plate_height=280,
            part_spacing=3,
            stl_scale_factor=1.5,
            rotation_enabled=True,
            rotation_x=90.0,
            rotation_y=45.0,
            rotation_z=30.0,
            default_orientation_match_preview=False,
            auto_generate_part_previews=False
        )
        test_db.add(settings_row)
        test_db.commit()
        
        response = client.get("/settings")
        assert response.status_code == 200
        
        data = response.json()
        assert data["default_plate_width"] == 300
        assert data["default_plate_depth"] == 250
        assert data["default_plate_height"] == 280
        assert data["part_spacing"] == 3
        assert data["stl_scale_factor"] == 1.5
        assert data["rotation_enabled"] is True
        assert data["rotation_x"] == 90.0
        assert data["rotation_y"] == 45.0
        assert data["rotation_z"] == 30.0
        assert data["default_orientation_match_preview"] is False
        assert data["auto_generate_part_previews"] is False


class TestUpdateSettings:
    """Tests for POST /settings endpoint."""

    def test_update_settings_creates_row_if_missing(self, client, test_db):
        """Test updating settings creates a row if one doesn't exist."""
        update_data = {
            "default_plate_width": 300,
            "stl_scale_factor": 1.5
        }
        
        response = client.post("/settings", json=update_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["settings"]["default_plate_width"] == 300
        assert data["settings"]["stl_scale_factor"] == 1.5
        assert data["cache_cleared"] is False
        
        # Verify row was created in DB
        row = test_db.query(AppSettings).filter(AppSettings.id == 1).first()
        assert row is not None
        assert row.default_plate_width == 300

    def test_update_settings_partial_update(self, client, test_db):
        """Test partial settings update."""
        # Create initial settings
        settings_row = AppSettings(
            id=1,
            default_plate_width=220,
            default_plate_depth=220,
            stl_scale_factor=1.0
        )
        test_db.add(settings_row)
        test_db.commit()
        
        # Update only one field
        update_data = {"default_plate_width": 350}
        response = client.post("/settings", json=update_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["settings"]["default_plate_width"] == 350
        assert data["settings"]["default_plate_depth"] == 220  # Unchanged
        assert data["settings"]["stl_scale_factor"] == 1.0  # Unchanged

    @patch('backend.api.routes.settings.STLConverter')
    def test_update_rotation_clears_cache(self, mock_converter_class, client, test_db):
        """Test that changing rotation_enabled clears STL cache."""
        # Setup mock
        mock_converter = Mock()
        mock_converter.clear_cache.return_value = 5
        mock_converter_class.return_value = mock_converter
        
        # Create initial settings with rotation disabled
        settings_row = AppSettings(id=1, rotation_enabled=False)
        test_db.add(settings_row)
        test_db.commit()
        
        # Enable rotation
        update_data = {"rotation_enabled": True}
        response = client.post("/settings", json=update_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["cache_cleared"] is True
        mock_converter.clear_cache.assert_called_once()

    @patch('backend.api.routes.settings.STLConverter')
    def test_update_orientation_clears_cache(self, mock_converter_class, client, test_db):
        """Test that changing default_orientation_match_preview clears cache."""
        mock_converter = Mock()
        mock_converter.clear_cache.return_value = 3
        mock_converter_class.return_value = mock_converter
        
        # Create initial settings
        settings_row = AppSettings(id=1, default_orientation_match_preview=True)
        test_db.add(settings_row)
        test_db.commit()
        
        # Change orientation setting
        update_data = {"default_orientation_match_preview": False}
        response = client.post("/settings", json=update_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["cache_cleared"] is True

    def test_update_settings_all_fields(self, client, test_db):
        """Test updating all settings fields."""
        update_data = {
            "default_plate_width": 300,
            "default_plate_depth": 280,
            "default_plate_height": 270,
            "part_spacing": 5,
            "stl_scale_factor": 2.0,
            "rotation_enabled": True,
            "rotation_x": 90.0,
            "rotation_y": 45.0,
            "rotation_z": 180.0,
            "default_orientation_match_preview": False,
            "auto_generate_part_previews": False
        }
        
        response = client.post("/settings", json=update_data)
        assert response.status_code == 200
        
        data = response.json()["settings"]
        for key, value in update_data.items():
            assert data[key] == value


class TestApiKeyUpdate:
    """Tests for POST /settings/api-key endpoint."""

    def test_update_api_key_success(self, client):
        """Test successful API key update."""
        update_data = {"api_key": "test_api_key_12345"}
        
        response = client.post("/settings/api-key", json=update_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "updated successfully" in data["message"].lower()

    def test_update_api_key_empty_fails(self, client):
        """Test that empty API key fails."""
        update_data = {"api_key": ""}
        
        response = client.post("/settings/api-key", json=update_data)
        assert response.status_code == 400

    def test_update_api_key_whitespace_only_fails(self, client):
        """Test that whitespace-only API key fails."""
        update_data = {"api_key": "   "}
        
        response = client.post("/settings/api-key", json=update_data)
        assert response.status_code == 400


class TestRebrickableCacheList:
    """Tests for GET /cache/rebrickable endpoint."""

    def test_list_empty_cache(self, client):
        """Test listing empty Rebrickable cache."""
        response = client.get("/cache/rebrickable")
        assert response.status_code == 200
        
        data = response.json()
        assert data["count"] == 0
        assert data["results"] == []
        assert data["page"] == 1
        assert data["next"] is None
        assert data["previous"] is None

    def test_list_cached_sets(self, client, test_db):
        """Test listing cached sets."""
        # Add some cached sets
        for i in range(5):
            cached_set = CachedSet(
                set_num=f"1234{i}-1",
                name=f"Test Set {i}",
                year=2020 + i,
                theme="Test",
                subtheme="",
                pieces=100 * i,
                image_url=f"https://example.com/{i}.jpg",
                data="{}"
            )
            test_db.add(cached_set)
        test_db.commit()
        
        response = client.get("/cache/rebrickable")
        assert response.status_code == 200
        
        data = response.json()
        assert data["count"] == 5
        assert len(data["results"]) == 5
        assert data["page"] == 1

    def test_list_cached_sets_pagination(self, client, test_db):
        """Test pagination of cached sets."""
        # Add 25 cached sets
        for i in range(25):
            cached_set = CachedSet(
                set_num=f"9999{i:02d}-1",
                name=f"Set {i}",
                year=2020,
                theme="Test",
                subtheme="",
                pieces=100,
                image_url="",
                data="{}"
            )
            test_db.add(cached_set)
        test_db.commit()
        
        # Get first page
        response = client.get("/cache/rebrickable?page=1&page_size=10")
        assert response.status_code == 200
        
        data = response.json()
        assert data["count"] == 25
        assert len(data["results"]) == 10
        assert data["page"] == 1
        assert data["next"] == 2
        assert data["previous"] is None
        
        # Get second page
        response = client.get("/cache/rebrickable?page=2&page_size=10")
        assert response.status_code == 200
        
        data = response.json()
        assert data["count"] == 25
        assert len(data["results"]) == 10
        assert data["page"] == 2
        assert data["next"] == 3
        assert data["previous"] == 1


class TestClearRebrickableCache:
    """Tests for DELETE /cache/rebrickable endpoint."""

    def test_clear_all_cache(self, client, test_db):
        """Test clearing all Rebrickable cache."""
        # Add some data
        cached_set = CachedSet(
            set_num="12345-1",
            name="Test Set",
            year=2020,
            theme="Test",
            subtheme="",
            pieces=100,
            image_url="",
            data="{}"
        )
        test_db.add(cached_set)
        
        cached_parts = CachedParts(
            set_num="12345-1",
            parts_data="{}"
        )
        test_db.add(cached_parts)
        test_db.commit()
        
        # Clear cache
        response = client.delete("/cache/rebrickable")
        assert response.status_code == 200
        
        data = response.json()
        assert data["sets"] == 1
        assert data["parts"] == 1
        
        # Verify cleared
        assert test_db.query(CachedSet).count() == 0
        assert test_db.query(CachedParts).count() == 0

    def test_clear_specific_set_cache(self, client, test_db):
        """Test clearing cache for a specific set."""
        # Add multiple sets
        for i in range(3):
            cached_set = CachedSet(
                set_num=f"1234{i}-1",
                name=f"Set {i}",
                year=2020,
                theme="Test",
                subtheme="",
                pieces=100,
                image_url="",
                data="{}"
            )
            test_db.add(cached_set)
        test_db.commit()
        
        # Clear only one
        response = client.delete("/cache/rebrickable?set_num=12340-1")
        assert response.status_code == 200
        
        data = response.json()
        assert data["sets"] == 1
        
        # Verify only one was cleared
        assert test_db.query(CachedSet).count() == 2


class TestCacheStats:
    """Tests for GET /cache/stats endpoint."""

    @patch('backend.api.routes.settings.STLConverter')
    def test_get_cache_stats(self, mock_converter_class, client):
        """Test getting STL cache statistics."""
        mock_converter = Mock()
        mock_converter.get_cache_stats.return_value = {
            'count': 10,
            'total_size_mb': 25.5,
            'cache_dir': '/tmp/cache'
        }
        mock_converter_class.return_value = mock_converter
        
        response = client.get("/cache/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert data["stl_count"] == 10
        assert data["total_size_mb"] == 25.5
        assert data["cache_dir"] == '/tmp/cache'


class TestClearCache:
    """Tests for DELETE /cache/clear endpoint."""

    @patch('backend.api.routes.settings.STLConverter')
    def test_clear_stl_cache(self, mock_converter_class, client):
        """Test clearing STL cache."""
        mock_converter = Mock()
        mock_converter.clear_cache.return_value = 15
        mock_converter_class.return_value = mock_converter
        
        response = client.delete("/cache/clear")
        assert response.status_code == 200
        
        data = response.json()
        assert data["deleted_count"] == 15
        assert "15" in data["message"]


class TestHelperFunctions:
    """Tests for helper functions in settings routes."""

    def test_row_to_response(self):
        """Test _row_to_response conversion."""
        row = AppSettings(
            id=1,
            default_plate_width=300,
            default_plate_depth=250,
            stl_scale_factor=1.5,
            rotation_enabled=True,
            rotation_x=90.0
        )
        
        response = _row_to_response(row)
        assert response.default_plate_width == 300
        assert response.default_plate_depth == 250
        assert response.stl_scale_factor == 1.5
        assert response.rotation_enabled is True
        assert response.rotation_x == 90.0

    def test_row_to_response_with_none_values(self):
        """Test _row_to_response with None values uses defaults."""
        row = AppSettings(
            id=1,
            default_plate_width=None,
            stl_scale_factor=None,
            rotation_x=None
        )
        
        response = _row_to_response(row)
        assert response.default_plate_width == 220  # Default
        assert response.stl_scale_factor == 1.0  # Default
        assert response.rotation_x == 0.0  # Default

    def test_sync_config_from_row(self):
        """Test _sync_config_from_row updates in-memory config."""
        row = AppSettings(
            id=1,
            default_plate_width=350,
            stl_scale_factor=2.0,
            rotation_enabled=True
        )
        
        _sync_config_from_row(row)
        
        assert app_settings.default_plate_width == 350
        assert app_settings.stl_scale_factor == 2.0
        assert app_settings.rotation_enabled is True
