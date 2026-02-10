"""Initial schema: projects, cached_sets, cached_parts, jobs, search_history, app_settings, stl_cache.

Revision ID: 001_initial
Revises:
Create Date: 2025-02-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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

    op.create_table(
        "cached_sets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("set_num", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("theme", sa.String(), nullable=True),
        sa.Column("subtheme", sa.String(), nullable=True),
        sa.Column("pieces", sa.Integer(), nullable=True),
        sa.Column("image_url", sa.String(), nullable=True),
        sa.Column("data", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cached_sets_set_num"), "cached_sets", ["set_num"], unique=True)

    op.create_table(
        "cached_parts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("set_num", sa.String(), nullable=True),
        sa.Column("parts_data", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cached_parts_set_num"), "cached_parts", ["set_num"], unique=False)

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
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_jobs_project_id"), "jobs", ["project_id"], unique=False)

    op.create_table(
        "search_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("query", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_search_history_query"), "search_history", ["query"], unique=False)

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
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        "INSERT INTO app_settings (id, default_plate_width, default_plate_depth, default_plate_height, part_spacing, "
        "stl_scale_factor, rotation_enabled, rotation_x, rotation_y, rotation_z, "
        "default_orientation_match_preview, auto_generate_part_previews, updated_at) "
        "VALUES (1, 250, 250, 250, 2, 1.0, 0, 0.0, 0.0, 0.0, 1, 1, CURRENT_TIMESTAMP)"
    )

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
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "part_num", "scale", "rotation_enabled",
            "rotation_x", "rotation_y", "rotation_z",
            name="uq_stl_cache_key",
        ),
    )
    op.create_index(op.f("ix_stl_cache_part_num"), "stl_cache", ["part_num"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_stl_cache_part_num"), table_name="stl_cache")
    op.drop_table("stl_cache")
    op.drop_table("app_settings")
    op.drop_index(op.f("ix_search_history_query"), table_name="search_history")
    op.drop_table("search_history")
    op.drop_index(op.f("ix_jobs_project_id"), table_name="jobs")
    op.drop_table("jobs")
    op.drop_index(op.f("ix_cached_parts_set_num"), table_name="cached_parts")
    op.drop_table("cached_parts")
    op.drop_index(op.f("ix_cached_sets_set_num"), table_name="cached_sets")
    op.drop_table("cached_sets")
    op.drop_index(op.f("ix_projects_set_num"), table_name="projects")
    op.drop_table("projects")
