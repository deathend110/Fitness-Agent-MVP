from __future__ import annotations

import json
from typing import Any

import httpx

from backend.providers.base import ProviderAdapter, ProviderAdapterError


class OpenAICompatibleProvider(ProviderAdapter):
    """兼容 OpenAI /models 与 chat tools 结构，供 DeepSeek 和同类接口复用。"""

    def __init__(self, client_factory=httpx.AsyncClient) -> None:
        super().__init__(client_factory=client_factory)

    async def list_remote_models(self, *, api_key: str, base_url: str) -> list[dict[str, Any]]:
        try:
            async with self.client_factory() as client:
                response = await client.get(
                    f"{base_url.rstrip('/')}/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
        except httpx.HTTPError as exc:
            raise ProviderAdapterError(
                f"OpenAI 兼容模型列表请求失败：{exc}",
                code="network_error",
            ) from exc

        self._raise_for_error_response(response)

        payload = response.json()
        data = payload.get("data") if isinstance(payload, dict) else []
        if not isinstance(data, list):
            raise ProviderAdapterError(
                "OpenAI 兼容模型列表响应格式异常。",
                code="invalid_response",
            )

        models: list[dict[str, Any]] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            remote_id = item.get("id")
            if not isinstance(remote_id, str) or not remote_id.strip():
                continue
            models.append(
                {
                    "remoteId": remote_id,
                    "label": remote_id,
                    "enabled": True,
                }
            )
        return models

    def build_tool_schema(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"],
                },
            }
            for tool in tools
        ]

    def normalize_tool_call_response(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        message = self._read_first_message(payload)
        if not isinstance(message, dict):
            return []

        tool_calls = message.get("tool_calls")
        if not isinstance(tool_calls, list):
            return []

        normalized_calls: list[dict[str, Any]] = []
        for tool_call in tool_calls:
            if not isinstance(tool_call, dict):
                continue
            function = tool_call.get("function")
            if not isinstance(function, dict):
                continue
            name = function.get("name")
            if not isinstance(name, str) or not name.strip():
                continue
            raw_arguments = function.get("arguments") or "{}"
            if isinstance(raw_arguments, dict):
                arguments = raw_arguments
            else:
                try:
                    parsed = json.loads(raw_arguments)
                except json.JSONDecodeError:
                    parsed = {}
                arguments = parsed if isinstance(parsed, dict) else {}
            normalized_calls.append(
                {
                    "toolName": name,
                    "callId": str(tool_call.get("id") or name),
                    "arguments": arguments,
                    "rawProviderPayload": {
                        "toolCall": tool_call,
                        "assistantMessage": message,
                    },
                }
            )
        return normalized_calls

    def build_followup_messages_after_tool_result(
        self,
        messages: list[dict[str, Any]],
        tool_call: dict[str, Any],
        tool_result: Any,
    ) -> list[dict[str, Any]]:
        updated_messages = list(messages)
        raw_payload = tool_call.get("rawProviderPayload")
        assistant_message = raw_payload.get("assistantMessage") if isinstance(raw_payload, dict) else None
        if isinstance(assistant_message, dict) and not self._has_matching_trailing_assistant(
            updated_messages,
            assistant_message,
        ):
            updated_messages.append(
                {
                    "role": "assistant",
                    "content": assistant_message.get("content", ""),
                    "tool_calls": assistant_message.get("tool_calls", []),
                    **(
                        {"reasoning_content": assistant_message["reasoning_content"]}
                        if isinstance(assistant_message.get("reasoning_content"), str)
                        else {}
                    ),
                }
            )

        return updated_messages + [
            {
                "role": "tool",
                "tool_call_id": tool_call["callId"],
                "name": tool_call["toolName"],
                "content": tool_result,
            }
        ]

    @staticmethod
    def _has_matching_trailing_assistant(
        messages: list[dict[str, Any]],
        assistant_message: dict[str, Any],
    ) -> bool:
        index = len(messages) - 1
        while index >= 0 and messages[index].get("role") == "tool":
            index -= 1

        if index < 0:
            return False

        candidate = messages[index]
        if candidate.get("role") != "assistant":
            return False

        return (
            candidate.get("content", "") == assistant_message.get("content", "")
            and candidate.get("tool_calls", []) == assistant_message.get("tool_calls", [])
            and candidate.get("reasoning_content") == assistant_message.get("reasoning_content")
        )

    def _raise_for_error_response(self, response: Any) -> None:
        if getattr(response, "is_success", False):
            return

        status = getattr(response, "status_code", None)
        reason = self._read_error_detail(response)
        reason_text = f"：{reason}" if reason else ""
        raise ProviderAdapterError(
            f"OpenAI 兼容模型列表请求失败（HTTP {status}）{reason_text}",
            status=status,
            code="http_error",
            reason=reason,
        )

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
