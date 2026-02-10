"""Tests for configuration management (backend/config.py)."""
import os
import tempfile
from pathlib import Path
import pytest
from backend.config import Settings


class TestSettings:
    """Test Settings class initialization and validation."""

    def test_default_values(self):
        """Test that settings have expected defaults."""
        settings = Settings()
        assert settings.rebrickable_api_key == ""
        assert settings.default_plate_width == 220
        assert settings.default_plate_depth == 220
        assert settings.default_plate_height == 250
        assert settings.part_spacing == 2
        assert settings.stl_scale_factor == 1.0
        assert settings.rotation_enabled is False
        assert settings.rotation_x == 0.0
        assert settings.rotation_y == 0.0
        assert settings.rotation_z == 0.0
        assert settings.default_orientation_match_preview is True
        assert settings.auto_generate_part_previews is True

    def test_scale_factor_backend_calculation(self):
        """Test that backend scale factor is correctly calculated."""
        settings = Settings(stl_scale_factor=1.0)
        assert settings.stl_scale_factor_backend == 10.0
        
        settings = Settings(stl_scale_factor=2.5)
        assert settings.stl_scale_factor_backend == 25.0
        
        settings = Settings(stl_scale_factor=0.5)
        assert settings.stl_scale_factor_backend == 5.0

    def test_load_from_env(self):
        """Test loading configuration from environment variables."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Set environment variables
            os.environ["REBRICKABLE_API_KEY"] = "test_key_123"
            os.environ["DEFAULT_PLATE_WIDTH"] = "300"
            os.environ["DEFAULT_PLATE_HEIGHT"] = "280"
            os.environ["STL_SCALE_FACTOR"] = "1.5"
            os.environ["ROTATION_ENABLED"] = "true"
            os.environ["ROTATION_X"] = "45.0"
            os.environ["CACHE_DIR"] = tmpdir
            
            try:
                settings = Settings()
                assert settings.rebrickable_api_key == "test_key_123"
                assert settings.default_plate_width == 300
                assert settings.default_plate_height == 280
                assert settings.stl_scale_factor == 1.5
                assert settings.rotation_enabled is True
                assert settings.rotation_x == 45.0
            finally:
                # Clean up environment variables
                for key in ["REBRICKABLE_API_KEY", "DEFAULT_PLATE_WIDTH", "DEFAULT_PLATE_HEIGHT", 
                           "STL_SCALE_FACTOR", "ROTATION_ENABLED", "ROTATION_X", "CACHE_DIR"]:
                    os.environ.pop(key, None)

    def test_path_configuration(self):
        """Test path configuration settings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["LDRAW_LIBRARY_PATH"] = f"{tmpdir}/ldraw"
            os.environ["CACHE_DIR"] = f"{tmpdir}/cache"
            os.environ["DATABASE_PATH"] = f"{tmpdir}/db/test.db"
            os.environ["OUTPUT_DIR"] = f"{tmpdir}/output"
            
            try:
                settings = Settings()
                assert settings.ldraw_library_path == Path(f"{tmpdir}/ldraw")
                assert settings.cache_dir == Path(f"{tmpdir}/cache")
                assert settings.database_path == Path(f"{tmpdir}/db/test.db")
                assert settings.output_dir == Path(f"{tmpdir}/output")
            finally:
                for key in ["LDRAW_LIBRARY_PATH", "CACHE_DIR", "DATABASE_PATH", "OUTPUT_DIR"]:
                    os.environ.pop(key, None)

    def test_api_configuration(self):
        """Test API-related configuration."""
        settings = Settings()
        assert settings.api_prefix == "/api"
        assert settings.cors_origins == ["*"]
        assert settings.max_job_age_hours == 24

    def test_boolean_parsing(self):
        """Test boolean environment variable parsing."""
        os.environ["ROTATION_ENABLED"] = "1"
        os.environ["DEFAULT_ORIENTATION_MATCH_PREVIEW"] = "yes"
        os.environ["AUTO_GENERATE_PART_PREVIEWS"] = "false"
        
        try:
            settings = Settings()
            assert settings.rotation_enabled is True
            assert settings.default_orientation_match_preview is True
            assert settings.auto_generate_part_previews is False
        finally:
            for key in ["ROTATION_ENABLED", "DEFAULT_ORIENTATION_MATCH_PREVIEW", "AUTO_GENERATE_PART_PREVIEWS"]:
                os.environ.pop(key, None)

    def test_numeric_constraints(self):
        """Test numeric value validation."""
        # Test that positive integers work
        settings = Settings(
            default_plate_width=100,
            default_plate_depth=150,
            part_spacing=5
        )
        assert settings.default_plate_width == 100
        assert settings.default_plate_depth == 150
        assert settings.part_spacing == 5

    def test_rotation_values(self):
        """Test rotation configuration values."""
        settings = Settings(
            rotation_enabled=True,
            rotation_x=90.5,
            rotation_y=-45.0,
            rotation_z=180.0
        )
        assert settings.rotation_enabled is True
        assert settings.rotation_x == 90.5
        assert settings.rotation_y == -45.0
        assert settings.rotation_z == 180.0
