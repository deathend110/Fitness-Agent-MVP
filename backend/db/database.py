from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.config import get_settings
from backend.db.models import Base


def create_engine_and_session_factory(
    database_url: str,
    *,
    echo: bool = False,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(database_url, echo=echo, future=True)
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return engine, session_factory


async def ensure_sqlite_chat_message_attachments_column(target_engine: AsyncEngine) -> None:
    async with target_engine.begin() as connection:
        if connection.dialect.name != "sqlite":
            return

        result = await connection.exec_driver_sql("PRAGMA table_info(chat_message)")
        columns = {row[1] for row in result.fetchall()}
        if "attachments" in columns:
            return

        # 旧版 SQLite 库不会自动补新增列，这里只修 chat_message 的 attachments，避免首次写附件消息时报错。
        await connection.exec_driver_sql(
            "ALTER TABLE chat_message ADD COLUMN attachments JSON NOT NULL DEFAULT '[]'"
        )


settings = get_settings()
engine, session_factory = create_engine_and_session_factory(settings.database_url)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


async def create_all_tables(target_engine: AsyncEngine | None = None) -> None:
    active_engine = target_engine or engine
    async with active_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await ensure_sqlite_chat_message_attachments_column(active_engine)
