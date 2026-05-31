from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite


revision = "20260531_1900"
down_revision = "20260531_1800"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chat_session_summary",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("covered_from_message_id", sa.Integer(), nullable=True),
        sa.Column("covered_to_message_id", sa.Integer(), nullable=True),
        sa.Column("token_estimate", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["covered_from_message_id"], ["chat_message.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["covered_to_message_id"], ["chat_message.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["session_id"], ["chat_session.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_chat_session_summary_session_id"),
        "chat_session_summary",
        ["session_id"],
        unique=False,
    )

    op.create_table(
        "memory_item",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("source_message_id", sa.Integer(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["source_message_id"], ["chat_message.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_memory_item_kind"), "memory_item", ["kind"], unique=False)

    op.create_table(
        "knowledge_item",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_file_id", sa.Integer(), nullable=True),
        sa.Column("source_session_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["source_session_id"], ["chat_session.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_knowledge_item_kind"), "knowledge_item", ["kind"], unique=False)

    op.create_table(
        "tool_call_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=True),
        sa.Column("tool_name", sa.String(length=96), nullable=False),
        sa.Column("arguments_json", sqlite.JSON(), nullable=False),
        sa.Column("result_summary", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["message_id"], ["chat_message.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["session_id"], ["chat_session.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tool_call_log_session_id"), "tool_call_log", ["session_id"], unique=False)
    op.create_index(op.f("ix_tool_call_log_tool_name"), "tool_call_log", ["tool_name"], unique=False)

    op.create_table(
        "usage_record",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=True),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column("prompt_cache_hit_tokens", sa.Integer(), nullable=False),
        sa.Column("prompt_cache_miss_tokens", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["message_id"], ["chat_message.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["session_id"], ["chat_session.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_usage_record_session_id"), "usage_record", ["session_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_usage_record_session_id"), table_name="usage_record")
    op.drop_table("usage_record")
    op.drop_index(op.f("ix_tool_call_log_tool_name"), table_name="tool_call_log")
    op.drop_index(op.f("ix_tool_call_log_session_id"), table_name="tool_call_log")
    op.drop_table("tool_call_log")
    op.drop_index(op.f("ix_knowledge_item_kind"), table_name="knowledge_item")
    op.drop_table("knowledge_item")
    op.drop_index(op.f("ix_memory_item_kind"), table_name="memory_item")
    op.drop_table("memory_item")
    op.drop_index(op.f("ix_chat_session_summary_session_id"), table_name="chat_session_summary")
    op.drop_table("chat_session_summary")

