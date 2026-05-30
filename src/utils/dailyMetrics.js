import {
  calcBMR,
  calcTrainingKcal,
  getTodayKey,
  getTodayStr,
  roundTo,
  toNullableNumber,
} from './calcBase.js'

function getRestPlan() {
  return { type: 'rest', exercises: [] }
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
export function buildDailyMetricsSummary(
  profile = {},
  weeklyPlan = {},
  dailyLog = {},
  referenceDate,
) {
  const todayKey = getTodayKey(referenceDate)
  const todayStr = getTodayStr(referenceDate)
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

// 保持现有 prompt 等调用方的返回结构，避免收口阶段扩大改动面。
export function calcTDEE(profile = {}, weeklyPlan = {}, dailyLog = {}, referenceDate) {
  const summary = buildDailyMetricsSummary(profile, weeklyPlan, dailyLog, referenceDate)

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
