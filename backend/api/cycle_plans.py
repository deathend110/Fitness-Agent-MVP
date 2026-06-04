from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db_session
from backend.plans.cycle_service import (
    create_active_cycle,
    generate_next_week,
    get_plan_source,
    list_presets,
    load_active_cycle_detail,
    save_week_override,
    set_plan_source,
    stop_cycle,
    confirm_next_week,
)
from backend.schemas import (
    ActiveCycleDetailSchema,
    CycleCreateRequestSchema,
    CyclePresetSchema,
    CycleWeekSnapshotSchema,
    PlanSourceSchema,
)

router = APIRouter(tags=["cycle-plans"])


@router.get("/api/plan-source", response_model=PlanSourceSchema, response_model_by_alias=True)
async def get_plan_source_state(session: AsyncSession = Depends(get_db_session)) -> PlanSourceSchema:
    return await get_plan_source(session)


@router.put("/api/plan-source", response_model=PlanSourceSchema, response_model_by_alias=True)
async def put_plan_source_state(
    payload: PlanSourceSchema,
    session: AsyncSession = Depends(get_db_session),
) -> PlanSourceSchema:
    return await set_plan_source(session, payload.activeSource)


@router.get("/api/cycles/presets", response_model=list[CyclePresetSchema], response_model_by_alias=True)
async def get_cycle_presets() -> list[CyclePresetSchema]:
    return list_presets()


@router.post("/api/cycles", response_model=ActiveCycleDetailSchema, response_model_by_alias=True)
async def post_cycle(
    payload: CycleCreateRequestSchema,
    session: AsyncSession = Depends(get_db_session),
) -> ActiveCycleDetailSchema:
    try:
        return await create_active_cycle(session, payload)
    except Exception as exc:  # pragma: no cover - 交给 API 层转成可读错误
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/cycles/active", response_model=ActiveCycleDetailSchema | None, response_model_by_alias=True)
async def get_active_cycle(session: AsyncSession = Depends(get_db_session)) -> ActiveCycleDetailSchema | None:
    return await load_active_cycle_detail(session)


@router.post(
    "/api/cycles/{cycle_id}/generate-next-week",
    response_model=CycleWeekSnapshotSchema,
    response_model_by_alias=True,
)
async def post_generate_next_week(
    cycle_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> CycleWeekSnapshotSchema:
    try:
        return await generate_next_week(session, cycle_id)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/cycles/{cycle_id}/confirm-next-week", response_model=ActiveCycleDetailSchema, response_model_by_alias=True)
async def post_confirm_next_week(
    cycle_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> ActiveCycleDetailSchema:
    try:
        return await confirm_next_week(session, cycle_id)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put(
    "/api/cycles/{cycle_id}/weeks/{week_index}/override",
    response_model=CycleWeekSnapshotSchema,
    response_model_by_alias=True,
)
async def put_cycle_week_override(
    cycle_id: int,
    week_index: int,
    payload: dict[str, Any],
    session: AsyncSession = Depends(get_db_session),
) -> CycleWeekSnapshotSchema:
    try:
        return await save_week_override(session, cycle_id, week_index, payload)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/cycles/{cycle_id}/stop", response_model=ActiveCycleDetailSchema, response_model_by_alias=True)
async def post_stop_cycle(
    cycle_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> ActiveCycleDetailSchema:
    try:
        return await stop_cycle(session, cycle_id)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=400, detail=str(exc)) from exc
