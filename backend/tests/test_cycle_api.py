from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import create_engine_and_session_factory, get_db_session
from backend.db.models import (
    ActiveCyclePlan,
    Base,
    CycleWeekSnapshot,
    PlanSourceState,
    Profile,
    WeeklyPlanDay,
)
from backend.main import app


@pytest_asyncio.fixture
async def api_client(tmp_path: Path) -> AsyncIterator[tuple[AsyncClient, Any]]:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'cycle-api.db'}"
    engine, session_factory = create_engine_and_session_factory(database_url)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_get_db_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, session_factory

    app.dependency_overrides.clear()
    await engine.dispose()


async def _seed_manual_state(session_factory: Any) -> None:
    async with session_factory() as session:
        session.add_all(
            [
                PlanSourceState(id=1, active_source="manual"),
                Profile(
                    id=1,
                    basic={"sex": "male", "age": 28, "height": 178, "weight": 80},
                    one_rm={"squat": 180, "bench": 120, "deadlift": 220},
                    goal="力量提升",
                    target_weight=None,
                    notes="",
                ),
                WeeklyPlanDay(
                    day_key="Monday",
                    type="manual_strength",
                    exercises=[
                        {
                            "name": "Manual Squat",
                            "ref1RM": "squat",
                            "pct": 0.7,
                            "sets": 3,
                            "reps": 5,
                        }
                    ],
                ),
                WeeklyPlanDay(day_key="Tuesday", type="rest", exercises=[]),
                WeeklyPlanDay(day_key="Wednesday", type="rest", exercises=[]),
                WeeklyPlanDay(day_key="Thursday", type="rest", exercises=[]),
                WeeklyPlanDay(day_key="Friday", type="rest", exercises=[]),
                WeeklyPlanDay(day_key="Saturday", type="rest", exercises=[]),
                WeeklyPlanDay(day_key="Sunday", type="rest", exercises=[]),
            ]
        )
        await session.commit()


def _build_create_cycle_payload() -> dict[str, Any]:
    return {
        "presetKey": "candito_6week",
        "startDate": "2026-06-01",
        "goal": "力量提升",
        "baseLifts": {
            "squat": {"oneRm": 180, "tm": 162},
            "bench": {"oneRm": 120, "tm": 108},
            "deadlift": {"oneRm": 220, "tm": 198},
        },
        "config": {"trainingDays": ["Tuesday", "Thursday", "Saturday", "Sunday"]},
    }


def _build_custom_strength_cycle_payload() -> dict[str, Any]:
    return {
        "presetKey": "custom_strength",
        "startDate": "2026-06-09",
        "goal": "strength",
        "baseLifts": {
            "squat": {"tm": 180},
            "bench": {"tm": 120},
        },
        "config": {
            "planType": "custom_strength",
            "name": "四周力量周期",
            "startDate": "2026-06-09",
            "totalWeeks": 2,
            "mainLifts": {
                "squat": {"tm": 180},
                "bench": {"tm": 120},
            },
            "weeks": [
                {
                    "weekIndex": 1,
                    "days": [
                        {
                            "dayIndex": 1,
                            "label": "周一",
                            "type": "lower_strength",
                            "exercises": [
                                {
                                    "id": "w1d1-squat",
                                    "name": "Back Squat",
                                    "category": "main",
                                    "progression": {
                                        "mode": "percent_tm",
                                        "liftKey": "squat",
                                        "percentTm": 0.75,
                                    },
                                    "prescription": {"sets": 5, "reps": 5},
                                    "notes": "",
                                }
                            ],
                        }
                    ],
                },
                {
                    "weekIndex": 2,
                    "days": [
                        {
                            "dayIndex": 1,
                            "label": "周一",
                            "type": "lower_intensity",
                            "exercises": [
                                {
                                    "id": "w2d1-squat",
                                    "name": "Back Squat",
                                    "category": "main",
                                    "progression": {
                                        "mode": "percent_tm",
                                        "liftKey": "squat",
                                        "percentTm": 0.8,
                                    },
                                    "prescription": {"sets": 4, "reps": 4},
                                    "notes": "",
                                }
                            ],
                        }
                    ],
                },
            ],
        },
    }


