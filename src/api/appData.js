import { createBackendClient } from './backendClient.js'

const DEFAULT_DAILY_LOG_RANGE_START = '2020-01-01'
const DEFAULT_DAILY_LOG_RANGE_END = '2100-12-31'

function isPlainObject(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

export function isSameAppDataSnapshot(previousValue, nextValue) {
  return JSON.stringify(previousValue ?? null) === JSON.stringify(nextValue ?? null)
}

function mapDailyLogEntryFromBackend(entry = {}) {
  if (!isPlainObject(entry)) {
    return {}
  }

  const { tdeeManual, ...rest } = entry

  return {
    ...rest,
    tdee: tdeeManual ?? null,
  }
}

function mapDailyLogEntryToBackend(entry = {}) {
  if (!isPlainObject(entry)) {
    return {}
  }

  const { tdee, ...rest } = entry

  return {
    ...rest,
    tdeeManual: tdee ?? null,
  }
}

export function fromBackendProfile(profile = {}) {
  if (!isPlainObject(profile)) {
    return {}
  }

  const { oneRm, ...rest } = profile

  return {
    ...rest,
    oneRM: isPlainObject(oneRm) ? oneRm : {},
  }
}

export function toBackendProfile(profile = {}) {
  if (!isPlainObject(profile)) {
    return {}
  }

  const { oneRM, ...rest } = profile

  return {
    ...rest,
    oneRm: isPlainObject(oneRM) ? oneRM : {},
  }
}

export function fromBackendDailyLog(dailyLog = {}) {
  if (!isPlainObject(dailyLog)) {
    return {}
  }

  return Object.fromEntries(
    Object.entries(dailyLog).map(([date, entry]) => [date, mapDailyLogEntryFromBackend(entry)]),
  )
}

export function toBackendDailyLog(dailyLog = {}) {
  if (!isPlainObject(dailyLog)) {
    return {}
  }

  return Object.fromEntries(
    Object.entries(dailyLog).map(([date, entry]) => [date, mapDailyLogEntryToBackend(entry)]),
  )
}

function getChangedDailyLogEntries(previousLog = {}, nextLog = {}) {
  const changedDates = new Set([...Object.keys(previousLog), ...Object.keys(nextLog)])

  return [...changedDates].filter((date) => {
    const previousEntry = previousLog?.[date] ?? null
    const nextEntry = nextLog?.[date] ?? null
    return !isSameAppDataSnapshot(previousEntry, nextEntry) && nextEntry !== null
  })
}

export async function loadAppData(options = {}) {
  const client = options.client ?? createBackendClient(options.clientOptions)
  const profile = fromBackendProfile(await client.getProfile({ signal: options.signal }))
  const weeklyPlan = await client.getWeeklyPlan({ signal: options.signal })
  const planSource = await client.getPlanSource({ signal: options.signal })
  const activeCyclePlan = await client.getActiveCyclePlan({ signal: options.signal })
  const dailyLog = fromBackendDailyLog(
    await client.getDailyLog(
      {
        from: options.dailyLogRange?.from ?? DEFAULT_DAILY_LOG_RANGE_START,
        to: options.dailyLogRange?.to ?? DEFAULT_DAILY_LOG_RANGE_END,
      },
      { signal: options.signal },
    ),
  )
  const effectiveWeeklyPlan = activeCyclePlan?.effectivePlan ?? weeklyPlan

  return {
    profile,
    weeklyPlan,
    effectiveWeeklyPlan,
    planSource,
    activeCyclePlan,
    dailyLog,
  }
}

export async function saveProfile(profile, options = {}) {
  const client = options.client ?? createBackendClient(options.clientOptions)
  return fromBackendProfile(
    await client.updateProfile(toBackendProfile(profile), { signal: options.signal }),
  )
}

export async function saveWeeklyPlan(weeklyPlan, options = {}) {
  const client = options.client ?? createBackendClient(options.clientOptions)
  return client.updateWeeklyPlan(weeklyPlan, { signal: options.signal })
}

export async function saveDailyLog(nextDailyLog, options = {}) {
  const client = options.client ?? createBackendClient(options.clientOptions)
  const previousLog = options.previousDailyLog ?? {}
  const backendDailyLog = toBackendDailyLog(nextDailyLog)
  const changedDates = getChangedDailyLogEntries(
    toBackendDailyLog(previousLog),
    backendDailyLog,
  )

  if (changedDates.length === 0) {
    return nextDailyLog
  }

  await Promise.all(
    changedDates.map((date) =>
      client.updateDailyLogEntry(date, backendDailyLog[date], { signal: options.signal }),
    ),
  )

  return nextDailyLog
}
