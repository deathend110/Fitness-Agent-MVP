from __future__ import annotations

from collections.abc import AsyncIterator
from copy import deepcopy
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.agent.adopt_plan import (
    build_day_plan_replace_proposal,
    build_plan_change_proposal,
    clear_plan_change_proposals,
    commit_plan_proposal,
    commit_validated_plan_change,
    validate_plan_changes,
)
from backend.api import tools as tools_api
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
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'plan-tools.db'}"
    engine, session_factory = create_engine_and_session_factory(database_url)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_get_db_session() -> AsyncIterator:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    clear_plan_change_proposals()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()
    clear_plan_change_proposals()
    await engine.dispose()


def build_weekly_plan() -> dict:
    rest_day = {"type": "rest", "exercises": []}
    return {
        "Monday": {
            "type": "strength",
            "exercises": [
                {
                    "id": "sq",
                    "name": "深蹲",
                    "template": {"loadMode": "percentage", "ref1RM": "squat", "sets": 5, "repsText": "5"},
                    "instance": {"pct": 0.75, "rpe": 8},
                    "ref1RM": "squat",
                    "pct": 0.75,
                    "rpe": 8,
                    "sets": 5,
                    "reps": 5,
                }
            ],
        },
        "Tuesday": deepcopy(rest_day),
        "Wednesday": deepcopy(rest_day),
        "Thursday": deepcopy(rest_day),
        "Friday": deepcopy(rest_day),
        "Saturday": deepcopy(rest_day),
        "Sunday": deepcopy(rest_day),
    }


def build_change(new_value=0.7) -> list[dict]:
    return [{"action": "update", "exerciseName": "深蹲", "field": "pct", "newValue": new_value}]


def build_day_plan_payload() -> dict:
    return {
        "type": "腿日",
        "exercises": [
            {
                "name": "深蹲",
                "tier": "main",
                "template": {
                    "loadMode": "percentage",
                    "ref1RM": "squat",
                    "setType": "straight",
                    "sets": 3,
                    "repsText": "5",
                },
                "instance": {
                    "pct": 0.7,
                    "kg": None,
                    "rpe": 7,
                    "note": "恢复周主项",
                },
                "ref1RM": "squat",
                "pct": 0.7,
                "kg": None,
                "sets": 3,
                "reps": 5,
                "rpe": 7,
                "note": "恢复周主项",
            }
        ],
    }


