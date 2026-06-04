import assert from 'node:assert/strict'
import test from 'node:test'
import { readFileSync } from 'node:fs'

test('PlanSettingsPanel 会挂载自定义力量编辑器入口与创建动作文案', () => {
  const source = readFileSync('src/components/plan-settings/PlanSettingsPanel.jsx', 'utf-8')

  assert.match(source, /自定义力量周期计划/)
  assert.match(source, /CustomStrengthPlanEditor/)
  assert.match(source, /创建自定义力量周期计划/)
})

test('PlanTab 会把 custom strength 草稿与 preset 周期草稿拆开编排', () => {
  const source = readFileSync('src/tabs/PlanTab.jsx', 'utf-8')

  assert.match(source, /customStrengthDraft/)
  assert.match(source, /createCustomStrengthDraft/)
  assert.match(source, /buildCreateCustomStrengthCyclePayload/)
  assert.match(source, /function handleCreateCustomStrengthCyclePlan\(/)
})
