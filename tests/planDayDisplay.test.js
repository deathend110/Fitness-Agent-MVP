import test from 'node:test'
import assert from 'node:assert/strict'

import { buildPlanDayDisplayModel } from '../src/utils/planDayDisplay.js'

test('buildPlanDayDisplayModel 会为休息日返回轻量空状态且不暴露备注入口', () => {
  const model = buildPlanDayDisplayModel({
    dayLabel: '周二',
    plan: {
      type: 'rest',
      exercises: [],
    },
    isTrainingDay: false,
  })

  assert.equal(model.variant, 'rest')
  assert.equal(model.showAddExerciseButton, false)
  assert.equal(model.showNoteEntry, false)
  assert.equal(model.emptyState.tone, 'rest')
  assert.equal(model.emptyState.title, '休息日')
  assert.equal(model.emptyState.description, '恢复节奏，给下一次训练留出余量。')
  assert.equal(model.preview.eyebrow, '轻安排')
})

test('buildPlanDayDisplayModel 会为无动作训练日返回独立空状态文案', () => {
  const model = buildPlanDayDisplayModel({
    dayLabel: '周四',
    plan: {
      type: '推日',
      exercises: [],
    },
    isTrainingDay: true,
  })

  assert.equal(model.variant, 'training')
  assert.equal(model.showAddExerciseButton, true)
  assert.equal(model.showNoteEntry, false)
  assert.equal(model.emptyState.tone, 'training-empty')
  assert.equal(model.emptyState.title, '暂未安排动作')
  assert.equal(model.emptyState.description, '先确定今天的训练重点，再补充动作。')
  assert.equal(model.preview.eyebrow, '待补充')
})

test('buildPlanDayDisplayModel 在休息日保留历史动作时继续开放编辑链路', () => {
  const model = buildPlanDayDisplayModel({
    dayLabel: '周六',
    plan: {
      type: 'rest',
      exercises: [{ id: 'deadlift', name: '硬拉' }],
    },
    isTrainingDay: false,
  })

  assert.equal(model.variant, 'rest')
  assert.equal(model.showAddExerciseButton, false)
  assert.equal(model.emptyState, null)
  assert.equal(model.historyHint, '当前标记为休息日，历史动作仍保留，切回训练类型后可继续补充。')
  assert.equal(model.preview.title, '保留 1 个历史动作')
})
