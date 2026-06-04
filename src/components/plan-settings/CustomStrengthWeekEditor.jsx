const DAY_TYPE_OPTIONS = [
  { value: 'rest', label: '休息 / 占位' },
  { value: 'lower_strength', label: '下肢力量' },
  { value: 'upper_strength', label: '上肢力量' },
  { value: 'lower_volume', label: '下肢容量' },
  { value: 'upper_volume', label: '上肢容量' },
]

function countWeekExercises(week) {
  return (week?.days ?? []).reduce((total, day) => total + (day?.exercises?.length ?? 0), 0)
}

function CustomStrengthWeekEditor({ week, onChangeDayType }) {
  return (
    <div className="space-y-3 rounded-xl border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="space-y-1">
          <p className="text-sm font-semibold text-slate-800">第 {week.weekIndex} 周</p>
          <p className="text-sm text-slate-500">
            当前保留周结构与 exercises 快照入口，先提供最小 day type 编辑和数量预览。
          </p>
        </div>
        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">
          动作数 {countWeekExercises(week)}
        </span>
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {(week.days ?? []).map((day) => (
          <label className="space-y-1 text-sm" key={`${week.weekIndex}-${day.dayIndex}`}>
            <span className="font-medium text-slate-700">{day.label || `第 ${day.dayIndex} 天`}</span>
            <select
              className="w-full rounded-lg border border-slate-200 px-3 py-2"
              onChange={(event) => onChangeDayType(week.weekIndex, day.dayIndex, event.target.value)}
              value={day.type ?? 'rest'}
            >
              {DAY_TYPE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <p className="text-xs text-slate-500">保留动作结构：{day.exercises?.length ?? 0} 项</p>
          </label>
        ))}
      </div>
    </div>
  )
}

export default CustomStrengthWeekEditor
