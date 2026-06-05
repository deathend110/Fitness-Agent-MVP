# Release Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 RepMind 建立一套可重复执行的发布前终极测试门禁，统一覆盖环境规范、前端单测、后端 pytest、浏览器核心回归、真实 AI 冒烟和高强度扰动测试。

**Architecture:** 采用“Python 可测试核心 + PowerShell 统一入口”的结构。`scripts/release_gate.py` 负责阶段清单、环境检查、日志归档和汇总报告，`scripts/run-release-gate.ps1` 只做 Windows 本地统一入口。浏览器门禁优先复用现有 `tests/e2e/coach_e2e_helpers.py`，新增一条发布主链路和五条发布级补强脚本，并把它们纳入统一阶段清单。

**Tech Stack:** PowerShell、Python 3.11、uv、pytest、Playwright、Vite、Node built-in test runner

---

## File Map

- Create: `scripts/release_gate.py`
  - 发布门禁核心模块，负责环境检查、阶段清单、阶段执行、报告落盘与 CLI。
- Create: `scripts/check-release-env.py`
  - 轻量 wrapper，单独暴露环境/规范检查命令，便于阶段 0 单跑。
- Create: `scripts/run-release-gate.ps1`
  - Windows 统一入口，调用 Python 核心执行全部阶段。
- Create: `backend/tests/test_release_gate.py`
  - 覆盖环境检查、阶段清单、报告摘要和文档约束。
- Create: `tests/e2e/release_core_journey.py`
  - 发布主链路：档案 -> 计划 -> 日志 -> AI -> 建议卡 -> 写回计划。
- Create: `tests/e2e/coach_real_provider_smoke.py`
  - 真实 provider 冒烟链路。
- Create: `tests/e2e/profile_input_fuzz.py`
  - 档案页非法输入与刷新恢复扰动。
- Create: `tests/e2e/today_log_fuzz.py`
  - 今日日志页非法输入、重复保存与刷新恢复扰动。
- Create: `tests/e2e/plan_mutation_stress.py`
  - 训练计划编辑、拖拽、来源切换和重复动作压力测试。
- Create: `tests/e2e/navigation_recovery_stress.py`
  - 高频切页、会话恢复、弹窗反复开关等扰动测试。
- Modify: `README.md`
  - 增加发布门禁命令、真实 AI 冒烟前提、测试报告目录说明。
- Modify: `ARCHITECTURE.md`
  - 增加发布门禁架构与测试分层说明。

### Task 1: 建立发布门禁核心模块与环境检查

**Files:**
- Create: `scripts/release_gate.py`
- Create: `scripts/check-release-env.py`
- Create: `backend/tests/test_release_gate.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests/test_release_gate.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.release_gate'`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/release_gate.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable


def collect_release_env_failures(
    repo_root: Path,
    required_paths: Iterable[str] | None = None,
) -> list[str]:
    normalized_root = Path(repo_root)
    missing: list[str] = []
    for relative_path in required_paths or []:
      target = normalized_root / relative_path
      if not target.exists():
        missing.append(relative_path)
    return missing


def write_release_summary(report_dir: Path, stage_rows: list[dict]) -> Path:
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

```python
# scripts/check-release-env.py
from scripts.release_gate import main


if __name__ == "__main__":
    raise SystemExit(main(["check-env"]))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest backend/tests/test_release_gate.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/release_gate.py scripts/check-release-env.py backend/tests/test_release_gate.py
git commit -m "新增发布门禁核心模块与环境检查"
```

### Task 2: 接通阶段清单、统一报告与 PowerShell 总入口

**Files:**
- Modify: `scripts/release_gate.py`
- Create: `scripts/run-release-gate.ps1`
- Modify: `backend/tests/test_release_gate.py`

- [ ] **Step 1: Write the failing test**

```python
from scripts.release_gate import build_release_gate_stages


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests/test_release_gate.py -q`

Expected: FAIL with `ImportError: cannot import name 'build_release_gate_stages'`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/release_gate.py
import subprocess
import time


