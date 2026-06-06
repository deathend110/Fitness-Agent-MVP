import json

from playwright.sync_api import expect, sync_playwright

from coach_e2e_helpers import APP_URL, ensure_vite_dev_server, install_coach_backend_fetch_mock


PERSISTED_STATE_KEY = "fitloop:e2e:profile-input-fuzz:mock-state"

BACKEND_PROFILE = {
    "basic": {
        "name": "档案压测用户",
        "sex": "male",
        "age": 30,
        "height": 178,
        "weight": 82.5,
        "waist": 84,
    },
    "oneRm": {"squat": 170, "bench": 112, "deadlift": 205},
    "goal": "增肌",
    "targetWeight": 85,
    "notes": "用于档案页非法输入扰动验证。",
}

LOCAL_PROFILE = {**BACKEND_PROFILE, "oneRM": BACKEND_PROFILE["oneRm"]}
WEEKLY_PLAN = {
    day: {"type": "rest", "exercises": []}
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
}


def seed_local_storage(context) -> None:
    context.add_init_script(
        """
        window.localStorage.setItem('fitloop_profile', JSON.stringify(%s));
        window.localStorage.setItem('fitloop_weeklyPlan', JSON.stringify(%s));
        window.localStorage.setItem('fitloop_dailyLog', JSON.stringify({}));
        window.localStorage.setItem('fitloop_chatHistory', JSON.stringify([]));
        window.localStorage.setItem('fitloop_storageVersion', JSON.stringify('v2-empty-defaults'));
        """
        % (
            json.dumps(LOCAL_PROFILE, ensure_ascii=False),
            json.dumps(WEEKLY_PLAN, ensure_ascii=False),
        )
    )


def build_mock_config() -> dict:
    return {
        "profile": BACKEND_PROFILE,
        "weeklyPlan": WEEKLY_PLAN,
        "dailyLog": {},
        "models": {"defaultModel": "", "defaultModelRef": "", "models": []},
        "defaultSession": {
            "id": 1,
            "title": "默认对话",
            "createdAt": "2026-06-06T00:00:00Z",
            "updatedAt": "2026-06-06T00:00:00Z",
        },
        "sessions": [
            {
                "id": 1,
                "title": "默认对话",
                "createdAt": "2026-06-06T00:00:00Z",
                "updatedAt": "2026-06-06T00:00:00Z",
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


def main() -> None:
    with ensure_vite_dev_server(APP_URL) as app_url:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 960})
            seed_local_storage(context)
            install_coach_backend_fetch_mock(
                context,
                build_mock_config(),
                persisted_state_key=PERSISTED_STATE_KEY,
            )
            page = context.new_page()

            page.goto(app_url)
            page.get_by_role("button", name="我的档案").click()

            weight_input = page.get_by_label("当前体重 (kg)")
            initial_weight = weight_input.input_value()
            invalid_values = ["9999", "-3", "1e4"]
            for invalid_value in invalid_values:
                weight_input.fill(invalid_value)
                page.wait_for_timeout(150)
                assert weight_input.input_value() in {initial_weight, ""}, weight_input.input_value()

            weight_input.fill("82.5")
            expect(weight_input).to_have_value("82.5", timeout=10_000)

            target_weight_input = page.get_by_label("目标体重 (kg)")
            target_weight_input.fill("500")
            page.wait_for_timeout(150)
            assert target_weight_input.input_value() in {"85", ""}, target_weight_input.input_value()
            target_weight_input.fill("84.3")
            expect(target_weight_input).to_have_value("84.3", timeout=10_000)

            page.wait_for_function(
                """
                () => {
                  const payload = JSON.parse(window.localStorage.getItem('fitloop_profile') || '{}');
                  return payload?.basic?.weight === 82.5 && payload?.targetWeight === 84.3;
                }
                """
            )

            page.reload()
            page.get_by_role("button", name="我的档案").click()
            expect(page.get_by_label("当前体重 (kg)")).to_have_value("82.5", timeout=10_000)
            expect(page.get_by_label("目标体重 (kg)")).to_have_value("84.3", timeout=10_000)

            browser.close()


if __name__ == "__main__":
    main()
