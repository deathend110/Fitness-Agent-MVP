"""phase4 files models drafts

Revision ID: 20260601_1000
Revises: 20260531_1900
Create Date: 2026-06-01 10:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite


revision: str = "20260601_1000"
down_revision: str | None = "20260531_1900"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "uploaded_file",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("stored_name", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("extension", sa.String(length=16), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("summary", sqlite.JSON(), nullable=False),
        sa.Column("parser_status", sa.String(length=32), nullable=False),
        sa.Column("parser_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("stored_name"),
    )
    op.create_index("ix_uploaded_file_extension", "uploaded_file", ["extension"])
    op.create_index("ix_uploaded_file_sha256", "uploaded_file", ["sha256"])

    op.create_table(
        "coach_draft",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("thinking", sqlite.JSON(), nullable=False),
        sa.Column("attached_file_ids", sqlite.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["chat_session.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("session_id"),
    )
    op.create_index("ix_coach_draft_session_id", "coach_draft", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_coach_draft_session_id", table_name="coach_draft")
    op.drop_table("coach_draft")
    op.drop_index("ix_uploaded_file_sha256", table_name="uploaded_file")
    op.drop_index("ix_uploaded_file_extension", table_name="uploaded_file")
    op.drop_table("uploaded_file")
