import type { HomeworkItem } from '../types'
const KAPALI = new Set(['yaptı', 'yapti', 'yapmadı', 'yapmadi', 'eksik'])
export function acikOdevler(liste: HomeworkItem[]): HomeworkItem[] {
  return (liste || []).filter(hw => hw.homework_key && !KAPALI.has((hw['Ödev Durumu'] || '').toLocaleLowerCase('tr-TR'))).slice(0, 20)
}
/** Ödevin tam adı: kısaltılan menü satırının `title`'ı (B35 — kesilen ad tam metniyle okunur). */
export function odevTamAdi(hw: HomeworkItem): string {
  return `${hw.normalized_course || hw['Ders Adı']} — ${hw['Ödev Başlığı']}`
}
/** "Matematik — Kesirler": ödev menüsünde ve bağlam çipinde aynı ad. */
export function odevAdi(hw: HomeworkItem): string {
  const ad = odevTamAdi(hw)
  return ad.length > 80 ? `${ad.slice(0, 79)}…` : ad
}
