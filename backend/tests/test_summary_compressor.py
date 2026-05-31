from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.context_manager import (
    StateReinjector,
    SummaryCompressor,
    TokenBudgetConfig,
)
from backend.db.database import create_engine_and_session_factory
from backend.db.models import Base, ChatMessage, ChatSession, ChatSessionSummary, utc_now


@pytest_asyncio.fixture
async def db_session(tmp_path: Path) -> AsyncIterator[AsyncSession]:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'summary-compressor.db'}"
    engine, session_factory = create_engine_and_session_factory(database_url)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        yield session

    await engine.dispose()


async def seed_long_chat(session: AsyncSession, *, count: int = 16) -> ChatSession:
    chat_session = ChatSession(title="长对话", created_at=utc_now(), updated_at=utc_now())
    session.add(chat_session)
    await session.flush()

    for index in range(count):
        session.add(
            ChatMessage(
                session_id=chat_session.id,
                role="user" if index % 2 == 0 else "assistant",
                content=f"第 {index} 轮：训练目标是增肌，左膝深蹲到底部疼痛，偏好晚训。" + "需要保留。" * 30,
                suggestion={"day": "Friday", "summary": "待确认降容量"} if index == count - 2 else None,
                created_at=utc_now(),
            )
        )
    await session.commit()
    return chat_session


@pytest.mark.asyncio
async def test_summary_compressor_triggers_over_85_percent_and_persists_range(
    db_session: AsyncSession,
) -> None:
    chat_session = await seed_long_chat(db_session)
    calls: list[list[dict[str, Any]]] = []

    async def fake_summarizer(messages: list[dict[str, Any]]) -> str:
        calls.append(messages)
        return "\n".join(
            [
                "训练目标: 增肌并保持力量。",
                "伤病/疼痛限制: 左膝深蹲到底部疼痛，来源为历史消息。",
                "用户偏好: 晚训。",
                "已采纳建议: 暂无。",
                "被拒绝建议: 暂无。",
                "待确认事项: 周五降容量建议卡仍待确认。",
                "当前周期/当前计划: 继续围绕深蹲主项调整。",
            ]
        )

    compressor = SummaryCompressor(
        budget=TokenBudgetConfig(max_context_tokens=360, reserved_response_tokens=60),
        summarizer=fake_summarizer,
        keep_recent_count=4,
    )

    result = await compressor.compress_if_needed(
        db_session,
        session_id=chat_session.id,
    )

    assert result.summary_created is True
    assert len(calls) == 1
    assert "左膝深蹲到底部疼痛" in result.summary_text
    assert "待确认" in result.summary_text
    assert len(result.recent_messages) == 4
    assert any(message.get("suggestion") for message in result.recent_messages)

    summaries = (
        await db_session.execute(select(ChatSessionSummary).where(ChatSessionSummary.session_id == chat_session.id))
    ).scalars().all()
    assert len(summaries) == 1
    assert summaries[0].covered_from_message_id is not None
    assert summaries[0].covered_to_message_id is not None
    assert summaries[0].covered_from_message_id < summaries[0].covered_to_message_id
    assert summaries[0].token_estimate > 0


@pytest.mark.asyncio
async def test_summary_compressor_keeps_recent_window_when_below_threshold(
    db_session: AsyncSession,
) -> None:
    chat_session = await seed_long_chat(db_session, count=2)
    compressor = SummaryCompressor(
        budget=TokenBudgetConfig(max_context_tokens=2000, reserved_response_tokens=200),
        summarizer=lambda _messages: "不应调用",
    )

    result = await compressor.compress_if_needed(db_session, session_id=chat_session.id)

    assert result.summary_created is False
    assert result.summary_text == ""
    assert len(result.recent_messages) == 2


@pytest.mark.asyncio
async def test_summary_compressor_opens_circuit_after_three_failures(
    db_session: AsyncSession,
) -> None:
    chat_session = await seed_long_chat(db_session)

    async def failing_summarizer(_messages: list[dict[str, Any]]) -> str:
        raise RuntimeError("summary failed")

    compressor = SummaryCompressor(
        budget=TokenBudgetConfig(max_context_tokens=360, reserved_response_tokens=60),
        summarizer=failing_summarizer,
        keep_recent_count=3,
    )

    first = await compressor.compress_if_needed(db_session, session_id=chat_session.id)
    second = await compressor.compress_if_needed(db_session, session_id=chat_session.id)
    third = await compressor.compress_if_needed(db_session, session_id=chat_session.id)

    assert first.failure_count == 1
    assert second.failure_count == 2
    assert third.failure_count == 3
    assert third.circuit_open is True
    assert third.summary_created is False
    assert len(third.recent_messages) == 3


def test_state_reinjector_keeps_active_state_outside_summary() -> None:
    messages = StateReinjector().build_state_messages(
        profile={"goal": "增肌"},
        weekly_plan={"Monday": {"type": "strength"}},
        daily_logs={"2026-05-31": {"fatigue": 5}},
        pending_suggestion={"day": "Friday", "summary": "降容量待确认"},
        recent_files_summary=["深蹲技术笔记"],
        tool_schema_version="phase3-readonly-v1",
    )

    rendered = "\n".join(message["content"] for message in messages)

    assert "增肌" in rendered
    assert "Monday" in rendered
    assert "降容量待确认" in rendered
    assert "深蹲技术笔记" in rendered
    assert "phase3-readonly-v1" in rendered
