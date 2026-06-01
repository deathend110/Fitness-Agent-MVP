import json
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright


APP_URL = "http://127.0.0.1:5173"


PROFILE = {
    "basic": {
        "name": "测试用户",
        "sex": "male",
        "age": 24,
        "height": 178,
        "weight": 82,
        "waist": 82,
    },
    "oneRM": {
        "squat": 150,
        "bench": 100,
        "deadlift": 180,
    },
    "goal": "增肌",
    "targetWeight": 84,
    "notes": "用于浏览器自动化冒烟验证。",
}

WEEKLY_PLAN = {
    "Monday": {
        "type": "训练日",
        "exercises": [
            {
                "id": "monday-squat",
                "name": "深蹲",
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

UPDATED_WEEKLY_PLAN = {
    **WEEKLY_PLAN,
    "Monday": {
        **WEEKLY_PLAN["Monday"],
        "exercises": [
            {
                **WEEKLY_PLAN["Monday"]["exercises"][0],
                "sets": 3,
                "note": "浏览器自动化已采纳",
            }
        ],
    },
}

USER_MESSAGE = "请帮我把周一深蹲降一点量"


def build_chat_history():
    history = []
    for index in range(12):
        history.append({"role": "user", "content": f"历史提问 {index + 1}"})
        history.append({"role": "assistant", "content": f"历史回复 {index + 1}"})

    history.append({"role": "user", "content": USER_MESSAGE})
    history.append(
        {
            "role": "assistant",
            "content": "建议先把周一深蹲总量降一组，观察恢复。",
            "suggestion": {
                "proposalId": "proposal-e2e",
                "day": "Monday",
                "summary": "周一深蹲降低一组，用于验证采纳链路。",
                "changes": [
                    {
                        "action": "update",
                        "exerciseName": "深蹲",
                        "field": "sets",
                        "oldValue": 4,
                        "newValue": 3,
                    }
                ],
            },
        }
    )
    return history


CHAT_HISTORY = build_chat_history()

BACKGROUND_TASK = {
    "taskId": "task-e2e",
    "sessionId": 1,
    "sourceUserIndex": len(CHAT_HISTORY) - 2,
    "userContent": USER_MESSAGE,
    "files": [],
    "createdAt": "2026-06-01T00:00:00.000Z",
}


def json_response(route, payload, status=200):
    route.fulfill(
        status=status,
        content_type="application/json",
        body=json.dumps(payload, ensure_ascii=False),
    )


def install_backend_mock(page, commit_calls):
    def handle_api(route):
        request = route.request
        path = urlparse(request.url).path.replace("/api", "", 1)
        method = request.method.upper()

        if method == "GET" and path == "/profile":
            return json_response(route, PROFILE)

        if method == "PUT" and path == "/profile":
            return json_response(route, PROFILE)

        if method == "GET" and path == "/weekly-plan":
            return json_response(route, WEEKLY_PLAN)

        if method == "PUT" and path == "/weekly-plan":
            return json_response(route, UPDATED_WEEKLY_PLAN)

        if method == "GET" and path == "/daily-log":
            return json_response(route, {})

        if method == "GET" and path == "/models":
            return json_response(
                route,
                {
                    "defaultModel": "deepseek-v4-flash",
                    "models": [
                        {
                            "id": "deepseek-v4-flash",
                            "label": "DeepSeek V4 Flash",
                            "supportsThinking": True,
                        }
                    ],
                    "thinking": {
                        "enabled": False,
                        "budget": "auto",
                        "options": ["off", "auto", "max"],
                    },
                },
            )

        if method == "GET" and path == "/chat/sessions/default":
            return json_response(
                route,
                {
                    "id": 1,
                    "title": "默认对话",
                    "createdAt": "2026-06-01T00:00:00Z",
                    "updatedAt": "2026-06-01T00:10:00Z",
                },
            )

        if method == "GET" and path == "/chat/sessions":
            return json_response(
                route,
                [
                    {
                        "id": 1,
                        "title": "默认对话",
                        "createdAt": "2026-06-01T00:00:00Z",
                        "updatedAt": "2026-06-01T00:10:00Z",
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
                        "createdAt": "2026-06-01T00:00:00Z",
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
                        "model": "deepseek-v4-flash",
                        "thinking": {"enabled": False, "budget": "auto"},
                    },
                )
            if method == "PUT":
                return json_response(route, {"ok": True})

        if method == "GET" and path == "/chat/background/task-e2e":
            return json_response(route, {"task_id": "task-e2e", "status": "pending"})

        if method == "POST" and path == "/tools/plan/commit":
            commit_calls.append(request.post_data_json)
            return json_response(
                route,
                {
                    "ok": True,
                    "message": "已采纳",
                    "plan": UPDATED_WEEKLY_PLAN,
                },
            )

        return json_response(route, {"ok": True})

    page.route("http://127.0.0.1:8000/api/**", handle_api)


def seed_local_storage(context):
    # 这里直接模拟“已发送消息 + 后台任务未完成 + 已生成采纳卡片”的真实恢复场景。
    seed_payload = json.dumps(
        {
            "profile": PROFILE,
            "weeklyPlan": WEEKLY_PLAN,
            "chatHistory": CHAT_HISTORY,
            "backgroundTask": BACKGROUND_TASK,
        },
        ensure_ascii=False,
    )

    context.add_init_script(
        f"""
        const seedPayload = {seed_payload};
        window.localStorage.setItem('fitloop_profile', JSON.stringify(seedPayload.profile));
        window.localStorage.setItem('fitloop_weeklyPlan', JSON.stringify(seedPayload.weeklyPlan));
        window.localStorage.setItem('fitloop_dailyLog', JSON.stringify({{}}));
        window.localStorage.setItem('fitloop_chatHistory', JSON.stringify(seedPayload.chatHistory));
        window.localStorage.setItem('fitloop:coach-active-session-id', '1');
        window.localStorage.setItem('fitloop_storageVersion', JSON.stringify('v2-empty-defaults'));
        window.localStorage.setItem('fitloop:coach-background-task', JSON.stringify(seedPayload.backgroundTask));
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
        expect(page.get_by_text("正在整理上下文...")).to_be_visible(timeout=10_000)
        expect(page.get_by_role("button", name="采纳并更新计划")).to_be_visible()
        coach_scroll = page.locator('main > div[style*="scrollbar-gutter"]')
        expect(coach_scroll).to_be_visible()
        page.wait_for_function(
            "() => { const el = document.querySelector('main > div[style*=\"scrollbar-gutter\"]'); return !!el && el.scrollTop > 0; }"
        )

        page.get_by_role("button", name="我的档案").click()
        page.get_by_role("button", name="AI 教练").click()

        expect(page.get_by_text("正在整理上下文...")).to_be_visible(timeout=10_000)
        expect(page.get_by_role("button", name="采纳并更新计划")).to_be_visible()
        page.wait_for_function(
            "() => { const el = document.querySelector('main > div[style*=\"scrollbar-gutter\"]'); return !!el && el.scrollTop > 0; }"
        )

        page.get_by_role("button", name="采纳并更新计划").click()
        expect(page.get_by_role("button", name="采纳并更新计划")).not_to_be_visible(timeout=5_000)

        assert commit_calls == [{"proposalId": "proposal-e2e"}], commit_calls
        browser.close()


if __name__ == "__main__":
    main()
