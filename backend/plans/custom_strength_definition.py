from __future__ import annotations

from copy import deepcopy
from datetime import date
from math import isfinite
import re
from typing import Any

from pydantic import ValidationError

from backend.schemas import CustomStrengthDefinitionSchema


VALID_CATEGORIES = {"main", "variation", "accessory"}
VALID_MAIN_LIFTS = {"squat", "bench", "deadlift", "ohp"}
ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def normalize_custom_strength_definition(payload: dict[str, Any]) -> dict[str, Any]:
    definition = deepcopy(payload) if isinstance(payload, dict) else {}
    if definition.get("planType") != "custom_strength":
        raise ValueError("planType 必须为 custom_strength。")

    definition["startDate"] = _parse_iso_start_date(definition.get("startDate"))
    total_weeks = _parse_positive_int(definition.get("totalWeeks"), "totalWeeks")
    weeks = definition.get("weeks")
    if not isinstance(weeks, list):
        raise ValueError("weeks 必须为列表。")
    if total_weeks <= 0 or len(weeks) != total_weeks:
        raise ValueError("totalWeeks 与 weeks 定义数量必须一致。")
    _validate_weeks(weeks, total_weeks)
    # normalize 的边界需要对合法输入产出稳定结构，因此按 weekIndex 排序后再继续下游校验与序列化。
    definition["weeks"] = sorted(weeks, key=lambda week: week["weekIndex"])
    weeks = definition["weeks"]
    referenced_main_lifts = _collect_referenced_main_lifts(weeks)

    main_lifts = definition.get("mainLifts")
    if not isinstance(main_lifts, dict):
        raise ValueError("mainLifts 必须为对象。")
    normalized_main_lifts: dict[str, dict[str, float]] = {}
    for lift_key, lift_value in main_lifts.items():
        if lift_key not in VALID_MAIN_LIFTS:
            raise ValueError(f"mainLifts 包含非法主项 key：{lift_key}。")
        if not isinstance(lift_value, dict):
            raise ValueError(f"mainLifts.{lift_key} 必须为对象。")

        normalized_lift: dict[str, float] = {}
        raw_tm_value = lift_value.get("tm")
        if raw_tm_value is not None:
            tm_value = _parse_positive_float(raw_tm_value, f"{lift_key}.tm")
            if tm_value <= 0:
                raise ValueError(f"{lift_key} 的 TM 必须大于 0。")
            normalized_lift["tm"] = tm_value
        elif lift_key in referenced_main_lifts:
            raise ValueError(f"{lift_key} 缺少对应 TM。")

        if lift_key in referenced_main_lifts and normalized_lift.get("tm", 0) <= 0:
            raise ValueError(f"{lift_key} 的 TM 必须大于 0。")

        normalized_main_lifts[lift_key] = normalized_lift

    for week in weeks:
        for day in week.get("days", []):
            exercises = day.get("exercises")
            if not isinstance(exercises, list):
                raise ValueError("exercises 必须为列表。")
            for exercise in exercises:
                _validate_custom_strength_exercise(exercise, normalized_main_lifts)

    schema_ready_main_lifts = _build_schema_ready_main_lifts(normalized_main_lifts, referenced_main_lifts)
    definition["mainLifts"] = schema_ready_main_lifts
    try:
        normalized_definition = CustomStrengthDefinitionSchema.model_validate(definition).model_dump()
    except ValidationError as exc:
        raise ValueError(_format_schema_validation_error(exc)) from None
    normalized_definition["mainLifts"] = normalized_main_lifts
    _prune_category_specific_exercise_fields(normalized_definition)
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


def _collect_referenced_main_lifts(weeks: list[dict[str, Any]]) -> set[str]:
    referenced_lifts: set[str] = set()
    for week in weeks:
        for day in week.get("days", []):
            exercises = day.get("exercises", [])
            if not isinstance(exercises, list):
                continue
            for exercise in exercises:
                if not isinstance(exercise, dict):
                    continue
                if exercise.get("category") != "main":
                    continue
                progression = exercise.get("progression")
                if not isinstance(progression, dict):
                    continue
                lift_key = progression.get("liftKey")
                if isinstance(lift_key, str) and lift_key:
                    referenced_lifts.add(lift_key)
    return referenced_lifts


def _build_schema_ready_main_lifts(
    normalized_main_lifts: dict[str, dict[str, float]],
    referenced_main_lifts: set[str],
) -> dict[str, dict[str, float]]:
    schema_ready_main_lifts: dict[str, dict[str, float]] = {}
    for lift_key, lift_value in normalized_main_lifts.items():
        if "tm" in lift_value:
            schema_ready_main_lifts[lift_key] = dict(lift_value)
            continue
        if lift_key in referenced_main_lifts:
            schema_ready_main_lifts[lift_key] = dict(lift_value)
            continue
        # 现有 schema 仍要求 tm 必填；这里只为通过结构校验补临时占位，最终返回值会恢复为空对象。
        schema_ready_main_lifts[lift_key] = {"tm": 1.0}
    return schema_ready_main_lifts


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


