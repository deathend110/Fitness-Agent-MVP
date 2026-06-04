import { useRef, useState } from 'react'
import {
  buildBackupFilename,
  buildBackupPayload,
  parseBackupJson,
} from '../utils/dataTransfer.js'

function DataTransferPanel({
  appState,
  backendStatus,
  migrationPrompt,
  onDismissMigrationPrompt,
  onImportData,
  onImportToBackend,
}) {
  const fileInputRef = useRef(null)
  const [isMigrating, setIsMigrating] = useState(false)
  const [notice, setNotice] = useState({ tone: 'idle', message: '' })

  function handleExport() {
    const payload = buildBackupPayload(appState)
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: 'application/json;charset=utf-8',
    })
    const objectUrl = URL.createObjectURL(blob)
    const anchor = document.createElement('a')

    anchor.href = objectUrl
    anchor.download = buildBackupFilename(payload.exportedAt)
    anchor.click()
    URL.revokeObjectURL(objectUrl)

    setNotice({
      tone: 'success',
      message: '已导出当前本地数据备份。',
    })
  }

  async function handleImportChange(event) {
    const file = event.target.files?.[0]

    if (!file) {
      return
    }

    try {
      const rawText = await file.text()
      const nextData = parseBackupJson(rawText)
      onImportData(nextData)
      setNotice({
        tone: 'success',
        message: '已导入备份并覆盖当前本地数据。刷新后仍会保留。',
      })
    } catch (error) {
      setNotice({
        tone: 'error',
        message: error instanceof Error ? error.message : '导入失败，请检查备份文件。',
      })
    } finally {
      event.target.value = ''
    }
  }

  async function handleBackendImport() {
    if (!onImportToBackend || backendStatus?.mode !== 'ready') {
      return
    }

    setIsMigrating(true)
    try {
      const result = await onImportToBackend()
      const skippedMessage = result?.skipped?.chatHistory
      setNotice({
        tone: 'success',
        message: skippedMessage
          ? `已导入到后端。${skippedMessage}`
          : '已将当前 localStorage 数据导入后端。',
      })
    } catch (error) {
      setNotice({
        tone: 'error',
        message: error instanceof Error ? error.message : '导入到后端失败，请稍后重试。',
      })
    } finally {
      setIsMigrating(false)
    }
  }

  const noticeTone = notice.tone === 'error'
    ? 'border-rose-200 bg-rose-50 text-rose-500'
    : 'border-emerald-200 bg-emerald-50 text-emerald-600'
  const isBackendReady = backendStatus?.mode === 'ready'
  const backendButtonDisabled = !isBackendReady || isMigrating || !onImportToBackend

  return (
    <article className="rounded-[1.5rem] border border-fitloop-line bg-fitloop-panel-muted p-5 shadow-sm shadow-black/20">
      {migrationPrompt?.visible ? (
        <div className="mb-5 rounded-[1.25rem] border border-amber-300/70 bg-amber-50 px-4 py-4 text-sm text-amber-700">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="max-w-2xl space-y-1">
              <p className="font-semibold text-amber-800">检测到浏览器 localStorage 里仍有旧数据</p>
              <p className="leading-6 text-amber-700/90">
                当前后端还是空库，可以一键导入 `profile / weeklyPlan / dailyLog`。`chatHistory`
                本阶段仍只保留在本地，不会写入数据库。
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                className="rounded-xl border border-amber-300 bg-amber-500 px-3.5 py-2 text-sm font-medium text-white transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={backendButtonDisabled}
                onClick={handleBackendImport}
                type="button"
              >
                {isMigrating ? '导入中...' : '一键导入到后端'}
              </button>
              <button
                className="rounded-xl border border-fitloop-line bg-fitloop-panel px-3.5 py-2 text-sm font-medium text-slate-300 transition hover:border-fitloop-orange/30 hover:text-fitloop-orange"
                onClick={onDismissMigrationPrompt}
                type="button"
              >
                稍后再说
              </button>
            </div>
          </div>
        </div>
      ) : null}

      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-slate-100">数据备份</p>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-300">
            当前数据只保存在浏览器 localStorage。这里可以导出 JSON 备份，也可以从备份文件恢复
            `profile / weeklyPlan / dailyLog / chatHistory`。
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            className="rounded-xl border border-fitloop-line bg-fitloop-panel px-3.5 py-2 text-sm font-medium text-slate-300 transition hover:border-fitloop-orange/30 hover:bg-fitloop-orange/8 hover:text-fitloop-orange"
            onClick={handleExport}
            type="button"
          >
            导出备份
          </button>
          <button
            className="rounded-xl border border-emerald-300 bg-emerald-50 px-3.5 py-2 text-sm font-medium text-emerald-700 transition hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={backendButtonDisabled}
            onClick={handleBackendImport}
            type="button"
          >
            {isMigrating ? '导入中...' : '导入到后端'}
          </button>
          <button
            className="rounded-xl border border-fitloop-orange bg-fitloop-orange px-3.5 py-2 text-sm font-medium text-white shadow-sm shadow-black/20 transition hover:brightness-110"
            onClick={() => fileInputRef.current?.click()}
            type="button"
          >
            导入备份
          </button>
        </div>
      </div>

      <input
        accept="application/json,.json"
        className="hidden"
        onChange={handleImportChange}
        ref={fileInputRef}
        type="file"
      />

      <p className="mt-4 text-sm leading-6 text-slate-400">
        导入会直接覆盖当前本地数据。建议先执行一次导出，再进行恢复测试。
      </p>
      <p className="mt-2 text-sm leading-6 text-slate-400">
        后端导入只会同步 `profile / weeklyPlan / dailyLog`，并保留 localStorage 原值；如果后端未启动，入口会自动禁用。
      </p>

      {notice.message ? (
        <p className={`mt-4 rounded-xl border px-3 py-2 text-sm leading-6 ${noticeTone}`}>
          {notice.message}
        </p>
      ) : null}
    </article>
  )
}

export default DataTransferPanel
