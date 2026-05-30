import { getExerciseKg } from './calc.js'
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

export function buildProfileSection(profile = {}) {
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

export function buildOneRmSection(profile = {}) {
  const oneRM = profile.oneRM ?? {}

  return [
    '【三大项 1RM】',
    `深蹲：${formatNumber(oneRM.squat, 'kg')}`,
    `卧推：${formatNumber(oneRM.bench, 'kg')}`,
    `硬拉：${formatNumber(oneRM.deadlift, 'kg')}`,
  ].join('\n')
}

export function buildWeeklyPlanSection(profile = {}, weeklyPlan = {}) {
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
      return `${dayKey}：${formatText(plan.type)}，暂时无记录`
    }

    const exerciseSummary = plan.exercises
      .map((exercise) => formatExerciseSummary(exercise, oneRM))
      .join(' | ')

    return `${dayKey}：${formatText(plan.type)}，${exerciseSummary}`
  })

  return ['【本周训练计划】', ...lines].join('\n')
}

export function buildWeightHistorySection(dailyLog = {}) {
  const entries = getRecentEntries(dailyLog, 14)

  if (!entries.length) {
    return '【近 14 天体重记录】\n暂无记录'
  }

  const lines = entries.map(([date, log]) => `${date}：${formatNumber(log?.weight, 'kg')}`)
  return ['【近 14 天体重记录】', ...lines].join('\n')
}

export function buildDietSection(dailyLog = {}) {
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

export function buildTrainingSection(dailyLog = {}) {
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
