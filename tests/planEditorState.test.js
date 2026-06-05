import assert from 'node:assert/strict'
import test from 'node:test'
import {
  canReorderPlanDayExercises,
  NEW_PLAN_EXERCISE_ID,
  clearPlanEditorState,
  clearPlanEditorStateAfterDelete,
  executePlanExerciseMenuAction,
  getPlanExerciseMenuActions,
  isPlanEditorTarget,
  startAddingExercise,
  startEditingExercise,
  updatePlanEditorDraft,
} from '../src/utils/planEditorState.js'
import { addExerciseToDay, removeExerciseFromDay, updateExerciseInDay } from '../src/utils/weeklyPlan.js'
import { demoWeeklyPlan } from '../src/utils/defaultData.js'

test('startAddingExercise 会为指定日期初始化新增动作草稿', () => {
  const state = startAddingExercise('Monday', [{ value: 'bench', label: '卧推 100kg' }])

  assert.equal(state.dayKey, 'Monday')
  assert.equal(state.exerciseId, NEW_PLAN_EXERCISE_ID)
  assert.equal(state.draft.name, '')
  assert.equal(state.draft.ref1RM, 'bench')
})

test('startEditingExercise 会锁定当前日期下的目标动作', () => {
  const state = startEditingExercise(
    'Wednesday',
    {
      id: 'wed-bench',
      name: '卧推',
      tier: 'main',
      ref1RM: 'bench',
      pct: 0.8,
      kg: null,
      sets: 5,
      reps: 4,
      rpe: 8,
      note: '顶组',
    },
    [{ value: 'squat', label: '深蹲 140kg' }],
  )

  assert.equal(state.dayKey, 'Wednesday')
  assert.equal(state.exerciseId, 'wed-bench')
  assert.equal(state.draft.name, '卧推')
  assert.equal(state.draft.weightMode, 'percentage')
  assert.equal(state.draft.pct, '0.8')
})

test('updatePlanEditorDraft 会保留目标定位并仅替换草稿', () => {
  const currentState = startAddingExercise('Friday', [{ value: 'deadlift', label: '硬拉 180kg' }])
  const nextState = updatePlanEditorDraft(currentState, {
    ...currentState.draft,
    name: '罗马尼亚硬拉',
  })

  assert.equal(nextState.dayKey, 'Friday')
  assert.equal(nextState.exerciseId, NEW_PLAN_EXERCISE_ID)
  assert.equal(nextState.draft.name, '罗马尼亚硬拉')
})

test('clearPlanEditorStateAfterDelete 只会在删除当前目标动作时清空编辑态', () => {
  const currentState = startEditingExercise(
    'Monday',
    {
      id: 'monday-squat',
      name: '深蹲',
      ref1RM: 'squat',
      pct: 0.75,
      kg: null,
      sets: 4,
      reps: 6,
      rpe: 8,
      note: '',
    },
    [{ value: 'squat', label: '深蹲 140kg' }],
  )

  assert.deepEqual(
    clearPlanEditorStateAfterDelete(currentState, 'Tuesday', 'monday-squat'),
    currentState,
  )
  assert.deepEqual(
    clearPlanEditorStateAfterDelete(currentState, 'Monday', 'other-exercise'),
    currentState,
  )
  assert.deepEqual(clearPlanEditorStateAfterDelete(currentState, 'Monday', 'monday-squat'), {
    dayKey: null,
    exerciseId: null,
    draft: null,
  })
})

test('isPlanEditorTarget 会同时校验日期和动作，避免误编辑到同 id 的其他日期', () => {
  const currentState = startEditingExercise(
    'Sunday',
    {
      id: 'shared-id',
      name: '深蹲',
    },
    [{ value: 'squat', label: '深蹲 140kg' }],
  )

  assert.equal(isPlanEditorTarget(currentState, 'Sunday', 'shared-id'), true)
  assert.equal(isPlanEditorTarget(currentState, 'Monday', 'shared-id'), false)
  assert.equal(isPlanEditorTarget(currentState, 'Sunday', 'other-id'), false)
})

