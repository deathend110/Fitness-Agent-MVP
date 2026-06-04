from __future__ import annotations

from copy import deepcopy
from typing import Any

DEFAULT_SET_TYPE = "straight"


def materialize_canonical_exercise(
    *,
    exercise_source: dict[str, Any],
    fallback_id: str,
) -> dict[str, Any]:
    load_mode = exercise_source.get("loadMode") or infer_load_mode(exercise_source)
    ref_1rm = exercise_source.get("ref1RM") if load_mode == "percentage" else None
    pct = read_number(exercise_source.get("pct")) if load_mode == "percentage" else None
    sets = coerce_int(exercise_source.get("sets"), 0)
    reps = coerce_int(exercise_source.get("reps"), 0)
    note = exercise_source.get("note") if isinstance(exercise_source.get("note"), str) else ""
    kg = read_number(exercise_source.get("kg")) if load_mode == "fixed" else None
    tier = exercise_source.get("tier") if isinstance(exercise_source.get("tier"), str) and exercise_source.get("tier") else (
        "main" if load_mode == "percentage" else "accessory"
    )
    # 共享周计划物化逻辑，确保不同引擎输出到同一 canonical contract。
    load_ref = normalize_load_ref(exercise_source.get("loadRef"), ref_1rm, load_mode)
    return {
        "id": exercise_source.get("id") if isinstance(exercise_source.get("id"), str) and exercise_source.get("id") else fallback_id,
        "name": exercise_source.get("name") if isinstance(exercise_source.get("name"), str) else "",
        "tier": tier,
        "template": {
            "loadMode": load_mode,
            "ref1RM": ref_1rm,
            "setType": DEFAULT_SET_TYPE,
            "sets": sets,
            "repsText": str(reps),
        },
        "instance": {
            "pct": pct if load_mode == "percentage" else None,
            "kg": kg if load_mode == "fixed" else None,
            "note": note,
        },
        "ref1RM": ref_1rm,
        "pct": pct if load_mode == "percentage" else None,
        "sets": sets,
        "reps": reps,
        "kg": kg if load_mode == "fixed" else None,
        "note": note,
        "loadRef": load_ref,
    }


def build_load_ref(base_lifts: dict[str, dict[str, Any]], ref_1rm: Any) -> dict[str, Any] | None:
    if not isinstance(ref_1rm, str) or not ref_1rm:
        return None
    lift_payload = base_lifts.get(ref_1rm)
    if not isinstance(lift_payload, dict):
        return {"lift": ref_1rm, "value": None, "source": None}
    tm_value = read_number(lift_payload.get("tm"))
    if tm_value is not None:
        return {"lift": ref_1rm, "value": tm_value, "source": "tm"}
    one_rm_value = read_number(lift_payload.get("oneRm"))
    return {"lift": ref_1rm, "value": one_rm_value, "source": "oneRm" if one_rm_value is not None else None}


def has_consistent_load_ref(raw_load_ref: Any, ref_1rm: str | None) -> bool:
    if ref_1rm is None:
        return not isinstance(raw_load_ref, dict)
    return isinstance(raw_load_ref, dict) and raw_load_ref.get("lift") == ref_1rm


def rebuild_load_ref_from_generated_week(
    *,
    generated_week: dict[str, dict[str, Any]] | None,
    ref_1rm: str | None,
) -> dict[str, Any] | None:
    if ref_1rm is None:
        return None
    if not isinstance(generated_week, dict):
        return {"lift": ref_1rm, "value": None, "source": None}
    # 当 override 只改了 ref1RM 时，优先沿用同周已生成动作上的 loadRef，避免 source/value 漂移。
    for day_plan in generated_week.values():
        if not isinstance(day_plan, dict):
            continue
        exercises = day_plan.get("exercises")
        if not isinstance(exercises, list):
            continue
        for exercise in exercises:
            if not isinstance(exercise, dict):
                continue
            load_ref = exercise.get("loadRef")
            if isinstance(load_ref, dict) and load_ref.get("lift") == ref_1rm:
                return deepcopy(load_ref)
    return {"lift": ref_1rm, "value": None, "source": None}


def infer_load_mode(exercise_source: dict[str, Any]) -> str:
    ref_1rm = exercise_source.get("ref1RM")
    pct = exercise_source.get("pct")
    if isinstance(ref_1rm, str) and ref_1rm:
        return "percentage"
    if read_number(pct) is not None:
        return "percentage"
    return "fixed"


def normalize_load_ref(raw_load_ref: Any, ref_1rm: str | None, load_mode: str) -> dict[str, Any] | None:
    if load_mode != "percentage":
        return None
    if not isinstance(raw_load_ref, dict):
        return {"lift": ref_1rm, "value": None, "source": None} if ref_1rm else None
    lift = raw_load_ref.get("lift") if isinstance(raw_load_ref.get("lift"), str) and raw_load_ref.get("lift") else ref_1rm
    value = read_number(raw_load_ref.get("value"))
    source = raw_load_ref.get("source") if raw_load_ref.get("source") in {"tm", "oneRm"} else None
    if lift is None:
        return None
    return {"lift": lift, "value": value, "source": source}


def coerce_int(value: Any, default: int) -> int:
    number = read_number(value)
    if number is None:
        return default
    return int(number)


def read_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    return None
