from __future__ import annotations

from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.agent.deepseek_client import (
    DeepSeekChatResult,
    DeepSeekClient,
    DeepSeekClientError,
    DeepSeekStreamEvent,
)
from backend.api import chat as chat_api
from backend.db.database import create_engine_and_session_factory, get_db_session
from backend.db.models import Base
from backend.main import app
from backend.model_config.types import ProviderConfig
from backend.providers.gemini_client import GeminiNativeClient


@pytest.mark.asyncio
async def test_gemini_native_client_requests_generate_content_and_reads_text() -> None:
    request_snapshot: dict[str, object] = {}

    class FakeClient:
        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

        async def post(
            self,
            url: str,
            *,
            params: dict[str, str] | None = None,
            json: dict[str, object] | None = None,
            headers: dict[str, str] | None = None,
        ):
            request_snapshot["url"] = url
            request_snapshot["params"] = params or {}
            request_snapshot["json"] = json or {}
            request_snapshot["headers"] = headers or {}

            class Response:
                status_code = 200
                is_success = True

                def json(self) -> dict[str, object]:
                    return {
                        "candidates": [
                            {
                                "content": {
                                    "parts": [
                                        {"text": "先做动态热身，主项强度控制在 RPE 7。"},
                                    ]
                                }
                            }
                        ],
                        "usageMetadata": {
                            "promptTokenCount": 123,
                            "candidatesTokenCount": 45,
                            "totalTokenCount": 168,
                        },
                    }

            return Response()

    client = GeminiNativeClient(
        api_key="AIza-test",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        client_factory=lambda **_: FakeClient(),
    )
    result = await client.request_chat_with_usage(
        messages=[
            {"role": "system", "content": "你是 AI 健身教练。"},
            {"role": "user", "content": "今天腿很酸，明天怎么练？"},
        ],
        model="gemini-2.5-flash",
        thinking={"type": "enabled", "budget": "standard"},
    )

    assert request_snapshot["url"] == "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    assert request_snapshot["params"] == {"key": "AIza-test"}
    assert request_snapshot["headers"] == {}
    assert request_snapshot["json"]["systemInstruction"]["parts"][0]["text"] == "你是 AI 健身教练。"
    assert request_snapshot["json"]["contents"][0]["parts"][0]["text"] == "今天腿很酸，明天怎么练？"
    assert result.content == "先做动态热身，主项强度控制在 RPE 7。"
    assert result.usage == {
        "prompt_tokens": 123,
        "completion_tokens": 45,
        "total_tokens": 168,
    }


@pytest.mark.asyncio
async def test_gemini_native_client_maps_auto_tool_choice_to_function_calling_config() -> None:
    request_snapshot: dict[str, object] = {}

    class FakeClient:
        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

        async def post(
            self,
            url: str,
            *,
            params: dict[str, str] | None = None,
            json: dict[str, object] | None = None,
            headers: dict[str, str] | None = None,
        ):
            request_snapshot["url"] = url
            request_snapshot["params"] = params or {}
            request_snapshot["json"] = json or {}
            request_snapshot["headers"] = headers or {}

            class Response:
                status_code = 200
                is_success = True

                def json(self) -> dict[str, object]:
                    return {
                        "candidates": [
                            {
                                "content": {
                                    "parts": [
                                        {
                                            "functionCall": {
                                                "name": "get_weekly_plan",
                                                "args": {},
                                                "id": "call_weekly",
                                            }
                                        }
                                    ]
                                }
                            }
                        ]
                    }

            return Response()

    client = GeminiNativeClient(
        api_key="AIza-test",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        client_factory=lambda **_: FakeClient(),
    )
    await client.generate_content_raw(
        messages=[{"role": "user", "content": "先读取本周计划"}],
        model="gemini-2.5-flash",
        tools=[
            {
                "functionDeclarations": [
                    {
                        "name": "get_weekly_plan",
                        "description": "读取当前周计划",
                        "parameters": {"type": "object", "properties": {}},
                    }
                ]
            }
        ],
        tool_choice="auto",
    )

    assert request_snapshot["json"]["toolConfig"] == {
        "functionCallingConfig": {"mode": "AUTO"}
    }


class _FakeStreamResponse:
    """模拟 httpx streaming 响应：暴露 is_success / status_code 与 aiter_lines。"""

    def __init__(self, *, lines: list[str], status_code: int = 200, is_success: bool = True) -> None:
        self._lines = lines
        self.status_code = status_code
        self.is_success = is_success

    async def __aenter__(self) -> "_FakeStreamResponse":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False

    async def aiter_lines(self):
        for line in self._lines:
            yield line


