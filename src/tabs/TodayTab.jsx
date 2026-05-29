import { getExerciseKg, getTodayKey, getTodayStr } from '../utils/calc.js'

function getTodayPlanSummary(plan, profile) {
  if (!plan || plan.exercises.length === 0) {
    return '今天是休息日，当前没有训练动作安排。'
  }

  return plan.exercises
    .map((exercise) => {
      const actualKg = getExerciseKg(exercise, profile.oneRM)
      return `${exercise.name} ${actualKg}kg × ${exercise.sets} × ${exercise.reps}`
    })
    .join(' | ')
}

function TodayTab({ dailyLog, weeklyPlan, profile }) {
  const todayDate = getTodayStr()
  const todayPlanKey = getTodayKey()
  const todayLog = dailyLog[todayDate]
  const todayPlan = weeklyPlan[todayPlanKey]

  return (
    <section className="rounded-lg border border-fitloop-line bg-fitloop-panel p-8 shadow-2xl shadow-black/20">
      <p className="text-sm font-semibold text-fitloop-mint">Tab 3</p>
      <h2 className="mt-3 text-2xl font-bold text-white">今日日志</h2>
      <p className="mt-4 max-w-2xl leading-7 text-slate-300">
        这里先展示默认日志摘要和今天的只读训练安排，后续任务再补录入表单。
      </p>

      <div className="mt-8 grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <article className="rounded-md border border-fitloop-line bg-fitloop-ink/40 p-4">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-400">{todayDate}</p>
          <h3 className="mt-3 text-lg font-semibold text-white">今日记录</h3>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <p className="text-sm text-slate-300">体重：{todayLog?.weight ?? '--'} kg</p>
            <p className="text-sm text-slate-300">热量：{todayLog?.kcal ?? '--'} kcal</p>
            <p className="text-sm text-slate-300">蛋白质：{todayLog?.protein ?? '--'} g</p>
            <p className="text-sm text-slate-300">睡眠：{todayLog?.sleep ?? '--'} h</p>
            <p className="text-sm text-slate-300">疲劳度：{todayLog?.fatigue ?? '--'} / 5</p>
            <p className="text-sm text-slate-300">
              训练完成：{todayLog?.trainingDone ? '是' : '否'}
            </p>
          </div>
          <p className="mt-4 text-sm leading-6 text-slate-300">
            训练备注：{todayLog?.trainingNotes || '今天还没有训练备注。'}
          </p>
        </article>

        <article className="rounded-md border border-fitloop-line bg-fitloop-ink/40 p-4">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-400">{todayPlanKey}</p>
          <h3 className="mt-3 text-lg font-semibold text-white">今日计划</h3>
          <p className="mt-4 text-sm text-slate-300">训练类型：{todayPlan?.type ?? 'rest'}</p>
          <p className="mt-4 text-sm leading-6 text-slate-300">
            {getTodayPlanSummary(todayPlan, profile)}
          </p>
        </article>
      </div>
    </section>
  )
}

export default TodayTab
