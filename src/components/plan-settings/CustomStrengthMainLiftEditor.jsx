import { useState } from 'react'
import {
  clampNumericInputDraft,
  getNumericFieldGuardrail,
} from '../../utils/numericFieldGuardrails.js'

const MAIN_LIFT_FIELDS = [
  { key: 'squat', label: '深蹲 TM' },
  { key: 'bench', label: '卧推 TM' },
  { key: 'deadlift', label: '硬拉 TM' },
  { key: 'ohp', label: '推举 TM' },
]

function CustomStrengthMainLiftEditor({ draft, onChange }) {
  const mainLifts = draft?.mainLifts ?? {}
  const [fieldErrors, setFieldErrors] = useState({})

  function handleTmChange(liftKey, value) {
    const fieldKey = `plan.custom.${liftKey}.tm`
    const { nextValue, error } = clampNumericInputDraft({
      fieldKey,
      previousValue: mainLifts[liftKey]?.tm ?? '',
      nextValue: value,
    })

    onChange({
      ...draft,
      mainLifts: {
        ...mainLifts,
        [liftKey]: {
          ...(mainLifts[liftKey] ?? {}),
          tm: nextValue,
        },
      },
    })

    setFieldErrors((current) => ({
      ...current,
      [fieldKey]: error,
    }))
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
              aria-invalid={Boolean(fieldErrors[`plan.custom.${field.key}.tm`])}
              className="w-full rounded-lg border border-slate-200 px-3 py-2"
              onChange={(event) => handleTmChange(field.key, event.target.value)}
              max={getNumericFieldGuardrail(`plan.custom.${field.key}.tm`)?.max}
              min={getNumericFieldGuardrail(`plan.custom.${field.key}.tm`)?.min}
              placeholder="输入 TM"
              step={getNumericFieldGuardrail(`plan.custom.${field.key}.tm`)?.step}
              type="number"
              value={mainLifts[field.key]?.tm ?? ''}
            />
            <span className="text-xs text-slate-400">
              {fieldErrors[`plan.custom.${field.key}.tm`] ?? '输入 TM'}
            </span>
          </label>
        ))}
      </div>
    </div>
  )
}

export default CustomStrengthMainLiftEditor
