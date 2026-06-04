from __future__ import annotations

from typing import Any

from backend.plans.cycle_engine import _materialize_canonical_exercise

WEEKDAY_ORDER = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)


def build_custom_strength_cycle_weeks(definition: dict[str, Any]) -> list[dict[str, dict[str, Any]]]:
    if not isinstance(definition, dict):
        raise ValueError("custom strength definition 必须是 dict。")
    normalized_definition = definition
    main_lifts = normalized_definition.get("mainLifts") if isinstance(normalized_definition.get("mainLifts"), dict) else {}
    weeks = normalized_definition.get("weeks")
    if not isinstance(weeks, list):
        raise ValueError("custom strength definition.weeks 必须是 list。")
    return [
        _build_week_plan(week=week, main_lifts=main_lifts)
        for week in weeks
    ]


def _build_week_plan(
    *,
    week: dict[str, Any],
    main_lifts: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    # 自定义周期需要产出完整 7 天结构，未定义日统一补 rest，便于沿用现有周计划读写链路。
    if not isinstance(week, dict):
        raise ValueError("custom strength week 必须是 dict。")
    weekly_plan = _build_empty_weekly_plan()
    days = week.get("days")
    if not isinstance(days, list):
        raise ValueError("custom strength week.days 必须是 list。")
    for day in days:
        if not isinstance(day, dict):
            raise ValueError("custom strength day 必须是 dict。")
        day_key = _day_key_from_index(day.get("dayIndex"))
        if day_key is None:
            raise ValueError("custom strength day.dayIndex 必须是 1-7 的整数。")
        exercises = day.get("exercises")
        if not isinstance(exercises, list):
            raise ValueError("custom strength day.exercises 必须是 list。")
        weekly_plan[day_key] = {
            "type": day.get("type") if isinstance(day.get("type"), str) and day.get("type") else "rest",
            "exercises": [
                _materialize_exercise(
                    week_index=week.get("weekIndex"),
                    day_index=day.get("dayIndex"),
                    exercise_index=index,
                    exercise=exercise,
                    main_lifts=main_lifts,
                )
                for index, exercise in enumerate(exercises)
            ],
        }
    return weekly_plan


def _build_empty_weekly_plan() -> dict[str, dict[str, Any]]:
    return {
        day_key: {"type": "rest", "exercises": []}
        for day_key in WEEKDAY_ORDER
    }


def _day_key_from_index(day_index: Any) -> str | None:
    if isinstance(day_index, bool) or not isinstance(day_index, int):
        return None
    if day_index < 1 or day_index > len(WEEKDAY_ORDER):
        return None
    return WEEKDAY_ORDER[day_index - 1]


def _materialize_exercise(
    *,
    week_index: Any,
    day_index: Any,
    exercise_index: int,
    exercise: dict[str, Any],
    main_lifts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if not isinstance(exercise, dict):
        raise ValueError("custom strength exercise 必须是 dict。")
    category = exercise.get("category") if isinstance(exercise.get("category"), str) else "accessory"
    prescription = exercise.get("prescription") if isinstance(exercise.get("prescription"), dict) else {}
    sets = _coerce_int(prescription.get("sets"))
    reps = _coerce_int(prescription.get("reps"))
    note = _resolve_note(exercise)
    # 这里只有主项保留百分比语义；variation/accessory 第一版都按静态动作落成 fixed 结构。
    load_mode = "percentage" if category == "main" else "fixed"
    ref_1rm = _resolve_ref_1rm(exercise, category)
    pct = _resolve_pct(exercise, category)
    load_ref = _build_load_ref(main_lifts=main_lifts, ref_1rm=ref_1rm) if category == "main" else None
    exercise_id = _build_exercise_id(
        raw_id=exercise.get("id"),
        week_index=week_index,
        day_index=day_index,
        exercise_index=exercise_index,
    )
    tier = "main" if category == "main" else ("variation" if category == "variation" else "accessory")
    return _materialize_canonical_exercise(
        exercise_source={
            "id": exercise.get("id"),
            "name": exercise.get("name"),
            "tier": tier,
            "loadMode": load_mode,
            "ref1RM": ref_1rm,
            "pct": pct if load_mode == "percentage" else None,
            "sets": sets,
            "reps": reps,
            "kg": None,
            "note": note,
            "loadRef": load_ref,
        },
        fallback_id=exercise_id,
    )


def _resolve_note(exercise: dict[str, Any]) -> str:
    load_text = exercise.get("loadText")
    if isinstance(load_text, str) and load_text:
        return load_text
    notes = exercise.get("notes")
    if isinstance(notes, str):
        return notes
    return ""


def _resolve_ref_1rm(exercise: dict[str, Any], category: str) -> str | None:
    if category != "main":
        return None
    progression = exercise.get("progression")
    if not isinstance(progression, dict):
        return None
    lift_key = progression.get("liftKey")
    return lift_key if isinstance(lift_key, str) and lift_key else None


def _resolve_pct(exercise: dict[str, Any], category: str) -> float | None:
    if category != "main":
        return None
    progression = exercise.get("progression")
    if not isinstance(progression, dict):
        return None
    percent_tm = progression.get("percentTm")
    if isinstance(percent_tm, bool):
        return None
    if isinstance(percent_tm, int | float):
        return float(percent_tm)
    return None


def _build_load_ref(
    *,
    main_lifts: dict[str, dict[str, Any]],
    ref_1rm: str | None,
) -> dict[str, Any] | None:
    if ref_1rm is None:
        return None
    lift_payload = main_lifts.get(ref_1rm)
    if not isinstance(lift_payload, dict):
        return {"lift": ref_1rm, "value": None, "source": None}
    tm = _read_number(lift_payload.get("tm"))
    if tm is not None:
        return {"lift": ref_1rm, "value": tm, "source": "tm"}
    one_rm = _read_number(lift_payload.get("oneRm"))
    return {"lift": ref_1rm, "value": one_rm, "source": "oneRm" if one_rm is not None else None}


def _build_exercise_id(
    *,
    raw_id: Any,
    week_index: Any,
    day_index: Any,
    exercise_index: int,
) -> str:
    if isinstance(raw_id, str) and raw_id:
        return raw_id
    return f"custom-w{week_index}-d{day_index}-{exercise_index}"


def _coerce_int(value: Any) -> int:
    number = _read_number(value)
    if number is None:
        return 0
    return int(number)


def _read_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    return None
