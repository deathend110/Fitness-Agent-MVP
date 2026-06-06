import json

from playwright.sync_api import expect, sync_playwright

from coach_e2e_helpers import APP_URL, ensure_vite_dev_server, install_coach_backend_fetch_mock


PERSISTED_STATE_KEY = "fitloop:e2e:coach-tab-pending-navigation-restore:mock-state"
MODEL_REF = "provider_deepseek_main::deepseek-v4-flash"
USER_MESSAGE = "我这周卧推状态掉得很明显，先别结束，继续分析原因"

BACKEND_PROFILE = {
    "basic": {
        "name": "切页恢复用户",
        "sex": "male",
        "age": 29,
        "height": 177,
        "weight": 81.2,
        "waist": 83,
    },
    "oneRm": {"squat": 170, "bench": 112, "deadlift": 195},
    "goal": "维持力量",
    "targetWeight": 81,
    "notes": "用于验证 AI 教练发送中切页恢复。",
}
LOCAL_PROFILE = {**BACKEND_PROFILE, "oneRM": BACKEND_PROFILE["oneRm"]}
WEEKLY_PLAN = {
    day: {"type": "rest", "exercises": []}
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
}
DAILY_LOG = {
    "2026-06-06": {
        "weight": 81.2,
        "kcal": 2450,
        "sleep": 7.0,
        "fatigue": 3,
        "trainingNotes": "今天主要验证发送中切页。",
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
            }
        ],
        "messagesBySession": {
            "1": [
                {
                    "id": 1001,
                    "sessionId": 1,
                    "role": "assistant",
                    "content": "把你这周的训练异常点发给我，我会继续结合上下文分析。",
                    "suggestion": None,
                    "attachments": [],
                    "createdAt": "2026-06-06T00:00:00Z",
                }
            ]
        },
        "draftsBySession": {
            "1": {
                "content": "",
                "model": MODEL_REF,
                "thinking": {"enabled": False, "budget": "standard"},
                "attachedFileIds": [],
            }
        },
        "streamScenarios": [
            {
                "type": "sse",
                "events": [
                    {"kind": "tool_status", "payload": {"label": "读取训练档案中"}, "delayMs": 150},
                    # 故意把正文首 token 延后，稳定覆盖“发送中切页再切回”的窗口。
                    {"kind": "delta", "text": "先", "delayMs": 15_000},
                    {"kind": "done", "text": "先看卧推训练量与恢复安排。", "delayMs": 50},
                ],
            }
        ],
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
            page.get_by_role("button", name="AI 教练", exact=True).click()
            composer = page.locator("textarea")
            expect(composer).to_be_visible(timeout=10_000)

            composer.fill(USER_MESSAGE)
            page.get_by_role("button", name="发送消息").click()

            expect(page.get_by_text(USER_MESSAGE).last).to_be_visible(timeout=10_000)
            expect(page.get_by_text("读取训练档案中").last).to_be_visible(timeout=10_000)

            page.get_by_role("button", name="训练计划", exact=True).click()
            expect(page.get_by_role("button", name="计划设置")).to_be_visible(timeout=10_000)

            page.get_by_role("button", name="AI 教练", exact=True).click()
            expect(page.get_by_text(USER_MESSAGE).last).to_be_visible(timeout=10_000)
            expect(page.get_by_text("读取训练档案中").last).to_be_visible(timeout=10_000)

            expect(page.get_by_text("先看卧推训练量与恢复安排。").last).to_be_visible(timeout=25_000)
            expect(page.get_by_text("读取训练档案中")).to_have_count(0, timeout=25_000)

            browser.close()


if __name__ == "__main__":
    main()
