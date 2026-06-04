from __future__ import annotations

from copy import deepcopy

import pytest

from backend.plans.custom_strength_definition import normalize_custom_strength_definition


def build_valid_definition() -> dict:
    week_template = {
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
            {**deepcopy(week_template), "weekIndex": 1},
            {**deepcopy(week_template), "weekIndex": 2},
            {**deepcopy(week_template), "weekIndex": 3},
            {**deepcopy(week_template), "weekIndex": 4},
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


def test_normalize_custom_strength_definition_rejects_non_consecutive_week_index() -> None:
    payload = build_valid_definition()
    payload["weeks"][1]["weekIndex"] = 3

    with pytest.raises(ValueError, match="weekIndex"):
        normalize_custom_strength_definition(payload)


def test_normalize_custom_strength_definition_rejects_duplicate_week_index() -> None:
    payload = build_valid_definition()
    payload["weeks"][1]["weekIndex"] = 1

    with pytest.raises(ValueError, match="weekIndex"):
        normalize_custom_strength_definition(payload)


def test_normalize_custom_strength_definition_rejects_duplicate_day_index_in_same_week() -> None:
    payload = build_valid_definition()
    payload["weeks"][0]["days"].append(
        {
            "dayIndex": 1,
            "label": "周三",
            "type": "upper_strength",
            "exercises": [],
        }
    )

    with pytest.raises(ValueError, match="dayIndex"):
        normalize_custom_strength_definition(payload)


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("tm", "abc"),
        ("percentTm", "abc"),
    ],
)
def test_normalize_custom_strength_definition_raises_stable_value_error_for_invalid_number(
    field: str,
    invalid_value: str,
) -> None:
    payload = build_valid_definition()

    if field == "tm":
        payload["mainLifts"]["squat"]["tm"] = invalid_value
    else:
        payload["weeks"][0]["days"][0]["exercises"][0]["progression"]["percentTm"] = invalid_value

    with pytest.raises(ValueError, match=field):
        normalize_custom_strength_definition(payload)


@pytest.mark.parametrize(
    ("mutator", "expected_message", "raw_error_fragment"),
    [
        (
            lambda payload: payload.__setitem__("totalWeeks", "abc"),
            "totalWeeks 必须为合法正整数。",
            "invalid literal for int()",
        ),
        (
            lambda payload: payload.__setitem__("mainLifts", {"squat": 180}),
            "mainLifts.squat 必须为对象。",
            "has no attribute 'get'",
        ),
        (
            lambda payload: payload.__setitem__("weeks", [1, 2, 3, 4]),
            "weeks 的每一项都必须为对象。",
            "has no attribute 'get'",
        ),
        (
            lambda payload: payload["weeks"][0].__setitem__("days", [1]),
            "第 1 周的 days 每一项都必须为对象。",
            "has no attribute 'get'",
        ),
    ],
)
def test_normalize_custom_strength_definition_rejects_invalid_structural_input_with_stable_value_error(
    mutator,
    expected_message: str,
    raw_error_fragment: str,
) -> None:
    payload = build_valid_definition()
    mutator(payload)

    with pytest.raises(ValueError) as exc_info:
        normalize_custom_strength_definition(payload)

    assert str(exc_info.value) == expected_message
    assert raw_error_fragment not in str(exc_info.value)
