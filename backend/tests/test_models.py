from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from backend.db.database import create_all_tables, create_engine_and_session_factory
from backend.db.models import Base, ChatMessage, DailyLog, Profile, WeeklyPlanDay, utc_now
from backend.db.seed import DEFAULT_PROFILE_ID, seed_if_empty


@pytest.mark.asyncio
async def test_models_round_trip_preserves_profile_weekly_plan_and_daily_log(tmp_path: Path):
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'models.db'}"
    engine, session_factory = create_engine_and_session_factory(database_url)

    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        monday_exercises = [
            {
                "id": "monday-squat",
                "name": "深蹲",
                "tier": "main",
                "template": {
                    "loadMode": "percentage",
                    "ref1RM": "squat",
                    "setType": "straight",
                    "sets": 4,
                    "repsText": "6",
                },
                "instance": {
                    "pct": 0.75,
                    "kg": None,
                    "rpe": 8,
                    "note": "主项，动作质量优先",
                },
                "ref1RM": "squat",
                "pct": 0.75,
                "kg": None,
                "sets": 4,
                "reps": 6,
                "rpe": 8,
                "note": "主项，动作质量优先",
            },
            {
                "id": "monday-rdl",
                "name": "罗马尼亚硬拉",
                "tier": "accessory",
                "template": {
                    "loadMode": "fixed",
                    "ref1RM": None,
                    "setType": "custom",
                    "sets": 3,
                    "repsText": "8-10",
                },
                "instance": {
                    "pct": None,
                    "kg": 80,
                    "rpe": 7.5,
                    "note": "控制离心",
                },
                "ref1RM": None,
                "pct": None,
                "kg": 80,
                "sets": 3,
                "reps": None,
                "rpe": 7.5,
                "note": "控制离心",
            },
        ]

        async with session_factory() as session:
            session.add(
                Profile(
                    id=DEFAULT_PROFILE_ID,
                    basic={
                        "name": "小林",
                        "sex": "male",
                        "age": 23,
                        "height": 178,
                        "weight": 82.1,
                        "waist": 82,
                    },
                    one_rm={"squat": 120, "bench": 90, "deadlift": 150},
                    goal="增肌减脂",
                    target_weight=78,
                    notes="工作日容易睡眠不足",
                )
            )
            session.add(
                WeeklyPlanDay(
                    day_key="Monday",
                    type="腿日",
                    exercises=monday_exercises,
                )
            )
            session.add(
                DailyLog(
                    date="2026-05-31",
                    weight=82.1,
                    kcal=2150,
                    protein=165,
                    sleep=6.8,
                    fatigue=4,
                    steps=7560,
                    training_done=True,
                    training_notes="深蹲第三组完成度下降，膝盖略紧。",
                    tdee_manual=2480,
                )
            )
            await session.commit()

        async with session_factory() as session:
            stored_profile = await session.get(Profile, DEFAULT_PROFILE_ID)
            stored_day = await session.get(WeeklyPlanDay, "Monday")
            stored_log = await session.get(DailyLog, "2026-05-31")

        assert stored_profile is not None
        assert stored_profile.basic["name"] == "小林"
        assert stored_profile.one_rm["deadlift"] == 150
        assert stored_profile.target_weight == 78

        assert stored_day is not None
        assert stored_day.type == "腿日"
        assert stored_day.exercises == monday_exercises
        assert stored_day.exercises[0]["template"]["loadMode"] == "percentage"
        assert stored_day.exercises[0]["instance"]["pct"] == 0.75
        assert stored_day.exercises[0]["pct"] == 0.75
        assert stored_day.exercises[1]["template"]["repsText"] == "8-10"
        assert stored_day.exercises[1]["instance"]["kg"] == 80
        assert stored_day.exercises[1]["kg"] == 80

        assert stored_log is not None
        assert stored_log.weight == pytest.approx(82.1)
        assert stored_log.training_done is True
        assert stored_log.tdee_manual == 2480

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_seed_if_empty_creates_blank_profile_weekdays_and_is_idempotent(tmp_path: Path):
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'seed.db'}"
    engine, session_factory = create_engine_and_session_factory(database_url)

    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        await seed_if_empty(session_factory)
        await seed_if_empty(session_factory)

        async with session_factory() as session:
            profile_count = len((await session.execute(select(Profile))).scalars().all())
            weekly_days = (await session.execute(select(WeeklyPlanDay).order_by(WeeklyPlanDay.day_key))).scalars().all()
            daily_logs = len((await session.execute(select(DailyLog))).scalars().all())

        assert profile_count == 1
        assert daily_logs == 0
        assert len(weekly_days) == 7
        assert {day.day_key for day in weekly_days} == {
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        }
        assert all(day.type == "rest" for day in weekly_days)
        assert all(day.exercises == [] for day in weekly_days)

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_create_all_tables_repairs_old_sqlite_chat_message_schema(tmp_path: Path):
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'old-chat.db'}"
    engine, session_factory = create_engine_and_session_factory(database_url)

    try:
        async with engine.begin() as connection:
            await connection.exec_driver_sql(
                """
                CREATE TABLE chat_session (
                    id INTEGER PRIMARY KEY,
                    title VARCHAR(128) NOT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
                """
            )
            await connection.exec_driver_sql(
                """
                CREATE TABLE chat_message (
                    id INTEGER PRIMARY KEY,
                    session_id INTEGER NOT NULL,
                    role VARCHAR(16) NOT NULL,
                    content TEXT NOT NULL,
                    suggestion JSON,
                    created_at DATETIME NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES chat_session(id) ON DELETE CASCADE
                )
                """
            )
            await connection.exec_driver_sql(
                "INSERT INTO chat_session (id, title, created_at, updated_at) VALUES (1, '默认对话', '2026-06-01 00:00:00', '2026-06-01 00:00:00')"
            )

        await create_all_tables(engine)

        async with session_factory() as session:
            session.add(
                ChatMessage(
                    session_id=1,
                    role="user",
                    content="附件消息",
                    suggestion=None,
                    attachments=[
                        {
                            "fileId": 3,
                            "originalName": "减脂容量型计划.xlsx",
                            "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            "extension": ".xlsx",
                            "sizeBytes": 10321,
                        }
                    ],
                    created_at=utc_now(),
                )
            )
            await session.commit()

        async with session_factory() as session:
            stored_message = await session.get(ChatMessage, 1)

        assert stored_message is not None
        assert stored_message.attachments[0]["originalName"] == "减脂容量型计划.xlsx"
        assert stored_message.attachments[0]["fileId"] == 3

    finally:
        await engine.dispose()
