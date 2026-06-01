from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from backend.model_config.runtime import get_provider_runtime
from backend.model_config.service import ModelProviderConfigService
from backend.providers.base import ProviderAdapter, ProviderAdapterError
from backend.providers.gemini_native import GeminiNativeProvider
from backend.providers.openai_compatible import OpenAICompatibleProvider

router = APIRouter(prefix="/api/model-config", tags=["model-config"])


class ProviderConnectionPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    type: str
    apiKey: str = ""
    baseUrl: str = ""


def get_model_config_path() -> Path:
    """统一暴露当前模型配置文件路径，便于测试把写盘目标切到临时目录。"""

    runtime = get_provider_runtime()
    return Path(runtime.config_path)


def get_provider_adapter(provider_type: str) -> ProviderAdapter:
    """根据 provider.type 选择适配层，后续新增协议时只需要在这里扩展。"""

    normalized_type = str(provider_type or "").strip().lower()
    if normalized_type == "openai_compatible":
        return OpenAICompatibleProvider()
    if normalized_type == "gemini_native":
        return GeminiNativeProvider()
    raise HTTPException(status_code=422, detail=f"不支持的 provider 类型: {provider_type}")


def raise_provider_http_error(error: ProviderAdapterError) -> None:
    """把适配层错误统一翻译成 API 错误响应，避免前端自己猜供应商异常。"""

    status_code = error.status or 503
    raise HTTPException(status_code=status_code, detail=str(error)) from error


@router.get("")
async def get_model_config() -> dict[str, Any]:
    """返回脱敏后的当前模型配置，供前端设置页直接回显。"""

    return get_provider_runtime().get_masked_config()


@router.put("")
async def put_model_config(payload: dict[str, Any]) -> dict[str, Any]:
    """保存模型配置并立即刷新进程内 runtime，让新设置无需重启即可生效。"""

    service = ModelProviderConfigService(config_path=get_model_config_path())
    saved = service.save(payload)
    get_provider_runtime().refresh()
    return saved


@router.post("/providers/test")
async def test_provider_connection(payload: ProviderConnectionPayload) -> dict[str, Any]:
    """用轻量模型发现请求测试 provider 凭据和 base URL 是否可用。"""

    adapter = get_provider_adapter(payload.type)
    try:
        models = await adapter.list_remote_models(
            api_key=payload.apiKey.strip(),
            base_url=payload.baseUrl.strip(),
        )
    except ProviderAdapterError as error:
        raise_provider_http_error(error)

    return {
        "ok": True,
        "modelCount": len(models),
    }


@router.post("/providers/discover-models")
async def discover_provider_models(payload: ProviderConnectionPayload) -> dict[str, Any]:
    """从远端 provider 拉取模型列表，供前端勾选需要展示的模型。"""

    adapter = get_provider_adapter(payload.type)
    try:
        models = await adapter.list_remote_models(
            api_key=payload.apiKey.strip(),
            base_url=payload.baseUrl.strip(),
        )
    except ProviderAdapterError as error:
        raise_provider_http_error(error)

    return {"models": models}
