import type { HistoryItem, MessageResponse } from '@carbon/ai-chat'
import type { AssistantCitation, AssistantResponse } from '../types'
import type { KayitliMesaj } from '../hooks/useSohbetler'
import { akisBaslat, sonYanit } from './olayEslemesi.ts'
import type { SonYanitSecenekleri } from './olayEslemesi.ts'

/** B3 kaydı → Carbon geçmişi. Kayıtlı kartlar (alıştırma, netleştirme, ödev önerisi) geri gelir;
 *  araç adımları kaydedilmediği için eski cevapta adım listesi yoktur (spec §5.1). */
export function gecmisOgeleri(mesajlar: KayitliMesaj[], sec: SonYanitSecenekleri): HistoryItem[] {
  return mesajlar.map(m => {
    const time = m.zaman ?? new Date(0).toISOString()
    if (m.rol === 'user') return { message: { id: m.id, input: { text: m.icerik } }, time }
    const payload: AssistantResponse = {
      answer: m.icerik, citations: JSON.parse(m.atiflar_json || '[]') as AssistantCitation[], safety_flags: [],
      plan_blocks: [], intent: 'qa', session_id: '', meta: { model: '' }, mesaj_id: m.id,
      quiz: m.alistirma?.[0] ?? null, netlestirme: m.netlestirme ?? null, odev_onerisi: m.odev_onerisi ?? null,
    }
    const d = { ...akisBaslat(m.id), alistirmalar: m.alistirma ?? [] }
    const yanit: MessageResponse = sonYanit(d, payload, sec)
    const gb = m.geri_bildirim
    if (gb && sec.geriBildirim) {
      yanit.history = { feedback: { [m.id]: { is_positive: gb.deger === 'olumlu',
        ...(gb.metin ? { text: gb.metin } : {}), ...(gb.kategori ? { categories: [gb.kategori] } : {}) } } }
    }
    return { message: yanit, time }
  })
}
