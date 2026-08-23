import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from 'react'

/**
 * Reader preferences and reading position.
 *
 * Both are written to localStorage under a key namespaced by the signed-in
 * profile, so two people sharing a device never see each other's bookmarks or
 * type settings. The position is additionally mirrored to the server (see
 * `useBookProgressSync`) because a bookmark belongs to the reader rather than
 * to the browser; localStorage stays the working copy so reading survives a
 * dropped connection.
 */

const SETTINGS_KEY = 'tedy-books-settings'
const PROGRESS_KEY = 'tedy-books-progress'

/* ── Profile namespacing ───────────────────────────────────────────────────── */

/** Fired on every local write so open screens re-read without polling. */
const PROGRESS_EVENT = 'tedy:books-progress'

let profileKey = 'anon'

function settingsKey(): string {
  return `${SETTINGS_KEY}::${profileKey}`
}

function progressKey(): string {
  return `${PROGRESS_KEY}::${profileKey}`
}

/**
 * Point the reader's storage at one profile.
 *
 * Called during render (before any reader screen mounts) so the very first read
 * already hits the right key; the change notification is deferred to a
 * microtask to keep the render phase free of side effects.
 *
 * `inheritLegacy` hands the pre-namespacing bookmarks to this profile. Only
 * full-access accounts may inherit them — those bookmarks were necessarily
 * written by one of them, and letting a reader adopt them would be exactly the
 * cross-profile bleed the namespacing exists to prevent.
 */
export function activateReaderProfile(
  email: string | null | undefined,
  { inheritLegacy = false }: { inheritLegacy?: boolean } = {},
) {
  const next = email ? email.toLowerCase() : 'anon'
  if (next === profileKey) return
  profileKey = next
  if (inheritLegacy) adoptLegacyKeys()
  queueMicrotask(() => window.dispatchEvent(new Event(PROGRESS_EVENT)))
}

function adoptLegacyKeys() {
  try {
    for (const [legacy, scoped] of [
      [PROGRESS_KEY, progressKey()],
      [SETTINGS_KEY, settingsKey()],
    ]) {
      const value = localStorage.getItem(legacy)
      if (value !== null && localStorage.getItem(scoped) === null) {
        localStorage.setItem(scoped, value)
      }
    }
  } catch { /* storage blocked — nothing to inherit, nothing to lose */ }
}

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

/**
 * Column width expressed as a side margin instead of a maximum.
 *
 * On a phone the viewport is always narrower than the narrowest measure, so
 * `max-width` never binds and the control is dead. The same three steps read as
 * gutters there: a narrow column is one with wide margins.
 */
export const READER_GUTTERS = ['10%', '6%', '2.5%']

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
    const raw = localStorage.getItem(settingsKey())
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
        localStorage.setItem(settingsKey(), JSON.stringify(next))
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

export type ProgressStore = Record<string, BookProgress>

function readRawStore(): string {
  try {
    return localStorage.getItem(progressKey()) ?? ''
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
    localStorage.setItem(progressKey(), JSON.stringify(store))
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

/** The whole profile's shelf state, for "where was I last?" across books. */
export function useAllBookProgress(): ProgressStore {
  const raw = useSyncExternalStore(subscribeProgress, readRawStore, () => '')

  return useMemo(() => {
    if (!raw) return {}
    try {
      const store = JSON.parse(raw) as ProgressStore
      if (!store || typeof store !== 'object') return {}
      return Object.fromEntries(
        Object.entries(store).map(([slug, entry]) => [slug, normalize(entry)]),
      )
    } catch {
      return {}
    }
  }, [raw])
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

/* ── Server mirror ────────────────────────────────────────────────────────── */

const SYNC_DEBOUNCE_MS = 4000

function newerThan(a: BookProgress | undefined, b: BookProgress | undefined): boolean {
  if (!a?.updatedAt) return false
  if (!b?.updatedAt) return true
  return a.updatedAt >= b.updatedAt
}

/** Union of both copies; per book the more recently touched one wins. */
function mergeStores(local: ProgressStore, remote: ProgressStore): ProgressStore {
  const merged: ProgressStore = { ...local }
  for (const [slug, entry] of Object.entries(remote)) {
    if (!merged[slug] || newerThan(entry, merged[slug])) merged[slug] = normalize(entry)
  }
  return merged
}

/**
 * Keep this profile's reading position in step with the server: pull once on
 * sign-in, then push local movement on a lazy timer. Mounted once, at the app
 * shell — the reader screens stay unaware of it and keep reading from
 * localStorage whether or not the network cooperates.
 */
export function useBookProgressSync(email: string | null | undefined) {
  useEffect(() => {
    if (!email) return

    let cancelled = false
    let applyingRemote = false
    let timer: ReturnType<typeof setTimeout> | null = null

    /** Remote writes must not look like user activity, or push/apply ping-pong. */
    const applyRemote = (store: ProgressStore) => {
      applyingRemote = true
      try {
        writeStore(store)
      } finally {
        applyingRemote = false
      }
    }

    const push = async () => {
      const local = readStore()
      if (!Object.keys(local).length) return
      try {
        const res = await fetch('/api/books/progress', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ books: local }),
        })
        if (!res.ok || cancelled) return
        const data = await res.json()
        applyRemote(mergeStores(readStore(), (data?.books ?? {}) as ProgressStore))
      } catch { /* offline — the local copy is still authoritative here */ }
    }

    const schedule = () => {
      if (applyingRemote || timer) return
      timer = setTimeout(() => {
        timer = null
        void push()
      }, SYNC_DEBOUNCE_MS)
    }

    const hydrate = async () => {
      try {
        const res = await fetch('/api/books/progress', { credentials: 'include' })
        if (!res.ok || cancelled) return
        const data = await res.json()
        applyRemote(mergeStores(readStore(), (data?.books ?? {}) as ProgressStore))
      } catch { /* offline — carry on with what this device remembers */ }
      if (!cancelled) void push()
    }

    void hydrate()
    window.addEventListener(PROGRESS_EVENT, schedule)

    return () => {
      window.removeEventListener(PROGRESS_EVENT, schedule)
      // A pending push still goes out: the response is ignored, the write isn't.
      if (timer) {
        clearTimeout(timer)
        timer = null
        void push()
      }
      cancelled = true
    }
  }, [email])
}
