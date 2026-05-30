function PlanRestDayPanel({ description, descriptionLines, title }) {
  const lines = Array.isArray(descriptionLines) && descriptionLines.length > 0
    ? descriptionLines
    : description
      ? description.split(/[，、]/).filter(Boolean)
      : []

  return (
    <div className="flex flex-1 items-center justify-center px-1 py-3 text-center">
      <div className="flex flex-col items-center">
        <svg
          aria-hidden="true"
          className="mb-2 h-12 w-12 text-slate-500/35"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.2"
          viewBox="0 0 24 24"
        >
          <path d="M4 9h16M4 9a2 2 0 00-2 2v5a2 2 0 002 2h16a2 2 0 002-2v-5a2 2 0 00-2-2M4 9V6a2 2 0 012-2h12a2 2 0 012 2v3M6 18v2m12-2v2" />
        </svg>
        <p className="text-xs font-semibold text-slate-200">{title}</p>
        <div className="mt-1 space-y-0.5 text-[11px] leading-4 text-slate-400">
          {lines.map((line) => (
            <p key={line}>{line}</p>
          ))}
        </div>
      </div>
    </div>
  )
}

export default PlanRestDayPanel
