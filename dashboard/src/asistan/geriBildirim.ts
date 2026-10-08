import type { BusEventFeedback } from '@carbon/ai-chat'

/** Carbon'un geri bildirim olayı → PUT /api/assistant/mesajlar/<id>/geri-bildirim (spec §5.2). */
export async function geriBildirimGonder(olay: BusEventFeedback): Promise<void> {
  if (String(olay.interactionType) !== 'submitted') return
  const id = (olay.messageItem.message_item_options?.feedback?.id) ?? ''
  if (!/^[0-9a-f]{32}$/.test(id)) return
  const kategori = olay.isPositive ? null : (olay.categories?.[0] ?? null)
  await fetch(`/api/assistant/mesajlar/${id}/geri-bildirim`, {
    method: 'PUT', credentials: 'include', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ deger: olay.isPositive ? 'olumlu' : 'olumsuz', kategori, metin: olay.text ?? '' }),
  })
}
