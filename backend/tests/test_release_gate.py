from pathlib import Path

from scripts.release_gate import (
    REAL_PROVIDER_ENV_KEYS,
    build_release_gate_stages,
    collect_release_env_failures,
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
