from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import Any

import httpx

from backend.agent.deepseek_client import DeepSeekChatResult, DeepSeekClientError, DeepSeekStreamEvent


class GeminiNativeClient:
    """把 Gemini Developer API 包装成当前聊天链可复用的最小客户端形态。"""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        timeout: float = 30.0,
        client_factory: Callable[..., Any] = httpx.AsyncClient,
    ) -> None:
        self.api_key = str(api_key or "").strip()
        self.base_url = str(base_url or "").rstrip("/")
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
                tools=tools,
                tool_choice=tool_choice,
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
                "Gemini 带 usage 的非流式请求不能启用 stream=True。",
                code="invalid_request",
            )

        response_payload = await self.generate_content_raw(
            messages=messages,
            model=model,
            thinking=thinking,
            tools=tools,
            tool_choice=tool_choice,
            reasoning_effort=reasoning_effort,
        )
        content = self._read_text_content(response_payload)
        if not content:
            raise DeepSeekClientError(
                "Gemini 已返回成功响应，但没有可展示的消息内容。",
                code="empty_content",
            )

        return DeepSeekChatResult(
            content=content,
            usage=self._read_usage_payload(response_payload),
        )

    async def stream_chat(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        thinking: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        reasoning_effort: str | None = None,
    ) -> AsyncIterator[str]:
        async for event in self.stream_chat_with_usage(
            messages=messages,
            model=model,
            thinking=thinking,
            tools=tools,
            tool_choice=tool_choice,
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
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        reasoning_effort: str | None = None,
    ) -> AsyncIterator[DeepSeekStreamEvent]:
        result = await self.request_chat_with_usage(
            messages=messages,
            model=model,
            thinking=thinking,
            tools=tools,
            tool_choice=tool_choice,
            reasoning_effort=reasoning_effort,
        )
        yield DeepSeekStreamEvent(text=result.content)
        if result.usage is not None:
            yield DeepSeekStreamEvent(usage=result.usage)

    async def generate_content_raw(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        thinking: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | dict[str, Any] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        reasoning_effort: str | None = None,
    ) -> dict[str, Any]:
        self._assert_api_key()
        payload = self._build_payload(
            messages=messages,
            thinking=thinking,
            tools=tools,
            tool_choice=tool_choice,
            reasoning_effort=reasoning_effort,
        )

        try:
            async with self.client_factory(timeout=self.timeout) as client:
                response = await client.post(
                    self._build_url(model),
                    params={"key": self.api_key},
                    json=payload,
                    headers={},
                )
        except httpx.HTTPError as exc:
            raise DeepSeekClientError(
                f"Gemini 网络请求失败：{exc}",
                code="network_error",
            ) from exc

        self._raise_for_error_response(response)
        raw_payload = self._read_json_payload(response)
        if not isinstance(raw_payload, dict):
            raise DeepSeekClientError(
                "Gemini 响应格式异常，请稍后重试。",
                code="invalid_response",
            )
        return raw_payload

    def _assert_api_key(self) -> None:
        if self.api_key:
            return
        raise DeepSeekClientError(
            "未配置 Gemini API Key，请先在模型设置中填写有效凭据。",
            code="missing_api_key",
            reason="missing_api_key",
        )

    def _build_url(self, model: str) -> str:
        return f"{self.base_url}/models/{model}:generateContent"

    def _build_payload(
        self,
        *,
        messages: list[dict[str, Any]],
        thinking: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | dict[str, Any] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        reasoning_effort: str | None = None,
    ) -> dict[str, Any]:
        system_texts: list[str] = []
        contents: list[dict[str, Any]] = []

        for message in messages:
            role = str(message.get("role") or "user")
            if role == "system":
                content = self._normalize_message_content(message.get("content"))
                if not content and isinstance(message.get("parts"), list):
                    content = self._normalize_parts_text(message.get("parts"))
                if not content:
                    continue
                system_texts.append(content)
                continue

            raw_parts = message.get("parts")
            if isinstance(raw_parts, list) and raw_parts:
                contents.append(
                    {
                        "role": "model" if role in {"assistant", "model"} else "user",
                        "parts": raw_parts,
                    }
                )
                continue

            content = self._normalize_message_content(message.get("content"))
            if not content:
                continue
            contents.append(
                {
                    "role": "model" if role in {"assistant", "model"} else "user",
                    "parts": [{"text": content}],
                }
            )

        payload: dict[str, Any] = {
            "contents": contents or [{"role": "user", "parts": [{"text": ""}]}],
        }
        if system_texts:
            payload["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_texts)}]}
        if tools:
            if isinstance(tools, dict):
                payload["tools"] = [tools]
            else:
                payload["tools"] = tools
        del thinking, tool_choice, reasoning_effort
        return payload

    @staticmethod
    def _normalize_message_content(raw_content: Any) -> str:
        if isinstance(raw_content, str):
            return raw_content.strip()
        if isinstance(raw_content, list):
            text_parts = [item.get("text", "") for item in raw_content if isinstance(item, dict)]
            return "\n".join(part.strip() for part in text_parts if isinstance(part, str) and part.strip())
        return ""

    @staticmethod
    def _normalize_parts_text(parts: Any) -> str:
        if not isinstance(parts, list):
            return ""
        text_parts = [item.get("text", "") for item in parts if isinstance(item, dict)]
        return "\n".join(part.strip() for part in text_parts if isinstance(part, str) and part.strip())

    @staticmethod
    def _read_text_content(response_payload: Any) -> str:
        if not isinstance(response_payload, dict):
            return ""

        candidates = response_payload.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            return ""

        first_candidate = candidates[0]
        if not isinstance(first_candidate, dict):
            return ""

        content = first_candidate.get("content")
        if not isinstance(content, dict):
            return ""

        parts = content.get("parts")
        if not isinstance(parts, list):
            return ""

        text_blocks: list[str] = []
        for part in parts:
            if not isinstance(part, dict):
                continue
            text = part.get("text")
            if isinstance(text, str) and text.strip():
                text_blocks.append(text.strip())
        return "\n".join(text_blocks).strip()

    @staticmethod
    def _read_usage_payload(response_payload: Any) -> dict[str, int] | None:
        if not isinstance(response_payload, dict):
            return None

        usage = response_payload.get("usageMetadata")
        if not isinstance(usage, dict):
            return None

        prompt_tokens = usage.get("promptTokenCount")
        completion_tokens = usage.get("candidatesTokenCount")
        total_tokens = usage.get("totalTokenCount")
        if not all(isinstance(value, int) for value in [prompt_tokens, completion_tokens, total_tokens]):
            return None
        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }

    @staticmethod
    def _raise_for_error_response(response: Any) -> None:
        if getattr(response, "is_success", False):
            return

        status = getattr(response, "status_code", None)
        reason = GeminiNativeClient._read_error_detail(response)
        reason_text = f"：{reason}" if reason else ""
        raise DeepSeekClientError(
            f"Gemini 请求失败（HTTP {status}）{reason_text}",
            status=status,
            code="http_error",
            reason=reason,
        )

    @staticmethod
    def _read_json_payload(response: Any) -> Any:
        try:
            return response.json()
        except Exception as exc:
            reason = str(exc).strip()
            reason_text = f"：{reason}" if reason else ""
            raise DeepSeekClientError(
                f"Gemini 响应解析失败{reason_text}",
                code="response_parse_error",
                reason=reason,
            ) from exc

    @staticmethod
    def _read_error_detail(response: Any) -> str:
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
