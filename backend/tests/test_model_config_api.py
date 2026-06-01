from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.api import model_config as model_config_api
from backend.main import app


@pytest_asyncio.fixture
async def api_client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.asyncio
async def test_get_model_config_returns_masked_runtime_payload(
    api_client: AsyncClient,
    monkeypatch,
) -> None:
    class FakeRuntime:
        def get_masked_config(self):
            return {
                "version": 1,
                "defaultModelRef": "provider_deepseek_main::deepseek-v4-flash",
                "providers": [
                    {
                        "id": "provider_deepseek_main",
                        "type": "openai_compatible",
                        "label": "DeepSeek 主账号",
                        "enabled": True,
                        "apiKeyPreview": "sk-t***1234",
                        "baseUrl": "https://api.deepseek.com",
                        "selectedModels": [
                            {"remoteId": "deepseek-v4-flash", "label": "DeepSeek V4 Flash", "enabled": True}
                        ],
                    }
                ],
            }

    monkeypatch.setattr(model_config_api, "get_provider_runtime", lambda: FakeRuntime())

    response = await api_client.get("/api/model-config")

    assert response.status_code == 200
    payload = response.json()
    assert payload["defaultModelRef"] == "provider_deepseek_main::deepseek-v4-flash"
    assert payload["providers"][0]["apiKeyPreview"] == "sk-t***1234"
    assert "apiKey" not in payload["providers"][0]


@pytest.mark.asyncio
async def test_put_model_config_persists_file_and_refreshes_runtime(
    api_client: AsyncClient,
    monkeypatch,
    tmp_path: Path,
) -> None:
    refreshed: list[str] = []

    class FakeRuntime:
        def refresh(self):
            refreshed.append("ok")

    monkeypatch.setattr(model_config_api, "get_provider_runtime", lambda: FakeRuntime())
    monkeypatch.setattr(model_config_api, "get_model_config_path", lambda: tmp_path / "model_providers.json")

    response = await api_client.put(
        "/api/model-config",
        json={
            "version": 1,
            "defaultModelRef": "provider_deepseek_main::deepseek-v4-flash",
            "providers": [
                {
                    "id": "provider_deepseek_main",
                    "type": "openai_compatible",
                    "label": "DeepSeek 主账号",
                    "enabled": True,
                    "apiKey": "sk-test",
                    "baseUrl": "https://api.deepseek.com",
                    "selectedModels": [
                        {"remoteId": "deepseek-v4-flash", "label": "DeepSeek V4 Flash", "enabled": True}
                    ],
                }
            ],
        },
    )

    assert response.status_code == 200
    assert refreshed == ["ok"]
    assert (tmp_path / "model_providers.json").exists()
    assert response.json()["providers"][0]["apiKeyPreview"].startswith("sk-t")
