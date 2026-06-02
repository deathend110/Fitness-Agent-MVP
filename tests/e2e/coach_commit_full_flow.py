import json
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright


APP_URL = "http://127.0.0.1:5173"
USER_MESSAGE = "最近疲劳有点高，帮我把周一训练改轻一点。"

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

LOCAL_PROFILE = {
    **BACKEND_PROFILE,
    "oneRM": BACKEND_PROFILE["oneRm"],
}

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

CHAT_HISTORY = [
    {"role": "user", "content": "今天腿很酸，明天怎么安排？"},
    {
        "role": "assistant",
        "content": "先根据疲劳度下调主项总量，再观察恢复。",
    },
    {"role": "user", "content": USER_MESSAGE},
    {
        "role": "assistant",
        "content": "建议把周一改成恢复腿日，先压低深蹲训练量。",
        "suggestion": {
            "proposalId": "proposal-commit-flow",
            "kind": "day_plan_replace",
            "day": "Monday",
            "summary": "把周一从高强度腿日调整为恢复腿日。",
            "dayPlan": UPDATED_WEEKLY_PLAN["Monday"],
        },
    },
]


def json_response(route, payload, status=200):
    route.fulfill(
        status=status,
        content_type="application/json",
        body=json.dumps(payload, ensure_ascii=False),
    )


def install_backend_mock(page, commit_calls):
    persisted_plan = {"value": WEEKLY_PLAN}

    def handle_api(route):
        request = route.request
        path = urlparse(request.url).path.replace("/api", "", 1)
        method = request.method.upper()

        if method == "GET" and path == "/profile":
            return json_response(route, BACKEND_PROFILE)

        if method == "PUT" and path == "/profile":
            return json_response(route, request.post_data_json)

        if method == "GET" and path == "/weekly-plan":
            return json_response(route, persisted_plan["value"])

        if method == "PUT" and path == "/weekly-plan":
            body = request.post_data_json
            persisted_plan["value"] = body
            return json_response(route, persisted_plan["value"])

        if method == "GET" and path == "/daily-log":
            return json_response(route, DAILY_LOG)

        if method == "GET" and path == "/models":
            return json_response(
                route,
                {
                    "defaultModel": "provider_deepseek_main::deepseek-v4-flash",
                    "defaultModelRef": "provider_deepseek_main::deepseek-v4-flash",
                    "models": [
                        {
                            "id": "provider_deepseek_main::deepseek-v4-flash",
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
                    "thinking": {
                        "enabled": False,
                        "budget": "standard",
                        "options": ["off", "standard"],
                    },
                },
            )

        if method == "GET" and path == "/chat/sessions/default":
            return json_response(
                route,
                {
                    "id": 1,
                    "title": "默认对话",
                    "createdAt": "2026-06-03T08:00:00Z",
                    "updatedAt": "2026-06-03T08:10:00Z",
                },
            )

        if method == "GET" and path == "/chat/sessions":
            return json_response(
                route,
                [
                    {
                        "id": 1,
                        "title": "默认对话",
                        "createdAt": "2026-06-03T08:00:00Z",
                        "updatedAt": "2026-06-03T08:10:00Z",
                    }
                ],
            )

        if method == "GET" and path == "/chat/sessions/1/messages":
            return json_response(
                route,
                [
                    {
                        "id": index + 1,
                        "sessionId": 1,
                        "role": message["role"],
                        "content": message["content"],
                        "suggestion": message.get("suggestion"),
                        "attachments": message.get("attachments", []),
                        "createdAt": "2026-06-03T08:00:00Z",
                    }
                    for index, message in enumerate(CHAT_HISTORY)
                ],
            )

        if path == "/chat/sessions/1/draft":
            if method == "GET":
                return json_response(
                    route,
                    {
                        "content": "",
                        "model": "provider_deepseek_main::deepseek-v4-flash",
                        "thinking": {"enabled": False, "budget": "standard"},
                        "attachedFileIds": [],
                    },
                )
            if method == "PUT":
                return json_response(route, {"ok": True})

        if method == "POST" and path == "/tools/plan/commit":
            commit_calls.append(request.post_data_json)
            persisted_plan["value"] = UPDATED_WEEKLY_PLAN
            return json_response(
                route,
                {
                    "ok": True,
                    "message": "已采纳",
                    "plan": UPDATED_WEEKLY_PLAN,
                },
            )

        if method == "POST" and path == "/tools/plan/ignore":
            return json_response(route, {"ok": True})

        return json_response(route, {"ok": True})

    page.route("http://127.0.0.1:8000/api/**", handle_api)


def seed_local_storage(context):
    seed_payload = json.dumps(
        {
            "profile": LOCAL_PROFILE,
            "weeklyPlan": WEEKLY_PLAN,
            "dailyLog": DAILY_LOG,
            "chatHistory": CHAT_HISTORY,
        },
        ensure_ascii=False,
    )

    context.add_init_script(
        f"""
        const seedPayload = {seed_payload};
        window.localStorage.setItem('fitloop_profile', JSON.stringify(seedPayload.profile));
        window.localStorage.setItem('fitloop_weeklyPlan', JSON.stringify(seedPayload.weeklyPlan));
        window.localStorage.setItem('fitloop_dailyLog', JSON.stringify(seedPayload.dailyLog));
        window.localStorage.setItem('fitloop_chatHistory', JSON.stringify(seedPayload.chatHistory));
        window.localStorage.setItem('fitloop:coach-active-session-id', '1');
        window.localStorage.setItem('fitloop_storageVersion', JSON.stringify('v2-empty-defaults'));
        """
    )


def main():
    commit_calls = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        seed_local_storage(context)
        page = context.new_page()
        install_backend_mock(page, commit_calls)

        page.goto(APP_URL)
        page.get_by_role("button", name="AI 教练").click()

        expect(page.get_by_text(USER_MESSAGE).first).to_be_visible(timeout=10_000)
        expect(page.get_by_text("把周一从高强度腿日调整为恢复腿日。")).to_be_visible(timeout=10_000)
        expect(page.get_by_role("button", name="采纳并更新计划")).to_be_visible(timeout=10_000)

        page.get_by_role("button", name="训练计划").click()
        expect(page.get_by_text("原计划高强度主项")).to_be_visible(timeout=10_000)
        expect(page.get_by_text("降低总量，优先恢复")).not_to_be_visible(timeout=2_000)
        expect(page.get_by_text("5 组 × 5 次")).to_be_visible(timeout=10_000)
        expect(page.get_by_text("3 组 × 5 次")).not_to_be_visible(timeout=2_000)

        page.get_by_role("button", name="AI 教练").click()
        page.get_by_role("button", name="采纳并更新计划").click()
        expect(page.get_by_role("button", name="采纳并更新计划")).not_to_be_visible(timeout=5_000)

        page.get_by_role("button", name="训练计划").click()
        expect(page.get_by_text("降低总量，优先恢复")).to_be_visible(timeout=10_000)
        expect(page.get_by_text("原计划高强度主项")).not_to_be_visible(timeout=5_000)
        expect(page.get_by_text("3 组 × 5 次")).to_be_visible(timeout=10_000)
        expect(page.get_by_text("5 组 × 5 次")).not_to_be_visible(timeout=5_000)
        expect(page.get_by_text("深蹲 1RM 160kg × 68%")).to_be_visible(timeout=10_000)

        assert commit_calls == [{"proposalId": "proposal-commit-flow"}], commit_calls

        browser.close()


if __name__ == "__main__":
    main()
