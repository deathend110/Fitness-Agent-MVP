const DEFAULT_TRAINING_DAYS = ['Monday', 'Wednesday', 'Friday']
const WEEKDAY_OPTIONS = [
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
  'Sunday',
]

function normalizeText(value) {
  return typeof value === 'string' ? value.trim() : ''
}

function normalizeNumber(value) {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }

  if (typeof value !== 'string') {
    return null
  }

  const normalizedValue = value.trim()
  if (!normalizedValue) {
    return null
  }

  const parsedValue = Number(normalizedValue)
  return Number.isFinite(parsedValue) ? parsedValue : null
}

function normalizeTrainingDays(trainingDays = []) {
  if (!Array.isArray(trainingDays)) {
    return []
  }

  const uniqueDays = []
  trainingDays.forEach((day) => {
    if (!WEEKDAY_OPTIONS.includes(day) || uniqueDays.includes(day)) {
      return
    }

    uniqueDays.push(day)
  })

  return uniqueDays
}

function buildLiftDraft(source = {}) {
  return {
    oneRm: source?.oneRm === null || source?.oneRm === undefined ? '' : `${source.oneRm}`,
    tm: source?.tm === null || source?.tm === undefined ? '' : `${source.tm}`,
  }
}

export function createCyclePlanDraft(profile = {}, activeCyclePlan = null) {
  const activeCycle = activeCyclePlan?.cycle ?? {}
  const baseLifts = activeCycle.baseLifts ?? {}
  const profileOneRm = profile?.oneRM ?? {}

  return {
    presetKey: normalizeText(activeCycle.presetKey) || 'candito_6week',
    startDate: normalizeText(activeCycle.startDate),
    goal: normalizeText(activeCycle.goal || profile?.goal),
    baseLifts: {
      squat: buildLiftDraft(baseLifts.squat ?? { oneRm: profileOneRm.squat ?? null }),
      bench: buildLiftDraft(baseLifts.bench ?? { oneRm: profileOneRm.bench ?? null }),
      deadlift: buildLiftDraft(baseLifts.deadlift ?? { oneRm: profileOneRm.deadlift ?? null }),
    },
    config: {
      trainingDays:
        normalizeTrainingDays(activeCycle.config?.trainingDays) || DEFAULT_TRAINING_DAYS,
    },
  }
}

export function toggleTrainingDay(trainingDays = [], dayKey) {
  const normalizedDays = normalizeTrainingDays(trainingDays)

  if (!WEEKDAY_OPTIONS.includes(dayKey)) {
    return normalizedDays
  }

  if (normalizedDays.includes(dayKey)) {
    return normalizedDays.filter((day) => day !== dayKey)
  }

  return [...normalizedDays, dayKey]
}

export function buildCreateCyclePlanPayload(draft = {}) {
  const baseLifts = draft?.baseLifts ?? {}

  return {
    presetKey: normalizeText(draft?.presetKey),
    startDate: normalizeText(draft?.startDate),
    goal: normalizeText(draft?.goal),
    baseLifts: {
      squat: {
        oneRm: normalizeNumber(baseLifts?.squat?.oneRm),
        tm: normalizeNumber(baseLifts?.squat?.tm),
      },
      bench: {
        oneRm: normalizeNumber(baseLifts?.bench?.oneRm),
        tm: normalizeNumber(baseLifts?.bench?.tm),
      },
      deadlift: {
        oneRm: normalizeNumber(baseLifts?.deadlift?.oneRm),
        tm: normalizeNumber(baseLifts?.deadlift?.tm),
      },
    },
    config: {
      trainingDays: normalizeTrainingDays(draft?.config?.trainingDays),
    },
  }
}

export const cyclePlanWeekdayOptions = WEEKDAY_OPTIONS
