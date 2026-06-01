from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


MODEL_PROVIDER_CONFIG_VERSION = 1
OPENAI_COMPATIBLE_WIRE_APIS = {"chat_completions", "responses"}
OPENAI_COMPATIBLE_API_PATH_MODES = {"raw_root", "append_v1"}


def _parse_default_model_ref(default_model_ref: str) -> tuple[str, str]:
    """把 defaultModelRef 解析成 provider 和模型 ID，便于做一致性校验。"""

    if default_model_ref.count("::") != 1:
        raise ValueError("defaultModelRef 必须采用 provider_id::remote_id 格式")
    provider_id, remote_id = default_model_ref.split("::", 1)
    if not provider_id or not remote_id:
        raise ValueError("defaultModelRef 必须同时包含 provider_id 和 remote_id")
    return provider_id, remote_id


def mask_api_key(api_key: str | None) -> str | None:
    """把密钥转换成适合返回给前端的预览值，避免把完整凭证回传到页面。"""

    if not api_key:
        return None
    if len(api_key) <= 8:
        return f"{api_key[:4]}***"
    return f"{api_key[:4]}***{api_key[-4:]}"


class SelectedModelConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    remote_id: str = Field(alias="remoteId")
    label: str = ""
    enabled: bool = True


class ProviderConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: str
    type: str
    label: str = ""
    enabled: bool = True
    api_key: str | None = Field(default=None, alias="apiKey")
    api_key_preview: str | None = Field(default=None, alias="apiKeyPreview")
    base_url: str = Field(default="", alias="baseUrl")
    wire_api: str | None = Field(default=None, alias="wireApi")
    api_path_mode: str | None = Field(default=None, alias="apiPathMode")
    selected_models: list[SelectedModelConfig] = Field(default_factory=list, alias="selectedModels")

    def to_masked_dict(self) -> dict[str, Any]:
        """返回给前端的安全视图，只保留 apiKey 的预览值。"""

        payload = self.model_dump(by_alias=True, exclude_none=True)
        preview = mask_api_key(self.api_key)
        if preview:
            payload["apiKeyPreview"] = preview
        payload.pop("apiKey", None)
        return payload

    def to_persisted_dict(self) -> dict[str, Any]:
        """返回写入磁盘的结构，必须保留真实 apiKey，但不能把预览值写进去。"""

        payload = self.model_dump(by_alias=True, exclude_none=True)
        payload.pop("apiKeyPreview", None)
        return payload

    @model_validator(mode="after")
    def validate_selected_models_unique(self) -> "ProviderConfig":
        """同一个 provider 内的模型远端 ID 必须唯一，避免默认模型和列表出现歧义。"""

        if self.type == "openai_compatible":
            if self.wire_api is None:
                self.wire_api = "chat_completions"
            if self.api_path_mode is None:
                self.api_path_mode = "raw_root"

            if self.wire_api not in OPENAI_COMPATIBLE_WIRE_APIS:
                raise ValueError(
                    f"provider {self.id} 的 wireApi 不合法: {self.wire_api}"
                )
            if self.api_path_mode not in OPENAI_COMPATIBLE_API_PATH_MODES:
                raise ValueError(
                    f"provider {self.id} 的 apiPathMode 不合法: {self.api_path_mode}"
                )
        else:
            self.wire_api = None
            self.api_path_mode = None

        seen_remote_ids: set[str] = set()
        for selected_model in self.selected_models:
            if selected_model.remote_id in seen_remote_ids:
                raise ValueError(
                    f"provider {self.id} 的 selectedModels.remoteId 重复: {selected_model.remote_id}"
                )
            seen_remote_ids.add(selected_model.remote_id)
        return self


class ModelProviderConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    version: int = MODEL_PROVIDER_CONFIG_VERSION
    default_model_ref: str = Field(default="", alias="defaultModelRef")
    providers: list[ProviderConfig] = Field(default_factory=list)

    def to_masked_dict(self) -> dict[str, Any]:
        """把完整配置转成前端可展示的结构，避免泄露原始密钥。"""

        payload = self.model_dump(by_alias=True, exclude_none=True)
        payload["providers"] = [provider.to_masked_dict() for provider in self.providers]
        return payload

    def to_persisted_dict(self) -> dict[str, Any]:
        """把完整配置转成磁盘结构，保留真实密钥但剔除所有预览字段。"""

        payload = self.model_dump(by_alias=True, exclude_none=True)
        payload["providers"] = [provider.to_persisted_dict() for provider in self.providers]
        return payload

    @model_validator(mode="after")
    def validate_consistency(self) -> "ModelProviderConfig":
        """配置写盘前先校验结构一致性，避免保存出无法回放的模型配置。"""

        if not self.providers:
            raise ValueError("providers 不能为空")

        providers_by_id: dict[str, ProviderConfig] = {}
        for provider in self.providers:
            if provider.id in providers_by_id:
                raise ValueError(f"provider id 重复: {provider.id}")
            providers_by_id[provider.id] = provider

        if not self.default_model_ref:
            raise ValueError("defaultModelRef 不能为空")

        provider_id, remote_id = _parse_default_model_ref(self.default_model_ref)
        provider = providers_by_id.get(provider_id)
        if provider is None:
            raise ValueError(f"defaultModelRef 指向不存在的 provider: {provider_id}")

        selected_ids = {selected_model.remote_id for selected_model in provider.selected_models}
        if remote_id not in selected_ids:
            raise ValueError(f"defaultModelRef 指向不存在的 selectedModels.remoteId: {remote_id}")

        return self
