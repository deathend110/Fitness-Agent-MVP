import json

from playwright.sync_api import expect, sync_playwright

from coach_e2e_helpers import APP_URL, ensure_vite_dev_server, get_message_texts, install_coach_backend_fetch_mock


MODEL_REF = "provider_deepseek_main::deepseek-v4-flash"
USER_MESSAGE = "最近疲劳有点高，帮我把周一训练改轻一点。"
FINAL_REPLY = "建议把周一改成恢复腿日，先压低深蹲训练量。"

BACKEND_PROFILE = {
    "basic": {
        "name": "深度流程用户",
        "sex": "male",
        "age": 27,
        "height": 180,
        "weight": 83,
        "waist": 84,
    },
    "oneRm": {"squat": 160, "bench": 110, "deadlift": 200},
    "goal": "增肌",
    "targetWeight": 85,
    "notes": "用于完整 proposal commit 闭环验证。",
}

LOCAL_PROFILE = {**BACKEND_PROFILE, "oneRM": BACKEND_PROFILE["oneRm"]}

DAILY_LOG = {
    "2026-06-03": {
        "weight": 82.6,
        "calories": 2820,
        "fatigue": 8,
        "sleepHours": 5.8,
        "trainingNote": "连续两次腿部训练后恢复偏慢。",
    }
}

WEEKLY_PLAN = {
    "Monday": {
        "type": "腿日",
        "exercises": [
            {
                "id": "monday-squat-main",
                "name": "深蹲",
                "tier": "main",
                "ref1RM": "squat",
                "pct": 0.78,
                "kg": None,
                "sets": 5,
                "reps": 5,
                "rpe": 8.5,
                "note": "原计划高强度主项",
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
                    "note": "降低总量，优先恢复",
                },
                "ref1RM": "squat",
                "pct": 0.68,
                "kg": None,
                "sets": 3,
                "reps": 5,
                "rpe": 7,
                "note": "降低总量，优先恢复",
            }
        ],
    },
}

PROPOSAL = {
    "proposalId": "proposal-commit-flow",
    "kind": "day_plan_replace",
    "day": "Monday",
    "summary": "把周一从高强度腿日调整为恢复腿日。",
    "dayPlan": UPDATED_WEEKLY_PLAN["Monday"],
}


def seed_local_storage(context):
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
            "createdAt": "2026-06-03T08:00:00Z",
            "updatedAt": "2026-06-03T08:10:00Z",
        },
        "sessions": [
            {
                "id": 1,
                "title": "默认对话",
                "createdAt": "2026-06-03T08:00:00Z",
                "updatedAt": "2026-06-03T08:10:00Z",
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
                    {"kind": "tool_status", "payload": {"tool": "get_daily_log", "status": "running"}},
                    {"kind": "delta", "text": "建议把周一改成恢复腿日，", "delayMs": 220},
                    {"kind": "delta", "text": "先压低深蹲训练量。", "delayMs": 260},
                    {"kind": "proposal", "proposal": PROPOSAL, "delayMs": 180},
                    {"kind": "done", "text": FINAL_REPLY, "delayMs": 80},
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


def wait_until_composer_ready(page):
    expect(page.locator("#coach-model-select")).to_have_value(MODEL_REF, timeout=10_000)
    expect(page.locator("textarea")).to_be_visible(timeout=10_000)


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

            expect(page.get_by_text("正在读取今日日志")).to_be_visible(timeout=10_000)
            page.wait_for_function(
                """
                () => {
                  const events = window.__coachMockState.eventLog;
                  return events.filter((entry) => entry.kind === 'delta').length === 2 &&
                    !events.some((entry) => entry.kind === 'proposal');
                }
                """
            )
            expect(page.get_by_text(FINAL_REPLY, exact=True)).to_be_visible(timeout=10_000)
            expect(page.get_by_role("button", name="采纳并更新计划")).not_to_be_visible(timeout=1_000)

            page.wait_for_function(
                "() => window.__coachMockState.eventLog.some((entry) => entry.kind === 'proposal')"
            )
            expect(page.get_by_role("button", name="采纳并更新计划")).to_be_visible(timeout=10_000)
            expect(page.get_by_text("把周一从高强度腿日调整为恢复腿日。")).to_be_visible(timeout=10_000)

            message_texts = get_message_texts(page)
            assert len(message_texts) == 2, message_texts
            assert USER_MESSAGE in message_texts[0], message_texts
            assert FINAL_REPLY in message_texts[1], message_texts

            page.get_by_role("button", name="训练计划").click()
            expect(page.get_by_text("原计划高强度主项")).to_be_visible(timeout=10_000)
            expect(page.get_by_text("降低总量，优先恢复")).not_to_be_visible(timeout=1_000)
            expect(page.get_by_text("5 组 × 5 次")).to_be_visible(timeout=10_000)
            expect(page.get_by_text("3 组 × 5 次")).not_to_be_visible(timeout=1_000)

            page.get_by_role("button", name="AI 教练").click()
            page.get_by_role("button", name="采纳并更新计划").click()
            expect(page.get_by_role("button", name="采纳并更新计划")).not_to_be_visible(timeout=5_000)

            page.get_by_role("button", name="训练计划").click()
            expect(page.get_by_text("降低总量，优先恢复")).to_be_visible(timeout=10_000)
            expect(page.get_by_text("原计划高强度主项")).not_to_be_visible(timeout=5_000)
            expect(page.get_by_text("3 组 × 5 次")).to_be_visible(timeout=10_000)
            expect(page.get_by_text("5 组 × 5 次")).not_to_be_visible(timeout=5_000)
            expect(page.get_by_text("深蹲 1RM 160kg × 68%")).to_be_visible(timeout=10_000)

            mock_state = page.evaluate("() => window.__coachMockState")
            assert mock_state["commitCalls"] == [{"proposalId": "proposal-commit-flow"}], mock_state
            assert len(mock_state["streamCalls"]) == 1, mock_state
            assert mock_state["streamCalls"][0]["userInput"] == USER_MESSAGE, mock_state
            assert mock_state["weeklyPlan"]["Monday"]["type"] == "恢复腿日", mock_state["weeklyPlan"]

            browser.close()


if __name__ == "__main__":
    main()
