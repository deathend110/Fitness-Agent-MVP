from __future__ import annotations

import pytest

from backend.agent.tool_calling import build_default_tool_registry
from backend.providers.base import ProviderAdapterError
from backend.providers.gemini_native import GeminiNativeProvider


def test_builds_gemini_tool_schema_from_internal_tools() -> None:
    provider = GeminiNativeProvider()
    schema = provider.build_tool_schema(
        [
            {
                "name": "get_profile",
                "description": "读取档案",
                "parameters": {"type": "object", "properties": {}},
            }
        ]
    )

    assert schema["functionDeclarations"][0]["name"] == "get_profile"
    assert schema["functionDeclarations"][0]["parameters"] == {"type": "object", "properties": {}}


def test_normalizes_gemini_function_call_response() -> None:
    provider = GeminiNativeProvider()
    normalized = provider.normalize_tool_call_response(
        {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "functionCall": {
                                    "name": "get_profile",
                                    "args": {"query": "latest"},
                                }
                            }
                        ]
                    }
                }
            ]
        }
    )

    assert normalized[0]["toolName"] == "get_profile"
    assert normalized[0]["arguments"] == {"query": "latest"}


def test_builds_followup_tool_result_message_in_gemini_format() -> None:
    provider = GeminiNativeProvider()

    messages = [{"role": "user", "parts": [{"text": "读取档案"}]}]
    next_messages = provider.build_followup_messages_after_tool_result(
        messages,
        {
            "toolName": "get_profile",
            "callId": "call-1",
            "arguments": {},
            "rawProviderPayload": {},
        },
        '{"name":"阿杰"}',
    )

    assert next_messages[-1]["role"] == "user"
    assert next_messages[-1]["parts"][0]["functionResponse"]["id"] == "call-1"
    assert next_messages[-1]["parts"][0]["functionResponse"]["name"] == "get_profile"
    assert next_messages[-1]["parts"][0]["functionResponse"]["response"]["result"] == '{"name":"阿杰"}'


def test_build_tool_schema_strips_openai_only_schema_fields_for_nested_tools() -> None:
    provider = GeminiNativeProvider()
    registry = build_default_tool_registry()

    schema = provider.build_tool_schema(registry.describe_tools())
    nested_parameters = next(
        declaration["parameters"]
        for declaration in schema["functionDeclarations"]
        if declaration["name"] == "propose_plan_change"
    )

    dumped = str(nested_parameters)

    assert "$defs" not in dumped
    assert "$ref" not in dumped
    assert "additionalProperties" not in dumped
    assert nested_parameters["properties"]["changes"]["items"]["properties"]["exerciseName"]["type"] == "string"
    # newValue 是 Any，Pydantic 产出空 schema；修复后必须兜底为 "string" 而不是空 dict，否则 Gemini 会拒绝整个工具声明。
    new_value_schema = nested_parameters["properties"]["changes"]["items"]["properties"]["newValue"]
    assert new_value_schema == {"type": "string"}


def test_build_tool_schema_gives_day_plan_replace_non_empty_object_properties() -> None:
    provider = GeminiNativeProvider()
    registry = build_default_tool_registry()

    schema = provider.build_tool_schema(registry.describe_tools())
    day_plan_parameters = next(
        declaration["parameters"]
        for declaration in schema["functionDeclarations"]
        if declaration["name"] == "propose_day_plan_replace"
    )

    day_plan_schema = day_plan_parameters["properties"]["dayPlan"]
    # dayPlan 过去是 dict[str, Any] -> {"type": "object", "properties": {}}，会被 Gemini 拒绝。
    # 修复后必须是带非空 properties 的 object，且同时暴露 type 与 exercises 两个字段指引。
    assert day_plan_schema["type"] == "object"
    assert day_plan_schema["properties"]
    assert "type" in day_plan_schema["properties"]
    assert "exercises" in day_plan_schema["properties"]
    # 嵌套动作里的 name 必须是带 type 的字符串属性，确保整条 functionDeclarations 不含无 type 的属性。
    exercise_name_schema = day_plan_schema["properties"]["exercises"]["items"]["properties"]["name"]
    assert exercise_name_schema["type"] == "string"


