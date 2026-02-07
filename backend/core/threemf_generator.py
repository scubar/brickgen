"""3MF file generation with bin packing for 3D printing."""
import logging
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Tuple, Optional, Dict
import re

logger = logging.getLogger(__name__)


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
        parts: List[Tuple[Path, str, int]],  # (stl_path, ldraw_id, quantity)
        plate_width: int,
        plate_depth: int,
        output_path: Path
    ) -> bool:
        """Generate 3MF file with parts arranged on build plate.
        
        Args:
            parts: List of (stl_path, ldraw_id, quantity) tuples
            plate_width: Build plate width in mm
            plate_depth: Build plate depth in mm
            output_path: Where to save the 3MF file
        
        Returns:
            True if successful, False if parts don't fit or error occurs
        """
        try:
            # Parse all STL files and get bounding boxes
            part_meshes = []
            for stl_path, ldraw_id, quantity in parts:
                mesh_data = self._parse_stl(stl_path)
                if mesh_data:
                    bbox = self._compute_bounding_box(mesh_data['vertices'])
                    part_meshes.append({
                        'mesh_data': mesh_data,
                        'ldraw_id': ldraw_id,
                        'bbox': bbox,
                        'quantity': quantity
                    })
            
            if not part_meshes:
                logger.error("No valid meshes to pack")
                return False
            
            # Perform bin packing
            placements = self._pack_parts(part_meshes, plate_width, plate_depth)
            
            if not placements:
                logger.error("Parts do not fit on build plate")
                return False
            
            # Generate 3MF file
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
    
    def _pack_parts(self, part_meshes: List[Dict], plate_width: int, plate_depth: int) -> Optional[List[Dict]]:
        """Pack parts onto build plate using shelf algorithm.
        
        Args:
            part_meshes: List of part mesh dictionaries
            plate_width: Build plate width in mm
            plate_depth: Build plate depth in mm
        
        Returns:
            List of placements with mesh_data and translation, or None if doesn't fit
        """
        placements = []
        
        # Create instances for all quantities
        instances = []
        for part in part_meshes:
            for i in range(part['quantity']):
                instances.append({
                    'mesh_data': part['mesh_data'],
                    'ldraw_id': part['ldraw_id'],
                    'bbox': part['bbox'],
                    'instance_num': i + 1
                })
        
        # Sort by footprint area (largest first for better packing)
        instances.sort(key=lambda x: x['bbox']['size'][0] * x['bbox']['size'][1], reverse=True)
        
        # Shelf packing algorithm
        shelves = []  # List of {'y': y_pos, 'height': height, 'x': current_x, 'width_remaining': width}
        current_y = 0
        
        for instance in instances:
            bbox = instance['bbox']
            width = bbox['size'][0]
            depth = bbox['size'][1]
            height = bbox['size'][2]
            
            # Add spacing
            width_with_spacing = width + self.part_spacing
            depth_with_spacing = depth + self.part_spacing
            
            # Try to fit in existing shelves
            placed = False
            for shelf in shelves:
                if shelf['width_remaining'] >= width_with_spacing and current_y + depth_with_spacing <= plate_depth:
                    # Place on this shelf
                    x_pos = shelf['x']
                    y_pos = shelf['y']
                    z_pos = 0  # On build plate
                    
                    # Calculate translation (move from bbox center to position)
                    translation = [
                        x_pos + width / 2 - bbox['center'][0],
                        y_pos + depth / 2 - bbox['center'][1],
                        -bbox['min'][2]  # Place bottom on Z=0
                    ]
                    
                    placements.append({
                        'mesh_data': instance['mesh_data'],
                        'translation': translation,
                        'ldraw_id': instance['ldraw_id'],
                        'instance_num': instance['instance_num']
                    })
                    
                    # Update shelf
                    shelf['x'] += width_with_spacing
                    shelf['width_remaining'] -= width_with_spacing
                    shelf['height'] = max(shelf['height'], height)
                    placed = True
                    break
            
            if not placed:
                # Create new shelf
                if current_y + depth_with_spacing > plate_depth:
                    # Doesn't fit on plate
                    logger.warning(f"Parts don't fit: plate_depth={plate_depth}, needed={current_y + depth_with_spacing}")
                    return None
                
                # Start new shelf
                x_pos = 0
                y_pos = current_y
                z_pos = 0
                
                translation = [
                    x_pos + width / 2 - bbox['center'][0],
                    y_pos + depth / 2 - bbox['center'][1],
                    -bbox['min'][2]
                ]
                
                placements.append({
                    'mesh_data': instance['mesh_data'],
                    'translation': translation,
                    'ldraw_id': instance['ldraw_id'],
                    'instance_num': instance['instance_num']
                })
                
                shelves.append({
                    'y': current_y,
                    'height': height,
                    'x': width_with_spacing,
                    'width_remaining': plate_width - width_with_spacing
                })
                
                # Update current_y for next shelf
                if shelves:
                    current_y += max(shelf['height'] for shelf in shelves) + self.part_spacing
        
        logger.info(f"Packed {len(placements)} parts onto build plate")
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
                    for root, dirs, files in tmppath.walk():
                        for file in files:
                            file_path = root / file
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
        """Create 3D/3dmodel.model file with meshes and build items."""
        model_ns = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
        
        root = ET.Element("model", unit="millimeter", xmlns=model_ns)
        resources = ET.SubElement(root, "resources")
        build = ET.SubElement(root, "build")
        
        # Add each mesh as a resource and build item
        for idx, placement in enumerate(placements):
            object_id = idx + 1
            mesh_data = placement['mesh_data']
            translation = placement['translation']
            
            # Create object resource with mesh
            obj = ET.SubElement(resources, "object", id=str(object_id), type="model")
            mesh = ET.SubElement(obj, "mesh")
            vertices_elem = ET.SubElement(mesh, "vertices")
            triangles_elem = ET.SubElement(mesh, "triangles")
            
            # Add vertices
            for vertex in mesh_data['vertices']:
                ET.SubElement(vertices_elem, "vertex",
                            x=f"{vertex[0]:.6f}",
                            y=f"{vertex[1]:.6f}",
                            z=f"{vertex[2]:.6f}")
            
            # Add triangles
            for triangle in mesh_data['triangles']:
                ET.SubElement(triangles_elem, "triangle",
                            v1=str(triangle[0]),
                            v2=str(triangle[1]),
                            v3=str(triangle[2]))
            
            # Add to build with transformation
            transform = f"{translation[0]:.6f} {translation[1]:.6f} {translation[2]:.6f}"
            ET.SubElement(build, "item", objectid=str(object_id), transform=f"translate({transform})")
        
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")
        tree.write(base_path / "3D" / "3dmodel.model", encoding="utf-8", xml_declaration=True)
