import { buildDailyMetricsSummary } from './dailyMetrics.js'

function formatText(value, fallback = '未记录') {
  if (value === null || value === undefined) {
    return fallback
  }

  const text = `${value}`.trim()
  return text ? text : fallback
}

function formatMetricNumber(value, unit = '', fractionDigits = 1) {
  if (!Number.isFinite(value)) {
    return '未记录'
  }

  return `${Number(value.toFixed(fractionDigits))}${unit}`
}

function getCalorieStatusLabel(status) {
  if (status === 'deficit') {
    return '热量缺口'
  }

  if (status === 'surplus') {
    return '热量盈余'
  }

  if (status === 'balanced') {
    return '热量基本持平'
  }

  return '未知'
}

function getProteinStatusLabel(status) {
  if (status === 'met') {
    return '已达到建议下限'
  }

  if (status === 'low') {
    return '低于建议下限'
  }

  return '未知'
}

export function buildStructuredMetrics(summary) {
  return {
    date: summary.todayStr,
    today_plan_type: summary.todayPlan?.type ?? 'rest',
    is_training_day: summary.isTrainingDay,
    bmr_kcal: summary.bmr,
    training_kcal: summary.trainingKcal,
    estimated_tdee_kcal: summary.estimatedTdee,
    tdee_source: summary.tdeeSource,
    tdee_kcal: summary.tdee,
    bmi: summary.bmi,
    steps_count: summary.activity.steps,
    calorie_intake_kcal: summary.calorie.intake,
    calorie_delta_kcal: summary.calorie.delta,
    calorie_status: summary.calorie.status,
    protein_intake_g: summary.protein.intake,
    protein_g_per_kg: summary.protein.gramsPerKg,
    protein_status: summary.protein.status,
    sleep_hours: summary.recovery.sleepHours,
    fatigue_level: summary.recovery.fatigueLevel,
  }
}

// 复杂指标段独立成单文件，便于 Task 6 后续继续扩展而不把通用 prompt 段重新堆胖。
export function buildMetricsSection(
  profile = {},
  weeklyPlan = {},
  dailyLog = {},
  referenceDate,
) {
  const summary = buildDailyMetricsSummary(profile, weeklyPlan, dailyLog, referenceDate)
  const structuredMetrics = buildStructuredMetrics(summary)
  const todayType = formatText(
    summary.todayPlan?.type === 'rest' ? '休息日' : summary.todayPlan?.type,
  )
  const todayIntake = formatMetricNumber(summary.calorie.intake, 'kcal', 0)
  const calorieDelta = formatMetricNumber(summary.calorie.delta, 'kcal', 0)
  const proteinIntake = formatMetricNumber(summary.protein.intake, 'g', 0)
  const proteinPerKg = formatMetricNumber(summary.protein.gramsPerKg, 'g/kg', 1)
  const sleepHours = formatMetricNumber(summary.recovery.sleepHours, 'h', 1)
  const steps = formatMetricNumber(summary.activity.steps, '步', 0)
  const fatigueLevel = formatMetricNumber(summary.recovery.fatigueLevel, '/5', 0)
  const tdeeSourceLabel = summary.tdeeSource === 'manual' ? '手填' : '估算'

  return [
    '【今日 TDEE 估算】',
    `日期：${summary.todayStr}`,
    `今日训练类型：${todayType}`,
    `基础代谢(BMR)：${summary.bmr}kcal`,
    `训练容量估算消耗：${summary.trainingKcal}kcal`,
    `步数：${steps}`,
    `当日 TDEE：${summary.tdee}kcal`,
    `TDEE来源：${tdeeSourceLabel}`,
    `参考估算 TDEE：${summary.estimatedTdee}kcal`,
    `今日摄入：${todayIntake}`,
    `热量缺口/盈余：${calorieDelta}`,
    `BMI：${formatMetricNumber(summary.bmi, '', 1)}`,
    `热量状态：${getCalorieStatusLabel(summary.calorie.status)}（状态值：${summary.calorie.status}）`,
    `蛋白质摄入：${proteinIntake}`,
    `蛋白质按体重：${proteinPerKg}`,
    `蛋白质状态：${getProteinStatusLabel(summary.protein.status)}（状态值：${summary.protein.status}）`,
    `恢复数据：睡眠 ${sleepHours}；疲劳度 ${fatigueLevel}`,
    '这些字段可作为训练负荷、饮食充足度和恢复状态的统一判断口径；如字段缺失，请明确说明不确定性，不要自行脑补。',
    `structured_metrics=${JSON.stringify(structuredMetrics, null, 2)}`,
  ].join('\n')
}
