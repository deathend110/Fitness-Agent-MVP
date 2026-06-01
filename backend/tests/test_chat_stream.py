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
from backend.db.models import Base, UploadedFile, utc_now
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

    async def stream_chat(self, *, messages: list[dict[str, Any]], model: str, **_: Any) -> AsyncIterator[str]:
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
        **_: Any,
    ) -> str:
        del messages, model, stream
        if self.error is not None:
            raise self.error
        return "".join(self.chunks)


class FakeToolProposalClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

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
        del model, tools, stream
        self.calls.append(
            {
                "messages": messages,
                "thinking": _.get("thinking"),
                "reasoning_effort": _.get("reasoning_effort"),
                "tool_choice": tool_choice,
            }
        )
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


class FakeDayPlanProposalClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

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
        del model, tools, stream
        self.calls.append(
            {
                "messages": messages,
                "thinking": _.get("thinking"),
                "reasoning_effort": _.get("reasoning_effort"),
                "tool_choice": tool_choice,
            }
        )
        if len(self.calls) == 1:
            return DeepSeekChatResult(
                content="",
                tool_calls=[
                    {
                        "id": "call_day_plan",
                        "type": "function",
                        "function": {
                            "name": "propose_day_plan_replace",
                            "arguments": json.dumps(
                                {
                                    "day": "Monday",
                                    "summary": "把周一改成恢复型腿日。",
                                    "dayPlan": {
                                        "type": "腿日",
                                        "exercises": [
                                            {
                                                "name": "深蹲",
                                                "tier": "main",
                                                "template": {
                                                    "loadMode": "percentage",
                                                    "ref1RM": "squat",
                                                    "setType": "straight",
                                                    "sets": 3,
                                                    "repsText": "5",
                                                },
                                                "instance": {
                                                    "pct": 0.7,
                                                    "kg": None,
                                                    "rpe": 7,
                                                    "note": "恢复周主项",
                                                },
                                                "ref1RM": "squat",
                                                "pct": 0.7,
                                                "kg": None,
                                                "sets": 3,
                                                "reps": 5,
                                                "rpe": 7,
                                                "note": "恢复周主项",
                                            }
                                        ],
                                    },
                                },
                                ensure_ascii=False,
                            ),
                        },
                    }
                ],
            )
        return DeepSeekChatResult(content="已生成一张单日训练计划卡。")


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
        setattr(client, "_session_factory", session_factory)
        yield client

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest_asyncio.fixture
async def uploaded_file(api_client: AsyncClient) -> dict[str, Any]:
    session_factory = getattr(api_client, "_session_factory")
    async with session_factory() as session:
        uploaded = UploadedFile(
            original_name="减脂容量型计划.xlsx",
            stored_name="test-message-attachment.xlsx",
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            extension=".xlsx",
            size_bytes=10321,
            sha256="a" * 64,
            storage_path="test-message-attachment.xlsx",
            summary={"summary": "容量型减脂计划摘要"},
            parser_status="parsed",
            parser_error=None,
            created_at=utc_now(),
        )
        session.add(uploaded)
        await session.commit()
        await session.refresh(uploaded)
        return {
            "fileId": uploaded.id,
            "originalName": uploaded.original_name,
            "mimeType": uploaded.mime_type,
            "extension": uploaded.extension,
            "sizeBytes": uploaded.size_bytes,
        }


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
            "thinking": json.dumps({"enabled": True, "budget": "max"}),
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
    assert fake_client.calls[0]["thinking"] == {"type": "enabled"}
    assert fake_client.calls[0]["reasoning_effort"] == "max"
    assert fake_client.calls[0]["tool_choice"] is None


@pytest.mark.asyncio
async def test_agent_stream_emits_day_plan_replace_proposal(
    api_client: AsyncClient,
):
    fake_client = FakeDayPlanProposalClient()
    app.dependency_overrides[chat_api.get_deepseek_client] = lambda: fake_client
    default_session = (await api_client.get("/api/chat/sessions/default")).json()
    assert (await api_client.put("/api/weekly-plan", json=build_weekly_plan())).status_code == 200

    response = await api_client.get(
        "/api/chat/stream",
        params={
            "session_id": default_session["id"],
            "userInput": "请给我一张周一恢复型腿日卡片。",
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
    assert events[1]["data"]["proposal"]["kind"] == "day_plan_replace"
    assert events[1]["data"]["proposal"]["dayPlan"]["type"] == "腿日"
    assert events[1]["data"]["proposal"]["dayPlan"]["exercises"][0]["name"] == "深蹲"


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


@pytest.mark.asyncio
async def test_chat_stream_persists_user_attachment_snapshot_and_empty_assistant_attachments(
    api_client: AsyncClient,
    uploaded_file: dict[str, Any],
):
    fake_client = FakeDeepSeekClient(["带附件的回复。"])
    app.dependency_overrides[chat_api.get_deepseek_client] = lambda: fake_client
    default_session = (await api_client.get("/api/chat/sessions/default")).json()

    response = await api_client.get(
        "/api/chat/stream",
        params={
            "session_id": default_session["id"],
            "userInput": "请基于我上传的文件给建议。",
            "fileIds": [str(uploaded_file["fileId"])],
        },
    )

    assert response.status_code == 200
    events = parse_sse_events(response.text)
    assert [event["event"] for event in events] == ["delta", "suggestion", "done"]

    messages_response = await api_client.get(
        f"/api/chat/sessions/{default_session['id']}/messages"
    )
    stored_messages = messages_response.json()

    assert len(stored_messages) == 2
    assert stored_messages[0]["role"] == "user"
    assert stored_messages[0]["attachments"] == [uploaded_file]
    assert stored_messages[1]["role"] == "assistant"
    assert stored_messages[1]["attachments"] == []
