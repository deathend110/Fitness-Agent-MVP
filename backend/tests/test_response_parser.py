from backend.agent.response_parser import parse_ai_response


def test_parse_ai_response_splits_plain_text_and_structured_suggestion():
    result = parse_ai_response(
        """
        今天建议先把主项容量降一点。
        ---JSON---
        {"day":"Monday","summary":"降低训练量","changes":[{"exerciseId":"sq-main","sets":4}]}
        """
    )

    assert result == {
        "text": "今天建议先把主项容量降一点。",
        "suggestion": {
            "day": "Monday",
            "summary": "降低训练量",
            "changes": [{"exerciseId": "sq-main", "sets": 4}],
        },
    }


def test_parse_ai_response_falls_back_to_raw_text_when_json_is_invalid():
    raw_content = "今天建议保守一点。---JSON---{invalid json}"

    result = parse_ai_response(raw_content)

    assert result == {
        "text": raw_content,
        "suggestion": None,
    }


def test_parse_ai_response_returns_trimmed_plain_text_when_separator_missing():
    result = parse_ai_response("  只返回自然语言建议。  ")

    assert result == {
        "text": "只返回自然语言建议。",
        "suggestion": None,
    }
