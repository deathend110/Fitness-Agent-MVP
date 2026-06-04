import { useEffect, useState } from 'react'
import DataTransferPanel from '../components/DataTransferPanel.jsx'
import {
  basicFields,
  draftToProfile,
  oneRmFields,
  profileToDraft,
  sexOptions,
} from '../utils/profileForm.js'
import { buildProfileSummaryCards, getProfileFieldHint } from '../utils/profileView.js'

const summaryCardToneClassNames = {
  weight:
    'border-sky-200/70 bg-[linear-gradient(180deg,rgba(240,249,255,0.96),rgba(255,255,255,0.98))] shadow-[0_20px_40px_-30px_rgba(56,189,248,0.45)]',
  targetWeight:
    'border-emerald-200/70 bg-[linear-gradient(180deg,rgba(236,253,245,0.96),rgba(255,255,255,0.98))] shadow-[0_20px_40px_-30px_rgba(16,185,129,0.34)]',
  waist:
    'border-violet-200/70 bg-[linear-gradient(180deg,rgba(245,243,255,0.98),rgba(255,255,255,0.98))] shadow-[0_20px_40px_-30px_rgba(139,92,246,0.36)]',
  goal:
    'border-amber-200/80 bg-[linear-gradient(180deg,rgba(255,251,235,0.98),rgba(255,255,255,0.98))] shadow-[0_20px_40px_-30px_rgba(245,158,11,0.32)]',
}

function getSummaryCardsWithTone(profile) {
  return buildProfileSummaryCards(profile).map((card) => ({
    ...card,
    tone: summaryCardToneClassNames[card.key] ?? summaryCardToneClassNames.goal,
  }))
}

function SectionCard({ children, eyebrow, title, description }) {
  return (
    <section className="rounded-[1.75rem] border border-fitloop-line bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(248,250,255,0.98))] p-6 shadow-xl shadow-black/20 sm:p-7">
      <div className="flex flex-col gap-2">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-fitloop-orange">
          {eyebrow}
        </p>
        <div className="space-y-1">
          <h3 className="text-xl font-semibold text-slate-100">{title}</h3>
          <p className="max-w-2xl text-sm leading-6 text-slate-400">{description}</p>
        </div>
      </div>
      <div className="mt-6">{children}</div>
    </section>
  )
}

function FieldLabel({ label, hint }) {
  return (
    <div className="space-y-1">
      <span className="text-sm font-medium text-slate-300">{label}</span>
      {hint ? <p className="text-xs leading-5 text-slate-400">{hint}</p> : null}
    </div>
  )
}

