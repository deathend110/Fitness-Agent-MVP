import test from 'node:test'
import assert from 'node:assert/strict'
import { demoWeeklyPlan } from '../src/utils/defaultData.js'
import {
  addExerciseToDay,
  getPlanDayTypes,
  getPlanDayTypeSuggestions,
  normalizeWeeklyPlan,
  removeExerciseFromDay,
  updateDayType,
  updateExerciseInDay,
} from '../src/utils/weeklyPlan.js'

test('updateDayType 切换到 rest 时保留原有动作', () => {
  const nextPlan = updateDayType(demoWeeklyPlan, 'Monday', 'rest')

  assert.equal(nextPlan.Monday.type, 'rest')
  assert.equal(nextPlan.Monday.exercises.length, demoWeeklyPlan.Monday.exercises.length)
  assert.deepEqual(nextPlan.Tuesday, demoWeeklyPlan.Tuesday)
})

test('updateDayType 遇到空字符串或纯空白时回退到 rest 并保留动作', () => {
  const weeklyPlan = {
    ...demoWeeklyPlan,
    Monday: {
      type: '',
      exercises: demoWeeklyPlan.Monday.exercises,
    },
  }

  const nextPlan = updateDayType(weeklyPlan, 'Monday', '   ')

  assert.equal(nextPlan.Monday.type, 'rest')
  assert.equal(nextPlan.Monday.exercises.length, demoWeeklyPlan.Monday.exercises.length)
})

test('updateDayType 会把损坏的单日计划恢复为默认结构', () => {
  const nextPlan = updateDayType(
    {
      ...demoWeeklyPlan,
      Monday: null,
    },
    'Monday',
    '',
  )

  assert.equal(nextPlan.Monday.type, 'rest')
  assert.deepEqual(nextPlan.Monday.exercises, [])
})

test('updateDayType 会保留自定义训练类型', () => {
  const nextPlan = updateDayType(demoWeeklyPlan, 'Monday', 'upper body strength')

  assert.equal(nextPlan.Monday.type, 'upper body strength')
  assert.equal(nextPlan.Monday.exercises.length, demoWeeklyPlan.Monday.exercises.length)
})

test('updateDayType 会保留旧枚举训练类型', () => {
  const nextPlan = updateDayType(demoWeeklyPlan, 'Monday', '腿日')

  assert.equal(nextPlan.Monday.type, '腿日')
  assert.equal(nextPlan.Monday.exercises.length, demoWeeklyPlan.Monday.exercises.length)
})

test('getPlanDayTypes 提供默认训练类型快捷选项', () => {
  assert.deepEqual(getPlanDayTypes(), ['腿日', '推日', '拉日', '有氧', 'rest'])
})

test('getPlanDayTypeSuggestions 会把当前自定义类型补进快捷候选', () => {
  assert.deepEqual(getPlanDayTypeSuggestions('upper body strength'), [
    '腿日',
    '推日',
    '拉日',
    '有氧',
    'rest',
    'upper body strength',
  ])
})

test('getPlanDayTypeSuggestions 会忽略空白当前类型', () => {
  assert.deepEqual(getPlanDayTypeSuggestions('   '), ['腿日', '推日', '拉日', '有氧', 'rest'])
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
  assert.equal(addedExercise.tier, 'main')
  assert.equal(addedExercise.template.loadMode, 'percentage')
  assert.equal(addedExercise.template.setType, 'straight')
  assert.equal(addedExercise.template.sets, 4)
  assert.equal(addedExercise.template.repsText, '6')
  assert.equal(addedExercise.instance.pct, 0.75)
  assert.equal(addedExercise.instance.kg, null)
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

test('addExerciseToDay 会把非法 RPE 归一化为 null', () => {
  const nextPlan = addExerciseToDay(demoWeeklyPlan, 'Tuesday', {
    name: '深蹲',
    ref1RM: 'squat',
    pct: 0.75,
    kg: null,
    sets: 4,
    reps: 6,
    rpe: 11,
    note: '主项',
  })

  const addedExercise = nextPlan.Tuesday.exercises.at(-1)

  assert.equal(addedExercise.rpe, null)
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
  assert.equal(nextPlan.Monday.exercises[0].tier, 'main')
  assert.equal(nextPlan.Monday.exercises[0].template.repsText, '4')
  assert.equal(nextPlan.Monday.exercises[0].instance.pct, 0.7)
  assert.equal(nextPlan.Monday.exercises[0].instance.rpe, 8)
  assert.equal(nextPlan.Wednesday.exercises[0].name, demoWeeklyPlan.Wednesday.exercises[0].name)
})

test('updateExerciseInDay 会把非法 RPE 归一化为 null', () => {
  const nextPlan = updateExerciseInDay(demoWeeklyPlan, 'Monday', 'monday-squat', {
    id: 'monday-squat',
    name: '暂停深蹲',
    ref1RM: 'squat',
    pct: 0.7,
    kg: null,
    sets: 5,
    reps: 4,
    rpe: -1,
    note: '次主项',
  })

  assert.equal(nextPlan.Monday.exercises[0].rpe, null)
})

test('removeExerciseFromDay 删除动作时不会影响其他日期', () => {
  const nextPlan = removeExerciseFromDay(demoWeeklyPlan, 'Monday', 'monday-rdl')

  assert.equal(nextPlan.Monday.exercises.some((exercise) => exercise.id === 'monday-rdl'), false)
  assert.equal(nextPlan.Monday.exercises.length, demoWeeklyPlan.Monday.exercises.length - 1)
  assert.equal(nextPlan.Friday.exercises.length, demoWeeklyPlan.Friday.exercises.length)
})

test('normalizeWeeklyPlan 会把旧结构动作升级为结构化字段并补齐 7 天', () => {
  const normalizedPlan = normalizeWeeklyPlan({
    weekMeta: {
      weekNumber: 22,
      weekStart: '2026-05-25',
      weekEnd: '2026-05-31',
    },
    Monday: {
      type: '腿日',
      exercises: [
        {
          id: 'legacy-squat',
          name: '深蹲',
          ref1RM: 'squat',
          pct: 0.8,
          kg: null,
          sets: 5,
          reps: 3,
          rpe: 8,
          note: '主项',
        },
      ],
    },
  })

  assert.equal(normalizedPlan.Monday.exercises[0].tier, 'main')
  assert.equal(normalizedPlan.Monday.exercises[0].template.loadMode, 'percentage')
  assert.equal(normalizedPlan.Monday.exercises[0].template.repsText, '3')
  assert.equal(normalizedPlan.Monday.exercises[0].instance.pct, 0.8)
  assert.equal(normalizedPlan.Monday.exercises[0].instance.note, '主项')
  assert.deepEqual(normalizedPlan.weekMeta, {
    weekNumber: 22,
    weekStart: '2026-05-25',
    weekEnd: '2026-05-31',
  })
  assert.deepEqual(normalizedPlan.Sunday, { type: 'rest', exercises: [] })
})

test('updateDayType 在写回时会保留周元信息，避免真实周计划刷新后丢失日期锚点', () => {
  const nextPlan = updateDayType(
    {
      weekMeta: {
        weekNumber: 22,
        weekStart: '2026-05-25',
        weekEnd: '2026-05-31',
      },
      Monday: { type: '腿日', exercises: [] },
    },
    'Monday',
    'rest',
  )

  assert.deepEqual(nextPlan.weekMeta, {
    weekNumber: 22,
    weekStart: '2026-05-25',
    weekEnd: '2026-05-31',
  })
  assert.equal(nextPlan.Monday.type, 'rest')
})
