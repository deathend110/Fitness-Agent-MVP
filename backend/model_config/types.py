from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


MODEL_PROVIDER_CONFIG_VERSION = 1


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
    selected_models: list[SelectedModelConfig] = Field(default_factory=list, alias="selectedModels")

    def to_masked_dict(self) -> dict[str, Any]:
        """返回给前端的安全视图，只保留 apiKey 的预览值。"""

        payload = self.model_dump(by_alias=True, exclude_none=True)
        preview = mask_api_key(self.api_key)
        if preview:
            payload["apiKeyPreview"] = preview
        payload.pop("apiKey", None)
        return payload


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
