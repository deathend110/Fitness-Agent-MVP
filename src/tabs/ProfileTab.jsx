function ProfileTab({ profile }) {
  const { basic, oneRM, goal, targetWeight, notes } = profile

  return (
    <section className="rounded-lg border border-fitloop-line bg-fitloop-panel p-8 shadow-2xl shadow-black/20">
      <p className="text-sm font-semibold text-fitloop-mint">Tab 1</p>
      <h2 className="mt-3 text-2xl font-bold text-white">我的档案</h2>
      <p className="mt-4 max-w-2xl leading-7 text-slate-300">
        当前先接入默认档案摘要，后续任务再在这里补完整编辑表单和实时保存交互。
      </p>

      <div className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <article className="rounded-md border border-fitloop-line bg-fitloop-ink/40 p-4">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-400">基本信息</p>
          <p className="mt-3 text-lg font-semibold text-white">{basic.name}</p>
          <p className="mt-2 text-sm text-slate-300">
            {basic.age} 岁 · {basic.sex === 'male' ? '男' : '女'} · {basic.height} cm ·{' '}
            {basic.weight} kg
          </p>
        </article>

        <article className="rounded-md border border-fitloop-line bg-fitloop-ink/40 p-4">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-400">三大项 1RM</p>
          <p className="mt-3 text-sm text-slate-200">深蹲 {oneRM.squat} kg</p>
          <p className="mt-2 text-sm text-slate-200">卧推 {oneRM.bench} kg</p>
          <p className="mt-2 text-sm text-slate-200">硬拉 {oneRM.deadlift} kg</p>
        </article>

        <article className="rounded-md border border-fitloop-line bg-fitloop-ink/40 p-4">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-400">目标</p>
          <p className="mt-3 text-lg font-semibold text-white">{goal}</p>
          <p className="mt-2 text-sm text-slate-300">目标体重 {targetWeight} kg</p>
        </article>

        <article className="rounded-md border border-fitloop-line bg-fitloop-ink/40 p-4">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-400">备注</p>
          <p className="mt-3 text-sm leading-6 text-slate-300">{notes}</p>
        </article>
      </div>
    </section>
  )
}

export default ProfileTab