test('getPlanExerciseMenuActions 与 executePlanExerciseMenuAction 会稳定映射编辑和删除动作', () => {
  const calls = []
  const actions = getPlanExerciseMenuActions()

  assert.deepEqual(
    actions.map((item) => item.key),
    ['edit', 'delete'],
  )
  assert.equal(actions[1].tone, 'danger')

  assert.equal(
    executePlanExerciseMenuAction('edit', {
      edit: () => calls.push('edit'),
      delete: () => calls.push('delete'),
    }),
    true,
  )
  assert.equal(
    executePlanExerciseMenuAction('delete', {
      edit: () => calls.push('edit'),
      delete: () => calls.push('delete'),
    }),
    true,
  )
  assert.equal(executePlanExerciseMenuAction('archive', {}), false)
  assert.deepEqual(calls, ['edit', 'delete'])
})

test('clearPlanEditorState 会回到空闲状态', () => {
  assert.deepEqual(clearPlanEditorState(), {
    dayKey: null,
    exerciseId: null,
    draft: null,
  })
})

test('canReorderPlanDayExercises 仅在无编辑态且动作数大于 1 时允许拖拽', () => {
  assert.equal(
    canReorderPlanDayExercises({
      editingState: clearPlanEditorState(),
      dayKey: 'Monday',
      exerciseCount: 2,
    }),
    true,
  )

  assert.equal(
    canReorderPlanDayExercises({
      editingState: startEditingExercise('Monday', { id: 'monday-squat', name: '深蹲' }, []),
      dayKey: 'Monday',
      exerciseCount: 2,
    }),
    false,
  )

  assert.equal(
    canReorderPlanDayExercises({
      editingState: startAddingExercise('Monday', []),
      dayKey: 'Monday',
      exerciseCount: 2,
    }),
    false,
  )

  assert.equal(
    canReorderPlanDayExercises({
      editingState: startEditingExercise('Tuesday', { id: 'tuesday-bench', name: '卧推' }, []),
      dayKey: 'Monday',
      exerciseCount: 2,
    }),
    true,
  )

  assert.equal(
    canReorderPlanDayExercises({
      editingState: clearPlanEditorState(),
      dayKey: 'Monday',
      exerciseCount: 1,
    }),
    false,
  )
})

test('编辑百分比动作和固定重量动作后，weeklyPlan 写回结果会同步更新对应展示字段', () => {
  const percentagePlan = updateExerciseInDay(demoWeeklyPlan, 'Monday', 'monday-squat', {
    id: 'monday-squat',
    name: '暂停深蹲',
    tier: 'main',
    ref1RM: 'squat',
    pct: 0.7,
    kg: null,
    sets: 5,
    reps: 4,
    rpe: 8,
    note: '顶组',
  })
  const fixedPlan = updateExerciseInDay(demoWeeklyPlan, 'Monday', 'monday-rdl', {
    id: 'monday-rdl',
    name: '罗马尼亚硬拉',
    tier: 'accessory',
    ref1RM: null,
    pct: null,
    kg: 90,
    sets: 4,
    reps: 8,
    rpe: 7.5,
    note: '控制离心',
  })

  assert.equal(percentagePlan.Monday.exercises[0].name, '暂停深蹲')
  assert.equal(percentagePlan.Monday.exercises[0].template.loadMode, 'percentage')
  assert.equal(percentagePlan.Monday.exercises[0].instance.pct, 0.7)
  assert.equal(fixedPlan.Monday.exercises[1].name, '罗马尼亚硬拉')
  assert.equal(fixedPlan.Monday.exercises[1].template.loadMode, 'fixed')
  assert.equal(fixedPlan.Monday.exercises[1].instance.kg, 90)
})

test('删除动作只影响当前日期，新增动作也只会写回目标日期', () => {
  const nextPlan = removeExerciseFromDay(demoWeeklyPlan, 'Monday', 'monday-rdl')
  const addedPlan = addExerciseToDay(demoWeeklyPlan, 'Tuesday', {
    name: '高举壶铃深蹲',
    tier: 'accessory',
    ref1RM: null,
    pct: null,
    kg: 24,
    sets: 3,
    reps: 12,
    rpe: 7,
    note: '热身后补充',
  })

  assert.equal(nextPlan.Monday.exercises.some((exercise) => exercise.id === 'monday-rdl'), false)
  assert.equal(nextPlan.Tuesday.exercises.length, demoWeeklyPlan.Tuesday.exercises.length)
  assert.equal(
    addedPlan.Tuesday.exercises.some((exercise) => exercise.name === '高举壶铃深蹲'),
    true,
  )
  assert.equal(addedPlan.Monday.exercises.length, demoWeeklyPlan.Monday.exercises.length)
})
