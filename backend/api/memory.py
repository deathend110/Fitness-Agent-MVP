from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.memory import MemoryRetriever
from backend.db.database import get_db_session
from backend.db.models import MemoryItem, utc_now

router = APIRouter(prefix="/api/memory", tags=["memory"])


@dataclass
class StoredMemoryCandidate:
    id: str
    kind: str
    content: str
    confidence: float
    source_message_id: int | None = None
    reason: str = ""
    status: str = "pending"

    def to_response(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "content": self.content,
            "confidence": self.confidence,
            "sourceMessageId": self.source_message_id,
            "reason": self.reason,
            "status": self.status,
            "requiresConfirmation": self.confidence < 0.8,
        }


class MemoryCandidateCreateSchema(BaseModel):
    kind: str
    content: str
    confidence: float = 0.7
    sourceMessageId: int | None = None
    reason: str = ""


_candidate_store: dict[str, StoredMemoryCandidate] = {}


def clear_memory_candidates() -> None:
    _candidate_store.clear()


def build_memory_item_response(item: MemoryItem) -> dict[str, Any]:
    return {
        "id": item.id,
        "kind": item.kind,
        "content": item.content,
        "confidence": item.confidence,
        "sourceMessageId": item.source_message_id,
        "lastUsedAt": item.last_used_at,
        "createdAt": item.created_at,
    }


@router.get("/items")
async def list_memory_items(
    kind: str | None = None,
    query: str | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    items = await MemoryRetriever().retrieve(session, kind=kind, query=query, update_last_used=False)
    return {"items": [build_memory_item_response(item) for item in items]}


@router.post("/candidates")
async def create_memory_candidate(payload: MemoryCandidateCreateSchema) -> dict[str, Any]:
    candidate = StoredMemoryCandidate(
        id=uuid4().hex,
        kind=payload.kind,
        content=payload.content,
        confidence=payload.confidence,
        source_message_id=payload.sourceMessageId,
        reason=payload.reason,
    )
    _candidate_store[candidate.id] = candidate
    return {"candidate": candidate.to_response()}


@router.post("/candidates/{candidate_id}/confirm")
async def confirm_memory_candidate(
    candidate_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    candidate = _read_candidate(candidate_id)
    if candidate.status == "ignored":
        raise HTTPException(status_code=409, detail="Memory candidate has been ignored")
    if candidate.status == "confirmed":
        raise HTTPException(status_code=409, detail="Memory candidate has already been confirmed")

    item = MemoryItem(
        kind=candidate.kind,
        content=candidate.content,
        confidence=candidate.confidence,
        source_message_id=candidate.source_message_id,
        created_at=utc_now(),
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    candidate.status = "confirmed"
    return {"candidate": candidate.to_response(), "item": build_memory_item_response(item)}


@router.post("/candidates/{candidate_id}/ignore")
async def ignore_memory_candidate(candidate_id: str) -> dict[str, Any]:
    candidate = _read_candidate(candidate_id)
    candidate.status = "ignored"
    return {"candidate": candidate.to_response()}


def _read_candidate(candidate_id: str) -> StoredMemoryCandidate:
    candidate = _candidate_store.get(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Memory candidate not found")
    return candidate
