import { useEffect, useRef, useState } from 'react'
import PlanHeaderLegend from './PlanHeaderLegend.jsx'
import {
  getNumericFieldGuardrail,
  validateNumericFieldValue,
} from '../../utils/numericFieldGuardrails.js'

function PlanHeaderToolbar({ headerModel, onPlanSettingsClick, onWeekNumberChange }) {
  const weekNumber = headerModel.weekMeta?.weekNumber ?? ''
  const weekNumberGuardrail = getNumericFieldGuardrail('plan.weekMeta.weekNumber')
  const [isEditingWeekNumber, setIsEditingWeekNumber] = useState(false)
  const [weekNumberDraft, setWeekNumberDraft] = useState(`${weekNumber}`)
  const weekNumberInputRef = useRef(null)

  useEffect(() => {
    if (!isEditingWeekNumber) {
      setWeekNumberDraft(`${weekNumber}`)
    }
  }, [isEditingWeekNumber, weekNumber])

  useEffect(() => {
    if (!isEditingWeekNumber) {
      return
    }

    const input = weekNumberInputRef.current
    input?.focus()
    input?.select()
  }, [isEditingWeekNumber])

  function commitWeekNumber() {
    const normalizedWeekNumber = `${weekNumberDraft}`.trim()
    const hasStrictIntegerFormat = /^\d+$/.test(normalizedWeekNumber)
    const validationError = hasStrictIntegerFormat
      ? validateNumericFieldValue('plan.weekMeta.weekNumber', normalizedWeekNumber)
      : '周数必须填写有效数字'
    const nextWeekNumber = hasStrictIntegerFormat ? Number(normalizedWeekNumber) : Number.NaN
    const isValidWeekNumber =
      hasStrictIntegerFormat && !validationError && Number.isInteger(nextWeekNumber)

    if (isValidWeekNumber && nextWeekNumber !== weekNumber && onWeekNumberChange) {
      onWeekNumberChange(nextWeekNumber)
    }

    setIsEditingWeekNumber(false)
    setWeekNumberDraft(`${isValidWeekNumber ? nextWeekNumber : weekNumber}`)
  }

  function handleWeekNumberKeyDown(event) {
    if (event.key === 'Enter') {
      event.preventDefault()
      commitWeekNumber()
    }

    if (event.key === 'Escape') {
      event.preventDefault()
      setIsEditingWeekNumber(false)
      setWeekNumberDraft(`${weekNumber}`)
    }
  }

  return (
    <header className="flex min-w-0 flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
      <div className="flex min-w-0 flex-wrap items-center gap-3">
        <h2 className="text-[1.75rem] font-bold leading-none text-slate-900">本周训练计划</h2>

        <span className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-1 text-sm font-medium text-slate-600 shadow-sm shadow-black/20">
          <span>{headerModel.weekRangeLabel}</span>
          <svg
            aria-hidden="true"
            className="h-4 w-4 text-slate-400"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            viewBox="0 0 24 24"
          >
            <path d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2z" />
          </svg>
        </span>

        <button
          className="inline-flex items-center gap-1 rounded-md bg-fitloop-orange/10 px-2.5 py-1 text-xs font-bold text-fitloop-orange transition hover:bg-fitloop-orange/15"
          onClick={() => setIsEditingWeekNumber(true)}
          type="button"
        >
          <span>第</span>
          {isEditingWeekNumber ? (
            <input
              aria-label="编辑周数"
              className="w-14 border-none bg-transparent p-0 text-center text-xs font-bold text-fitloop-orange outline-none"
              inputMode="numeric"
              max={weekNumberGuardrail.max}
              min={weekNumberGuardrail.min}
              onBlur={commitWeekNumber}
              onChange={(event) => setWeekNumberDraft(event.target.value)}
              onKeyDown={handleWeekNumberKeyDown}
              ref={weekNumberInputRef}
              step={weekNumberGuardrail.step}
              value={weekNumberDraft}
            />
          ) : (
            <span>{weekNumber}</span>
          )}
          <span>周</span>
        </button>

        <button
          aria-label={headerModel.settingsButton.label}
          className="inline-flex items-center rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-600 shadow-sm shadow-black/20 transition hover:border-slate-300 hover:text-slate-800"
          onClick={onPlanSettingsClick}
          title={headerModel.settingsButton.hint}
          type="button"
        >
          {headerModel.settingsButton.label}
        </button>
      </div>

      <div className="flex min-w-0 items-center gap-6">
        <div className="inline-flex items-center rounded-xl border border-slate-200/80 bg-slate-100 p-0.5">
          {headerModel.viewTabs.map((tab) => {
            const tabClassName = tab.isActive
              ? 'bg-white text-fitloop-orange shadow-sm shadow-black/20'
              : 'text-slate-500'

            return (
              <button
                aria-pressed={tab.isActive}
                className={`rounded-lg px-4 py-1.5 text-xs font-semibold transition ${tabClassName}`}
                key={tab.key}
                type="button"
              >
                {tab.label}
              </button>
            )
          })}
        </div>

        <PlanHeaderLegend items={headerModel.legendItems} />
      </div>
    </header>
  )
}

export default PlanHeaderToolbar
