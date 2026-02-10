"""Drop legacy cache tables: cached_sets, cached_parts.

These were introduced in the initial migration. The generic api_cache table
(003) can be used for API response caching instead.

Revision ID: 004_drop_old_cache
Revises: 003_api_cache
Create Date: 2025-02-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "004_drop_old_cache"
down_revision: Union[str, None] = "003_api_cache"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index(op.f("ix_cached_parts_set_num"), table_name="cached_parts")
    op.drop_table("cached_parts")
    op.drop_index(op.f("ix_cached_sets_set_num"), table_name="cached_sets")
    op.drop_table("cached_sets")


def downgrade() -> None:
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
