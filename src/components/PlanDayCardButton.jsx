function getButtonClassName(kind = 'secondary') {
  if (kind === 'danger') {
    return 'rounded-md border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-sm font-medium text-rose-200 transition hover:border-rose-400 hover:bg-rose-500/20'
  }

  if (kind === 'primary') {
    return 'rounded-md border border-fitloop-orange bg-fitloop-orange px-3 py-2 text-sm font-medium text-white transition hover:opacity-90'
  }

  return 'rounded-md border border-fitloop-line bg-fitloop-panel/70 px-3 py-2 text-sm font-medium text-slate-200 transition hover:border-slate-400 hover:text-white'
}

function PlanDayCardButton({ children, kind = 'secondary', ...props }) {
  return (
    <button {...props} className={getButtonClassName(kind)} type={props.type ?? 'button'}>
      {children}
    </button>
  )
}

export default PlanDayCardButton
