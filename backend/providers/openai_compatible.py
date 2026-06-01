from __future__ import annotations

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
