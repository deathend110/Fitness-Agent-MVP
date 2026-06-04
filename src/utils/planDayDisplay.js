function getExerciseCountLabel(count = 0) {
  if (count <= 0) {
    return '暂无动作'
  }

  return `已排 ${count} 个动作`
}

function getHistoryTitle(count = 0) {
  if (count <= 0) {
    return '保留历史动作'
  }

  return `保留 ${count} 个历史动作`
}

function getTrainingPreviewTitle(planType = '') {
  const normalizedType = typeof planType === 'string' ? planType.trim() : ''

  if (!normalizedType || normalizedType === 'rest') {
    return '训练日'
  }

  const allowedDisplayTypes = new Set(['腿日', '推日', '拉日', '有氧', '训练日'])
  return allowedDisplayTypes.has(normalizedType) ? normalizedType : '训练日'
}

function createHeaderModel(dayLabel = '', dateLabel = '') {
  return {
    eyebrow: '',
    title: dayLabel,
    meta: '',
    dateLabel,
  }
}

/**
 * 将计划日的展示判断集中到纯函数里，先稳定空状态与休息日语义，
 * 再让 React 组件只负责按模型渲染，避免 JSX 里散落条件分支。
 */
export function buildPlanDayDisplayModel({
  dayLabel = '',
  dateLabel = '',
  plan = {},
  isTrainingDay = false,
} = {}) {
  const exercises = Array.isArray(plan.exercises) ? plan.exercises : []
  const exerciseCount = exercises.length
  const isRestDay = !isTrainingDay

  if (isRestDay) {
    const hasHistoryExercises = exerciseCount > 0

    return {
      dayLabel,
      variant: 'rest',
      layout: hasHistoryExercises ? 'rest-history' : 'rest-compact',
      showAddExerciseButton: false,
      showDayTypeSection: true,
      dayTypeSectionVariant: hasHistoryExercises ? 'full' : 'compact',
      dayTypeQuickOptions: ['腿日', '推日', '拉日', '有氧'],
      showNoteEntry: false,
      headerBadgeLabel: '休息',
      header: createHeaderModel(dayLabel, dateLabel),
      historyHint:
        hasHistoryExercises
          ? '当前标记为休息日，历史动作仍保留，切回训练类型后可继续补充。'
          : null,
      preview: {
        eyebrow: '',
        title: hasHistoryExercises ? getHistoryTitle(exerciseCount) : '恢复优先',
        meta: hasHistoryExercises ? getExerciseCountLabel(exerciseCount) : '身体恢复 · 蓄力',
      },
      emptyState:
        hasHistoryExercises
          ? null
          : {
              tone: 'rest',
              title: '休息日',
              description: '恢复节奏，给下一次训练留出余量。',
              descriptionLines: ['身体恢复', '蓄力'],
            },
    }
  }

  return {
    dayLabel,
    variant: 'training',
    layout: 'training',
    showAddExerciseButton: true,
    showDayTypeSection: true,
    dayTypeSectionVariant: 'full',
    dayTypeQuickOptions: [],
    showNoteEntry: false,
    headerBadgeLabel: null,
    header: createHeaderModel(dayLabel, dateLabel),
    historyHint: null,
    preview: {
      eyebrow: exerciseCount === 0 ? '待补充' : '训练日',
      title: getTrainingPreviewTitle(plan.type),
      meta: getExerciseCountLabel(exerciseCount),
    },
    emptyState:
      exerciseCount === 0
          ? {
              tone: 'training-empty',
              title: '暂未安排动作',
              description: '先确定今天的训练重点，再补充动作。',
            }
          : null,
  }
}

export default buildPlanDayDisplayModel
