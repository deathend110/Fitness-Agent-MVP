from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from backend.config import get_settings
from backend.model_config.bootstrap import bootstrap_legacy_deepseek_config
from backend.model_config.types import ModelProviderConfig, ProviderConfig


class ModelProviderConfigService:
    def __init__(
        self,
        config_path: Path | str | None = None,
        legacy_settings: Mapping[str, Any] | None = None,
    ) -> None:
        settings = get_settings()
        self.config_path = Path(config_path or settings.model_provider_config_path)
        if legacy_settings is None:
            self.legacy_settings = self._build_live_legacy_settings(settings)
        else:
            self.legacy_settings = dict(legacy_settings)

    def load(self) -> ModelProviderConfig:
        """优先读取独立 JSON 文件；文件不存在时用 legacy DeepSeek 配置补第一份。"""

        if self.config_path.exists():
            return self._read_config()

        if self.legacy_settings.get("deepseek_api_key"):
            config = bootstrap_legacy_deepseek_config(self.legacy_settings)
            self._write_config(config)
            return config

        return ModelProviderConfig()

    def save(self, payload: Mapping[str, Any] | ModelProviderConfig) -> dict[str, Any]:
        """保存完整密钥到磁盘，但返回给调用方的是脱敏后的安全结构。"""

        config = self._coerce_config(payload)
        existing_config = self._read_config() if self.config_path.exists() else None
        config = self._merge_with_existing_config(config, existing_config)
        self._write_config(config)
        return config.to_masked_dict()

    def _coerce_config(self, payload: Mapping[str, Any] | ModelProviderConfig) -> ModelProviderConfig:
        if isinstance(payload, ModelProviderConfig):
            return payload
        return ModelProviderConfig.model_validate(payload)

    def _read_config(self) -> ModelProviderConfig:
        raw_text = self.config_path.read_text(encoding="utf-8")
        return ModelProviderConfig.model_validate(json.loads(raw_text))

    def _build_live_legacy_settings(self, settings: Any) -> dict[str, Any]:
        """把当前启动配置转换成 legacy DeepSeek 视图，供首次落盘时自动生成 JSON。"""

        return {
            "deepseek_api_key": settings.deepseek_api_key,
            "deepseek_base_url": settings.deepseek_base_url,
            "default_model": settings.default_model,
            "model_allowlist": list(settings.model_allowlist),
            "default_thinking_enabled": settings.default_thinking_enabled,
            "default_thinking_budget": settings.default_thinking_budget,
        }

    def _merge_with_existing_config(
        self,
        incoming: ModelProviderConfig,
        existing: ModelProviderConfig | None,
    ) -> ModelProviderConfig:
        """合并保存内容时保留旧密钥，避免前端回传的预览值覆盖真实凭证。"""

        if existing is None:
            return incoming

        existing_by_id = {provider.id: provider for provider in existing.providers}
        merged_providers: list[ProviderConfig] = []
        for provider in incoming.providers:
            existing_provider = existing_by_id.get(provider.id)
            api_key = provider.api_key
            if not api_key and existing_provider and existing_provider.api_key:
                api_key = existing_provider.api_key
            merged_providers.append(
                ProviderConfig(
                    id=provider.id,
                    type=provider.type,
                    label=provider.label,
                    enabled=provider.enabled,
                    api_key=api_key,
                    base_url=provider.base_url,
                    selected_models=provider.selected_models,
                )
            )

        return ModelProviderConfig(
            version=incoming.version,
            default_model_ref=incoming.default_model_ref,
            providers=merged_providers,
        )

    def _write_config(self, config: ModelProviderConfig) -> None:
        # 先写入同目录临时文件，再原子替换，避免进程中断时留下半截 JSON。
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.config_path.with_name(f"{self.config_path.name}.tmp")
        payload = json.dumps(config.to_persisted_dict(), ensure_ascii=False, indent=2)
        temp_path.write_text(payload + "\n", encoding="utf-8")
        temp_path.replace(self.config_path)
