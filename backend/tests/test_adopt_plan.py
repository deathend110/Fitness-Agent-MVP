from __future__ import annotations

from collections.abc import AsyncIterator
from copy import deepcopy
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.db.database import create_engine_and_session_factory, get_db_session
from backend.db.models import Base
from backend.main import app

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
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'adopt-plan.db'}"
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


def build_weekly_plan() -> dict:
    rest_day = {"type": "rest", "exercises": []}
    return {
        "Monday": {
            "type": "腿日",
            "exercises": [
                {
                    "id": "sq-main",
                    "name": "深蹲",
                    "tier": "main",
                    "template": {
                        "loadMode": "percentage",
                        "ref1RM": "squat",
                        "setType": "straight",
                        "sets": 5,
                        "repsText": "5",
                    },
                    "instance": {
                        "pct": 0.75,
                        "kg": None,
                        "rpe": 8,
                        "note": "保持深度",
                    },
                    "ref1RM": "squat",
                    "pct": 0.75,
                    "kg": None,
                    "sets": 5,
                    "reps": 5,
                    "rpe": 8,
                    "note": "保持深度",
                    "source": {"from": "demo"},
                },
                {
                    "id": "leg-press",
                    "name": "腿举",
                    "tier": "accessory",
                    "template": {
                        "loadMode": "fixed",
                        "ref1RM": None,
                        "setType": "straight",
                        "sets": 4,
                        "repsText": "10",
                    },
                    "instance": {
                        "pct": None,
                        "kg": 120,
                        "rpe": 7,
                        "note": "控制离心",
                    },
                    "ref1RM": None,
                    "pct": None,
                    "kg": 120,
                    "sets": 4,
                    "reps": 10,
                    "rpe": 7,
                    "note": "控制离心",
                },
            ],
        },
        "Tuesday": deepcopy(rest_day),
        "Wednesday": deepcopy(rest_day),
        "Thursday": deepcopy(rest_day),
        "Friday": deepcopy(rest_day),
        "Saturday": deepcopy(rest_day),
        "Sunday": deepcopy(rest_day),
    }


async def seed_weekly_plan(api_client: AsyncClient, weekly_plan: dict | None = None) -> dict:
    payload = weekly_plan or build_weekly_plan()
    response = await api_client.put("/api/weekly-plan", json=payload)
    assert response.status_code == 200
    return payload


