from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
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
