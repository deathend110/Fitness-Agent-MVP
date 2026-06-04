from __future__ import annotations

from copy import deepcopy
from typing import Any

from backend.schemas import CustomStrengthDefinitionSchema


VALID_CATEGORIES = {"main", "variation", "accessory"}
VALID_MAIN_LIFTS = {"squat", "bench", "deadlift", "ohp"}


def normalize_custom_strength_definition(payload: dict[str, Any]) -> dict[str, Any]:
    definition = deepcopy(payload) if isinstance(payload, dict) else {}
    if definition.get("planType") != "custom_strength":
        raise ValueError("planType 必须为 custom_strength。")

    total_weeks = int(definition.get("totalWeeks") or 0)
    weeks = definition.get("weeks") if isinstance(definition.get("weeks"), list) else []
    if total_weeks <= 0 or len(weeks) != total_weeks:
        raise ValueError("totalWeeks 与 weeks 定义数量必须一致。")
    _validate_weeks(weeks, total_weeks)

    main_lifts = definition.get("mainLifts") if isinstance(definition.get("mainLifts"), dict) else {}
    normalized_main_lifts: dict[str, dict[str, float]] = {}
    for lift_key, lift_value in main_lifts.items():
        if lift_key not in VALID_MAIN_LIFTS:
            raise ValueError(f"mainLifts 包含非法主项 key：{lift_key}。")
        tm_value = _parse_positive_float(lift_value.get("tm"), f"{lift_key}.tm")
        if tm_value <= 0:
            raise ValueError(f"{lift_key} 的 TM 必须大于 0。")
        normalized_main_lifts[lift_key] = {"tm": tm_value}

    for week in weeks:
        for day in week.get("days", []):
            for exercise in day.get("exercises", []):
                _validate_custom_strength_exercise(exercise, normalized_main_lifts)

    definition["mainLifts"] = normalized_main_lifts
    normalized_definition = CustomStrengthDefinitionSchema.model_validate(definition).model_dump()
    return normalized_definition


def _validate_weeks(weeks: list[dict[str, Any]], total_weeks: int) -> None:
    week_indexes = [week.get("weekIndex") for week in weeks]
    expected_week_indexes = list(range(1, total_weeks + 1))
    if sorted(week_indexes) != expected_week_indexes:
        raise ValueError("weeks.weekIndex 必须从 1 开始连续且唯一。")

    for week in weeks:
        days = week.get("days") if isinstance(week.get("days"), list) else []
        day_indexes = [day.get("dayIndex") for day in days]
        if len(day_indexes) != len(set(day_indexes)):
            raise ValueError(f"第 {week.get('weekIndex')} 周的 dayIndex 必须唯一。")


def _parse_positive_float(raw_value: Any, field_name: str) -> float:
    try:
        return float(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} 必须为合法数字。") from exc


def _validate_custom_strength_exercise(
    exercise: dict[str, Any],
    main_lifts: dict[str, dict[str, float]],
) -> None:
    category = exercise.get("category")
    if category not in VALID_CATEGORIES:
        raise ValueError("动作 category 非法。")

    progression = exercise.get("progression") if isinstance(exercise.get("progression"), dict) else {}
    progression_mode = progression.get("mode")

    if category == "main":
        if progression_mode != "percent_tm":
            raise ValueError("主项动作必须使用 percent_tm。")
        lift_key = progression.get("liftKey")
        if lift_key not in main_lifts:
            raise ValueError(f"{lift_key} 缺少对应 TM。")
        percent_tm = _parse_positive_float(progression.get("percentTm"), "percentTm")
        if percent_tm <= 0:
            raise ValueError("主项动作的 percentTm 必须大于 0。")
        return

    if progression_mode == "percent_tm":
        raise ValueError(f"{category} 动作第一版不能使用 percent_tm。")
