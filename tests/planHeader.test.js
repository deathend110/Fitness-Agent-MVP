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

test('buildPlanHeaderModel 在旧数据缺少周元信息时仍返回稳定头部字段', () => {
  const headerModel = buildPlanHeaderModel({
    referenceDate: '2026-05-30',
    weeklyPlan: {
      Monday: {
        type: '腿日',
        exercises: [],
      },
    },
  })

  assert.deepEqual(headerModel.weekMeta, {
    source: 'derived',
    weekNumber: 22,
    weekStart: '2026-05-25',
    weekEnd: '2026-05-31',
  })
  assert.equal(headerModel.weekRangeLabel, '2026年5月25日 - 5月31日')
  assert.equal(headerModel.weekBadgeLabel, '第 22 周')
})

test('buildPlanHeaderModel 优先复用兼容周元信息，并在缺字段时自动补齐', () => {
  const headerModel = buildPlanHeaderModel({
    referenceDate: '2026-05-30',
    weeklyPlan: {
      weekMeta: {
        weekNumber: 9,
      },
    },
  })

  assert.deepEqual(headerModel.weekMeta, {
    source: 'weeklyPlan',
    weekNumber: 9,
    weekStart: '2026-05-25',
    weekEnd: '2026-05-31',
  })
  assert.equal(headerModel.weekBadgeLabel, '第 9 周')
  assert.equal(headerModel.weekRangeLabel, '2026年5月25日 - 5月31日')
})

test('buildPlanHeaderModel 在空计划下也会返回明确的计划设置占位说明', () => {
  const headerModel = buildPlanHeaderModel({
    referenceDate: '2026-05-30',
    weeklyPlan: null,
  })

  assert.deepEqual(headerModel.settingsButton, {
    label: '计划设置',
    hint: '当前仅提供入口占位，周期计划与经典计划模板将在后续版本开放。',
    title: '计划设置（建设中）',
    description: '这里会放周模板、周期节奏和经典计划库配置；当前 MVP 先保留统一入口，避免误导为完整功能已上线。',
    confirmLabel: '知道了',
    isPlaceholder: true,
  })
})
