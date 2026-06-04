from __future__ import annotations

from copy import deepcopy
from math import isfinite
from typing import Any

from pydantic import ValidationError

from backend.schemas import CustomStrengthDefinitionSchema


VALID_CATEGORIES = {"main", "variation", "accessory"}
VALID_MAIN_LIFTS = {"squat", "bench", "deadlift", "ohp"}


def normalize_custom_strength_definition(payload: dict[str, Any]) -> dict[str, Any]:
    definition = deepcopy(payload) if isinstance(payload, dict) else {}
    if definition.get("planType") != "custom_strength":
        raise ValueError("planType 必须为 custom_strength。")

    total_weeks = _parse_positive_int(definition.get("totalWeeks"), "totalWeeks")
    weeks = definition.get("weeks") if isinstance(definition.get("weeks"), list) else []
    if total_weeks <= 0 or len(weeks) != total_weeks:
        raise ValueError("totalWeeks 与 weeks 定义数量必须一致。")
    _validate_weeks(weeks, total_weeks)
    # normalize 的边界需要对合法输入产出稳定结构，因此按 weekIndex 排序后再继续下游校验与序列化。
    definition["weeks"] = sorted(weeks, key=lambda week: week["weekIndex"])
    weeks = definition["weeks"]

    main_lifts = definition.get("mainLifts")
    if not isinstance(main_lifts, dict):
        raise ValueError("mainLifts 必须为对象。")
    normalized_main_lifts: dict[str, dict[str, float]] = {}
    for lift_key, lift_value in main_lifts.items():
        if lift_key not in VALID_MAIN_LIFTS:
            raise ValueError(f"mainLifts 包含非法主项 key：{lift_key}。")
        if not isinstance(lift_value, dict):
            raise ValueError(f"mainLifts.{lift_key} 必须为对象。")
        tm_value = _parse_positive_float(lift_value.get("tm"), f"{lift_key}.tm")
        if tm_value <= 0:
            raise ValueError(f"{lift_key} 的 TM 必须大于 0。")
        normalized_main_lifts[lift_key] = {"tm": tm_value}

    for week in weeks:
        for day in week.get("days", []):
            exercises = day.get("exercises")
            if not isinstance(exercises, list):
                raise ValueError("exercises 必须为列表。")
            for exercise in exercises:
                _validate_custom_strength_exercise(exercise, normalized_main_lifts)

    definition["mainLifts"] = normalized_main_lifts
    try:
        normalized_definition = CustomStrengthDefinitionSchema.model_validate(definition).model_dump()
    except ValidationError as exc:
        raise ValueError(_format_schema_validation_error(exc)) from None
    return normalized_definition


def _validate_weeks(weeks: list[dict[str, Any]], total_weeks: int) -> None:
    for week in weeks:
        if not isinstance(week, dict):
            raise ValueError("weeks 的每一项都必须为对象。")

    week_indexes = []
    for week in weeks:
        week_indexes.append(_parse_positive_int(week.get("weekIndex"), "weekIndex"))
    expected_week_indexes = list(range(1, total_weeks + 1))
    if sorted(week_indexes) != expected_week_indexes:
        raise ValueError("weeks.weekIndex 必须从 1 开始连续且唯一。")

    for week, week_index in zip(weeks, week_indexes):
        days = week.get("days")
        if not isinstance(days, list):
            raise ValueError(f"第 {week_index} 周的 days 必须为列表。")
        normalized_day_indexes: list[int] = []
        for day in days:
            if not isinstance(day, dict):
                raise ValueError(f"第 {week_index} 周的 days 每一项都必须为对象。")
            normalized_day_indexes.append(_parse_day_index(day.get("dayIndex")))
        if len(normalized_day_indexes) != len(set(normalized_day_indexes)):
            raise ValueError(f"第 {week_index} 周的 dayIndex 必须唯一。")
        # normalize 阶段需要保证 days 顺序稳定，避免合法但乱序的输入继续残留到下游。
        week["days"] = sorted(days, key=lambda day: day["dayIndex"])


def _parse_positive_int(raw_value: Any, field_name: str) -> int:
    if isinstance(raw_value, bool) or not isinstance(raw_value, int):
        raise ValueError(f"{field_name} 必须为合法正整数。")
    if raw_value <= 0:
        raise ValueError(f"{field_name} 必须为合法正整数。")
    return raw_value


def _parse_positive_float(raw_value: Any, field_name: str) -> float:
    if isinstance(raw_value, bool):
        raise ValueError(f"{field_name} 必须为合法数字。")
    try:
        parsed_value = float(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} 必须为合法数字。") from exc
    if not isfinite(parsed_value):
        raise ValueError(f"{field_name} 必须为有限数字。")
    return parsed_value


def _parse_day_index(raw_value: Any) -> int:
    day_index = _parse_positive_int(raw_value, "dayIndex")
    if day_index > 7:
        raise ValueError("dayIndex 必须为 1..7 的合法正整数。")
    return day_index


def _validate_prescription(prescription: Any) -> None:
    if not isinstance(prescription, dict):
        raise ValueError("prescription 必须为对象。")
    _parse_positive_int(prescription.get("sets"), "prescription.sets")
    _parse_positive_int(prescription.get("reps"), "prescription.reps")


def _validate_custom_strength_exercise(
    exercise: dict[str, Any],
    main_lifts: dict[str, dict[str, float]],
) -> None:
    if not isinstance(exercise, dict):
        raise ValueError("exercises 的每一项都必须为对象。")

    category = exercise.get("category")
    if category not in VALID_CATEGORIES:
        raise ValueError("动作 category 非法。")
    _validate_prescription(exercise.get("prescription"))

    progression = exercise.get("progression")
    if not isinstance(progression, dict):
        raise ValueError("progression 必须为对象。")
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
        # 在进入 schema 前就把百分比归一化为稳定 float，避免保留原始字符串。
        progression["percentTm"] = percent_tm
        return

    if progression_mode != "static":
        raise ValueError(f"{category} 动作第一版必须使用 static。")
    # non-main + static 只保留稳定语义，避免残留 liftKey / percentTm 造成误解。
    exercise["progression"] = {"mode": "static"}


def _format_schema_validation_error(exc: ValidationError) -> str:
    first_error = exc.errors()[0] if exc.errors() else None
    if not first_error:
        return "自定义力量计划定义校验失败。"

    location = ".".join(str(part) for part in first_error.get("loc", ()))
    message = first_error.get("msg", "字段校验失败。")
    if location:
        return f"{location}: {message}"
    return f"自定义力量计划定义校验失败：{message}"
