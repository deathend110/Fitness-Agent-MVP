import json

from playwright.sync_api import expect, sync_playwright

from coach_e2e_helpers import APP_URL, ensure_vite_dev_server, install_coach_backend_fetch_mock


MODEL_REF = "provider_deepseek_main::deepseek-v4-flash"
USER_MESSAGE = "帮我把周一调整轻一点"
FINAL_REPLY = "建议把周一改成恢复腿日。"

BACKEND_PROFILE = {
    "basic": {
        "name": "发布门禁用户",
        "sex": "male",
        "age": 29,
        "height": 181,
        "weight": 84,
        "waist": 85,
    },
    "oneRm": {"squat": 165, "bench": 108, "deadlift": 195},
    "goal": "减脂",
    "targetWeight": 80,
    "notes": "用于发布主链路验证。",
}

LOCAL_PROFILE = {**BACKEND_PROFILE, "oneRM": BACKEND_PROFILE["oneRm"]}

WEEKLY_PLAN = {
    "Monday": {
        "type": "腿日",
        "exercises": [
            {
                "id": "monday-squat-main",
                "name": "深蹲",
                "tier": "main",
                "ref1RM": "squat",
                "pct": 0.75,
                "kg": None,
                "sets": 4,
                "reps": 6,
                "rpe": 8,
                "note": "主项",
            }
        ],
    },
    "Tuesday": {"type": "rest", "exercises": []},
    "Wednesday": {"type": "rest", "exercises": []},
    "Thursday": {"type": "rest", "exercises": []},
    "Friday": {"type": "rest", "exercises": []},
    "Saturday": {"type": "rest", "exercises": []},
    "Sunday": {"type": "rest", "exercises": []},
}

DAILY_LOG = {}

UPDATED_WEEKLY_PLAN = {
    **WEEKLY_PLAN,
    "Monday": {
        "type": "恢复腿日",
        "exercises": [
            {
                "id": "monday-squat-recovery",
                "name": "深蹲",
                "tier": "main",
                "template": {
                    "loadMode": "percentage",
                    "ref1RM": "squat",
                    "setType": "straight",
                    "sets": 3,
                    "repsText": "5",
                },
                "instance": {
                    "pct": 0.68,
                    "kg": None,
                    "rpe": 7,
                    "note": "降低总量",
                },
                "ref1RM": "squat",
                "pct": 0.68,
                "kg": None,
                "sets": 3,
                "reps": 5,
                "rpe": 7,
                "note": "降低总量",
            }
        ],
    },
}

PROPOSAL = {
    "proposalId": "release-gate-proposal",
    "kind": "day_plan_replace",
    "day": "Monday",
    "summary": "降低周一深蹲总量。",
    "dayPlan": UPDATED_WEEKLY_PLAN["Monday"],
}


def seed_local_storage(context):
    # 直接预置 MVP 核心数据，避免 UI 初始化阶段受空态干扰。
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


def build_mock_config():
    # 复用共享 fetch mock，保证对话流、proposal 写回和计划读取走同一份状态。
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
                "type": "sse",
                "events": [
                    {"kind": "tool_status", "payload": {"tool": "get_profile", "status": "running"}},
                    {"kind": "tool_status", "payload": {"tool": "get_weekly_plan", "status": "running"}, "delayMs": 120},
                    {"kind": "tool_status", "payload": {"tool": "get_daily_log", "status": "running"}, "delayMs": 120},
                    {"kind": "delta", "text": "建议把周一改成恢复腿日。", "delayMs": 180},
                    {"kind": "proposal", "proposal": PROPOSAL, "delayMs": 120},
                    {"kind": "done", "text": FINAL_REPLY, "delayMs": 60},
                ],
            }
        ],
        "replyScenarios": [],
        "commitResult": {
            "ok": True,
            "message": "已采纳",
            "plan": UPDATED_WEEKLY_PLAN,
        },
    }


def main():
    with ensure_vite_dev_server(APP_URL) as app_url:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 960})
            seed_local_storage(context)
            install_coach_backend_fetch_mock(context, build_mock_config())
            page = context.new_page()

            page.goto(app_url)

            page.get_by_role("button", name="我的档案").click()
            expect(page.get_by_role("heading", name="我的档案")).to_be_visible(timeout=10_000)
            expect(page.get_by_label("姓名")).to_have_value("发布门禁用户", timeout=10_000)

            page.get_by_role("button", name="训练计划").click()
            expect(page.get_by_role("heading", name="本周训练计划")).to_be_visible(timeout=10_000)
            expect(page.get_by_text("深蹲", exact=True)).to_be_visible(timeout=10_000)
            expect(page.get_by_text("深蹲 1RM 165kg × 75%")).to_be_visible(timeout=10_000)

            page.get_by_role("button", name="今日日志").click()
            expect(page.get_by_role("heading", name="今日日志")).to_be_visible(timeout=10_000)
            page.get_by_label("体重").fill("83.6")
            page.get_by_role("button", name="保存今日日志").click()
            page.wait_for_function(
                """
                () => {
                  const todayKey = new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Shanghai' }).replaceAll('/', '-');
                  const payload = JSON.parse(window.localStorage.getItem('fitloop_dailyLog') || '{}');
                  return payload?.[todayKey]?.weight === 83.6;
                }
                """
            )

            page.get_by_role("button", name="AI 教练", exact=True).click()
            expect(page.locator("#coach-model-select")).to_have_value(MODEL_REF, timeout=10_000)
            page.locator("textarea").fill(USER_MESSAGE)
            page.get_by_role("button", name="发送消息").click()

            expect(page.get_by_text("正在读取用户档案")).to_be_visible(timeout=10_000)
            expect(page.get_by_text(FINAL_REPLY, exact=True)).to_be_visible(timeout=10_000)
            expect(page.get_by_role("button", name="采纳并更新计划")).to_be_visible(timeout=10_000)
            expect(page.get_by_text("降低周一深蹲总量。")).to_be_visible(timeout=10_000)

            page.get_by_role("button", name="采纳并更新计划").click()
            expect(page.get_by_role("button", name="采纳并更新计划")).not_to_be_visible(timeout=5_000)

            page.get_by_role("button", name="训练计划").click()
            expect(page.get_by_text("深蹲 1RM 165kg × 68%")).to_be_visible(timeout=10_000)
            expect(page.get_by_text("降低总量")).to_be_visible(timeout=10_000)
            expect(page.get_by_text("3 组 × 5 次")).to_be_visible(timeout=10_000)

            mock_state = page.evaluate("() => window.__coachMockState")
            assert mock_state["streamCalls"][0]["userInput"] == USER_MESSAGE, mock_state
            assert mock_state["commitCalls"] == [{"proposalId": "release-gate-proposal"}], mock_state
            assert mock_state["weeklyPlan"]["Monday"]["type"] == "恢复腿日", mock_state["weeklyPlan"]

            browser.close()


if __name__ == "__main__":
    main()
