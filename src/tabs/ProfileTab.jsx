import { useEffect, useState } from 'react'
import {
  basicFields,
  draftToProfile,
  oneRmFields,
  profileToDraft,
  sexOptions,
} from '../utils/profileForm.js'

function ProfileTab({ profile, onProfileChange }) {
  const [draft, setDraft] = useState(() => profileToDraft(profile))

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

  function renderBasicField(field) {
    if (field.type === 'select') {
      return (
        <label className="space-y-2" key={field.key}>
          <span className="text-sm text-slate-300">{field.label}</span>
          <select
            className="w-full rounded-md border border-fitloop-line bg-fitloop-ink/60 px-3 py-2 text-white outline-none transition focus:border-fitloop-orange"
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
      <label className="space-y-2" key={field.key}>
        <span className="text-sm text-slate-300">{field.label}</span>
        <input
          className="w-full rounded-md border border-fitloop-line bg-fitloop-ink/60 px-3 py-2 text-white outline-none transition placeholder:text-slate-500 focus:border-fitloop-orange"
          inputMode={field.inputMode}
          onChange={(event) => updateNestedField('basic', field.key, event.target.value)}
          step={field.step}
          type={field.type}
          value={field.key === 'name' ? draft.basic.name : draft.basic[field.key]}
        />
      </label>
    )
  }

  return (
    <section className="rounded-lg border border-fitloop-line bg-fitloop-panel p-8 shadow-2xl shadow-black/20">
      <p className="text-sm font-semibold text-fitloop-mint">Tab 1</p>
      <h2 className="mt-3 text-2xl font-bold text-white">我的档案</h2>
      <p className="mt-4 max-w-2xl leading-7 text-slate-300">
        这里直接编辑并保存用户档案，所有数字字段都会以数字形式写入 `fitloop_profile`，
        刷新后仍然保留。
      </p>

      <form className="mt-8 space-y-6">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {basicFields.map(renderBasicField)}
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <label className="space-y-2">
            <span className="text-sm text-slate-300">目标体重 (kg)</span>
            <input
              className="w-full rounded-md border border-fitloop-line bg-fitloop-ink/60 px-3 py-2 text-white outline-none transition placeholder:text-slate-500 focus:border-fitloop-orange"
              inputMode="numeric"
              onChange={(event) =>
                setDraft((current) => {
                  const nextDraft = { ...current, targetWeight: event.target.value }
                  onProfileChange(draftToProfile(nextDraft))
                  return nextDraft
                })
              }
              step="0.1"
              type="number"
              value={draft.targetWeight}
            />
          </label>

          <label className="space-y-2">
            <span className="text-sm text-slate-300">训练目标</span>
            <input
              className="w-full rounded-md border border-fitloop-line bg-fitloop-ink/60 px-3 py-2 text-white outline-none transition placeholder:text-slate-500 focus:border-fitloop-orange"
              onChange={(event) =>
                setDraft((current) => {
                  const nextDraft = { ...current, goal: event.target.value }
                  onProfileChange(draftToProfile(nextDraft))
                  return nextDraft
                })
              }
              value={draft.goal}
            />
          </label>

          <label className="space-y-2">
            <span className="text-sm text-slate-300">备注</span>
            <textarea
              className="min-h-24 w-full rounded-md border border-fitloop-line bg-fitloop-ink/60 px-3 py-2 text-white outline-none transition placeholder:text-slate-500 focus:border-fitloop-orange"
              onChange={(event) =>
                setDraft((current) => {
                  const nextDraft = { ...current, notes: event.target.value }
                  onProfileChange(draftToProfile(nextDraft))
                  return nextDraft
                })
              }
              value={draft.notes}
            />
          </label>
        </div>

        <div className="rounded-md border border-fitloop-line bg-fitloop-ink/40 p-4">
          <p className="text-sm font-semibold text-slate-100">三大项 1RM</p>
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            {oneRmFields.map((field) => (
              <label className="space-y-2" key={field.key}>
                <span className="text-sm text-slate-300">{field.label}</span>
                <input
                  className="w-full rounded-md border border-fitloop-line bg-fitloop-ink/60 px-3 py-2 text-white outline-none transition placeholder:text-slate-500 focus:border-fitloop-orange"
                  inputMode="numeric"
                  onChange={(event) => updateNestedField('oneRM', field.key, event.target.value)}
                  step="0.1"
                  type="number"
                  value={draft.oneRM[field.key]}
                />
              </label>
            ))}
          </div>
        </div>
      </form>
    </section>
  )
}

export default ProfileTab
