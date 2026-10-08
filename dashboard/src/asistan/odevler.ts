import type { HomeworkItem } from '../types'
const KAPALI = new Set(['yaptı', 'yapti', 'yapmadı', 'yapmadi', 'eksik'])
export function acikOdevler(liste: HomeworkItem[]): HomeworkItem[] {
  return (liste || []).filter(hw => hw.homework_key && !KAPALI.has((hw['Ödev Durumu'] || '').toLocaleLowerCase('tr-TR'))).slice(0, 20)
}
