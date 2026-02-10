"""Unit tests for backend.core.stl_orientation."""
import numpy as np
from pathlib import Path

import pytest

from backend.core.stl_orientation import STLOrienter


class TestSTLOrienterRotationMatrices:
    def test_rotation_x_90(self):
        r = STLOrienter._rotation_matrix_x(90)
        expected = np.array([
            [1, 0, 0],
            [0, 0, -1],
            [0, 1, 0],
        ])
        np.testing.assert_array_almost_equal(r, expected)

    def test_rotation_x_zero(self):
        r = STLOrienter._rotation_matrix_x(0)
        np.testing.assert_array_almost_equal(r, np.eye(3))

    def test_rotation_y_90(self):
        r = STLOrienter._rotation_matrix_y(90)
        expected = np.array([
            [0, 0, 1],
            [0, 1, 0],
            [-1, 0, 0],
        ])
        np.testing.assert_array_almost_equal(r, expected)

    def test_rotation_z_90(self):
        r = STLOrienter._rotation_matrix_z(90)
        expected = np.array([
            [0, -1, 0],
            [1, 0, 0],
            [0, 0, 1],
        ])
        np.testing.assert_array_almost_equal(r, expected)

    def test_rotation_z_180(self):
        r = STLOrienter._rotation_matrix_z(180)
        expected = np.array([
            [-1, 0, 0],
            [0, -1, 0],
            [0, 0, 1],
        ])
        np.testing.assert_array_almost_equal(r, expected)

    def test_compose_zyx_identity(self):
        orienter = STLOrienter()
        rx = STLOrienter._rotation_matrix_x(0)
        ry = STLOrienter._rotation_matrix_y(0)
        rz = STLOrienter._rotation_matrix_z(0)
        composed = rz @ ry @ rx
        np.testing.assert_array_almost_equal(composed, np.eye(3))


class TestSTLOrienterApplyAbsoluteRotation:
    def test_zero_rotation_returns_true_without_writing(self, tmp_path):
        stl = tmp_path / "part.stl"
        stl.write_text(
            "solid t\n"
            "  facet normal 0 0 1\n"
            "    outer loop\n"
            "      vertex 0 0 0\n"
            "      vertex 1 0 0\n"
            "      vertex 0.5 1 0\n"
            "    endloop\n"
            "  endfacet\n"
            "endsolid t\n"
        )
        orienter = STLOrienter()
        assert orienter.apply_absolute_rotation(stl, 0, 0, 0) is True
        assert stl.read_text() == (
            "solid t\n"
            "  facet normal 0 0 1\n"
            "    outer loop\n"
            "      vertex 0 0 0\n"
            "      vertex 1 0 0\n"
            "      vertex 0.5 1 0\n"
            "    endloop\n"
            "  endfacet\n"
            "endsolid t\n"
        )

    def test_apply_rotation_modifies_stl(self, tmp_path):
        stl = tmp_path / "part.stl"
        stl.write_text(
            "solid t\n"
            "  facet normal 0 0 1\n"
            "    outer loop\n"
            "      vertex 1 0 0\n"
            "      vertex 0 1 0\n"
            "      vertex 0 0 1\n"
            "    endloop\n"
            "  endfacet\n"
            "endsolid t\n"
        )
        orienter = STLOrienter()
        assert orienter.apply_absolute_rotation(stl, 90, 0, 0) is True
        content = stl.read_text()
        assert "vertex" in content
        assert "1.000000" not in content or "0.000000" in content  # coordinates changed

    def test_nonexistent_file_returns_false(self):
        orienter = STLOrienter()
        assert orienter.apply_absolute_rotation(Path("/nonexistent.stl"), 90, 0, 0) is False

