import test from 'node:test'
import assert from 'node:assert/strict'
import {
  demoDailyLog,
  demoProfile,
  demoWeeklyPlan,
} from '../src/utils/defaultData.js'
import { getTodayKey } from '../src/utils/calc.js'
import { buildSystemPrompt } from '../src/utils/prompt.js'

test('buildSystemPrompt 会把档案、计划、日志与 TDEE 注入到 prompt 文本', () => {
  const prompt = buildSystemPrompt(demoProfile, demoWeeklyPlan, demoDailyLog)

  assert.match(prompt, /基本信息/)
  assert.match(prompt, /三大项 1RM/)
  assert.match(prompt, /本周训练计划/)
  assert.match(prompt, /近 14 天体重记录/)
  assert.match(prompt, /近 7 天饮食摘要/)
  assert.match(prompt, /近 7 天训练完成情况/)
  assert.match(prompt, /今日 TDEE 估算/)
  assert.match(prompt, /小林/)
  assert.match(prompt, /深蹲/)
  assert.match(prompt, /深蹲第.*组.*完成/)
  assert.match(prompt, /当日 TDEE：\d+kcal/)
})

test('buildSystemPrompt 在新用户空日志场景下返回兜底文案且不报错', () => {
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
})

test('buildSystemPrompt 在休息日会把训练消耗写成 0 且保留固定 kg 动作信息', () => {
  const todayKey = getTodayKey()
  const exerciseDay = todayKey === 'Monday' ? 'Tuesday' : 'Monday'
  const weeklyPlan = {
    Sunday: { type: 'rest', exercises: [] },
    Monday: { type: 'rest', exercises: [] },
    Tuesday: { type: 'rest', exercises: [] },
    Wednesday: { type: 'rest', exercises: [] },
    Thursday: { type: 'rest', exercises: [] },
    Friday: { type: 'rest', exercises: [] },
    Saturday: { type: 'rest', exercises: [] },
    [exerciseDay]: {
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

  const prompt = buildSystemPrompt(demoProfile, weeklyPlan, {})

  assert.match(prompt, /骑车 20kg x 1组 x 30次/)
  assert.match(prompt, /训练容量估算消耗：0kcal/)
})
