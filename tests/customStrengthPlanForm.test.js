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
