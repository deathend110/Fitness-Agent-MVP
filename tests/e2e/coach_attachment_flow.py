import json
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import expect, sync_playwright


APP_URL = "http://127.0.0.1:5173"
FIRST_MESSAGE = "请结合我上传的训练记录，看看明天需不需要降负荷。"
SECOND_MESSAGE = "如果不带附件，只根据今天情况再总结一句。"
ATTACHMENT_NAME = "coach-upload-note.txt"
ATTACHMENT_CONTENT = "周一深蹲 5x5 @ 125kg，主观疲劳 8，睡眠不足。"

BACKEND_PROFILE = {
    "basic": {
        "name": "附件流程用户",
        "sex": "male",
        "age": 29,
        "height": 175,
        "weight": 78,
        "waist": 80,
    },
    "oneRm": {"squat": 155, "bench": 95, "deadlift": 185},
    "goal": "力量提升",
    "targetWeight": 79,
    "notes": "用于附件上传与 fileIds 语义验证。",
}

LOCAL_PROFILE = {
    **BACKEND_PROFILE,
    "oneRM": BACKEND_PROFILE["oneRm"],
}

WEEKLY_PLAN = {
    day: {"type": "rest", "exercises": []}
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
}

FIRST_REPLY = {
    "text": "我读到了你上传的训练记录，明天建议先小幅降负荷并优先补觉。",
    "suggestion": None,
    "proposal": None,
}

SECOND_REPLY = {
    "text": "不带附件时，我会只基于当前日志给出保守建议。",
    "suggestion": None,
    "proposal": None,
}


def json_response(route, payload, status=200):
    route.fulfill(
        status=status,
        content_type="application/json",
        body=json.dumps(payload, ensure_ascii=False),
    )


def install_backend_mock(page, upload_calls, reply_calls):
    draft_state = {"attachedFileIds": []}
    message_state = {"messages": []}
    reply_queue = [FIRST_REPLY, SECOND_REPLY]
    upload_id_state = {"next": 701}

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
                    "createdAt": "2026-06-03T10:00:00Z",
                    "updatedAt": "2026-06-03T10:00:00Z",
                },
            )

        if method == "GET" and path == "/chat/sessions":
            return json_response(
                route,
                [
                    {
                        "id": 1,
                        "title": "默认对话",
                        "createdAt": "2026-06-03T10:00:00Z",
                        "updatedAt": "2026-06-03T10:00:00Z",
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
                        "attachedFileIds": draft_state["attachedFileIds"],
                    },
                )
            if method == "PUT":
                body = request.post_data_json
                draft_state["attachedFileIds"] = body.get("attachedFileIds", [])
                return json_response(route, {"ok": True})

        if method == "POST" and path == "/files/upload":
            query = parse_qs(parsed.query)
            upload_calls.append(
                {
                    "query": {key: values[-1] for key, values in query.items()},
                    "headers": request.headers,
                }
            )
            uploaded_file_id = upload_id_state["next"]
            upload_id_state["next"] += 1
            uploaded_file = {
                "id": uploaded_file_id,
                "originalName": ATTACHMENT_NAME,
                "name": ATTACHMENT_NAME,
                "mimeType": "text/plain",
                "extension": ".txt",
                "sizeBytes": len(ATTACHMENT_CONTENT.encode("utf-8")),
            }
            draft_state["attachedFileIds"] = [uploaded_file["id"]]
            return json_response(route, {"file": uploaded_file})

        if method == "GET" and path == "/chat/stream":
            route.fulfill(status=500, content_type="application/json", body=json.dumps({"message": "force fallback"}))
            return

        if method == "POST" and path == "/chat/reply":
            payload = request.post_data_json
            reply_calls.append(payload)
            reply = reply_queue.pop(0)
            attachments = [
                {
                    "fileId": file_id,
                    "originalName": ATTACHMENT_NAME,
                    "mimeType": "text/plain",
                    "extension": ".txt",
                    "sizeBytes": len(ATTACHMENT_CONTENT.encode("utf-8")),
                }
                for file_id in payload.get("fileIds", [])
            ]
            next_user_id = len(message_state["messages"]) + 1
            message_state["messages"].append(
                {
                    "id": next_user_id,
                    "sessionId": 1,
                    "role": "user",
                    "content": payload.get("userInput", ""),
                    "suggestion": None,
                    "attachments": attachments,
                    "createdAt": "2026-06-03T10:01:00Z",
                }
            )
            message_state["messages"].append(
                {
                    "id": next_user_id + 1,
                    "sessionId": 1,
                    "role": "assistant",
                    "content": reply["text"],
                    "suggestion": None,
                    "attachments": [],
                    "createdAt": "2026-06-03T10:01:10Z",
                }
            )
            draft_state["attachedFileIds"] = []
            return json_response(route, reply)

        return json_response(route, {"ok": True})

    page.route("http://127.0.0.1:8000/api/**", handle_api)


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


def create_upload_file():
    temp_dir = tempfile.mkdtemp(prefix="coach-attachment-flow-")
    upload_path = Path(temp_dir) / ATTACHMENT_NAME
    upload_path.write_text(ATTACHMENT_CONTENT, encoding="utf-8")
    return upload_path


def main():
    upload_calls = []
    reply_calls = []
    upload_path = create_upload_file()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        seed_local_storage(context)
        page = context.new_page()
        install_backend_mock(page, upload_calls, reply_calls)

        page.goto(APP_URL)
        page.get_by_role("button", name="AI 教练").click()

        file_input = page.locator('input[type="file"]')
        file_input.set_input_files(str(upload_path))
        expect(page.get_by_text(ATTACHMENT_NAME)).to_be_visible(timeout=10_000)

        composer = page.get_by_placeholder("Ask RepMind...")
        composer.fill(FIRST_MESSAGE)
        page.get_by_role("button", name="发送消息").click()

        expect(page.get_by_text(FIRST_MESSAGE).last).to_be_visible(timeout=10_000)
        expect(page.get_by_text(ATTACHMENT_NAME).last).to_be_visible(timeout=10_000)
        expect(page.get_by_text(FIRST_REPLY["text"])).to_be_visible(timeout=10_000)

        file_input.set_input_files(str(upload_path))
        remove_button = page.get_by_role("button", name="移除附件")
        expect(remove_button).to_be_visible(timeout=10_000)
        remove_button.click()
        expect(remove_button).not_to_be_visible(timeout=5_000)

        composer.fill(SECOND_MESSAGE)
        page.get_by_role("button", name="发送消息").click()

        expect(page.get_by_text(SECOND_MESSAGE).last).to_be_visible(timeout=10_000)
        expect(page.get_by_text(SECOND_REPLY["text"])).to_be_visible(timeout=10_000)

        assert len(upload_calls) == 2, upload_calls
        assert upload_calls[0]["query"] == {"sessionId": "1"}, upload_calls
        assert upload_calls[1]["query"] == {"sessionId": "1"}, upload_calls
        assert len(reply_calls) == 2, reply_calls
        assert reply_calls[0]["userInput"] == FIRST_MESSAGE, reply_calls
        assert reply_calls[0]["fileIds"] == [701], reply_calls
        assert reply_calls[1]["userInput"] == SECOND_MESSAGE, reply_calls
        assert reply_calls[1].get("fileIds", []) == [], reply_calls

        browser.close()


if __name__ == "__main__":
    main()
