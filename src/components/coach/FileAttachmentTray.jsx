import { useRef } from 'react'

function FileAttachmentTray({
  attachedFiles = [],
  disabled = false,
  isUploading = false,
  onFilesSelected,
  onRemoveFile,
}) {
  const inputRef = useRef(null)

  function handleChange(event) {
    const files = Array.from(event.target.files || [])
    if (files.length) {
      onFilesSelected?.(files)
    }
    event.target.value = ''
  }

  return (
    <div className="flex min-w-0 flex-1 items-center gap-2">
      <input
        className="sr-only"
        disabled={disabled}
        multiple
        onChange={handleChange}
        ref={inputRef}
        type="file"
      />
      <button
        aria-label="添加附件"
        className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-fitloop-line text-slate-400 transition hover:border-fitloop-orange/30 hover:text-fitloop-orange disabled:cursor-not-allowed disabled:opacity-40"
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
        type="button"
      >
        <span className="text-base leading-none">+</span>
      </button>

      <div className="flex min-w-0 flex-wrap items-center gap-1.5">
        {attachedFiles.map((file) => (
          <span
            className="inline-flex max-w-[180px] items-center gap-1 rounded-md border border-fitloop-line bg-fitloop-canvas px-2 py-1 text-[11px] text-slate-600"
            key={file.id || file.name}
            title={file.parserError || file.originalName || file.name}
          >
            <span className="truncate">{file.originalName || file.name}</span>
            {file.parserStatus && file.parserStatus !== 'parsed' ? (
              <span className="text-amber-600">{file.parserStatus}</span>
            ) : null}
            <button
              aria-label="移除附件"
              className="text-slate-400 hover:text-red-500"
              onClick={() => onRemoveFile?.(file.id)}
              type="button"
            >
              ×
            </button>
          </span>
        ))}
        {isUploading ? <span className="text-[11px] text-slate-400">上传中...</span> : null}
      </div>
    </div>
  )
}

export default FileAttachmentTray
