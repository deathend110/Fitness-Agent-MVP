import { getWeekdayOrder, normalizeWeeklyPlan } from './weeklyPlan.js'

export function mergeCommittedWeeklyPlan(currentPlan = {}, committedPlan = {}) {
  const mergedDays = normalizeWeeklyPlan(committedPlan)
  const nextPlan =
    currentPlan && typeof currentPlan === 'object' && !Array.isArray(currentPlan)
      ? { ...currentPlan }
      : {}

  getWeekdayOrder().forEach((dayKey) => {
    nextPlan[dayKey] = mergedDays[dayKey]
  })

  return nextPlan
}
