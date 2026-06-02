from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.chat_session import build_agent_request
from backend.api import chat as chat_api
from backend.db.database import create_engine_and_session_factory, get_db_session
from backend.db.models import (
    Base,
    ChatMessage,
    ChatSession,
    DailyLog,
    MemoryItem,
    Profile,
    WeeklyPlanDay,
    utc_now,
)
from backend.main import app

pytestmark = [
    pytest.mark.filterwarnings(
        "error::pydantic.warnings.UnsupportedFieldAttributeWarning"
    ),
    pytest.mark.filterwarnings(
        "ignore:'asyncio.iscoroutinefunction' is deprecated:DeprecationWarning"
    ),
]


class CapturingDeepSeekClient:
    def __init__(self, reply: str = "后端上下文已就绪。") -> None:
        self.reply = reply
        self.calls: list[list[dict[str, Any]]] = []

    async def request_chat(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        stream: bool = False,
    ) -> str:
        del model, stream
        self.calls.append(messages)
        return self.reply


@pytest_asyncio.fixture
async def db_session(tmp_path: Path) -> AsyncIterator[AsyncSession]:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'chat-session-context.db'}"
    engine, session_factory = create_engine_and_session_factory(database_url)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def api_client(tmp_path: Path) -> AsyncIterator[tuple[AsyncClient, CapturingDeepSeekClient]]:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'chat-session-api.db'}"
    engine, session_factory = create_engine_and_session_factory(database_url)
    fake_client = CapturingDeepSeekClient()

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_get_db_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[chat_api.get_deepseek_client] = lambda: fake_client

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, fake_client

    app.dependency_overrides.clear()
    await engine.dispose()


async def seed_agent_state(session: AsyncSession) -> ChatSession:
    chat_session = ChatSession(title="后端编排测试", created_at=utc_now(), updated_at=utc_now())
    session.add(chat_session)
    await session.flush()

    session.add_all(
        [
            Profile(
                id=1,
                basic={"name": "阿杰", "age": 26},
                one_rm={"squat": 150, "bench": 105, "deadlift": 190},
                goal="增肌同时保持力量",
                target_weight=86,
                notes="晚训表现更好",
            ),
            WeeklyPlanDay(
                day_key="Monday",
                type="strength",
                exercises=[{"name": "深蹲", "sets": 5, "reps": 5, "rpe": 8}],
            ),
            DailyLog(
                date="2026-05-31",
                weight=82.4,
                kcal=2310,
                protein=168,
                sleep=6.5,
                fatigue=5,
                steps=6200,
                training_done=True,
                training_notes="深蹲最后两组速度明显下降。",
                tdee_manual=2550,
            ),
            MemoryItem(
                kind="safety",
                content="深蹲到底部时左膝偶发疼痛。",
                confidence=0.95,
            ),
            ChatMessage(
                session_id=chat_session.id,
                role="assistant",
                content="上次建议把周五硬拉降到 RPE 7。",
                suggestion=None,
                created_at=utc_now(),
            ),
        ]
    )
    await session.commit()
    return chat_session


@pytest.mark.asyncio
async def test_build_agent_request_reads_database_state_when_frontend_only_sends_user_input(
    db_session: AsyncSession,
) -> None:
    chat_session = await seed_agent_state(db_session)

    request = await build_agent_request(
        session=db_session,
        session_id=chat_session.id,
        user_input="明天训练怎么安排？",
        model_config={"model": "deepseek-chat"},
    )

    rendered = "\n".join(message["content"] for message in request.messages)

    assert request.model == "deepseek-chat"
    assert request.messages[0]["role"] == "system"
    assert "阿杰" in rendered
    assert "深蹲" in rendered
    assert "深蹲最后两组速度明显下降" in rendered
    assert "左膝偶发疼痛" in rendered
    assert "上次建议把周五硬拉降到 RPE 7" in rendered
    assert request.messages[-1] == {"role": "user", "content": "明天训练怎么安排？"}
    assert request.debug["source"] == "agent_orchestrator"


