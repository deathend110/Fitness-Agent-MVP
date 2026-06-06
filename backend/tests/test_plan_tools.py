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
from backend.api import chat as chat_api
from backend.api import tools as tools_api
from backend.db.database import create_engine_and_session_factory, get_db_session
from backend.db.models import ActiveCyclePlan, Base, CycleWeekSnapshot, PlanSourceState, WeeklyPlanDay
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


async def _seed_cycle_mode(async_client: AsyncClient) -> int:
    await async_client.put("/api/weekly-plan", json=build_weekly_plan())
    create_response = await async_client.post(
        "/api/cycles",
        json={
            "presetKey": "candito_6week",
            "startDate": "2026-06-01",
            "goal": "力量提升",
            "baseLifts": {
                "squat": {"oneRm": 180, "tm": 162},
                "bench": {"oneRm": 120, "tm": 108},
                "deadlift": {"oneRm": 220, "tm": 198},
            },
            "config": {"trainingDays": ["Tuesday", "Thursday", "Saturday", "Sunday"]},
        },
    )
    return create_response.json()["cycle"]["id"]


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


def build_ambiguous_name_weekly_plan() -> dict:
    plan = build_weekly_plan()
    plan["Monday"]["exercises"] = [
        {
            "id": "sq-top",
            "name": "深蹲",
            "tier": "main",
            "template": {"loadMode": "percentage", "ref1RM": "squat", "sets": 1, "repsText": "1"},
            "instance": {"pct": 0.85, "rpe": 8.5},
            "ref1RM": "squat",
            "pct": 0.85,
            "rpe": 8.5,
            "sets": 1,
            "reps": 1,
        },
        {
            "id": "sq-backoff",
            "name": "深蹲",
            "tier": "main",
            "template": {"loadMode": "fixed", "sets": 3, "repsText": "5"},
            "instance": {"kg": 100, "rpe": 7},
            "kg": 100,
            "rpe": 7,
            "sets": 3,
            "reps": 5,
        },
    ]
    return plan


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


