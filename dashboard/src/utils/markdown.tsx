import type { ReactNode } from 'react'

/**
 * Purpose-built Markdown renderer for Tedy Books chapters and the assistant's
 * answers.
 *
 * Chapter files use a deliberately small subset: headings, horizontal rules,
 * blockquotes (used for verse, where line breaks are significant), lists and
 * inline emphasis. Rendering to React elements rather than an HTML string
 * keeps the reader immune to markup smuggled into a chapter file.
 *
 * The assistant (`bicim: 'sohbet'`) is set as an interface, not a book: its
 * own `ac-md__*` classes in Carbon type, no first-line indent, no loose-verse
 * folding, and a few shapes the model writes that a book never does — a bold
 * line standing in for a heading, a closing "**Şimdi:**" line, a table.
 */

interface ListItem { text: string; children?: { ordered: boolean; items: string[] } }

type Block =
  | { kind: 'heading'; level: 2 | 3 | 4; hashes: number; text: string }
  | { kind: 'verse'; lines: string[] }
  | { kind: 'list'; ordered: boolean; start: number; items: ListItem[] }
  | { kind: 'table'; header: string[]; rows: string[][] }
  | { kind: 'rule' }
  | { kind: 'paragraph'; text: string; sourceLines: number }

const HEADING_RE = /^(#{1,6})\s+(.*)$/
const RULE_RE = /^\s*(?:---+|\*\*\*+|___+)\s*$/
const QUOTE_RE = /^>\s?(.*)$/
const ITEM_RE = /^(\s*)([-*+]|\d+[.)])\s+(.+)$/
const TABLE_SEP_RE = /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/

/** Width of a line's indent, a tab counting as four. */
const indentOf = (s: string) => s.replace(/\t/g, '    ').length
const isOrdered = (marker: string) => /\d/.test(marker)
const tableCells = (line: string) =>
  line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map(c => c.trim())

function parseBlocks(markdown: string, sohbet: boolean): Block[] {
  const lines = markdown.replace(/\r\n?/g, '\n').split('\n')
  const blocks: Block[] = []
  let paragraph: string[] = []

  const flushParagraph = () => {
    if (paragraph.length === 0) return
    blocks.push({
      kind: 'paragraph',
      text: paragraph.join(' ').trim(),
      sourceLines: paragraph.length,
    })
    paragraph = []
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]

    if (line.trim() === '') {
      flushParagraph()
      continue
    }

    if (RULE_RE.test(line)) {
      flushParagraph()
      blocks.push({ kind: 'rule' })
      continue
    }

    const heading = HEADING_RE.exec(line)
    if (heading) {
      flushParagraph()
      const level = Math.min(4, Math.max(2, heading[1].length + 1)) as 2 | 3 | 4
      blocks.push({ kind: 'heading', level, hashes: heading[1].length, text: heading[2].trim() })
      continue
    }

    if (sohbet && line.trim().startsWith('|') && TABLE_SEP_RE.test(lines[i + 1] ?? '')) {
      flushParagraph()
      const header = tableCells(line)
      const rows: string[][] = []
      i += 2
      while (i < lines.length && lines[i].trim().startsWith('|')) {
        rows.push(tableCells(lines[i]))
        i++
      }
      i--
      blocks.push({ kind: 'table', header, rows })
      continue
    }

    if (QUOTE_RE.test(line)) {
      flushParagraph()
      const verse: string[] = []
      while (i < lines.length) {
        const quoted = QUOTE_RE.exec(lines[i])
        if (quoted) {
          verse.push(quoted[1])
          i++
        } else if (lines[i].trim() === '' && QUOTE_RE.test(lines[i + 1] ?? '')) {
          verse.push('')
          i++
        } else {
          break
        }
      }
      i--
      blocks.push({ kind: 'verse', lines: verse })
      continue
    }

    const first = ITEM_RE.exec(line)
    if (first) {
      flushParagraph()
      const ordered = isOrdered(first[2])
      const start = ordered ? parseInt(first[2], 10) : 1
      const items: ListItem[] = []
      while (i < lines.length) {
        const cur = lines[i]
        const m = ITEM_RE.exec(cur)
        if (m && indentOf(m[1]) < 2) {
          // A top-level item of the other kind starts a new list.
          if (isOrdered(m[2]) !== ordered) break
          items.push({ text: m[3].trim() })
          i++
          continue
        }
        if (m && items.length > 0) {
          // One level of nesting. It used to end the list, so a bullet under
          // "1." restarted the numbering at 1 below it.
          const last = items[items.length - 1]
          last.children ??= { ordered: isOrdered(m[2]), items: [] }
          last.children.items.push(m[3].trim())
          i++
          continue
        }
        if (cur.trim() === '') {
          // A blank line between items keeps the list (a loose list); each
          // item used to become its own list, every one numbered 1.
          let j = i + 1
          while (j < lines.length && lines[j].trim() === '') j++
          const next = ITEM_RE.exec(lines[j] ?? '')
          if (next && (indentOf(next[1]) >= 2 || isOrdered(next[2]) === ordered)) {
            i = j
            continue
          }
          break
        }
        if (/^\s{2,}\S/.test(cur) && items.length > 0) {
          // An indented line continues the item above it.
          const last = items[items.length - 1]
          const kids = last.children?.items
          if (kids?.length) kids[kids.length - 1] += ` ${cur.trim()}`
          else last.text += ` ${cur.trim()}`
          i++
          continue
        }
        break
      }
      i--
      blocks.push({ kind: 'list', ordered, start, items })
      continue
    }

    const t = line.trim()
    if (sohbet && BOLD_LINE_RE.test(t)) {
      // A bold line is a heading even when no blank line sets it off.
      flushParagraph()
      paragraph.push(t)
      flushParagraph()
      continue
    }
    if (sohbet && CALLOUT_RE.test(t)) flushParagraph()
    paragraph.push(t)
  }

  flushParagraph()
  // Short lines in an answer are short answers, not a song.
  return sohbet ? blocks : foldLooseVerse(blocks)
}

