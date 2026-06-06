import json

from playwright.sync_api import expect, sync_playwright

from coach_e2e_helpers import APP_URL, ensure_vite_dev_server


PERSISTED_STATE_KEY = "fitloop:e2e:plan-mutation-stress:mock-state"

PROFILE = {
    "basic": {
        "name": "计划压测用户",
        "sex": "male",
        "age": 29,
        "height": 181,
        "weight": 83,
        "waist": 85,
    },
    "oneRM": {"squat": 180, "bench": 118, "deadlift": 210},
    "goal": "力量提升",
    "targetWeight": 84,
    "notes": "用于训练计划编辑、删除、拖拽与来源切换压测。",
}
BACKEND_PROFILE = {**PROFILE, "oneRm": PROFILE["oneRM"]}
MANUAL_WEEKLY_PLAN = {
    day: {"type": "rest", "exercises": []}
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
}
MANUAL_WEEKLY_PLAN["Monday"] = {
    "type": "腿日",
    "exercises": [
        {
            "id": "manual-squat",
            "name": "Manual Squat",
            "ref1RM": "squat",
            "pct": 0.72,
            "kg": None,
            "sets": 3,
            "reps": 5,
            "rpe": 8,
            "note": "manual baseline",
        },
        {
            "id": "manual-rdl",
            "name": "Manual RDL",
            "ref1RM": None,
            "pct": None,
            "kg": 110,
            "sets": 3,
            "reps": 8,
            "rpe": 7,
            "note": "second slot",
        },
    ],
}
MANUAL_WEEKLY_PLAN["Wednesday"] = {
    "type": "推日",
    "exercises": [
        {
            "id": "wed-bench",
            "name": "Bench Press",
            "ref1RM": "bench",
            "pct": 0.75,
            "kg": None,
            "sets": 4,
            "reps": 5,
            "rpe": 8,
            "note": "bench baseline",
        }
    ],
}
CYCLE_EFFECTIVE_PLAN = {
    day: {"type": "rest", "exercises": []}
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
}
CYCLE_EFFECTIVE_PLAN["Monday"] = {
    "type": "lower_strength",
    "exercises": [
        {
            "id": "cycle-squat",
            "name": "Cycle Squat",
            "ref1RM": "squat",
            "pct": 0.8,
            "kg": None,
            "sets": 6,
            "reps": 4,
            "rpe": 8,
            "note": "cycle projected week",
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
            json.dumps(PROFILE, ensure_ascii=False),
            json.dumps(MANUAL_WEEKLY_PLAN, ensure_ascii=False),
        )
    )


def install_plan_stress_mock(context) -> None:
    context.add_init_script(
        """
        (() => {
          const persistedStateKey = %s;
          const nativeFetch = window.fetch.bind(window);
          const clone = (value) => JSON.parse(JSON.stringify(value));
          const storedText = window.localStorage.getItem(persistedStateKey);
          const state = storedText ? JSON.parse(storedText) : {
            profile: %s,
            weeklyPlan: %s,
            dailyLog: {},
            planSource: { activeSource: 'manual', updatedAt: '2026-06-06T00:00:00Z' },
            activeCyclePlan: {
              cycle: {
                id: 101,
                presetKey: 'candito_6week',
                presetLabel: 'Candito 6 Week Strength',
                status: 'active',
                startDate: '2026-06-01',
                currentWeekIndex: 1,
              },
              currentWeek: {
                cycleId: 101,
                weekIndex: 1,
                effectivePlan: %s,
              },
              effectivePlan: %s,
            },
            cyclePresets: [
              {
                key: 'candito_6week',
                label: 'Candito 6 Week Strength',
                summary: '6 周力量模板',
                supportedWeeks: [1, 2, 3, 4, 5, 6],
                supportsTm: true,
                repeatMode: 'fixed_length',
              }
            ],
            modelConfig: { version: 1, providers: [] },
          };

          function persist() {
            window.localStorage.setItem(persistedStateKey, JSON.stringify(state));
          }

          function jsonResponse(payload, status = 200) {
            return new Response(JSON.stringify(payload), {
              status,
              headers: { 'Content-Type': 'application/json' },
            });
          }

          function pathOf(input) {
            const url = typeof input === 'string' ? input : input?.url || '';
            return new URL(url, window.location.origin).pathname;
          }

          persist();
          window.__planStressMockState = state;

          window.fetch = async (input, init = {}) => {
            const path = pathOf(input);
            const method = (init.method || 'GET').toUpperCase();
            const body = typeof init.body === 'string' ? JSON.parse(init.body) : null;

            if (!path.startsWith('/api/')) {
              return nativeFetch(input, init);
            }

            if (method === 'GET' && path === '/api/profile') {
              return jsonResponse(clone(state.profile));
            }
            if (method === 'PUT' && path === '/api/profile') {
              state.profile = clone(body ?? state.profile);
              persist();
              return jsonResponse(clone(state.profile));
            }
            if (method === 'GET' && path === '/api/weekly-plan') {
              return jsonResponse(clone(state.weeklyPlan));
            }
            if (method === 'PUT' && path === '/api/weekly-plan') {
              state.weeklyPlan = clone(body ?? state.weeklyPlan);
              persist();
              return jsonResponse(clone(state.weeklyPlan));
            }
            if (method === 'GET' && path === '/api/plan-source') {
              return jsonResponse(clone(state.planSource));
            }
            if (method === 'PUT' && path === '/api/plan-source') {
              state.planSource = {
                activeSource: body?.activeSource === 'cycle' ? 'cycle' : 'manual',
                updatedAt: '2026-06-06T00:00:00Z',
              };
              persist();
              return jsonResponse(clone(state.planSource));
            }
            if (method === 'GET' && path === '/api/cycles/active') {
              return jsonResponse(clone(state.activeCyclePlan));
            }
            if (method === 'GET' && path === '/api/cycles/presets') {
              return jsonResponse(clone(state.cyclePresets));
            }
            if (method === 'GET' && path === '/api/daily-log') {
              return jsonResponse({});
            }
            if (method === 'PUT' && path === '/api/cycles/101/weeks/1/override') {
              state.activeCyclePlan.effectivePlan = clone(body);
              state.activeCyclePlan.currentWeek.effectivePlan = clone(body);
              persist();
              return jsonResponse({ effectivePlan: clone(body) });
            }

            return jsonResponse({ ok: true });
          };
        })();
        """
        % (
            json.dumps(PERSISTED_STATE_KEY, ensure_ascii=False),
            json.dumps(BACKEND_PROFILE, ensure_ascii=False),
            json.dumps(MANUAL_WEEKLY_PLAN, ensure_ascii=False),
            json.dumps(CYCLE_EFFECTIVE_PLAN, ensure_ascii=False),
            json.dumps(CYCLE_EFFECTIVE_PLAN, ensure_ascii=False),
        )
    )
def main() -> None:
    with ensure_vite_dev_server(APP_URL) as app_url:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 960})
            seed_local_storage(context)
            install_plan_stress_mock(context)
            page = context.new_page()

            page.goto(app_url)
            page.get_by_role("button", name="训练计划").click()
            monday_column = page.locator('[data-day-key="Monday"]')

            monday_cards = page.locator('[data-day-key="Monday"] [data-exercise-id]')
            expect(monday_cards).to_have_count(2, timeout=10_000)

            page.drag_and_drop(
                '[data-day-key="Monday"] [data-exercise-id="manual-rdl"]',
                '[data-day-key="Monday"] [data-exercise-id="manual-squat"]',
            )
            page.wait_for_function(
                """
                () => {
                  const ids = Array.from(
                    document.querySelectorAll('[data-day-key="Monday"] [data-exercise-id]')
                  ).map((node) => node.getAttribute('data-exercise-id'));
                  return ids.join(',') === 'manual-rdl,manual-squat';
                }
                """
            )

            monday_column.get_by_role("button", name="添加动作").click()
            page.get_by_label("动作名称").fill("Paused Bench")
            page.get_by_label("组数").fill("5")
            page.get_by_label("次数").fill("3")
            page.get_by_label("RPE").fill("8")
            page.get_by_role("button", name="保存新增动作").click()
            expect(page.locator('[data-day-key="Monday"] [data-exercise-id]')).to_have_count(
                3,
                timeout=10_000,
            )
            expect(page.get_by_text("Paused Bench", exact=True)).to_be_visible(timeout=10_000)

            page.locator('[data-day-key="Monday"] [data-exercise-id="manual-squat"] button[aria-label="更多操作"]').click()
            page.get_by_role("menuitem", name="删除动作").click()
            expect(page.locator('[data-day-key="Monday"] [data-exercise-id]')).to_have_count(
                2,
                timeout=10_000,
            )
            expect(
                page.locator('[data-day-key="Monday"] [data-exercise-id="manual-squat"]')
            ).to_have_count(0, timeout=10_000)

            settings_button = page.get_by_role("button", name="计划设置")
            settings_button.click()
            expect(page.get_by_text("计划设置入口")).to_be_visible(timeout=10_000)
            page.evaluate(
                """
                (persistedStateKey) => {
                  window.__planStressMockState.planSource = {
                    activeSource: 'cycle',
                    updatedAt: '2026-06-06T00:00:00Z',
                  };
                  window.localStorage.setItem(
                    persistedStateKey,
                    JSON.stringify(window.__planStressMockState),
                  );
                }
                """,
                PERSISTED_STATE_KEY,
            )
            page.reload()
            page.get_by_role("button", name="训练计划").click()
            expect(page.get_by_text("Cycle Squat", exact=True)).to_be_visible(timeout=10_000)

            settings_button = page.get_by_role("button", name="计划设置")
            settings_button.click()
            expect(page.get_by_text("计划设置入口")).to_be_visible(timeout=10_000)
            page.get_by_role("button", name="非周期计划", exact=True).click()
            switch_to_manual_button = page.get_by_role("button", name="切换为非周期计划")
            switch_to_manual_button.click()
            expect(page.get_by_text("当前来源：非周期计划")).to_be_visible(timeout=10_000)
            expect(switch_to_manual_button).to_be_disabled(timeout=10_000)
            expect(page.get_by_text("Paused Bench", exact=True)).to_be_visible(timeout=10_000)
            expect(page.get_by_text("Cycle Squat", exact=True)).not_to_be_visible(timeout=1_000)

            page.reload()
            page.get_by_role("button", name="训练计划").click()
            reloaded_cards = page.locator('[data-day-key="Monday"] [data-exercise-id]')
            expect(reloaded_cards).to_have_count(2, timeout=10_000)
            expect(reloaded_cards.nth(0)).to_contain_text("Manual RDL", timeout=10_000)
            expect(page.get_by_text("Paused Bench", exact=True)).to_be_visible(timeout=10_000)
            expect(
                page.locator('[data-day-key="Monday"] [data-exercise-id="manual-squat"]')
            ).to_have_count(0, timeout=10_000)

            state = page.evaluate("() => window.__planStressMockState")
            assert state["planSource"]["activeSource"] == "manual", state
            assert [item["name"] for item in state["weeklyPlan"]["Monday"]["exercises"]] == [
                "Manual RDL",
                "Paused Bench",
            ], state["weeklyPlan"]["Monday"]["exercises"]

            browser.close()


if __name__ == "__main__":
    main()
