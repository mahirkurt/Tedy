import type { SubjectFamily } from '../theme/subjects'

/** Öğretmen modunda ders rengi Carbon AI Chat'e CSS özel özellikleriyle geçer (gölge köke miras; Görev 1, 3.
 *  satır); marka bandı değişmez. Değerler aile sınıfının (`ted-subject--<aile>`) rol token'ları — eski
 *  `.ac[data-ogretmen]` kuralının aynısı (balonda surface/on-surface 4.5:1, tests/test_ders_renkleri.py). */
export function ogretmenDegiskenleri(aile: SubjectFamily | null): Record<string, string> {
  if (!aile) return {}
  return {
    '--cds-button-primary': 'var(--ted-subject-accent)',
    '--cds-button-primary-hover': 'var(--ted-subject-text)',
    '--cds-button-primary-active': 'var(--ted-subject-text)',
    // Carbon AI Chat'in gönder simgesi --cds-interactive ile boyanır (prompt-line/send-control).
    '--cds-interactive': 'var(--ted-subject-accent)',
    '--cds-chat-bubble-user': 'var(--ted-subject-surface)',
    '--cds-chat-bubble-user-text': 'var(--ted-subject-on-surface)',
  }
}
