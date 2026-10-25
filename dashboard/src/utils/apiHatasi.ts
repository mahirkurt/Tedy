/**
 * B43 (D3, D4): a failed request has a kind, and the reader is told the kind in a sentence — never the raw
 * fetch text ("HTTP 500", "Non-JSON response (HTTP 502)", a browser's "Failed to fetch").
 */
export type ApiHataTuru = 'baglanti' | 'oturum' | 'yetki' | 'bulunamadi' | 'sunucu' | 'bicim'

/** The kind of a failed request: no answer, an HTTP status, or an answer that is not the JSON promised. */
export function apiHataTuru(durum: number | null, jsonDegil = false): ApiHataTuru {
  if (durum === null) return 'baglanti'
  if (jsonDegil) return 'bicim'
  if (durum === 401) return 'oturum'
  if (durum === 403) return 'yetki'
  if (durum === 404) return 'bulunamadi'
  return 'sunucu'
}

/** "Modüller yüklenemedi." + what to do, by kind. `ne` is the surface's own noun ("Modüller"). */
export function apiHataCumlesi(tur: ApiHataTuru, ne: string): { baslik: string; ayrinti: string } {
  const baslik = `${ne} yüklenemedi.`
  switch (tur) {
    case 'baglanti': return { baslik, ayrinti: 'Bağlantını kontrol edip sayfayı yenile.' }
    case 'oturum': return { baslik, ayrinti: 'Oturumun kapanmış; yeniden giriş yap.' }
    case 'yetki': return { baslik, ayrinti: 'Bu hesabın bu sayfaya erişimi yok.' }
    case 'bulunamadi': return { baslik, ayrinti: 'Aranan kayıt bulunamadı; kaldırılmış olabilir.' }
    case 'bicim':
    case 'sunucu': return { baslik, ayrinti: 'Sayfayı birkaç dakika sonra yeniden aç.' }
  }
}

const MESAJ_SINIRI = 200

/** D15: a failed answer may carry the server's own sentence (`{error, mesaj}`, e.g. 409 "Yeni yılın tabloları
 *  bekleniyor."). Only that sentence reaches the page; a gateway's HTML, a missing field or an overlong text is null. */
export function sunucuMesaji(govde: string): string | null {
  try {
    const v: unknown = JSON.parse(govde)
    const m = v && typeof v === 'object' ? (v as Record<string, unknown>).mesaj : null
    return typeof m === 'string' && m.trim() !== '' && m.length <= MESAJ_SINIRI ? m : null
  } catch {
    return null
  }
}