/* ── Unmarked verse ───────────────────────────────────────────────────────── */

const VERSE_MAX_LENGTH = 80
const VERSE_MIN_LINES = 2
const QUOTE_OPENERS = new Set(['"', '“', '«', "'", '‘', '’', '-', '–', '—'])

/**
 * A verse line looks nothing like prose: it is short, it stands alone between
 * blank lines, and it does not open with a quotation or dash the way dialogue
 * does. Requiring a run of them keeps stray short sentences out.
 */
function looksLikeVerseLine(block: Block): boolean {
  if (block.kind !== 'paragraph' || block.sourceLines !== 1) return false
  const text = block.text
  return text.length > 0
    && text.length < VERSE_MAX_LENGTH
    && !QUOTE_OPENERS.has(text[0])
}

/**
 * Chapter files do not always mark songs and inscriptions with `>`. Left alone,
 * each line would set as its own indented, justified paragraph — prose shape on
 * poetry. A `>` block is still authoritative; this only rescues what it misses.
 */
function foldLooseVerse(blocks: Block[]): Block[] {
  const out: Block[] = []
  let run: Block[] = []

  const flushRun = () => {
    if (run.length >= VERSE_MIN_LINES) {
      out.push({
        kind: 'verse',
        lines: run.map(b => (b.kind === 'paragraph' ? b.text : '')),
      })
    } else {
      out.push(...run)
    }
    run = []
  }

  for (const block of blocks) {
    if (looksLikeVerseLine(block)) {
      run.push(block)
    } else {
      flushRun()
      out.push(block)
    }
  }
  flushRun()

  return out
}

