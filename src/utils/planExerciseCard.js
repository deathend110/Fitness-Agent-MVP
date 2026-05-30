import { formatCountDisplay, formatRpeDisplay, formatWeightDisplay, getExerciseKg } from './calc.js'

function isMainTier(exercise = {}) {
  return exercise.tier === 'main'
}

function buildVolumeLabel(exercise = {}) {
  const setsLabel = formatCountDisplay(exercise.sets)
  const repsLabel = formatCountDisplay(exercise.reps)

  return `${setsLabel} 组 x ${repsLabel} 次`
}

function buildNoteLabel(exercise = {}) {
  const note = typeof exercise.note === 'string' ? exercise.note.trim() : ''
  const hasRpe = exercise.rpe !== null && exercise.rpe !== undefined
  const rpeLabel = hasRpe ? formatRpeDisplay(exercise.rpe) : ''

  if (note && hasRpe) {
    return `${note} · RPE ${rpeLabel}`
  }

  if (note) {
    return note
  }

  if (hasRpe) {
    return `RPE ${rpeLabel}`
  }

  return '暂无备注'
}

export function buildPlanExerciseCardModel(exercise = {}, profile = {}) {
  const name = typeof exercise.name === 'string' && exercise.name.trim() ? exercise.name.trim() : '未命名动作'
  const tierTone = isMainTier(exercise) ? 'main' : 'accessory'
  const tierLabel = tierTone === 'main' ? '主项' : '辅项'
  const weightValue = getExerciseKg(exercise, profile.oneRM)
  const weightLabel = formatWeightDisplay(weightValue)
  const volumeLabel = buildVolumeLabel(exercise)
  const summaryLabel = `${weightLabel} · ${volumeLabel}`
  const noteLabel = buildNoteLabel(exercise)

  return {
    id: exercise.id ?? name,
    name,
    tierLabel,
    tierTone,
    weightLabel,
    volumeLabel,
    summaryLabel,
    noteLabel,
    metricItems: [
      { label: '重量', value: weightLabel },
      { label: '组次', value: volumeLabel },
    ],
    cardClassName:
      tierTone === 'main'
        ? 'border-fitloop-orange/35 bg-fitloop-orange/8'
        : 'border-fitloop-line/70 bg-fitloop-ink/50',
    tierBadgeClassName:
      tierTone === 'main'
        ? 'border-fitloop-orange/30 bg-fitloop-orange/15 text-fitloop-orange'
        : 'border-fitloop-line/70 bg-black/10 text-slate-300',
    titleClassName: 'text-slate-100',
    metricValueClassName: 'text-slate-100',
    noteClassName: tierTone === 'main' ? 'text-slate-300' : 'text-slate-400',
  }
}
