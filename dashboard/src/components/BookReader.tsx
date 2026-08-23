import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import {
  Close, ChevronLeft, ChevronRight, ListBulleted, TextFont,
  Add, Subtract, CheckmarkFilled, Translate,
} from '@carbon/icons-react'
import { useApi } from '../hooks/useApi'
import {
  useReaderSettings, useProgressWriter, readBookProgress,
  READER_FONT_SIZES, READER_LINE_HEIGHTS, READER_MEASURES, READER_GUTTERS,
  type ReaderTheme, type ReaderFont,
} from '../hooks/useBookReader'
import { renderMarkdown } from '../utils/markdown'
import Ornament from './Ornament'
import type { BookChapterResponse, BookDetail } from '../types'
import './BookReaderTranslation.scss'

const THEME_OPTIONS: { id: ReaderTheme; label: string }[] = [
  { id: 'paper', label: 'Kâğıt' },
  { id: 'sepia', label: 'Sepya' },
  { id: 'night', label: 'Gece' },
]

const FONT_OPTIONS: { id: ReaderFont; label: string }[] = [
  { id: 'serif', label: 'Serif' },
  { id: 'sans', label: 'Sans' },
]

/* Smooth scrolling and late-loading webfonts mean the ratio rarely settles at a
   clean 1.0, so "finished" is generous rather than exact. */
const DONE_THRESHOLD = 0.95
const TRANSLATION_MAX_BYTES = 500
const TRANSLATION_CONTEXT_MAX_BYTES = 1500

