from pathlib import Path
import json
import subprocess
import sys
from types import SimpleNamespace

from scripts.release_gate import (
    REAL_PROVIDER_ENV_KEYS,
    build_release_gate_stages,
    collect_release_env_failures,
    decode_process_output,
    main,
    run_stage,
    write_release_summary,
)


def test_collect_release_env_failures_reports_missing_files(tmp_path: Path) -> None:
    repo_root = tmp_path

    failures = collect_release_env_failures(
        repo_root,
        required_paths=[
            "README.md",
            "ARCHITECTURE.md",
            "tests/e2e/coach_browser_smoke.py",
            "backend/.env.example",
        ],
    )

    assert "README.md" in failures
    assert "ARCHITECTURE.md" in failures
    assert "tests/e2e/coach_browser_smoke.py" in failures
    assert "backend/.env.example" in failures


def test_write_release_summary_persists_stage_results(tmp_path: Path) -> None:
    report_dir = tmp_path / "tests" / "reports" / "release-gate"

    summary_path = write_release_summary(
        report_dir,
        [
            {
                "id": "stage-frontend",
                "label": "前端门禁",
                "status": "passed",
                "duration_seconds": 12.5,
                "command": "npm test",
            },
            {
                "id": "stage-backend",
                "label": "后端门禁",
                "status": "failed",
                "duration_seconds": 3.2,
                "command": "uv run pytest backend/tests -q",
            },
        ],
    )

    assert summary_path.exists()

    payload = summary_path.read_text(encoding="utf-8")
    assert '"id": "stage-frontend"' in payload
    assert '"status": "failed"' in payload
    assert '"command": "uv run pytest backend/tests -q"' in payload


def test_build_release_gate_stages_keeps_required_order() -> None:
    stages = build_release_gate_stages()
    stage_ids = [stage["id"] for stage in stages]

    assert stage_ids == [
        "env-bootstrap",
        "frontend-quality",
        "backend-quality",
        "browser-core",
        "real-provider-smoke",
        "browser-stress",
    ]

    assert stages[0]["commands"] == [
        "npm install",
        "uv sync",
        "uv run python -m playwright install chromium",
        "uv run python scripts/check-release-env.py",
    ]


def test_browser_core_stage_includes_release_core_journey_script() -> None:
    stages = build_release_gate_stages()
    browser_core = next(stage for stage in stages if stage["id"] == "browser-core")

    assert "uv run python tests/e2e/release_core_journey.py" in browser_core["commands"]
    assert Path("tests/e2e/release_core_journey.py").exists()


def test_real_provider_stage_requires_explicit_env_keys() -> None:
    assert REAL_PROVIDER_ENV_KEYS == (
        "BACKEND_HOST",
        "BACKEND_PORT",
        "MODEL_PROVIDER_CONFIG_PATH",
    )

    real_provider_stage = next(
        stage for stage in build_release_gate_stages() if stage["id"] == "real-provider-smoke"
    )
    assert real_provider_stage["commands"] == [
        "uv run python tests/e2e/coach_real_provider_smoke.py"
    ]


def test_browser_stress_stage_requires_task5_script_suite() -> None:
    browser_stress_stage = next(
        stage for stage in build_release_gate_stages() if stage["id"] == "browser-stress"
    )

    assert browser_stress_stage["commands"] == [
        "uv run python tests/e2e/profile_input_fuzz.py",
        "uv run python tests/e2e/today_log_fuzz.py",
        "uv run python tests/e2e/plan_mutation_stress.py",
        "uv run python tests/e2e/navigation_recovery_stress.py",
    ]

    assert Path("tests/e2e/profile_input_fuzz.py").exists()
    assert Path("tests/e2e/today_log_fuzz.py").exists()
    assert Path("tests/e2e/plan_mutation_stress.py").exists()
    assert Path("tests/e2e/navigation_recovery_stress.py").exists()


