from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import UsageRecord


USAGE_FIELDS = (
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "prompt_cache_hit_tokens",
    "prompt_cache_miss_tokens",
)


def normalize_usage(usage: dict[str, Any] | None) -> dict[str, int]:
    payload = usage or {}
    normalized = {field: _to_non_negative_int(payload.get(field)) for field in USAGE_FIELDS}
    if normalized["total_tokens"] == 0:
        normalized["total_tokens"] = normalized["prompt_tokens"] + normalized["completion_tokens"]
    return normalized


async def record_usage(
    session: AsyncSession,
    *,
    session_id: int,
    message_id: int | None,
    model: str,
    usage: dict[str, Any] | None,
) -> UsageRecord:
    normalized = normalize_usage(usage)
    # DeepSeek Context Caching 默认可用；记录 hit/miss 是为了判断稳定 prompt 前缀是否真的被缓存复用。
    record = UsageRecord(
        session_id=session_id,
        message_id=message_id,
        model=model,
        prompt_tokens=normalized["prompt_tokens"],
        completion_tokens=normalized["completion_tokens"],
        total_tokens=normalized["total_tokens"],
        prompt_cache_hit_tokens=normalized["prompt_cache_hit_tokens"],
        prompt_cache_miss_tokens=normalized["prompt_cache_miss_tokens"],
    )
    session.add(record)
    return record


async def summarize_session_usage(session: AsyncSession, session_id: int) -> dict[str, Any]:
    result = await session.execute(select(UsageRecord).where(UsageRecord.session_id == session_id))
    records = result.scalars().all()
    summary = {
        "prompt_tokens": sum(record.prompt_tokens for record in records),
        "completion_tokens": sum(record.completion_tokens for record in records),
        "total_tokens": sum(record.total_tokens for record in records),
        "prompt_cache_hit_tokens": sum(record.prompt_cache_hit_tokens for record in records),
        "prompt_cache_miss_tokens": sum(record.prompt_cache_miss_tokens for record in records),
    }
    cache_total = summary["prompt_cache_hit_tokens"] + summary["prompt_cache_miss_tokens"]
    summary["cache_hit_rate"] = (
        summary["prompt_cache_hit_tokens"] / cache_total
        if cache_total > 0
        else 0.0
    )
    return summary


def _to_non_negative_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int | float):
        return max(0, int(value))
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return 0
