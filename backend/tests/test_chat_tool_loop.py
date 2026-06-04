from __future__ import annotations

from collections.abc import AsyncIterator
import json
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.chat_session import run_tool_calling_chat
from backend.agent.deepseek_client import DeepSeekChatResult
from backend.agent.tool_calling import build_default_tool_registry
from backend.db.database import create_engine_and_session_factory
from backend.db.models import Base, ChatSession, ToolCallLog, WeeklyPlanDay, utc_now
from backend.providers.gemini_client import GeminiNativeClient


class ToolLoopClient:
    def __init__(self) -> None:
        self.calls: list[list[dict[str, Any]]] = []

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
        del model, tools, tool_choice, stream
        self.calls.append(messages)
        if len(self.calls) == 1:
            return DeepSeekChatResult(
                content="",
                tool_calls=[
                    {
                        "id": "call_weekly",
                        "type": "function",
                        "function": {"name": "get_weekly_plan", "arguments": "{}"},
                    }
                ],
            )
        return DeepSeekChatResult(content="我读取了本周计划，建议保持深蹲容量。")


class ThinkingToolLoopClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def request_chat_with_usage(self, **kwargs: Any) -> DeepSeekChatResult:
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            return DeepSeekChatResult(
                content="",
                reasoning_content="需要先读取本周计划。",
                tool_calls=[
                    {
                        "id": "call_weekly",
                        "type": "function",
                        "function": {"name": "get_weekly_plan", "arguments": "{}"},
                    }
                ],
            )
        return DeepSeekChatResult(content="读取后建议保持容量。")


class MultiToolLoopClient:
    def __init__(self) -> None:
        self.calls: list[list[dict[str, Any]]] = []

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
        del model, tools, tool_choice, stream
        self.calls.append(messages)
        if len(self.calls) == 1:
            return DeepSeekChatResult(
                content="",
                tool_calls=[
                    {
                        "id": "call_profile",
                        "type": "function",
                        "function": {"name": "get_profile", "arguments": "{}"},
                    },
                    {
                        "id": "call_weekly",
                        "type": "function",
                        "function": {"name": "get_weekly_plan", "arguments": "{}"},
                    },
                ],
            )
        return DeepSeekChatResult(content="我已经读取了档案和本周计划。")


class ProposalToolLoopClient:
    def __init__(self) -> None:
        self.calls: list[list[dict[str, Any]]] = []

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
        del model, tools, tool_choice, stream
        self.calls.append(messages)
        if len(self.calls) == 1:
            return DeepSeekChatResult(
                content="",
                tool_calls=[
                    {
                        "id": "call_proposal",
                        "type": "function",
                        "function": {
                            "name": "propose_plan_change",
                            "arguments": json.dumps(
                                {
                                    "day": "Monday",
                                    "summary": "长摘要" * 400,
                                    "changes": [
                                        {
                                            "action": "update",
                                            "exerciseName": "深蹲",
                                            "field": "pct",
                                            "newValue": 0.7,
                                        }
                                    ],
                                },
                                ensure_ascii=False,
                            ),
                        },
                    }
                ],
            )
        return DeepSeekChatResult(content="建议已整理成可确认 proposal。")


class FakeGeminiResponse:
    def __init__(self, json_data: dict[str, Any], status_code: int = 200) -> None:
        self._json_data = json_data
        self.status_code = status_code
        self.reason_phrase = "OK"

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300

    def json(self) -> dict[str, Any]:
        return self._json_data


