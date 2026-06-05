from pathlib import Path

from scripts.release_gate import collect_release_env_failures, write_release_summary


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
