import { useEffect, useMemo, useState } from 'react'
import type { CSSProperties } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { Tag } from '@carbon/react'
import { ArrowRight, ArrowLeft, CheckmarkFilled, Time, Book as BookIcon } from '@carbon/icons-react'
import { useApi } from '../hooks/useApi'
import { useBookProgress, useAllBookProgress } from '../hooks/useBookReader'
import { useSession } from '../contexts/session'
import Ornament from './Ornament'
import type { BookSummary, BookDetail as BookDetailType, BookChapter } from '../types'

/* ── Shared pieces ─────────────────────────────────────────────────────────── */

export function BookCover({ book, size = 'md' }: { book: BookSummary; size?: 'sm' | 'md' | 'lg' }) {
  const palette = book.cover?.palette || 'forest'
  return (
    <div className={`book-cover book-cover--${size}`} data-palette={palette} aria-hidden>
      <div className="book-cover__spine" />
      <div className="book-cover__frame">
        <span className="book-cover__author">{book.author}</span>
        <span className="book-cover__rule" />
        <span
          className="book-cover__title"
          style={{ '--kelime': Math.max(...book.title.split(/\s+/).map(k => k.length)) } as CSSProperties}
        >{book.title}</span>
        {book.subtitle && <span className="book-cover__subtitle">{book.subtitle}</span>}
        <span className="book-cover__ornament"><Ornament variant="mark" /></span>
        <span className="book-cover__imprint">{book.publisher}</span>
      </div>
    </div>
  )
}

function formatMinutes(minutes: number): string {
  if (!minutes) return '—'
  if (minutes < 60) return `${minutes} dk`
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return m ? `${h} sa ${m} dk` : `${h} sa`
}

/* ── Home-page callout ─────────────────────────────────────────────────────── */

/**
 * Deliberately styled against the light Carbon dashboard rather than with it:
 * on the "Bugün" page this dark, gold-ruled block reads as a doorway into a
 * different room, which is exactly what it is.
 */
export function BooksCallout() {
  const navigate = useNavigate()
  const { data, loading } = useApi<{ books: BookSummary[] }>('/api/books', { books: [] })
  const book = data.books[0]
  const progress = useBookProgress(book?.slug)

  if (loading || !book) return null

  const resumeId = progress.lastChapterId
  const target = resumeId ? `/kitaplar/${book.slug}/${resumeId}` : `/kitaplar/${book.slug}`

  return (
    <section className="books-callout" data-palette={book.cover?.palette || 'forest'}>
      <BookCover book={book} size="sm" />

      <div className="books-callout__text">
        <p className="books-callout__eyebrow">Tedy Books</p>
        <h2 className="books-callout__title">{book.title}</h2>
        <p className="books-callout__meta">
          {book.author}
          {book.subtitle && <> · {book.subtitle}</>}
          <> · {book.availableChapters}/{book.totalChapters} bölüm hazır</>
        </p>
      </div>

      <div className="books-callout__actions">
        <button
          type="button"
          className="books-callout__cta"
          onClick={() => navigate(target)}
        >
          {resumeId ? 'Kaldığın yerden oku' : 'Okumaya başla'}
          <ArrowRight size={16} />
        </button>
        <Link to="/kitaplar" className="books-callout__link">Kitaplığa git</Link>
      </div>
    </section>
  )
}

/* ── Resume band ───────────────────────────────────────────────────────────── */

/**
 * "Where you left off", pulled from this profile's own bookmark.
 *
 * The shelf's job is to show what exists; this band's job is to get the reader
 * back into the text in one click, so it sits above the shelf, wears the book's
 * own cloth, and names the exact chapter rather than just the book.
 */
