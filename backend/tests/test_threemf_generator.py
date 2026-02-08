"""Unit tests for backend.core.threemf_generator."""
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from backend.core.threemf_generator import ThreeMFGenerator, NS_M


# --- ASCII STL helpers for tests ---

def _write_ascii_stl(path: Path, vertices: list, triangles: list) -> None:
    """Write a minimal ASCII STL (one triangle per facet)."""
    lines = ["solid test"]
    for tri in triangles:
        i, j, k = tri
        a, b, c = vertices[i], vertices[j], vertices[k]
        # Normal from cross product (simplified: assume upward)
        lines.append("  facet normal 0 0 1")
        lines.append(f"    outer loop")
        lines.append(f"      vertex {a[0]} {a[1]} {a[2]}")
        lines.append(f"      vertex {b[0]} {b[1]} {b[2]}")
        lines.append(f"      vertex {c[0]} {c[1]} {c[2]}")
        lines.append(f"    endloop")
        lines.append("  endfacet")
    lines.append("endsolid test")
    path.write_text("\n".join(lines))


class TestThreeMFGeneratorComputeBoundingBox:
    def test_empty_vertices(self):
        gen = ThreeMFGenerator()
        result = gen._compute_bounding_box([])
        assert result["min"] == [0, 0, 0]
        assert result["max"] == [0, 0, 0]
        assert result["size"] == [0, 0, 0]
        assert result["center"] == [0, 0, 0]

    def test_single_vertex(self):
        gen = ThreeMFGenerator()
        result = gen._compute_bounding_box([[1.0, 2.0, 3.0]])
        assert result["min"] == [1.0, 2.0, 3.0]
        assert result["max"] == [1.0, 2.0, 3.0]
        assert result["size"] == [0, 0, 0]
        assert result["center"] == [1.0, 2.0, 3.0]

    def test_cube(self):
        gen = ThreeMFGenerator()
        vertices = [
            [0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 10, 0],
            [0, 0, 5], [10, 0, 5], [10, 10, 5], [0, 10, 5],
        ]
        result = gen._compute_bounding_box(vertices)
        assert result["min"] == [0, 0, 0]
        assert result["max"] == [10, 10, 5]
        assert result["size"] == [10, 10, 5]
        assert result["center"] == [5.0, 5.0, 2.5]


class TestThreeMFGeneratorParseStl:
    def test_valid_ascii_stl(self, tmp_path):
        gen = ThreeMFGenerator()
        stl = tmp_path / "part.stl"
        vertices = [[0, 0, 0], [1, 0, 0], [0.5, 1, 0]]
        triangles = [[0, 1, 2]]
        _write_ascii_stl(stl, vertices, triangles)
        result = gen._parse_stl(stl)
        assert result is not None
        assert len(result["vertices"]) == 3
        assert result["triangles"] == [[0, 1, 2]]

    def test_missing_file_returns_none(self):
        gen = ThreeMFGenerator()
        result = gen._parse_stl(Path("/nonexistent/file.stl"))
        assert result is None


class TestThreeMFGeneratorPackParts:
    def test_single_part_fits(self):
        gen = ThreeMFGenerator(part_spacing=2)
        mesh = {
            "vertices": [[0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 10, 0],
                        [0, 0, 5], [10, 0, 5], [10, 10, 5], [0, 10, 5]],
            "triangles": [[0, 1, 2], [0, 2, 3], [4, 5, 6], [4, 6, 7], [0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5], [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7]],
        }
        bbox = gen._compute_bounding_box(mesh["vertices"])
        part_meshes = [
            {"mesh_data": mesh, "ldraw_id": "3005", "bbox": bbox, "quantity": 1, "color_rgb": None}
        ]
        placements = gen._pack_parts(part_meshes, plate_width=220, plate_depth=220)
        assert placements is not None
        assert len(placements) == 1
        assert "translation" in placements[0]
        assert placements[0]["ldraw_id"] == "3005"

    def test_quantity_two(self):
        gen = ThreeMFGenerator(part_spacing=2)
        mesh = {
            "vertices": [[0, 0, 0], [5, 0, 0], [5, 5, 0], [0, 5, 0]],
            "triangles": [[0, 1, 2], [0, 2, 3]],
        }
        bbox = gen._compute_bounding_box(mesh["vertices"])
        part_meshes = [
            {"mesh_data": mesh, "ldraw_id": "x", "bbox": bbox, "quantity": 2, "color_rgb": "FF0000"}
        ]
        placements = gen._pack_parts(part_meshes, plate_width=100, plate_depth=100)
        assert placements is not None
        assert len(placements) == 2


class TestThreeMFGeneratorCreate3mf:
    def test_create_3mf_file(self, tmp_path):
        gen = ThreeMFGenerator()
        mesh = {
            "vertices": [[0, 0, 0], [1, 0, 0], [0.5, 1, 0]],
            "triangles": [[0, 1, 2]],
        }
        placements = [
            {
                "mesh_data": mesh,
                "translation": [0.0, 0.0, 0.0],
                "ldraw_id": "3005",
                "instance_num": 1,
                "color_rgb": "808080",
            }
        ]
        out = tmp_path / "out.3mf"
        assert gen._create_3mf_file(placements, out) is True
        assert out.exists()
        with zipfile.ZipFile(out, "r") as zf:
            names = zf.namelist()
        assert "[Content_Types].xml" in names
        assert "_rels/.rels" in names
        assert "3D/3dmodel.model" in names

    def test_3mf_model_has_mesh_and_build_item(self, tmp_path):
        gen = ThreeMFGenerator()
        mesh = {
            "vertices": [[0, 0, 0], [1, 0, 0], [0.5, 1, 0]],
            "triangles": [[0, 1, 2]],
        }
        placements = [
            {
                "mesh_data": mesh,
                "translation": [1.0, 2.0, 0.0],
                "ldraw_id": "3005",
                "instance_num": 1,
                "color_rgb": None,
            }
        ]
        out = tmp_path / "out.3mf"
        gen._create_3mf_file(placements, out)
        with zipfile.ZipFile(out, "r") as zf:
            raw = zf.read("3D/3dmodel.model").decode("utf-8")
        root = ET.fromstring(raw)
        model_ns = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
        ns = {"m": model_ns}
        vertices = root.findall(".//m:vertices", ns)
        build_items = root.findall(".//m:item", ns)
        assert len(vertices) >= 1
        assert len(build_items) >= 1


class TestThreeMFGeneratorGenerate3mf:
    def test_generate_3mf_integration(self, tmp_path):
        stl = tmp_path / "part.stl"
        _write_ascii_stl(stl, [[0, 0, 0], [10, 0, 0], [5, 10, 0]], [[0, 1, 2]])
        gen = ThreeMFGenerator(part_spacing=2)
        parts = [(str(stl), "3005", 1)]
        out = tmp_path / "project.3mf"
        assert gen.generate_3mf(parts, plate_width=220, plate_depth=220, output_path=out) is True
        assert out.exists()

    def test_generate_3mf_with_color(self, tmp_path):
        stl = tmp_path / "part.stl"
        _write_ascii_stl(stl, [[0, 0, 0], [10, 0, 0], [5, 10, 0]], [[0, 1, 2]])
        gen = ThreeMFGenerator(part_spacing=2)
        parts = [(str(stl), "3005", 1, "FF5500")]
        out = tmp_path / "project.3mf"
        assert gen.generate_3mf(parts, plate_width=220, plate_depth=220, output_path=out) is True
        assert out.exists()
