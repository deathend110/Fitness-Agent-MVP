import { useEffect, useId, useState } from 'react'
import {
  exerciseSetTypeOptions,
  exerciseTierOptions,
  exerciseWeightModes,
  getRpeFieldHint,
} from '../utils/exerciseForm.js'
import {
  clampNumericInputDraft,
  getNumericFieldGuardrail,
} from '../utils/numericFieldGuardrails.js'

function ExerciseEditor({ value, onChange, oneRmOptions = [], rpeError = null }) {
  const modeName = useId()
  const [fieldErrors, setFieldErrors] = useState({})
  const kgGuardrail = getNumericFieldGuardrail('plan.exercise.kg')
  const pctGuardrail = getNumericFieldGuardrail('plan.exercise.pct')
  const setsGuardrail = getNumericFieldGuardrail('plan.exercise.sets')
  const repsGuardrail = getNumericFieldGuardrail('plan.exercise.reps')
  const rpeGuardrail = getNumericFieldGuardrail('plan.exercise.rpe')
  const rpeHint = getRpeFieldHint(fieldErrors['plan.exercise.rpe'] ?? rpeError)

  useEffect(() => {
    setFieldErrors((current) => {
      const nextErrors = { ...current }
      if (value.weightMode !== 'fixed') {
        delete nextErrors['plan.exercise.kg']
      }
      if (value.weightMode !== 'percentage') {
        delete nextErrors['plan.exercise.pct']
      }
      if (value.setType === 'custom') {
        delete nextErrors['plan.exercise.reps']
      }
      return nextErrors
    })
  }, [value.setType, value.weightMode])

  function updateField(key, nextValue) {
    onChange({ ...value, [key]: nextValue })
  }

  function updateGuardedField(key, fieldKey, nextValue) {
    const { nextValue: guardedValue, error } = clampNumericInputDraft({
      fieldKey,
      previousValue: value[key],
      nextValue,
    })

    onChange({ ...value, [key]: guardedValue })
    setFieldErrors((current) => ({
      ...current,
      [fieldKey]: error,
    }))
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
          <legend className="text-sm text-slate-300">负重来源</legend>
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
                    name={modeName}
                    onChange={() => updateWeightMode(option.value)}
                    type="radio"
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
                aria-invalid={Boolean(fieldErrors['plan.exercise.pct'])}
                className="w-full rounded-xl border border-fitloop-line bg-fitloop-panel px-3 py-2.5 text-slate-100 outline-none transition focus:border-fitloop-orange"
                inputMode="decimal"
                max={pctGuardrail.max}
                min={pctGuardrail.min}
                onChange={(event) => updateGuardedField('pct', 'plan.exercise.pct', event.target.value)}
                step={pctGuardrail.step}
                type="number"
                value={value.pct}
              />
              <p className="text-xs text-slate-400">
                {fieldErrors['plan.exercise.pct'] ?? `范围 ${pctGuardrail.min}-${pctGuardrail.max}`}
              </p>
            </label>
          </>
        ) : (
          <label className="space-y-2">
            <span className="text-sm text-slate-300">固定 kg</span>
            <input
              aria-invalid={Boolean(fieldErrors['plan.exercise.kg'])}
              className="w-full rounded-xl border border-fitloop-line bg-fitloop-panel px-3 py-2.5 text-slate-100 outline-none transition focus:border-fitloop-orange"
              inputMode="decimal"
              max={kgGuardrail.max}
              min={kgGuardrail.min}
              onChange={(event) => updateGuardedField('kg', 'plan.exercise.kg', event.target.value)}
              step={kgGuardrail.step}
              type="number"
              value={value.kg}
            />
            <p className="text-xs text-slate-400">
              {fieldErrors['plan.exercise.kg'] ?? `范围 ${kgGuardrail.min}-${kgGuardrail.max}kg`}
            </p>
          </label>
        )}

        <label className="space-y-2">
          <span className="text-sm text-slate-300">组数</span>
          <input
            aria-invalid={Boolean(fieldErrors['plan.exercise.sets'])}
            className="w-full rounded-xl border border-fitloop-line bg-fitloop-panel px-3 py-2.5 text-slate-100 outline-none transition focus:border-fitloop-orange"
            inputMode="numeric"
            max={setsGuardrail.max}
            min={setsGuardrail.min}
            onChange={(event) => updateGuardedField('sets', 'plan.exercise.sets', event.target.value)}
            step={setsGuardrail.step}
            type="number"
            value={value.sets}
          />
          <p className="text-xs text-slate-400">
            {fieldErrors['plan.exercise.sets'] ?? `范围 ${setsGuardrail.min}-${setsGuardrail.max} 组`}
          </p>
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
              placeholder="例如：6-8、AMRAP、阶梯组"
              value={value.repsText}
            />
          </label>
        ) : (
          <label className="space-y-2">
            <span className="text-sm text-slate-300">次数</span>
            <input
              aria-invalid={Boolean(fieldErrors['plan.exercise.reps'])}
              className="w-full rounded-xl border border-fitloop-line bg-fitloop-panel px-3 py-2.5 text-slate-100 outline-none transition focus:border-fitloop-orange"
              inputMode="numeric"
              max={repsGuardrail.max}
              min={repsGuardrail.min}
              onChange={(event) => updateGuardedField('reps', 'plan.exercise.reps', event.target.value)}
              step={repsGuardrail.step}
              type="number"
              value={value.reps}
            />
            <p className="text-xs text-slate-400">
              {fieldErrors['plan.exercise.reps'] ?? `范围 ${repsGuardrail.min}-${repsGuardrail.max} 次`}
            </p>
          </label>
        )}

        {value.setType === 'custom' ? (
          <p className="self-end text-xs leading-6 text-slate-400">
            自定义组型会把“次数表达”作为唯一来源，便于兼容 AMRAP、范围次数和周期计划写法。
          </p>
        ) : null}

        <label className="space-y-2">
          <span className="text-sm text-slate-300">RPE</span>
          <input
            aria-invalid={Boolean(fieldErrors['plan.exercise.rpe'] ?? rpeError)}
            className="w-full rounded-xl border border-fitloop-line bg-fitloop-panel px-3 py-2.5 text-slate-100 outline-none transition focus:border-fitloop-orange"
            inputMode="decimal"
            max={rpeGuardrail.max}
            min={rpeGuardrail.min}
            onChange={(event) => updateGuardedField('rpe', 'plan.exercise.rpe', event.target.value)}
            step={rpeGuardrail.step}
            type="number"
            value={value.rpe}
          />
          <p className={`text-xs ${fieldErrors['plan.exercise.rpe'] || rpeError ? 'text-rose-300' : 'text-slate-400'}`}>{rpeHint}</p>
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
