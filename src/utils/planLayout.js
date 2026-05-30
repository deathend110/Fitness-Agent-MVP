import { normalizeWeeklyPlan } from './weeklyPlan.js'

export function buildWeeklyPlanColumns(weeklyPlan = {}) {
  const normalizedPlan = normalizeWeeklyPlan(weeklyPlan)

  return Object.entries(normalizedPlan).map(([dayKey, dayPlan]) => {
    const isTrainingDay = dayPlan.type !== 'rest'

    return {
      dayKey,
      plan: dayPlan,
      isTrainingDay,
      exerciseCount: dayPlan.exercises.length,
      width: isTrainingDay ? 'wide' : 'narrow',
      widthClassName: isTrainingDay ? 'min-w-[17rem] flex-[1.35_1_17rem]' : 'min-w-[12rem] flex-[0.85_1_12rem]',
    }
  })
}