const INLINE_RE = /(\*\*[^*]+\*\*|__[^_]+__|\*[^*]+\*|_[^_]+_|`[^`]+`)/g

export type TokenRenderer = (token: string, key: string) => ReactNode

const CITATION_RE = /\[S\d+\]/g

/**
 * Push a plain-text run, handing any [S1] markers to the caller's renderer.
 *
 * Doing this inside renderInline rather than by splitting the source keeps a
 * citation in whatever block it was written in — a marker at the end of a list
 * item stays inside the <li> instead of landing after the list.
 */
function pushText(
  nodes: ReactNode[],
  text: string,
  key: string,
  renderToken?: TokenRenderer,
): void {
  if (!renderToken) {
    nodes.push(text)
    return
  }
  let last = 0
  let m: RegExpExecArray | null
  CITATION_RE.lastIndex = 0
  while ((m = CITATION_RE.exec(text)) !== null) {
    if (m.index > last) nodes.push(text.slice(last, m.index))
    nodes.push(renderToken(m[0], `${key}-c${m.index}`))
    last = m.index + m[0].length
  }
  if (last < text.length) nodes.push(text.slice(last))
}

/** Renders `**bold**`, `*italic*`, `_italic_` and `` `code` ``. */
function renderInline(
  text: string,
  keyPrefix: string,
  renderToken?: TokenRenderer,
): ReactNode[] {
  const nodes: ReactNode[] = []
  let last = 0
  let match: RegExpExecArray | null
  INLINE_RE.lastIndex = 0

  while ((match = INLINE_RE.exec(text)) !== null) {
    if (match.index > last) {
      pushText(nodes, text.slice(last, match.index), `${keyPrefix}-${last}`, renderToken)
    }
    const token = match[0]
    const key = `${keyPrefix}-${match.index}`
    if (token.startsWith('**') || token.startsWith('__')) {
      // The emphasised text is itself a plain-text run, so a [S1] marker
      // written inside "**...**" gets the same renderToken treatment as one
      // outside it — otherwise "**a warning [S1]**" (ordinary model prose)
      // would carry a citation into a <strong> that never became a chip.
      const inner: ReactNode[] = []
      pushText(inner, token.slice(2, -2), key, renderToken)
      nodes.push(<strong key={key}>{inner}</strong>)
    } else if (token.startsWith('`')) {
      // Code spans are verbatim by design: a "[S1]"-shaped string inside
      // `code` is example text, not a citation marker, so it deliberately
      // does NOT go through pushText/renderToken. Do not "fix" this to match
      // the bold/italic branches — that would turn code samples into chips.
      nodes.push(<code key={key}>{token.slice(1, -1)}</code>)
    } else {
      const inner: ReactNode[] = []
      pushText(inner, token.slice(1, -1), key, renderToken)
      nodes.push(<em key={key}>{inner}</em>)
    }
    last = match.index + token.length
  }

  if (last < text.length) {
    pushText(nodes, text.slice(last), `${keyPrefix}-${last}`, renderToken)
  }
  return nodes
}

interface RenderOptions {
  /** Enlarge the opening letter of the first paragraph, as a printed book does. */
  dropCap?: boolean
  /** Replace inline [S1]-style markers — used by the assistant for citations. */
  renderToken?: TokenRenderer
  /** 'kitap' (default) sets a chapter; 'sohbet' sets an assistant answer. */
  bicim?: 'kitap' | 'sohbet'
}

/** A paragraph that is nothing but bold text — the model's stand-in heading. */
const BOLD_LINE_RE = /^\*\*([^*]+?)\*\*:?$/
/** The two closing lines the prompt asks for, and the labels models reach for
 * instead of them. Anything else stays a paragraph with a bold lead. */
const CALLOUT_RE = /^\*\*(Şimdi|Öneri|İpucu|Sonraki adım|Not|Dikkat|Hatırlatma)\s*:\s*\*\*\s*(.+)$|^\*\*(Şimdi|Öneri|İpucu|Sonraki adım|Not|Dikkat|Hatırlatma)\*\*\s*:\s*(.+)$/
const EYLEM = new Set(['Şimdi', 'Öneri', 'İpucu', 'Sonraki adım'])

