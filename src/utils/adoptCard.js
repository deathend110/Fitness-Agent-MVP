import {
  formatCountDisplay,
  formatPercentDisplay,
  formatRpeDisplay,
  formatWeightDisplay,
} from './calc.js'

const DAY_LABELS = {
  Monday: '周一',
  Tuesday: '周二',
  Wednesday: '周三',
  Thursday: '周四',
  Friday: '周五',
  Saturday: '周六',
  Sunday: '周日',
}

const FIELD_LABELS = {
  kg: '重量',
  note: '备注',
  pct: '训练百分比',
  reps: '次数',
  rpe: 'RPE',
  sets: '组数',
}

const ACTION_LABELS = {
  add: '新增',
  remove: '删除',
  update: '调整',
}

function formatDayLabel(day) {
  if (typeof day !== 'string' || !day.trim()) {
    return '待确认'
  }

  return DAY_LABELS[day] || day.trim()
}

function formatFieldLabel(field) {
  if (typeof field !== 'string' || !field.trim()) {
    return '字段'
  }

  return FIELD_LABELS[field] || field.trim()
}

function formatActionLabel(action) {
  if (typeof action !== 'string' || !action.trim()) {
    return '调整'
  }

  return ACTION_LABELS[action] || action.trim()
}

function formatChangeValue(field, value) {
  if (value === null || value === undefined || value === '') {
    return '未提供'
  }

  if (field === 'pct' && typeof value === 'number') {
    return formatPercentDisplay(value)
  }

  if (field === 'sets' && typeof value === 'number') {
    return `${formatCountDisplay(value)} 组`
  }

  if (field === 'reps' && typeof value === 'number') {
    return `${formatCountDisplay(value)} 次`
  }

  if (field === 'kg' && typeof value === 'number') {
    return formatWeightDisplay(value)
  }

  if (field === 'rpe' && typeof value === 'number') {
    return formatRpeDisplay(value)
  }

  return String(value)
}

/**
 * 将 AI suggestion 整理成卡片展示模型，避免 CoachTab 直接处理字段映射与文案格式。
 */
export function buildAdoptCardModel(suggestion) {
  if (!suggestion || typeof suggestion !== 'object') {
    return null
  }

  const summary = typeof suggestion.summary === 'string' ? suggestion.summary.trim() : ''
  const rawChanges = Array.isArray(suggestion.changes) ? suggestion.changes : []

  if (!summary && rawChanges.length === 0) {
    return null
  }

  return {
    dayLabel: formatDayLabel(suggestion.day),
    summary: summary || 'AI 给出了一条训练计划调整建议。',
    changes: rawChanges.map((change, index) => ({
      id: `${index}-${change.action || 'update'}-${change.exerciseName || 'exercise'}-${
        change.field || 'field'
      }`,
      actionLabel: formatActionLabel(change.action),
      exerciseName: change.exerciseName || '未命名动作',
      fieldLabel: formatFieldLabel(change.field),
      beforeLabel: formatChangeValue(change.field, change.oldValue),
      afterLabel: formatChangeValue(change.field, change.newValue),
    })),
  }
}
