from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.db.database import create_engine_and_session_factory, get_db_session
from backend.db.models import Base
from backend.main import app
from backend.schemas import DailyLogEntrySchema, ProfileSchema

pytestmark = [
    pytest.mark.filterwarnings(
        "error::pydantic.warnings.UnsupportedFieldAttributeWarning"
    ),
    pytest.mark.filterwarnings(
        "ignore:'asyncio.iscoroutinefunction' is deprecated:DeprecationWarning"
    ),
]


@pytest_asyncio.fixture
async def api_client(tmp_path: Path) -> AsyncIterator[AsyncClient]:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'crud-api.db'}"
    engine, session_factory = create_engine_and_session_factory(database_url)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_get_db_session() -> AsyncIterator:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_profile_endpoints_return_empty_default_then_persist_updates(api_client: AsyncClient):
    empty_response = await api_client.get("/api/profile")

    assert empty_response.status_code == 200
    assert empty_response.json() == {
        "basic": {
            "name": "",
            "sex": "",
            "age": None,
            "height": None,
            "weight": None,
            "waist": None,
        },
        "oneRm": {
            "squat": None,
            "bench": None,
            "deadlift": None,
        },
        "goal": "",
        "targetWeight": None,
        "notes": "",
    }

    payload = {
        "basic": {
            "name": "阿杰",
            "sex": "male",
            "age": 26,
            "height": 181,
            "weight": 84.2,
            "waist": 83,
        },
        "oneRm": {
            "squat": 150,
            "bench": 105,
            "deadlift": 190,
        },
        "goal": "增肌",
        "targetWeight": 86,
        "notes": "晚训表现更好",
    }

    put_response = await api_client.put("/api/profile", json=payload)

    assert put_response.status_code == 200
    assert put_response.json() == payload

    round_trip_response = await api_client.get("/api/profile")

    assert round_trip_response.status_code == 200
    assert round_trip_response.json() == payload


@pytest.mark.asyncio
async def test_weekly_plan_endpoints_return_default_week_and_preserve_exercise_shape(api_client: AsyncClient):
    empty_response = await api_client.get("/api/weekly-plan")

    assert empty_response.status_code == 200
    assert empty_response.json() == {
        "Monday": {"type": "rest", "exercises": []},
        "Tuesday": {"type": "rest", "exercises": []},
        "Wednesday": {"type": "rest", "exercises": []},
        "Thursday": {"type": "rest", "exercises": []},
        "Friday": {"type": "rest", "exercises": []},
        "Saturday": {"type": "rest", "exercises": []},
        "Sunday": {"type": "rest", "exercises": []},
    }

    payload = {
        "Monday": {
            "type": "strength",
            "exercises": [
                {
                    "id": "sq-main",
                    "name": "深蹲",
                    "template": {
                        "loadMode": "percentage",
                        "ref1RM": "squat",
                        "setType": "straight",
                        "sets": 5,
                        "repsText": "5",
                    },
                    "instance": {
                        "pct": 0.8,
                        "kg": None,
                        "rpe": 8,
                        "note": "专注稳定性",
                    },
                    "ref1RM": "squat",
                    "pct": 0.8,
                    "kg": None,
                    "sets": 5,
                    "reps": 5,
                    "rpe": 8,
                    "note": "专注稳定性",
                }
            ],
        },
        "Tuesday": {"type": "rest", "exercises": []},
        "Wednesday": {
            "type": "upper",
            "exercises": [
                {
                    "id": "bp-main",
                    "name": "卧推",
                    "template": {"loadMode": "fixed", "sets": 4, "repsText": "6"},
                    "instance": {"kg": 82.5, "pct": None, "rpe": 7.5},
                    "kg": 82.5,
                    "sets": 4,
                    "reps": 6,
                    "extraField": {"tempo": "31X0"},
                }
            ],
        },
        "Thursday": {"type": "rest", "exercises": []},
        "Friday": {"type": "conditioning", "exercises": []},
        "Saturday": {"type": "rest", "exercises": []},
        "Sunday": {"type": "mobility", "exercises": []},
    }

    put_response = await api_client.put("/api/weekly-plan", json=payload)

    assert put_response.status_code == 200
    assert put_response.json() == payload

    round_trip_response = await api_client.get("/api/weekly-plan")

    assert round_trip_response.status_code == 200
    assert round_trip_response.json() == payload
    assert round_trip_response.json()["Monday"]["exercises"][0]["template"]["loadMode"] == "percentage"
    assert round_trip_response.json()["Monday"]["exercises"][0]["instance"]["pct"] == 0.8
    assert round_trip_response.json()["Wednesday"]["exercises"][0]["extraField"] == {"tempo": "31X0"}


