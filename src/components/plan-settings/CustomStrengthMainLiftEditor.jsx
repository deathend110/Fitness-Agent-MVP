const MAIN_LIFT_FIELDS = [
  { key: 'squat', label: '深蹲 TM' },
  { key: 'bench', label: '卧推 TM' },
  { key: 'deadlift', label: '硬拉 TM' },
  { key: 'ohp', label: '推举 TM' },
]

function CustomStrengthMainLiftEditor({ draft, onChange }) {
  const mainLifts = draft?.mainLifts ?? {}

  function handleTmChange(liftKey, value) {
    onChange({
      ...draft,
      mainLifts: {
        ...mainLifts,
        [liftKey]: {
          ...(mainLifts[liftKey] ?? {}),
          tm: value,
        },
      },
    })
  }

  return (
    <div className="space-y-3 rounded-xl border border-slate-200 bg-white p-4">
      <div className="space-y-1">
        <p className="text-sm font-semibold text-slate-800">主项 TM</p>
        <p className="text-sm text-slate-500">
          这里只维护主项训练最大重量，后端会据此生成 custom strength 的周快照。
        </p>
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {MAIN_LIFT_FIELDS.map((field) => (
          <label className="space-y-1 text-sm" key={field.key}>
            <span className="font-medium text-slate-700">{field.label}</span>
            <input
              className="w-full rounded-lg border border-slate-200 px-3 py-2"
              onChange={(event) => handleTmChange(field.key, event.target.value)}
              placeholder="输入 TM"
              value={mainLifts[field.key]?.tm ?? ''}
            />
          </label>
        ))}
      </div>
    </div>
  )
}

export default CustomStrengthMainLiftEditor
