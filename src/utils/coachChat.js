import {
  getBackendCoachBackgroundTask,
  requestBackendCoachReply,
  streamBackendCoachReply,
  submitBackendCoachBackgroundTask,
} from '../api/coachBackend.js'

function buildAgentPayload({
  files = [],
  model,
  sessionId = null,
  thinking,
  userInput = '',
} = {}) {
  return {
    files,
    model,
    sessionId,
    thinking,
    userInput: userInput.trim(),
  }
}

export function shouldFallbackCoachStream({ hasReceivedText = false, isBackgroundFallback = false } = {}) {
  if (isBackgroundFallback) {
    return false
  }

  // 已经收到流式文本时，后端可能已经完成或即将完成本轮落库；此时自动重试普通请求会制造重复消息。
  return !hasReceivedText
}

export async function requestCoachReply(
  { files = [], model, sessionId = null, thinking, userInput = '' },
  { requestImpl = requestBackendCoachReply, signal } = {},
) {
  const payload = buildAgentPayload({ files, model, sessionId, thinking, userInput })
  return requestImpl(payload, { sessionId, signal })
}

// Phase 3 起后端负责 prompt 与上下文拼装；前端只传当前用户输入和会话配置。
export async function requestCoachReplyStream(
  { files = [], model, sessionId = null, thinking, userInput = '' },
  {
    onText,
    signal,
    streamImpl = streamBackendCoachReply,
  } = {},
) {
  const payload = buildAgentPayload({ files, model, sessionId, thinking, userInput })
  return streamImpl(payload, {
    sessionId,
    signal,
    onDelta: (_delta, fullText) => {
      onText?.(fullText)
    },
  })
}

export async function startBackgroundCoachReply(
  { files = [], model, sessionId = null, thinking, userInput = '' },
  {
    submitImpl = submitBackendCoachBackgroundTask,
  } = {},
) {
  const payload = buildAgentPayload({ files, model, sessionId, thinking, userInput })
  return submitImpl(payload, { sessionId })
}

export function buildBackgroundCoachTaskRecord(task, { sourceUserIndex = null, userInput = '' } = {}) {
  if (!task?.taskId) {
    return null
  }

  return {
    taskId: task.taskId,
    sessionId: Number.isInteger(task.sessionId) ? task.sessionId : null,
    sourceUserIndex: Number.isInteger(sourceUserIndex) ? sourceUserIndex : null,
    userContent: userInput.trim(),
    createdAt: new Date().toISOString(),
  }
}

export function mergeBackgroundCoachReply({ currentHistory = [], reply, storedTask } = {}) {
  const assistantText = typeof reply?.text === 'string' ? reply.text.trim() : ''
  const userContent = typeof storedTask?.userContent === 'string' ? storedTask.userContent.trim() : ''

  if (!assistantText) {
    return {
      nextHistory: currentHistory,
      status: 'empty_reply',
    }
  }

  const alreadyExists = currentHistory.some(
    (message) => message.role === 'assistant' && message.content === assistantText,
  )

  if (alreadyExists) {
    return {
      nextHistory: currentHistory,
      status: 'duplicate',
    }
  }

  const sourceUserIndex = Number.isInteger(storedTask?.sourceUserIndex)
    ? storedTask.sourceUserIndex
    : null
  const sourceUser = sourceUserIndex === null
    ? null
    : currentHistory[sourceUserIndex]
  const hasSourceUser = sourceUserIndex === null
    ? currentHistory.some((message) => message.role === 'user' && message.content === userContent)
    : sourceUser?.role === 'user' && sourceUser.content === userContent

  if (!hasSourceUser) {
    return {
      nextHistory: currentHistory,
      status: 'source_user_missing',
    }
  }

  const nextHistory = [
    ...currentHistory,
    { role: 'assistant', content: assistantText },
  ]

  return {
    assistantIndex: nextHistory.length - 1,
    nextHistory,
    status: 'merged',
    suggestion: reply?.suggestion ?? null,
  }
}

export async function getBackgroundCoachTask(
  taskId,
  { getTaskImpl = getBackendCoachBackgroundTask } = {},
) {
  return getTaskImpl(taskId)
}
