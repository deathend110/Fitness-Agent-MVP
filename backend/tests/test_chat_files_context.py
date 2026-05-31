from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.chat_session import build_agent_request
from backend.agent.tool_calling import ToolResultSlimmer, build_default_tool_registry
from backend.db.database import create_engine_and_session_factory
from backend.db.models import Base, ChatSession, UploadedFile, utc_now


@pytest_asyncio.fixture
async def db_session(tmp_path: Path) -> AsyncIterator[AsyncSession]:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'chat-files.db'}"
    engine, session_factory = create_engine_and_session_factory(database_url)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        yield session

    await engine.dispose()


async def seed_uploaded_file(session: AsyncSession) -> tuple[ChatSession, UploadedFile]:
    chat_session = ChatSession(title="文件上下文", created_at=utc_now(), updated_at=utc_now())
    session.add(chat_session)
    await session.flush()

    uploaded = UploadedFile(
        original_name="训练表.xlsx",
        stored_name="abc.xlsx",
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        extension=".xlsx",
        size_bytes=2048,
        sha256="b" * 64,
        storage_path="abc.xlsx",
        summary={
            "kind": "excel",
            "title": "训练表",
            "summary": "周一深蹲 5x5，周三卧推 4x6。",
            "preview": {"sheets": [{"name": "Week"}]},
            "text": "不应完整注入的超长原文" * 400,
        },
        parser_status="parsed",
        created_at=utc_now(),
    )
    session.add(uploaded)
    await session.commit()
    return chat_session, uploaded


@pytest.mark.asyncio
async def test_build_agent_request_injects_selected_file_summary(db_session: AsyncSession) -> None:
    chat_session, uploaded = await seed_uploaded_file(db_session)

    request = await build_agent_request(
        session=db_session,
        session_id=chat_session.id,
        user_input="结合附件调整计划",
        file_ids=[uploaded.id, 999],
    )

    rendered = "\n".join(message["content"] for message in request.messages)
    assert "上传文件摘要" in rendered
    assert "周一深蹲 5x5" in rendered
    assert "不应完整注入的超长原文" not in rendered
    assert request.debug["selected_files"] == [uploaded.id]
    assert request.debug["missing_files"] == [999]


@pytest.mark.asyncio
async def test_read_uploaded_file_summary_tool_returns_real_summary(db_session: AsyncSession) -> None:
    _chat_session, uploaded = await seed_uploaded_file(db_session)
    registry = build_default_tool_registry()

    result = await registry.execute(db_session, "read_uploaded_file_summary", {"file_id": uploaded.id})
    missing = await registry.execute(db_session, "read_uploaded_file_summary", {"file_id": 404})

    assert result["fileId"] == uploaded.id
    assert result["status"] == "parsed"
    assert result["summary"]["summary"] == "周一深蹲 5x5，周三卧推 4x6。"
    assert missing["ok"] is False
    assert "not found" in missing["error"]


def test_tool_result_slimmer_trims_large_file_summary() -> None:
    slimmed = ToolResultSlimmer(max_chars=120).slim(
        "read_uploaded_file_summary",
        {"fileId": 1, "summary": {"text": "深蹲" * 300}},
    )

    assert len(slimmed) <= 150
    assert "trimmed:read_uploaded_file_summary" in slimmed
