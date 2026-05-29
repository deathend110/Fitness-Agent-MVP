function toChartDateKey(date) {
  const year = date.getFullYear()
  const month = `${date.getMonth() + 1}`.padStart(2, '0')
  const day = `${date.getDate()}`.padStart(2, '0')

  return `${year}-${month}-${day}`
}

function toChartLabel(dateKey) {
  return dateKey.slice(5).replace('-', '/')
}

function buildRecentDateKeys(todayStr, days) {
  const today = new Date(`${todayStr}T00:00:00`)

  return Array.from({ length: days }, (_, index) => {
    const nextDate = new Date(today)
    nextDate.setDate(today.getDate() - (days - 1 - index))
    return toChartDateKey(nextDate)
  })
}

// 将今日日志中的体重记录整理成近 14 天可直接喂给图表的数据模型。
export function buildWeightChartModel(dailyLog = {}, todayStr, days = 14) {
  const recentDateKeys = new Set(buildRecentDateKeys(todayStr, days))
  const points = Object.entries(dailyLog)
    .filter(([dateKey, log]) => recentDateKeys.has(dateKey) && Number.isFinite(log?.weight))
    .sort(([leftDate], [rightDate]) => leftDate.localeCompare(rightDate))
    .map(([dateKey, log]) => ({
      dateKey,
      label: toChartLabel(dateKey),
      weight: log.weight,
    }))

  return {
    hasEnoughData: points.length >= 2,
    points,
    emptyMessage: '近 14 天至少需要 2 条体重记录，才会显示趋势图。',
  }
}
