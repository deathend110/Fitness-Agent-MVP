import { useState } from 'react'
import ExerciseEditor from '../components/ExerciseEditor.jsx'
import { createExerciseDraft, draftToExercise } from '../utils/exerciseForm.js'
import { getExerciseKg, getTodayKey } from '../utils/calc.js'

const WEEKDAY_ORDER = [
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
  'Sunday',
]

function getExerciseDisplay(profile, exercise) {
  if (exercise.ref1RM) {
    const actualKg = getExerciseKg(exercise, profile.oneRM)
    return `${Math.round((exercise.pct ?? 0) * 100)}% -> ${actualKg}kg`
  }

  return `${getExerciseKg(exercise, profile.oneRM)}kg`
}

function getOneRmOptions(profile) {
  return [
    { value: 'squat', label: `深蹲 ${profile.oneRM?.squat ?? '--'}kg` },
    { value: 'bench', label: `卧推 ${profile.oneRM?.bench ?? '--'}kg` },
    { value: 'deadlift', label: `硬拉 ${profile.oneRM?.deadlift ?? '--'}kg` },
  ]
}

function createDemoDrafts() {
  return {
    squat: createExerciseDraft({
      name: '深蹲',
      ref1RM: 'squat',
      pct: 0.75,
      kg: null,
      sets: 4,
      reps: 6,
      rpe: null,
      note: '百分比模式示例',
    }),
    rdl: createExerciseDraft({
      name: '罗马尼亚硬拉',
      ref1RM: null,
      pct: null,
      kg: 80,
      sets: 3,
      reps: 10,
      rpe: null,
      note: '固定 kg 模式示例',
    }),
  }
}

function ExercisePreview({ exercise, profile }) {
  return (
    <div className="rounded-md border border-fitloop-line/80 bg-fitloop-panel/70 p-3">
      <p className="text-sm font-semibold text-slate-100">{exercise.name || '未命名动作'}</p>
      <p className="mt-1 text-sm text-slate-300">
        {getExerciseDisplay(profile, exercise)} · {exercise.sets} 组 × {exercise.reps} 次
      </p>
      <p className="mt-1 text-xs text-slate-400">
        {exercise.note || '当前没有补充备注'}
      </p>
      <pre className="mt-3 overflow-x-auto rounded-md bg-black/30 p-3 text-xs leading-5 text-slate-200">
        {JSON.stringify(exercise, null, 2)}
      </pre>
    </div>
  )
}

function PlanTab({ profile, weeklyPlan }) {
  const [expandedDay, setExpandedDay] = useState(() => getTodayKey())
  const [demoDrafts, setDemoDrafts] = useState(() => createDemoDrafts())
  const oneRmOptions = getOneRmOptions(profile)
  const demoExercises = {
    squat: draftToExercise(demoDrafts.squat),
    rdl: draftToExercise(demoDrafts.rdl),
  }
  const days = WEEKDAY_ORDER.map((day) => [
    day,
    weeklyPlan?.[day] ?? { type: 'rest', exercises: [] },
  ])

  function toggleDay(day) {
    setExpandedDay((currentDay) => (currentDay === day ? null : day))
  }

  function updateDemoDraft(key, nextDraft) {
    setDemoDrafts((current) => ({
      ...current,
      [key]: nextDraft,
    }))
  }

  return (
    <section className="rounded-lg border border-fitloop-line bg-fitloop-panel p-8 shadow-2xl shadow-black/20">
      <p className="text-sm font-semibold text-fitloop-mint">Tab 2</p>
      <h2 className="mt-3 text-2xl font-bold text-white">训练计划</h2>
      <p className="mt-4 max-w-2xl leading-7 text-slate-300">
        当前页面已经接入统一的重量计算工具，会根据 1RM 百分比或固定 kg 展示实际训练重量。
      </p>

      <div className="mt-8 grid gap-4 lg:grid-cols-2">
        {days.map(([day, plan]) => (
          <article className="rounded-md border border-fitloop-line bg-fitloop-ink/40 p-4" key={day}>
            <button
              className="flex w-full items-center justify-between gap-3 text-left"
              aria-expanded={expandedDay === day}
              onClick={() => toggleDay(day)}
              type="button"
            >
              <div>
                <h3 className="text-lg font-semibold text-white">{day}</h3>
                <p className="mt-1 text-sm text-slate-400">{plan.exercises.length} 个动作</p>
              </div>
              <div className="flex items-center gap-2">
                <span className="rounded-md bg-fitloop-orange/15 px-2 py-1 text-xs font-medium text-fitloop-orange">
                  {plan.type}
                </span>
                <span className="text-xs text-slate-400">
                  {expandedDay === day ? '收起' : '展开'}
                </span>
              </div>
            </button>

            {expandedDay === day ? (
              plan.exercises.length === 0 ? (
                <p className="mt-4 text-sm text-slate-400">休息日，当前没有安排动作。</p>
              ) : (
                <ul className="mt-4 space-y-3">
                  {plan.exercises.map((exercise) => (
                    <li
                      className="rounded-md border border-fitloop-line/80 bg-fitloop-panel/70 p-3"
                      key={exercise.id}
                    >
                      <p className="text-sm font-semibold text-slate-100">{exercise.name}</p>
                      <p className="mt-1 text-sm text-slate-300">
                        {getExerciseDisplay(profile, exercise)} · {exercise.sets} 组 × {exercise.reps} 次
                      </p>
                      <p className="mt-1 text-xs text-slate-400">
                        {exercise.note || '当前没有补充备注'}
                      </p>
                    </li>
                  ))}
                </ul>
              )
            ) : null}
          </article>
        ))}
      </div>

      <div className="mt-8 rounded-md border border-fitloop-line bg-fitloop-ink/40 p-4">
        <p className="text-sm font-semibold text-fitloop-orange">动作编辑演示</p>
        <p className="mt-2 text-sm leading-6 text-slate-300">
          下面两个示例只在当前页面内编辑，用来验证单动作的规范化结果，不会写回整周计划。
        </p>

        <div className="mt-4 grid gap-4 xl:grid-cols-2">
          <div className="space-y-3">
            <h3 className="text-base font-semibold text-white">百分比模式</h3>
            <ExerciseEditor
              oneRmOptions={oneRmOptions}
              onChange={(nextDraft) => updateDemoDraft('squat', nextDraft)}
              value={demoDrafts.squat}
            />
            <ExercisePreview exercise={demoExercises.squat} profile={profile} />
          </div>

          <div className="space-y-3">
            <h3 className="text-base font-semibold text-white">固定重量模式</h3>
            <ExerciseEditor
              oneRmOptions={oneRmOptions}
              onChange={(nextDraft) => updateDemoDraft('rdl', nextDraft)}
              value={demoDrafts.rdl}
            />
            <ExercisePreview exercise={demoExercises.rdl} profile={profile} />
          </div>
        </div>
      </div>
    </section>
  )
}

export default PlanTab
