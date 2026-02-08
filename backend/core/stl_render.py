"""Render STL files to PNG for part preview with rotation."""
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_FACE_COLOR = "lightgray"


def render_stl_to_png(
    stl_path: Path,
    output_path: Path,
    size: int = 256,
    face_color: Optional[str] = None,
) -> bool:
    """Render an STL file to a PNG image using matplotlib.

    Args:
        stl_path: Path to the STL file (ASCII or binary).
        output_path: Path for the output PNG.
        size: Width and height of the image in pixels.
        face_color: Optional hex color for faces (e.g. '#FF5500'). Default light gray.

    Returns:
        True if successful, False otherwise.
    """
    try:
        from stl import mesh as stl_mesh
        from mpl_toolkits.mplot3d import art3d
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError as e:
        logger.warning(f"STL render dependencies missing: {e}")
        return False

    try:
        mesh = stl_mesh.Mesh.from_file(str(stl_path))
        output_path.parent.mkdir(parents=True, exist_ok=True)

        fig = plt.figure(figsize=(size / 100, size / 100), dpi=100)
        ax = fig.add_subplot(111, projection="3d")

        fc = face_color if face_color else _DEFAULT_FACE_COLOR
        ax.add_collection3d(art3d.Poly3DCollection(
            mesh.vectors,
            facecolors=fc,
            edgecolors="gray",
            linewidths=0.1,
            alpha=0.9,
        ))

        scale = mesh.points.flatten()
        ax.auto_scale_xyz(scale, scale, scale)
        ax.set_axis_off()
        ax.view_init(elev=20, azim=45)

        plt.tight_layout(pad=0)
        plt.savefig(
            str(output_path),
            dpi=100,
            bbox_inches="tight",
            pad_inches=0.05,
            format="png",
        )
        plt.close(fig)
        return output_path.exists() and output_path.stat().st_size > 0
    except Exception as e:
        logger.warning(f"Failed to render STL to PNG: {e}")
        return False