function selectionSentenceContext(range: Range, element: Element) {
  const sourceText = range.toString().replace(/\s+/g, ' ').trim()
  const block = element.closest('.bookmd__p, .bookmd__verse, li, blockquote')
  if (!block?.textContent) return sourceText

  const fullText = block.textContent
  const prefix = range.cloneRange()
  prefix.selectNodeContents(block)
  prefix.setEnd(range.startContainer, range.startOffset)
  const selectionStart = prefix.toString().length
  const selectionEnd = selectionStart + range.toString().length

  let sentenceStart = 0
  const beforeSelection = fullText.slice(0, selectionStart)
  const startBoundary = /[.!?](?:["'’”)\]]*)?(?:\s+|$)/g
  for (const match of beforeSelection.matchAll(startBoundary)) {
    sentenceStart = (match.index ?? 0) + match[0].length
  }

  const tailStart = Math.max(selectionStart, selectionEnd - 1)
  const afterSelection = fullText.slice(tailStart)
  const endBoundary = afterSelection.match(/[.!?](?:["'’”)\]]*)?(?=\s|$)/)
  const sentenceEnd = endBoundary?.index === undefined
    ? fullText.length
    : tailStart + endBoundary.index + endBoundary[0].length
  const context = fullText.slice(sentenceStart, sentenceEnd).replace(/\s+/g, ' ').trim()

  return new TextEncoder().encode(context).length <= TRANSLATION_CONTEXT_MAX_BYTES
    ? context
    : sourceText
}

interface TranslationResponse {
  sourceText: string
  translatedText: string
  sourceLanguage: string
  targetLanguage: string
  provider: string
}

interface TranslationState {
  sourceText: string
  translatedText: string
  provider: string
  status: 'loading' | 'ready' | 'error'
  error: string
}

export default function BookReader() {
  const { slug, chapterId } = useParams<{ slug: string; chapterId: string }>()
  const navigate = useNavigate()
  const scrollRef = useRef<HTMLDivElement>(null)
  const pageRef = useRef<HTMLElement>(null)
  const lastScrollY = useRef(0)
  const restored = useRef<string | null>(null)
  const translationRequest = useRef<AbortController | null>(null)
  const lastSelection = useRef('')

  const { settings, update } = useReaderSettings()
  const { save, flush } = useProgressWriter(slug, chapterId)

  const { data, loading, error } = useApi<BookChapterResponse | null>(
    `/api/books/${slug}/chapters/${chapterId}`, null
  )
  const { data: detail } = useApi<BookDetail | null>(`/api/books/${slug}`, null)

  const [ratio, setRatio] = useState(0)
  const [chromeVisible, setChromeVisible] = useState(true)
  const [panel, setPanel] = useState<'toc' | 'type' | null>(null)
  const [translation, setTranslation] = useState<TranslationState | null>(null)

  const chapter = data?.chapter
  const translationEnabled = data?.book.language.toLowerCase() === 'en'
  const body = useMemo(
    () => (chapter ? renderMarkdown(chapter.content, { dropCap: true }) : null),
    [chapter]
  )

  /* The reader owns the whole viewport, so the page behind it must not scroll. */
  useEffect(() => {
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = previous }
  }, [])

  /* Restore the saved position once, after the chapter has actually rendered. */
  useEffect(() => {
    if (!chapter || !slug || !chapterId) return
    if (restored.current === chapterId) return
    restored.current = chapterId

    const saved = readBookProgress(slug).chapters[chapterId]?.ratio ?? 0
    const el = scrollRef.current
    if (!el) return

    const frame = requestAnimationFrame(() => {
      const span = el.scrollHeight - el.clientHeight
      if (saved > 0.01 && saved < DONE_THRESHOLD && span > 0) {
        el.scrollTop = saved * span
        setRatio(saved)
      } else {
        el.scrollTop = 0
        setRatio(0)
      }
    })
    return () => cancelAnimationFrame(frame)
  }, [chapter, slug, chapterId])

  const handleScroll = useCallback(() => {
    const el = scrollRef.current
    if (!el) return
    const span = el.scrollHeight - el.clientHeight
    const y = el.scrollTop
    const next = span > 0 ? Math.min(1, Math.max(0, y / span)) : 1
    setRatio(next)
    save(next, next >= DONE_THRESHOLD)

    if (y < 72) setChromeVisible(true)
    else if (y > lastScrollY.current + 10) setChromeVisible(false)
    else if (y < lastScrollY.current - 10) setChromeVisible(true)
    lastScrollY.current = y
  }, [save])

  /**
   * Tapping the page toggles the toolbar, the way a reading app does. Once the
   * chrome has auto-hidden on scroll-down this is the only way back to the
   * table of contents without scrolling to the top first.
   */
  const handleSurfaceClick = useCallback((e: React.MouseEvent) => {
    const target = e.target as HTMLElement
    if (target.closest('button, a, input, select')) return
    if (!window.getSelection()?.isCollapsed) return
    setChromeVisible(v => !v)
  }, [])

  const closeTranslation = useCallback(() => {
    translationRequest.current?.abort()
    translationRequest.current = null
    lastSelection.current = ''
    setTranslation(null)
    window.getSelection()?.removeAllRanges()
  }, [])

  const translateSelection = useCallback(async (sourceText: string, context: string) => {
    translationRequest.current?.abort()
    const controller = new AbortController()
    translationRequest.current = controller
    lastSelection.current = `${sourceText}\u0000${context}`

    if (new TextEncoder().encode(sourceText).length > TRANSLATION_MAX_BYTES) {
      setTranslation({
        sourceText,
        translatedText: '',
        provider: '',
        status: 'error',
        error: 'En fazla tek kısa cümle seçebilirsin.',
      })
      return
    }

    setTranslation({
      sourceText,
      translatedText: '',
      provider: '',
      status: 'loading',
      error: '',
    })

    try {
      const response = await fetch('/api/books/translate', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: sourceText, context }),
        signal: controller.signal,
      })
      const payload = await response.json() as TranslationResponse & { error?: string }
      if (!response.ok || !payload.translatedText) {
        throw new Error(payload.error || `HTTP ${response.status}`)
      }
      setTranslation({
        sourceText: payload.sourceText,
        translatedText: payload.translatedText,
        provider: payload.provider,
        status: 'ready',
        error: '',
      })
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return
      setTranslation(current => current?.sourceText === sourceText ? {
        ...current,
        status: 'error',
        error: 'Çeviri şu anda alınamadı. Biraz sonra yeniden dene.',
      } : current)
    }
  }, [])

  useEffect(() => {
    if (!translationEnabled || !chapter) return
    let timer: number | undefined

    const captureSelection = () => {
      window.clearTimeout(timer)
      timer = window.setTimeout(() => {
        const selection = window.getSelection()
        if (!selection || selection.isCollapsed || selection.rangeCount === 0) return

        const range = selection.getRangeAt(0)
        const ancestor = range.commonAncestorContainer
        const element = ancestor.nodeType === Node.ELEMENT_NODE
          ? ancestor as Element
          : ancestor.parentElement
        if (!element || !pageRef.current?.contains(element)) return

        const sourceText = selection.toString().replace(/\s+/g, ' ').trim()
        const context = selectionSentenceContext(range, element)
        const selectionKey = `${sourceText}\u0000${context}`
        if (!sourceText || selectionKey === lastSelection.current) return
        void translateSelection(sourceText, context)
      }, 280)
    }

    document.addEventListener('selectionchange', captureSelection)
    return () => {
      window.clearTimeout(timer)
      document.removeEventListener('selectionchange', captureSelection)
    }
  }, [chapter, translationEnabled, translateSelection])

  useEffect(() => {
    closeTranslation()
  }, [chapterId, closeTranslation])

  useEffect(() => () => translationRequest.current?.abort(), [])

  const goToChapter = useCallback((targetId: string) => {
    flush()
    restored.current = null
    lastScrollY.current = 0
    setPanel(null)
    setChromeVisible(true)
    navigate(`/kitaplar/${slug}/${targetId}`)
  }, [flush, navigate, slug])

  const exit = useCallback(() => {
    flush()
    navigate(`/kitaplar/${slug}`)
  }, [flush, navigate, slug])

  /* Keyboard: arrows page through chapters, Escape leaves the book. */
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const target = e.target as HTMLElement | null
      if (target && /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName)) return
      if (e.key === 'Escape') {
        if (translation) closeTranslation()
        else if (panel) setPanel(null)
        else exit()
      } else if (e.key === 'ArrowRight' && data?.next) {
        goToChapter(data.next.id)
      } else if (e.key === 'ArrowLeft' && data?.prev) {
        goToChapter(data.prev.id)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [data, panel, translation, closeTranslation, exit, goToChapter])

  const style = {
    '--reader-font-size': READER_FONT_SIZES[settings.fontSize],
    '--reader-line-height': READER_LINE_HEIGHTS[settings.lineHeight],
    '--reader-measure': READER_MEASURES[settings.measure],
    // Narrow viewports cannot honour a max-width; there the same step is a margin.
    '--reader-gutter': READER_GUTTERS[settings.measure],
  } as React.CSSProperties

  if (error) {
    return (
      <div className="reader" data-theme={settings.theme}>
        <div className="reader__fallback">
          <h2>Bölüm açılamadı</h2>
          <p>Bu bölüm henüz eklenmemiş olabilir.</p>
          <Link to={`/kitaplar/${slug}`} className="book-btn book-btn--ghost">İçindekiler</Link>
        </div>
      </div>
    )
  }

  return (
    <div
      className="reader"
      data-theme={settings.theme}
      data-font={settings.font}
      style={style}
    >
      <div className={`reader__chrome${chromeVisible || panel ? '' : ' reader__chrome--hidden'}`}>
        <div className="reader__bar">
          <button type="button" className="reader__icon-btn" onClick={exit} aria-label="Okumayı bitir">
            <Close size={18} />
          </button>

          <div className="reader__bar-title">
            <span className="reader__bar-book">{data?.book.title ?? 'Tedy Books'}</span>
            {chapter && (
              <span className="reader__bar-chapter">
                {[chapter.label, chapter.title].filter(Boolean).join(' · ')}
              </span>
            )}
          </div>

          <div className="reader__bar-actions">
            <button
              type="button"
              className={`reader__icon-btn${panel === 'type' ? ' reader__icon-btn--on' : ''}`}
              onClick={() => setPanel(p => (p === 'type' ? null : 'type'))}
              aria-label="Yazı ayarları"
              aria-expanded={panel === 'type'}
            >
              <TextFont size={18} />
            </button>
            <button
              type="button"
              className={`reader__icon-btn${panel === 'toc' ? ' reader__icon-btn--on' : ''}`}
              onClick={() => setPanel(p => (p === 'toc' ? null : 'toc'))}
              aria-label="İçindekiler"
              aria-expanded={panel === 'toc'}
            >
              <ListBulleted size={18} />
            </button>
          </div>
        </div>

        <div className="reader__progress" role="progressbar"
             aria-valuenow={Math.round(ratio * 100)} aria-valuemin={0} aria-valuemax={100}
             aria-label="Bölüm ilerlemesi">
          <div className="reader__progress-fill" style={{ width: `${ratio * 100}%` }} />
        </div>
      </div>

      {panel === 'type' && (
        <TypePanel settings={settings} update={update} onClose={() => setPanel(null)} />
      )}

      {panel === 'toc' && (
        <TocPanel
          detail={detail}
          currentId={chapterId}
          onPick={goToChapter}
          onClose={() => setPanel(null)}
        />
      )}

      <div
        className="reader__scroll"
        ref={scrollRef}
        onScroll={handleScroll}
        onClick={handleSurfaceClick}
      >
        {loading && !chapter ? (
          <div className="reader__skeleton">
            {Array.from({ length: 8 }).map((_, i) => <span key={i} />)}
          </div>
        ) : chapter ? (
          <article className="reader__page" ref={pageRef}>
            <header className="reader__opening">
              {chapter.partHeading && (
                <p className="reader__part">{chapter.partHeading}</p>
              )}
              {chapter.label && <p className="reader__chapter-label">{chapter.label}</p>}
              <h1 className="reader__chapter-title">{chapter.title}</h1>
              <p className="reader__ornament"><Ornament /></p>
              {translationEnabled && (
                <p className="reader__selection-hint">
                  Bir kelimeyi veya kısa cümleyi seç — Türkçe karşılığını gör.
                </p>
              )}
            </header>

            <div className="bookmd">{body}</div>

            <footer className="reader__end">
              <p className="reader__ornament"><Ornament /></p>
              {ratio >= DONE_THRESHOLD && (
                <p className="reader__done"><CheckmarkFilled size={16} /> Bu bölümü bitirdin</p>
              )}
              {chapter.credit && <p className="reader__credit">{chapter.credit}</p>}
              <div className="reader__end-nav">
                {data?.prev ? (
                  <button type="button" className="reader__end-btn" onClick={() => goToChapter(data.prev!.id)}>
                    <ChevronLeft size={16} />
                    <span>
                      <em>Önceki</em>
                      {data.prev.title}
                    </span>
                  </button>
                ) : <span />}
                {data?.next ? (
                  <button
                    type="button"
                    className="reader__end-btn reader__end-btn--next"
                    onClick={() => goToChapter(data.next!.id)}
                  >
                    <span>
                      <em>Sonraki</em>
                      {data.next.title}
                    </span>
                    <ChevronRight size={16} />
                  </button>
                ) : (
                  <p className="reader__end-note">
                    Yayındaki son bölüm. Yeni bölümler eklendikçe burada devam edecek.
                  </p>
                )}
              </div>
            </footer>
          </article>
        ) : null}
      </div>

      {translation && (
        <aside
          className="reader-translation"
          role="dialog"
          aria-label="Türkçe çeviri"
          aria-live="polite"
        >
          <header className="reader-translation__header">
            <span className="reader-translation__title">
              <Translate size={18} /> Türkçe çeviri
            </span>
            <button
              type="button"
              className="reader-translation__close"
              onClick={closeTranslation}
              aria-label="Çeviriyi kapat"
            >
              <Close size={16} />
            </button>
          </header>
          <p className="reader-translation__source" lang="en">{translation.sourceText}</p>
          {translation.status === 'loading' ? (
            <p className="reader-translation__status">Çevriliyor…</p>
          ) : translation.status === 'error' ? (
            <p className="reader-translation__error">{translation.error}</p>
          ) : (
            <>
              <p className="reader-translation__result" lang="tr">
                {translation.translatedText}
              </p>
              <p className="reader-translation__provider">{translation.provider}</p>
            </>
          )}
        </aside>
      )}
    </div>
  )
}

