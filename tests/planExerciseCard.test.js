import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'
import vm from 'node:vm'

import { buildPlanExerciseCardModel } from '../src/utils/planExerciseCard.js'

const planExerciseItemSource = fs.readFileSync(
  new URL('../src/components/PlanExerciseItem.jsx', import.meta.url),
  'utf8',
)

function loadPlanExerciseItemHelpers() {
  const helperBlockMatch = planExerciseItemSource.match(
    /export function isPlanExerciseNoDragTarget[\s\S]*?export function shouldBlockPlanExerciseDragStart[\s\S]*?\r?\n}\r?\n/,
  )

  assert.ok(helperBlockMatch, '未找到 PlanExerciseItem 拖拽 helper 定义')

  const helperBlock = helperBlockMatch[0].replaceAll('export function', 'function')
  const script = new vm.Script(
    `${helperBlock}
module.exports = {
  isPlanExerciseNoDragTarget,
  createPlanExerciseDragState,
  shouldBlockPlanExerciseDragStart,
}`,
  )
  const context = {
    module: { exports: {} },
    exports: {},
  }

  script.runInNewContext(context)
  return context.module.exports
}

const {
  createPlanExerciseDragState,
  shouldBlockPlanExerciseDragStart,
} = loadPlanExerciseItemHelpers()

test('buildPlanExerciseCardModel 会把主项百分比动作整理成效果稿卡片模型', () => {
  const model = buildPlanExerciseCardModel(
    {
      id: 'squat-1',
      name: '深蹲',
      tier: 'main',
      ref1RM: 'squat',
      pct: 0.75,
      kg: null,
      sets: 4,
      reps: 6,
      rpe: 8,
      note: '主项，保持核心稳定',
    },
    {
      oneRM: {
        squat: 150,
      },
    },
  )

  assert.equal(model.tierLabel, '主项')
  assert.equal(model.tierTone, 'main')
  assert.equal(model.topMetaLabel, '深蹲 1RM 150kg × 75%')
  assert.equal(model.volumeLabel, '4 组 × 6 次')
  assert.equal(model.weightLabel, '112.5kg')
  assert.equal(model.effortLabel, 'RPE 8')
  assert.equal(model.noteLabel, '主项，保持核心稳定')
  assert.equal(model.noteEmpty, false)
  assert.equal(model.topMetaMuted, false)
  assert.equal(model.weightUnitLabel, 'kg')
  assert.equal(model.summaryLabel, '112.5kg · 4 组 × 6 次 · RPE 8')
  assert.deepEqual(model.volumePill, {
    label: '组次',
    value: '4 组 × 6 次',
  })
  assert.deepEqual(model.effortPill, {
    label: 'RPE',
    value: 'RPE 8',
  })
})

test('buildPlanExerciseCardModel 会给固定重量辅项保留空来源占位与备注兜底', () => {
  const model = buildPlanExerciseCardModel(
    {
      id: 'row-1',
      name: '坐姿划船',
      tier: 'accessory',
      kg: 60,
      sets: 3,
      reps: 10,
      rpe: 7,
      note: '',
    },
    {},
  )

  assert.equal(model.tierLabel, '辅项')
  assert.equal(model.tierTone, 'accessory')
  assert.equal(model.topMetaLabel, '固定重量')
  assert.equal(model.topMetaMuted, false)
  assert.equal(model.weightLabel, '60kg')
  assert.equal(model.weightUnitLabel, 'kg')
  assert.equal(model.loadDetailLabel, '固定重量')
  assert.equal(model.loadBadgeLabel, '固定 kg')
  assert.equal(model.noteLabel, '暂无备注')
  assert.equal(model.noteEmpty, true)
})

test('buildPlanExerciseCardModel 会为自重动作提供稳定主显示与说明', () => {
  const model = buildPlanExerciseCardModel(
    {
      id: 'pull-up-1',
      name: '引体向上',
      tier: 'main',
      kg: null,
      ref1RM: null,
      pct: null,
      sets: 4,
      reps: 8,
      rpe: null,
      note: '   ',
    },
    {},
  )

  assert.equal(model.weightLabel, '自重')
  assert.equal(model.weightUnitLabel, '')
  assert.equal(model.topMetaLabel, '自重动作')
  assert.equal(model.topMetaMuted, false)
  assert.equal(model.effortLabel, '未填写 RPE')
  assert.equal(model.noteLabel, '暂无备注')
  assert.equal(model.noteEmpty, true)
})

