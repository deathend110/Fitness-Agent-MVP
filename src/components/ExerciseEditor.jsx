import { useId } from 'react'
import {
  exerciseSetTypeOptions,
  exerciseTierOptions,
  exerciseWeightModes,
  getRpeFieldHint,
} from '../utils/exerciseForm.js'

function ExerciseEditor({ value, onChange, oneRmOptions = [], rpeError = null }) {
  const modeName = useId()
  const rpeHint = getRpeFieldHint(rpeError)

  function updateField(key, nextValue) {
    onChange({ ...value, [key]: nextValue })
  }

  function updateWeightMode(nextMode) {
    const firstRef = oneRmOptions[0]?.value ?? 'squat'

    onChange({
      ...value,
      weightMode: nextMode,
      ref1RM: nextMode === 'percentage' ? value.ref1RM || firstRef : value.ref1RM,
      pct: nextMode === 'percentage' ? value.pct || '0.75' : value.pct,
      kg: nextMode === 'fixed' ? value.kg || '' : value.kg,
    })
  }

  function updateSetType(nextSetType) {
    const nextRepsText =
      nextSetType === 'custom' ? value.repsText || value.reps : value.repsText || value.reps || ''

    onChange({
      ...value,
      setType: nextSetType,
      reps: nextSetType === 'custom' ? '' : value.reps,
      repsText: nextRepsText,
    })
  }

  return (
    <div className="rounded-xl border border-fitloop-line bg-fitloop-panel p-4 shadow-sm shadow-black/20">
      <div className="grid gap-4">
        <label className="space-y-2">
          <span className="text-sm text-slate-300">动作名称</span>
          <input
            className="w-full rounded-xl border border-fitloop-line bg-fitloop-panel px-3 py-2.5 text-slate-100 outline-none transition focus:border-fitloop-orange"
            onChange={(event) => updateField('name', event.target.value)}
            value={value.name}
          />
        </label>

        <label className="space-y-2">
          <span className="text-sm text-slate-300">动作层级</span>
          <select
            className="w-full rounded-xl border border-fitloop-line bg-fitloop-panel px-3 py-2.5 text-slate-100 outline-none transition focus:border-fitloop-orange"
            onChange={(event) => updateField('tier', event.target.value)}
            value={value.tier}
          >
            {exerciseTierOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <fieldset className="space-y-2">
          <legend className="text-sm text-slate-300">重量来源</legend>
          <div className="flex flex-wrap gap-2">
            {exerciseWeightModes.map((option) => {
              const checked = value.weightMode === option.value

              return (
                <label
                  className={`inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm transition ${
                    checked
                      ? 'border-fitloop-orange bg-fitloop-orange/15 text-fitloop-orange'
                      : 'border-fitloop-line bg-fitloop-panel text-slate-300'
                  }`}
                  key={option.value}
                >
                  <input
                    checked={checked}
                    onChange={() => updateWeightMode(option.value)}
                    type="radio"
                    name={modeName}
                    value={option.value}
                  />
                  {option.label}
                </label>
              )
            })}
          </div>
        </fieldset>

        {value.weightMode === 'percentage' ? (
          <>
            <label className="space-y-2">
              <span className="text-sm text-slate-300">参考 1RM</span>
              <select
                className="w-full rounded-xl border border-fitloop-line bg-fitloop-panel px-3 py-2.5 text-slate-100 outline-none transition focus:border-fitloop-orange"
                onChange={(event) => updateField('ref1RM', event.target.value)}
                value={value.ref1RM}
              >
                {oneRmOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="space-y-2">
              <span className="text-sm text-slate-300">百分比</span>
              <input
                className="w-full rounded-xl border border-fitloop-line bg-fitloop-panel px-3 py-2.5 text-slate-100 outline-none transition focus:border-fitloop-orange"
                inputMode="decimal"
                onChange={(event) => updateField('pct', event.target.value)}
                step="0.01"
                type="number"
                value={value.pct}
              />
            </label>
          </>
        ) : (
          <label className="space-y-2">
            <span className="text-sm text-slate-300">固定 kg</span>
            <input
              className="w-full rounded-xl border border-fitloop-line bg-fitloop-panel px-3 py-2.5 text-slate-100 outline-none transition focus:border-fitloop-orange"
              inputMode="decimal"
              onChange={(event) => updateField('kg', event.target.value)}
              step="0.5"
              type="number"
              value={value.kg}
            />
          </label>
        )}

        <label className="space-y-2">
          <span className="text-sm text-slate-300">组数</span>
          <input
            className="w-full rounded-xl border border-fitloop-line bg-fitloop-panel px-3 py-2.5 text-slate-100 outline-none transition focus:border-fitloop-orange"
            inputMode="numeric"
            onChange={(event) => updateField('sets', event.target.value)}
            step="1"
            type="number"
            value={value.sets}
          />
        </label>

        <label className="space-y-2">
          <span className="text-sm text-slate-300">组型</span>
          <select
            className="w-full rounded-xl border border-fitloop-line bg-fitloop-panel px-3 py-2.5 text-slate-100 outline-none transition focus:border-fitloop-orange"
            onChange={(event) => updateSetType(event.target.value)}
            value={value.setType}
          >
            {exerciseSetTypeOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        {value.setType === 'custom' ? (
          <label className="space-y-2">
            <span className="text-sm text-slate-300">次数表达</span>
            <input
              className="w-full rounded-xl border border-fitloop-line bg-fitloop-panel px-3 py-2.5 text-slate-100 outline-none transition focus:border-fitloop-orange"
              onChange={(event) => updateField('repsText', event.target.value)}
              placeholder="例如：6-8、AMRAP、阶梯"
              value={value.repsText}
            />
          </label>
        ) : (
          <label className="space-y-2">
            <span className="text-sm text-slate-300">次数</span>
            <input
              className="w-full rounded-xl border border-fitloop-line bg-fitloop-panel px-3 py-2.5 text-slate-100 outline-none transition focus:border-fitloop-orange"
              inputMode="numeric"
              onChange={(event) => updateField('reps', event.target.value)}
              step="1"
              type="number"
              value={value.reps}
            />
          </label>
        )}

        {value.setType === 'custom' ? (
          <p className="self-end text-xs leading-6 text-slate-400">
            自定义组型会以“次数表达”为唯一来源，便于兼容 AMRAP、范围次数和周期计划写法。
          </p>
        ) : null}

        <label className="space-y-2">
          <span className="text-sm text-slate-300">RPE</span>
          <input
            className="w-full rounded-xl border border-fitloop-line bg-fitloop-panel px-3 py-2.5 text-slate-100 outline-none transition focus:border-fitloop-orange"
            aria-invalid={Boolean(rpeError)}
            inputMode="decimal"
            max="10"
            min="0"
            onChange={(event) => updateField('rpe', event.target.value)}
            step="0.5"
            type="number"
            value={value.rpe}
          />
          <p className={`text-xs ${rpeError ? 'text-rose-300' : 'text-slate-400'}`}>{rpeHint}</p>
        </label>
      </div>

      <label className="mt-4 block space-y-2">
        <span className="text-sm text-slate-300">备注</span>
        <textarea
          className="min-h-24 w-full rounded-xl border border-fitloop-line bg-fitloop-panel px-3 py-2.5 text-slate-100 outline-none transition focus:border-fitloop-orange"
          onChange={(event) => updateField('note', event.target.value)}
          value={value.note}
        />
      </label>
    </div>
  )
}

export default ExerciseEditor
