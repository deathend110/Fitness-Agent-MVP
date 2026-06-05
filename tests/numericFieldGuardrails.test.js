import test from 'node:test'
import assert from 'node:assert/strict'

import {
  NUMERIC_FIELD_GUARDRAILS,
  getNumericFieldGuardrail,
  validateNumericFieldValue,
  clampNumericInputDraft,
} from '../src/utils/numericFieldGuardrails.js'

test('共享规则层会暴露完整规则表，并返回档案体重和动作 RPE 的范围配置', () => {
  assert.equal(typeof NUMERIC_FIELD_GUARDRAILS, 'object')
  assert.equal(getNumericFieldGuardrail('profile.basic.weight').min, 25)
  assert.equal(getNumericFieldGuardrail('profile.basic.weight').max, 300)
  assert.equal(getNumericFieldGuardrail('plan.exercise.rpe').min, 0)
  assert.equal(getNumericFieldGuardrail('plan.exercise.rpe').max, 10)
  assert.equal(getNumericFieldGuardrail('unknown.field'), null)
})

test('validateNumericFieldValue 对空值放行，对合法值返回 null', () => {
  assert.equal(validateNumericFieldValue('today.weight', ''), null)
  assert.equal(validateNumericFieldValue('today.weight', '   '), null)
  assert.equal(validateNumericFieldValue('today.weight', '82.5'), null)
  assert.equal(validateNumericFieldValue('unknown.field', '9999'), null)
})

test('validateNumericFieldValue 对越界值返回稳定错误文案', () => {
  assert.equal(
    validateNumericFieldValue('today.weight', '9999'),
    '体重 必须在 25-300kg 之间',
  )
  assert.equal(
    validateNumericFieldValue('profile.oneRM.bench', '-1'),
    '卧推 1RM 必须在 5-400kg 之间',
  )
})

test('clampNumericInputDraft 会保留空串并拒绝越界输入进入下一草稿值', () => {
  assert.deepEqual(
    clampNumericInputDraft({
      fieldKey: 'plan.exercise.kg',
      previousValue: '100',
      nextValue: '',
    }),
    { nextValue: '', error: null },
  )

  assert.deepEqual(
    clampNumericInputDraft({
      fieldKey: 'plan.exercise.kg',
      previousValue: '100',
      nextValue: '120',
    }),
    { nextValue: '120', error: null },
  )

  assert.deepEqual(
    clampNumericInputDraft({
      fieldKey: 'plan.exercise.kg',
      previousValue: '100',
      nextValue: '100000',
    }),
    {
      nextValue: '100',
      error: '固定重量 必须在 0.5-500kg 之间',
    },
  )
})
