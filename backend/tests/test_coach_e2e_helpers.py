from __future__ import annotations

from pathlib import Path
from urllib.request import urlopen

from tests.e2e.coach_e2e_helpers import ensure_backend_dev_server, find_listening_process_id


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


def test_ensure_backend_dev_server_force_restart_replaces_existing_listener(monkeypatch) -> None:
    calls: list[object] = []
    port_states = iter([True, False])

    monkeypatch.setattr("tests.e2e.coach_e2e_helpers._is_port_open", lambda host, port: next(port_states))
    monkeypatch.setattr("tests.e2e.coach_e2e_helpers.find_listening_process_id", lambda host, port: 4321)
    monkeypatch.setattr("tests.e2e.coach_e2e_helpers.stop_process_tree", lambda pid: calls.append(("stop", pid)))
    monkeypatch.setattr("tests.e2e.coach_e2e_helpers.wait_for_backend_ready", lambda backend_url, timeout_seconds=45: calls.append(("wait", backend_url)))
    monkeypatch.setattr("tests.e2e.coach_e2e_helpers.wait_for_port_release", lambda host, port, timeout_seconds=10.0: calls.append(("release", host, port)))
    monkeypatch.setattr("tests.e2e.coach_e2e_helpers.shutil.which", lambda name: "uv")

    class FakeProcess:
        pid = 9876

        def poll(self):
            return None

    monkeypatch.setattr(
        "tests.e2e.coach_e2e_helpers.subprocess.Popen",
        lambda *args, **kwargs: calls.append(("spawn", args, kwargs)) or FakeProcess(),
    )

    with ensure_backend_dev_server(
        host="127.0.0.1",
        port=8000,
        env={"BACKEND_HOST": "127.0.0.1"},
        force_restart=True,
    ):
        pass

    assert ("stop", 4321) in calls
    assert ("release", "127.0.0.1", 8000) in calls
    assert any(call[0] == "spawn" for call in calls)
    assert ("stop", 9876) in calls


def test_ensure_backend_dev_server_force_restart_fails_when_port_stays_busy(monkeypatch) -> None:
    monkeypatch.setattr("tests.e2e.coach_e2e_helpers._is_port_open", lambda host, port: True)
    monkeypatch.setattr("tests.e2e.coach_e2e_helpers.find_listening_process_id", lambda host, port: 4321)
    monkeypatch.setattr("tests.e2e.coach_e2e_helpers.stop_process_tree", lambda pid: None)

    def fake_wait_for_port_release(host, port, timeout_seconds=10.0):
        raise RuntimeError("后端端口 127.0.0.1:8000 在指定时间内未释放，无法安全重启。")

    monkeypatch.setattr("tests.e2e.coach_e2e_helpers.wait_for_port_release", fake_wait_for_port_release)

    try:
        with ensure_backend_dev_server(host="127.0.0.1", port=8000, force_restart=True):
            raise AssertionError("should not enter context")
    except RuntimeError as exc:
        assert "无法安全重启" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ensure_backend_dev_server to fail")


def test_find_listening_process_id_falls_back_to_powershell_when_psutil_missing(monkeypatch) -> None:
    import builtins

    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "psutil":
            raise ImportError("psutil missing")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr("builtins.__import__", fake_import)
    monkeypatch.setattr(
        "tests.e2e.coach_e2e_helpers.subprocess.run",
        lambda *args, **kwargs: type(
            "Completed",
            (),
            {
                "returncode": 0,
                "stdout": '[{"LocalAddress":"127.0.0.1","OwningProcess":2468}]',
            },
        )(),
    )

    assert find_listening_process_id("127.0.0.1", 8000) == 2468
