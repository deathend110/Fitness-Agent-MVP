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
  const columns = buildWeeklyPlanColumns(demoWeeklyPlan)

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
})

test('buildWeeklyPlanLayoutModel 会输出桌面比例网格模板与窄屏兜底标志', () => {
  const layoutModel = buildWeeklyPlanLayoutModel(demoWeeklyPlan)

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
  })

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

test('PlanTab 移除 expandedDay 和 toggleDay 列展开状态链路', () => {
  const planTabSource = readWorkspaceFile('src/tabs/PlanTab.jsx')

  assert.doesNotMatch(planTabSource, /expandedDay/)
  assert.doesNotMatch(planTabSource, /toggleDay/)
  assert.doesNotMatch(planTabSource, /expanded=/)
  assert.doesNotMatch(planTabSource, /onToggle=/)
})

test('PlanWeekGrid 保持桌面固定 7 列模板且不依赖横向滚动', () => {
  const gridSource = readWorkspaceFile('src/components/plan-grid/PlanWeekGrid.jsx')

  assert.match(gridSource, /xl:grid-cols-\[var\(--plan-grid-columns\)\]/)
  assert.doesNotMatch(gridSource, /overflow-x-auto/)
})

test('PlanWeekGridColumn 不再保留 expanded 状态或用 CSS 遮盖交互残留', () => {
  const columnSource = readWorkspaceFile('src/components/plan-grid/PlanWeekGridColumn.jsx')

  assert.doesNotMatch(columnSource, /isExpanded/)
  assert.doesNotMatch(columnSource, /pointer-events:\s*none/)
  assert.doesNotMatch(columnSource, /display:\s*none/)
  assert.doesNotMatch(columnSource, /aria-expanded/)
  assert.match(columnSource, /column\.isTrainingDay/)
})

test('PlanDayCard 删除 expanded 和 onToggle 接口，并始终渲染完整卡片内容', () => {
  const cardSource = readWorkspaceFile('src/components/PlanDayCard.jsx')

  assert.doesNotMatch(cardSource, /\bexpanded\b/)
  assert.doesNotMatch(cardSource, /\bonToggle\b/)
  assert.doesNotMatch(cardSource, /\{expanded \?/)
  assert.match(cardSource, /<PlanDayCardHeader/)
  assert.match(cardSource, /<PlanDayTypeSection/)
  assert.match(cardSource, /<div className="mt-4 space-y-4">/)
})

test('PlanDayCardHeader 删除按钮展开语义，不再输出 aria-expanded、展开、收起', () => {
  const headerSource = readWorkspaceFile('src/components/PlanDayCardHeader.jsx')

  assert.doesNotMatch(headerSource, /expanded/)
  assert.doesNotMatch(headerSource, /onToggle/)
  assert.doesNotMatch(headerSource, /aria-expanded/)
  assert.doesNotMatch(headerSource, /toggleLabel/)
  assert.doesNotMatch(headerSource, /<button/)
  assert.doesNotMatch(headerSource, /展开|收起/)
  assert.match(headerSource, /<div/)
})
