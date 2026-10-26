// Kılavuz PDF'ini indirir (plan Görev 14).
import { indirmeAdi } from './hazirlik'

/** null: indirildi ya da `iptal` ile vazgeçildi (indirme olmaz); dize: okura söylenecek cümle (sunucunun `mesaj`'ı ya
 *  da genel cümle; ham HTTP metni okura gitmez, D4). Ad `Content-Disposition`'dan (`filename*` önce). */
export async function pdfIndir(adres: string, iptal?: AbortSignal): Promise<string | null> {
  let r: Response
  try {
    r = await fetch(adres, { credentials: 'include', signal: iptal })
  } catch {
    return iptal?.aborted ? null : 'Bağlantı kurulamadı; yeniden dene.'
  }
  if (!r.ok) {
    try {
      const j = await r.json() as { mesaj?: unknown }
      return typeof j.mesaj === 'string' && j.mesaj ? j.mesaj : 'PDF hazırlanamadı.'
    } catch {
      return 'PDF hazırlanamadı.'
    }
  }
  let blob: Blob
  try {
    blob = await r.blob()
  } catch {
    return iptal?.aborted ? null : 'Bağlantı kesildi; yeniden dene.'
  }
  if (iptal?.aborted) return null
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = indirmeAdi(r.headers.get('Content-Disposition'))
  document.body.append(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 60_000)
  return null
}
