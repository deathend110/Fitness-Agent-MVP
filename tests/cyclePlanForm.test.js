import assert from 'node:assert/strict'
import test from 'node:test'

import {
  buildCreateCyclePlanPayload,
  createCyclePlanDraft,
  toggleTrainingDay,
} from '../src/utils/cyclePlanForm.js'

test('buildCreateCyclePlanPayload 会把周期草稿安全映射成后端载荷', () => {
  const payload = buildCreateCyclePlanPayload({
    presetKey: 'madcow_5x5',
    startDate: '2026-06-08',
    goal: 'strength',
    baseLifts: {
      squat: { oneRm: '180', tm: '165' },
      bench: { oneRm: '125.5', tm: '' },
      deadlift: { oneRm: '220', tm: '0' },
    },
    config: {
      trainingDays: ['Tuesday', 'Thursday', 'Saturday'],
    },
  })

  assert.deepEqual(payload, {
    presetKey: 'madcow_5x5',
    startDate: '2026-06-08',
    goal: 'strength',
    baseLifts: {
      squat: { oneRm: 180, tm: 165 },
      bench: { oneRm: 125.5, tm: null },
      deadlift: { oneRm: 220, tm: 0 },
    },
    config: {
      trainingDays: ['Tuesday', 'Thursday', 'Saturday'],
    },
  })
})

test('buildCreateCyclePlanPayload 会把空白和非法数字归一化为 null', () => {
  const payload = buildCreateCyclePlanPayload({
    presetKey: 'texas_method',
    startDate: ' 2026-06-10 ',
    goal: '  ',
    baseLifts: {
      squat: { oneRm: 'abc', tm: '' },
      bench: { oneRm: null, tm: undefined },
      deadlift: { oneRm: '  ', tm: 'NaN' },
    },
    config: {
      trainingDays: ['Monday', 'Monday', '', 'Friday'],
    },
  })

  assert.deepEqual(payload, {
    presetKey: 'texas_method',
    startDate: '2026-06-10',
    goal: '',
    baseLifts: {
      squat: { oneRm: null, tm: null },
      bench: { oneRm: null, tm: null },
      deadlift: { oneRm: null, tm: null },
    },
    config: {
      trainingDays: ['Monday', 'Friday'],
    },
  })
})

test('createCyclePlanDraft 会优先用 profile 和活动周期回填草稿', () => {
  const draft = createCyclePlanDraft(
    {
      goal: '增肌',
      oneRM: { squat: 160, bench: 110, deadlift: 200 },
    },
    {
      cycle: {
        presetKey: 'candito_6week',
        startDate: '2026-06-01',
        goal: 'strength',
        baseLifts: {
          squat: { oneRm: 170, tm: 155 },
          bench: { oneRm: 115, tm: 105 },
          deadlift: { oneRm: 210, tm: 190 },
        },
        config: { trainingDays: ['Tuesday', 'Thursday'] },
      },
    },
  )

  assert.equal(draft.presetKey, 'candito_6week')
  assert.equal(draft.goal, 'strength')
  assert.equal(draft.baseLifts.squat.oneRm, '170')
  assert.equal(draft.baseLifts.squat.tm, '155')
  assert.deepEqual(draft.config.trainingDays, ['Tuesday', 'Thursday'])
})

test('toggleTrainingDay 会稳定增删训练日且保持顺序', () => {
  assert.deepEqual(toggleTrainingDay(['Tuesday'], 'Thursday'), ['Tuesday', 'Thursday'])
  assert.deepEqual(toggleTrainingDay(['Tuesday', 'Thursday'], 'Tuesday'), ['Thursday'])
})
