import test from 'node:test'
import assert from 'node:assert/strict'

import {
  NUMERIC_FIELD_GUARDRAILS,
  getNumericFieldGuardrail,
  validateNumericFieldValue,
  clampNumericInputDraft,
  getNumericFieldInputProps,
} from '../src/utils/numericFieldGuardrails.js'

test('共享规则层会暴露完整规则表，并返回档案体重和动作 RPE 的范围配置', () => {
  assert.equal(typeof NUMERIC_FIELD_GUARDRAILS, 'object')
  assert.equal(getNumericFieldGuardrail('profile.basic.weight').min, 25)
  assert.equal(getNumericFieldGuardrail('profile.basic.weight').max, 300)
  assert.equal(getNumericFieldGuardrail('plan.exercise.rpe').min, 0)
  assert.equal(getNumericFieldGuardrail('plan.exercise.rpe').max, 10)
  assert.equal(getNumericFieldGuardrail('unknown.field'), null)
})

test('共享规则层会提供可直接复用的输入约束，避免调用方手写 min/max/step', () => {
  assert.deepEqual(getNumericFieldInputProps('profile.basic.weight'), {
    min: 25,
    max: 300,
    step: 0.1,
    inputMode: null,
  })

  assert.deepEqual(getNumericFieldInputProps('today.fatigue'), {
    min: 1,
    max: 5,
    step: 1,
    inputMode: null,
  })

  assert.equal(getNumericFieldInputProps('unknown.field'), null)
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

test('validateNumericFieldValue 会拦截不符合 step 语义的最终值', () => {
  assert.equal(
    validateNumericFieldValue('today.fatigue', '3.5'),
    '疲劳度 必须按 1 的步长填写',
  )
  assert.equal(
    validateNumericFieldValue('today.kcal', '12.5'),
    '热量 必须按 1 的步长填写',
  )
  assert.equal(
    validateNumericFieldValue('plan.exercise.kg', '0.55'),
    '固定重量 必须按 0.5 的步长填写',
  )
})

test('validateNumericFieldValue 会拒绝科学计数法和进制字面量这类伪数字字符串', () => {
  assert.equal(
    validateNumericFieldValue('today.kcal', '1e3'),
    '热量 必须填写有效数字',
  )
  assert.equal(
    validateNumericFieldValue('profile.basic.age', '0x20'),
    '年龄 必须填写有效数字',
  )
  assert.equal(
    validateNumericFieldValue('today.weight', '0b1010000'),
    '体重 必须填写有效数字',
  )
})

test('共享规则表和单条规则对象是只读的，调用方无法篡改共享配置', () => {
  const originalMin = getNumericFieldGuardrail('plan.exercise.kg').min

  assert.throws(() => {
    NUMERIC_FIELD_GUARDRAILS['plan.exercise.kg'] = { label: '坏规则', min: -1, max: -1 }
  }, TypeError)

  assert.throws(() => {
    getNumericFieldGuardrail('plan.exercise.kg').min = 999999
  }, TypeError)

  assert.equal(getNumericFieldGuardrail('plan.exercise.kg').min, originalMin)
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

test('clampNumericInputDraft 会放行最终可达合法值的中间态输入', () => {
  assert.deepEqual(
    clampNumericInputDraft({
      fieldKey: 'profile.oneRM.squat',
      previousValue: '',
      nextValue: '1',
    }),
    { nextValue: '1', error: null },
  )

  assert.deepEqual(
    clampNumericInputDraft({
      fieldKey: 'plan.exercise.kg',
      previousValue: '',
      nextValue: '0',
    }),
    { nextValue: '0', error: null },
  )

  assert.deepEqual(
    clampNumericInputDraft({
      fieldKey: 'plan.exercise.kg',
      previousValue: '0',
      nextValue: '0.',
    }),
    { nextValue: '0.', error: null },
  )

  assert.deepEqual(
    clampNumericInputDraft({
      fieldKey: 'plan.exercise.kg',
      previousValue: '',
      nextValue: '.',
    }),
    { nextValue: '.', error: null },
  )

  assert.deepEqual(
    clampNumericInputDraft({
      fieldKey: 'plan.exercise.kg',
      previousValue: '.',
      nextValue: '.5',
    }),
    { nextValue: '.5', error: null },
  )
})

test('clampNumericInputDraft 不会把点号中间态误放开到不支持该路径的字段', () => {
  assert.deepEqual(
    clampNumericInputDraft({
      fieldKey: 'profile.oneRM.squat',
      previousValue: '',
      nextValue: '.',
    }),
    {
      nextValue: '',
      error: '深蹲 1RM 必须填写有效数字',
    },
  )
})

test('clampNumericInputDraft 会继续拦截明显不可能形成合法值的草稿', () => {
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
