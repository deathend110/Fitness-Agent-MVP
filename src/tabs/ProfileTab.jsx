function ProfileTab() {
  return (
    <section className="rounded-lg border border-fitloop-line bg-fitloop-panel p-8 shadow-2xl shadow-black/20">
      <p className="text-sm font-semibold text-fitloop-mint">Tab 1</p>
      <h2 className="mt-3 text-2xl font-bold text-white">我的档案</h2>
      <p className="mt-4 max-w-2xl leading-7 text-slate-300">
        这里将录入用户基础信息、三大项 1RM、训练目标和备注。Task 1.1 只搭建页面入口，真实表单会在后续任务实现。
      </p>
    </section>
  )
}

export default ProfileTab
