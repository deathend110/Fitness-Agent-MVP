from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.tool_calling import build_default_tool_registry
from backend.agent.tool_loop import ToolLoopOrchestrator
from backend.db.database import create_engine_and_session_factory
from backend.db.models import Base, Profile


class FakeProvider:
    def __init__(self) -> None:
        self.calls = 0

    def build_tool_schema(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return tools

    def normalize_tool_call_response(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        if self.calls == 1:
            return [
                {
                    "toolName": "get_profile",
                    "callId": "call-1",
                    "arguments": {},
                    "rawProviderPayload": payload,
                }
            ]
        return []

    def build_followup_messages_after_tool_result(
        self,
        messages: list[dict[str, Any]],
        tool_call: dict[str, Any],
        tool_result: Any,
    ) -> list[dict[str, Any]]:
        return messages + [
            {
                "role": "tool",
                "name": tool_call["toolName"],
                "content": str(tool_result),
            }
        ]

    async def generate_chat(self, **kwargs: Any) -> dict[str, Any]:
        self.calls += 1
        if self.calls == 1:
            return {"text": "", "toolCalls": [{"name": "get_profile"}], "raw": {"round": 1}}
        return {"text": "final-answer", "toolCalls": [], "raw": {"round": 2}}


@pytest_asyncio.fixture
async def db_session(tmp_path: Path) -> AsyncIterator[AsyncSession]:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'tool-loop-orchestrator.db'}"
    engine, session_factory = create_engine_and_session_factory(database_url)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        session.add(
            Profile(
                id=1,
                basic={"name": "阿杰"},
                one_rm={"squat": 150},
                goal="增肌",
                target_weight=86,
                notes="",
            )
        )
        await session.commit()
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_tool_loop_executes_tool_and_returns_final_text(db_session: AsyncSession) -> None:
    orchestrator = ToolLoopOrchestrator(registry=build_default_tool_registry(), max_rounds=4)
    provider = FakeProvider()

    result = await orchestrator.run(
        session=db_session,
        provider=provider,
        messages=[{"role": "user", "content": "给我建议"}],
        model="provider::model",
    )

    assert result.content == "final-answer"
    assert result.tool_rounds == 1
