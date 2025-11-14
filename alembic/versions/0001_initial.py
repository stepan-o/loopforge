"""Initial schema for Loopforge City

Revision ID: 0001_initial
Revises: 
Create Date: 2025-11-14
"""
from __future__ import annotations

from alembic import op  # type: ignore
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # robots table
    op.create_table(
        "robots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("personality_json", sa.JSON(), nullable=True),
        sa.Column("location", sa.String(length=64), nullable=False, server_default=sa.text("'factory_floor'")),
        sa.Column("battery_level", sa.Integer(), nullable=False, server_default=sa.text("100")),
        sa.Column("stress", sa.Float(), nullable=False, server_default=sa.text("0.2")),
        sa.Column("curiosity", sa.Float(), nullable=False, server_default=sa.text("0.5")),
        sa.Column("social_need", sa.Float(), nullable=False, server_default=sa.text("0.5")),
        sa.Column("satisfaction", sa.Float(), nullable=False, server_default=sa.text("0.5")),
    )
    op.create_index("ix_robots_name", "robots", ["name"], unique=True)

    # memories table
    op.create_table(
        "memories",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("robot_id", sa.Integer(), sa.ForeignKey("robots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("timestamp_step", sa.Integer(), nullable=False),
        sa.Column("text", sa.String(length=255), nullable=False),
        sa.Column("importance", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("tags", sa.JSON(), nullable=True),
    )
    op.create_index("ix_memories_robot_id", "memories", ["robot_id"], unique=False)
    op.create_index("ix_memories_timestamp_step", "memories", ["timestamp_step"], unique=False)

    # action_logs table
    op.create_table(
        "action_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("robot_id", sa.Integer(), sa.ForeignKey("robots.id"), nullable=True),
        sa.Column("actor_type", sa.String(length=16), nullable=False),
        sa.Column("action_type", sa.String(length=32), nullable=False),
        sa.Column("target_robot_name", sa.String(length=64), nullable=True),
        sa.Column("destination", sa.String(length=64), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("timestamp_step", sa.Integer(), nullable=False),
    )
    op.create_index("ix_action_logs_robot_id", "action_logs", ["robot_id"], unique=False)
    op.create_index("ix_action_logs_timestamp_step", "action_logs", ["timestamp_step"], unique=False)

    # environment_events table
    op.create_table(
        "environment_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("location", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("timestamp_step", sa.Integer(), nullable=False),
    )
    op.create_index("ix_environment_events_timestamp_step", "environment_events", ["timestamp_step"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_environment_events_timestamp_step", table_name="environment_events")
    op.drop_table("environment_events")

    op.drop_index("ix_action_logs_timestamp_step", table_name="action_logs")
    op.drop_index("ix_action_logs_robot_id", table_name="action_logs")
    op.drop_table("action_logs")

    op.drop_index("ix_memories_timestamp_step", table_name="memories")
    op.drop_index("ix_memories_robot_id", table_name="memories")
    op.drop_table("memories")

    op.drop_index("ix_robots_name", table_name="robots")
    op.drop_table("robots")
