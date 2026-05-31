from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.adopt_plan import build_plan_change_proposal
from backend.agent.memory import MemoryRetriever
from backend.db.models import DailyLog, Profile, UploadedFile, WEEKDAY_ORDER, WeeklyPlanDay
from backend.db.seed import DEFAULT_PROFILE_ID


class EmptyToolArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DailyLogToolArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")


class SearchMemoryToolArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = ""
    kind: str | None = None


class ReadFileSummaryToolArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_id: int


class PlanChangeItemArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str
    exerciseName: str
    field: str
    newValue: Any
    oldValue: Any | None = None


class ProposePlanChangeToolArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    day: str
    summary: str = ""
    changes: list[PlanChangeItemArgs]


@dataclass(frozen=True)
class RegisteredTool:
    name: str
    description: str
    args_model: type[BaseModel]
    handler: Callable[[AsyncSession, BaseModel], Any]

    def to_deepseek_tool(self) -> dict[str, Any]:
        schema = self.args_model.model_json_schema()
        schema["additionalProperties"] = False
        schema.setdefault("required", list(schema.get("properties", {}).keys()))
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": schema,
            },
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, tool: RegisteredTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> RegisteredTool:
        if name not in self._tools:
            raise KeyError(name)
        return self._tools[name]

    def to_deepseek_tools(self) -> list[dict[str, Any]]:
        return [tool.to_deepseek_tool() for tool in self._tools.values()]

    async def execute(self, session: AsyncSession, name: str, arguments: dict[str, Any]) -> Any:
        tool = self.get(name)
        parsed_args = tool.args_model.model_validate(arguments)
        return await _maybe_await(tool.handler(session, parsed_args))


class ToolResultSlimmer:
    def __init__(self, max_chars: int = 1000) -> None:
        self.max_chars = max_chars

    def slim(self, tool_name: str, result: Any) -> str:
        if tool_name == "get_weekly_plan" and isinstance(result, dict):
            lines = []
            for day, value in result.items():
                if not isinstance(value, dict):
                    continue
                names = [
                    str(exercise.get("name"))
                    for exercise in value.get("exercises", [])[:6]
                    if isinstance(exercise, dict) and exercise.get("name")
                ]
                lines.append(f"{day} {value.get('type')}: {', '.join(names) if names else '无动作'}")
            content = "；".join(lines)
            if len(content) <= self.max_chars:
                return content
            suffix = f"...[trimmed:{tool_name}]"
            head_length = max(0, self.max_chars - len(suffix))
            return content[:head_length] + suffix
        content = json.dumps(result, ensure_ascii=False, default=str)
        if len(content) <= self.max_chars:
            return content
        suffix = f"...[trimmed:{tool_name}]"
        head_length = max(0, self.max_chars - len(suffix))
        return content[:head_length] + suffix


def build_default_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        RegisteredTool("get_profile", "读取用户档案和训练目标。", EmptyToolArgs, _get_profile)
    )
    registry.register(
        RegisteredTool("get_weekly_plan", "读取本周训练计划。", EmptyToolArgs, _get_weekly_plan)
    )
    registry.register(
        RegisteredTool("get_daily_log", "按日期读取今日日志。", DailyLogToolArgs, _get_daily_log)
    )
    registry.register(
        RegisteredTool("calculate_metrics", "基于当前日志返回轻量训练/恢复指标。", DailyLogToolArgs, _calculate_metrics)
    )
    registry.register(
        RegisteredTool("search_memory", "检索长期记忆。", SearchMemoryToolArgs, _search_memory)
    )
    registry.register(
        RegisteredTool("read_uploaded_file_summary", "读取用户上传文件的真实解析摘要。", ReadFileSummaryToolArgs, _read_uploaded_file_summary)
    )
    registry.register(
        RegisteredTool(
            "propose_plan_change",
            "生成训练计划修改建议卡；只生成 proposal，不直接写入计划。",
            ProposePlanChangeToolArgs,
            _propose_plan_change,
        )
    )
    return registry


