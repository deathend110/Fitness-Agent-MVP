function getAttachmentTypeLabel(attachment = {}) {
  const extension = String(attachment.extension || '').trim().toLowerCase()
  const mimeType = String(attachment.mimeType || '').trim().toLowerCase()

  if (extension === '.xlsx' || extension === '.xlsm' || mimeType.includes('sheet')) {
    return 'XLSX'
  }
  if (extension === '.docx' || mimeType.includes('wordprocessingml')) {
    return 'DOCX'
  }
  if (
    extension === '.png' ||
    extension === '.jpg' ||
    extension === '.jpeg' ||
    extension === '.webp' ||
    mimeType.startsWith('image/')
  ) {
    return 'IMG'
  }
  if (extension === '.md') {
    return 'MD'
  }
  if (extension === '.txt' || mimeType.startsWith('text/plain')) {
    return 'TXT'
  }

  return extension ? extension.replace('.', '').toUpperCase() : 'FILE'
}

function formatAttachmentSize(sizeBytes) {
  if (!Number.isFinite(sizeBytes) || sizeBytes <= 0) {
    return ''
  }

  if (sizeBytes >= 1024 * 1024) {
    return `${(sizeBytes / (1024 * 1024)).toFixed(2)}MB`
  }

  return `${(sizeBytes / 1024).toFixed(2)}KB`
}

function buildAttachmentMetaText(attachment = {}) {
  const typeLabel = getAttachmentTypeLabel(attachment)
  const sizeLabel = formatAttachmentSize(attachment.sizeBytes)
  return [typeLabel, sizeLabel].filter(Boolean).join(' ')
}

function getAttachmentIconClass(typeLabel) {
  if (typeLabel === 'XLSX') {
    return 'bg-emerald-100 text-emerald-600'
  }
  if (typeLabel === 'DOCX') {
    return 'bg-blue-100 text-blue-600'
  }
  if (typeLabel === 'IMG') {
    return 'bg-amber-100 text-amber-600'
  }
  return 'bg-slate-100 text-slate-500'
}

function MessageAttachmentCard({ attachment }) {
  const typeLabel = getAttachmentTypeLabel(attachment)
  const metaText = buildAttachmentMetaText(attachment)
  const fileName = attachment?.originalName || '未命名文件'

  return (
    <div className="flex w-full max-w-[360px] items-center gap-3 rounded-2xl border border-fitloop-line bg-white px-4 py-3 shadow-[0_10px_24px_rgba(148,163,184,0.12)]">
      <div
        aria-hidden="true"
        className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-xs font-semibold ${getAttachmentIconClass(typeLabel)}`}
      >
        {typeLabel}
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-slate-800">{fileName}</p>
        <p className="mt-0.5 text-xs text-slate-500">{metaText}</p>
      </div>
    </div>
  )
}

export default MessageAttachmentCard
