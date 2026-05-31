from __future__ import annotations

import json
from typing import Any

JSON_SEPARATOR = "---JSON---"


def parse_ai_response(content: Any) -> dict[str, Any]:
    """将 AI 文本拆成可展示正文与可选建议，保持前后端语义一致。"""

    raw_content = content if isinstance(content, str) else ""
    separator_index = raw_content.find(JSON_SEPARATOR)

    if separator_index == -1:
        return {
            "text": raw_content.strip(),
            "suggestion": None,
        }

    text = raw_content[:separator_index].strip()
    json_text = raw_content[separator_index + len(JSON_SEPARATOR) :].strip()

    try:
        suggestion = json.loads(json_text)
    except json.JSONDecodeError:
        return {
            "text": raw_content,
            "suggestion": None,
        }

    return {
        "text": text,
        "suggestion": suggestion,
    }
