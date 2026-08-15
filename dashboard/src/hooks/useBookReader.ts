import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from 'react'

/**
 * Reader preferences and reading position, both persisted to localStorage.
 *
 * Position is deliberately device-local: it is a "where was I on this screen"
 * bookmark, not shared state, so it needs no server round-trip and survives
 * offline reading.
 */

const SETTINGS_KEY = 'tedy-books-settings'
const PROGRESS_KEY = 'tedy-books-progress'

export const READER_THEMES = ['paper', 'sepia', 'night'] as const
export const READER_FONTS = ['serif', 'sans'] as const

export type ReaderTheme = (typeof READER_THEMES)[number]
export type ReaderFont = (typeof READER_FONTS)[number]

export interface ReaderSettings {
  theme: ReaderTheme
  font: ReaderFont
  /** Index into a fixed scale rather than a raw px value, so steps stay tasteful. */
  fontSize: number
  lineHeight: number
  measure: number
}

export const READER_FONT_SIZES = ['1rem', '1.0625rem', '1.1875rem', '1.3125rem', '1.4375rem', '1.625rem']
export const READER_LINE_HEIGHTS = ['1.6', '1.75', '1.9', '2.05']
export const READER_MEASURES = ['32rem', '38rem', '44rem']

export const DEFAULT_READER_SETTINGS: ReaderSettings = {
  theme: 'paper',
  font: 'serif',
  fontSize: 2,
  lineHeight: 1,
  measure: 1,
}

function clampIndex(value: unknown, length: number, fallback: number): number {
  const n = Number(value)
  return Number.isInteger(n) && n >= 0 && n < length ? n : fallback
}

function readSettings(): ReaderSettings {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY)
    if (!raw) return DEFAULT_READER_SETTINGS
    const parsed = JSON.parse(raw) as Partial<ReaderSettings>
    return {
      theme: READER_THEMES.includes(parsed.theme as ReaderTheme)
        ? (parsed.theme as ReaderTheme) : DEFAULT_READER_SETTINGS.theme,
      font: READER_FONTS.includes(parsed.font as ReaderFont)
        ? (parsed.font as ReaderFont) : DEFAULT_READER_SETTINGS.font,
      fontSize: clampIndex(parsed.fontSize, READER_FONT_SIZES.length, DEFAULT_READER_SETTINGS.fontSize),
      lineHeight: clampIndex(parsed.lineHeight, READER_LINE_HEIGHTS.length, DEFAULT_READER_SETTINGS.lineHeight),
      measure: clampIndex(parsed.measure, READER_MEASURES.length, DEFAULT_READER_SETTINGS.measure),
    }
  } catch {
    return DEFAULT_READER_SETTINGS
  }
}

export function useReaderSettings() {
  const [settings, setSettings] = useState<ReaderSettings>(readSettings)

  const update = useCallback((patch: Partial<ReaderSettings>) => {
    setSettings(prev => {
      const next = { ...prev, ...patch }
      try {
        localStorage.setItem(SETTINGS_KEY, JSON.stringify(next))
      } catch { /* storage full or blocked — preferences simply won't persist */ }
      return next
    })
  }, [])

  return { settings, update }
}

/* ── Reading position ─────────────────────────────────────────────────────── */

export interface ChapterProgress {
  ratio: number
  done: boolean
}

export interface BookProgress {
  lastChapterId: string | null
  updatedAt: string | null
  chapters: Record<string, ChapterProgress>
}

const EMPTY_PROGRESS: BookProgress = { lastChapterId: null, updatedAt: null, chapters: {} }

type ProgressStore = Record<string, BookProgress>

/** Fired on every local write so open screens re-read without polling. */
const PROGRESS_EVENT = 'tedy:books-progress'

function readRawStore(): string {
  try {
    return localStorage.getItem(PROGRESS_KEY) ?? ''
  } catch {
    return ''
  }
}

function readStore(): ProgressStore {
  const raw = readRawStore()
  if (!raw) return {}
  try {
    const parsed = JSON.parse(raw)
    return parsed && typeof parsed === 'object' ? (parsed as ProgressStore) : {}
  } catch {
    return {}
  }
}

function writeStore(store: ProgressStore) {
  try {
    localStorage.setItem(PROGRESS_KEY, JSON.stringify(store))
  } catch { /* storage full or blocked — the bookmark just won't persist */ }
  window.dispatchEvent(new Event(PROGRESS_EVENT))
}

function normalize(entry: BookProgress | undefined): BookProgress {
  if (!entry) return EMPTY_PROGRESS
  return {
    lastChapterId: typeof entry.lastChapterId === 'string' ? entry.lastChapterId : null,
    updatedAt: typeof entry.updatedAt === 'string' ? entry.updatedAt : null,
    chapters: entry.chapters && typeof entry.chapters === 'object' ? entry.chapters : {},
  }
}

export function readBookProgress(slug: string): BookProgress {
  return normalize(readStore()[slug])
}

function subscribeProgress(onChange: () => void) {
  window.addEventListener('storage', onChange)
  window.addEventListener(PROGRESS_EVENT, onChange)
  return () => {
    window.removeEventListener('storage', onChange)
    window.removeEventListener(PROGRESS_EVENT, onChange)
  }
}

/**
 * Subscribe to a book's saved position. The snapshot is the raw stored string —
 * a stable primitive — so `useSyncExternalStore` can compare it cheaply; parsing
 * happens once per actual change.
 */
export function useBookProgress(slug: string | undefined): BookProgress {
  const raw = useSyncExternalStore(subscribeProgress, readRawStore, () => '')

  return useMemo(() => {
    if (!slug || !raw) return EMPTY_PROGRESS
    try {
      const store = JSON.parse(raw) as ProgressStore
      return normalize(store?.[slug])
    } catch {
      return EMPTY_PROGRESS
    }
  }, [raw, slug])
}

const SAVE_INTERVAL_MS = 1200

/**
 * Persist the reading position for one chapter. Scroll fires continuously, so
 * writes are coalesced onto a timer and flushed on unmount.
 */
export function useProgressWriter(slug: string | undefined, chapterId: string | undefined) {
  const pending = useRef<{ ratio: number; done: boolean } | null>(null)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const flush = useCallback(() => {
    if (timer.current) {
      clearTimeout(timer.current)
      timer.current = null
    }
    const next = pending.current
    pending.current = null
    if (!slug || !chapterId || !next) return

    const store = readStore()
    const book = store[slug] ?? { lastChapterId: null, updatedAt: null, chapters: {} }
    const previous = book.chapters?.[chapterId]
    store[slug] = {
      ...book,
      lastChapterId: chapterId,
      updatedAt: new Date().toISOString(),
      chapters: {
        ...book.chapters,
        [chapterId]: { ratio: next.ratio, done: next.done || previous?.done === true },
      },
    }
    writeStore(store)
  }, [slug, chapterId])

  const save = useCallback((ratio: number, done = false) => {
    pending.current = { ratio: Math.min(1, Math.max(0, ratio)), done }
    if (timer.current) return
    timer.current = setTimeout(() => {
      timer.current = null
      flush()
    }, SAVE_INTERVAL_MS)
  }, [flush])

  useEffect(() => flush, [flush])

  return { save, flush }
}
