import test from 'node:test'
import assert from 'node:assert/strict'

import {
  demoDailyLog,
  demoProfile,
  demoWeeklyPlan,
} from '../src/utils/defaultData.js'
import { buildDailyMetricsSummary } from '../src/utils/dailyMetrics.js'
import { buildSystemPrompt } from '../src/utils/prompt.js'

test('buildSystemPrompt 会把档案、计划、日志与结构化指标注入到 prompt 文本', () => {
  const referenceDate = {
    todayStr: Object.keys(demoDailyLog).sort().at(-1),
  }
  const summary = buildDailyMetricsSummary(
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

  assert.match(prompt, /基本信息/)
  assert.match(prompt, /三大项 1RM/)
  assert.match(prompt, /本周训练计划/)
  assert.match(prompt, /近 14 天体重记录/)
  assert.match(prompt, /近 7 天饮食摘要/)
  assert.match(prompt, /近 7 天训练完成情况/)
  assert.match(prompt, /今日 TDEE 估算/)
  assert.match(prompt, /BMI/)
  assert.match(prompt, /热量状态/)
  assert.match(prompt, /蛋白质按体重/)
  assert.match(prompt, /蛋白质状态/)
  assert.match(prompt, /恢复数据/)
  assert.match(prompt, /structured_metrics/)
  assert.match(prompt, /小林/)
  assert.match(prompt, /深蹲/)
  assert.match(prompt, /深蹲第三组没有按计划完成/)
  assert.match(prompt, /当日 TDEE：\d+kcal/)
  assert.match(prompt, /"bmi":\s*25\.9/)
  assert.match(
    prompt,
    new RegExp(`"calorie_delta_kcal":\\s*${summary.calorie.delta}`),
  )
  assert.match(
    prompt,
    new RegExp(`"calorie_status":\\s*"${summary.calorie.status}"`),
  )
  assert.match(prompt, /"protein_g_per_kg":\s*2/)
  assert.match(prompt, /"protein_status":\s*"met"/)
  assert.match(prompt, /"sleep_hours":\s*6\.8/)
  assert.match(prompt, /"fatigue_level":\s*4/)
})

test('buildSystemPrompt 在新用户空日志场景下返回兜底文案且保留结构化空值', () => {
  const prompt = buildSystemPrompt(
    {
      basic: {},
      oneRM: {},
      goal: '',
      targetWeight: null,
      notes: '',
    },
    {},
    {},
  )

  assert.match(prompt, /暂无记录/)
  assert.match(prompt, /未记录/)
  assert.match(prompt, /姓名：未记录/)
  assert.match(prompt, /当日 TDEE：\d+kcal/)
  assert.match(prompt, /"bmi": null/)
  assert.match(prompt, /"calorie_status":\s*"unknown"/)
  assert.match(prompt, /"protein_g_per_kg": null/)
  assert.match(prompt, /"protein_status":\s*"unknown"/)
  assert.match(prompt, /"sleep_hours": null/)
  assert.match(prompt, /"fatigue_level": null/)
})

test('buildSystemPrompt 在休息日会把训练消耗写成 0 且保留固定 kg 动作信息', () => {
  const referenceDate = {
    todayStr: '2026-05-25',
  }
  const weeklyPlan = {
    Sunday: { type: 'rest', exercises: [] },
    Monday: { type: 'rest', exercises: [] },
    Tuesday: { type: 'rest', exercises: [] },
    Wednesday: { type: 'rest', exercises: [] },
    Thursday: { type: 'rest', exercises: [] },
    Friday: { type: 'rest', exercises: [] },
    Saturday: { type: 'rest', exercises: [] },
    Tuesday: {
      type: '有氧',
      exercises: [
        {
          id: 'bike',
          name: '骑车',
          ref1RM: null,
          pct: null,
          kg: 20,
          sets: 1,
          reps: 30,
          rpe: null,
          note: '固定阻力',
        },
      ],
    },
  }

  const prompt = buildSystemPrompt(demoProfile, weeklyPlan, {}, referenceDate)

  assert.match(prompt, /骑车 20kg x 1组 x 30次/)
  assert.match(prompt, /训练容量估算消耗：0kcal/)
})
