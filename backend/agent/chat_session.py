from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.context_manager import AgentContext, PromptAssembler, SummaryCompressor
from backend.agent.deepseek_client import DeepSeekChatResult
from backend.agent.memory import MemoryRetriever
from backend.agent.tool_calling import ToolRegistry, ToolResultSlimmer
from backend.db.models import (
    ChatMessage,
    ChatSessionSummary,
    DailyLog,
    KnowledgeItem,
    MemoryItem,
    Profile,
    ToolCallLog,
    WEEKDAY_ORDER,
    WeeklyPlanDay,
    utc_now,
)
from backend.db.seed import DEFAULT_PROFILE_ID


@dataclass(frozen=True)
class AgentRequest:
    messages: list[dict[str, str]]
    debug: dict[str, Any]
    model: str | None = None


@dataclass(frozen=True)
class ToolLoopResult:
    content: str
    messages: list[dict[str, Any]]
    tool_rounds: int


async def build_agent_request(
    *,
    session: AsyncSession,
    session_id: int,
    user_input: str,
    model_config: dict[str, Any] | None = None,
    assembler: PromptAssembler | None = None,
    compressor: SummaryCompressor | None = None,
) -> AgentRequest:
    active_assembler = assembler or PromptAssembler()
    if compressor is not None:
        await compressor.compress_if_needed(session, session_id=session_id)

    context = active_assembler.assemble(
        user_input=user_input,
        profile=await _load_profile(session),
        weekly_plan=await _load_weekly_plan(session),
        daily_logs=await _load_recent_daily_logs(session),
        memories=await _load_memories(session),
        knowledge=await _load_knowledge(session),
        summaries=await _load_session_summaries(session, session_id),
        recent_messages=await _load_recent_messages(session, session_id),
    )
    return AgentRequest(
        messages=context.messages,
        debug={
            **context.debug,
            "source": "agent_orchestrator",
            "session_id": session_id,
        },
        model=(model_config or {}).get("model"),
    )


async def run_tool_calling_chat(
    *,
    session: AsyncSession,
    session_id: int,
    messages: list[dict[str, Any]],
    model: str,
    deepseek_client: Any,
    registry: ToolRegistry,
    max_tool_rounds: int = 4,
    slimmer: ToolResultSlimmer | None = None,
) -> ToolLoopResult:
    active_messages = list(messages)
    active_slimmer = slimmer or ToolResultSlimmer()
    tools = registry.to_deepseek_tools()

    for round_index in range(max_tool_rounds + 1):
        result: DeepSeekChatResult = await deepseek_client.request_chat_with_usage(
            messages=active_messages,
            model=model,
            tools=tools,
            tool_choice="auto",
            stream=False,
        )
        if not result.tool_calls:
            return ToolLoopResult(content=result.content, messages=active_messages, tool_rounds=round_index)

        if round_index >= max_tool_rounds:
            return ToolLoopResult(
                content="工具调用次数过多，请稍后重试或缩小问题范围。",
                messages=active_messages,
                tool_rounds=round_index,
            )

        active_messages.append(
            {
                "role": "assistant",
                "content": result.content,
                "tool_calls": result.tool_calls,
            }
        )
        for tool_call in result.tool_calls:
            tool_name, tool_arguments = _read_tool_call(tool_call)
            tool_call_id = str(tool_call.get("id") or tool_name)
            try:
                tool_result = await registry.execute(session, tool_name, tool_arguments)
                result_summary = active_slimmer.slim(tool_name, tool_result)
                status = "succeeded"
                error_message = None
            except Exception as exc:
                result_summary = json.dumps({"error": str(exc)}, ensure_ascii=False)
                status = "failed"
                error_message = str(exc)

            session.add(
                ToolCallLog(
                    session_id=session_id,
                    message_id=None,
                    tool_name=tool_name,
                    arguments_json=tool_arguments,
                    result_summary=result_summary,
                    status=status,
                    error_message=error_message,
                    created_at=utc_now(),
                )
            )
            active_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "name": tool_name,
                    "content": result_summary,
                }
            )
        await session.commit()

    return ToolLoopResult(
        content="工具调用次数过多，请稍后重试或缩小问题范围。",
        messages=active_messages,
        tool_rounds=max_tool_rounds,
    )


