from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.api import chat as chat_api
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


class FakeDeepSeekClient:
    def __init__(self, replies: dict[str, Any]) -> None:
        self.replies = replies
        self.calls: list[list[dict[str, Any]]] = []

    async def request_chat(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        stream: bool = False,
    ) -> Any:
        del model, stream
        self.calls.append(messages)
        user_content = next(
            (
                message.get("content")
                for message in reversed(messages)
                if message.get("role") == "user"
            ),
            "",
        )
        reply = self.replies.get(user_content, "默认后台回复")
        if isinstance(reply, Exception):
            raise reply
        return reply


@pytest_asyncio.fixture
async def api_client(tmp_path: Path) -> AsyncIterator[tuple[AsyncClient, FakeDeepSeekClient]]:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'background-worker.db'}"
    engine, session_factory = create_engine_and_session_factory(database_url)
    fake_client = FakeDeepSeekClient(
        {
            "今天腿很累，周三怎么调？": '建议周三降低容量。\n---JSON---\n{"day":"Wednesday","summary":"降容量"}',
            "第一条问题": "第一条后台回复",
            "第二条问题": "第二条后台回复",
            "返回空回复": "",
        }
    )

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_get_db_session() -> AsyncIterator:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    chat_api.initialize_background_worker(
        session_factory=session_factory,
        client_factory=lambda: fake_client,
        default_model="deepseek-chat",
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, fake_client

    app.dependency_overrides.clear()
    chat_api.initialize_background_worker(None)
    await engine.dispose()


def build_messages(user_content: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": "SYSTEM_PROMPT"},
        {"role": "user", "content": user_content},
    ]


async def wait_for_task(client: AsyncClient, task_id: str) -> dict[str, Any]:
    for _ in range(20):
        response = await client.get(f"/api/chat/background/{task_id}")
        assert response.status_code == 200
        payload = response.json()
        if payload["status"] in {"succeeded", "failed"}:
            return payload
        await asyncio.sleep(0.01)

    pytest.fail(f"后台任务 {task_id} 未在预期时间内结束")


@pytest.mark.asyncio
async def test_background_task_finishes_and_persists_chat_turn(
    api_client: tuple[AsyncClient, FakeDeepSeekClient],
):
    client, _fake_client = api_client
    session_response = await client.get("/api/chat/sessions/default")
    session_id = session_response.json()["id"]

    submit_response = await client.post(
        f"/api/chat/{session_id}/background",
        json={"messages": build_messages("今天腿很累，周三怎么调？")},
    )

    assert submit_response.status_code == 200
    task_id = submit_response.json()["task_id"]
    result = await wait_for_task(client, task_id)

    assert result["status"] == "succeeded"
    assert result["result"] == {
        "text": "建议周三降低容量。",
        "suggestion": {"day": "Wednesday", "summary": "降容量"},
    }

    messages_response = await client.get(f"/api/chat/sessions/{session_id}/messages")
    assert messages_response.status_code == 200
    stored_messages = messages_response.json()
    assert [(message["role"], message["content"]) for message in stored_messages] == [
        ("user", "今天腿很累，周三怎么调？"),
        ("assistant", "建议周三降低容量。"),
    ]
    assert stored_messages[1]["suggestion"] == {"day": "Wednesday", "summary": "降容量"}


@pytest.mark.asyncio
async def test_background_concurrent_tasks_keep_results_isolated(
    api_client: tuple[AsyncClient, FakeDeepSeekClient],
):
    client, _fake_client = api_client
    first_session_id = (await client.post("/api/chat/sessions", json={"title": "A"})).json()["id"]
    second_session_id = (await client.post("/api/chat/sessions", json={"title": "B"})).json()["id"]

    first_submit = await client.post(
        f"/api/chat/{first_session_id}/background",
        json={"messages": build_messages("第一条问题")},
    )
    second_submit = await client.post(
        f"/api/chat/{second_session_id}/background",
        json={"messages": build_messages("第二条问题")},
    )

    assert first_submit.status_code == 200
    assert second_submit.status_code == 200
    first_task_id = first_submit.json()["task_id"]
    second_task_id = second_submit.json()["task_id"]
    assert first_task_id != second_task_id

    first_result = await wait_for_task(client, first_task_id)
    second_result = await wait_for_task(client, second_task_id)

    assert first_result["status"] == "succeeded"
    assert second_result["status"] == "succeeded"
    assert first_result["result"]["text"] == "第一条后台回复"
    assert second_result["result"]["text"] == "第二条后台回复"

    first_messages = (await client.get(f"/api/chat/sessions/{first_session_id}/messages")).json()
    second_messages = (await client.get(f"/api/chat/sessions/{second_session_id}/messages")).json()
    assert [message["content"] for message in first_messages] == ["第一条问题", "第一条后台回复"]
    assert [message["content"] for message in second_messages] == ["第二条问题", "第二条后台回复"]


@pytest.mark.asyncio
async def test_unknown_background_task_returns_explicit_status(
    api_client: tuple[AsyncClient, FakeDeepSeekClient],
):
    client, _fake_client = api_client

    response = await client.get("/api/chat/background/not-exist")

    assert response.status_code == 200
    assert response.json() == {
        "task_id": "not-exist",
        "status": "not_found",
        "result": None,
        "message": "未找到对应的后台思考任务。",
    }


@pytest.mark.asyncio
async def test_background_task_failed_status_does_not_persist_dirty_assistant(
    api_client: tuple[AsyncClient, FakeDeepSeekClient],
):
    client, _fake_client = api_client
    session_id = (await client.post("/api/chat/sessions", json={"title": "失败任务"})).json()["id"]

    submit_response = await client.post(
        f"/api/chat/{session_id}/background",
        json={"messages": build_messages("返回空回复")},
    )

    assert submit_response.status_code == 200
    result = await wait_for_task(client, submit_response.json()["task_id"])

    assert result["status"] == "failed"
    assert result["result"] is None
    assert "没有可展示的消息内容" in result["message"]

    messages_response = await client.get(f"/api/chat/sessions/{session_id}/messages")
    assert messages_response.status_code == 200
    assert messages_response.json() == []