function renderSohbet(blocks: Block[], renderToken?: TokenRenderer): ReactNode[] {
  // The page's own title is an h2, so an answer's sections are h3 and their
  // parts h4 — never an h4 straight under the h2.
  let sawSection = false
  const heading = (key: string, text: string, depth: 3 | 4) => {
    const level = depth === 4 && !sawSection ? 3 : depth
    if (level === 3) sawSection = true
    const Tag = `h${level}` as 'h3' | 'h4'
    return (
      <Tag key={key} className={`ac-md__h ac-md__h--${level}`}>
        {renderInline(text.replace(/:\s*$/, ''), key, renderToken)}
      </Tag>
    )
  }
  const list = (key: string, ordered: boolean, items: ListItem[], start = 1) => {
    const Tag = ordered ? 'ol' : 'ul'
    return (
      <Tag key={key} className={`ac-md__list ac-md__list--${ordered ? 'ol' : 'ul'}`}
        start={ordered && start !== 1 ? start : undefined}>
        {items.map((item, j) => (
          <li key={j}>
            {renderInline(item.text, `${key}-${j}`, renderToken)}
            {item.children && list(`${key}-${j}-k`, item.children.ordered,
              item.children.items.map(text => ({ text })))}
          </li>
        ))}
      </Tag>
    )
  }

  return blocks.map((block, i) => {
    const key = `b${i}`
    switch (block.kind) {
      case 'rule':
        return <hr key={key} className="ac-md__rule" />
      case 'heading':
        // "#" to "###" are the answer's sections (the prompt asks for "###");
        // only a deeper heading is a part of one.
        return heading(key, block.text, block.hashes <= 3 ? 3 : 4)
      case 'verse':
        return (
          <blockquote key={key} className="ac-md__quote">
            {block.lines.map((line, j) => (
              <p key={j}>{renderInline(line, `${key}-${j}`, renderToken)}</p>
            ))}
          </blockquote>
        )
      case 'list':
        return list(key, block.ordered, block.items, block.start)
      case 'table':
        return (
          <table key={key} className="ac-md__table">
            <thead>
              <tr>{block.header.map((h, j) => (
                <th key={j} scope="col">{renderInline(h, `${key}-h${j}`, renderToken)}</th>
              ))}</tr>
            </thead>
            <tbody>
              {block.rows.map((row, r) => (
                <tr key={r}>{row.map((cell, j) => (
                  <td key={j}>{renderInline(cell, `${key}-${r}-${j}`, renderToken)}</td>
                ))}</tr>
              ))}
            </tbody>
          </table>
        )
      case 'paragraph': {
        const bold = BOLD_LINE_RE.exec(block.text)
        if (bold && bold[1].length <= 80) return heading(key, bold[1], 4)
        const callout = CALLOUT_RE.exec(block.text)
        if (callout) {
          const label = callout[1] ?? callout[3]
          const body = callout[2] ?? callout[4]
          return (
            <div key={key} className={`ac-md__callout ac-md__callout--${EYLEM.has(label) ? 'eylem' : 'not'}`}>
              <span className="ac-md__callout-label">{label}</span>
              <p className="ac-md__p">{renderInline(body, key, renderToken)}</p>
            </div>
          )
        }
        return <p key={key} className="ac-md__p">{renderInline(block.text, key, renderToken)}</p>
      }
    }
  })
}

export function renderMarkdown(markdown: string, options: RenderOptions = {}): ReactNode[] {
  const sohbet = options.bicim === 'sohbet'
  const blocks = parseBlocks(markdown, sohbet)
  if (sohbet) return renderSohbet(blocks, options.renderToken)
  let paragraphIndex = 0

  return blocks.map((block, i) => {
    const key = `b${i}`

    switch (block.kind) {
      case 'rule':
        return <hr key={key} className="bookmd__rule" />

      case 'heading': {
        const Tag = `h${block.level}` as 'h2' | 'h3' | 'h4'
        return (
          <Tag key={key} className={`bookmd__heading bookmd__heading--${block.level}`}>
            {renderInline(block.text, key, options.renderToken)}
          </Tag>
        )
      }

      case 'verse':
        return (
          <div key={key} className="bookmd__verse">
            {block.lines.map((line, j) =>
              line.trim() === ''
                ? <span key={j} className="bookmd__verse-gap" />
                : <span key={j} className="bookmd__verse-line">{renderInline(line, `${key}-${j}`, options.renderToken)}</span>
            )}
          </div>
        )

      case 'list': {
        const Tag = block.ordered ? 'ol' : 'ul'
        return (
          <Tag key={key} className="bookmd__list" start={block.ordered && block.start !== 1 ? block.start : undefined}>
            {block.items.map((item, j) => (
              <li key={j}>
                {renderInline(item.text, `${key}-${j}`, options.renderToken)}
                {item.children && (
                  item.children.ordered
                    ? <ol className="bookmd__list">{item.children.items.map((t, k) => <li key={k}>{renderInline(t, `${key}-${j}-${k}`, options.renderToken)}</li>)}</ol>
                    : <ul className="bookmd__list">{item.children.items.map((t, k) => <li key={k}>{renderInline(t, `${key}-${j}-${k}`, options.renderToken)}</li>)}</ul>
                )}
              </li>
            ))}
          </Tag>
        )
      }

      case 'table':
        // Parsed only for 'sohbet'; a chapter never reaches here.
        return null

      case 'paragraph': {
        const isFirst = paragraphIndex === 0
        paragraphIndex++
        const className = [
          'bookmd__p',
          options.dropCap && isFirst && /^[\p{L}]/u.test(block.text) && 'bookmd__p--dropcap',
        ].filter(Boolean).join(' ')
        return (
          <p key={key} className={className}>
            {renderInline(block.text, key, options.renderToken)}
          </p>
        )
      }
    }
  })
}
