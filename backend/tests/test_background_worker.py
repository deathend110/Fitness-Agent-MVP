from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
import json
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.agent.adopt_plan import clear_plan_change_proposals
from backend.agent.deepseek_client import DeepSeekChatResult
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
    def __init__(self, replies: dict[str, Any]) -> None:
        self.replies = replies
        self.calls: list[dict[str, Any]] = []

    async def request_chat(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        stream: bool = False,
        **_: Any,
    ) -> Any:
        del stream
        self.calls.append(
            {
                "messages": messages,
                "model": model,
                "thinking": _.get("thinking"),
                "reasoning_effort": _.get("reasoning_effort"),
            }
        )
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
        del model, tools, tool_choice, stream
        self.calls.append({"messages": messages})
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
                                    "summary": "把深蹲百分比下调，给疲劳留余量。",
                                    "changes": [
                                        {
                                            "action": "update",
                                            "exerciseName": "深蹲",
                                            "field": "pct",
                                            "newValue": 0.7,
                                        }
                                    ],
                                },
                                ensure_ascii=False,
                            ),
                        },
                    }
                ],
            )
        return DeepSeekChatResult(content="已生成一张训练计划调整卡，等你确认后写回。")


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
        del model, tools, tool_choice, stream
        self.calls.append({"messages": messages})
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
        return DeepSeekChatResult(content="已生成一张单日训练计划卡，等你确认后写回。")


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
    clear_plan_change_proposals()
    chat_api.initialize_background_worker(
        session_factory=session_factory,
        client_factory=lambda: fake_client,
        default_model="deepseek-chat",
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        setattr(client, "_session_factory", session_factory)
        yield client, fake_client

    app.dependency_overrides.clear()
    clear_plan_change_proposals()
    chat_api.initialize_background_worker(None)
    await engine.dispose()


async def seed_uploaded_file(session_factory: Any) -> dict[str, Any]:
    async with session_factory() as session:
        uploaded = UploadedFile(
            original_name="减脂容量型计划.xlsx",
            stored_name="background-message-attachment.xlsx",
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            extension=".xlsx",
            size_bytes=10321,
            sha256="b" * 64,
            storage_path="background-message-attachment.xlsx",
            summary={"summary": "后台任务附件摘要"},
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


def build_messages(user_content: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": "SYSTEM_PROMPT"},
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
                    "template": {"loadMode": "percentage", "ref1RM": "squat", "sets": 5, "repsText": "5"},
                    "instance": {"pct": 0.75, "rpe": 8},
                    "ref1RM": "squat",
                    "pct": 0.75,
                    "rpe": 8,
                    "sets": 5,
                    "reps": 5,
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
async def test_background_task_with_file_ids_persists_attachment_snapshot(
    api_client: tuple[AsyncClient, FakeDeepSeekClient],
):
    client, _fake_client = api_client
    session_factory = getattr(client, "_session_factory")
    uploaded_file = await seed_uploaded_file(session_factory)
    session_id = (await client.post("/api/chat/sessions", json={"title": "附件后台"})).json()["id"]

    submit_response = await client.post(
        f"/api/chat/{session_id}/background",
        json={
            "userInput": "今天腿很累，周三怎么调？",
            "fileIds": [uploaded_file["fileId"]],
        },
    )

    assert submit_response.status_code == 200
    result = await wait_for_task(client, submit_response.json()["task_id"])

    assert result["status"] == "succeeded"

    messages_response = await client.get(f"/api/chat/sessions/{session_id}/messages")
    stored_messages = messages_response.json()
    assert stored_messages[0]["attachments"] == [uploaded_file]
    assert stored_messages[1]["attachments"] == []


@pytest.mark.asyncio
async def test_background_task_with_agent_user_input_generates_committable_plan_proposal(
    api_client: tuple[AsyncClient, FakeDeepSeekClient],
):
    client, _legacy_client = api_client
    fake_tool_client = FakeToolProposalClient()
    chat_api.initialize_background_worker(
        session_factory=chat_api.background_worker.session_factory,
        client_factory=lambda: fake_tool_client,
        default_model="deepseek-chat",
    )
    session_id = (await client.post("/api/chat/sessions", json={"title": "proposal"})).json()["id"]
    assert (await client.put("/api/weekly-plan", json=build_weekly_plan())).status_code == 200

    submit_response = await client.post(
        f"/api/chat/{session_id}/background",
        json={"userInput": "请根据我今天很累的状态，生成一张需要确认的深蹲调整卡。"},
    )

    assert submit_response.status_code == 200
    result = await wait_for_task(client, submit_response.json()["task_id"])

    assert result["status"] == "succeeded"
    suggestion = result["result"]["suggestion"]
    assert suggestion["proposalId"]
    assert suggestion["day"] == "Monday"
    assert suggestion["changes"][0]["newValue"] == 0.7

    messages_response = await client.get(f"/api/chat/sessions/{session_id}/messages")
    stored_messages = messages_response.json()
    assert stored_messages[1]["suggestion"]["proposalId"] == suggestion["proposalId"]

    committed = await client.post("/api/tools/plan/commit", json={"proposalId": suggestion["proposalId"]})
    assert committed.status_code == 200
    assert committed.json()["ok"] is True
    assert committed.json()["plan"]["Monday"]["exercises"][0]["pct"] == 0.7


@pytest.mark.asyncio
async def test_background_task_generates_committable_day_plan_replace_proposal(
    api_client: tuple[AsyncClient, FakeDeepSeekClient],
):
    client, _legacy_client = api_client
    fake_tool_client = FakeDayPlanProposalClient()
    chat_api.initialize_background_worker(
        session_factory=chat_api.background_worker.session_factory,
        client_factory=lambda: fake_tool_client,
        default_model="deepseek-chat",
    )
    session_id = (await client.post("/api/chat/sessions", json={"title": "day-plan-proposal"})).json()["id"]
    assert (await client.put("/api/weekly-plan", json=build_weekly_plan())).status_code == 200

    submit_response = await client.post(
        f"/api/chat/{session_id}/background",
        json={"userInput": "请给我一张需要确认的周一恢复型腿日卡。"},
    )

    assert submit_response.status_code == 200
    result = await wait_for_task(client, submit_response.json()["task_id"])

    assert result["status"] == "succeeded"
    suggestion = result["result"]["suggestion"]
    assert suggestion["proposalId"]
    assert suggestion["kind"] == "day_plan_replace"
    assert suggestion["dayPlan"]["type"] == "腿日"

    committed = await client.post("/api/tools/plan/commit", json={"proposalId": suggestion["proposalId"]})
    assert committed.status_code == 200
    assert committed.json()["ok"] is True
    assert committed.json()["plan"]["Monday"]["type"] == "腿日"
    assert committed.json()["plan"]["Monday"]["exercises"][0]["name"] == "深蹲"


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
async def test_background_task_forwards_thinking_config(
    api_client: tuple[AsyncClient, FakeDeepSeekClient],
):
    client, fake_client = api_client
    session_id = (await client.post("/api/chat/sessions", json={"title": "thinking"})).json()["id"]

    submit_response = await client.post(
        f"/api/chat/{session_id}/background",
        json={
            "userInput": "第一条问题",
            "model": "deepseek-v4-pro",
            "thinking": {"enabled": True, "budget": "max"},
        },
    )

    assert submit_response.status_code == 200
    result = await wait_for_task(client, submit_response.json()["task_id"])

    assert result["status"] == "succeeded"
    assert fake_client.calls[-1]["model"] == "deepseek-v4-pro"
    assert fake_client.calls[-1]["thinking"] == {"type": "enabled"}
    assert fake_client.calls[-1]["reasoning_effort"] == "max"


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
