"""3MF file generation with bin packing for 3D printing.

Note on Bambu Studio: When opening a 3MF not created by Bambu Lab, Bambu Studio shows
"load geometry data and color data only". It uses the 3MF Production Extension by default;
for other 3MF files it may ignore build-item transforms (placement) and only import
meshes, then apply its own arrangement. So pre-placed parts may still appear stacked in
the center in Bambu; other slicers (e.g. PrusaSlicer, Cura) that fully support 3MF Core
should respect our placement. We output standard 3MF Core with matrix transforms and
optional Materials Extension colors for maximum compatibility.
"""
import logging
import os
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
import re

logger = logging.getLogger(__name__)

# 3MF Materials Extension namespace for color
NS_M = "http://schemas.microsoft.com/3dmanufacturing/material/2015/02"


class ThreeMFGenerator:
    """Generate 3MF files with parts arranged on build plate using bin packing."""
    
    def __init__(self, part_spacing: int = 2):
        """Initialize generator.
        
        Args:
            part_spacing: Minimum spacing between parts in mm
        """
        self.part_spacing = part_spacing
    
    def generate_3mf(
        self,
        parts: List[Tuple[Any, ...]],  # (stl_path, ldraw_id, quantity) or (..., color_rgb)
        plate_width: int,
        plate_depth: int,
        plate_height: int,
        output_path: Path
    ) -> bool:
        """Generate 3MF file with parts arranged on build plate(s) using bin packing.
        
        Args:
            parts: (stl_path, ldraw_id, quantity) or (stl_path, ldraw_id, quantity, color_rgb).
                   color_rgb optional, e.g. "FF5500" (hex without #).
            plate_width: Build plate width in mm
            plate_depth: Build plate depth in mm
            plate_height: Build plate height in mm (for reference; packing uses width/depth)
            output_path: Where to save the 3MF file
        
        Returns:
            True if successful, False if parts don't fit or error occurs
        """
        try:
            part_meshes = []
            for t in parts:
                stl_path, ldraw_id, quantity = t[0], t[1], t[2]
                color_rgb = (t[3].strip().lstrip("#") or None) if len(t) > 3 and t[3] else None
                if color_rgb and len(color_rgb) != 6:
                    color_rgb = None
                mesh_data = self._parse_stl(Path(stl_path))
                if mesh_data:
                    bbox = self._compute_bounding_box(mesh_data['vertices'])
                    part_meshes.append({
                        'mesh_data': mesh_data,
                        'ldraw_id': ldraw_id,
                        'bbox': bbox,
                        'quantity': quantity,
                        'color_rgb': color_rgb,
                    })
            if not part_meshes:
                logger.error("No valid meshes to pack")
                return False
            placements = self._pack_parts(part_meshes, plate_width, plate_depth, plate_height)
            if not placements:
                logger.error("Parts do not fit on build plate(s)")
                return False
            return self._create_3mf_file(placements, output_path)
            
        except Exception as e:
            logger.error(f"Error generating 3MF: {e}")
            return False
    
    def _parse_stl(self, stl_path: Path) -> Optional[Dict]:
        """Parse ASCII STL file to extract vertices and triangles.
        
        Returns:
            Dict with 'vertices' and 'triangles' or None
        """
        try:
            vertices = []
            triangles = []
            current_vertices = []
            
            with open(stl_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    
                    if line.startswith('vertex'):
                        parts = line.split()
                        if len(parts) >= 4:
                            vertex = [float(parts[1]), float(parts[2]), float(parts[3])]
                            vertices.append(vertex)
                            current_vertices.append(len(vertices) - 1)
                    
                    elif line.startswith('endfacet'):
                        if len(current_vertices) == 3:
                            triangles.append(current_vertices[:])
                        current_vertices = []
            
            return {
                'vertices': vertices,
                'triangles': triangles
            }
            
        except Exception as e:
            logger.error(f"Error parsing STL {stl_path}: {e}")
            return None
    
    def _compute_bounding_box(self, vertices: List[List[float]]) -> Dict:
        """Compute axis-aligned bounding box of vertices.
        
        Returns:
            Dict with 'min', 'max', 'size', 'center'
        """
        if not vertices:
            return {'min': [0, 0, 0], 'max': [0, 0, 0], 'size': [0, 0, 0], 'center': [0, 0, 0]}
        
        min_x = min(v[0] for v in vertices)
        min_y = min(v[1] for v in vertices)
        min_z = min(v[2] for v in vertices)
        max_x = max(v[0] for v in vertices)
        max_y = max(v[1] for v in vertices)
        max_z = max(v[2] for v in vertices)
        
        size_x = max_x - min_x
        size_y = max_y - min_y
        size_z = max_z - min_z
        
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        center_z = (min_z + max_z) / 2
        
        return {
            'min': [min_x, min_y, min_z],
            'max': [max_x, max_y, max_z],
            'size': [size_x, size_y, size_z],
            'center': [center_x, center_y, center_z]
        }
    
    def _pack_parts(self, part_meshes: List[Dict], plate_width: int, plate_depth: int, plate_height: int) -> Optional[List[Dict]]:
        """Pack parts onto build plate using shelf algorithm.
        
        Args:
            part_meshes: List of part mesh dictionaries
            plate_width: Build plate width in mm
            plate_depth: Build plate depth in mm
            plate_height: Build plate height in mm (for reference; packing uses width/depth)
        
        Returns:
            List of placements with mesh_data and translation, or None if doesn't fit
        """
        placements = []
        
        # Build instance list (one per quantity) and carry color
        instances = []
        for part in part_meshes:
            for i in range(part['quantity']):
                instances.append({
                    'mesh_data': part['mesh_data'],
                    'ldraw_id': part['ldraw_id'],
                    'bbox': part['bbox'],
                    'instance_num': i + 1,
                    'color_rgb': part.get('color_rgb'),
                })
        
        instances.sort(key=lambda x: x['bbox']['size'][0] * x['bbox']['size'][1], reverse=True)
        
        plate_gap = 10  # mm between logical plates
        plate_offset_y = 0.0
        shelves = []
        current_y = 0.0
        
        for instance in instances:
            bbox = instance['bbox']
            width = bbox['size'][0]
            depth = bbox['size'][1]
            height = bbox['size'][2]
            width_with_spacing = width + self.part_spacing
            depth_with_spacing = depth + self.part_spacing
            
            placed = False
            for shelf in shelves:
                if shelf['width_remaining'] >= width_with_spacing and current_y + depth_with_spacing <= plate_depth:
                    x_pos = shelf['x']
                    y_pos = shelf['y'] + plate_offset_y
                    translation = [
                        x_pos + width / 2 - bbox['center'][0],
                        y_pos + depth / 2 - bbox['center'][1],
                        -bbox['min'][2]
                    ]
                    placements.append({
                        'mesh_data': instance['mesh_data'],
                        'translation': translation,
                        'ldraw_id': instance['ldraw_id'],
                        'instance_num': instance['instance_num'],
                        'color_rgb': instance.get('color_rgb'),
                    })
                    shelf['x'] += width_with_spacing
                    shelf['width_remaining'] -= width_with_spacing
                    shelf['height'] = max(shelf['height'], height)
                    placed = True
                    break
            
            if not placed:
                if current_y + depth_with_spacing > plate_depth:
                    # Start a new build plate
                    plate_offset_y += plate_depth + plate_gap
                    current_y = 0.0
                    shelves = []
                
                x_pos = 0
                y_pos = current_y + plate_offset_y
                translation = [
                    x_pos + width / 2 - bbox['center'][0],
                    y_pos + depth / 2 - bbox['center'][1],
                    -bbox['min'][2]
                ]
                placements.append({
                    'mesh_data': instance['mesh_data'],
                    'translation': translation,
                    'ldraw_id': instance['ldraw_id'],
                    'instance_num': instance['instance_num'],
                    'color_rgb': instance.get('color_rgb'),
                })
                shelves.append({
                    'y': current_y,
                    'height': height,
                    'x': width_with_spacing,
                    'width_remaining': plate_width - width_with_spacing
                })
                current_y += height + self.part_spacing
        
        num_plates = 1 + int(plate_offset_y / (plate_depth + plate_gap)) if plate_offset_y > 0 else 1
        logger.info(f"Packed {len(placements)} parts onto {num_plates} build plate(s)")
        return placements
    
    def _create_3mf_file(self, placements: List[Dict], output_path: Path) -> bool:
        """Create 3MF ZIP file with proper structure.
        
        Args:
            placements: List of part placements with mesh_data and translation
            output_path: Where to save the 3MF file
        
        Returns:
            True if successful
        """
        try:
            # Create temporary directory for 3MF structure
            import tempfile
            import shutil
            
            with tempfile.TemporaryDirectory() as tmpdir:
                tmppath = Path(tmpdir)
                
                # Create 3MF directory structure
                (tmppath / "3D").mkdir()
                (tmppath / "_rels").mkdir()
                
                # Create [Content_Types].xml
                self._create_content_types(tmppath)
                
                # Create _rels/.rels
                self._create_rels(tmppath)
                
                # Create 3D/3dmodel.model (main model file)
                self._create_model_file(tmppath, placements)
                
                # Create 3MF ZIP file
                with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for root, _dirs, files in os.walk(tmppath):
                        root_path = Path(root)
                        for file in files:
                            file_path = root_path / file
                            arcname = file_path.relative_to(tmppath)
                            zf.write(file_path, arcname)
                
                logger.info(f"Created 3MF file: {output_path}")
                return True
                
        except Exception as e:
            logger.error(f"Error creating 3MF file: {e}")
            return False
    
    def _create_content_types(self, base_path: Path):
        """Create [Content_Types].xml file."""
        root = ET.Element("Types", xmlns="http://schemas.openxmlformats.org/package/2006/content-types")
        ET.SubElement(root, "Default", Extension="rels", ContentType="application/vnd.openxmlformats-package.relationships+xml")
        ET.SubElement(root, "Default", Extension="model", ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml")
        
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")
        tree.write(base_path / "[Content_Types].xml", encoding="utf-8", xml_declaration=True)
    
    def _create_rels(self, base_path: Path):
        """Create _rels/.rels file."""
        root = ET.Element("Relationships", xmlns="http://schemas.openxmlformats.org/package/2006/relationships")
        ET.SubElement(root, "Relationship",
                     Target="/3D/3dmodel.model",
                     Id="rel0",
                     Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel")
        
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")
        tree.write(base_path / "_rels" / ".rels", encoding="utf-8", xml_declaration=True)
    
    def _create_model_file(self, base_path: Path, placements: List[Dict]):
        """Create 3D/3dmodel.model file with meshes, optional colors, and build items.
        Uses 3MF Core transform matrix (column-major 3x4) for placement compatibility.
        """
        model_ns = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
        root = ET.Element("model", unit="millimeter", xmlns=model_ns)
        root.set("xmlns:m", NS_M)
        resources = ET.SubElement(root, "resources")
        build = ET.SubElement(root, "build")
        
        # Collect unique colors and build colorgroup (Materials Extension)
        unique_colors = []
        color_to_index = {}
        default_hex = "808080"
        for p in placements:
            rgb = (p.get("color_rgb") or "").strip().upper()
            if len(rgb) == 6 and all(c in "0123456789ABCDEF" for c in rgb):
                if rgb not in color_to_index:
                    color_to_index[rgb] = len(unique_colors)
                    unique_colors.append(rgb)
            else:
                if default_hex not in color_to_index:
                    color_to_index[default_hex] = len(unique_colors)
                    unique_colors.append(default_hex)
        
        # Resource IDs must be unique. Use id=1 for colorgroup, 2+ for objects.
        next_object_id = 2 if unique_colors else 1
        if unique_colors:
            cg = ET.SubElement(resources, f"{{{NS_M}}}colorgroup", id="1")
            for hex_rgb in unique_colors:
                ET.SubElement(cg, f"{{{NS_M}}}color", color=f"#{hex_rgb}")
        
        for idx, placement in enumerate(placements):
            object_id = next_object_id + idx
            mesh_data = placement['mesh_data']
            translation = placement['translation']
            rgb = (placement.get("color_rgb") or "").strip().upper()
            if len(rgb) != 6 or not all(c in "0123456789ABCDEF" for c in rgb):
                rgb = default_hex
            color_index = color_to_index.get(rgb, 0)
            
            obj_attrib = {"id": str(object_id), "type": "model"}
            if unique_colors:
                obj_attrib["pid"] = "1"
                obj_attrib["pindex"] = str(color_index)
            obj = ET.SubElement(resources, "object", **obj_attrib)
            mesh = ET.SubElement(obj, "mesh")
            vertices_elem = ET.SubElement(mesh, "vertices")
            triangles_elem = ET.SubElement(mesh, "triangles")
            for vertex in mesh_data['vertices']:
                ET.SubElement(vertices_elem, "vertex",
                    x=f"{vertex[0]:.6f}", y=f"{vertex[1]:.6f}", z=f"{vertex[2]:.6f}")
            for triangle in mesh_data['triangles']:
                ET.SubElement(triangles_elem, "triangle",
                    v1=str(triangle[0]), v2=str(triangle[1]), v3=str(triangle[2]))
            
            # 3MF transform: 3x4 matrix column-major (m00 m10 m20 m01 m11 m21 m02 m12 m22 m03 m13 m23)
            tx, ty, tz = translation[0], translation[1], translation[2]
            matrix = f"1 0 0 0 1 0 0 0 1 {tx:.6f} {ty:.6f} {tz:.6f}"
            ET.SubElement(build, "item", objectid=str(object_id), transform=matrix)
        
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")
        tree.write(base_path / "3D" / "3dmodel.model", encoding="utf-8", xml_declaration=True)
