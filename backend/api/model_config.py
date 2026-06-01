from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter

from backend.model_config.runtime import get_provider_runtime
from backend.model_config.service import ModelProviderConfigService

router = APIRouter(prefix="/api/model-config", tags=["model-config"])


def get_model_config_path() -> Path:
    """统一暴露当前模型配置文件路径，便于测试把写盘目标切到临时目录。"""

    runtime = get_provider_runtime()
    return Path(runtime.config_path)


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
