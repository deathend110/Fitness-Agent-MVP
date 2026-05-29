import { getExerciseKg } from '../utils/calc.js'

function getExerciseDisplay(profile, exercise) {
  if (exercise.ref1RM) {
    const actualKg = getExerciseKg(exercise, profile.oneRM)

    return `${Math.round(exercise.pct * 100)}% → ${actualKg}kg`
  }

  return `${getExerciseKg(exercise, profile.oneRM)}kg`
}

function PlanTab({ profile, weeklyPlan }) {
  const days = Object.entries(weeklyPlan)

  return (
    <section className="rounded-lg border border-fitloop-line bg-fitloop-panel p-8 shadow-2xl shadow-black/20">
      <p className="text-sm font-semibold text-fitloop-mint">Tab 2</p>
      <h2 className="mt-3 text-2xl font-bold text-white">训练计划</h2>
      <p className="mt-4 max-w-2xl leading-7 text-slate-300">
        当前页面已经接入统一的重量计算工具，会根据 1RM 百分比或固定 kg 展示实际训练重量。
      </p>

      <div className="mt-8 grid gap-4 lg:grid-cols-2">
        {days.map(([day, plan]) => (
          <article
            className="rounded-md border border-fitloop-line bg-fitloop-ink/40 p-4"
            key={day}
          >
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-lg font-semibold text-white">{day}</h3>
              <span className="rounded-md bg-fitloop-orange/15 px-2 py-1 text-xs font-medium text-fitloop-orange">
                {plan.type}
              </span>
            </div>

            {plan.exercises.length === 0 ? (
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
                      {getExerciseDisplay(profile, exercise)} · {exercise.sets} 组 × {exercise.reps}{' '}
                      次
                    </p>
                    <p className="mt-1 text-xs text-slate-400">
                      {exercise.note || '当前没有补充备注'}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </article>
        ))}
      </div>
    </section>
  )
}

export default PlanTab