async def _get_profile(session: AsyncSession, _args: BaseModel) -> dict[str, Any]:
    profile = await session.get(Profile, DEFAULT_PROFILE_ID)
    if profile is None:
        return {}
    return {
        "basic": profile.basic,
        "oneRm": profile.one_rm,
        "goal": profile.goal,
        "targetWeight": profile.target_weight,
        "notes": profile.notes,
    }


async def _get_weekly_plan(session: AsyncSession, _args: BaseModel) -> dict[str, Any]:
    result = await session.execute(select(WeeklyPlanDay))
    days = {item.day_key: item for item in result.scalars().all()}
    return {
        day_key: {"type": days[day_key].type, "exercises": days[day_key].exercises}
        for day_key in WEEKDAY_ORDER
        if day_key in days
    }


async def _get_daily_log(session: AsyncSession, args: DailyLogToolArgs) -> dict[str, Any]:
    entry = await session.get(DailyLog, args.date)
    if entry is None:
        return {}
    return _dump_daily_log(entry)


async def _calculate_metrics(session: AsyncSession, args: DailyLogToolArgs) -> dict[str, Any]:
    entry = await session.get(DailyLog, args.date)
    if entry is None:
        return {"date": args.date, "available": False}
    return {
        "date": args.date,
        "available": True,
        "fatigue": entry.fatigue,
        "sleep": entry.sleep,
        "kcal": entry.kcal,
        "protein": entry.protein,
        "recoveryFlag": "high_fatigue" if (entry.fatigue or 0) >= 5 else "normal",
    }


async def _search_memory(session: AsyncSession, args: SearchMemoryToolArgs) -> dict[str, Any]:
    items = await MemoryRetriever().retrieve(session, kind=args.kind, query=args.query)
    return {
        "items": [
            {
                "id": item.id,
                "kind": item.kind,
                "content": item.content,
                "confidence": item.confidence,
            }
            for item in items
        ]
    }


async def _read_uploaded_file_summary(session: AsyncSession, args: ReadFileSummaryToolArgs) -> dict[str, Any]:
    uploaded = await session.get(UploadedFile, args.file_id)
    if uploaded is None:
        return {"ok": False, "fileId": args.file_id, "error": "uploaded file not found"}

    summary = dict(uploaded.summary or {})
    text = str(summary.get("text") or "")
    if len(text) > 1500:
        summary["text"] = text[:1500] + "...[trimmed:file_text]"

    return {
        "ok": True,
        "fileId": uploaded.id,
        "name": uploaded.original_name,
        "status": uploaded.parser_status,
        "parserError": uploaded.parser_error,
        "summary": summary,
    }


async def _propose_plan_change(session: AsyncSession, args: ProposePlanChangeToolArgs) -> dict[str, Any]:
    current_plan = await _get_weekly_plan(session, EmptyToolArgs())
    proposal = build_plan_change_proposal(
        current_plan=current_plan,
        session_id=None,
        day=args.day,
        summary=args.summary,
        changes=[item.model_dump() for item in args.changes],
    )
    return {
        "proposal": proposal.card,
        "validation": {
            "ok": proposal.validation.ok,
            "message": proposal.validation.message,
        },
    }


def _dump_daily_log(entry: DailyLog) -> dict[str, Any]:
    return {
        "date": entry.date,
        "weight": entry.weight,
        "kcal": entry.kcal,
        "protein": entry.protein,
        "sleep": entry.sleep,
        "fatigue": entry.fatigue,
        "steps": entry.steps,
        "trainingDone": entry.training_done,
        "trainingNotes": entry.training_notes,
        "tdeeManual": entry.tdee_manual,
    }


async def _maybe_await(value: Any) -> Any:
    if hasattr(value, "__await__"):
        return await value
    return value
