import { validateNumericFieldValue } from './numericFieldGuardrails.js'

export const sexOptions = [
  { value: 'male', label: '男' },
  { value: 'female', label: '女' },
]

export const basicFields = [
  { key: 'name', label: '姓名', type: 'text' },
  { key: 'sex', label: '性别', type: 'select' },
  { key: 'age', label: '年龄', type: 'number', step: '1', inputMode: 'numeric', guardrailKey: 'profile.basic.age' },
  { key: 'height', label: '身高 (cm)', type: 'number', step: '0.1', inputMode: 'numeric', guardrailKey: 'profile.basic.height' },
  { key: 'weight', label: '当前体重 (kg)', type: 'number', step: '0.1', inputMode: 'numeric', guardrailKey: 'profile.basic.weight' },
  { key: 'waist', label: '腰围 (cm)', type: 'number', step: '0.1', inputMode: 'numeric', guardrailKey: 'profile.basic.waist' },
]

export const oneRmFields = [
  { key: 'squat', label: '深蹲 (kg)', guardrailKey: 'profile.oneRM.squat' },
  { key: 'bench', label: '卧推 (kg)', guardrailKey: 'profile.oneRM.bench' },
  { key: 'deadlift', label: '硬拉 (kg)', guardrailKey: 'profile.oneRM.deadlift' },
]

export function toInputValue(value) {
  return value === null || value === undefined ? '' : `${value}`
}

export function toNumberOrNull(value) {
  if (value === '') {
    return null
  }

  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

/**
 * 保存前再次复核数值边界，避免绕过页面输入限制后把异常业务值写入档案。
 */
export function toGuardedNumberOrNull(fieldKey, value) {
  if (value === null || value === undefined) {
    return null
  }

  const normalizedValue = `${value}`.trim()
  if (!normalizedValue) {
    return null
  }

  if (validateNumericFieldValue(fieldKey, normalizedValue)) {
    return null
  }

  return toNumberOrNull(normalizedValue)
}

export function profileToDraft(profile) {
  return {
    basic: {
      name: profile.basic?.name ?? '',
      sex: profile.basic?.sex ?? 'male',
      age: toInputValue(profile.basic?.age),
      height: toInputValue(profile.basic?.height),
      weight: toInputValue(profile.basic?.weight),
      waist: toInputValue(profile.basic?.waist),
    },
    oneRM: {
      squat: toInputValue(profile.oneRM?.squat),
      bench: toInputValue(profile.oneRM?.bench),
      deadlift: toInputValue(profile.oneRM?.deadlift),
    },
    goal: profile.goal ?? '',
    targetWeight: toInputValue(profile.targetWeight),
    notes: profile.notes ?? '',
  }
}

export function draftToProfile(draft) {
  return {
    basic: {
      name: draft.basic.name,
      sex: draft.basic.sex,
      age: toGuardedNumberOrNull('profile.basic.age', draft.basic.age),
      height: toGuardedNumberOrNull('profile.basic.height', draft.basic.height),
      weight: toGuardedNumberOrNull('profile.basic.weight', draft.basic.weight),
      waist: toGuardedNumberOrNull('profile.basic.waist', draft.basic.waist),
    },
    oneRM: {
      squat: toGuardedNumberOrNull('profile.oneRM.squat', draft.oneRM.squat),
      bench: toGuardedNumberOrNull('profile.oneRM.bench', draft.oneRM.bench),
      deadlift: toGuardedNumberOrNull('profile.oneRM.deadlift', draft.oneRM.deadlift),
    },
    goal: draft.goal,
    targetWeight: toGuardedNumberOrNull('profile.targetWeight', draft.targetWeight),
    notes: draft.notes,
  }
}
