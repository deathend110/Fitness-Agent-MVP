import { buildBackupPayload } from './dataTransfer.js'
import { loadStorage, saveStorage } from './storage.js'
import {
  defaultDailyLog,
  defaultProfile,
  defaultWeeklyPlan,
  storageKeys,
} from './defaultData.js'

export const localMigrationKeys = {
  migratedFlag: 'fitloop_migrated_to_backend',
}

const LOCAL_FALLBACK_MIGRATION_BASE_URL = 'http://127.0.0.1:8000/api'

function isSameSnapshot(leftValue, rightValue) {
  return JSON.stringify(leftValue ?? null) === JSON.stringify(rightValue ?? null)
}

export function isLocalMigrationCandidate(appState = {}) {
  // Phase 1 只有 profile / weeklyPlan / dailyLog 会迁入后端，chatHistory 仍只保留在本地。
  return (
    !isSameSnapshot(appState.profile, defaultProfile) ||
    !isSameSnapshot(appState.weeklyPlan, defaultWeeklyPlan) ||
    !isSameSnapshot(appState.dailyLog, defaultDailyLog)
  )
}

export function hasLocalMigrationFlag() {
  return loadStorage(localMigrationKeys.migratedFlag, false) === true
}

export function markLocalMigrationDone() {
  saveStorage(localMigrationKeys.migratedFlag, true)
}

export function buildLocalMigrationPayload(appState, exportedAt = new Date().toISOString()) {
  return buildBackupPayload(appState, exportedAt)
}

function trimTrailingSlash(url = '') {
  return typeof url === 'string' ? url.replace(/\/+$/, '') : LOCAL_FALLBACK_MIGRATION_BASE_URL
}

export function resolveMigrationBaseUrl(env = import.meta.env) {
  const envBaseUrl = typeof env?.VITE_API_BASE_URL === 'string' ? env.VITE_API_BASE_URL.trim() : ''

  // 本地历史数据迁移也走统一 API 地址，避免页面能连通但迁移请求仍指向旧端口。
  return trimTrailingSlash(envBaseUrl || LOCAL_FALLBACK_MIGRATION_BASE_URL)
}

function buildImportUrl(baseUrl = resolveMigrationBaseUrl()) {
  return `${trimTrailingSlash(baseUrl)}/migrate/import`
}

async function readResponseData(response) {
  try {
    return await response.json()
  } catch {
    return null
  }
}

export async function importLocalStorageToBackend(appState, options = {}) {
  const payload = buildLocalMigrationPayload(appState)
  const fetchImpl = options.fetchImpl ?? globalThis.fetch
  if (typeof fetchImpl !== 'function') {
    throw new Error('当前环境不支持 fetch，无法连接本地后端。')
  }

  const response = await fetchImpl(buildImportUrl(options.baseUrl), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
    signal: options.signal,
  })

  if (!response.ok) {
    const data = await readResponseData(response)
    const detail = typeof data?.detail === 'string' ? `：${data.detail}` : ''
    throw new Error(`迁移到后端失败（HTTP ${response.status}）${detail}`)
  }

  const data = await readResponseData(response)

  markLocalMigrationDone()
  return data
}

export function loadLocalStorageSnapshot() {
  return {
    profile: loadStorage(storageKeys.profile, null),
    weeklyPlan: loadStorage(storageKeys.weeklyPlan, null),
    dailyLog: loadStorage(storageKeys.dailyLog, null),
    chatHistory: loadStorage(storageKeys.chatHistory, []),
  }
}
