"""LDView quality columns on app_settings; quality_key on stl_cache.

Revision ID: 002_ldview
Revises: 001_initial
Create Date: 2025-02-09

"""
from typing import Sequence, Union
import hashlib

from alembic import op
import sqlalchemy as sa


revision: str = "002_ldview"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _default_quality_key() -> str:
    """Canonical string for default LDView settings; hash matches get_ldview_quality_key() at defaults."""
    parts = [
        "AllowPrimitiveSubstitution=1", "UseQualityStuds=1", "CurveQuality=2", "Seams=0", "SeamWidth=0",
        "BFC=1", "BoundingBoxesOnly=0", "ShowHighlightLines=0", "PolygonOffset=1", "EdgeThickness=0.0",
        "LineSmoothing=0", "BlackHighlights=0", "ConditionalHighlights=0", "Wireframe=0",
        "WireframeThickness=0.0", "RemoveHiddenLines=0", "TextureStuds=1", "Texmaps=1", "HiResPrimitives=0",
        "TextureFilterType=9987", "AnisoLevel=0", "TextureOffsetFactor=5.0", "Lighting=1",
        "UseQualityLighting=0", "UseSpecular=1", "SubduedLighting=0", "PerformSmoothing=1",
        "UseFlatShading=0", "Antialias=0", "ProcessLDConfig=1", "SortTransparent=1", "UseStipple=0",
        "MemoryUsage=2",
    ]
    canonical = "_".join(parts)
    return hashlib.md5(canonical.encode()).hexdigest()[:16]


