from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image


def parse_image_file(path: Path, mime_type: str = "") -> dict[str, Any]:
    with Image.open(path) as image:
        width, height = image.size
        image_format = image.format or path.suffix.lstrip(".").upper()

    return {
        "kind": "image",
        "title": path.name,
        "summary": f"图片文件 {path.name}，尺寸 {width}x{height}，格式 {image_format}。",
        "preview": {
            "width": width,
            "height": height,
            "format": image_format,
            "mimeType": mime_type,
            "localReference": path.name,
        },
        # 图片暂不注入完整内容；后续视觉模型只应通过受控文件引用读取。
        "text": f"图片：{path.name}；尺寸：{width}x{height}；格式：{image_format}。",
    }
