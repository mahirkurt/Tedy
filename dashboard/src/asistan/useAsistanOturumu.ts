import type { ChatInstance } from '@carbon/ai-chat'
import type { useSohbetler } from '../hooks/useSohbetler'
import { gecmisOgeleri } from './gecmis.ts'
import { asistanDeposu } from './asistanDeposu.ts'
import type { Yukleme } from '../components/YuklenenEk'

type Depo = ReturnType<typeof useSohbetler>

/** Sayfa ile başlatıcı aynı sohbeti açar: etkin sohbet sekme oturumunda, kişiye ayrı (localStorage değil). */
export function etkinSohbetAnahtari(email?: string): string | null {
  return email ? `tedy-asistan-etkin::${email.trim().toLocaleLowerCase('tr-TR')}` : null
}
export function etkinSohbetiOku(email?: string): { id: string; salt: boolean } | null {
  const k = etkinSohbetAnahtari(email)
  try { return k ? JSON.parse(sessionStorage.getItem(k) ?? 'null') : null } catch { return null }
}
export function etkinSohbetiYaz(email: string | undefined, d: { id: string; salt: boolean } | null) {
  const k = etkinSohbetAnahtari(email)
  if (!k) return
  try { if (d) sessionStorage.setItem(k, JSON.stringify(d)); else sessionStorage.removeItem(k) } catch { /* yalnız bellek */ }
}

export async function sohbetiAc(inst: ChatInstance, depo: Depo, ogretmenSec: (id: string) => void, id: string, salt: boolean) {
  const sonuc = await depo.ac(id, salt)
  if (!sonuc) return
  const saltMi = sonuc.read_only ?? salt
  etkinSohbetiYaz(asistanDeposu.al().email, { id, salt: saltMi })
  ogretmenSec(sonuc.sohbet.ogretmen)
  const ekGoruntuleri: Record<string, Yukleme[]> = {}
  for (const m of sonuc.mesajlar) if (m.rol === 'user' && m.yuklemeler?.length) ekGoruntuleri[m.id] = m.yuklemeler
  asistanDeposu.ayarla({ saltOkunur: saltMi, sohbetId: id, cipler: [], bekleyen: null, ekGoruntuleri,
    mesajVar: sonuc.mesajlar.length > 0,
    dokum: sonuc.mesajlar.map(m => ({ role: m.rol, content: m.icerik })) })
  await inst.messaging.clearConversation()
  await inst.messaging.insertHistory(gecmisOgeleri(sonuc.mesajlar, { geriBildirim: !saltMi, ogrenci: asistanDeposu.al().okur === 'ogrenci' }))
  inst.updateInputIsDisabled(saltMi)
}

export async function yeniSohbet(inst: ChatInstance, depo: Depo) {
  const d = asistanDeposu.al()
  const id = await depo.yeni(d.ogretmenId)
  etkinSohbetiYaz(d.email, { id, salt: false })
  asistanDeposu.ayarla({ saltOkunur: false, sohbetId: id, dokum: [], cipler: [], bekleyen: null, ekGoruntuleri: {}, mesajVar: false })
  await inst.messaging.clearConversation()
  inst.updateInputIsDisabled(false)
}