def build_release_gate_stages() -> list[dict]:
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
            "commands": ["npm test", "npm run build"],
        },
        {
            "id": "backend-quality",
            "label": "后端 pytest 门禁",
            "commands": ["uv run pytest backend/tests -q"],
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
            "commands": ["uv run python tests/e2e/coach_real_provider_smoke.py"],
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


def run_stage(stage: dict, repo_root: Path, report_dir: Path) -> dict:
    started_at = time.time()
    stage_log_path = report_dir / f"{stage['id']}.log"
    with stage_log_path.open("w", encoding="utf-8") as handle:
        for command in stage["commands"]:
            completed = subprocess.run(
                command,
                cwd=repo_root,
                shell=True,
                text=True,
                capture_output=True,
            )
            handle.write(f"$ {command}\n")
            handle.write(completed.stdout)
            handle.write(completed.stderr)
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
        "command": stage["commands"][-1],
    }


def run_all() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    report_dir = repo_root / "tests" / "reports" / "release-gate"
    results = []
    for stage in build_release_gate_stages():
        result = run_stage(stage, repo_root, report_dir)
        results.append(result)
        if result["status"] != "passed":
            write_release_summary(report_dir, results)
            return 1
    write_release_summary(report_dir, results)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = argv or []
    if args and args[0] == "run-all":
        return run_all()
    ...
```

```powershell
# scripts/run-release-gate.ps1
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
uv run python scripts/release_gate.py run-all
exit $LASTEXITCODE
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest backend/tests/test_release_gate.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/release_gate.py scripts/run-release-gate.ps1 backend/tests/test_release_gate.py
git commit -m "接通发布门禁阶段清单与统一入口"
```

### Task 3: 新增发布主链路浏览器回归脚本并纳入核心阶段

**Files:**
- Create: `tests/e2e/release_core_journey.py`
- Modify: `backend/tests/test_release_gate.py`

- [ ] **Step 1: Write the failing test**

```python
from scripts.release_gate import build_release_gate_stages


