from __future__ import annotations

from pathlib import Path
from typing import Any

from docx import Document

MAX_TEXT_CHARS = 4000


def parse_docx_file(path: Path) -> dict[str, Any]:
    document = Document(path)
    paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
    text = "\n".join(paragraphs)[:MAX_TEXT_CHARS]
    title = paragraphs[0] if paragraphs else path.stem

    return {
        "kind": "docx",
        "title": title,
        "summary": "\n".join(paragraphs[:5]),
        "preview": {
            "paragraphCount": len(paragraphs),
            "truncated": len("\n".join(paragraphs)) > MAX_TEXT_CHARS,
        },
        "text": text,
    }
