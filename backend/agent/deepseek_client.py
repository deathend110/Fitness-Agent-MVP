from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
import json
from json import JSONDecodeError
from typing import Any

import httpx


class DeepSeekClientError(Exception):
    """统一封装 DeepSeek 请求失败，便于 API 层后续做稳定映射。"""

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        code: str = "deepseek_error",
        reason: str = "",
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.reason = reason


@dataclass(frozen=True)
class DeepSeekChatResult:
    content: str
    usage: dict[str, int] | None = None
    reasoning_content: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


@dataclass(frozen=True)
class DeepSeekStreamEvent:
    text: str = ""
    usage: dict[str, int] | None = None


class DeepSeekClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        timeout: float = 30.0,
        client_factory: Callable[..., Any] = httpx.AsyncClient,
    ) -> None:
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client_factory = client_factory

    async def request_chat(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        stream: bool = False,
        thinking: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        reasoning_effort: str | None = None,
    ) -> str | AsyncIterator[str]:
        if stream:
            return self.stream_chat(
                messages=messages,
                model=model,
                thinking=thinking,
                reasoning_effort=reasoning_effort,
            )

        result = await self.request_chat_with_usage(
            messages=messages,
            model=model,
            stream=False,
            thinking=thinking,
            tools=tools,
            tool_choice=tool_choice,
            reasoning_effort=reasoning_effort,
        )
        return result.content

    async def request_chat_with_usage(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        stream: bool = False,
        thinking: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        reasoning_effort: str | None = None,
    ) -> DeepSeekChatResult:
        if stream:
            raise DeepSeekClientError(
                "带 usage 的非流式请求不能启用 stream=True，请使用 stream_chat_with_usage。",
                code="invalid_request",
            )

        self._assert_api_key()
        payload = self._build_payload(
            messages=messages,
            model=model,
            stream=False,
            thinking=thinking,
            tools=tools,
            tool_choice=tool_choice,
            reasoning_effort=reasoning_effort,
        )

        try:
            async with self.client_factory(timeout=self.timeout) as client:
                response = await client.post(
                    self._build_url(),
                    json=payload,
                    headers=self._build_headers(),
                )
        except httpx.HTTPError as exc:
            raise DeepSeekClientError(
                f"DeepSeek 网络请求失败：{exc}",
                code="network_error",
            ) from exc

        self._raise_for_error_response(response)
        payload = self._read_json_payload(response)
        content = self._read_message_content(payload)
        tool_calls = self._read_tool_calls(payload)

        if not content and not tool_calls:
            raise DeepSeekClientError(
                "DeepSeek 已返回成功响应，但没有可展示的消息内容。",
                code="empty_content",
            )

        return DeepSeekChatResult(
            content=content,
            usage=self._read_usage_payload(payload),
            reasoning_content=self._read_reasoning_content(payload),
            tool_calls=tool_calls,
        )

    async def stream_chat(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        thinking: dict[str, Any] | None = None,
        reasoning_effort: str | None = None,
    ) -> AsyncIterator[str]:
        async for event in self.stream_chat_with_usage(
            messages=messages,
            model=model,
            thinking=thinking,
            reasoning_effort=reasoning_effort,
        ):
            if event.text:
                yield event.text

    async def stream_chat_with_usage(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        thinking: dict[str, Any] | None = None,
        reasoning_effort: str | None = None,
    ) -> AsyncIterator[DeepSeekStreamEvent]:
        self._assert_api_key()
        payload = self._build_payload(
            messages=messages,
            model=model,
            stream=True,
            thinking=thinking,
            reasoning_effort=reasoning_effort,
        )

        try:
            async with self.client_factory(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    self._build_url(),
                    json=payload,
                    headers=self._build_headers(),
                ) as response:
                    self._raise_for_error_response(response)

                    saw_done = False
                    yielded_text = False
                    usage: dict[str, int] | None = None

                    async for raw_line in response.aiter_lines():
                        data = self._parse_sse_data_line(raw_line)
                        if data is None:
                            continue

                        if data == "[DONE]":
                            saw_done = True
                            break

                        try:
                            event = json.loads(data)
                        except JSONDecodeError as exc:
                            raise DeepSeekClientError(
                                "DeepSeek 流式响应解析失败，请稍后重试。",
                                code="stream_parse_error",
                            ) from exc

                        event_usage = self._read_usage_payload(event)
                        if event_usage is not None:
                            usage = event_usage

                        delta = self._read_delta_content(event)
                        if not delta:
                            continue

                        yielded_text = True
                        yield DeepSeekStreamEvent(text=delta)

        except httpx.HTTPError as exc:
            raise DeepSeekClientError(
                f"DeepSeek 流式请求失败：{exc}",
                code="network_error",
            ) from exc

        if not saw_done:
            raise DeepSeekClientError(
                "DeepSeek 流式响应在完成前中断，请稍后重试。",
                code="stream_interrupted",
            )

        if not yielded_text:
            raise DeepSeekClientError(
                "DeepSeek 流式响应已结束，但没有返回可展示的消息内容。",
                code="empty_content",
            )

        if usage is not None:
            yield DeepSeekStreamEvent(usage=usage)

    async def list_models(self) -> list[dict[str, Any]]:
        self._assert_api_key()

        try:
            async with self.client_factory(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers=self._build_headers(),
                )
        except httpx.HTTPError as exc:
            raise DeepSeekClientError(
                f"DeepSeek 模型列表请求失败：{exc}",
                code="network_error",
            ) from exc

        self._raise_for_error_response(response)
        payload = self._read_json_payload(response)
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, list):
            raise DeepSeekClientError(
                "DeepSeek 模型列表响应格式异常。",
                code="invalid_response",
            )
        return [item for item in data if isinstance(item, dict)]

    def _assert_api_key(self) -> None:
        if self.api_key:
            return

        raise DeepSeekClientError(
            "未配置后端 DeepSeek API Key，请在 backend/.env 中设置 DEEPSEEK_API_KEY。",
            code="missing_api_key",
            reason="missing_api_key",
        )

    def _build_url(self) -> str:
        return f"{self.base_url}/chat/completions"

    def _build_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_payload(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        stream: bool,
        thinking: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        reasoning_effort: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }
        if thinking is not None:
            payload["thinking"] = thinking
        if tools is not None:
            payload["tools"] = tools
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice
        if reasoning_effort is not None:
            payload["reasoning_effort"] = reasoning_effort
        return payload

    def _raise_for_error_response(self, response: Any) -> None:
        if getattr(response, "is_success", False):
            return

        status = getattr(response, "status_code", None)
        reason = self._read_error_detail(response)
        reason_text = f"：{reason}" if reason else ""
        raise DeepSeekClientError(
            f"DeepSeek 请求失败（HTTP {status}）{reason_text}",
            status=status,
            code="http_error",
            reason=reason,
        )

    def _read_json_payload(self, response: Any) -> Any:
        try:
            return response.json()
        except Exception as exc:
            reason = str(exc).strip()
            reason_text = f"：{reason}" if reason else ""
            raise DeepSeekClientError(
                f"DeepSeek 响应解析失败{reason_text}",
                code="response_parse_error",
                reason=reason,
            ) from exc

    def _read_error_detail(self, response: Any) -> str:
        try:
            payload = response.json()
        except Exception:
            payload = None

        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict) and isinstance(error.get("message"), str):
                return error["message"].strip()
            if isinstance(payload.get("message"), str):
                return payload["message"].strip()

        reason_phrase = getattr(response, "reason_phrase", "")
        return reason_phrase.strip() if isinstance(reason_phrase, str) else ""

    def _read_message_content(self, payload: Any) -> str:
        if not isinstance(payload, dict):
            return ""

        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            return ""

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            return ""

        message = first_choice.get("message")
        if not isinstance(message, dict):
            return ""

        content = message.get("content")
        if not isinstance(content, str):
            return ""

        return content.strip()

    def _read_reasoning_content(self, payload: Any) -> str | None:
        message = self._read_first_message(payload)
        if not isinstance(message, dict):
            return None

        reasoning_content = message.get("reasoning_content")
        return reasoning_content if isinstance(reasoning_content, str) else None

    def _read_tool_calls(self, payload: Any) -> list[dict[str, Any]] | None:
        message = self._read_first_message(payload)
        if not isinstance(message, dict):
            return None

        tool_calls = message.get("tool_calls")
        if not isinstance(tool_calls, list):
            return None
        return [item for item in tool_calls if isinstance(item, dict)]

    def _read_first_message(self, payload: Any) -> dict[str, Any] | None:
        if not isinstance(payload, dict):
            return None

        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            return None

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            return None

        message = first_choice.get("message")
        return message if isinstance(message, dict) else None

    def _read_usage_payload(self, payload: Any) -> dict[str, int] | None:
        if not isinstance(payload, dict):
            return None

        usage = payload.get("usage")
        if not isinstance(usage, dict):
            return None

        fields = (
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "prompt_cache_hit_tokens",
            "prompt_cache_miss_tokens",
        )
        normalized = {field: self._to_non_negative_int(usage.get(field)) for field in fields}
        if normalized["total_tokens"] == 0:
            normalized["total_tokens"] = normalized["prompt_tokens"] + normalized["completion_tokens"]
        return normalized

    def _parse_sse_data_line(self, line: str) -> str | None:
        trimmed = line.strip()
        if not trimmed or trimmed.startswith(":") or not trimmed.startswith("data:"):
            return None

        return trimmed[5:].strip()

    def _read_delta_content(self, payload: Any) -> str:
        if not isinstance(payload, dict):
            return ""

        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            return ""

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            return ""

        delta = first_choice.get("delta")
        if not isinstance(delta, dict):
            return ""

        content = delta.get("content")
        if not isinstance(content, str):
            return ""

        return content

    def _to_non_negative_int(self, value: Any) -> int:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int | float):
            return max(0, int(value))
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
        return 0
