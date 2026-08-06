"""Add custom projects support: is_custom column on projects, project_parts table, ldraw_part_index table.

Revision ID: 002_custom_projects
Revises: 001_initial
Create Date: 2026-02-23
"""
from typing import Sequence, Union
from alembic import op
from sqlalchemy import inspect
import sqlalchemy as sa


revision: str = "002_custom_projects"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(conn, table: str, column: str) -> bool:
    cols = [c["name"] for c in inspect(conn).get_columns(table)]
    return column in cols


def _tables_exist(conn):
    return set(inspect(conn).get_table_names())


def upgrade() -> None:
    conn = op.get_bind()
    existing = _tables_exist(conn)

    # Add is_custom column to projects if not present
    if "projects" in existing and not _column_exists(conn, "projects", "is_custom"):
        op.add_column("projects", sa.Column("is_custom", sa.Boolean(), nullable=False, server_default="0"))

    if "project_parts" not in existing:
        op.create_table(
            "project_parts",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("project_id", sa.String(), nullable=False),
            sa.Column("part_num", sa.String(), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("color", sa.String(), nullable=True),
            sa.Column("color_rgb", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_project_parts_project_id"), "project_parts", ["project_id"], unique=False)

    if "ldraw_part_index" not in existing:
        op.create_table(
            "ldraw_part_index",
            sa.Column("part_num", sa.String(), nullable=False),
            sa.Column("description", sa.String(), nullable=True),
            sa.Column("indexed_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("part_num"),
        )


def downgrade() -> None:
    op.drop_table("ldraw_part_index")
    op.drop_index(op.f("ix_project_parts_project_id"), table_name="project_parts")
    op.drop_table("project_parts")
    # SQLite doesn't support DROP COLUMN in older versions; skip for now
