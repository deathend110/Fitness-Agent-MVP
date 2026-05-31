from __future__ import annotations

from pathlib import Path
from typing import Any

MAX_TEXT_CHARS = 4000


def parse_text_file(path: Path, extension: str) -> dict[str, Any]:
    raw_text = path.read_text(encoding="utf-8", errors="replace")
    text = raw_text[:MAX_TEXT_CHARS]
    lines = [line.rstrip() for line in text.splitlines()]
    non_empty_lines = [line for line in lines if line.strip()]
    title = _extract_title(non_empty_lines, path.stem)

    return {
        "kind": "markdown" if extension == ".md" else "text",
        "title": title,
        "summary": _first_text_lines(non_empty_lines),
        "preview": {
            "lineCount": len(non_empty_lines),
            "truncated": len(raw_text) > MAX_TEXT_CHARS,
        },
        "text": text,
    }


def _extract_title(lines: list[str], fallback: str) -> str:
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or fallback
    return lines[0].strip() if lines else fallback


def _first_text_lines(lines: list[str], limit: int = 5) -> str:
    return "\n".join(lines[:limit])
