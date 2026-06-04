from __future__ import annotations

from collections.abc import AsyncIterator
import json
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
import httpx
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from backend.agent.chat_session import (
    OpenAICompatibleRuntimeClient,
    _ChatCompletionsToolLoopProvider,
    _OpenAIResponsesToolLoopProvider,
    build_provider_bound_client,
)
from backend.agent.deepseek_client import (
    DeepSeekChatResult,
    DeepSeekClient,
    DeepSeekClientError,
    DeepSeekStreamEvent,
)
from backend.api import chat as chat_api
from backend.db.database import create_engine_and_session_factory, get_db_session
from backend.db.models import Base, ToolCallLog, UploadedFile, utc_now
from backend.main import app
from backend.providers.gemini_client import GeminiNativeClient

pytestmark = [
    pytest.mark.filterwarnings(
        "error::pydantic.warnings.UnsupportedFieldAttributeWarning"
    ),
    pytest.mark.filterwarnings(
        "ignore:'asyncio.iscoroutinefunction' is deprecated:DeprecationWarning"
    ),
]


class FakeDeepSeekClient:
    def __init__(
        self,
        chunks: list[str] | None = None,
        *,
        error: DeepSeekClientError | None = None,
        error_after_chunks: DeepSeekClientError | None = None,
    ) -> None:
        self.chunks = chunks or []
        self.error = error
        self.error_after_chunks = error_after_chunks

    async def stream_chat(self, *, messages: list[dict[str, Any]], model: str, **_: Any) -> AsyncIterator[str]:
        del messages, model
        if self.error is not None:
            raise self.error

        for chunk in self.chunks:
            yield chunk

        if self.error_after_chunks is not None:
            raise self.error_after_chunks

    async def request_chat(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        stream: bool = False,
        **_: Any,
    ) -> str:
        del messages, model, stream
        if self.error is not None:
            raise self.error
        return "".join(self.chunks)


class FakeReplyModelClient(FakeDeepSeekClient):
    def __init__(self, reply: str) -> None:
        super().__init__([reply])
        self.calls: list[dict[str, Any]] = []

    async def request_chat(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        stream: bool = False,
        **_: Any,
    ) -> str:
        self.calls.append({"messages": messages, "model": model})
        return await super().request_chat(messages=messages, model=model, stream=stream, **_)


class FakeOpenAICompatibleChatCompletionsClient(FakeReplyModelClient):
    def __init__(self, reply: str) -> None:
        super().__init__(reply)
        self.stream_calls: list[dict[str, Any]] = []

    async def stream_chat_with_usage(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        **_: Any,
    ) -> AsyncIterator[DeepSeekStreamEvent]:
        self.stream_calls.append({"messages": messages, "model": model})
        yield DeepSeekStreamEvent(text="兼容 chat_completions 流式回复。")


class FakeAsyncHttpxResponse:
    def __init__(
        self,
        *,
        payload: dict[str, Any] | None = None,
        json_error: Exception | None = None,
        lines: list[str] | None = None,
        headers: dict[str, str] | None = None,
        status_code: int = 200,
        reason_phrase: str = "OK",
    ) -> None:
        self._payload = payload or {}
        self._json_error = json_error
        self._lines = lines or []
        self.headers = headers or {"content-type": "application/json"}
        self.status_code = status_code
        self.reason_phrase = reason_phrase
        self.is_success = 200 <= status_code < 300

    def json(self) -> dict[str, Any]:
        if self._json_error is not None:
            raise self._json_error
        return self._payload

    async def aiter_lines(self) -> AsyncIterator[str]:
        for line in self._lines:
            yield line


class FakeAsyncHttpxStreamContext:
    def __init__(self, response: FakeAsyncHttpxResponse) -> None:
        self.response = response

    async def __aenter__(self) -> FakeAsyncHttpxResponse:
        return self.response

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


class FakeAsyncHttpxClient:
    def __init__(
        self,
        *,
        post_response: FakeAsyncHttpxResponse | None = None,
        stream_response: FakeAsyncHttpxResponse | None = None,
        recorder: list[dict[str, Any]] | None = None,
        **_: Any,
    ) -> None:
        self.post_response = post_response or FakeAsyncHttpxResponse()
        self.stream_response = stream_response or FakeAsyncHttpxResponse(lines=["data: [DONE]"])
        self.recorder = recorder if recorder is not None else []

    async def __aenter__(self) -> "FakeAsyncHttpxClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False

    async def post(self, url: str, *, json: dict[str, Any], headers: dict[str, Any]) -> FakeAsyncHttpxResponse:
        self.recorder.append({"kind": "post", "url": url, "json": json, "headers": headers})
        return self.post_response

    def stream(
        self,
        method: str,
        url: str,
        *,
        json: dict[str, Any],
        headers: dict[str, Any],
    ) -> FakeAsyncHttpxStreamContext:
        self.recorder.append(
            {
                "kind": "stream",
                "method": method,
                "url": url,
                "json": json,
                "headers": headers,
            }
        )
        return FakeAsyncHttpxStreamContext(self.stream_response)


