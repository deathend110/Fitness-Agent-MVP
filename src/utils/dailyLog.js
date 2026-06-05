import { getTodayStr } from './calc.js'
import { validateNumericFieldValue } from './numericFieldGuardrails.js'

function toFormValue(value) {
  if (value === null || value === undefined) {
    return ''
  }

  return `${value}`
}

function toNullableNumber(value) {
  if (value === null || value === undefined) {
    return null
  }

  const trimmedValue = `${value}`.trim()

  if (!trimmedValue) {
    return null
  }

  const parsed = Number(trimmedValue)
  return Number.isFinite(parsed) ? parsed : null
}

/**
 * 今日日志在落库前统一走共享 guardrail，保证手填和导入数据都遵守同一边界。
 */
function toGuardedNullableNumber(fieldKey, value) {
  if (value === null || value === undefined) {
    return null
  }

  const trimmedValue = `${value}`.trim()
  if (!trimmedValue) {
    return null
  }

  if (validateNumericFieldValue(fieldKey, trimmedValue)) {
    return null
  }

  return toNullableNumber(trimmedValue)
}

/**
 * 将已保存的今日日志转成表单草稿，保证可选字段为空时也能稳定渲染受控输入。
 */
export function readTodayLogForm(entry = {}) {
  return {
    weight: toFormValue(entry.weight),
    kcal: toFormValue(entry.kcal),
    protein: toFormValue(entry.protein),
    sleep: toFormValue(entry.sleep),
    steps: toFormValue(entry.steps),
    fatigue: toFormValue(entry.fatigue),
    tdee: toFormValue(entry.tdee),
    trainingDone: Boolean(entry.trainingDone),
    trainingNotes: entry.trainingNotes ?? '',
  }
}

/**
 * 统一规范化今日日志的数据形态，避免页面摘要和后续上下文读取遇到 undefined。
 */
export function normalizeTodayLogEntry(form = {}) {
  return {
    weight: toGuardedNullableNumber('today.weight', form.weight),
    kcal: toGuardedNullableNumber('today.kcal', form.kcal),
    protein: toGuardedNullableNumber('today.protein', form.protein),
    sleep: toGuardedNullableNumber('today.sleep', form.sleep),
    steps: toGuardedNullableNumber('today.steps', form.steps),
    fatigue: toGuardedNullableNumber('today.fatigue', form.fatigue),
    tdee: toGuardedNullableNumber('today.tdee', form.tdee),
    trainingDone: Boolean(form.trainingDone),
    trainingNotes: `${form.trainingNotes ?? ''}`.trim(),
  }
}

/**
 * 使用当天日期作为键写回 dailyLog，保持其他日期记录不受影响。
 */
export function buildTodayLogPayload(dailyLog = {}, today = getTodayStr(), form = {}) {
  return {
    ...dailyLog,
    [today]: normalizeTodayLogEntry(form),
  }
}
