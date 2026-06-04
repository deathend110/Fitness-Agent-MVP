"""add cycle plan mode persistence tables"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite


revision: str = "20260604_2200"
down_revision: str | None = "20260601_1600"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "plan_source_state",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("active_source", sa.String(length=16), nullable=False, server_default="manual"),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "active_source IN ('manual', 'cycle')",
            name="ck_plan_source_state_active_source",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "active_cycle_plan",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("preset_key", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("start_date", sa.String(length=10), nullable=False, server_default=""),
        sa.Column("current_week_index", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("pending_week_index", sa.Integer(), nullable=True),
        sa.Column("goal", sa.Text(), nullable=False, server_default=""),
        sa.Column("base_lifts", sqlite.JSON(), nullable=False),
        sa.Column("config", sqlite.JSON(), nullable=False),
        sa.Column("last_generated_at", sa.DateTime(), nullable=True),
        sa.Column("last_confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "cycle_week_snapshot",
        sa.Column("cycle_id", sa.Integer(), nullable=False),
        sa.Column("week_index", sa.Integer(), nullable=False),
        sa.Column("generated_plan", sqlite.JSON(), nullable=False),
        sa.Column("override_plan", sqlite.JSON(), nullable=True),
        sa.Column("is_confirmed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("week_start", sa.String(length=10), nullable=False, server_default=""),
        sa.Column("week_end", sa.String(length=10), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["cycle_id"], ["active_cycle_plan.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("cycle_id", "week_index", name="pk_cycle_week_snapshot"),
    )


def downgrade() -> None:
    op.drop_table("cycle_week_snapshot")
    op.drop_table("active_cycle_plan")
    op.drop_table("plan_source_state")
