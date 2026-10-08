import { useSyncExternalStore } from 'react'
import type { UserRole } from '../hooks/useAuth'

/** Yol → sayfa adı; adlar arka uçtaki SAYFA_ADLARI ile aynıdır (dashboard_api.py). */
export const SAYFA_YOLLARI: Record<string, string> = {
  '/': 'bugun', '/isler': 'isler', '/dersler': 'dersler', '/notlar': 'notlar', '/takvim': 'takvim',
  '/takimlar': 'takimlar', '/ilerleme': 'ilerleme', '/duyurular': 'duyurular', '/profil': 'profil',
  '/moduller': 'moduller', '/kitaplar': 'kitaplar', '/sinavlar': 'sinavlar',
}
export const SAYFA_ETIKETLERI: Record<string, string> = {
  bugun: 'Bugün', isler: 'İşler', dersler: 'Dersler', notlar: 'Notlar', takvim: 'Takvim', takimlar: 'Takımlar',
  ilerleme: 'İlerleme', duyurular: 'Duyurular', profil: 'Profil', moduller: 'Modüller', kitaplar: 'Tedy Books', sinavlar: 'Sınavlar',
}
/** Adresten ya da yoldan gelen ad bilinen bir sayfaysa etiketi; değilse null (Object.hasOwn: "toString" sayfa değil). */
export function sayfaEtiketi(ad: string | null): string | null {
  return ad && Object.hasOwn(SAYFA_ETIKETLERI, ad) ? SAYFA_ETIKETLERI[ad] : null
}

// Asistanın kendisi, modül görüntüleyici ve kitap okuyucu tam ekran yüzeylerdir: başlatıcı orada durmaz.
const GIZLI = [/^\/asistan(\/|$)/, /^\/moduller\/taslak\//, /^\/moduller\/[^/]+\/[^/]+$/, /^\/kitaplar\/[^/]+\/[^/]+$/]

export function sayfaAdi(yol: string): string | null {
  if (Object.hasOwn(SAYFA_YOLLARI, yol)) return SAYFA_YOLLARI[yol]
  const kok = `/${yol.split('/')[1] ?? ''}`
  return kok !== '/' && Object.hasOwn(SAYFA_YOLLARI, kok) ? SAYFA_YOLLARI[kok] : null
}

export function baslaticiGorunur(yol: string, rol: UserRole, odak: boolean, genis: boolean): boolean {
  return rol === 'full' && !odak && genis && !GIZLI.some(r => r.test(yol)) && sayfaAdi(yol) !== null
}

export interface AcikOge { tur: 'odev' | 'sinav' | 'etkinlik' | 'ders_haftasi'; id: string; etiket: string }
let acik: AcikOge | null = null
const dinleyenler = new Set<() => void>()
/** Sayfalar açık öğeyi buraya bildirir (ödev penceresi, seçili sınav/etkinlik, ders içeriği haftası). */
export function acikOgeyiBildir(oge: AcikOge | null): void { acik = oge; dinleyenler.forEach(f => f()) }
export function useAcikOge(): AcikOge | null {
  return useSyncExternalStore(f => { dinleyenler.add(f); return () => { dinleyenler.delete(f) } }, () => acik)
}
