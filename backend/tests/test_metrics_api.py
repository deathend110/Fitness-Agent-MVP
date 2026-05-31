from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.db.database import create_engine_and_session_factory, get_db_session
from backend.db.models import Base, DailyLog, Profile, WeeklyPlanDay
from backend.main import app


@pytest_asyncio.fixture
async def api_client(tmp_path: Path) -> AsyncIterator[AsyncClient]:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'metrics-api.db'}"
    engine, session_factory = create_engine_and_session_factory(database_url)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_get_db_session() -> AsyncIterator[Any]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()
    await engine.dispose()


async def seed_metric_state() -> None:
    async for session in app.dependency_overrides[get_db_session]():
        session.add_all(
            [
                Profile(
                    id=1,
                    basic={"sex": "male", "age": 29, "height": 175, "weight": 70},
                    one_rm={"squat": 140, "bench": 100, "deadlift": 180},
                    goal="增肌",
                    target_weight=None,
                    notes="",
                ),
                WeeklyPlanDay(
                    day_key="Monday",
                    type="strength",
                    exercises=[
                        {"name": "Back Squat", "ref1RM": "squat", "pct": 0.8, "sets": 5, "reps": 5},
                        {"name": "Bench Press", "ref1RM": "bench", "pct": 0.7, "sets": 4, "reps": 6},
                    ],
                ),
                DailyLog(
                    date="2026-06-01",
                    kcal=2500,
                    protein=105,
                    sleep=7.2,
                    fatigue=3,
                    training_done=True,
                    training_notes="状态稳定",
                ),
            ]
        )
        await session.commit()
        return


@pytest.mark.asyncio
async def test_daily_metrics_api_matches_frontend_rules(api_client: AsyncClient) -> None:
    await seed_metric_state()

    response = await api_client.get("/api/metrics/daily-summary", params={"date": "2026-06-01"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["today_key"] == "Monday"
    assert payload["today_str"] == "2026-06-01"
    assert payload["tdee_kcal"] == 2433
    assert payload["calorie_delta_kcal"] == 67
    assert payload["calorie_status"] == "balanced"
    assert payload["protein_g_per_kg"] == 1.5
    assert payload["protein_status"] == "low"


@pytest.mark.asyncio
async def test_daily_metrics_api_returns_unknown_when_profile_or_log_missing(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/metrics/daily-summary", params={"date": "2026-06-01"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["bmr_kcal"] is None
    assert payload["tdee_kcal"] is None
    assert payload["calorie_status"] == "unknown"
    assert payload["protein_status"] == "unknown"