def _app_settings_columns():
    """Yield (name, column) for each LDView column to add to app_settings."""
    return [
        ("ldview_allow_primitive_substitution", sa.Column("ldview_allow_primitive_substitution", sa.Boolean(), nullable=True)),
        ("ldview_use_quality_studs", sa.Column("ldview_use_quality_studs", sa.Boolean(), nullable=True)),
        ("ldview_curve_quality", sa.Column("ldview_curve_quality", sa.Integer(), nullable=True)),
        ("ldview_seams", sa.Column("ldview_seams", sa.Boolean(), nullable=True)),
        ("ldview_seam_width", sa.Column("ldview_seam_width", sa.Integer(), nullable=True)),
        ("ldview_bfc", sa.Column("ldview_bfc", sa.Boolean(), nullable=True)),
        ("ldview_bounding_boxes_only", sa.Column("ldview_bounding_boxes_only", sa.Boolean(), nullable=True)),
        ("ldview_show_highlight_lines", sa.Column("ldview_show_highlight_lines", sa.Boolean(), nullable=True)),
        ("ldview_polygon_offset", sa.Column("ldview_polygon_offset", sa.Boolean(), nullable=True)),
        ("ldview_edge_thickness", sa.Column("ldview_edge_thickness", sa.Float(), nullable=True)),
        ("ldview_line_smoothing", sa.Column("ldview_line_smoothing", sa.Boolean(), nullable=True)),
        ("ldview_black_highlights", sa.Column("ldview_black_highlights", sa.Boolean(), nullable=True)),
        ("ldview_conditional_highlights", sa.Column("ldview_conditional_highlights", sa.Boolean(), nullable=True)),
        ("ldview_wireframe", sa.Column("ldview_wireframe", sa.Boolean(), nullable=True)),
        ("ldview_wireframe_thickness", sa.Column("ldview_wireframe_thickness", sa.Float(), nullable=True)),
        ("ldview_remove_hidden_lines", sa.Column("ldview_remove_hidden_lines", sa.Boolean(), nullable=True)),
        ("ldview_texture_studs", sa.Column("ldview_texture_studs", sa.Boolean(), nullable=True)),
        ("ldview_texmaps", sa.Column("ldview_texmaps", sa.Boolean(), nullable=True)),
        ("ldview_hi_res_primitives", sa.Column("ldview_hi_res_primitives", sa.Boolean(), nullable=True)),
        ("ldview_texture_filter_type", sa.Column("ldview_texture_filter_type", sa.Integer(), nullable=True)),
        ("ldview_aniso_level", sa.Column("ldview_aniso_level", sa.Integer(), nullable=True)),
        ("ldview_texture_offset_factor", sa.Column("ldview_texture_offset_factor", sa.Float(), nullable=True)),
        ("ldview_lighting", sa.Column("ldview_lighting", sa.Boolean(), nullable=True)),
        ("ldview_use_quality_lighting", sa.Column("ldview_use_quality_lighting", sa.Boolean(), nullable=True)),
        ("ldview_use_specular", sa.Column("ldview_use_specular", sa.Boolean(), nullable=True)),
        ("ldview_subdued_lighting", sa.Column("ldview_subdued_lighting", sa.Boolean(), nullable=True)),
        ("ldview_perform_smoothing", sa.Column("ldview_perform_smoothing", sa.Boolean(), nullable=True)),
        ("ldview_use_flat_shading", sa.Column("ldview_use_flat_shading", sa.Boolean(), nullable=True)),
        ("ldview_antialias", sa.Column("ldview_antialias", sa.Integer(), nullable=True)),
        ("ldview_process_ldconfig", sa.Column("ldview_process_ldconfig", sa.Boolean(), nullable=True)),
        ("ldview_sort_transparent", sa.Column("ldview_sort_transparent", sa.Boolean(), nullable=True)),
        ("ldview_use_stipple", sa.Column("ldview_use_stipple", sa.Boolean(), nullable=True)),
        ("ldview_memory_usage", sa.Column("ldview_memory_usage", sa.Integer(), nullable=True)),
    ]


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    app_cols = {c["name"] for c in insp.get_columns("app_settings")}

    # app_settings: add LDView quality columns only if missing (idempotent for retries)
    for name, col in _app_settings_columns():
        if name not in app_cols:
            op.add_column("app_settings", col)

    # stl_cache: use batch_alter_table for SQLite (cannot ALTER constraints directly)
    default_key = _default_quality_key()
    stl_cols = {c["name"] for c in insp.get_columns("stl_cache")}

    with op.batch_alter_table("stl_cache", schema=None) as batch_op:
        if "quality_key" not in stl_cols:
            batch_op.add_column(sa.Column("quality_key", sa.String(), nullable=True))
        batch_op.drop_constraint("uq_stl_cache_key", type_="unique")
        batch_op.create_unique_constraint(
            "uq_stl_cache_key",
            ["part_num", "scale", "rotation_enabled", "rotation_x", "rotation_y", "rotation_z", "quality_key"],
        )

    op.execute(sa.text("UPDATE stl_cache SET quality_key = :k WHERE quality_key IS NULL").bindparams(k=default_key))


def downgrade() -> None:
    with op.batch_alter_table("stl_cache", schema=None) as batch_op:
        batch_op.drop_constraint("uq_stl_cache_key", type_="unique")
        batch_op.create_unique_constraint(
            "uq_stl_cache_key",
            ["part_num", "scale", "rotation_enabled", "rotation_x", "rotation_y", "rotation_z"],
        )
        batch_op.drop_column("quality_key")

    for col in (
        "ldview_memory_usage", "ldview_use_stipple", "ldview_sort_transparent", "ldview_process_ldconfig",
        "ldview_antialias", "ldview_use_flat_shading", "ldview_perform_smoothing", "ldview_subdued_lighting",
        "ldview_use_specular", "ldview_use_quality_lighting", "ldview_lighting", "ldview_texture_offset_factor",
        "ldview_aniso_level", "ldview_texture_filter_type", "ldview_hi_res_primitives", "ldview_texmaps",
        "ldview_texture_studs", "ldview_remove_hidden_lines", "ldview_wireframe_thickness", "ldview_wireframe",
        "ldview_conditional_highlights", "ldview_black_highlights", "ldview_line_smoothing", "ldview_edge_thickness",
        "ldview_polygon_offset", "ldview_show_highlight_lines", "ldview_bounding_boxes_only", "ldview_bfc",
        "ldview_seam_width", "ldview_seams", "ldview_curve_quality", "ldview_use_quality_studs",
        "ldview_allow_primitive_substitution",
    ):
        op.drop_column("app_settings", col)