test('buildPlanExerciseCardModel 会为长动作名和未命名动作保留稳定字段', () => {
  const unnamedModel = buildPlanExerciseCardModel(
    {
      id: 'unnamed-1',
      name: '   ',
      tier: 'accessory',
      kg: 25,
      sets: 3,
      reps: 15,
      rpe: 8,
      note: '',
    },
    {},
  )

  const longName = '杠铃保加利亚分腿蹲停顿离心控制强化组'
  const longNameModel = buildPlanExerciseCardModel(
    {
      id: 'long-name-1',
      name: longName,
      tier: 'main',
      ref1RM: 'squat',
      pct: 0.6,
      kg: null,
      sets: 3,
      reps: 8,
      rpe: 7.5,
      note: '',
    },
    {
      oneRM: {
        squat: 140,
      },
    },
  )

  assert.equal(unnamedModel.name, '未命名动作')
  assert.equal(unnamedModel.noteLabel, '暂无备注')
  assert.equal(longNameModel.name, longName)
  assert.equal(longNameModel.topMetaLabel, '深蹲 1RM 140kg × 60%')
  assert.equal(longNameModel.summaryLabel, '84kg · 3 组 × 8 次 · RPE 7.5')
})

test('PlanExerciseItem 会渲染固定重量来源说明与三点入口', () => {
  assert.match(planExerciseItemSource, /\{cardModel\.topMetaLabel \|\| '\\u00A0'\}/)
  assert.match(planExerciseItemSource, /aria-label="更多操作"/)
})

test('PlanExerciseItem 会保留菜单入口并为整卡拖拽添加隔离操作区', () => {
  assert.match(planExerciseItemSource, /draggable=\{dragEnabled\}/)
  assert.match(planExerciseItemSource, /onDragStart=/)
  assert.match(planExerciseItemSource, /onDragEnter=/)
  assert.match(planExerciseItemSource, /onDragOver=/)
  assert.match(planExerciseItemSource, /onDrop=/)
  assert.match(planExerciseItemSource, /data-no-drag/)
  assert.match(planExerciseItemSource, /onPointerDownCapture=/)
  assert.match(planExerciseItemSource, /aria-label="更多操作"/)
})

test('shouldBlockPlanExerciseDragStart 会在 no-drag 区域按下后阻断一次拖拽启动', () => {
  const targetInMenu = {
    closest(selector) {
      return selector === '[data-no-drag="true"]' ? {} : null
    },
  }
  const state = createPlanExerciseDragState()

  assert.equal(state.dragBlocked, false)
  assert.equal(state.markPointerDown(targetInMenu), true)
  assert.equal(state.dragBlocked, true)
  assert.equal(shouldBlockPlanExerciseDragStart(true, state), true)
  assert.equal(state.dragBlocked, false)
  assert.equal(shouldBlockPlanExerciseDragStart(true, state), false)
  assert.equal(state.markPointerDown(null), false)
  assert.equal(shouldBlockPlanExerciseDragStart(false, state), true)
})

test('shouldBlockPlanExerciseDragStart 在禁拖期间也会消费阻断状态，避免重新启用后误伤第一次正常拖拽', () => {
  const targetInMenu = {
    closest(selector) {
      return selector === '[data-no-drag="true"]' ? {} : null
    },
  }
  const state = createPlanExerciseDragState()

  assert.equal(state.markPointerDown(targetInMenu), true)
  assert.equal(state.dragBlocked, true)
  assert.equal(shouldBlockPlanExerciseDragStart(false, state), true)
  assert.equal(state.dragBlocked, false)
  assert.equal(shouldBlockPlanExerciseDragStart(true, state), false)
})

test('createPlanExerciseDragState 会稳定维护拖拽悬停深度，避免卡片内部切换时闪烁', () => {
  const state = createPlanExerciseDragState()

  assert.equal(state.dropActive, false)
  assert.equal(state.enter(true), true)
  assert.equal(state.dropActive, true)
  assert.equal(state.enter(true), true)
  assert.equal(state.dropDepth, 2)
  assert.equal(state.leave(), true)
  assert.equal(state.dropActive, true)
  assert.equal(state.dropDepth, 1)
  assert.equal(state.leave(), false)
  assert.equal(state.dropActive, false)
  assert.equal(state.dropDepth, 0)
  assert.equal(state.enter(false), false)
  assert.equal(state.dropDepth, 0)
  state.enter(true)
  state.resetDrop()
  assert.equal(state.dropActive, false)
  assert.equal(state.dropDepth, 0)
})
