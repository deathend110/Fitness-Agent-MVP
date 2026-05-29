import { requestDeepSeekChat } from '../api/deepseek.js'
import { buildSystemPrompt } from './prompt.js'

/**
 * 组装一次 AI 教练对话请求，确保每次发送前都注入最新 system prompt。
 */
export async function requestCoachReply(
  { chatHistory = [], dailyLog = {}, profile = {}, userInput = '', weeklyPlan = {} },
  { buildPromptImpl = buildSystemPrompt, requestImpl = requestDeepSeekChat } = {},
) {
  const systemPrompt = buildPromptImpl(profile, weeklyPlan, dailyLog)
  const messages = [
    { role: 'system', content: systemPrompt },
    ...chatHistory,
    { role: 'user', content: userInput.trim() },
  ]

  return requestImpl(messages)
}
