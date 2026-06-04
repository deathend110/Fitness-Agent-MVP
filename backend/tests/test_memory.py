from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.memory import MemoryRetriever, extract_memory_candidates
from backend.db.database import create_engine_and_session_factory
from backend.db.models import Base, MemoryItem, utc_now


@pytest_asyncio.fixture
async def db_session(tmp_path: Path) -> AsyncIterator[AsyncSession]:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'memory.db'}"
    engine, session_factory = create_engine_and_session_factory(database_url)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        yield session

    await engine.dispose()


def test_extract_memory_candidates_from_explicit_long_term_facts() -> None:
    candidates = extract_memory_candidates(
        "我家里只有哑铃和弹力带；我的目标是增肌；我只能晚上训练；我不吃乳制品。",
        source_message_id=12,
    )

    by_kind = {candidate.kind: candidate for candidate in candidates}

    assert by_kind["equipment"].content == "用户家里只有哑铃和弹力带。"
    assert by_kind["goal"].content == "用户目标是增肌。"
    assert by_kind["schedule"].requires_confirmation is False
    assert by_kind["nutrition"].source_message_id == 12


def test_extract_memory_candidates_does_not_promote_single_day_state() -> None:
    assert extract_memory_candidates("今天很累，睡得也不好。", source_message_id=1) == []


def test_extract_memory_candidates_marks_pain_as_safety_and_low_confidence_for_vague_text() -> None:
    candidates = extract_memory_candidates("我膝盖深蹲到底部会疼，可能也不太适合太晚练。", source_message_id=5)

    safety = next(candidate for candidate in candidates if candidate.kind == "safety")
    vague = next(candidate for candidate in candidates if candidate.kind == "preference")

    assert safety.content == "用户膝盖深蹲到底部会疼。"
    assert safety.confidence >= 0.9
    assert vague.requires_confirmation is True


@pytest.mark.asyncio
async def test_memory_retriever_prioritizes_safety_then_keyword_and_updates_last_used(
    db_session: AsyncSession,
) -> None:
    db_session.add_all(
        [
            MemoryItem(kind="preference", content="用户偏好晚间训练。", confidence=0.9, created_at=utc_now()),
            MemoryItem(kind="safety", content="用户深蹲到底部左膝疼痛。", confidence=0.95, created_at=utc_now()),
            MemoryItem(kind="nutrition", content="用户不吃乳制品。", confidence=0.9, created_at=utc_now()),
        ]
    )
    await db_session.commit()

    results = await MemoryRetriever().retrieve(db_session, query="深蹲 晚间")

    assert [item.kind for item in results[:2]] == ["safety", "preference"]
    assert all(item.last_used_at is not None for item in results)


@pytest.mark.asyncio
async def test_retrieve_ordering_is_stable_across_calls(
    db_session: AsyncSession,
) -> None:
    # 连续两次检索的顺序必须逐项一致，锁定前缀缓存所依赖的记忆段稳定性。
    db_session.add_all(
        [
            MemoryItem(kind="preference", content="用户偏好晚间训练。", confidence=0.9, created_at=utc_now()),
            MemoryItem(kind="safety", content="用户深蹲到底部左膝疼痛。", confidence=0.95, created_at=utc_now()),
            MemoryItem(kind="nutrition", content="用户不吃乳制品。", confidence=0.9, created_at=utc_now()),
            MemoryItem(kind="goal", content="用户目标是增肌。", confidence=0.9, created_at=utc_now()),
        ]
    )
    await db_session.commit()

    first = await MemoryRetriever().retrieve(db_session)
    second = await MemoryRetriever().retrieve(db_session)

    assert [item.id for item in first] == [item.id for item in second]

