function getToneClassName(tone = 'training-empty') {
  if (tone === 'rest') {
    return 'border-slate-700/40 bg-slate-900/30 text-slate-300'
  }

  return 'border-fitloop-line/80 bg-fitloop-ink/40 text-slate-200'
}

function PlanDayEmptyState({ description, title, tone = 'training-empty' }) {
  return (
    <div className={`rounded-2xl border px-4 py-5 text-center ${getToneClassName(tone)}`}>
      <div className="space-y-2">
        <p className="text-sm font-semibold">{title}</p>
        <p className="text-xs leading-6 text-slate-400">{description}</p>
      </div>
    </div>
  )
}

export default PlanDayEmptyState
