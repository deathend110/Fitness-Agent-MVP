import assert from 'node:assert/strict'
import test from 'node:test'

import {
  buildCycleSettingsStatus,
  buildCyclePresetSummary,
  getCyclePlanSourceLabel,
  getCycleStatusLabel,
  resolvePlanSettingsMode,
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

test('resolvePlanSettingsMode 会把设置页模式与真实生效来源拆开', () => {
  assert.equal(resolvePlanSettingsMode({ activeSource: 'manual' }, null), 'manual')
  assert.equal(
    resolvePlanSettingsMode(
      { activeSource: 'manual' },
      { cycle: { id: 8, status: 'active' } },
      'cycle',
    ),
    'cycle',
  )
  assert.equal(
    resolvePlanSettingsMode(
      { activeSource: 'cycle' },
      { cycle: { id: 8, status: 'active' } },
      'manual',
    ),
    'manual',
  )
})

test('buildCycleSettingsStatus 会返回独立计划提示和待确认周状态', () => {
  const model = buildCycleSettingsStatus({
    planSource: { activeSource: 'manual' },
    activeCyclePlan: {
      cycle: {
        id: 3,
        presetLabel: 'Candito 6 Week Strength',
        presetKey: 'candito_6week',
        status: 'active',
        currentWeekIndex: 2,
        pendingWeekIndex: 3,
      },
    },
  })

  assert.equal(model.activeSource, 'manual')
  assert.equal(model.sourceLabel, '当前来源：非周期计划')
  assert.equal(model.summaryLabel, 'Candito 6 Week Strength · 第 2 周')
  assert.equal(model.pendingWeekLabel, '已生成待确认的第 3 周')
  assert.equal(model.currentWeekLabel, '当前周期周次：第 2 周')
  assert.equal(model.canActivateCycle, true)
  assert.equal(model.canCreateCycle, false)
  assert.match(model.manualPlanHint, /手动计划与周期计划独立保存/)
})
