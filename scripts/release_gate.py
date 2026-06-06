from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable

from tests.e2e.coach_e2e_helpers import ensure_backend_dev_server


REAL_PROVIDER_ENV_KEYS = (
    "BACKEND_HOST",
    "BACKEND_PORT",
    "MODEL_PROVIDER_CONFIG_PATH",
)
WORKTREE_ENV_FILES = (
    ".env",
    "backend/.env",
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


def discover_main_repo_root(repo_root: Path) -> Path | None:
    normalized_root = Path(repo_root).resolve()
    try:
        worktrees_index = normalized_root.parts.index(".worktrees")
    except ValueError:
        return None
    return Path(*normalized_root.parts[:worktrees_index])


def copy_env_file_if_missing(repo_root: Path, relative_path: str, source_root: Path | None) -> None:
    target_path = Path(repo_root) / relative_path
    if target_path.exists() or source_root is None:
        return

    source_path = source_root / relative_path
    if not source_path.exists():
        return

    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_path, target_path)


def copy_supporting_file_if_missing(
    repo_root: Path,
    source_root: Path | None,
    target_path: Path,
    source_path: Path,
) -> None:
    if target_path.exists() or source_root is None or not source_path.exists():
        return
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_path, target_path)


def parse_env_file(env_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not env_path.exists():
        return values

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        values[key.strip()] = raw_value.strip().strip("\"'")
    return values


def prepare_real_provider_workspace(repo_root: Path) -> dict[str, object]:
    normalized_root = Path(repo_root).resolve()
    source_root = discover_main_repo_root(normalized_root)

    for relative_path in WORKTREE_ENV_FILES:
        copy_env_file_if_missing(normalized_root, relative_path, source_root)

    env_path = normalized_root / ".env"
    backend_env_path = normalized_root / "backend" / ".env"
    missing_files = [
        relative_path
        for relative_path, path in (
            (".env", env_path),
            ("backend/.env", backend_env_path),
        )
        if not path.exists()
    ]
    if missing_files:
        raise SystemExit(
            "真实 provider 冒烟缺少环境文件: "
            + ", ".join(missing_files)
            + "；请先在主仓库或当前 worktree 提供可用配置。"
        )

    backend_env = parse_env_file(backend_env_path)
    backend_host = backend_env.get("BACKEND_HOST") or os.environ.get("BACKEND_HOST") or "127.0.0.1"
    raw_backend_port = backend_env.get("BACKEND_PORT") or os.environ.get("BACKEND_PORT") or "8000"
    model_provider_config_path = (
        backend_env.get("MODEL_PROVIDER_CONFIG_PATH")
        or os.environ.get("MODEL_PROVIDER_CONFIG_PATH")
        or ""
    )

    try:
        backend_port = int(raw_backend_port)
    except ValueError as exc:
        raise SystemExit(f"真实 provider 冒烟的 BACKEND_PORT 非法: {raw_backend_port}") from exc

    os.environ["BACKEND_HOST"] = backend_host
    os.environ["BACKEND_PORT"] = str(backend_port)

    if not model_provider_config_path:
        raise SystemExit("真实 provider 冒烟缺少环境变量: MODEL_PROVIDER_CONFIG_PATH")

    config_path = Path(model_provider_config_path)
    if not config_path.is_absolute():
        relative_config_path = Path("backend") / config_path
        target_config_path = (normalized_root / relative_config_path).resolve()
        source_config_path = (
            (source_root / relative_config_path).resolve() if source_root is not None else target_config_path
        )
        copy_supporting_file_if_missing(
            normalized_root,
            source_root,
            target_config_path,
            source_config_path,
        )
        config_path = target_config_path
    if not config_path.exists():
        raise SystemExit(
            "真实 provider 冒烟缺少 provider 配置文件: "
            f"{config_path}"
        )

    os.environ["MODEL_PROVIDER_CONFIG_PATH"] = str(config_path)
    return {
        "backend_host": backend_host,
        "backend_port": backend_port,
        "model_provider_config_path": str(config_path),
    }


@contextmanager
def ensure_real_provider_runtime(repo_root: Path):
    runtime = prepare_real_provider_workspace(repo_root)
    backend_env = {
        "BACKEND_HOST": str(runtime["backend_host"]),
        "BACKEND_PORT": str(runtime["backend_port"]),
        "MODEL_PROVIDER_CONFIG_PATH": str(runtime["model_provider_config_path"]),
    }

    with ensure_backend_dev_server(
        host=str(runtime["backend_host"]),
        port=int(runtime["backend_port"]),
        env=backend_env,
    ):
        yield runtime


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
                runtime_context = ensure_real_provider_runtime(repo_root)
                with runtime_context:
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
            except SystemExit as exc:
                error_message = str(exc)
                # 真实 provider 缺配置或自举失败时要按阶段失败落盘，避免 summary 保留上一次结果。
                if last_command:
                    handle.write(f"$ {last_command}\n")
                handle.write(error_message + "\n")
                return {
                    "id": stage["id"],
                    "label": stage["label"],
                    "status": "failed",
                    "duration_seconds": round(time.time() - started_at, 2),
                    "command": last_command,
                    "error": error_message,
                }
        else:
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
