import test from 'node:test'
import assert from 'node:assert/strict'
import { buildPlanHeaderModel } from '../src/utils/planHeader.js'

test('buildPlanHeaderModel 会生成训练计划头部展示模型', () => {
  const headerModel = buildPlanHeaderModel({
    referenceDate: '2026-05-30',
  })

  assert.equal(headerModel.title, '本周训练计划')
  assert.equal(headerModel.weekRangeLabel, '2026年5月25日 - 5月31日')
  assert.equal(headerModel.weekBadgeLabel, '第 22 周')
  assert.equal(headerModel.settingsButton.label, '计划设置')
  assert.equal(headerModel.settingsButton.isPlaceholder, true)
  assert.deepEqual(headerModel.secondaryActions, [])
  assert.equal(headerModel.legendItems.length, 2)
  assert.deepEqual(
    headerModel.legendItems.map((item) => ({
      label: item.label,
      tone: item.tone,
    })),
    [
      { label: '主项', tone: 'main' },
      { label: '辅项', tone: 'accessory' },
    ],
  )
})

test('buildPlanHeaderModel 在周日参考日期下仍返回同一自然周区间', () => {
  const headerModel = buildPlanHeaderModel({
    referenceDate: '2026-05-31',
  })

  assert.equal(headerModel.weekRangeLabel, '2026年5月25日 - 5月31日')
  assert.equal(headerModel.weekBadgeLabel, '第 22 周')
})

test('buildPlanHeaderModel 在跨年周里返回正确的 ISO 周编号', () => {
  const headerModel = buildPlanHeaderModel({
    referenceDate: '2027-01-01',
  })

  assert.equal(headerModel.weekRangeLabel, '2026年12月28日 - 1月3日')
  assert.equal(headerModel.weekBadgeLabel, '第 53 周')
})
