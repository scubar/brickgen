"""Unit tests for backend.core.ldview_converter."""
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from backend.core.ldview_converter import LDViewConverter


class TestLDViewConverterFindPartFile:
    def test_find_part_file_exact(self, tmp_ldraw_parts):
        (tmp_ldraw_parts / "3005.dat").write_text("0 placeholder")
        conv = LDViewConverter(ldraw_library_path=tmp_ldraw_parts.parent)
        found = conv._find_part_file("3005")
        assert found is not None
        assert found.name == "3005.dat"

    def test_find_part_file_strips_dot_dat(self, tmp_ldraw_parts):
        (tmp_ldraw_parts / "3005.dat").write_text("0")
        conv = LDViewConverter(ldraw_library_path=tmp_ldraw_parts.parent)
        assert conv._find_part_file("3005.dat") is not None
        assert conv._find_part_file("3005").name == "3005.dat"

    def test_find_part_file_tries_variants(self, tmp_ldraw_parts):
        (tmp_ldraw_parts / "3005a.dat").write_text("0")
        conv = LDViewConverter(ldraw_library_path=tmp_ldraw_parts.parent)
        found = conv._find_part_file("3005")
        assert found is not None
        assert found.name == "3005a.dat"

    def test_find_part_file_not_found_returns_none(self, tmp_ldraw_parts):
        conv = LDViewConverter(ldraw_library_path=tmp_ldraw_parts.parent)
        assert conv._find_part_file("nonexistent999") is None

    def test_find_part_file_case_insensitive_id(self, tmp_ldraw_parts):
        (tmp_ldraw_parts / "3005.dat").write_text("0")
        conv = LDViewConverter(ldraw_library_path=tmp_ldraw_parts.parent)
        found = conv._find_part_file("3005")
        assert found is not None


class TestLDViewConverterScaleStl:
    def test_scale_stl_file_ascii(self, tmp_path):
        inp = tmp_path / "in.stl"
        inp.write_text(
            "solid t\n"
            "  facet normal 0 0 1\n"
            "    outer loop\n"
            "      vertex 1 2 3\n"
            "      vertex 4 5 6\n"
            "      vertex 7 8 9\n"
            "    endloop\n"
            "  endfacet\n"
            "endsolid t\n"
        )
        out = tmp_path / "out.stl"
        conv = LDViewConverter(ldraw_library_path=Path("/tmp"))
        assert conv._scale_stl_file(inp, out, scale_factor=10.0) is True
        content = out.read_text()
        assert "10.000000 20.000000 30.000000" in content
        assert "40.000000 50.000000 60.000000" in content
        assert "70.000000 80.000000 90.000000" in content

    def test_scale_stl_preserves_non_vertex_lines(self, tmp_path):
        inp = tmp_path / "in.stl"
        inp.write_text(
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
        out = tmp_path / "out.stl"
        conv = LDViewConverter(ldraw_library_path=Path("/tmp"))
        conv._scale_stl_file(inp, out, scale_factor=2.0)
        assert "solid t" in out.read_text()
        assert "facet normal" in out.read_text()
