import test from 'node:test'
import assert from 'node:assert/strict'
import { demoWeeklyPlan } from '../src/utils/defaultData.js'
import { buildWeeklyPlanColumns, buildWeeklyPlanLayoutModel } from '../src/utils/planLayout.js'

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
  assert.deepEqual(columns.map((column) => column.desktopSpan), [2, 1, 2, 1, 2, 1, 1])
  assert.equal(columns[0].isTrainingDay, true)
  assert.equal(columns[1].isTrainingDay, false)
  assert.equal(columns[0].exerciseCount, demoWeeklyPlan.Monday.exercises.length)
})

test('buildWeeklyPlanLayoutModel 会输出桌面比例网格模板与窄屏兜底标志', () => {
  const layoutModel = buildWeeklyPlanLayoutModel(demoWeeklyPlan)

  assert.equal(layoutModel.desktopTemplateColumns, '2fr 1fr 2fr 1fr 2fr 1fr 1fr')
  assert.equal(layoutModel.desktopGridColumnCount, 10)
  assert.equal(layoutModel.compactMode, 'stack')
  assert.equal(layoutModel.shouldAvoidHorizontalScrollOnDesktop, true)
  assert.deepEqual(
    layoutModel.columns.map((column) => ({
      dayKey: column.dayKey,
      desktopSpan: column.desktopSpan,
      width: column.width,
    })),
    [
      { dayKey: 'Monday', desktopSpan: 2, width: 'wide' },
      { dayKey: 'Tuesday', desktopSpan: 1, width: 'narrow' },
      { dayKey: 'Wednesday', desktopSpan: 2, width: 'wide' },
      { dayKey: 'Thursday', desktopSpan: 1, width: 'narrow' },
      { dayKey: 'Friday', desktopSpan: 2, width: 'wide' },
      { dayKey: 'Saturday', desktopSpan: 1, width: 'narrow' },
      { dayKey: 'Sunday', desktopSpan: 1, width: 'narrow' },
    ],
  )
})
