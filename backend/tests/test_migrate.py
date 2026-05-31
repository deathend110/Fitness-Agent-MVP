from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.db.database import create_engine_and_session_factory, get_db_session
from backend.db.models import Base
from backend.main import app


@pytest_asyncio.fixture
async def api_client(tmp_path: Path) -> AsyncIterator[AsyncClient]:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'migrate-api.db'}"
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


def build_backup_payload() -> dict:
    return {
        "app": "fitloop-mvp",
        "version": 1,
        "exportedAt": "2026-05-31T11:30:00.000Z",
        "profile": {
            "basic": {
                "name": "小周",
                "sex": "female",
                "age": 28,
                "height": 168,
                "weight": 62.5,
                "waist": 70,
            },
            "oneRM": {
                "squat": 95,
                "bench": 52.5,
                "deadlift": 115,
            },
            "goal": "减脂保力量",
            "targetWeight": 59,
            "notes": "工作日只能晚训。",
        },
        "weeklyPlan": {
            "Monday": {
                "type": "lower",
                "exercises": [
                    {
                        "id": "sq",
                        "name": "深蹲",
                        "template": {"loadMode": "percentage", "sets": 4, "repsText": "5"},
                        "instance": {"pct": 0.78, "kg": None, "rpe": 8},
                        "pct": 0.78,
                        "sets": 4,
                        "reps": 5,
                        "customField": {"cluster": False},
                    }
                ],
            },
            "Tuesday": {"type": "rest", "exercises": []},
            "Wednesday": {"type": "upper", "exercises": []},
            "Thursday": {"type": "rest", "exercises": []},
            "Friday": {"type": "conditioning", "exercises": []},
            "Saturday": {"type": "rest", "exercises": []},
            "Sunday": {"type": "mobility", "exercises": []},
        },
        "dailyLog": {
            "2026-05-30": {
                "weight": 62.4,
                "kcal": 1850,
                "protein": 132,
                "sleep": 7.5,
                "fatigue": 2,
                "steps": 9200,
                "trainingDone": True,
                "trainingNotes": "深蹲状态不错。",
                "tdee": 2100,
            }
        },
        "chatHistory": [
            {"role": "user", "content": "今天要不要减量？"},
            {"role": "assistant", "content": "先看疲劳和睡眠。"},
        ],
    }


@pytest.mark.asyncio
async def test_import_endpoint_persists_profile_weekly_plan_and_daily_log(api_client: AsyncClient):
    payload = build_backup_payload()

    response = await api_client.post("/api/migrate/import", json=payload)

    assert response.status_code == 200
    assert response.json() == {
        "imported": {
            "profile": True,
            "weeklyPlanDays": 7,
            "dailyLogs": 1,
        },
        "skipped": {
            "chatHistory": "chatHistory 已接收，但当前 Phase 1 仍只保留在 localStorage，未写入数据库。",
        },
    }

    profile_response = await api_client.get("/api/profile")
    weekly_plan_response = await api_client.get("/api/weekly-plan")
    daily_log_response = await api_client.get(
        "/api/daily-log",
        params={"from": "2026-05-01", "to": "2026-05-31"},
    )

    assert profile_response.status_code == 200
    assert profile_response.json() == {
        "basic": payload["profile"]["basic"],
        "oneRm": payload["profile"]["oneRM"],
        "goal": payload["profile"]["goal"],
        "targetWeight": payload["profile"]["targetWeight"],
        "notes": payload["profile"]["notes"],
    }
    assert weekly_plan_response.status_code == 200
    assert weekly_plan_response.json() == payload["weeklyPlan"]
    assert daily_log_response.status_code == 200
    assert daily_log_response.json() == {
        "2026-05-30": {
            "tdeeManual": payload["dailyLog"]["2026-05-30"]["tdee"],
            **{
                key: value
                for key, value in payload["dailyLog"]["2026-05-30"].items()
                if key != "tdee"
            },
        }
    }
    assert (
        weekly_plan_response.json()["Monday"]["exercises"][0]["customField"] == {"cluster": False}
    )


@pytest.mark.asyncio
async def test_import_endpoint_is_idempotent_for_repeat_payloads(api_client: AsyncClient):
    payload = build_backup_payload()

    first_response = await api_client.post("/api/migrate/import", json=payload)
    second_response = await api_client.post("/api/migrate/import", json=payload)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert second_response.json()["imported"] == {
        "profile": True,
        "weeklyPlanDays": 7,
        "dailyLogs": 1,
    }

    weekly_plan_response = await api_client.get("/api/weekly-plan")
    daily_log_response = await api_client.get(
        "/api/daily-log",
        params={"from": "2026-05-01", "to": "2026-05-31"},
    )

    assert len(weekly_plan_response.json()) == 7
    assert list(daily_log_response.json().keys()) == ["2026-05-30"]


@pytest.mark.asyncio
async def test_import_endpoint_rejects_missing_required_fields(api_client: AsyncClient):
    payload = build_backup_payload()
    payload.pop("weeklyPlan")

    response = await api_client.post("/api/migrate/import", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"] == "备份文件缺少必要字段：weeklyPlan"

    profile_response = await api_client.get("/api/profile")
    weekly_plan_response = await api_client.get("/api/weekly-plan")

    assert profile_response.status_code == 200
    assert profile_response.json()["basic"]["name"] == ""
    assert weekly_plan_response.status_code == 200
    assert weekly_plan_response.json()["Monday"] == {"type": "rest", "exercises": []}


@pytest.mark.asyncio
async def test_import_endpoint_accepts_chat_history_without_writing_database_rows(api_client: AsyncClient):
    payload = build_backup_payload()

    response = await api_client.post("/api/migrate/import", json=payload)

    assert response.status_code == 200
    assert response.json()["skipped"] == {
        "chatHistory": "chatHistory 已接收，但当前 Phase 1 仍只保留在 localStorage，未写入数据库。",
    }
