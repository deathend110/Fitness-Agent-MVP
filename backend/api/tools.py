from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.adopt_plan import (
    build_day_plan_replace_proposal,
    build_plan_change_proposal,
    commit_plan_proposal,
    ignore_plan_proposal,
)
from backend.api.weekly_plan import build_weekly_plan_response, dump_weekly_plan_response
from backend.db.database import get_db_session
from backend.db.models import ChatMessage, WeeklyPlanDay
from backend.schemas import WeeklyPlanSchema

router = APIRouter(prefix="/api/tools", tags=["tools"])


class PlanProposeRequestSchema(BaseModel):
    kind: str = "field_changes"
    sessionId: int | None = None
    day: str
    summary: str = ""
    changes: list[dict[str, Any]] = Field(default_factory=list)
    dayPlan: dict[str, Any] | None = None


class PlanCommitRequestSchema(BaseModel):
    proposalId: str


class PlanIgnoreRequestSchema(BaseModel):
    proposalId: str


@router.post("/plan/propose")
async def propose_plan_change(
    payload: PlanProposeRequestSchema,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    current_plan = await _load_current_plan(session)
    if payload.kind == "day_plan_replace":
        proposal = build_day_plan_replace_proposal(
            current_plan=current_plan,
            session_id=payload.sessionId,
            day=payload.day,
            summary=payload.summary,
            day_plan=payload.dayPlan or {},
        )
    else:
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
    result = commit_plan_proposal(
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
    await _sync_committed_proposal_status(session, payload.proposalId)
    refreshed_plan = await _load_current_plan(session)
    return {
        "ok": True,
        "message": result.message,
        "plan": refreshed_plan,
    }


@router.post("/plan/ignore")
async def ignore_plan_change(
    payload: PlanIgnoreRequestSchema,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    proposal = ignore_plan_proposal(payload.proposalId)
    if proposal is None:
        return {
            "ok": False,
            "message": "未找到计划修改提议，无法忽略。",
        }

    await _sync_proposal_status(session, payload.proposalId, "ignored")
    return {
        "ok": True,
        "message": "已忽略该计划建议卡。",
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


async def _sync_committed_proposal_status(session: AsyncSession, proposal_id: str) -> None:
    await _sync_proposal_status(session, proposal_id, "committed")


async def _sync_proposal_status(
    session: AsyncSession,
    proposal_id: str,
    next_status: str,
) -> None:
    result = await session.execute(select(ChatMessage).where(ChatMessage.role == "assistant"))
    updated = False
    for item in result.scalars().all():
        suggestion = item.suggestion
        if not isinstance(suggestion, dict):
            continue
        if str(suggestion.get("proposalId") or "").strip() != proposal_id:
            continue
        if suggestion.get("status") == next_status:
            continue
        item.suggestion = {**suggestion, "status": next_status}
        updated = True

    if updated:
        await session.commit()
