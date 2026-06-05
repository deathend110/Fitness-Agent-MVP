import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { demoWeeklyPlan } from '../src/utils/defaultData.js'
import { buildWeeklyPlanColumns, buildWeeklyPlanLayoutModel } from '../src/utils/planLayout.js'

const workspaceRoot = process.cwd()

function readWorkspaceFile(relativePath) {
  return readFileSync(path.join(workspaceRoot, relativePath), 'utf8')
}

test('buildWeeklyPlanColumns 会生成按周一到周日排列的 7 天列，并区分训练日与休息日比例', () => {
  const columns = buildWeeklyPlanColumns(demoWeeklyPlan, { referenceDate: '2026-05-30' })

  assert.equal(columns.length, 7)
  assert.deepEqual(columns.map((column) => column.dayKey), [
    'Monday',
    'Tuesday',
    'Wednesday',
    'Thursday',
    'Friday',
    'Saturday',
    'Sunday',
  ])
  assert.deepEqual(columns.map((column) => column.width), [
    'wide',
    'narrow',
    'wide',
    'narrow',
    'wide',
    'narrow',
    'narrow',
  ])
  assert.equal(columns[0].isTrainingDay, true)
  assert.equal(columns[1].isTrainingDay, false)
  assert.equal(columns[0].exerciseCount, demoWeeklyPlan.Monday.exercises.length)
  assert.equal(columns[0].dateLabel, '5月25日')
  assert.equal(columns[6].dateLabel, '5月31日')
})

test('buildWeeklyPlanLayoutModel 会输出桌面比例网格模板与窄屏兜底标志', () => {
  const layoutModel = buildWeeklyPlanLayoutModel(demoWeeklyPlan, { referenceDate: '2026-05-30' })

  assert.equal(layoutModel.desktopTemplateColumns, '2fr 1fr 2fr 1fr 2fr 1fr 1fr')
  assert.equal(layoutModel.desktopGridColumnCount, 7)
  assert.equal(layoutModel.compactMode, 'stack')
  assert.equal(layoutModel.shouldAvoidHorizontalScrollOnDesktop, true)
  assert.deepEqual(
    layoutModel.columns.map((column) => ({
      dayKey: column.dayKey,
      width: column.width,
    })),
    [
      { dayKey: 'Monday', width: 'wide' },
      { dayKey: 'Tuesday', width: 'narrow' },
      { dayKey: 'Wednesday', width: 'wide' },
      { dayKey: 'Thursday', width: 'narrow' },
      { dayKey: 'Friday', width: 'wide' },
      { dayKey: 'Saturday', width: 'narrow' },
      { dayKey: 'Sunday', width: 'narrow' },
    ],
  )
  assert.equal('expandedDay' in layoutModel, false)
  assert.equal('defaultExpandedDayKey' in layoutModel, false)
})

test('buildWeeklyPlanLayoutModel 会根据训练日与休息日动态生成 7 列宽窄比例模板', () => {
  const layoutModel = buildWeeklyPlanLayoutModel({
    Monday: { type: 'rest', exercises: [] },
    Tuesday: { type: 'bench', exercises: [{ id: 'bench-1' }] },
    Wednesday: { type: 'rest', exercises: [] },
    Thursday: { type: 'deadlift', exercises: [{ id: 'deadlift-1' }] },
    Friday: { type: 'rest', exercises: [] },
    Saturday: { type: 'squat', exercises: [{ id: 'squat-1' }] },
    Sunday: { type: 'rest', exercises: [] },
  }, { referenceDate: '2026-05-30' })

  assert.deepEqual(layoutModel.columns.map((column) => column.dayKey), [
    'Monday',
    'Tuesday',
    'Wednesday',
    'Thursday',
    'Friday',
    'Saturday',
    'Sunday',
  ])
  assert.equal(layoutModel.desktopTemplateColumns, '1fr 2fr 1fr 2fr 1fr 2fr 1fr')
  assert.deepEqual(layoutModel.columns.map((column) => column.width), [
    'narrow',
    'wide',
    'narrow',
    'wide',
    'narrow',
    'wide',
    'narrow',
  ])
})

test('buildWeeklyPlanLayoutModel 会把周元信息暴露到布局模型顶层，供头部和列共享', () => {
  const layoutModel = buildWeeklyPlanLayoutModel(demoWeeklyPlan, { referenceDate: '2026-05-30' })

  assert.deepEqual(layoutModel.weekMeta, {
    source: 'derived',
    weekNumber: 22,
    weekStart: '2026-05-25',
    weekEnd: '2026-05-31',
  })
})

test('buildWeeklyPlanColumns 会优先使用 weeklyPlan.weekMeta 生成每天日期标签', () => {
  const columns = buildWeeklyPlanColumns({
    weekMeta: {
      weekNumber: 22,
      weekStart: '2026-05-25',
      weekEnd: '2026-05-31',
    },
    Monday: { type: '腿日', exercises: [] },
    Tuesday: { type: 'rest', exercises: [] },
    Wednesday: { type: '推日', exercises: [] },
    Thursday: { type: 'rest', exercises: [] },
    Friday: { type: '拉日', exercises: [] },
    Saturday: { type: 'rest', exercises: [] },
    Sunday: { type: 'rest', exercises: [] },
  }, { referenceDate: '2026-05-30' })

  assert.deepEqual(columns.map((column) => column.dateLabel), [
    '5月25日',
    '5月26日',
    '5月27日',
    '5月28日',
    '5月29日',
    '5月30日',
    '5月31日',
  ])
})

