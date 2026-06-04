from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import ActiveCyclePlan, CycleWeekSnapshot, PlanSourceState
from backend.db.seed import DEFAULT_PLAN_SOURCE_STATE_ID
from backend.plans.custom_strength_definition import normalize_custom_strength_definition
from backend.plans.custom_strength_engine import build_custom_strength_cycle_weeks
from backend.plans.cycle_engine import build_cycle_week_plan, merge_cycle_week_override
from backend.plans.preset_library import list_cycle_presets
from backend.schemas import (
    ActiveCycleDetailSchema,
    ActiveCyclePlanSchema,
    CycleCreateRequestSchema,
    CyclePresetSchema,
    CycleWeekSnapshotSchema,
    PlanSourceSchema,
)


async def get_or_create_plan_source_state(session: AsyncSession) -> PlanSourceState:
    state = await session.get(PlanSourceState, DEFAULT_PLAN_SOURCE_STATE_ID)
    if state is None:
        state = PlanSourceState(id=DEFAULT_PLAN_SOURCE_STATE_ID, active_source="manual")
        session.add(state)
        await session.flush()
    return state


async def get_plan_source(session: AsyncSession) -> PlanSourceSchema:
    state = await get_or_create_plan_source_state(session)
    return PlanSourceSchema(activeSource=state.active_source, updatedAt=state.updated_at)


async def set_plan_source(session: AsyncSession, active_source: str) -> PlanSourceSchema:
    state = await get_or_create_plan_source_state(session)
    state.active_source = active_source
    await session.commit()
    await session.refresh(state)
    return PlanSourceSchema(activeSource=state.active_source, updatedAt=state.updated_at)


def list_presets() -> list[CyclePresetSchema]:
    return list_cycle_presets()


async def create_active_cycle(
    session: AsyncSession,
    payload: CycleCreateRequestSchema,
) -> ActiveCycleDetailSchema:
    existing_cycle = await _get_open_cycle(session)
    if existing_cycle is not None:
        raise ValueError("当前存在未结束的活动周期，请先结束后再创建新周期。")

    cycle_seed = _build_cycle_creation_seed(payload)
    cycle = ActiveCyclePlan(
        preset_key=cycle_seed["preset_key"],
        status="active",
        start_date=cycle_seed["start_date"],
        current_week_index=1,
        pending_week_index=None,
        goal=cycle_seed["goal"],
        base_lifts=cycle_seed["base_lifts"],
        config=cycle_seed["config"],
    )
    session.add(cycle)
    await session.flush()

    for week_index, generated_plan in enumerate(cycle_seed["compiled_weeks"], start=1):
        week_start, week_end = _build_week_bounds(cycle_seed["start_date"], week_index)
        session.add(
            CycleWeekSnapshot(
                cycle_id=cycle.id,
                week_index=week_index,
                generated_plan=generated_plan,
                override_plan=None,
                is_confirmed=week_index == 1,
                week_start=week_start,
                week_end=week_end,
            )
        )

    source_state = await get_or_create_plan_source_state(session)
    source_state.active_source = "cycle"
    first_snapshot = await session.get(CycleWeekSnapshot, {"cycle_id": cycle.id, "week_index": 1})
    cycle.last_confirmed_at = first_snapshot.updated_at if first_snapshot is not None else None
    await session.commit()
    await session.refresh(cycle)
    await session.refresh(source_state)
    if first_snapshot is None:
        raise ValueError("当前周快照创建失败。")
    await session.refresh(first_snapshot)
    return build_active_cycle_detail(cycle, first_snapshot)


async def load_active_cycle_detail(session: AsyncSession) -> ActiveCycleDetailSchema | None:
    cycle = await _get_open_cycle(session)
    if cycle is None:
        return None
    snapshot = await session.get(
        CycleWeekSnapshot,
        {"cycle_id": cycle.id, "week_index": cycle.current_week_index},
    )
    if snapshot is None:
        return None
    return build_active_cycle_detail(cycle, snapshot)