def build_gemini_day_plan_payload() -> dict:
    return {
        "type": "active_recovery/aerobic_core",
        "exercises": [
            {
                "exerciseName": "慢跑/快走",
                "time": 30,
                "unit": "分钟",
                "sets": 1,
            },
            {
                "exerciseName": "平板支撑",
                "time": 60,
                "unit": "秒",
                "sets": 3,
            },
            {
                "exerciseName": "俄罗斯转体",
                "reps": 20,
                "unit": "次",
                "sets": 3,
            },
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


def test_build_day_plan_replace_proposal_inherits_missing_load_block_from_unique_match() -> None:
    plan = build_weekly_plan()

    proposal = build_day_plan_replace_proposal(
        current_plan=plan,
        session_id=1,
        day="Monday",
        summary="把深蹲改轻一点",
        day_plan={
            "type": "strength",
            "exercises": [
                {
                    "name": "深蹲",
                    "tier": "main",
                    "sets": 3,
                    "reps": 5,
                    "rpe": 7,
                    "note": "恢复周主项",
                }
            ],
        },
    )

    exercise = proposal.card["dayPlan"]["exercises"][0]

    assert exercise["template"]["loadMode"] == "percentage"
    assert exercise["template"]["ref1RM"] == "squat"
    assert exercise["ref1RM"] == "squat"
    assert exercise["pct"] == 0.75
    assert exercise["instance"]["pct"] == 0.75
    assert exercise["kg"] is None
    assert "暂沿用原计划负重" in exercise["note"]


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


def test_commit_day_plan_replace_inherits_missing_load_block_from_unique_match() -> None:
    plan = build_weekly_plan()
    proposal = build_day_plan_replace_proposal(
        current_plan=plan,
        session_id=1,
        day="Monday",
        summary="把深蹲改轻一点",
        day_plan={
            "type": "strength",
            "exercises": [
                {
                    "name": "深蹲",
                    "tier": "main",
                    "sets": 3,
                    "reps": 5,
                    "rpe": 7,
                    "note": "恢复周主项",
                }
            ],
        },
    )

    committed = commit_plan_proposal(
        current_plan=plan,
        proposal_id=proposal.proposal_id,
        confirmed_by_user=True,
    )

    exercise = committed.next_plan["Monday"]["exercises"][0]

    assert committed.ok is True
    assert exercise["template"]["loadMode"] == "percentage"
    assert exercise["template"]["ref1RM"] == "squat"
    assert exercise["ref1RM"] == "squat"
    assert exercise["pct"] == 0.75
    assert exercise["instance"]["pct"] == 0.75
    assert exercise["kg"] is None
    assert "暂沿用原计划负重" in exercise["note"]


def test_commit_day_plan_replace_inherits_same_name_percentage_load_source() -> None:
    plan = build_weekly_plan()
    proposal = build_day_plan_replace_proposal(
        current_plan=plan,
        session_id=1,
        day="Monday",
        summary="把深蹲改轻一点",
        day_plan={
            "type": "strength",
            "exercises": [
                {
                    "name": "深蹲",
                    "tier": "main",
                    "sets": 3,
                    "reps": 5,
                    "pct": 0.7,
                    "rpe": 7,
                    "note": "恢复周主项",
                }
            ],
        },
    )

    committed = commit_plan_proposal(
        current_plan=plan,
        proposal_id=proposal.proposal_id,
        confirmed_by_user=True,
    )

    exercise = committed.next_plan["Monday"]["exercises"][0]

    assert committed.ok is True
    assert exercise["template"]["loadMode"] == "percentage"
    assert exercise["template"]["ref1RM"] == "squat"
    assert exercise["ref1RM"] == "squat"
    assert exercise["pct"] == 0.7
    assert exercise["instance"]["pct"] == 0.7
    assert exercise["kg"] is None
    assert "暂沿用原计划负重" not in exercise["note"]


def test_build_day_plan_replace_proposal_only_backfills_source_for_explicit_pct() -> None:
    plan = build_weekly_plan()

    proposal = build_day_plan_replace_proposal(
        current_plan=plan,
        session_id=1,
        day="Monday",
        summary="把深蹲改轻一点",
        day_plan={
            "type": "strength",
            "exercises": [
                {
                    "name": "深蹲",
                    "tier": "main",
                    "pct": 0.7,
                    "sets": 3,
                    "reps": 5,
                    "rpe": 7,
                    "note": "恢复周主项",
                }
            ],
        },
    )

    exercise = proposal.card["dayPlan"]["exercises"][0]

    assert exercise["template"]["loadMode"] == "percentage"
    assert exercise["template"]["ref1RM"] == "squat"
    assert exercise["ref1RM"] == "squat"
    assert exercise["pct"] == 0.7
    assert exercise["instance"]["pct"] == 0.7
    assert "暂沿用原计划负重" not in exercise["note"]


def test_build_day_plan_replace_proposal_does_not_inherit_old_pct_when_only_ref1rm_is_explicit() -> None:
    plan = build_weekly_plan()

    proposal = build_day_plan_replace_proposal(
        current_plan=plan,
        session_id=1,
        day="Monday",
        summary="只指定了参考 1RM",
        day_plan={
            "type": "strength",
            "exercises": [
                {
                    "name": "深蹲",
                    "tier": "main",
                    "ref1RM": "squat",
                    "sets": 3,
                    "reps": 5,
                    "rpe": 7,
                    "note": "恢复周主项",
                }
            ],
        },
    )

    exercise = proposal.card["dayPlan"]["exercises"][0]

    assert exercise["template"]["loadMode"] == "percentage"
    assert exercise["template"]["ref1RM"] == "squat"
    assert exercise["ref1RM"] == "squat"
    assert exercise["pct"] is None
    assert exercise["instance"]["pct"] is None
    assert "暂沿用原计划负重" not in exercise["note"]


def test_build_day_plan_replace_proposal_does_not_inherit_old_kg_when_fixed_mode_has_no_kg() -> None:
    plan = build_weekly_plan()

    proposal = build_day_plan_replace_proposal(
        current_plan=plan,
        session_id=1,
        day="Monday",
        summary="只指定 fixed 模式",
        day_plan={
            "type": "strength",
            "exercises": [
                {
                    "name": "深蹲",
                    "tier": "main",
                    "loadMode": "fixed",
                    "sets": 3,
                    "reps": 5,
                    "rpe": 7,
                    "note": "恢复周主项",
                }
            ],
        },
    )

    exercise = proposal.card["dayPlan"]["exercises"][0]

    assert exercise["template"]["loadMode"] == "fixed"
    assert exercise["template"]["ref1RM"] is None
    assert exercise["ref1RM"] is None
    assert exercise["kg"] is None
    assert exercise["instance"]["kg"] is None
    assert "暂沿用原计划负重" not in exercise["note"]


def test_build_day_plan_replace_proposal_skips_inherit_when_name_is_ambiguous() -> None:
    plan = build_ambiguous_name_weekly_plan()

    proposal = build_day_plan_replace_proposal(
        current_plan=plan,
        session_id=1,
        day="Monday",
        summary="深蹲微调",
        day_plan={
            "type": "strength",
            "exercises": [
                {
                    "name": "深蹲",
                    "tier": "main",
                    "sets": 2,
                    "reps": 5,
                    "note": "动作名重复时不要误继承",
                }
            ],
        },
    )

    exercise = proposal.card["dayPlan"]["exercises"][0]

    assert exercise["template"]["loadMode"] == "fixed"
    assert exercise["template"]["ref1RM"] is None
    assert exercise["ref1RM"] is None
    assert exercise["pct"] is None
    assert exercise["kg"] is None


def test_build_day_plan_replace_proposal_resolves_pct_and_kg_conflict_deterministically() -> None:
    plan = build_weekly_plan()

    proposal = build_day_plan_replace_proposal(
        current_plan=plan,
        session_id=1,
        day="Monday",
        summary="深蹲同时给了百分比和重量",
        day_plan={
            "type": "strength",
            "exercises": [
                {
                    "name": "深蹲",
                    "tier": "main",
                    "ref1RM": "squat",
                    "pct": 0.7,
                    "kg": 100,
                    "sets": 3,
                    "reps": 5,
                    "note": "恢复周主项",
                }
            ],
        },
    )

    exercise = proposal.card["dayPlan"]["exercises"][0]

    assert exercise["template"]["loadMode"] == "percentage"
    assert exercise["ref1RM"] == "squat"
    assert exercise["pct"] == 0.7
    assert exercise["kg"] is None
    assert "kg=100" in exercise["note"]


def test_build_day_plan_replace_proposal_preserves_explicit_fixed_mode_with_kg_only() -> None:
    plan = build_weekly_plan()

    proposal = build_day_plan_replace_proposal(
        current_plan=plan,
        session_id=1,
        day="Monday",
        summary="深蹲显式改成固定重量",
        day_plan={
            "type": "strength",
            "exercises": [
                {
                    "name": "深蹲",
                    "tier": "main",
                    "loadMode": "fixed",
                    "kg": 100,
                    "sets": 3,
                    "reps": 5,
                    "note": "固定重量恢复周主项",
                }
            ],
        },
    )

    exercise = proposal.card["dayPlan"]["exercises"][0]

    assert exercise["template"]["loadMode"] == "fixed"
    assert exercise["ref1RM"] is None
    assert exercise["pct"] is None
    assert exercise["kg"] == 100
    assert exercise["instance"]["kg"] == 100


def test_build_day_plan_replace_proposal_preserves_explicit_percentage_mode_with_kg_conflict_note() -> None:
    plan = build_weekly_plan()

    proposal = build_day_plan_replace_proposal(
        current_plan=plan,
        session_id=1,
        day="Monday",
        summary="深蹲显式百分比但混入固定重量",
        day_plan={
            "type": "strength",
            "exercises": [
                {
                    "name": "深蹲",
                    "tier": "main",
                    "loadMode": "percentage",
                    "kg": 100,
                    "sets": 3,
                    "reps": 5,
                    "note": "混合信号",
                }
            ],
        },
    )

    exercise = proposal.card["dayPlan"]["exercises"][0]

    assert exercise["template"]["loadMode"] == "percentage"
    assert exercise["ref1RM"] == "squat"
    assert exercise["pct"] is None
    assert exercise["kg"] is None
    assert "kg=100" in exercise["note"]


def test_build_day_plan_replace_proposal_preserves_explicit_fixed_mode_with_pct_conflict_note() -> None:
    plan = build_weekly_plan()

    proposal = build_day_plan_replace_proposal(
        current_plan=plan,
        session_id=1,
        day="Monday",
        summary="深蹲显式固定重量但混入百分比",
        day_plan={
            "type": "strength",
            "exercises": [
                {
                    "name": "深蹲",
                    "tier": "main",
                    "loadMode": "fixed",
                    "pct": 0.7,
                    "kg": 100,
                    "sets": 3,
                    "reps": 5,
                    "note": "混合信号",
                }
            ],
        },
    )

    exercise = proposal.card["dayPlan"]["exercises"][0]

    assert exercise["template"]["loadMode"] == "fixed"
    assert exercise["ref1RM"] is None
    assert exercise["pct"] is None
    assert exercise["kg"] == 100
    assert exercise["instance"]["kg"] == 100
    assert "pct=0.7" in exercise["note"]


def test_gemini_style_day_plan_replace_preserves_name_and_duration_note() -> None:
    plan = build_weekly_plan()
    proposal = build_day_plan_replace_proposal(
        current_plan=plan,
        session_id=1,
        day="Monday",
        summary="改成有氧加核心恢复",
        day_plan=build_gemini_day_plan_payload(),
    )

    committed = commit_plan_proposal(
        current_plan=plan,
        proposal_id=proposal.proposal_id,
        confirmed_by_user=True,
    )

    first_exercise = proposal.card["dayPlan"]["exercises"][0]
    committed_first_exercise = committed.next_plan["Monday"]["exercises"][0]
    committed_second_exercise = committed.next_plan["Monday"]["exercises"][1]

    assert proposal.validation.ok is True
    assert first_exercise["name"] == "慢跑/快走"
    assert "30 分钟" in first_exercise["note"]
    assert committed.ok is True
    assert committed_first_exercise["name"] == "慢跑/快走"
    assert "30 分钟" in committed_first_exercise["note"]
    assert committed_second_exercise["name"] == "平板支撑"
    assert "60 秒" in committed_second_exercise["note"]


def test_rest_day_additive_field_changes_are_upgraded_to_day_plan_replace() -> None:
    plan = build_weekly_plan()
    proposal = build_plan_change_proposal(
        current_plan=plan,
        session_id=1,
        day="Tuesday",
        summary="把休息日改成有氧加核心恢复。",
        changes=[
            {
                "action": "add",
                "exerciseName": "坡度步行",
                "field": "exercises",
                "newValue": "30分钟",
                "oldValue": None,
            },
            {
                "action": "add",
                "exerciseName": "平板支撑",
                "field": "exercises",
                "newValue": "3组x60秒",
                "oldValue": None,
            },
            {
                "action": "add",
                "exerciseName": "俄罗斯转体",
                "field": "exercises",
                "newValue": "3组x20次",
                "oldValue": None,
            },
        ],
    )

    committed = commit_plan_proposal(
        current_plan=plan,
        proposal_id=proposal.proposal_id,
        confirmed_by_user=True,
    )

    assert proposal.kind == "day_plan_replace"
    assert proposal.validation.ok is True
    assert proposal.card["status"] == "pending"
    assert proposal.card["dayPlan"]["type"] == "active_recovery"
    assert proposal.card["dayPlan"]["exercises"][0]["name"] == "坡度步行"
    assert "30分钟" in proposal.card["dayPlan"]["exercises"][0]["note"]
    assert committed.ok is True
    assert committed.next_plan["Tuesday"]["exercises"][1]["name"] == "平板支撑"


def test_rest_day_mixed_gemini_fields_still_upgrade_to_day_plan_replace() -> None:
    plan = build_weekly_plan()
    proposal = build_plan_change_proposal(
        current_plan=plan,
        session_id=1,
        day="Tuesday",
        summary="把周二改成有氧与核心恢复日。",
        changes=[
            {
                "action": "replace",
                "exerciseName": "有氧（低强度恒速）",
                "field": "sets/reps/note",
                "newValue": "30-40分钟，心率控制在130-140bpm之间",
                "oldValue": None,
            },
            {
                "action": "add",
                "exerciseName": "死虫式",
                "field": "sets/reps",
                "newValue": "3组 x 16次",
                "oldValue": None,
            },
        ],
    )

    assert proposal.kind == "day_plan_replace"
    assert proposal.validation.ok is True
    assert proposal.card["dayPlan"]["exercises"][0]["name"] == "有氧（低强度恒速）"
    assert "30-40分钟" in proposal.card["dayPlan"]["exercises"][0]["note"]


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
async def test_plan_commit_endpoint_updates_matching_chat_message_suggestion_status(
    api_client: AsyncClient,
) -> None:
    original_plan = build_weekly_plan()
    await api_client.put("/api/weekly-plan", json=original_plan)
    session_id = (await api_client.post("/api/chat/sessions", json={"title": "proposal-status-sync"})).json()["id"]

    proposal = await api_client.post(
        "/api/tools/plan/propose",
        json={"sessionId": session_id, "day": "Monday", "summary": "降强度", "changes": build_change()},
    )
    proposal_id = proposal.json()["proposalId"]
    proposal_card = proposal.json()["card"]

    message_response = await api_client.post(
        f"/api/chat/sessions/{session_id}/messages",
        json={
            "role": "assistant",
            "content": "已生成一张周一调整卡，请确认。",
            "suggestion": proposal_card,
            "attachments": [],
        },
    )
    assert message_response.status_code == 200

    committed = await api_client.post("/api/tools/plan/commit", json={"proposalId": proposal_id})
    assert committed.status_code == 200
    assert committed.json()["ok"] is True

    messages_response = await api_client.get(f"/api/chat/sessions/{session_id}/messages")
    messages = messages_response.json()
    assert messages[-1]["suggestion"]["proposalId"] == proposal_id
    assert messages[-1]["suggestion"]["status"] == "committed"


@pytest.mark.asyncio
async def test_plan_ignore_endpoint_updates_matching_chat_message_suggestion_status(
    api_client: AsyncClient,
) -> None:
    original_plan = build_weekly_plan()
    await api_client.put("/api/weekly-plan", json=original_plan)
    session_id = (await api_client.post("/api/chat/sessions", json={"title": "proposal-status-ignore"})).json()["id"]

    proposal = await api_client.post(
        "/api/tools/plan/propose",
        json={"sessionId": session_id, "day": "Monday", "summary": "降强度", "changes": build_change()},
    )
    proposal_id = proposal.json()["proposalId"]
    proposal_card = proposal.json()["card"]

    message_response = await api_client.post(
        f"/api/chat/sessions/{session_id}/messages",
        json={
            "role": "assistant",
            "content": "已生成一张周一调整卡，请确认。",
            "suggestion": proposal_card,
            "attachments": [],
        },
    )
    assert message_response.status_code == 200

    ignored = await api_client.post("/api/tools/plan/ignore", json={"proposalId": proposal_id})
    assert ignored.status_code == 200
    assert ignored.json()["ok"] is True

    messages_response = await api_client.get(f"/api/chat/sessions/{session_id}/messages")
    messages = messages_response.json()
    assert messages[-1]["suggestion"]["proposalId"] == proposal_id
    assert messages[-1]["suggestion"]["status"] == "ignored"


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


@pytest.mark.asyncio
async def test_plan_propose_uses_cycle_effective_plan_when_cycle_source_is_active(api_client: AsyncClient) -> None:
    await _seed_cycle_mode(api_client)

    response = await api_client.post(
        "/api/tools/plan/propose",
        json={"sessionId": 8, "day": "Tuesday", "summary": "降低周期深蹲强度", "changes": [{"action": "update", "exerciseName": "Back Squat", "field": "pct", "newValue": 0.76}]},
    )

    assert response.status_code == 200
    assert response.json()["validation"]["ok"] is True


@pytest.mark.asyncio
async def test_plan_commit_in_cycle_mode_writes_snapshot_override_and_not_manual_weekly_plan(api_client: AsyncClient) -> None:
    cycle_id = await _seed_cycle_mode(api_client)
    proposal = await api_client.post(
        "/api/tools/plan/propose",
        json={"sessionId": 9, "day": "Tuesday", "summary": "降低周期深蹲强度", "changes": [{"action": "update", "exerciseName": "Back Squat", "field": "pct", "newValue": 0.76}]},
    )
    proposal_id = proposal.json()["proposalId"]

    committed = await api_client.post("/api/tools/plan/commit", json={"proposalId": proposal_id})

    assert committed.status_code == 200
    assert committed.json()["ok"] is True
    assert committed.json()["plan"]["Tuesday"]["exercises"][0]["pct"] == 0.76

    current_plan = await api_client.get("/api/weekly-plan")
    assert current_plan.json()["Monday"]["exercises"][0]["name"] == "深蹲"

    active_cycle = await api_client.get("/api/cycles/active")
    assert active_cycle.json()["cycle"]["id"] == cycle_id
    assert active_cycle.json()["currentWeek"]["overridePlan"]["Tuesday"]["exercises"][0]["pct"] == 0.76
