export const CHAT_HISTORY_LIMIT = 20

/**
 * 统一追加聊天消息，并将历史裁剪到最近 20 条，避免本地缓存无限增长。
 */
export function appendChatMessages(history = [], newMessages = []) {
  return [...history, ...newMessages].slice(-CHAT_HISTORY_LIMIT)
}