async def generate_next_week(session: AsyncSession, cycle_id: int) -> CycleWeekSnapshotSchema:
    cycle = await _get_cycle_or_raise(session, cycle_id)
    next_week_index = cycle.pending_week_index or (cycle.current_week_index + 1)
    existing_snapshot = await session.get(
        CycleWeekSnapshot,
        {"cycle_id": cycle.id, "week_index": next_week_index},
    )
    if existing_snapshot is not None:
        cycle.pending_week_index = next_week_index
        await session.commit()
        await session.refresh(cycle)
        return build_cycle_week_snapshot_schema(existing_snapshot)

    generated_plan = build_cycle_week_plan(
        preset_key=cycle.preset_key,
        week_index=next_week_index,
        base_lifts=cycle.base_lifts,
        config=cycle.config,
    )
    week_start, week_end = _build_week_bounds(cycle.start_date, next_week_index)
    snapshot = CycleWeekSnapshot(
        cycle_id=cycle.id,
        week_index=next_week_index,
        generated_plan=generated_plan,
        override_plan=None,
        is_confirmed=False,
        week_start=week_start,
        week_end=week_end,
    )
    session.add(snapshot)
    cycle.pending_week_index = next_week_index
    await session.commit()
    await session.refresh(snapshot)
    await session.refresh(cycle)
    return build_cycle_week_snapshot_schema(snapshot)


async def confirm_next_week(session: AsyncSession, cycle_id: int) -> ActiveCycleDetailSchema:
    cycle = await _get_cycle_or_raise(session, cycle_id)
    if cycle.pending_week_index is None:
        snapshot_schema = await generate_next_week(session, cycle_id)
        pending_week_index = snapshot_schema.weekIndex
    else:
        pending_week_index = cycle.pending_week_index

    snapshot = await session.get(
        CycleWeekSnapshot,
        {"cycle_id": cycle.id, "week_index": pending_week_index},
    )
    if snapshot is None:
        raise ValueError("待确认周不存在。")

    snapshot.is_confirmed = True
    cycle.current_week_index = pending_week_index
    cycle.pending_week_index = None
    cycle.last_confirmed_at = snapshot.updated_at
    await session.commit()
    await session.refresh(cycle)
    await session.refresh(snapshot)
    return build_active_cycle_detail(cycle, snapshot)


async def save_week_override(
    session: AsyncSession,
    cycle_id: int,
    week_index: int,
    override_plan: dict[str, Any] | None,
) -> CycleWeekSnapshotSchema:
    await _get_cycle_or_raise(session, cycle_id)
    snapshot = await session.get(CycleWeekSnapshot, {"cycle_id": cycle_id, "week_index": week_index})
    if snapshot is None:
        raise ValueError("目标周不存在。")
    snapshot.override_plan = override_plan
    await session.commit()
    await session.refresh(snapshot)
    return build_cycle_week_snapshot_schema(snapshot)


async def stop_cycle(session: AsyncSession, cycle_id: int) -> ActiveCycleDetailSchema:
    cycle = await _get_cycle_or_raise(session, cycle_id)
    cycle.status = "completed"
    source_state = await get_or_create_plan_source_state(session)
    source_state.active_source = "manual"
    await session.commit()
    await session.refresh(cycle)
    snapshot = await session.get(
        CycleWeekSnapshot,
        {"cycle_id": cycle.id, "week_index": cycle.current_week_index},
    )
    if snapshot is None:
        raise ValueError("当前周快照不存在。")
    return build_active_cycle_detail(cycle, snapshot)


