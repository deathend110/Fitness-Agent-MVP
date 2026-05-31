from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.db.models import DailyLog, Profile, WEEKDAY_ORDER, WeeklyPlanDay


DEFAULT_PROFILE_ID = 1

EMPTY_PROFILE_BASIC = {
    "name": "",
    "sex": "",
    "age": None,
    "height": None,
    "weight": None,
    "waist": None,
}

EMPTY_PROFILE_ONE_RM = {
    "squat": None,
    "bench": None,
    "deadlift": None,
}


def create_empty_day_plan(day_key: str) -> WeeklyPlanDay:
    return WeeklyPlanDay(
        day_key=day_key,
        type="rest",
        exercises=[],
    )


async def seed_if_empty(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        profile = await session.get(Profile, DEFAULT_PROFILE_ID)
        if profile is None:
            session.add(
                Profile(
                    id=DEFAULT_PROFILE_ID,
                    basic=dict(EMPTY_PROFILE_BASIC),
                    one_rm=dict(EMPTY_PROFILE_ONE_RM),
                    goal="",
                    target_weight=None,
                    notes="",
                )
            )

        existing_days = set((await session.execute(select(WeeklyPlanDay.day_key))).scalars().all())
        for day_key in WEEKDAY_ORDER:
            if day_key not in existing_days:
                session.add(create_empty_day_plan(day_key))

        # 每日日志保持空表，只有用户实际录入后才写入。
        await session.commit()
