function buildFailureResult(weeklyPlan, message) {
  return {
    ok: false,
    message,
    nextPlan: weeklyPlan,
  }
}

function findExerciseIndex(exercises, exerciseName) {
  return exercises.findIndex((exercise) => exercise.name === exerciseName)
}

/**
 * 按 AI suggestion 中的 day / changes 更新周计划。
 * 这里先集中校验目标日期、动作名和字段，避免出现部分写回导致计划状态不一致。
 */
export function adoptPlanChange(weeklyPlan = {}, day, changes = []) {
  const dayKey = typeof day === 'string' ? day.trim() : ''
  if (!dayKey || !weeklyPlan?.[dayKey]) {
    return buildFailureResult(weeklyPlan, `未找到 ${dayKey || '目标日期'} 的训练计划，无法采纳该建议。`)
  }

  if (!Array.isArray(changes) || changes.length === 0) {
    return buildFailureResult(weeklyPlan, '当前建议没有可采纳的计划变更。')
  }

  const currentDayPlan = weeklyPlan[dayKey]
  const nextExercises = currentDayPlan.exercises.map((exercise) => ({ ...exercise }))

  for (const change of changes) {
    if (change?.action && change.action !== 'update') {
      return buildFailureResult(
        weeklyPlan,
        `当前仅支持更新现有动作，暂不支持“${change.action}”建议。`,
      )
    }

    const exerciseName = typeof change?.exerciseName === 'string' ? change.exerciseName.trim() : ''
    const field = typeof change?.field === 'string' ? change.field.trim() : ''

    if (!exerciseName) {
      return buildFailureResult(weeklyPlan, '建议缺少目标动作名称，无法采纳该建议。')
    }

    const targetIndex = findExerciseIndex(nextExercises, exerciseName)
    if (targetIndex === -1) {
      return buildFailureResult(weeklyPlan, `未找到 ${dayKey} 的动作“${exerciseName}”，无法采纳该建议。`)
    }

    if (!field || !(field in nextExercises[targetIndex])) {
      return buildFailureResult(
        weeklyPlan,
        `未找到动作“${exerciseName}”的字段“${field || '未知字段'}”，无法采纳该建议。`,
      )
    }

    nextExercises[targetIndex] = {
      ...nextExercises[targetIndex],
      [field]: change.newValue,
    }
  }

  return {
    ok: true,
    message: '已采纳 AI 建议，训练计划已更新。',
    nextPlan: {
      ...weeklyPlan,
      [dayKey]: {
        ...currentDayPlan,
        exercises: nextExercises,
      },
    },
  }
}
