from __future__ import annotations

from datetime import date
from typing import Any

from backend.db.models import WEEKDAY_ORDER


def build_daily_metrics_summary(
    *,
    profile: dict[str, Any] | None,
    weekly_plan: dict[str, Any],
    daily_log: dict[str, Any] | None,
    target_date: str,
) -> dict[str, Any]:
    today_key = _weekday_key(target_date)
    today_plan = weekly_plan.get(today_key, {"type": "rest", "exercises": []})
    is_training_day = today_plan.get("type") != "rest"
    basic = (profile or {}).get("basic") or {}
    one_rm = (profile or {}).get("oneRm") or {}
    bmr = _calc_bmr(basic)
    training_kcal = _calc_training_kcal(today_plan.get("exercises") or [], one_rm) if is_training_day else 0
    estimated_tdee = round(bmr * 1.2 + training_kcal) if bmr is not None else None
    manual_tdee = _to_nullable_number((daily_log or {}).get("tdeeManual"))
    tdee = manual_tdee if manual_tdee is not None else estimated_tdee
    calorie_intake = _to_nullable_number((daily_log or {}).get("kcal"))
    calorie_delta = calorie_intake - tdee if calorie_intake is not None and tdee is not None else None
    weight = _to_nullable_number(basic.get("weight"))
    protein_intake = _to_nullable_number((daily_log or {}).get("protein"))
    protein_per_kg = _round_to(protein_intake / weight, 1) if protein_intake and weight else None

    # 后端指标服务是后续统一展示、prompt 注入和 Agent 工具判断口径的来源。
    return {
        "today_key": today_key,
        "today_str": target_date,
        "today_plan_type": today_plan.get("type") or "rest",
        "is_training_day": is_training_day,
        "bmr_kcal": bmr,
        "training_kcal": training_kcal,
        "estimated_tdee_kcal": estimated_tdee,
        "tdee_source": "manual" if manual_tdee is not None else "estimated",
        "tdee_kcal": tdee,
        "bmi": _calc_bmi(basic),
        "steps_count": _to_nullable_number((daily_log or {}).get("steps")),
        "calorie_intake_kcal": calorie_intake,
        "calorie_delta_kcal": calorie_delta,
        "calorie_status": _calorie_status(calorie_delta),
        "protein_intake_g": protein_intake,
        "protein_g_per_kg": protein_per_kg,
        "protein_status": _protein_status(protein_per_kg),
        "sleep_hours": _to_nullable_number((daily_log or {}).get("sleep")),
        "fatigue_level": _to_nullable_number((daily_log or {}).get("fatigue")),
    }


def _weekday_key(target_date: str) -> str:
    parsed = date.fromisoformat(target_date)
    return WEEKDAY_ORDER[parsed.weekday()]


def _to_number(value: Any) -> float:
    try:
      parsed = float(value)
    except (TypeError, ValueError):
      return 0.0
    return parsed


def _to_nullable_number(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed


def _round_to(value: float, digits: int = 1) -> float:
    return round(value, digits)


def _calc_bmr(basic: dict[str, Any]) -> int | None:
    weight = _to_nullable_number(basic.get("weight"))
    height = _to_nullable_number(basic.get("height"))
    age = _to_nullable_number(basic.get("age"))
    if weight is None or height is None or age is None:
        return None
    offset = -161 if basic.get("sex") == "female" else 5
    return round(10 * weight + 6.25 * height - 5 * age + offset)


def _calc_bmi(basic: dict[str, Any]) -> float | None:
    weight = _to_nullable_number(basic.get("weight"))
    height = _to_nullable_number(basic.get("height"))
    if weight is None or height is None or height <= 0:
        return None
    height_m = height / 100
    return _round_to(weight / (height_m * height_m), 1)


def _calc_training_kcal(exercises: list[dict[str, Any]], one_rm: dict[str, Any]) -> int:
    total_volume = 0.0
    for exercise in exercises:
        kg = _exercise_kg(exercise, one_rm)
        total_volume += kg * _to_number(exercise.get("sets")) * _to_number(exercise.get("reps"))
    return round(total_volume * 0.1)


def _exercise_kg(exercise: dict[str, Any], one_rm: dict[str, Any]) -> float:
    ref = exercise.get("ref1RM")
    if ref:
        return _to_number(one_rm.get(ref)) * _to_number(exercise.get("pct"))
    return _to_number(exercise.get("kg"))


def _calorie_status(delta: float | None) -> str:
    if delta is None:
        return "unknown"
    if delta > 100:
        return "surplus"
    if delta < -100:
        return "deficit"
    return "balanced"


def _protein_status(protein_per_kg: float | None) -> str:
    if protein_per_kg is None:
        return "unknown"
    return "met" if protein_per_kg >= 1.6 else "low"