def _parse_iso_start_date(raw_value: Any) -> str:
    # 计划起始日需要在定义层就拒绝非标准日期字符串，避免 datetime/schema 宽松解析造成脏数据混入。
    if not isinstance(raw_value, str) or not ISO_DATE_PATTERN.fullmatch(raw_value):
        raise ValueError("startDate 必须为 YYYY-MM-DD 格式的合法日期。")
    try:
        return date.fromisoformat(raw_value).isoformat()
    except ValueError as exc:
        raise ValueError("startDate 必须为 YYYY-MM-DD 格式的合法日期。") from exc


def _validate_prescription(prescription: Any) -> dict[str, int]:
    if not isinstance(prescription, dict):
        raise ValueError("prescription 必须为对象。")
    sets = _parse_positive_int(prescription.get("sets"), "prescription.sets")
    reps = _parse_positive_int(prescription.get("reps"), "prescription.reps")
    # 处方只保留稳定必要字段，避免调用方透传脏字段进入持久化结果。
    return {"sets": sets, "reps": reps}


def _validate_custom_strength_exercise(
    exercise: dict[str, Any],
    main_lifts: dict[str, dict[str, float]],
) -> None:
    if not isinstance(exercise, dict):
        raise ValueError("exercises 的每一项都必须为对象。")

    category = exercise.get("category")
    if category not in VALID_CATEGORIES:
        raise ValueError("动作 category 非法。")
    exercise["prescription"] = _validate_prescription(exercise.get("prescription"))
    _normalize_exercise_category_fields(exercise, category, main_lifts)

    progression = exercise.get("progression")
    if not isinstance(progression, dict):
        raise ValueError("progression 必须为对象。")
    progression_mode = progression.get("mode")

    if category == "main":
        if progression_mode != "percent_tm":
            raise ValueError("主项动作必须使用 percent_tm。")
        lift_key = progression.get("liftKey")
        if not isinstance(lift_key, str) or not lift_key:
            raise ValueError("progression.liftKey 必填。")
        if lift_key not in main_lifts:
            raise ValueError(f"{lift_key} 缺少对应 TM。")
        percent_tm = _parse_positive_float(progression.get("percentTm"), "percentTm")
        if percent_tm <= 0:
            raise ValueError("主项动作的 percentTm 必须大于 0。")
        # 主项 progression 在进入 schema 前裁剪为稳定字段集合，避免保留透传脏数据。
        exercise["progression"] = {
            "mode": "percent_tm",
            "liftKey": lift_key,
            "percentTm": percent_tm,
        }
        return

    if progression_mode != "static":
        raise ValueError(f"{category} 动作第一版必须使用 static。")
    # non-main + static 只保留稳定语义，避免残留 liftKey / percentTm 造成误解。
    exercise["progression"] = {"mode": "static"}


def _normalize_exercise_category_fields(
    exercise: dict[str, Any],
    category: str,
    main_lifts: dict[str, dict[str, float]],
) -> None:
    raw_load_text = exercise.get("loadText")
    normalized_load_text = raw_load_text if isinstance(raw_load_text, str) else ""

    if category == "main":
        # 主项负重由 percent_tm 明确表达，referenceLift/loadText 都属于脏冗余字段，直接裁剪。
        exercise.pop("referenceLift", None)
        exercise.pop("loadText", None)
        return

    if category == "variation":
        reference_lift = exercise.get("referenceLift")
        if not isinstance(reference_lift, str) or not reference_lift:
            raise ValueError("variation.referenceLift 必填，且必须引用当前 mainLifts 中已定义的主项。")
        if reference_lift not in VALID_MAIN_LIFTS:
            raise ValueError("referenceLift 必须引用合法主项。")
        if reference_lift not in main_lifts:
            raise ValueError("referenceLift 必须引用当前 mainLifts 中已定义的主项。")
        exercise["referenceLift"] = reference_lift
        exercise["loadText"] = normalized_load_text
        return

    # accessory 允许保留自由负重描述，但不应该冒充“参考主项”。
    exercise.pop("referenceLift", None)
    exercise["loadText"] = normalized_load_text


def _prune_category_specific_exercise_fields(definition: dict[str, Any]) -> None:
    for week in definition.get("weeks", []):
        for day in week.get("days", []):
            for exercise in day.get("exercises", []):
                category = exercise.get("category")
                if category == "main":
                    exercise.pop("referenceLift", None)
                    exercise.pop("loadText", None)
                elif category == "variation":
                    if exercise.get("referenceLift") is None:
                        exercise.pop("referenceLift", None)
                elif category == "accessory":
                    exercise.pop("referenceLift", None)


def _format_schema_validation_error(exc: ValidationError) -> str:
    first_error = exc.errors()[0] if exc.errors() else None
    if not first_error:
        return "自定义力量计划定义校验失败。"

    location = ".".join(str(part) for part in first_error.get("loc", ()))
    error_type = first_error.get("type")
    if error_type == "missing":
        message = "必填字段缺失。"
    else:
        message = "字段校验失败。"
    if location:
        return f"{location}: {message}"
    return f"自定义力量计划定义校验失败：{message}"