def _build_custom_strength_cycle_payload_with_conflict(
    *,
    start_date: str | None = None,
    squat_tm: float | None = None,
) -> dict[str, Any]:
    payload = _build_custom_strength_cycle_payload()
    if start_date is not None:
        payload["startDate"] = start_date
    if squat_tm is not None:
        payload["baseLifts"]["squat"]["tm"] = squat_tm
    return payload


@pytest.mark.asyncio
async def test_plan_source_defaults_to_manual_and_can_switch_to_cycle(api_client: tuple[AsyncClient, Any]) -> None:
    client, session_factory = api_client
    await _seed_manual_state(session_factory)

    response = await client.get("/api/plan-source")

    assert response.status_code == 200
    assert response.json()["activeSource"] == "manual"

    put_response = await client.put("/api/plan-source", json={"activeSource": "cycle"})

    assert put_response.status_code == 200
    assert put_response.json()["activeSource"] == "cycle"


@pytest.mark.asyncio
async def test_cycle_presets_endpoint_returns_registered_presets(api_client: tuple[AsyncClient, Any]) -> None:
    client, session_factory = api_client
    await _seed_manual_state(session_factory)

    response = await client.get("/api/cycles/presets")

    assert response.status_code == 200
    preset_keys = {item["key"] for item in response.json()}
    assert {"candito_6week", "madcow_5x5", "texas_method"} <= preset_keys


@pytest.mark.asyncio
async def test_create_cycle_creates_active_cycle_first_snapshot_and_switches_source(api_client: tuple[AsyncClient, Any]) -> None:
    client, session_factory = api_client
    await _seed_manual_state(session_factory)

    response = await client.post("/api/cycles", json=_build_create_cycle_payload())

    assert response.status_code == 200
    payload = response.json()
    assert payload["cycle"]["presetKey"] == "candito_6week"
    assert payload["cycle"]["status"] == "active"
    assert payload["currentWeek"]["weekIndex"] == 1
    assert payload["currentWeek"]["isConfirmed"] is True
    assert payload["effectivePlan"]["Tuesday"]["type"] == "lower_strength"

    async with session_factory() as session:
        source = await session.get(PlanSourceState, 1)
        cycle = (await session.execute(select(ActiveCyclePlan))).scalar_one()
        snapshot = await session.get(CycleWeekSnapshot, {"cycle_id": cycle.id, "week_index": 1})

    assert source is not None
    assert source.active_source == "cycle"
    assert snapshot is not None
    assert snapshot.is_confirmed is True


@pytest.mark.asyncio
async def test_create_custom_strength_cycle_generates_all_week_snapshots(
    api_client: tuple[AsyncClient, Any],
) -> None:
    client, session_factory = api_client
    await _seed_manual_state(session_factory)

    response = await client.post("/api/cycles", json=_build_custom_strength_cycle_payload())

    assert response.status_code == 200
    payload = response.json()
    assert payload["cycle"]["presetKey"] == "custom_strength"
    assert payload["cycle"]["baseLifts"] == {
        "squat": {"tm": 180.0},
        "bench": {"tm": 120.0},
    }
    assert payload["cycle"]["config"]["planType"] == "custom_strength"
    assert payload["effectivePlan"]["Monday"]["exercises"][0]["pct"] == 0.75

    async with session_factory() as session:
        cycle = (await session.execute(select(ActiveCyclePlan))).scalar_one()
        snapshots = (
            await session.execute(
                select(CycleWeekSnapshot)
                .where(CycleWeekSnapshot.cycle_id == cycle.id)
                .order_by(CycleWeekSnapshot.week_index.asc())
            )
        ).scalars().all()

    assert len(snapshots) == 2
    assert snapshots[0].week_index == 1
    assert snapshots[0].is_confirmed is True
    assert snapshots[1].week_index == 2
    assert snapshots[1].is_confirmed is False
    assert snapshots[1].generated_plan["Monday"]["type"] == "lower_intensity"


