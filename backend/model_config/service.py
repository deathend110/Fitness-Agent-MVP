from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from backend.config import get_settings
from backend.model_config.bootstrap import bootstrap_legacy_deepseek_config
from backend.model_config.types import ModelProviderConfig


class ModelProviderConfigService:
    def __init__(
        self,
        config_path: Path | str | None = None,
        legacy_settings: Mapping[str, Any] | None = None,
    ) -> None:
        settings = get_settings()
        self.config_path = Path(config_path or settings.model_provider_config_path)
        self.legacy_settings = dict(legacy_settings or {})

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
        self._write_config(config)
        return config.to_masked_dict()

    def _coerce_config(self, payload: Mapping[str, Any] | ModelProviderConfig) -> ModelProviderConfig:
        if isinstance(payload, ModelProviderConfig):
            return payload
        return ModelProviderConfig.model_validate(payload)

    def _read_config(self) -> ModelProviderConfig:
        raw_text = self.config_path.read_text(encoding="utf-8")
        return ModelProviderConfig.model_validate(json.loads(raw_text))

    def _write_config(self, config: ModelProviderConfig) -> None:
        # 先写入同目录临时文件，再原子替换，避免进程中断时留下半截 JSON。
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.config_path.with_name(f"{self.config_path.name}.tmp")
        payload = json.dumps(config.model_dump(by_alias=True, exclude_none=True), ensure_ascii=False, indent=2)
        temp_path.write_text(payload + "\n", encoding="utf-8")
        temp_path.replace(self.config_path)
