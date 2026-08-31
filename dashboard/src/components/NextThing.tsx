import { Button } from '@carbon/react'
import { ArrowRight } from '@carbon/icons-react'
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
}

/**
 * The single named next step.
 *
 * It offers a time box rather than an estimate: nothing in the portal tells us
 * how long a piece of homework takes, so saying "10 dakika" as a duration would
 * be an invention. "10 dakikayla başla" is a proposal — honest, and the part
 * that makes an over-estimated task startable (principle İ3).
 */
export function NextThing({
  eyebrow, title, stepMinutes, stepSuffix = 'başla',
  actionLabel, onAction, variant = 'work',
}: NextThingProps) {
  return (
    <section className={`next-thing${variant === 'reading' ? ' next-thing--reading' : ''}`}>
      <div className="next-thing__body">
        <span className="next-thing__eyebrow">{eyebrow}</span>
        <h2 className="next-thing__title">{title}</h2>
        <span className="next-thing__step">
          <span className="next-thing__step-time">{stepMinutes} dakikayla</span> {stepSuffix}
        </span>
      </div>
      <div className="next-thing__action">
        <Button kind="primary" size="lg" renderIcon={ArrowRight} onClick={onAction}>
          {actionLabel}
        </Button>
      </div>
    </section>
  )
}