@pytest.mark.asyncio
async def test_lists_models_from_gemini_models_endpoint() -> None:
    class FakeClient:
        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

        async def get(
            self,
            url: str,
            *,
            headers: dict[str, str] | None = None,
            params: dict[str, str] | None = None,
        ):
            class Response:
                status_code = 200
                is_success = True

                def json(self) -> dict[str, list[dict[str, object]]]:
                    return {
                        "models": [
                            {
                                "name": "models/gemini-2.5-flash",
                                "displayName": "Gemini 2.5 Flash",
                                "supportedGenerationMethods": ["generateContent"],
                            },
                            {
                                "name": "models/text-embedding-004",
                                "displayName": "Text Embedding 004",
                                "supportedGenerationMethods": ["embedContent"],
                            },
                        ]
                    }

            return Response()

    provider = GeminiNativeProvider(client_factory=lambda **_: FakeClient())
    models = await provider.list_remote_models(
        api_key="AIza-test",
        base_url="https://generativelanguage.googleapis.com/v1beta",
    )

    assert models == [
        {
            "remoteId": "gemini-2.5-flash",
            "label": "Gemini 2.5 Flash",
            "enabled": True,
        }
    ]


@pytest.mark.asyncio
async def test_list_remote_models_accepts_openai_style_optional_args_without_affecting_gemini() -> None:
    request_snapshot: dict[str, object] = {}

    class FakeClient:
        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

        async def get(
            self,
            url: str,
            *,
            headers: dict[str, str] | None = None,
            params: dict[str, str] | None = None,
        ):
            request_snapshot["url"] = url
            request_snapshot["headers"] = headers or {}
            request_snapshot["params"] = params or {}

            class Response:
                status_code = 200
                is_success = True

                def json(self) -> dict[str, list[dict[str, object]]]:
                    return {"models": []}

            return Response()

    provider = GeminiNativeProvider(client_factory=lambda **_: FakeClient())
    models = await provider.list_remote_models(
        api_key="AIza-test",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        wire_api="responses",
        api_path_mode="append_v1",
    )

    assert models == []
    assert request_snapshot["url"] == "https://generativelanguage.googleapis.com/v1beta/models"
    assert request_snapshot["params"] == {"key": "AIza-test"}
    assert request_snapshot["headers"] == {}


@pytest.mark.asyncio
async def test_normalizes_official_gemini_base_url_and_uses_query_api_key() -> None:
    request_snapshot: dict[str, object] = {}

    class FakeClient:
        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

        async def get(
            self,
            url: str,
            *,
            headers: dict[str, str] | None = None,
            params: dict[str, str] | None = None,
        ):
            request_snapshot["url"] = url
            request_snapshot["headers"] = headers or {}
            request_snapshot["params"] = params or {}

            class Response:
                status_code = 200
                is_success = True

                def json(self) -> dict[str, list[dict[str, object]]]:
                    return {"models": []}

            return Response()

    provider = GeminiNativeProvider(client_factory=lambda **_: FakeClient())
    await provider.list_remote_models(
        api_key="AIza-test",
        base_url="https://generativelanguage.googleapis.com",
    )

    assert request_snapshot["url"] == "https://generativelanguage.googleapis.com/v1beta/models"
    assert request_snapshot["params"] == {"key": "AIza-test"}
    assert request_snapshot["headers"] == {}


@pytest.mark.asyncio
async def test_list_remote_models_maps_http_error_to_provider_adapter_error() -> None:
    class FakeClient:
        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

        async def get(
            self,
            url: str,
            *,
            headers: dict[str, str] | None = None,
            params: dict[str, str] | None = None,
        ):
            class Response:
                status_code = 403
                is_success = False
                reason_phrase = "Forbidden"

                def json(self) -> dict[str, dict[str, str]]:
                    return {"error": {"message": "API key not valid"}}

            return Response()

    provider = GeminiNativeProvider(client_factory=lambda **_: FakeClient())

    with pytest.raises(ProviderAdapterError) as exc_info:
        await provider.list_remote_models(
            api_key="AIza-test",
            base_url="https://generativelanguage.googleapis.com/v1beta",
        )

    assert exc_info.value.status == 403
    assert exc_info.value.code == "http_error"
    assert exc_info.value.reason == "API key not valid"
