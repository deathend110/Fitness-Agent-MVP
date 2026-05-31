from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil
import json
from typing import Any

from backend.agent.prompt_templates import build_stable_system_message


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

        state_content = self._format_current_state(profile, weekly_plan, daily_logs)
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
        daily_logs: dict[str, Any] | None,
    ) -> str:
        sections: list[str] = []
        if profile:
            sections.append(f"档案: {_compact_json(profile)}")
        if weekly_plan:
            sections.append(f"本周计划: {_compact_json(weekly_plan)}")
        if daily_logs:
            sections.append(f"今日日志/最近日志: {_compact_json(daily_logs)}")
        if not sections:
            return ""
        return "## 当前用户状态\n" + "\n".join(sections)

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
