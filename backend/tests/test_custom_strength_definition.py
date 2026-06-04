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


@pytest.mark.parametrize("invalid_start_date", ["not-a-date", "2026-06-09T00:00:00"])
def test_normalize_custom_strength_definition_rejects_invalid_start_date_with_stable_value_error(
    invalid_start_date: str,
) -> None:
    payload = build_valid_definition()
    payload["startDate"] = invalid_start_date

    with pytest.raises(ValueError) as exc_info:
        normalize_custom_strength_definition(payload)

    assert str(exc_info.value) == "startDate 必须为 YYYY-MM-DD 格式的合法日期。"


def test_normalize_custom_strength_definition_accepts_valid_start_date_and_keeps_stable_iso_format() -> None:
    normalized = normalize_custom_strength_definition(build_valid_definition())

    assert normalized["startDate"] == "2026-06-09"


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
    exercise = payload["weeks"][0]["days"][0]["exercises"][0]
    exercise["category"] = "variation"
    exercise["referenceLift"] = "squat"

    with pytest.raises(ValueError, match="variation.*static"):
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


def test_normalize_custom_strength_definition_rejects_string_week_index_with_stable_value_error() -> None:
    payload = build_valid_definition()
    payload["weeks"][1]["weekIndex"] = "2"

    with pytest.raises(ValueError) as exc_info:
        normalize_custom_strength_definition(payload)

    assert str(exc_info.value) == "weekIndex 必须为合法正整数。"


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


def test_normalize_custom_strength_definition_rejects_missing_plan_type() -> None:
    payload = build_valid_definition()
    payload.pop("planType")

    with pytest.raises(ValueError, match="planType"):
        normalize_custom_strength_definition(payload)


def test_normalize_custom_strength_definition_rejects_non_list_exercises() -> None:
    payload = build_valid_definition()
    payload["weeks"][0]["days"][0]["exercises"] = 123

    with pytest.raises(ValueError, match="exercises.*列表"):
        normalize_custom_strength_definition(payload)


def test_normalize_custom_strength_definition_rejects_unstable_day_index_type() -> None:
    payload = build_valid_definition()
    payload["weeks"][0]["days"][0]["dayIndex"] = {"bad": 1}

    with pytest.raises(ValueError, match="dayIndex"):
        normalize_custom_strength_definition(payload)


def test_normalize_custom_strength_definition_rejects_non_static_mode_on_variation() -> None:
    payload = build_valid_definition()
    exercise = payload["weeks"][0]["days"][0]["exercises"][0]
    exercise["category"] = "variation"
    exercise["referenceLift"] = "squat"
    exercise["progression"] = {
        "mode": "weird_mode",
    }

    with pytest.raises(ValueError, match="variation.*static"):
        normalize_custom_strength_definition(payload)


def test_normalize_custom_strength_definition_rejects_variation_without_reference_lift_with_stable_value_error() -> None:
    payload = build_valid_definition()
    exercise = payload["weeks"][0]["days"][0]["exercises"][0]
    exercise["category"] = "variation"
    exercise["progression"] = {
        "mode": "static",
    }

    with pytest.raises(ValueError) as exc_info:
        normalize_custom_strength_definition(payload)

    assert str(exc_info.value) == "variation.referenceLift 必填，且必须引用当前 mainLifts 中已定义的主项。"


def test_normalize_custom_strength_definition_accepts_accessory_without_reference_lift() -> None:
    payload = build_valid_definition()
    exercise = payload["weeks"][0]["days"][0]["exercises"][0]
    exercise["category"] = "accessory"
    exercise["progression"] = {
        "mode": "static",
    }

    normalized = normalize_custom_strength_definition(payload)

    exercise = normalized["weeks"][0]["days"][0]["exercises"][0]
    assert exercise["category"] == "accessory"
    assert exercise["progression"]["mode"] == "static"


