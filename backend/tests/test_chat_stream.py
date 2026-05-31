from __future__ import annotations

from collections.abc import AsyncIterator
import json
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.agent.deepseek_client import DeepSeekChatResult, DeepSeekClientError
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
    def __init__(
        self,
        chunks: list[str] | None = None,
        *,
        error: DeepSeekClientError | None = None,
        error_after_chunks: DeepSeekClientError | None = None,
    ) -> None:
        self.chunks = chunks or []
        self.error = error
        self.error_after_chunks = error_after_chunks

    async def stream_chat(self, *, messages: list[dict[str, Any]], model: str) -> AsyncIterator[str]:
        del messages, model
        if self.error is not None:
            raise self.error

        for chunk in self.chunks:
            yield chunk

        if self.error_after_chunks is not None:
            raise self.error_after_chunks

    async def request_chat(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        stream: bool = False,
    ) -> str:
        del messages, model, stream
        if self.error is not None:
            raise self.error
        return "".join(self.chunks)


class FakeToolProposalClient:
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
    ) -> DeepSeekChatResult:
        del model, tools, tool_choice, stream
        self.calls.append(messages)
        if len(self.calls) == 1:
            return DeepSeekChatResult(
                content="",
                tool_calls=[
                    {
                        "id": "call_propose",
                        "type": "function",
                        "function": {
                            "name": "propose_plan_change",
                            "arguments": json.dumps(
                                {
                                    "day": "Monday",
                                    "summary": "把深蹲 RPE 下调，降低疲劳风险。",
                                    "changes": [
                                        {
                                            "action": "update",
                                            "exerciseName": "深蹲",
                                            "field": "rpe",
                                            "newValue": 7,
                                        }
                                    ],
                                },
                                ensure_ascii=False,
                            ),
                        },
                    }
                ],
            )
        return DeepSeekChatResult(content="已生成一张需要你确认的训练计划调整卡。")


@pytest_asyncio.fixture
async def api_client(tmp_path: Path) -> AsyncIterator[AsyncClient]:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'chat-stream.db'}"
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


