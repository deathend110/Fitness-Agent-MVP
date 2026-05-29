const REQUIRED_FIELDS = ['profile', 'weeklyPlan', 'dailyLog', 'chatHistory']

function assertObject(value, fieldName) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error(`备份文件中的 ${fieldName} 结构无效。`)
  }
}

export function buildBackupPayload(appState, exportedAt = new Date().toISOString()) {
  return {
    app: 'fitloop-mvp',
    version: 1,
    exportedAt,
    profile: appState.profile,
    weeklyPlan: appState.weeklyPlan,
    dailyLog: appState.dailyLog,
    chatHistory: appState.chatHistory,
  }
}

export function buildBackupFilename(exportedAt = new Date().toISOString()) {
  return `fitloop-backup-${exportedAt.slice(0, 10)}.json`
}

// 导入前只做最小字段校验，避免把明显错误的 JSON 覆盖到当前本地数据。
export function parseBackupJson(rawText) {
  const payload = JSON.parse(rawText)

  REQUIRED_FIELDS.forEach((fieldName) => {
    if (!(fieldName in payload)) {
      throw new Error(`备份文件缺少必要字段：${fieldName}`)
    }
  })

  assertObject(payload.profile, 'profile')
  assertObject(payload.weeklyPlan, 'weeklyPlan')
  assertObject(payload.dailyLog, 'dailyLog')

  if (!Array.isArray(payload.chatHistory)) {
    throw new Error('备份文件中的 chatHistory 结构无效。')
  }

  return {
    profile: payload.profile,
    weeklyPlan: payload.weeklyPlan,
    dailyLog: payload.dailyLog,
    chatHistory: payload.chatHistory,
  }
}
