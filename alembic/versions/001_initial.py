"""Initial schema: projects, jobs, search_history, app_settings, stl_cache, api_cache.

Consolidated from previous migrations. No downgrade (new project).
Idempotent: skips create_table/create_index/insert when objects already exist,
so startup does not fail if the DB has tables but alembic_version was missing.
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect
import sqlalchemy as sa


revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables_exist(conn):
    return set(inspect(conn).get_table_names())


def upgrade() -> None:
    conn = op.get_bind()
    existing = _tables_exist(conn)

    if "projects" not in existing:
        op.create_table(
            "projects",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("set_num", sa.String(), nullable=True),
            sa.Column("name", sa.String(), nullable=True),
            sa.Column("set_name", sa.String(), nullable=True),
            sa.Column("image_url", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_projects_set_num"), "projects", ["set_num"], unique=False)

    if "jobs" not in existing:
        op.create_table(
            "jobs",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("project_id", sa.String(), nullable=True),
            sa.Column("set_num", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("progress", sa.Integer(), nullable=True),
            sa.Column("plate_height", sa.Integer(), nullable=True),
            sa.Column("plate_width", sa.Integer(), nullable=True),
            sa.Column("plate_depth", sa.Integer(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("output_file", sa.String(), nullable=True),
            sa.Column("brickgen_version", sa.String(), nullable=True),
            sa.Column("settings", sa.Text(), nullable=True),
            sa.Column("log", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_jobs_project_id"), "jobs", ["project_id"], unique=False)

    if "search_history" not in existing:
        op.create_table(
            "search_history",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("query", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_search_history_query"), "search_history", ["query"], unique=False)

    if "app_settings" not in existing:
        op.create_table(
            "app_settings",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("default_plate_width", sa.Integer(), nullable=True),
            sa.Column("default_plate_depth", sa.Integer(), nullable=True),
            sa.Column("default_plate_height", sa.Integer(), nullable=True),
            sa.Column("part_spacing", sa.Integer(), nullable=True),
            sa.Column("stl_scale_factor", sa.Float(), nullable=True),
            sa.Column("rotation_enabled", sa.Boolean(), nullable=True),
            sa.Column("rotation_x", sa.Float(), nullable=True),
            sa.Column("rotation_y", sa.Float(), nullable=True),
            sa.Column("rotation_z", sa.Float(), nullable=True),
            sa.Column("default_orientation_match_preview", sa.Boolean(), nullable=True),
            sa.Column("auto_generate_part_previews", sa.Boolean(), nullable=True),
            sa.Column("ldview_allow_primitive_substitution", sa.Boolean(), nullable=True),
            sa.Column("ldview_use_quality_studs", sa.Boolean(), nullable=True),
            sa.Column("ldview_curve_quality", sa.Integer(), nullable=True),
            sa.Column("ldview_seams", sa.Boolean(), nullable=True),
            sa.Column("ldview_seam_width", sa.Integer(), nullable=True),
            sa.Column("ldview_bfc", sa.Boolean(), nullable=True),
            sa.Column("ldview_bounding_boxes_only", sa.Boolean(), nullable=True),
            sa.Column("ldview_show_highlight_lines", sa.Boolean(), nullable=True),
            sa.Column("ldview_polygon_offset", sa.Boolean(), nullable=True),
            sa.Column("ldview_edge_thickness", sa.Float(), nullable=True),
            sa.Column("ldview_line_smoothing", sa.Boolean(), nullable=True),
            sa.Column("ldview_black_highlights", sa.Boolean(), nullable=True),
            sa.Column("ldview_conditional_highlights", sa.Boolean(), nullable=True),
            sa.Column("ldview_wireframe", sa.Boolean(), nullable=True),
            sa.Column("ldview_wireframe_thickness", sa.Float(), nullable=True),
            sa.Column("ldview_remove_hidden_lines", sa.Boolean(), nullable=True),
            sa.Column("ldview_texture_studs", sa.Boolean(), nullable=True),
            sa.Column("ldview_texmaps", sa.Boolean(), nullable=True),
            sa.Column("ldview_hi_res_primitives", sa.Boolean(), nullable=True),
            sa.Column("ldview_texture_filter_type", sa.Integer(), nullable=True),
            sa.Column("ldview_aniso_level", sa.Integer(), nullable=True),
            sa.Column("ldview_texture_offset_factor", sa.Float(), nullable=True),
            sa.Column("ldview_lighting", sa.Boolean(), nullable=True),
            sa.Column("ldview_use_quality_lighting", sa.Boolean(), nullable=True),
            sa.Column("ldview_use_specular", sa.Boolean(), nullable=True),
            sa.Column("ldview_subdued_lighting", sa.Boolean(), nullable=True),
            sa.Column("ldview_perform_smoothing", sa.Boolean(), nullable=True),
            sa.Column("ldview_use_flat_shading", sa.Boolean(), nullable=True),
            sa.Column("ldview_antialias", sa.Integer(), nullable=True),
            sa.Column("ldview_process_ldconfig", sa.Boolean(), nullable=True),
            sa.Column("ldview_sort_transparent", sa.Boolean(), nullable=True),
            sa.Column("ldview_use_stipple", sa.Boolean(), nullable=True),
            sa.Column("ldview_memory_usage", sa.Integer(), nullable=True),
            sa.Column("onboarding_wizard_complete", sa.Boolean(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.execute(
            "INSERT OR IGNORE INTO app_settings ("
            "id, default_plate_width, default_plate_depth, default_plate_height, part_spacing, "
            "stl_scale_factor, rotation_enabled, rotation_x, rotation_y, rotation_z, "
            "default_orientation_match_preview, auto_generate_part_previews, "
            "ldview_allow_primitive_substitution, ldview_use_quality_studs, ldview_curve_quality, "
            "ldview_seams, ldview_seam_width, ldview_bfc, ldview_bounding_boxes_only, ldview_show_highlight_lines, "
            "ldview_polygon_offset, ldview_edge_thickness, ldview_line_smoothing, ldview_black_highlights, "
            "ldview_conditional_highlights, ldview_wireframe, ldview_wireframe_thickness, ldview_remove_hidden_lines, "
            "ldview_texture_studs, ldview_texmaps, ldview_hi_res_primitives, ldview_texture_filter_type, "
            "ldview_aniso_level, ldview_texture_offset_factor, ldview_lighting, ldview_use_quality_lighting, "
            "ldview_use_specular, ldview_subdued_lighting, ldview_perform_smoothing, ldview_use_flat_shading, "
            "ldview_antialias, ldview_process_ldconfig, ldview_sort_transparent, ldview_use_stipple, ldview_memory_usage, "
            "onboarding_wizard_complete, updated_at"
            ") VALUES ("
            "1, 250, 250, 250, 2, 1.0, 0, 0.0, 0.0, 0.0, 1, 1, "
            "1, 1, 2, 0, 0, 1, 0, 0, 1, 0.0, 0, 0, 0, 0, 0.0, 0, 1, 1, 0, 9987, "
            "0, 5.0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 2, 0, CURRENT_TIMESTAMP)"
        )

    if "stl_cache" not in existing:
        op.create_table(
            "stl_cache",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("part_num", sa.String(), nullable=True),
            sa.Column("file_path", sa.String(), nullable=True),
            sa.Column("file_size", sa.Integer(), nullable=True),
            sa.Column("rotation_enabled", sa.Boolean(), nullable=True),
            sa.Column("rotation_x", sa.Float(), nullable=True),
            sa.Column("rotation_y", sa.Float(), nullable=True),
            sa.Column("rotation_z", sa.Float(), nullable=True),
            sa.Column("scale", sa.Float(), nullable=True),
            sa.Column("quality_key", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "part_num", "scale", "rotation_enabled",
                "rotation_x", "rotation_y", "rotation_z", "quality_key",
                name="uq_stl_cache_key",
            ),
        )
        op.create_index(op.f("ix_stl_cache_part_num"), "stl_cache", ["part_num"], unique=False)

    if "api_cache" not in existing:
        op.create_table(
            "api_cache",
            sa.Column("key", sa.String(), nullable=False),
            sa.Column("value", sa.Text(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("key"),
        )


def downgrade() -> None:
    raise NotImplementedError("Initial Schema has no downgrade.")