@pytest.mark.asyncio
async def test_plan_proposal_does_not_write_weekly_plan(api_client: AsyncClient) -> None:
    original_plan = build_weekly_plan()
    assert (await api_client.put("/api/weekly-plan", json=original_plan)).status_code == 200

    response = await api_client.post(
        "/api/tools/plan/propose",
        json={"sessionId": 1, "day": "Monday", "summary": "降低深蹲强度", "changes": build_change()},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["validation"]["ok"] is True
    assert body["card"]["summary"] == "降低深蹲强度"
    assert (await api_client.get("/api/weekly-plan")).json() == original_plan


def test_validate_and_commit_plan_change_requires_user_confirm() -> None:
    plan = build_weekly_plan()
    validation = validate_plan_changes(plan, "Monday", build_change())
    proposal = build_plan_change_proposal(
        current_plan=plan,
        session_id=1,
        day="Monday",
        changes=build_change(),
        summary="降强度",
    )

    blocked = commit_validated_plan_change(plan, proposal.proposal_id, confirmed_by_user=False)
    committed = commit_validated_plan_change(plan, proposal.proposal_id, confirmed_by_user=True)
    repeated = commit_validated_plan_change(committed.next_plan, proposal.proposal_id, confirmed_by_user=True)

    assert validation.ok is True
    assert blocked.ok is False
    assert "用户确认" in blocked.message
    assert committed.ok is True
    assert committed.next_plan["Monday"]["exercises"][0]["pct"] == 0.7
    assert repeated.ok is False
    assert "已处理" in repeated.message


def test_build_day_plan_replace_proposal_preserves_day_plan_payload() -> None:
    plan = build_weekly_plan()

    proposal = build_day_plan_replace_proposal(
        current_plan=plan,
        session_id=1,
        day="Monday",
        summary="改成恢复型腿日",
        day_plan=build_day_plan_payload(),
    )

    assert proposal.kind == "day_plan_replace"
    assert proposal.card["dayPlan"]["exercises"][0]["name"] == "深蹲"
    assert proposal.validation.ok is True


def test_commit_day_plan_replace_overwrites_target_day() -> None:
    plan = build_weekly_plan()
    proposal = build_day_plan_replace_proposal(
        current_plan=plan,
        session_id=1,
        day="Monday",
        summary="改成恢复型腿日",
        day_plan=build_day_plan_payload(),
    )

    committed = commit_plan_proposal(
        current_plan=plan,
        proposal_id=proposal.proposal_id,
        confirmed_by_user=True,
    )

    assert committed.ok is True
    assert committed.next_plan["Monday"]["type"] == "腿日"
    assert committed.next_plan["Monday"]["exercises"][0]["sets"] == 3
    assert committed.next_plan["Monday"]["exercises"][0]["rpe"] == 7


@pytest.mark.asyncio
async def test_plan_commit_endpoint_writes_only_after_confirm(api_client: AsyncClient) -> None:
    original_plan = build_weekly_plan()
    await api_client.put("/api/weekly-plan", json=original_plan)
    proposal = await api_client.post(
        "/api/tools/plan/propose",
        json={"sessionId": 2, "day": "Monday", "summary": "降强度", "changes": build_change()},
    )
    proposal_id = proposal.json()["proposalId"]

    committed = await api_client.post("/api/tools/plan/commit", json={"proposalId": proposal_id})
    repeated = await api_client.post("/api/tools/plan/commit", json={"proposalId": proposal_id})

    assert committed.status_code == 200
    assert committed.json()["ok"] is True
    assert committed.json()["plan"]["Monday"]["exercises"][0]["pct"] == 0.7
    assert repeated.json()["ok"] is False
    assert "已处理" in repeated.json()["message"]


@pytest.mark.asyncio
async def test_plan_propose_endpoint_accepts_day_plan_replace(api_client: AsyncClient) -> None:
    original_plan = build_weekly_plan()
    await api_client.put("/api/weekly-plan", json=original_plan)

    response = await api_client.post(
        "/api/tools/plan/propose",
        json={
            "kind": "day_plan_replace",
            "sessionId": 3,
            "day": "Monday",
            "summary": "改成恢复型腿日",
            "dayPlan": build_day_plan_payload(),
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["validation"]["ok"] is True
    assert body["card"]["kind"] == "day_plan_replace"
    assert body["card"]["dayPlan"]["exercises"][0]["name"] == "深蹲"


@pytest.mark.asyncio
async def test_plan_commit_endpoint_writes_day_plan_replace(api_client: AsyncClient) -> None:
    original_plan = build_weekly_plan()
    await api_client.put("/api/weekly-plan", json=original_plan)

    proposal = await api_client.post(
        "/api/tools/plan/propose",
        json={
            "kind": "day_plan_replace",
            "sessionId": 5,
            "day": "Monday",
            "summary": "改成恢复型腿日",
            "dayPlan": build_day_plan_payload(),
        },
    )
    proposal_id = proposal.json()["proposalId"]

    committed = await api_client.post("/api/tools/plan/commit", json={"proposalId": proposal_id})
    assert committed.status_code == 200
    assert committed.json()["ok"] is True
    assert committed.json()["plan"]["Monday"]["exercises"][0]["name"] == "深蹲"


@pytest.mark.asyncio
async def test_plan_tools_reject_invalid_changes_without_dirty_write(api_client: AsyncClient) -> None:
    original_plan = build_weekly_plan()
    await api_client.put("/api/weekly-plan", json=original_plan)

    invalid = await api_client.post(
        "/api/tools/plan/propose",
        json={"sessionId": 3, "day": "Monday", "summary": "坏参数", "changes": build_change("NaN")},
    )

    assert invalid.status_code == 200
    assert invalid.json()["validation"]["ok"] is False
    assert (await api_client.get("/api/weekly-plan")).json() == original_plan
