import type { ReactNode } from 'react'

/**
 * Purpose-built Markdown renderer for Tedy Books chapters.
 *
 * Chapter files use a deliberately small subset: headings, horizontal rules,
 * blockquotes (used for verse, where line breaks are significant), lists and
 * inline emphasis. Rendering to React elements rather than an HTML string
 * keeps the reader immune to markup smuggled into a chapter file.
 */

type Block =
  | { kind: 'heading'; level: 2 | 3 | 4; text: string }
  | { kind: 'verse'; lines: string[] }
  | { kind: 'list'; ordered: boolean; items: string[] }
  | { kind: 'rule' }
  | { kind: 'paragraph'; text: string; sourceLines: number }

const HEADING_RE = /^(#{1,6})\s+(.*)$/
const RULE_RE = /^\s*(?:---+|\*\*\*+|___+)\s*$/
const QUOTE_RE = /^>\s?(.*)$/
const UL_RE = /^\s*[-*+]\s+(.+)$/
const OL_RE = /^\s*\d+[.)]\s+(.+)$/

function parseBlocks(markdown: string): Block[] {
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
      blocks.push({ kind: 'heading', level, text: heading[2].trim() })
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

    const listMatch = UL_RE.exec(line) || OL_RE.exec(line)
    if (listMatch) {
      flushParagraph()
      const ordered = OL_RE.test(line)
      const items: string[] = []
      while (i < lines.length) {
        const m = ordered ? OL_RE.exec(lines[i]) : UL_RE.exec(lines[i])
        if (!m) break
        items.push(m[1].trim())
        i++
      }
      i--
      blocks.push({ kind: 'list', ordered, items })
      continue
    }

    paragraph.push(line.trim())
  }

  flushParagraph()
  return foldLooseVerse(blocks)
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
}

export function renderMarkdown(markdown: string, options: RenderOptions = {}): ReactNode[] {
  const blocks = parseBlocks(markdown)
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
          <Tag key={key} className="bookmd__list">
            {block.items.map((item, j) => (
              <li key={j}>{renderInline(item, `${key}-${j}`, options.renderToken)}</li>
            ))}
          </Tag>
        )
      }

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
