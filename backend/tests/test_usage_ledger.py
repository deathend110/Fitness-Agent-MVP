from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.deepseek_client import DeepSeekChatResult, DeepSeekStreamEvent
from backend.agent.usage_ledger import normalize_usage, record_usage, summarize_session_usage
from backend.api import chat as chat_api
from backend.db.database import create_engine_and_session_factory, get_db_session
from backend.db.models import Base, ChatMessage, ChatSession, UsageRecord, utc_now
from backend.main import app

pytestmark = [
    pytest.mark.filterwarnings(
        "error::pydantic.warnings.UnsupportedFieldAttributeWarning"
    ),
    pytest.mark.filterwarnings(
        "ignore:'asyncio.iscoroutinefunction' is deprecated:DeprecationWarning"
    ),
]


class UsageAwareClient:
    def __init__(
        self,
        *,
        reply: str = "建议今天降低一点容量。",
        usage: dict[str, Any] | None = None,
        stream_events: list[DeepSeekStreamEvent] | None = None,
    ) -> None:
        self.reply = reply
        self.usage = usage or {}
        self.stream_events = stream_events or []

    async def request_chat_with_usage(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        stream: bool = False,
    ) -> DeepSeekChatResult:
        del messages, model, stream
        return DeepSeekChatResult(content=self.reply, usage=self.usage)

    async def stream_chat_with_usage(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
    ) -> AsyncIterator[DeepSeekStreamEvent]:
        del messages, model
        for event in self.stream_events:
            yield event


@pytest_asyncio.fixture
async def db_session(tmp_path: Path) -> AsyncIterator[AsyncSession]:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'usage-ledger.db'}"
    engine, session_factory = create_engine_and_session_factory(database_url)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def api_client(tmp_path: Path) -> AsyncIterator[tuple[AsyncClient, async_sessionmaker_for_test]]:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'usage-api.db'}"
    engine, session_factory = create_engine_and_session_factory(database_url)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_get_db_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, session_factory

    app.dependency_overrides.clear()
    await engine.dispose()


async_sessionmaker_for_test = Any


def parse_sse_events(raw_text: str) -> list[str]:
    return [
        line.removeprefix("event:").strip()
        for line in raw_text.splitlines()
        if line.startswith("event:")
    ]


def test_normalize_usage_extracts_token_and_cache_fields_with_zero_defaults() -> None:
    assert normalize_usage(
        {
            "prompt_tokens": 120,
            "completion_tokens": 30,
            "total_tokens": 150,
            "prompt_cache_hit_tokens": 80,
            "prompt_cache_miss_tokens": 40,
        }
    ) == {
        "prompt_tokens": 120,
        "completion_tokens": 30,
        "total_tokens": 150,
        "prompt_cache_hit_tokens": 80,
        "prompt_cache_miss_tokens": 40,
    }

    assert normalize_usage({"prompt_tokens": 7}) == {
        "prompt_tokens": 7,
        "completion_tokens": 0,
        "total_tokens": 7,
        "prompt_cache_hit_tokens": 0,
        "prompt_cache_miss_tokens": 0,
    }


@pytest.mark.asyncio
async def test_record_usage_and_summarize_session_usage(db_session: AsyncSession) -> None:
    chat_session = ChatSession(title="usage", created_at=utc_now(), updated_at=utc_now())
    db_session.add(chat_session)
    await db_session.flush()
    message = ChatMessage(
        session_id=chat_session.id,
        role="assistant",
        content="建议降低容量。",
        suggestion=None,
        created_at=utc_now(),
    )
    db_session.add(message)
    await db_session.flush()

    await record_usage(
        db_session,
        session_id=chat_session.id,
        message_id=message.id,
        model="deepseek-chat",
        usage={
            "prompt_tokens": 100,
            "completion_tokens": 20,
            "total_tokens": 120,
            "prompt_cache_hit_tokens": 70,
            "prompt_cache_miss_tokens": 30,
        },
    )
    await record_usage(
        db_session,
        session_id=chat_session.id,
        message_id=message.id,
        model="deepseek-chat",
        usage={"prompt_tokens": 50, "completion_tokens": 10},
    )
    await db_session.commit()

    summary = await summarize_session_usage(db_session, chat_session.id)

    assert summary == {
        "prompt_tokens": 150,
        "completion_tokens": 30,
        "total_tokens": 180,
        "prompt_cache_hit_tokens": 70,
        "prompt_cache_miss_tokens": 30,
        "cache_hit_rate": pytest.approx(0.7),
    }


