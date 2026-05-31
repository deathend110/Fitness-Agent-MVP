import { parseMarkdownMessage } from '../../utils/markdownMessage.js'

function InlineSegments({ segments = [] }) {
  return segments.map((segment, index) => {
    const key = `${segment.type}-${index}-${segment.text || segment.href || ''}`

    if (segment.type === 'strong') {
      return (
        <strong className="font-semibold text-slate-900" key={key}>
          {segment.text}
        </strong>
      )
    }

    if (segment.type === 'code') {
      return (
        <code className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[0.92em] text-slate-700" key={key}>
          {segment.text}
        </code>
      )
    }

    if (segment.type === 'link') {
      return (
        <a
          className="text-fitloop-orange underline decoration-fitloop-orange/30 underline-offset-2"
          href={segment.href}
          key={key}
          rel="noreferrer"
          target="_blank"
        >
          {segment.text}
        </a>
      )
    }

    return <span key={key}>{segment.text}</span>
  })
}

function MarkdownMessage({ content = '' }) {
  const blocks = parseMarkdownMessage(content)

  return (
    <div className="space-y-2 break-words">
      {blocks.map((block, index) => {
        const key = `${block.type}-${index}`

        if (block.type === 'heading') {
          const HeadingTag = block.level === 1 ? 'h3' : block.level === 2 ? 'h4' : 'h5'
          return (
            <HeadingTag className="mt-1 text-sm font-semibold leading-6 text-slate-900" key={key}>
              <InlineSegments segments={block.children} />
            </HeadingTag>
          )
        }

        if (block.type === 'list') {
          const ListTag = block.ordered ? 'ol' : 'ul'
          return (
            <ListTag
              className={`space-y-1 pl-5 ${block.ordered ? 'list-decimal' : 'list-disc'}`}
              key={key}
            >
              {block.items.map((item, itemIndex) => (
                <li key={`${key}-${itemIndex}`}>
                  <InlineSegments segments={item.children} />
                </li>
              ))}
            </ListTag>
          )
        }

        if (block.type === 'code') {
          return (
            <pre
              className="max-w-full overflow-x-auto rounded-lg border border-fitloop-line bg-white px-3 py-2 font-mono text-xs leading-5 text-slate-700"
              key={key}
            >
              <code>{block.text}</code>
            </pre>
          )
        }

        return (
          <p className="whitespace-pre-wrap" key={key}>
            <InlineSegments segments={block.children} />
          </p>
        )
      })}
    </div>
  )
}

export default MarkdownMessage
