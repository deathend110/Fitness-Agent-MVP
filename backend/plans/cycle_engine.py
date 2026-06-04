from __future__ import annotations

from copy import deepcopy
from typing import Any

from backend.plans.preset_library import get_cycle_preset

DEFAULT_SET_TYPE = "straight"
WEEKDAY_ORDER = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)


def build_cycle_week_plan(
    *,
    preset_key: str,
    week_index: int,
    base_lifts: dict[str, dict[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    preset = get_cycle_preset(preset_key)
    if week_index not in preset.supportedWeeks:
        raise ValueError(f"{preset_key} 不支持第 {week_index} 周。")

    normalized_base_lifts = deepcopy(base_lifts) if isinstance(base_lifts, dict) else {}
    if preset_key == "candito_6week":
        day_templates = _build_candito_week_templates(week_index)
    elif preset_key == "madcow_5x5":
        day_templates = _build_madcow_week_templates(week_index)
    elif preset_key == "texas_method":
        day_templates = _build_texas_method_templates()
    else:
        raise KeyError(f"未注册的周期模板：{preset_key}")

    weekly_plan = _build_empty_weekly_plan()
    for day_key in WEEKDAY_ORDER:
        template_day = day_templates.get(day_key) or {"type": "rest", "exercises": []}
        weekly_plan[day_key] = {
            "type": template_day["type"],
            "exercises": [
                _materialize_exercise(
                    preset_key=preset_key,
                    week_index=week_index,
                    day_key=day_key,
                    exercise_index=index,
                    exercise_template=exercise_template,
                    base_lifts=normalized_base_lifts,
                )
                for index, exercise_template in enumerate(template_day.get("exercises", []))
            ],
        }
    return weekly_plan


def merge_cycle_week_override(
    generated: dict[str, dict[str, Any]],
    override: dict[str, dict[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    merged = deepcopy(generated) if isinstance(generated, dict) else _build_empty_weekly_plan()
    if not isinstance(override, dict):
        return merged

    for day_key in WEEKDAY_ORDER:
        override_day = override.get(day_key)
        if isinstance(override_day, dict):
            merged[day_key] = deepcopy(override_day)
    return merged


def _build_empty_weekly_plan() -> dict[str, dict[str, Any]]:
    return {
        day_key: {"type": "rest", "exercises": []}
        for day_key in WEEKDAY_ORDER
    }


def _build_candito_week_templates(week_index: int) -> dict[str, dict[str, Any]]:
    week_map: dict[int, dict[str, dict[str, Any]]] = {
        1: {
            "Monday": {
                "type": "lower_strength",
                "exercises": [
                    _pct_exercise("Back Squat", "squat", 0.8, 6, 4),
                    _fixed_exercise("Romanian Deadlift", 3, 6, note="保持髋主导发力"),
                ],
            },
            "Wednesday": {
                "type": "upper_strength",
                "exercises": [
                    _pct_exercise("Bench Press", "bench", 0.8, 6, 4),
                    _fixed_exercise("Barbell Row", 4, 6, note="肩胛先收紧再发力"),
                ],
            },
            "Friday": {
                "type": "lower_power",
                "exercises": [
                    _pct_exercise("Deadlift", "deadlift", 0.78, 4, 4),
                    _fixed_exercise("Front Squat", 3, 5, note="控制离心节奏"),
                ],
            },
            "Saturday": {
                "type": "upper_power",
                "exercises": [
                    _pct_exercise("Bench Press", "bench", 0.75, 5, 4),
                    _fixed_exercise("Pull Up", 4, 6, note="保留 1-2 次余力"),
                ],
            },
        },
        2: {
            "Monday": {"type": "lower_volume", "exercises": [_pct_exercise("Back Squat", "squat", 0.77, 6, 5)]},
            "Wednesday": {"type": "upper_volume", "exercises": [_pct_exercise("Bench Press", "bench", 0.77, 6, 5)]},
            "Friday": {"type": "lower_power", "exercises": [_pct_exercise("Deadlift", "deadlift", 0.8, 4, 4)]},
            "Saturday": {"type": "upper_power", "exercises": [_pct_exercise("Bench Press", "bench", 0.78, 5, 5)]},
        },
        3: {
            "Monday": {"type": "lower_intensity", "exercises": [_pct_exercise("Back Squat", "squat", 0.84, 5, 3)]},
            "Wednesday": {"type": "upper_intensity", "exercises": [_pct_exercise("Bench Press", "bench", 0.84, 5, 3)]},
            "Friday": {"type": "lower_power", "exercises": [_pct_exercise("Deadlift", "deadlift", 0.84, 4, 3)]},
            "Saturday": {"type": "upper_power", "exercises": [_pct_exercise("Bench Press", "bench", 0.8, 4, 4)]},
        },
        4: {
            "Monday": {"type": "lower_intensity", "exercises": [_pct_exercise("Back Squat", "squat", 0.87, 4, 3)]},
            "Wednesday": {"type": "upper_intensity", "exercises": [_pct_exercise("Bench Press", "bench", 0.87, 4, 3)]},
            "Friday": {"type": "lower_power", "exercises": [_pct_exercise("Deadlift", "deadlift", 0.87, 3, 3)]},
            "Saturday": {"type": "upper_power", "exercises": [_pct_exercise("Bench Press", "bench", 0.82, 4, 3)]},
        },
        5: {
            "Monday": {"type": "lower_peak", "exercises": [_pct_exercise("Back Squat", "squat", 0.9, 3, 2)]},
            "Wednesday": {"type": "upper_peak", "exercises": [_pct_exercise("Bench Press", "bench", 0.9, 3, 2)]},
            "Friday": {"type": "lower_peak", "exercises": [_pct_exercise("Deadlift", "deadlift", 0.9, 2, 2)]},
            "Saturday": {"type": "upper_peak", "exercises": [_pct_exercise("Bench Press", "bench", 0.85, 3, 2)]},
        },
        6: {
            "Monday": {"type": "lower_test", "exercises": [_pct_exercise("Back Squat", "squat", 0.92, 2, 1)]},
            "Wednesday": {"type": "upper_test", "exercises": [_pct_exercise("Bench Press", "bench", 0.92, 2, 1)]},
            "Friday": {"type": "pull_test", "exercises": [_pct_exercise("Deadlift", "deadlift", 0.92, 2, 1)]},
        },
    }
    return deepcopy(week_map[week_index])


def _build_madcow_week_templates(week_index: int) -> dict[str, dict[str, Any]]:
    intensity_step = (week_index - 1) * 0.025
    monday_pct = round(0.75 + intensity_step, 3)
    wednesday_pct = round(0.625 + intensity_step, 3)
    friday_pct = round(0.85 + intensity_step, 3)
    return {
        "Monday": {
            "type": "volume_ramp",
            "exercises": [
                _pct_exercise("Back Squat", "squat", monday_pct, 5, 5),
                _pct_exercise("Bench Press", "bench", monday_pct, 5, 5),
                _pct_exercise("Barbell Row", "bench", 0.7 + intensity_step, 5, 5),
            ],
        },
        "Wednesday": {
            "type": "recovery_ramp",
            "exercises": [
                _pct_exercise("Back Squat", "squat", wednesday_pct, 4, 5),
                _pct_exercise("Overhead Press", "bench", 0.65 + intensity_step, 4, 5),
                _fixed_exercise("Back Extension", 3, 10, note="主动恢复，避免做到力竭"),
            ],
        },
        "Friday": {
            "type": "intensity_top_set",
            "exercises": [
                _pct_exercise("Back Squat", "squat", friday_pct, 1, 5),
                _pct_exercise("Bench Press", "bench", friday_pct, 1, 5),
                _pct_exercise("Deadlift", "deadlift", 0.8 + intensity_step, 1, 5),
            ],
        },
    }


def _build_texas_method_templates() -> dict[str, dict[str, Any]]:
    return {
        "Monday": {
            "type": "volume",
            "exercises": [
                _pct_exercise("Back Squat", "squat", 0.85, 5, 5),
                _pct_exercise("Bench Press", "bench", 0.85, 5, 5),
            ],
        },
        "Wednesday": {
            "type": "recovery",
            "exercises": [
                _pct_exercise("Back Squat", "squat", 0.7, 2, 5),
                _fixed_exercise("Chin Up", 3, 8, note="恢复日以动作速度和活动度为主"),
            ],
        },
        "Friday": {
            "type": "intensity",
            "exercises": [
                _pct_exercise("Back Squat", "squat", 0.9, 1, 5),
                _pct_exercise("Bench Press", "bench", 0.9, 1, 5),
                _pct_exercise("Deadlift", "deadlift", 0.9, 1, 3),
            ],
        },
    }


def _pct_exercise(name: str, ref_1rm: str, pct: float, sets: int, reps: int, *, note: str = "") -> dict[str, Any]:
    return {
        "name": name,
        "loadMode": "percentage",
        "ref1RM": ref_1rm,
        "pct": pct,
        "sets": sets,
        "reps": reps,
        "note": note,
    }


def _fixed_exercise(name: str, sets: int, reps: int, *, note: str = "") -> dict[str, Any]:
    return {
        "name": name,
        "loadMode": "fixed",
        "ref1RM": None,
        "pct": None,
        "sets": sets,
        "reps": reps,
        "note": note,
    }


def _materialize_exercise(
    *,
    preset_key: str,
    week_index: int,
    day_key: str,
    exercise_index: int,
    exercise_template: dict[str, Any],
    base_lifts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    load_mode = exercise_template.get("loadMode") or "fixed"
    ref_1rm = exercise_template.get("ref1RM")
    pct = exercise_template.get("pct")
    sets = int(exercise_template["sets"])
    reps = int(exercise_template["reps"])
    note = exercise_template.get("note") or ""
    instance: dict[str, Any] = {
        "pct": pct if load_mode == "percentage" else None,
        "kg": None,
        "note": note,
    }
    if load_mode == "percentage" and isinstance(ref_1rm, str):
        source_max = _resolve_source_max(base_lifts, ref_1rm)
        instance["sourceMax"] = source_max
        instance["targetWeight"] = round(source_max * float(pct), 1) if source_max is not None and pct is not None else None

    return {
        "id": f"{preset_key}-w{week_index}-{day_key.lower()}-{exercise_index}",
        "name": exercise_template["name"],
        "tier": "main" if load_mode == "percentage" else "accessory",
        "template": {
            "loadMode": load_mode,
            "ref1RM": ref_1rm if load_mode == "percentage" else None,
            "setType": DEFAULT_SET_TYPE,
            "sets": sets,
            "repsText": str(reps),
        },
        "instance": instance,
        "ref1RM": ref_1rm if load_mode == "percentage" else None,
        "pct": pct if load_mode == "percentage" else None,
        "sets": sets,
        "reps": reps,
        "kg": None,
        "note": note,
    }


def _resolve_source_max(base_lifts: dict[str, dict[str, Any]], ref_1rm: str) -> float | None:
    lift_payload = base_lifts.get(ref_1rm)
    if not isinstance(lift_payload, dict):
        return None
    tm_value = _read_number(lift_payload.get("tm"))
    if tm_value is not None:
        return tm_value
    return _read_number(lift_payload.get("oneRm"))


def _read_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    return None
