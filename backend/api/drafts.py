from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.db.database import get_db_session
from backend.db.models import ChatSession, CoachDraft, UploadedFile, utc_now

router = APIRouter(prefix="/api/chat/sessions", tags=["drafts"])


class CoachDraftSchema(BaseModel):
    content: str = ""
    model: str | None = None
    thinking: dict[str, Any] = Field(default_factory=dict)
    attachedFileIds: list[int] = Field(default_factory=list)


async def _ensure_chat_session(session: AsyncSession, session_id: int) -> None:
    if await session.get(ChatSession, session_id) is None:
        raise HTTPException(status_code=404, detail="Chat session not found")


async def _validate_file_ids(session: AsyncSession, file_ids: list[int]) -> list[int]:
    unique_ids = list(dict.fromkeys(file_id for file_id in file_ids if file_id > 0))
    if not unique_ids:
        return []
    result = await session.execute(select(UploadedFile.id).where(UploadedFile.id.in_(unique_ids)))
    existing = set(result.scalars().all())
    missing = [file_id for file_id in unique_ids if file_id not in existing]
    if missing:
        raise HTTPException(status_code=422, detail=f"Unknown attached file ids: {missing}")
    return unique_ids


@router.get("/{session_id}/draft")
async def get_coach_draft(
    session_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    await _ensure_chat_session(session, session_id)
    result = await session.execute(select(CoachDraft).where(CoachDraft.session_id == session_id))
    draft = result.scalar_one_or_none()
    if draft is not None:
        return build_draft_response(draft)

    settings = get_settings()
    return {
        "sessionId": session_id,
        "content": "",
        "model": settings.default_model,
        "thinking": {
            "enabled": settings.default_thinking_enabled,
            "budget": settings.default_thinking_budget,
        },
        "attachedFileIds": [],
        "updatedAt": None,
    }


@router.put("/{session_id}/draft")
async def save_coach_draft(
    session_id: int,
    payload: CoachDraftSchema,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    await _ensure_chat_session(session, session_id)
    attached_file_ids = await _validate_file_ids(session, payload.attachedFileIds)
    result = await session.execute(select(CoachDraft).where(CoachDraft.session_id == session_id))
    draft = result.scalar_one_or_none()

    if draft is None:
        draft = CoachDraft(session_id=session_id)
        session.add(draft)

    draft.content = payload.content
    draft.model = payload.model
    draft.thinking = payload.thinking or {}
    draft.attached_file_ids = attached_file_ids
    draft.updated_at = utc_now()
    await session.commit()
    await session.refresh(draft)
    return build_draft_response(draft)


def build_draft_response(draft: CoachDraft) -> dict[str, Any]:
    return {
        "sessionId": draft.session_id,
        "content": draft.content,
        "model": draft.model,
        "thinking": draft.thinking,
        "attachedFileIds": draft.attached_file_ids,
        "updatedAt": draft.updated_at.isoformat() if draft.updated_at else None,
    }
