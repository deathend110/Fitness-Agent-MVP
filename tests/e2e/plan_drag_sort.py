import json
from contextlib import contextmanager
from types import SimpleNamespace

from playwright.sync_api import expect, sync_playwright

from coach_e2e_helpers import APP_URL, ensure_vite_dev_server, install_coach_backend_fetch_mock


PROFILE = {
    "basic": {
        "name": "拖拽验证用户",
        "sex": "male",
        "age": 28,
        "height": 180,
        "weight": 82,
        "waist": 84,
    },
    "oneRM": {"squat": 160, "bench": 105, "deadlift": 190},
    "goal": "增肌",
    "targetWeight": 84,
    "notes": "用于训练计划拖拽排序回归验证。",
}

BACKEND_PROFILE = {**PROFILE, "oneRm": PROFILE["oneRM"]}

WEEKLY_PLAN = {
    "Monday": {
        "type": "腿日",
        "exercises": [
            {
                "id": "monday-squat",
                "name": "深蹲",
                "ref1RM": "squat",
                "pct": 0.75,
                "kg": None,
                "sets": 4,
                "reps": 6,
                "rpe": None,
                "note": "主项",
            },
            {
                "id": "monday-rdl",
                "name": "罗马尼亚硬拉",
                "ref1RM": None,
                "pct": None,
                "kg": 80,
                "sets": 3,
                "reps": 10,
                "rpe": None,
                "note": "",
            },
        ],
    },
    "Tuesday": {"type": "rest", "exercises": []},
    "Wednesday": {"type": "rest", "exercises": []},
    "Thursday": {"type": "rest", "exercises": []},
    "Friday": {"type": "rest", "exercises": []},
    "Saturday": {"type": "rest", "exercises": []},
    "Sunday": {"type": "rest", "exercises": []},
}


def seed_local_storage(context):
    context.add_init_script(
        """
        window.localStorage.setItem('fitloop_profile', JSON.stringify(%s));
        window.localStorage.setItem('fitloop_weeklyPlan', JSON.stringify(%s));
        window.localStorage.setItem('fitloop_dailyLog', JSON.stringify({}));
        window.localStorage.setItem('fitloop_chatHistory', JSON.stringify([]));
        window.localStorage.setItem('fitloop_storageVersion', JSON.stringify('v2-empty-defaults'));
        """
        % (
            json.dumps(PROFILE, ensure_ascii=False),
            json.dumps(WEEKLY_PLAN, ensure_ascii=False),
        )
    )


def build_mock_config():
    return {
        "profile": BACKEND_PROFILE,
        "weeklyPlan": WEEKLY_PLAN,
        "dailyLog": {},
        "models": {"defaultModel": "", "defaultModelRef": "", "models": []},
        "defaultSession": {
            "id": 1,
            "title": "默认对话",
            "createdAt": "2026-06-04T08:00:00Z",
            "updatedAt": "2026-06-04T08:00:00Z",
        },
        "sessions": [
            {
                "id": 1,
                "title": "默认对话",
                "createdAt": "2026-06-04T08:00:00Z",
                "updatedAt": "2026-06-04T08:00:00Z",
            }
        ],
        "messagesBySession": {"1": []},
        "draftsBySession": {
            "1": {
                "content": "",
                "model": "",
                "thinking": {"enabled": False, "budget": "standard"},
                "attachedFileIds": [],
            }
        },
        "streamScenarios": [],
        "replyScenarios": [],
    }


@contextmanager
def run_app_with_mock_state():
    with ensure_vite_dev_server(APP_URL) as app_url:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 960})
            seed_local_storage(context)
            install_coach_backend_fetch_mock(context, build_mock_config())
            page = context.new_page()

            try:
                yield SimpleNamespace(browser=browser, context=context, page=page, url=app_url)
            finally:
                browser.close()


def test_plan_drag_sort_persists():
    with run_app_with_mock_state() as app:
        page = app.page
        page.goto(app.url)
        page.get_by_role("button", name="训练计划").click()

        monday_cards = page.locator('[data-day-key="Monday"] [data-exercise-id]')
        expect(monday_cards).to_have_count(2, timeout=10_000)
        before_first = monday_cards.nth(0).text_content()
        before_second = monday_cards.nth(1).text_content()

        page.drag_and_drop(
            '[data-day-key="Monday"] [data-exercise-id="monday-rdl"]',
            '[data-day-key="Monday"] [data-exercise-id="monday-squat"]',
        )

        expect(monday_cards.nth(0)).to_contain_text(before_second.strip(), timeout=10_000)
        after_first = monday_cards.nth(0).text_content()
        assert after_first == before_second
        page.wait_for_function(
            """
            () => window.__coachMockState.weeklyPlan?.Monday?.exercises?.[0]?.id === 'monday-rdl'
            """
        )

        page.reload()
        page.get_by_role("button", name="训练计划").click()
        expect(page.locator('[data-day-key="Monday"] [data-exercise-id]')).to_have_count(
            2,
            timeout=10_000,
        )
        reloaded_first = (
            page.locator('[data-day-key="Monday"] [data-exercise-id]').nth(0).text_content()
        )
        assert reloaded_first == before_second


def main():
    test_plan_drag_sort_persists()


if __name__ == "__main__":
    main()
