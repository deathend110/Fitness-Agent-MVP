import test from 'node:test'
import assert from 'node:assert/strict'
import { buildTodayPlanSummary } from '../src/utils/todayPlan.js'

test('buildTodayPlanSummary 在 rest 日返回休息日摘要', () => {
  const summary = buildTodayPlanSummary(
    {
      type: 'rest',
      exercises: [],
    },
    {},
  )

  assert.equal(summary.typeLabel, '休息日')
  assert.equal(summary.isRestDay, true)
  assert.equal(summary.message, '今天是休息日，当前没有训练动作安排。')
  assert.deepEqual(summary.exercises, [])
})

test('buildTodayPlanSummary 在训练日返回可扫描的动作摘要', () => {
  const summary = buildTodayPlanSummary(
    {
      type: '腿日',
      exercises: [
        {
          id: 'monday-squat',
          name: '深蹲',
          ref1RM: 'squat',
          pct: 0.75,
          kg: null,
          sets: 4,
          reps: 6,
          rpe: 8,
          note: '主项',
        },
        {
          id: 'monday-rdl',
          name: '罗马尼亚硬拉',
          ref1RM: null,
          pct: null,
          kg: 80,
          sets: 3,
          reps: 10,
          rpe: null,
          note: '',
        },
      ],
    },
    {
      squat: 120,
    },
  )

  assert.equal(summary.typeLabel, '腿日')
  assert.equal(summary.isRestDay, false)
  assert.equal(summary.message, '')
  assert.deepEqual(summary.exercises, [
    {
      id: 'monday-squat',
      name: '深蹲',
      detail: '90kg 路 4 组 x 6 次 路 RPE 8 路 主项',
    },
    {
      id: 'monday-rdl',
      name: '罗马尼亚硬拉',
      detail: '80kg 路 3 组 x 10 次',
    },
  ])
})

test('buildTodayPlanSummary 在非 rest 但没有动作时返回空计划提示', () => {
  const summary = buildTodayPlanSummary(
    {
      type: '推日',
      exercises: [],
    },
    {
      bench: 90,
    },
  )

  assert.equal(summary.typeLabel, '推日')
  assert.equal(summary.isRestDay, true)
  assert.equal(summary.message, '今天暂不训练，当前计划还没有安排具体动作。')
  assert.deepEqual(summary.exercises, [])
})