def parse_sse_events(raw_text: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []

    for block in raw_text.strip().split("\n\n"):
        event_name = ""
        data = ""

        for line in block.splitlines():
            if line.startswith("event:"):
                event_name = line.removeprefix("event:").strip()
            if line.startswith("data:"):
                data = line.removeprefix("data:").strip()

        if event_name:
            events.append({"event": event_name, "data": json.loads(data)})

    return events


def build_messages(user_content: str = "今天深蹲很累，周五硬拉要改吗？") -> list[dict[str, str]]:
    return [
        {"role": "system", "content": "SYSTEM_PROMPT"},
        {"role": "assistant", "content": "先观察疲劳。"},
        {"role": "user", "content": user_content},
    ]


def build_weekly_plan() -> dict[str, Any]:
    rest_day = {"type": "rest", "exercises": []}
    return {
        "Monday": {
            "type": "strength",
            "exercises": [
                {
                    "id": "sq",
                    "name": "深蹲",
                    "sets": 4,
                    "reps": 5,
                    "rpe": 9,
                }
            ],
        },
        "Tuesday": dict(rest_day),
        "Wednesday": dict(rest_day),
        "Thursday": dict(rest_day),
        "Friday": dict(rest_day),
        "Saturday": dict(rest_day),
        "Sunday": dict(rest_day),
    }


@pytest.mark.asyncio
async def test_chat_stream_emits_delta_suggestion_done_and_persists_clean_messages(
    api_client: AsyncClient,
):
    fake_client = FakeDeepSeekClient(
        [
            "建议周五硬拉降一点，先保住动作质量。\n",
            '---JSON---\n{"suggest_plan_update":true,"day":"Friday","summary":"降低硬拉强度"}',
        ]
    )
    app.dependency_overrides[chat_api.get_deepseek_client] = lambda: fake_client
    default_session = (await api_client.get("/api/chat/sessions/default")).json()

    response = await api_client.get(
        "/api/chat/stream",
        params={
            "session_id": default_session["id"],
            "messages": json.dumps(build_messages(), ensure_ascii=False),
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = parse_sse_events(response.text)

    assert [event["event"] for event in events] == [
        "delta",
        "delta",
        "suggestion",
        "done",
    ]
    assert events[0]["data"] == {"text": "建议周五硬拉降一点，先保住动作质量。\n"}
    assert events[1]["data"] == {
        "text": '---JSON---\n{"suggest_plan_update":true,"day":"Friday","summary":"降低硬拉强度"}'
    }
    assert events[2]["data"] == {
        "suggestion": {
            "suggest_plan_update": True,
            "day": "Friday",
            "summary": "降低硬拉强度",
        }
    }
    assert events[3]["data"] == {"text": "建议周五硬拉降一点，先保住动作质量。"}

    messages_response = await api_client.get(
        f"/api/chat/sessions/{default_session['id']}/messages"
    )
    stored_messages = messages_response.json()

    assert [(message["role"], message["content"]) for message in stored_messages] == [
        ("user", "今天深蹲很累，周五硬拉要改吗？"),
        ("assistant", "建议周五硬拉降一点，先保住动作质量。"),
    ]
    assert stored_messages[1]["suggestion"] == events[2]["data"]["suggestion"]


@pytest.mark.asyncio
async def test_chat_stream_emits_null_suggestion_for_plain_text_reply(
    api_client: AsyncClient,
):
    fake_client = FakeDeepSeekClient(["只建议今天降低一点容量。"])
    app.dependency_overrides[chat_api.get_deepseek_client] = lambda: fake_client
    default_session = (await api_client.get("/api/chat/sessions/default")).json()

    response = await api_client.get(
        "/api/chat/stream",
        params={
            "session_id": default_session["id"],
            "messages": json.dumps(build_messages(), ensure_ascii=False),
        },
    )

    assert response.status_code == 200
    events = parse_sse_events(response.text)

    assert [event["event"] for event in events] == ["delta", "suggestion", "done"]
    assert events[1]["data"] == {"suggestion": None}
    assert events[2]["data"] == {"text": "只建议今天降低一点容量。"}


@pytest.mark.asyncio
async def test_agent_stream_executes_tool_loop_and_emits_plan_proposal(
    api_client: AsyncClient,
):
    fake_client = FakeToolProposalClient()
    app.dependency_overrides[chat_api.get_deepseek_client] = lambda: fake_client
    default_session = (await api_client.get("/api/chat/sessions/default")).json()
    assert (await api_client.put("/api/weekly-plan", json=build_weekly_plan())).status_code == 200

    response = await api_client.get(
        "/api/chat/stream",
        params={
            "session_id": default_session["id"],
            "userInput": "请读取我的计划，并给出需要我确认的深蹲调整卡。",
        },
    )

    assert response.status_code == 200
    events = parse_sse_events(response.text)

    assert [event["event"] for event in events] == [
        "delta",
        "proposal",
        "suggestion",
        "done",
    ]
    assert events[0]["data"] == {"text": "已生成一张需要你确认的训练计划调整卡。"}
    assert events[1]["data"]["proposal"]["day"] == "Monday"
    assert events[1]["data"]["proposal"]["summary"] == "把深蹲 RPE 下调，降低疲劳风险。"
    assert events[1]["data"]["proposal"]["changes"][0]["newValue"] == 7
    assert events[1]["data"]["proposal"]["proposalId"]
    assert events[2]["data"] == {"suggestion": None}
    assert events[3]["data"] == {"text": "已生成一张需要你确认的训练计划调整卡。"}
    assert len(fake_client.calls) == 2


@pytest.mark.asyncio
async def test_chat_stream_emits_error_and_does_not_persist_partial_assistant(
    api_client: AsyncClient,
):
    fake_client = FakeDeepSeekClient(
        ["半截回复"],
        error=DeepSeekClientError(
            "未配置后端 DeepSeek API Key，请在 backend/.env 中设置 DEEPSEEK_API_KEY。",
            code="missing_api_key",
        ),
    )
    app.dependency_overrides[chat_api.get_deepseek_client] = lambda: fake_client
    default_session = (await api_client.get("/api/chat/sessions/default")).json()

    response = await api_client.get(
        "/api/chat/stream",
        params={
            "session_id": default_session["id"],
            "messages": json.dumps(build_messages(), ensure_ascii=False),
        },
    )

    assert response.status_code == 200
    events = parse_sse_events(response.text)

    assert [event["event"] for event in events] == ["error"]
    assert events[0]["data"]["code"] == "missing_api_key"
    assert "DeepSeek API Key" in events[0]["data"]["message"]

    messages_response = await api_client.get(
        f"/api/chat/sessions/{default_session['id']}/messages"
    )

    assert messages_response.json() == []


@pytest.mark.asyncio
async def test_chat_stream_rolls_back_when_upstream_breaks_after_delta(
    api_client: AsyncClient,
):
    fake_client = FakeDeepSeekClient(
        ["已经发给前端的半截回复"],
        error_after_chunks=DeepSeekClientError(
            "DeepSeek 流式响应在完成前中断，请稍后重试。",
            code="stream_interrupted",
        ),
    )
    app.dependency_overrides[chat_api.get_deepseek_client] = lambda: fake_client
    default_session = (await api_client.get("/api/chat/sessions/default")).json()

    response = await api_client.get(
        "/api/chat/stream",
        params={
            "session_id": default_session["id"],
            "messages": json.dumps(build_messages(), ensure_ascii=False),
        },
    )

    assert response.status_code == 200
    events = parse_sse_events(response.text)

    assert [event["event"] for event in events] == ["delta", "error"]
    assert events[0]["data"] == {"text": "已经发给前端的半截回复"}
    assert events[1]["data"]["code"] == "stream_interrupted"

    messages_response = await api_client.get(
        f"/api/chat/sessions/{default_session['id']}/messages"
    )

    assert messages_response.json() == []
