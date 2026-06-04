from __future__ import annotations

from copy import deepcopy

import pytest

from backend.plans.custom_strength_definition import normalize_custom_strength_definition
from backend.plans.custom_strength_engine import build_custom_strength_cycle_weeks


def _build_definition() -> dict:
    return {
        "planType": "custom_strength",
        "name": "自定义四周力量周期",
        "startDate": "2026-06-09",
        "totalWeeks": 2,
        "mainLifts": {
            "squat": {"tm": 180},
            "bench": {"tm": 125},
        },
        "weeks": [
            {
                "weekIndex": 1,
                "days": [
                    {
                        "dayIndex": 1,
                        "label": "周一",
                        "type": "lower_strength",
                        "exercises": [
                            {
                                "id": "w1d1-squat",
                                "name": "Back Squat",
                                "category": "main",
                                "progression": {
                                    "mode": "percent_tm",
                                    "liftKey": "squat",
                                    "percentTm": 0.75,
                                },
                                "prescription": {"sets": 5, "reps": 5},
                                "notes": "主项周一",
                            },
                            {
                                "id": "w1d1-split-squat",
                                "name": "Bulgarian Split Squat",
                                "category": "accessory",
                                "progression": {"mode": "static"},
                                "prescription": {"sets": 3, "reps": 10},
                                "loadText": "自重 + 20kg",
                                "notes": "每侧控制离心",
                            },
                        ],
                    }
                ],
            },
            {
                "weekIndex": 2,
                "days": [
                    {
                        "dayIndex": 1,
                        "label": "周一",
                        "type": "lower_deload",
                        "exercises": [
                            {
                                "id": "w2d1-squat",
                                "name": "Back Squat",
                                "category": "main",
                                "progression": {
                                    "mode": "percent_tm",
                                    "liftKey": "squat",
                                    "percentTm": 0.7,
                                },
                                "prescription": {"sets": 3, "reps": 5},
                                "notes": "降载周",
                            }
                        ],
                    }
                ],
            },
        ],
    }


def test_build_custom_strength_cycle_weeks_generates_multiple_weeks_with_rest_day_defaults() -> None:
    definition = normalize_custom_strength_definition(_build_definition())

    weekly_plan = build_custom_strength_cycle_weeks(definition)

    assert len(weekly_plan) == 2
    assert weekly_plan[0]["Monday"]["type"] == "lower_strength"
    assert weekly_plan[1]["Monday"]["type"] == "lower_deload"
    assert weekly_plan[0]["Tuesday"] == {"type": "rest", "exercises": []}
    assert weekly_plan[1]["Sunday"] == {"type": "rest", "exercises": []}


def test_build_custom_strength_cycle_weeks_materializes_main_load_ref_from_tm() -> None:
    definition = normalize_custom_strength_definition(_build_definition())

    weekly_plan = build_custom_strength_cycle_weeks(definition)
    main_exercise = weekly_plan[0]["Monday"]["exercises"][0]

    assert main_exercise["ref1RM"] == "squat"
    assert main_exercise["pct"] == 0.75
    assert main_exercise["loadRef"] == {"lift": "squat", "value": 180.0, "source": "tm"}
    assert main_exercise["kg"] is None


def test_build_custom_strength_cycle_weeks_keeps_static_accessory_without_percentage_semantics() -> None:
    definition = normalize_custom_strength_definition(_build_definition())

    weekly_plan = build_custom_strength_cycle_weeks(definition)
    accessory = weekly_plan[0]["Monday"]["exercises"][1]

    assert accessory["kg"] is None
    assert accessory["pct"] is None
    assert accessory["loadRef"] is None
    assert accessory["note"] == "自重 + 20kg"
    assert accessory["template"]["loadMode"] == "fixed"
    assert accessory["instance"]["pct"] is None
    assert accessory["instance"]["kg"] is None


def test_build_custom_strength_cycle_weeks_materializes_canonical_fields_for_main_and_variation() -> None:
    definition = normalize_custom_strength_definition(_build_definition())
    definition["weeks"][0]["days"][0]["exercises"].append(
        {
            "name": "Paused Bench Press",
            "category": "variation",
            "progression": {"mode": "static"},
            "prescription": {"sets": 4, "reps": 6},
            "notes": "底部停顿 2 秒",
        }
    )

    weekly_plan = build_custom_strength_cycle_weeks(definition)
    main_exercise = weekly_plan[0]["Monday"]["exercises"][0]
    variation = weekly_plan[0]["Monday"]["exercises"][2]

    assert main_exercise["template"]["setType"] == "straight"
    assert main_exercise["template"]["repsText"] == "5"
    assert main_exercise["instance"]["note"] == "主项周一"

    assert variation["id"] == "custom-w1-d1-2"
    assert variation["tier"] == "variation"
    assert variation["template"]["loadMode"] == "fixed"
    assert variation["template"]["setType"] == "straight"
    assert variation["template"]["repsText"] == "6"
    assert variation["instance"]["note"] == "底部停顿 2 秒"
    assert variation["instance"]["pct"] is None
    assert variation["instance"]["kg"] is None


def test_build_custom_strength_cycle_weeks_rejects_invalid_day_and_exercise_payloads() -> None:
    definition = normalize_custom_strength_definition(_build_definition())
    definition["weeks"][0]["days"] = [
        {
            "dayIndex": 1,
            "type": "lower_strength",
            "exercises": [
                {
                    "name": "Back Squat",
                    "category": "main",
                    "progression": {
                        "mode": "percent_tm",
                        "liftKey": "squat",
                        "percentTm": 0.75,
                    },
                    "prescription": {"sets": 5, "reps": 5},
                },
                "bad-exercise",
            ],
        },
        "bad-day",
    ]

    with pytest.raises(ValueError, match="custom strength"):
        build_custom_strength_cycle_weeks(definition)
