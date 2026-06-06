import json

from playwright.sync_api import expect, sync_playwright

from coach_e2e_helpers import APP_URL, ensure_vite_dev_server, install_coach_backend_fetch_mock


PERSISTED_STATE_KEY = "fitloop:e2e:navigation-recovery-stress:mock-state"
MODEL_REF = "provider_deepseek_main::deepseek-v4-flash"

BACKEND_PROFILE = {
    "basic": {
        "name": "导航恢复用户",
        "sex": "male",
        "age": 31,
        "height": 179,
        "weight": 80.8,
        "waist": 82,
    },
    "oneRm": {"squat": 175, "bench": 110, "deadlift": 200},
    "goal": "维持力量",
    "targetWeight": 80,
    "notes": "用于高频切页和 AI 会话恢复压测。",
}
LOCAL_PROFILE = {**BACKEND_PROFILE, "oneRM": BACKEND_PROFILE["oneRm"]}
WEEKLY_PLAN = {
    day: {"type": "rest", "exercises": []}
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
}
DAILY_LOG = {
    "2026-06-06": {
        "weight": 80.8,
        "kcal": 2400,
        "sleep": 7.2,
        "fatigue": 2,
        "trainingNotes": "状态稳定，今天主要验证会话恢复。",
    }
}


def seed_local_storage(context) -> None:
    context.add_init_script(
        """
        window.localStorage.setItem('fitloop_profile', JSON.stringify(%s));
        window.localStorage.setItem('fitloop_weeklyPlan', JSON.stringify(%s));
        window.localStorage.setItem('fitloop_dailyLog', JSON.stringify(%s));
        window.localStorage.setItem('fitloop_chatHistory', JSON.stringify([]));
        window.localStorage.setItem('fitloop:coach-active-session-id', '1');
        window.localStorage.setItem('fitloop_storageVersion', JSON.stringify('v2-empty-defaults'));
        """
        % (
            json.dumps(LOCAL_PROFILE, ensure_ascii=False),
            json.dumps(WEEKLY_PLAN, ensure_ascii=False),
            json.dumps(DAILY_LOG, ensure_ascii=False),
        )
    )


def build_mock_config() -> dict:
    return {
        "profile": BACKEND_PROFILE,
        "weeklyPlan": WEEKLY_PLAN,
        "dailyLog": DAILY_LOG,
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
            "createdAt": "2026-06-06T00:00:00Z",
            "updatedAt": "2026-06-06T00:00:00Z",
        },
        "sessions": [
            {
                "id": 1,
                "title": "默认对话",
                "createdAt": "2026-06-06T00:00:00Z",
                "updatedAt": "2026-06-06T00:00:00Z",
            },
            {
                "id": 2,
                "title": "恢复记录",
                "createdAt": "2026-06-05T00:00:00Z",
                "updatedAt": "2026-06-05T00:00:00Z",
            },
        ],
        "messagesBySession": {
            "1": [
                {
                    "id": 1001,
                    "sessionId": 1,
                    "role": "assistant",
                    "content": "我会持续读取你的档案、训练计划和今日日志。",
                    "suggestion": None,
                    "attachments": [],
                    "createdAt": "2026-06-06T00:00:00Z",
                }
            ],
            "2": [
                {
                    "id": 2001,
                    "sessionId": 2,
                    "role": "assistant",
                    "content": "旧会话：记录恢复建议。",
                    "suggestion": None,
                    "attachments": [],
                    "createdAt": "2026-06-05T00:00:00Z",
                }
            ],
        },
        "draftsBySession": {
            "1": {
                "content": "保持高频切页后草稿仍可恢复",
                "model": MODEL_REF,
                "thinking": {"enabled": False, "budget": "standard"},
                "attachedFileIds": [],
            },
            "2": {
                "content": "旧会话草稿",
                "model": MODEL_REF,
                "thinking": {"enabled": False, "budget": "standard"},
                "attachedFileIds": [],
            },
        },
        "streamScenarios": [],
        "replyScenarios": [],
    }


def main() -> None:
    with ensure_vite_dev_server(APP_URL) as app_url:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 960})
            seed_local_storage(context)
            install_coach_backend_fetch_mock(
                context,
                build_mock_config(),
                persisted_state_key=PERSISTED_STATE_KEY,
            )
            page = context.new_page()

            page.goto(app_url)
            for tab_name in ["我的档案", "训练计划", "今日日志", "AI 教练"] * 3:
                page.get_by_role("button", name=tab_name, exact=True).click()

            page.get_by_role("button", name="AI 教练", exact=True).click()
            composer = page.locator("textarea")
            expect(composer).to_be_visible(timeout=10_000)
            expect(page.locator("#coach-model-select")).to_have_value(MODEL_REF, timeout=10_000)
            expect(composer).to_have_value("保持高频切页后草稿仍可恢复", timeout=10_000)
            expect(
                page.get_by_text("我会持续读取你的档案、训练计划和今日日志。").first
            ).to_be_visible(timeout=10_000)

            page.reload()
            page.get_by_role("button", name="AI 教练", exact=True).click()
            expect(page.locator("textarea")).to_have_value(
                "保持高频切页后草稿仍可恢复",
                timeout=10_000,
            )
            expect(
                page.get_by_text("我会持续读取你的档案、训练计划和今日日志。").first
            ).to_be_visible(timeout=10_000)

            page.get_by_role("button", name="训练计划", exact=True).click()
            settings_button = page.get_by_role("button", name="计划设置")
            settings_button.click()
            expect(page.get_by_text("计划设置入口")).to_be_visible(timeout=10_000)
            settings_button.click()
            expect(page.get_by_text("计划设置入口")).not_to_be_visible(timeout=10_000)
            settings_button.click()
            expect(page.get_by_text("计划设置入口")).to_be_visible(timeout=10_000)

            page.get_by_role("button", name="今日日志", exact=True).click()
            expect(page.get_by_text("2400 kcal")).to_be_visible(timeout=10_000)
            page.get_by_role("button", name="我的档案", exact=True).click()
            expect(page.get_by_label("当前体重 (kg)")).to_have_value("80.8", timeout=10_000)

            state = page.evaluate("() => window.__coachMockState")
            assert state["defaultSession"]["id"] == 1, state
            assert state["draftsBySession"]["1"]["content"] == "保持高频切页后草稿仍可恢复", state

            browser.close()


if __name__ == "__main__":
    main()
