import test from 'node:test'
import assert from 'node:assert/strict'

import { buildDailyMetricsSummary } from '../src/utils/calc.js'
import { buildDailyMetricsPanelModel } from '../src/utils/dailyMetricsPanel.js'
import { buildSystemPrompt } from '../src/utils/prompt.js'

function extractStructuredMetrics(promptText) {
  const matched = promptText.match(/structured_metrics=(\{[\s\S]*\})/)
  assert.ok(matched, 'prompt 中应包含 structured_metrics JSON')

  return JSON.parse(matched[1])
}

test('Task 6.4 固定样本下 Today 展示与 prompt 注入使用同一份复杂指标口径', () => {
  const referenceDate = {
    todayKey: 'Monday',
    todayStr: '2026-05-25',
  }
  const profile = {
    basic: {
      name: '测试用户',
      sex: 'male',
      age: 29,
      height: 175,
      weight: 70,
    },
    oneRM: {
      squat: 140,
      bench: 100,
      deadlift: 180,
    },
    goal: '增肌',
  }
  const weeklyPlan = {
    Sunday: { type: 'rest', exercises: [] },
    Monday: {
      type: 'strength',
      exercises: [
        {
          id: 'squat',
          name: 'Back Squat',
          ref1RM: 'squat',
          pct: 0.8,
          sets: 5,
          reps: 5,
        },
        {
          id: 'bench',
          name: 'Bench Press',
          ref1RM: 'bench',
          pct: 0.7,
          sets: 4,
          reps: 6,
        },
      ],
    },
    Tuesday: { type: 'rest', exercises: [] },
    Wednesday: { type: 'rest', exercises: [] },
    Thursday: { type: 'rest', exercises: [] },
    Friday: { type: 'rest', exercises: [] },
    Saturday: { type: 'rest', exercises: [] },
  }
  const dailyLog = {
    '2026-05-25': {
      kcal: 2500,
      protein: 105,
      sleep: 7.2,
      fatigue: 3,
      trainingDone: true,
      trainingNotes: '状态稳定',
    },
  }

  const summary = buildDailyMetricsSummary(profile, weeklyPlan, dailyLog, referenceDate)
  const panelModel = buildDailyMetricsPanelModel(profile, weeklyPlan, dailyLog, referenceDate)
  const promptText = buildSystemPrompt(profile, weeklyPlan, dailyLog, referenceDate)
  const structuredMetrics = extractStructuredMetrics(promptText)

  assert.equal(summary.todayKey, 'Monday')
  assert.equal(summary.todayStr, '2026-05-25')
  assert.equal(summary.tdee, 2433)
  assert.equal(summary.calorie.status, 'balanced')
  assert.equal(summary.protein.status, 'low')
  assert.deepEqual(summary.recovery, {
    sleepHours: 7.2,
    fatigueLevel: 3,
  })

  assert.equal(panelModel.source.summary.tdee, summary.tdee)
  assert.equal(panelModel.metrics.tdee.value, '2433 kcal')
  assert.equal(panelModel.metrics.calorieStatus.value, '热量基本持平')
  assert.equal(panelModel.metrics.protein.value, '105 g / 1.5 g/kg')
  assert.equal(panelModel.metrics.proteinStatus.value, '低于建议下限')
  assert.equal(panelModel.metrics.recovery.value, '睡眠 7.2 h / 疲劳 3 / 5')

  assert.deepEqual(structuredMetrics, {
    date: '2026-05-25',
    today_plan_type: 'strength',
    is_training_day: true,
    bmr_kcal: 1654,
    training_kcal: 448,
    tdee_kcal: 2433,
    bmi: 22.9,
    calorie_intake_kcal: 2500,
    calorie_delta_kcal: 67,
    calorie_status: 'balanced',
    protein_intake_g: 105,
    protein_g_per_kg: 1.5,
    protein_status: 'low',
    sleep_hours: 7.2,
    fatigue_level: 3,
  })
})
