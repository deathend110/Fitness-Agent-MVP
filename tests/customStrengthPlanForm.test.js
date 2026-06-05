import assert from 'node:assert/strict'
import test from 'node:test'

import {
  buildCreateCustomStrengthCyclePayload,
  createCustomStrengthDraft,
} from '../src/utils/customStrengthPlanForm.js'

test('createCustomStrengthDraft 会默认创建 4 周 7 天的中文空草稿', () => {
  const draft = createCustomStrengthDraft()

  assert.equal(draft.name, '')
  assert.equal(draft.startDate, '')
  assert.equal(draft.totalWeeks, 4)
  assert.equal(draft.weeks.length, 4)
  assert.equal(draft.weeks[0].weekIndex, 1)
  assert.equal(draft.weeks[0].days.length, 7)
  assert.deepEqual(
    draft.weeks[0].days.map((day) => day.label),
    ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
  )
  assert.deepEqual(draft.mainLifts, {
    squat: { tm: '' },
    bench: { tm: '' },
    deadlift: { tm: '' },
    ohp: { tm: '' },
  })
})

test('buildCreateCustomStrengthCyclePayload 会把草稿映射成 custom_strength 创建载荷', () => {
  const payload = buildCreateCustomStrengthCyclePayload({
    name: '四周力量周期',
    startDate: '2026-06-09',
    totalWeeks: 2,
    mainLifts: {
      squat: { tm: '180' },
      bench: { tm: '120.5' },
      deadlift: { tm: '' },
      ohp: { tm: '  ' },
    },
    weeks: [
      {
        weekIndex: 1,
        days: [
          { dayIndex: 1, label: '周一', type: 'lower', exercises: [] },
        ],
      },
      {
        weekIndex: 2,
        days: [
          { dayIndex: 1, label: '周一', type: 'upper', exercises: [] },
        ],
      },
    ],
  })

  assert.deepEqual(payload, {
    presetKey: 'custom_strength',
    startDate: '2026-06-09',
    goal: 'strength',
    baseLifts: {
      squat: { tm: 180 },
      bench: { tm: 120.5 },
    },
    config: {
      planType: 'custom_strength',
      name: '四周力量周期',
      startDate: '2026-06-09',
      totalWeeks: 2,
      mainLifts: {
        squat: { tm: 180 },
        bench: { tm: 120.5 },
      },
      weeks: [
        {
          weekIndex: 1,
          days: [{ dayIndex: 1, label: '周一', type: 'lower', exercises: [] }],
        },
        {
          weekIndex: 2,
          days: [{ dayIndex: 1, label: '周一', type: 'upper', exercises: [] }],
        },
      ],
    },
  })
})

test('buildCreateCustomStrengthCyclePayload 会用最终 weeks 长度矫正 totalWeeks', () => {
  const payload = buildCreateCustomStrengthCyclePayload({
    name: '周数不一致草稿',
    startDate: '2026-06-09',
    totalWeeks: 4,
    mainLifts: {
      squat: { tm: '180' },
    },
    weeks: [
      { weekIndex: 1, days: [] },
      { weekIndex: 2, days: [] },
    ],
  })

  assert.equal(payload.config.totalWeeks, 2)
  assert.equal(payload.config.weeks.length, 2)
})

test('buildCreateCustomStrengthCyclePayload 会在 weeks 非数组时稳定回退', () => {
  const payload = buildCreateCustomStrengthCyclePayload({
    name: '异常草稿',
    startDate: '2026-06-09',
    totalWeeks: 3,
    mainLifts: {
      bench: { tm: '110' },
    },
    weeks: null,
  })

  assert.equal(payload.config.totalWeeks, 0)
  assert.deepEqual(payload.config.weeks, [])
  assert.deepEqual(payload.baseLifts, {
    bench: { tm: 110 },
  })
})

test('buildCreateCustomStrengthCyclePayload 不会误改 weeks 内已有 day 与 exercise 结构', () => {
  const existingWeeks = [
    {
      weekIndex: 1,
      days: [
        {
          dayIndex: 1,
          label: '周一',
          type: 'lower_strength',
          exercises: [
            {
              id: 'w1d1-squat',
              name: 'Back Squat',
              category: 'main',
              progression: { mode: 'percent_tm', liftKey: 'squat', percentTm: 0.75 },
              prescription: { sets: 5, reps: 5 },
              notes: '保持技术稳定',
            },
          ],
        },
      ],
    },
  ]

  const payload = buildCreateCustomStrengthCyclePayload({
    name: '结构保持草稿',
    startDate: '2026-06-09',
    totalWeeks: 7,
    mainLifts: {
      squat: { tm: '180' },
    },
    weeks: existingWeeks,
  })

  assert.equal(payload.config.totalWeeks, 1)
  assert.deepEqual(payload.config.weeks, existingWeeks)
  assert.notEqual(payload.config.weeks, existingWeeks)
  assert.notEqual(payload.baseLifts, payload.config.mainLifts)
})

test('buildCreateCustomStrengthCyclePayload 会过滤 weeks 中的异常数组元素', () => {
  const validWeek = {
    weekIndex: 2,
    days: [{ dayIndex: 3, label: '周三', type: 'pull', exercises: [] }],
  }

  const payload = buildCreateCustomStrengthCyclePayload({
    name: '坏周元素草稿',
    startDate: '2026-06-09',
    totalWeeks: 9,
    mainLifts: {
      deadlift: { tm: '200' },
    },
    weeks: [null, 1, 'bad', undefined, validWeek],
  })

  assert.equal(payload.config.totalWeeks, 1)
  assert.deepEqual(payload.config.weeks, [validWeek])
})

test('buildCreateCustomStrengthCyclePayload 会过滤 weeks 中的数组型坏元素', () => {
  const validWeek = { weekIndex: 1, days: [] }

  const payload = buildCreateCustomStrengthCyclePayload({
    name: '数组型坏周草稿',
    startDate: '2026-06-09',
    totalWeeks: 5,
    mainLifts: {
      squat: { tm: '180' },
    },
    weeks: [[], [1], validWeek],
  })

  assert.equal(payload.config.totalWeeks, 1)
  assert.deepEqual(payload.config.weeks, [validWeek])
})
