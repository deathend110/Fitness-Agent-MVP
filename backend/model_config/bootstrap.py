from __future__ import annotations

from typing import Any, Mapping

from backend.model_config.types import ModelProviderConfig, ProviderConfig, SelectedModelConfig


def _normalize_model_ids(raw_ids: Any, default_model: str) -> list[str]:
    """把 legacy allowlist 归一成稳定的模型 ID 列表，确保默认模型一定会被写进去。"""

    model_ids: list[str] = []
    if isinstance(raw_ids, list):
        for item in raw_ids:
            model_id = str(item).strip()
            if model_id and model_id not in model_ids:
                model_ids.append(model_id)
    if default_model and default_model not in model_ids:
        model_ids.insert(0, default_model)
    return model_ids


def bootstrap_legacy_deepseek_config(legacy_settings: Mapping[str, Any]) -> ModelProviderConfig:
    """把旧版平铺 DeepSeek 环境变量转换成首份独立 JSON 配置。"""

    api_key = str(legacy_settings.get("deepseek_api_key") or "").strip()
    base_url = str(legacy_settings.get("deepseek_base_url") or "https://api.deepseek.com").strip()
    default_model = str(legacy_settings.get("default_model") or "deepseek-v4-flash").strip()
    model_ids = _normalize_model_ids(legacy_settings.get("model_allowlist"), default_model)

    provider = ProviderConfig(
        id="provider_deepseek_default",
        type="openai_compatible",
        label="DeepSeek 默认账号",
        enabled=bool(api_key),
        api_key=api_key or None,
        base_url=base_url,
        wire_api="chat_completions",
        api_path_mode="raw_root",
        selected_models=[
            SelectedModelConfig(remote_id=model_id, label=model_id, enabled=True) for model_id in model_ids
        ],
    )
    return ModelProviderConfig(
        default_model_ref=f"{provider.id}::{default_model}",
        providers=[provider],
    )
