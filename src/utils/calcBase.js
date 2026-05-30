const WEEKDAY_KEYS = [
  'Sunday',
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
]

export function toNumber(value) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

export function toNullableNumber(value) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function normalizeDecimal(value, fractionDigits = 1) {
  const parsed = Number(value)

  if (!Number.isFinite(parsed)) {
    return '0'
  }

  const normalized = Number(parsed.toFixed(fractionDigits))
  return `${normalized}`
}

export function roundTo(value, fractionDigits = 1) {
  if (!Number.isFinite(value)) {
    return null
  }

  return Number(value.toFixed(fractionDigits))
}

function buildDateString(date) {
  const year = date.getFullYear()
  const month = `${date.getMonth() + 1}`.padStart(2, '0')
  const day = `${date.getDate()}`.padStart(2, '0')

  return `${year}-${month}-${day}`
}

function getWeekdayKey(date) {
  return WEEKDAY_KEYS[date.getDay()]
}

// 返回与 weeklyPlan 对齐的英文星期键，同时允许测试注入固定参考日期。
export function getTodayKey(referenceDate) {
  if (referenceDate?.todayKey) {
    return referenceDate.todayKey
  }

  if (referenceDate?.todayStr) {
    return getWeekdayKey(new Date(`${referenceDate.todayStr}T00:00:00`))
  }

  return getWeekdayKey(new Date())
}

// 使用本地时区拼接 YYYY-MM-DD，同时允许测试注入固定日期，避免跨时区偏移。
export function getTodayStr(referenceDate) {
  if (referenceDate?.todayStr) {
    return referenceDate.todayStr
  }

  return buildDateString(new Date())
}

export function getExerciseKg(exercise = {}, oneRM = {}) {
  if (exercise.ref1RM) {
    const baseKg = toNumber(oneRM?.[exercise.ref1RM])
    const pct = toNumber(exercise.pct)
    return baseKg * pct
  }

  return toNumber(exercise.kg)
}

export function formatDecimalDisplay(value, fractionDigits = 1) {
  return normalizeDecimal(value, fractionDigits)
}

export function formatWeightDisplay(value) {
  return `${formatDecimalDisplay(value, 1)}kg`
}

export function formatCountDisplay(value) {
  return formatDecimalDisplay(value, 0)
}

export function formatPercentDisplay(value) {
  return `${formatDecimalDisplay(toNumber(value) * 100, 0)}%`
}

export function formatRpeDisplay(value) {
  return formatDecimalDisplay(value, 1)
}

export function calcBMR(profileBasic = {}) {
  const weight = toNumber(profileBasic.weight)
  const height = toNumber(profileBasic.height)
  const age = toNumber(profileBasic.age)
  const offset = profileBasic.sex === 'female' ? -161 : 5

  return Math.round(10 * weight + 6.25 * height - 5 * age + offset)
}

export function calcTrainingKcal(exercises = [], oneRM = {}) {
  const totalVolume = exercises.reduce((sum, exercise) => {
    const kg = getExerciseKg(exercise, oneRM)
    const sets = toNumber(exercise.sets)
    const reps = toNumber(exercise.reps)

    return sum + kg * sets * reps
  }, 0)

  return Math.round(totalVolume * 0.1)
}
