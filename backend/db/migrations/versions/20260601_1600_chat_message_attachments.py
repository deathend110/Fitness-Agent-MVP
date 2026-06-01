"""chat message attachment snapshots"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite


revision: str = "20260601_1600"
down_revision: str | None = "20260601_1000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "chat_message",
        sa.Column("attachments", sqlite.JSON(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("chat_message", "attachments")
