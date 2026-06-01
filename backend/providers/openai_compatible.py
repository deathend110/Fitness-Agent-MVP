from __future__ import annotations

import json
from typing import Any

import httpx

from backend.providers.base import ProviderAdapter, ProviderAdapterError
from backend.providers.openai_compatible_client import (
    OPENAI_COMPATIBLE_DEFAULT_TIMEOUT,
    OpenAICompatibleClient,
)


class OpenAICompatibleProvider(ProviderAdapter):
    """统一适配 OpenAI 兼容供应商的模型发现、文本读取与工具回环结构。"""

    def __init__(
        self,
        *,
        client_factory=httpx.AsyncClient,
        wire_api: str = "chat_completions",
        api_path_mode: str = "raw_root",
        timeout: float = OPENAI_COMPATIBLE_DEFAULT_TIMEOUT,
    ) -> None:
        super().__init__(client_factory=client_factory)
        self.wire_api = wire_api
        self.api_path_mode = api_path_mode
        self.timeout = timeout

    async def list_remote_models(
        self,
        *,
        api_key: str,
        base_url: str,
        wire_api: str | None = None,
        api_path_mode: str | None = None,
    ) -> list[dict[str, Any]]:
        client = self._build_http_client(
            api_key=api_key,
            base_url=base_url,
            wire_api=wire_api,
            api_path_mode=api_path_mode,
        )
        payload = await client.get_json("/models", action_label="OpenAI 兼容模型列表请求")
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

    def build_request_url(
        self,
        *,
        base_url: str,
        path: str,
        api_path_mode: str | None = None,
    ) -> str:
        return OpenAICompatibleClient.build_request_url(
            base_url=base_url,
            path=path,
            api_path_mode=api_path_mode or self.api_path_mode,
        )

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

    async def generate_chat(
        self,
        *,
        api_key: str,
        base_url: str,
        messages: list[dict[str, Any]],
        model: str,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        wire_api: str | None = None,
        api_path_mode: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        active_wire_api = wire_api or self.wire_api
        client = self._build_http_client(
            api_key=api_key,
            base_url=base_url,
            wire_api=active_wire_api,
            api_path_mode=api_path_mode,
        )
        payload = self._build_generate_payload(
            wire_api=active_wire_api,
            messages=messages,
            model=model,
            tools=tools,
            tool_choice=tool_choice,
            extra=kwargs,
        )
        raw_payload = await client.post_json(
            client.build_chat_path(),
            payload=payload,
            action_label="OpenAI 兼容聊天请求",
        )
        return {
            "text": self.read_text_response(raw_payload, wire_api=active_wire_api),
            "toolCalls": self.normalize_tool_call_response(raw_payload, wire_api=active_wire_api),
            "raw": raw_payload,
        }

    def read_text_response(self, payload: Any, *, wire_api: str | None = None) -> str:
        active_wire_api = wire_api or self.wire_api
        if active_wire_api == "responses":
            return self._read_responses_text(payload)
        return self._read_chat_completions_text(payload)

    def normalize_tool_call_response(
        self,
        payload: dict[str, Any],
        *,
        wire_api: str | None = None,
    ) -> list[dict[str, Any]]:
        active_wire_api = wire_api or self.wire_api
        if active_wire_api == "responses":
            return self._normalize_responses_function_calls(payload)
        return self._normalize_chat_completions_tool_calls(payload)

    def build_followup_messages_after_tool_result(
        self,
        messages: list[dict[str, Any]],
        tool_call: dict[str, Any],
        tool_result: Any,
    ) -> list[dict[str, Any]]:
        if self._resolve_wire_api_from_tool_call(tool_call) == "responses":
            return self._build_responses_followup_messages(messages, tool_call, tool_result)
        return self._build_chat_completions_followup_messages(messages, tool_call, tool_result)

    def _build_http_client(
        self,
        *,
        api_key: str,
        base_url: str,
        wire_api: str | None = None,
        api_path_mode: str | None = None,
    ) -> OpenAICompatibleClient:
        return OpenAICompatibleClient(
            api_key=api_key,
            base_url=base_url,
            wire_api=wire_api or self.wire_api,
            api_path_mode=api_path_mode or self.api_path_mode,
            timeout=self.timeout,
            client_factory=self.client_factory,
        )

    def _build_generate_payload(
        self,
        *,
        wire_api: str,
        messages: list[dict[str, Any]],
        model: str,
        tools: list[dict[str, Any]] | None,
        tool_choice: str | dict[str, Any] | None,
        extra: dict[str, Any],
    ) -> dict[str, Any]:
        if wire_api == "responses":
            payload: dict[str, Any] = {
                "model": model,
                "input": messages,
            }
            if tools is not None:
                payload["tools"] = tools
            if tool_choice is not None:
                payload["tool_choice"] = tool_choice
            for key, value in extra.items():
                if value is not None:
                    payload[key] = value
            return payload

        payload = {
            "model": model,
            "messages": messages,
        }
        if tools is not None:
            payload["tools"] = tools
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice
        for key, value in extra.items():
            if value is not None:
                payload[key] = value
        return payload

    def _normalize_chat_completions_tool_calls(self, payload: Any) -> list[dict[str, Any]]:
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
            normalized_calls.append(
                {
                    "toolName": name,
                    "callId": str(tool_call.get("id") or name),
                    "arguments": self._parse_function_arguments(function.get("arguments")),
                    "rawProviderPayload": {
                        "toolCall": tool_call,
                        "assistantMessage": message,
                    },
                }
            )
        return normalized_calls

    def _normalize_responses_function_calls(self, payload: Any) -> list[dict[str, Any]]:
        output_items = payload.get("output") if isinstance(payload, dict) else None
        if not isinstance(output_items, list):
            return []

        normalized_calls: list[dict[str, Any]] = []
        for output_item in output_items:
            if not isinstance(output_item, dict):
                continue
            if output_item.get("type") != "function_call":
                continue
            name = output_item.get("name")
            if not isinstance(name, str) or not name.strip():
                continue
            normalized_calls.append(
                {
                    "toolName": name,
                    "callId": str(output_item.get("call_id") or name),
                    "arguments": self._parse_function_arguments(output_item.get("arguments")),
                    "rawProviderPayload": {
                        "responseId": payload.get("id"),
                        "functionCall": output_item,
                    },
                }
            )
        return normalized_calls

    def _build_chat_completions_followup_messages(
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

    def _build_responses_followup_messages(
        self,
        messages: list[dict[str, Any]],
        tool_call: dict[str, Any],
        tool_result: Any,
    ) -> list[dict[str, Any]]:
        updated_messages = list(messages)
        raw_payload = tool_call.get("rawProviderPayload")
        function_call = raw_payload.get("functionCall") if isinstance(raw_payload, dict) else None
        if isinstance(function_call, dict) and not self._has_matching_trailing_response_item(
            updated_messages,
            function_call,
        ):
            updated_messages.append(function_call)

        updated_messages.append(
            {
                "type": "function_call_output",
                "call_id": tool_call["callId"],
                "output": tool_result,
            }
        )
        return updated_messages

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

    @staticmethod
    def _has_matching_trailing_response_item(
        messages: list[dict[str, Any]],
        function_call: dict[str, Any],
    ) -> bool:
        if not messages:
            return False
        candidate = messages[-1]
        return candidate == function_call

    def _read_chat_completions_text(self, payload: Any) -> str:
        message = self._read_first_message(payload)
        if not isinstance(message, dict):
            return ""
        content = message.get("content")
        return content.strip() if isinstance(content, str) else ""

    def _read_responses_text(self, payload: Any) -> str:
        if not isinstance(payload, dict):
            return ""

        output_text = payload.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()

        output_items = payload.get("output")
        if not isinstance(output_items, list):
            return ""

        collected: list[str] = []
        for output_item in output_items:
            if not isinstance(output_item, dict):
                continue
            if output_item.get("type") != "message":
                continue
            content_items = output_item.get("content")
            if not isinstance(content_items, list):
                continue
            for content_item in content_items:
                if not isinstance(content_item, dict):
                    continue
                if content_item.get("type") != "output_text":
                    continue
                text = content_item.get("text")
                if isinstance(text, str) and text:
                    collected.append(text)
        return "".join(collected).strip()

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

    def _resolve_wire_api_from_tool_call(self, tool_call: dict[str, Any]) -> str:
        raw_payload = tool_call.get("rawProviderPayload")
        if isinstance(raw_payload, dict) and (
            "responseId" in raw_payload or "functionCall" in raw_payload
        ):
            return "responses"
        return self.wire_api

    @staticmethod
    def _parse_function_arguments(raw_arguments: Any) -> dict[str, Any]:
        if isinstance(raw_arguments, dict):
            return raw_arguments

        if not isinstance(raw_arguments, str) or not raw_arguments.strip():
            return {}

        try:
            parsed = json.loads(raw_arguments)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
