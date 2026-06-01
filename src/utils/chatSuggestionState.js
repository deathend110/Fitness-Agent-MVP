const DISMISSED_SUGGESTIONS_STORAGE_KEY = 'fitloop:coach-dismissed-suggestions'

function getSuggestionCommitKey(suggestion) {
  if (!suggestion) {
    return ''
  }

  if (suggestion.proposalId) {
    return `proposal:${suggestion.proposalId}`
  }

  // 旧版 suggestion 没有 proposalId，只能用 day + changes 表示同一张本地采纳卡片。
  return `legacy:${suggestion.day || ''}:${JSON.stringify(suggestion.changes || [])}`
}

function readDismissedSuggestionStorage() {
  if (typeof window === 'undefined') {
    return {}
  }

  try {
    const parsed = JSON.parse(
      window.localStorage.getItem(DISMISSED_SUGGESTIONS_STORAGE_KEY) || '{}',
    )
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {}
  } catch {
    window.localStorage.removeItem(DISMISSED_SUGGESTIONS_STORAGE_KEY)
    return {}
  }
}

function readDismissedSuggestionKeys(sessionId) {
  if (!Number.isInteger(sessionId)) {
    return []
  }

  const storage = readDismissedSuggestionStorage()
  const rawKeys = storage[String(sessionId)]
  return Array.isArray(rawKeys) ? rawKeys.filter((item) => typeof item === 'string' && item) : []
}

function persistDismissedSuggestionKey(sessionId, suggestion) {
  const commitKey = getSuggestionCommitKey(suggestion)

  if (!Number.isInteger(sessionId) || !commitKey || typeof window === 'undefined') {
    return
  }

  const storage = readDismissedSuggestionStorage()
  const sessionKey = String(sessionId)
  const nextKeys = new Set(readDismissedSuggestionKeys(sessionId))

  nextKeys.add(commitKey)
  storage[sessionKey] = [...nextKeys]
  window.localStorage.setItem(
    DISMISSED_SUGGESTIONS_STORAGE_KEY,
    JSON.stringify(storage),
  )
}

function buildMessageStableKeys(messages = []) {
  const sameMessageCounts = new Map()

  return messages.map((message) => {
    const baseKey = `${message?.role || 'unknown'}::${message?.content || ''}`
    const occurrence = sameMessageCounts.get(baseKey) || 0

    sameMessageCounts.set(baseKey, occurrence + 1)
    return `${baseKey}::${occurrence}`
  })
}

function mergeMessageMeta(messages = [], currentMeta = [], options = {}) {
  const hiddenCommitKeys =
    options.hiddenCommitKeys instanceof Set ? options.hiddenCommitKeys : new Set()
  const currentBuckets = currentMeta.reduce((buckets, entry) => {
    if (!entry?.messageKey) {
      return buckets
    }

    const bucket = buckets.get(entry.messageKey) || []
    bucket.push(entry)
    buckets.set(entry.messageKey, bucket)
    return buckets
  }, new Map())

  return buildMessageStableKeys(messages).map((messageKey, index) => {
    const bucket = currentBuckets.get(messageKey)
    const messageSuggestion = messages[index]?.suggestion || null

    if (bucket?.length) {
      const currentEntry = bucket.shift()
      const currentSuggestion = currentEntry?.suggestion || null
      const nextSuggestion = messageSuggestion || currentSuggestion
      const nextCommitKey = getSuggestionCommitKey(nextSuggestion)
      const sameSuggestion =
        getSuggestionCommitKey(currentSuggestion) &&
        getSuggestionCommitKey(currentSuggestion) === getSuggestionCommitKey(messageSuggestion)

      return {
        ...currentEntry,
        // 新消息如果已经携带了 suggestion，永远优先使用新 suggestion，避免旧 proposalId 覆盖新卡片。
        suggestion: nextSuggestion,
        // 只有同一张卡片才保留 dismissed 状态，避免旧的隐藏标记误伤新 proposal。
        isDismissed:
          hiddenCommitKeys.has(nextCommitKey) ||
          (sameSuggestion ? Boolean(currentEntry?.isDismissed) : false),
      }
    }

    const nextCommitKey = getSuggestionCommitKey(messageSuggestion)
    return {
      isDismissed: hiddenCommitKeys.has(nextCommitKey),
      messageKey,
      suggestion: messageSuggestion,
    }
  })
}

export {
  buildMessageStableKeys,
  getSuggestionCommitKey,
  mergeMessageMeta,
  persistDismissedSuggestionKey,
  readDismissedSuggestionKeys,
}
