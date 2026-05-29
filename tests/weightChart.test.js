import test from 'node:test'
import assert from 'node:assert/strict'
import { buildWeightChartModel } from '../src/utils/weightChart.js'

test('buildWeightChartModel 只保留近 14 天内有效体重并按日期升序输出', () => {
  const model = buildWeightChartModel(
    {
      '2026-05-12': { weight: 79.8 },
      '2026-05-17': { weight: 80.2 },
      '2026-05-20': { weight: null },
      '2026-05-24': { weight: 80.5 },
      '2026-05-30': { weight: 81.1 },
      '2026-05-31': { weight: 81.4 },
    },
    '2026-05-30',
  )

  assert.equal(model.hasEnoughData, true)
  assert.deepEqual(model.points, [
    { dateKey: '2026-05-17', label: '05/17', weight: 80.2 },
    { dateKey: '2026-05-24', label: '05/24', weight: 80.5 },
    { dateKey: '2026-05-30', label: '05/30', weight: 81.1 },
  ])
})

test('buildWeightChartModel 在有效体重少于 2 条时返回空状态模型', () => {
  const model = buildWeightChartModel(
    {
      '2026-05-18': { weight: null },
      '2026-05-29': { weight: 80.8 },
    },
    '2026-05-30',
  )

  assert.equal(model.hasEnoughData, false)
  assert.deepEqual(model.points, [{ dateKey: '2026-05-29', label: '05/29', weight: 80.8 }])
  assert.equal(model.emptyMessage, '近 14 天至少需要 2 条体重记录，才会显示趋势图。')
})
