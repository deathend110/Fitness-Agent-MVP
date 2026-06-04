from __future__ import annotations

from copy import deepcopy

from backend.plans.cycle_engine import build_cycle_week_plan, merge_cycle_week_override
from backend.plans.preset_library import get_cycle_preset, list_cycle_presets


def _build_base_lifts(*, squat_tm: float | None = None) -> dict[str, dict[str, float]]:
    return {
        "squat": {"oneRm": 180, "tm": squat_tm},
        "bench": {"oneRm": 120, "tm": 108},
        "deadlift": {"oneRm": 220, "tm": 198},
    }


def test_preset_library_registers_required_strength_templates() -> None:
    presets = {preset.key: preset for preset in list_cycle_presets()}

    assert {"candito_6week", "madcow_5x5", "texas_method"} <= set(presets)
    assert presets["candito_6week"].supportsTm is True
    assert presets["candito_6week"].repeatMode == "fixed_length"
    assert presets["candito_6week"].supportedWeeks == [1, 2, 3, 4, 5, 6]
    assert presets["madcow_5x5"].repeatMode == "repeating"
    assert presets["madcow_5x5"].supportedWeeks == list(range(1, 13))
    assert presets["texas_method"].repeatMode == "repeating"
    assert presets["texas_method"].supportedWeeks == list(range(1, 13))


def test_build_cycle_week_plan_for_candito_week_one_returns_compatible_weekly_plan() -> None:
    weekly_plan = build_cycle_week_plan(
        preset_key="candito_6week",
        week_index=1,
        base_lifts=_build_base_lifts(),
    )

    assert set(weekly_plan) == {
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    }
    assert weekly_plan["Monday"]["type"] == "lower_strength"
    assert weekly_plan["Wednesday"]["type"] == "upper_strength"
    monday_main_lift = weekly_plan["Monday"]["exercises"][0]
    assert monday_main_lift["name"] == "Back Squat"
    assert monday_main_lift["ref1RM"] == "squat"
    assert monday_main_lift["pct"] == 0.8
    assert monday_main_lift["sets"] == 6
    assert monday_main_lift["reps"] == 4
    assert monday_main_lift["template"]["loadMode"] == "percentage"
    assert monday_main_lift["template"]["ref1RM"] == "squat"
    assert monday_main_lift["instance"]["pct"] == 0.8


def test_build_cycle_week_plan_for_madcow_prefers_tm_for_percentage_movements() -> None:
    weekly_plan = build_cycle_week_plan(
        preset_key="madcow_5x5",
        week_index=3,
        base_lifts=_build_base_lifts(squat_tm=162),
    )

    monday_squat = weekly_plan["Monday"]["exercises"][0]
    friday_top_set = weekly_plan["Friday"]["exercises"][0]

    assert monday_squat["ref1RM"] == "squat"
    assert monday_squat["pct"] == 0.8
    assert friday_top_set["pct"] == 0.9
    assert set(monday_squat["instance"]) == {"pct", "kg", "note"}
    assert "sourceMax" not in monday_squat["instance"]
    assert "targetWeight" not in friday_top_set["instance"]


def test_build_cycle_week_plan_for_texas_method_has_hlm_day_type_differences() -> None:
    weekly_plan = build_cycle_week_plan(
        preset_key="texas_method",
        week_index=8,
        base_lifts=_build_base_lifts(),
    )

    assert weekly_plan["Monday"]["type"] == "volume"
    assert weekly_plan["Wednesday"]["type"] == "recovery"
    assert weekly_plan["Friday"]["type"] == "intensity"
    assert weekly_plan["Wednesday"]["exercises"][0]["name"] == "Back Squat"
    assert weekly_plan["Friday"]["exercises"][0]["pct"] > weekly_plan["Wednesday"]["exercises"][0]["pct"]


