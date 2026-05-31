from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db_session
from backend.db.models import DailyLog
from backend.schemas import DailyLogEntrySchema, DailyLogMapSchema

router = APIRouter(prefix="/api/daily-log", tags=["daily-log"])


def build_daily_log_entry_response(entry: DailyLog) -> DailyLogEntrySchema:
    return DailyLogEntrySchema(
        weight=entry.weight,
        kcal=entry.kcal,
        protein=entry.protein,
        sleep=entry.sleep,
        fatigue=entry.fatigue,
        steps=entry.steps,
        trainingDone=entry.training_done,
        trainingNotes=entry.training_notes,
        tdeeManual=entry.tdee_manual,
    )


@router.get("", response_model=DailyLogMapSchema, response_model_by_alias=True)
async def get_daily_logs(
    from_date: str = Query(..., alias="from"),
    to_date: str = Query(..., alias="to"),
    session: AsyncSession = Depends(get_db_session),
) -> DailyLogMapSchema:
    result = await session.execute(
        select(DailyLog)
        .where(DailyLog.date >= from_date)
        .where(DailyLog.date <= to_date)
        .order_by(DailyLog.date)
    )
    payload = {
        entry.date: build_daily_log_entry_response(entry)
        for entry in result.scalars().all()
    }
    return DailyLogMapSchema(root=payload)


@router.put("/{date}", response_model=DailyLogEntrySchema, response_model_by_alias=True)
async def put_daily_log(
    payload: DailyLogEntrySchema,
    date: str = Path(..., min_length=10, max_length=10),
    session: AsyncSession = Depends(get_db_session),
) -> DailyLogEntrySchema:
    entry = await session.get(DailyLog, date)
    if entry is None:
        entry = DailyLog(
            date=date,
            weight=payload.weight,
            kcal=payload.kcal,
            protein=payload.protein,
            sleep=payload.sleep,
            fatigue=payload.fatigue,
            steps=payload.steps,
            training_done=payload.trainingDone,
            training_notes=payload.trainingNotes,
            tdee_manual=payload.tdeeManual,
        )
        session.add(entry)
    else:
        entry.weight = payload.weight
        entry.kcal = payload.kcal
        entry.protein = payload.protein
        entry.sleep = payload.sleep
        entry.fatigue = payload.fatigue
        entry.steps = payload.steps
        entry.training_done = payload.trainingDone
        entry.training_notes = payload.trainingNotes
        entry.tdee_manual = payload.tdeeManual

    await session.commit()
    await session.refresh(entry)
    return build_daily_log_entry_response(entry)
