function PlanRestDayPanel({ description, title }) {
  return (
    <div className="flex min-h-[10rem] flex-1 items-center justify-center rounded-2xl border border-fitloop-line/70 bg-fitloop-panel px-3 py-5 text-center">
      <div className="space-y-2">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full border border-fitloop-line/70 bg-fitloop-ink/30 text-slate-400">
          <span className="text-lg">Zz</span>
        </div>
        <p className="text-sm font-semibold text-slate-100">{title}</p>
        <p className="text-xs leading-6 text-slate-400">{description}</p>
      </div>
    </div>
  )
}

export default PlanRestDayPanel