def test_browser_core_stage_includes_release_core_journey() -> None:
    browser_core = next(
        stage for stage in build_release_gate_stages() if stage["id"] == "browser-core"
    )
    assert "uv run python tests/e2e/release_core_journey.py" in browser_core["commands"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests/test_release_gate.py -q`

Expected: FAIL because `release_core_journey.py` 尚未加入阶段清单

- [ ] **Step 3: Write minimal implementation**

```python
# tests/e2e/release_core_journey.py
import json

from playwright.sync_api import expect, sync_playwright

from coach_e2e_helpers import APP_URL, ensure_vite_dev_server, install_coach_backend_fetch_mock


def seed_local_storage(context) -> None:
    profile = {
        "basic": {"name": "发布门禁用户", "sex": "male", "age": 29, "height": 181, "weight": 84, "waist": 85},
        "oneRM": {"squat": 165, "bench": 108, "deadlift": 195},
        "goal": "减脂",
        "targetWeight": 80,
        "notes": "用于发布主链路验证。",
    }
    weekly_plan = {
        "Monday": {
            "type": "腿日",
            "exercises": [{"id": "monday-squat", "name": "深蹲", "ref1RM": "squat", "pct": 0.75, "kg": None, "sets": 4, "reps": 6, "rpe": 8, "note": "主项"}],
        },
        "Tuesday": {"type": "rest", "exercises": []},
        "Wednesday": {"type": "rest", "exercises": []},
        "Thursday": {"type": "rest", "exercises": []},
        "Friday": {"type": "rest", "exercises": []},
        "Saturday": {"type": "rest", "exercises": []},
        "Sunday": {"type": "rest", "exercises": []},
    }
    daily_log = {}
    context.add_init_script(
        """
        window.localStorage.setItem('fitloop_profile', JSON.stringify(%s));
        window.localStorage.setItem('fitloop_weeklyPlan', JSON.stringify(%s));
        window.localStorage.setItem('fitloop_dailyLog', JSON.stringify(%s));
        window.localStorage.setItem('fitloop_chatHistory', JSON.stringify([]));
        window.localStorage.setItem('fitloop_storageVersion', JSON.stringify('v2-empty-defaults'));
        """
        % (
            json.dumps(profile, ensure_ascii=False),
            json.dumps(weekly_plan, ensure_ascii=False),
            json.dumps(daily_log, ensure_ascii=False),
        )
    )


def build_mock_config() -> dict:
    updated_plan = {
        "Monday": {
            "type": "恢复腿日",
            "exercises": [{"id": "monday-squat", "name": "深蹲", "ref1RM": "squat", "pct": 0.68, "kg": None, "sets": 3, "reps": 5, "rpe": 7, "note": "降低总量"}],
        }
    }
    return {
        "profile": {
            "basic": {"name": "发布门禁用户", "sex": "male", "age": 29, "height": 181, "weight": 84, "waist": 85},
            "oneRm": {"squat": 165, "bench": 108, "deadlift": 195},
            "goal": "减脂",
            "targetWeight": 80,
            "notes": "用于发布主链路验证。",
        },
        "weeklyPlan": updated_plan,
        "dailyLog": {},
        "models": {"defaultModel": "", "defaultModelRef": "", "models": []},
        "defaultSession": {"id": 1, "title": "默认对话", "createdAt": "2026-06-06T00:00:00Z", "updatedAt": "2026-06-06T00:00:00Z"},
        "sessions": [{"id": 1, "title": "默认对话", "createdAt": "2026-06-06T00:00:00Z", "updatedAt": "2026-06-06T00:00:00Z"}],
        "messagesBySession": {"1": []},
        "draftsBySession": {"1": {"content": "", "model": "", "thinking": {"enabled": False, "budget": "standard"}, "attachedFileIds": []}},
        "streamScenarios": [{
            "type": "sse",
            "events": [
                {"kind": "delta", "text": "建议把周一改成恢复腿日。"},
                {"kind": "proposal", "proposal": {"proposalId": "release-gate-proposal", "kind": "day_plan_replace", "day": "Monday", "summary": "降低周一深蹲总量。", "dayPlan": updated_plan["Monday"]}},
                {"kind": "done", "text": "建议把周一改成恢复腿日。"},
            ],
        }],
        "replyScenarios": [],
        "commitResult": {"ok": True, "message": "已采纳", "plan": {**updated_plan, "Tuesday": {"type": "rest", "exercises": []}, "Wednesday": {"type": "rest", "exercises": []}, "Thursday": {"type": "rest", "exercises": []}, "Friday": {"type": "rest", "exercises": []}, "Saturday": {"type": "rest", "exercises": []}, "Sunday": {"type": "rest", "exercises": []}}},
    }


def main() -> None:
    with ensure_vite_dev_server(APP_URL) as app_url:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 960})
            seed_local_storage(context)
            install_coach_backend_fetch_mock(context, build_mock_config())
            page = context.new_page()
            page.goto(app_url)
            page.get_by_role("button", name="我的档案").click()
            page.get_by_label("姓名").fill("发布门禁用户")
            page.get_by_role("button", name="训练计划").click()
            expect(page.get_by_text("深蹲")).to_be_visible(timeout=10_000)
            page.get_by_role("button", name="今日日志").click()
            page.get_by_label("体重 (kg)").fill("83.6")
            page.get_by_role("button", name="AI 教练").click()
            page.locator("textarea").fill("帮我把周一调整轻一点")
            page.get_by_role("button", name="发送消息").click()
            expect(page.get_by_role("button", name="采纳并更新计划")).to_be_visible(timeout=10_000)
            page.get_by_role("button", name="采纳并更新计划").click()
            page.get_by_role("button", name="训练计划").click()
            expect(page.get_by_text("恢复腿日")).to_be_visible(timeout=10_000)
            expect(page.get_by_text("降低总量")).to_be_visible(timeout=10_000)
            browser.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest backend/tests/test_release_gate.py -q`

Expected: PASS

Run: `uv run python tests/e2e/release_core_journey.py`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/e2e/release_core_journey.py backend/tests/test_release_gate.py
git commit -m "新增发布门禁主链路浏览器回归测试"
```

### Task 4: 新增真实 provider 冒烟链路并纳入外部依赖门禁

**Files:**
- Create: `tests/e2e/coach_real_provider_smoke.py`
- Modify: `scripts/release_gate.py`
- Modify: `backend/tests/test_release_gate.py`

- [ ] **Step 1: Write the failing test**

```python
from scripts.release_gate import REAL_PROVIDER_ENV_KEYS, build_release_gate_stages


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests/test_release_gate.py -q`

Expected: FAIL because `REAL_PROVIDER_ENV_KEYS` 尚未定义

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/release_gate.py
import os