test('buildWeeklyPlanColumns 会固定输出 7 天列，并保留周元信息和自定义训练类型', () => {
  const weeklyPlan = {
    weekMeta: {
      weekNumber: 22,
      weekStart: '2026-05-25',
      weekEnd: '2026-05-31',
    },
    Monday: null,
    Tuesday: {
      type: 'rest',
      exercises: 'not-an-array',
    },
    Wednesday: {
      type: 'upper body strength',
      exercises: [],
    },
    Friday: {
      type: '拉日',
      exercises: [{ id: 'friday-row' }],
    },
  }

  const columns = buildWeeklyPlanColumns(weeklyPlan, { referenceDate: '2026-05-30' })

  assert.equal(columns.length, 7)
  assert.deepEqual(columns.map((column) => column.dayKey), [
    'Monday',
    'Tuesday',
    'Wednesday',
    'Thursday',
    'Friday',
    'Saturday',
    'Sunday',
  ])
  assert.equal(columns[0].dateLabel, '5月25日')
  assert.equal(columns[0].dateLabelSource, 'weeklyPlan')
  assert.equal(columns[0].weekMeta.weekNumber, 22)
  assert.equal(columns[0].plan.type, 'rest')
  assert.equal(columns[1].plan.type, 'rest')
  assert.equal(columns[2].plan.type, 'upper body strength')
  assert.equal(columns[2].isTrainingDay, true)
  assert.equal(columns[4].plan.type, '拉日')
  assert.equal(columns[4].isTrainingDay, true)
  assert.equal(columns[1].exerciseCount, 0)
})

test('buildWeeklyPlanColumns 在旧 weekMeta 缺失完整周区间时会回退到当前自然周日期标签', () => {
  const columns = buildWeeklyPlanColumns({
    weekMeta: {
      weekNumber: 22,
      weekStart: '2026-04-27',
    },
    Monday: { type: 'rest', exercises: [] },
    Tuesday: { type: 'rest', exercises: [] },
    Wednesday: { type: 'rest', exercises: [] },
    Thursday: { type: 'rest', exercises: [] },
    Friday: { type: 'rest', exercises: [] },
    Saturday: { type: 'rest', exercises: [] },
    Sunday: { type: 'rest', exercises: [] },
  }, { referenceDate: '2026-05-30' })

  assert.deepEqual(columns.map((column) => column.dateLabel), [
    '5月25日',
    '5月26日',
    '5月27日',
    '5月28日',
    '5月29日',
    '5月30日',
    '5月31日',
  ])
})

test('PlanTab 不再保留展开状态链路或无意义的 getTodayKey 占位', () => {
  const planTabSource = readWorkspaceFile('src/tabs/PlanTab.jsx')

  assert.doesNotMatch(planTabSource, /expandedDay/)
  assert.doesNotMatch(planTabSource, /toggleDay/)
  assert.doesNotMatch(planTabSource, /expanded=/)
  assert.doesNotMatch(planTabSource, /onToggle=/)
  assert.doesNotMatch(planTabSource, /getTodayKey/)
})

test('PlanWeekGrid 与布局模型继续用桌面模板列保证 7 天固定看板', () => {
  const gridSource = readWorkspaceFile('src/components/plan-grid/PlanWeekGrid.jsx')

  assert.match(gridSource, /plan-grid-columns/)
  assert.doesNotMatch(gridSource, /overflow-x-auto/)
})

test('PlanWeekGridColumn 不再保留展开态字段，也不通过样式遮盖交互语义', () => {
  const columnSource = readWorkspaceFile('src/components/plan-grid/PlanWeekGridColumn.jsx')

  assert.doesNotMatch(columnSource, /isExpanded/)
  assert.doesNotMatch(columnSource, /pointer-events:\s*none/)
  assert.doesNotMatch(columnSource, /aria-expanded/)
})

test('PlanDayCard 删除展开接口与条件渲染分支，只保留固定展示完整内容', () => {
  const cardSource = readWorkspaceFile('src/components/PlanDayCard.jsx')

  assert.doesNotMatch(cardSource, /\bexpanded\b/)
  assert.doesNotMatch(cardSource, /\bonToggle\b/)
  assert.doesNotMatch(cardSource, /\{expanded\s*\?/)
})

test('PlanDayCard 源码会按动作数和编辑态决定是否允许动作拖拽', () => {
  const cardSource = readWorkspaceFile('src/components/PlanDayCard.jsx')

  assert.match(cardSource, /canReorderPlanDayExercises|dragEnabled/)
  assert.match(cardSource, /onMoveExercise/)
  assert.match(cardSource, /plan\.exercises\.length/)
  assert.match(cardSource, /editingExerciseId/)
})

test('PlanDayCardHeader 删除展开相关接口和 ARIA 语义', () => {
  const headerSource = readWorkspaceFile('src/components/PlanDayCardHeader.jsx')

  assert.doesNotMatch(headerSource, /\bexpanded\b/)
  assert.doesNotMatch(headerSource, /\bonToggle\b/)
  assert.doesNotMatch(headerSource, /aria-expanded/)
  assert.doesNotMatch(headerSource, /toggleLabel/)
  assert.doesNotMatch(headerSource, /展开|收起/)
})
