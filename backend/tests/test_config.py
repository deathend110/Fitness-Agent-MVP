from pathlib import Path

from backend.config import (
    BACKEND_DIR,
    Settings,
    apply_runtime_proxy_environment,
    resolve_sqlite_url,
)


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


def test_apply_runtime_proxy_environment_promotes_proxy_fields_to_process_env():
    settings = Settings(
        http_proxy="http://127.0.0.1:7890",
        https_proxy="http://127.0.0.1:7890",
        all_proxy="socks5://127.0.0.1:7891",
        no_proxy="127.0.0.1,localhost",
    )
    target_env: dict[str, str] = {}

    applied = apply_runtime_proxy_environment(settings, target_env)

    assert applied == {
        "HTTP_PROXY": "http://127.0.0.1:7890",
        "HTTPS_PROXY": "http://127.0.0.1:7890",
        "ALL_PROXY": "socks5://127.0.0.1:7891",
        "NO_PROXY": "127.0.0.1,localhost",
    }
    assert target_env["HTTP_PROXY"] == "http://127.0.0.1:7890"
    assert target_env["http_proxy"] == "http://127.0.0.1:7890"
    assert target_env["HTTPS_PROXY"] == "http://127.0.0.1:7890"
    assert target_env["https_proxy"] == "http://127.0.0.1:7890"
    assert target_env["ALL_PROXY"] == "socks5://127.0.0.1:7891"
    assert target_env["all_proxy"] == "socks5://127.0.0.1:7891"
    assert target_env["NO_PROXY"] == "127.0.0.1,localhost"
    assert target_env["no_proxy"] == "127.0.0.1,localhost"


def test_settings_support_backend_host_and_backend_port():
    settings = Settings(backend_host="0.0.0.0", backend_port=9234)

    assert settings.backend_host == "0.0.0.0"
    assert settings.backend_port == 9234
