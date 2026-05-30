import { useRef, useState } from 'react'
import {
  buildBackupFilename,
  buildBackupPayload,
  parseBackupJson,
} from '../utils/dataTransfer.js'

function DataTransferPanel({ appState, onImportData }) {
  const fileInputRef = useRef(null)
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

  const noticeTone = notice.tone === 'error'
    ? 'border-rose-200 bg-rose-50 text-rose-500'
    : 'border-emerald-200 bg-emerald-50 text-emerald-600'

  return (
    <article className="rounded-xl border border-fitloop-line bg-fitloop-panel p-4 shadow-xl shadow-black/20">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-100">数据备份</p>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-300">
            当前数据只保存在浏览器 localStorage。这里可以导出 JSON 备份，也可以从备份文件恢复
            `profile / weeklyPlan / dailyLog / chatHistory`。
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            className="rounded-md border border-fitloop-line bg-fitloop-panel px-3 py-2 text-sm font-medium text-slate-300 transition hover:border-fitloop-orange/30 hover:bg-fitloop-orange/8 hover:text-fitloop-orange"
            onClick={handleExport}
            type="button"
          >
            导出备份
          </button>
          <button
            className="rounded-md border border-fitloop-orange bg-fitloop-orange px-3 py-2 text-sm font-medium text-white shadow-sm shadow-black/20 transition hover:brightness-110"
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

      {notice.message ? (
        <p className={`mt-4 rounded-md border px-3 py-2 text-sm leading-6 ${noticeTone}`}>
          {notice.message}
        </p>
      ) : null}
    </article>
  )
}

export default DataTransferPanel
