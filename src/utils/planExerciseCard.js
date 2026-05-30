import {
  formatCountDisplay,
  formatPercentDisplay,
  formatRpeDisplay,
  formatWeightDisplay,
  getExerciseKg,
  toNumber,
} from './calc.js'

const ONE_RM_LABELS = {
  squat: '深蹲',
  bench: '卧推',
  deadlift: '硬拉',
}

function isMainTier(exercise = {}) {
  return exercise.tier === 'main'
}

function hasValue(value) {
  return value !== null && value !== undefined && `${value}`.trim() !== ''
}

function isBodyweightExercise(exercise = {}) {
  return !hasValue(exercise.ref1RM) && !hasValue(exercise.kg)
}

function getExerciseName(exercise = {}) {
  return typeof exercise.name === 'string' && exercise.name.trim() ? exercise.name.trim() : '未命名动作'
}

function buildVolumeLabel(exercise = {}) {
  const setsLabel = formatCountDisplay(exercise.sets)
  const repsLabel = formatCountDisplay(exercise.reps)

  return `${setsLabel} 组 x ${repsLabel} 次`
}

function buildEffortLabel(exercise = {}) {
  if (exercise.rpe === null || exercise.rpe === undefined) {
    return '未填写 RPE'
  }

  return `RPE ${formatRpeDisplay(exercise.rpe)}`
}

function buildNoteLabel(exercise = {}) {
  const note = typeof exercise.note === 'string' ? exercise.note.trim() : ''
  const hasRpe = exercise.rpe !== null && exercise.rpe !== undefined

  if (note && hasRpe) {
    return `${note} · RPE ${formatRpeDisplay(exercise.rpe)}`
  }

  if (note) {
    return note
  }

  if (!hasRpe) {
    return '暂无备注'
  }

  return `RPE ${formatRpeDisplay(exercise.rpe)}`
}

// 这里统一把“实际重量”和“负重来源说明”拆开，方便卡片在不加横向滚动的前提下压缩布局。
function buildLoadSummary(exercise = {}, profile = {}) {
  if (hasValue(exercise.ref1RM)) {
    const oneRmValue = toNumber(profile.oneRM?.[exercise.ref1RM])
    const exerciseKg = getExerciseKg(exercise, profile.oneRM)
    const refLabel = ONE_RM_LABELS[exercise.ref1RM] ?? '参考 1RM'

    return {
      weightLabel: formatWeightDisplay(exerciseKg),
      loadDetailLabel: `${refLabel} 1RM ${formatWeightDisplay(oneRmValue)} × ${formatPercentDisplay(exercise.pct)}`,
      loadBadgeLabel: '百分比',
    }
  }

  if (hasValue(exercise.kg)) {
    return {
      weightLabel: formatWeightDisplay(exercise.kg),
      loadDetailLabel: '固定重量',
      loadBadgeLabel: '固定 kg',
    }
  }

  if (isBodyweightExercise(exercise)) {
    return {
      weightLabel: '自重',
      loadDetailLabel: '自重动作',
      loadBadgeLabel: '自重',
    }
  }

  return {
    weightLabel: formatWeightDisplay(0),
    loadDetailLabel: '未填写负重',
    loadBadgeLabel: '待补充',
  }
}

function buildMetricItems({ weightLabel, loadDetailLabel, volumeLabel, effortLabel }) {
  return [
    {
      key: 'load',
      label: '负重',
      value: weightLabel,
      detail: loadDetailLabel,
    },
    {
      key: 'volume',
      label: '组次',
      value: volumeLabel,
      detail: '训练安排',
    },
    {
      key: 'effort',
      label: 'RPE',
      value: effortLabel,
      detail: '主观强度',
    },
  ]
}

export function buildPlanExerciseCardModel(exercise = {}, profile = {}) {
  const name = getExerciseName(exercise)
  const tierTone = isMainTier(exercise) ? 'main' : 'accessory'
  const tierLabel = tierTone === 'main' ? '主项' : '辅项'
  const { weightLabel, loadDetailLabel, loadBadgeLabel } = buildLoadSummary(exercise, profile)
  const volumeLabel = buildVolumeLabel(exercise)
  const effortLabel = buildEffortLabel(exercise)
  const noteLabel = buildNoteLabel(exercise)
  const noteEmpty = noteLabel === '暂无备注'

  return {
    id: exercise.id ?? name,
    name,
    tierLabel,
    tierTone,
    weightLabel,
    loadDetailLabel,
    loadBadgeLabel,
    volumeLabel,
    effortLabel,
    summaryLabel: `${weightLabel} · ${volumeLabel} · ${effortLabel}`,
    noteLabel,
    noteEmpty,
    metricItems: buildMetricItems({
      weightLabel,
      loadDetailLabel,
      volumeLabel,
      effortLabel,
    }),
    cardClassName:
      tierTone === 'main'
        ? 'border-fitloop-orange/35 bg-fitloop-orange/8'
        : 'border-fitloop-line/70 bg-fitloop-ink/50',
    tierBadgeClassName:
      tierTone === 'main'
        ? 'border-fitloop-orange/30 bg-fitloop-orange/15 text-fitloop-orange'
        : 'border-fitloop-line/70 bg-black/10 text-slate-300',
    loadBadgeClassName:
      tierTone === 'main'
        ? 'border-fitloop-orange/30 bg-fitloop-orange/10 text-fitloop-orange'
        : 'border-fitloop-line/70 bg-fitloop-panel text-slate-400',
    titleClassName: 'text-slate-100',
    metricValueClassName: 'text-slate-100',
    noteClassName: noteEmpty ? 'text-slate-400 italic' : 'text-slate-300',
    actionSlotClassName:
      'flex h-8 w-8 items-center justify-center rounded-full border border-fitloop-line/70 bg-fitloop-panel text-sm font-semibold text-slate-400 transition hover:border-fitloop-orange/30 hover:text-fitloop-orange',
  }
}
