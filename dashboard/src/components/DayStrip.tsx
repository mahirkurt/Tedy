import { clock, describeRemaining } from './patterns/time'
import { Rakamli } from './patterns/Rakamli'
import { gunParcalari, odevAraligi, PARCA_ADI, type GunGirdisi } from '../utils/gunSeridi'
import './patterns/patterns.scss'
import './DayStrip.scss'

export interface DayStripProps {
  /** Minutes since midnight. */
  nowMin: number
  /** When the day stops being spendable. */
  bedtimeMin: number
  /** When sustained attention stops being available. */
  focusEndMin: number
  /** Where homework time starts on a day without school. */
  dayStartMin: number
  /** Today's school, or null on a day without school. */
  school: { bas: number; bit: number } | null
}


/**
 * Today, from now until bedtime, drawn to scale and cut into named parts.
 *
 * Only the remaining span is drawn. Hours already spent are not actionable, so
 * giving them width would spend the reader's attention on nothing (İ7) — and
 * because the track is anchored to "now", it shortens by itself as the day goes
 * on, which is the time signal a date string cannot give (İ2). Each part says
 * what it is in its own words — Sabah, Okul, Ödev zamanı, Akşam — so the strip
 * reads without a legend and without an hour scale.
 */
export function DayStrip({ nowMin, bedtimeMin, focusEndMin, dayStartMin, school }: DayStripProps) {
  const girdi: GunGirdisi = {
    simdi: nowMin, yatma: bedtimeMin, odakSonu: focusEndMin, gunBasi: dayStartMin, okul: school,
  }
  const parcalar = gunParcalari(girdi)
  const span = Math.max(bedtimeMin - nowMin, 1)
  const genislik = (bas: number, bit: number) => ((bit - bas) / span) * 100

  // The homework slot is named under the strip as long as it is still ahead
  // or under way: it is where the card's work is anchored (İ3), and at its
  // usual fifteen minutes it is too narrow to carry its own name.
  const odev = odevAraligi(girdi)
  const odevGorunur = odev != null && odev.bit > nowMin && nowMin < bedtimeMin
  const remaining = describeRemaining(bedtimeMin - nowMin)

  const cumle = [
    `Şimdi ${clock(nowMin)}.`,
    ...parcalar.map(p => `${PARCA_ADI[p.tur]} ${clock(p.bas)}–${clock(p.bit)}.`),
    `${remaining}.`,
  ].join(' ')

  return (
    <section className="day-strip" aria-label={cumle}>
      {/* Sentence case (S38); only the figures are mono (.tedy-time). */}
      <div className="day-strip__head">
        <span className="day-strip__now-label">Şimdi <span className="tedy-time">{clock(nowMin)}</span></span>
        <span className="day-strip__left"><Rakamli metin={remaining} /></span>
      </div>

      {parcalar.length > 0 && (
        <div className="day-strip__track" aria-hidden="true">
          {/* First in the DOM so the last part stays :last-of-type. */}
          <div className="day-strip__now" />
          {parcalar.map((p, i) => (
            <div
              key={p.tur}
              className={`day-strip__part day-strip__part--${p.tur}`}
              // The last part fills what is left (flex), so rounding never
              // leaves a gap or pushes it past the rail's end.
              style={i < parcalar.length - 1 ? { inlineSize: `${genislik(p.bas, p.bit)}%` } : undefined}
            >
              <span className="day-strip__part-name">{PARCA_ADI[p.tur]}</span>
            </div>
          ))}
        </div>
      )}

      <div className="day-strip__foot">
        {odevGorunur && (
          <span className="day-strip__homework">
            <span className="day-strip__swatch" aria-hidden="true" />
            Ödev zamanı{' '}
            <span className="tedy-time">{clock(odev.bas)}–{clock(odev.bit)}</span>
          </span>
        )}
        <span className="day-strip__end-label">Yatma <span className="tedy-time">{clock(bedtimeMin)}</span></span>
      </div>
    </section>
  )
}
