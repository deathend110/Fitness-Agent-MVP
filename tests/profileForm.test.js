import test from 'node:test'
import assert from 'node:assert/strict'

import {
  basicFields,
  draftToProfile,
  oneRmFields,
  targetWeightField,
} from '../src/utils/profileForm.js'

test('draftToProfile 会把越界档案数值转成 null，避免非法业务值落库', () => {
  const profile = draftToProfile({
    basic: {
      name: 'A',
      sex: 'male',
      age: '999',
      height: '9999',
      weight: '-1',
      waist: '300',
    },
    oneRM: {
      squat: '100000',
      bench: '-1',
      deadlift: '600',
    },
    goal: '',
    targetWeight: '9999',
    notes: '',
  })

  assert.equal(profile.basic.age, null)
  assert.equal(profile.basic.height, null)
  assert.equal(profile.basic.weight, null)
  assert.equal(profile.basic.waist, null)
  assert.equal(profile.oneRM.squat, null)
  assert.equal(profile.oneRM.bench, null)
  assert.equal(profile.oneRM.deadlift, null)
  assert.equal(profile.targetWeight, null)
})

test('draftToProfile 会保留空值并透传合法档案数值', () => {
  const profile = draftToProfile({
    basic: {
      name: 'B',
      sex: 'female',
      age: '',
      height: '165.5',
      weight: '60.2',
      waist: '',
    },
    oneRM: {
      squat: '140',
      bench: '',
      deadlift: '180',
    },
    goal: 'cut',
    targetWeight: '',
    notes: 'ok',
  })

  assert.deepEqual(profile, {
    basic: {
      name: 'B',
      sex: 'female',
      age: null,
      height: 165.5,
      weight: 60.2,
      waist: null,
    },
    oneRM: {
      squat: 140,
      bench: null,
      deadlift: 180,
    },
    goal: 'cut',
    targetWeight: null,
    notes: 'ok',
  })
})

test('profileForm 的数值字段配置会直接携带 guardrailKey，避免页面层重复手写映射', () => {
  assert.deepEqual(
    basicFields
      .filter((field) => field.type === 'number')
      .map((field) => ({ key: field.key, guardrailKey: field.guardrailKey })),
    [
      { key: 'age', guardrailKey: 'profile.basic.age' },
      { key: 'height', guardrailKey: 'profile.basic.height' },
      { key: 'weight', guardrailKey: 'profile.basic.weight' },
      { key: 'waist', guardrailKey: 'profile.basic.waist' },
    ],
  )

  assert.deepEqual(
    oneRmFields.map((field) => ({ key: field.key, guardrailKey: field.guardrailKey })),
    [
      { key: 'squat', guardrailKey: 'profile.oneRM.squat' },
      { key: 'bench', guardrailKey: 'profile.oneRM.bench' },
      { key: 'deadlift', guardrailKey: 'profile.oneRM.deadlift' },
    ],
  )
})

test('draftToProfile 会把 step 不合法的最终值转成 null，同时保留合法值和空值', () => {
  const profile = draftToProfile({
    basic: {
      name: 'C',
      sex: 'male',
      age: '30.5',
      height: '165.5',
      weight: '',
      waist: '80.05',
    },
    oneRM: {
      squat: '140.25',
      bench: '100',
      deadlift: '',
    },
    goal: '',
    targetWeight: '70.05',
    notes: '',
  })

  assert.deepEqual(profile, {
    basic: {
      name: 'C',
      sex: 'male',
      age: null,
      height: 165.5,
      weight: null,
      waist: null,
    },
    oneRM: {
      squat: null,
      bench: 100,
      deadlift: null,
    },
    goal: '',
    targetWeight: null,
    notes: '',
  })
})

test('draftToProfile 会拒绝科学计数法和进制字面量，避免伪数字绕过档案保存', () => {
  const profile = draftToProfile({
    basic: {
      name: 'D',
      sex: 'male',
      age: '0x20',
      height: '1e2',
      weight: '0b1010000',
      waist: '80',
    },
    oneRM: {
      squat: '140',
      bench: '0x64',
      deadlift: '180',
    },
    goal: '',
    targetWeight: '7e1',
    notes: '',
  })

  assert.deepEqual(profile, {
    basic: {
      name: 'D',
      sex: 'male',
      age: null,
      height: null,
      weight: null,
      waist: 80,
    },
    oneRM: {
      squat: 140,
      bench: null,
      deadlift: 180,
    },
    goal: '',
    targetWeight: null,
    notes: '',
  })
})

test('draftToProfile 会接受尾随小数点格式，避免保存时误清空合法档案草稿', () => {
  const profile = draftToProfile({
    basic: {
      name: 'E',
      sex: 'female',
      age: '30',
      height: '165.',
      weight: '60.',
      waist: '80.',
    },
    oneRM: {
      squat: '140.',
      bench: '100.',
      deadlift: '180.',
    },
    goal: '',
    targetWeight: '58.',
    notes: '',
  })

  assert.deepEqual(profile, {
    basic: {
      name: 'E',
      sex: 'female',
      age: 30,
      height: 165,
      weight: 60,
      waist: 80,
    },
    oneRM: {
      squat: 140,
      bench: 100,
      deadlift: 180,
    },
    goal: '',
    targetWeight: 58,
    notes: '',
  })
})

test('profileForm 的共享字段配置会暴露输入约束，避免页面层继续手写 step min max', () => {
  assert.deepEqual(
    basicFields
      .filter((field) => field.type === 'number')
      .map((field) => ({ key: field.key, min: field.min, max: field.max, step: field.step })),
    [
      { key: 'age', min: 12, max: 100, step: 1 },
      { key: 'height', min: 120, max: 250, step: 0.1 },
      { key: 'weight', min: 25, max: 300, step: 0.1 },
      { key: 'waist', min: 40, max: 200, step: 0.1 },
    ],
  )

  assert.deepEqual(
    { min: targetWeightField.min, max: targetWeightField.max, step: targetWeightField.step },
    { min: 25, max: 300, step: 0.1 },
  )

  assert.deepEqual(
    oneRmFields.map((field) => ({ key: field.key, min: field.min, max: field.max, step: field.step })),
    [
      { key: 'squat', min: 10, max: 500, step: 0.1 },
      { key: 'bench', min: 5, max: 400, step: 0.1 },
      { key: 'deadlift', min: 10, max: 500, step: 0.1 },
    ],
  )
})
