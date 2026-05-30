function getButtonClassName(kind = 'secondary') {
  if (kind === 'danger') {
    return 'rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm font-medium text-rose-500 transition hover:border-rose-300 hover:bg-rose-100'
  }

  if (kind === 'primary') {
    return 'rounded-md border border-fitloop-orange bg-fitloop-orange px-3 py-2 text-sm font-medium text-white shadow-sm shadow-black/20 transition hover:brightness-110'
  }

  return 'rounded-md border border-fitloop-line bg-fitloop-panel px-3 py-2 text-sm font-medium text-slate-300 transition hover:border-fitloop-orange/30 hover:bg-fitloop-orange/8 hover:text-fitloop-orange'
}

function PlanDayCardButton({ children, className = '', kind = 'secondary', ...props }) {
  return (
    <button
      {...props}
      className={`${getButtonClassName(kind)} ${className}`.trim()}
      type={props.type ?? 'button'}
    >
      {children}
    </button>
  )
}

export default PlanDayCardButton
