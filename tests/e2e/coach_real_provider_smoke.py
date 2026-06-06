from __future__ import annotations

import json
import os
from urllib.request import Request, urlopen

from playwright.sync_api import Page, expect, sync_playwright

from coach_e2e_helpers import APP_URL, ensure_backend_dev_server, ensure_vite_dev_server


REAL_PROVIDER_ENV_KEYS = (
    "BACKEND_HOST",
    "BACKEND_PORT",
    "MODEL_PROVIDER_CONFIG_PATH",
)
PROMPT = "请用一句话确认你已经读取到了我的训练上下文。"
PROFILE = {
    "basic": {
        "name": "真实冒烟用户",
        "sex": "male",
        "age": 28,
        "height": 180,
        "weight": 82,
        "waist": 83,
    },
    "oneRM": {"squat": 160, "bench": 105, "deadlift": 190},
    "goal": "减脂",
    "targetWeight": 79,
    "notes": "用于真实 provider 冒烟门禁。",
}
WEEKLY_PLAN = {
    day: {"type": "rest", "exercises": []}
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
}


def ensure_required_env() -> None:
    # 脚本入口自检和 release gate 门禁都做一次，便于单跑时快速区分环境阻塞与脚本失败。
    missing_keys = [key for key in REAL_PROVIDER_ENV_KEYS if not os.environ.get(key)]
    if missing_keys:
        raise SystemExit("真实 provider 冒烟缺少环境变量: " + ", ".join(missing_keys))


def seed_local_storage(context) -> None:
    # 预置最小可用档案，避免 AI 教练前置 guard 因空数据直接拦截发送。
    context.add_init_script(
        """
        window.localStorage.setItem('fitloop_profile', JSON.stringify(%s));
        window.localStorage.setItem('fitloop_weeklyPlan', JSON.stringify(%s));
        window.localStorage.setItem('fitloop_dailyLog', JSON.stringify({}));
        window.localStorage.setItem('fitloop_chatHistory', JSON.stringify([]));
        window.localStorage.setItem('fitloop:coach-active-session-id', '1');
        window.localStorage.setItem('fitloop_storageVersion', JSON.stringify('v2-empty-defaults'));
        """
        % (
            json.dumps(PROFILE, ensure_ascii=False),
            json.dumps(WEEKLY_PLAN, ensure_ascii=False),
        )
    )


def put_backend_json(base_url: str, path: str, payload: dict) -> None:
    request = Request(
        f"{base_url}{path}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="PUT",
    )
    with urlopen(request, timeout=15) as response:
        if response.status >= 400:  # pragma: no cover
            raise RuntimeError(f"写入真实后端失败：{path} -> HTTP {response.status}")


def seed_backend_state(base_url: str) -> None:
    # 真实 provider 冒烟必须走真实后端上下文注入链路，因此先通过 API 写入最小可用数据，
    # 避免前端首屏拉取空档案/空计划后把本地注入状态覆盖掉。
    put_backend_json(
        base_url,
        "/api/profile",
        {
            "basic": PROFILE["basic"],
            "oneRm": PROFILE["oneRM"],
            "goal": PROFILE["goal"],
            "targetWeight": PROFILE["targetWeight"],
            "notes": PROFILE["notes"],
        },
    )
    put_backend_json(base_url, "/api/weekly-plan", WEEKLY_PLAN)


def wait_for_reply(page: Page) -> None:
    messages = page.locator("article.group")
    page.wait_for_function(
        """
        () => {
          const nodes = Array.from(document.querySelectorAll('article.group'));
          return nodes.some((node) => {
            const text = (node.innerText || '').trim();
            return text && /训练|上下文|计划|恢复|疲劳/.test(text);
          });
        }
        """,
        timeout=120_000,
    )
    page.wait_for_function(
        """
        () => document.querySelectorAll('article.group').length >= 2
        """,
        timeout=30_000,
    )


def wait_until_composer_ready(page: Page) -> None:
    expect(page.locator("textarea").first).to_be_visible(timeout=20_000)
    expect(
        page.get_by_text("请先完善档案中的姓名、当前体重、训练目标和深蹲 1RM，再使用 AI 教练。")
    ).not_to_be_visible(timeout=10_000)
    # 真实后端场景下会先异步恢复默认会话与 draft；等模型下拉拿到有效值后再输入，
    # 避免 draft 水合晚到把刚填入的 prompt 覆盖掉，导致发送按钮一直禁用。
    page.wait_for_function(
        """
        () => {
          const select = document.querySelector('#coach-model-select');
          return Boolean(select && typeof select.value === 'string' && select.value.trim());
        }
        """,
        timeout=20_000,
    )


def main() -> None:
    ensure_required_env()

    with ensure_backend_dev_server(
        host=os.environ["BACKEND_HOST"],
        port=int(os.environ["BACKEND_PORT"]),
        env={
            "BACKEND_HOST": os.environ["BACKEND_HOST"],
            "BACKEND_PORT": os.environ["BACKEND_PORT"],
            "MODEL_PROVIDER_CONFIG_PATH": os.environ["MODEL_PROVIDER_CONFIG_PATH"],
        },
        force_restart=True,
    ):
        seed_backend_state(f"http://{os.environ['BACKEND_HOST']}:{os.environ['BACKEND_PORT']}")
        with ensure_vite_dev_server(APP_URL) as app_url:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(viewport={"width": 1440, "height": 960})
                seed_local_storage(context)
                page = context.new_page()

                page.goto(app_url)
                page.get_by_role("button", name="AI 教练").click()

                composer = page.locator("textarea").first
                wait_until_composer_ready(page)
                composer.fill(PROMPT)
                expect(page.get_by_role("button", name="发送消息")).to_be_enabled(timeout=10_000)
                page.get_by_role("button", name="发送消息").click()
                expect(page.get_by_text("思考中")).to_be_visible(timeout=20_000)
                wait_for_reply(page)

                browser.close()


if __name__ == "__main__":
    main()