function ResumeBand({ books }: { books: BookSummary[] }) {
  const progress = useAllBookProgress()
  const [detail, setDetail] = useState<BookDetailType | null>(null)

  // Most recently touched book that is still on the shelf.
  const latest = useMemo(() => {
    const shelved = new Set(books.map(b => b.slug))
    return Object.entries(progress)
      .filter(([slug, entry]) => shelved.has(slug) && entry.lastChapterId && entry.updatedAt)
      .sort((a, b) => (b[1].updatedAt || '').localeCompare(a[1].updatedAt || ''))[0]
  }, [books, progress])

  const slug = latest?.[0]
  const lastChapterId = latest?.[1].lastChapterId ?? null

  useEffect(() => {
    if (!slug) return
    let cancelled = false
    fetch(`/api/books/${slug}`, { credentials: 'include' })
      .then(res => (res.ok ? res.json() : null))
      .then(data => { if (!cancelled) setDetail(data) })
      .catch(() => { if (!cancelled) setDetail(null) })
    return () => { cancelled = true }
  }, [slug])

  // Detail lags the bookmark by one fetch; rendering it against a different
  // book would show the wrong chapter for a frame.
  if (!slug || !lastChapterId || detail?.slug !== slug) return null

  const readable = detail.chapters.filter(c => c.available)
  const index = readable.findIndex(c => c.id === lastChapterId)
  if (index < 0) return null

  const chapter = readable[index]
  const ratio = latest[1].chapters[lastChapterId]?.ratio ?? 0
  const pct = Math.max(1, Math.round(ratio * 100))
  const finished = readable.filter(c => latest[1].chapters[c.id]?.done).length

  return (
    <section className="resume-band" data-palette={detail.cover?.palette || 'forest'}>
      <div className="resume-band__cover">
        <BookCover book={detail} size="sm" />
      </div>

      <div className="resume-band__text">
        <p className="resume-band__eyebrow">
          Kaldığın yer
          <span className="resume-band__rule" aria-hidden />
        </p>
        <h2 className="resume-band__chapter">
          {chapter.label && <span className="resume-band__label">{chapter.label} · </span>}
          {chapter.title}
        </h2>
        <p className="resume-band__book">{detail.title} · {detail.author}</p>

        <div className="resume-band__meter" aria-hidden>
          <div className="resume-band__meter-fill" style={{ width: `${pct}%` }} />
        </div>
        <p className="resume-band__meta">
          Bu bölümde %{pct} okudun · {index + 1}. bölüm / {readable.length}
          {finished > 0 && <> · {finished} bölüm tamamlandı</>}
        </p>
      </div>

      <Link to={`/kitaplar/${slug}/${lastChapterId}`} className="resume-band__cta">
        Devam et
        <ArrowRight size={16} />
      </Link>
    </section>
  )
}

/* ── Shelf: /kitaplar ──────────────────────────────────────────────────────── */

export default function TedyBooks() {
  const { data, loading } = useApi<{ books: BookSummary[] }>('/api/books', { books: [] })
  const user = useSession()
  const isReader = user?.role === 'reader'

  if (loading) {
    return (
      <div className="books-loading">
        <div className="books-loading__cover" />
        <div className="books-loading__lines">
          <span /><span /><span />
        </div>
      </div>
    )
  }

  return (
    <div className={`books${isReader ? ' books--reader' : ''}`}>
      <header className="books__masthead">
        {isReader && (
          <p className="books__exlibris">
            <span className="books__exlibris-label">Ex libris</span>
            <span className="books__exlibris-name">{user?.name || user?.email}</span>
          </p>
        )}
        <p className="books__eyebrow">Tedy Books</p>
        <h1 className="books__wordmark">Kitaplık</h1>
        <p className="books__tagline">
          {isReader
            ? 'Bu raf yalnızca sana ait. Okuduğun yer hesabına kayıtlı; hangi cihazdan girersen gir kaldığın yerden devam edersin.'
            : 'Rafındaki kitapları buradan, kendi okuma düzeninde okuyabilirsin.'}
        </p>
      </header>

      {data.books.length > 0 && <ResumeBand books={data.books} />}

      {data.books.length === 0 ? (
        <div className="books-empty">
          <BookIcon size={32} className="books-empty__icon" />
          <h2 className="books-empty__title">Raf henüz boş</h2>
          <p className="books-empty__text">
            <code>books/</code> klasörüne bir kitap eklendiğinde burada görünür.
          </p>
        </div>
      ) : (
        <div className="books__shelf">
          {data.books.map(book => <ShelfCard key={book.slug} book={book} />)}
        </div>
      )}
    </div>
  )
}

