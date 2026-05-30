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

  return `${setsLabel} 组 × ${repsLabel} 次`
}

function buildEffortLabel(exercise = {}) {
  if (exercise.rpe === null || exercise.rpe === undefined) {
    return '未填写 RPE'
  }

  return `RPE ${formatRpeDisplay(exercise.rpe)}`
}

function buildNoteLabel(exercise = {}) {
  const note = typeof exercise.note === 'string' ? exercise.note.trim() : ''

  return note || '暂无备注'
}

function splitWeightLabel(weightLabel) {
  if (weightLabel === '自重') {
    return {
      weightValue: '自重',
      weightUnitLabel: '',
    }
  }

  const matched = /^(.+?)(kg)$/.exec(weightLabel)

  if (!matched) {
    return {
      weightValue: weightLabel,
      weightUnitLabel: '',
    }
  }

  return {
    weightValue: matched[1],
    weightUnitLabel: matched[2],
  }
}

// 这里统一生成“重量主显示”和“来源说明”，让组件只负责排版，不再临时拼接文案。
function buildLoadSummary(exercise = {}, profile = {}) {
  if (hasValue(exercise.ref1RM)) {
    const oneRmValue = toNumber(profile.oneRM?.[exercise.ref1RM])
    const exerciseKg = getExerciseKg(exercise, profile.oneRM)
    const refLabel = ONE_RM_LABELS[exercise.ref1RM] ?? '参考'

    return {
      weightLabel: formatWeightDisplay(exerciseKg),
      topMetaLabel: `${refLabel} 1RM ${formatWeightDisplay(oneRmValue)} × ${formatPercentDisplay(exercise.pct)}`,
      loadDetailLabel: `${refLabel} 1RM ${formatWeightDisplay(oneRmValue)} × ${formatPercentDisplay(exercise.pct)}`,
      loadBadgeLabel: '百分比',
      topMetaMuted: false,
    }
  }

  if (hasValue(exercise.kg)) {
    return {
      weightLabel: formatWeightDisplay(exercise.kg),
      topMetaLabel: '',
      loadDetailLabel: '固定重量',
      loadBadgeLabel: '固定 kg',
      topMetaMuted: true,
    }
  }

  if (isBodyweightExercise(exercise)) {
    return {
      weightLabel: '自重',
      topMetaLabel: '自重动作',
      loadDetailLabel: '自重动作',
      loadBadgeLabel: '自重',
      topMetaMuted: false,
    }
  }

  return {
    weightLabel: formatWeightDisplay(0),
    topMetaLabel: '待补充负重',
    loadDetailLabel: '待补充负重',
    loadBadgeLabel: '待补充',
    topMetaMuted: false,
  }
}

export function buildPlanExerciseCardModel(exercise = {}, profile = {}) {
  const name = getExerciseName(exercise)
  const tierTone = isMainTier(exercise) ? 'main' : 'accessory'
  const tierLabel = tierTone === 'main' ? '主项' : '辅项'
  const { weightLabel, topMetaLabel, loadDetailLabel, loadBadgeLabel, topMetaMuted } =
    buildLoadSummary(exercise, profile)
  const volumeLabel = buildVolumeLabel(exercise)
  const effortLabel = buildEffortLabel(exercise)
  const noteLabel = buildNoteLabel(exercise)
  const noteEmpty = noteLabel === '暂无备注'
  const { weightValue, weightUnitLabel } = splitWeightLabel(weightLabel)

  return {
    id: exercise.id ?? name,
    name,
    tierLabel,
    tierTone,
    topMetaLabel,
    topMetaMuted,
    weightLabel,
    weightValue,
    weightUnitLabel,
    loadDetailLabel,
    loadBadgeLabel,
    volumeLabel,
    effortLabel,
    volumePill: {
      label: '组次',
      value: volumeLabel,
    },
    effortPill: {
      label: 'RPE',
      value: effortLabel,
    },
    summaryLabel: `${weightLabel} · ${volumeLabel} · ${effortLabel}`,
    noteLabel,
    noteEmpty,
    cardClassName:
      tierTone === 'main'
        ? 'border-fitloop-orange/35 bg-fitloop-orange/8'
        : 'border-fitloop-line/70 bg-fitloop-ink/50',
    tierBadgeClassName:
      tierTone === 'main'
        ? 'border-fitloop-orange/30 bg-fitloop-orange text-white'
        : 'border-sky-500/30 bg-sky-600 text-white',
    topMetaClassName: topMetaMuted ? 'text-transparent' : 'text-slate-400',
    titleClassName: 'text-slate-100',
    weightValueClassName: 'text-sky-400',
    weightUnitClassName: 'text-sky-400/80',
    volumePillClassName: 'border-fitloop-line/70 bg-fitloop-panel text-slate-300',
    effortPillClassName: 'border-fitloop-line/70 bg-fitloop-panel text-slate-400',
    noteClassName: noteEmpty ? 'text-slate-500' : 'text-slate-400',
    actionSlotClassName:
      'flex h-7 w-7 items-center justify-center rounded-md text-base leading-none text-slate-500 transition hover:bg-white/5 hover:text-slate-200',
  }
}
