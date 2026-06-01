import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app
from backend.model_config.runtime import ProviderRuntimeCache


def _write_config(path: Path, *, default_model_ref: str, label: str, remote_model_ids: list[str] | None = None) -> None:
    remote_model_ids = remote_model_ids or ["gemini-2.5-flash"]
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "defaultModelRef": default_model_ref,
                "providers": [
                    {
                        "id": "provider_gemini_main",
                        "type": "gemini_native",
                        "label": label,
                        "enabled": True,
                        "apiKey": "AIza-real-key",
                        "baseUrl": "https://generativelanguage.googleapis.com/v1beta",
                        "selectedModels": [
                            {"remoteId": remote_model_id, "label": remote_model_id, "enabled": True}
                            for remote_model_id in remote_model_ids
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_resolves_model_ref_to_provider_and_remote_model(tmp_path: Path) -> None:
    config_file = tmp_path / "model_providers.json"
    _write_config(
        config_file,
        default_model_ref="provider_gemini_main::gemini-2.5-flash",
        label="Gemini 主账号",
    )

    runtime = ProviderRuntimeCache.from_path(config_file)
    provider, remote_model_id = runtime.resolve_model_ref("provider_gemini_main::gemini-2.5-flash")

    assert runtime.default_model_ref == "provider_gemini_main::gemini-2.5-flash"
    assert provider.id == "provider_gemini_main"
    assert provider.label == "Gemini 主账号"
    assert remote_model_id == "gemini-2.5-flash"


def test_resolve_model_ref_rejects_invalid_format(tmp_path: Path) -> None:
    config_file = tmp_path / "model_providers.json"
    _write_config(
        config_file,
        default_model_ref="provider_gemini_main::gemini-2.5-flash",
        label="Gemini 主账号",
    )

    runtime = ProviderRuntimeCache.from_path(config_file)

    try:
        runtime.resolve_model_ref("gemini-2.5-flash")
        raise AssertionError("应该抛出 ValueError")
    except ValueError as exc:
        assert "modelRef 必须采用 provider_id::remote_id 格式" in str(exc)


def test_resolve_model_ref_rejects_unknown_provider(tmp_path: Path) -> None:
    config_file = tmp_path / "model_providers.json"
    _write_config(
        config_file,
        default_model_ref="provider_gemini_main::gemini-2.5-flash",
        label="Gemini 主账号",
    )

    runtime = ProviderRuntimeCache.from_path(config_file)

    try:
        runtime.resolve_model_ref("provider_unknown::gemini-2.5-flash")
        raise AssertionError("应该抛出 ValueError")
    except ValueError as exc:
        assert "未找到 provider: provider_unknown" in str(exc)


def test_resolve_model_ref_rejects_unknown_remote_model_id(tmp_path: Path) -> None:
    config_file = tmp_path / "model_providers.json"
    _write_config(
        config_file,
        default_model_ref="provider_gemini_main::gemini-2.5-flash",
        label="Gemini 主账号",
    )

    runtime = ProviderRuntimeCache.from_path(config_file)

    try:
        runtime.resolve_model_ref("provider_gemini_main::gemini-2.5-pro")
        raise AssertionError("应该抛出 ValueError")
    except ValueError as exc:
        assert "provider provider_gemini_main 不包含 remote_id: gemini-2.5-pro" in str(exc)


def test_refresh_reloads_updated_model_file(tmp_path: Path) -> None:
    config_file = tmp_path / "model_providers.json"
    _write_config(
        config_file,
        default_model_ref="provider_gemini_main::gemini-2.5-flash",
        label="旧版 Gemini 账号",
    )

    runtime = ProviderRuntimeCache.from_path(config_file)

    _write_config(
        config_file,
        default_model_ref="provider_gemini_main::gemini-2.5-pro",
        label="新版 Gemini 账号",
        remote_model_ids=["gemini-2.5-flash", "gemini-2.5-pro"],
    )
    # 刷新时重新读取磁盘 JSON，后续保存后的改动无需重启进程。
    runtime.refresh()

    provider, remote_model_id = runtime.resolve_model_ref("provider_gemini_main::gemini-2.5-flash")

    assert runtime.default_model_ref == "provider_gemini_main::gemini-2.5-pro"
    assert runtime.document.providers[0].label == "新版 Gemini 账号"
    assert remote_model_id == "gemini-2.5-flash"
    assert provider.label == "新版 Gemini 账号"


def test_provider_access_returns_copies_not_internal_state(tmp_path: Path) -> None:
    config_file = tmp_path / "model_providers.json"
    _write_config(
        config_file,
        default_model_ref="provider_gemini_main::gemini-2.5-flash",
        label="原始 Gemini 账号",
    )

    runtime = ProviderRuntimeCache.from_path(config_file)

    provider_copy = runtime.providers_by_id["provider_gemini_main"]
    provider_copy.label = "外部篡改的标题"

    resolved_provider, _ = runtime.resolve_model_ref("provider_gemini_main::gemini-2.5-flash")
    resolved_provider.label = "另一处篡改"

    assert runtime.document.providers[0].label == "原始 Gemini 账号"
    assert runtime.providers_by_id["provider_gemini_main"].label == "原始 Gemini 账号"


def test_app_exposes_provider_runtime_on_startup(monkeypatch, tmp_path: Path) -> None:
    config_file = tmp_path / "model_providers.json"
    _write_config(
        config_file,
        default_model_ref="provider_gemini_main::gemini-2.5-flash",
        label="启动时 Gemini 账号",
    )

    monkeypatch.setattr("backend.main.settings.model_provider_config_path", str(config_file))

    with TestClient(app):
        runtime = app.state.provider_runtime
        assert runtime.default_model_ref == "provider_gemini_main::gemini-2.5-flash"
        provider, remote_model_id = runtime.resolve_model_ref("provider_gemini_main::gemini-2.5-flash")
        assert provider.label == "启动时 Gemini 账号"
        assert remote_model_id == "gemini-2.5-flash"
