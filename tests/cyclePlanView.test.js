import assert from 'node:assert/strict'
import test from 'node:test'

import {
  buildCyclePresetSummary,
  getCyclePlanSourceLabel,
  getCycleStatusLabel,
} from '../src/utils/cyclePlanView.js'

test('getCyclePlanSourceLabel 会返回稳定的计划来源标签', () => {
  assert.deepEqual(getCyclePlanSourceLabel({ activeSource: 'manual' }), {
    tone: 'manual',
    label: '当前来源：非周期计划',
  })
  assert.deepEqual(getCyclePlanSourceLabel({ activeSource: 'cycle' }), {
    tone: 'cycle',
    label: '当前来源：周期计划',
  })
})

test('buildCyclePresetSummary 会组合 preset 标签与周次信息', () => {
  assert.equal(
    buildCyclePresetSummary({
      cycle: {
        presetLabel: 'Madcow 5x5',
        presetKey: 'madcow_5x5',
        currentWeekIndex: 3,
      },
    }),
    'Madcow 5x5 · 第 3 周',
  )

  assert.equal(
    buildCyclePresetSummary({
      cycle: {
        presetKey: 'texas_method',
      },
    }),
    'texas_method',
  )
})

test('getCycleStatusLabel 会把活动状态映射成中文标签', () => {
  assert.deepEqual(getCycleStatusLabel('active'), {
    tone: 'active',
    label: '进行中',
  })
  assert.deepEqual(getCycleStatusLabel('completed'), {
    tone: 'completed',
    label: '已停止',
  })
  assert.deepEqual(getCycleStatusLabel('pending'), {
    tone: 'default',
    label: 'pending',
  })
})
