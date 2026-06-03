import {
  getBackendCoachBackgroundTask,
  requestBackendCoachReply,
  streamBackendCoachReply,
  submitBackendCoachBackgroundTask,
} from '../api/coachBackend.js'

const STREAM_TOOL_STATUS_LABELS = {
  get_chat_session_context: '整理对话上下文',
  get_daily_log: '读取今日日志',
  get_profile: '读取用户档案',
  get_recent_chat_history: '整理最近对话',
  get_weekly_plan: '读取训练计划',
}

function buildAgentPayload({
  files = [],
  fileIds,
  model,
  sessionId = null,
  thinking,
  userInput = '',
} = {}) {
  const normalizedFileIds = Array.isArray(fileIds)
    ? fileIds
    : files
        .map((file) => (Number.isInteger(file) ? file : file?.id))
        .filter(Number.isInteger)

  return {
    fileIds: normalizedFileIds,
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
    onProposal,
    onStatusLabel,
    onSuggestion,
    onText,
    signal,
    streamImpl = streamBackendCoachReply,
  } = {},
) {
  const payload = buildAgentPayload({ files, model, sessionId, thinking, userInput })
  return streamImpl(payload, {
    onProposal,
    sessionId,
    onSuggestion,
    signal,
    onDelta: (_delta, fullText) => {
      onText?.(fullText)
    },
    onToolStatus: (toolStatus) => {
      onStatusLabel?.(resolveCoachStreamStatusLabel(toolStatus))
    },
  })
}

export function resolveCoachStreamStatusLabel(toolStatus) {
  if (!toolStatus || typeof toolStatus !== 'object') {
    return ''
  }

  const message =
    typeof toolStatus.message === 'string'
      ? toolStatus.message.trim()
      : typeof toolStatus.label === 'string'
        ? toolStatus.label.trim()
        : ''

  if (message) {
    return message
  }

  const tool = typeof toolStatus.tool === 'string' ? toolStatus.tool.trim() : ''
  const status = typeof toolStatus.status === 'string' ? toolStatus.status.trim() : ''
  const toolLabel = STREAM_TOOL_STATUS_LABELS[tool] || ''

  if (status === 'succeeded' || status === 'completed') {
    return ''
  }

  if (toolLabel) {
    return `正在${toolLabel}`
  }

  if (status === 'pending' || status === 'running') {
    return '正在整理上下文'
  }

  return ''
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
    files: Array.isArray(task.files)
      ? task.files.map((file) => ({ id: file.id, name: file.name || file.originalName || '' }))
      : [],
    createdAt: new Date().toISOString(),
  }
}

function hasBackgroundTaskSourceUser(currentHistory = [], storedTask = {}) {
  const userContent = typeof storedTask?.userContent === 'string' ? storedTask.userContent.trim() : ''
  const sourceUserIndex = Number.isInteger(storedTask?.sourceUserIndex)
    ? storedTask.sourceUserIndex
    : null
  const sourceUser = sourceUserIndex === null
    ? null
    : currentHistory[sourceUserIndex]

  // 后台任务只能回填到原始用户消息仍存在的对话，避免旧任务污染新会话。
  return sourceUserIndex === null
    ? currentHistory.some((message) => message.role === 'user' && message.content === userContent)
    : sourceUser?.role === 'user' && sourceUser.content === userContent
}

export function shouldShowBackgroundCoachPendingIndicator({
  currentHistory = [],
  storedTask,
  taskStatus,
} = {}) {
  if (!storedTask?.taskId) {
    return false
  }

  if (taskStatus !== 'pending' && taskStatus !== 'running') {
    return false
  }

  return hasBackgroundTaskSourceUser(currentHistory, storedTask)
}

export function mergeBackgroundCoachReply({ currentHistory = [], reply, storedTask } = {}) {
  const assistantText = typeof reply?.text === 'string' ? reply.text.trim() : ''
  const suggestion = reply?.proposal ?? reply?.suggestion ?? null

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

  if (!hasBackgroundTaskSourceUser(currentHistory, storedTask)) {
    return {
      nextHistory: currentHistory,
      status: 'source_user_missing',
    }
  }

  const nextHistory = [
    ...currentHistory,
    { role: 'assistant', content: assistantText, suggestion },
  ]

  return {
    assistantIndex: nextHistory.length - 1,
    nextHistory,
    status: 'merged',
    suggestion,
  }
}

export async function getBackgroundCoachTask(
  taskId,
  { getTaskImpl = getBackendCoachBackgroundTask } = {},
) {
  return getTaskImpl(taskId)
}
