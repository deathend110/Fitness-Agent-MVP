from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
import json
from typing import Any

import httpx


class ProviderAdapterError(Exception):
    """统一封装 provider 适配层错误，便于 API 层稳定映射。"""

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        code: str = "provider_error",
        reason: str = "",
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.reason = reason


class ProviderAdapter(ABC):
    """定义多供应商适配层的最小公共接口，先统一模型发现和工具 schema 输出。"""

    def __init__(
        self,
        *,
        client_factory: Callable[..., Any] = httpx.AsyncClient,
    ) -> None:
        self.client_factory = client_factory

    @abstractmethod
    async def list_remote_models(
        self,
        *,
        api_key: str,
        base_url: str,
        wire_api: str | None = None,
        api_path_mode: str | None = None,
    ) -> list[dict[str, Any]]:
        """从供应商远端接口发现可选模型，并兼容需要额外路径协议参数的供应商。"""

    @abstractmethod
    def build_tool_schema(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """把本地工具描述转换成供应商可接受的 tool schema。"""


def convert_messages_to_responses_input(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """把现有 chat/tool loop 消息统一转换成 Responses API 可接受的 input 结构。"""

    input_items: list[dict[str, Any]] = []
    for message in messages:
        item_type = str(message.get("type") or "").strip()
        if item_type in {"message", "function_call", "function_call_output", "reasoning"}:
            input_items.append(message)
            continue

        role = str(message.get("role") or "user")
        if role == "tool":
            call_id = str(message.get("tool_call_id") or message.get("call_id") or "").strip()
            if not call_id:
                continue
            input_items.append(
                {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": stringify_tool_result(message.get("content", "")),
                }
            )
            continue

        content = message.get("content")
        if not isinstance(content, str):
            content = ""
        part_type = "output_text" if role in {"assistant", "model"} else "input_text"
        input_items.append(
            {
                "type": "message",
                "role": "assistant" if role in {"assistant", "model"} else role,
                "content": [{"type": part_type, "text": content}],
            }
        )
    return input_items


def read_responses_output_text(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""

    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    output_items = payload.get("output")
    if not isinstance(output_items, list):
        return ""

    text_blocks: list[str] = []
    for output_item in output_items:
        if not isinstance(output_item, dict) or output_item.get("type") != "message":
            continue
        content_items = output_item.get("content")
        if not isinstance(content_items, list):
            continue
        for content_item in content_items:
            if not isinstance(content_item, dict):
                continue
            part_type = content_item.get("type")
            text = content_item.get("text")
            if part_type in {"output_text", "text"} and isinstance(text, str) and text.strip():
                text_blocks.append(text.strip())
    return "\n".join(text_blocks).strip()


def normalize_responses_tool_call_response(payload: Any) -> list[dict[str, Any]]:
    output_items = payload.get("output") if isinstance(payload, dict) else None
    if not isinstance(output_items, list):
        return []

    normalized_calls: list[dict[str, Any]] = []
    for index, output_item in enumerate(output_items):
        if not isinstance(output_item, dict) or output_item.get("type") != "function_call":
            continue
        name = output_item.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        normalized_calls.append(
            {
                "toolName": name,
                "callId": str(output_item.get("call_id") or output_item.get("id") or f"{name}-{index}"),
                "arguments": _parse_response_function_arguments(output_item.get("arguments")),
                "rawProviderPayload": {
                    "responseId": payload.get("id") if isinstance(payload, dict) else None,
                    "outputItems": output_items,
                    "functionCall": output_item,
                },
            }
        )
    return normalized_calls


def build_responses_followup_messages(
    messages: list[dict[str, Any]],
    tool_call: dict[str, Any],
    tool_result: Any,
) -> list[dict[str, Any]]:
    updated_messages = convert_messages_to_responses_input(messages)
    raw_payload = tool_call.get("rawProviderPayload")
    output_items = raw_payload.get("outputItems") if isinstance(raw_payload, dict) else None
    if isinstance(output_items, list) and not _has_matching_trailing_response_items(
        updated_messages,
        output_items,
    ):
        updated_messages.extend(output_items)

    updated_messages.append(
        {
            "type": "function_call_output",
            "call_id": tool_call["callId"],
            "output": stringify_tool_result(tool_result),
        }
    )
    return updated_messages


def stringify_tool_result(tool_result: Any) -> str:
    if isinstance(tool_result, str):
        return tool_result
    return json.dumps(tool_result, ensure_ascii=False)


def _parse_response_function_arguments(raw_arguments: Any) -> dict[str, Any]:
    if isinstance(raw_arguments, dict):
        return raw_arguments
    if not isinstance(raw_arguments, str) or not raw_arguments.strip():
        return {}

    try:
        parsed = json.loads(raw_arguments)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _has_matching_trailing_response_items(
    messages: list[dict[str, Any]],
    output_items: list[dict[str, Any]],
) -> bool:
    if len(messages) < len(output_items):
        return False

    index = len(messages)
    while index > 0 and _is_response_function_call_output(messages[index - 1]):
        index -= 1

    if index < len(output_items):
        return False

    return messages[index - len(output_items) : index] == output_items


def _is_response_function_call_output(message: Any) -> bool:
    return isinstance(message, dict) and message.get("type") == "function_call_output"
