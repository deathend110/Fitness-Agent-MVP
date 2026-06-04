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

test('PlanTab 源码包含手动周期设置流程的关键入口', () => {
  const source = readFileSync('src/tabs/PlanTab.jsx', 'utf-8')

  assert.match(source, /isPlanSettingsOpen/)
  assert.match(source, /planSource\.activeSource/)
  assert.match(source, /非周期计划/)
  assert.match(source, /周期计划/)
  assert.match(source, /getCyclePresets|createCyclePlan/)
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
