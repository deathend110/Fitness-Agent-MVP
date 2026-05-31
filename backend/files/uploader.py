from __future__ import annotations

import hashlib
import re
from pathlib import Path
from uuid import uuid4


SAFE_NAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


def normalize_extension(filename: str) -> str:
    return Path(filename).suffix.lower()


def sanitize_filename(filename: str) -> str:
    stem = Path(filename).stem.strip() or "upload"
    suffix = normalize_extension(filename)
    safe_stem = SAFE_NAME_PATTERN.sub("-", stem).strip(".-_") or "upload"
    return f"{safe_stem[:80]}{suffix}"


def calculate_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def build_stored_name(original_name: str, sha256: str) -> str:
    safe_name = sanitize_filename(original_name)
    suffix = normalize_extension(safe_name)
    stem = Path(safe_name).stem
    return f"{sha256[:16]}-{uuid4().hex[:8]}-{stem[:40]}{suffix}"


def ensure_uploads_dir(uploads_dir: str) -> Path:
    path = Path(uploads_dir).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_storage_path(uploads_dir: str, storage_path: str) -> Path:
    uploads_root = ensure_uploads_dir(uploads_dir)
    target = (uploads_root / storage_path).resolve()
    if uploads_root not in target.parents and target != uploads_root:
        raise ValueError("Invalid storage path")
    return target