def test_normalize_custom_strength_definition_normalizes_percent_tm_string_to_float() -> None:
    payload = build_valid_definition()
    payload["weeks"][0]["days"][0]["exercises"][0]["progression"]["percentTm"] = "0.75"

    normalized = normalize_custom_strength_definition(payload)

    percent_tm = normalized["weeks"][0]["days"][0]["exercises"][0]["progression"]["percentTm"]
    assert percent_tm == 0.75
    assert isinstance(percent_tm, float)


def test_normalize_custom_strength_definition_cleans_unexpected_fields_from_main_progression_and_prescription() -> None:
    payload = build_valid_definition()
    exercise = payload["weeks"][0]["days"][0]["exercises"][0]
    exercise["progression"]["unexpected"] = "dirty"
    exercise["prescription"]["unexpected"] = "dirty"

    normalized = normalize_custom_strength_definition(payload)

    normalized_exercise = normalized["weeks"][0]["days"][0]["exercises"][0]
    assert normalized_exercise["progression"] == {
        "mode": "percent_tm",
        "liftKey": "squat",
        "percentTm": 0.75,
    }
    assert normalized_exercise["prescription"] == {"sets": 5, "reps": 5}


def test_normalize_custom_strength_definition_rejects_missing_lift_key_with_stable_field_error() -> None:
    payload = build_valid_definition()
    payload["weeks"][0]["days"][0]["exercises"][0]["progression"].pop("liftKey")

    with pytest.raises(ValueError) as exc_info:
        normalize_custom_strength_definition(payload)

    assert "liftKey" in str(exc_info.value)


def test_normalize_custom_strength_definition_rejects_invalid_reference_lift_on_variation() -> None:
    payload = build_valid_definition()
    exercise = payload["weeks"][0]["days"][0]["exercises"][0]
    exercise["category"] = "variation"
    exercise["progression"] = {"mode": "static"}
    exercise["referenceLift"] = "pullup"

    with pytest.raises(ValueError) as exc_info:
        normalize_custom_strength_definition(payload)

    assert str(exc_info.value) == "referenceLift 必须引用合法主项。"


def test_normalize_custom_strength_definition_rejects_reference_lift_missing_from_current_main_lifts() -> None:
    payload = build_valid_definition()
    payload["mainLifts"].pop("bench")
    payload["weeks"][0]["days"].append(
        {
            "dayIndex": 2,
            "label": "周二",
            "type": "upper_hypertrophy",
            "exercises": [
                {
                    "id": "w1d2-bench-variation",
                    "name": "Paused Bench",
                    "category": "variation",
                    "progression": {"mode": "static"},
                    "prescription": {"sets": 4, "reps": 6},
                    "referenceLift": "bench",
                    "loadText": "RPE 8",
                    "notes": "",
                }
            ],
        }
    )

    with pytest.raises(ValueError) as exc_info:
        normalize_custom_strength_definition(payload)

    assert str(exc_info.value) == "referenceLift 必须引用当前 mainLifts 中已定义的主项。"


def test_normalize_custom_strength_definition_cleans_category_specific_reference_lift_and_load_text_fields() -> None:
    payload = build_valid_definition()
    main_exercise = payload["weeks"][0]["days"][0]["exercises"][0]
    main_exercise["referenceLift"] = "squat"
    main_exercise["loadText"] = "85%"

    payload["weeks"][0]["days"].append(
        {
            "dayIndex": 2,
            "label": "周二",
            "type": "upper_hypertrophy",
            "exercises": [
                {
                    "id": "w1d2-bench-variation",
                    "name": "Paused Bench",
                    "category": "variation",
                    "progression": {"mode": "static"},
                    "prescription": {"sets": 4, "reps": 6},
                    "referenceLift": "bench",
                    "loadText": "RPE 8",
                    "notes": "",
                },
                {
                    "id": "w1d2-row",
                    "name": "Chest Supported Row",
                    "category": "accessory",
                    "progression": {"mode": "static"},
                    "prescription": {"sets": 3, "reps": 12},
                    "referenceLift": "squat",
                    "loadText": "3 x 12",
                    "notes": "",
                },
            ],
        }
    )

    normalized = normalize_custom_strength_definition(payload)

    normalized_main_exercise = normalized["weeks"][0]["days"][0]["exercises"][0]
    normalized_variation = normalized["weeks"][0]["days"][1]["exercises"][0]
    normalized_accessory = normalized["weeks"][0]["days"][1]["exercises"][1]

    assert "referenceLift" not in normalized_main_exercise
    assert "loadText" not in normalized_main_exercise
    assert normalized_variation["referenceLift"] == "bench"
    assert normalized_variation["loadText"] == "RPE 8"
    assert "referenceLift" not in normalized_accessory
    assert normalized_accessory["loadText"] == "3 x 12"


