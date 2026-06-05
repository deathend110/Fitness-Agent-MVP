import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

import {
  buildProfileSummaryCards,
  getProfileFieldHint,
} from '../src/utils/profileView.js'

test('buildProfileSummaryCards 会基于现有档案字段生成四张中性事实摘要卡', () => {
  const cards = buildProfileSummaryCards({
    basic: {
      weight: 82.4,
      waist: 86,
    },
    targetWeight: 78,
    goal: '增肌同时控制体脂',
  })

  assert.deepEqual(cards, [
    {
      key: 'weight',
      label: '当前体重',
      value: '82.4 kg',
      hint: '当前记录',
    },
    {
      key: 'targetWeight',
      label: '目标体重',
      value: '78 kg',
      hint: '目标值',
    },
    {
      key: 'waist',
      label: '腰围',
      value: '86 cm',
      hint: '围度记录',
    },
    {
      key: 'goal',
      label: '训练目标',
      value: '增肌同时控制体脂',
      hint: '当前方向',
    },
  ])
})

test('buildProfileSummaryCards 在字段为空时返回统一占位文案', () => {
  const cards = buildProfileSummaryCards({
    basic: {},
    targetWeight: null,
    goal: '',
  })

  assert.deepEqual(
    cards.map((card) => card.value),
    ['未填写', '未填写', '未填写', '未填写'],
  )
})

test('getProfileFieldHint 会为关键字段提供稳定单位提示', () => {
  assert.equal(getProfileFieldHint('height'), '单位 cm')
  assert.equal(getProfileFieldHint('weight'), '单位 kg')
  assert.equal(getProfileFieldHint('waist'), '单位 cm')
  assert.equal(getProfileFieldHint('targetWeight'), '目标体重，单位 kg')
  assert.equal(getProfileFieldHint('goal'), '例如减脂、增肌或力量提升')
  assert.equal(getProfileFieldHint('notes'), '记录补充信息，例如伤病或训练限制')
})

test('ProfileTab 源码包含摘要区、分组表单和默认收起的数据管理区', () => {
  const source = readFileSync('src/tabs/ProfileTab.jsx', 'utf-8')

  assert.match(source, /buildProfileSummaryCards/)
  assert.match(source, /基础资料/)
  assert.match(source, /目标与状态/)
  assert.match(source, /力量基础/)
  assert.match(source, /数据管理/)
  assert.match(source, /isDataPanelOpen/)
  assert.match(source, /aria-expanded=/)
})

