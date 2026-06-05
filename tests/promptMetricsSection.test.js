import test from 'node:test'
import assert from 'node:assert/strict'

import {
  demoDailyLog,
  demoProfile,
  demoWeeklyPlan,
} from '../src/utils/defaultData.js'
import { buildDailyMetricsSummary } from '../src/utils/dailyMetrics.js'
import { buildSystemPrompt } from '../src/utils/prompt.js'
import { buildMetricsSection } from '../src/utils/promptMetricsSection.js'

test('buildMetricsSection 可独立构建复杂指标段，且 buildSystemPrompt 继续复用同一输出', () => {
  const referenceDate = {
    todayStr: Object.keys(demoDailyLog).sort().at(-1),
  }
  const summary = buildDailyMetricsSummary(
    demoProfile,
    demoWeeklyPlan,
    demoDailyLog,
    referenceDate,
  )
  const metricsSection = buildMetricsSection(
    demoProfile,
    demoWeeklyPlan,
    demoDailyLog,
    referenceDate,
  )
  const prompt = buildSystemPrompt(
    demoProfile,
    demoWeeklyPlan,
    demoDailyLog,
    referenceDate,
  )

  assert.match(metricsSection, /今日 TDEE 估算/)
  assert.match(metricsSection, /structured_metrics=/)
  assert.match(
    metricsSection,
    new RegExp(`"calorie_delta_kcal":\\s*${summary.calorie.delta}`),
  )
  assert.match(
    metricsSection,
    new RegExp(`"calorie_status":\\s*"${summary.calorie.status}"`),
  )
  assert.match(metricsSection, /"protein_status":\s*"met"/)
  assert.match(metricsSection, /"sleep_hours":\s*6\.8/)
  assert.ok(prompt.includes(metricsSection))
})
