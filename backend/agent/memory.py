from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import MemoryItem, utc_now


@dataclass(frozen=True)
class MemoryCandidate:
    kind: str
    content: str
    confidence: float
    source_message_id: int | None = None
    reason: str = ""

    @property
    def requires_confirmation(self) -> bool:
        return self.confidence < 0.8

    def model_dump(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "content": self.content,
            "confidence": self.confidence,
            "sourceMessageId": self.source_message_id,
            "reason": self.reason,
            "requiresConfirmation": self.requires_confirmation,
        }


def extract_memory_candidates(content: str, *, source_message_id: int | None = None) -> list[MemoryCandidate]:
    text = content.strip()
    candidates: list[MemoryCandidate] = []
    if not text or _is_single_day_state(text):
        return []

    if "膝盖" in text and ("疼" in text or "痛" in text):
        candidates.append(
            MemoryCandidate(
                kind="safety",
                content="用户膝盖深蹲到底部会疼。" if "深蹲" in text else "用户膝盖训练时会疼。",
                confidence=0.95,
                source_message_id=source_message_id,
                reason="用户明确提到疼痛或伤病限制",
            )
        )
    if "只有" in text and ("哑铃" in text or "弹力带" in text):
        candidates.append(
            MemoryCandidate(
                kind="equipment",
                content="用户家里只有哑铃和弹力带。",
                confidence=0.9,
                source_message_id=source_message_id,
                reason="用户明确说明可用器械",
            )
        )
    if "目标是" in text:
        goal = text.split("目标是", 1)[1].split("；", 1)[0].split("。", 1)[0].strip()
        if goal:
            candidates.append(
                MemoryCandidate(
                    kind="goal",
                    content=f"用户目标是{goal}。",
                    confidence=0.9,
                    source_message_id=source_message_id,
                    reason="用户明确说明训练目标",
                )
            )
    if "只能晚上训练" in text or "只能晚训" in text:
        candidates.append(
            MemoryCandidate(
                kind="schedule",
                content="用户只能晚上训练。",
                confidence=0.9,
                source_message_id=source_message_id,
                reason="用户明确说明训练时间限制",
            )
        )
    elif "可能" in text and "太晚练" in text:
        candidates.append(
            MemoryCandidate(
                kind="preference",
                content="用户可能不太适合太晚训练。",
                confidence=0.55,
                source_message_id=source_message_id,
                reason="表达含糊，需要用户确认",
            )
        )
    if "不吃乳制品" in text or "不喝牛奶" in text:
        candidates.append(
            MemoryCandidate(
                kind="nutrition",
                content="用户不吃乳制品。",
                confidence=0.9,
                source_message_id=source_message_id,
                reason="用户明确说明饮食禁忌",
            )
        )

    return candidates


class MemoryRetriever:
    async def retrieve(
        self,
        session: AsyncSession,
        *,
        kind: str | None = None,
        query: str | None = None,
        limit: int = 8,
        update_last_used: bool = True,
    ) -> list[MemoryItem]:
        statement = select(MemoryItem)
        if kind:
            statement = statement.where(MemoryItem.kind == kind)

        result = await session.execute(statement)
        items = list(result.scalars().all())
        tokens = _query_tokens(query)
        if tokens:
            items = [
                item
                for item in items
                if any(token in item.content.lower() or token in item.kind.lower() for token in tokens)
            ]

        items.sort(
            key=lambda item: (
                0 if item.kind == "safety" else 1,
                -(item.last_used_at.timestamp() if item.last_used_at else 0),
                -item.id,
            )
        )
        selected = items[:limit]
        if update_last_used and selected:
            now = utc_now()
            for item in selected:
                item.last_used_at = now
            await session.flush()
        return selected


def _is_single_day_state(text: str) -> bool:
    return ("今天" in text or "昨晚" in text) and any(keyword in text for keyword in ("累", "睡得", "睡眠"))


def _query_tokens(query: str | None) -> list[str]:
    if not query:
        return []
    return [token.strip().lower() for token in query.replace("，", " ").split() if token.strip()]
