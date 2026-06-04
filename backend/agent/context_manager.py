from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil
import json
from typing import Any
from collections.abc import Awaitable, Callable

from backend.agent.prompt_templates import build_stable_system_message
from backend.db.models import ChatMessage, ChatSessionSummary, utc_now
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class TokenBudgetConfig:
    max_context_tokens: int = 8000
    reserved_response_tokens: int = 1200
    warning_ratio: float = 0.70
    compression_trigger_ratio: float = 0.85
    hard_trim_ratio: float = 0.95

    @property
    def available_for_prompt(self) -> int:
        return max(1, self.max_context_tokens - self.reserved_response_tokens)


@dataclass(frozen=True)
class AgentContext:
    messages: list[dict[str, str]]
    debug: dict[str, Any]


@dataclass(frozen=True)
class CompressionResult:
    summary_created: bool
    summary_text: str
    recent_messages: list[dict[str, Any]]
    token_estimate: int
    failure_count: int = 0
    circuit_open: bool = False


@dataclass
class _ContextItem:
    section: str
    message: dict[str, str]
    required: bool = False
    priority: int = 100
    token_estimate: int = field(init=False)

    def __post_init__(self) -> None:
        self.token_estimate = estimate_message_tokens(self.message)


def estimate_text_tokens(text: str) -> int:
    return max(1, ceil(len(text) / 3))


def estimate_message_tokens(message: dict[str, str]) -> int:
    return estimate_text_tokens(message.get("role", "")) + estimate_text_tokens(message.get("content", ""))


def estimate_messages_tokens(messages: list[dict[str, str]]) -> int:
    return sum(estimate_message_tokens(message) for message in messages)


class StateReinjector:
    def build_state_messages(
        self,
        *,
        profile: dict[str, Any] | None = None,
        weekly_plan: dict[str, Any] | None = None,
        daily_logs: dict[str, Any] | None = None,
        pending_suggestion: dict[str, Any] | None = None,
        recent_files_summary: list[str] | None = None,
        tool_schema_version: str = "",
    ) -> list[dict[str, str]]:
        state = {
            "profile": profile or {},
            "weeklyPlan": weekly_plan or {},
            "dailyLogs": daily_logs or {},
            "pendingSuggestion": pending_suggestion or None,
            "recentFilesSummary": recent_files_summary or [],
            "toolSchemaVersion": tool_schema_version,
        }
        # 当前活动状态必须在摘要之外重新注入，避免长对话压缩后只剩旧摘要。
        return [{"role": "system", "content": "## 压缩后状态回注\n" + _compact_json(state)}]