REAL_PROVIDER_ENV_KEYS = (
    "BACKEND_HOST",
    "BACKEND_PORT",
    "MODEL_PROVIDER_CONFIG_PATH",
)


def ensure_real_provider_env() -> None:
    missing = [key for key in REAL_PROVIDER_ENV_KEYS if not os.environ.get(key)]
    if missing:
        raise SystemExit("真实 provider 冒烟缺少环境变量: " + ", ".join(missing))
```

```python
# tests/e2e/coach_real_provider_smoke.py
from playwright.sync_api import expect, sync_playwright


APP_URL = "http://127.0.0.1:5173"
PROMPT = "请用一句话确认你已经读取到了我的训练上下文。"


def main() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 960})
        page.goto(APP_URL, wait_until="networkidle")
        page.get_by_role("button", name="AI 教练").click()
        composer = page.locator("textarea").first
        expect(composer).to_be_visible(timeout=20_000)
        composer.fill(PROMPT)
        page.get_by_role("button", name="发送消息").click()
        expect(page.get_by_text("思考中")).to_be_visible(timeout=20_000)
        assistant_messages = page.locator('[data-role="assistant-message"]')
        expect(assistant_messages.last).to_contain_text("训练", timeout=120_000)
        browser.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest backend/tests/test_release_gate.py -q`

Expected: PASS

Run: `uv run python tests/e2e/coach_real_provider_smoke.py`

Expected: PASS with a real assistant reply visible in the UI

- [ ] **Step 5: Commit**

```bash
git add scripts/release_gate.py tests/e2e/coach_real_provider_smoke.py backend/tests/test_release_gate.py
git commit -m "新增真实AI冒烟门禁测试"
```

### Task 5: 新增四类扰动测试并接入高强度阶段

**Files:**
- Create: `tests/e2e/profile_input_fuzz.py`
- Create: `tests/e2e/today_log_fuzz.py`
- Create: `tests/e2e/plan_mutation_stress.py`
- Create: `tests/e2e/navigation_recovery_stress.py`
- Modify: `backend/tests/test_release_gate.py`

- [ ] **Step 1: Write the failing test**

```python
from scripts.release_gate import build_release_gate_stages


def test_browser_stress_stage_lists_all_release_gate_stress_scripts() -> None:
    browser_stress = next(
        stage for stage in build_release_gate_stages() if stage["id"] == "browser-stress"
    )
    assert browser_stress["commands"] == [
        "uv run python tests/e2e/profile_input_fuzz.py",
        "uv run python tests/e2e/today_log_fuzz.py",
        "uv run python tests/e2e/plan_mutation_stress.py",
        "uv run python tests/e2e/navigation_recovery_stress.py",
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests/test_release_gate.py -q`

Expected: FAIL because高强度阶段命令尚未齐全

- [ ] **Step 3: Write minimal implementation**

```python
# tests/e2e/profile_input_fuzz.py
from playwright.sync_api import expect, sync_playwright

from coach_e2e_helpers import APP_URL, ensure_vite_dev_server


def main() -> None:
    with ensure_vite_dev_server(APP_URL) as app_url:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(app_url)
            page.get_by_role("button", name="我的档案").click()
            weight_input = page.get_by_label("当前体重 (kg)")
            weight_input.fill("9999")
            expect(page.get_by_text("体重", exact=False)).to_be_visible(timeout=5_000)
            weight_input.fill("82.5")
            page.reload()
            page.get_by_role("button", name="我的档案").click()
            expect(page.get_by_label("当前体重 (kg)")).to_have_value("82.5", timeout=10_000)
            browser.close()
```

```python
# tests/e2e/today_log_fuzz.py
from playwright.sync_api import expect, sync_playwright

from coach_e2e_helpers import APP_URL, ensure_vite_dev_server


def main() -> None:
    with ensure_vite_dev_server(APP_URL) as app_url:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(app_url)
            page.get_by_role("button", name="今日日志").click()
            kcal_input = page.get_by_label("热量 (kcal)")
            kcal_input.fill("-1")
            expect(page.get_by_text("热量", exact=False)).to_be_visible(timeout=5_000)
            kcal_input.fill("2300")
            page.reload()
            page.get_by_role("button", name="今日日志").click()
            expect(page.get_by_label("热量 (kcal)")).to_have_value("2300", timeout=10_000)
            browser.close()
```

```python
# tests/e2e/plan_mutation_stress.py
from playwright.sync_api import expect, sync_playwright

from coach_e2e_helpers import APP_URL, ensure_vite_dev_server


def main() -> None:
    with ensure_vite_dev_server(APP_URL) as app_url:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 960})
            page.goto(app_url)
            page.get_by_role("button", name="训练计划").click()
            for _ in range(3):
                page.drag_and_drop(
                    '[data-day-key="Monday"] [data-exercise-id]:nth-child(2)',
                    '[data-day-key="Monday"] [data-exercise-id]:nth-child(1)',
                )
            expect(page.locator('[data-day-key="Monday"] [data-exercise-id]')).to_have_count(2, timeout=10_000)
            browser.close()
