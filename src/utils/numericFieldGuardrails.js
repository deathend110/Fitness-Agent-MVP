function freezeGuardrails(guardrails) {
  const frozenEntries = Object.entries(guardrails).map(([fieldKey, rule]) => [
    fieldKey,
    Object.freeze({ ...rule }),
  ])

  return Object.freeze(Object.fromEntries(frozenEntries))
}

/**
 * 统一维护三大页面共享的数值边界，避免输入限制、错误提示和保存校验各自漂移。
 */
export const NUMERIC_FIELD_GUARDRAILS = freezeGuardrails({
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
})

function parseNumericDraft(value) {
  if (value === null || value === undefined) {
    return null
  }

  const normalizedValue = `${value}`.trim()
  if (!normalizedValue) {
    return null
  }

  if (!/^-?\d+(\.\d*)?$/.test(normalizedValue) && !/^-?\.\d+$/.test(normalizedValue)) {
    return Number.NaN
  }

  const parsedValue = Number(normalizedValue)
  return Number.isFinite(parsedValue) ? parsedValue : Number.NaN
}

function countDecimalPlaces(value) {
  const normalizedValue = `${value}`.toLowerCase()

  if (normalizedValue.includes('e')) {
    const [mantissa, exponentValue] = normalizedValue.split('e')
    const exponent = Number.parseInt(exponentValue, 10)
    const mantissaDecimals = countDecimalPlaces(mantissa)
    return Math.max(0, mantissaDecimals - exponent)
  }

  const decimalPart = normalizedValue.split('.')[1]
  return decimalPart ? decimalPart.length : 0
}

function isAlignedToStep(parsedValue, guardrail) {
  const step = Number(guardrail.step)
  if (!Number.isFinite(step) || step <= 0) {
    return true
  }

  const base = Number.isFinite(guardrail.min) ? guardrail.min : 0
  const scale = 10 ** Math.max(
    countDecimalPlaces(step),
    countDecimalPlaces(base),
    countDecimalPlaces(parsedValue),
  )

  const scaledDelta = Math.round((parsedValue - base) * scale)
  const scaledStep = Math.round(step * scale)

  if (scaledStep === 0) {
    return true
  }

  return scaledDelta % scaledStep === 0
}

export function getNumericFieldGuardrail(fieldKey) {
  return NUMERIC_FIELD_GUARDRAILS[fieldKey] ?? null
}

/**
 * 供后续页面接线直接复用共享规则里的输入约束，避免在组件层重复抄写 min/max/step。
 */
export function getNumericFieldInputProps(fieldKey) {
  const guardrail = getNumericFieldGuardrail(fieldKey)
  if (!guardrail) {
    return null
  }

  return {
    min: guardrail.min ?? null,
    max: guardrail.max ?? null,
    step: guardrail.step ?? null,
    inputMode: guardrail.inputMode ?? null,
  }
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

  if (!Number.isFinite(parsedValue)) {
    return `${guardrail.label} 必须填写有效数字`
  }

  if (parsedValue < guardrail.min || parsedValue > guardrail.max) {
    return `${guardrail.label} 必须在 ${guardrail.min}-${guardrail.max}${guardrail.unit ?? ''} 之间`
  }

  if (!isAlignedToStep(parsedValue, guardrail)) {
    return `${guardrail.label} 必须按 ${guardrail.step} 的步长填写`
  }

  return null
}

/**
 * 识别应继续保留在受控输入里的中间草稿，避免父层同步时把用户尚未输完的小数形式抹掉。
 */
export function isTransientNumericFieldDraft(fieldKey, value) {
  const guardrail = getNumericFieldGuardrail(fieldKey)
  if (!guardrail || typeof value !== 'string') {
    return false
  }

  const normalizedValue = value.trim()
  if (!normalizedValue) {
    return false
  }

  if (/^-?\d+\.$/.test(normalizedValue) || /^-?\.\d+$/.test(normalizedValue)) {
    return true
  }

  const validationError = validateNumericFieldValue(fieldKey, normalizedValue)
  if (!validationError) {
    return false
  }

  return isReachableIntermediateValue(guardrail, normalizedValue)
}

function isReachableIntermediateValue(guardrail, nextValue) {
  if (typeof nextValue !== 'string') {
    return false
  }

  const normalizedValue = nextValue.trim()
  if (!normalizedValue) {
    return false
  }

  if (normalizedValue === '.') {
    return guardrail.min < 1 && guardrail.step < 1
  }

  // 小数输入过程中允许保留未完成的小数形式，后续可继续补齐到合法值。
  if (/^\d+\.$/.test(normalizedValue)) {
    const integerPart = Number.parseInt(normalizedValue.slice(0, -1), 10)
    return Number.isFinite(integerPart) && integerPart <= guardrail.max
  }

  if (!/^\d+(\.\d+)?$/.test(normalizedValue)) {
    return false
  }

  const parsedValue = Number(normalizedValue)
  if (!Number.isFinite(parsedValue) || parsedValue > guardrail.max) {
    return false
  }

  const hasDecimalPoint = normalizedValue.includes('.')
  if (hasDecimalPoint) {
    return parsedValue < guardrail.min
  }

  if (parsedValue >= guardrail.min) {
    return false
  }

  if (parsedValue === 0 && guardrail.min < 1) {
    return true
  }

  return canReachValidIntegerPrefix(normalizedValue, guardrail)
}

function canReachValidIntegerPrefix(normalizedValue, guardrail) {
  if (!/^\d+$/.test(normalizedValue)) {
    return false
  }

  const lowerBound = Math.max(0, Math.ceil(guardrail.min))
  const upperBound = Math.floor(guardrail.max)

  for (let candidate = lowerBound; candidate <= upperBound; candidate += 1) {
    if (`${candidate}`.startsWith(normalizedValue)) {
      return true
    }
  }

  return false
}

/**
 * 输入阶段越界时维持上一次稳定草稿，避免 UI 把非法值继续扩散到后续状态。
 */
export function clampNumericInputDraft({ fieldKey, previousValue, nextValue }) {
  const guardrail = getNumericFieldGuardrail(fieldKey)
  if (!guardrail) {
    return {
      nextValue,
      error: null,
    }
  }

  const error = validateNumericFieldValue(fieldKey, nextValue)
  if (error) {
    if (isReachableIntermediateValue(guardrail, nextValue)) {
      return {
        nextValue,
        error: null,
      }
    }

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
