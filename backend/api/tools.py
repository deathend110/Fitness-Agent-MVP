from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.adopt_plan import (
    build_plan_change_proposal,
    commit_validated_plan_change,
)
from backend.api.weekly_plan import build_weekly_plan_response, dump_weekly_plan_response
from backend.db.database import get_db_session
from backend.db.models import WeeklyPlanDay
from backend.schemas import WeeklyPlanSchema

router = APIRouter(prefix="/api/tools", tags=["tools"])


class PlanProposeRequestSchema(BaseModel):
    sessionId: int | None = None
    day: str
    summary: str = ""
    changes: list[dict[str, Any]]


class PlanCommitRequestSchema(BaseModel):
    proposalId: str


@router.post("/plan/propose")
async def propose_plan_change(
    payload: PlanProposeRequestSchema,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    current_plan = await _load_current_plan(session)
    proposal = build_plan_change_proposal(
        current_plan=current_plan,
        session_id=payload.sessionId,
        day=payload.day,
        changes=payload.changes,
        summary=payload.summary,
    )
    return {
        "proposalId": proposal.proposal_id,
        "card": proposal.card,
        "validation": {
            "ok": proposal.validation.ok,
            "message": proposal.validation.message,
        },
    }


@router.post("/plan/commit")
async def commit_plan_change(
    payload: PlanCommitRequestSchema,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    current_plan = await _load_current_plan(session)
    result = commit_validated_plan_change(
        current_plan,
        payload.proposalId,
        confirmed_by_user=True,
    )
    if not result.ok:
        return {
            "ok": False,
            "message": result.message,
            "plan": current_plan,
        }

    await _write_plan(session, result.next_plan)
    refreshed_plan = await _load_current_plan(session)
    return {
        "ok": True,
        "message": result.message,
        "plan": refreshed_plan,
    }


async def _load_current_plan(session: AsyncSession) -> dict[str, Any]:
    result = await session.execute(select(WeeklyPlanDay))
    days = {item.day_key: item for item in result.scalars().all()}
    return dump_weekly_plan_response(build_weekly_plan_response(days))


async def _write_plan(session: AsyncSession, plan: dict[str, Any]) -> None:
    result = await session.execute(select(WeeklyPlanDay))
    existing_days = {item.day_key: item for item in result.scalars().all()}
    schema = WeeklyPlanSchema.model_validate(plan)

    for day_key, day_payload in schema.model_dump().items():
        existing = existing_days.get(day_key)
        if existing is None:
            session.add(
                WeeklyPlanDay(
                    day_key=day_key,
                    type=day_payload["type"],
                    exercises=day_payload["exercises"],
                )
            )
        else:
            existing.type = day_payload["type"]
            existing.exercises = day_payload["exercises"]
    await session.commit()
