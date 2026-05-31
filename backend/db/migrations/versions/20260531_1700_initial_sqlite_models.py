from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite


revision = "20260531_1700"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "daily_log",
        sa.Column("date", sa.String(length=10), nullable=False),
        sa.Column("weight", sa.Float(), nullable=True),
        sa.Column("kcal", sa.Integer(), nullable=True),
        sa.Column("protein", sa.Integer(), nullable=True),
        sa.Column("sleep", sa.Float(), nullable=True),
        sa.Column("fatigue", sa.Integer(), nullable=True),
        sa.Column("steps", sa.Integer(), nullable=True),
        sa.Column("training_done", sa.Boolean(), nullable=True),
        sa.Column("training_notes", sa.Text(), nullable=False),
        sa.Column("tdee_manual", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("date"),
    )
    op.create_table(
        "profile",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("basic", sqlite.JSON(), nullable=False),
        sa.Column("one_rm", sqlite.JSON(), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("target_weight", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "weekly_plan_day",
        sa.Column("day_key", sa.String(length=16), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("exercises", sqlite.JSON(), nullable=False),
        sa.CheckConstraint(
            "day_key IN ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')",
            name="ck_weekly_plan_day_day_key",
        ),
        sa.PrimaryKeyConstraint("day_key"),
    )


def downgrade() -> None:
    op.drop_table("weekly_plan_day")
    op.drop_table("profile")
    op.drop_table("daily_log")
