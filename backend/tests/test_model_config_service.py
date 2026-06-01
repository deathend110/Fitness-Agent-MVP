import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

import backend.model_config.service as model_config_service_module
from backend.model_config.service import ModelProviderConfigService


def test_loads_provider_config_from_json_file(tmp_path: Path) -> None:
    config_file = tmp_path / "model_providers.json"
    config_file.write_text(
        """
        {
          "version": 1,
          "defaultModelRef": "provider_deepseek_main::deepseek-v4-flash",
          "providers": [
            {
              "id": "provider_deepseek_main",
              "type": "openai_compatible",
              "label": "DeepSeek 主账号",
              "enabled": true,
              "apiKey": "sk-test",
              "baseUrl": "https://api.deepseek.com",
              "selectedModels": [
                {
                  "remoteId": "deepseek-v4-flash",
                  "label": "DeepSeek V4 Flash",
                  "enabled": true
                }
              ]
            }
          ]
        }
        """.strip(),
        encoding="utf-8",
    )

    service = ModelProviderConfigService(config_path=config_file)
    config = service.load()

    assert config.default_model_ref == "provider_deepseek_main::deepseek-v4-flash"
    assert config.providers[0].type == "openai_compatible"


def test_bootstraps_legacy_deepseek_env_when_json_missing(tmp_path: Path) -> None:
    config_file = tmp_path / "missing.json"
    service = ModelProviderConfigService(
        config_path=config_file,
        legacy_settings={
            "deepseek_api_key": "sk-legacy",
            "deepseek_base_url": "https://api.deepseek.com",
            "default_model": "deepseek-v4-flash",
            "model_allowlist": ["deepseek-v4-flash", "deepseek-v4-pro"],
            "default_thinking_enabled": False,
            "default_thinking_budget": "auto",
        },
    )

    config = service.load()

    assert config.providers[0].id == "provider_deepseek_default"
    assert config.default_model_ref == "provider_deepseek_default::deepseek-v4-flash"
    assert config_file.exists()


