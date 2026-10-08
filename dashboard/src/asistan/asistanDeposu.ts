import { useSyncExternalStore } from 'react'
import type { AssistantCitation } from '../types'
import type { Yukleme } from '../components/YuklenenEk'

export interface Cip { yerel: string; ad: string; tur?: string; id?: string; hata?: string; yukleniyor?: boolean; baglaniyor?: boolean; baglandi?: boolean }
export interface SayfaIstegi { ad: string; oge?: { tur: string; id: string }; etiket: string; ogeEtiketi?: string }
export interface AsistanDurumu {
  okur: 'ogrenci' | 'aile'; email?: string; ogretmenId: string; saltOkunur: boolean; sohbetId?: string
  odevKey: string; cipler: Cip[]; sayfa: SayfaIstegi | null
  sonrakiIstek: { deep?: boolean; transient?: boolean; plan?: boolean }
  dokum: { role: 'user' | 'assistant'; content: string }[]
  bekleyen: { govde: Record<string, unknown>; plan: boolean } | null
  yukleniyor: boolean; ekGoruntuleri: Record<string, Yukleme[]>
  acikAtif: { atiflar: AssistantCitation[]; etkin: string | null } | null
  /** Son tamamlanan asistan yanıtının Carbon kimliği: netleştirme yalnız son cevapta etkin. */
  sonYanitId?: string
  /** AI açıklamasındaki "Son yanıtı … yazdı" için. */
  sonModel?: string
  /** Tek paylaşılan sesli okuyucu: bir cevabı okumak öncekini durdurur, düğme etiketleri birlikte değişir. */
  ses: { var: boolean; okunan: string | null; oku: (id: string, metin: string) => void } | null
  /** Ekranda mesaj var mı (başlangıç ekranını kapatmak için, tedyChatConfig). */
  mesajVar: boolean
}

const BASLANGIC: AsistanDurumu = { okur: 'aile', ogretmenId: 'genel', saltOkunur: false, odevKey: '', cipler: [], sayfa: null,
  sonrakiIstek: {}, dokum: [], bekleyen: null, yukleniyor: false, ekGoruntuleri: {}, acikAtif: null, ses: null, mesajVar: false }

let durum = BASLANGIC
const dinleyiciler = new Set<() => void>()

export const asistanDeposu = {
  al: () => durum,
  ayarla(p: Partial<AsistanDurumu>) { durum = { ...durum, ...p }; dinleyiciler.forEach(f => f()) },
  sifirla() { durum = BASLANGIC; dinleyiciler.forEach(f => f()) },
  abone(f: () => void) { dinleyiciler.add(f); return () => { dinleyiciler.delete(f) } },
}

export function useAsistanDurumu<T>(sec: (d: AsistanDurumu) => T): T {
  return useSyncExternalStore(asistanDeposu.abone, () => sec(asistanDeposu.al()))
}