```

```python
# tests/e2e/navigation_recovery_stress.py
from playwright.sync_api import expect, sync_playwright

from coach_e2e_helpers import APP_URL, ensure_vite_dev_server


def main() -> None:
    with ensure_vite_dev_server(APP_URL) as app_url:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 960})
            page.goto(app_url)
            for tab_name in ["我的档案", "训练计划", "今日日志", "AI 教练"] * 3:
                page.get_by_role("button", name=tab_name).click()
            page.reload()
            page.get_by_role("button", name="AI 教练").click()
            expect(page.locator("textarea")).to_be_visible(timeout=10_000)
            browser.close()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest backend/tests/test_release_gate.py -q`

Expected: PASS

Run: `uv run python tests/e2e/profile_input_fuzz.py`

Expected: PASS

Run: `uv run python tests/e2e/today_log_fuzz.py`

Expected: PASS

Run: `uv run python tests/e2e/plan_mutation_stress.py`

Expected: PASS

Run: `uv run python tests/e2e/navigation_recovery_stress.py`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/e2e/profile_input_fuzz.py tests/e2e/today_log_fuzz.py tests/e2e/plan_mutation_stress.py tests/e2e/navigation_recovery_stress.py backend/tests/test_release_gate.py
git commit -m "新增发布门禁高强度扰动测试"
```

### Task 6: 同步文档并完成发布门禁最终验证

**Files:**
- Modify: `README.md`
- Modify: `ARCHITECTURE.md`
- Modify: `backend/tests/test_release_gate.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path


def test_release_gate_docs_are_listed_in_readme_and_architecture() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    architecture = Path("ARCHITECTURE.md").read_text(encoding="utf-8")

    assert "run-release-gate.ps1" in readme
    assert "coach_real_provider_smoke.py" in readme
    assert "release gate" in architecture.lower()
    assert "发布门禁" in architecture
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests/test_release_gate.py -q`

Expected: FAIL because 文档尚未提到发布门禁命令和分层结构

- [ ] **Step 3: Write minimal implementation**

```md
<!-- README.md -->
## 发布门禁

发布前执行统一门禁：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-release-gate.ps1
```

其中包含：

1. 环境与规范检查
2. 前端单测与构建
3. 后端 pytest
4. 浏览器核心回归
5. 真实 AI 冒烟（`tests/e2e/coach_real_provider_smoke.py`）
6. 高强度扰动测试
```

```md
<!-- ARCHITECTURE.md -->
## 发布门禁架构

项目在常规前后端测试之外，新增一套 release gate：

1. `scripts/run-release-gate.ps1` 作为 Windows 统一入口
2. `scripts/release_gate.py` 负责阶段清单、执行与摘要归档
3. `tests/e2e/release_core_journey.py` 负责主闭环
4. `tests/e2e/coach_real_provider_smoke.py` 负责真实 provider 冒烟
5. `tests/e2e/*_fuzz.py` / `*_stress.py` 负责乱操作扰动验证
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest backend/tests/test_release_gate.py -q`

Expected: PASS

Run: `npm test`

Expected: PASS

Run: `uv run pytest backend/tests -q`

Expected: PASS

Run: `powershell -ExecutionPolicy Bypass -File .\scripts\run-release-gate.ps1`

Expected: PASS and `tests/reports/release-gate/summary.json` created

- [ ] **Step 5: Commit**

```bash
git add README.md ARCHITECTURE.md backend/tests/test_release_gate.py
git commit -m "补充发布门禁文档与最终验证记录"
```
