from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import ActiveCyclePlan, CycleWeekSnapshot, PlanSourceState, WEEKDAY_ORDER, WeeklyPlanDay
from backend.db.seed import DEFAULT_PLAN_SOURCE_STATE_ID
from backend.plans.cycle_engine import merge_cycle_week_override


async def load_effective_weekly_plan(session: AsyncSession) -> dict[str, Any]:
    source_state = await session.get(PlanSourceState, DEFAULT_PLAN_SOURCE_STATE_ID)
    if source_state is not None and source_state.active_source == "cycle":
        cycle_context = await load_active_cycle_context(session)
        if cycle_context is not None:
            return cycle_context["effectivePlan"]
    return await _load_manual_weekly_plan(session)


async def load_active_cycle_context(session: AsyncSession) -> dict[str, Any] | None:
    cycle = await _load_open_cycle(session)
    if cycle is None:
        return None
    snapshot = await session.get(
        CycleWeekSnapshot,
        {"cycle_id": cycle.id, "week_index": cycle.current_week_index},
    )
    if snapshot is None:
        return None
    return {
        "cycle": cycle,
        "snapshot": snapshot,
        "effectivePlan": merge_cycle_week_override(snapshot.generated_plan, snapshot.override_plan),
    }


async def _load_open_cycle(session: AsyncSession) -> ActiveCyclePlan | None:
    result = await session.execute(
        select(ActiveCyclePlan)
        .where(ActiveCyclePlan.status.in_(("draft", "active")))
        .order_by(ActiveCyclePlan.id.desc())
    )
    return result.scalars().first()


async def _load_manual_weekly_plan(session: AsyncSession) -> dict[str, Any]:
    result = await session.execute(select(WeeklyPlanDay))
    days = {item.day_key: item for item in result.scalars().all()}
    return {
        day_key: {
            "type": days[day_key].type if day_key in days else "rest",
            "exercises": days[day_key].exercises if day_key in days else [],
        }
        for day_key in WEEKDAY_ORDER
    }
