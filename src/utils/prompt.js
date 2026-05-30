import {
  buildDietSection,
  buildOneRmSection,
  buildProfileSection,
  buildTrainingSection,
  buildWeeklyPlanSection,
  buildWeightHistorySection,
} from './promptSections.js'
import { buildMetricsSection } from './promptMetricsSection.js'

/**
 * 为 AI 教练统一构建最新上下文，确保 PromptPreview 与实际注入共享同一份结构化指标口径。
 */
export function buildSystemPrompt(profile = {}, weeklyPlan = {}, dailyLog = {}, referenceDate) {
  return [
    '你是一位专业的力量训练与饮食管理顾问，风格直接、专业、有据可依。',
    '以下是用户当前的完整上下文，请基于这些数据提供具体、可执行的建议。',
    buildProfileSection(profile),
    buildOneRmSection(profile),
    buildWeeklyPlanSection(profile, weeklyPlan),
    buildWeightHistorySection(dailyLog),
    buildDietSection(dailyLog),
    buildTrainingSection(dailyLog),
    buildMetricsSection(profile, weeklyPlan, dailyLog, referenceDate),
  ].join('\n\n')
}
