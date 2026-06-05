from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable


def collect_release_env_failures(
    repo_root: Path,
    required_paths: Iterable[str] | None = None,
) -> list[str]:
    """收集发布门禁所需基础文件的缺失项。"""
    normalized_root = Path(repo_root)
    missing_paths: list[str] = []

    for relative_path in required_paths or []:
        target_path = normalized_root / relative_path
        if not target_path.exists():
            missing_paths.append(relative_path)

    return missing_paths


def write_release_summary(report_dir: Path, stage_rows: list[dict]) -> Path:
    """将阶段执行摘要写入固定 JSON 文件，供后续门禁汇总复用。"""
    normalized_dir = Path(report_dir)
    normalized_dir.mkdir(parents=True, exist_ok=True)

    summary_path = normalized_dir / "summary.json"
    summary_path.write_text(
        json.dumps({"stages": stage_rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary_path


def main(argv: list[str] | None = None) -> int:
    args = argv or []
    if args and args[0] == "check-env":
        repo_root = Path(__file__).resolve().parents[1]
        failures = collect_release_env_failures(
            repo_root,
            required_paths=[
                "README.md",
                "ARCHITECTURE.md",
                ".env.example",
                "backend/.env.example",
                "tests/e2e/coach_browser_smoke.py",
            ],
        )
        if failures:
            raise SystemExit("缺少发布门禁依赖文件: " + ", ".join(failures))
        print("release gate env check passed")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