class FakeGeminiHttpClient:
    def __init__(
        self,
        *,
        responses: list[FakeGeminiResponse],
        request_log: list[dict[str, Any]],
        **_: Any,
    ) -> None:
        self.responses = responses
        self.request_log = request_log

    async def __aenter__(self) -> "FakeGeminiHttpClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False

    async def post(
        self,
        url: str,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> FakeGeminiResponse:
        self.request_log.append(
            {
                "url": url,
                "params": params or {},
                "json": json or {},
                "headers": headers or {},
            }
        )
        return self.responses.pop(0)


class RepeatingProposalToolLoopClient:
    def __init__(self) -> None:
        self.calls: list[list[dict[str, Any]]] = []

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
        del model, tools, tool_choice, stream
        self.calls.append(messages)
        return DeepSeekChatResult(
            content="",
            tool_calls=[
                {
                    "id": f"call_proposal_{len(self.calls)}",
                    "type": "function",
                    "function": {
                        "name": "propose_day_plan_replace",
                        "arguments": json.dumps(
                            {
                                "day": "Monday",
                                "summary": "把周一继续压低成完全休息日。",
                                "dayPlan": {
                                    "type": "rest",
                                    "exercises": [
                                        {
                                            "name": "睡前轻量拉伸",
                                            "tier": "accessory",
                                            "template": {
                                                "loadMode": "fixed",
                                                "setType": "straight",
                                                "sets": 1,
                                                "repsText": "10分钟",
                                                "ref1RM": None,
                                            },
                                            "instance": {
                                                "kg": None,
                                                "pct": None,
                                                "rpe": None,
                                                "note": "仅保留极低强度放松。",
                                            },
                                            "ref1RM": None,
                                            "pct": None,
                                            "kg": None,
                                            "sets": 1,
                                            "reps": None,
                                            "rpe": None,
                                            "note": "仅保留极低强度放松。",
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


@pytest_asyncio.fixture
async def db_session(tmp_path: Path) -> AsyncIterator[AsyncSession]:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'tool-loop.db'}"
    engine, session_factory = create_engine_and_session_factory(database_url)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_tool_loop_executes_readonly_tool_and_logs_slimmed_result(
    db_session: AsyncSession,
) -> None:
    chat_session = ChatSession(title="tool-loop", created_at=utc_now(), updated_at=utc_now())
    db_session.add(chat_session)
    await db_session.flush()
    db_session.add(WeeklyPlanDay(day_key="Monday", type="strength", exercises=[{"name": "深蹲", "rpe": 8}]))
    await db_session.commit()

    client = ToolLoopClient()
    result = await run_tool_calling_chat(
        session=db_session,
        session_id=chat_session.id,
        messages=[{"role": "user", "content": "读取本周计划再建议"}],
        model="deepseek-chat",
        deepseek_client=client,
        registry=build_default_tool_registry(),
    )

    logs = (await db_session.execute(select(ToolCallLog))).scalars().all()

    assert result.content == "我读取了本周计划，建议保持深蹲容量。"
    assert len(client.calls) == 2
    assert client.calls[1][-1]["role"] == "tool"
    assert client.calls[1][-1]["tool_call_id"] == "call_weekly"
    assert len(logs) == 1
    assert logs[0].tool_name == "get_weekly_plan"
    assert logs[0].status == "succeeded"
    assert "深蹲" in logs[0].result_summary


@pytest.mark.asyncio
async def test_tool_loop_returns_error_when_tool_rounds_exceed_limit(
    db_session: AsyncSession,
) -> None:
    class InfiniteToolClient(ToolLoopClient):
        async def request_chat_with_usage(self, **kwargs: Any) -> DeepSeekChatResult:
            self.calls.append(kwargs["messages"])
            return DeepSeekChatResult(
                content="",
                tool_calls=[
                    {
                        "id": f"call_{len(self.calls)}",
                        "type": "function",
                        "function": {"name": "get_weekly_plan", "arguments": "{}"},
                    }
                ],
            )

    chat_session = ChatSession(title="tool-loop-limit", created_at=utc_now(), updated_at=utc_now())
    db_session.add(chat_session)
    await db_session.commit()

    result = await run_tool_calling_chat(
        session=db_session,
        session_id=chat_session.id,
        messages=[{"role": "user", "content": "一直读工具"}],
        model="deepseek-chat",
        deepseek_client=InfiniteToolClient(),
        registry=build_default_tool_registry(),
        max_tool_rounds=2,
    )

    assert result.content == "工具调用次数过多，请稍后重试或缩小问题范围。"


@pytest.mark.asyncio
async def test_tool_loop_preserves_thinking_reasoning_content_between_rounds(
    db_session: AsyncSession,
) -> None:
    chat_session = ChatSession(title="tool-loop-thinking", created_at=utc_now(), updated_at=utc_now())
    db_session.add(chat_session)
    await db_session.flush()
    db_session.add(WeeklyPlanDay(day_key="Monday", type="strength", exercises=[{"name": "深蹲"}]))
    await db_session.commit()

    client = ThinkingToolLoopClient()
    result = await run_tool_calling_chat(
        session=db_session,
        session_id=chat_session.id,
        messages=[{"role": "user", "content": "思考后读取计划"}],
        model="deepseek-v4-pro",
        deepseek_client=client,
        registry=build_default_tool_registry(),
        thinking={"type": "enabled"},
        reasoning_effort="max",
    )

    assert result.content == "读取后建议保持容量。"
    assert client.calls[0]["thinking"] == {"type": "enabled"}
    assert client.calls[0]["reasoning_effort"] == "max"
    assert client.calls[0]["tool_choice"] is None
    assistant_message = client.calls[1]["messages"][1]
    assert assistant_message["role"] == "assistant"
    assert assistant_message["reasoning_content"] == "需要先读取本周计划。"


@pytest.mark.asyncio
async def test_tool_loop_keeps_one_assistant_tool_call_message_for_parallel_deepseek_calls(
    db_session: AsyncSession,
) -> None:
    chat_session = ChatSession(title="tool-loop-parallel", created_at=utc_now(), updated_at=utc_now())
    db_session.add(chat_session)
    await db_session.flush()
    db_session.add(WeeklyPlanDay(day_key="Monday", type="strength", exercises=[{"name": "深蹲"}]))
    await db_session.commit()

    client = MultiToolLoopClient()
    result = await run_tool_calling_chat(
        session=db_session,
        session_id=chat_session.id,
        messages=[{"role": "user", "content": "同时读取档案和计划"}],
        model="deepseek-v4-pro",
        deepseek_client=client,
        registry=build_default_tool_registry(),
    )

    followup_messages = client.calls[1]
    assistant_messages = [message for message in followup_messages if message.get("role") == "assistant"]
    tool_messages = [message for message in followup_messages if message.get("role") == "tool"]

    assert result.content == "我已经读取了档案和本周计划。"
    assert len(assistant_messages) == 1
    assert [message["tool_call_id"] for message in tool_messages] == ["call_profile", "call_weekly"]


@pytest.mark.asyncio
async def test_tool_loop_keeps_full_proposal_payload_in_chat_completions_followup_messages(
    db_session: AsyncSession,
) -> None:
    chat_session = ChatSession(title="tool-loop-proposal", created_at=utc_now(), updated_at=utc_now())
    db_session.add(chat_session)
    await db_session.flush()
    db_session.add(WeeklyPlanDay(day_key="Monday", type="strength", exercises=[{"name": "深蹲", "pct": 0.75}]))
    await db_session.commit()

    client = ProposalToolLoopClient()
    result = await run_tool_calling_chat(
        session=db_session,
        session_id=chat_session.id,
        messages=[{"role": "user", "content": "给我一张降强度 proposal 卡"}],
        model="deepseek-chat",
        deepseek_client=client,
        registry=build_default_tool_registry(),
    )

    followup_tool_message = client.calls[1][-1]
    tool_payload = json.loads(followup_tool_message["content"])

    assert result.content == "建议已整理成可确认 proposal。"
    assert followup_tool_message["role"] == "tool"
    assert "[trimmed:propose_plan_change]" not in followup_tool_message["content"]
    assert tool_payload["proposal"]["summary"] == "长摘要" * 400
    assert tool_payload["proposal"]["proposalId"]
    assert tool_payload["proposal"]["status"] == "pending"
    assert tool_payload["validation"]["ok"] is True


@pytest.mark.asyncio
async def test_tool_loop_returns_latest_proposal_instead_of_round_limit_placeholder_when_model_repeats_proposals(
    db_session: AsyncSession,
) -> None:
    chat_session = ChatSession(title="tool-loop-repeat-proposal", created_at=utc_now(), updated_at=utc_now())
    db_session.add(chat_session)
    await db_session.flush()
    db_session.add(WeeklyPlanDay(day_key="Monday", type="active_recovery", exercises=[{"name": "散步", "sets": 1, "reps": 20}]))
    await db_session.commit()

    client = RepeatingProposalToolLoopClient()
    result = await run_tool_calling_chat(
        session=db_session,
        session_id=chat_session.id,
        messages=[{"role": "user", "content": "给我一张待确认的周一休息日 proposal 卡"}],
        model="deepseek-chat",
        deepseek_client=client,
        registry=build_default_tool_registry(),
        max_tool_rounds=2,
    )

    assert result.proposals
    assert result.proposals[-1]["proposalId"]
    assert result.proposals[-1]["status"] == "pending"
    assert result.content != "工具调用次数过多，请稍后重试或缩小问题范围。"


@pytest.mark.asyncio
async def test_gemini_tool_loop_returns_function_response_in_followup_history(
    db_session: AsyncSession,
) -> None:
    chat_session = ChatSession(title="gemini-tool-loop", created_at=utc_now(), updated_at=utc_now())
    db_session.add(chat_session)
    await db_session.flush()
    db_session.add(WeeklyPlanDay(day_key="Monday", type="strength", exercises=[{"name": "深蹲", "rpe": 8}]))
    await db_session.commit()

    request_log: list[dict[str, Any]] = []
    queued_responses = [
        FakeGeminiResponse(
            {
                "candidates": [
                    {
                        "content": {
                            "role": "model",
                            "parts": [
                                {
                                    "functionCall": {
                                        "id": "call_weekly",
                                        "name": "get_weekly_plan",
                                        "args": {},
                                    }
                                }
                            ],
                        }
                    }
                ]
            }
        ),
        FakeGeminiResponse(
            {
                "candidates": [
                    {
                        "content": {
                            "role": "model",
                            "parts": [{"text": "我读取了本周计划，建议今天维持原计划。"}],
                        }
                    }
                ]
            }
        ),
    ]
    client = GeminiNativeClient(
        api_key="AIza-test",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        client_factory=lambda **kwargs: FakeGeminiHttpClient(
            responses=queued_responses,
            request_log=request_log,
            **kwargs,
        ),
    )

    result = await run_tool_calling_chat(
        session=db_session,
        session_id=chat_session.id,
        messages=[{"role": "user", "content": "读取本周计划再建议"}],
        model="gemini-2.5-flash",
        deepseek_client=client,
        registry=build_default_tool_registry(),
    )

    second_payload = request_log[1]["json"]

    assert result.content == "我读取了本周计划，建议今天维持原计划。"
    assert second_payload["tools"][0]["functionDeclarations"][0]["name"] == "get_profile"
    assert second_payload["contents"][1]["role"] == "model"
    assert second_payload["contents"][1]["parts"][0]["functionCall"]["name"] == "get_weekly_plan"
    assert second_payload["contents"][2]["role"] == "user"
    assert second_payload["contents"][2]["parts"][0]["functionResponse"]["name"] == "get_weekly_plan"
    assert second_payload["contents"][2]["parts"][0]["functionResponse"]["id"] == "call_weekly"


@pytest.mark.asyncio
async def test_gemini_tool_loop_generates_day_plan_replace_proposal(
    db_session: AsyncSession,
) -> None:
    # 锁定 Gemini 通过 functionCall 触发 propose_day_plan_replace 时，dayPlan 经 DayPlanArgs
    # 解析 + model_dump() 回到普通 dict 后仍能正确生成待确认 proposal 卡。
    chat_session = ChatSession(title="gemini-day-plan-proposal", created_at=utc_now(), updated_at=utc_now())
    db_session.add(chat_session)
    await db_session.flush()
    db_session.add(WeeklyPlanDay(day_key="Monday", type="strength", exercises=[{"name": "深蹲", "pct": 0.75}]))
    await db_session.commit()

    request_log: list[dict[str, Any]] = []
    queued_responses = [
        FakeGeminiResponse(
            {
                "candidates": [
                    {
                        "content": {
                            "role": "model",
                            "parts": [
                                {
                                    "functionCall": {
                                        "id": "call_day_plan",
                                        "name": "propose_day_plan_replace",
                                        # Gemini 直接把结构化参数放在 args（非 JSON 字符串），
                                        # dayPlan 携带 type + exercises，验证新 DayPlanArgs 模型可被工具回环消费。
                                        "args": {
                                            "day": "Monday",
                                            "summary": "把周一改成恢复型腿日",
                                            "dayPlan": {
                                                "type": "腿日",
                                                "exercises": [
                                                    {
                                                        "name": "深蹲",
                                                        "tier": "main",
                                                        "sets": 3,
                                                        "reps": 5,
                                                        "rpe": 7,
                                                        "note": "恢复周主项",
                                                    }
                                                ],
                                            },
                                        },
                                    }
                                }
                            ],
                        }
                    }
                ]
            }
        ),
        FakeGeminiResponse(
            {
                "candidates": [
                    {
                        "content": {
                            "role": "model",
                            "parts": [{"text": "已整理成可确认的周一替换 proposal。"}],
                        }
                    }
                ]
            }
        ),
    ]
    client = GeminiNativeClient(
        api_key="AIza-test",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        client_factory=lambda **kwargs: FakeGeminiHttpClient(
            responses=queued_responses,
            request_log=request_log,
            **kwargs,
        ),
    )

    result = await run_tool_calling_chat(
        session=db_session,
        session_id=chat_session.id,
        messages=[{"role": "user", "content": "把周一改成恢复型腿日"}],
        model="gemini-2.5-flash",
        deepseek_client=client,
        registry=build_default_tool_registry(),
    )

    assert result.content == "已整理成可确认的周一替换 proposal。"
    assert result.proposals
    latest_proposal = result.proposals[-1]
    assert latest_proposal["kind"] == "day_plan_replace"
    assert latest_proposal["status"] == "pending"
    assert latest_proposal["proposalId"]
    assert latest_proposal["dayPlan"]["type"] == "腿日"
    assert latest_proposal["dayPlan"]["exercises"][0]["name"] == "深蹲"
