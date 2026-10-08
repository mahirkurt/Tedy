import type { BusEventFeedback } from '@carbon/ai-chat'
import { asistanDeposu } from './asistanDeposu.ts'

const KAYDEDILEMEDI = 'Geri bildirim kaydedilemedi.'

/** Carbon'un geri bildirim olayı → PUT /api/assistant/mesajlar/<id>/geri-bildirim (spec §5.2). Carbon gönderilmiş
 *  durumu kendisi gösterir; kaydedilemezse okura giriş üstünde söylenir (sessiz hata yok). */
export async function geriBildirimGonder(olay: BusEventFeedback, f: typeof fetch = fetch): Promise<void> {
  if (String(olay.interactionType) !== 'submitted') return
  const id = (olay.messageItem.message_item_options?.feedback?.id) ?? ''
  if (!/^[0-9a-f]{32}$/.test(id)) return
  const kategori = olay.isPositive ? null : (olay.categories?.[0] ?? null)
  try {
    const res = await f(`/api/assistant/mesajlar/${id}/geri-bildirim`, {
      method: 'PUT', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ deger: olay.isPositive ? 'olumlu' : 'olumsuz', kategori, metin: olay.text ?? '' }),
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
  } catch {
    asistanDeposu.ayarla({ uyari: KAYDEDILEMEDI })
  }
}