@pytest.mark.asyncio
async def test_daily_log_endpoints_filter_range_and_upsert_new_dates(api_client: AsyncClient):
    empty_response = await api_client.get("/api/daily-log", params={"from": "2026-06-01", "to": "2026-06-07"})

    assert empty_response.status_code == 200
    assert empty_response.json() == {}

    first_payload = {
        "weight": 82.4,
        "kcal": 2310,
        "protein": 168,
        "sleep": 7.2,
        "fatigue": 3,
        "steps": 8450,
        "trainingDone": True,
        "trainingNotes": "卧推最后一组保留 1 次。",
        "tdeeManual": 2550,
    }
    second_payload = {
        "weight": 82.0,
        "kcal": 2080,
        "protein": 160,
        "sleep": 6.5,
        "fatigue": 5,
        "steps": 6200,
        "trainingDone": False,
        "trainingNotes": "主动休息。",
        "tdeeManual": None,
    }

    first_put = await api_client.put("/api/daily-log/2026-06-02", json=first_payload)
    second_put = await api_client.put("/api/daily-log/2026-06-05", json=second_payload)

    assert first_put.status_code == 200
    assert first_put.json() == first_payload
    assert second_put.status_code == 200
    assert second_put.json() == second_payload

    range_response = await api_client.get("/api/daily-log", params={"from": "2026-06-01", "to": "2026-06-03"})

    assert range_response.status_code == 200
    assert range_response.json() == {
        "2026-06-02": first_payload,
    }

    full_response = await api_client.get("/api/daily-log", params={"from": "2026-06-01", "to": "2026-06-07"})

    assert full_response.status_code == 200
    assert full_response.json() == {
        "2026-06-02": first_payload,
        "2026-06-05": second_payload,
    }


@pytest.mark.asyncio
async def test_invalid_body_returns_422_without_writing_dirty_data(api_client: AsyncClient):
    invalid_response = await api_client.put(
        "/api/weekly-plan",
        json={
            "Monday": {"type": "strength"},
        },
    )

    assert invalid_response.status_code == 422

    weekly_plan_response = await api_client.get("/api/weekly-plan")

    assert weekly_plan_response.status_code == 200
    assert weekly_plan_response.json() == {
        "Monday": {"type": "rest", "exercises": []},
        "Tuesday": {"type": "rest", "exercises": []},
        "Wednesday": {"type": "rest", "exercises": []},
        "Thursday": {"type": "rest", "exercises": []},
        "Friday": {"type": "rest", "exercises": []},
        "Saturday": {"type": "rest", "exercises": []},
        "Sunday": {"type": "rest", "exercises": []},
    }


def test_profile_and_daily_log_schema_alias_contract_stays_stable():
    profile = ProfileSchema.model_validate(
        {
            "basic": {"name": "阿杰"},
            "oneRm": {"squat": 160},
            "goal": "增肌",
            "targetWeight": 85,
            "notes": "测试",
        }
    )
    daily_log = DailyLogEntrySchema.model_validate(
        {
            "weight": 82.5,
            "trainingDone": True,
            "trainingNotes": "状态不错",
            "tdeeManual": 2600,
        }
    )

    assert profile.model_dump(by_alias=True) == {
        "basic": {
            "name": "阿杰",
            "sex": "",
            "age": None,
            "height": None,
            "weight": None,
            "waist": None,
        },
        "oneRm": {"squat": 160.0, "bench": None, "deadlift": None},
        "goal": "增肌",
        "targetWeight": 85.0,
        "notes": "测试",
    }
    assert daily_log.model_dump(by_alias=True) == {
        "weight": 82.5,
        "kcal": None,
        "protein": None,
        "sleep": None,
        "fatigue": None,
        "steps": None,
        "trainingDone": True,
        "trainingNotes": "状态不错",
        "tdeeManual": 2600,
    }
