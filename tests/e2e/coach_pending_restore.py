import json
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright


APP_URL = "http://127.0.0.1:5173"
USER_MESSAGE = "请继续分析我刚发出的训练调整问题"


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
    "notes": "用于 pending 恢复验证。",
}

WEEKLY_PLAN = {
    day: {"type": "rest", "exercises": []}
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
}

STORED_TASK = {
    "taskId": "pending-task",
    "sessionId": 1,
    "sourceUserIndex": 2,
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


def install_backend_mock(page):
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
                    "models": [{"id": "deepseek-v4-flash", "label": "DeepSeek V4 Flash"}],
                    "thinking": {"enabled": False, "budget": "auto", "options": ["off", "auto", "max"]},
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
            # 模拟后台任务尚未落库当前 user 消息，前端必须从 task 记录恢复等待态锚点。
            return json_response(
                route,
                [
                    {
                        "id": 1,
                        "sessionId": 1,
                        "role": "user",
                        "content": "上一轮问题",
                        "suggestion": None,
                        "createdAt": "2026-06-01T00:00:00Z",
                    },
                    {
                        "id": 2,
                        "sessionId": 1,
                        "role": "assistant",
                        "content": "上一轮回答",
                        "suggestion": None,
                        "createdAt": "2026-06-01T00:01:00Z",
                    },
                ],
            )
        if path == "/chat/sessions/1/draft":
            return json_response(
                route,
                {
                    "content": "",
                    "model": "deepseek-v4-flash",
                    "thinking": {"enabled": False, "budget": "auto"},
                    "attachedFileIds": [],
                },
            )
        if method == "GET" and path == "/chat/background/pending-task":
            return json_response(route, {"task_id": "pending-task", "status": "pending"})

        return json_response(route, {"ok": True})

    page.route("http://127.0.0.1:8000/api/**", handle_api)


def seed_local_storage(context):
    context.add_init_script(
        f"""
        window.localStorage.setItem('fitloop:coach-active-session-id', '1');
        window.localStorage.setItem('fitloop:coach-background-task', JSON.stringify({json.dumps(STORED_TASK, ensure_ascii=False)}));
        window.localStorage.setItem('fitloop_storageVersion', JSON.stringify('v2-empty-defaults'));
        """
    )


def main():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        seed_local_storage(context)
        page = context.new_page()
        install_backend_mock(page)

        page.goto(APP_URL)
        page.get_by_role("button", name="AI 教练").click()

        expect(page.get_by_text(USER_MESSAGE)).to_be_visible(timeout=10_000)
        expect(page.get_by_text("正在整理上下文...")).to_be_visible(timeout=10_000)
        browser.close()


if __name__ == "__main__":
    main()