@pytest.mark.asyncio
async def test_reply_endpoint_uses_backend_context_for_user_input_request(
    api_client: tuple[AsyncClient, CapturingDeepSeekClient],
) -> None:
    client, fake_client = api_client
    session_id = (await client.post("/api/chat/sessions", json={"title": "API 编排"})).json()["id"]
    async for session in app.dependency_overrides[get_db_session]():
        chat_session = await session.get(ChatSession, session_id)
        assert chat_session is not None
        await seed_agent_state(session)
        break

    response = await client.post(
        "/api/chat/reply",
        json={
            "sessionId": session_id,
            "userInput": "只看今天疲劳，明天要降容量吗？",
            "model": "deepseek-chat",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "text": "后端上下文已就绪。",
        "suggestion": None,
        "proposal": None,
    }
    sent_messages = fake_client.calls[-1]
    assert sent_messages[0]["role"] == "system"
    assert sent_messages[-1]["content"] == "只看今天疲劳，明天要降容量吗？"
    assert any("当前用户状态" in message["content"] for message in sent_messages)


@pytest.mark.asyncio
async def test_reply_endpoint_keeps_phase2_messages_request_compatible(
    api_client: tuple[AsyncClient, CapturingDeepSeekClient],
) -> None:
    client, fake_client = api_client
    default_session = (await client.get("/api/chat/sessions/default")).json()
    legacy_messages = [
        {"role": "system", "content": "SYSTEM_PROMPT"},
        {"role": "user", "content": "旧路径仍然可用吗？"},
    ]

    response = await client.post(
        "/api/chat/reply",
        json={
            "sessionId": default_session["id"],
            "messages": legacy_messages,
            "model": "deepseek-chat",
        },
    )

    assert response.status_code == 200
    assert fake_client.calls[-1] == legacy_messages


def test_normalize_chat_request_payload_unifies_agent_and_legacy_contracts() -> None:
    agent_payload = chat_api.normalize_chat_request_payload(
        payload=chat_api.ChatReplyRequestSchema(
            sessionId=7,
            userInput="  只看今天疲劳，明天要降容量吗？  ",
            model="deepseek-chat",
            fileIds=[3, 5],
        )
    )
    legacy_payload = chat_api.normalize_chat_request_payload(
        payload=chat_api.ChatReplyRequestSchema(
            sessionId=7,
            messages=[
                {"role": "system", "content": "SYSTEM_PROMPT"},
                {"role": "user", "content": "旧路径仍然可用吗？"},
            ],
            model="deepseek-chat",
        )
    )

    assert agent_payload.source == "agent"
    assert agent_payload.user_content == "只看今天疲劳，明天要降容量吗？"
    assert agent_payload.session_id == 7
    assert agent_payload.model == "deepseek-chat"
    assert agent_payload.file_ids == [3, 5]
    assert agent_payload.messages is None

    assert legacy_payload.source == "legacy_messages"
    assert legacy_payload.user_content == "旧路径仍然可用吗？"
    assert legacy_payload.session_id == 7
    assert legacy_payload.model == "deepseek-chat"
    assert legacy_payload.file_ids == []
    assert legacy_payload.messages == [
        {"role": "system", "content": "SYSTEM_PROMPT"},
        {"role": "user", "content": "旧路径仍然可用吗？"},
    ]


@pytest.mark.asyncio
async def test_build_agent_request_includes_committed_proposal_status_in_recent_history(
    db_session: AsyncSession,
) -> None:
    chat_session = ChatSession(title="proposal-status", created_at=utc_now(), updated_at=utc_now())
    db_session.add(chat_session)
    await db_session.flush()
    db_session.add_all(
        [
            ChatMessage(
                session_id=chat_session.id,
                role="user",
                content="先给我一张周一恢复卡。",
                suggestion=None,
                created_at=utc_now(),
            ),
            ChatMessage(
                session_id=chat_session.id,
                role="assistant",
                content="已生成一张周一恢复卡，等待确认。",
                suggestion={
                    "proposalId": "proposal-1",
                    "kind": "day_plan_replace",
                    "day": "Monday",
                    "summary": "先把周一改成恢复日。",
                    "status": "committed",
                },
                created_at=utc_now(),
            ),
        ]
    )
    await db_session.commit()

    request = await build_agent_request(
        session=db_session,
        session_id=chat_session.id,
        user_input="继续调整周一，给我第二张卡。",
        model_config={"model": "provider_deepseek_main::deepseek-v4-flash"},
    )

    rendered = "\n".join(message["content"] for message in request.messages if message["role"] != "system")
    assert "建议状态：committed" in rendered
    assert "proposalId=proposal-1" in rendered
