from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.tool_calling import (
    DailyLogToolArgs,
    ProposePlanChangeToolArgs,
    ToolRegistry,
    ToolResultSlimmer,
    build_default_tool_registry,
)
from backend.db.database import create_engine_and_session_factory
from backend.db.models import Base, DailyLog, MemoryItem, Profile, WeeklyPlanDay, utc_now


@pytest_asyncio.fixture
async def db_session(tmp_path: Path) -> AsyncIterator[AsyncSession]:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'tools.db'}"
    engine, session_factory = create_engine_and_session_factory(database_url)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        yield session

    await engine.dispose()


async def seed_tool_state(session: AsyncSession) -> None:
    session.add_all(
        [
            Profile(id=1, basic={"name": "阿杰"}, one_rm={"squat": 150}, goal="增肌", target_weight=86, notes=""),
            WeeklyPlanDay(day_key="Monday", type="strength", exercises=[{"name": "深蹲", "rpe": 8}]),
            DailyLog(date="2026-05-31", fatigue=5, sleep=6.5, training_notes="深蹲速度下降"),
            MemoryItem(kind="safety", content="用户深蹲到底部左膝疼痛。", confidence=0.95, created_at=utc_now()),
        ]
    )
    await session.commit()


def test_default_tool_registry_exports_deepseek_compatible_strict_schema() -> None:
    registry = build_default_tool_registry()
    tools = registry.to_deepseek_tools()
    names = [tool["function"]["name"] for tool in tools]

    assert names == [
        "get_profile",
        "get_weekly_plan",
        "get_daily_log",
        "calculate_metrics",
        "search_memory",
        "read_uploaded_file_summary",
        "propose_plan_change",
        "propose_day_plan_replace",
    ]
    assert all(tool["type"] == "function" for tool in tools)
    assert all(tool["function"]["parameters"]["additionalProperties"] is False for tool in tools)
    assert tools[names.index("get_daily_log")]["function"]["parameters"]["required"] == ["date"]


def test_tool_argument_validation_rejects_unknown_fields_and_invalid_date() -> None:
    with pytest.raises(ValidationError):
        DailyLogToolArgs.model_validate({"date": "20260531"})

    with pytest.raises(ValidationError):
        DailyLogToolArgs.model_validate({"date": "2026-05-31", "extra": True})


@pytest.mark.asyncio
async def test_readonly_tools_execute_and_slim_large_results(db_session: AsyncSession) -> None:
    await seed_tool_state(db_session)
    registry = build_default_tool_registry()

    profile = await registry.execute(db_session, "get_profile", {})
    weekly_plan = await registry.execute(db_session, "get_weekly_plan", {})
    daily_log = await registry.execute(db_session, "get_daily_log", {"date": "2026-05-31"})
    metrics = await registry.execute(db_session, "calculate_metrics", {"date": "2026-05-31"})
    memory = await registry.execute(db_session, "search_memory", {"query": "深蹲", "kind": "safety"})

    assert profile["goal"] == "增肌"
    assert weekly_plan["Monday"]["exercises"][0]["name"] == "深蹲"
    assert daily_log["trainingNotes"] == "深蹲速度下降"
    assert metrics["fatigue"] == 5
    assert memory["items"][0]["kind"] == "safety"

    slimmed = ToolResultSlimmer(max_chars=60).slim("get_weekly_plan", weekly_plan)
    assert len(slimmed) <= 80
    assert "深蹲" in slimmed


@pytest.mark.asyncio
async def test_plan_replace_tool_generates_proposal_card(db_session: AsyncSession) -> None:
    await seed_tool_state(db_session)
    registry = build_default_tool_registry()

    result = await registry.execute(
        db_session,
        "propose_day_plan_replace",
        {
            "day": "Monday",
            "summary": "改成恢复型腿日",
            "dayPlan": {
                "type": "active_recovery",
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
        },
    )

    assert result["proposal"]["kind"] == "day_plan_replace"
    assert result["proposal"]["dayPlan"]["type"] == "active_recovery"
    assert result["proposal"]["dayPlan"]["exercises"][0]["name"] == "深蹲"


def test_unknown_tool_is_rejected() -> None:
    registry = ToolRegistry()

    with pytest.raises(KeyError):
        registry.get("missing_tool")


class TestLiteralEnumConstraints:
    """验证弱模型稳定性加固：关键字符串参数的 Literal 枚举约束正确拒绝非法值。"""

    def test_literal_day_rejects_chinese(self) -> None:
        with pytest.raises(ValidationError):
            ProposePlanChangeToolArgs.model_validate(
                {"day": "周一", "changes": [{"action": "update", "exerciseName": "深蹲", "field": "pct", "newValue": 0.75}]}
            )

    def test_literal_day_rejects_abbrev(self) -> None:
        with pytest.raises(ValidationError):
            ProposePlanChangeToolArgs.model_validate(
                {"day": "Mon", "changes": [{"action": "update", "exerciseName": "深蹲", "field": "pct", "newValue": 0.75}]}
            )

    def test_literal_action_rejects_modify(self) -> None:
        with pytest.raises(ValidationError):
            ProposePlanChangeToolArgs.model_validate(
                {"day": "Monday", "changes": [{"action": "modify", "exerciseName": "深蹲", "field": "pct", "newValue": 0.75}]}
            )

    def test_literal_field_rejects_percentage(self) -> None:
        with pytest.raises(ValidationError):
            ProposePlanChangeToolArgs.model_validate(
                {"day": "Monday", "changes": [{"action": "update", "exerciseName": "深蹲", "field": "percentage", "newValue": 0.75}]}
            )

    def test_literal_accepts_valid_values(self) -> None:
        m = ProposePlanChangeToolArgs.model_validate(
            {"day": "Monday", "changes": [{"action": "update", "exerciseName": "深蹲", "field": "pct", "newValue": 0.75}]}
        )
        assert m.day == "Monday"
        assert m.changes[0].action == "update"
        assert m.changes[0].field == "pct"
