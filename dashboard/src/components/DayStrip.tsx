import { clock, describeRemaining } from './patterns/time'
import './patterns/patterns.scss'
import './DayStrip.scss'

export interface DayStripProps {
  /** Minutes since midnight. */
  nowMin: number
  /** When the day stops being spendable. */
  bedtimeMin: number
  /** When sustained attention stops being available. */
  focusEndMin: number
  /** Where the next thing sits, in minutes since midnight. */
  anchorMin?: number
}


/**
 * Today, from now until bedtime, drawn to scale.
 *
 * Only the remaining span is drawn. Hours already spent are not actionable, so
 * giving them width would spend the reader's attention on nothing (İ7) — and
 * because the track is anchored to "now", it shortens by itself as the day goes
 * on, which is the time signal a date string cannot give (İ2).
 */
export function DayStrip({ nowMin, bedtimeMin, focusEndMin, anchorMin }: DayStripProps) {
  const span = Math.max(bedtimeMin - nowMin, 1)
  const pct = (min: number) => ((min - nowMin) / span) * 100

  const windowEnd = Math.min(focusEndMin, bedtimeMin)
  const windowOpen = windowEnd > nowMin
  const windowWidth = windowOpen ? pct(windowEnd) : 0

  // Whole-hour marks inside the remaining span, thinned out so the row stays
  // information rather than texture. Anything that would collide with the
  // window boundary is dropped: that boundary carries its own label, and it is
  // the more useful of the two.
  const step = span > 8 * 60 ? 120 : 60
  const ticks: number[] = []
  for (let m = Math.ceil(nowMin / step) * step; m < bedtimeMin; m += step) {
    if (windowOpen && Math.abs(m - windowEnd) < 45) continue
    ticks.push(m)
  }

  const anchorPct =
    anchorMin !== undefined && anchorMin > nowMin && anchorMin < bedtimeMin
      ? pct(anchorMin)
      : undefined

  const remaining = describeRemaining(bedtimeMin - nowMin)

  return (
    <section
      className="day-strip"
      aria-label={
        `Şimdi ${clock(nowMin)}. ${remaining}. ` +
        (windowOpen ? `Odak penceresi ${clock(windowEnd)}'da kapanıyor. ` : '') +
        `Gün ${clock(bedtimeMin)}'da bitiyor.`
      }
    >
      <div className="day-strip__head">
        <span className="day-strip__now-label tedy-time">ŞİMDİ {clock(nowMin)}</span>
        <span className="day-strip__left">{remaining}</span>
        <span className="day-strip__end-label tedy-time">yatma {clock(bedtimeMin)}</span>
      </div>

      <div className="day-strip__track">
        {windowOpen && (
          <div className="day-strip__window" style={{ width: `${windowWidth}%` }} />
        )}
        <div className="day-strip__now" />
        {anchorPct !== undefined && (
          <div className="day-strip__anchor" style={{ insetInlineStart: `${anchorPct}%` }} />
        )}
      </div>

      <div className="day-strip__scale">
        {/* The boundary says the thing worth knowing: not "this band is the
            focus window", but "your focus ends here". */}
        {windowOpen && (
          <span
            // Centred on the boundary normally; when the window is short the
            // label would hang off the start of the strip, so it starts there
            // and runs right instead of being clipped.
            className={
              'day-strip__boundary tedy-time' +
              (windowWidth < 24 ? ' day-strip__boundary--start' : '')
            }
            style={{ insetInlineStart: `${windowWidth}%` }}
          >
            odak sonu {clock(windowEnd)}
          </span>
        )}
        {ticks.map(m => (
          <span key={m} className="day-strip__tick tedy-time" style={{ insetInlineStart: `${pct(m)}%` }}>
            {clock(m)}
          </span>
        ))}
      </div>

      {anchorPct !== undefined && (
        <div
          className="day-strip__anchor-line"
          style={{ ['--anchor-pos' as string]: `${anchorPct}%` }}
        />
      )}
    </section>
  )
}
