import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'

import { buildPlanDayDisplayModel } from '../src/utils/planDayDisplay.js'

const workspaceRoot = process.cwd()

function readWorkspaceFile(relativePath) {
  return readFileSync(path.join(workspaceRoot, relativePath), 'utf8')
}

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
  assert.equal(model.layout, 'rest-compact')
  assert.equal(model.showAddExerciseButton, false)
  assert.equal(model.showDayTypeSection, false)
  assert.equal(model.showNoteEntry, false)
  assert.equal(model.emptyState.tone, 'rest')
  assert.equal(model.emptyState.title, '休息日')
  assert.deepEqual(model.emptyState.descriptionLines, ['身体恢复', '蓄力'])
  assert.equal(model.headerBadgeLabel, '休息')
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
  assert.equal(model.layout, 'training')
  assert.equal(model.showAddExerciseButton, true)
  assert.equal(model.showDayTypeSection, true)
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
  assert.equal(model.layout, 'rest-history')
  assert.equal(model.showAddExerciseButton, false)
  assert.equal(model.showDayTypeSection, true)
  assert.equal(model.emptyState, null)
  assert.equal(model.historyHint, '当前标记为休息日，历史动作仍保留，切回训练类型后可继续补充。')
  assert.equal(model.preview.title, '保留 1 个历史动作')
})

test('PlanDayCard 会为紧凑休息日隐藏日类型区并走独立轻量面板分支', () => {
  const cardSource = readWorkspaceFile('src/components/PlanDayCard.jsx')

  assert.match(cardSource, /const showDayTypeSection = displayModel\.showDayTypeSection !== false/)
  assert.match(cardSource, /const isCompactRestDay = displayModel\.layout === 'rest-compact'/)
  assert.match(cardSource, /\{showDayTypeSection \? \(/)
  assert.match(cardSource, /<PlanRestDayPanel[\s\S]*descriptionLines=\{visibleEmptyState\.descriptionLines\}/)
})

test('PlanRestDayPanel 去掉旧版厚卡片边框，改为轻量图标和两行恢复文案', () => {
  const panelSource = readWorkspaceFile('src/components/plan-rest/PlanRestDayPanel.jsx')

  assert.match(panelSource, /function PlanRestDayPanel\(\{ description, descriptionLines, title \}\)/)
  assert.match(panelSource, /svg/)
  assert.match(panelSource, /map\(\(line\)/)
  assert.doesNotMatch(panelSource, /rounded-2xl border border-fitloop-line\/70 bg-fitloop-panel/)
  assert.doesNotMatch(panelSource, /Zz/)
})
