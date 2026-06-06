import json
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright
from coach_e2e_helpers import ensure_vite_dev_server


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
    "oneRM": {"squat": 150, "bench": 100, "deadlift": 180},
    "goal": "增肌",
    "targetWeight": 84,
    "notes": "用于真实会话历史浏览器验证。",
}

WEEKLY_PLAN = {
    day: {"type": "rest", "exercises": []}
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
}

SESSIONS = [
    {
        "id": 2,
        "title": "腿日复盘",
        "createdAt": "2026-06-01T08:00:00Z",
        "updatedAt": "2026-06-01T10:00:00Z",
    },
    {
        "id": 1,
        "title": "默认对话",
        "createdAt": "2026-06-01T07:00:00Z",
        "updatedAt": "2026-06-01T09:00:00Z",
    },
]

MESSAGES = {
    1: [
        {
            "id": 101,
            "sessionId": 1,
            "role": "user",
            "content": "默认会话的问题",
            "suggestion": None,
            "createdAt": "2026-06-01T09:00:00Z",
        },
        {
            "id": 102,
            "sessionId": 1,
            "role": "assistant",
            "content": "默认会话的回答",
            "suggestion": None,
            "createdAt": "2026-06-01T09:01:00Z",
        },
    ],
    2: [
        {
            "id": 201,
            "sessionId": 2,
            "role": "user",
            "content": "腿日复盘的问题",
            "suggestion": None,
            "createdAt": "2026-06-01T10:00:00Z",
        },
        {
            "id": 202,
            "sessionId": 2,
            "role": "assistant",
            "content": "腿日复盘的回答",
            "suggestion": None,
            "createdAt": "2026-06-01T10:01:00Z",
        },
    ],
    3: [],
}


def json_response(route, payload, status=200):
    route.fulfill(
        status=status,
        content_type="application/json",
        body=json.dumps(payload, ensure_ascii=False),
    )


def install_backend_mock(page, sessions, created_sessions):
    def handle_api(route):
        request = route.request
        path = urlparse(request.url).path.replace("/api", "", 1)
        method = request.method.upper()

        if method == "GET" and path == "/profile":
            return json_response(route, PROFILE)

        if method == "GET" and path == "/weekly-plan":
            return json_response(route, WEEKLY_PLAN)

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
                    "thinking": {"enabled": False, "budget": "auto", "options": ["off", "auto", "max"]},
                },
            )

        if method == "GET" and path == "/chat/sessions":
            return json_response(route, sessions)

        if method == "POST" and path == "/chat/sessions":
            created = {
                "id": 3,
                "title": "新对话",
                "createdAt": "2026-06-01T11:00:00Z",
                "updatedAt": "2026-06-01T11:00:00Z",
            }
            created_sessions.append(created)
            if not any(item["id"] == created["id"] for item in sessions):
                sessions.insert(0, created)
            return json_response(route, created)

        if method == "GET" and path.startswith("/chat/sessions/") and path.endswith("/messages"):
            session_id = int(path.split("/")[3])
            return json_response(route, MESSAGES.get(session_id, []))

        if path.startswith("/chat/sessions/") and path.endswith("/draft"):
            return json_response(
                route,
                {
                    "content": "",
                    "model": "deepseek-v4-flash",
                    "thinking": {"enabled": False, "budget": "auto"},
                    "attachedFileIds": [],
                },
            )

        if method in {"PUT", "POST"}:
            return json_response(route, {"ok": True})

        return json_response(route, {"ok": True})

    page.route("http://127.0.0.1:8000/api/**", handle_api)


def session_switch_button(page, title):
    # 仅匹配会话卡片里可见的标题文本，避免误命中带同名 aria-label 的删除按钮。
    return page.get_by_role("button").filter(has_text=title)


def main():
    sessions = [dict(item) for item in SESSIONS]
    created_sessions = []

    with ensure_vite_dev_server(APP_URL) as app_url:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()
            install_backend_mock(page, sessions, created_sessions)

            page.goto(app_url)
            page.get_by_role("button", name="AI 教练").click()

            expect(session_switch_button(page, "腿日复盘")).to_be_visible(timeout=10_000)
            expect(session_switch_button(page, "默认对话")).to_be_visible(timeout=10_000)
            expect(page.get_by_text("腿日复盘的问题")).to_be_visible(timeout=10_000)
            expect(page.get_by_text("腿日复盘的回答")).to_be_visible(timeout=10_000)

            session_switch_button(page, "默认对话").click()
            expect(page.get_by_text("默认会话的问题")).to_be_visible(timeout=10_000)
            expect(page.get_by_text("腿日复盘的问题")).not_to_be_visible(timeout=10_000)

            page.get_by_role("button", name="新建对话").click()
            expect(session_switch_button(page, "新对话")).to_be_visible(timeout=10_000)
            expect(session_switch_button(page, "腿日复盘")).to_be_visible(timeout=10_000)
            expect(session_switch_button(page, "默认对话")).to_be_visible(timeout=10_000)
            expect(page.get_by_text("默认会话的问题")).not_to_be_visible(timeout=10_000)

            assert created_sessions == [
                {
                    "id": 3,
                    "title": "新对话",
                    "createdAt": "2026-06-01T11:00:00Z",
                    "updatedAt": "2026-06-01T11:00:00Z",
                }
            ]

            browser.close()


if __name__ == "__main__":
    main()
