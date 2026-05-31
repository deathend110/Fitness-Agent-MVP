from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db_session
from backend.db.models import WEEKDAY_ORDER, WeeklyPlanDay
from backend.schemas import WeeklyPlanDaySchema, WeeklyPlanSchema

router = APIRouter(prefix="/api/weekly-plan", tags=["weekly-plan"])


def build_empty_day_schema() -> WeeklyPlanDaySchema:
    return WeeklyPlanDaySchema(type="rest", exercises=[])


def build_day_schema(day: WeeklyPlanDay | None) -> WeeklyPlanDaySchema:
    if day is None:
        return build_empty_day_schema()
    return WeeklyPlanDaySchema(type=day.type, exercises=day.exercises)


def build_weekly_plan_response(days: dict[str, WeeklyPlanDay]) -> WeeklyPlanSchema:
    return WeeklyPlanSchema(
        Monday=build_day_schema(days.get("Monday")),
        Tuesday=build_day_schema(days.get("Tuesday")),
        Wednesday=build_day_schema(days.get("Wednesday")),
        Thursday=build_day_schema(days.get("Thursday")),
        Friday=build_day_schema(days.get("Friday")),
        Saturday=build_day_schema(days.get("Saturday")),
        Sunday=build_day_schema(days.get("Sunday")),
    )


def get_payload_day(payload: WeeklyPlanSchema, day_key: str) -> WeeklyPlanDaySchema:
    return getattr(payload, day_key)


@router.get("", response_model=WeeklyPlanSchema, response_model_by_alias=True)
async def get_weekly_plan(session: AsyncSession = Depends(get_db_session)) -> WeeklyPlanSchema:
    result = await session.execute(select(WeeklyPlanDay))
    days = {item.day_key: item for item in result.scalars().all()}
    return build_weekly_plan_response(days)


@router.put("", response_model=WeeklyPlanSchema, response_model_by_alias=True)
async def put_weekly_plan(
    payload: WeeklyPlanSchema,
    session: AsyncSession = Depends(get_db_session),
) -> WeeklyPlanSchema:
    result = await session.execute(select(WeeklyPlanDay))
    existing_days = {item.day_key: item for item in result.scalars().all()}

    for day_key in WEEKDAY_ORDER:
        day_payload = get_payload_day(payload, day_key)
        existing_day = existing_days.get(day_key)
        if existing_day is None:
            session.add(
                WeeklyPlanDay(
                    day_key=day_key,
                    type=day_payload.type,
                    exercises=day_payload.exercises,
                )
            )
            continue

        existing_day.type = day_payload.type
        existing_day.exercises = day_payload.exercises

    await session.commit()

    refreshed_result = await session.execute(select(WeeklyPlanDay))
    refreshed_days = {item.day_key: item for item in refreshed_result.scalars().all()}
    return build_weekly_plan_response(refreshed_days)
