import assert from 'node:assert/strict'
import test from 'node:test'

import {
  formatCountDisplay,
  formatDecimalDisplay,
  formatPercentDisplay,
  formatWeightDisplay,
} from '../src/utils/calc.js'
import { buildAdoptCardModel } from '../src/utils/adoptCard.js'
import { buildTodayPlanSummary } from '../src/utils/todayPlan.js'

test('formatDecimalDisplay 会把长小数压缩为更短的展示', () => {
  assert.equal(formatDecimalDisplay(97.25), '97.3')
  assert.equal(formatDecimalDisplay(7.0), '7')
})

test('formatWeightDisplay 会统一显示体重和训练重量', () => {
  assert.equal(formatWeightDisplay(97.25), '97.3kg')
  assert.equal(formatWeightDisplay(80), '80kg')
})

test('formatPercentDisplay 会把比例统一转成百分比展示', () => {
  assert.equal(formatPercentDisplay(0.75), '75%')
  assert.equal(formatPercentDisplay(0.7), '70%')
})

test('formatCountDisplay 会把组数和次数压成整数展示', () => {
  assert.equal(formatCountDisplay(4.8), '5')
  assert.equal(formatCountDisplay(6), '6')
})

test('buildAdoptCardModel 会用统一规则展示重量数值', () => {
  const card = buildAdoptCardModel({
    day: 'Monday',
    summary: '调整深蹲强度',
    changes: [
      {
        action: 'update',
        exerciseName: '深蹲',
        field: 'kg',
        oldValue: 97.25,
        newValue: 98.5,
      },
    ],
  })

  assert.equal(card.changes[0].beforeLabel, '97.3kg')
  assert.equal(card.changes[0].afterLabel, '98.5kg')
})

test('buildTodayPlanSummary 会用统一规则展示固定重量动作', () => {
  const summary = buildTodayPlanSummary(
    {
      type: '腿日',
      exercises: [
        {
          id: 'squat',
          name: '深蹲',
          ref1RM: null,
          pct: null,
          kg: 97.25,
          sets: 4,
          reps: 6,
          rpe: 7.25,
          note: '主项',
        },
      ],
    },
    {},
  )

  assert.equal(summary.exercises[0].detail, '97.3kg 路 4 组 x 6 次 路 RPE 7.3 路 主项')
})
