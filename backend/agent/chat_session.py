from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.context_manager import AgentContext, PromptAssembler, SummaryCompressor
from backend.agent.tool_loop import ToolLoopOrchestrator, ToolLoopResult
from backend.agent.deepseek_client import DeepSeekChatResult
from backend.agent.memory import MemoryRetriever
from backend.agent.tool_calling import ToolRegistry, ToolResultSlimmer
from backend.providers.gemini_client import GeminiNativeClient
from backend.providers.gemini_native import GeminiNativeProvider
from backend.providers.openai_compatible import OpenAICompatibleProvider
from backend.db.models import (
    ChatMessage,
    ChatSessionSummary,
    DailyLog,
    KnowledgeItem,
    MemoryItem,
    Profile,
    UploadedFile,
    WEEKDAY_ORDER,
    WeeklyPlanDay,
)
from backend.db.seed import DEFAULT_PROFILE_ID


@dataclass(frozen=True)
class AgentRequest:
    messages: list[dict[str, str]]
    debug: dict[str, Any]
    model: str | None = None


async def build_agent_request(
    *,
    session: AsyncSession,
    session_id: int,
    user_input: str,
    file_ids: list[int] | None = None,
    model_config: dict[str, Any] | None = None,
    assembler: PromptAssembler | None = None,
    compressor: SummaryCompressor | None = None,
) -> AgentRequest:
    active_assembler = assembler or PromptAssembler()
    if compressor is not None:
        await compressor.compress_if_needed(session, session_id=session_id)

    file_context = await _load_selected_file_summaries(session, file_ids or [])
    context = active_assembler.assemble(
        user_input=user_input,
        profile=await _load_profile(session),
        weekly_plan=await _load_weekly_plan(session),
        daily_logs=await _load_recent_daily_logs(session),
        recent_files_summary=file_context["summaries"],
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
            "selected_files": file_context["selected_files"],
            "missing_files": file_context["missing_files"],
            "trimmed_file_summaries": file_context["trimmed_file_summaries"],
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
    thinking: dict[str, Any] | None = None,
    reasoning_effort: str | None = None,
    max_tool_rounds: int = 4,
    slimmer: ToolResultSlimmer | None = None,
) -> ToolLoopResult:
    provider = _build_tool_loop_provider(deepseek_client)
    orchestrator = ToolLoopOrchestrator(
        registry=registry,
        max_rounds=max_tool_rounds,
        slimmer=slimmer,
    )
    return await orchestrator.run(
        session=session,
        session_id=session_id,
        provider=provider,
        messages=messages,
        model=model,
        thinking=thinking,
        reasoning_effort=reasoning_effort,
        tool_choice=None if thinking and thinking.get("type") == "enabled" else "auto",
    )


def _build_tool_loop_provider(client: Any) -> Any:
    if isinstance(client, GeminiNativeClient):
        return _GeminiToolLoopProvider(client=client)
    return _DeepSeekToolLoopProvider(client=client)


class _DeepSeekToolLoopProvider(OpenAICompatibleProvider):
    """把现有 DeepSeekClient 包装成统一 provider 接口，供新工具循环复用。"""

    def __init__(self, *, client: Any) -> None:
        super().__init__(client_factory=None)
        self.client = client

    async def generate_chat(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        tools: list[dict[str, Any]],
        tool_choice: str | dict[str, Any] | None = None,
        thinking: dict[str, Any] | None = None,
        reasoning_effort: str | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        result: DeepSeekChatResult = await self.client.request_chat_with_usage(
            messages=messages,
            model=model,
            tools=tools,
            tool_choice=tool_choice,
            stream=False,
            thinking=thinking,
            reasoning_effort=reasoning_effort,
        )
        raw_payload = {
            "choices": [
                {
                    "message": {
                        "content": result.content,
                        "tool_calls": result.tool_calls or [],
                    }
                }
            ]
        }
        if result.reasoning_content:
            raw_payload["choices"][0]["message"]["reasoning_content"] = result.reasoning_content
        return {
            "text": result.content,
            "toolCalls": result.tool_calls or [],
            "raw": raw_payload,
        }


class _GeminiToolLoopProvider(GeminiNativeProvider):
    """把 Gemini 原生 REST client 接到统一工具回环里。"""

    def __init__(self, *, client: GeminiNativeClient) -> None:
        super().__init__(client_factory=None)
        self.client = client

    async def generate_chat(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        tools: dict[str, Any],
        tool_choice: str | dict[str, Any] | None = None,
        thinking: dict[str, Any] | None = None,
        reasoning_effort: str | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        raw_payload = await self.client.generate_content_raw(
            messages=messages,
            model=model,
            thinking=thinking,
            tools=tools,
            tool_choice=tool_choice,
            reasoning_effort=reasoning_effort,
        )
        return {
            "text": self.client._read_text_content(raw_payload),
            "toolCalls": self.normalize_tool_call_response(raw_payload),
            "raw": raw_payload,
        }



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


async def _load_selected_file_summaries(session: AsyncSession, file_ids: list[int]) -> dict[str, Any]:
    if not file_ids:
        return {"summaries": [], "selected_files": [], "missing_files": [], "trimmed_file_summaries": []}

    unique_ids = list(dict.fromkeys(int(file_id) for file_id in file_ids if int(file_id) > 0))
    if not unique_ids:
        return {"summaries": [], "selected_files": [], "missing_files": [], "trimmed_file_summaries": []}

    result = await session.execute(select(UploadedFile).where(UploadedFile.id.in_(unique_ids)))
    files_by_id = {item.id: item for item in result.scalars().all()}
    summaries: list[dict[str, Any]] = []
    trimmed: list[int] = []

    for file_id in unique_ids:
        uploaded = files_by_id.get(file_id)
        if uploaded is None:
            continue
        summary = uploaded.summary or {}
        text = str(summary.get("summary") or summary.get("text") or "").strip()
        if len(text) > 800:
            text = text[:800] + "...[trimmed:file_summary]"
            trimmed.append(file_id)
        summaries.append(
            {
                "fileId": uploaded.id,
                "name": uploaded.original_name,
                "kind": summary.get("kind") or uploaded.extension.lstrip("."),
                "status": uploaded.parser_status,
                "summary": text,
            }
        )

    return {
        "summaries": summaries,
        "selected_files": [item["fileId"] for item in summaries],
        "missing_files": [file_id for file_id in unique_ids if file_id not in files_by_id],
        "trimmed_file_summaries": trimmed,
    }


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
