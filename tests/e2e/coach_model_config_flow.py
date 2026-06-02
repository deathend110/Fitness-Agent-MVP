import json
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import expect, sync_playwright


APP_URL = "http://127.0.0.1:5173"

DEFAULT_MODEL = "provider_deepseek_main::deepseek-v4-flash"
DISCOVERED_DEFAULT_MODEL = "provider_deepseek_main::deepseek-v4-pro"
GEMINI_MODEL = "provider_gemini_main::gemini-2.5-flash"
USER_MESSAGE = "保存配置后请用新的默认模型继续回复"
REPLY_TEXT = "新默认模型已生效：后续优先使用 V4 Pro。"

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
    "notes": "用于模型配置弹窗浏览器验证。",
}

BACKEND_PROFILE = {
    **LOCAL_PROFILE,
    "oneRm": LOCAL_PROFILE["oneRM"],
}

WEEKLY_PLAN = {
    day: {"type": "rest", "exercises": []}
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
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


def build_runtime_models(config_payload, included_refs=None):
    models = []
    for provider in config_payload.get("providers", []):
        provider_type = provider.get("type", "openai_compatible")
        for model in provider.get("selectedModels", []):
            model_ref = f'{provider["id"]}::{model["remoteId"]}'
            if included_refs is not None and model_ref not in included_refs:
                continue
            models.append(
                {
                    "id": model_ref,
                    "providerId": provider["id"],
                    "providerType": provider_type,
                    "providerLabel": provider["label"],
                    "remoteModelId": model["remoteId"],
                    "label": f'{provider["label"]} / {model["label"]}',
                    "supportsThinking": provider_type == "openai_compatible",
                    "thinking": {
                        "supported": provider_type == "openai_compatible",
                        "canDisable": True,
                        "defaultEnabled": False,
                        "intensityOptions": [{"id": "standard", "label": "标准"}],
                        "defaultIntensity": "standard",
                    }
                    if provider_type == "openai_compatible"
                    else None,
                }
            )

    return {
        "defaultModel": config_payload["defaultModelRef"],
        "defaultModelRef": config_payload["defaultModelRef"],
        "models": models,
        "thinking": {"enabled": False, "budget": "standard", "options": ["off", "standard"]},
    }


def install_backend_mock(page, test_calls, discover_calls, save_calls, stream_calls):
    config_state = {
        "version": 1,
        "defaultModelRef": DEFAULT_MODEL,
        "providers": [
            {
                "id": "provider_deepseek_main",
                "type": "openai_compatible",
                "label": "DeepSeek 主账号",
                "enabled": True,
                "apiKeyPreview": "sk-d***1234",
                "baseUrl": "https://api.deepseek.com/v1",
                "wireApi": "chat_completions",
                "apiPathMode": "append_v1",
                "selectedModels": [
                    {
                        "remoteId": "deepseek-v4-flash",
                        "label": "DeepSeek V4 Flash",
                        "enabled": True,
                    }
                ],
            },
            {
                "id": "provider_gemini_main",
                "type": "gemini_native",
                "label": "Gemini 主账号",
                "enabled": True,
                "apiKeyPreview": "AIza***1234",
                "baseUrl": "https://generativelanguage.googleapis.com/v1beta",
                "selectedModels": [
                    {
                        "remoteId": "gemini-2.5-flash",
                        "label": "Gemini 2.5 Flash",
                        "enabled": True,
                    }
                ],
            },
        ],
    }
    runtime_state = build_runtime_models(config_state)

    def handle_api(route):
        nonlocal config_state, runtime_state

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
            return json_response(route, runtime_state)

        if method == "GET" and path == "/model-config":
            return json_response(route, config_state)

        if method == "POST" and path == "/model-config/providers/test":
            payload = read_request_json(request)
            test_calls.append(payload)
            return json_response(route, {"ok": True, "modelCount": 2})

        if method == "POST" and path == "/model-config/providers/discover-models":
            payload = read_request_json(request)
            discover_calls.append(payload)
            return json_response(
                route,
                {
                    "models": [
                        {
                            "remoteId": "deepseek-v4-flash",
                            "label": "DeepSeek V4 Flash",
                            "enabled": True,
                        },
                        {
                            "remoteId": "deepseek-v4-pro",
                            "label": "DeepSeek V4 Pro",
                            "enabled": True,
                        },
                    ]
                },
            )

        if method == "PUT" and path == "/model-config":
            payload = read_request_json(request)
            save_calls.append(payload)
            config_state = {
                "version": payload["version"],
                "defaultModelRef": payload["defaultModelRef"],
                "providers": [
                    {
                        **provider,
                        "apiKeyPreview": provider.get("apiKeyPreview", ""),
                    }
                    for provider in payload["providers"]
                ],
            }
            runtime_state = build_runtime_models(
                payload, included_refs={payload["defaultModelRef"], GEMINI_MODEL}
            )
            return json_response(route, config_state)

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
                return json_response(
                    route,
                    {
                        "content": "",
                        "model": runtime_state["defaultModelRef"],
                        "thinking": {"enabled": False, "budget": "standard"},
                        "attachedFileIds": [],
                    },
                )
            if method == "PUT":
                return json_response(route, {"ok": True})

        if method == "GET" and path == "/chat/stream":
            stream_calls.append(request.url)
            return stream_response(route, REPLY_TEXT)

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


def wait_until_coach_ready(page):
    expect(page.locator("#coach-model-select")).to_have_value(DEFAULT_MODEL, timeout=10_000)
    expect(page.locator("textarea")).to_be_visible(timeout=10_000)
    expect(
        page.get_by_text("请先完善档案中的姓名、当前体重、训练目标和深蹲 1RM，再使用 AI 教练。")
    ).not_to_be_visible(timeout=10_000)


def main():
    test_calls = []
    discover_calls = []
    save_calls = []
    stream_calls = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        seed_local_storage(context)
        page = context.new_page()
        install_backend_mock(page, test_calls, discover_calls, save_calls, stream_calls)

        page.goto(APP_URL)
        page.get_by_role("button", name="AI 教练").click()
        wait_until_coach_ready(page)

        page.get_by_role("button", name="模型设置").click()
        dialog = page.get_by_text("模型与供应商设置")
        expect(dialog).to_be_visible(timeout=10_000)

        page.get_by_label("展示名称").nth(0).fill("DeepSeek 实验账号")
        page.get_by_label("Base URL").nth(0).fill("https://api.deepseek.com/v1")
        page.get_by_label("接口协议").nth(0).select_option("responses")
        page.get_by_label("Base URL 拼接模式").nth(0).select_option("append_v1")
        page.get_by_label("API Key").nth(0).fill("sk-new-deepseek")

        page.get_by_role("button", name="测试连接").nth(0).click()
        expect(page.get_by_text("连接成功，发现 2 个模型。")).to_be_visible(timeout=10_000)

        page.get_by_role("button", name="发现模型").nth(0).click()
        expect(page.get_by_text("已同步 2 个远端模型，可按需关闭不想展示的项。")).to_be_visible(
            timeout=10_000
        )

        page.get_by_label("默认模型").select_option(DISCOVERED_DEFAULT_MODEL)
        page.get_by_role("button", name="保存配置").click()

        expect(page.get_by_text("模型与供应商设置")).not_to_be_visible(timeout=10_000)
        expect(page.locator("#coach-model-select")).to_have_value(DISCOVERED_DEFAULT_MODEL)
        expect(page.locator("header")).to_contain_text("DeepSeek 实验账号 / DeepSeek V4 Pro")

        page.locator("textarea").fill(USER_MESSAGE)
        page.get_by_role("button", name="发送消息").click()
        expect(page.get_by_text(REPLY_TEXT, exact=True)).to_be_visible(timeout=10_000)

        assert len(test_calls) == 1, test_calls
        assert test_calls[0] == {
            "id": "provider_deepseek_main",
            "type": "openai_compatible",
            "label": "DeepSeek 实验账号",
            "enabled": True,
            "baseUrl": "https://api.deepseek.com/v1",
            "selectedModels": [
                {
                    "remoteId": "deepseek-v4-flash",
                    "label": "DeepSeek V4 Flash",
                    "enabled": True,
                }
            ],
            "wireApi": "responses",
            "apiPathMode": "append_v1",
            "apiKey": "sk-new-deepseek",
        }, test_calls

        assert len(discover_calls) == 1, discover_calls
        assert discover_calls[0] == test_calls[0], discover_calls

        assert len(save_calls) == 1, save_calls
        assert save_calls[0] == {
            "version": 1,
            "defaultModelRef": DISCOVERED_DEFAULT_MODEL,
            "providers": [
                {
                    "id": "provider_deepseek_main",
                    "type": "openai_compatible",
                    "label": "DeepSeek 实验账号",
                    "enabled": True,
                    "baseUrl": "https://api.deepseek.com/v1",
                    "selectedModels": [
                        {
                            "remoteId": "deepseek-v4-flash",
                            "label": "DeepSeek V4 Flash",
                            "enabled": True,
                        },
                        {
                            "remoteId": "deepseek-v4-pro",
                            "label": "DeepSeek V4 Pro",
                            "enabled": True,
                        },
                    ],
                    "wireApi": "responses",
                    "apiPathMode": "append_v1",
                    "apiKey": "sk-new-deepseek",
                },
                {
                    "id": "provider_gemini_main",
                    "type": "gemini_native",
                    "label": "Gemini 主账号",
                    "enabled": True,
                    "baseUrl": "https://generativelanguage.googleapis.com/v1beta",
                    "selectedModels": [
                        {
                            "remoteId": "gemini-2.5-flash",
                            "label": "Gemini 2.5 Flash",
                            "enabled": True,
                        }
                    ],
                },
            ],
        }, save_calls

        assert len(stream_calls) == 1, stream_calls
        stream_query = parse_qs(urlparse(stream_calls[0]).query)
        assert stream_query["model"] == [DISCOVERED_DEFAULT_MODEL], stream_query
        assert stream_query["userInput"] == [USER_MESSAGE], stream_query

        browser.close()


if __name__ == "__main__":
    main()
