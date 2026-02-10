"""LDView CLI wrapper for converting LDraw parts to STL."""
import hashlib
import subprocess
import logging
from pathlib import Path
from typing import Optional, List
from backend.config import settings
import struct

logger = logging.getLogger(__name__)

# Which LDView settings affect STL export vs preview (PNG snapshot).
# Format: (config_attr_suffix, LDViewName, affects_stl, affects_preview)
_LDVIEW_SETTINGS = [
    ("allow_primitive_substitution", "AllowPrimitiveSubstitution", True, True),
    ("use_quality_studs", "UseQualityStuds", True, True),
    ("curve_quality", "CurveQuality", True, True),
    ("seams", "Seams", True, False),
    ("seam_width", "SeamWidth", True, False),
    ("bfc", "BFC", True, True),
    ("bounding_boxes_only", "BoundingBoxesOnly", True, True),
    ("show_highlight_lines", "ShowHighlightLines", False, True),
    ("polygon_offset", "PolygonOffset", False, True),
    ("edge_thickness", "EdgeThickness", False, True),
    ("line_smoothing", "LineSmoothing", False, True),
    ("black_highlights", "BlackHighlights", False, True),
    ("conditional_highlights", "ConditionalHighlights", False, True),
    ("wireframe", "Wireframe", False, True),
    ("wireframe_thickness", "WireframeThickness", False, True),
    ("remove_hidden_lines", "RemoveHiddenLines", False, True),
    ("texture_studs", "TextureStuds", False, True),
    ("texmaps", "Texmaps", False, True),
    ("hi_res_primitives", "HiResPrimitives", True, True),
    ("texture_filter_type", "TextureFilterType", False, True),
    ("aniso_level", "AnisoLevel", False, True),
    ("texture_offset_factor", "TextureOffsetFactor", False, True),
    ("lighting", "Lighting", False, True),
    ("use_quality_lighting", "UseQualityLighting", False, True),
    ("use_specular", "UseSpecular", False, True),
    ("subdued_lighting", "SubduedLighting", False, True),
    ("perform_smoothing", "PerformSmoothing", True, True),
    ("use_flat_shading", "UseFlatShading", False, True),
    ("antialias", "Antialias", False, True),
    ("process_ldconfig", "ProcessLDConfig", True, True),
    ("sort_transparent", "SortTransparent", False, True),
    ("use_stipple", "UseStipple", False, True),
    ("memory_usage", "MemoryUsage", True, True),
]


def _ldview_quality_args(for_stl: bool) -> List[str]:
    """Build -SettingName=value args from current settings. for_stl=True for STL export, False for snapshot."""
    args = []
    for suffix, name, affects_stl, affects_preview in _LDVIEW_SETTINGS:
        if for_stl and not affects_stl:
            continue
        if not for_stl and not affects_preview:
            continue
        attr = getattr(settings, f"ldview_{suffix}", None)
        if attr is None:
            continue
        if isinstance(attr, bool):
            args.append(f"-{name}={1 if attr else 0}")
        elif isinstance(attr, float):
            args.append(f"-{name}={attr}")
        else:
            args.append(f"-{name}={attr}")
    return args


def get_ldview_quality_key() -> str:
    """Deterministic short key from all LDView quality settings for cache (STL and preview)."""
    parts = []
    for suffix, name, _stl, _preview in _LDVIEW_SETTINGS:
        attr = getattr(settings, f"ldview_{suffix}", None)
        if attr is None:
            continue
        if isinstance(attr, bool):
            parts.append(f"{name}={1 if attr else 0}")
        elif isinstance(attr, float):
            parts.append(f"{name}={attr}")
        else:
            parts.append(f"{name}={attr}")
    canonical = "_".join(parts)
    return hashlib.md5(canonical.encode()).hexdigest()[:16]


class LDViewConverter:
    """Convert LDraw parts to STL using LDView CLI tool."""
    
    def __init__(self, ldraw_library_path: Optional[Path] = None):
        self.ldraw_library_path = ldraw_library_path or settings.ldraw_library_path
        self.parts_dir = self.ldraw_library_path / "parts"
    
    def convert_to_stl(self, ldraw_id: str, output_path: Path, scale_factor: float = 10.0) -> bool:
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
            cmd.extend(_ldview_quality_args(for_stl=True))

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
            
            # Scale the STL: LDView exports in cm; default scale 10 converts to mm (calibration: 3034, 3404).
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
    
    def export_snapshot(self, ldraw_id: str, output_path: Path, width: int = 256, height: int = 256) -> bool:
        """Export a PNG snapshot of an LDraw part for preview. Cached by caller.
        
        Args:
            ldraw_id: LDraw part ID (e.g. "3005")
            output_path: Where to save the PNG file
            width: Image width in pixels
            height: Image height in pixels
        Returns:
            True if successful
        """
        try:
            dat_file = self._find_part_file(ldraw_id)
            if not dat_file:
                logger.warning(f"LDraw part file not found for preview: {ldraw_id}")
                return False
            output_path.parent.mkdir(parents=True, exist_ok=True)
            cmd = [
                'ldview',
                str(dat_file),
                f'-SaveSnapshot={output_path}',
                f'-SaveWidth={width}',
                f'-SaveHeight={height}',
                '-SaveZoomToFit=1',
                '-AutoCrop=1',
                '-LDrawDir=' + str(self.ldraw_library_path)
            ]
            cmd.extend(_ldview_quality_args(for_stl=False))
            env = {'LDRAWDIR': str(self.ldraw_library_path), 'PATH': '/usr/local/bin:/usr/bin:/bin'}
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, env=env)
            if result.returncode != 0:
                logger.warning(f"LDView snapshot failed for {ldraw_id}: {result.stderr}")
                return False
            if not output_path.exists() or output_path.stat().st_size == 0:
                return False
            return True
        except subprocess.TimeoutExpired:
            logger.warning(f"LDView snapshot timeout for {ldraw_id}")
            return False
        except Exception as e:
            logger.error(f"Error exporting snapshot for {ldraw_id}: {e}")
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
