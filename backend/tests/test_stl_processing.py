"""Unit tests for backend.core.stl_processing."""
import pytest

from backend.core.stl_processing import STLConverter, _cache_filename


class TestCacheFilename:
    """Tests for _cache_filename (omit 0/false for shorter names)."""

    def test_part_only_scale_zero(self):
        assert _cache_filename("3404", 0, False, 0, 0, 0, "") == "3404"

    def test_part_and_scale(self):
        assert _cache_filename("3404", 10, False, 0, 0, 0, "abc123") == "3404_scale10_qabc123"

    def test_rotation_enabled_zero_angles(self):
        assert _cache_filename("3404", 10, True, 0, 0, 0, "abc123") == "3404_scale10_rotation1_qabc123"

    def test_rotation_enabled_with_x(self):
        assert _cache_filename("3404", 10, True, 233, 0, 0, "abc123") == "3404_scale10_rotation1_rotationX233_qabc123"

    def test_rotation_enabled_x_y_z(self):
        s = _cache_filename("3404", 10, True, 233, 45, 90, "abc123")
        assert s == "3404_scale10_rotation1_rotationX233_rotationY45_rotationZ90_qabc123"

    def test_omit_zero_angles(self):
        s = _cache_filename("3005", 10, True, -90, 0, 0, "abc123")
        assert "rotationX-90" in s
        assert "rotationY" not in s
        assert "rotationZ" not in s
        assert "qabc123" in s


class TestSTLConverterRotationSuffix:
    def test_no_rotation_empty_suffix(self):
        conv = STLConverter()
        assert conv._rotation_suffix(False, 0, 0, 0) == ""
        assert conv._rotation_suffix(False, 90, 0, 0) == ""

    def test_rotation_disabled_ignores_angles(self):
        conv = STLConverter()
        assert conv._rotation_suffix(False, 90, 45, 30) == ""

    def test_zero_angles_empty_suffix(self):
        conv = STLConverter()
        assert conv._rotation_suffix(True, 0, 0, 0) == ""

    def test_rotation_enabled_nonzero_angles_suffix(self):
        conv = STLConverter()
        s = conv._rotation_suffix(True, 90, 0, 0)
        assert "_r" in s
        assert "90" in s
        s2 = conv._rotation_suffix(True, 90, 45, 30)
        assert "_r" in s2
        assert "90" in s2 and "45" in s2 and "30" in s2


class TestSTLConverterCacheStats:
    def test_empty_cache(self):
        conv = STLConverter()
        stats = conv.get_cache_stats()
        assert stats["count"] == 0
        assert stats["total_size_mb"] == 0.0
        assert "cache_dir" in stats

    def test_cache_stats_with_files(self):
        conv = STLConverter()
        (conv.cache_dir / "3005.stl").write_text("x" * 100)
        (conv.cache_dir / "3001.stl").write_text("y" * 200)
        stats = conv.get_cache_stats()
        assert stats["count"] == 2
        assert stats["total_size_mb"] == pytest.approx(300 / (1024 * 1024), rel=1e-3)
        # Clean up so other tests don't see these
        (conv.cache_dir / "3005.stl").unlink()
        (conv.cache_dir / "3001.stl").unlink()


class TestSTLConverterClearCache:
    def test_clear_cache_removes_files(self):
        conv = STLConverter()
        (conv.cache_dir / "a.stl").write_text("a")
        (conv.cache_dir / "b.stl").write_text("b")
        n = conv.clear_cache()
        assert n == 2
        assert not (conv.cache_dir / "a.stl").exists()
        assert not (conv.cache_dir / "b.stl").exists()

    def test_clear_cache_empty_returns_zero(self):
        conv = STLConverter()
        # Ensure cache is empty (may have been cleared by env)
        for f in conv.cache_dir.glob("*.stl"):
            f.unlink()
        n = conv.clear_cache()
        assert n == 0