function ShelfCard({ book }: { book: BookSummary }) {
  const navigate = useNavigate()
  const progress = useBookProgress(book.slug)
  const readyPct = book.totalChapters
    ? Math.round((book.availableChapters / book.totalChapters) * 100)
    : 0
  const resumeId = progress.lastChapterId

  return (
    <article className="shelf-card">
      {/* A second way to the book page for the pointer; keyboard and screen
          reader reach it through "İçindekiler". As its own tab stop its name
          ("… — kitap sayfası") did not contain the cover's visible text, which
          fails WCAG 2.5.3 (IBM Equal Access, 2026-09-25). */}
      <Link to={`/kitaplar/${book.slug}`} className="shelf-card__cover-link" tabIndex={-1} aria-hidden="true">
        <BookCover book={book} size="lg" />
      </Link>

      <div className="shelf-card__body">
        <div className="shelf-card__head">
          <h2 className="shelf-card__title">{book.title}</h2>
          {book.subtitle && <p className="shelf-card__subtitle">{book.subtitle}</p>}
          <p className="shelf-card__byline">
            {book.author}
            {book.translator && <> · çev. {book.translator}</>}
          </p>
        </div>

        {book.description && <p className="shelf-card__desc">{book.description}</p>}

        <div className="shelf-card__actions">
          <button
            type="button"
            className="book-btn book-btn--primary"
            onClick={() => navigate(
              resumeId
                ? `/kitaplar/${book.slug}/${resumeId}`
                : `/kitaplar/${book.slug}`
            )}
            disabled={book.availableChapters === 0}
          >
            {resumeId ? 'Kaldığın yerden devam et' : 'Okumaya başla'}
            <ArrowRight size={16} />
          </button>
          <Link to={`/kitaplar/${book.slug}`} className="book-btn book-btn--ghost">
            İçindekiler
          </Link>
        </div>

        <dl className="shelf-card__stats">
          <div>
            <dt>Hazır bölüm</dt>
            <dd>{book.availableChapters} / {book.totalChapters}</dd>
          </div>
          <div>
            <dt>Okuma süresi</dt>
            <dd>{formatMinutes(book.readingMinutes)}</dd>
          </div>
          {book.edition && (
            <div>
              <dt>Baskı</dt>
              <dd>{book.edition}</dd>
            </div>
          )}
        </dl>

        <div className="shelf-card__meter">
          <div className="shelf-card__meter-track">
            <div className="shelf-card__meter-fill" style={{ width: `${readyPct}%` }} />
          </div>
          <span className="shelf-card__meter-label">
            Kitabın %{readyPct} kadarı yayında · yeni bölümler eklendikçe burada belirir
          </span>
        </div>
      </div>
    </article>
  )
}

/* ── Book page: /kitaplar/:slug ────────────────────────────────────────────── */

interface ChapterGroup {
  volume: string
  parts: { part: string; chapters: BookChapter[] }[]
}

function groupChapters(chapters: BookChapter[]): ChapterGroup[] {
  const groups: ChapterGroup[] = []
  for (const ch of chapters) {
    let group = groups.find(g => g.volume === ch.volume)
    if (!group) {
      group = { volume: ch.volume, parts: [] }
      groups.push(group)
    }
    let part = group.parts.find(p => p.part === ch.part)
    if (!part) {
      part = { part: ch.part, chapters: [] }
      group.parts.push(part)
    }
    part.chapters.push(ch)
  }
  return groups
}

