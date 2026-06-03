import json
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright


APP_URL = "http://127.0.0.1:5173"

DEEPSEEK_MODEL = "provider_deepseek_main::deepseek-v4-flash"
RESPONSES_MODEL = "provider_openai_responses::gpt-4.1-mini"
GEMINI_MODEL = "provider_gemini_main::gemini-2.5-flash"

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
    "notes": "用于模型切换浏览器验证。",
}

BACKEND_PROFILE = {
    **LOCAL_PROFILE,
    "oneRm": LOCAL_PROFILE["oneRM"],
}

WEEKLY_PLAN = {
    day: {"type": "rest", "exercises": []}
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
}

MODEL_REPLIES = {
    DEEPSEEK_MODEL: "DeepSeek 模型回复：周五维持当前强度。",
    RESPONSES_MODEL: "Responses 模型回复：周三卧推先减一组。",
    GEMINI_MODEL: "Gemini 模型回复：周日补充轻量恢复训练。",
}


def json_response(route, payload, status=200):
    route.fulfill(
        status=status,
        content_type="application/json",
        body=json.dumps(payload, ensure_ascii=False),
    )


def stream_response(route, text):
    route.fulfill(
        status=200,
        content_type="text/event-stream",
        body=f'event: done\ndata: {json.dumps({"text": text}, ensure_ascii=False)}\n\n',
    )


def read_request_json(request):
    payload = request.post_data_json
    return payload() if callable(payload) else payload


def wait_until_composer_ready(page):
    expect(page.locator("#coach-model-select")).to_have_value(DEEPSEEK_MODEL, timeout=10_000)
    expect(page.locator("textarea")).to_be_visible(timeout=10_000)
    expect(
        page.get_by_text("请先完善档案中的姓名、当前体重、训练目标和深蹲 1RM，再使用 AI 教练。")
    ).not_to_be_visible(timeout=10_000)


def install_backend_mock(page, draft_requests, stream_requests):
    draft_state = {
        "content": "",
        "model": DEEPSEEK_MODEL,
        "thinking": {"enabled": False, "budget": "standard"},
        "attachedFileIds": [],
    }

    def handle_api(route):
        request = route.request
        parsed = urlparse(request.url)
        path = parsed.path.replace("/api", "", 1)
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
                    "defaultModel": DEEPSEEK_MODEL,
                    "defaultModelRef": DEEPSEEK_MODEL,
                    "models": [
                        {
                            "id": DEEPSEEK_MODEL,
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
                        },
                        {
                            "id": RESPONSES_MODEL,
                            "providerId": "provider_openai_responses",
                            "providerType": "openai_compatible",
                            "providerLabel": "OpenAI Responses 实验账号",
                            "remoteModelId": "gpt-4.1-mini",
                            "label": "OpenAI Responses 实验账号 / GPT-4.1 Mini",
                            "supportsThinking": True,
                            "thinking": {
                                "supported": True,
                                "canDisable": True,
                                "defaultEnabled": False,
                                "intensityOptions": [{"id": "balanced", "label": "Balanced"}],
                                "defaultIntensity": "balanced",
                            },
                        },
                        {
                            "id": GEMINI_MODEL,
                            "providerId": "provider_gemini_main",
                            "providerType": "gemini_native",
                            "providerLabel": "Gemini 主账号",
                            "remoteModelId": "gemini-2.5-flash",
                            "label": "Gemini 主账号 / Gemini 2.5 Flash",
                            "supportsThinking": False,
                        },
                    ],
                    "thinking": {
                        "enabled": False,
                        "budget": "standard",
                        "options": ["off", "standard"],
                    },
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

        if method == "GET" and path == "/chat/sessions/1/messages":
            return json_response(route, [])

        if path == "/chat/sessions/1/draft":
            if method == "GET":
                return json_response(route, draft_state)
            if method == "PUT":
                payload = read_request_json(request)
                draft_requests.append(payload)
                draft_state.update(payload)
                return json_response(route, {"ok": True})

        if method == "POST" and path == "/chat/stream":
            payload = read_request_json(request)
            model = payload.get("model", "")
            user_input = payload.get("userInput", "")
            session_id = payload.get("sessionId", "")
            stream_requests.append(
                {
                    "model": model,
                    "userInput": user_input,
                    "session_id": session_id,
                }
            )
            return stream_response(route, MODEL_REPLIES[model])

        return json_response(route, {"ok": True})

    page.route("http://127.0.0.1:8000/api/**", handle_api)


def seed_local_storage(context):
    seed_payload = json.dumps(LOCAL_PROFILE, ensure_ascii=False)
    context.add_init_script(
        f"""
        const profile = {seed_payload};
        window.localStorage.setItem('fitloop_profile', JSON.stringify(profile));
        window.localStorage.setItem('fitloop_storageVersion', JSON.stringify('v2-empty-defaults'));
        """
    )


def send_message(page, text, expected_reply):
    page.get_by_role("button", name="发送消息").click()
    expect(page.get_by_text(expected_reply, exact=True)).to_be_visible(timeout=10_000)


def main():
    draft_requests = []
    stream_requests = []

    message_plan = [
        (RESPONSES_MODEL, "请用 Responses 模型继续帮我看卧推安排", MODEL_REPLIES[RESPONSES_MODEL]),
        (GEMINI_MODEL, "切到 Gemini 后继续给我恢复建议", MODEL_REPLIES[GEMINI_MODEL]),
        (DEEPSEEK_MODEL, "切回 DeepSeek 再确认一次周五训练", MODEL_REPLIES[DEEPSEEK_MODEL]),
    ]

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        seed_local_storage(context)
        page = context.new_page()
        install_backend_mock(page, draft_requests, stream_requests)

        page.goto(APP_URL)
        page.get_by_role("button", name="AI 教练").click()

        wait_until_composer_ready(page)
        model_select = page.locator("#coach-model-select")
        expect(model_select).to_have_value(DEEPSEEK_MODEL)

        for model_ref, user_text, expected_reply in message_plan:
            model_select.select_option(model_ref)
            expect(model_select).to_have_value(model_ref)
            page.locator("textarea").fill(user_text)

            send_message(page, user_text, expected_reply)

        assert [item["model"] for item in stream_requests] == [
            RESPONSES_MODEL,
            GEMINI_MODEL,
            DEEPSEEK_MODEL,
        ], stream_requests
        assert [item["userInput"] for item in stream_requests] == [
            item[1] for item in message_plan
        ], stream_requests

        for model_ref, user_text, _ in message_plan:
            matching_drafts = [
                payload
                for payload in draft_requests
                if payload.get("content") == user_text and payload.get("model") == model_ref
            ]
            if matching_drafts:
                assert matching_drafts[-1]["model"] == model_ref, matching_drafts

        browser.close()


if __name__ == "__main__":
    main()
