from __future__ import annotations

from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from backend.agent.deepseek_client import DeepSeekClientError
from backend.api import models as models_api
from backend.config import Settings
from backend.main import app


class FakeModelsClient:
    def __init__(self, payload: list[dict[str, Any]] | None = None, error: Exception | None = None) -> None:
        self.payload = payload or []
        self.error = error

    async def list_models(self) -> list[dict[str, Any]]:
        if self.error is not None:
            raise self.error
        return self.payload


@pytest.mark.asyncio
async def test_models_api_filters_remote_models_to_allowlist() -> None:
    app.dependency_overrides[models_api.get_models_settings] = lambda: Settings(
        deepseek_api_key="test-key",
        model_allowlist=["deepseek-v4-flash", "deepseek-v4-pro"],
        default_model="deepseek-v4-flash",
    )
    app.dependency_overrides[models_api.get_models_client] = lambda: FakeModelsClient(
        [
            {"id": "deepseek-v4-pro"},
            {"id": "unknown-model"},
            {"id": "deepseek-v4-flash"},
        ]
    )

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get("/api/models")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "remote"
    assert payload["defaultModel"] == "deepseek-v4-flash"
    assert [item["id"] for item in payload["models"]] == ["deepseek-v4-pro", "deepseek-v4-flash"]
    assert payload["models"][0]["label"] == "DeepSeek V4 Pro"
    assert payload["models"][0]["supportsThinking"] is True
    assert payload["thinking"] == {"enabled": False, "budget": "auto", "options": ["off", "auto", "max"]}


@pytest.mark.asyncio
async def test_models_api_falls_back_without_key_or_when_upstream_fails() -> None:
    app.dependency_overrides[models_api.get_models_settings] = lambda: Settings(
        deepseek_api_key="",
        model_allowlist=["deepseek-v4-flash", "deepseek-v4-pro"],
        default_model="deepseek-v4-flash",
    )
    app.dependency_overrides[models_api.get_models_client] = lambda: FakeModelsClient(
        error=DeepSeekClientError("boom", code="network_error")
    )

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get("/api/models")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "fallback"
    assert payload["warning"]
    assert [item["id"] for item in payload["models"]] == ["deepseek-v4-flash", "deepseek-v4-pro"]
    assert "deepseek-chat" not in [item["id"] for item in payload["models"]]