@pytest.mark.asyncio
async def test_create_cycle_rejects_when_an_open_cycle_already_exists(
    api_client: tuple[AsyncClient, Any],
) -> None:
    client, session_factory = api_client
    await _seed_manual_state(session_factory)

    first_response = await client.post("/api/cycles", json=_build_create_cycle_payload())
    assert first_response.status_code == 200

    second_response = await client.post("/api/cycles", json=_build_create_cycle_payload())

    assert second_response.status_code == 400
    assert second_response.json()["detail"] == "当前存在未结束的活动周期，请先结束后再创建新周期。"

    async with session_factory() as session:
        open_cycles = (
            await session.execute(select(ActiveCyclePlan).where(ActiveCyclePlan.status.in_(("draft", "active"))))
        ).scalars().all()

    assert len(open_cycles) == 1


@pytest.mark.asyncio
async def test_get_active_cycle_returns_current_week_effective_plan(api_client: tuple[AsyncClient, Any]) -> None:
    client, session_factory = api_client
    await _seed_manual_state(session_factory)
    create_response = await client.post("/api/cycles", json=_build_create_cycle_payload())
    cycle_id = create_response.json()["cycle"]["id"]

    response = await client.get("/api/cycles/active")

    assert response.status_code == 200
    payload = response.json()
    assert payload["cycle"]["id"] == cycle_id
    assert payload["currentWeek"]["weekIndex"] == 1
    assert payload["effectivePlan"]["Thursday"]["type"] == "upper_strength"


@pytest.mark.asyncio
async def test_generate_next_week_creates_pending_snapshot_without_advancing_current_week(api_client: tuple[AsyncClient, Any]) -> None:
    client, session_factory = api_client
    await _seed_manual_state(session_factory)
    create_response = await client.post("/api/cycles", json=_build_create_cycle_payload())
    cycle_id = create_response.json()["cycle"]["id"]

    response = await client.post(f"/api/cycles/{cycle_id}/generate-next-week")

    assert response.status_code == 200
    payload = response.json()
    assert payload["weekIndex"] == 2
    assert payload["isConfirmed"] is False

    active_response = await client.get("/api/cycles/active")
    assert active_response.json()["cycle"]["currentWeekIndex"] == 1
    assert active_response.json()["cycle"]["pendingWeekIndex"] == 2


@pytest.mark.asyncio
async def test_generate_next_week_rejects_custom_strength_after_last_precompiled_week(
    api_client: tuple[AsyncClient, Any],
) -> None:
    client, session_factory = api_client
    await _seed_manual_state(session_factory)
    create_response = await client.post("/api/cycles", json=_build_custom_strength_cycle_payload())
    cycle_id = create_response.json()["cycle"]["id"]

    confirm_response = await client.post(f"/api/cycles/{cycle_id}/confirm-next-week")
    assert confirm_response.status_code == 200
    assert confirm_response.json()["cycle"]["currentWeekIndex"] == 2

    response = await client.post(f"/api/cycles/{cycle_id}/generate-next-week")

    assert response.status_code == 400
    assert response.json()["detail"] == "自定义力量周期已到最后一周，不能继续生成下一周。"