@pytest.mark.parametrize(
    ("mutator", "expected_fragment"),
    [
        (
            lambda payload: payload["weeks"][0]["days"][0].pop("label"),
            "label",
        ),
        (
            lambda payload: payload["weeks"][0]["days"][0]["exercises"][0].pop("id"),
            "id",
        ),
    ],
)
def test_normalize_custom_strength_definition_wraps_schema_validation_error_as_stable_value_error(
    mutator,
    expected_fragment: str,
) -> None:
    payload = build_valid_definition()
    mutator(payload)

    with pytest.raises(ValueError) as exc_info:
        normalize_custom_strength_definition(payload)

    assert isinstance(exc_info.value, ValueError)
    assert expected_fragment in str(exc_info.value)
    assert "ValidationError" not in str(exc_info.value)
    assert "Input should" not in str(exc_info.value)
    assert "Field required" not in str(exc_info.value)


def test_normalize_custom_strength_definition_normalizes_unordered_weeks_to_stable_order() -> None:
    payload = build_valid_definition()
    payload["weeks"] = [
        deepcopy(payload["weeks"][1]),
        deepcopy(payload["weeks"][0]),
        deepcopy(payload["weeks"][2]),
        deepcopy(payload["weeks"][3]),
    ]

    normalized = normalize_custom_strength_definition(payload)

    assert [week["weekIndex"] for week in normalized["weeks"]] == [1, 2, 3, 4]


def test_normalize_custom_strength_definition_normalizes_unordered_days_to_stable_order() -> None:
    payload = build_valid_definition()
    payload["weeks"][0]["days"] = [
        {
            "dayIndex": 2,
            "label": "周二",
            "type": "upper_strength",
            "exercises": [],
        },
        deepcopy(payload["weeks"][0]["days"][0]),
    ]

    normalized = normalize_custom_strength_definition(payload)

    assert [day["dayIndex"] for day in normalized["weeks"][0]["days"]] == [1, 2]


def test_normalize_custom_strength_definition_cleans_percent_tm_fields_from_static_variation_progression() -> None:
    payload = build_valid_definition()
    exercise = payload["weeks"][0]["days"][0]["exercises"][0]
    exercise["category"] = "variation"
    exercise["referenceLift"] = "squat"
    exercise["progression"] = {
        "mode": "static",
        "percentTm": 0.8,
        "liftKey": "squat",
    }

    normalized = normalize_custom_strength_definition(payload)

    progression = normalized["weeks"][0]["days"][0]["exercises"][0]["progression"]
    assert progression == {"mode": "static"}


def test_normalize_custom_strength_definition_cleans_percent_tm_fields_from_static_accessory_progression() -> None:
    payload = build_valid_definition()
    exercise = payload["weeks"][0]["days"][0]["exercises"][0]
    exercise["category"] = "accessory"
    exercise["progression"] = {
        "mode": "static",
        "percentTm": 0.8,
        "liftKey": "squat",
    }

    normalized = normalize_custom_strength_definition(payload)

    progression = normalized["weeks"][0]["days"][0]["exercises"][0]["progression"]
    assert progression == {"mode": "static"}


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


@pytest.mark.parametrize("invalid_value", ["NaN", "inf", "-inf", float("nan"), float("inf"), float("-inf")])
def test_normalize_custom_strength_definition_rejects_non_finite_percent_tm(
    invalid_value,
) -> None:
    payload = build_valid_definition()
    payload["weeks"][0]["days"][0]["exercises"][0]["progression"]["percentTm"] = invalid_value

    with pytest.raises(ValueError, match="percentTm"):
        normalize_custom_strength_definition(payload)


