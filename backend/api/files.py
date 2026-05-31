from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import Settings, get_settings
from backend.db.database import get_db_session
from backend.db.models import KnowledgeItem, UploadedFile, utc_now
from backend.files.parsers import parse_uploaded_file
from backend.files.uploader import (
    build_stored_name,
    calculate_sha256,
    ensure_uploads_dir,
    normalize_extension,
    resolve_storage_path,
)

router = APIRouter(prefix="/api/files", tags=["files"])


def get_file_settings() -> Settings:
    return get_settings()


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    sessionId: int | None = None,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_file_settings),
) -> dict[str, Any]:
    original_name = file.filename or "upload"
    extension = normalize_extension(original_name)
    if extension not in settings.allowed_upload_extensions:
        raise HTTPException(status_code=415, detail="Unsupported file type")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="Empty file is not supported")
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail="File is too large")

    sha256 = calculate_sha256(content)
    existing = (
        await session.execute(select(UploadedFile).where(UploadedFile.sha256 == sha256))
    ).scalar_one_or_none()
    if existing is not None:
        return {"file": build_uploaded_file_response(existing), "deduplicated": True}

    uploads_dir = ensure_uploads_dir(settings.uploads_dir)
    stored_name = build_stored_name(original_name, sha256)
    target_path = (uploads_dir / stored_name).resolve()
    if uploads_dir not in target_path.parents:
        raise HTTPException(status_code=400, detail="Invalid upload path")
    target_path.write_bytes(content)

    parsed = parse_uploaded_file(target_path, extension, file.content_type or "")
    uploaded = UploadedFile(
        original_name=original_name,
        stored_name=stored_name,
        mime_type=file.content_type or "",
        extension=extension,
        size_bytes=len(content),
        sha256=sha256,
        storage_path=stored_name,
        summary=parsed["summary"],
        parser_status=parsed["status"],
        parser_error=parsed["error"],
        created_at=utc_now(),
    )
    session.add(uploaded)
    await session.flush()

    text = str(parsed["summary"].get("text") or "").strip()
    if uploaded.parser_status == "parsed" and text:
        session.add(
            KnowledgeItem(
                kind="uploaded_file",
                title=original_name,
                content=text[:4000],
                source_file_id=uploaded.id,
                source_session_id=sessionId,
                created_at=utc_now(),
            )
        )
    await session.commit()
    await session.refresh(uploaded)
    return {"file": build_uploaded_file_response(uploaded), "deduplicated": False}


@router.get("")
async def list_files(session: AsyncSession = Depends(get_db_session)) -> dict[str, Any]:
    result = await session.execute(select(UploadedFile).order_by(UploadedFile.created_at.desc()))
    files = result.scalars().all()
    return {"files": [build_uploaded_file_response(item) for item in files]}


@router.get("/{file_id}")
async def get_file(file_id: int, session: AsyncSession = Depends(get_db_session)) -> dict[str, Any]:
    uploaded = await session.get(UploadedFile, file_id)
    if uploaded is None:
        raise HTTPException(status_code=404, detail="File not found")
    return {"file": build_uploaded_file_response(uploaded)}


@router.delete("/{file_id}")
async def delete_file(
    file_id: int,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_file_settings),
) -> dict[str, Any]:
    uploaded = await session.get(UploadedFile, file_id)
    if uploaded is None:
        raise HTTPException(status_code=404, detail="File not found")

    await session.execute(delete(KnowledgeItem).where(KnowledgeItem.source_file_id == file_id))
    await session.delete(uploaded)
    await session.commit()

    try:
        path = resolve_storage_path(settings.uploads_dir, uploaded.storage_path)
        if path.exists():
            path.unlink()
    except ValueError:
        # 数据库里只应保存相对路径；如果旧数据异常，删除 DB 记录后不冒险删除任意路径。
        pass

    return {"ok": True}


def build_uploaded_file_response(file: UploadedFile) -> dict[str, Any]:
    return {
        "id": file.id,
        "originalName": file.original_name,
        "storedName": file.stored_name,
        "mimeType": file.mime_type,
        "extension": file.extension,
        "sizeBytes": file.size_bytes,
        "sha256": file.sha256,
        "summary": file.summary,
        "parserStatus": file.parser_status,
        "parserError": file.parser_error,
        "createdAt": file.created_at.isoformat() if file.created_at else None,
    }
