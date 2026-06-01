from __future__ import annotations

import pytest

from backend.providers.base import ProviderAdapterError
from backend.providers.openai_compatible import OpenAICompatibleProvider


@pytest.mark.asyncio
async def test_lists_models_from_openai_compatible_models_endpoint() -> None:
    requests: list[tuple[str, dict[str, str]]] = []

    class FakeClient:
        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

        async def get(self, url: str, *, headers: dict[str, str]):
            requests.append((url, headers))

            class Response:
                status_code = 200
                is_success = True

                def json(self) -> dict[str, list[dict[str, str]]]:
                    return {"data": [{"id": "deepseek-v4-flash"}]}

            return Response()

    provider = OpenAICompatibleProvider(client_factory=lambda **_: FakeClient())
    models = await provider.list_remote_models(
        api_key="sk-test",
        base_url="https://api.deepseek.com",
    )

    assert models == [
        {
            "remoteId": "deepseek-v4-flash",
            "label": "deepseek-v4-flash",
            "enabled": True,
        }
    ]
    assert requests[0][0] == "https://api.deepseek.com/models"
    assert requests[0][1]["Authorization"] == "Bearer sk-test"


def test_builds_tool_schema_in_openai_format() -> None:
    provider = OpenAICompatibleProvider()
    schema = provider.build_tool_schema(
        [
            {
                "name": "get_profile",
                "description": "读取档案",
                "parameters": {"type": "object", "properties": {}},
            }
        ]
    )

    assert schema[0]["type"] == "function"
    assert schema[0]["function"]["name"] == "get_profile"
    assert schema[0]["function"]["parameters"] == {"type": "object", "properties": {}}


@pytest.mark.asyncio
async def test_list_remote_models_maps_http_error_to_provider_adapter_error() -> None:
    class FakeClient:
        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

        async def get(self, url: str, *, headers: dict[str, str]):
            class Response:
                status_code = 401
                is_success = False
                reason_phrase = "Unauthorized"

                def json(self) -> dict[str, dict[str, str]]:
                    return {"error": {"message": "Invalid API key"}}

            return Response()

    provider = OpenAICompatibleProvider(client_factory=lambda **_: FakeClient())

    with pytest.raises(ProviderAdapterError) as exc_info:
        await provider.list_remote_models(
            api_key="sk-test",
            base_url="https://api.deepseek.com",
        )

    assert exc_info.value.status == 401
    assert exc_info.value.code == "http_error"
    assert exc_info.value.reason == "Invalid API key"
