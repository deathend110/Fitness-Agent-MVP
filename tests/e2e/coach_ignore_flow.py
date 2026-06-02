import json
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright


APP_URL = "http://127.0.0.1:5173"
FOLLOW_UP_MESSAGE = "那我今晚还需要补点碳水吗？"

BACKEND_PROFILE = {
    "basic": {
        "name": "忽略流程用户",
        "sex": "female",
        "age": 25,
        "height": 168,
        "weight": 60,
        "waist": 70,
    },
    "oneRm": {"squat": 95, "bench": 55, "deadlift": 120},
    "goal": "减脂保肌",
    "targetWeight": 58,
    "notes": "用于忽略 proposal 深度验证。",
}

LOCAL_PROFILE = {
    **BACKEND_PROFILE,
    "oneRM": BACKEND_PROFILE["oneRm"],
}

WEEKLY_PLAN = {
    day: {"type": "rest", "exercises": []}
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
}

INITIAL_MESSAGES = [
    {
        "id": 1,
        "sessionId": 1,
        "role": "user",
        "content": "今天训练后疲劳很高，要不要调一下周五计划？",
        "suggestion": None,
        "attachments": [],
        "createdAt": "2026-06-03T09:00:00Z",
    },
    {
        "id": 2,
        "sessionId": 1,
        "role": "assistant",
        "content": "建议暂时把周五从推日改成恢复上肢日。",
        "suggestion": {
            "proposalId": "proposal-ignore-flow",
            "kind": "day_plan_replace",
            "day": "Friday",
            "summary": "把周五改成恢复上肢日，减少推举总量。",
            "dayPlan": {
                "type": "恢复上肢日",
                "exercises": [
                    {
                        "id": "friday-bench-light",
                        "name": "卧推",
                        "tier": "main",
                        "ref1RM": "bench",
                        "pct": 0.65,
                        "kg": None,
                        "sets": 3,
                        "reps": 6,
                        "rpe": 7,
                        "note": "恢复优先",
                    }
                ],
            },
        },
        "attachments": [],
        "createdAt": "2026-06-03T09:01:00Z",
    },
]

FOLLOW_UP_REPLY = {
    "text": "可以适量补一点碳水，重点放在训练后主餐，别再增加额外训练量。",
    "suggestion": None,
    "proposal": None,
}


def json_response(route, payload, status=200):
    route.fulfill(
        status=status,
        content_type="application/json",
        body=json.dumps(payload, ensure_ascii=False),
    )


