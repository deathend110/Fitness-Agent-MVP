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

function buildMessageStableKeys(messages = []) {
  const sameMessageCounts = new Map()

  return messages.map((message) => {
    const baseKey = `${message?.role || 'unknown'}::${message?.content || ''}`
    const occurrence = sameMessageCounts.get(baseKey) || 0

    sameMessageCounts.set(baseKey, occurrence + 1)
    return `${baseKey}::${occurrence}`
  })
}

function mergeMessageMeta(messages = [], currentMeta = []) {
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
      const sameSuggestion =
        getSuggestionCommitKey(currentSuggestion) &&
        getSuggestionCommitKey(currentSuggestion) === getSuggestionCommitKey(messageSuggestion)

      return {
        ...currentEntry,
        // 新消息如果已经携带了 suggestion，永远优先使用新 suggestion，避免旧 proposalId 覆盖新卡片。
        suggestion: messageSuggestion || currentSuggestion,
        // 只有同一张卡片才保留 dismissed 状态，避免旧的隐藏标记误伤新 proposal。
        isDismissed: sameSuggestion ? Boolean(currentEntry?.isDismissed) : false,
      }
    }

    return {
      isDismissed: false,
      messageKey,
      suggestion: messageSuggestion,
    }
  })
}

export {
  buildMessageStableKeys,
  getSuggestionCommitKey,
  mergeMessageMeta,
}
