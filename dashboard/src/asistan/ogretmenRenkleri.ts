import type { SubjectFamily } from '../theme/subjects'

/** Öğretmen modunda ders rengi Carbon AI Chat'e CSS özel özellikleriyle geçer (gölge köke miras); yalnız yüzey
 *  rolleri: okurun balonu ders yüzeyinde, ders yüzeyinin metniyle (surface/on-surface ≥ 4.5:1,
 *  tests/test_ders_renkleri.py). Eylem rengi asla boyanmaz: gönder düğmesi ve simgesi her kipte Carbon'un
 *  `--cds-button-primary` / `--cds-interactive` mavisidir (S35, B68). Panel kenarı ve üst şerit AsistanSayfasi.scss'te. */
export function ogretmenDegiskenleri(aile: SubjectFamily | null): Record<string, string> {
  if (!aile) return {}
  return {
    '--cds-chat-bubble-user': 'var(--ted-subject-surface)',
    '--cds-chat-bubble-user-text': 'var(--ted-subject-on-surface)',
  }
}