class FakeOpenAICompatibleResponsesClient:
    def __init__(
        self,
        *,
        text_reply: str = "responses 文本回复。",
        final_text: str = "已生成一张需要确认的训练计划调整卡。",
    ) -> None:
        self.text_reply = text_reply
        self.final_text = final_text
        self.response_calls: list[dict[str, Any]] = []
        self.stream_calls: list[dict[str, Any]] = []

    async def request_responses_with_usage(
        self,
        *,
        input_items: list[dict[str, Any]],
        model: str,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        self.response_calls.append(
            {
                "input_items": input_items,
                "model": model,
                "tools": tools,
                "tool_choice": tool_choice,
            }
        )
        if tools:
            if len(self.response_calls) == 1:
                return {
                    "output_text": "",
                    "output": [
                        {
                            "type": "function_call",
                            "call_id": "call_propose",
                            "name": "propose_plan_change",
                            "arguments": json.dumps(
                                {
                                    "day": "Monday",
                                    "summary": "把深蹲 RPE 下调，降低疲劳风险。",
                                    "changes": [
                                        {
                                            "action": "update",
                                            "exerciseName": "深蹲",
                                            "field": "rpe",
                                            "newValue": 7,
                                        }
                                    ],
                                },
                                ensure_ascii=False,
                            ),
                        }
                    ],
                }
            return {"output_text": self.final_text, "output": []}
        return {"output_text": self.text_reply, "output": []}

    async def stream_responses_with_usage(
        self,
        *,
        input_items: list[dict[str, Any]],
        model: str,
        **_: Any,
    ) -> AsyncIterator[tuple[str | None, dict[str, Any] | None]]:
        self.stream_calls.append({"input_items": input_items, "model": model})
        yield ("兼容 responses 流式回复。", None)

    async def stream_chat_with_usage(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        **_: Any,
    ) -> AsyncIterator[DeepSeekStreamEvent]:
        self.stream_calls.append({"messages": messages, "model": model})
        split_index = max(1, len(self.final_text) // 2)
        yield DeepSeekStreamEvent(text=self.final_text[:split_index])
        yield DeepSeekStreamEvent(text=self.final_text[split_index:])


class FakeToolProposalClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.stream_calls: list[dict[str, Any]] = []

    async def request_chat_with_usage(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        stream: bool = False,
        **_: Any,
    ) -> DeepSeekChatResult:
        del model, tools, stream
        self.calls.append(
            {
                "messages": messages,
                "thinking": _.get("thinking"),
                "reasoning_effort": _.get("reasoning_effort"),
                "tool_choice": tool_choice,
            }
        )
        if len(self.calls) == 1:
            return DeepSeekChatResult(
                content="",
                tool_calls=[
                    {
                        "id": "call_propose",
                        "type": "function",
                        "function": {
                            "name": "propose_plan_change",
                            "arguments": json.dumps(
                                {
                                    "day": "Monday",
                                    "summary": "把深蹲 RPE 下调，降低疲劳风险。",
                                    "changes": [
                                        {
                                            "action": "update",
                                            "exerciseName": "深蹲",
                                            "field": "rpe",
                                            "newValue": 7,
                                        }
                                    ],
                                },
                                ensure_ascii=False,
                            ),
                        },
                    }
                ],
            )
        return DeepSeekChatResult(content="已生成一张需要你确认的训练计划调整卡。")

    async def stream_chat_with_usage(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        **_: Any,
    ) -> AsyncIterator[DeepSeekStreamEvent]:
        self.stream_calls.append({"messages": messages, "model": model})
        yield DeepSeekStreamEvent(text="已生成一张需要你确认的")
        yield DeepSeekStreamEvent(text="训练计划调整卡。")


class FakeMisleadingToolProposalClient(FakeToolProposalClient):
    async def request_chat_with_usage(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> DeepSeekChatResult:
        result = await super().request_chat_with_usage(
            messages=messages,
            model=model,
            tools=tools,
            tool_choice=tool_choice,
            stream=stream,
            **kwargs,
        )
        if len(self.calls) >= 2:
            return DeepSeekChatResult(content="我已采纳并写入计划，今天就按这个调整执行。")
        return result

    async def stream_chat_with_usage(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        **_: Any,
    ) -> AsyncIterator[DeepSeekStreamEvent]:
        self.stream_calls.append({"messages": messages, "model": model})
        yield DeepSeekStreamEvent(text="已生成待确认的训练计划调整建议：把深蹲 RPE 下调，")
        yield DeepSeekStreamEvent(text="降低疲劳风险。当前仍未写回计划，请确认后再采纳。")


class FakeDayPlanProposalClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.stream_calls: list[dict[str, Any]] = []

    async def request_chat_with_usage(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        stream: bool = False,
        **_: Any,
    ) -> DeepSeekChatResult:
        del model, tools, stream
        self.calls.append(
            {
                "messages": messages,
                "thinking": _.get("thinking"),
                "reasoning_effort": _.get("reasoning_effort"),
                "tool_choice": tool_choice,
            }
        )
        if len(self.calls) == 1:
            return DeepSeekChatResult(
                content="",
                tool_calls=[
                    {
                        "id": "call_day_plan",
                        "type": "function",
                        "function": {
                            "name": "propose_day_plan_replace",
                            "arguments": json.dumps(
                                {
                                    "day": "Monday",
                                    "summary": "把周一改成恢复型腿日。",
                                    "dayPlan": {
                                        "type": "active_recovery",
                                        "exercises": [
                                            {
                                                "name": "深蹲",
                                                "tier": "main",
                                                "template": {
                                                    "loadMode": "percentage",
                                                    "ref1RM": "squat",
                                                    "setType": "straight",
                                                    "sets": 3,
                                                    "repsText": "5",
                                                },
                                                "instance": {
                                                    "pct": 0.7,
                                                    "kg": None,
                                                    "rpe": 7,
                                                    "note": "恢复周主项",
                                                },
                                                "ref1RM": "squat",
                                                "pct": 0.7,
                                                "kg": None,
                                                "sets": 3,
                                                "reps": 5,
                                                "rpe": 7,
                                                "note": "恢复周主项",
                                            }
                                        ],
                                    },
                                },
                                ensure_ascii=False,
                            ),
                        },
                    }
                ],
            )
        return DeepSeekChatResult(content="已生成一张单日训练计划卡。")

    async def stream_chat_with_usage(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        **_: Any,
    ) -> AsyncIterator[DeepSeekStreamEvent]:
        self.stream_calls.append({"messages": messages, "model": model})
        yield DeepSeekStreamEvent(text="已生成一张单日")
        yield DeepSeekStreamEvent(text="训练计划卡。")


class FakePlainAgentStreamClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.stream_calls: list[dict[str, Any]] = []

    async def request_chat_with_usage(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        stream: bool = False,
        **_: Any,
    ) -> DeepSeekChatResult:
        del model, stream
        self.calls.append(
            {
                "messages": messages,
                "tools": tools,
                "tool_choice": tool_choice,
            }
        )
        return DeepSeekChatResult(content="今天改成轻量恢复，主项减一组并控制 RPE。")

    async def stream_chat_with_usage(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        **_: Any,
    ) -> AsyncIterator[DeepSeekStreamEvent]:
        self.stream_calls.append({"messages": messages, "model": model})
        yield DeepSeekStreamEvent(text="今天改成轻量恢复，")
        yield DeepSeekStreamEvent(text="主项减一组并控制 RPE。")


class FakeInterruptingAgentProposalClient(FakeToolProposalClient):
    async def stream_chat_with_usage(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        **_: Any,
    ) -> AsyncIterator[DeepSeekStreamEvent]:
        self.stream_calls.append({"messages": messages, "model": model})
        yield DeepSeekStreamEvent(text="已经发给前端的半截 proposal 正文")
        raise DeepSeekClientError(
            "DeepSeek 流式响应在完成前中断，请稍后重试。",
            code="stream_interrupted",
        )


class FakeSequentialProposalClient:
    """按回合返回不同 proposal，便于复现同会话连续修改计划。"""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def request_chat_with_usage(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> DeepSeekChatResult:
        del tools, stream, kwargs
        self.calls.append({"messages": messages, "model": model, "tool_choice": tool_choice})

        tool_round_index = sum(1 for call in self.calls if call["tool_choice"] is not None)
        if tool_round_index == 1:
            return DeepSeekChatResult(
                content="",
                tool_calls=[
                    {
                        "id": "call_propose_round_1",
                        "type": "function",
                        "function": {
                            "name": "propose_plan_change",
                            "arguments": json.dumps(
                                {
                                    "day": "Monday",
                                    "summary": "把深蹲 RPE 下调到 7，降低疲劳风险。",
                                    "changes": [
                                        {
                                            "action": "update",
                                            "exerciseName": "深蹲",
                                            "field": "rpe",
                                            "newValue": 7,
                                        }
                                    ],
                                },
                                ensure_ascii=False,
                            ),
                        },
                    }
                ],
            )
        if tool_round_index == 2:
            return DeepSeekChatResult(content="已生成第一张待确认计划卡。")
        if tool_round_index == 3:
            return DeepSeekChatResult(
                content="",
                tool_calls=[
                    {
                        "id": "call_propose_round_2",
                        "type": "function",
                        "function": {
                            "name": "propose_plan_change",
                            "arguments": json.dumps(
                                {
                                    "day": "Monday",
                                    "summary": "把深蹲组数降到 2 组，继续控制疲劳。",
                                    "changes": [
                                        {
                                            "action": "update",
                                            "exerciseName": "深蹲",
                                            "field": "sets",
                                            "newValue": 2,
                                        }
                                    ],
                                },
                                ensure_ascii=False,
                            ),
                        },
                    }
                ],
            )
        return DeepSeekChatResult(content=f"{model} 已生成第二张待确认计划卡。")


class FakeTextOnlyPlanCardClient:
    """模拟模型没有调用工具，只输出 markdown 计划卡文本。"""

    async def request_chat_with_usage(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        stream: bool = False,
        **_: Any,
    ) -> DeepSeekChatResult:
        del messages, model, tools, tool_choice, stream
        return DeepSeekChatResult(
            content=(
                "---\n\n"
                "### 修改建议卡（待你确认）\n\n"
                "| 动作 | 当前 | -> 修改后 |\n"
                "|:----|:----:|:--------:|\n"
                "| 平板支撑 | 3x45秒 | 2x45秒 |\n\n"
                "如果没问题，跟我说“写入”即可生效。"
            )
        )


class FakeRepairableTextOnlyPlanCardClient:
    """模拟模型首轮只输出文字版卡片，补充约束后才真正调用 proposal 工具。"""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def request_chat_with_usage(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        stream: bool = False,
        **_: Any,
    ) -> DeepSeekChatResult:
        del model, tools, stream
        self.calls.append(
            {
                "messages": messages,
                "tool_choice": tool_choice,
            }
        )

        if len(self.calls) == 1:
            return DeepSeekChatResult(
                content=(
                    "下面先给你一版文字计划卡：\n"
                    "- 坡度走 30 分钟\n"
                    "- 平板支撑 3 组\n"
                    "- 死虫式 3 组"
                )
            )

        if any(
            isinstance(message, dict)
            and str(message.get("role")) == "system"
            and "必须通过 proposal 工具" in str(message.get("content") or "")
            for message in messages
        ):
            return DeepSeekChatResult(
                content="已按要求生成结构化计划修改卡。",
                tool_calls=[
                    {
                        "id": "call_retry_plan_card",
                        "type": "function",
                        "function": {
                            "name": "propose_day_plan_replace",
                            "arguments": json.dumps(
                                {
                                    "day": "Monday",
                                    "summary": "把周一改成更适合减脂恢复期的有氧+核心轻量方案。",
                                    "dayPlan": {
                                        "type": "active_recovery",
                                        "exercises": [
                                            {
                                                "name": "坡度快走",
                                                "sets": 1,
                                                "repsText": "30分钟",
                                                "note": "保持低心率有氧，不压恢复。",
                                            },
                                            {
                                                "name": "平板支撑",
                                                "sets": 2,
                                                "repsText": "30秒",
                                                "note": "只保留轻量核心激活。",
                                            },
                                        ],
                                    },
                                },
                                ensure_ascii=False,
                            ),
                        },
                    }
                ],
            )

        return DeepSeekChatResult(content="已按要求生成结构化计划修改卡。")


class FakeDeepSeekRepairableProposalClient:
    """模拟 DeepSeek 不接受 required，需要靠纠偏重试才愿意走 proposal 工具。"""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.provider_label = "DeepSeek 主账号"
        self.base_url = "https://api.deepseek.com/v1"

    async def request_chat_with_usage(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        stream: bool = False,
        **_: Any,
    ) -> DeepSeekChatResult:
        del model, tools, stream
        self.calls.append({"tool_choice": tool_choice, "messages": messages})
        has_retry_instruction = any(
            isinstance(message, dict)
            and str(message.get("role")) == "system"
            and "必须通过 proposal 工具" in str(message.get("content") or "")
            for message in messages
        )
        if not has_retry_instruction:
            return DeepSeekChatResult(
                content="我建议把周一整体再轻一点，先生成一张待确认卡再说。"
            )
        return DeepSeekChatResult(
            content="",
            tool_calls=[
                {
                    "id": "call_propose_required",
                    "type": "function",
                    "function": {
                        "name": "propose_plan_change",
                        "arguments": json.dumps(
                            {
                                "day": "Monday",
                                "summary": "把深蹲组数降到 2 组，继续控制疲劳。",
                                "changes": [
                                    {
                                        "action": "update",
                                        "exerciseName": "深蹲",
                                        "field": "sets",
                                        "newValue": 2,
                                    }
                                ],
                            },
                            ensure_ascii=False,
                        ),
                    },
                }
            ],
        )


class FakeGeminiTextOnlyUnlessRequiredProposalClient(GeminiNativeClient):
    """模拟 Gemini 在 AUTO 下只回正文，但在 required 下会正确走 proposal 工具。"""

    def __init__(self) -> None:
        super().__init__(
            api_key="AIza-test",
            base_url="https://generativelanguage.googleapis.com/v1beta",
        )
        self.calls: list[dict[str, Any]] = []

    async def generate_content_raw(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        thinking: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | dict[str, Any] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        reasoning_effort: str | None = None,
    ) -> dict[str, Any]:
        del messages, thinking, tools, reasoning_effort
        self.calls.append({"model": model, "tool_choice": tool_choice})

        if len(self.calls) == 1 and tool_choice != "required":
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": (
                                        "我建议把周一训练量再降一点，先生成一张待确认卡片再决定是否写回。"
                                    )
                                }
                            ]
                        }
                    }
                ]
            }

        if len(self.calls) == 1:
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "functionCall": {
                                        "id": "gemini-call-propose-round-2",
                                        "name": "propose_plan_change",
                                        "args": {
                                            "day": "Monday",
                                            "summary": "把深蹲组数降到 2 组，继续控制疲劳。",
                                            "changes": [
                                                {
                                                    "action": "update",
                                                    "exerciseName": "深蹲",
                                                    "field": "sets",
                                                    "newValue": 2,
                                                }
                                            ],
                                        },
                                    }
                                }
                            ]
                        }
                    }
                ]
            }

        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": "Gemini 已生成第二张待确认计划卡。"
                            }
                        ]
                    }
                }
            ]
        }


@pytest_asyncio.fixture
async def api_client(tmp_path: Path) -> AsyncIterator[AsyncClient]:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'chat-stream.db'}"
    engine, session_factory = create_engine_and_session_factory(database_url)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_get_db_session() -> AsyncIterator:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        setattr(client, "_session_factory", session_factory)
        yield client

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest_asyncio.fixture
async def uploaded_file(api_client: AsyncClient) -> dict[str, Any]:
    session_factory = getattr(api_client, "_session_factory")
    async with session_factory() as session:
        uploaded = UploadedFile(
            original_name="减脂容量型计划.xlsx",
            stored_name="test-message-attachment.xlsx",
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            extension=".xlsx",
            size_bytes=10321,
            sha256="a" * 64,
            storage_path="test-message-attachment.xlsx",
            summary={"summary": "容量型减脂计划摘要"},
            parser_status="parsed",
            parser_error=None,
            created_at=utc_now(),
        )
        session.add(uploaded)
        await session.commit()
        await session.refresh(uploaded)
        return {
            "fileId": uploaded.id,
            "originalName": uploaded.original_name,
            "mimeType": uploaded.mime_type,
            "extension": uploaded.extension,
            "sizeBytes": uploaded.size_bytes,
        }