class SummaryCompressor:
    def __init__(
        self,
        *,
        budget: TokenBudgetConfig | None = None,
        summarizer: Callable[[list[dict[str, Any]]], Awaitable[str] | str] | None = None,
        keep_recent_count: int = 6,
        failure_threshold: int = 3,
    ) -> None:
        self.budget = budget or TokenBudgetConfig()
        self.summarizer = summarizer or self._default_summarizer
        self.keep_recent_count = keep_recent_count
        self.failure_threshold = failure_threshold
        self._failure_counts: dict[int, int] = {}

    async def compress_if_needed(
        self,
        session: AsyncSession,
        *,
        session_id: int,
    ) -> CompressionResult:
        messages = await self._load_session_messages(session, session_id)
        recent_messages = messages[-self.keep_recent_count :]
        token_estimate = estimate_messages_tokens(
            [{"role": item["role"], "content": item["content"]} for item in messages]
        )

        if token_estimate < self._compression_trigger_tokens():
            return CompressionResult(
                summary_created=False,
                summary_text="",
                recent_messages=messages,
                token_estimate=token_estimate,
                failure_count=self._failure_counts.get(session_id, 0),
            )

        if self._failure_counts.get(session_id, 0) >= self.failure_threshold:
            return CompressionResult(
                summary_created=False,
                summary_text="",
                recent_messages=recent_messages,
                token_estimate=token_estimate,
                failure_count=self._failure_counts[session_id],
                circuit_open=True,
            )

        covered_messages = messages[: -self.keep_recent_count] if len(messages) > self.keep_recent_count else messages
        if not covered_messages:
            return CompressionResult(
                summary_created=False,
                summary_text="",
                recent_messages=recent_messages,
                token_estimate=token_estimate,
                failure_count=self._failure_counts.get(session_id, 0),
            )

        try:
            summary_text = await _maybe_await(self.summarizer(covered_messages))
        except Exception:
            failure_count = self._failure_counts.get(session_id, 0) + 1
            self._failure_counts[session_id] = failure_count
            return CompressionResult(
                summary_created=False,
                summary_text="",
                recent_messages=recent_messages,
                token_estimate=token_estimate,
                failure_count=failure_count,
                circuit_open=failure_count >= self.failure_threshold,
            )

        clean_summary = summary_text.strip()
        if not clean_summary:
            failure_count = self._failure_counts.get(session_id, 0) + 1
            self._failure_counts[session_id] = failure_count
            return CompressionResult(
                summary_created=False,
                summary_text="",
                recent_messages=recent_messages,
                token_estimate=token_estimate,
                failure_count=failure_count,
                circuit_open=failure_count >= self.failure_threshold,
            )

        now = utc_now()
        session.add(
            ChatSessionSummary(
                session_id=session_id,
                summary_text=clean_summary,
                covered_from_message_id=covered_messages[0]["id"],
                covered_to_message_id=covered_messages[-1]["id"],
                token_estimate=estimate_text_tokens(clean_summary),
                created_at=now,
                updated_at=now,
            )
        )
        await session.commit()
        self._failure_counts[session_id] = 0
        return CompressionResult(
            summary_created=True,
            summary_text=clean_summary,
            recent_messages=recent_messages,
            token_estimate=token_estimate,
            failure_count=0,
        )

    async def _load_session_messages(
        self,
        session: AsyncSession,
        session_id: int,
    ) -> list[dict[str, Any]]:
        result = await session.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at, ChatMessage.id)
        )
        return [
            {
                "id": item.id,
                "role": item.role,
                "content": item.content,
                "suggestion": item.suggestion,
                "created_at": item.created_at,
            }
            for item in result.scalars().all()
        ]

    def _compression_trigger_tokens(self) -> int:
        return int(self.budget.max_context_tokens * self.budget.compression_trigger_ratio)

    def _default_summarizer(self, messages: list[dict[str, Any]]) -> str:
        joined = "\n".join(f"{item['role']}: {item['content']}" for item in messages[-12:])
        return "\n".join(
            [
                "训练目标: 从历史对话中保留明确目标，未知则标记待确认。",
                "伤病/疼痛限制: 仅保留用户明确提到的疼痛/疾病/限制，不把单日疲劳升级为长期伤病。",
                "用户偏好: 保留训练时间、器械、饮食禁忌等稳定偏好。",
                "已采纳建议: 保留已确认写回的计划调整。",
                "被拒绝建议: 保留用户明确拒绝的方向。",
                "待确认事项: 保留未确认建议卡和需要追问的问题。",
                "当前周期/当前计划: 保留当前训练周期和关键计划线索。",
                f"历史摘录: {joined[:1200]}",
            ]
        )


