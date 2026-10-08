import { asistanDeposu } from './asistanDeposu.ts'
import type { Cip } from './asistanDeposu.ts'

const guncelle = (yerel: string, p: Partial<Cip>) =>
  asistanDeposu.ayarla({ cipler: asistanDeposu.al().cipler.map(c => (c.yerel === yerel ? { ...c, ...p } : c)) })

async function yukleBir(yerel: string, file: File) {
  const body = new FormData()
  body.append('dosya', file)
  try {
    const res = await fetch('/api/assistant/uploads', { method: 'POST', credentials: 'include', body })
    let p: { error?: unknown; id?: unknown; ad?: unknown; tur?: unknown } = {}
    try { p = await res.json() } catch { p = {} }
    if (!res.ok || typeof p.id !== 'string') {
      guncelle(yerel, { yukleniyor: false, hata: typeof p.error === 'string' ? p.error : 'Dosya yüklenemedi.' }); return
    }
    guncelle(yerel, { yukleniyor: false, id: p.id, ad: typeof p.ad === 'string' ? p.ad : undefined, tur: typeof p.tur === 'string' ? p.tur : undefined })
  } catch { guncelle(yerel, { yukleniyor: false, hata: 'Dosya yüklenemedi.' }) }
}

export function dosyalariEkle(files: File[]) {
  const d = asistanDeposu.al()
  if (!files.length || d.saltOkunur || d.yukleniyor) return
  let yer = 4 - d.cipler.filter(c => c.yukleniyor || c.id).length
  const yeni: Cip[] = []
  const yuklenecek: [string, File][] = []
  for (const file of files) {
    const yerel = crypto.randomUUID()
    if (yer > 0) { yer -= 1; yeni.push({ yerel, ad: file.name, yukleniyor: true }); yuklenecek.push([yerel, file]) }
    else yeni.push({ yerel, ad: file.name, hata: 'Bir mesaja en fazla 4 dosya eklenebilir.' })
  }
  asistanDeposu.ayarla({ cipler: [...d.cipler, ...yeni] })
  for (const [yerel, file] of yuklenecek) void yukleBir(yerel, file)
}

export const cipKaldir = (yerel: string) =>
  asistanDeposu.ayarla({ cipler: asistanDeposu.al().cipler.filter(c => c.yerel !== yerel) })

export async function odeveBagla(yerel: string) {
  const d = asistanDeposu.al()
  const cip = d.cipler.find(c => c.yerel === yerel)
  if (!cip?.id || !d.odevKey || cip.baglaniyor || cip.baglandi) return
  guncelle(yerel, { baglaniyor: true, hata: undefined })
  try {
    const res = await fetch(`/api/assistant/uploads/${cip.id}/odeve-bagla`, { method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ anahtar: d.odevKey }) })
    const p = await res.json()
    if (!res.ok) throw new Error(p.error || 'Belge ödeve bağlanamadı.')
    guncelle(yerel, { baglaniyor: false, baglandi: true })
    window.dispatchEvent(new CustomEvent('tedy:homework-updated'))
  } catch (e) { guncelle(yerel, { baglaniyor: false, hata: e instanceof Error ? e.message : 'Belge ödeve bağlanamadı.' }) }
}
