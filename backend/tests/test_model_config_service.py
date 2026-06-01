from pathlib import Path

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