export function BookDetail() {
  const { slug } = useParams<{ slug: string }>()
  const navigate = useNavigate()
  const { data: book, loading, error } = useApi<BookDetailType | null>(
    `/api/books/${slug}`, null
  )
  const progress = useBookProgress(slug)

  const groups = useMemo(() => groupChapters(book?.chapters ?? []), [book])
  const firstAvailable = book?.chapters.find(c => c.available)
  const resumeId = progress.lastChapterId && book?.chapters.some(
    c => c.id === progress.lastChapterId && c.available
  ) ? progress.lastChapterId : null

  if (loading) {
    return (
      <div className="books-loading">
        <div className="books-loading__cover" />
        <div className="books-loading__lines"><span /><span /><span /></div>
      </div>
    )
  }

  if (error || !book) {
    return (
      <div className="books-empty">
        <h2 className="books-empty__title">Kitap bulunamadı</h2>
        <p className="books-empty__text">Bu kitap rafta yok ya da okunamadı.</p>
        <Link to="/kitaplar" className="book-btn book-btn--ghost">Kitaplığa dön</Link>
      </div>
    )
  }

  return (
    <div className="book-page">
      <Link to="/kitaplar" className="book-page__back">
        <ArrowLeft size={16} /> Kitaplık
      </Link>

      <header className="book-page__title-page">
        <BookCover book={book} size="md" />
        <div className="book-page__title-text">
          <p className="book-page__author">{book.author}</p>
          <h1 className="book-page__title">{book.title}</h1>
          {book.subtitle && <p className="book-page__subtitle">{book.subtitle}</p>}
          <p className="book-page__imprint">
            {[book.translator && `çev. ${book.translator}`, book.publisher, book.edition]
              .filter(Boolean).join(' · ')}
          </p>
          {book.epigraph && <p className="book-page__epigraph">“{book.epigraph}”</p>}
          <div className="book-page__actions">
            <button
              type="button"
              className="book-btn book-btn--primary"
              disabled={!firstAvailable}
              onClick={() => {
                const target = resumeId || firstAvailable?.id
                if (target) navigate(`/kitaplar/${book.slug}/${target}`)
              }}
            >
              {resumeId ? 'Devam et' : 'Okumaya başla'}
              <ArrowRight size={16} />
            </button>
            <span className="book-page__ready">
              {book.availableChapters} / {book.totalChapters} bölüm hazır
            </span>
          </div>
        </div>
      </header>

      <div className="book-page__ornament"><Ornament /></div>

      <section className="book-toc">
        <h2 className="book-toc__heading">İçindekiler</h2>
        {groups.map(group => (
          <div key={group.volume || 'tek'} className="book-toc__volume">
            {group.volume && <h3 className="book-toc__volume-title">{group.volume}</h3>}
            {group.parts.map(part => (
              <div key={part.part || 'bolumler'} className="book-toc__part">
                {part.part && part.part !== group.volume && (
                  <h4 className="book-toc__part-title">{part.part}</h4>
                )}
                <ol className="book-toc__list">
                  {part.chapters.map(ch => (
                    <TocRow
                      key={ch.id}
                      slug={book.slug}
                      chapter={ch}
                      ratio={progress.chapters[ch.id]?.ratio ?? 0}
                      done={progress.chapters[ch.id]?.done ?? false}
                    />
                  ))}
                </ol>
              </div>
            ))}
          </div>
        ))}
      </section>
    </div>
  )
}

function TocRow({ slug, chapter, ratio, done }: {
  slug: string
  chapter: BookChapter
  ratio: number
  done: boolean
}) {
  const pct = Math.round(ratio * 100)

  if (!chapter.available) {
    return (
      <li className="book-toc__row book-toc__row--pending">
        <span className="book-toc__num">{chapter.numeral || '—'}</span>
        <span className="book-toc__title">{chapter.title}</span>
        <Tag type="cool-gray" size="sm">Yakında</Tag>
      </li>
    )
  }

  return (
    <li className="book-toc__row">
      <Link to={`/kitaplar/${slug}/${chapter.id}`} className="book-toc__link">
        <span className="book-toc__num">{chapter.numeral || '—'}</span>
        <span className="book-toc__title">{chapter.title}</span>
        <span className="book-toc__meta">
          {done ? (
            <span className="book-toc__done"><CheckmarkFilled size={14} /> Okundu</span>
          ) : pct > 2 ? (
            <span className="book-toc__partial">%{pct}</span>
          ) : null}
          <span className="book-toc__minutes"><Time size={14} /> {chapter.readingMinutes} dk</span>
        </span>
      </Link>
    </li>
  )
}
