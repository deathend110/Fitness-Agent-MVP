from __future__ import annotations

import json
import os

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
    expect(messages).to_have_count(2, timeout=30_000)


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
    ):
        with ensure_vite_dev_server(APP_URL) as app_url:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(viewport={"width": 1440, "height": 960})
                seed_local_storage(context)
                page = context.new_page()

                page.goto(app_url)
                page.get_by_role("button", name="AI 教练").click()

                composer = page.locator("textarea").first
                expect(composer).to_be_visible(timeout=20_000)
                expect(
                    page.get_by_text("请先完善档案中的姓名、当前体重、训练目标和深蹲 1RM，再使用 AI 教练。")
                ).not_to_be_visible(timeout=10_000)

                composer.fill(PROMPT)
                page.get_by_role("button", name="发送消息").click()
                expect(page.get_by_text("思考中")).to_be_visible(timeout=20_000)
                wait_for_reply(page)

                browser.close()


if __name__ == "__main__":
    main()