class PromptAssembler:
    def __init__(self, budget: TokenBudgetConfig | None = None) -> None:
        self.budget = budget or TokenBudgetConfig()

    def assemble(
        self,
        *,
        user_input: str,
        profile: dict[str, Any] | None = None,
        weekly_plan: dict[str, Any] | None = None,
        daily_logs: dict[str, Any] | None = None,
        recent_files_summary: list[dict[str, Any]] | None = None,
        memories: list[dict[str, Any]] | None = None,
        knowledge: list[dict[str, Any]] | None = None,
        summaries: list[dict[str, Any]] | None = None,
        recent_messages: list[dict[str, Any]] | None = None,
    ) -> AgentContext:
        items = self._build_items(
            user_input=user_input,
            profile=profile,
            weekly_plan=weekly_plan,
            daily_logs=daily_logs,
            recent_files_summary=recent_files_summary or [],
            memories=memories or [],
            knowledge=knowledge or [],
            summaries=summaries or [],
            recent_messages=recent_messages or [],
        )
        messages, trimmed = self._fit_budget(items)
        selected_sections = [item.section for item in items if item.message in messages]

        return AgentContext(
            messages=messages,
            debug={
                "selected_sections": selected_sections,
                "estimated_prompt_tokens": estimate_messages_tokens(messages),
                "token_budget": {
                    "max_context_tokens": self.budget.max_context_tokens,
                    "reserved_response_tokens": self.budget.reserved_response_tokens,
                    "available_for_prompt": self.budget.available_for_prompt,
                    "warning_tokens": int(self.budget.max_context_tokens * self.budget.warning_ratio),
                    "compression_trigger_tokens": int(
                        self.budget.max_context_tokens * self.budget.compression_trigger_ratio
                    ),
                    "hard_trim_tokens": int(self.budget.max_context_tokens * self.budget.hard_trim_ratio),
                },
                "trimmed_items": trimmed,
            },
        )

    def _build_items(
        self,
        *,
        user_input: str,
        profile: dict[str, Any] | None,
        weekly_plan: dict[str, Any] | None,
        daily_logs: dict[str, Any] | None,
        recent_files_summary: list[dict[str, Any]],
        memories: list[dict[str, Any]],
        knowledge: list[dict[str, Any]],
        summaries: list[dict[str, Any]],
        recent_messages: list[dict[str, Any]],
    ) -> list[_ContextItem]:
        items: list[_ContextItem] = [
            _ContextItem(
                "stable_system_prompt",
                build_stable_system_message(),
                required=True,
                priority=0,
            )
        ]

        state_content = self._format_current_state(profile, weekly_plan)
        if state_content:
            items.append(
                _ContextItem(
                    "current_state",
                    {"role": "system", "content": state_content},
                    required=True,
                    priority=10,
                )
            )

        safety_memories = [item for item in memories if item.get("kind") == "safety"]
        normal_memories = [item for item in memories if item.get("kind") != "safety"]
        if safety_memories:
            items.append(
                _ContextItem(
                    "safety_memory",
                    {"role": "system", "content": self._format_memory("## 安全限制", safety_memories)},
                    required=True,
                    priority=20,
                )
            )
        if normal_memories:
            items.append(
                _ContextItem(
                    "relevant_memory",
                    {"role": "system", "content": self._format_memory("## 相关记忆", normal_memories)},
                    priority=30,
                )
            )
        if knowledge:
            items.append(
                _ContextItem(
                    "knowledge",
                    {"role": "system", "content": self._format_collection("## 相关知识", knowledge)},
                    priority=40,
                )
            )
        if recent_files_summary:
            items.append(
                _ContextItem(
                    "uploaded_files",
                    {"role": "system", "content": self._format_collection("## 上传文件摘要", recent_files_summary)},
                    priority=42,
                )
            )
        for summary in summaries[-2:]:
            text = str(summary.get("summary_text") or summary.get("content") or "").strip()
            if text:
                items.append(
                    _ContextItem(
                        "session_summary",
                        {"role": "system", "content": f"## 会话摘要\n{text}"},
                        priority=50,
                    )
                )
        # daily_logs 按日变化，排在所有相对稳定块之后、每轮易变的近期消息之前，避免每天失效整段前缀缓存。
        daily_state_content = self._format_daily_state(daily_logs)
        if daily_state_content:
            items.append(
                _ContextItem(
                    "daily_state",
                    {"role": "system", "content": daily_state_content},
                    required=True,
                    priority=60,
                )
            )
        for message in recent_messages[-12:]:
            role = str(message.get("role", "")).strip()
            content = str(message.get("content", "")).strip()
            if role in {"user", "assistant"} and content:
                items.append(
                    _ContextItem(
                        "recent_message",
                        {"role": role, "content": content},
                        priority=70,
                    )
                )

        items.append(
            _ContextItem(
                "current_user_input",
                {"role": "user", "content": user_input.strip()},
                required=True,
                priority=90,
            )
        )
        return items

    def _fit_budget(self, items: list[_ContextItem]) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
        selected: list[_ContextItem] = []
        trimmed: list[dict[str, Any]] = []
        used_tokens = 0
        available = self.budget.available_for_prompt

        for item in items:
            next_total = used_tokens + item.token_estimate
            if item.required or next_total <= available:
                selected.append(item)
                used_tokens += item.token_estimate
                continue

            trimmed.append(
                {
                    "section": item.section,
                    "reason": "token_budget_exceeded",
                    "estimated_tokens": item.token_estimate,
                }
            )

        while estimate_messages_tokens([item.message for item in selected]) > available and selected:
            removable_index = next(
                (index for index in range(len(selected) - 1, -1, -1) if not selected[index].required),
                None,
            )
            if removable_index is None:
                break
            removed = selected.pop(removable_index)
            trimmed.append(
                {
                    "section": removed.section,
                    "reason": "hard_trim",
                    "estimated_tokens": removed.token_estimate,
                }
            )

        return [item.message for item in selected], trimmed

    def _format_current_state(
        self,
        profile: dict[str, Any] | None,
        weekly_plan: dict[str, Any] | None,
    ) -> str:
        # 只保留变化不频繁的档案与周计划，让这段留在稳定前缀里，利于命中前缀缓存。
        sections: list[str] = []
        if profile:
            sections.append(f"档案: {_compact_json(profile)}")
        if weekly_plan:
            sections.append(f"本周计划: {_compact_json(weekly_plan)}")
        if not sections:
            return ""
        return "## 当前用户状态\n" + "\n".join(sections)

    def _format_daily_state(self, daily_logs: dict[str, Any] | None) -> str:
        # daily_logs 按日期分键、每天都会变；单独成段并排到稳定前缀之后，避免每天失效整段缓存。
        if not daily_logs:
            return ""
        return "## 今日/近期日志\n" + _compact_json(daily_logs)

    def _format_memory(self, title: str, memories: list[dict[str, Any]]) -> str:
        lines = [
            f"- [{item.get('kind', 'memory')}] {item.get('content', '')}"
            for item in memories
            if str(item.get("content", "")).strip()
        ]
        return f"{title}\n" + "\n".join(lines)

    def _format_collection(self, title: str, items: list[dict[str, Any]]) -> str:
        return f"{title}\n{_compact_json(items)}"


def _compact_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)


async def _maybe_await(value: Awaitable[str] | str) -> str:
    if hasattr(value, "__await__"):
        return await value  # type: ignore[misc]
    return value
