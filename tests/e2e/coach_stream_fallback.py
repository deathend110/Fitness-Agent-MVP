import json

from playwright.sync_api import expect, sync_playwright

from coach_e2e_helpers import APP_URL, ensure_vite_dev_server, get_message_texts, install_coach_backend_fetch_mock


MODEL_REF = "provider_deepseek_main::deepseek-v4-flash"
USER_MESSAGE = "请在流式失败后继续给我一个普通回复"
REPLY_TEXT = "回退成功：今天把硬拉训练量减少一组。"

LOCAL_PROFILE = {
    "basic": {
        "name": "测试用户",
        "sex": "male",
        "age": 24,
        "height": 178,
        "weight": 82,
        "waist": 82,
    },
    "oneRM": {"squat": 150, "bench": 100, "deadlift": 180},
    "goal": "增肌",
    "targetWeight": 84,
    "notes": "用于流式回退浏览器验证。",
}

BACKEND_PROFILE = {**LOCAL_PROFILE, "oneRm": LOCAL_PROFILE["oneRM"]}

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
            json.dumps(LOCAL_PROFILE, ensure_ascii=False),
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
            "createdAt": "2026-06-01T00:00:00Z",
            "updatedAt": "2026-06-01T00:10:00Z",
        },
        "sessions": [
            {
                "id": 1,
                "title": "默认对话",
                "createdAt": "2026-06-01T00:00:00Z",
                "updatedAt": "2026-06-01T00:10:00Z",
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
        "streamScenarios": [
            {
                "type": "http_error",
                "status": 503,
                "message": "stream down",
            }
        ],
        "replyScenarios": [{"text": REPLY_TEXT, "suggestion": None, "proposal": None}],
    }


def wait_until_composer_ready(page):
    expect(page.locator("#coach-model-select")).to_have_value(MODEL_REF, timeout=10_000)
    expect(page.locator("textarea")).to_be_visible(timeout=10_000)
    expect(
        page.get_by_text("请先完善档案中的姓名、当前体重、训练目标和深蹲 1RM，再使用 AI 教练。")
    ).not_to_be_visible(timeout=10_000)


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

            wait_until_composer_ready(page)
            page.locator("textarea").fill(USER_MESSAGE)
            page.get_by_role("button", name="发送消息").click()

            expect(page.get_by_text(REPLY_TEXT, exact=True)).to_be_visible(timeout=10_000)
            expect(page.get_by_text("思考中")).not_to_be_visible(timeout=10_000)

            message_texts = get_message_texts(page)
            assert len(message_texts) == 2, message_texts
            assert USER_MESSAGE in message_texts[0], message_texts
            assert REPLY_TEXT in message_texts[1], message_texts

            mock_state = page.evaluate("() => window.__coachMockState")
            assert len(mock_state["streamCalls"]) == 1, mock_state
            assert len(mock_state["replyCalls"]) == 1, mock_state
            assert mock_state["streamCalls"][0]["model"] == MODEL_REF, mock_state
            assert mock_state["streamCalls"][0]["userInput"] == USER_MESSAGE, mock_state
            assert mock_state["replyCalls"][0]["model"] == MODEL_REF, mock_state
            assert mock_state["replyCalls"][0]["userInput"] == USER_MESSAGE, mock_state
            assert mock_state["messagesBySession"]["1"][-1]["content"] == REPLY_TEXT, mock_state["messagesBySession"]

            browser.close()


if __name__ == "__main__":
    main()