def build_active_cycle_detail(cycle: ActiveCyclePlan, snapshot: CycleWeekSnapshot) -> ActiveCycleDetailSchema:
    effective_plan = merge_cycle_week_override(snapshot.generated_plan, snapshot.override_plan)
    return ActiveCycleDetailSchema(
        cycle=build_active_cycle_plan_schema(cycle),
        currentWeek=build_cycle_week_snapshot_schema(snapshot),
        effectivePlan=effective_plan,
    )


def build_active_cycle_plan_schema(cycle: ActiveCyclePlan) -> ActiveCyclePlanSchema:
    return ActiveCyclePlanSchema(
        id=cycle.id,
        presetKey=cycle.preset_key,
        status=cycle.status,
        startDate=cycle.start_date,
        currentWeekIndex=cycle.current_week_index,
        pendingWeekIndex=cycle.pending_week_index,
        goal=cycle.goal,
        baseLifts=cycle.base_lifts,
        config=cycle.config,
        lastGeneratedAt=cycle.last_generated_at,
        lastConfirmedAt=cycle.last_confirmed_at,
        createdAt=cycle.created_at,
        updatedAt=cycle.updated_at,
    )


def build_cycle_week_snapshot_schema(snapshot: CycleWeekSnapshot) -> CycleWeekSnapshotSchema:
    effective_plan = merge_cycle_week_override(snapshot.generated_plan, snapshot.override_plan)
    return CycleWeekSnapshotSchema(
        cycleId=snapshot.cycle_id,
        weekIndex=snapshot.week_index,
        generatedPlan=snapshot.generated_plan,
        overridePlan=snapshot.override_plan,
        effectivePlan=effective_plan,
        isConfirmed=snapshot.is_confirmed,
        weekStart=snapshot.week_start,
        weekEnd=snapshot.week_end,
        createdAt=snapshot.created_at,
        updatedAt=snapshot.updated_at,
    )


async def _get_open_cycle(session: AsyncSession) -> ActiveCyclePlan | None:
    result = await session.execute(
        select(ActiveCyclePlan)
        .where(ActiveCyclePlan.status.in_(("draft", "active")))
        .order_by(ActiveCyclePlan.id.desc())
    )
    return result.scalars().first()


async def _get_cycle_or_raise(session: AsyncSession, cycle_id: int) -> ActiveCyclePlan:
    cycle = await session.get(ActiveCyclePlan, cycle_id)
    if cycle is None:
        raise ValueError("活动周期不存在。")
    return cycle


def _build_cycle_creation_seed(payload: CycleCreateRequestSchema) -> dict[str, Any]:
    if payload.presetKey == "custom_strength":
        return _build_custom_strength_cycle_seed(payload)

    generated_plan = build_cycle_week_plan(
        preset_key=payload.presetKey,
        week_index=1,
        base_lifts=payload.baseLifts,
        config=payload.config,
    )
    return {
        "preset_key": payload.presetKey,
        "start_date": payload.startDate,
        "goal": payload.goal,
        "base_lifts": payload.baseLifts,
        "config": payload.config,
        "compiled_weeks": [generated_plan],
    }


def _build_custom_strength_cycle_seed(payload: CycleCreateRequestSchema) -> dict[str, Any]:
    # 自定义力量创建链路需要在 service 层完成归一化和编译，这样 API contract 仍保持显式且下游无需理解来源差异。
    definition = normalize_custom_strength_definition(payload.config)
    compiled_weeks = build_custom_strength_cycle_weeks(definition)
    if not compiled_weeks:
        raise ValueError("自定义力量周期至少需要 1 周计划。")
    return {
        "preset_key": "custom_strength",
        "start_date": definition["startDate"],
        "goal": payload.goal,
        "base_lifts": definition["mainLifts"],
        "config": definition,
        "compiled_weeks": compiled_weeks,
    }


def _build_week_bounds(start_date: str, week_index: int) -> tuple[str, str]:
    start = date.fromisoformat(start_date) + timedelta(days=(week_index - 1) * 7)
    end = start + timedelta(days=6)
    return start.isoformat(), end.isoformat()
