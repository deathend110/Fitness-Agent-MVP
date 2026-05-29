import { calcTDEE, getExerciseKg } from './calc.js'
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

function buildTdeeSection(profile = {}, weeklyPlan = {}, dailyLog = {}) {
  const summary = calcTDEE(profile, weeklyPlan, dailyLog)
  const todayType = formatText(summary.todayPlan?.type === 'rest' ? '休息日' : summary.todayPlan?.type)
  const todayKcal = dailyLog?.[summary.todayStr]?.kcal == null ? '未记录' : `${summary.todayKcal}kcal`
  const deltaText = dailyLog?.[summary.todayStr]?.kcal == null ? '未记录' : `${summary.delta}kcal`

  return [
    '【今日 TDEE 估算】',
    `日期：${summary.todayStr}`,
    `今日训练类型：${todayType}`,
    `基础代谢(BMR)：${summary.bmr}kcal`,
    `训练容量估算消耗：${summary.trainingKcal}kcal`,
    `当日 TDEE：${summary.tdee}kcal`,
    `今日摄入：${todayKcal}`,
    `热量缺口/盈余：${deltaText}`,
  ].join('\n')
}

/**
 * 为 AI 教练统一构建最新上下文，保证新用户、空日志、休息日等场景都能稳定生成文本预览。
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
    buildTdeeSection(profile, weeklyPlan, dailyLog),
  ].join('\n\n')
}
