"""Tests for underlying functions used by API routes (no server/TestClient)."""
import pytest

from backend.api.routes.parts import _rotation_suffix, _parse_preview_filename


class TestPartsRotationSuffix:
    """Tests for _rotation_suffix used by part preview cache key."""

    def test_all_zero_returns_empty(self):
        assert _rotation_suffix(0, 0, 0) == ""

    def test_single_axis(self):
        assert "_r90" in _rotation_suffix(90, 0, 0)
        assert "_r-90" in _rotation_suffix(-90, 0, 0)
        assert _rotation_suffix(90, 0, 0) == "_r90_0_0"

    def test_all_axes(self):
        s = _rotation_suffix(90, 45, 30)
        assert s == "_r90_45_30"

    def test_float_rounded(self):
        assert _rotation_suffix(90.7, 0, 0) == "_r91_0_0"


class TestParsePreviewFilename:
    """Tests for _parse_preview_filename used by preview-cache list."""

    def test_simple_stem(self):
        assert _parse_preview_filename("3005_256") == {
            "ldraw_id": "3005",
            "size": 256,
            "rotation_x": 0,
            "rotation_y": 0,
            "rotation_z": 0,
        }

    def test_with_rotation(self):
        assert _parse_preview_filename("3005_512_r-90_0_0") == {
            "ldraw_id": "3005",
            "size": 512,
            "rotation_x": -90,
            "rotation_y": 0,
            "rotation_z": 0,
        }

    def test_with_color_suffix(self):
        # Parser allows optional _c[hex] at end; groups 4,5,6 are rotation
        out = _parse_preview_filename("3005_256_cff5500")
        assert out["ldraw_id"] == "3005"
        assert out["size"] == 256
        assert out["rotation_x"] == 0 and out["rotation_y"] == 0 and out["rotation_z"] == 0

    def test_invalid_returns_empty(self):
        assert _parse_preview_filename("") == {}
        assert _parse_preview_filename("nospace") == {}
        assert _parse_preview_filename("3005") == {}