def _make_stream_client_factory(lines: list[str], snapshot: dict[str, object]):
    """构造一个 client_factory，stream() 回放给定 SSE 行并记录请求 url/params。"""

    class FakeClient:
        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

        def stream(
            self,
            method: str,
            url: str,
            *,
            params: dict[str, str] | None = None,
            json: dict[str, object] | None = None,
            headers: dict[str, str] | None = None,
        ) -> _FakeStreamResponse:
            snapshot["method"] = method
            snapshot["url"] = url
            snapshot["params"] = params or {}
            snapshot["json"] = json or {}
            snapshot["headers"] = headers or {}
            return _FakeStreamResponse(lines=lines)

    return lambda **_: FakeClient()


def _sse(payload: dict[str, object]) -> str:
    import json as _json

    return "data: " + _json.dumps(payload, ensure_ascii=False)


@pytest.mark.asyncio
async def test_gemini_native_client_streams_incremental_text_then_usage() -> None:
    snapshot: dict[str, object] = {}
    lines = [
        _sse({"candidates": [{"content": {"parts": [{"text": "第一段"}]}}]}),
        "",
        _sse({"candidates": [{"content": {"parts": [{"text": "第二段"}]}}]}),
        "",
        _sse(
            {
                "candidates": [
                    {
                        "content": {"parts": [{"text": "第三段"}]},
                        "finishReason": "STOP",
                    }
                ],
                "usageMetadata": {
                    "promptTokenCount": 10,
                    "candidatesTokenCount": 5,
                    "totalTokenCount": 15,
                },
            }
        ),
        "",
    ]

    client = GeminiNativeClient(
        api_key="AIza-test",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        client_factory=_make_stream_client_factory(lines, snapshot),
    )
    events = [
        event
        async for event in client.stream_chat_with_usage(
            messages=[{"role": "user", "content": "给我一个恢复建议"}],
            model="gemini-2.5-flash",
        )
    ]

    assert events == [
        DeepSeekStreamEvent(text="第一段"),
        DeepSeekStreamEvent(text="第二段"),
        DeepSeekStreamEvent(text="第三段"),
        DeepSeekStreamEvent(usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}),
    ]
    assert str(snapshot["url"]).endswith(":streamGenerateContent")
    assert snapshot["params"] == {"key": "AIza-test", "alt": "sse"}


@pytest.mark.asyncio
async def test_gemini_native_client_stream_tolerates_empty_parts_final_chunk() -> None:
    # MAX_TOKENS 收尾块只带 finishReason、没有 parts 文本，不能崩，且要正常完成。
    snapshot: dict[str, object] = {}
    lines = [
        _sse({"candidates": [{"content": {"parts": [{"text": "仅有的一段"}]}}]}),
        "",
        _sse({"candidates": [{"finishReason": "MAX_TOKENS"}]}),
        "",
    ]

    client = GeminiNativeClient(
        api_key="AIza-test",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        client_factory=_make_stream_client_factory(lines, snapshot),
    )
    events = [
        event
        async for event in client.stream_chat_with_usage(
            messages=[{"role": "user", "content": "给我一个恢复建议"}],
            model="gemini-2.5-flash",
        )
    ]

    assert events == [DeepSeekStreamEvent(text="仅有的一段")]


@pytest.mark.asyncio
async def test_gemini_native_client_stream_raises_on_malformed_json_line() -> None:
    snapshot: dict[str, object] = {}
    lines = [
        "data: {not valid json",
        "",
    ]

    client = GeminiNativeClient(
        api_key="AIza-test",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        client_factory=_make_stream_client_factory(lines, snapshot),
    )

    with pytest.raises(DeepSeekClientError) as exc_info:
        async for _ in client.stream_chat_with_usage(
            messages=[{"role": "user", "content": "给我一个恢复建议"}],
            model="gemini-2.5-flash",
        ):
            pass

    assert exc_info.value.code == "stream_parse_error"


