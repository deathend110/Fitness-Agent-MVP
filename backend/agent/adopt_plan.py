from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import math
from typing import Any
from uuid import uuid4

from backend.db.models import WEEKDAY_ORDER

RPE_MIN = 0
RPE_MAX = 10
DEFAULT_SET_TYPE = "straight"
SUCCESS_MESSAGE = "已采纳 AI 建议，训练计划已更新。"
NUMERIC_FIELDS = {"pct", "kg", "sets", "reps", "rpe"}


@dataclass(frozen=True)
class AdoptPlanResult:
    ok: bool
    message: str
    next_plan: dict[str, Any]


@dataclass(frozen=True)
class PlanChangeProposal:
    proposal_id: str
    session_id: int | None
    day: str
    changes: list[dict[str, Any]]
    card: dict[str, Any]
    validation: AdoptPlanResult
    status: str = "pending"


_proposal_store: dict[str, PlanChangeProposal] = {}


def clear_plan_change_proposals() -> None:
    _proposal_store.clear()


def validate_plan_changes(
    weekly_plan: dict[str, Any] | None,
    day: str | None,
    changes: list[dict[str, Any]] | None,
) -> AdoptPlanResult:
    return adopt_plan_change(weekly_plan, day, changes)


def build_plan_change_proposal(
    *,
    current_plan: dict[str, Any],
    session_id: int | None,
    day: str,
    changes: list[dict[str, Any]],
    summary: str = "",
) -> PlanChangeProposal:
    validation = validate_plan_changes(current_plan, day, changes)
    proposal_id = uuid4().hex
    proposal = PlanChangeProposal(
        proposal_id=proposal_id,
        session_id=session_id,
        day=day,
        changes=deepcopy(changes),
        card={
            "proposalId": proposal_id,
            "day": day,
            "summary": summary,
            "changes": deepcopy(changes),
            "status": "pending" if validation.ok else "invalid",
        },
        validation=validation,
        status="pending" if validation.ok else "invalid",
    )
    _proposal_store[proposal_id] = proposal
    return proposal


def commit_validated_plan_change(
    current_plan: dict[str, Any],
    proposal_id: str,
    *,
    confirmed_by_user: bool,
) -> AdoptPlanResult:
    proposal = _proposal_store.get(proposal_id)
    if proposal is None:
        return _build_failure_result(current_plan, "未找到计划修改提议，无法写回。")
    if proposal.status != "pending":
        return _build_failure_result(current_plan, "该计划修改提议已处理，不能重复提交。")
    if not confirmed_by_user:
        return _build_failure_result(current_plan, "计划写回必须来自用户确认。")

    result = adopt_plan_change(current_plan, proposal.day, proposal.changes)
    next_status = "committed" if result.ok else "failed"
    _proposal_store[proposal_id] = PlanChangeProposal(
        proposal_id=proposal.proposal_id,
        session_id=proposal.session_id,
        day=proposal.day,
        changes=proposal.changes,
        card={**proposal.card, "status": next_status},
        validation=proposal.validation,
        status=next_status,
    )
    return result


def _build_failure_result(weekly_plan: dict[str, Any], message: str) -> AdoptPlanResult:
    return AdoptPlanResult(ok=False, message=message, next_plan=weekly_plan)


def _is_plain_object(value: Any) -> bool:
    return isinstance(value, dict)


def _read_string_value(*values: Any) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _read_number_value(*values: Any) -> int | float | None:
    for value in values:
        if isinstance(value, bool):
            continue
        if isinstance(value, int | float):
            return value
    return None


def _coerce_number(value: Any) -> int | float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return value if math.isfinite(value) else None
    if isinstance(value, str) and value.strip():
        try:
            parsed_value = float(value.strip())
        except ValueError:
            return None
        if not math.isfinite(parsed_value):
            return None
        if parsed_value.is_integer():
            return int(parsed_value)
        return parsed_value
    return None


def _normalize_rpe(rpe: int | float | None) -> int | float | None:
    if rpe is None:
        return None
    if rpe < RPE_MIN or rpe > RPE_MAX:
        return None
    return rpe


def _normalize_tier(exercise: dict[str, Any], note: str) -> str:
    direct_tier = _read_string_value(exercise.get("tier"), exercise.get("role"))
    if direct_tier in {"main", "accessory"}:
        return direct_tier
    if "主项" in note or "次主项" in note:
        return "main"
    return "accessory"


