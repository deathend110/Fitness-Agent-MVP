from __future__ import annotations

import pytest

from backend.plans.custom_strength_definition import normalize_custom_strength_definition


def build_valid_definition() -> dict:
    week_template = [
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
                            "notes": "",
                        }
                    ],
                }
            ],
        }
    ]

    return {
        "planType": "custom_strength",
        "name": "四周力量周期",
        "startDate": "2026-06-09",
        "totalWeeks": 4,
        "mainLifts": {
            "squat": {"tm": 180},
            "bench": {"tm": 125},
        },
        "weeks": [
            {**week_template[0], "weekIndex": 1},
            {**week_template[0], "weekIndex": 2},
            {**week_template[0], "weekIndex": 3},
            {**week_template[0], "weekIndex": 4},
        ],
    }


def test_normalize_custom_strength_definition_accepts_minimum_valid_definition() -> None:
    normalized = normalize_custom_strength_definition(build_valid_definition())

    assert normalized["planType"] == "custom_strength"
    assert normalized["totalWeeks"] == 4
    assert normalized["mainLifts"]["squat"]["tm"] == 180.0
    assert normalized["weeks"][0]["days"][0]["exercises"][0]["category"] == "main"


def test_normalize_custom_strength_definition_rejects_missing_tm_for_referenced_main_lift() -> None:
    payload = build_valid_definition()
    payload["mainLifts"].pop("squat")

    with pytest.raises(ValueError, match="squat.*TM"):
        normalize_custom_strength_definition(payload)


def test_normalize_custom_strength_definition_rejects_invalid_main_lift_key() -> None:
    payload = build_valid_definition()
    payload["mainLifts"]["pullup"] = {"tm": 60}

    with pytest.raises(ValueError, match="pullup"):
        normalize_custom_strength_definition(payload)


def test_normalize_custom_strength_definition_rejects_percent_tm_on_variation() -> None:
    payload = build_valid_definition()
    payload["weeks"][0]["days"][0]["exercises"][0]["category"] = "variation"

    with pytest.raises(ValueError, match="variation.*percent_tm"):
        normalize_custom_strength_definition(payload)


def test_normalize_custom_strength_definition_rejects_total_weeks_mismatch() -> None:
    payload = build_valid_definition()
    payload["totalWeeks"] = 6

    with pytest.raises(ValueError, match="totalWeeks"):
        normalize_custom_strength_definition(payload)
