from __future__ import annotations

from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse

import httpx

from backend.providers.base import ProviderAdapterError

OPENAI_COMPATIBLE_DEFAULT_TIMEOUT = 30.0


class OpenAICompatibleClient:
    """统一封装 OpenAI 兼容 HTTP 细节，避免 provider 层重复处理 URL 和错误映射。"""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        wire_api: str = "chat_completions",
        api_path_mode: str = "raw_root",
        timeout: float = OPENAI_COMPATIBLE_DEFAULT_TIMEOUT,
        client_factory: Callable[..., Any] = httpx.AsyncClient,
    ) -> None:
        self.api_key = str(api_key or "").strip()
        self.base_url = str(base_url or "").strip()
        self.wire_api = str(wire_api or "chat_completions").strip() or "chat_completions"
        self.api_path_mode = str(api_path_mode or "raw_root").strip() or "raw_root"
        self.timeout = timeout
        self.client_factory = client_factory

    @classmethod
    def build_request_url(
        cls,
        *,
        base_url: str,
        path: str,
        api_path_mode: str = "raw_root",
    ) -> str:
        normalized_base_url = cls._normalize_base_url(
            base_url=base_url,
            api_path_mode=api_path_mode,
        )
        normalized_path = f"/{str(path or '').lstrip('/')}"
        return f"{normalized_base_url}{normalized_path}"

    async def get_json(self, path: str, *, action_label: str) -> Any:
        try:
            async with self.client_factory(timeout=self.timeout) as client:
                response = await client.get(
                    self.build_request_url(
                        base_url=self.base_url,
                        path=path,
                        api_path_mode=self.api_path_mode,
                    ),
                    headers=self._build_headers(),
                    timeout=self.timeout,
                )
        except httpx.HTTPError as exc:
            raise ProviderAdapterError(
                f"{action_label}失败（{exc.__class__.__name__}）：{exc}",
                code="network_error",
            ) from exc

        self._raise_for_error_response(response, action_label=action_label)
        return self._read_json_payload(response, action_label=action_label)

    async def post_json(
        self,
        path: str,
        *,
        payload: dict[str, Any],
        action_label: str,
    ) -> Any:
        try:
            async with self.client_factory(timeout=self.timeout) as client:
                response = await client.post(
                    self.build_request_url(
                        base_url=self.base_url,
                        path=path,
                        api_path_mode=self.api_path_mode,
                    ),
                    json=payload,
                    headers=self._build_headers(),
                    timeout=self.timeout,
                )
        except httpx.HTTPError as exc:
            raise ProviderAdapterError(
                f"{action_label}失败（{exc.__class__.__name__}）：{exc}",
                code="network_error",
            ) from exc

        self._raise_for_error_response(response, action_label=action_label)
        return self._read_json_payload(response, action_label=action_label)

    def build_chat_path(self) -> str:
        if self.wire_api == "responses":
            return "/responses"
        return "/chat/completions"

    @staticmethod
    def _normalize_base_url(*, base_url: str, api_path_mode: str) -> str:
        normalized = str(base_url or "").strip().rstrip("/")
        if not normalized:
            return ""

        if api_path_mode != "append_v1":
            return normalized

        parsed = urlparse(normalized)
        path = parsed.path.rstrip("/")
        if path.endswith("/v1") or path == "/v1":
            return normalized
        if path in {"", "/"}:
            return f"{normalized}/v1"
        return f"{normalized}/v1"

    def _build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _raise_for_error_response(self, response: Any, *, action_label: str) -> None:
        if getattr(response, "is_success", False):
            return

        status = getattr(response, "status_code", None)
        reason = self._read_error_detail(response)
        reason_text = f"：{reason}" if reason else ""
        raise ProviderAdapterError(
            f"{action_label}失败（HTTP {status}）{reason_text}",
            status=status,
            code="http_error",
            reason=reason,
        )

    def _read_json_payload(self, response: Any, *, action_label: str) -> Any:
        try:
            return response.json()
        except Exception as exc:
            reason = str(exc).strip()
            reason_text = f"：{reason}" if reason else ""
            raise ProviderAdapterError(
                f"{action_label}响应解析失败{reason_text}",
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
