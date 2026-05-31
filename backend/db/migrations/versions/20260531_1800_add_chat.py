from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite


revision = "20260531_1800"
down_revision = "20260531_1700"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chat_session",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "chat_message",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("suggestion", sqlite.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["chat_session.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_chat_message_session_id"),
        "chat_message",
        ["session_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_chat_message_session_id"), table_name="chat_message")
    op.drop_table("chat_message")
    op.drop_table("chat_session")