/* ── Panels ────────────────────────────────────────────────────────────────── */

function TypePanel({ settings, update, onClose }: {
  settings: ReturnType<typeof useReaderSettings>['settings']
  update: ReturnType<typeof useReaderSettings>['update']
  onClose: () => void
}) {
  return (
    <>
      <div className="reader__scrim" onClick={onClose} aria-hidden />
      <div className="reader-panel reader-panel--type" role="dialog" aria-label="Yazı ayarları">
        <div className="reader-panel__group">
          <span className="reader-panel__label">Tema</span>
          <div className="reader-panel__segmented">
            {THEME_OPTIONS.map(opt => (
              <button
                key={opt.id}
                type="button"
                className={`reader-panel__seg${settings.theme === opt.id ? ' reader-panel__seg--on' : ''}`}
                onClick={() => update({ theme: opt.id })}
              >
                <span className={`reader-panel__swatch reader-panel__swatch--${opt.id}`} />
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        <div className="reader-panel__group">
          <span className="reader-panel__label">Yazı tipi</span>
          <div className="reader-panel__segmented">
            {FONT_OPTIONS.map(opt => (
              <button
                key={opt.id}
                type="button"
                className={`reader-panel__seg reader-panel__seg--${opt.id}${settings.font === opt.id ? ' reader-panel__seg--on' : ''}`}
                onClick={() => update({ font: opt.id })}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        <Stepper
          label="Punto"
          value={settings.fontSize}
          max={READER_FONT_SIZES.length - 1}
          onChange={v => update({ fontSize: v })}
        />
        <Stepper
          label="Satır aralığı"
          value={settings.lineHeight}
          max={READER_LINE_HEIGHTS.length - 1}
          onChange={v => update({ lineHeight: v })}
        />
        <Stepper
          label="Sütun genişliği"
          value={settings.measure}
          max={READER_MEASURES.length - 1}
          onChange={v => update({ measure: v })}
        />
      </div>
    </>
  )
}

function Stepper({ label, value, max, onChange }: {
  label: string
  value: number
  max: number
  onChange: (v: number) => void
}) {
  return (
    <div className="reader-panel__group reader-panel__group--row">
      <span className="reader-panel__label">{label}</span>
      <div className="reader-panel__stepper">
        <button
          type="button" className="reader-panel__step" aria-label={`${label} küçült`}
          onClick={() => onChange(Math.max(0, value - 1))} disabled={value <= 0}
        >
          <Subtract size={16} />
        </button>
        <span className="reader-panel__dots" aria-hidden>
          {Array.from({ length: max + 1 }).map((_, i) => (
            <span key={i} className={i <= value ? 'is-on' : ''} />
          ))}
        </span>
        <button
          type="button" className="reader-panel__step" aria-label={`${label} büyüt`}
          onClick={() => onChange(Math.min(max, value + 1))} disabled={value >= max}
        >
          <Add size={16} />
        </button>
      </div>
    </div>
  )
}

function TocPanel({ detail, currentId, onPick, onClose }: {
  detail: BookDetail | null
  currentId?: string
  onPick: (id: string) => void
  onClose: () => void
}) {
  const chapters = detail?.chapters ?? []
  // Headings print only where the volume/part actually turns over. The part
  // heading matters here: chapter numerals restart at I inside every book.
  const rows = chapters.map((ch, i) => {
    const previous = chapters[i - 1]
    return {
      chapter: ch,
      showVolume: Boolean(ch.volume) && ch.volume !== previous?.volume,
      showPart: Boolean(ch.part) && ch.part !== ch.volume
        && (ch.part !== previous?.part || ch.volume !== previous?.volume),
    }
  })

  return (
    <>
      <div className="reader__scrim" onClick={onClose} aria-hidden />
      <nav className="reader-panel reader-panel--toc" aria-label="İçindekiler">
        <header className="reader-panel__head">
          <span className="reader-panel__title">İçindekiler</span>
          <button type="button" className="reader__icon-btn" onClick={onClose} aria-label="Kapat">
            <Close size={16} />
          </button>
        </header>
        <ol className="reader-toc">
          {rows.map(({ chapter: ch, showVolume, showPart }) => {
            return (
              <li key={ch.id}>
                {showVolume && <p className="reader-toc__volume">{ch.volume}</p>}
                {showPart && <p className="reader-toc__part">{ch.part}</p>}
                <button
                  type="button"
                  className={[
                    'reader-toc__item',
                    ch.id === currentId && 'reader-toc__item--current',
                    !ch.available && 'reader-toc__item--pending',
                  ].filter(Boolean).join(' ')}
                  onClick={() => ch.available && onPick(ch.id)}
                  disabled={!ch.available}
                >
                  <span className="reader-toc__num">{ch.numeral || '—'}</span>
                  <span className="reader-toc__name">{ch.title}</span>
                  {!ch.available && <span className="reader-toc__soon">Yakında</span>}
                </button>
              </li>
            )
          })}
        </ol>
      </nav>
    </>
  )
}