def test_build_cycle_week_plan_respects_configured_training_days_in_template_order() -> None:
    weekly_plan = build_cycle_week_plan(
        preset_key="candito_6week",
        week_index=1,
        base_lifts=_build_base_lifts(),
        config={"trainingDays": ["Tuesday", "Thursday", "Saturday", "Sunday"]},
    )

    assert weekly_plan["Tuesday"]["type"] == "lower_strength"
    assert weekly_plan["Thursday"]["type"] == "upper_strength"
    assert weekly_plan["Saturday"]["type"] == "lower_power"
    assert weekly_plan["Sunday"]["type"] == "upper_power"
    assert weekly_plan["Monday"] == {"type": "rest", "exercises": []}
    assert weekly_plan["Wednesday"] == {"type": "rest", "exercises": []}


def test_build_cycle_week_plan_keeps_default_days_when_training_days_config_is_invalid() -> None:
    weekly_plan = build_cycle_week_plan(
        preset_key="candito_6week",
        week_index=1,
        base_lifts=_build_base_lifts(),
        config={"trainingDays": ["Tuesday", "Tuesday", "Funday"]},
    )

    assert weekly_plan["Monday"]["type"] == "lower_strength"
    assert weekly_plan["Wednesday"]["type"] == "upper_strength"


def test_merge_cycle_week_override_only_replaces_declared_days() -> None:
    generated = build_cycle_week_plan(
        preset_key="candito_6week",
        week_index=1,
        base_lifts=_build_base_lifts(),
    )
    generated_snapshot = deepcopy(generated)
    override = {
        "Wednesday": {
            "type": "upper_test",
            "exercises": [
                {
                    "name": "Close Grip Bench Press",
                    "ref1RM": "bench",
                    "pct": 0.7,
                    "sets": 4,
                    "reps": 6,
                    "template": {
                        "loadMode": "percentage",
                        "ref1RM": "bench",
                        "setType": "straight",
                        "sets": 4,
                        "repsText": "6",
                    },
                    "instance": {"pct": 0.7},
                }
            ],
        }
    }

    merged = merge_cycle_week_override(generated, override)

    assert merged["Wednesday"]["type"] == "upper_test"
    assert merged["Wednesday"]["exercises"][0]["name"] == "Close Grip Bench Press"
    assert merged["Monday"] == generated_snapshot["Monday"]
    assert merged["Friday"] == generated_snapshot["Friday"]
    assert generated == generated_snapshot


def test_merge_cycle_week_override_normalizes_partial_override_to_canonical_shape() -> None:
    generated = build_cycle_week_plan(
        preset_key="candito_6week",
        week_index=1,
        base_lifts=_build_base_lifts(),
    )

    merged = merge_cycle_week_override(
        generated,
        {
            "Wednesday": {
                "type": "upper_test",
                "exercises": [
                    {
                        "name": "Close Grip Bench Press",
                        "ref1RM": "bench",
                        "pct": 0.72,
                        "sets": 4,
                        "reps": 6,
                    }
                ],
            }
        },
    )

    exercise = merged["Wednesday"]["exercises"][0]
    assert merged["Wednesday"]["type"] == "upper_test"
    assert exercise["id"] == generated["Wednesday"]["exercises"][0]["id"]
    assert exercise["tier"] == "main"
    assert exercise["kg"] is None
    assert exercise["note"] == ""
    assert exercise["template"] == {
        "loadMode": "percentage",
        "ref1RM": "bench",
        "setType": "straight",
        "sets": 4,
        "repsText": "6",
    }
    assert exercise["instance"] == {"pct": 0.72, "kg": None, "note": ""}


def test_merge_cycle_week_override_returns_generated_when_override_is_missing() -> None:
    generated = build_cycle_week_plan(
        preset_key=get_cycle_preset("texas_method").key,
        week_index=1,
        base_lifts=_build_base_lifts(),
    )

    merged = merge_cycle_week_override(generated, None)

    assert merged == generated
