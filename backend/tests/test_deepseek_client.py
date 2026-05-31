from __future__ import annotations

from collections.abc import AsyncIterator, Callable

import pytest

from backend.agent.deepseek_client import DeepSeekClient, DeepSeekClientError


class FakeResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        json_data: object | None = None,
        json_error: Exception | None = None,
        lines: list[str] | None = None,
        reason_phrase: str = "OK",
    ) -> None:
        self.status_code = status_code
        self._json_data = json_data
        self._json_error = json_error
        self._lines = lines or []
        self.reason_phrase = reason_phrase

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300

    def json(self) -> object | None:
        if self._json_error is not None:
            raise self._json_error
        return self._json_data

    async def aiter_lines(self) -> AsyncIterator[str]:
        for line in self._lines:
            yield line


class FakeStreamContext:
    def __init__(self, response: FakeResponse) -> None:
        self._response = response

    async def __aenter__(self) -> FakeResponse:
        return self._response

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


class FakeAsyncClient:
    def __init__(
        self,
        *,
        post_responses: list[FakeResponse],
        stream_responses: list[FakeResponse],
        request_log: list[dict],
        **_: object,
    ) -> None:
        self._post_responses = post_responses
        self._stream_responses = stream_responses
        self._request_log = request_log

    async def __aenter__(self) -> FakeAsyncClient:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False

    async def post(self, url: str, *, json: dict, headers: dict) -> FakeResponse:
        self._request_log.append(
            {
                "method": "POST",
                "url": url,
                "json": json,
                "headers": headers,
            }
        )
        return self._post_responses.pop(0)

    def stream(self, method: str, url: str, *, json: dict, headers: dict) -> FakeStreamContext:
        self._request_log.append(
            {
                "method": method,
                "url": url,
                "json": json,
                "headers": headers,
            }
        )
        return FakeStreamContext(self._stream_responses.pop(0))


def build_client_factory(
    *,
    post_responses: list[FakeResponse] | None = None,
    stream_responses: list[FakeResponse] | None = None,
    request_log: list[dict] | None = None,
) -> tuple[Callable[..., FakeAsyncClient], list[dict]]:
    requests = request_log if request_log is not None else []
    queued_post_responses = list(post_responses or [])
    queued_stream_responses = list(stream_responses or [])

    def factory(**kwargs: object) -> FakeAsyncClient:
        return FakeAsyncClient(
            post_responses=queued_post_responses,
            stream_responses=queued_stream_responses,
            request_log=requests,
            **kwargs,
        )

    return factory, requests


async def collect_stream(stream: AsyncIterator[str]) -> list[str]:
    chunks: list[str] = []

    async for chunk in stream:
        chunks.append(chunk)

    return chunks


@pytest.mark.asyncio
async def test_request_chat_returns_full_text_for_non_stream_response():
    factory, requests = build_client_factory(
        post_responses=[
            FakeResponse(
                json_data={
                    "choices": [
                        {
                            "message": {
                                "content": "今天下肢疲劳偏高，主项先减一组。"
                            }
                        }
                    ]
                }
            )
        ]
    )
    client = DeepSeekClient(
        api_key="test-key",
        base_url="https://fake.deepseek.local",
        client_factory=factory,
    )

    result = await client.request_chat(
        messages=[{"role": "user", "content": "给我今天的训练建议"}],
        model="deepseek-v4-flash",
        stream=False,
    )

    assert result == "今天下肢疲劳偏高，主项先减一组。"
    assert requests == [
        {
            "method": "POST",
            "url": "https://fake.deepseek.local/chat/completions",
            "json": {
                "model": "deepseek-v4-flash",
                "messages": [{"role": "user", "content": "给我今天的训练建议"}],
                "stream": False,
            },
            "headers": {
                "Authorization": "Bearer test-key",
                "Content-Type": "application/json",
            },
        }
    ]


@pytest.mark.asyncio
async def test_request_chat_maps_http_error_to_unified_exception():
    factory, _ = build_client_factory(
        post_responses=[
            FakeResponse(
                status_code=401,
                reason_phrase="Unauthorized",
                json_data={"error": {"message": "Invalid API key"}},
            )
        ]
    )
    client = DeepSeekClient(api_key="bad-key", client_factory=factory)

    with pytest.raises(DeepSeekClientError) as exc_info:
        await client.request_chat(
            messages=[{"role": "user", "content": "hello"}],
            model="deepseek-chat",
            stream=False,
        )

    assert exc_info.value.status == 401
    assert exc_info.value.code == "http_error"
    assert exc_info.value.reason == "Invalid API key"
    assert "Invalid API key" in str(exc_info.value)
    assert "401" in str(exc_info.value)


