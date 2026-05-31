from __future__ import annotations

from collections.abc import AsyncIterator
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from PIL import Image
from sqlalchemy import select

from backend.config import Settings
from backend.db.database import create_engine_and_session_factory, get_db_session
from backend.db.models import Base, KnowledgeItem, UploadedFile
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
    from backend.api.files import get_file_settings

    database_url = f"sqlite+aiosqlite:///{tmp_path / 'files-api.db'}"
    engine, session_factory = create_engine_and_session_factory(database_url)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_get_db_session() -> AsyncIterator[Any]:
        async with session_factory() as session:
            yield session

    def override_file_settings() -> Settings:
        return Settings(
            data_dir=str(tmp_path / "data"),
            uploads_dir=str(tmp_path / "data" / "uploads"),
            max_upload_mb=1,
        )

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_file_settings] = override_file_settings

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()
    await engine.dispose()


async def _session_records() -> tuple[list[UploadedFile], list[KnowledgeItem]]:
    async for session in app.dependency_overrides[get_db_session]():
        files = (await session.execute(select(UploadedFile))).scalars().all()
        knowledge = (await session.execute(select(KnowledgeItem))).scalars().all()
        return list(files), list(knowledge)
    return [], []


def _png_bytes() -> bytes:
    image = Image.new("RGB", (16, 12), color=(80, 120, 160))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_upload_markdown_writes_file_db_and_knowledge(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/api/files/upload",
        files={"file": ("plan.md", b"# Plan\n\nSquat 5x5", "text/markdown")},
    )

    assert response.status_code == 200
    payload = response.json()["file"]
    assert payload["originalName"] == "plan.md"
    assert payload["parserStatus"] == "parsed"
    assert payload["summary"]["kind"] == "markdown"
    assert "storagePath" not in payload

    files, knowledge = await _session_records()
    assert len(files) == 1
    assert files[0].storage_path.endswith(".md")
    assert knowledge[0].kind == "uploaded_file"
    assert "Squat" in knowledge[0].content


@pytest.mark.asyncio
async def test_upload_png_and_list_get_delete_metadata(api_client: AsyncClient) -> None:
    uploaded = await api_client.post(
        "/api/files/upload",
        files={"file": ("form.png", _png_bytes(), "image/png")},
    )
    file_id = uploaded.json()["file"]["id"]

    listed = await api_client.get("/api/files")
    metadata = await api_client.get(f"/api/files/{file_id}")

    assert listed.status_code == 200
    assert listed.json()["files"][0]["originalName"] == "form.png"
    assert metadata.status_code == 200
    assert metadata.json()["file"]["summary"]["preview"]["width"] == 16
    assert "content" not in metadata.json()["file"]

    deleted = await api_client.delete(f"/api/files/{file_id}")
    missing = await api_client.get(f"/api/files/{file_id}")

    assert deleted.status_code == 200
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_upload_reuses_duplicate_sha_without_duplicate_db_row(api_client: AsyncClient) -> None:
    file_tuple = ("same.md", b"# Same\n\nRepeat", "text/markdown")

    first = await api_client.post("/api/files/upload", files={"file": file_tuple})
    second = await api_client.post("/api/files/upload", files={"file": file_tuple})

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["file"]["id"] == second.json()["file"]["id"]
    files, _knowledge = await _session_records()
    assert len(files) == 1


@pytest.mark.asyncio
async def test_upload_rejects_too_large_unsupported_and_empty(api_client: AsyncClient) -> None:
    too_large = await api_client.post(
        "/api/files/upload",
        files={"file": ("big.md", b"a" * (1024 * 1024 + 1), "text/markdown")},
    )
    unsupported = await api_client.post(
        "/api/files/upload",
        files={"file": ("run.exe", b"not allowed", "application/octet-stream")},
    )
    empty = await api_client.post(
        "/api/files/upload",
        files={"file": ("empty.md", b"", "text/markdown")},
    )

    assert too_large.status_code == 413
    assert unsupported.status_code == 415
    assert empty.status_code == 422
    files, _knowledge = await _session_records()
    assert files == []
