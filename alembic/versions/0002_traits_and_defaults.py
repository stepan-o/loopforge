"""Add traits_json to robots and adjust social_need default

Revision ID: 0002_traits_and_defaults
Revises: 0001_initial
Create Date: 2025-11-14
"""
from __future__ import annotations

from alembic import op  # type: ignore
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_traits_and_defaults"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add traits_json column to robots
    op.add_column("robots", sa.Column("traits_json", sa.JSON(), nullable=True))

    # Update server default for social_need from 0.5 to 0.3
    # Note: existing rows will keep their current values; this affects new inserts only.
    op.alter_column(
        "robots",
        "social_need",
        existing_type=sa.Float(),
        server_default=sa.text("0.3"),
        existing_nullable=False,
    )


def downgrade() -> None:
    # Revert server default for social_need back to 0.5
    op.alter_column(
        "robots",
        "social_need",
        existing_type=sa.Float(),
        server_default=sa.text("0.5"),
        existing_nullable=False,
    )

    # Drop traits_json column
    op.drop_column("robots", "traits_json")
