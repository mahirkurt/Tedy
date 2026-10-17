import { Button, InlineLoading, InlineNotification } from '@carbon/react'
import { ArrowRight } from '@carbon/icons-react'
import type { PortalEki } from '../types'
import { EkBaglantisi } from './patterns/EkBaglantisi'
import { Rakamli } from './patterns/Rakamli'
import './patterns/patterns.scss'
import './NextThing.scss'
import SubjectLabel from './SubjectLabel'
import { subjectClass } from '../utils/subject'

export interface NextThingProps {
  /** When this happens — "Şimdi", "Bu akşam" (sentence case, S38). */
  eyebrow: string
  /** What it is, named the way Işık would name it. */
  title: string
  /** The course the work belongs to: its mark leads the title, and its panel
   *  is the card's ground (Tedy İ8 — the view's one subject surface). */
  course?: string
  /** The opening move. A box to start inside, not a claim about length. */
  stepMinutes: number
  stepSuffix?: string
  actionLabel: string
  onAction: () => void
  variant?: 'work' | 'reading'
  /** When the window is closed, a quieter reason — not a second action. */
  hint?: string
  /** "Teslim yarın 12:00": when it is owed, as a day rather than a countdown. */
  due?: string
  /** Before the last bell the work is a preview under the lesson: named and
   *  dated, not yet an action (İ1 — the lesson is the one thing then). */
  quiet?: boolean
  /** The box "Başla" opened, once it is open. */
  box?: { durum: 'suruyor'; kalanDk: number } | { durum: 'doldu' }
  /** The teacher's own words, shown while the box runs — what to do for
   *  those minutes, without going to find it on another page (İ5). */
  instruction?: string[]
  attachments?: PortalEki[]
  /** Another box, once one has run out. */
  onMore?: () => void
  /** Close the box and return the card to rest. */
  onStop?: () => void
  /** "Yaptım" inside the box: record the work as done, on this page. */
  onDone?: () => void
  doneState?: 'bos' | 'kaydediliyor' | 'hata'
}

/**
 * The single named next step.
 *
 * It offers a time box rather than an estimate: nothing in the portal tells us
 * how long a piece of homework takes, so saying "10 dakika" as a duration would
 * be an invention. "10 dakikayla başla" is a proposal — honest, and the part
 * that makes an over-estimated task startable (principle İ3).
 *
 * "Başla" opens that box in place when the caller passes one: the card says
 * "Başladın" (İ9 — the action keeps its name through the flow), counts the
 * minutes down, and shows the teacher's instructions. When the box runs out it
 * offers one more, never a verdict on how much got done.
 *
 * The card is the view's one subject panel (İ8.3): the course's step-10 ground,
 * its step-30 border and a 4px accent edge — the edge, not the ground, is what
 * separates a grey family's panel from the page (talimatname [3.2-15]). Without
 * a course (reading) it is a neutral layer with a strong edge.
 */
export function NextThing({
  eyebrow, title, stepMinutes, stepSuffix = 'başla',
  actionLabel, onAction, variant = 'work', hint,
  due, quiet, box, instruction, attachments, onMore, onStop, onDone, doneState = 'bos',
  course,
}: NextThingProps) {
  const baslik = course ? <SubjectLabel course={course}>{title}</SubjectLabel> : title
  if (quiet) {
    return (
      <section className="next-thing next-thing--quiet" aria-label="Okuldan sonraki iş">
        <div className="next-thing__body">
          <span className="next-thing__eyebrow">{eyebrow}</span>
          <p className="next-thing__title">{baslik}</p>
          {due && <span className="next-thing__due"><Rakamli metin={due} /></span>}
        </div>
      </section>
    )
  }

  const suruyor = box?.durum === 'suruyor'
  const doldu = box?.durum === 'doldu'
  const ust = suruyor
    ? `Başladın · ${box.kalanDk} dk kaldı`
    : doldu ? 'Süre doldu' : eyebrow
  const kaydediliyor = doneState === 'kaydediliyor'

  // Saving replaces the button that started it (S36): one InlineLoading, in
  // place, and nothing else on the card moves.
  // While the box runs "Yaptım" is the card's only forward action, so it is the
  // primary; once the box has run out "10 dakika daha" is, and "Yaptım" steps
  // down to tertiary. Carbon keeps secondary for the negative action beside a
  // primary, and allows one primary per view (talimatname §4.1, S12).
  const yaptimDugmesi = onDone && (kaydediliyor
    ? <InlineLoading className="next-thing__saving" description="Kaydediliyor…" iconDescription="Kaydediliyor" />
    : <Button kind={doldu ? 'tertiary' : 'primary'} size="lg" onClick={onDone}>Yaptım</Button>)

  return (
    <section
      className={[
        'next-thing',
        course ? subjectClass(course) : 'next-thing--neutral',
        variant === 'reading' && 'next-thing--reading',
        suruyor && 'next-thing--running',
      ].filter(Boolean).join(' ')}
    >
      <div className="next-thing__body">
        <span className="next-thing__eyebrow"><Rakamli metin={ust} /></span>
        <h2 className="next-thing__title">{baslik}</h2>
        {due && <span className="next-thing__due"><Rakamli metin={due} /></span>}

        {!box && (
          <span className="next-thing__step">
            <span className="next-thing__step-time"><Rakamli metin={String(stepMinutes)} /> dakikayla</span> {stepSuffix}
          </span>
        )}
        {!box && hint && <p className="next-thing__hint">{hint}</p>}

        {suruyor && (instruction?.length ?? 0) > 0 && (
          <div className="next-thing__instruction">
            {instruction!.map((satir, i) => <p key={i}>{satir}</p>)}
          </div>
        )}
        {suruyor && (attachments?.length ?? 0) > 0 && (
          <ul className="next-thing__attachments">
            {attachments!.map((ek, i) => (
              <li key={ek.id ?? `${i}-${ek.url}`}><EkBaglantisi ek={ek} /></li>
            ))}
          </ul>
        )}

        {doldu && (
          <p className="next-thing__hint">
            <Rakamli metin={`${stepMinutes} dakika doldu. Devam etmek istersen bir ${stepMinutes} dakika daha.`} />
          </p>
        )}
        {/* A failed "Yaptım" says so on the card it was pressed on, and the box
            stays open: nothing the reader did is lost to a network error (D3). */}
        {box && doneState === 'hata' && (
          <InlineNotification
            className="next-thing__error"
            kind="error"
            lowContrast
            hideCloseButton
            role="alert"
            statusIconDescription="Hata"
            title="Kaydedilemedi"
            subtitle="Bağlantını kontrol edip yeniden dene."
          />
        )}
      </div>

      <div className="next-thing__action">
        {!box && (
          <Button kind="primary" size="lg" renderIcon={ArrowRight} onClick={onAction}>
            {actionLabel}
          </Button>
        )}
        {suruyor && (
          <>
            {yaptimDugmesi}
            {onStop && <Button kind="ghost" size="lg" onClick={onStop}>Bırak</Button>}
          </>
        )}
        {doldu && (
          <>
            {onMore && (
              <Button kind="primary" size="lg" onClick={onMore}>
                {stepMinutes} dakika daha
              </Button>
            )}
            {yaptimDugmesi}
            {onStop && (
              <Button kind="ghost" size="lg" onClick={onStop}>Şimdilik bu kadar</Button>
            )}
          </>
        )}
      </div>
    </section>
  )
}
