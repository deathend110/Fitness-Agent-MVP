from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.db.database import create_engine_and_session_factory, get_db_session
from backend.db.models import Base, ChatSession, UploadedFile, utc_now
from backend.main import app


@pytest_asyncio.fixture
async def api_client(tmp_path: Path) -> AsyncIterator[AsyncClient]:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'drafts-api.db'}"
    engine, session_factory = create_engine_and_session_factory(database_url)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_get_db_session() -> AsyncIterator[Any]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()
    await engine.dispose()


async def seed_session_and_file() -> tuple[int, int]:
    async for session in app.dependency_overrides[get_db_session]():
        chat_session = ChatSession(title="草稿测试", created_at=utc_now(), updated_at=utc_now())
        session.add(chat_session)
        await session.flush()
        uploaded = UploadedFile(
            original_name="plan.md",
            stored_name="plan.md",
            mime_type="text/markdown",
            extension=".md",
            size_bytes=10,
            sha256="c" * 64,
            storage_path="plan.md",
            summary={"kind": "markdown", "summary": "训练计划"},
            parser_status="parsed",
            created_at=utc_now(),
        )
        session.add(uploaded)
        await session.commit()
        return chat_session.id, uploaded.id
    raise AssertionError("session fixture missing")


@pytest.mark.asyncio
async def test_get_empty_draft_returns_defaults(api_client: AsyncClient) -> None:
    session_id, _file_id = await seed_session_and_file()

    response = await api_client.get(f"/api/chat/sessions/{session_id}/draft")

    assert response.status_code == 200
    payload = response.json()
    assert payload["content"] == ""
    assert payload["model"] == "deepseek-v4-flash"
    assert payload["thinking"] == {"enabled": False, "budget": "auto"}
    assert payload["attachedFileIds"] == []


@pytest.mark.asyncio
async def test_put_draft_round_trips_content_model_thinking_and_files(api_client: AsyncClient) -> None:
    session_id, file_id = await seed_session_and_file()

    saved = await api_client.put(
        f"/api/chat/sessions/{session_id}/draft",
        json={
            "content": "帮我分析附件",
            "model": "deepseek-v4-pro",
            "thinking": {"enabled": True, "budget": "max"},
            "attachedFileIds": [file_id],
        },
    )
    loaded = await api_client.get(f"/api/chat/sessions/{session_id}/draft")

    assert saved.status_code == 200
    assert loaded.json()["content"] == "帮我分析附件"
    assert loaded.json()["model"] == "deepseek-v4-pro"
    assert loaded.json()["thinking"] == {"enabled": True, "budget": "max"}
    assert loaded.json()["attachedFileIds"] == [file_id]


@pytest.mark.asyncio
async def test_draft_rejects_missing_session_and_unknown_file(api_client: AsyncClient) -> None:
    session_id, _file_id = await seed_session_and_file()

    missing_session = await api_client.get("/api/chat/sessions/404/draft")
    unknown_file = await api_client.put(
        f"/api/chat/sessions/{session_id}/draft",
        json={"content": "x", "attachedFileIds": [999]},
    )

    assert missing_session.status_code == 404
    assert unknown_file.status_code == 422
