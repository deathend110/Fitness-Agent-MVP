from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.active_plan import load_effective_weekly_plan
from backend.db.database import get_db_session
from backend.db.models import DailyLog, Profile
from backend.db.seed import DEFAULT_PROFILE_ID
from backend.metrics.daily_metrics import build_daily_metrics_summary

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/daily-summary")
async def get_daily_metrics_summary(
    date: str = Query(pattern=r"^\d{4}-\d{2}-\d{2}$"),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    profile = await _load_profile(session)
    weekly_plan = await _load_weekly_plan(session)
    daily_log = await _load_daily_log(session, date)
    return build_daily_metrics_summary(
        profile=profile,
        weekly_plan=weekly_plan,
        daily_log=daily_log,
        target_date=date,
    )


async def _load_profile(session: AsyncSession) -> dict[str, Any] | None:
    profile = await session.get(Profile, DEFAULT_PROFILE_ID)
    if profile is None:
        return None
    return {"basic": profile.basic, "oneRm": profile.one_rm}


async def _load_weekly_plan(session: AsyncSession) -> dict[str, Any]:
    return await load_effective_weekly_plan(session)


async def _load_daily_log(session: AsyncSession, target_date: str) -> dict[str, Any] | None:
    entry = await session.get(DailyLog, target_date)
    if entry is None:
        return None
    return {
        "kcal": entry.kcal,
        "protein": entry.protein,
        "sleep": entry.sleep,
        "fatigue": entry.fatigue,
        "steps": entry.steps,
        "tdeeManual": entry.tdee_manual,
    }