def test_release_gate_docs_cover_commands_and_architecture() -> None:
    readme = Path("README.md").read_text(encoding="utf-8").lower()
    architecture = Path("ARCHITECTURE.md").read_text(encoding="utf-8").lower()

    assert "run-release-gate.ps1" in readme
    assert "coach_real_provider_smoke.py" in readme
    assert "release gate" in architecture or "发布门禁" in architecture


def test_main_reads_sys_argv_when_no_explicit_argv(monkeypatch) -> None:
    captured = {"called": False}

    def fake_run_all() -> int:
        captured["called"] = True
        return 7

    monkeypatch.setattr("scripts.release_gate.run_all", fake_run_all)
    monkeypatch.setattr("sys.argv", ["scripts/release_gate.py", "run-all"])

    assert main() == 7
    assert captured["called"] is True


def test_check_release_env_script_runs_from_repo_root() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "scripts/check-release-env.py"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "release gate env check passed" in result.stdout.lower()


def test_decode_process_output_handles_none_and_bytes() -> None:
    assert decode_process_output(None) == ""
    assert decode_process_output("plain text") == "plain text"
    assert decode_process_output("中文输出".encode("utf-8")) == "中文输出"


def test_run_stage_writes_log_even_when_process_output_is_missing(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "scripts.release_gate.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=None, stderr=""),
    )

    stage = {
        "id": "fake-stage",
        "label": "假阶段",
        "commands": ["echo noop"],
    }
    result = run_stage(stage, tmp_path, tmp_path / "reports")
    log_path = tmp_path / "reports" / "fake-stage.log"

    assert result["status"] == "passed"
    assert log_path.exists()
    assert "$ echo noop" in log_path.read_text(encoding="utf-8")


def test_real_provider_stage_missing_env_returns_structured_failure_and_updates_summary(
    monkeypatch,
    tmp_path: Path,
) -> None:
    real_provider_stage = next(
        stage for stage in build_release_gate_stages() if stage["id"] == "real-provider-smoke"
    )
    report_dir = tmp_path / "tests" / "reports" / "release-gate"

    for key in REAL_PROVIDER_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)

    stage_result = run_stage(real_provider_stage, tmp_path, report_dir)
    command_log = stage_result["command"]

    assert stage_result["status"] == "failed"
    assert command_log == "uv run python tests/e2e/coach_real_provider_smoke.py"
    assert "BACKEND_HOST" in stage_result["error"]
    assert "MODEL_PROVIDER_CONFIG_PATH" in stage_result["error"]

    stage_log = report_dir / "real-provider-smoke.log"
    stage_log_text = stage_log.read_text(encoding="utf-8")
    assert stage_log.exists()
    assert stage_log_text.startswith(f"$ {command_log}")
    assert "真实 provider 冒烟缺少环境变量" in stage_log_text

    env_bootstrap_stage = build_release_gate_stages()[0]
    monkeypatch.setattr(
        "scripts.release_gate.build_release_gate_stages",
        lambda: [env_bootstrap_stage, real_provider_stage],
    )
    executed_commands: list[str] = []

    def fake_run(command: str, cwd: Path, shell: bool, capture_output: bool) -> SimpleNamespace:
        executed_commands.append(command)
        assert command in env_bootstrap_stage["commands"]
        return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr("scripts.release_gate.subprocess.run", fake_run)
    monkeypatch.setattr("scripts.release_gate.__file__", str(tmp_path / "scripts" / "release_gate.py"))

    exit_code = main(["run-all"])

    assert exit_code == 1

    summary_payload = json.loads((report_dir / "summary.json").read_text(encoding="utf-8"))
    failed_stage = summary_payload["stages"][-1]
    assert failed_stage["id"] == "real-provider-smoke"
    assert failed_stage["status"] == "failed"
    assert failed_stage["command"] == command_log
    assert "BACKEND_PORT" in failed_stage["error"]
    assert command_log not in executed_commands
