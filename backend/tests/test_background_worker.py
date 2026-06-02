from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
import json
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.agent.chat_session import OpenAICompatibleRuntimeClient, build_provider_bound_client
from backend.agent.adopt_plan import clear_plan_change_proposals
from backend.agent.deepseek_client import DeepSeekChatResult, DeepSeekClient
from backend.agent.tool_loop import ToolLoopResult
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


class FakeOpenAICompatibleResponsesBackgroundClient:
    def __init__(self, *, final_text: str = "已生成一张训练计划调整卡，等你确认后写回。") -> None:
        self.final_text = final_text
        self.response_calls: list[dict[str, Any]] = []

    async def request_responses_with_usage(
        self,
        *,
        input_items: list[dict[str, Any]],
        model: str,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        self.response_calls.append(
            {
                "input_items": input_items,
                "model": model,
                "tools": tools,
                "tool_choice": tool_choice,
            }
        )
        if tools and len(self.response_calls) == 1:
            return {
                "output_text": "",
                "output": [
                    {
                        "type": "function_call",
                        "call_id": "call_propose",
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
                    }
                ],
            }
        return {"output_text": self.final_text, "output": []}


class FakeAsyncHttpxResponse:
    def __init__(
        self,
        *,
        payload: dict[str, Any] | None = None,
        lines: list[str] | None = None,
        status_code: int = 200,
        reason_phrase: str = "OK",
    ) -> None:
        self._payload = payload or {}
        self._lines = lines or []
        self.status_code = status_code
        self.reason_phrase = reason_phrase
        self.is_success = 200 <= status_code < 300

    def json(self) -> dict[str, Any]:
        return self._payload

    async def aiter_lines(self):
        for line in self._lines:
            yield line


class FakeAsyncHttpxStreamContext:
    def __init__(self, response: FakeAsyncHttpxResponse) -> None:
        self.response = response

    async def __aenter__(self) -> FakeAsyncHttpxResponse:
        return self.response

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


class FakeAsyncHttpxClient:
    def __init__(
        self,
        *,
        post_response: FakeAsyncHttpxResponse | None = None,
        stream_response: FakeAsyncHttpxResponse | None = None,
        recorder: list[dict[str, Any]] | None = None,
        **_: Any,
    ) -> None:
        self.post_response = post_response or FakeAsyncHttpxResponse()
        self.stream_response = stream_response or FakeAsyncHttpxResponse(lines=["data: [DONE]"])
        self.recorder = recorder if recorder is not None else []

    async def __aenter__(self) -> "FakeAsyncHttpxClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False

    async def post(self, url: str, *, json: dict[str, Any], headers: dict[str, Any]) -> FakeAsyncHttpxResponse:
        self.recorder.append({"kind": "post", "url": url, "json": json, "headers": headers})
        return self.post_response

    def stream(
        self,
        method: str,
        url: str,
        *,
        json: dict[str, Any],
        headers: dict[str, Any],
    ) -> FakeAsyncHttpxStreamContext:
        self.recorder.append(
            {
                "kind": "stream",
                "method": method,
                "url": url,
                "json": json,
                "headers": headers,
            }
        )
        return FakeAsyncHttpxStreamContext(self.stream_response)


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


@pytest.mark.asyncio
async def test_background_task_uses_runtime_default_model_ref_when_model_missing(
    api_client: tuple[AsyncClient, FakeDeepSeekClient],
) -> None:
    client, fake_client = api_client
    session_id = (await client.post("/api/chat/sessions", json={"title": "runtime-default"})).json()["id"]

    class FakeRuntime:
        default_model_ref = "provider_deepseek_main::deepseek-v4-pro"

        def resolve_model_ref(self, model_ref: str):
            assert model_ref == "provider_deepseek_main::deepseek-v4-pro"
            return (
                type("Provider", (), {"type": "openai_compatible", "api_key": None, "base_url": ""})(),
                "deepseek-v4-pro",
            )

    chat_api.initialize_background_worker(
        session_factory=chat_api.background_worker.session_factory,
        client_factory=lambda: fake_client,
        runtime_provider=lambda: FakeRuntime(),
    )

    submit_response = await client.post(
        f"/api/chat/{session_id}/background",
        json={"messages": build_messages("第一条问题")},
    )

    assert submit_response.status_code == 200
    result = await wait_for_task(client, submit_response.json()["task_id"])

    assert result["status"] == "succeeded"
    assert fake_client.calls[-1]["model"] == "deepseek-v4-pro"


def test_background_worker_builds_gemini_client_for_gemini_provider(
    monkeypatch,
) -> None:
    calls: list[dict[str, Any]] = []

    class FakeGeminiClient:
        def __init__(self, *, api_key: str, base_url: str, timeout: float) -> None:
            calls.append(
                {
                    "api_key": api_key,
                    "base_url": base_url,
                    "timeout": timeout,
                    "constructed": True,
                }
            )

    provider = type(
        "Provider",
        (),
        {
            "type": "gemini_native",
            "api_key": "AIza-test",
            "base_url": "https://generativelanguage.googleapis.com/v1beta",
        },
    )()

    monkeypatch.setattr("backend.agent.background_worker.GeminiNativeClient", FakeGeminiClient)
    worker = chat_api.BackgroundWorker(
        session_factory=None,  # type: ignore[arg-type]
        client_factory=lambda: DeepSeekClient(api_key="sk-test", base_url="https://api.deepseek.com"),
    )
    client = worker._build_client_for_provider(
        provider,
        DeepSeekClient(api_key="sk-test", base_url="https://api.deepseek.com"),
    )

    assert isinstance(client, FakeGeminiClient)
    assert calls[0]["constructed"] is True


@pytest.mark.asyncio
async def test_background_task_uses_openai_compatible_responses_runtime_for_proposal_flow(
    api_client: tuple[AsyncClient, FakeDeepSeekClient],
) -> None:
    client, _legacy_client = api_client
    fake_responses_client = FakeOpenAICompatibleResponsesBackgroundClient()

    class FakeRuntime:
        default_model_ref = "provider_openai_responses::gpt-4.1-mini"

        def resolve_model_ref(self, model_ref: str):
            assert model_ref == "provider_openai_responses::gpt-4.1-mini"
            return (
                type(
                    "Provider",
                    (),
                    {
                        "type": "openai_compatible",
                        "api_key": "sk-openai",
                        "base_url": "https://api.openai.com",
                        "wire_api": "responses",
                        "api_path_mode": "append_v1",
                    },
                )(),
                "gpt-4.1-mini",
            )

    chat_api.initialize_background_worker(
        session_factory=chat_api.background_worker.session_factory,
        client_factory=lambda: fake_responses_client,
        runtime_provider=lambda: FakeRuntime(),
    )
    session_id = (await client.post("/api/chat/sessions", json={"title": "responses-proposal"})).json()["id"]
    assert (await client.put("/api/weekly-plan", json=build_weekly_plan())).status_code == 200

    submit_response = await client.post(
        f"/api/chat/{session_id}/background",
        json={
            "userInput": "请根据我今天很累的状态，生成一张需要确认的深蹲调整卡。",
            "model": "provider_openai_responses::gpt-4.1-mini",
        },
    )

    assert submit_response.status_code == 200
    result = await wait_for_task(client, submit_response.json()["task_id"])

    assert result["status"] == "succeeded"
    assert result["result"]["suggestion"]["proposalId"]
    assert result["result"]["suggestion"]["changes"][0]["newValue"] == 0.7
    assert fake_responses_client.response_calls[0]["model"] == "gpt-4.1-mini"


@pytest.mark.asyncio
async def test_background_task_returns_provider_aware_error_message_for_openai_provider(
    api_client: tuple[AsyncClient, FakeDeepSeekClient],
) -> None:
    client, _legacy_client = api_client

    class FakeFailureClient:
        async def request_chat(
            self,
            *,
            messages: list[dict[str, Any]],
            model: str,
            stream: bool = False,
            **_: Any,
        ) -> Any:
            del messages, model, stream
            raise chat_api.DeepSeekClientError(
                "OpenAI 请求失败（HTTP 401）：invalid api key",
                code="http_error",
            )

    class FakeRuntime:
        default_model_ref = "provider_openai_chat::gpt-4.1-mini"

        def resolve_model_ref(self, model_ref: str):
            assert model_ref == "provider_openai_chat::gpt-4.1-mini"
            return (
                type(
                    "Provider",
                    (),
                    {
                        "type": "openai_compatible",
                        "api_key": "sk-openai",
                        "base_url": "https://api.openai.com",
                        "wire_api": "chat_completions",
                        "api_path_mode": "append_v1",
                    },
                )(),
                "gpt-4.1-mini",
            )

    chat_api.initialize_background_worker(
        session_factory=chat_api.background_worker.session_factory,
        client_factory=lambda: FakeFailureClient(),
        runtime_provider=lambda: FakeRuntime(),
    )
    session_id = (await client.post("/api/chat/sessions", json={"title": "openai-failed"})).json()["id"]

    submit_response = await client.post(
        f"/api/chat/{session_id}/background",
        json={
            "messages": build_messages("第一条问题"),
            "model": "provider_openai_chat::gpt-4.1-mini",
        },
    )

    assert submit_response.status_code == 200
    result = await wait_for_task(client, submit_response.json()["task_id"])

    assert result["status"] == "failed"
    assert "OpenAI 请求失败" in result["message"]
    assert "DeepSeek" not in result["message"]


def test_background_worker_build_client_keeps_legacy_fallback_when_provider_missing() -> None:
    fallback_client = DeepSeekClient(api_key="sk-test", base_url="https://api.deepseek.com")
    worker = chat_api.BackgroundWorker(
        session_factory=None,  # type: ignore[arg-type]
        client_factory=lambda: fallback_client,
    )

    client = worker._build_client_for_provider(None, fallback_client)

    assert client is fallback_client


def test_build_provider_bound_client_prefers_openai_compatible_runtime_for_deepseek_provider_in_worker() -> None:
    fallback_client = DeepSeekClient(api_key="sk-test", base_url="https://api.deepseek.com")
    provider = type(
        "Provider",
        (),
        {
            "type": "openai_compatible",
            "api_key": "sk-provider",
            "base_url": "https://api.deepseek.com",
            "wire_api": "chat_completions",
            "api_path_mode": "raw_root",
            "label": "DeepSeek 主账号",
        },
    )()

    client = build_provider_bound_client(provider, fallback_client)

    assert isinstance(client, OpenAICompatibleRuntimeClient)
    assert not isinstance(client, DeepSeekClient)


@pytest.mark.asyncio
async def test_background_task_uses_openai_compatible_runtime_when_runtime_default_is_deepseek_model_ref(
    api_client: tuple[AsyncClient, FakeDeepSeekClient],
    monkeypatch,
) -> None:
    client, _legacy_client = api_client
    session_id = (await client.post("/api/chat/sessions", json={"title": "deepseek-runtime-default"})).json()["id"]
    observed_clients: list[Any] = []
    runtime_requests: list[dict[str, Any]] = []
    fallback_requests: list[dict[str, Any]] = []

    class FakeRuntime:
        default_model_ref = "provider_deepseek_main::deepseek-chat"

        def resolve_model_ref(self, model_ref: str):
            assert model_ref == "provider_deepseek_main::deepseek-chat"
            return (
                type(
                    "Provider",
                    (),
                    {
                        "type": "openai_compatible",
                        "api_key": "sk-provider",
                        "base_url": "https://api.deepseek.com",
                        "wire_api": "chat_completions",
                        "api_path_mode": "raw_root",
                        "label": "DeepSeek 主账号",
                    },
                )(),
                "deepseek-chat",
            )

    fallback_client = DeepSeekClient(
        api_key="sk-fallback",
        base_url="https://api.deepseek.com",
        client_factory=lambda **kwargs: FakeAsyncHttpxClient(
            recorder=fallback_requests,
            post_response=FakeAsyncHttpxResponse(
                payload={
                    "choices": [
                        {
                            "message": {
                                "content": "legacy fallback reply",
                            }
                        }
                    ]
                }
            ),
            **kwargs,
        ),
    )

    async def fake_run_tool_calling_chat(
        *,
        deepseek_client: Any,
        messages: list[dict[str, Any]],
        model: str,
        **_: Any,
    ) -> ToolLoopResult:
        observed_clients.append(deepseek_client)
        result = await deepseek_client.request_chat_with_usage(
            messages=messages,
            model=model,
        )
        return ToolLoopResult(
            content=result.content,
            messages=messages,
            tool_rounds=0,
            proposals=[],
        )

    monkeypatch.setattr("backend.agent.background_worker.run_tool_calling_chat", fake_run_tool_calling_chat)
    from backend.agent import background_worker as background_worker_module

    original_build_provider_bound_client = background_worker_module.build_provider_bound_client

    def build_runtime_client(provider, fallback_client, timeout=None):
        runtime_client = original_build_provider_bound_client(
            provider,
            fallback_client,
            timeout=timeout or 30.0,
        )
        if isinstance(runtime_client, OpenAICompatibleRuntimeClient):
            runtime_client.client_factory = lambda **kwargs: FakeAsyncHttpxClient(
                recorder=runtime_requests,
                post_response=FakeAsyncHttpxResponse(
                    payload={
                        "choices": [
                            {
                                "message": {
                                    "content": "DeepSeek 后台运行时回复。",
                                }
                            }
                        ]
                    }
                ),
                **kwargs,
            )
        return runtime_client

    monkeypatch.setattr("backend.agent.background_worker.build_provider_bound_client", build_runtime_client)
    chat_api.initialize_background_worker(
        session_factory=chat_api.background_worker.session_factory,
        client_factory=lambda: fallback_client,
        runtime_provider=lambda: FakeRuntime(),
    )

    submit_response = await client.post(
        f"/api/chat/{session_id}/background",
        json={"messages": build_messages("第一条问题")},
    )

    assert submit_response.status_code == 200
    result = await wait_for_task(client, submit_response.json()["task_id"])

    assert result["status"] == "succeeded"
    assert result["result"]["text"] == "DeepSeek 后台运行时回复。"
    assert isinstance(observed_clients[0], OpenAICompatibleRuntimeClient)
    assert runtime_requests[0]["kind"] == "post"
    assert runtime_requests[0]["url"] == "https://api.deepseek.com/chat/completions"
    assert runtime_requests[0]["json"]["model"] == "deepseek-chat"
    assert fallback_requests == []
