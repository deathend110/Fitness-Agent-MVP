import { getExerciseKg } from './calc.js'

function getTypeLabel(type) {
  return type === 'rest' || !type ? '休息日' : type
}

function formatExerciseDetail(exercise = {}, oneRM = {}) {
  const detailParts = []
  const hasResolvedKg = Boolean(exercise.ref1RM) || Number.isFinite(exercise.kg)
  const hasSetsAndReps =
    Number.isFinite(exercise.sets) && Number.isFinite(exercise.reps)

  if (hasResolvedKg) {
    detailParts.push(`${getExerciseKg(exercise, oneRM)}kg`)
  } else {
    detailParts.push('重量待定')
  }

  if (hasSetsAndReps) {
    detailParts.push(`${exercise.sets} 组 x ${exercise.reps} 次`)
  }

  if (Number.isFinite(exercise.rpe)) {
    detailParts.push(`RPE ${exercise.rpe}`)
  }

  if (exercise.note?.trim()) {
    detailParts.push(exercise.note.trim())
  }

  return detailParts.join(' · ')
}

export function buildTodayPlanSummary(dayPlan = {}, oneRM = {}) {
  const type = dayPlan?.type ?? 'rest'
  const exercises = Array.isArray(dayPlan?.exercises) ? dayPlan.exercises : []

  // TodayTab 只读展示当日计划；rest 或空动作都明确回到“休息/未安排”语义。
  if (type === 'rest') {
    return {
      typeLabel: getTypeLabel(type),
      isRestDay: true,
      message: '今天是休息日，当前没有训练动作安排。',
      exercises: [],
    }
  }

  if (exercises.length === 0) {
    return {
      typeLabel: getTypeLabel(type),
      isRestDay: true,
      message: '今天暂不训练，当前计划还没有安排具体动作。',
      exercises: [],
    }
  }

  return {
    typeLabel: getTypeLabel(type),
    isRestDay: false,
    message: '',
    exercises: exercises.map((exercise) => ({
      id: exercise.id ?? `${exercise.name ?? 'exercise'}-${formatExerciseDetail(exercise, oneRM)}`,
      name: exercise.name?.trim() || '未命名动作',
      detail: formatExerciseDetail(exercise, oneRM),
    })),
  }
}
