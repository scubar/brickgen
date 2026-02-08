"""STL orientation optimization for 3D printing."""
import logging
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional
import re

logger = logging.getLogger(__name__)


class STLOrienter:
    """Apply absolute rotation (X, Y, Z degrees) to STL for 3D printing."""

    def __init__(self, strategy: str = "original"):
        """Initialize orienter. strategy kept for backward compat but unused; use apply_absolute_rotation."""
        self.strategy = strategy

    def apply_absolute_rotation(self, stl_path: Path, x_deg: float, y_deg: float, z_deg: float) -> bool:
        """Apply rotation by Euler angles (X, Y, Z) in degrees. Order: X then Y then Z."""
        if x_deg == 0 and y_deg == 0 and z_deg == 0:
            return True
        rx = self._rotation_matrix_x(x_deg)
        ry = self._rotation_matrix_y(y_deg)
        rz = self._rotation_matrix_z(z_deg)
        # Compose: apply Z then Y then X (same as typical Euler ZYX)
        rotation_matrix = rz @ ry @ rx
        return self._apply_transformation(stl_path, rotation_matrix)

    def optimize_orientation(self, stl_path: Path) -> bool:
        """
        Analyze STL and rotate to optimal print orientation.
        
        Algorithm:
        1. Parse ASCII STL to extract vertices and normals
        2. Test 6 primary orientations (+X, -X, +Y, -Y, +Z, -Z facing down)
        3. For each orientation, calculate:
           - Overhang area (faces with normals pointing downward)
           - Contact area with build plate (lowest Z faces)
        4. Score = contact_area - overhang_area (maximize)
        5. Apply best transformation
        
        Args:
            stl_path: Path to ASCII STL file
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Skip if strategy is "original"
            if self.strategy == "original":
                logger.info("Original orientation strategy - no rotation applied")
                return True
            
            # Parse STL file
            vertices, normals = self._parse_stl(stl_path)
            
            # Check if parsing was successful
            if len(vertices) == 0 or len(normals) == 0:
                logger.warning(f"Failed to parse STL file: {stl_path}")
                return False
            
            # Test all 6 orientations
            best_orientation = None
            best_score = float('-inf')
            
            orientations = [
                ('original', np.eye(3)),  # No rotation
                ('x_down', self._rotation_matrix_x(90)),
                ('x_up', self._rotation_matrix_x(-90)),
                ('y_down', self._rotation_matrix_y(90)),
                ('y_up', self._rotation_matrix_y(-90)),
                ('z_flip', self._rotation_matrix_z(180))
            ]
            
            for name, rotation_matrix in orientations:
                if self.strategy == "studs_up":
                    score = self._score_studs_up_orientation(vertices, normals, rotation_matrix)
                elif self.strategy == "flat":
                    score = self._score_flat_orientation(vertices, rotation_matrix)
                else:  # minimize_supports
                    score = self._score_support_orientation(vertices, normals, rotation_matrix)
                
                # Log detailed info for debugging
                rotated_verts = vertices @ rotation_matrix.T
                min_c = np.min(rotated_verts, axis=0)
                max_c = np.max(rotated_verts, axis=0)
                dims = max_c - min_c
                logger.debug(f"  {name}: score={score:.2f}, dims=[W:{dims[0]:.1f}, D:{dims[1]:.1f}, H:{dims[2]:.1f}]")
                
                if score > best_score:
                    best_score = score
                    best_orientation = (name, rotation_matrix)
            
            # Apply best orientation
            if best_orientation and best_orientation[0] != 'original':
                logger.info(f"Best orientation: {best_orientation[0]} (score: {best_score:.2f}, strategy: {self.strategy})")
                return self._apply_transformation(stl_path, best_orientation[1])
            else:
                logger.info(f"Original orientation is optimal (score: {best_score:.2f}, strategy: {self.strategy})")
                return True
            
        except Exception as e:
            logger.error(f"Error optimizing STL orientation: {e}")
            return False
    
    def _parse_stl(self, stl_path: Path) -> Tuple[np.ndarray, np.ndarray]:
        """Parse ASCII STL file to extract vertices and face normals.
        
        Returns:
            Tuple of (vertices array Nx3, normals array Mx3)
        """
        vertices = []
        normals = []
        
        try:
            with open(stl_path, 'r') as f:
                current_normal = None
                for line in f:
                    line = line.strip()
                    
                    if line.startswith('facet normal'):
                        # Extract normal vector
                        parts = line.split()
                        if len(parts) >= 5:
                            normal = [float(parts[2]), float(parts[3]), float(parts[4])]
                            current_normal = normal
                    
                    elif line.startswith('vertex'):
                        # Extract vertex coordinates
                        parts = line.split()
                        if len(parts) >= 4:
                            vertex = [float(parts[1]), float(parts[2]), float(parts[3])]
                            vertices.append(vertex)
                    
                    elif line.startswith('endfacet') and current_normal:
                        # Store normal for this face
                        normals.append(current_normal)
                        current_normal = None
            
            return np.array(vertices), np.array(normals)
            
        except Exception as e:
            logger.error(f"Error parsing STL: {e}")
            return np.array([]), np.array([])
    
    def _score_studs_up_orientation(self, vertices: np.ndarray, normals: np.ndarray,
                                    rotation_matrix: np.ndarray) -> float:
        """Score orientation for LEGO parts: solid studs up, hollow recess down.
        
        For LEGO bricks:
        - TOP: Solid cylindrical studs pointing UP (+Z) - more complex geometry
        - BOTTOM: Hollow recess facing DOWN (-Z) on build plate - simpler/hollow
        - SIDES: Vertical walls perpendicular to build plate
        
        This provides:
        - Best bed adhesion (hollow bottom sits flat)
        - No support material needed
        - Studs print cleanly pointing upward
        
        Args:
            vertices: Original vertex array
            normals: Original normal vectors
            rotation_matrix: 3x3 rotation matrix to apply
        
        Returns:
            Score (higher is better)
        """
        # Rotate vertices and normals
        rotated_vertices = vertices @ rotation_matrix.T
        rotated_normals = normals @ rotation_matrix.T
        
        # Compute bounding box
        min_coords = np.min(rotated_vertices, axis=0)
        max_coords = np.max(rotated_vertices, axis=0)
        dimensions = max_coords - min_coords  # [width, depth, height]
        
        width, depth, height = dimensions[0], dimensions[1], dimensions[2]
        contact_area = width * depth
        
        # Analyze normals to understand surface complexity
        # Studs (solid cylinders) create MORE surface area with upward normals
        # Hollow recess creates LESS surface area with downward normals
        
        up_normals = np.sum(rotated_normals[:, 2] > 0.7)  # Pointing up (+Z)
        down_normals = np.sum(rotated_normals[:, 2] < -0.7)  # Pointing down (-Z)
        
        # KEY INSIGHT: For LEGO bricks with studs:
        # - Studs create MORE upward-facing surface area (cylinders sticking up)
        # - Hollow bottom creates LESS downward-facing surface area (it's hollow/recessed)
        # - We want MORE up normals (studs up) and FEWER down normals (hollow down)
        
        # 1. Maximize contact area (large flat base)
        contact_score = contact_area * 1000.0
        
        # 2. Minimize height (brick lying flat, not standing on edge)
        height_score = -height * 100.0
        
        # 3. Height should be the smallest dimension (brick thickness vertical)
        sorted_dims = sorted([width, depth, height])
        if abs(height - sorted_dims[0]) < 0.01:  # Height is smallest
            dimension_bonus = 10000.0
        else:
            dimension_bonus = -5000.0 * abs(height - sorted_dims[0])
        
        # 4. CRITICAL: Prefer MORE up normals (studs on top) and FEWER down normals (hollow bottom)
        # High ratio = complex top (studs), simple bottom (recess) = CORRECT orientation
        if down_normals > 0:
            stud_ratio = up_normals / down_normals
        else:
            stud_ratio = up_normals  # No down normals = very hollow bottom (excellent!)
        
        stud_orientation_score = stud_ratio * 500.0
        
        # 5. Bonus for high up-normal count (lots of stud geometry on top)
        stud_count_bonus = up_normals * 5.0
        
        # 6. Flatness ratio
        if height > 0.001:
            flatness_score = (contact_area / height) * 100.0
        else:
            flatness_score = 100000.0
        
        # Combine all scores
        total_score = (contact_score + height_score + dimension_bonus + 
                      stud_orientation_score + stud_count_bonus + flatness_score)
        
        return total_score
    
    def _score_flat_orientation(self, vertices: np.ndarray, rotation_matrix: np.ndarray) -> float:
        """Score orientation by how flat/stable it lays (smallest dimension vertical).
        
        For LEGO bricks, we want the large flat face (top/bottom) on the build plate,
        not the thin side edge. This means the smallest dimension should be vertical (Z).
        
        Args:
            vertices: Original vertex array
            rotation_matrix: 3x3 rotation matrix to apply
        
        Returns:
            Score (higher is better)
        """
        # Rotate vertices
        rotated_vertices = vertices @ rotation_matrix.T
        
        # Compute bounding box
        min_coords = np.min(rotated_vertices, axis=0)
        max_coords = np.max(rotated_vertices, axis=0)
        dimensions = max_coords - min_coords  # [width (X), depth (Y), height (Z)]
        
        width, depth, height = dimensions[0], dimensions[1], dimensions[2]
        
        # For flat orientation, we want:
        # 1. The SMALLEST original dimension to be vertical (Z/height)
        # 2. The two LARGEST dimensions to be horizontal (X/Y for contact area)
        # 3. Maximum contact area (width * depth)
        
        # Calculate contact area
        contact_area = width * depth
        
        # Heavily penalize if height is NOT the smallest dimension
        # (This ensures thin parts lay flat, not on edge)
        sorted_dims = sorted([width, depth, height])
        smallest_dim = sorted_dims[0]
        
        # Big penalty if height is not the smallest dimension
        if height != smallest_dim:
            dimension_penalty = 10000.0 * (height - smallest_dim)
        else:
            dimension_penalty = 0.0  # Height IS smallest - this is what we want!
        
        # Reward large contact area
        contact_area_score = contact_area * 100.0
        
        # Small bonus for low aspect ratio (prefer square base over long thin)
        if height > 0:
            flatness_ratio = contact_area / height
        else:
            flatness_ratio = 10000.0
        
        # Final score: maximize contact area, minimize height, ensure height is smallest
        score = contact_area_score + flatness_ratio - dimension_penalty
        
        return score
    
    def _score_support_orientation(self, vertices: np.ndarray, normals: np.ndarray, 
                          rotation_matrix: np.ndarray) -> float:
        """Calculate print-ability score for a given orientation.
        
        Args:
            vertices: Original vertex array
            normals: Original normal vectors
            rotation_matrix: 3x3 rotation matrix to apply
        
        Returns:
            Score (higher is better)
        """
        # Check if arrays are empty
        if len(vertices) == 0 or len(normals) == 0:
            return float('-inf')
        
        # Rotate vertices and normals
        rotated_vertices = vertices @ rotation_matrix.T
        rotated_normals = normals @ rotation_matrix.T
        
        # Find min Z (build plate level)
        min_z = np.min(rotated_vertices[:, 2])
        
        # Calculate contact area (faces near build plate pointing down)
        contact_score = 0.0
        num_faces = len(rotated_normals)
        
        for face_idx in range(num_faces):
            # Get the 3 vertices for this face
            vert_start_idx = face_idx * 3
            if vert_start_idx + 2 >= len(rotated_vertices):
                break
            
            normal = rotated_normals[face_idx]
            face_verts = rotated_vertices[vert_start_idx:vert_start_idx+3]
            
            # Check if face is near build plate (within 1mm)
            avg_z = np.mean(face_verts[:, 2])
            if avg_z - min_z < 1.0:  # Near build plate
                # Check if normal points down (good contact)
                if normal[2] < -0.5:  # Strong downward component
                    contact_score += abs(normal[2])
        
        # Calculate overhang penalty (faces pointing down, not at base)
        overhang_penalty = 0.0
        for face_idx in range(num_faces):
            vert_start_idx = face_idx * 3
            if vert_start_idx + 2 >= len(rotated_vertices):
                break
            
            normal = rotated_normals[face_idx]
            face_verts = rotated_vertices[vert_start_idx:vert_start_idx+3]
            
            avg_z = np.mean(face_verts[:, 2])
            # If not at base and normal points down -> overhang
            if avg_z - min_z >= 1.0 and normal[2] < -0.3:
                overhang_penalty += abs(normal[2])
        
        # Final score: maximize contact, minimize overhang
        score = contact_score - overhang_penalty
        
        return score
    
    def _apply_transformation(self, stl_path: Path, rotation_matrix: np.ndarray) -> bool:
        """Apply rotation transformation to STL file.
        
        Args:
            stl_path: Path to STL file (will be modified in-place)
            rotation_matrix: 3x3 rotation matrix
        
        Returns:
            True if successful
        """
        try:
            # Read original file
            with open(stl_path, 'r') as f:
                lines = f.readlines()
            
            # Process lines and rotate vertices
            transformed_lines = []
            for line in lines:
                stripped = line.strip()
                
                if 'vertex' in stripped and stripped.startswith('vertex'):
                    parts = stripped.split()
                    if len(parts) == 4:
                        # Extract and rotate vertex
                        vertex = np.array([float(parts[1]), float(parts[2]), float(parts[3])])
                        rotated = vertex @ rotation_matrix.T
                        transformed_line = f"      vertex {rotated[0]:.6f} {rotated[1]:.6f} {rotated[2]:.6f}\n"
                        transformed_lines.append(transformed_line)
                    else:
                        transformed_lines.append(line)
                
                elif 'facet normal' in stripped:
                    parts = stripped.split()
                    if len(parts) >= 5 and parts[0] == 'facet' and parts[1] == 'normal':
                        # Rotate normal vector
                        normal = np.array([float(parts[2]), float(parts[3]), float(parts[4])])
                        rotated_normal = normal @ rotation_matrix.T
                        # Normalize
                        norm = np.linalg.norm(rotated_normal)
                        if norm > 1e-10:
                            rotated_normal = rotated_normal / norm
                        transformed_line = f"  facet normal {rotated_normal[0]:.6f} {rotated_normal[1]:.6f} {rotated_normal[2]:.6f}\n"
                        transformed_lines.append(transformed_line)
                    else:
                        transformed_lines.append(line)
                else:
                    transformed_lines.append(line)
            
            # Write back to file
            with open(stl_path, 'w') as f:
                f.writelines(transformed_lines)
            
            logger.info(f"Applied transformation to {stl_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error applying transformation: {e}")
            return False
    
    @staticmethod
    def _rotation_matrix_x(degrees: float) -> np.ndarray:
        """Create rotation matrix around X axis."""
        rad = np.radians(degrees)
        return np.array([
            [1, 0, 0],
            [0, np.cos(rad), -np.sin(rad)],
            [0, np.sin(rad), np.cos(rad)]
        ])
    
    @staticmethod
    def _rotation_matrix_y(degrees: float) -> np.ndarray:
        """Create rotation matrix around Y axis."""
        rad = np.radians(degrees)
        return np.array([
            [np.cos(rad), 0, np.sin(rad)],
            [0, 1, 0],
            [-np.sin(rad), 0, np.cos(rad)]
        ])
    
    @staticmethod
    def _rotation_matrix_z(degrees: float) -> np.ndarray:
        """Create rotation matrix around Z axis."""
        rad = np.radians(degrees)
        return np.array([
            [np.cos(rad), -np.sin(rad), 0],
            [np.sin(rad), np.cos(rad), 0],
            [0, 0, 1]
        ])
