from __future__ import annotations

import pytest

from backend.providers.base import (
    ProviderAdapterError,
    build_responses_followup_messages,
    convert_messages_to_responses_input,
)
from backend.providers.openai_compatible import OpenAICompatibleProvider


def test_builds_models_endpoint_for_raw_root_base_url() -> None:
    provider = OpenAICompatibleProvider()

    assert (
        provider.build_request_url(
            base_url="https://api.deepseek.com",
            path="/models",
            api_path_mode="raw_root",
        )
        == "https://api.deepseek.com/models"
    )


def test_builds_models_endpoint_without_double_v1_when_base_url_already_contains_v1() -> None:
    provider = OpenAICompatibleProvider()

    assert (
        provider.build_request_url(
            base_url="https://api.deepseek.com/v1",
            path="/models",
            api_path_mode="append_v1",
        )
        == "https://api.deepseek.com/v1/models"
    )


def test_builds_chat_completions_endpoint_with_append_v1_mode() -> None:
    provider = OpenAICompatibleProvider()

    assert (
        provider.build_request_url(
            base_url="https://host",
            path="/chat/completions",
            api_path_mode="append_v1",
        )
        == "https://host/v1/chat/completions"
    )


def test_builds_chat_completions_endpoint_without_double_v1_when_base_url_already_contains_v1() -> None:
    provider = OpenAICompatibleProvider()

    assert (
        provider.build_request_url(
            base_url="https://api.deepseek.com/v1",
            path="/chat/completions",
            api_path_mode="append_v1",
        )
        == "https://api.deepseek.com/v1/chat/completions"
    )


@pytest.mark.asyncio
async def test_lists_models_from_openai_compatible_models_endpoint() -> None:
    requests: list[tuple[str, dict[str, str], float]] = []

    class FakeClient:
        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

        async def get(
            self,
            url: str,
            *,
            headers: dict[str, str],
            timeout: float,
        ):
            requests.append((url, headers, timeout))

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
    assert requests[0][2] > 0


@pytest.mark.asyncio
async def test_lists_models_with_append_v1_mode_for_root_host() -> None:
    requests: list[str] = []

    class FakeClient:
        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

        async def get(
            self,
            url: str,
            *,
            headers: dict[str, str],
            timeout: float,
        ):
            del headers, timeout
            requests.append(url)

            class Response:
                status_code = 200
                is_success = True

                def json(self) -> dict[str, list[dict[str, str]]]:
                    return {"data": []}

            return Response()

    provider = OpenAICompatibleProvider(client_factory=lambda **_: FakeClient())
    await provider.list_remote_models(
        api_key="sk-test",
        base_url="https://host",
        api_path_mode="append_v1",
    )

    assert requests == ["https://host/v1/models"]


@pytest.mark.asyncio
async def test_lists_models_accepts_explicit_wire_api_and_append_v1_without_double_prefix() -> None:
    requests: list[str] = []

    class FakeClient:
        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

        async def get(
            self,
            url: str,
            *,
            headers: dict[str, str],
            timeout: float,
        ):
            del headers, timeout
            requests.append(url)

            class Response:
                status_code = 200
                is_success = True

                def json(self) -> dict[str, list[dict[str, str]]]:
                    return {"data": [{"id": "gpt-4.1-mini"}]}

            return Response()

    provider = OpenAICompatibleProvider(client_factory=lambda **_: FakeClient())
    models = await provider.list_remote_models(
        api_key="sk-test",
        base_url="https://api.openai.com/v1",
        wire_api="responses",
        api_path_mode="append_v1",
    )

    assert requests == ["https://api.openai.com/v1/models"]
    assert models == [
        {
            "remoteId": "gpt-4.1-mini",
            "label": "gpt-4.1-mini",
            "enabled": True,
        }
    ]


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


def test_normalizes_chat_completions_tool_calls() -> None:
    provider = OpenAICompatibleProvider()

    normalized = provider.normalize_tool_call_response(
        {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "get_profile",
                                    "arguments": '{"scope":"latest"}',
                                },
                            }
                        ],
                    }
                }
            ]
        }
    )

    assert normalized == [
        {
            "toolName": "get_profile",
            "callId": "call_1",
            "arguments": {"scope": "latest"},
            "rawProviderPayload": {
                "toolCall": {
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "get_profile",
                        "arguments": '{"scope":"latest"}',
                    },
                },
                "assistantMessage": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "get_profile",
                                "arguments": '{"scope":"latest"}',
                            },
                        }
                    ],
                },
            },
        }
    ]


def test_reads_chat_completions_text_from_first_message() -> None:
    provider = OpenAICompatibleProvider()

    assert (
        provider.read_text_response(
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "这是建议内容",
                        }
                    }
                ]
            }
        )
        == "这是建议内容"
    )


def test_normalizes_responses_function_calls() -> None:
    provider = OpenAICompatibleProvider(wire_api="responses")

    normalized = provider.normalize_tool_call_response(
        {
            "id": "resp_1",
            "output": [
                {"type": "reasoning", "summary": []},
                {
                    "type": "function_call",
                    "call_id": "call_1",
                    "name": "get_profile",
                    "arguments": '{"scope":"latest"}',
                },
            ],
        }
    )

    assert normalized == [
        {
            "toolName": "get_profile",
            "callId": "call_1",
            "arguments": {"scope": "latest"},
            "rawProviderPayload": {
                "responseId": "resp_1",
                "outputItems": [
                    {"type": "reasoning", "summary": []},
                    {
                        "type": "function_call",
                        "call_id": "call_1",
                        "name": "get_profile",
                        "arguments": '{"scope":"latest"}',
                    },
                ],
                "functionCall": {
                    "type": "function_call",
                    "call_id": "call_1",
                    "name": "get_profile",
                    "arguments": '{"scope":"latest"}',
                },
            },
        }
    ]


