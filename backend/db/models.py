from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, PrimaryKeyConstraint, String, Text, text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


WEEKDAY_ORDER = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)


class Base(DeclarativeBase):
    pass


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Profile(Base):
    __tablename__ = "profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    basic: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    one_rm: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    goal: Mapped[str] = mapped_column(Text, nullable=False, default="")
    target_weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")


class WeeklyPlanDay(Base):
    __tablename__ = "weekly_plan_day"
    __table_args__ = (
        CheckConstraint(
            "day_key IN ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')",
            name="ck_weekly_plan_day_day_key",
        ),
    )

    day_key: Mapped[str] = mapped_column(String(16), primary_key=True)
    type: Mapped[str] = mapped_column(String(64), nullable=False, default="rest")
    # exercises 整存 JSON，保持 template + instance + 扁平兼容字段原样往返，避免采纳链路字段被提前规范化丢失。
    exercises: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)


class DailyLog(Base):
    __tablename__ = "daily_log"

    date: Mapped[str] = mapped_column(String(10), primary_key=True)
    weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    kcal: Mapped[int | None] = mapped_column(Integer, nullable=True)
    protein: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sleep: Mapped[float | None] = mapped_column(Float, nullable=True)
    fatigue: Mapped[int | None] = mapped_column(Integer, nullable=True)
    steps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    training_done: Mapped[bool | None] = mapped_column(nullable=True)
    training_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tdee_manual: Mapped[int | None] = mapped_column(Integer, nullable=True)


class PlanSourceState(Base):
    __tablename__ = "plan_source_state"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_plan_source_state_singleton_id"),
        CheckConstraint(
            "active_source IN ('manual', 'cycle')",
            name="ck_plan_source_state_active_source",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # 该表只保存当前训练计划入口，显式限制来源值，避免前后端把未知模式写入后破坏演示态切换。
    active_source: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="manual",
        server_default=text("'manual'"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=utc_now,
    )


class ActiveCyclePlan(Base):
    __tablename__ = "active_cycle_plan"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'active', 'completed', 'archived')",
            name="ck_active_cycle_plan_status",
        ),
        CheckConstraint("current_week_index >= 1", name="ck_active_cycle_plan_current_week_index"),
        CheckConstraint(
            "pending_week_index IS NULL OR pending_week_index >= 1",
            name="ck_active_cycle_plan_pending_week_index",
        ),
        Index(
            "ux_active_cycle_plan_single_open_cycle",
            text("1"),
            unique=True,
            sqlite_where=text("status IN ('draft', 'active')"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    preset_key: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="draft",
        server_default=text("'draft'"),
    )
    start_date: Mapped[str] = mapped_column(String(10), nullable=False)
    current_week_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )
    pending_week_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    goal: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default=text("''"))
    # base_lifts 保留 oneRm/tm 等原始周期参数，后续周生成和重新确认都依赖这份基线快照。
    base_lifts: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    last_generated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=utc_now,
    )


class CycleWeekSnapshot(Base):
    __tablename__ = "cycle_week_snapshot"
    __table_args__ = (
        PrimaryKeyConstraint("cycle_id", "week_index", name="pk_cycle_week_snapshot"),
        CheckConstraint("week_index >= 1", name="ck_cycle_week_snapshot_week_index"),
    )

    cycle_id: Mapped[int] = mapped_column(
        ForeignKey("active_cycle_plan.id", ondelete="CASCADE"),
        nullable=False,
    )
    week_index: Mapped[int] = mapped_column(Integer, nullable=False)
    generated_plan: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    # override_plan 保存用户或 AI 对某周计划的覆盖结果，不能在读写过程中被规范化丢失。
    override_plan: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    is_confirmed: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        server_default=text("0"),
    )
    week_start: Mapped[str] = mapped_column(String(10), nullable=False)
    week_end: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=utc_now,
    )


class ChatSession(Base):
    __tablename__ = "chat_session"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(128), nullable=False, default="默认对话")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)


class ChatMessage(Base):
    __tablename__ = "chat_message"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("chat_session.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # suggestion 保存 AI 回复中的结构化采纳建议；为空时表示普通聊天消息，避免前端被迫补空对象。
    suggestion: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # attachments 保存用户消息附件快照，历史回显只依赖这份元数据，不依赖源文件是否仍存在。
    attachments: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)


class ChatSessionSummary(Base):
    __tablename__ = "chat_session_summary"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("chat_session.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    covered_from_message_id: Mapped[int | None] = mapped_column(
        ForeignKey("chat_message.id", ondelete="SET NULL"),
        nullable=True,
    )
    covered_to_message_id: Mapped[int | None] = mapped_column(
        ForeignKey("chat_message.id", ondelete="SET NULL"),
        nullable=True,
    )
    token_estimate: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)


class MemoryItem(Base):
    __tablename__ = "memory_item"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # memory 是用户长期事实或稳定偏好；不要把一次性日志、AI 自己的建议直接晋升到这里。
    content: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    source_message_id: Mapped[int | None] = mapped_column(
        ForeignKey("chat_message.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)


class KnowledgeItem(Base):
    __tablename__ = "knowledge_item"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    # knowledge 是外部资料、上传文件或训练模板片段，和用户长期记忆分开，避免资料污染用户画像。
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_file_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_session_id: Mapped[int | None] = mapped_column(
        ForeignKey("chat_session.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)


class UploadedFile(Base):
    __tablename__ = "uploaded_file"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    extension: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # storage_path 保存相对 uploads_dir 的路径，避免把用户机器绝对路径写进数据库。
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    # 上传文件是本地缓存资料；只有摘要或用户确认后的稳定事实才能进入 knowledge/memory。
    summary: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    parser_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    parser_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)


class CoachDraft(Base):
    __tablename__ = "coach_draft"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("chat_session.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    thinking: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    attached_file_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)


class ToolCallLog(Base):
    __tablename__ = "tool_call_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("chat_session.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message_id: Mapped[int | None] = mapped_column(
        ForeignKey("chat_message.id", ondelete="SET NULL"),
        nullable=True,
    )
    tool_name: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    arguments_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    result_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)


class UsageRecord(Base):
    __tablename__ = "usage_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("chat_session.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message_id: Mapped[int | None] = mapped_column(
        ForeignKey("chat_message.id", ondelete="SET NULL"),
        nullable=True,
    )
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    prompt_cache_hit_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    prompt_cache_miss_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
