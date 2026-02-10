"""STL orientation optimization for 3D printing."""
import logging
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)


class STLOrienter:
    """Apply absolute rotation (X, Y, Z degrees) to STL for 3D printing."""

    def __init__(self):
        """Initialize orienter."""
        pass

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