@pytest.mark.asyncio
async def test_gemini_native_client_stream_raises_when_no_finish_reason() -> None:
    # 流在没有任何 finishReason 的情况下结束，视为中途中断。
    snapshot: dict[str, object] = {}
    lines = [
        _sse({"candidates": [{"content": {"parts": [{"text": "半截内容"}]}}]}),
        "",
    ]

    client = GeminiNativeClient(
        api_key="AIza-test",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        client_factory=_make_stream_client_factory(lines, snapshot),
    )

    with pytest.raises(DeepSeekClientError) as exc_info:
        async for _ in client.stream_chat_with_usage(
            messages=[{"role": "user", "content": "给我一个恢复建议"}],
            model="gemini-2.5-flash",
        ):
            pass

    assert exc_info.value.code == "stream_interrupted"


@pytest.mark.asyncio
async def test_gemini_native_client_stream_raises_when_no_text_yielded() -> None:
    # 只有 finishReason 块、全程没有任何可展示文本，应报 empty_content。
    snapshot: dict[str, object] = {}
    lines = [
        _sse({"candidates": [{"finishReason": "STOP"}]}),
        "",
    ]

    client = GeminiNativeClient(
        api_key="AIza-test",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        client_factory=_make_stream_client_factory(lines, snapshot),
    )

    with pytest.raises(DeepSeekClientError) as exc_info:
        async for _ in client.stream_chat_with_usage(
            messages=[{"role": "user", "content": "给我一个恢复建议"}],
            model="gemini-2.5-flash",
        ):
            pass

    assert exc_info.value.code == "empty_content"


def test_build_provider_bound_client_returns_gemini_native_client_for_gemini_provider() -> None:
    fallback_client = DeepSeekClient(api_key="sk-test", base_url="https://api.deepseek.com")
    provider = ProviderConfig(
        id="provider_gemini_ai_studio",
        type="gemini_native",
        label="Gemini",
        enabled=True,
        apiKey="AIza-test",
        baseUrl="https://generativelanguage.googleapis.com/v1beta",
        selectedModels=[{"remoteId": "gemini-2.5-flash", "label": "Gemini 2.5 Flash", "enabled": True}],
    )

    provider_client = chat_api.build_provider_bound_client(provider, fallback_client)

    assert isinstance(provider_client, GeminiNativeClient)


@pytest_asyncio.fixture
async def api_client(tmp_path: Path) -> AsyncClient:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'gemini-client.db'}"
    engine, session_factory = create_engine_and_session_factory(database_url)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_get_db_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_chat_reply_routes_gemini_model_ref_to_gemini_client(
    api_client: AsyncClient,
    monkeypatch,
) -> None:
    session_id = (await api_client.post("/api/chat/sessions", json={"title": "gemini-runtime"})).json()["id"]
    calls: list[dict[str, object]] = []

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

        async def request_chat_with_usage(
            self,
            *,
            messages: list[dict[str, object]],
            model: str,
            stream: bool = False,
            **_: object,
        ) -> DeepSeekChatResult:
            calls.append({"messages": messages, "model": model, "stream": stream})
            return DeepSeekChatResult(content="Gemini 运行时聊天已接管。")

    class FakeRuntime:
        default_model_ref = "provider_gemini_main::gemini-2.5-flash"

        def resolve_model_ref(self, model_ref: str):
            assert model_ref == "provider_gemini_main::gemini-2.5-flash"
            return (
                type(
                    "Provider",
                    (),
                    {
                        "type": "gemini_native",
                        "api_key": "AIza-test",
                        "base_url": "https://generativelanguage.googleapis.com/v1beta",
                        "label": "Gemini",
                    },
                )(),
                "gemini-2.5-flash",
            )

    monkeypatch.setattr(chat_api, "get_provider_runtime", lambda: FakeRuntime())
    monkeypatch.setattr(
        chat_api,
        "build_provider_bound_client",
        lambda provider, fallback_client, timeout=None: FakeGeminiClient(
            api_key=provider.api_key,
            base_url=provider.base_url,
            timeout=timeout or 30.0,
        ),
    )
    app.dependency_overrides[chat_api.get_deepseek_client] = lambda: DeepSeekClient(
        api_key="sk-test",
        base_url="https://api.deepseek.com",
    )

    response = await api_client.post(
        "/api/chat/reply",
        json={
            "sessionId": session_id,
            "messages": [{"role": "user", "content": "今天练什么？"}],
            "model": "provider_gemini_main::gemini-2.5-flash",
        },
    )

    assert response.status_code == 200
    assert response.json()["text"] == "Gemini 运行时聊天已接管。"
    assert calls[0]["constructed"] is True
    assert calls[1]["model"] == "gemini-2.5-flash"

    app.dependency_overrides.pop(chat_api.get_deepseek_client, None)
