import test from 'node:test'
import assert from 'node:assert/strict'

import {
  demoDailyLog,
  demoProfile,
  demoWeeklyPlan,
} from '../src/utils/defaultData.js'
import { buildSystemPrompt } from '../src/utils/prompt.js'
import { buildMetricsSection } from '../src/utils/promptMetricsSection.js'

test('buildMetricsSection 可独立构建复杂指标段，且 buildSystemPrompt 继续复用同一输出', () => {
  const metricsSection = buildMetricsSection(demoProfile, demoWeeklyPlan, demoDailyLog)
  const prompt = buildSystemPrompt(demoProfile, demoWeeklyPlan, demoDailyLog)

  assert.match(metricsSection, /今日 TDEE 估算/)
  assert.match(metricsSection, /structured_metrics=/)
  assert.match(metricsSection, /"calorie_delta_kcal":\s*-195/)
  assert.match(metricsSection, /"calorie_status":\s*"deficit"/)
  assert.match(metricsSection, /"protein_status":\s*"met"/)
  assert.match(metricsSection, /"sleep_hours":\s*6\.8/)
  assert.ok(prompt.includes(metricsSection))
})
