export const sexOptions = [
  { value: 'male', label: '男' },
  { value: 'female', label: '女' },
]

export const basicFields = [
  { key: 'name', label: '姓名', type: 'text' },
  { key: 'sex', label: '性别', type: 'select' },
  { key: 'age', label: '年龄', type: 'number', step: '1', inputMode: 'numeric' },
  { key: 'height', label: '身高 (cm)', type: 'number', step: '0.1', inputMode: 'numeric' },
  { key: 'weight', label: '当前体重 (kg)', type: 'number', step: '0.1', inputMode: 'numeric' },
  { key: 'waist', label: '腰围 (cm)', type: 'number', step: '0.1', inputMode: 'numeric' },
]

export const oneRmFields = [
  { key: 'squat', label: '深蹲 (kg)' },
  { key: 'bench', label: '卧推 (kg)' },
  { key: 'deadlift', label: '硬拉 (kg)' },
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
      age: toNumberOrNull(draft.basic.age),
      height: toNumberOrNull(draft.basic.height),
      weight: toNumberOrNull(draft.basic.weight),
      waist: toNumberOrNull(draft.basic.waist),
    },
    oneRM: {
      squat: toNumberOrNull(draft.oneRM.squat),
      bench: toNumberOrNull(draft.oneRM.bench),
      deadlift: toNumberOrNull(draft.oneRM.deadlift),
    },
    goal: draft.goal,
    targetWeight: toNumberOrNull(draft.targetWeight),
    notes: draft.notes,
  }
}
