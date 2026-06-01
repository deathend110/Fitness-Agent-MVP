from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.db.database import create_engine_and_session_factory, get_db_session
from backend.db.models import Base
from backend.main import app

pytestmark = [
    pytest.mark.filterwarnings(
        "error::pydantic.warnings.UnsupportedFieldAttributeWarning"
    ),
    pytest.mark.filterwarnings(
        "ignore:'asyncio.iscoroutinefunction' is deprecated:DeprecationWarning"
    ),
]


@pytest_asyncio.fixture
async def api_client(tmp_path: Path) -> AsyncIterator[AsyncClient]:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'chat-store.db'}"
    engine, session_factory = create_engine_and_session_factory(database_url)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_get_db_session() -> AsyncIterator:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()
    await engine.dispose()


def parse_api_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


@pytest.mark.asyncio
async def test_chat_session_appends_messages_full_history_and_refreshes_updated_at(api_client: AsyncClient):
    default_response = await api_client.get("/api/chat/sessions/default")

    assert default_response.status_code == 200
    default_session = default_response.json()
    assert default_session["title"] == "默认对话"

    create_response = await api_client.post(
        "/api/chat/sessions",
        json={"title": "训练复盘"},
    )

    assert create_response.status_code == 200
    created_session = create_response.json()
    assert created_session["title"] == "训练复盘"
    assert parse_api_datetime(created_session["createdAt"])
    before_updated_at = parse_api_datetime(created_session["updatedAt"])

    session_id = created_session["id"]
    suggestion = {
        "type": "weeklyPlanPatch",
        "reason": "疲劳偏高，降低周五硬拉量。",
        "patch": {
            "day": "Friday",
            "exerciseId": "deadlift-main",
            "changes": {"sets": 3, "rpe": 7},
        },
    }

    for index in range(25):
        payload = {
            "role": "assistant" if index == 10 else "user",
            "content": f"第 {index + 1} 条训练对话",
            "suggestion": suggestion if index == 10 else None,
        }
        response = await api_client.post(
            f"/api/chat/sessions/{session_id}/messages",
            json=payload,
        )
        assert response.status_code == 200

    messages_response = await api_client.get(f"/api/chat/sessions/{session_id}/messages")

    assert messages_response.status_code == 200
    messages = messages_response.json()
    assert len(messages) == 25
    assert [message["content"] for message in messages] == [
        f"第 {index + 1} 条训练对话" for index in range(25)
    ]
    assert messages[10]["role"] == "assistant"
    assert messages[10]["suggestion"] == suggestion

    sessions_response = await api_client.get("/api/chat/sessions")

    assert sessions_response.status_code == 200
    refreshed_session = next(
        session for session in sessions_response.json() if session["id"] == session_id
    )
    assert parse_api_datetime(refreshed_session["updatedAt"]) > before_updated_at


@pytest.mark.asyncio
async def test_chat_empty_session_null_suggestion_and_failure_cases(api_client: AsyncClient):
    default_response = await api_client.get("/api/chat/sessions/default")
    default_session_id = default_response.json()["id"]

    create_response = await api_client.post("/api/chat/sessions", json={})

    assert create_response.status_code == 200
    session_id = create_response.json()["id"]
    assert create_response.json()["title"] == "新对话"

    default_again_response = await api_client.get("/api/chat/sessions/default")

    assert default_again_response.status_code == 200
    assert default_again_response.json()["id"] == default_session_id

    empty_response = await api_client.get(f"/api/chat/sessions/{session_id}/messages")

    assert empty_response.status_code == 200
    assert empty_response.json() == []

    message_response = await api_client.post(
        f"/api/chat/sessions/{session_id}/messages",
        json={"role": "system", "content": "请以训练安全为优先。"},
    )

    assert message_response.status_code == 200
    assert message_response.json()["suggestion"] is None

    missing_session_response = await api_client.post(
        "/api/chat/sessions/999999/messages",
        json={"role": "user", "content": "这条消息不应该写入。"},
    )
    invalid_role_response = await api_client.post(
        f"/api/chat/sessions/{session_id}/messages",
        json={"role": "coach", "content": "非法角色。"},
    )

    assert missing_session_response.status_code == 404
    assert invalid_role_response.status_code == 422


@pytest.mark.asyncio
async def test_untitled_session_uses_first_user_prompt_as_history_title(api_client: AsyncClient):
    create_response = await api_client.post("/api/chat/sessions", json={})

    assert create_response.status_code == 200
    session_payload = create_response.json()
    session_id = session_payload["id"]
    assert session_payload["title"] == "新对话"

    first_prompt = "帮我根据今天腿部训练后的疲劳感，安排明天的恢复建议和有氧强度。"
    first_message_response = await api_client.post(
        f"/api/chat/sessions/{session_id}/messages",
        json={"role": "user", "content": first_prompt},
    )

    assert first_message_response.status_code == 200

    sessions_response = await api_client.get("/api/chat/sessions")
    assert sessions_response.status_code == 200
    renamed_session = next(session for session in sessions_response.json() if session["id"] == session_id)
    assert renamed_session["title"] == first_prompt[:48]

    second_message_response = await api_client.post(
        f"/api/chat/sessions/{session_id}/messages",
        json={"role": "user", "content": "再补充一下，我昨晚只睡了 6 小时。"},
    )
    assert second_message_response.status_code == 200

    sessions_after_second_message = await api_client.get("/api/chat/sessions")
    stable_session = next(
        session for session in sessions_after_second_message.json() if session["id"] == session_id
    )
    assert stable_session["title"] == first_prompt[:48]


@pytest.mark.asyncio
async def test_delete_chat_session_removes_it_from_history_and_messages(api_client: AsyncClient):
    create_response = await api_client.post("/api/chat/sessions", json={"title": "准备删除"})

    assert create_response.status_code == 200
    session_id = create_response.json()["id"]

    message_response = await api_client.post(
        f"/api/chat/sessions/{session_id}/messages",
        json={"role": "user", "content": "这条对话稍后会被删除。"},
    )
    assert message_response.status_code == 200

    delete_response = await api_client.delete(f"/api/chat/sessions/{session_id}")
    assert delete_response.status_code == 204

    sessions_response = await api_client.get("/api/chat/sessions")
    assert sessions_response.status_code == 200
    assert all(session["id"] != session_id for session in sessions_response.json())

    messages_response = await api_client.get(f"/api/chat/sessions/{session_id}/messages")
    assert messages_response.status_code == 404

    missing_delete_response = await api_client.delete(f"/api/chat/sessions/{session_id}")
    assert missing_delete_response.status_code == 404


@pytest.mark.asyncio
async def test_chat_message_attachment_snapshots_round_trip(api_client: AsyncClient):
    create_response = await api_client.post("/api/chat/sessions", json={"title": "附件回显"})

    assert create_response.status_code == 200
    session_id = create_response.json()["id"]

    attachments = [
        {
            "fileId": 7,
            "originalName": "减脂容量型计划.xlsx",
            "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "extension": ".xlsx",
            "sizeBytes": 10321,
        }
    ]

    message_response = await api_client.post(
        f"/api/chat/sessions/{session_id}/messages",
        json={
            "role": "user",
            "content": "这是带附件的训练问题。",
            "attachments": attachments,
        },
    )

    assert message_response.status_code == 200
    assert message_response.json()["attachments"] == attachments

    messages_response = await api_client.get(f"/api/chat/sessions/{session_id}/messages")

    assert messages_response.status_code == 200
    messages = messages_response.json()
    assert len(messages) == 1
    assert messages[0]["attachments"] == attachments