def test_bootstraps_live_settings_when_legacy_settings_not_provided(
    monkeypatch,
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "missing.json"
    fake_settings = SimpleNamespace(
        model_provider_config_path=str(config_file),
        deepseek_api_key="sk-live",
        deepseek_base_url="https://api.deepseek.com",
        default_model="deepseek-v4-flash",
        model_allowlist=["deepseek-v4-flash", "deepseek-v4-pro"],
        default_thinking_enabled=False,
        default_thinking_budget="auto",
    )
    monkeypatch.setattr(model_config_service_module, "get_settings", lambda: fake_settings)

    service = ModelProviderConfigService()
    config = service.load()

    assert config.providers[0].id == "provider_deepseek_default"
    assert config.default_model_ref == "provider_deepseek_default::deepseek-v4-flash"
    assert config_file.exists()


def test_bootstraps_live_settings_even_when_deepseek_api_key_is_empty(
    monkeypatch,
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "missing.json"
    fake_settings = SimpleNamespace(
        model_provider_config_path=str(config_file),
        deepseek_api_key="",
        deepseek_base_url="https://api.deepseek.com",
        default_model="deepseek-v4-flash",
        model_allowlist=["deepseek-v4-flash", "deepseek-v4-pro"],
        default_thinking_enabled=False,
        default_thinking_budget="auto",
    )
    monkeypatch.setattr(model_config_service_module, "get_settings", lambda: fake_settings)

    service = ModelProviderConfigService()
    config = service.load()

    assert config.providers[0].base_url == "https://api.deepseek.com"
    assert [model.remote_id for model in config.providers[0].selected_models] == [
        "deepseek-v4-flash",
        "deepseek-v4-pro",
    ]
    assert config_file.exists()


def test_constructor_skips_global_settings_when_explicit_inputs_are_provided(monkeypatch, tmp_path: Path) -> None:
    config_file = tmp_path / "model_providers.json"

    def _boom() -> object:
        raise AssertionError("get_settings should not be called for explicit constructor inputs")

    monkeypatch.setattr(model_config_service_module, "get_settings", _boom)

    service = ModelProviderConfigService(
        config_path=config_file,
        legacy_settings={
            "deepseek_api_key": "sk-legacy",
            "deepseek_base_url": "https://api.deepseek.com",
            "default_model": "deepseek-v4-flash",
            "model_allowlist": ["deepseek-v4-flash"],
            "default_thinking_enabled": False,
            "default_thinking_budget": "auto",
        },
    )

    assert service.config_path == config_file
    assert service.legacy_settings["deepseek_api_key"] == "sk-legacy"


def test_load_rejects_invalid_json(tmp_path: Path) -> None:
    config_file = tmp_path / "model_providers.json"
    config_file.write_text("{ invalid json", encoding="utf-8")

    service = ModelProviderConfigService(
        config_path=config_file,
        legacy_settings={
            "deepseek_api_key": "sk-legacy",
            "deepseek_base_url": "https://api.deepseek.com",
            "default_model": "deepseek-v4-flash",
            "model_allowlist": ["deepseek-v4-flash"],
            "default_thinking_enabled": False,
            "default_thinking_budget": "auto",
        },
    )

    with pytest.raises(json.JSONDecodeError):
        service.load()


def test_save_rejects_invalid_default_model_ref(tmp_path: Path) -> None:
    config_file = tmp_path / "model_providers.json"
    service = ModelProviderConfigService(config_path=config_file)
    payload = {
        "version": 1,
        "defaultModelRef": "provider_missing::missing-model",
        "providers": [
            {
                "id": "provider_gemini_main",
                "type": "gemini_native",
                "label": "Gemini 主账号",
                "enabled": True,
                "apiKey": "AIza-real-key",
                "baseUrl": "https://generativelanguage.googleapis.com/v1beta",
                "selectedModels": [
                    {"remoteId": "gemini-2.5-flash", "label": "Gemini 2.5 Flash", "enabled": True}
                ],
            }
        ],
    }

    with pytest.raises(ValidationError, match="defaultModelRef"):
        service.save(payload)

    assert not config_file.exists()


def test_save_rejects_duplicate_provider_ids(tmp_path: Path) -> None:
    config_file = tmp_path / "model_providers.json"
    service = ModelProviderConfigService(config_path=config_file)
    payload = {
        "version": 1,
        "defaultModelRef": "provider_gemini_main::gemini-2.5-flash",
        "providers": [
            {
                "id": "provider_gemini_main",
                "type": "gemini_native",
                "label": "Gemini 主账号 A",
                "enabled": True,
                "apiKey": "AIza-real-key",
                "baseUrl": "https://generativelanguage.googleapis.com/v1beta",
                "selectedModels": [
                    {"remoteId": "gemini-2.5-flash", "label": "Gemini 2.5 Flash", "enabled": True}
                ],
            },
            {
                "id": "provider_gemini_main",
                "type": "gemini_native",
                "label": "Gemini 主账号 B",
                "enabled": True,
                "apiKey": "AIza-real-key-2",
                "baseUrl": "https://generativelanguage.googleapis.com/v1beta",
                "selectedModels": [
                    {"remoteId": "gemini-2.5-pro", "label": "Gemini 2.5 Pro", "enabled": True}
                ],
            },
        ],
    }

    with pytest.raises(ValidationError, match="provider id"):
        service.save(payload)

    assert not config_file.exists()


def test_save_rejects_duplicate_selected_model_ids(tmp_path: Path) -> None:
    config_file = tmp_path / "model_providers.json"
    service = ModelProviderConfigService(config_path=config_file)
    payload = {
        "version": 1,
        "defaultModelRef": "provider_gemini_main::gemini-2.5-flash",
        "providers": [
            {
                "id": "provider_gemini_main",
                "type": "gemini_native",
                "label": "Gemini 主账号",
                "enabled": True,
                "apiKey": "AIza-real-key",
                "baseUrl": "https://generativelanguage.googleapis.com/v1beta",
                "selectedModels": [
                    {"remoteId": "gemini-2.5-flash", "label": "Gemini 2.5 Flash", "enabled": True},
                    {"remoteId": "gemini-2.5-flash", "label": "重复项", "enabled": False},
                ],
            }
        ],
    }

    with pytest.raises(ValidationError, match="selectedModels.remoteId"):
        service.save(payload)

    assert not config_file.exists()


def test_save_masks_api_key_in_response_but_persists_full_value(tmp_path: Path) -> None:
    config_file = tmp_path / "model_providers.json"
    service = ModelProviderConfigService(config_path=config_file)
    payload = {
        "version": 1,
        "defaultModelRef": "provider_gemini_main::gemini-2.5-flash",
        "providers": [
            {
                "id": "provider_gemini_main",
                "type": "gemini_native",
                "label": "Gemini 主账号",
                "enabled": True,
                "apiKey": "AIza-real-key",
                "baseUrl": "https://generativelanguage.googleapis.com/v1beta",
                "selectedModels": [
                    {"remoteId": "gemini-2.5-flash", "label": "Gemini 2.5 Flash", "enabled": True}
                ],
            }
        ],
    }

    saved = service.save(payload)

    assert saved["providers"][0]["apiKeyPreview"].startswith("AIza")
    assert "apiKey" not in saved["providers"][0]
    assert "AIza-real-key" in config_file.read_text(encoding="utf-8")


def test_save_preserves_existing_api_key_and_ignores_preview_only_payload(tmp_path: Path) -> None:
    config_file = tmp_path / "model_providers.json"
    config_file.write_text(
        json.dumps(
            {
                "version": 1,
                "defaultModelRef": "provider_gemini_main::gemini-2.5-flash",
                "providers": [
                    {
                        "id": "provider_gemini_main",
                        "type": "gemini_native",
                        "label": "Gemini 主账号",
                        "enabled": True,
                        "apiKey": "old-real-key",
                        "baseUrl": "https://generativelanguage.googleapis.com/v1beta",
                        "selectedModels": [
                            {
                                "remoteId": "gemini-2.5-flash",
                                "label": "Gemini 2.5 Flash",
                                "enabled": True,
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    service = ModelProviderConfigService(config_path=config_file)
    payload = {
        "version": 1,
        "defaultModelRef": "provider_gemini_main::gemini-2.5-flash",
        "providers": [
            {
                "id": "provider_gemini_main",
                "type": "gemini_native",
                "label": "Gemini 主账号（已更新）",
                "enabled": True,
                "apiKeyPreview": "AIza-preview-only",
                "baseUrl": "https://generativelanguage.googleapis.com/v1beta",
                "selectedModels": [
                    {"remoteId": "gemini-2.5-flash", "label": "Gemini 2.5 Flash", "enabled": True}
                ],
            }
        ],
    }

    saved = service.save(payload)
    file_text = config_file.read_text(encoding="utf-8")

    assert "old-real-key" in file_text
    assert "apiKeyPreview" not in file_text
    assert saved["providers"][0]["apiKeyPreview"] == "old-***-key"
    assert "apiKey" not in saved["providers"][0]


def test_save_clears_existing_api_key_when_empty_string_is_explicitly_provided(tmp_path: Path) -> None:
    config_file = tmp_path / "model_providers.json"
    config_file.write_text(
        json.dumps(
            {
                "version": 1,
                "defaultModelRef": "provider_gemini_main::gemini-2.5-flash",
                "providers": [
                    {
                        "id": "provider_gemini_main",
                        "type": "gemini_native",
                        "label": "Gemini 主账号",
                        "enabled": True,
                        "apiKey": "old-real-key",
                        "baseUrl": "https://generativelanguage.googleapis.com/v1beta",
                        "selectedModels": [
                            {
                                "remoteId": "gemini-2.5-flash",
                                "label": "Gemini 2.5 Flash",
                                "enabled": True,
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    service = ModelProviderConfigService(config_path=config_file)
    payload = {
        "version": 1,
        "defaultModelRef": "provider_gemini_main::gemini-2.5-flash",
        "providers": [
            {
                "id": "provider_gemini_main",
                "type": "gemini_native",
                "label": "Gemini 主账号（清空密钥）",
                "enabled": True,
                "apiKey": "",
                "baseUrl": "https://generativelanguage.googleapis.com/v1beta",
                "selectedModels": [
                    {"remoteId": "gemini-2.5-flash", "label": "Gemini 2.5 Flash", "enabled": True}
                ],
            }
        ],
    }

    saved = service.save(payload)
    persisted = config_file.read_text(encoding="utf-8")
    loaded = service.load()

    assert "old-real-key" not in persisted
    assert '"apiKey": ""' in persisted
    assert loaded.providers[0].api_key == ""
    assert "apiKeyPreview" not in saved["providers"][0]

    second_payload = {
        "version": 1,
        "defaultModelRef": "provider_gemini_main::gemini-2.5-flash",
        "providers": [
            {
                "id": "provider_gemini_main",
                "type": "gemini_native",
                "label": "Gemini 主账号（继续保存）",
                "enabled": True,
                "baseUrl": "https://generativelanguage.googleapis.com/v1beta",
                "selectedModels": [
                    {"remoteId": "gemini-2.5-flash", "label": "Gemini 2.5 Flash", "enabled": True}
                ],
            }
        ],
    }

    second_saved = service.save(second_payload)
    persisted_again = config_file.read_text(encoding="utf-8")

    assert '"apiKey": ""' in persisted_again
    assert "old-real-key" not in persisted_again
    assert "apiKeyPreview" not in second_saved["providers"][0]