def install_backend_mock(page, ignore_calls, reply_calls):
    message_state = {"messages": [dict(item) for item in INITIAL_MESSAGES]}

    def handle_api(route):
        request = route.request
        path = urlparse(request.url).path.replace("/api", "", 1)
        method = request.method.upper()

        if method == "GET" and path == "/profile":
            return json_response(route, BACKEND_PROFILE)

        if method == "GET" and path == "/weekly-plan":
            return json_response(route, WEEKLY_PLAN)

        if method == "GET" and path == "/daily-log":
            return json_response(route, {})

        if method == "GET" and path == "/models":
            return json_response(
                route,
                {
                    "defaultModel": "deepseek-v4-flash",
                    "defaultModelRef": "deepseek-v4-flash",
                    "models": [
                        {
                            "id": "deepseek-v4-flash",
                            "label": "DeepSeek V4 Flash",
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
            )

        if method == "GET" and path == "/chat/sessions/default":
            return json_response(
                route,
                {
                    "id": 1,
                    "title": "默认对话",
                    "createdAt": "2026-06-03T09:00:00Z",
                    "updatedAt": "2026-06-03T09:01:00Z",
                },
            )

        if method == "GET" and path == "/chat/sessions":
            return json_response(
                route,
                [
                    {
                        "id": 1,
                        "title": "默认对话",
                        "createdAt": "2026-06-03T09:00:00Z",
                        "updatedAt": "2026-06-03T09:01:00Z",
                    }
                ],
            )

        if method == "GET" and path == "/chat/sessions/1/messages":
            return json_response(route, message_state["messages"])

        if path == "/chat/sessions/1/draft":
            if method == "GET":
                return json_response(
                    route,
                    {
                        "content": "",
                        "model": "deepseek-v4-flash",
                        "thinking": {"enabled": False, "budget": "standard"},
                        "attachedFileIds": [],
                    },
                )
            if method == "PUT":
                return json_response(route, {"ok": True})

        if method == "GET" and path == "/chat/stream":
            route.fulfill(status=500, content_type="application/json", body=json.dumps({"message": "force fallback"}))
            return

        if method == "POST" and path == "/chat/reply":
            payload = request.post_data_json
            reply_calls.append(payload)
            next_user_id = len(message_state["messages"]) + 1
            message_state["messages"].append(
                {
                    "id": next_user_id,
                    "sessionId": 1,
                    "role": "user",
                    "content": payload.get("userInput", ""),
                    "suggestion": None,
                    "attachments": [],
                    "createdAt": "2026-06-03T09:02:00Z",
                }
            )
            message_state["messages"].append(
                {
                    "id": next_user_id + 1,
                    "sessionId": 1,
                    "role": "assistant",
                    "content": FOLLOW_UP_REPLY["text"],
                    "suggestion": None,
                    "attachments": [],
                    "createdAt": "2026-06-03T09:02:10Z",
                }
            )
            return json_response(route, FOLLOW_UP_REPLY)

        if method == "POST" and path == "/tools/plan/ignore":
            ignore_calls.append(request.post_data_json)
            return json_response(route, {"ok": True, "message": "已忽略"})

        if method == "POST" and path == "/tools/plan/commit":
            return json_response(route, {"ok": True, "plan": WEEKLY_PLAN})

        return json_response(route, {"ok": True})

    page.route("http://127.0.0.1:8000/api/**", handle_api)


def seed_local_storage(context):
    seed_payload = json.dumps(
        {
            "profile": LOCAL_PROFILE,
            "weeklyPlan": WEEKLY_PLAN,
            "chatHistory": [
                {
                    "role": message["role"],
                    "content": message["content"],
                    "suggestion": message.get("suggestion"),
                    "attachments": message.get("attachments", []),
                }
                for message in INITIAL_MESSAGES
            ],
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
        """
    )


def main():
    ignore_calls = []
    reply_calls = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        seed_local_storage(context)
        page = context.new_page()
        install_backend_mock(page, ignore_calls, reply_calls)

        page.goto(APP_URL)
        page.get_by_role("button", name="AI 教练").click()

        expect(page.get_by_text("把周五改成恢复上肢日，减少推举总量。")).to_be_visible(timeout=10_000)
        expect(page.get_by_role("button", name="忽略")).to_be_visible(timeout=10_000)

        page.get_by_role("button", name="忽略").click()
        expect(page.get_by_role("button", name="忽略")).not_to_be_visible(timeout=5_000)
        expect(page.get_by_role("button", name="采纳并更新计划")).not_to_be_visible(timeout=5_000)
        expect(page.get_by_text("把周五改成恢复上肢日，减少推举总量。")).not_to_be_visible(timeout=5_000)

        composer = page.get_by_placeholder("Ask RepMind...")
        composer.fill(FOLLOW_UP_MESSAGE)
        page.get_by_role("button", name="发送消息").click()

        expect(page.get_by_text(FOLLOW_UP_MESSAGE).last).to_be_visible(timeout=10_000)
        expect(page.get_by_text(FOLLOW_UP_REPLY["text"])).to_be_visible(timeout=10_000)
        expect(page.get_by_role("button", name="忽略")).not_to_be_visible(timeout=5_000)
        expect(page.get_by_text("把周五改成恢复上肢日，减少推举总量。")).not_to_be_visible(timeout=5_000)

        assert ignore_calls == [{"proposalId": "proposal-ignore-flow"}], ignore_calls
        assert len(reply_calls) == 1, reply_calls
        assert reply_calls[0]["userInput"] == FOLLOW_UP_MESSAGE, reply_calls
        assert reply_calls[0].get("fileIds", []) == [], reply_calls

        browser.close()


if __name__ == "__main__":
    main()
