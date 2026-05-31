from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.files.parsers.docx_parser import parse_docx_file
from backend.files.parsers.excel_parser import parse_excel_file
from backend.files.parsers.image_parser import parse_image_file
from backend.files.parsers.md_parser import parse_text_file


def parse_uploaded_file(path: Path, extension: str, mime_type: str = "") -> dict[str, Any]:
    """按扩展名分发解析器，统一返回 parser_status 与摘要结构。"""
    try:
        if extension in {".md", ".txt"}:
            summary = parse_text_file(path, extension)
        elif extension == ".docx":
            summary = parse_docx_file(path)
        elif extension in {".xlsx", ".xlsm"}:
            summary = parse_excel_file(path)
        elif extension in {".png", ".jpg", ".jpeg", ".webp"}:
            summary = parse_image_file(path, mime_type)
        else:
            raise ValueError(f"Unsupported extension: {extension}")
    except Exception as exc:  # noqa: BLE001 - 上传解析失败要转成可展示状态，不能把请求打成 500。
        return {
            "status": "failed",
            "summary": {
                "kind": extension.lstrip(".") or "unknown",
                "title": path.name,
                "summary": "",
                "preview": {},
                "text": "",
            },
            "error": str(exc),
        }

    text = str(summary.get("text") or "").strip()
    status = "parsed" if text or summary.get("kind") == "image" else "empty"
    return {"status": status, "summary": summary, "error": None}
