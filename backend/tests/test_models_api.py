from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from backend.api import models as models_api
from backend.main import app


@pytest.mark.asyncio
async def test_models_api_returns_selected_models_from_runtime_cache(monkeypatch) -> None:
    class FakeRuntime:
        default_model_ref = "provider_gemini_main::gemini-2.5-flash"

        def list_enabled_models(self):
            return [
                {
                    "id": "provider_gemini_main::gemini-2.5-flash",
                    "providerId": "provider_gemini_main",
                    "providerType": "gemini_native",
                    "providerLabel": "Gemini 主账号",
                    "remoteModelId": "gemini-2.5-flash",
                    "label": "Gemini 主账号 / Gemini 2.5 Flash",
                    "supportsThinking": True,
                    "thinking": {
                        "supported": True,
                        "canDisable": True,
                        "defaultEnabled": True,
                        "intensityOptions": [{"id": "standard", "label": "标准"}],
                        "defaultIntensity": "standard",
                    },
                }
            ]

    monkeypatch.setattr(models_api, "get_provider_runtime", lambda: FakeRuntime())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/api/models")

    assert response.status_code == 200
    payload = response.json()
    assert payload["defaultModel"] == "provider_gemini_main::gemini-2.5-flash"
    assert payload["defaultModelRef"] == "provider_gemini_main::gemini-2.5-flash"
    assert payload["models"][0]["label"] == "Gemini 主账号 / Gemini 2.5 Flash"
    assert payload["models"][0]["thinking"]["defaultIntensity"] == "standard"
    assert payload["warning"] == ""


@pytest.mark.asyncio
async def test_models_api_keeps_legacy_top_level_thinking_for_current_ui(monkeypatch) -> None:
    class FakeRuntime:
        default_model_ref = "provider_deepseek_main::deepseek-v4-flash"

        def list_enabled_models(self):
            return [
                {
                    "id": "provider_deepseek_main::deepseek-v4-flash",
                    "providerId": "provider_deepseek_main",
                    "providerType": "openai_compatible",
                    "providerLabel": "DeepSeek 主账号",
                    "remoteModelId": "deepseek-v4-flash",
                    "label": "DeepSeek 主账号 / DeepSeek V4 Flash",
                    "supportsThinking": True,
                    "thinking": {
                        "supported": True,
                        "canDisable": True,
                        "defaultEnabled": False,
                        "intensityOptions": [
                            {"id": "standard", "label": "标准"},
                            {"id": "deep", "label": "深入"},
                        ],
                        "defaultIntensity": "standard",
                    },
                }
            ]

    monkeypatch.setattr(models_api, "get_provider_runtime", lambda: FakeRuntime())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/api/models")

    assert response.status_code == 200
    payload = response.json()
    assert payload["thinking"] == {"enabled": False, "budget": "standard", "options": ["off", "standard", "deep"]}