@pytest.mark.asyncio
async def test_reply_endpoint_records_non_stream_usage(
    api_client: tuple[AsyncClient, Any],
) -> None:
    client, session_factory = api_client
    usage_client = UsageAwareClient(
        usage={
            "prompt_tokens": 100,
            "completion_tokens": 25,
            "total_tokens": 125,
            "prompt_cache_hit_tokens": 60,
            "prompt_cache_miss_tokens": 40,
        }
    )
    app.dependency_overrides[chat_api.get_deepseek_client] = lambda: usage_client
    session_id = (await client.get("/api/chat/sessions/default")).json()["id"]

    response = await client.post(
        "/api/chat/reply",
        json={
            "sessionId": session_id,
            "messages": [{"role": "user", "content": "今天怎么练？"}],
            "model": "deepseek-chat",
        },
    )

    assert response.status_code == 200
    async with session_factory() as session:
        records = (await session.execute(select(UsageRecord))).scalars().all()
    assert len(records) == 1
    assert records[0].session_id == session_id
    assert records[0].model == "deepseek-chat"
    assert records[0].prompt_cache_hit_tokens == 60


@pytest.mark.asyncio
async def test_stream_endpoint_records_usage_when_final_stream_event_contains_usage(
    api_client: tuple[AsyncClient, Any],
) -> None:
    client, session_factory = api_client
    usage_client = UsageAwareClient(
        stream_events=[
            DeepSeekStreamEvent(text="先降低一点容量。"),
            DeepSeekStreamEvent(
                usage={
                    "prompt_tokens": 90,
                    "completion_tokens": 15,
                    "total_tokens": 105,
                    "prompt_cache_hit_tokens": 30,
                    "prompt_cache_miss_tokens": 60,
                }
            ),
        ]
    )
    app.dependency_overrides[chat_api.get_deepseek_client] = lambda: usage_client
    session_id = (await client.get("/api/chat/sessions/default")).json()["id"]

    response = await client.post(
        "/api/chat/stream",
        json={
            "sessionId": session_id,
            "messages": [{"role": "user", "content": "明天要调吗？"}],
            "model": "deepseek-chat",
        },
    )

    assert response.status_code == 200
    assert parse_sse_events(response.text) == ["delta", "suggestion", "done"]
    async with session_factory() as session:
        records = (await session.execute(select(UsageRecord))).scalars().all()
    assert len(records) == 1
    assert records[0].total_tokens == 105
    assert records[0].prompt_cache_miss_tokens == 60


@pytest.mark.asyncio
async def test_context_debug_endpoint_returns_usage_summary(
    api_client: tuple[AsyncClient, Any],
) -> None:
    client, _session_factory = api_client
    usage_client = UsageAwareClient(
        usage={
            "prompt_tokens": 40,
            "completion_tokens": 10,
            "total_tokens": 50,
            "prompt_cache_hit_tokens": 25,
            "prompt_cache_miss_tokens": 15,
        }
    )
    app.dependency_overrides[chat_api.get_deepseek_client] = lambda: usage_client
    session_id = (await client.get("/api/chat/sessions/default")).json()["id"]

    reply = await client.post(
        "/api/chat/reply",
        json={
            "sessionId": session_id,
            "messages": [{"role": "user", "content": "记录 usage"}],
            "model": "deepseek-chat",
        },
    )
    assert reply.status_code == 200

    debug_response = await client.get(f"/api/chat/sessions/{session_id}/context/debug")

    assert debug_response.status_code == 200
    assert debug_response.json()["usageSummary"] == {
        "prompt_tokens": 40,
        "completion_tokens": 10,
        "total_tokens": 50,
        "prompt_cache_hit_tokens": 25,
        "prompt_cache_miss_tokens": 15,
        "cache_hit_rate": 0.625,
    }
