import assert from 'node:assert/strict'
import test from 'node:test'

import { defaultWeeklyPlan } from '../src/utils/defaultData.js'
import { adoptPlanChange } from '../src/utils/adoptPlan.js'

test('adoptPlanChange 会按 suggestion 的 day 和 changes 更新目标动作字段', () => {
  const result = adoptPlanChange(defaultWeeklyPlan, 'Monday', [
    {
      action: 'update',
      exerciseName: '深蹲',
      field: 'pct',
      newValue: 0.7,
    },
  ])

  assert.equal(result.ok, true)
  assert.equal(result.message, '已采纳 AI 建议，训练计划已更新。')
  assert.equal(result.nextPlan.Monday.exercises[0].pct, 0.7)
  assert.equal(result.nextPlan.Monday.exercises[1].kg, 80)
  assert.equal(defaultWeeklyPlan.Monday.exercises[0].pct, 0.75)
})

test('adoptPlanChange 在目标 day 不存在时返回失败结果', () => {
  const result = adoptPlanChange(defaultWeeklyPlan, 'Holiday', [
    {
      action: 'update',
      exerciseName: '深蹲',
      field: 'pct',
      newValue: 0.7,
    },
  ])

  assert.deepEqual(result, {
    ok: false,
    message: '未找到 Holiday 的训练计划，无法采纳该建议。',
    nextPlan: defaultWeeklyPlan,
  })
})

test('adoptPlanChange 在目标动作不存在时返回失败结果，且不产生部分写回', () => {
  const result = adoptPlanChange(defaultWeeklyPlan, 'Monday', [
    {
      action: 'update',
      exerciseName: '深蹲',
      field: 'pct',
      newValue: 0.7,
    },
    {
      action: 'update',
      exerciseName: '卧推',
      field: 'pct',
      newValue: 0.65,
    },
  ])

  assert.deepEqual(result, {
    ok: false,
    message: '未找到 Monday 的动作“卧推”，无法采纳该建议。',
    nextPlan: defaultWeeklyPlan,
  })
  assert.equal(defaultWeeklyPlan.Monday.exercises[0].pct, 0.75)
})
