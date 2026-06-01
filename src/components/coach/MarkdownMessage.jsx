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

        if (block.type === 'divider') {
          return <hr className="border-0 border-t border-fitloop-line/80" key={key} />
        }

        if (block.type === 'table') {
          return (
            <div className="overflow-x-auto rounded-lg border border-fitloop-line/80 bg-white" key={key}>
              <table className="min-w-full border-collapse text-left text-xs leading-5 text-slate-700">
                <thead className="bg-slate-50/90">
                  <tr>
                    {block.headers.map((header, headerIndex) => (
                      <th
                        className={`border-b border-fitloop-line/80 px-3 py-2 font-semibold text-slate-900 ${getTableAlignClass(block.alignments[headerIndex])}`}
                        key={`${key}-header-${headerIndex}`}
                      >
                        <InlineSegments segments={header} />
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {block.rows.map((row, rowIndex) => (
                    <tr className="odd:bg-white even:bg-slate-50/40" key={`${key}-row-${rowIndex}`}>
                      {row.map((cell, cellIndex) => (
                        <td
                          className={`border-t border-fitloop-line/60 px-3 py-2 align-top ${getTableAlignClass(block.alignments[cellIndex])}`}
                          key={`${key}-cell-${rowIndex}-${cellIndex}`}
                        >
                          <InlineSegments segments={cell} />
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
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

function getTableAlignClass(alignment = 'left') {
  if (alignment === 'center') {
    return 'text-center'
  }
  if (alignment === 'right') {
    return 'text-right'
  }
  return 'text-left'
}

export default MarkdownMessage