def _normalize_planned_exercise(exercise: dict[str, Any], fallback_id: Any = None) -> dict[str, Any]:
    template = deepcopy(exercise.get("template")) if _is_plain_object(exercise.get("template")) else {}
    instance = deepcopy(exercise.get("instance")) if _is_plain_object(exercise.get("instance")) else {}
    name = _read_string_value(exercise.get("name"))
    sets = _read_number_value(exercise.get("sets"), template.get("sets"))
    reps = _read_number_value(exercise.get("reps"))
    note = _read_string_value(exercise.get("note"), instance.get("note"))
    ref_1rm = _read_string_value(exercise.get("ref1RM"), template.get("ref1RM")) or None
    pct = _read_number_value(exercise.get("pct"), instance.get("pct"))
    kg = _read_number_value(exercise.get("kg"), instance.get("kg"))
    rpe = _normalize_rpe(_read_number_value(exercise.get("rpe"), instance.get("rpe")))
    reps_text = (
        str(reps)
        if "reps" in exercise and reps is not None
        else _read_string_value(template.get("repsText")) or (
            str(reps) if reps is not None else ""
        )
    )
    load_mode = (
        "percentage"
        if ref_1rm or _read_string_value(template.get("loadMode")) == "percentage"
        else "fixed"
    )

    # 采纳链路需要保留旧版扁平字段和新版 template/instance，避免 AI 后续建议找不到字段。
    normalized = {
        **exercise,
        "id": exercise.get("id") or fallback_id,
        "name": name,
        "tier": _normalize_tier(exercise, note),
        "template": {
            **template,
            "loadMode": load_mode,
            "ref1RM": ref_1rm if load_mode == "percentage" else None,
            "setType": _read_string_value(template.get("setType")) or DEFAULT_SET_TYPE,
            "sets": sets,
            "repsText": reps_text,
        },
        "instance": {
            **instance,
            "pct": pct if load_mode == "percentage" else None,
            "kg": None if load_mode == "percentage" else kg,
            "rpe": rpe,
            "note": note,
        },
        "ref1RM": ref_1rm if load_mode == "percentage" else None,
        "pct": pct if load_mode == "percentage" else None,
        "kg": None if load_mode == "percentage" else kg,
        "sets": sets,
        "reps": reps,
        "rpe": rpe,
        "note": note,
    }
    return normalized


def _find_exercise_index(exercises: list[dict[str, Any]], exercise_name: str) -> int:
    for index, exercise in enumerate(exercises):
        if exercise.get("name") == exercise_name:
            return index
    return -1


def _normalize_change_value(
    change: dict[str, Any],
    exercise_name: str,
) -> tuple[bool, Any, str]:
    field = _read_string_value(change.get("field"))
    new_value = change.get("newValue")

    if field in NUMERIC_FIELDS:
        number_value = _coerce_number(new_value)
        if number_value is None:
            return (
                False,
                None,
                f"动作“{exercise_name}”的字段“{field}”必须是有效数字，无法采纳该建议。",
            )
        new_value = number_value

    if field == "rpe":
        if new_value < RPE_MIN or new_value > RPE_MAX:
            return (
                False,
                None,
                f"动作“{exercise_name}”的 RPE 必须在 0-10 之间，无法采纳该建议。",
            )

    return True, new_value, ""


def adopt_plan_change(
    weekly_plan: dict[str, Any] | None = None,
    day: str | None = None,
    changes: list[dict[str, Any]] | None = None,
) -> AdoptPlanResult:
    safe_plan = deepcopy(weekly_plan) if _is_plain_object(weekly_plan) else {}
    day_key = day.strip() if isinstance(day, str) else ""

    if not day_key or day_key not in safe_plan or day_key not in WEEKDAY_ORDER:
        return _build_failure_result(
            safe_plan,
            f"未找到 {day_key or '目标日期'} 的训练计划，无法采纳该建议。",
        )

    if not isinstance(changes, list) or len(changes) == 0:
        return _build_failure_result(safe_plan, "当前建议没有可采纳的计划变更。")

    current_day_plan = safe_plan.get(day_key) if _is_plain_object(safe_plan.get(day_key)) else {}
    current_exercises = current_day_plan.get("exercises")
    next_exercises = deepcopy(current_exercises) if isinstance(current_exercises, list) else []

    for change in changes:
        safe_change = change if _is_plain_object(change) else {}
        action = _read_string_value(safe_change.get("action"))
        if action != "update":
            return _build_failure_result(
                safe_plan,
                f"当前仅支持 action 为 update 的现有动作更新建议，暂不支持“{action or '缺失动作'}”。",
            )

        exercise_name = _read_string_value(safe_change.get("exerciseName"))
        field = _read_string_value(safe_change.get("field"))

        if not exercise_name:
            return _build_failure_result(safe_plan, "建议缺少目标动作名称，无法采纳该建议。")

        target_index = _find_exercise_index(next_exercises, exercise_name)
        if target_index == -1:
            return _build_failure_result(
                safe_plan,
                f"未找到 {day_key} 的动作“{exercise_name}”，无法采纳该建议。",
            )

        if not field or field not in next_exercises[target_index]:
            return _build_failure_result(
                safe_plan,
                f"未找到动作“{exercise_name}”的字段“{field or '未知字段'}”，无法采纳该建议。",
            )

        is_valid_value, normalized_value, validation_message = _normalize_change_value(
            safe_change,
            exercise_name,
        )
        if not is_valid_value:
            return _build_failure_result(safe_plan, validation_message)

        changed_exercise = {
            **next_exercises[target_index],
            field: normalized_value,
        }
        next_exercises[target_index] = _normalize_planned_exercise(
            changed_exercise,
            next_exercises[target_index].get("id"),
        )

    return AdoptPlanResult(
        ok=True,
        message=SUCCESS_MESSAGE,
        next_plan={
            **safe_plan,
            day_key: {
                **current_day_plan,
                "exercises": next_exercises,
            },
        },
    )
