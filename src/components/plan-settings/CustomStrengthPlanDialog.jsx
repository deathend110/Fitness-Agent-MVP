import CustomStrengthPlanEditor from './CustomStrengthPlanEditor.jsx'

function CustomStrengthPlanDialog({
  canCreate,
  draft,
  isSubmitting,
  onChange,
  onClose,
  onSubmit,
  open = false,
}) {
  if (!open) {
    return null
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 px-4 py-6 backdrop-blur-sm">
      <div className="absolute inset-0" onClick={onClose} />

      <div className="relative z-10 flex max-h-[min(92vh,900px)] w-full max-w-[1080px] flex-col overflow-hidden rounded-[32px] border border-white/30 bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(248,250,255,0.96))] shadow-[0_24px_80px_rgba(15,23,42,0.28)]">
        <div className="flex items-start justify-between gap-4 border-b border-fitloop-line/70 px-6 py-5">
          <div>
            <p className="text-lg font-semibold text-slate-900">自定义力量周期计划</p>
            <p className="mt-1 text-sm text-slate-500">
              在弹窗内维护名称、开始日期、周数、主项 TM 和每周基础结构，避免计划设置页常驻展开。
            </p>
          </div>
          <button
            className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-fitloop-line bg-white text-slate-500 transition hover:border-fitloop-orange/30 hover:text-fitloop-orange"
            onClick={onClose}
            type="button"
          >
            ×
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-5">
          <CustomStrengthPlanEditor
            canCreate={canCreate}
            draft={draft}
            isSubmitting={isSubmitting}
            onChange={onChange}
            onSubmit={onSubmit}
          />
        </div>
      </div>
    </div>
  )
}

export default CustomStrengthPlanDialog
