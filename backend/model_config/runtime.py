from __future__ import annotations

from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from backend.model_config.service import ModelProviderConfigService
from backend.model_config.types import ModelProviderConfig, ProviderConfig


def _parse_model_ref(model_ref: str) -> tuple[str, str]:
    """把 provider::model 形式拆开，供运行时快速定位具体模型。"""

    if model_ref.count("::") != 1:
        raise ValueError("modelRef 必须采用 provider_id::remote_id 格式")
    provider_id, remote_model_id = model_ref.split("::", 1)
    if not provider_id or not remote_model_id:
        raise ValueError("modelRef 必须同时包含 provider_id 和 remote_id")
    return provider_id, remote_model_id


class ProviderRuntimeCache:
    def __init__(self, service: ModelProviderConfigService) -> None:
        self.service = service
        self.config_path = service.config_path
        self._document = service.load()
        self._providers_by_id = self._index_providers(self._document)

    @classmethod
    def from_path(
        cls,
        config_path: Path | str,
        legacy_settings: Mapping[str, Any] | None = None,
    ) -> "ProviderRuntimeCache":
        """用独立 JSON 配置文件路径创建运行时缓存。"""

        service = ModelProviderConfigService(config_path=config_path, legacy_settings=legacy_settings)
        return cls(service)

    @property
    def default_model_ref(self) -> str:
        """暴露当前默认模型引用，供后续路由和 UI 初始化直接读取。"""

        return self._document.default_model_ref

    @property
    def document(self) -> ModelProviderConfig:
        """只读暴露当前配置文档，避免外部直接改写缓存内部状态。"""

        return ModelProviderConfig.model_validate(self._document.model_dump(by_alias=True, exclude_none=True))

    @property
    def providers_by_id(self) -> Mapping[str, ProviderConfig]:
        """只读暴露 provider 索引，便于调用方查询但不直接持有内部字段。"""

        return MappingProxyType({provider_id: self._clone_provider(provider) for provider_id, provider in self._providers_by_id.items()})

    def refresh(self) -> ModelProviderConfig:
        """重新读取磁盘 JSON，让保存后的配置无需重启即可生效。"""

        self._document = self.service.load()
        self._providers_by_id = self._index_providers(self._document)
        return self._document

    def resolve_model_ref(self, model_ref: str) -> tuple[ProviderConfig, str]:
        """把 provider::remote_model_id 解析成 provider 对象和远端模型 ID。"""

        provider_id, remote_model_id = _parse_model_ref(model_ref)
        provider = self._providers_by_id.get(provider_id)
        if provider is None:
            raise ValueError(f"未找到 provider: {provider_id}")

        remote_model_ids = {model.remote_id for model in provider.selected_models}
        if remote_model_id not in remote_model_ids:
            raise ValueError(f"provider {provider_id} 不包含 remote_id: {remote_model_id}")

        return self._clone_provider(provider), remote_model_id

    @staticmethod
    def _index_providers(document: ModelProviderConfig) -> dict[str, ProviderConfig]:
        """按 provider.id 建索引，避免后续解析时每次遍历完整配置。"""

        return {provider.id: provider for provider in document.providers}

    @staticmethod
    def _clone_provider(provider: ProviderConfig) -> ProviderConfig:
        """对外返回 provider 副本，避免调用方修改共享缓存里的原始对象。"""

        return ProviderConfig.model_validate(provider.model_dump(by_alias=True, exclude_none=True))
