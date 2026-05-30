import { buildDailyMetricsSummary, getExerciseKg } from './calc.js'
import { getWeekdayOrder } from './weeklyPlan.js'

function formatText(value, fallback = '未记录') {
  if (value === null || value === undefined) {
    return fallback
  }

  const text = `${value}`.trim()
  return text ? text : fallback
}

function formatNumber(value, unit = '', fallback = '未记录') {
  if (value === null || value === undefined || value === '') {
    return fallback
  }

  return `${value}${unit}`
}

function formatMetricNumber(value, unit = '', fractionDigits = 1) {
  if (!Number.isFinite(value)) {
    return '未记录'
  }

  return `${Number(value.toFixed(fractionDigits))}${unit}`
}

function getRecentEntries(dailyLog = {}, limit) {
  return Object.entries(dailyLog)
    .sort(([left], [right]) => right.localeCompare(left))
    .slice(0, limit)
}

function formatExerciseSummary(exercise = {}, oneRM = {}) {
  const name = formatText(exercise.name)
  const kg = `${getExerciseKg(exercise, oneRM)}kg`
  const sets = formatText(exercise.sets)
  const reps = formatText(exercise.reps)
  const note = exercise.note ? `，备注：${exercise.note}` : ''

  return `${name} ${kg} x ${sets}组 x ${reps}次${note}`
}

function buildProfileSection(profile = {}) {
  const basic = profile.basic ?? {}

  return [
    '【基本信息】',
    `姓名：${formatText(basic.name)}`,
    `性别：${basic.sex === 'female' ? '女' : basic.sex === 'male' ? '男' : '未记录'}`,
    `年龄：${formatNumber(basic.age, '岁')}`,
    `身高：${formatNumber(basic.height, 'cm')}`,
    `当前体重：${formatNumber(basic.weight, 'kg')}`,
    `腰围：${formatNumber(basic.waist, 'cm')}`,
    `训练目标：${formatText(profile.goal)}`,
    `目标体重：${formatNumber(profile.targetWeight, 'kg')}`,
    `用户备注：${formatText(profile.notes, '暂无记录')}`,
  ].join('\n')
}

function buildOneRmSection(profile = {}) {
  const oneRM = profile.oneRM ?? {}

  return [
    '【三大项 1RM】',
    `深蹲：${formatNumber(oneRM.squat, 'kg')}`,
    `卧推：${formatNumber(oneRM.bench, 'kg')}`,
    `硬拉：${formatNumber(oneRM.deadlift, 'kg')}`,
  ].join('\n')
}

function buildWeeklyPlanSection(profile = {}, weeklyPlan = {}) {
  const oneRM = profile.oneRM ?? {}
  const hasPlan = Object.keys(weeklyPlan ?? {}).length > 0

  if (!hasPlan) {
    return '【本周训练计划】\n暂无记录'
  }

  const lines = getWeekdayOrder().map((dayKey) => {
    const plan = weeklyPlan?.[dayKey] ?? { type: 'rest', exercises: [] }

    if (plan.type === 'rest') {
      return `${dayKey}：休息日`
    }

    if (!Array.isArray(plan.exercises) || plan.exercises.length === 0) {
      return `${dayKey}：${formatText(plan.type)}，暂无记录`
    }

    const exerciseSummary = plan.exercises
      .map((exercise) => formatExerciseSummary(exercise, oneRM))
      .join(' | ')

    return `${dayKey}：${formatText(plan.type)}，${exerciseSummary}`
  })

  return ['【本周训练计划】', ...lines].join('\n')
}

function buildWeightHistorySection(dailyLog = {}) {
  const entries = getRecentEntries(dailyLog, 14)

  if (!entries.length) {
    return '【近 14 天体重记录】\n暂无记录'
  }

  const lines = entries.map(([date, log]) => `${date}：${formatNumber(log?.weight, 'kg')}`)
  return ['【近 14 天体重记录】', ...lines].join('\n')
}

