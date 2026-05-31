from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db_session
from backend.db.models import Profile, WEEKDAY_ORDER, DailyLog, WeeklyPlanDay
from backend.db.seed import DEFAULT_PROFILE_ID

router = APIRouter(prefix="/api/migrate", tags=["migrate"])

CHAT_HISTORY_SKIPPED_MESSAGE = (
    "chatHistory 已接收，但当前 Phase 1 仍只保留在 localStorage，未写入数据库。"
)


def assert_object(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise HTTPException(status_code=422, detail=f"备份文件中的 {field_name} 结构无效。")
    return value


def assert_backup_payload(payload: dict[str, Any]) -> dict[str, Any]:
    for field_name in ("profile", "weeklyPlan", "dailyLog", "chatHistory"):
        if field_name not in payload:
            raise HTTPException(status_code=422, detail=f"备份文件缺少必要字段：{field_name}")

    profile = assert_object(payload["profile"], "profile")
    weekly_plan = assert_object(payload["weeklyPlan"], "weeklyPlan")
    daily_log = assert_object(payload["dailyLog"], "dailyLog")
    chat_history = payload["chatHistory"]

    if not isinstance(chat_history, list):
        raise HTTPException(status_code=422, detail="备份文件中的 chatHistory 结构无效。")

    for day_key in WEEKDAY_ORDER:
        day_payload = weekly_plan.get(day_key)
        if not isinstance(day_payload, dict):
            raise HTTPException(status_code=422, detail=f"备份文件中的 weeklyPlan.{day_key} 结构无效。")
        if "type" not in day_payload or "exercises" not in day_payload:
            raise HTTPException(
                status_code=422,
                detail=f"备份文件中的 weeklyPlan.{day_key} 缺少必要字段：type 或 exercises",
            )
        if not isinstance(day_payload["exercises"], list):
            raise HTTPException(
                status_code=422,
                detail=f"备份文件中的 weeklyPlan.{day_key}.exercises 结构无效。",
            )

    for log_date, log_entry in daily_log.items():
        if not isinstance(log_date, str) or len(log_date) != 10 or not isinstance(log_entry, dict):
            raise HTTPException(status_code=422, detail="备份文件中的 dailyLog 结构无效。")

    if "basic" not in profile or "oneRM" not in profile:
        raise HTTPException(status_code=422, detail="备份文件中的 profile 缺少必要字段：basic 或 oneRM")
    assert_object(profile["basic"], "profile.basic")
    assert_object(profile["oneRM"], "profile.oneRM")

    return {
        "profile": profile,
        "weeklyPlan": weekly_plan,
        "dailyLog": daily_log,
        "chatHistory": chat_history,
    }


async def upsert_profile(session: AsyncSession, profile_payload: dict[str, Any]) -> None:
    profile = await session.get(Profile, DEFAULT_PROFILE_ID)
    if profile is None:
        profile = Profile(
            id=DEFAULT_PROFILE_ID,
            basic=profile_payload["basic"],
            one_rm=profile_payload["oneRM"],
            goal=profile_payload.get("goal", ""),
            target_weight=profile_payload.get("targetWeight"),
            notes=profile_payload.get("notes", ""),
        )
        session.add(profile)
        return

    profile.basic = profile_payload["basic"]
    profile.one_rm = profile_payload["oneRM"]
    profile.goal = profile_payload.get("goal", "")
    profile.target_weight = profile_payload.get("targetWeight")
    profile.notes = profile_payload.get("notes", "")


async def upsert_weekly_plan(session: AsyncSession, weekly_plan_payload: dict[str, Any]) -> int:
    result = await session.execute(select(WeeklyPlanDay))
    existing_days = {item.day_key: item for item in result.scalars().all()}

    for day_key in WEEKDAY_ORDER:
        day_payload = weekly_plan_payload[day_key]
        existing_day = existing_days.get(day_key)
        if existing_day is None:
            session.add(
                WeeklyPlanDay(
                    day_key=day_key,
                    type=day_payload["type"],
                    exercises=day_payload["exercises"],
                )
            )
            continue

        existing_day.type = day_payload["type"]
        existing_day.exercises = day_payload["exercises"]

    return len(WEEKDAY_ORDER)


async def upsert_daily_log(session: AsyncSession, daily_log_payload: dict[str, Any]) -> int:
    for log_date, log_entry in daily_log_payload.items():
        entry = await session.get(DailyLog, log_date)
        if entry is None:
            entry = DailyLog(
                date=log_date,
                weight=log_entry.get("weight"),
                kcal=log_entry.get("kcal"),
                protein=log_entry.get("protein"),
                sleep=log_entry.get("sleep"),
                fatigue=log_entry.get("fatigue"),
                steps=log_entry.get("steps"),
                training_done=log_entry.get("trainingDone"),
                training_notes=log_entry.get("trainingNotes", ""),
                tdee_manual=log_entry.get("tdee"),
            )
            session.add(entry)
            continue

        entry.weight = log_entry.get("weight")
        entry.kcal = log_entry.get("kcal")
        entry.protein = log_entry.get("protein")
        entry.sleep = log_entry.get("sleep")
        entry.fatigue = log_entry.get("fatigue")
        entry.steps = log_entry.get("steps")
        entry.training_done = log_entry.get("trainingDone")
        entry.training_notes = log_entry.get("trainingNotes", "")
        entry.tdee_manual = log_entry.get("tdee")

    return len(daily_log_payload)


@router.post("/import")
async def import_local_storage_backup(
    payload: dict[str, Any],
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    validated_payload = assert_backup_payload(payload)

    await upsert_profile(session, validated_payload["profile"])
    weekly_plan_days = await upsert_weekly_plan(session, validated_payload["weeklyPlan"])
    daily_logs = await upsert_daily_log(session, validated_payload["dailyLog"])
    await session.commit()

    return {
        "imported": {
            "profile": True,
            "weeklyPlanDays": weekly_plan_days,
            "dailyLogs": daily_logs,
        },
        "skipped": {
            "chatHistory": CHAT_HISTORY_SKIPPED_MESSAGE,
        },
    }
