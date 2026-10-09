import type { AssistantResponse } from '../types'
import { AkisHatasi } from './olayEslemesi.ts'
import type { TedyOlayi } from './olayEslemesi.ts'

export class IstekHatasi extends Error {
  durum: number
  constructor(mesaj: string, durum: number) { super(mesaj); this.durum = durum }
}

const OTURUM = 'Oturumun sona ermiş; sayfayı yenileyip yeniden giriş yap.'
const GENEL = 'Asistan yanıtı alınamadı.'

/** Okura gösterilen cümle: oturum düşmesi ayrı söylenir; sunucunun kendi Türkçe cümlesi korunur;
 *  "HTTP 502", "Failed to fetch" gibi iç metinler okura ulaşmaz (D4). */
export function okurHatasi(e: unknown): string {
  if (e instanceof IstekHatasi) {
    if (e.durum === 401 || e.durum === 403) return OTURUM
    const m = e.message.trim()
    // Sunucunun Türkçe cümlesi korunur; "session_required" gibi tek kelime kodlar ve "HTTP 502" korunmaz.
    if (!/^HTTP \d+/.test(m) && /\s|[çğıöşüÇĞİÖŞÜ]/.test(m)) return m
  }
  return GENEL
}

export async function sseOku(res: Response, onOlay: (o: TedyOlayi) => void): Promise<void> {
  const okuyucu = res.body?.getReader()
  if (!okuyucu) throw new AkisHatasi('akış gövdesi yok')
  const cozucu = new TextDecoder()
  let tampon = ''
  for (;;) {
    const { done, value } = await okuyucu.read()
    if (done) break
    tampon += cozucu.decode(value, { stream: true })
    const cerceveler = tampon.split('\n\n')
    tampon = cerceveler.pop() ?? ''
    for (const c of cerceveler) {
      let ad = 'message'
      let veri = '{}'
      for (const s of c.split('\n')) {
        if (s.startsWith('event: ')) ad = s.slice(7).trim()
        else if (s.startsWith('data: ')) veri = s.slice(6)
      }
      // Yalnız bozuk JSON çerçevesi atlanır; işleyicinin kendi hatası yukarı çıkar (yutulursa okur cevapsız kalır).
      let cozulen: Record<string, unknown>
      try { cozulen = JSON.parse(veri) } catch { continue }
      onOlay({ ad, veri: cozulen })
    }
  }
}

async function jsonIstek(url: string, govde: unknown, signal: AbortSignal, f: typeof fetch): Promise<AssistantResponse> {
  const res = await f(url, { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(govde), signal })
  let veri: Record<string, unknown> = {}
  try { veri = await res.json() } catch { veri = {} }
  if (!res.ok || 'error' in veri) throw new IstekHatasi(String(veri.error ?? `HTTP ${res.status}`), res.status)
  return veri as unknown as AssistantResponse
}

const iptalMi = (e: unknown) => (e as { name?: string })?.name === 'AbortError'

export async function soruGonder(govde: Record<string, unknown>, onOlay: (o: TedyOlayi) => void,
  signal: AbortSignal, f: typeof fetch = fetch): Promise<void> {
  let cevaplandi = false
  try {
    const res = await f('/api/assistant/stream', { method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(govde), signal })
    if (!res.ok || !res.body) throw new IstekHatasi(`HTTP ${res.status}`, res.status)
    await sseOku(res, o => {
      if (o.ad === 'error') {
        // Cevaptan sonra gelen hata ikinci bir cevap doğurmaz; okur cevabını almıştır.
        if (cevaplandi) return
        throw new AkisHatasi(String(o.veri.error ?? 'akış hatası'))
      }
      onOlay(o)
      if (o.ad === 'answer') cevaplandi = true   // işleyici cevabı gerçekten aldıktan sonra
    })
    if (!cevaplandi) throw new AkisHatasi('akış yanıtsız kapandı')
  } catch (e) {
    if (cevaplandi) return
    if (iptalMi(e) || signal.aborted) throw e
    // Ara katman SSE'yi tamponluyor, eski işçi ya da akış yarıda koptu: okur cevabını yine alır.
    console.warn('akış başarısız, klasik uca düşülüyor:', e)
    onOlay({ ad: 'akis_dustu', veri: { yeniId: crypto.randomUUID() } })
    const payload = await jsonIstek('/api/assistant/chat', govde, signal, f)
    onOlay({ ad: 'answer', veri: { payload } })
  }
}

export function planGonder(govde: Record<string, unknown>, signal: AbortSignal, f: typeof fetch = fetch) {
  return jsonIstek('/api/assistant/plan', govde, signal, f)
}
