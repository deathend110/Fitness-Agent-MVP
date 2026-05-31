import { useEffect, useState } from 'react'
import DataTransferPanel from '../components/DataTransferPanel.jsx'
import {
  basicFields,
  draftToProfile,
  oneRmFields,
  profileToDraft,
  sexOptions,
} from '../utils/profileForm.js'

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
    if (field.type === 'select') {
      return (
        <label className="space-y-2" key={field.key}>
          <span className="text-sm text-slate-300">{field.label}</span>
          <select
            className="w-full rounded-xl border border-fitloop-line bg-fitloop-panel px-3 py-2.5 text-slate-100 outline-none transition focus:border-fitloop-orange"
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
          className="w-full rounded-xl border border-fitloop-line bg-fitloop-panel px-3 py-2.5 text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-fitloop-orange"
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
    <section className="rounded-[1.5rem] border border-fitloop-line bg-fitloop-panel/90 p-8 shadow-2xl shadow-black/20">
      <p className="text-sm font-semibold uppercase tracking-[0.16em] text-fitloop-orange">
        Profile
      </p>
      <h2 className="mt-3 text-3xl font-semibold text-slate-100">我的档案</h2>
      
      <div className="mt-8 space-y-6">
        <form className="space-y-6">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {basicFields.map(renderBasicField)}
          </div>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <label className="space-y-2">
              <span className="text-sm text-slate-300">目标体重 (kg)</span>
              <input
                className="w-full rounded-xl border border-fitloop-line bg-fitloop-panel px-3 py-2.5 text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-fitloop-orange"
                inputMode="numeric"
                onChange={(event) => updateTopLevelField('targetWeight', event.target.value)}
                step="0.1"
                type="number"
                value={draft.targetWeight}
              />
            </label>

            <label className="space-y-2">
              <span className="text-sm text-slate-300">训练目标</span>
              <input
                className="w-full rounded-xl border border-fitloop-line bg-fitloop-panel px-3 py-2.5 text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-fitloop-orange"
                onChange={(event) => updateTopLevelField('goal', event.target.value)}
                value={draft.goal}
              />
            </label>

            <label className="space-y-2">
              <span className="text-sm text-slate-300">备注</span>
              <textarea
                className="min-h-28 w-full rounded-xl border border-fitloop-line bg-fitloop-panel px-3 py-2.5 text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-fitloop-orange"
                onChange={(event) => updateTopLevelField('notes', event.target.value)}
                value={draft.notes}
              />
            </label>
          </div>

          <div className="rounded-2xl border border-fitloop-line bg-fitloop-ink/30 p-5 shadow-sm shadow-black/20">
            <p className="text-sm font-semibold uppercase tracking-[0.16em] text-fitloop-orange">
              Strength Base
            </p>
            <h3 className="mt-2 text-lg font-semibold text-slate-100">三大项 1RM</h3>
            <div className="mt-4 grid gap-4 md:grid-cols-3">
              {oneRmFields.map((field) => (
                <label className="space-y-2" key={field.key}>
                  <span className="text-sm text-slate-300">{field.label}</span>
                  <input
                    className="w-full rounded-xl border border-fitloop-line bg-fitloop-panel px-3 py-2.5 text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-fitloop-orange"
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

        <DataTransferPanel
          appState={appState}
          backendStatus={backendStatus}
          migrationPrompt={migrationPrompt}
          onDismissMigrationPrompt={onDismissMigrationPrompt}
          onImportData={onImportData}
          onImportToBackend={onImportToBackend}
        />
      </div>
    </section>
  )
}

export default ProfileTab
