from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from backend.agent.deepseek_client import DeepSeekClient, DeepSeekClientError
from backend.config import Settings, get_settings

router = APIRouter(prefix="/api/models", tags=["models"])

MODEL_LABELS = {
    "deepseek-v4-flash": "DeepSeek V4 Flash",
    "deepseek-v4-pro": "DeepSeek V4 Pro",
    "deepseek-chat": "DeepSeek Chat（兼容名）",
    "deepseek-reasoner": "DeepSeek Reasoner（兼容名）",
}

THINKING_MODELS = {"deepseek-v4-flash", "deepseek-v4-pro"}


def get_models_settings() -> Settings:
    return get_settings()


def get_models_client(settings: Settings = Depends(get_models_settings)) -> DeepSeekClient:
    return DeepSeekClient(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        timeout=settings.deepseek_timeout_seconds,
    )


@router.get("")
async def list_models(
    settings: Settings = Depends(get_models_settings),
    client: DeepSeekClient = Depends(get_models_client),
) -> dict[str, Any]:
    warning = ""
    source = "remote"
    model_ids: list[str]

    if not settings.deepseek_api_key.strip():
        source = "fallback"
        warning = "未配置 DeepSeek API Key，已使用本地模型白名单。"
        model_ids = list(settings.model_allowlist)
    else:
        try:
            remote_models = await client.list_models()
            remote_ids = [str(item.get("id")) for item in remote_models if isinstance(item, dict) and item.get("id")]
            model_ids = [model_id for model_id in remote_ids if model_id in settings.model_allowlist]
            if not model_ids:
                source = "fallback"
                warning = "DeepSeek /models 未返回白名单模型，已使用本地模型白名单。"
                model_ids = list(settings.model_allowlist)
        except DeepSeekClientError as exc:
            source = "fallback"
            warning = str(exc)
            model_ids = list(settings.model_allowlist)

    return {
        "source": source,
        "warning": warning,
        "defaultModel": settings.default_model if settings.default_model in model_ids else model_ids[0],
        "models": [build_model_option(model_id) for model_id in model_ids],
        "thinking": {
            "enabled": settings.default_thinking_enabled,
            "budget": settings.default_thinking_budget,
            "options": ["off", "auto", "max"],
        },
    }


def build_model_option(model_id: str) -> dict[str, Any]:
    return {
        "id": model_id,
        "label": MODEL_LABELS.get(model_id, model_id),
        "supportsThinking": model_id in THINKING_MODELS,
    }
