from __future__ import annotations

from pathlib import Path
from urllib.request import urlopen

from tests.e2e.coach_e2e_helpers import ensure_backend_dev_server


def test_ensure_backend_dev_server_starts_backend_and_serves_healthcheck(
    monkeypatch,
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    backend_env_path = repo_root / "backend" / ".env"
    original_backend_env = backend_env_path.read_text(encoding="utf-8") if backend_env_path.exists() else None
    backend_port = 8017
    data_dir = tmp_path / "backend-data"
    uploads_dir = data_dir / "uploads"
    provider_config_path = tmp_path / "model_providers.test.json"
    provider_config_path.write_text(
        "\n".join(
            [
                "{",
                '  "version": 1,',
                '  "defaultModelRef": "provider_smoke::test-model",',
                '  "providers": [',
                "    {",
                '      "id": "provider_smoke",',
                '      "type": "openai_compatible",',
                '      "label": "Smoke Provider",',
                '      "enabled": true,',
                '      "apiKey": "sk-smoke-test",',
                '      "baseUrl": "https://example.com/v1",',
                '      "wireApi": "responses",',
                '      "apiPathMode": "append_v1",',
                '      "selectedModels": [',
                "        {",
                '          "remoteId": "test-model",',
                '          "label": "Test Model",',
                '          "enabled": true',
                "        }",
                "      ]",
                "    }",
                "  ]",
                "}",
            ]
        ),
        encoding="utf-8",
    )

    backend_env_path.write_text(
        "\n".join(
            [
                f"DATA_DIR={data_dir.as_posix()}",
                f"UPLOADS_DIR={uploads_dir.as_posix()}",
                "DATABASE_URL=sqlite+aiosqlite:///./data/repmind-e2e-helper.db",
                "BACKEND_HOST=127.0.0.1",
                f"BACKEND_PORT={backend_port}",
                f"MODEL_PROVIDER_CONFIG_PATH={provider_config_path.as_posix()}",
                'CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]',
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(repo_root)

    try:
        with ensure_backend_dev_server(
            host="127.0.0.1",
            port=backend_port,
            env={
                "BACKEND_HOST": "127.0.0.1",
                "BACKEND_PORT": str(backend_port),
                "MODEL_PROVIDER_CONFIG_PATH": str(provider_config_path),
            },
        ):
            with urlopen(f"http://127.0.0.1:{backend_port}/api/health", timeout=3) as response:
                assert response.status == 200
                assert response.read().decode("utf-8") == '{"status":"ok"}'
    finally:
        if original_backend_env is None:
            backend_env_path.unlink(missing_ok=True)
        else:
            backend_env_path.write_text(original_backend_env, encoding="utf-8")
