import assert from 'node:assert/strict'
import test from 'node:test'
import * as exerciseForm from '../src/utils/exerciseForm.js'

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

test('getRpeFieldHint 会给出清晰的范围提示，并在出错时优先显示错误', () => {
  assert.equal(typeof exerciseForm.getRpeFieldHint, 'function')
  assert.equal(exerciseForm.getRpeFieldHint(null), 'RPE 请输入 0-10 之间的数值')
  assert.equal(exerciseForm.getRpeFieldHint('RPE 只能在 0-10 之间'), 'RPE 只能在 0-10 之间')
})
