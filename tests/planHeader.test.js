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
  assert.equal(headerModel.settingsButton.isPlaceholder, false)
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

test('buildPlanHeaderModel 在 only weekStart 的旧周元数据下整体回退到当前自然周', () => {
  const headerModel = buildPlanHeaderModel({
    referenceDate: '2026-05-30',
    weeklyPlan: {
      weekMeta: {
        weekNumber: 18,
        weekStart: '2026-04-27',
      },
    },
  })

  assert.deepEqual(headerModel.weekMeta, {
    source: 'weeklyPlan',
    weekNumber: 18,
    weekStart: '2026-05-25',
    weekEnd: '2026-05-31',
  })
  assert.equal(headerModel.weekRangeLabel, '2026年5月25日 - 5月31日')
  assert.equal(headerModel.weekBadgeLabel, '第 18 周')
})

test('buildPlanHeaderModel 在 only weekEnd 的旧周元数据下整体回退到当前自然周', () => {
  const headerModel = buildPlanHeaderModel({
    referenceDate: '2026-05-30',
    weeklyPlan: {
      weekMeta: {
        weekNumber: 18,
        weekEnd: '2026-05-03',
      },
    },
  })

  assert.deepEqual(headerModel.weekMeta, {
    source: 'weeklyPlan',
    weekNumber: 18,
    weekStart: '2026-05-25',
    weekEnd: '2026-05-31',
  })
  assert.equal(headerModel.weekRangeLabel, '2026年5月25日 - 5月31日')
  assert.equal(headerModel.weekBadgeLabel, '第 18 周')
})

test('计划设置入口会返回真实按钮文案而不是开发中占位说明', () => {
  const headerModel = buildPlanHeaderModel({
    referenceDate: '2026-05-30',
    weeklyPlan: null,
  })

  assert.deepEqual(headerModel.settingsButton, {
    label: '计划设置',
    hint: '打开训练计划设置入口，切换手动计划与周期计划。',
    title: '训练计划设置',
    description: '进入训练计划设置入口，查看当前计划来源并管理周期计划配置。',
    confirmLabel: '打开设置',
    isPlaceholder: false,
  })
  assert.doesNotMatch(headerModel.settingsButton.title, /开发中/)
  assert.doesNotMatch(headerModel.settingsButton.description, /开发中/)
})

test('PlanTab 传给 buildPlanHeaderModel 的 referenceDate 必须是真实日期字符串而不是星期 key', () => {
  const planTabSource = readWorkspaceFile('src/tabs/PlanTab.jsx')

  assert.match(planTabSource, /const todayStr = getTodayStr\(\)/)
  assert.match(planTabSource, /referenceDate: todayStr/)
  assert.doesNotMatch(planTabSource, /referenceDate: getTodayKey\(\)/)
  assert.doesNotMatch(planTabSource, /getTodayKey/)
})

test('PlanTab 移除双层卡片承载框，只保留页面 header 加内容区结构', () => {
  const planTabSource = readWorkspaceFile('src/tabs/PlanTab.jsx')

  assert.doesNotMatch(planTabSource, /fitloop_weeklyPlan/)
  assert.doesNotMatch(planTabSource, /这里可以直接维护一周训练计划/)
  assert.match(planTabSource, /<PlanHeaderToolbar/)
  assert.match(planTabSource, /headerModel=\{headerModel\}/)
  assert.match(planTabSource, /onPlanSettingsClick=\{openPlanSettings\}/)
  assert.match(planTabSource, /onWeekNumberChange=\{handleWeekNumberChange\}/)
  assert.match(planTabSource, /<PlanWeekGrid/)
})

test('PlanHeaderToolbar 源码恢复效果稿的一行式结构与计划设置入口', () => {
  const toolbarSource = readWorkspaceFile('src/components/plan-header/PlanHeaderToolbar.jsx')

  assert.match(toolbarSource, /本周训练计划/)
  assert.match(toolbarSource, /headerModel\.weekRangeLabel/)
  assert.match(toolbarSource, /onWeekNumberChange/)
  assert.match(toolbarSource, /canEditWeekNumber/)
  assert.match(toolbarSource, /aria-label="编辑周数"/)
  assert.match(toolbarSource, /inputMode="numeric"/)
  assert.match(toolbarSource, /svg/)
  assert.match(toolbarSource, /M8 7V3m8 4V3m-9 8h10M5 21h14/)
  assert.match(toolbarSource, /lg:flex-row/)
  assert.match(toolbarSource, /items-center gap-6/)
  assert.match(toolbarSource, /headerModel\.viewTabs\.map/)
  assert.match(toolbarSource, /<PlanHeaderLegend items=\{headerModel\.legendItems\} \/>/)
  assert.match(toolbarSource, /headerModel\.settingsButton\.label/)
  assert.match(toolbarSource, /onPlanSettingsClick/)
  assert.match(toolbarSource, /onClick=\{onPlanSettingsClick\}/)
  assert.doesNotMatch(toolbarSource, /flex-col gap-3 lg:items-end/)
  assert.doesNotMatch(toolbarSource, /w-fit/)
})

test('PlanHeaderToolbar 源码接入周数 guardrail 并限制提交非法值', () => {
  const toolbarSource = readWorkspaceFile('src/components/plan-header/PlanHeaderToolbar.jsx')

  assert.match(toolbarSource, /getNumericFieldGuardrail/)
  assert.match(toolbarSource, /validateNumericFieldValue/)
  assert.match(toolbarSource, /plan\.weekMeta\.weekNumber/)
  assert.match(toolbarSource, /disabled=\{!canEditWeekNumber\}/)
  assert.match(toolbarSource, /if \(!canEditWeekNumber\) \{\s*return\s*\}/)
  assert.match(toolbarSource, /min=\{weekNumberGuardrail\.min\}/)
  assert.match(toolbarSource, /max=\{weekNumberGuardrail\.max\}/)
  assert.match(toolbarSource, /step=\{weekNumberGuardrail\.step\}/)
  assert.match(toolbarSource, /commitWeekNumber/)
  assert.match(
    toolbarSource,
    /hasStrictIntegerFormat/,
  )
  assert.match(
    toolbarSource,
    /validateNumericFieldValue\('plan\.weekMeta\.weekNumber', normalizedWeekNumber\)/,
  )
})

test('PlanHeaderLegend 继续保持主项与辅项的横排图例点样式', () => {
  const legendSource = readWorkspaceFile('src/components/plan-header/PlanHeaderLegend.jsx')

  assert.match(legendSource, /item\.tone === 'main'/)
  assert.match(legendSource, /item\.tone === 'accessory'/)
  assert.match(legendSource, /flex-wrap items-center gap-4/)
})

test('PlanTab 在周期覆盖模式下会把周次徽标降级为只读展示，避免输入后回弹', () => {
  const planTabSource = readWorkspaceFile('src/tabs/PlanTab.jsx')

  assert.match(planTabSource, /function isCycleOverrideMode\(\)/)
  assert.match(planTabSource, /if \(isCycleOverrideMode\(\)\) \{\s*return\s*\}/)
  assert.match(planTabSource, /canEditWeekNumber=\{!isCycleOverrideMode\(\)\}/)
})
