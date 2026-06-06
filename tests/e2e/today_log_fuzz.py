import json

from playwright.sync_api import expect, sync_playwright

from coach_e2e_helpers import APP_URL, ensure_vite_dev_server, install_coach_backend_fetch_mock


PERSISTED_STATE_KEY = "fitloop:e2e:today-log-fuzz:mock-state"

BACKEND_PROFILE = {
    "basic": {
        "name": "今日日志压测用户",
        "sex": "female",
        "age": 27,
        "height": 168,
        "weight": 61.2,
        "waist": 73,
    },
    "oneRm": {"squat": 115, "bench": 65, "deadlift": 145},
    "goal": "减脂",
    "targetWeight": 58,
    "notes": "用于今日日志非法输入与恢复验证。",
}

LOCAL_PROFILE = {**BACKEND_PROFILE, "oneRM": BACKEND_PROFILE["oneRm"]}
WEEKLY_PLAN = {
    day: {"type": "rest", "exercises": []}
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
}
WEEKLY_PLAN["Saturday"] = {
    "type": "训练日",
    "exercises": [
        {
            "id": "sat-squat",
            "name": "深蹲",
            "ref1RM": "squat",
            "pct": 0.72,
            "kg": None,
            "sets": 4,
            "reps": 6,
            "rpe": 7.5,
            "note": "恢复正常推进",
        }
    ],
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


def install_daily_log_put_mock(context) -> None:
    context.add_init_script(
        """
        (() => {
          const previousFetch = window.fetch.bind(window);
          const persistedStateKey = %s;

          window.fetch = async (input, init = {}) => {
            const requestUrl = typeof input === 'string' ? input : input?.url || '';
            const path = new URL(requestUrl, window.location.origin).pathname;
            const method = (init.method || 'GET').toUpperCase();

            if (method === 'PUT' && /^\\/api\\/daily-log\\/\\d{4}-\\d{2}-\\d{2}$/.test(path)) {
              const date = path.split('/').pop();
              const payload = typeof init.body === 'string' ? JSON.parse(init.body) : {};
              window.__coachMockState.dailyLog = {
                ...(window.__coachMockState.dailyLog || {}),
                [date]: payload,
              };
              window.localStorage.setItem(
                persistedStateKey,
                JSON.stringify(window.__coachMockState),
              );

              return new Response(JSON.stringify(payload), {
                status: 200,
                headers: { 'Content-Type': 'application/json' },
              });
            }

            return previousFetch(input, init);
          };
        })();
        """
        % json.dumps(PERSISTED_STATE_KEY, ensure_ascii=False)
    )


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
            install_daily_log_put_mock(context)
            page = context.new_page()

            page.goto(app_url)
            page.get_by_role("button", name="今日日志").click()

            inputs = page.locator('form input[type="number"]')
            weight_input = inputs.nth(0)
            kcal_input = inputs.nth(1)
            sleep_input = inputs.nth(3)
            fatigue_input = inputs.nth(6)
            for invalid_value in ["-1", "99999", "1e5"]:
                kcal_input.fill(invalid_value)
                page.wait_for_timeout(150)
                assert kcal_input.input_value() in {"", "0"}, kcal_input.input_value()

            sleep_input.fill("48")
            page.wait_for_timeout(150)
            assert sleep_input.input_value() in {"", "0"}, sleep_input.input_value()

            fatigue_input.fill("0")
            page.wait_for_timeout(150)
            assert fatigue_input.input_value() in {"", "1"}, fatigue_input.input_value()

            kcal_input.fill("2300")
            sleep_input.fill("7.5")
            fatigue_input.fill("3")
            weight_input.fill("61.0")
            page.get_by_label("训练备注").fill("第一次保存，观察 reload 后恢复。")

            save_button = page.get_by_role("button", name="保存今日日志")
            save_button.click()
            expect(page.get_by_role("status")).to_have_text("今日日志已保存到本地。", timeout=10_000)

            page.get_by_label("训练备注").fill("第二次保存，确认重复提交不会破坏数据。")
            save_button.click()

            page.wait_for_function(
                """
                () => {
                  const todayKey = new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Shanghai' }).replaceAll('/', '-');
                  const payload = JSON.parse(window.localStorage.getItem('fitloop_dailyLog') || '{}');
                  return payload?.[todayKey]?.kcal === 2300
                    && payload?.[todayKey]?.sleep === 7.5
                    && payload?.[todayKey]?.fatigue === 3
                    && payload?.[todayKey]?.trainingNotes === '第二次保存，确认重复提交不会破坏数据。';
                }
                """
            )

            page.reload()
            page.get_by_role("button", name="今日日志").click()
            reloaded_inputs = page.locator('form input[type="number"]')
            expect(reloaded_inputs.nth(1)).to_have_value("2300", timeout=10_000)
            expect(reloaded_inputs.nth(3)).to_have_value("7.5", timeout=10_000)
            expect(reloaded_inputs.nth(6)).to_have_value("3", timeout=10_000)
            expect(page.get_by_label("训练备注")).to_have_value(
                "第二次保存，确认重复提交不会破坏数据。",
                timeout=10_000,
            )

            browser.close()


if __name__ == "__main__":
    main()
