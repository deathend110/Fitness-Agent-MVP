import { formatDecimalDisplay } from './calc.js'

const TODAY_LOG_FIELDS = {
  weight: {
    key: 'weight',
    guardrailKey: 'today.weight',
    label: '体重',
    inputMode: 'decimal',
    step: '0.1',
    unit: 'kg',
    hint: '用于趋势统计与 BMI 推导',
  },
  kcal: {
    key: 'kcal',
    guardrailKey: 'today.kcal',
    label: '热量',
    inputMode: 'numeric',
    step: '1',
    unit: 'kcal',
    hint: '记录全天总摄入热量',
  },
  protein: {
    key: 'protein',
    guardrailKey: 'today.protein',
    label: '蛋白质',
    inputMode: 'numeric',
    step: '1',
    unit: 'g',
    hint: '优先记录全天蛋白质总量',
  },
  sleep: {
    key: 'sleep',
    guardrailKey: 'today.sleep',
    label: '睡眠',
    inputMode: 'decimal',
    step: '0.1',
    unit: 'h',
    hint: '按昨晚到今早的有效睡眠时长记录',
  },
  steps: {
    key: 'steps',
    guardrailKey: 'today.steps',
    label: '步数',
    inputMode: 'numeric',
    step: '1',
    unit: '步',
    hint: '用于活动量与 TDEE 判断',
  },
  tdee: {
    key: 'tdee',
    guardrailKey: 'today.tdee',
    label: 'TDEE',
    inputMode: 'numeric',
    step: '1',
    unit: 'kcal',
    hint: '当前实现支持手填或估算来源',
  },
  fatigue: {
    key: 'fatigue',
    guardrailKey: 'today.fatigue',
    label: '疲劳度',
    inputMode: 'numeric',
    step: '1',
    min: '1',
    max: '5',
    unit: '/ 5',
    hint: '使用 1 到 5 记录主观疲劳程度',
  },
}

function formatSummaryValue(value, suffix = '') {
  if (value === null || value === undefined || value === '') {
    return '未记录'
  }

  return `${formatDecimalDisplay(value)}${suffix}`
}

export function buildTodayLogFieldGroups() {
  return [
    {
      key: 'body',
      title: '身体数据',
      description: '快速记录今天最核心的身体反馈。',
      fields: [TODAY_LOG_FIELDS.weight],
    },
    {
      key: 'intake',
      title: '摄入记录',
      description: '围绕能量与蛋白质的当天输入。',
      fields: [TODAY_LOG_FIELDS.kcal, TODAY_LOG_FIELDS.protein],
    },
    {
      key: 'recovery',
      title: '恢复与状态',
      description: '记录训练恢复和活动负荷相关信息。',
      fields: [
        TODAY_LOG_FIELDS.sleep,
        TODAY_LOG_FIELDS.steps,
        TODAY_LOG_FIELDS.tdee,
        TODAY_LOG_FIELDS.fatigue,
      ],
    },
  ]
}

export function buildTodayLogSummaryItems(todayLog = {}) {
  return [
    { key: 'weight', label: '体重', value: formatSummaryValue(todayLog.weight, ' kg') },
    { key: 'kcal', label: '热量', value: formatSummaryValue(todayLog.kcal, ' kcal') },
    { key: 'protein', label: '蛋白质', value: formatSummaryValue(todayLog.protein, ' g') },
    { key: 'sleep', label: '睡眠', value: formatSummaryValue(todayLog.sleep, ' h') },
    { key: 'steps', label: '步数', value: formatSummaryValue(todayLog.steps, ' 步') },
    { key: 'tdee', label: 'TDEE', value: formatSummaryValue(todayLog.tdee, ' kcal') },
    { key: 'fatigue', label: '疲劳度', value: formatSummaryValue(todayLog.fatigue, ' / 5') },
    { key: 'trainingDone', label: '训练完成', value: todayLog.trainingDone ? '是' : '否' },
  ]
}