@pytest.mark.parametrize("invalid_day_index", [0, -1])
def test_normalize_custom_strength_definition_rejects_non_positive_day_index(
    invalid_day_index: int,
) -> None:
    payload = build_valid_definition()
    payload["weeks"][0]["days"][0]["dayIndex"] = invalid_day_index

    with pytest.raises(ValueError, match="dayIndex"):
        normalize_custom_strength_definition(payload)


def test_normalize_custom_strength_definition_rejects_day_index_above_week_range() -> None:
    payload = build_valid_definition()
    payload["weeks"][0]["days"][0]["dayIndex"] = 8

    with pytest.raises(ValueError) as exc_info:
        normalize_custom_strength_definition(payload)

    assert str(exc_info.value) == "dayIndex 必须为 1..7 的合法正整数。"


@pytest.mark.parametrize(("field", "invalid_value"), [("tm", True), ("percentTm", True)])
def test_normalize_custom_strength_definition_rejects_boolean_number_fields(
    field: str,
    invalid_value: bool,
) -> None:
    payload = build_valid_definition()

    if field == "tm":
        payload["mainLifts"]["squat"]["tm"] = invalid_value
    else:
        payload["weeks"][0]["days"][0]["exercises"][0]["progression"]["percentTm"] = invalid_value

    with pytest.raises(ValueError, match=field):
        normalize_custom_strength_definition(payload)


@pytest.mark.parametrize("category", ["main", "variation", "accessory"])
@pytest.mark.parametrize(
    ("prescription_value", "expected_message"),
    [
        ({}, "prescription.sets 必须为合法正整数。"),
        ({"sets": "abc", "reps": 5}, "prescription.sets 必须为合法正整数。"),
        ({"sets": 3, "reps": 0}, "prescription.reps 必须为合法正整数。"),
    ],
)
def test_normalize_custom_strength_definition_rejects_invalid_prescription_fields(
    category: str,
    prescription_value: dict,
    expected_message: str,
) -> None:
    payload = build_valid_definition()
    exercise = payload["weeks"][0]["days"][0]["exercises"][0]
    exercise["category"] = category
    exercise["prescription"] = prescription_value
    if category != "main":
        exercise["progression"] = {"mode": "static"}

    with pytest.raises(ValueError) as exc_info:
        normalize_custom_strength_definition(payload)

    assert str(exc_info.value) == expected_message


@pytest.mark.parametrize(
    ("mutator", "expected_message", "raw_error_fragment"),
    [
        (
            lambda payload: payload.__setitem__("totalWeeks", "abc"),
            "totalWeeks 必须为合法正整数。",
            "invalid literal for int()",
        ),
        (
            lambda payload: payload.__setitem__("totalWeeks", 4.8),
            "totalWeeks 必须为合法正整数。",
            "",
        ),
        (
            lambda payload: payload.__setitem__("totalWeeks", True),
            "totalWeeks 必须为合法正整数。",
            "",
        ),
        (
            lambda payload: payload.__setitem__("mainLifts", []),
            "mainLifts 必须为对象。",
            "",
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
            lambda payload: payload["weeks"][0].__setitem__("days", {}),
            "第 1 周的 days 必须为列表。",
            "",
        ),
        (
            lambda payload: payload["weeks"][0].__setitem__("days", [1]),
            "第 1 周的 days 每一项都必须为对象。",
            "has no attribute 'get'",
        ),
        (
            lambda payload: payload["weeks"][0]["days"][0]["exercises"][0].__setitem__("progression", []),
            "progression 必须为对象。",
            "",
        ),
        (
            lambda payload: payload["weeks"][0]["days"][0].__setitem__("exercises", [123]),
            "exercises 的每一项都必须为对象。",
            "",
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
    if raw_error_fragment:
        assert raw_error_fragment not in str(exc_info.value)
