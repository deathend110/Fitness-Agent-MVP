const WEEKDAY_KEYS = [
  'Sunday',
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
]

function toNumber(value) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

function toNullableNumber(value) {
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

function roundTo(value, fractionDigits = 1) {
  if (!Number.isFinite(value)) {
    return null
  }

  return Number(value.toFixed(fractionDigits))
}

function getRestPlan() {
  return { type: 'rest', exercises: [] }
}

// 返回与 weeklyPlan 对齐的英文星期键，避免多个页面各自维护映射。
export function getTodayKey() {
  return WEEKDAY_KEYS[new Date().getDay()]
}

// 使用本地时区拼接 YYYY-MM-DD，避免 ISO 字符串跨时区偏移到前一天。
export function getTodayStr() {
  const now = new Date()
  const year = now.getFullYear()
  const month = `${now.getMonth() + 1}`.padStart(2, '0')
  const day = `${now.getDate()}`.padStart(2, '0')

  return `${year}-${month}-${day}`
}

// 统一解析动作实际重量，兼容 ref1RM 百分比模式和固定 kg 模式。
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

// 按 spec 中的 Mifflin-St Jeor 公式估算基础代谢。
export function calcBMR(profileBasic = {}) {
  const weight = toNumber(profileBasic.weight)
  const height = toNumber(profileBasic.height)
  const age = toNumber(profileBasic.age)
  const offset = profileBasic.sex === 'female' ? -161 : 5

  return Math.round(10 * weight + 6.25 * height - 5 * age + offset)
}

// 训练消耗按 kg * sets * reps * 0.1 估算，空计划或休息日调用时自然返回 0。
export function calcTrainingKcal(exercises = [], oneRM = {}) {
  const totalVolume = exercises.reduce((sum, exercise) => {
    const kg = getExerciseKg(exercise, oneRM)
    const sets = toNumber(exercise.sets)
    const reps = toNumber(exercise.reps)

    return sum + kg * sets * reps
  }, 0)

  return Math.round(totalVolume * 0.1)
}

function calcBMI(profileBasic = {}) {
  const weight = toNullableNumber(profileBasic.weight)
  const heightCm = toNullableNumber(profileBasic.height)

  if (weight === null || weight <= 0 || heightCm === null || heightCm <= 0) {
    return null
  }

  const heightM = heightCm / 100
  return roundTo(weight / (heightM * heightM), 1)
}

// 蛋白质按体重折算采用 g/kg，适合作为 prompt 与 UI 的统一口径。
function calcProteinPerKg(proteinIntake, weight) {
  if (!Number.isFinite(proteinIntake) || proteinIntake <= 0) {
    return null
  }

  if (!Number.isFinite(weight) || weight <= 0) {
    return null
  }

  return roundTo(proteinIntake / weight, 1)
}

function getCalorieStatus(delta) {
  if (!Number.isFinite(delta)) {
    return 'unknown'
  }

  if (delta > 100) {
    return 'surplus'
  }

  if (delta < -100) {
    return 'deficit'
  }

  return 'balanced'
}

function getProteinStatus(proteinPerKg) {
  if (!Number.isFinite(proteinPerKg)) {
    return 'unknown'
  }

  return proteinPerKg >= 1.6 ? 'met' : 'low'
}

// 汇总今日本地即可确定的训练、营养与恢复指标，供 prompt 注入和页面展示复用。
export function buildDailyMetricsSummary(profile = {}, weeklyPlan = {}, dailyLog = {}) {
  const todayKey = getTodayKey()
  const todayStr = getTodayStr()
  const todayPlan = weeklyPlan?.[todayKey] ?? getRestPlan()
  const isTrainingDay = todayPlan.type !== 'rest'
  const bmr = calcBMR(profile.basic)
  const trainingKcal = isTrainingDay
    ? calcTrainingKcal(todayPlan.exercises, profile.oneRM)
    : 0
  const tdee = Math.round(bmr * 1.2 + trainingKcal)
  const todayLog = dailyLog?.[todayStr] ?? {}
  const calorieIntake = toNullableNumber(todayLog.kcal)
  const proteinIntake = toNullableNumber(todayLog.protein)
  const sleepHours = toNullableNumber(todayLog.sleep)
  const fatigueLevel = toNullableNumber(todayLog.fatigue)
  const calorieDelta = calorieIntake === null ? null : calorieIntake - tdee
  const bodyWeight = toNullableNumber(profile?.basic?.weight)
  const proteinPerKg = calcProteinPerKg(proteinIntake, bodyWeight)

  return {
    todayKey,
    todayStr,
    todayPlan,
    isTrainingDay,
    bmr,
    bmi: calcBMI(profile.basic),
    trainingKcal,
    tdee,
    calorie: {
      intake: calorieIntake,
      delta: calorieDelta,
      status: getCalorieStatus(calorieDelta),
    },
    protein: {
      intake: proteinIntake,
      gramsPerKg: proteinPerKg,
      status: getProteinStatus(proteinPerKg),
    },
    recovery: {
      sleepHours,
      fatigueLevel,
    },
  }
}

// 保持现有 prompt 等调用方的返回结构，避免 6.1 阶段扩散改动范围。
export function calcTDEE(profile = {}, weeklyPlan = {}, dailyLog = {}) {
  const summary = buildDailyMetricsSummary(profile, weeklyPlan, dailyLog)

  return {
    todayKey: summary.todayKey,
    todayStr: summary.todayStr,
    todayPlan: summary.todayPlan,
    isTrainingDay: summary.isTrainingDay,
    bmr: summary.bmr,
    trainingKcal: summary.trainingKcal,
    tdee: summary.tdee,
    todayKcal: summary.calorie.intake ?? 0,
    delta: summary.calorie.delta ?? 0,
  }
}
