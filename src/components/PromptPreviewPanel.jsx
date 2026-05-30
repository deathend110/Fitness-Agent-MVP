function PromptPreviewPanel({ previewModel }) {
  const detailsProps = previewModel.defaultExpanded ? { open: true } : {}

  return (
    <details
      className="rounded-xl border border-fitloop-line bg-fitloop-panel p-4 shadow-xl shadow-black/20 xl:min-h-[32rem]"
      {...detailsProps}
    >
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 marker:hidden [&::-webkit-details-marker]:hidden">
        <h3 className="text-lg font-semibold text-slate-100">{previewModel.title}</h3>
        <span className="text-xs uppercase tracking-[0.16em] text-fitloop-orange">
          {previewModel.codeLabel}
        </span>
      </summary>

      <p className="mt-3 text-sm leading-6 text-slate-300">{previewModel.description}</p>
      <pre className="mt-4 overflow-x-auto whitespace-pre-wrap rounded-md border border-fitloop-line/80 bg-fitloop-ink/40 p-4 text-xs leading-6 text-slate-200">
        {previewModel.promptText}
      </pre>
    </details>
  )
}

export default PromptPreviewPanel