@pytest.mark.asyncio
async def test_create_cycle_rejects_custom_strength_when_top_level_start_date_conflicts(
    api_client: tuple[AsyncClient, Any],
) -> None:
    client, session_factory = api_client
    await _seed_manual_state(session_factory)

    response = await client.post(
        "/api/cycles",
        json=_build_custom_strength_cycle_payload_with_conflict(start_date="2026-06-16"),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "自定义力量周期的 startDate 与 config.startDate 不一致。"


@pytest.mark.asyncio
async def test_create_cycle_rejects_custom_strength_when_top_level_base_lifts_conflict(
    api_client: tuple[AsyncClient, Any],
) -> None:
    client, session_factory = api_client
    await _seed_manual_state(session_factory)

    response = await client.post(
        "/api/cycles",
        json=_build_custom_strength_cycle_payload_with_conflict(squat_tm=181),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "自定义力量周期的 baseLifts 与 config.mainLifts 不一致。"


@pytest.mark.asyncio
async def test_confirm_next_week_advances_current_week(api_client: tuple[AsyncClient, Any]) -> None:
    client, session_factory = api_client
    await _seed_manual_state(session_factory)
    create_response = await client.post("/api/cycles", json=_build_create_cycle_payload())
    cycle_id = create_response.json()["cycle"]["id"]
    await client.post(f"/api/cycles/{cycle_id}/generate-next-week")

    response = await client.post(f"/api/cycles/{cycle_id}/confirm-next-week")

    assert response.status_code == 200
    payload = response.json()
    assert payload["cycle"]["currentWeekIndex"] == 2
    assert payload["cycle"]["pendingWeekIndex"] is None
    assert payload["currentWeek"]["weekIndex"] == 2
    assert payload["currentWeek"]["isConfirmed"] is True


@pytest.mark.asyncio
async def test_override_endpoint_updates_effective_plan(api_client: tuple[AsyncClient, Any]) -> None:
    client, session_factory = api_client
    await _seed_manual_state(session_factory)
    create_response = await client.post("/api/cycles", json=_build_create_cycle_payload())
    cycle_id = create_response.json()["cycle"]["id"]

    response = await client.put(
        f"/api/cycles/{cycle_id}/weeks/1/override",
        json={
            "Wednesday": {
                "type": "upper_override",
                "exercises": [
                    {
                        "name": "Pause Squat",
                        "ref1RM": "squat",
                        "pct": 0.65,
                        "sets": 4,
                        "reps": 4,
                    }
                ],
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["effectivePlan"]["Wednesday"]["type"] == "upper_override"
    assert payload["effectivePlan"]["Wednesday"]["exercises"][0]["name"] == "Pause Squat"


@pytest.mark.asyncio
async def test_stop_cycle_switches_back_to_manual_source(api_client: tuple[AsyncClient, Any]) -> None:
    client, session_factory = api_client
    await _seed_manual_state(session_factory)
    create_response = await client.post("/api/cycles", json=_build_create_cycle_payload())
    cycle_id = create_response.json()["cycle"]["id"]

    response = await client.post(f"/api/cycles/{cycle_id}/stop")

    assert response.status_code == 200
    assert response.json()["cycle"]["status"] == "completed"

    source_response = await client.get("/api/plan-source")
    assert source_response.json()["activeSource"] == "manual"


@pytest.mark.asyncio
async def test_manual_weekly_plan_remains_unchanged_after_cycle_create_override_and_stop(
    api_client: tuple[AsyncClient, Any],
) -> None:
    client, session_factory = api_client
    await _seed_manual_state(session_factory)

    manual_before = await client.get("/api/weekly-plan")
    create_response = await client.post("/api/cycles", json=_build_create_cycle_payload())
    cycle_id = create_response.json()["cycle"]["id"]

    override_response = await client.put(
        f"/api/cycles/{cycle_id}/weeks/1/override",
        json={
            "Tuesday": {
                "type": "cycle_override_day",
                "exercises": [
                    {
                        "name": "Cycle Pause Squat",
                        "ref1RM": "squat",
                        "pct": 0.66,
                        "sets": 4,
                        "reps": 4,
                    }
                ],
            }
        },
    )
    stop_response = await client.post(f"/api/cycles/{cycle_id}/stop")
    manual_after = await client.get("/api/weekly-plan")

    assert override_response.status_code == 200
    assert stop_response.status_code == 200
    assert manual_before.json() == manual_after.json()
    assert manual_after.json()["Monday"]["exercises"][0]["name"] == "Manual Squat"
    assert override_response.json()["effectivePlan"]["Tuesday"]["exercises"][0]["name"] == "Cycle Pause Squat"


@pytest.mark.asyncio
async def test_metrics_reads_cycle_plan_when_cycle_source_is_active(api_client: tuple[AsyncClient, Any]) -> None:
    client, session_factory = api_client
    await _seed_manual_state(session_factory)
    await client.put("/api/daily-log/2026-06-01", json={"kcal": 2500, "protein": 150, "sleep": 7, "fatigue": 3})
    await client.post("/api/cycles", json=_build_create_cycle_payload())

    response = await client.get("/api/metrics/daily-summary", params={"date": "2026-06-01"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["today_key"] == "Monday"
    assert payload["today_plan_type"] == "rest"
