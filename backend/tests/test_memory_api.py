from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.api import memory as memory_api
from backend.db.database import create_engine_and_session_factory, get_db_session
from backend.db.models import Base, MemoryItem, utc_now
from backend.main import app

pytestmark = [
    pytest.mark.filterwarnings(
        "error::pydantic.warnings.UnsupportedFieldAttributeWarning"
    ),
    pytest.mark.filterwarnings(
        "ignore:'asyncio.iscoroutinefunction' is deprecated:DeprecationWarning"
    ),
]


@pytest_asyncio.fixture
async def api_client(tmp_path: Path) -> AsyncIterator[AsyncClient]:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'memory-api.db'}"
    engine, session_factory = create_engine_and_session_factory(database_url)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_get_db_session() -> AsyncIterator[Any]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    memory_api.clear_memory_candidates()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()
    memory_api.clear_memory_candidates()
    await engine.dispose()


@pytest.mark.asyncio
async def test_memory_items_can_be_filtered_by_kind_and_query(api_client: AsyncClient) -> None:
    async for session in app.dependency_overrides[get_db_session]():
        session.add_all(
            [
                MemoryItem(kind="safety", content="用户深蹲到底部左膝疼痛。", confidence=0.95, created_at=utc_now()),
                MemoryItem(kind="equipment", content="用户只有哑铃。", confidence=0.9, created_at=utc_now()),
            ]
        )
        await session.commit()
        break

    response = await api_client.get("/api/memory/items", params={"kind": "safety", "query": "深蹲"})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 1
    assert payload["items"][0]["kind"] == "safety"


@pytest.mark.asyncio
async def test_memory_candidate_confirm_promotes_item(api_client: AsyncClient) -> None:
    created = await api_client.post(
        "/api/memory/candidates",
        json={
            "kind": "equipment",
            "content": "用户家里只有哑铃和弹力带。",
            "confidence": 0.7,
            "sourceMessageId": 9,
            "reason": "用户明确说明器械条件",
        },
    )
    candidate_id = created.json()["candidate"]["id"]

    confirmed = await api_client.post(f"/api/memory/candidates/{candidate_id}/confirm")
    items = await api_client.get("/api/memory/items", params={"kind": "equipment"})

    assert confirmed.status_code == 200
    assert confirmed.json()["item"]["content"] == "用户家里只有哑铃和弹力带。"
    assert items.json()["items"][0]["sourceMessageId"] == 9


@pytest.mark.asyncio
async def test_ignored_candidate_is_not_injected(api_client: AsyncClient) -> None:
    created = await api_client.post(
        "/api/memory/candidates",
        json={
            "kind": "preference",
            "content": "用户可能偏好很晚训练。",
            "confidence": 0.55,
            "reason": "低置信度，需要确认",
        },
    )
    candidate_id = created.json()["candidate"]["id"]

    ignored = await api_client.post(f"/api/memory/candidates/{candidate_id}/ignore")
    items = await api_client.get("/api/memory/items", params={"query": "很晚训练"})

    assert ignored.status_code == 200
    assert ignored.json()["candidate"]["status"] == "ignored"
    assert items.json()["items"] == []
