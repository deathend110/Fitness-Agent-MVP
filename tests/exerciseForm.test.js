import assert from 'node:assert/strict'
import test from 'node:test'
import * as exerciseForm from '../src/utils/exerciseForm.js'

test('createExerciseDraft 会从结构化动作中带出层级、组型和次数表达', () => {
  const draft = exerciseForm.createExerciseDraft(
    {
      name: '深蹲',
      tier: 'main',
      ref1RM: 'squat',
      pct: 0.75,
      kg: null,
      sets: 4,
      reps: null,
      rpe: 8,
      note: '主项',
      template: {
        setType: 'custom',
        repsText: '6-8',
      },
    },
    'squat',
  )

  assert.equal(draft.tier, 'main')
  assert.equal(draft.setType, 'custom')
  assert.equal(draft.repsText, '6-8')
  assert.equal(draft.reps, '')
})

test('createExerciseDraft 会兼容 template.ref1RM 与旧版次数字段回填', () => {
  const draft = exerciseForm.createExerciseDraft(
    {
      name: '卧推',
      tier: 'accessory',
      pct: 0.72,
      kg: null,
      sets: 5,
      reps: 5,
      rpe: 7.5,
      note: '旧结构',
      template: {
        loadMode: 'percentage',
        ref1RM: 'bench',
        setType: 'straight',
        repsText: '5',
      },
    },
    'squat',
  )

  assert.equal(draft.weightMode, 'percentage')
  assert.equal(draft.ref1RM, 'bench')
  assert.equal(draft.reps, '5')
  assert.equal(draft.repsText, '5')
})

test('getRpeValidationError 会拦截 11 和 -1，并允许 0 和 10', () => {
  assert.equal(typeof exerciseForm.getRpeValidationError, 'function')
  assert.equal(exerciseForm.getRpeValidationError('11'), 'RPE 只能在 0-10 之间')
  assert.equal(exerciseForm.getRpeValidationError('-1'), 'RPE 只能在 0-10 之间')
  assert.equal(exerciseForm.getRpeValidationError('10'), null)
  assert.equal(exerciseForm.getRpeValidationError('0'), null)
})

test('buildExerciseSavePayload 会阻止非法 RPE 进入保存结果', () => {
  assert.equal(typeof exerciseForm.buildExerciseSavePayload, 'function')

  const validPayload = exerciseForm.buildExerciseSavePayload({
    name: '深蹲',
    weightMode: 'fixed',
    kg: '100',
    sets: '4',
    reps: '6',
    rpe: '10',
    note: '',
  })
  const zeroPayload = exerciseForm.buildExerciseSavePayload({
    name: '深蹲',
    weightMode: 'fixed',
    kg: '100',
    sets: '4',
    reps: '6',
    rpe: '0',
    note: '',
  })

  assert.equal(validPayload?.rpe, 10)
  assert.equal(zeroPayload?.rpe, 0)
  assert.equal(
    exerciseForm.buildExerciseSavePayload({
      name: '深蹲',
      weightMode: 'fixed',
      kg: '100',
      sets: '4',
      reps: '6',
      rpe: '11',
      note: '',
    }),
    null,
  )
  assert.equal(
    exerciseForm.buildExerciseSavePayload({
      name: '深蹲',
      weightMode: 'fixed',
      kg: '100',
      sets: '4',
      reps: '6',
      rpe: '-1',
      note: '',
    }),
    null,
  )
})

test('buildExerciseSavePayload 会保留层级、组型与次数表达字段', () => {
  const payload = exerciseForm.buildExerciseSavePayload({
    name: '深蹲',
    tier: 'main',
    weightMode: 'percentage',
    ref1RM: 'squat',
    pct: '0.75',
    kg: '',
    sets: '4',
    reps: '6',
    repsText: '6',
    setType: 'straight',
    rpe: '8',
    note: '主项',
  })

  assert.equal(payload?.tier, 'main')
  assert.equal(payload?.template?.setType, 'straight')
  assert.equal(payload?.template?.repsText, '6')
  assert.equal(payload?.reps, 6)
})

test('buildExerciseSavePayload 在自定义次数表达下会保留 repsText 并允许顶层 reps 为空', () => {
  const payload = exerciseForm.buildExerciseSavePayload({
    name: '卧推',
    tier: 'accessory',
    weightMode: 'fixed',
    ref1RM: 'bench',
    pct: '',
    kg: '72.5',
    sets: '3',
    reps: '',
    repsText: 'AMRAP',
    setType: 'custom',
    rpe: '',
    note: '',
  })

  assert.equal(payload?.tier, 'accessory')
  assert.equal(payload?.template?.setType, 'custom')
  assert.equal(payload?.template?.repsText, 'AMRAP')
  assert.equal(payload?.reps, null)
  assert.equal(payload?.kg, 72.5)
})

test('buildExerciseSavePayload 在自定义组型下会忽略陈旧的数字次数输入', () => {
  const payload = exerciseForm.buildExerciseSavePayload({
    name: '卧推',
    tier: 'main',
    weightMode: 'percentage',
    ref1RM: 'bench',
    pct: '0.8',
    kg: '',
    sets: '4',
    reps: '6',
    repsText: 'AMRAP',
    setType: 'custom',
    rpe: '9',
    note: '顶组',
  })

  assert.equal(payload?.template?.setType, 'custom')
  assert.equal(payload?.template?.repsText, 'AMRAP')
  assert.equal(payload?.reps, null)
})

test('getRpeFieldHint 会给出清晰的范围提示，并在出错时优先显示错误', () => {
  assert.equal(typeof exerciseForm.getRpeFieldHint, 'function')
  assert.equal(exerciseForm.getRpeFieldHint(null), 'RPE 请输入 0-10 之间的数值')
  assert.equal(exerciseForm.getRpeFieldHint('RPE 只能在 0-10 之间'), 'RPE 只能在 0-10 之间')
})
