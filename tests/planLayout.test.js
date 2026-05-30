import test from 'node:test'
import assert from 'node:assert/strict'
import { demoWeeklyPlan } from '../src/utils/defaultData.js'
import { buildWeeklyPlanColumns } from '../src/utils/planLayout.js'

test('buildWeeklyPlanColumns 会生成按周一到周日排列的 7 天列，并标记训练日和休息日宽度', () => {
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
