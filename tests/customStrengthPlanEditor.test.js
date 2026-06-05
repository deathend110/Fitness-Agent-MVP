import assert from 'node:assert/strict'
import test from 'node:test'
import { readFileSync } from 'node:fs'
import { shouldDisableCustomStrengthCreate } from '../src/components/plan-settings/customStrengthPlanEditorState.js'

test('PlanSettingsPanel 会挂载自定义力量编辑器入口与创建动作文案', () => {
  const source = readFileSync('src/components/plan-settings/PlanSettingsPanel.jsx', 'utf-8')

  assert.match(source, /自定义力量周期计划/)
  assert.match(source, /CustomStrengthPlanEditor/)
  assert.match(source, /创建自定义力量周期计划/)
  assert.match(source, /canCreate=\{settingsStatus\.canCreateCycle\}/)
})

test('PlanTab 会把 custom strength 草稿与 preset 周期草稿拆开编排', () => {
  const source = readFileSync('src/tabs/PlanTab.jsx', 'utf-8')

  assert.match(source, /customStrengthDraft/)
  assert.match(source, /buildCreateCyclePlanPayload\(cycleDraft\)/)
  assert.match(source, /createCustomStrengthDraft/)
  assert.match(source, /buildCreateCustomStrengthCyclePayload/)
  assert.match(source, /buildCreateCustomStrengthCyclePayload\(customStrengthDraft\)/)
  assert.match(source, /function handleCreateCustomStrengthCyclePlan\(/)
})

test('shouldDisableCustomStrengthCreate 会在不可创建时禁用按钮', () => {
  assert.equal(
    shouldDisableCustomStrengthCreate({
      canCreate: false,
      isSubmitting: false,
    }),
    true,
  )
})

test('shouldDisableCustomStrengthCreate 会在提交中时禁用按钮', () => {
  assert.equal(
    shouldDisableCustomStrengthCreate({
      canCreate: true,
      isSubmitting: true,
    }),
    true,
  )
})

test('shouldDisableCustomStrengthCreate 会在允许创建且未提交时启用按钮', () => {
  assert.equal(
    shouldDisableCustomStrengthCreate({
      canCreate: true,
      isSubmitting: false,
    }),
    false,
  )
})

test('CustomStrengthPlanEditor 源码会复用禁用判定 helper', () => {
  const source = readFileSync('src/components/plan-settings/CustomStrengthPlanEditor.jsx', 'utf-8')

  assert.match(source, /shouldDisableCustomStrengthCreate/)
  assert.match(source, /创建自定义力量周期计划/)
})
