import { Button } from '@carbon/react'
import { ArrowRight, Document } from '@carbon/icons-react'
import './patterns/patterns.scss'
import './NextThing.scss'

export interface NextThingProps {
  /** When this happens — "ŞİMDİ", "BU AKŞAM". */
  eyebrow: string
  /** What it is, named the way Işık would name it. */
  title: string
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
  attachments?: { name: string; url: string }[]
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
 * "BAŞLADIN" (İ9 — the action keeps its name through the flow), counts the
 * minutes down, and shows the teacher's instructions. When the box runs out it
 * offers one more, never a verdict on how much got done.
 */
export function NextThing({
  eyebrow, title, stepMinutes, stepSuffix = 'başla',
  actionLabel, onAction, variant = 'work', hint,
  due, quiet, box, instruction, attachments, onMore, onStop, onDone, doneState = 'bos',
}: NextThingProps) {
  if (quiet) {
    return (
      <section className="next-thing next-thing--quiet" aria-label="Okuldan sonraki iş">
        <div className="next-thing__body">
          <span className="next-thing__eyebrow">{eyebrow}</span>
          <p className="next-thing__title">{title}</p>
          {due && <span className="next-thing__due">{due}</span>}
        </div>
      </section>
    )
  }

  const suruyor = box?.durum === 'suruyor'
  const doldu = box?.durum === 'doldu'
  const ust = suruyor
    ? `BAŞLADIN · ${box.kalanDk} dk kaldı`
    : doldu ? 'SÜRE DOLDU' : eyebrow

  return (
    <section
      className={[
        'next-thing',
        variant === 'reading' && 'next-thing--reading',
        suruyor && 'next-thing--running',
      ].filter(Boolean).join(' ')}
    >
      <div className="next-thing__body">
        <span className="next-thing__eyebrow">{ust}</span>
        <h2 className="next-thing__title">{title}</h2>
        {due && <span className="next-thing__due">{due}</span>}

        {!box && (
          <span className="next-thing__step">
            <span className="next-thing__step-time tedy-time">{stepMinutes} dakikayla</span> {stepSuffix}
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
              <li key={i}>
                <a href={ek.url} target="_blank" rel="noopener noreferrer">
                  <Document size={16} /> {ek.name}
                </a>
              </li>
            ))}
          </ul>
        )}

        {doldu && (
          <p className="next-thing__hint">
            {stepMinutes} dakika doldu. Devam etmek istersen bir {stepMinutes} dakika daha.
          </p>
        )}
        {box && doneState === 'hata' && (
          <p className="next-thing__error" role="alert">
            Kaydedilemedi. Bağlantını kontrol edip yeniden dene.
          </p>
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
            {onDone && (
              <Button kind="secondary" size="lg" onClick={onDone} disabled={doneState === 'kaydediliyor'}>
                {doneState === 'kaydediliyor' ? 'Kaydediliyor…' : 'Yaptım'}
              </Button>
            )}
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
            {onDone && (
              <Button kind="secondary" size="lg" onClick={onDone} disabled={doneState === 'kaydediliyor'}>
                {doneState === 'kaydediliyor' ? 'Kaydediliyor…' : 'Yaptım'}
              </Button>
            )}
            {onStop && (
              <Button kind="ghost" size="lg" onClick={onStop}>Şimdilik bu kadar</Button>
            )}
          </>
        )}
      </div>
    </section>
  )
}