def parse_sse_events(raw_text: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []

    for block in raw_text.strip().split("\n\n"):
        event_name = ""
        data = ""

        for line in block.splitlines():
            if line.startswith("event:"):
                event_name = line.removeprefix("event:").strip()
            if line.startswith("data:"):
                data = line.removeprefix("data:").strip()

        if event_name:
            events.append({"event": event_name, "data": json.loads(data)})

    return events


def build_messages(user_content: str = "今天深蹲很累，周五硬拉要改吗？") -> list[dict[str, str]]:
    return [
        {"role": "system", "content": "SYSTEM_PROMPT"},
        {"role": "assistant", "content": "先观察疲劳。"},
        {"role": "user", "content": user_content},
    ]


def build_weekly_plan() -> dict[str, Any]:
    rest_day = {"type": "rest", "exercises": []}
    return {
        "Monday": {
            "type": "strength",
            "exercises": [
                {
                    "id": "sq",
                    "name": "深蹲",
                    "sets": 4,
                    "reps": 5,
                    "rpe": 9,
                }
            ],
        },
        "Tuesday": dict(rest_day),
        "Wednesday": dict(rest_day),
        "Thursday": dict(rest_day),
        "Friday": dict(rest_day),
        "Saturday": dict(rest_day),
        "Sunday": dict(rest_day),
    }


@pytest.mark.asyncio
async def test_chat_stream_emits_delta_suggestion_done_and_persists_clean_messages(
    api_client: AsyncClient,
):
    fake_client = FakeDeepSeekClient(
        [
            "建议周五硬拉降一点，先保住动作质量。\n",
            '---JSON---\n{"suggest_plan_update":true,"day":"Friday","summary":"降低硬拉强度"}',
        ]
    )
    app.dependency_overrides[chat_api.get_deepseek_client] = lambda: fake_client
    default_session = (await api_client.get("/api/chat/sessions/default")).json()

    response = await api_client.post(
        "/api/chat/stream",
        json={
            "sessionId": default_session["id"],
            "messages": build_messages(),
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = parse_sse_events(response.text)

    assert [event["event"] for event in events] == [
        "delta",
        "delta",
        "suggestion",
        "done",
    ]
    assert events[0]["data"] == {"text": "建议周五硬拉降一点，先保住动作质量。\n"}
    assert events[1]["data"] == {
        "text": '---JSON---\n{"suggest_plan_update":true,"day":"Friday","summary":"降低硬拉强度"}'
    }
    assert events[2]["data"] == {
        "suggestion": {
            "suggest_plan_update": True,
            "day": "Friday",
            "summary": "降低硬拉强度",
        }
    }
    assert events[3]["data"] == {"text": "建议周五硬拉降一点，先保住动作质量。"}

    messages_response = await api_client.get(
        f"/api/chat/sessions/{default_session['id']}/messages"
    )
    stored_messages = messages_response.json()

    assert [(message["role"], message["content"]) for message in stored_messages] == [
        ("user", "今天深蹲很累，周五硬拉要改吗？"),
        ("assistant", "建议周五硬拉降一点，先保住动作质量。"),
    ]
    assert stored_messages[1]["suggestion"] == events[2]["data"]["suggestion"]


@pytest.mark.asyncio
async def test_chat_stream_emits_null_suggestion_for_plain_text_reply(
    api_client: AsyncClient,
):
    fake_client = FakeDeepSeekClient(["只建议今天降低一点容量。"])
    app.dependency_overrides[chat_api.get_deepseek_client] = lambda: fake_client
    default_session = (await api_client.get("/api/chat/sessions/default")).json()

    response = await api_client.post(
        "/api/chat/stream",
        json={
            "sessionId": default_session["id"],
            "messages": build_messages(),
        },
    )

    assert response.status_code == 200
    events = parse_sse_events(response.text)

    assert [event["event"] for event in events] == ["delta", "suggestion", "done"]
    assert events[1]["data"] == {"suggestion": None}
    assert events[2]["data"] == {"text": "只建议今天降低一点容量。"}


@pytest.mark.asyncio
async def test_agent_stream_executes_tool_loop_and_emits_plan_proposal(
    api_client: AsyncClient,
):
    fake_client = FakeToolProposalClient()
    app.dependency_overrides[chat_api.get_deepseek_client] = lambda: fake_client
    default_session = (await api_client.get("/api/chat/sessions/default")).json()
    assert (await api_client.put("/api/weekly-plan", json=build_weekly_plan())).status_code == 200

    response = await api_client.post(
        "/api/chat/stream",
        json={
            "sessionId": default_session["id"],
            "userInput": "请读取我的计划，并给出需要我确认的深蹲调整卡。",
            "thinking": {"enabled": True, "budget": "max"},
        },
    )

    assert response.status_code == 200
    events = parse_sse_events(response.text)

    assert [event["event"] for event in events] == [
        "delta",
        "delta",
        "proposal",
        "suggestion",
        "done",
    ]
    assert events[0]["data"] == {"text": "已生成一张需要你确认的"}
    assert events[1]["data"] == {"text": "训练计划调整卡。"}
    assert events[2]["data"]["proposal"]["day"] == "Monday"
    assert events[2]["data"]["proposal"]["summary"] == "把深蹲 RPE 下调，降低疲劳风险。"
    assert events[2]["data"]["proposal"]["changes"][0]["newValue"] == 7
    assert events[2]["data"]["proposal"]["proposalId"]
    assert events[3]["data"] == {"suggestion": None}
    assert events[4]["data"] == {"text": "已生成一张需要你确认的训练计划调整卡。"}
    assert events[4]["data"]["text"] == events[0]["data"]["text"] + events[1]["data"]["text"]
    assert len(fake_client.calls) == 1
    assert len(fake_client.stream_calls) == 1
    assert fake_client.calls[0]["thinking"] == {"type": "enabled"}
    assert fake_client.calls[0]["reasoning_effort"] == "max"
    assert fake_client.calls[0]["tool_choice"] is None

    messages_response = await api_client.get(
        f"/api/chat/sessions/{default_session['id']}/messages"
    )
    stored_messages = messages_response.json()
    assert [(message["role"], message["content"]) for message in stored_messages] == [
        ("user", "请读取我的计划，并给出需要我确认的深蹲调整卡。"),
        ("assistant", events[4]["data"]["text"]),
    ]
    assert stored_messages[1]["suggestion"] == events[2]["data"]["proposal"]


@pytest.mark.asyncio
async def test_chat_reply_closes_pending_proposal_copy_before_persisting(
    api_client: AsyncClient,
):
    fake_client = FakeMisleadingToolProposalClient()
    app.dependency_overrides[chat_api.get_deepseek_client] = lambda: fake_client
    default_session = (await api_client.get("/api/chat/sessions/default")).json()
    assert (await api_client.put("/api/weekly-plan", json=build_weekly_plan())).status_code == 200

    response = await api_client.post(
        "/api/chat/reply",
        json={
            "sessionId": default_session["id"],
            "userInput": "请直接给我一张深蹲降强度 proposal 卡。",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["proposal"]["status"] == "pending"
    assert "待确认" in payload["text"]
    assert "未写回" in payload["text"]
    assert "已采纳" not in payload["text"]
    assert "已写入计划" not in payload["text"]
    assert "已更新计划" not in payload["text"]

    messages_response = await api_client.get(
        f"/api/chat/sessions/{default_session['id']}/messages"
    )
    stored_messages = messages_response.json()

    assert stored_messages[-1]["role"] == "assistant"
    assert stored_messages[-1]["content"] == payload["text"]
    assert stored_messages[-1]["suggestion"] == payload["proposal"]


@pytest.mark.asyncio
async def test_agent_stream_closes_pending_proposal_copy_before_done_and_persisting(
    api_client: AsyncClient,
):
    fake_client = FakeMisleadingToolProposalClient()
    app.dependency_overrides[chat_api.get_deepseek_client] = lambda: fake_client
    default_session = (await api_client.get("/api/chat/sessions/default")).json()
    assert (await api_client.put("/api/weekly-plan", json=build_weekly_plan())).status_code == 200

    response = await api_client.post(
        "/api/chat/stream",
        json={
            "sessionId": default_session["id"],
            "userInput": "请读取我的计划，并给出需要我确认的深蹲调整卡。",
        },
    )

    assert response.status_code == 200
    events = parse_sse_events(response.text)

    assert [event["event"] for event in events] == [
        "delta",
        "delta",
        "proposal",
        "suggestion",
        "done",
    ]
    assert events[2]["data"]["proposal"]["status"] == "pending"
    assert "待确认" in events[0]["data"]["text"]
    assert "未写回" in (events[0]["data"]["text"] + events[1]["data"]["text"])
    assert "已采纳" not in events[0]["data"]["text"]
    assert "已写入计划" not in events[0]["data"]["text"]
    assert "已更新计划" not in events[0]["data"]["text"]
    full_text = events[0]["data"]["text"] + events[1]["data"]["text"]
    assert events[4]["data"] == {"text": full_text}

    messages_response = await api_client.get(
        f"/api/chat/sessions/{default_session['id']}/messages"
    )
    stored_messages = messages_response.json()

    assert stored_messages[-1]["role"] == "assistant"
    assert stored_messages[-1]["content"] == full_text
    assert stored_messages[-1]["suggestion"] == events[2]["data"]["proposal"]


@pytest.mark.asyncio
async def test_agent_stream_emits_day_plan_replace_proposal(
    api_client: AsyncClient,
):
    fake_client = FakeDayPlanProposalClient()
    app.dependency_overrides[chat_api.get_deepseek_client] = lambda: fake_client
    default_session = (await api_client.get("/api/chat/sessions/default")).json()
    assert (await api_client.put("/api/weekly-plan", json=build_weekly_plan())).status_code == 200

    response = await api_client.post(
        "/api/chat/stream",
        json={
            "sessionId": default_session["id"],
            "userInput": "请给我一张周一恢复型腿日卡片。",
        },
    )

    assert response.status_code == 200
    events = parse_sse_events(response.text)

    assert [event["event"] for event in events] == [
        "delta",
        "delta",
        "proposal",
        "suggestion",
        "done",
    ]
    assert events[2]["data"]["proposal"]["kind"] == "day_plan_replace"
    assert events[2]["data"]["proposal"]["dayPlan"]["type"] == "active_recovery"
    assert events[2]["data"]["proposal"]["dayPlan"]["exercises"][0]["name"] == "深蹲"


@pytest.mark.asyncio
async def test_agent_stream_emits_plain_text_without_proposal_when_tool_loop_returns_no_plan_card(
    api_client: AsyncClient,
):
    fake_client = FakePlainAgentStreamClient()
    app.dependency_overrides[chat_api.get_deepseek_client] = lambda: fake_client
    default_session = (await api_client.get("/api/chat/sessions/default")).json()
    assert (await api_client.put("/api/weekly-plan", json=build_weekly_plan())).status_code == 200

    response = await api_client.post(
        "/api/chat/stream",
        json={
            "sessionId": default_session["id"],
            "userInput": "请根据我的疲劳情况直接给一个普通建议，不需要计划卡。",
        },
    )

    assert response.status_code == 200
    events = parse_sse_events(response.text)

    assert [event["event"] for event in events] == ["delta", "delta", "suggestion", "done"]
    assert events[0]["data"] == {"text": "今天改成轻量恢复，"}
    assert events[1]["data"] == {"text": "主项减一组并控制 RPE。"}
    assert events[2]["data"] == {"suggestion": None}
    assert events[3]["data"] == {"text": "今天改成轻量恢复，主项减一组并控制 RPE。"}
    assert events[3]["data"]["text"] == events[0]["data"]["text"] + events[1]["data"]["text"]
    assert len(fake_client.calls) == 1
    assert len(fake_client.stream_calls) == 1

    messages_response = await api_client.get(
        f"/api/chat/sessions/{default_session['id']}/messages"
    )
    stored_messages = messages_response.json()
    assert [(message["role"], message["content"]) for message in stored_messages] == [
        ("user", "请根据我的疲劳情况直接给一个普通建议，不需要计划卡。"),
        ("assistant", events[3]["data"]["text"]),
    ]
    assert stored_messages[1]["suggestion"] is None


@pytest.mark.asyncio
async def test_chat_reply_allows_second_plan_proposal_after_first_proposal_commit_in_same_session(
    api_client: AsyncClient,
):
    fake_client = FakeSequentialProposalClient()
    app.dependency_overrides[chat_api.get_deepseek_client] = lambda: fake_client
    default_session = (await api_client.get("/api/chat/sessions/default")).json()
    assert (await api_client.put("/api/weekly-plan", json=build_weekly_plan())).status_code == 200

    first_reply = await api_client.post(
        "/api/chat/reply",
        json={
            "sessionId": default_session["id"],
            "userInput": "先给我一张周一深蹲降疲劳的计划卡。",
        },
    )
    assert first_reply.status_code == 200
    first_payload = first_reply.json()
    first_proposal = first_payload["proposal"]
    assert first_proposal["status"] == "pending"

    commit_response = await api_client.post(
        "/api/tools/plan/commit",
        json={"proposalId": first_proposal["proposalId"]},
    )
    assert commit_response.status_code == 200

    second_reply = await api_client.post(
        "/api/chat/reply",
        json={
            "sessionId": default_session["id"],
            "userInput": "继续调整周一，把深蹲组数也降一点，再给我一张计划卡。",
        },
    )
    assert second_reply.status_code == 200
    second_payload = second_reply.json()

    assert second_payload["proposal"] is not None
    assert second_payload["proposal"]["status"] == "pending"
    assert second_payload["proposal"]["proposalId"] != first_proposal["proposalId"]
    assert second_payload["proposal"]["changes"][0]["field"] == "sets"
    assert second_payload["proposal"]["changes"][0]["newValue"] == 2
    assert "待确认" in second_payload["text"]


@pytest.mark.asyncio
async def test_chat_reply_returns_to_normal_chat_after_proposal_commit_until_user_explicitly_reinvokes_plan_card(
    api_client: AsyncClient,
):
    fake_client = FakeSequentialProposalClient()
    app.dependency_overrides[chat_api.get_deepseek_client] = lambda: fake_client
    default_session = (await api_client.get("/api/chat/sessions/default")).json()
    assert (await api_client.put("/api/weekly-plan", json=build_weekly_plan())).status_code == 200

    first_reply = await api_client.post(
        "/api/chat/reply",
        json={
            "sessionId": default_session["id"],
            "userInput": "先给我一张周一深蹲降疲劳的计划卡。",
        },
    )
    assert first_reply.status_code == 200
    first_proposal = first_reply.json()["proposal"]

    commit_response = await api_client.post(
        "/api/tools/plan/commit",
        json={"proposalId": first_proposal["proposalId"]},
    )
    assert commit_response.status_code == 200

    normal_chat_response = await api_client.post(
        "/api/chat/reply",
        json={
            "sessionId": default_session["id"],
            "userInput": "解释一下你刚才这样调整的原因。",
        },
    )

    assert normal_chat_response.status_code == 200
    normal_payload = normal_chat_response.json()
    assert normal_payload["proposal"] is None
    assert normal_payload["suggestion"] is None


@pytest.mark.asyncio
async def test_chat_reply_same_session_can_switch_model_and_still_generate_second_plan_proposal(
    api_client: AsyncClient,
    monkeypatch,
):
    default_session = (await api_client.get("/api/chat/sessions/default")).json()
    assert (await api_client.put("/api/weekly-plan", json=build_weekly_plan())).status_code == 200

    class FakeRuntime:
        default_model_ref = "provider_deepseek_main::deepseek-v4-flash"

        def resolve_model_ref(self, model_ref: str):
            provider_map = {
                "provider_deepseek_main::deepseek-v4-flash": type(
                    "Provider",
                    (),
                    {
                        "type": "openai_compatible",
                        "api_key": "sk-provider",
                        "base_url": "https://api.deepseek.com/v1",
                        "wire_api": "chat_completions",
                        "api_path_mode": "append_v1",
                        "label": "DeepSeek 主账号",
                    },
                )(),
                "provider_gemini_main::gemini-2.5-flash": type(
                    "Provider",
                    (),
                    {
                        "type": "gemini_native",
                        "api_key": "sk-gemini",
                        "base_url": "https://generativelanguage.googleapis.com/v1beta",
                        "label": "Gemini 主账号",
                    },
                )(),
            }
            return provider_map[model_ref], model_ref.split("::", 1)[1]

    observed_models: list[str] = []
    shared_client = FakeSequentialProposalClient()

    def build_runtime_client(provider, fallback_client, timeout=None):
        del provider, fallback_client, timeout
        original_request = shared_client.request_chat_with_usage

        async def wrapped_request_chat_with_usage(**kwargs: Any):
            observed_models.append(kwargs["model"])
            return await original_request(**kwargs)

        shared_client.request_chat_with_usage = wrapped_request_chat_with_usage  # type: ignore[method-assign]
        return shared_client

    monkeypatch.setattr(chat_api, "get_provider_runtime", lambda: FakeRuntime())
    monkeypatch.setattr(chat_api, "build_provider_bound_client", build_runtime_client)

    first_reply = await api_client.post(
        "/api/chat/reply",
        json={
            "sessionId": default_session["id"],
            "userInput": "先给我一张周一深蹲降疲劳的计划卡。",
            "model": "provider_deepseek_main::deepseek-v4-flash",
        },
    )
    assert first_reply.status_code == 200
    first_payload = first_reply.json()
    first_proposal = first_payload["proposal"]
    assert first_proposal["status"] == "pending"

    commit_response = await api_client.post(
        "/api/tools/plan/commit",
        json={"proposalId": first_proposal["proposalId"]},
    )
    assert commit_response.status_code == 200

    second_reply = await api_client.post(
        "/api/chat/reply",
        json={
            "sessionId": default_session["id"],
            "userInput": "继续调整周一，把深蹲组数也降一点，再给我一张计划卡。",
            "model": "provider_gemini_main::gemini-2.5-flash",
        },
    )
    assert second_reply.status_code == 200
    second_payload = second_reply.json()

    assert second_payload["proposal"] is not None
    assert second_payload["proposal"]["status"] == "pending"
    assert second_payload["proposal"]["changes"][0]["field"] == "sets"
    assert second_payload["proposal"]["changes"][0]["newValue"] == 2
    assert observed_models[0] == "deepseek-v4-flash"


@pytest.mark.asyncio
async def test_chat_reply_switching_to_gemini_requires_structured_proposal_tool_call(
    api_client: AsyncClient,
    monkeypatch,
):
    default_session = (await api_client.get("/api/chat/sessions/default")).json()
    assert (await api_client.put("/api/weekly-plan", json=build_weekly_plan())).status_code == 200

    class FakeRuntime:
        default_model_ref = "provider_deepseek_main::deepseek-v4-flash"

        def resolve_model_ref(self, model_ref: str):
            provider_map = {
                "provider_deepseek_main::deepseek-v4-flash": type(
                    "Provider",
                    (),
                    {
                        "type": "openai_compatible",
                        "api_key": "sk-provider",
                        "base_url": "https://api.deepseek.com/v1",
                        "wire_api": "chat_completions",
                        "api_path_mode": "append_v1",
                        "label": "DeepSeek 主账号",
                    },
                )(),
                "provider_gemini_main::gemini-2.5-flash": type(
                    "Provider",
                    (),
                    {
                        "type": "gemini_native",
                        "api_key": "sk-gemini",
                        "base_url": "https://generativelanguage.googleapis.com/v1beta",
                        "label": "Gemini 主账号",
                    },
                )(),
            }
            return provider_map[model_ref], model_ref.split("::", 1)[1]

    deepseek_client = FakeSequentialProposalClient()
    gemini_client = FakeGeminiTextOnlyUnlessRequiredProposalClient()

    def build_runtime_client(provider, fallback_client, timeout=None):
        del fallback_client, timeout
        if provider.type == "gemini_native":
            return gemini_client
        return deepseek_client

    monkeypatch.setattr(chat_api, "get_provider_runtime", lambda: FakeRuntime())
    monkeypatch.setattr(chat_api, "build_provider_bound_client", build_runtime_client)

    first_reply = await api_client.post(
        "/api/chat/reply",
        json={
            "sessionId": default_session["id"],
            "userInput": "先给我一张周一深蹲降疲劳的计划卡。",
            "model": "provider_deepseek_main::deepseek-v4-flash",
        },
    )
    assert first_reply.status_code == 200
    first_proposal = first_reply.json()["proposal"]

    commit_response = await api_client.post(
        "/api/tools/plan/commit",
        json={"proposalId": first_proposal["proposalId"]},
    )
    assert commit_response.status_code == 200

    second_reply = await api_client.post(
        "/api/chat/reply",
        json={
            "sessionId": default_session["id"],
            "userInput": "继续调整周一，把深蹲组数也降一点，然后生成计划修改卡。",
            "model": "provider_gemini_main::gemini-2.5-flash",
            "thinking": {"enabled": True, "budget": "max"},
        },
    )

    assert second_reply.status_code == 200
    second_payload = second_reply.json()
    assert second_payload["proposal"] is not None
    assert second_payload["proposal"]["status"] == "pending"
    assert second_payload["proposal"]["changes"][0]["field"] == "sets"
    assert second_payload["proposal"]["changes"][0]["newValue"] == 2
    assert gemini_client.calls[0]["tool_choice"] == "required"


@pytest.mark.asyncio
async def test_chat_reply_requires_structured_proposal_tool_call_for_openai_compatible_clients_too(
    api_client: AsyncClient,
    monkeypatch,
):
    default_session = (await api_client.get("/api/chat/sessions/default")).json()
    assert (await api_client.put("/api/weekly-plan", json=build_weekly_plan())).status_code == 200

    class FakeRuntime:
        default_model_ref = "provider_deepseek_main::deepseek-v4-flash"

        def resolve_model_ref(self, model_ref: str):
            provider = type(
                "Provider",
                (),
                {
                    "type": "openai_compatible",
                    "api_key": "sk-provider",
                    "base_url": "https://api.deepseek.com/v1",
                    "wire_api": "chat_completions",
                    "api_path_mode": "append_v1",
                    "label": "DeepSeek 主账号",
                },
            )()
            return provider, model_ref.split("::", 1)[1]

    first_client = FakeSequentialProposalClient()
    second_client = FakeDeepSeekRepairableProposalClient()
    build_count = {"value": 0}

    def build_runtime_client(provider, fallback_client, timeout=None):
        del provider, fallback_client, timeout
        build_count["value"] += 1
        if build_count["value"] == 1:
            return first_client
        return second_client

    monkeypatch.setattr(chat_api, "get_provider_runtime", lambda: FakeRuntime())
    monkeypatch.setattr(chat_api, "build_provider_bound_client", build_runtime_client)

    first_reply = await api_client.post(
        "/api/chat/reply",
        json={
            "sessionId": default_session["id"],
            "userInput": "先给我一张周一深蹲降疲劳的计划卡。",
            "model": "provider_deepseek_main::deepseek-v4-flash",
        },
    )
    assert first_reply.status_code == 200
    first_proposal = first_reply.json()["proposal"]

    commit_response = await api_client.post(
        "/api/tools/plan/commit",
        json={"proposalId": first_proposal["proposalId"]},
    )
    assert commit_response.status_code == 200

    second_reply = await api_client.post(
        "/api/chat/reply",
        json={
            "sessionId": default_session["id"],
            "userInput": "继续调整周一，把深蹲组数也降一点，然后生成计划修改卡。",
            "model": "provider_deepseek_main::deepseek-v4-flash",
        },
    )

    assert second_reply.status_code == 200
    second_payload = second_reply.json()
    assert second_payload["proposal"] is not None
    assert second_payload["proposal"]["status"] == "pending"
    assert second_payload["proposal"]["changes"][0]["field"] == "sets"
    assert second_payload["proposal"]["changes"][0]["newValue"] == 2
    assert second_client.calls[0]["tool_choice"] is None
    assert any(
        any(
            isinstance(message, dict)
            and str(message.get("role")) == "system"
            and "必须通过 proposal 工具" in str(message.get("content") or "")
            for message in call["messages"]
        )
        for call in second_client.calls[1:]
    )


@pytest.mark.asyncio
async def test_chat_reply_deepseek_thinking_does_not_send_required_tool_choice(
    api_client: AsyncClient,
    monkeypatch,
):
    from backend.agent.tool_choice import resolve_tool_choice_for_request

    provider_client = OpenAICompatibleRuntimeClient(
        api_key="sk-provider",
        base_url="https://api.deepseek.com/v1",
        wire_api="chat_completions",
        api_path_mode="append_v1",
        provider_label="DeepSeek 主账号",
    )

    tool_choice = resolve_tool_choice_for_request(
        user_content="继续调整周一，把深蹲组数也降一点，然后生成计划修改卡。",
        provider_client=provider_client,
        thinking={"type": "enabled"},
    )

    assert tool_choice is None


@pytest.mark.asyncio
async def test_chat_reply_standard_openai_compatible_thinking_keeps_required_tool_choice(
    api_client: AsyncClient,
    monkeypatch,
):
    del api_client, monkeypatch
    from backend.agent.tool_choice import resolve_tool_choice_for_request

    provider_client = OpenAICompatibleRuntimeClient(
        api_key="sk-provider",
        base_url="https://api.openai.com/v1",
        wire_api="chat_completions",
        api_path_mode="append_v1",
        provider_label="OpenAI 主账号",
    )

    tool_choice = resolve_tool_choice_for_request(
        user_content="继续调整周一，把深蹲组数也降一点，然后生成计划修改卡。",
        provider_client=provider_client,
        thinking={"type": "enabled"},
    )

    assert tool_choice == "required"


@pytest.mark.asyncio
async def test_chat_reply_rejects_text_only_plan_card_when_user_explicitly_requests_pending_proposal(
    api_client: AsyncClient,
):
    app.dependency_overrides[chat_api.get_deepseek_client] = lambda: FakeTextOnlyPlanCardClient()
    default_session = (await api_client.get("/api/chat/sessions/default")).json()

    response = await api_client.post(
        "/api/chat/reply",
        json={
            "sessionId": default_session["id"],
            "userInput": "为周一休息日设计一份有氧+核心运动计划，然后生成计划修改卡。",
        },
    )

    assert response.status_code == 503
    assert "计划卡" in response.json()["detail"]
    assert "tool" in response.json()["detail"].lower() or "工具" in response.json()["detail"]


@pytest.mark.asyncio
async def test_chat_stream_rejects_text_only_plan_card_when_user_explicitly_requests_pending_proposal(
    api_client: AsyncClient,
):
    app.dependency_overrides[chat_api.get_deepseek_client] = lambda: FakeTextOnlyPlanCardClient()
    default_session = (await api_client.get("/api/chat/sessions/default")).json()

    response = await api_client.post(
        "/api/chat/stream",
        json={
            "sessionId": default_session["id"],
            "userInput": "为周一休息日设计一份有氧+核心运动计划，然后生成计划修改卡。",
        },
    )

    assert response.status_code == 200
    events = parse_sse_events(response.text)
    assert [event["event"] for event in events] == ["error"]
    assert events[0]["data"]["code"] == "missing_plan_proposal"
    assert "计划卡" in events[0]["data"]["message"]
    assert "proposal" in events[0]["data"]["message"]

    messages_response = await api_client.get(
        f"/api/chat/sessions/{default_session['id']}/messages"
    )
    assert messages_response.json() == []


@pytest.mark.asyncio
async def test_chat_reply_retries_with_strict_prompt_when_model_returns_text_only_plan_card(
    api_client: AsyncClient,
):
    fake_client = FakeRepairableTextOnlyPlanCardClient()
    app.dependency_overrides[chat_api.get_deepseek_client] = lambda: fake_client
    default_session = (await api_client.get("/api/chat/sessions/default")).json()
    assert (await api_client.put("/api/weekly-plan", json=build_weekly_plan())).status_code == 200

    response = await api_client.post(
        "/api/chat/reply",
        json={
            "sessionId": default_session["id"],
            "userInput": "为周一休息日设计一份有氧+核心运动计划，然后生成计划修改卡。",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["proposal"] is not None
    assert payload["proposal"]["status"] == "pending"
    assert payload["proposal"]["kind"] == "day_plan_replace"
    assert len(fake_client.calls) >= 2
    assert fake_client.calls[0]["tool_choice"] == "required"
    assert any(
        any(
            isinstance(message, dict)
            and str(message.get("role")) == "system"
            and "必须通过 proposal 工具" in str(message.get("content") or "")
            for message in call["messages"]
        )
        for call in fake_client.calls[1:]
    )


@pytest.mark.asyncio
async def test_chat_stream_emits_error_and_does_not_persist_partial_assistant(
    api_client: AsyncClient,
):
    fake_client = FakeDeepSeekClient(
        ["半截回复"],
        error=DeepSeekClientError(
            "未配置后端 DeepSeek API Key，请在 backend/.env 中设置 DEEPSEEK_API_KEY。",
            code="missing_api_key",
        ),
    )
    app.dependency_overrides[chat_api.get_deepseek_client] = lambda: fake_client
    default_session = (await api_client.get("/api/chat/sessions/default")).json()

    response = await api_client.post(
        "/api/chat/stream",
        json={
            "sessionId": default_session["id"],
            "messages": build_messages(),
        },
    )

    assert response.status_code == 200
    events = parse_sse_events(response.text)

    assert [event["event"] for event in events] == ["error"]
    assert events[0]["data"]["code"] == "missing_api_key"
    assert "DeepSeek API Key" in events[0]["data"]["message"]

    messages_response = await api_client.get(
        f"/api/chat/sessions/{default_session['id']}/messages"
    )

    assert messages_response.json() == []


@pytest.mark.asyncio
async def test_chat_stream_rolls_back_when_upstream_breaks_after_delta(
    api_client: AsyncClient,
):
    fake_client = FakeDeepSeekClient(
        ["已经发给前端的半截回复"],
        error_after_chunks=DeepSeekClientError(
            "DeepSeek 流式响应在完成前中断，请稍后重试。",
            code="stream_interrupted",
        ),
    )
    app.dependency_overrides[chat_api.get_deepseek_client] = lambda: fake_client
    default_session = (await api_client.get("/api/chat/sessions/default")).json()

    response = await api_client.post(
        "/api/chat/stream",
        json={
            "sessionId": default_session["id"],
            "messages": build_messages(),
        },
    )

    assert response.status_code == 200
    events = parse_sse_events(response.text)

    assert [event["event"] for event in events] == ["delta", "error"]
    assert events[0]["data"] == {"text": "已经发给前端的半截回复"}
    assert events[1]["data"]["code"] == "stream_interrupted"

    messages_response = await api_client.get(
        f"/api/chat/sessions/{default_session['id']}/messages"
    )

    assert messages_response.json() == []


@pytest.mark.asyncio
async def test_agent_stream_rolls_back_when_final_answer_stream_breaks_after_delta(
    api_client: AsyncClient,
):
    fake_client = FakeInterruptingAgentProposalClient()
    app.dependency_overrides[chat_api.get_deepseek_client] = lambda: fake_client
    default_session = (await api_client.get("/api/chat/sessions/default")).json()
    assert (await api_client.put("/api/weekly-plan", json=build_weekly_plan())).status_code == 200

    response = await api_client.post(
        "/api/chat/stream",
        json={
            "sessionId": default_session["id"],
            "userInput": "请读取我的计划，并给出需要我确认的深蹲调整卡。",
        },
    )

    assert response.status_code == 200
    events = parse_sse_events(response.text)

    assert [event["event"] for event in events] == ["delta", "error"]
    assert events[0]["data"] == {"text": "已经发给前端的半截 proposal 正文"}
    assert events[1]["data"]["code"] == "stream_interrupted"

    messages_response = await api_client.get(
        f"/api/chat/sessions/{default_session['id']}/messages"
    )

    assert messages_response.json() == []

    session_factory = getattr(api_client, "_session_factory")
    async with session_factory() as session:
        logs = (await session.execute(select(ToolCallLog))).scalars().all()

    assert len(logs) == 1
    assert logs[0].tool_name == "propose_plan_change"


@pytest.mark.asyncio
async def test_chat_stream_persists_user_attachment_snapshot_and_empty_assistant_attachments(
    api_client: AsyncClient,
    uploaded_file: dict[str, Any],
):
    fake_client = FakeDeepSeekClient(["带附件的回复。"])
    app.dependency_overrides[chat_api.get_deepseek_client] = lambda: fake_client
    default_session = (await api_client.get("/api/chat/sessions/default")).json()

    response = await api_client.post(
        "/api/chat/stream",
        json={
            "sessionId": default_session["id"],
            "userInput": "请基于我上传的文件给建议。",
            "fileIds": [uploaded_file["fileId"]],
        },
    )

    assert response.status_code == 200
    events = parse_sse_events(response.text)
    assert [event["event"] for event in events] == ["delta", "suggestion", "done"]

    messages_response = await api_client.get(
        f"/api/chat/sessions/{default_session['id']}/messages"
    )
    stored_messages = messages_response.json()

    assert len(stored_messages) == 2
    assert stored_messages[0]["role"] == "user"
    assert stored_messages[0]["attachments"] == [uploaded_file]
    assert stored_messages[1]["role"] == "assistant"
    assert stored_messages[1]["attachments"] == []


@pytest.mark.asyncio
async def test_chat_reply_resolves_model_ref_before_requesting_provider_client(
    api_client: AsyncClient,
    monkeypatch,
) -> None:
    fake_client = FakeReplyModelClient("按解析后的远端模型回复。")
    app.dependency_overrides[chat_api.get_deepseek_client] = lambda: fake_client
    default_session = (await api_client.get("/api/chat/sessions/default")).json()
    resolved_model_refs: list[str] = []

    class FakeRuntime:
        default_model_ref = "provider_deepseek_main::deepseek-v4-flash"

        def resolve_model_ref(self, model_ref: str):
            resolved_model_refs.append(model_ref)
            return (
                type("Provider", (), {"type": "openai_compatible", "api_key": None, "base_url": ""})(),
                "deepseek-v4-flash",
            )

    monkeypatch.setattr(chat_api, "get_provider_runtime", lambda: FakeRuntime())

    response = await api_client.post(
        "/api/chat/reply",
        json={
            "sessionId": default_session["id"],
            "messages": build_messages("hello"),
            "model": "provider_deepseek_main::deepseek-v4-flash",
        },
    )

    assert response.status_code == 200
    assert resolved_model_refs == ["provider_deepseek_main::deepseek-v4-flash"]
    assert fake_client.calls[0]["model"] == "deepseek-v4-flash"


@pytest.mark.asyncio
async def test_chat_reply_uses_openai_compatible_responses_client_without_falling_back_to_deepseek(
    api_client: AsyncClient,
    monkeypatch,
) -> None:
    fake_client = FakeOpenAICompatibleResponsesClient(text_reply="按 responses wire 返回。")
    default_session = (await api_client.get("/api/chat/sessions/default")).json()

    class FakeRuntime:
        default_model_ref = "provider_openai_responses::gpt-4.1-mini"

        def resolve_model_ref(self, model_ref: str):
            assert model_ref == "provider_openai_responses::gpt-4.1-mini"
            return (
                type(
                    "Provider",
                    (),
                    {
                        "type": "openai_compatible",
                        "api_key": "sk-openai",
                        "base_url": "https://api.openai.com",
                        "wire_api": "responses",
                        "api_path_mode": "append_v1",
                    },
                )(),
                "gpt-4.1-mini",
            )

    monkeypatch.setattr(chat_api, "get_provider_runtime", lambda: FakeRuntime())
    monkeypatch.setattr(
        chat_api,
        "build_provider_bound_client",
        lambda provider, fallback_client, timeout=None: fake_client,
    )

    response = await api_client.post(
        "/api/chat/reply",
        json={
            "sessionId": default_session["id"],
            "messages": build_messages("走 responses wire"),
            "model": "provider_openai_responses::gpt-4.1-mini",
        },
    )

    assert response.status_code == 200
    assert response.json()["text"] == "按 responses wire 返回。"
    assert fake_client.response_calls[0]["model"] == "gpt-4.1-mini"


@pytest.mark.asyncio
async def test_chat_stream_uses_openai_compatible_chat_completions_stream_client(
    api_client: AsyncClient,
    monkeypatch,
) -> None:
    fake_client = FakeOpenAICompatibleChatCompletionsClient("不会走非流式。")
    default_session = (await api_client.get("/api/chat/sessions/default")).json()

    class FakeRuntime:
        default_model_ref = "provider_openai_chat::gpt-4.1-mini"

        def resolve_model_ref(self, model_ref: str):
            assert model_ref == "provider_openai_chat::gpt-4.1-mini"
            return (
                type(
                    "Provider",
                    (),
                    {
                        "type": "openai_compatible",
                        "api_key": "sk-openai",
                        "base_url": "https://api.openai.com",
                        "wire_api": "chat_completions",
                        "api_path_mode": "append_v1",
                    },
                )(),
                "gpt-4.1-mini",
            )

    monkeypatch.setattr(chat_api, "get_provider_runtime", lambda: FakeRuntime())
    monkeypatch.setattr(
        chat_api,
        "build_provider_bound_client",
        lambda provider, fallback_client, timeout=None: fake_client,
    )

    response = await api_client.post(
        "/api/chat/stream",
        json={
            "sessionId": default_session["id"],
            "messages": build_messages("走 chat_completions stream"),
            "model": "provider_openai_chat::gpt-4.1-mini",
        },
    )

    assert response.status_code == 200
    events = parse_sse_events(response.text)
    assert [event["event"] for event in events] == ["delta", "suggestion", "done"]
    assert events[0]["data"] == {"text": "兼容 chat_completions 流式回复。"}
    assert fake_client.stream_calls[0]["model"] == "gpt-4.1-mini"


@pytest.mark.asyncio
async def test_agent_stream_executes_tool_loop_with_openai_compatible_responses_wire(
    api_client: AsyncClient,
    monkeypatch,
) -> None:
    fake_client = FakeOpenAICompatibleResponsesClient()
    default_session = (await api_client.get("/api/chat/sessions/default")).json()
    assert (await api_client.put("/api/weekly-plan", json=build_weekly_plan())).status_code == 200

    class FakeRuntime:
        default_model_ref = "provider_openai_responses::gpt-4.1-mini"

        def resolve_model_ref(self, model_ref: str):
            assert model_ref == "provider_openai_responses::gpt-4.1-mini"
            return (
                type(
                    "Provider",
                    (),
                    {
                        "type": "openai_compatible",
                        "api_key": "sk-openai",
                        "base_url": "https://api.openai.com",
                        "wire_api": "responses",
                        "api_path_mode": "append_v1",
                    },
                )(),
                "gpt-4.1-mini",
            )

    monkeypatch.setattr(chat_api, "get_provider_runtime", lambda: FakeRuntime())
    monkeypatch.setattr(
        chat_api,
        "build_provider_bound_client",
        lambda provider, fallback_client, timeout=None: fake_client,
    )

    response = await api_client.post(
        "/api/chat/stream",
        json={
            "sessionId": default_session["id"],
            "userInput": "请读取我的计划，并给出需要我确认的深蹲调整卡。",
            "model": "provider_openai_responses::gpt-4.1-mini",
        },
    )

    assert response.status_code == 200
    events = parse_sse_events(response.text)
    assert [event["event"] for event in events] == ["delta", "delta", "proposal", "suggestion", "done"]
    assert events[2]["data"]["proposal"]["proposalId"]
    assert fake_client.response_calls[0]["tools"] is not None
    assert len(fake_client.stream_calls) == 1


@pytest.mark.asyncio
async def test_chat_stream_reports_provider_aware_error_message_for_openai_provider(
    api_client: AsyncClient,
    monkeypatch,
) -> None:
    fake_client = FakeDeepSeekClient(
        error=DeepSeekClientError(
            "OpenAI 请求失败（HTTP 401）：invalid api key",
            code="http_error",
        )
    )
    default_session = (await api_client.get("/api/chat/sessions/default")).json()

    class FakeRuntime:
        default_model_ref = "provider_openai_chat::gpt-4.1-mini"

        def resolve_model_ref(self, model_ref: str):
            return (
                type(
                    "Provider",
                    (),
                    {
                        "type": "openai_compatible",
                        "api_key": "sk-openai",
                        "base_url": "https://api.openai.com",
                        "wire_api": "chat_completions",
                        "api_path_mode": "append_v1",
                        "label": "OpenAI 主账号",
                    },
                )(),
                "gpt-4.1-mini",
            )

    monkeypatch.setattr(chat_api, "get_provider_runtime", lambda: FakeRuntime())
    monkeypatch.setattr(
        chat_api,
        "build_provider_bound_client",
        lambda provider, fallback_client, timeout=None: fake_client,
    )

    response = await api_client.post(
        "/api/chat/stream",
        json={
            "sessionId": default_session["id"],
            "messages": build_messages("触发 OpenAI 错误"),
            "model": "provider_openai_chat::gpt-4.1-mini",
        },
    )

    assert response.status_code == 200
    events = parse_sse_events(response.text)
    assert events[0]["event"] == "error"
    assert "OpenAI 请求失败" in events[0]["data"]["message"]
    assert "DeepSeek" not in events[0]["data"]["message"]


@pytest.mark.asyncio
async def test_openai_compatible_runtime_client_keeps_json_responses_path() -> None:
    recorded_requests: list[dict[str, Any]] = []
    client = OpenAICompatibleRuntimeClient(
        api_key="sk-openai",
        base_url="https://api.openai.com",
        wire_api="responses",
        api_path_mode="append_v1",
        client_factory=lambda **kwargs: FakeAsyncHttpxClient(
            recorder=recorded_requests,
            post_response=FakeAsyncHttpxResponse(
                payload={
                    "id": "resp_json_123",
                    "status": "completed",
                    "output": [],
                    "usage": {
                        "input_tokens": 11,
                        "output_tokens": 7,
                        "total_tokens": 18,
                    },
                }
            ),
            **kwargs,
        ),
    )

    payload = await client.request_responses_with_usage(
        input_items=[{"role": "user", "content": [{"type": "input_text", "text": "hello"}]}],
        model="gpt-4.1-mini",
    )

    assert payload["id"] == "resp_json_123"
    assert payload["usage"]["total_tokens"] == 18
    assert recorded_requests[0]["url"] == "https://api.openai.com/v1/responses"


@pytest.mark.asyncio
async def test_openai_compatible_runtime_client_restores_completed_payload_from_sse_response() -> None:
    client = OpenAICompatibleRuntimeClient(
        api_key="sk-openai",
        base_url="https://api.openai.com",
        wire_api="responses",
        api_path_mode="append_v1",
        client_factory=lambda **kwargs: FakeAsyncHttpxClient(
            post_response=FakeAsyncHttpxResponse(
                json_error=ValueError("Expecting value: line 1 column 1 (char 0)"),
                headers={"content-type": "text/event-stream; charset=utf-8"},
                lines=[
                    "event: response.created",
                    'data: {"type":"response.created","response":{"id":"resp_sse_123","status":"in_progress"}}',
                    "",
                    "event: response.completed",
                    'data: {"type":"response.completed","response":{"id":"resp_sse_123","status":"completed","output":[{"type":"message","content":[{"type":"output_text","text":"SSE 工具调用最终回复"}]}],"usage":{"input_tokens":21,"output_tokens":9,"total_tokens":30}}}',
                    "",
                ],
            ),
            **kwargs,
        ),
    )

    payload = await client.request_responses_with_usage(
        input_items=[{"role": "user", "content": [{"type": "input_text", "text": "use tools"}]}],
        model="gpt-4.1-mini",
        tools=[
            {
                "type": "function",
                "name": "get_weekly_plan",
                "description": "读取周计划",
                "parameters": {"type": "object", "properties": {}},
            }
        ],
    )

    assert payload["id"] == "resp_sse_123"
    assert payload["status"] == "completed"
    assert payload["output"][0]["content"][0]["text"] == "SSE 工具调用最终回复"
    assert payload["usage"]["total_tokens"] == 30


@pytest.mark.asyncio
async def test_openai_compatible_runtime_client_retries_transient_sse_upstream_failure() -> None:
    recorded_requests: list[dict[str, Any]] = []
    queued_responses = [
        FakeAsyncHttpxResponse(
            json_error=ValueError("Expecting value: line 1 column 1 (char 0)"),
            headers={"content-type": "text/event-stream; charset=utf-8"},
            lines=[
                'data: {"id":"chatcmpl-ws-ingress","object":"chat.completion.chunk","choices":[{"delta":{"content":"\\u200b"}}]}',
                'data: {"error":{"message":"upstream connection failed: openai ws dial"}}',
                "",
            ],
        ),
        FakeAsyncHttpxResponse(
            payload={
                "id": "resp_retry_ok",
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "重试后恢复成功"}],
                    }
                ],
            }
        ),
    ]

    class SequencedFakeAsyncHttpxClient(FakeAsyncHttpxClient):
        async def post(
            self,
            url: str,
            *,
            json: dict[str, Any],
            headers: dict[str, Any],
        ) -> FakeAsyncHttpxResponse:
            self.recorder.append({"kind": "post", "url": url, "json": json, "headers": headers})
            return queued_responses.pop(0)

    client = OpenAICompatibleRuntimeClient(
        api_key="sk-openai",
        base_url="https://api.openai.com",
        wire_api="responses",
        api_path_mode="append_v1",
        client_factory=lambda **kwargs: SequencedFakeAsyncHttpxClient(
            recorder=recorded_requests,
            **kwargs,
        ),
    )

    payload = await client.request_responses_with_usage(
        input_items=[{"role": "user", "content": [{"type": "input_text", "text": "retry tools"}]}],
        model="gpt-4.1-mini",
        tools=[
            {
                "type": "function",
                "name": "get_weekly_plan",
                "description": "读取周计划",
                "parameters": {"type": "object", "properties": {}},
            }
        ],
    )

    assert payload["id"] == "resp_retry_ok"
    assert payload["output"][0]["content"][0]["text"] == "重试后恢复成功"
    assert len(recorded_requests) == 2


@pytest.mark.asyncio
async def test_openai_compatible_runtime_client_falls_back_to_chat_completions_after_responses_upstream_failure() -> None:
    recorded_requests: list[dict[str, Any]] = []
    queued_responses = [
        FakeAsyncHttpxResponse(
            json_error=ValueError("Expecting value: line 1 column 1 (char 0)"),
            headers={"content-type": "text/event-stream; charset=utf-8"},
            lines=[
                'data: {"error":{"message":"upstream connection failed: openai ws dial failed: status=403"}}',
                "",
            ],
        ),
        FakeAsyncHttpxResponse(
            json_error=ValueError("Expecting value: line 1 column 1 (char 0)"),
            headers={"content-type": "text/event-stream; charset=utf-8"},
            lines=[
                'data: {"error":{"message":"upstream connection failed: openai ws dial failed: status=403"}}',
                "",
            ],
        ),
        FakeAsyncHttpxResponse(
            json_error=ValueError("Expecting value: line 1 column 1 (char 0)"),
            headers={"content-type": "text/event-stream; charset=utf-8"},
            lines=[
                'data: {"error":{"message":"upstream connection failed: openai ws dial failed: status=403"}}',
                "",
            ],
        ),
        FakeAsyncHttpxResponse(
            payload={
                "choices": [
                    {
                        "message": {
                            "content": "已自动降级到 chat_completions 并返回正文。",
                        }
                    }
                ],
                "usage": {"prompt_tokens": 18, "completion_tokens": 11, "total_tokens": 29},
            }
        ),
    ]

    class SequencedFallbackClient(FakeAsyncHttpxClient):
        async def post(
            self,
            url: str,
            *,
            json: dict[str, Any],
            headers: dict[str, Any],
        ) -> FakeAsyncHttpxResponse:
            self.recorder.append({"kind": "post", "url": url, "json": json, "headers": headers})
            return queued_responses.pop(0)

    client = OpenAICompatibleRuntimeClient(
        api_key="sk-openai",
        base_url="https://sub2.congmingai.com/v1",
        wire_api="responses",
        api_path_mode="append_v1",
        client_factory=lambda **kwargs: SequencedFallbackClient(
            recorder=recorded_requests,
            **kwargs,
        ),
    )

    result = await client.request_chat_with_usage(
        messages=build_messages("降级验证"),
        model="gpt-5.5",
    )

    assert result.content == "已自动降级到 chat_completions 并返回正文。"
    assert result.usage == {"prompt_tokens": 18, "completion_tokens": 11, "total_tokens": 29}
    assert [request["url"] for request in recorded_requests] == [
        "https://sub2.congmingai.com/v1/responses",
        "https://sub2.congmingai.com/v1/responses",
        "https://sub2.congmingai.com/v1/responses",
        "https://sub2.congmingai.com/v1/chat/completions",
    ]


@pytest.mark.asyncio
async def test_openai_compatible_runtime_client_network_error_uses_provider_label_and_fallback_detail() -> None:
    class FailingHttpxClient(FakeAsyncHttpxClient):
        async def post(
            self,
            url: str,
            *,
            json: dict[str, Any],
            headers: dict[str, Any],
        ) -> FakeAsyncHttpxResponse:
            del url, json, headers
            raise httpx.ReadTimeout("timed out")

    client = OpenAICompatibleRuntimeClient(
        api_key="sk-openai",
        base_url="https://sub2.congmingai.com/v1",
        wire_api="chat_completions",
        api_path_mode="append_v1",
        provider_label="聪明AI",
        client_factory=lambda **kwargs: FailingHttpxClient(**kwargs),
    )

    with pytest.raises(DeepSeekClientError) as exc_info:
        await client.request_chat_with_usage(
            messages=build_messages("网络错误文案测试"),
            model="gpt-5.4-mini",
        )

    assert str(exc_info.value) == "聪明AI 网络请求失败：timed out"


@pytest.mark.asyncio
async def test_openai_compatible_runtime_client_sse_network_error_uses_provider_label() -> None:
    client = OpenAICompatibleRuntimeClient(
        api_key="sk-openai",
        base_url="https://sub2.congmingai.com/v1",
        wire_api="responses",
        api_path_mode="append_v1",
        provider_label="聪明AI",
        client_factory=lambda **kwargs: FakeAsyncHttpxClient(
            post_response=FakeAsyncHttpxResponse(
                json_error=ValueError("Expecting value: line 1 column 1 (char 0)"),
                headers={"content-type": "text/event-stream; charset=utf-8"},
                lines=[
                    'data: {"error":{"message":"upstream connection failed: openai ws dial failed: status=403"}}',
                    "",
                ],
            ),
            **kwargs,
        ),
    )

    with pytest.raises(DeepSeekClientError) as exc_info:
        await client.request_responses_with_usage(
            input_items=[{"role": "user", "content": [{"type": "input_text", "text": "测试中转站 SSE 错误"}]}],
            model="gpt-5.4-mini",
        )

    assert (
        str(exc_info.value)
        == "聪明AI 网络请求失败：upstream connection failed: openai ws dial failed: status=403"
    )


@pytest.mark.asyncio
async def test_openai_compatible_runtime_stream_fallback_does_not_issue_duplicate_non_stream_chat_completion_request() -> None:
    recorded_requests: list[dict[str, Any]] = []
    queued_post_responses = [
        FakeAsyncHttpxResponse(
            json_error=ValueError("Expecting value: line 1 column 1 (char 0)"),
            headers={"content-type": "text/event-stream; charset=utf-8"},
            lines=[
                'data: {"error":{"message":"upstream connection failed: openai ws dial failed: status=403"}}',
                "",
            ],
        ),
        FakeAsyncHttpxResponse(
            json_error=ValueError("Expecting value: line 1 column 1 (char 0)"),
            headers={"content-type": "text/event-stream; charset=utf-8"},
            lines=[
                'data: {"error":{"message":"upstream connection failed: openai ws dial failed: status=403"}}',
                "",
            ],
        ),
        FakeAsyncHttpxResponse(
            json_error=ValueError("Expecting value: line 1 column 1 (char 0)"),
            headers={"content-type": "text/event-stream; charset=utf-8"},
            lines=[
                'data: {"error":{"message":"upstream connection failed: openai ws dial failed: status=403"}}',
                "",
            ],
        ),
    ]

    class SequencedFallbackClient(FakeAsyncHttpxClient):
        async def post(
            self,
            url: str,
            *,
            json: dict[str, Any],
            headers: dict[str, Any],
        ) -> FakeAsyncHttpxResponse:
            self.recorder.append({"kind": "post", "url": url, "json": json, "headers": headers})
            return queued_post_responses.pop(0)

        def stream(
            self,
            method: str,
            url: str,
            *,
            json: dict[str, Any],
            headers: dict[str, Any],
        ) -> FakeAsyncHttpxStreamContext:
            self.recorder.append(
                {
                    "kind": "stream",
                    "method": method,
                    "url": url,
                    "json": json,
                    "headers": headers,
                }
            )
            return FakeAsyncHttpxStreamContext(
                FakeAsyncHttpxResponse(
                    lines=[
                        'data: {"choices":[{"delta":{"content":"兼容"}}]}',
                        'data: {"choices":[{"delta":{"content":"流式"}}],"usage":{"prompt_tokens":8,"completion_tokens":4,"total_tokens":12}}',
                        "data: [DONE]",
                    ]
                )
            )

    client = OpenAICompatibleRuntimeClient(
        api_key="sk-openai",
        base_url="https://sub2.congmingai.com/v1",
        wire_api="responses",
        api_path_mode="append_v1",
        client_factory=lambda **kwargs: SequencedFallbackClient(
            recorder=recorded_requests,
            **kwargs,
        ),
    )

    chunks: list[str] = []
    usage_payload: dict[str, Any] | None = None
    async for event in client.stream_chat_with_usage(
        messages=build_messages("流式降级验证"),
        model="gpt-5.5",
    ):
        if event.text:
            chunks.append(event.text)
        if event.usage:
            usage_payload = event.usage

    assert "".join(chunks) == "兼容流式"
    assert usage_payload == {"prompt_tokens": 8, "completion_tokens": 4, "total_tokens": 12}
    assert [request["kind"] for request in recorded_requests] == ["post", "post", "post", "stream"]
    assert recorded_requests[-1]["url"] == "https://sub2.congmingai.com/v1/chat/completions"


@pytest.mark.asyncio
async def test_openai_responses_tool_loop_provider_falls_back_to_chat_completions_and_preserves_tool_calls() -> None:
    recorded_requests: list[dict[str, Any]] = []
    queued_responses = [
        FakeAsyncHttpxResponse(
            json_error=ValueError("Expecting value: line 1 column 1 (char 0)"),
            headers={"content-type": "text/event-stream; charset=utf-8"},
            lines=[
                'data: {"error":{"message":"upstream connection failed: openai ws dial failed: status=403"}}',
                "",
            ],
        ),
        FakeAsyncHttpxResponse(
            json_error=ValueError("Expecting value: line 1 column 1 (char 0)"),
            headers={"content-type": "text/event-stream; charset=utf-8"},
            lines=[
                'data: {"error":{"message":"upstream connection failed: openai ws dial failed: status=403"}}',
                "",
            ],
        ),
        FakeAsyncHttpxResponse(
            json_error=ValueError("Expecting value: line 1 column 1 (char 0)"),
            headers={"content-type": "text/event-stream; charset=utf-8"},
            lines=[
                'data: {"error":{"message":"upstream connection failed: openai ws dial failed: status=403"}}',
                "",
            ],
        ),
        FakeAsyncHttpxResponse(
            payload={
                "choices": [
                    {
                        "message": {
                            "content": "",
                            "tool_calls": [
                                {
                                    "id": "call_propose",
                                    "type": "function",
                                    "function": {
                                        "name": "propose_plan_change",
                                        "arguments": json.dumps(
                                            {
                                                "day": "Monday",
                                                "summary": "改成恢复型安排。",
                                                "changes": [
                                                    {
                                                        "action": "update",
                                                        "exerciseName": "深蹲",
                                                        "field": "rpe",
                                                        "newValue": 7,
                                                    }
                                                ],
                                            },
                                            ensure_ascii=False,
                                        ),
                                    },
                                }
                            ],
                        }
                    }
                ]
            }
        ),
    ]

    class SequencedFallbackClient(FakeAsyncHttpxClient):
        async def post(
            self,
            url: str,
            *,
            json: dict[str, Any],
            headers: dict[str, Any],
        ) -> FakeAsyncHttpxResponse:
            self.recorder.append({"kind": "post", "url": url, "json": json, "headers": headers})
            return queued_responses.pop(0)

    runtime_client = OpenAICompatibleRuntimeClient(
        api_key="sk-openai",
        base_url="https://sub2.congmingai.com/v1",
        wire_api="responses",
        api_path_mode="append_v1",
        client_factory=lambda **kwargs: SequencedFallbackClient(
            recorder=recorded_requests,
            **kwargs,
        ),
    )
    provider = _OpenAIResponsesToolLoopProvider(client=runtime_client)

    response = await provider.generate_chat(
        messages=build_messages("请生成一张计划修改卡"),
        model="gpt-5.5",
        tools=[
            {
                "type": "function",
                "name": "propose_plan_change",
                "description": "生成训练计划修改建议卡",
                "parameters": {"type": "object", "properties": {}},
            }
        ],
    )

    normalized_calls = provider.normalize_tool_call_response(response["raw"])

    assert response["text"] == ""
    assert normalized_calls[0]["toolName"] == "propose_plan_change"
    assert normalized_calls[0]["arguments"]["day"] == "Monday"
    assert normalized_calls[0]["rawProviderPayload"]["wireApi"] == "chat_completions"
    assert recorded_requests[-1]["url"] == "https://sub2.congmingai.com/v1/chat/completions"
    assert recorded_requests[-1]["json"]["tools"] == [
        {
            "type": "function",
            "function": {
                "name": "propose_plan_change",
                "description": "生成训练计划修改建议卡",
                "parameters": {"type": "object", "properties": {}},
            },
        }
    ]


@pytest.mark.asyncio
async def test_openai_runtime_converts_responses_followup_messages_when_function_call_output_http_mode_is_rejected() -> None:
    recorded_requests: list[dict[str, Any]] = []
    queued_responses = [
        FakeAsyncHttpxResponse(
            payload={
                "id": "resp_fc_1",
                "status": "completed",
                "output": [
                    {
                        "type": "function_call",
                        "call_id": "call_propose",
                        "name": "propose_plan_change",
                        "arguments": json.dumps(
                            {
                                "day": "Monday",
                                "summary": "改成恢复型安排。",
                                "changes": [
                                    {
                                        "action": "update",
                                        "exerciseName": "深蹲",
                                        "field": "rpe",
                                        "newValue": 7,
                                    }
                                ],
                            },
                            ensure_ascii=False,
                        ),
                    }
                ],
            }
        ),
        FakeAsyncHttpxResponse(
            status_code=400,
            reason_phrase="Bad Request",
            payload={
                "error": {
                    "message": "function_call_output requires item_reference ids matching each call_id on HTTP requests; continuation via previous_response_id is only supported on Responses WebSocket v2"
                }
            },
        ),
        FakeAsyncHttpxResponse(
            payload={
                "choices": [
                    {
                        "message": {
                            "content": "已生成待确认计划卡。",
                        }
                    }
                ]
            }
        ),
    ]

    class SequencedFallbackClient(FakeAsyncHttpxClient):
        async def post(
            self,
            url: str,
            *,
            json: dict[str, Any],
            headers: dict[str, Any],
        ) -> FakeAsyncHttpxResponse:
            self.recorder.append({"kind": "post", "url": url, "json": json, "headers": headers})
            return queued_responses.pop(0)

    runtime_client = OpenAICompatibleRuntimeClient(
        api_key="sk-openai",
        base_url="https://sub2.congmingai.com/v1",
        wire_api="responses",
        api_path_mode="append_v1",
        client_factory=lambda **kwargs: SequencedFallbackClient(
            recorder=recorded_requests,
            **kwargs,
        ),
    )

    first_payload, first_wire = await runtime_client.request_openai_payload_with_fallback(
        messages=build_messages("请生成计划卡"),
        model="gpt-5.5",
        tools=[
            {
                "type": "function",
                "name": "propose_plan_change",
                "description": "生成训练计划修改建议卡",
                "parameters": {"type": "object", "properties": {}},
            }
        ],
    )
    assert first_wire == "responses"

    followup_messages = [
        {"role": "system", "content": "SYSTEM_PROMPT"},
        {"role": "assistant", "content": "先观察疲劳。"},
        {"role": "user", "content": "请生成计划卡"},
        first_payload["output"][0],
        {"type": "function_call_output", "call_id": "call_propose", "output": '{"ok":true}'},
    ]

    second_payload, second_wire = await runtime_client.request_openai_payload_with_fallback(
        messages=followup_messages,
        model="gpt-5.5",
        tools=[
            {
                "type": "function",
                "name": "propose_plan_change",
                "description": "生成训练计划修改建议卡",
                "parameters": {"type": "object", "properties": {}},
            }
        ],
    )

    assert second_wire == "chat_completions"
    assert second_payload["choices"][0]["message"]["content"] == "已生成待确认计划卡。"
    assert recorded_requests[-1]["url"] == "https://sub2.congmingai.com/v1/chat/completions"
    chat_messages = recorded_requests[-1]["json"]["messages"]
    assert chat_messages[-2]["role"] == "assistant"
    assert chat_messages[-2]["tool_calls"][0]["id"] == "call_propose"
    assert chat_messages[-1] == {
        "role": "tool",
        "tool_call_id": "call_propose",
        "name": "propose_plan_change",
        "content": '{"ok":true}',
    }


def test_build_provider_bound_client_prefers_openai_compatible_runtime_for_deepseek_provider() -> None:
    recorded_requests: list[dict[str, Any]] = []
    fallback_client = DeepSeekClient(
        api_key="sk-fallback",
        base_url="https://api.deepseek.com",
        client_factory=lambda **kwargs: FakeAsyncHttpxClient(
            recorder=recorded_requests,
            post_response=FakeAsyncHttpxResponse(
                payload={
                    "choices": [
                        {
                            "message": {
                                "content": "legacy fallback reply",
                            }
                        }
                    ]
                }
            ),
            stream_response=FakeAsyncHttpxResponse(
                lines=[
                    'data: {"choices":[{"delta":{"content":"legacy stream"}}]}',
                    "data: [DONE]",
                ]
            ),
            **kwargs,
        ),
    )
    provider = type(
        "Provider",
        (),
        {
            "type": "openai_compatible",
            "api_key": "sk-provider",
            "base_url": "https://api.deepseek.com",
            "wire_api": "chat_completions",
            "api_path_mode": "raw_root",
            "label": "DeepSeek 主账号",
        },
    )()

    client = build_provider_bound_client(provider, fallback_client)

    assert isinstance(client, OpenAICompatibleRuntimeClient)
    assert not isinstance(client, DeepSeekClient)


def test_chat_completions_tool_loop_provider_replaces_legacy_deepseek_specific_name() -> None:
    provider = _ChatCompletionsToolLoopProvider(client=FakeReplyModelClient("ok"))
    assert provider.__class__.__name__ == "_ChatCompletionsToolLoopProvider"


@pytest.mark.asyncio
async def test_chat_stream_deepseek_model_ref_uses_openai_compatible_runtime_not_legacy_fallback(
    api_client: AsyncClient,
    monkeypatch,
) -> None:
    runtime_requests: list[dict[str, Any]] = []
    fallback_requests: list[dict[str, Any]] = []
    default_session = (await api_client.get("/api/chat/sessions/default")).json()

    class FakeRuntime:
        default_model_ref = "provider_deepseek_main::deepseek-chat"

        def resolve_model_ref(self, model_ref: str):
            assert model_ref == "provider_deepseek_main::deepseek-chat"
            return (
                type(
                    "Provider",
                    (),
                    {
                        "type": "openai_compatible",
                        "api_key": "sk-provider",
                        "base_url": "https://api.deepseek.com",
                        "wire_api": "chat_completions",
                        "api_path_mode": "raw_root",
                        "label": "DeepSeek 主账号",
                    },
                )(),
                "deepseek-chat",
            )

    fallback_client = DeepSeekClient(
        api_key="sk-fallback",
        base_url="https://api.deepseek.com",
        client_factory=lambda **kwargs: FakeAsyncHttpxClient(
            recorder=fallback_requests,
            post_response=FakeAsyncHttpxResponse(
                payload={
                    "choices": [
                        {
                            "message": {
                                "content": "legacy fallback reply",
                            }
                        }
                    ]
                }
            ),
            stream_response=FakeAsyncHttpxResponse(
                lines=[
                    'data: {"choices":[{"delta":{"content":"legacy fallback stream"}}]}',
                    "data: [DONE]",
                ]
            ),
            **kwargs,
        ),
    )
    app.dependency_overrides[chat_api.get_deepseek_client] = lambda: fallback_client
    monkeypatch.setattr(chat_api, "get_provider_runtime", lambda: FakeRuntime())

    def build_runtime_client(provider, fallback_client, timeout=None):
        client = build_provider_bound_client(
            provider,
            fallback_client,
            timeout=timeout or 30.0,
        )
        if isinstance(client, OpenAICompatibleRuntimeClient):
            client.client_factory = lambda **kwargs: FakeAsyncHttpxClient(
                recorder=runtime_requests,
                post_response=FakeAsyncHttpxResponse(
                    payload={
                        "choices": [
                            {
                                "message": {
                                    "content": "runtime non-stream should stay unused",
                                }
                            }
                        ]
                    }
                ),
                stream_response=FakeAsyncHttpxResponse(
                    lines=[
                        'data: {"choices":[{"delta":{"content":"DeepSeek 运行时流式回复。"}}]}',
                        'data: {"usage":{"prompt_tokens":12,"completion_tokens":8,"total_tokens":20}}',
                        "data: [DONE]",
                    ]
                ),
                **kwargs,
            )
        return client

    monkeypatch.setattr(chat_api, "build_provider_bound_client", build_runtime_client)

    response = await api_client.post(
        "/api/chat/stream",
        json={
            "sessionId": default_session["id"],
            "messages": build_messages("走 DeepSeek modelRef 流式链路"),
            "model": "provider_deepseek_main::deepseek-chat",
        },
    )

    assert response.status_code == 200
    events = parse_sse_events(response.text)
    assert [event["event"] for event in events] == ["delta", "suggestion", "done"]
    assert events[0]["data"] == {"text": "DeepSeek 运行时流式回复。"}
    assert runtime_requests[0]["kind"] == "stream"
    assert runtime_requests[0]["url"] == "https://api.deepseek.com/chat/completions"
    assert runtime_requests[0]["json"]["model"] == "deepseek-chat"
    assert fallback_requests == []