def test_reads_responses_text_from_output_message() -> None:
    provider = OpenAICompatibleProvider(wire_api="responses")

    assert (
        provider.read_text_response(
            {
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": "先减量一周，再观察疲劳恢复。",
                            }
                        ],
                    }
                ]
            }
        )
        == "先减量一周，再观察疲劳恢复。"
    )


def test_builds_followup_messages_for_chat_completions_tool_result() -> None:
    provider = OpenAICompatibleProvider()

    messages = [{"role": "user", "content": "读取档案"}]
    next_messages = provider.build_followup_messages_after_tool_result(
        messages,
        {
            "toolName": "get_profile",
            "callId": "call_1",
            "arguments": {},
            "rawProviderPayload": {
                "assistantMessage": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "get_profile",
                                "arguments": "{}",
                            },
                        }
                    ],
                    "reasoning_content": "先读取档案。",
                }
            },
        },
        '{"name":"阿杰"}',
    )

    assert next_messages[-2]["role"] == "assistant"
    assert next_messages[-2]["tool_calls"][0]["id"] == "call_1"
    assert next_messages[-2]["reasoning_content"] == "先读取档案。"
    assert next_messages[-1] == {
        "role": "tool",
        "tool_call_id": "call_1",
        "name": "get_profile",
        "content": '{"name":"阿杰"}',
    }


def test_builds_followup_messages_for_responses_function_output() -> None:
    provider = OpenAICompatibleProvider(wire_api="responses")

    messages = [{"role": "user", "content": "读取档案"}]
    next_messages = provider.build_followup_messages_after_tool_result(
        messages,
        {
            "toolName": "get_profile",
            "callId": "call_1",
            "arguments": {},
            "rawProviderPayload": {
                "responseId": "resp_1",
                "outputItems": [
                    {"type": "reasoning", "summary": []},
                    {
                        "type": "function_call",
                        "call_id": "call_1",
                        "name": "get_profile",
                        "arguments": "{}",
                    },
                ],
                "functionCall": {
                    "type": "function_call",
                    "call_id": "call_1",
                    "name": "get_profile",
                    "arguments": "{}",
                },
            },
        },
        '{"name":"阿杰"}',
    )

    assert next_messages[-3] == {"type": "reasoning", "summary": []}
    assert next_messages[-2] == {
        "type": "function_call",
        "call_id": "call_1",
        "name": "get_profile",
        "arguments": "{}",
    }
    assert next_messages[-1] == {
        "type": "function_call_output",
        "call_id": "call_1",
        "output": '{"name":"阿杰"}',
    }


def test_deduplicates_trailing_chat_completions_assistant_message_before_tool_result() -> None:
    provider = OpenAICompatibleProvider()
    assistant_message = {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "get_profile", "arguments": "{}"},
            }
        ],
    }

    next_messages = provider.build_followup_messages_after_tool_result(
        [
            {"role": "user", "content": "读取档案"},
            assistant_message,
        ],
        {
            "toolName": "get_profile",
            "callId": "call_1",
            "arguments": {},
            "rawProviderPayload": {"assistantMessage": assistant_message},
        },
        '{"name":"阿杰"}',
    )

    assert next_messages == [
        {"role": "user", "content": "读取档案"},
        assistant_message,
        {
            "role": "tool",
            "tool_call_id": "call_1",
            "name": "get_profile",
            "content": '{"name":"阿杰"}',
        },
    ]


def test_converts_messages_to_responses_input_for_user_assistant_and_tool_messages() -> None:
    converted = convert_messages_to_responses_input(
        [
            {"role": "system", "content": "你是 AI 教练"},
            {"role": "user", "content": "读取今天状态"},
            {"role": "assistant", "content": "先读取数据"},
            {
                "role": "tool",
                "tool_call_id": "call_1",
                "name": "get_profile",
                "content": {"fatigue": 8},
            },
        ]
    )

    assert converted == [
        {
            "type": "message",
            "role": "system",
            "content": [{"type": "input_text", "text": "你是 AI 教练"}],
        },
        {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": "读取今天状态"}],
        },
        {
            "type": "message",
            "role": "assistant",
            "content": [{"type": "output_text", "text": "先读取数据"}],
        },
        {
            "type": "function_call_output",
            "call_id": "call_1",
            "output": '{"fatigue": 8}',
        },
    ]


def test_build_responses_followup_messages_preserves_full_output_items_once() -> None:
    messages = [{"role": "user", "content": "读取档案"}]
    tool_call = {
        "toolName": "get_profile",
        "callId": "call_1",
        "arguments": {},
        "rawProviderPayload": {
            "responseId": "resp_1",
            "outputItems": [
                {"type": "reasoning", "summary": [{"type": "summary_text", "text": "先看档案"}]},
                {
                    "type": "function_call",
                    "call_id": "call_1",
                    "name": "get_profile",
                    "arguments": "{}",
                },
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": "已准备调用工具"}],
                },
            ],
        },
    }

    first_followup = build_responses_followup_messages(messages, tool_call, '{"name":"阿杰"}')
    second_followup = build_responses_followup_messages(first_followup, tool_call, '{"name":"阿杰"}')

    assert first_followup[-4:-1] == tool_call["rawProviderPayload"]["outputItems"]
    assert first_followup[-1] == {
        "type": "function_call_output",
        "call_id": "call_1",
        "output": '{"name":"阿杰"}',
    }
    assert second_followup.count(tool_call["rawProviderPayload"]["outputItems"][0]) == 1


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
            headers: dict[str, str],
            timeout: float,
        ):
            del url, headers, timeout

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
