import test from 'node:test'
import assert from 'node:assert/strict'
import {
  buildDailyMetricsSummary,
  calcTDEE,
  getTodayKey,
  getTodayStr,
} from '../src/utils/calc.js'

function buildWeeklyPlanForToday(todayKey, todayPlan) {
  return {
    Sunday: { type: 'rest', exercises: [] },
    Monday: { type: 'rest', exercises: [] },
    Tuesday: { type: 'rest', exercises: [] },
    Wednesday: { type: 'rest', exercises: [] },
    Thursday: { type: 'rest', exercises: [] },
    Friday: { type: 'rest', exercises: [] },
    Saturday: { type: 'rest', exercises: [] },
    [todayKey]: todayPlan,
  }
}

test('buildDailyMetricsSummary 会汇总训练日的本地可计算指标与状态标签', () => {
  const todayKey = getTodayKey()
  const todayStr = getTodayStr()
  const profile = {
    basic: {
      sex: 'male',
      age: 30,
      height: 180,
      weight: 80,
    },
    oneRM: {
      squat: 200,
    },
  }
  const weeklyPlan = buildWeeklyPlanForToday(todayKey, {
    type: 'strength',
    exercises: [
      {
        id: 'squat-top',
        name: 'Back Squat',
        ref1RM: 'squat',
        pct: 0.75,
        sets: 5,
        reps: 5,
      },
      {
        id: 'rdl',
        name: 'Romanian Deadlift',
        kg: 60,
        sets: 3,
        reps: 8,
      },
    ],
  })
  const dailyLog = {
    [todayStr]: {
      kcal: 2400,
      protein: 150,
      sleep: 7.5,
      steps: 9800,
      fatigue: 4,
      tdee: 2721,
    },
  }

  const summary = buildDailyMetricsSummary(profile, weeklyPlan, dailyLog)

  assert.equal(summary.todayKey, todayKey)
  assert.equal(summary.todayStr, todayStr)
  assert.equal(summary.isTrainingDay, true)
  assert.equal(summary.bmr, 1780)
  assert.equal(summary.bmi, 24.7)
  assert.equal(summary.trainingKcal, 519)
  assert.equal(summary.estimatedTdee, 2655)
  assert.equal(summary.tdee, 2721)
  assert.equal(summary.tdeeSource, 'manual')
  assert.deepEqual(summary.calorie, {
    intake: 2400,
    delta: -321,
    status: 'deficit',
  })
  assert.deepEqual(summary.protein, {
    intake: 150,
    gramsPerKg: 1.9,
    status: 'met',
  })
  assert.deepEqual(summary.recovery, {
    sleepHours: 7.5,
    fatigueLevel: 4,
  })
  assert.equal(summary.activity.steps, 9800)
})

test('buildDailyMetricsSummary 在缺失日志或身高时返回稳定的空值与 unknown 标签', () => {
  const todayKey = getTodayKey()
  const profile = {
    basic: {
      sex: 'female',
      age: 28,
      height: null,
      weight: 60,
    },
    oneRM: {},
  }
  const weeklyPlan = buildWeeklyPlanForToday(todayKey, {
    type: 'rest',
    exercises: [],
  })

  const summary = buildDailyMetricsSummary(profile, weeklyPlan, {})

  assert.equal(summary.isTrainingDay, false)
  assert.equal(summary.bmr, 299)
  assert.equal(summary.bmi, null)
  assert.equal(summary.trainingKcal, 0)
  assert.equal(summary.estimatedTdee, 359)
  assert.equal(summary.tdee, 359)
  assert.equal(summary.tdeeSource, 'estimated')
  assert.deepEqual(summary.calorie, {
    intake: null,
    delta: null,
    status: 'unknown',
  })
  assert.deepEqual(summary.protein, {
    intake: null,
    gramsPerKg: null,
    status: 'unknown',
  })
  assert.deepEqual(summary.recovery, {
    sleepHours: null,
    fatigueLevel: null,
  })
  assert.equal(summary.activity.steps, null)
})

test('calcTDEE 会继续返回兼容旧调用方的核心字段', () => {
  const todayKey = getTodayKey()
  const todayStr = getTodayStr()
  const profile = {
    basic: { sex: 'male', age: 30, height: 180, weight: 80 },
    oneRM: {},
  }
  const weeklyPlan = buildWeeklyPlanForToday(todayKey, {
    type: 'rest',
    exercises: [],
  })
  const dailyLog = {
    [todayStr]: { kcal: 2200 },
  }

  const summary = calcTDEE(profile, weeklyPlan, dailyLog)

  assert.equal(summary.todayKey, todayKey)
  assert.equal(summary.todayStr, todayStr)
  assert.equal(summary.bmr, 1780)
  assert.equal(summary.trainingKcal, 0)
  assert.equal(summary.estimatedTdee, 2136)
  assert.equal(summary.tdee, 2136)
  assert.equal(summary.todayKcal, 2200)
  assert.equal(summary.delta, 64)
})
