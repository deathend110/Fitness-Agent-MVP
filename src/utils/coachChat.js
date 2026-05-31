import {
  getBackendCoachBackgroundTask,
  requestBackendCoachReply,
  streamBackendCoachReply,
  submitBackendCoachBackgroundTask,
} from '../api/coachBackend.js'
import { buildSystemPrompt } from './prompt.js'

function buildCoachMessages({ chatHistory = [], dailyLog = {}, profile = {}, userInput = '', weeklyPlan = {} }, buildPromptImpl) {
  const systemPrompt = buildPromptImpl(profile, weeklyPlan, dailyLog)

  return [
    { role: 'system', content: systemPrompt },
    ...chatHistory,
    { role: 'user', content: userInput.trim() },
  ]
}

export function shouldFallbackCoachStream({ hasReceivedText = false, isBackgroundFallback = false } = {}) {
  if (isBackgroundFallback) {
    return false
  }

  // 已经收到流式文本时，后端可能已经完成或即将完成本轮落库；此时自动重试普通请求会制造重复消息。
  return !hasReceivedText
}

export async function requestCoachReply(
  { chatHistory = [], dailyLog = {}, profile = {}, sessionId = null, userInput = '', weeklyPlan = {} },
  { buildPromptImpl = buildSystemPrompt, requestImpl = requestBackendCoachReply, signal } = {},
) {
  const messages = buildCoachMessages(
    { chatHistory, dailyLog, profile, userInput, weeklyPlan },
    buildPromptImpl,
  )

  return requestImpl(messages, { sessionId, signal })
}

// 后端已完成 DeepSeek 调用、SSE 转译和 JSON 建议解析；前端只负责构建上下文并展示增量文本。
export async function requestCoachReplyStream(
  { chatHistory = [], dailyLog = {}, profile = {}, sessionId = null, userInput = '', weeklyPlan = {} },
  {
    buildPromptImpl = buildSystemPrompt,
    onText,
    signal,
    streamImpl = streamBackendCoachReply,
  } = {},
) {
  const messages = buildCoachMessages(
    { chatHistory, dailyLog, profile, userInput, weeklyPlan },
    buildPromptImpl,
  )
  return streamImpl(messages, {
    sessionId,
    signal,
    onDelta: (_delta, fullText) => {
      onText?.(fullText)
    },
  })
}

export async function startBackgroundCoachReply(
  { chatHistory = [], dailyLog = {}, profile = {}, sessionId = null, userInput = '', weeklyPlan = {} },
  {
    buildPromptImpl = buildSystemPrompt,
    submitImpl = submitBackendCoachBackgroundTask,
  } = {},
) {
  const messages = buildCoachMessages(
    { chatHistory, dailyLog, profile, userInput, weeklyPlan },
    buildPromptImpl,
  )

  return submitImpl(messages, { sessionId })
}

export function buildBackgroundCoachTaskRecord(task, { userInput = '' } = {}) {
  if (!task?.taskId) {
    return null
  }

  return {
    taskId: task.taskId,
    sessionId: Number.isInteger(task.sessionId) ? task.sessionId : null,
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

  const hasSourceUser = currentHistory.some(
    (message) => message.role === 'user' && message.content === userContent,
  )

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
