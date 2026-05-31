from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.chat_session import run_tool_calling_chat
from backend.agent.deepseek_client import DeepSeekChatResult
from backend.agent.tool_calling import build_default_tool_registry
from backend.db.database import create_engine_and_session_factory
from backend.db.models import Base, ChatSession, ToolCallLog, WeeklyPlanDay, utc_now


class ToolLoopClient:
    def __init__(self) -> None:
        self.calls: list[list[dict[str, Any]]] = []

    async def request_chat_with_usage(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        stream: bool = False,
        **_: Any,
    ) -> DeepSeekChatResult:
        del model, tools, tool_choice, stream
        self.calls.append(messages)
        if len(self.calls) == 1:
            return DeepSeekChatResult(
                content="",
                tool_calls=[
                    {
                        "id": "call_weekly",
                        "type": "function",
                        "function": {"name": "get_weekly_plan", "arguments": "{}"},
                    }
                ],
            )
        return DeepSeekChatResult(content="我读取了本周计划，建议保持深蹲容量。")


class ThinkingToolLoopClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def request_chat_with_usage(self, **kwargs: Any) -> DeepSeekChatResult:
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            return DeepSeekChatResult(
                content="",
                reasoning_content="需要先读取本周计划。",
                tool_calls=[
                    {
                        "id": "call_weekly",
                        "type": "function",
                        "function": {"name": "get_weekly_plan", "arguments": "{}"},
                    }
                ],
            )
        return DeepSeekChatResult(content="读取后建议保持容量。")


@pytest_asyncio.fixture
async def db_session(tmp_path: Path) -> AsyncIterator[AsyncSession]:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'tool-loop.db'}"
    engine, session_factory = create_engine_and_session_factory(database_url)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_tool_loop_executes_readonly_tool_and_logs_slimmed_result(
    db_session: AsyncSession,
) -> None:
    chat_session = ChatSession(title="tool-loop", created_at=utc_now(), updated_at=utc_now())
    db_session.add(chat_session)
    await db_session.flush()
    db_session.add(WeeklyPlanDay(day_key="Monday", type="strength", exercises=[{"name": "深蹲", "rpe": 8}]))
    await db_session.commit()

    client = ToolLoopClient()
    result = await run_tool_calling_chat(
        session=db_session,
        session_id=chat_session.id,
        messages=[{"role": "user", "content": "读取本周计划再建议"}],
        model="deepseek-chat",
        deepseek_client=client,
        registry=build_default_tool_registry(),
    )

    logs = (await db_session.execute(select(ToolCallLog))).scalars().all()

    assert result.content == "我读取了本周计划，建议保持深蹲容量。"
    assert len(client.calls) == 2
    assert client.calls[1][-1]["role"] == "tool"
    assert client.calls[1][-1]["tool_call_id"] == "call_weekly"
    assert len(logs) == 1
    assert logs[0].tool_name == "get_weekly_plan"
    assert logs[0].status == "succeeded"
    assert "深蹲" in logs[0].result_summary


@pytest.mark.asyncio
async def test_tool_loop_returns_error_when_tool_rounds_exceed_limit(
    db_session: AsyncSession,
) -> None:
    class InfiniteToolClient(ToolLoopClient):
        async def request_chat_with_usage(self, **kwargs: Any) -> DeepSeekChatResult:
            self.calls.append(kwargs["messages"])
            return DeepSeekChatResult(
                content="",
                tool_calls=[
                    {
                        "id": f"call_{len(self.calls)}",
                        "type": "function",
                        "function": {"name": "get_weekly_plan", "arguments": "{}"},
                    }
                ],
            )

    chat_session = ChatSession(title="tool-loop-limit", created_at=utc_now(), updated_at=utc_now())
    db_session.add(chat_session)
    await db_session.commit()

    result = await run_tool_calling_chat(
        session=db_session,
        session_id=chat_session.id,
        messages=[{"role": "user", "content": "一直读工具"}],
        model="deepseek-chat",
        deepseek_client=InfiniteToolClient(),
        registry=build_default_tool_registry(),
        max_tool_rounds=2,
    )

    assert result.content == "工具调用次数过多，请稍后重试或缩小问题范围。"


@pytest.mark.asyncio
async def test_tool_loop_preserves_thinking_reasoning_content_between_rounds(
    db_session: AsyncSession,
) -> None:
    chat_session = ChatSession(title="tool-loop-thinking", created_at=utc_now(), updated_at=utc_now())
    db_session.add(chat_session)
    await db_session.flush()
    db_session.add(WeeklyPlanDay(day_key="Monday", type="strength", exercises=[{"name": "深蹲"}]))
    await db_session.commit()

    client = ThinkingToolLoopClient()
    result = await run_tool_calling_chat(
        session=db_session,
        session_id=chat_session.id,
        messages=[{"role": "user", "content": "思考后读取计划"}],
        model="deepseek-v4-pro",
        deepseek_client=client,
        registry=build_default_tool_registry(),
        thinking={"type": "enabled"},
        reasoning_effort="max",
    )

    assert result.content == "读取后建议保持容量。"
    assert client.calls[0]["thinking"] == {"type": "enabled"}
    assert client.calls[0]["reasoning_effort"] == "max"
    assert client.calls[0]["tool_choice"] is None
    assistant_message = client.calls[1]["messages"][1]
    assert assistant_message["role"] == "assistant"
    assert assistant_message["reasoning_content"] == "需要先读取本周计划。"
