from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable


REAL_PROVIDER_ENV_KEYS = (
    "BACKEND_HOST",
    "BACKEND_PORT",
    "MODEL_PROVIDER_CONFIG_PATH",
)


def build_release_gate_stages() -> list[dict]:
    """定义发布门禁的固定阶段顺序与阶段命令清单。"""
    return [
        {
            "id": "env-bootstrap",
            "label": "环境与规范门禁",
            "commands": [
                "npm install",
                "uv sync",
                "uv run python -m playwright install chromium",
                "uv run python scripts/check-release-env.py",
            ],
        },
        {
            "id": "frontend-quality",
            "label": "前端单测与构建门禁",
            "commands": [
                "npm test",
                "npm run build",
            ],
        },
        {
            "id": "backend-quality",
            "label": "后端 pytest 门禁",
            "commands": [
                "uv run pytest backend/tests -q",
            ],
        },
        {
            "id": "browser-core",
            "label": "浏览器核心回归门禁",
            "commands": [
                "uv run python tests/e2e/release_core_journey.py",
                "uv run python tests/e2e/coach_browser_smoke.py",
                "uv run python tests/e2e/plan_drag_sort.py",
                "uv run python tests/e2e/coach_commit_full_flow.py",
                "uv run python tests/e2e/coach_session_history.py",
                "uv run python tests/e2e/coach_model_config_flow.py",
            ],
        },
        {
            "id": "real-provider-smoke",
            "label": "真实 AI 冒烟门禁",
            "commands": [
                "uv run python tests/e2e/coach_real_provider_smoke.py",
            ],
        },
        {
            "id": "browser-stress",
            "label": "浏览器高强度扰动门禁",
            "commands": [
                "uv run python tests/e2e/profile_input_fuzz.py",
                "uv run python tests/e2e/today_log_fuzz.py",
                "uv run python tests/e2e/plan_mutation_stress.py",
                "uv run python tests/e2e/navigation_recovery_stress.py",
            ],
        },
    ]


def ensure_real_provider_env() -> None:
    """真实 provider 冒烟前显式校验必要环境，避免把配置问题误判成业务失败。"""
    missing_keys = [key for key in REAL_PROVIDER_ENV_KEYS if not os.environ.get(key)]
    if missing_keys:
        raise SystemExit("真实 provider 冒烟缺少环境变量: " + ", ".join(missing_keys))


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


def decode_process_output(payload: bytes | str | None) -> str:
    """兼容 Windows 下命令输出编码波动，统一把日志内容收敛成可写入文本。"""
    if payload is None:
        return ""

    if isinstance(payload, str):
        return payload

    for encoding in ("utf-8", "gbk", sys.getdefaultencoding()):
        try:
            return payload.decode(encoding)
        except UnicodeDecodeError:
            continue

    return payload.decode("utf-8", errors="replace")


def run_stage(stage: dict, repo_root: Path, report_dir: Path) -> dict:
    """执行单个阶段并把命令输出落到对应日志文件。"""
    normalized_report_dir = Path(report_dir)
    normalized_report_dir.mkdir(parents=True, exist_ok=True)

    started_at = time.time()
    stage_log_path = normalized_report_dir / f"{stage['id']}.log"
    last_command = stage["commands"][-1] if stage["commands"] else ""

    with stage_log_path.open("w", encoding="utf-8") as handle:
        if stage["id"] == "real-provider-smoke":
            try:
                ensure_real_provider_env()
            except SystemExit as exc:
                error_message = str(exc)
                # 真实 provider 缺配置时要按阶段失败落盘，避免 summary 保留上一次结果。
                handle.write(error_message + "\n")
                return {
                    "id": stage["id"],
                    "label": stage["label"],
                    "status": "failed",
                    "duration_seconds": round(time.time() - started_at, 2),
                    "command": last_command,
                    "error": error_message,
                }

        for command in stage["commands"]:
            completed = subprocess.run(
                command,
                cwd=repo_root,
                shell=True,
                capture_output=True,
            )
            handle.write(f"$ {command}\n")
            handle.write(decode_process_output(completed.stdout))
            handle.write(decode_process_output(completed.stderr))

            if completed.returncode != 0:
                return {
                    "id": stage["id"],
                    "label": stage["label"],
                    "status": "failed",
                    "duration_seconds": round(time.time() - started_at, 2),
                    "command": command,
                }

    return {
        "id": stage["id"],
        "label": stage["label"],
        "status": "passed",
        "duration_seconds": round(time.time() - started_at, 2),
        "command": last_command,
    }


def run_all() -> int:
    """按固定顺序执行全部发布门禁阶段，并产出统一摘要。"""
    repo_root = Path(__file__).resolve().parents[1]
    report_dir = repo_root / "tests" / "reports" / "release-gate"
    results: list[dict] = []

    for stage in build_release_gate_stages():
        result = run_stage(stage, repo_root, report_dir)
        results.append(result)
        if result["status"] != "passed":
            write_release_summary(report_dir, results)
            return 1

    write_release_summary(report_dir, results)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(argv) if argv is not None else sys.argv[1:]
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
    elif args and args[0] == "run-all":
        return run_all()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
