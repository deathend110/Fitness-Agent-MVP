from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from backend.model_config.runtime import get_provider_runtime

router = APIRouter(prefix="/api/models", tags=["models"])


def build_legacy_top_level_thinking(models: list[dict[str, Any]], default_model_ref: str) -> dict[str, Any]:
    """兼容旧版 UI：优先从默认模型的能力信息回推顶层 thinking。"""

    selected_model = next((item for item in models if item.get("id") == default_model_ref), None)
    if not isinstance(selected_model, dict):
        return {"enabled": False, "budget": "auto", "options": ["off", "auto", "max"]}

    thinking = selected_model.get("thinking")
    if not isinstance(thinking, dict) or not thinking.get("supported"):
        return {"enabled": False, "budget": "auto", "options": ["off", "auto", "max"]}

    options = ["off"]
    options.extend(
        option["id"]
        for option in thinking.get("intensityOptions", [])
        if isinstance(option, dict) and isinstance(option.get("id"), str)
    )
    return {
        "enabled": bool(thinking.get("defaultEnabled")),
        "budget": str(thinking.get("defaultIntensity") or "auto"),
        "options": options,
    }


@router.get("")
async def list_models() -> dict[str, Any]:
    """返回运行时启用模型列表，并保留旧版前端仍在消费的顶层 thinking 字段。"""

    runtime = get_provider_runtime()
    models = runtime.list_enabled_models()
    return {
        "source": "runtime",
        "warning": "",
        "defaultModel": runtime.default_model_ref,
        "defaultModelRef": runtime.default_model_ref,
        "models": models,
        "thinking": (
            runtime.get_legacy_default_thinking()
            if hasattr(runtime, "get_legacy_default_thinking")
            else build_legacy_top_level_thinking(models, runtime.default_model_ref)
        ),
    }
