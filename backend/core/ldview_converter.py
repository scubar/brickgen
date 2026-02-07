"""LDView CLI wrapper for converting LDraw parts to STL."""
import subprocess
import logging
from pathlib import Path
from typing import Optional
from backend.config import settings
import struct

logger = logging.getLogger(__name__)


class LDViewConverter:
    """Convert LDraw parts to STL using LDView CLI tool."""
    
    def __init__(self, ldraw_library_path: Optional[Path] = None):
        self.ldraw_library_path = ldraw_library_path or settings.ldraw_library_path
        self.parts_dir = self.ldraw_library_path / "parts"
    
    def convert_to_stl(self, ldraw_id: str, output_path: Path, scale_factor: float = 16.67) -> bool:
        """Convert LDraw part to STL using LDView.
        
        Args:
            ldraw_id: LDraw part number (e.g., "3005", "3001")
            output_path: Where to save the STL file
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Find the .dat file
            dat_file = self._find_part_file(ldraw_id)
            if not dat_file:
                logger.warning(f"LDraw part file not found: {ldraw_id}")
                return False
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Build LDView command
            # OSMesa version doesn't need xvfb (offscreen rendering)
            temp_output = output_path.with_suffix('.temp.stl')
            
            cmd = [
                'ldview',
                str(dat_file),
                f'-ExportFile={temp_output}',
                '-ExportSuffix=.stl',
                '-SaveSnapshot=0',  # Don't save snapshots
                '-SaveActualSize=0',  # Use default size
                '-AutoCrop=0',  # Don't auto-crop
                '-LDrawDir=' + str(self.ldraw_library_path)  # Explicit LDraw path
            ]
            
            # Set environment variables for LDView
            env = {
                'LDRAWDIR': str(self.ldraw_library_path),
                'PATH': '/usr/local/bin:/usr/bin:/bin'
            }
            
            # Run LDView
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,  # 30 second timeout per part
                env=env
            )
            
            if result.returncode != 0:
                logger.error(f"LDView conversion failed for {ldraw_id}: {result.stderr}")
                return False
            
            # Verify output file exists and has content
            if not temp_output.exists():
                logger.error(f"LDView did not create output file for {ldraw_id}")
                return False
            
            if temp_output.stat().st_size == 0:
                logger.error(f"LDView created empty file for {ldraw_id}")
                temp_output.unlink()
                return False
            
            # Scale the STL file (LDraw units are not standard - need to scale)
            # Default 16.67x makes a 1x1 brick (8mm) come out correctly in mm
            if not self._scale_stl_file(temp_output, output_path, scale_factor=scale_factor):
                logger.error(f"Failed to scale STL for {ldraw_id}")
                temp_output.unlink()
                return False
            
            # Clean up temp file
            temp_output.unlink()
            
            logger.info(f"Successfully converted and scaled {ldraw_id} to STL ({output_path.stat().st_size} bytes)")
            return True
            
        except subprocess.TimeoutExpired:
            logger.error(f"LDView conversion timeout for {ldraw_id}")
            return False
        except Exception as e:
            logger.error(f"Error converting {ldraw_id} to STL: {e}")
            return False
    
    def _find_part_file(self, ldraw_id: str) -> Optional[Path]:
        """Find LDraw .dat file for a part number.
        
        Args:
            ldraw_id: LDraw part ID (e.g., "3005")
        
        Returns:
            Path to .dat file or None
        """
        # Clean the ID
        clean_id = ldraw_id.replace(".dat", "").strip().lower()
        
        # Try common naming patterns
        possible_names = [
            f"{clean_id}.dat",
            f"{clean_id}a.dat",
            f"{clean_id}b.dat",
            f"{clean_id}c.dat",
            f"{clean_id}p01.dat",
        ]
        
        for name in possible_names:
            part_path = self.parts_dir / name
            if part_path.exists():
                return part_path
        
        return None
    
    def _scale_stl_file(self, input_path: Path, output_path: Path, scale_factor: float) -> bool:
        """Scale an STL file by reading and rewriting with scaled coordinates.
        
        Args:
            input_path: Input STL file
            output_path: Output STL file
            scale_factor: Multiplication factor for all coordinates
        
        Returns:
            True if successful
        """
        try:
            # Read ASCII STL file
            with open(input_path, 'r') as f:
                lines = f.readlines()
            
            # Scale vertex lines
            scaled_lines = []
            for line in lines:
                if 'vertex' in line:
                    parts = line.strip().split()
                    if len(parts) == 4 and parts[0] == 'vertex':
                        x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                        scaled_line = f"      vertex {x*scale_factor:.6f} {y*scale_factor:.6f} {z*scale_factor:.6f}\n"
                        scaled_lines.append(scaled_line)
                    else:
                        scaled_lines.append(line)
                else:
                    scaled_lines.append(line)
            
            # Write scaled STL
            with open(output_path, 'w') as f:
                f.writelines(scaled_lines)
            
            return True
            
        except Exception as e:
            logger.error(f"Error scaling STL file: {e}")
            return False
    
    def test_ldview_available(self) -> bool:
        """Test if LDView is available and working.
        
        Returns:
            True if LDView can be executed
        """
        try:
            result = subprocess.run(
                ['ldview', '--help'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0 or result.returncode == 1  # Some versions return 1 for help
        except Exception as e:
            logger.error(f"LDView not available: {e}")
            return False