function ProfileTab({
  appState,
  backendStatus,
  migrationPrompt,
  onDismissMigrationPrompt,
  onImportData,
  onImportToBackend,
  onProfileChange,
  profile,
}) {
  const [draft, setDraft] = useState(() => profileToDraft(profile))
  const [isDataPanelOpen, setIsDataPanelOpen] = useState(false)

  useEffect(() => {
    setDraft(profileToDraft(profile))
  }, [profile])

  function commitDraft(nextDraft) {
    setDraft(nextDraft)
    onProfileChange(draftToProfile(nextDraft))
  }

  function updateNestedField(group, key, value) {
    commitDraft({
      ...draft,
      [group]: {
        ...draft[group],
        [key]: value,
      },
    })
  }

  function updateTopLevelField(key, value) {
    commitDraft({
      ...draft,
      [key]: value,
    })
  }

  function renderBasicField(field) {
    const hint = getProfileFieldHint(field.key)

    if (field.type === 'select') {
      return (
        <label className="space-y-3" key={field.key}>
          <FieldLabel hint={hint} label={field.label} />
          <select
            className="h-12 w-full rounded-2xl border border-fitloop-line bg-fitloop-panel-muted px-4 text-[15px] text-slate-100 outline-none transition focus:border-fitloop-orange"
            onChange={(event) => updateNestedField('basic', field.key, event.target.value)}
            value={draft.basic[field.key]}
          >
            {sexOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      )
    }

    return (
      <label className="space-y-3" key={field.key}>
        <FieldLabel hint={hint} label={field.label} />
        <input
          className="h-12 w-full rounded-2xl border border-fitloop-line bg-fitloop-panel-muted px-4 text-[15px] text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-fitloop-orange"
          inputMode={field.inputMode}
          onChange={(event) => updateNestedField('basic', field.key, event.target.value)}
          placeholder={hint || field.label}
          step={field.step}
          type={field.type}
          value={field.key === 'name' ? draft.basic.name : draft.basic[field.key]}
        />
      </label>
    )
  }

  const summaryCards = getSummaryCardsWithTone(profile)

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-[2rem] border border-fitloop-line bg-gradient-to-b from-[#fdfdff] via-[#f6f8ff] to-[#eef4ff] shadow-2xl shadow-black/20">
        <div className="relative px-6 py-8 sm:px-8 sm:py-9">
          <div className="pointer-events-none absolute inset-x-0 top-0 h-40 bg-[radial-gradient(circle_at_top_left,rgba(109,94,252,0.18),transparent_58%)]" />
          <div className="pointer-events-none absolute right-0 top-10 h-36 w-36 rounded-full bg-[radial-gradient(circle,rgba(56,189,248,0.18),transparent_68%)]" />
          <div className="relative">
            <p className="text-sm font-semibold uppercase tracking-[0.16em] text-fitloop-orange">
              Profile
            </p>
            <div className="mt-4 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
              <div className="space-y-3">
                <h2 className="text-3xl font-semibold tracking-tight text-slate-100 sm:text-[2.15rem]">
                  我的档案
                </h2>
                <p className="max-w-2xl text-sm leading-7 text-slate-400 sm:text-[15px]">
                  记录当前身体数据、训练目标和力量基线，作为计划安排与 AI 教练判断的基础输入。
                </p>
              </div>
              <div className="inline-flex items-center rounded-full border border-fitloop-orange/30 bg-white/75 px-4 py-2 text-sm text-fitloop-orange shadow-sm shadow-black/20 backdrop-blur">
                当前数据会同步保存到本地与后端
              </div>
            </div>
          </div>

          <div className="relative mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {summaryCards.map((card) => (
              <article
                className={`rounded-[1.5rem] border p-5 shadow-lg backdrop-blur ${card.tone}`}
                key={card.key}
              >
                <p className="text-sm font-medium text-slate-400">{card.label}</p>
                <p className="mt-3 text-[1.7rem] font-semibold tracking-tight text-slate-100">
                  {card.value}
                </p>
                <p className="mt-2 text-xs uppercase tracking-[0.14em] text-slate-400">
                  {card.hint}
                </p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <form className="space-y-6">
        <SectionCard
          description="维护日常记录所需的基础身体信息。这里的信息会直接参与训练估算和上下文构建。"
          eyebrow="Basic Info"
          title="基础资料"
        >
          <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            {basicFields.map(renderBasicField)}
          </div>
        </SectionCard>

        <SectionCard
          description="记录近期目标与补充说明，方便后续在计划、日志和教练对话中引用。"
          eyebrow="Goal & Status"
          title="目标与状态"
        >
          <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr),minmax(0,1fr)]">
            <div className="grid gap-5 md:grid-cols-2">
              <label className="space-y-3">
                <FieldLabel
                  hint={getProfileFieldHint('targetWeight')}
                  label="目标体重 (kg)"
                />
                <input
                  className="h-12 w-full rounded-2xl border border-fitloop-line bg-fitloop-panel-muted px-4 text-[15px] text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-fitloop-orange"
                  inputMode="numeric"
                  onChange={(event) => updateTopLevelField('targetWeight', event.target.value)}
                  placeholder="目标体重，单位 kg"
                  step="0.1"
                  type="number"
                  value={draft.targetWeight}
                />
              </label>

              <label className="space-y-3">
                <FieldLabel hint={getProfileFieldHint('goal')} label="训练目标" />
                <input
                  className="h-12 w-full rounded-2xl border border-fitloop-line bg-fitloop-panel-muted px-4 text-[15px] text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-fitloop-orange"
                  onChange={(event) => updateTopLevelField('goal', event.target.value)}
                  placeholder="例如减脂、增肌或力量提升"
                  value={draft.goal}
                />
              </label>
            </div>

            <label className="space-y-3">
              <FieldLabel hint={getProfileFieldHint('notes')} label="备注" />
              <textarea
                className="min-h-[10.5rem] w-full rounded-[1.5rem] border border-fitloop-line bg-fitloop-panel-muted px-4 py-3 text-[15px] leading-7 text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-fitloop-orange"
                onChange={(event) => updateTopLevelField('notes', event.target.value)}
                placeholder="记录补充信息，例如伤病或训练限制"
                value={draft.notes}
              />
            </label>
          </div>
        </SectionCard>

        <SectionCard
          description="三大项 1RM 作为当前力量基准，用于百分比训练重量推算和教练上下文判断。"
          eyebrow="Strength Base"
          title="力量基础"
        >
          <div className="grid gap-5 md:grid-cols-3">
            {oneRmFields.map((field) => (
              <label className="space-y-3" key={field.key}>
                <FieldLabel hint="单位 kg" label={field.label} />
                <input
                  className="h-12 w-full rounded-2xl border border-fitloop-line bg-fitloop-panel-muted px-4 text-[15px] text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-fitloop-orange"
                  inputMode="numeric"
                  onChange={(event) => updateNestedField('oneRM', field.key, event.target.value)}
                  placeholder="单位 kg"
                  step="0.1"
                  type="number"
                  value={draft.oneRM[field.key]}
                />
              </label>
            ))}
          </div>
        </SectionCard>
      </form>

      <section className="rounded-[1.75rem] border border-fitloop-line bg-fitloop-panel p-5 shadow-xl shadow-black/20 sm:p-6">
        <button
          aria-expanded={isDataPanelOpen}
          className="flex w-full items-start justify-between gap-4 rounded-[1.25rem] border border-transparent px-1 py-1 text-left transition hover:border-fitloop-line"
          onClick={() => setIsDataPanelOpen((current) => !current)}
          type="button"
        >
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-fitloop-orange">
              Data Control
            </p>
            <div className="space-y-1">
              <h3 className="text-lg font-semibold text-slate-100">数据管理</h3>
              <p className="max-w-2xl text-sm leading-6 text-slate-400">
                用于导出、导入和迁移数据。默认收起，避免干扰日常档案编辑。
              </p>
            </div>
          </div>
          <span className="mt-1 inline-flex min-w-[5.5rem] items-center justify-center rounded-full border border-fitloop-orange/30 bg-fitloop-orange/8 px-3 py-1.5 text-sm text-fitloop-orange">
            {isDataPanelOpen ? '收起' : '展开'}
          </span>
        </button>

        {isDataPanelOpen ? (
          <div className="mt-5 border-t border-fitloop-line pt-5">
            <DataTransferPanel
              appState={appState}
              backendStatus={backendStatus}
              migrationPrompt={migrationPrompt}
              onDismissMigrationPrompt={onDismissMigrationPrompt}
              onImportData={onImportData}
              onImportToBackend={onImportToBackend}
            />
          </div>
        ) : null}
      </section>
    </div>
  )
}

export default ProfileTab
