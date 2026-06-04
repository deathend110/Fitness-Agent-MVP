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
        sa.CheckConstraint("id = 1", name="ck_plan_source_state_singleton_id"),
        sa.CheckConstraint(
            "active_source IN ('manual', 'cycle')",
            name="ck_plan_source_state_active_source",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "active_cycle_plan",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("preset_key", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("start_date", sa.String(length=10), nullable=False),
        sa.Column("current_week_index", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("pending_week_index", sa.Integer(), nullable=True),
        sa.Column("goal", sa.Text(), nullable=False, server_default=""),
        sa.Column("base_lifts", sqlite.JSON(), nullable=False),
        sa.Column("config", sqlite.JSON(), nullable=False),
        sa.Column("last_generated_at", sa.DateTime(), nullable=True),
        sa.Column("last_confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('draft', 'active', 'completed', 'archived')",
            name="ck_active_cycle_plan_status",
        ),
        sa.CheckConstraint("current_week_index >= 1", name="ck_active_cycle_plan_current_week_index"),
        sa.CheckConstraint(
            "pending_week_index IS NULL OR pending_week_index >= 1",
            name="ck_active_cycle_plan_pending_week_index",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ux_active_cycle_plan_single_open_cycle",
        "active_cycle_plan",
        [sa.text("1")],
        unique=True,
        sqlite_where=sa.text("status IN ('draft', 'active')"),
    )

    op.create_table(
        "cycle_week_snapshot",
        sa.Column("cycle_id", sa.Integer(), nullable=False),
        sa.Column("week_index", sa.Integer(), nullable=False),
        sa.Column("generated_plan", sqlite.JSON(), nullable=False),
        sa.Column("override_plan", sqlite.JSON(), nullable=True),
        sa.Column("is_confirmed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("week_start", sa.String(length=10), nullable=False),
        sa.Column("week_end", sa.String(length=10), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("week_index >= 1", name="ck_cycle_week_snapshot_week_index"),
        sa.ForeignKeyConstraint(["cycle_id"], ["active_cycle_plan.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("cycle_id", "week_index", name="pk_cycle_week_snapshot"),
    )


def downgrade() -> None:
    op.drop_table("cycle_week_snapshot")
    op.drop_index("ux_active_cycle_plan_single_open_cycle", table_name="active_cycle_plan")
    op.drop_table("active_cycle_plan")
    op.drop_table("plan_source_state")