@pytest.mark.asyncio
async def test_request_chat_raises_empty_content_when_non_stream_choices_are_empty():
    factory, _ = build_client_factory(
        post_responses=[
            FakeResponse(
                json_data={
                    "choices": [],
                }
            )
        ]
    )
    client = DeepSeekClient(api_key="test-key", client_factory=factory)

    with pytest.raises(DeepSeekClientError) as exc_info:
        await client.request_chat(
            messages=[{"role": "user", "content": "给我建议"}],
            model="deepseek-chat",
            stream=False,
        )

    assert exc_info.value.code == "empty_content"


@pytest.mark.asyncio
async def test_request_chat_maps_invalid_json_to_response_parse_error():
    factory, _ = build_client_factory(
        post_responses=[
            FakeResponse(
                json_error=ValueError("not valid json"),
            )
        ]
    )
    client = DeepSeekClient(api_key="test-key", client_factory=factory)

    with pytest.raises(DeepSeekClientError) as exc_info:
        await client.request_chat(
            messages=[{"role": "user", "content": "给我建议"}],
            model="deepseek-chat",
            stream=False,
        )

    assert exc_info.value.code == "response_parse_error"
    assert exc_info.value.reason == "not valid json"


@pytest.mark.asyncio
async def test_stream_chat_yields_delta_chunks_and_ignores_empty_choices():
    factory, requests = build_client_factory(
        stream_responses=[
            FakeResponse(
                lines=[
                    'data: {"choices":[{"delta":{"content":"先"}}]}',
                    'data: {"choices":[]}',
                    'data: {"choices":[{"delta":{"content":"做"}}]}',
                    'data: {"choices":[{"delta":{}}]}',
                    "data: [DONE]",
                ]
            )
        ]
    )
    client = DeepSeekClient(api_key="test-key", client_factory=factory)

    chunks = await collect_stream(
        client.stream_chat(
            messages=[{"role": "user", "content": "流式输出建议"}],
            model="deepseek-chat",
        )
    )

    assert chunks == ["先", "做"]
    assert requests == [
        {
            "method": "POST",
            "url": "https://api.deepseek.com/chat/completions",
            "json": {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": "流式输出建议"}],
                "stream": True,
            },
            "headers": {
                "Authorization": "Bearer test-key",
                "Content-Type": "application/json",
            },
        }
    ]


@pytest.mark.asyncio
async def test_stream_chat_raises_when_stream_finishes_without_displayable_text():
    factory, _ = build_client_factory(
        stream_responses=[
            FakeResponse(
                lines=[
                    'data: {"choices":[]}',
                    'data: {"choices":[{"delta":{}}]}',
                    "data: [DONE]",
                ]
            )
        ]
    )
    client = DeepSeekClient(api_key="test-key", client_factory=factory)

    with pytest.raises(DeepSeekClientError) as exc_info:
        await collect_stream(
            client.stream_chat(
                messages=[{"role": "user", "content": "空流式消息"}],
                model="deepseek-chat",
            )
        )

    assert exc_info.value.code == "empty_content"


@pytest.mark.asyncio
async def test_stream_chat_raises_clear_error_when_connection_breaks_before_done():
    factory, _ = build_client_factory(
        stream_responses=[
            FakeResponse(
                lines=[
                    'data: {"choices":[{"delta":{"content":"先热身"}}]}',
                ]
            )
        ]
    )
    client = DeepSeekClient(api_key="test-key", client_factory=factory)

    with pytest.raises(DeepSeekClientError) as exc_info:
        await collect_stream(
            client.stream_chat(
                messages=[{"role": "user", "content": "测试断流"}],
                model="deepseek-chat",
            )
        )

    assert exc_info.value.code == "stream_interrupted"


@pytest.mark.asyncio
async def test_request_chat_raises_missing_key_before_http_call():
    factory, requests = build_client_factory()
    client = DeepSeekClient(api_key="  ", client_factory=factory)

    with pytest.raises(DeepSeekClientError) as exc_info:
        await client.request_chat(
            messages=[{"role": "user", "content": "hello"}],
            model="deepseek-chat",
            stream=False,
        )

    assert exc_info.value.code == "missing_api_key"
    assert requests == []