function buildDietSection(dailyLog = {}) {
  const entries = getRecentEntries(dailyLog, 7)

  if (!entries.length) {
    return '【近 7 天饮食摘要】\n暂无记录'
  }

  const lines = entries.map(
    ([date, log]) =>
      `${date}：摄入 ${formatNumber(log?.kcal, 'kcal')} / 蛋白质 ${formatNumber(log?.protein, 'g')}`,
  )

  return ['【近 7 天饮食摘要】', ...lines].join('\n')
}

function buildTrainingSection(dailyLog = {}) {
  const entries = getRecentEntries(dailyLog, 7)

  if (!entries.length) {
    return '【近 7 天训练完成情况】\n暂无记录'
  }

  const lines = entries.map(([date, log]) => {
    const status = log?.trainingDone ? '已完成训练' : '未完成/休息'
    const fatigue = formatNumber(log?.fatigue, '/5')
    const sleep = formatNumber(log?.sleep, 'h')
    const notes = formatText(log?.trainingNotes, '暂无记录')

    return `${date}：${status}，疲劳度 ${fatigue}，睡眠 ${sleep}，备注：${notes}`
  })

  return ['【近 7 天训练完成情况】', ...lines].join('\n')
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

function buildStructuredMetrics(summary) {
  return {
    date: summary.todayStr,
    today_plan_type: summary.todayPlan?.type ?? 'rest',
    is_training_day: summary.isTrainingDay,
    bmr_kcal: summary.bmr,
    training_kcal: summary.trainingKcal,
    tdee_kcal: summary.tdee,
    bmi: summary.bmi,
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

// 这里同时保留解释性文字和可机读字段，保证大模型既能直接读懂，也能在后续按统一键名继续推算。
function buildMetricsSection(profile = {}, weeklyPlan = {}, dailyLog = {}) {
  const summary = buildDailyMetricsSummary(profile, weeklyPlan, dailyLog)
  const structuredMetrics = buildStructuredMetrics(summary)
  const todayType = formatText(
    summary.todayPlan?.type === 'rest' ? '休息日' : summary.todayPlan?.type,
  )
  const todayIntake = formatMetricNumber(summary.calorie.intake, 'kcal', 0)
  const calorieDelta = formatMetricNumber(summary.calorie.delta, 'kcal', 0)
  const proteinIntake = formatMetricNumber(summary.protein.intake, 'g', 0)
  const proteinPerKg = formatMetricNumber(summary.protein.gramsPerKg, 'g/kg', 1)
  const sleepHours = formatMetricNumber(summary.recovery.sleepHours, 'h', 1)
  const fatigueLevel = formatMetricNumber(summary.recovery.fatigueLevel, '/5', 0)

  return [
    '【今日 TDEE 估算】',
    `日期：${summary.todayStr}`,
    `今日训练类型：${todayType}`,
    `基础代谢(BMR)：${summary.bmr}kcal`,
    `训练容量估算消耗：${summary.trainingKcal}kcal`,
    `当日 TDEE：${summary.tdee}kcal`,
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

/**
 * 为 AI 教练统一构建最新上下文，确保 PromptPreview 与实际注入共享同一份结构化指标口径。
 */
export function buildSystemPrompt(profile = {}, weeklyPlan = {}, dailyLog = {}) {
  return [
    '你是一位专业的力量训练与饮食管理顾问，风格直接、专业、有据可依。',
    '以下是用户当前的完整上下文，请基于这些数据提供具体、可执行的建议。',
    buildProfileSection(profile),
    buildOneRmSection(profile),
    buildWeeklyPlanSection(profile, weeklyPlan),
    buildWeightHistorySection(dailyLog),
    buildDietSection(dailyLog),
    buildTrainingSection(dailyLog),
    buildMetricsSection(profile, weeklyPlan, dailyLog),
  ].join('\n\n')
}
