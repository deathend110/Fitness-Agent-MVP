from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import httpx

from backend.providers.base import ProviderAdapter, ProviderAdapterError

DEFAULT_GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
OFFICIAL_GEMINI_API_HOST = "generativelanguage.googleapis.com"


class GeminiNativeProvider(ProviderAdapter):
    """适配 Gemini 原生 REST 接口，统一模型发现与函数调用消息结构。"""

    def __init__(self, client_factory=httpx.AsyncClient) -> None:
        super().__init__(client_factory=client_factory)

    async def list_remote_models(self, *, api_key: str, base_url: str) -> list[dict[str, Any]]:
        normalized_base_url = self._normalize_base_url(base_url)
        try:
            async with self.client_factory() as client:
                response = await client.get(
                    f"{normalized_base_url}/models",
                    params={"key": api_key},
                )
        except httpx.HTTPError as exc:
            raise ProviderAdapterError(
                f"Gemini 模型列表请求失败（{exc.__class__.__name__}）：{exc}",
                code="network_error",
            ) from exc

        self._raise_for_error_response(response)
        payload = response.json()
        models = payload.get("models") if isinstance(payload, dict) else []
        if not isinstance(models, list):
            raise ProviderAdapterError(
                "Gemini 模型列表响应格式异常。",
                code="invalid_response",
            )

        discovered: list[dict[str, Any]] = []
        for item in models:
            if not isinstance(item, dict):
                continue
            supported_methods = item.get("supportedGenerationMethods")
            if "generateContent" not in supported_methods:
                continue
            name = item.get("name")
            if not isinstance(name, str) or not name.strip():
                continue
            discovered.append(
                {
                    "remoteId": name.removeprefix("models/"),
                    "label": item.get("displayName") or name.removeprefix("models/"),
                    "enabled": True,
                }
            )
        return discovered

    def _normalize_base_url(self, base_url: str) -> str:
        normalized = str(base_url or "").strip().rstrip("/")
        if not normalized:
            return DEFAULT_GEMINI_API_BASE_URL

        parsed = urlparse(normalized)
        if parsed.netloc == OFFICIAL_GEMINI_API_HOST and parsed.path.rstrip("/") in {"", "/"}:
            return DEFAULT_GEMINI_API_BASE_URL
        return normalized

    def build_tool_schema(self, tools: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "functionDeclarations": [
                {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"],
                }
                for tool in tools
            ]
        }

    def normalize_tool_call_response(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        candidates = payload.get("candidates") if isinstance(payload, dict) else None
        if not isinstance(candidates, list) or not candidates:
            return []

        first_candidate = candidates[0]
        if not isinstance(first_candidate, dict):
            return []

        content = first_candidate.get("content")
        if not isinstance(content, dict):
            return []

        parts = content.get("parts")
        if not isinstance(parts, list):
            return []

        normalized_calls: list[dict[str, Any]] = []
        for index, part in enumerate(parts):
            if not isinstance(part, dict):
                continue
            function_call = part.get("functionCall")
            if not isinstance(function_call, dict):
                continue
            name = function_call.get("name")
            if not isinstance(name, str) or not name.strip():
                continue
            arguments = function_call.get("args")
            normalized_calls.append(
                {
                    "toolName": name,
                    "callId": str(function_call.get("id") or f"{name}-{index}"),
                    "arguments": dict(arguments) if isinstance(arguments, dict) else {},
                    "rawProviderPayload": part,
                }
            )
        return normalized_calls

    def build_followup_messages_after_tool_result(
        self,
        messages: list[dict[str, Any]],
        tool_call: dict[str, Any],
        tool_result: Any,
    ) -> list[dict[str, Any]]:
        return messages + [
            {
                "role": "tool",
                "parts": [
                    {
                        "functionResponse": {
                            "name": tool_call["toolName"],
                            "response": {"result": tool_result},
                        }
                    }
                ],
            }
        ]

    def _raise_for_error_response(self, response: Any) -> None:
        if getattr(response, "is_success", False):
            return

        status = getattr(response, "status_code", None)
        reason = self._read_error_detail(response)
        reason_text = f"：{reason}" if reason else ""
        raise ProviderAdapterError(
            f"Gemini 模型列表请求失败（HTTP {status}）{reason_text}",
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
