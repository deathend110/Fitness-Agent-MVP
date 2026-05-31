from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from backend.config import Settings
from backend.db.database import create_engine_and_session_factory
from backend.db.models import Base, ChatSession, CoachDraft, KnowledgeItem, UploadedFile


@pytest.mark.asyncio
async def test_phase4_file_and_draft_models_round_trip(tmp_path: Path) -> None:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'phase4-models.db'}"
    engine, session_factory = create_engine_and_session_factory(database_url)

    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        async with session_factory() as session:
            chat_session = ChatSession(title="Phase 4 草稿")
            session.add(chat_session)
            await session.flush()

            uploaded_file = UploadedFile(
                original_name="训练记录.xlsx",
                stored_name="abc123.xlsx",
                mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                extension=".xlsx",
                size_bytes=4096,
                sha256="a" * 64,
                storage_path="abc123.xlsx",
                summary={"kind": "excel", "summary": "包含深蹲训练表。"},
                parser_status="parsed",
            )
            session.add(uploaded_file)
            await session.flush()

            knowledge = KnowledgeItem(
                kind="uploaded_file",
                title="训练记录.xlsx",
                content="包含深蹲训练表。",
                source_file_id=uploaded_file.id,
                source_session_id=chat_session.id,
            )
            draft = CoachDraft(
                session_id=chat_session.id,
                content="帮我分析这个表格",
                model="deepseek-v4-flash",
                thinking={"enabled": True, "budget": "auto"},
                attached_file_ids=[uploaded_file.id],
            )
            session.add_all([knowledge, draft])
            await session.commit()

        async with session_factory() as session:
            stored_file = (await session.execute(select(UploadedFile))).scalar_one()
            stored_knowledge = (await session.execute(select(KnowledgeItem))).scalar_one()
            stored_draft = (await session.execute(select(CoachDraft))).scalar_one()

        assert stored_file.original_name == "训练记录.xlsx"
        assert stored_file.extension == ".xlsx"
        assert stored_file.summary["kind"] == "excel"
        assert stored_file.parser_status == "parsed"
        assert stored_file.parser_error is None

        assert stored_knowledge.source_file_id == stored_file.id
        assert stored_knowledge.kind == "uploaded_file"

        assert stored_draft.content == "帮我分析这个表格"
        assert stored_draft.model == "deepseek-v4-flash"
        assert stored_draft.thinking == {"enabled": True, "budget": "auto"}
        assert stored_draft.attached_file_ids == [stored_file.id]
    finally:
        await engine.dispose()


def test_phase4_settings_resolve_uploads_dir(tmp_path: Path) -> None:
    settings = Settings(data_dir=str(tmp_path / "data"), uploads_dir="./data/uploads")

    assert Path(settings.uploads_dir).is_absolute()
    assert settings.uploads_dir.endswith(str(Path("backend") / "data" / "uploads"))
    assert settings.max_upload_mb == 15
    assert ".xlsx" in settings.allowed_upload_extensions
    assert ".docx" in settings.allowed_upload_extensions
    assert "deepseek-v4-flash" in settings.model_allowlist
    assert settings.default_thinking_enabled is False
    assert settings.default_thinking_budget == "auto"
