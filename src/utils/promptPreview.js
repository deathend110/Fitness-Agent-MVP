import { buildSystemPrompt } from './prompt.js'

export const promptPreviewLabels = {
  title: '当前上下文预览',
  description: '展示本次发送前注入给 AI 的 system prompt。',
  codeLabel: 'buildSystemPrompt()',
}

/**
 * 统一整理上下文预览面板所需的数据，避免 CoachTab 同时承担 prompt 构建和展示文案职责。
 */
export function buildPromptPreviewModel(profile = {}, weeklyPlan = {}, dailyLog = {}) {
  return {
    ...promptPreviewLabels,
    defaultExpanded: false,
    promptText: buildSystemPrompt(profile, weeklyPlan, dailyLog),
  }
}
