from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from backend.db.database import create_engine_and_session_factory
from backend.db.models import (
    Base,
    ChatMessage,
    ChatSession,
    ChatSessionSummary,
    KnowledgeItem,
    MemoryItem,
    ToolCallLog,
    UsageRecord,
)


@pytest.mark.asyncio
async def test_phase3_context_memory_tool_and_usage_models_round_trip(tmp_path: Path):
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'phase3-models.db'}"
    engine, session_factory = create_engine_and_session_factory(database_url)

    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        async with session_factory() as session:
            chat_session = ChatSession(title="Phase 3 长对话")
            session.add(chat_session)
            await session.flush()

            first_message = ChatMessage(
                session_id=chat_session.id,
                role="user",
                content="我膝盖深蹲到底部会疼，之后安排要保守一点。",
            )
            second_message = ChatMessage(
                session_id=chat_session.id,
                role="assistant",
                content="之后我会把深蹲深度和疲劳管理作为安全限制。",
            )
            session.add_all([first_message, second_message])
            await session.flush()

            session_summary = ChatSessionSummary(
                session_id=chat_session.id,
                summary_text=(
                    "用户目标是增肌减脂；安全限制：深蹲到底部膝盖疼；"
                    "当前待办：后续计划降低深蹲深度和 RPE。"
                ),
                covered_from_message_id=first_message.id,
                covered_to_message_id=second_message.id,
                token_estimate=86,
            )
            safety_memory = MemoryItem(
                kind="safety",
                content="深蹲到底部时膝盖会疼，训练计划需要控制深度和 RPE。",
                confidence=0.95,
                source_message_id=first_message.id,
            )
            knowledge_item = KnowledgeItem(
                kind="training_note",
                title="5x5 模板摘要",
                content="5x5 模板通常以主项多组低次数为核心，需按恢复情况调节。",
                source_session_id=chat_session.id,
            )
            tool_log = ToolCallLog(
                session_id=chat_session.id,
                message_id=second_message.id,
                tool_name="get_weekly_plan",
                arguments_json={"days": ["Monday", "Friday"]},
                result_summary="返回 Monday 与 Friday 的动作名、组数、RPE 摘要。",
                status="succeeded",
            )
            usage_record = UsageRecord(
                session_id=chat_session.id,
                message_id=second_message.id,
                model="deepseek-v4-flash",
                prompt_tokens=1200,
                completion_tokens=220,
                total_tokens=1420,
                prompt_cache_hit_tokens=800,
                prompt_cache_miss_tokens=400,
            )
            session.add_all(
                [
                    session_summary,
                    safety_memory,
                    knowledge_item,
                    tool_log,
                    usage_record,
                ]
            )
            await session.commit()

        async with session_factory() as session:
            stored_summary = (
                await session.execute(select(ChatSessionSummary))
            ).scalar_one()
            stored_memory = (await session.execute(select(MemoryItem))).scalar_one()
            stored_knowledge = (await session.execute(select(KnowledgeItem))).scalar_one()
            stored_tool_log = (await session.execute(select(ToolCallLog))).scalar_one()
            stored_usage = (await session.execute(select(UsageRecord))).scalar_one()

        assert stored_summary.covered_from_message_id == first_message.id
        assert stored_summary.covered_to_message_id == second_message.id
        assert stored_summary.token_estimate == 86
        assert "膝盖疼" in stored_summary.summary_text

        assert stored_memory.kind == "safety"
        assert stored_memory.confidence == pytest.approx(0.95)
        assert stored_memory.source_message_id == first_message.id
        assert stored_memory.last_used_at is None

        assert stored_knowledge.kind == "training_note"
        assert stored_knowledge.source_session_id == chat_session.id
        assert "5x5" in stored_knowledge.title

        assert stored_tool_log.tool_name == "get_weekly_plan"
        assert stored_tool_log.arguments_json == {"days": ["Monday", "Friday"]}
        assert stored_tool_log.status == "succeeded"
        assert stored_tool_log.error_message is None

        assert stored_usage.model == "deepseek-v4-flash"
        assert stored_usage.prompt_tokens == 1200
        assert stored_usage.completion_tokens == 220
        assert stored_usage.total_tokens == 1420
        assert stored_usage.prompt_cache_hit_tokens == 800
        assert stored_usage.prompt_cache_miss_tokens == 400

    finally:
        await engine.dispose()