def _read_tool_call(tool_call: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    function = tool_call.get("function") if isinstance(tool_call, dict) else {}
    if not isinstance(function, dict):
        function = {}
    name = str(function.get("name") or "").strip()
    raw_arguments = function.get("arguments") or "{}"
    if not name:
        raise ValueError("工具调用缺少 function.name")
    if isinstance(raw_arguments, dict):
        return name, raw_arguments
    try:
        parsed = json.loads(raw_arguments)
    except json.JSONDecodeError as exc:
        raise ValueError("工具调用参数不是合法 JSON") from exc
    if not isinstance(parsed, dict):
        raise ValueError("工具调用参数必须是 JSON object")
    return name, parsed


async def _load_profile(session: AsyncSession) -> dict[str, Any] | None:
    profile = await session.get(Profile, DEFAULT_PROFILE_ID)
    if profile is None:
        return None
    return {
        "basic": profile.basic,
        "oneRm": profile.one_rm,
        "goal": profile.goal,
        "targetWeight": profile.target_weight,
        "notes": profile.notes,
    }


async def _load_weekly_plan(session: AsyncSession) -> dict[str, Any]:
    result = await session.execute(select(WeeklyPlanDay))
    days = {item.day_key: item for item in result.scalars().all()}
    return {
        day_key: {
            "type": days[day_key].type,
            "exercises": days[day_key].exercises,
        }
        for day_key in WEEKDAY_ORDER
        if day_key in days
    }


async def _load_recent_daily_logs(session: AsyncSession, limit: int = 7) -> dict[str, Any]:
    result = await session.execute(select(DailyLog).order_by(DailyLog.date.desc()).limit(limit))
    entries = list(result.scalars().all())
    return {
        entry.date: {
            "weight": entry.weight,
            "kcal": entry.kcal,
            "protein": entry.protein,
            "sleep": entry.sleep,
            "fatigue": entry.fatigue,
            "steps": entry.steps,
            "trainingDone": entry.training_done,
            "trainingNotes": entry.training_notes,
            "tdeeManual": entry.tdee_manual,
        }
        for entry in reversed(entries)
    }


async def _load_memories(session: AsyncSession, limit: int = 12) -> list[dict[str, Any]]:
    return [
        {
            "id": item.id,
            "kind": item.kind,
            "content": item.content,
            "confidence": item.confidence,
        }
        for item in await MemoryRetriever().retrieve(session, limit=limit)
    ]


async def _load_knowledge(session: AsyncSession, limit: int = 5) -> list[dict[str, Any]]:
    result = await session.execute(select(KnowledgeItem).order_by(KnowledgeItem.id.desc()).limit(limit))
    return [
        {
            "id": item.id,
            "kind": item.kind,
            "title": item.title,
            "content": item.content,
        }
        for item in result.scalars().all()
    ]


async def _load_session_summaries(
    session: AsyncSession,
    session_id: int,
    limit: int = 2,
) -> list[dict[str, Any]]:
    result = await session.execute(
        select(ChatSessionSummary)
        .where(ChatSessionSummary.session_id == session_id)
        .order_by(ChatSessionSummary.id.desc())
        .limit(limit)
    )
    return [
        {
            "id": item.id,
            "summary_text": item.summary_text,
            "token_estimate": item.token_estimate,
        }
        for item in reversed(result.scalars().all())
    ]


async def _load_recent_messages(
    session: AsyncSession,
    session_id: int,
    limit: int = 12,
) -> list[dict[str, Any]]:
    result = await session.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.id.desc())
        .limit(limit)
    )
    return [
        {
            "role": item.role,
            "content": item.content,
        }
        for item in reversed(result.scalars().all())
    ]
