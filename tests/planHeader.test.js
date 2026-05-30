import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { buildPlanHeaderModel } from '../src/utils/planHeader.js'

const workspaceRoot = process.cwd()

function readWorkspaceFile(relativePath) {
  return readFileSync(path.join(workspaceRoot, relativePath), 'utf8')
}

test('buildPlanHeaderModel 会生成训练计划头部展示模型', () => {
  const headerModel = buildPlanHeaderModel({
    referenceDate: '2026-05-30',
  })

  assert.equal(headerModel.title, '本周训练计划')
  assert.equal(headerModel.weekRangeLabel, '2026年5月25日 - 5月31日')
  assert.equal(headerModel.weekBadgeLabel, '第 22 周')
  assert.equal(headerModel.settingsButton.label, '计划设置')
  assert.equal(headerModel.settingsButton.isPlaceholder, true)
  assert.deepEqual(headerModel.viewTabs, [
    { key: 'week', label: '周视图', isActive: true, isInteractive: false },
    { key: 'list', label: '列表视图', isActive: false, isInteractive: false },
  ])
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

test('buildPlanHeaderModel 在计划内已有周起止日期时沿用真实周区间展示', () => {
  const headerModel = buildPlanHeaderModel({
    referenceDate: '2026-05-30',
    weeklyPlan: {
      weekMeta: {
        weekNumber: 18,
        weekStart: '2026-04-27',
        weekEnd: '2026-05-03',
      },
    },
  })

  assert.deepEqual(headerModel.weekMeta, {
    source: 'weeklyPlan',
    weekNumber: 18,
    weekStart: '2026-04-27',
    weekEnd: '2026-05-03',
  })
  assert.equal(headerModel.weekRangeLabel, '2026年4月27日 - 5月3日')
  assert.equal(headerModel.weekBadgeLabel, '第 18 周')
})

test('buildPlanHeaderModel 在空计划下也会返回明确的计划设置占位说明', () => {
  const headerModel = buildPlanHeaderModel({
    referenceDate: '2026-05-30',
    weeklyPlan: null,
  })

  assert.deepEqual(headerModel.settingsButton, {
    label: '计划设置',
    hint: '当前仅保留训练计划设置入口，后续版本会接入周期模板与高级配置。',
    title: '计划设置（开发中）',
    description: '训练计划页头部暂时只保留一个统一入口，供后续接入计划模板、周期节奏和高级设置。',
    confirmLabel: '知道了',
    isPlaceholder: true,
  })
})

test('PlanTab 移除效果稿之外的说明文案并保留新的承载框架', () => {
  const planTabSource = readWorkspaceFile('src/tabs/PlanTab.jsx')

  assert.doesNotMatch(planTabSource, /fitloop_weeklyPlan/)
  assert.doesNotMatch(planTabSource, /这里可以直接维护一周训练计划/)
  assert.match(planTabSource, /<PlanHeaderToolbar headerModel=\{headerModel\} \/>/)
  assert.match(planTabSource, /rounded-\[1\.5rem\] border border-fitloop-line bg-white\/80 p-6/)
  assert.match(planTabSource, /rounded-\[1\.25rem\] border border-fitloop-line bg-white p-3/)
})

test('PlanHeaderToolbar 与 Legend 源码不再保留旧版卡片式头部痕迹', () => {
  const toolbarSource = readWorkspaceFile('src/components/plan-header/PlanHeaderToolbar.jsx')
  const legendSource = readWorkspaceFile('src/components/plan-header/PlanHeaderLegend.jsx')

  assert.match(toolbarSource, /本周训练计划/)
  assert.match(toolbarSource, /headerModel\.weekRangeLabel/)
  assert.match(toolbarSource, /headerModel\.weekBadgeLabel/)
  assert.match(toolbarSource, /headerModel\.viewTabs\.map/)
  assert.match(toolbarSource, /\{tab\.label\}/)
  assert.doesNotMatch(toolbarSource, /uppercase tracking-\[0\.16em\]/)
  assert.doesNotMatch(toolbarSource, /disabled/)
  assert.match(toolbarSource, /headerModel\.settingsButton\.label/)
  assert.match(toolbarSource, /headerModel\.settingsButton\.hint/)
  assert.match(legendSource, /item\.tone === 'main'/)
  assert.match(legendSource, /item\.tone === 'accessory'/)
})
