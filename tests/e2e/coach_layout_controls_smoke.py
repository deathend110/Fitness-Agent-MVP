import json

from playwright.sync_api import expect, sync_playwright

from coach_e2e_helpers import APP_URL, ensure_vite_dev_server, install_coach_backend_fetch_mock


MODEL_REF = "provider_deepseek_main::deepseek-v4-flash"

PROFILE = {
    "basic": {
        "name": "布局回归用户",
        "sex": "male",
        "age": 28,
        "height": 180,
        "weight": 82,
        "waist": 84,
    },
    "oneRM": {"squat": 160, "bench": 105, "deadlift": 190},
    "goal": "维持",
    "targetWeight": 82,
    "notes": "用于验证 AI 教练页顶部和底部操作区不会被布局挤出视口。",
}

BACKEND_PROFILE = {**PROFILE, "oneRm": PROFILE["oneRM"]}

WEEKLY_PLAN = {
    day: {"type": "rest", "exercises": []}
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
}


def seed_local_storage(context):
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


def build_mock_config():
    return {
        "profile": BACKEND_PROFILE,
        "weeklyPlan": WEEKLY_PLAN,
        "dailyLog": {},
        "models": {
            "defaultModel": MODEL_REF,
            "defaultModelRef": MODEL_REF,
            "models": [
                {
                    "id": MODEL_REF,
                    "providerId": "provider_deepseek_main",
                    "providerType": "openai_compatible",
                    "providerLabel": "DeepSeek 主账号",
                    "remoteModelId": "deepseek-v4-flash",
                    "label": "DeepSeek 主账号 / DeepSeek V4 Flash",
                    "supportsThinking": True,
                    "thinking": {
                        "supported": True,
                        "canDisable": True,
                        "defaultEnabled": False,
                        "intensityOptions": [{"id": "standard", "label": "标准"}],
                        "defaultIntensity": "standard",
                    },
                }
            ],
            "thinking": {"enabled": False, "budget": "standard", "options": ["off", "standard"]},
        },
        "defaultSession": {
            "id": 1,
            "title": "默认对话",
            "createdAt": "2026-06-06T08:00:00Z",
            "updatedAt": "2026-06-06T08:00:00Z",
        },
        "sessions": [
            {
                "id": 1,
                "title": "默认对话",
                "createdAt": "2026-06-06T08:00:00Z",
                "updatedAt": "2026-06-06T08:00:00Z",
            }
        ],
        "messagesBySession": {"1": []},
        "draftsBySession": {
            "1": {
                "content": "",
                "model": MODEL_REF,
                "thinking": {"enabled": False, "budget": "standard"},
                "attachedFileIds": [],
            }
        },
        "streamScenarios": [],
        "replyScenarios": [],
    }


def assert_in_viewport(page, selector):
    box = page.locator(selector).bounding_box()
    assert box is not None, f"{selector} 没有可见边界盒"
    viewport = page.viewport_size
    assert viewport is not None
    assert box["y"] >= 0, f"{selector} 顶部溢出视口: {box}"
    assert box["y"] + box["height"] <= viewport["height"], f"{selector} 底部溢出视口: {box}"


def main():
    with ensure_vite_dev_server(APP_URL) as app_url:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            seed_local_storage(context)
            install_coach_backend_fetch_mock(context, build_mock_config())
            page = context.new_page()

            page.goto(app_url)
            page.get_by_role("button", name="AI 教练").click()

            expect(page.get_by_role("button", name="模型设置")).to_be_visible(timeout=10_000)
            expect(page.get_by_role("button", name="清除对话")).to_be_visible(timeout=10_000)
            expect(page.get_by_role("button", name="导出对话")).to_be_visible(timeout=10_000)
            expect(page.locator("#coach-model-select")).to_be_visible(timeout=10_000)
            expect(page.locator("textarea")).to_be_visible(timeout=10_000)
            expect(page.get_by_role("button", name="发送消息")).to_be_visible(timeout=10_000)

            assert_in_viewport(page, 'button[aria-label="模型设置"]')
            assert_in_viewport(page, "#coach-model-select")
            assert_in_viewport(page, "textarea")
            assert_in_viewport(page, 'button[aria-label="发送消息"]')

            browser.close()


if __name__ == "__main__":
    main()
