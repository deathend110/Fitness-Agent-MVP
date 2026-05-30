import test from 'node:test'
import assert from 'node:assert/strict'
import { demoWeeklyPlan } from '../src/utils/defaultData.js'
import {
  addExerciseToDay,
  removeExerciseFromDay,
  updateDayType,
  updateExerciseInDay,
} from '../src/utils/weeklyPlan.js'

test('updateDayType 将某天改成 rest 时保留原有动作', () => {
  const nextPlan = updateDayType(demoWeeklyPlan, 'Monday', 'rest')

  assert.equal(nextPlan.Monday.type, 'rest')
  assert.equal(nextPlan.Monday.exercises.length, demoWeeklyPlan.Monday.exercises.length)
  assert.deepEqual(nextPlan.Tuesday, demoWeeklyPlan.Tuesday)
})

test('addExerciseToDay 新增百分比动作时会生成 id 且 kg 为 null', () => {
  const nextPlan = addExerciseToDay(demoWeeklyPlan, 'Tuesday', {
    name: '深蹲',
    ref1RM: 'squat',
    pct: 0.75,
    kg: null,
    sets: 4,
    reps: 6,
    rpe: null,
    note: '主项',
  })

  const addedExercise = nextPlan.Tuesday.exercises.at(-1)

  assert.ok(addedExercise.id)
  assert.equal(addedExercise.ref1RM, 'squat')
  assert.equal(addedExercise.pct, 0.75)
  assert.equal(addedExercise.kg, null)
})

test('addExerciseToDay 新增固定重量动作时会清空 ref1RM 和 pct', () => {
  const nextPlan = addExerciseToDay(demoWeeklyPlan, 'Tuesday', {
    name: '罗马尼亚硬拉',
    ref1RM: null,
    pct: null,
    kg: 80,
    sets: 3,
    reps: 10,
    rpe: 8,
    note: '',
  })

  const addedExercise = nextPlan.Tuesday.exercises.at(-1)

  assert.ok(addedExercise.id)
  assert.equal(addedExercise.ref1RM, null)
  assert.equal(addedExercise.pct, null)
  assert.equal(addedExercise.kg, 80)
})

test('updateExerciseInDay 只更新目标日期中的目标动作', () => {
  const nextPlan = updateExerciseInDay(demoWeeklyPlan, 'Monday', 'monday-squat', {
    id: 'monday-squat',
    name: '暂停深蹲',
    ref1RM: 'squat',
    pct: 0.7,
    kg: null,
    sets: 5,
    reps: 4,
    rpe: 8,
    note: '次主项',
  })

  assert.equal(nextPlan.Monday.exercises[0].name, '暂停深蹲')
  assert.equal(nextPlan.Monday.exercises[0].kg, null)
  assert.equal(nextPlan.Monday.exercises[0].pct, 0.7)
  assert.equal(nextPlan.Wednesday.exercises[0].name, demoWeeklyPlan.Wednesday.exercises[0].name)
})

test('removeExerciseFromDay 删除动作时不会影响其他日期', () => {
  const nextPlan = removeExerciseFromDay(demoWeeklyPlan, 'Monday', 'monday-rdl')

  assert.equal(nextPlan.Monday.exercises.some((exercise) => exercise.id === 'monday-rdl'), false)
  assert.equal(nextPlan.Monday.exercises.length, demoWeeklyPlan.Monday.exercises.length - 1)
  assert.equal(nextPlan.Friday.exercises.length, demoWeeklyPlan.Friday.exercises.length)
})
