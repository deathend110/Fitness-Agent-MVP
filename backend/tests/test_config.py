from pathlib import Path

from backend.config import BACKEND_DIR, resolve_sqlite_url


def test_resolve_sqlite_url_uses_backend_dir_for_relative_paths():
    resolved_url = resolve_sqlite_url("sqlite+aiosqlite:///./data/repmind.db")

    expected_path = (BACKEND_DIR / "data" / "repmind.db").resolve().as_posix()
    assert resolved_url == f"sqlite+aiosqlite:///{expected_path}"


def test_resolve_sqlite_url_preserves_absolute_or_external_urls(tmp_path: Path):
    absolute_db = tmp_path / "custom.db"
    absolute_url = f"sqlite+aiosqlite:///{absolute_db.as_posix()}"
    postgres_url = "postgresql+asyncpg://user:pass@example.com/fitloop"

    assert resolve_sqlite_url(absolute_url) == absolute_url
    assert resolve_sqlite_url("sqlite+aiosqlite:///:memory:") == "sqlite+aiosqlite:///:memory:"
    assert resolve_sqlite_url(postgres_url) == postgres_url
