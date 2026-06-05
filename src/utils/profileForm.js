import {
  getNumericFieldInputProps,
  isTransientNumericFieldDraft,
  validateNumericFieldValue,
} from './numericFieldGuardrails.js'

export const sexOptions = [
  { value: 'male', label: '男' },
  { value: 'female', label: '女' },
]

function buildGuardedField(baseField) {
  return {
    ...getNumericFieldInputProps(baseField.guardrailKey),
    ...baseField,
  }
}

export const basicFields = [
  { key: 'name', label: '姓名', type: 'text' },
  { key: 'sex', label: '性别', type: 'select' },
  buildGuardedField({
    key: 'age',
    label: '年龄',
    type: 'number',
    inputMode: 'numeric',
    guardrailKey: 'profile.basic.age',
  }),
  buildGuardedField({
    key: 'height',
    label: '身高 (cm)',
    type: 'number',
    inputMode: 'numeric',
    guardrailKey: 'profile.basic.height',
  }),
  buildGuardedField({
    key: 'weight',
    label: '当前体重 (kg)',
    type: 'number',
    inputMode: 'numeric',
    guardrailKey: 'profile.basic.weight',
  }),
  buildGuardedField({
    key: 'waist',
    label: '腰围 (cm)',
    type: 'number',
    inputMode: 'numeric',
    guardrailKey: 'profile.basic.waist',
  }),
]

export const targetWeightField = buildGuardedField({
  key: 'targetWeight',
  label: '目标体重 (kg)',
  type: 'number',
  inputMode: 'numeric',
  guardrailKey: 'profile.targetWeight',
})

export const oneRmFields = [
  buildGuardedField({ key: 'squat', label: '深蹲 (kg)', type: 'number', inputMode: 'numeric', guardrailKey: 'profile.oneRM.squat' }),
  buildGuardedField({ key: 'bench', label: '卧推 (kg)', type: 'number', inputMode: 'numeric', guardrailKey: 'profile.oneRM.bench' }),
  buildGuardedField({ key: 'deadlift', label: '硬拉 (kg)', type: 'number', inputMode: 'numeric', guardrailKey: 'profile.oneRM.deadlift' }),
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

/**
 * 档案页是受控输入加上游持久态双向同步，外部 profile 回流时要保留用户仍在输入中的数字草稿。
 */
export function syncProfileDraft(currentDraft, profile) {
  const nextDraft = profileToDraft(profile)
  if (!currentDraft) {
    return nextDraft
  }

  return {
    basic: {
      ...nextDraft.basic,
      age: isTransientNumericFieldDraft('profile.basic.age', currentDraft.basic?.age) ? currentDraft.basic.age : nextDraft.basic.age,
      height: isTransientNumericFieldDraft('profile.basic.height', currentDraft.basic?.height) ? currentDraft.basic.height : nextDraft.basic.height,
      weight: isTransientNumericFieldDraft('profile.basic.weight', currentDraft.basic?.weight) ? currentDraft.basic.weight : nextDraft.basic.weight,
      waist: isTransientNumericFieldDraft('profile.basic.waist', currentDraft.basic?.waist) ? currentDraft.basic.waist : nextDraft.basic.waist,
    },
    oneRM: {
      ...nextDraft.oneRM,
      squat: isTransientNumericFieldDraft('profile.oneRM.squat', currentDraft.oneRM?.squat) ? currentDraft.oneRM.squat : nextDraft.oneRM.squat,
      bench: isTransientNumericFieldDraft('profile.oneRM.bench', currentDraft.oneRM?.bench) ? currentDraft.oneRM.bench : nextDraft.oneRM.bench,
      deadlift: isTransientNumericFieldDraft('profile.oneRM.deadlift', currentDraft.oneRM?.deadlift) ? currentDraft.oneRM.deadlift : nextDraft.oneRM.deadlift,
    },
    goal: nextDraft.goal,
    targetWeight: isTransientNumericFieldDraft('profile.targetWeight', currentDraft.targetWeight) ? currentDraft.targetWeight : nextDraft.targetWeight,
    notes: nextDraft.notes,
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
