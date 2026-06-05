/**
 * 统一维护三大页面共享的数值边界，避免输入限制、错误提示和保存校验各自漂移。
 */
export const NUMERIC_FIELD_GUARDRAILS = {
  'profile.basic.age': { label: '年龄', min: 12, max: 100, step: 1 },
  'profile.basic.height': { label: '身高', min: 120, max: 250, step: 0.1, unit: 'cm' },
  'profile.basic.weight': { label: '当前体重', min: 25, max: 300, step: 0.1, unit: 'kg' },
  'profile.basic.waist': { label: '腰围', min: 40, max: 200, step: 0.1, unit: 'cm' },
  'profile.targetWeight': { label: '目标体重', min: 25, max: 300, step: 0.1, unit: 'kg' },
  'profile.oneRM.squat': { label: '深蹲 1RM', min: 10, max: 500, step: 0.1, unit: 'kg' },
  'profile.oneRM.bench': { label: '卧推 1RM', min: 5, max: 400, step: 0.1, unit: 'kg' },
  'profile.oneRM.deadlift': { label: '硬拉 1RM', min: 10, max: 500, step: 0.1, unit: 'kg' },
  'today.weight': { label: '体重', min: 25, max: 300, step: 0.1, unit: 'kg' },
  'today.kcal': { label: '热量', min: 0, max: 10000, step: 1, unit: 'kcal' },
  'today.protein': { label: '蛋白质', min: 0, max: 400, step: 1, unit: 'g' },
  'today.sleep': { label: '睡眠', min: 0, max: 24, step: 0.1, unit: 'h' },
  'today.steps': { label: '步数', min: 0, max: 100000, step: 1, unit: '步' },
  'today.tdee': { label: 'TDEE', min: 800, max: 7000, step: 1, unit: 'kcal' },
  'today.fatigue': { label: '疲劳度', min: 1, max: 5, step: 1, unit: '/5' },
  'plan.weekMeta.weekNumber': { label: '周数', min: 1, max: 999, step: 1, unit: '周' },
  'plan.exercise.pct': { label: '百分比负重', min: 0.2, max: 1.5, step: 0.01, unit: '倍' },
  'plan.exercise.kg': { label: '固定重量', min: 0.5, max: 500, step: 0.5, unit: 'kg' },
  'plan.exercise.sets': { label: '组数', min: 1, max: 20, step: 1, unit: '组' },
  'plan.exercise.reps': { label: '次数', min: 1, max: 100, step: 1, unit: '次' },
  'plan.exercise.rpe': { label: 'RPE', min: 0, max: 10, step: 0.5, unit: '/10' },
  'plan.cycle.squat.oneRm': { label: '深蹲 1RM', min: 10, max: 500, step: 0.1, unit: 'kg' },
  'plan.cycle.squat.tm': { label: '深蹲 TM', min: 10, max: 500, step: 0.1, unit: 'kg' },
  'plan.cycle.bench.oneRm': { label: '卧推 1RM', min: 5, max: 400, step: 0.1, unit: 'kg' },
  'plan.cycle.bench.tm': { label: '卧推 TM', min: 5, max: 400, step: 0.1, unit: 'kg' },
  'plan.cycle.deadlift.oneRm': { label: '硬拉 1RM', min: 10, max: 500, step: 0.1, unit: 'kg' },
  'plan.cycle.deadlift.tm': { label: '硬拉 TM', min: 10, max: 500, step: 0.1, unit: 'kg' },
  'plan.custom.totalWeeks': { label: '周数', min: 1, max: 24, step: 1, unit: '周' },
  'plan.custom.squat.tm': { label: '深蹲 TM', min: 10, max: 500, step: 0.1, unit: 'kg' },
  'plan.custom.bench.tm': { label: '卧推 TM', min: 5, max: 400, step: 0.1, unit: 'kg' },
  'plan.custom.deadlift.tm': { label: '硬拉 TM', min: 10, max: 500, step: 0.1, unit: 'kg' },
  'plan.custom.ohp.tm': { label: '推举 TM', min: 5, max: 250, step: 0.1, unit: 'kg' },
}

function parseNumericDraft(value) {
  if (value === null || value === undefined) {
    return null
  }

  const normalizedValue = `${value}`.trim()
  if (!normalizedValue) {
    return null
  }

  const parsedValue = Number(normalizedValue)
  return Number.isFinite(parsedValue) ? parsedValue : Number.NaN
}

export function getNumericFieldGuardrail(fieldKey) {
  return NUMERIC_FIELD_GUARDRAILS[fieldKey] ?? null
}

export function validateNumericFieldValue(fieldKey, value) {
  const guardrail = getNumericFieldGuardrail(fieldKey)
  if (!guardrail) {
    return null
  }

  const parsedValue = parseNumericDraft(value)
  if (parsedValue === null) {
    return null
  }

  if (!Number.isFinite(parsedValue) || parsedValue < guardrail.min || parsedValue > guardrail.max) {
    return `${guardrail.label} 必须在 ${guardrail.min}-${guardrail.max}${guardrail.unit ?? ''} 之间`
  }

  return null
}

/**
 * 输入阶段越界时维持上一次稳定草稿，避免 UI 把非法值继续扩散到后续状态。
 */
export function clampNumericInputDraft({ fieldKey, previousValue, nextValue }) {
  const error = validateNumericFieldValue(fieldKey, nextValue)
  if (error) {
    return {
      nextValue: previousValue,
      error,
    }
  }

  return {
    nextValue,
    error: null,
  }
}
