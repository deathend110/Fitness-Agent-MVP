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

    main_lifts = definition.get("mainLifts") if isinstance(definition.get("mainLifts"), dict) else {}
    normalized_main_lifts: dict[str, dict[str, float]] = {}
    for lift_key, lift_value in main_lifts.items():
        if lift_key not in VALID_MAIN_LIFTS:
            continue
        tm_value = float(lift_value.get("tm"))
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
        percent_tm = float(progression.get("percentTm"))
        if percent_tm <= 0:
            raise ValueError("主项动作的 percentTm 必须大于 0。")
        return

    if progression_mode == "percent_tm":
        raise ValueError(f"{category} 动作第一版不能使用 percent_tm。")
