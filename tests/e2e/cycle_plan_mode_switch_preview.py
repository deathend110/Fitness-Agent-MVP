from __future__ import annotations

import json

from playwright.sync_api import expect, sync_playwright

from coach_e2e_helpers import APP_URL, ensure_vite_dev_server


PROFILE = {
    "basic": {
        "name": "周期验证用户",
        "sex": "male",
        "age": 28,
        "height": 178,
        "weight": 80,
        "waist": 82,
    },
    "oneRM": {
        "squat": 180,
        "bench": 120,
        "deadlift": 220,
    },
    "goal": "力量提升",
    "targetWeight": None,
    "notes": "验证手动计划与周期计划切换展示。",
}
MANUAL_EXERCISE_NAME = "Manual Squat"
CYCLE_EXERCISE_NAME = "Back Squat"
MANUAL_WEEKLY_PLAN = {
    day: {"type": "rest", "exercises": []}
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
}
MANUAL_WEEKLY_PLAN["Monday"] = {
    "type": "manual_strength",
    "exercises": [
        {
            "id": "manual-squat",
            "name": MANUAL_EXERCISE_NAME,
            "template": {
                "loadMode": "percentage",
                "ref1RM": "squat",
                "setType": "straight",
                "sets": 3,
                "repsText": "5",
            },
            "instance": {"pct": 0.72, "kg": None, "rpe": 8, "note": "manual baseline"},
            "ref1RM": "squat",
            "pct": 0.72,
            "kg": None,
            "sets": 3,
            "reps": 5,
            "rpe": 8,
            "note": "manual baseline",
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
            "name": CYCLE_EXERCISE_NAME,
            "template": {
                "loadMode": "percentage",
                "ref1RM": "squat",
                "setType": "straight",
                "sets": 6,
                "repsText": "4",
            },
            "instance": {"pct": 0.8, "kg": None, "rpe": None, "note": ""},
            "ref1RM": "squat",
            "pct": 0.8,
            "kg": None,
            "sets": 6,
            "reps": 4,
            "rpe": None,
            "note": "",
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


def install_cycle_plan_mock(context) -> None:
    context.add_init_script(
        """
        (() => {
          const profile = %s
          const manualWeeklyPlan = %s
          const cycleEffectivePlan = %s
          const cycleDetail = {
            cycle: {
              id: 101,
              presetKey: 'candito_6week',
              presetLabel: 'Candito 6 Week Strength',
              status: 'active',
              startDate: '2026-06-01',
              currentWeekIndex: 1,
              pendingWeekIndex: null,
              goal: '力量提升',
              baseLifts: {
                squat: { oneRm: 180, tm: 162 },
                bench: { oneRm: 120, tm: 108 },
                deadlift: { oneRm: 220, tm: 198 },
              },
              config: { trainingDays: ['Monday', 'Wednesday', 'Friday', 'Saturday'] },
            },
            currentWeek: {
              cycleId: 101,
              weekIndex: 1,
              generatedPlan: cycleEffectivePlan,
              overridePlan: null,
              effectivePlan: cycleEffectivePlan,
              isConfirmed: true,
              weekStart: '2026-06-01',
              weekEnd: '2026-06-07',
            },
            effectivePlan: cycleEffectivePlan,
          }

          const state = {
            profile,
            manualWeeklyPlan,
            cycleEffectivePlan,
            activeSource: 'manual',
            activeCyclePlan: null,
          }

          window.__cyclePlanMockState = state
          const nativeFetch = window.fetch.bind(window)

          function jsonResponse(payload, status = 200) {
            return new Response(JSON.stringify(payload), {
              status,
              headers: { 'Content-Type': 'application/json' },
            })
          }

          function clone(value) {
            return JSON.parse(JSON.stringify(value))
          }

          function requestPath(input) {
            const url = typeof input === 'string' ? input : input?.url || ''
            return new URL(url, window.location.origin).pathname
          }

          window.fetch = async (input, init = {}) => {
            const path = requestPath(input)
            const method = (init.method || 'GET').toUpperCase()

            if (!path.startsWith('/api/')) {
              return nativeFetch(input, init)
            }

            if (method === 'GET' && path === '/api/profile') {
              return jsonResponse(profile)
            }
            if (method === 'GET' && path === '/api/weekly-plan') {
              return jsonResponse(clone(state.manualWeeklyPlan))
            }
            if (method === 'GET' && path === '/api/plan-source') {
              return jsonResponse({ activeSource: state.activeSource, updatedAt: '2026-06-04T10:00:00Z' })
            }
            if (method === 'PUT' && path === '/api/plan-source') {
              const payload = JSON.parse(init.body || '{}')
              state.activeSource = payload.activeSource === 'cycle' ? 'cycle' : 'manual'
              return jsonResponse({ activeSource: state.activeSource, updatedAt: '2026-06-04T10:00:00Z' })
            }
            if (method === 'GET' && path === '/api/cycles/active') {
              return jsonResponse(state.activeCyclePlan ? clone(state.activeCyclePlan) : null)
            }
            if (method === 'GET' && path === '/api/cycles/presets') {
              return jsonResponse([
                { key: 'candito_6week', label: 'Candito 6 Week Strength', summary: '6 周力量模板', supportedWeeks: [1,2,3,4,5,6], supportsTm: true, repeatMode: 'fixed_length' }
              ])
            }
            if (method === 'GET' && path === '/api/daily-log') {
              return jsonResponse({})
            }
            if (method === 'POST' && path === '/api/cycles') {
              state.activeSource = 'cycle'
              state.activeCyclePlan = clone(cycleDetail)
              return jsonResponse(clone(cycleDetail))
            }
            if (method === 'POST' && path === '/api/cycles/101/stop') {
              state.activeSource = 'manual'
              state.activeCyclePlan = {
                ...clone(cycleDetail),
                cycle: { ...clone(cycleDetail.cycle), status: 'completed' },
              }
              return jsonResponse(clone(state.activeCyclePlan))
            }

            return jsonResponse({ detail: 'Not Found' }, 404)
          }
        })()
        """
        % (
            json.dumps({**PROFILE, "oneRm": PROFILE["oneRM"]}, ensure_ascii=False),
            json.dumps(MANUAL_WEEKLY_PLAN, ensure_ascii=False),
            json.dumps(CYCLE_EFFECTIVE_PLAN, ensure_ascii=False),
        )
    )


def open_plan_tab(page) -> None:
    page.get_by_role("button", name="训练计划").click()
    expect(page.get_by_role("heading", name="本周训练计划")).to_be_visible(timeout=10_000)


def open_plan_settings(page) -> None:
    settings_button = page.get_by_role("button", name="计划设置")
    panel = page.get_by_text("计划设置入口")
    if panel.count() > 0 and panel.first.is_visible():
        return
    settings_button.click()
    expect(panel).to_be_visible(timeout=10_000)


def main() -> None:
    with ensure_vite_dev_server(APP_URL) as app_url:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 960})
            seed_local_storage(context)
            install_cycle_plan_mock(context)
            page = context.new_page()

            page.goto(app_url, wait_until="networkidle")
            open_plan_tab(page)
            expect(page.get_by_text(MANUAL_EXERCISE_NAME)).to_be_visible(timeout=10_000)
            expect(page.get_by_text(CYCLE_EXERCISE_NAME)).not_to_be_visible(timeout=1_000)

            open_plan_settings(page)
            page.get_by_role("button", name="周期计划", exact=True).click()
            page.locator("input[type='date']").first.fill("2026-06-01")
            page.get_by_role("button", name="Monday").click()
            page.get_by_role("button", name="Wednesday").click()
            page.get_by_role("button", name="Friday").click()
            page.get_by_role("button", name="创建周期计划").click()

            expect(page.get_by_text("周期计划已创建。")).to_be_visible(timeout=10_000)
            expect(page.get_by_text(CYCLE_EXERCISE_NAME)).to_be_visible(timeout=10_000)
            expect(page.get_by_text(MANUAL_EXERCISE_NAME)).not_to_be_visible(timeout=1_000)

            open_plan_settings(page)
            page.get_by_role("button", name="非周期计划", exact=True).click()
            page.get_by_role("button", name="切换为非周期计划").click()

            expect(page.get_by_text("当前来源：非周期计划")).to_be_visible(timeout=10_000)
            expect(page.get_by_text(MANUAL_EXERCISE_NAME)).to_be_visible(timeout=10_000)
            expect(page.get_by_text(CYCLE_EXERCISE_NAME)).not_to_be_visible(timeout=1_000)

            state = page.evaluate("() => window.__cyclePlanMockState")
            assert state["manualWeeklyPlan"]["Monday"]["exercises"][0]["name"] == MANUAL_EXERCISE_NAME
            assert state["activeSource"] == "manual"

            browser.close()


if __name__ == "__main__":
    main()
