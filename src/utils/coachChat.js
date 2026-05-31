import { requestBackendCoachReply, streamBackendCoachReply } from '../api/coachBackend.js'
import { buildSystemPrompt } from './prompt.js'

function buildCoachMessages({ chatHistory = [], dailyLog = {}, profile = {}, userInput = '', weeklyPlan = {} }, buildPromptImpl) {
  const systemPrompt = buildPromptImpl(profile, weeklyPlan, dailyLog)

  return [
    { role: 'system', content: systemPrompt },
    ...chatHistory,
    { role: 'user', content: userInput.trim() },
  ]
}

export function shouldFallbackCoachStream({ hasReceivedText = false } = {}) {
  // 已经收到流式文本时，后端可能已经完成或即将完成本轮落库；此时自动重试普通请求会制造重复消息。
  return !hasReceivedText
}

export async function requestCoachReply(
  { chatHistory = [], dailyLog = {}, profile = {}, sessionId = null, userInput = '', weeklyPlan = {} },
  { buildPromptImpl = buildSystemPrompt, requestImpl = requestBackendCoachReply } = {},
) {
  const messages = buildCoachMessages(
    { chatHistory, dailyLog, profile, userInput, weeklyPlan },
    buildPromptImpl,
  )

  return requestImpl(messages, { sessionId })
}

// 后端已完成 DeepSeek 调用、SSE 转译和 JSON 建议解析；前端只负责构建上下文并展示增量文本。
export async function requestCoachReplyStream(
  { chatHistory = [], dailyLog = {}, profile = {}, sessionId = null, userInput = '', weeklyPlan = {} },
  {
    buildPromptImpl = buildSystemPrompt,
    onText,
    streamImpl = streamBackendCoachReply,
  } = {},
) {
  const messages = buildCoachMessages(
    { chatHistory, dailyLog, profile, userInput, weeklyPlan },
    buildPromptImpl,
  )
  return streamImpl(messages, {
    sessionId,
    onDelta: (_delta, fullText) => {
      onText?.(fullText)
    },
  })
}