@pytest.mark.asyncio
async def test_adopt_update_writes_back_and_preserves_flat_exercise_fields(api_client: AsyncClient):
    await seed_weekly_plan(api_client)

    response = await api_client.post(
        "/api/weekly-plan/adopt",
        json={
            "day": "Monday",
            "changes": [
                {
                    "action": "update",
                    "exerciseName": "深蹲",
                    "field": "pct",
                    "newValue": 0.7,
                }
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    exercise = body["plan"]["Monday"]["exercises"][0]

    assert body["ok"] is True
    assert body["message"] == "已采纳 AI 建议，训练计划已更新。"
    assert exercise["pct"] == 0.7
    assert exercise["instance"]["pct"] == 0.7
    assert exercise["template"] == {
        "loadMode": "percentage",
        "ref1RM": "squat",
        "setType": "straight",
        "sets": 5,
        "repsText": "5",
    }
    assert exercise["ref1RM"] == "squat"
    assert exercise["kg"] is None
    assert exercise["sets"] == 5
    assert exercise["reps"] == 5
    assert exercise["rpe"] == 8
    assert exercise["note"] == "保持深度"
    assert exercise["source"] == {"from": "demo"}

    persisted_response = await api_client.get("/api/weekly-plan")
    assert persisted_response.json()["Monday"]["exercises"][0]["pct"] == 0.7


@pytest.mark.asyncio
async def test_adopt_rejects_invalid_action_without_dirty_write(api_client: AsyncClient):
    original_plan = await seed_weekly_plan(api_client)

    for action in ["add", "", None]:
        response = await api_client.post(
            "/api/weekly-plan/adopt",
            json={
                "day": "Monday",
                "changes": [
                    {
                        "action": action,
                        "exerciseName": "深蹲",
                        "field": "pct",
                        "newValue": 0.7,
                    }
                ],
            },
        )

        assert response.status_code == 200
        assert response.json()["ok"] is False
        assert "仅支持" in response.json()["message"]

        persisted_response = await api_client.get("/api/weekly-plan")
        assert persisted_response.json() == original_plan

    missing_action_response = await api_client.post(
        "/api/weekly-plan/adopt",
        json={
            "day": "Monday",
            "changes": [
                {
                    "exerciseName": "深蹲",
                    "field": "pct",
                    "newValue": 0.7,
                }
            ],
        },
    )

    assert missing_action_response.status_code == 200
    assert missing_action_response.json()["ok"] is False
    assert "仅支持" in missing_action_response.json()["message"]
    assert (await api_client.get("/api/weekly-plan")).json() == original_plan


@pytest.mark.asyncio
async def test_adopt_rejects_out_of_range_rpe_without_dirty_write(api_client: AsyncClient):
    original_plan = await seed_weekly_plan(api_client)

    response = await api_client.post(
        "/api/weekly-plan/adopt",
        json={
            "day": "Monday",
            "changes": [
                {
                    "action": "update",
                    "exerciseName": "深蹲",
                    "field": "rpe",
                    "newValue": 11,
                }
            ],
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "ok": False,
        "message": "动作“深蹲”的 RPE 必须在 0-10 之间，无法采纳该建议。",
        "plan": original_plan,
    }

    persisted_response = await api_client.get("/api/weekly-plan")
    assert persisted_response.json() == original_plan


@pytest.mark.asyncio
async def test_adopt_applies_multiple_changes_as_one_batch(api_client: AsyncClient):
    await seed_weekly_plan(api_client)

    response = await api_client.post(
        "/api/weekly-plan/adopt",
        json={
            "day": "Monday",
            "changes": [
                {
                    "action": "update",
                    "exerciseName": "深蹲",
                    "field": "pct",
                    "newValue": 0.68,
                },
                {
                    "action": "update",
                    "exerciseName": "腿举",
                    "field": "kg",
                    "newValue": 110,
                },
                {
                    "action": "update",
                    "exerciseName": "腿举",
                    "field": "note",
                    "newValue": "降重保动作",
                },
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["ok"] is True
    assert body["plan"]["Monday"]["exercises"][0]["pct"] == 0.68
    assert body["plan"]["Monday"]["exercises"][0]["instance"]["pct"] == 0.68
    assert body["plan"]["Monday"]["exercises"][1]["kg"] == 110
    assert body["plan"]["Monday"]["exercises"][1]["instance"]["kg"] == 110
    assert body["plan"]["Monday"]["exercises"][1]["note"] == "降重保动作"
    assert body["plan"]["Monday"]["exercises"][1]["instance"]["note"] == "降重保动作"


@pytest.mark.asyncio
async def test_adopt_coerces_numeric_string_value_before_writing(api_client: AsyncClient):
    await seed_weekly_plan(api_client)

    response = await api_client.post(
        "/api/weekly-plan/adopt",
        json={
            "day": "Monday",
            "changes": [
                {
                    "action": "update",
                    "exerciseName": "深蹲",
                    "field": "pct",
                    "newValue": "0.7",
                },
                {
                    "action": "update",
                    "exerciseName": "腿举",
                    "field": "kg",
                    "newValue": "110",
                },
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["ok"] is True
    assert body["plan"]["Monday"]["exercises"][0]["pct"] == 0.7
    assert body["plan"]["Monday"]["exercises"][0]["instance"]["pct"] == 0.7
    assert body["plan"]["Monday"]["exercises"][1]["kg"] == 110
    assert body["plan"]["Monday"]["exercises"][1]["instance"]["kg"] == 110


@pytest.mark.asyncio
async def test_adopt_rejects_invalid_numeric_string_without_dirty_write(api_client: AsyncClient):
    original_plan = await seed_weekly_plan(api_client)

    response = await api_client.post(
        "/api/weekly-plan/adopt",
        json={
            "day": "Monday",
            "changes": [
                {
                    "action": "update",
                    "exerciseName": "深蹲",
                    "field": "pct",
                    "newValue": "heavy",
                },
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["ok"] is False
    assert response.json()["plan"] == original_plan
    assert "pct" in response.json()["message"]
    assert (await api_client.get("/api/weekly-plan")).json() == original_plan


@pytest.mark.asyncio
async def test_adopt_reps_update_keeps_template_reps_text_in_sync(api_client: AsyncClient):
    await seed_weekly_plan(api_client)

    response = await api_client.post(
        "/api/weekly-plan/adopt",
        json={
            "day": "Monday",
            "changes": [
                {
                    "action": "update",
                    "exerciseName": "深蹲",
                    "field": "reps",
                    "newValue": "3",
                },
            ],
        },
    )

    assert response.status_code == 200
    exercise = response.json()["plan"]["Monday"]["exercises"][0]

    assert response.json()["ok"] is True
    assert exercise["reps"] == 3
    assert exercise["template"]["repsText"] == "3"


@pytest.mark.asyncio
async def test_adopt_rejects_unknown_exercise_and_unknown_field_without_partial_write(
    api_client: AsyncClient,
):
    original_plan = await seed_weekly_plan(api_client)

    missing_exercise_response = await api_client.post(
        "/api/weekly-plan/adopt",
        json={
            "day": "Monday",
            "changes": [
                {
                    "action": "update",
                    "exerciseName": "卧推",
                    "field": "pct",
                    "newValue": 0.6,
                }
            ],
        },
    )
    missing_field_response = await api_client.post(
        "/api/weekly-plan/adopt",
        json={
            "day": "Monday",
            "changes": [
                {
                    "action": "update",
                    "exerciseName": "深蹲",
                    "field": "volume",
                    "newValue": "low",
                }
            ],
        },
    )

    assert missing_exercise_response.status_code == 200
    assert missing_exercise_response.json()["ok"] is False
    assert "卧推" in missing_exercise_response.json()["message"]
    assert missing_field_response.status_code == 200
    assert missing_field_response.json()["ok"] is False
    assert "volume" in missing_field_response.json()["message"]

    persisted_response = await api_client.get("/api/weekly-plan")
    assert persisted_response.json() == original_plan
