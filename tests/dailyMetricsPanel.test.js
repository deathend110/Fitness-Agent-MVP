import test from 'node:test'
import assert from 'node:assert/strict'
import {
  buildDailyMetricsPanelModel,
  getMetricToneClassNames,
} from '../src/utils/dailyMetricsPanel.js'
import { getTodayKey, getTodayStr } from '../src/utils/calc.js'

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

test('buildDailyMetricsPanelModel 会基于统一 summary 生成训练日展示数据', () => {
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
    },
  }

  const panelModel = buildDailyMetricsPanelModel(profile, weeklyPlan, dailyLog)

  assert.equal(panelModel.header.date, todayStr)
  assert.equal(panelModel.header.trainingTag, '训练日')
  assert.equal(panelModel.header.planTypeLabel, 'strength')
  assert.equal(panelModel.metrics.bmr.value, '1780 kcal')
  assert.equal(panelModel.metrics.trainingKcal.value, '519 kcal')
  assert.equal(panelModel.metrics.tdee.value, '2655 kcal')
  assert.equal(panelModel.metrics.steps.value, '9800 步')
  assert.equal(panelModel.metrics.bmi.value, '24.7')
  assert.equal(panelModel.metrics.calorie.value, '2400 kcal')
  assert.equal(panelModel.metrics.calorieStatus.value, '热量缺口')
  assert.equal(panelModel.metrics.calorieStatus.tone, 'warning')
  assert.equal(panelModel.metrics.protein.value, '150 g / 1.9 g/kg')
  assert.equal(panelModel.metrics.proteinStatus.value, '已达到建议下限')
  assert.equal(panelModel.metrics.recovery.value, '睡眠 7.5 h / 疲劳 4 / 5')
  assert.equal(panelModel.aiEntry.title, '去 AI 教练获取辅助判断')
  assert.match(panelModel.aiEntry.description, /同一份本地复杂指标/)
})

test('buildDailyMetricsPanelModel 在缺失日志时返回稳定兜底文案', () => {
  const todayKey = getTodayKey()
  const todayStr = getTodayStr()
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

  const panelModel = buildDailyMetricsPanelModel(profile, weeklyPlan, {})

  assert.equal(panelModel.header.date, todayStr)
  assert.equal(panelModel.header.trainingTag, '休息日')
  assert.equal(panelModel.header.planTypeLabel, '休息日')
  assert.equal(panelModel.metrics.bmr.value, '299 kcal')
  assert.equal(panelModel.metrics.trainingKcal.value, '0 kcal')
  assert.equal(panelModel.metrics.tdee.value, '359 kcal')
  assert.equal(panelModel.metrics.steps.value, '未记录')
  assert.equal(panelModel.metrics.bmi.value, '未记录')
  assert.equal(panelModel.metrics.calorie.value, '未记录')
  assert.equal(panelModel.metrics.calorieStatus.value, '热量未知')
  assert.equal(panelModel.metrics.calorieStatus.tone, 'neutral')
  assert.equal(panelModel.metrics.protein.value, '未记录')
  assert.equal(panelModel.metrics.proteinStatus.value, '蛋白质未知')
  assert.equal(panelModel.metrics.recovery.value, '睡眠 未记录 / 疲劳 未记录')
  assert.equal(panelModel.source.summary.todayStr, todayStr)
  assert.equal(panelModel.source.summary.calorie.status, 'unknown')
})

test('buildDailyMetricsPanelModel 会把计划类型和状态色整理成可直接展示的中文与样式 token', () => {
  const todayKey = getTodayKey()
  const emptyTypePlan = buildWeeklyPlanForToday(todayKey, {
    type: '',
    exercises: [],
  })

  const panelModel = buildDailyMetricsPanelModel({}, emptyTypePlan, {})
  const warningTone = getMetricToneClassNames('warning')
  const neutralTone = getMetricToneClassNames()

  assert.equal(panelModel.header.planTypeLabel, '未设置')
  assert.notEqual(warningTone.labelClassName, 'text-slate-400')
  assert.notEqual(warningTone.valueClassName, 'text-slate-100')
  assert.equal(neutralTone.labelClassName, 'text-slate-400')
  assert.equal(neutralTone.valueClassName, 'text-slate-100')
})
