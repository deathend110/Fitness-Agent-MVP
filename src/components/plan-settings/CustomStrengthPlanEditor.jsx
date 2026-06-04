import CustomStrengthMainLiftEditor from './CustomStrengthMainLiftEditor.jsx'
import CustomStrengthWeekEditor from './CustomStrengthWeekEditor.jsx'

const DAY_LABELS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

function createEmptyDay(dayIndex) {
  return {
    dayIndex,
    label: DAY_LABELS[dayIndex - 1] ?? '',
    type: 'rest',
    exercises: [],
  }
}

function createEmptyWeek(weekIndex) {
  return {
    weekIndex,
    days: Array.from({ length: 7 }, (_, dayOffset) => createEmptyDay(dayOffset + 1)),
  }
}

function normalizeTotalWeeks(value) {
  const parsedValue = Number(value)
  if (!Number.isFinite(parsedValue)) {
    return 1
  }
  return Math.max(1, Math.floor(parsedValue))
}

function resizeWeeks(draft, nextTotalWeeks) {
  const safeTotalWeeks = normalizeTotalWeeks(nextTotalWeeks)
  const currentWeeks = Array.isArray(draft?.weeks) ? draft.weeks : []
  const nextWeeks = Array.from({ length: safeTotalWeeks }, (_, weekOffset) => {
    const existingWeek = currentWeeks[weekOffset]
    if (existingWeek && typeof existingWeek === 'object' && !Array.isArray(existingWeek)) {
      return {
        ...existingWeek,
        weekIndex: weekOffset + 1,
        days: Array.isArray(existingWeek.days)
          ? existingWeek.days.map((day, dayOffset) => ({
              ...day,
              dayIndex: dayOffset + 1,
              label: day?.label ?? DAY_LABELS[dayOffset] ?? '',
            }))
          : createEmptyWeek(weekOffset + 1).days,
      }
    }
    return createEmptyWeek(weekOffset + 1)
  })

  return {
    ...draft,
    totalWeeks: safeTotalWeeks,
    weeks: nextWeeks,
  }
}

function updateWeekDayType(draft, targetWeekIndex, targetDayIndex, nextType) {
  return {
    ...draft,
    weeks: (draft?.weeks ?? []).map((week) => {
      if (week.weekIndex !== targetWeekIndex) {
        return week
      }

      return {
        ...week,
        days: (week.days ?? []).map((day) =>
          day.dayIndex === targetDayIndex
            ? {
                ...day,
                type: nextType,
              }
            : day,
        ),
      }
    }),
  }
}

function CustomStrengthPlanEditor({ draft, isSubmitting, onChange, onSubmit }) {
  return (
    <div className="space-y-4 rounded-xl border border-emerald-200 bg-emerald-50/60 p-4">
      <div className="space-y-1">
        <p className="text-sm font-semibold text-slate-900">自定义力量周期计划</p>
        <p className="text-sm text-slate-600">
          这一版先支持名称、开始日期、周数、主项 TM 和周列表基础配置，不影响现有 preset 周期计划流程。
        </p>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <label className="space-y-1 text-sm">
          <span className="font-medium text-slate-700">名称</span>
          <input
            className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2"
            onChange={(event) =>
              onChange({
                ...draft,
                name: event.target.value,
              })
            }
            placeholder="例如：四周力量周期"
            value={draft.name}
          />
        </label>

        <label className="space-y-1 text-sm">
          <span className="font-medium text-slate-700">开始日期</span>
          <input
            className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2"
            onChange={(event) =>
              onChange({
                ...draft,
                startDate: event.target.value,
              })
            }
            type="date"
            value={draft.startDate}
          />
        </label>

        <label className="space-y-1 text-sm">
          <span className="font-medium text-slate-700">周数</span>
          <input
            className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2"
            min="1"
            onChange={(event) => onChange(resizeWeeks(draft, event.target.value))}
            type="number"
            value={draft.totalWeeks}
          />
        </label>
      </div>

      <CustomStrengthMainLiftEditor draft={draft} onChange={onChange} />

      <div className="space-y-3">
        {(draft.weeks ?? []).map((week) => (
          <CustomStrengthWeekEditor
            key={week.weekIndex}
            onChangeDayType={(weekIndex, dayIndex, nextType) =>
              onChange(updateWeekDayType(draft, weekIndex, dayIndex, nextType))
            }
            week={week}
          />
        ))}
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-emerald-300"
          disabled={isSubmitting}
          onClick={onSubmit}
          type="button"
        >
          创建自定义力量周期计划
        </button>
      </div>
    </div>
  )
}

export default CustomStrengthPlanEditor