test('ProfileTab 源码为档案页定义浅色渐变头图和分色摘要卡', () => {
  const source = readFileSync('src/tabs/ProfileTab.jsx', 'utf-8')

  assert.match(source, /from-\[#fdfdff\] via-\[#f6f8ff\] to-\[#eef4ff\]/)
  assert.match(source, /card\.tone/)
  assert.match(source, /border-sky-200\/70/)
  assert.match(source, /border-emerald-200\/70/)
  assert.match(source, /border-violet-200\/70/)
  assert.match(source, /border-amber-200\/80/)
})

test('ProfileTab 源码会复用共享 targetWeight 与 1RM 字段配置，而不是继续手写 step 和边界', () => {
  const source = readFileSync('src/tabs/ProfileTab.jsx', 'utf-8')

  assert.match(source, /targetWeightField/)
  assert.match(source, /min=\{targetWeightField\.min\}/)
  assert.match(source, /max=\{targetWeightField\.max\}/)
  assert.match(source, /step=\{targetWeightField\.step\}/)
  assert.match(source, /inputMode=\{targetWeightField\.inputMode\}/)
  assert.match(source, /min=\{field\.min\}/)
  assert.match(source, /max=\{field\.max\}/)
  assert.match(source, /step=\{field\.step\}/)
})

test('PlanTab 源码包含手动周期设置流程的关键入口', () => {
  const source = readFileSync('src/tabs/PlanTab.jsx', 'utf-8')

  assert.match(source, /isPlanSettingsOpen/)
  assert.match(source, /planSettingsMode/)
  assert.match(source, /planSource\.activeSource/)
  assert.match(source, /非周期计划/)
  assert.match(source, /周期计划/)
  assert.match(source, /getCyclePresets|createCyclePlan/)
  assert.match(source, /customStrengthDraft/)
  assert.match(source, /handleCreateCustomStrengthCyclePlan/)
  assert.match(source, /生成下一周|确认进入下一周|停止周期/)
})

test('PlanTab 源码在周期来源下会走当前周 override 更新链路', () => {
  const source = readFileSync('src/tabs/PlanTab.jsx', 'utf-8')

  assert.match(source, /planSource\.activeSource === 'cycle'/)
  assert.match(source, /activeCyclePlan\?\.cycle\?\.id/)
  assert.match(source, /activeCyclePlan\?\.cycle\?\.currentWeekIndex/)
  assert.match(source, /backendClient\.updateCycleWeekOverride/)
  assert.match(source, /onEffectiveWeeklyPlanChange\?\.\(/)
})

test('PlanTab 源码在手动来源下仍保留 onWeeklyPlanChange 更新链路', () => {
  const source = readFileSync('src/tabs/PlanTab.jsx', 'utf-8')

  assert.match(source, /if \(!isCycleOverrideMode\(\)\) \{/)
  assert.match(source, /onWeeklyPlanChange\(planUpdater\)/)
  assert.match(source, /if \(isCycleOverrideMode\(\)\) \{\s*return/)
  assert.match(source, /weekMeta/)
})

test('PlanTab 生成下一周后会重新读取 active cycle detail，而不是把 snapshot 直接写进 activeCyclePlan', () => {
  const source = readFileSync('src/tabs/PlanTab.jsx', 'utf-8')

  assert.match(source, /await backendClient\.generateNextCycleWeek\(activeCyclePlan\.cycle\.id\)/)
  assert.match(source, /const nextActiveCyclePlan = await backendClient\.getActiveCyclePlan\(\)/)
})

test('PlanTab 在尚未创建活动周期时会回退显示手动周计划', () => {
  const source = readFileSync('src/tabs/PlanTab.jsx', 'utf-8')

  assert.match(source, /const hasActiveCycle = Number\.isInteger\(activeCyclePlan\?\.cycle\?\.id\)/)
  assert.match(
    source,
    /planSource\.activeSource === 'cycle' && hasActiveCycle && effectiveWeeklyPlan/,
  )
})

test('PlanTab 创建周期计划后会保留完整 active cycle detail，避免把 response.cycle 内层对象误当成页面状态', () => {
  const source = readFileSync('src/tabs/PlanTab.jsx', 'utf-8')

  assert.match(source, /function buildNextActiveCyclePayload\(response\) \{/)
  assert.match(source, /if \(response\?\.activeCyclePlan\) \{/)
  assert.match(source, /if \(response\?\.currentWeek \|\| response\?\.effectivePlan\) \{/)
  assert.match(source, /return response \?\? null/)
  assert.doesNotMatch(source, /return response\?\.activeCyclePlan \?\? response\?\.cycle \?\? response \?\? null/)
  assert.match(source, /const nextActiveCyclePlan = buildNextActiveCyclePayload\(response\)/)
  assert.match(source, /const nextEffectivePlan = readNextEffectivePlan\(response\)/)
  assert.match(source, /onPlanSourceChange\?\.\(\{ activeSource: 'cycle' \}\)/)
  assert.match(source, /onActiveCyclePlanChange\?\.\(nextActiveCyclePlan\)/)
  assert.match(source, /if \(nextEffectivePlan\) \{\s*onEffectiveWeeklyPlanChange\?\.\(nextEffectivePlan\)/)
})

test('PlanTab 源码会把设置页模式与真实计划来源拆开，并通过后端接口显式切换真实来源', () => {
  const source = readFileSync('src/tabs/PlanTab.jsx', 'utf-8')

  assert.match(source, /resolvePlanSettingsMode/)
  assert.match(source, /setPlanSettingsMode/)
  assert.match(source, /function handleSelectPlanSettingsMode/)
  assert.match(source, /backendClient\.updatePlanSource\(\{ activeSource: 'manual' \}\)/)
  assert.match(source, /backendClient\.updatePlanSource\(\{ activeSource: 'cycle' \}\)/)
  assert.match(source, /buildCycleSettingsStatus/)
})
