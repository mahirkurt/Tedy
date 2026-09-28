import { Checkmark } from '@carbon/icons-react'
import type { Ogretmen } from '../types'
import type { SubjectFamily } from '../theme/subjects'
import { subjectClass } from '../utils/subject'
import { GENEL } from '../hooks/useOgretmen'

interface Secenek {
  id: string
  ad: string
  aile: SubjectFamily | null
}

/**
 * Genel · Türkçe · Fen · Sosyal · Matematik (spec §1 "Seçici ve tema").
 *
 * A native radio group styled as chips: arrow keys move and select, Tab leaves the group,
 * and a screen reader hears "Öğretmen, grup; Matematik, radyo düğmesi, 5'ten 5'i". Chips wrap
 * on a phone, where five equal switcher segments cut "Matematik" short. Each chip carries its
 * subject's family, so the chosen one fills with its own accent; a checkmark says "chosen"
 * without colour (İ8, and forced-colors mode drops the fill).
 */
export default function OgretmenSecici({ liste, secili, onSec, hata }: {
  liste: Ogretmen[]
  secili: string
  onSec: (id: string) => void
  /** The sentence shown when the list could not be loaded; Genel still works. */
  hata?: string | null
}) {
  const secenekler: Secenek[] = [
    { id: GENEL, ad: 'Genel', aile: null },
    ...liste.map(o => ({ id: o.id, ad: o.kisa_ad, aile: o.renk_ailesi })),
  ]
  return (
    <fieldset className="ac__ogretmen">
      <legend className="ac__ogretmen-baslik">Öğretmen</legend>
      <div className="ac__ogretmen-secenekler">
        {secenekler.map(s => (
          <label key={s.id}
            className={['ac__ogretmen-secenek', s.aile && subjectClass(null, s.aile)].filter(Boolean).join(' ')}>
            <input
              type="radio"
              name="ac-ogretmen"
              value={s.id}
              checked={secili === s.id}
              onChange={() => onSec(s.id)}
              className="ac__ogretmen-girdi cds--visually-hidden"
            />
            <span className="ac__ogretmen-cip">
              {secili === s.id
                ? <Checkmark size={16} aria-hidden="true" />
                : s.aile && <span className="ac__ogretmen-isaret" aria-hidden="true" />}
              {s.ad}
            </span>
          </label>
        ))}
      </div>
      {hata && <p className="ac__ogretmen-hata" role="status">{hata}</p>}
    </fieldset>
  )
}
