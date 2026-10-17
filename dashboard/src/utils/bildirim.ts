// Sınav uyarıları: bu cihazda web push aç/kapat (spec 2026-10-16 §7, §8).
// Saf kısım (durum, metin, anahtar çözme, cihaz adı) node:test ile; tarayıcı
// akışları e2e ile sınanır. Servis çalışanı yalnız bildirim içindir.

export type BildirimDurumu = 'acik' | 'acik-bekliyor' | 'kapali' | 'reddedildi' | 'desteklenmiyor' | 'ios-ana-ekran'

export interface BildirimOrtami {
  destek: boolean
  izin: 'default' | 'granted' | 'denied'
  abone: boolean
  ios: boolean
  ekranda: boolean
  // Sunucunun uyarı bayrağı (/api/bildirim/anahtar `acik`); bilinmiyorsa undefined.
  sunucuAcik?: boolean
}

export class BildirimHatasi extends Error {
  kod: string
  constructor(kod: string, mesaj: string) {
    super(mesaj)
    this.kod = kod
  }
}

export const DURUM_METNI: Record<BildirimDurumu, string> = {
  acik: 'Bu cihazda açık. Sınav duyurulunca ve yaklaşınca bildirim gelir.',
  'acik-bekliyor': 'Bu cihazda açık; sınav uyarıları henüz başlatılmadı.',
  kapali: 'Bu cihazda kapalı.',
  reddedildi: 'Bildirim izni reddedilmiş. Tarayıcı ayarlarından bu siteye bildirim izni verilmeli.',
  desteklenmiyor: 'Bu tarayıcı bildirim desteklemiyor.',
  'ios-ana-ekran': "iPhone'da bildirim için TEDY ana ekrana eklenmeli: Paylaş → Ana Ekrana Ekle, sonra oradan açılır.",
}

export function bildirimDurumu(o: BildirimOrtami): BildirimDurumu {
  if (o.ios && !o.ekranda) return 'ios-ana-ekran'
  if (!o.destek) return 'desteklenmiyor'
  if (o.izin === 'denied') return 'reddedildi'
  if (o.izin === 'granted' && o.abone) return o.sunucuAcik === false ? 'acik-bekliyor' : 'acik'
  return 'kapali'
}

export const IZIN_VERILMEDI_METNI = 'İzin verilmedi; bildirimler kapalı kaldı.'
export const GENEL_HATA_METNI = 'İşlem tamamlanamadı; biraz sonra yeniden denenebilir.'

// İzin penceresi kapatılırsa (requestPermission → 'default') sunucu hatası değil,
// yalnızca "izin verilmedi" söylenir.
export function hataMetni(kod: string): string {
  if (kod === 'reddedildi') return DURUM_METNI.reddedildi
  if (kod === 'kapali') return IZIN_VERILMEDI_METNI
  return GENEL_HATA_METNI
}

// ArrayBuffer-destekli dönüş tipi: pushManager.subscribe SharedArrayBuffer kabul etmez.
export function anahtarBaytlari(b64url: string): Uint8Array<ArrayBuffer> {
  const b64 = (b64url + '='.repeat((4 - (b64url.length % 4)) % 4)).replace(/-/g, '+').replace(/_/g, '/')
  const ham = atob(b64)
  return Uint8Array.from(ham, c => c.charCodeAt(0))
}

export function cihazAdi(ua: string): string {
  if (/iPhone|iPad|iPod/.test(ua)) return 'iPhone'
  if (/Android/.test(ua)) return 'Android'
  if (/Macintosh/.test(ua)) return 'Mac'
  if (/Windows/.test(ua)) return 'Windows'
  return 'Tarayıcı'
}

function iosMu(): boolean {
  return /iPhone|iPad|iPod/.test(navigator.userAgent)
    || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
}

function ekrandaMi(): boolean {
  return window.matchMedia?.('(display-mode: standalone)').matches
    || (navigator as Navigator & { standalone?: boolean }).standalone === true
}

function destekVar(): boolean {
  return 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window
}

async function mevcutAbonelik(): Promise<PushSubscription | null> {
  if (!destekVar()) return null
  const kayit = await navigator.serviceWorker.getRegistration('/')
  return kayit ? kayit.pushManager.getSubscription() : null
}

async function sunucuBayragi(): Promise<boolean | undefined> {
  try {
    const yanit = await fetch('/api/bildirim/anahtar', { credentials: 'include' })
    if (!yanit.ok) return undefined
    const { acik } = (await yanit.json()) as { acik?: boolean }
    return typeof acik === 'boolean' ? acik : undefined
  } catch {
    return undefined
  }
}

export async function ortamiOku(): Promise<BildirimOrtami> {
  const destek = destekVar()
  const abone = destek ? (await mevcutAbonelik()) !== null : false
  return {
    destek,
    izin: destek ? Notification.permission : 'default',
    abone,
    ios: iosMu(),
    ekranda: ekrandaMi(),
    // Bayrak yalnız abone cihazda anlamlı; okunamazsa "açık" varsayılır.
    sunucuAcik: abone ? await sunucuBayragi() : undefined,
  }
}

export async function bildirimiAc(): Promise<void> {
  const izin = await Notification.requestPermission()
  if (izin !== 'granted') throw new BildirimHatasi(izin === 'denied' ? 'reddedildi' : 'kapali', 'İzin verilmedi')
  const kayit = await navigator.serviceWorker.register('/sw.js')
  await navigator.serviceWorker.ready
  const yanit = await fetch('/api/bildirim/anahtar', { credentials: 'include' })
  const { anahtar } = (await yanit.json()) as { anahtar: string | null }
  if (!yanit.ok || !anahtar) throw new BildirimHatasi('sunucu', 'Bildirim anahtarı alınamadı')
  const abonelik = await kayit.pushManager.subscribe({
    userVisibleOnly: true, applicationServerKey: anahtarBaytlari(anahtar),
  })
  const kayitYaniti = await fetch('/api/bildirim/abonelik', {
    method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...abonelik.toJSON(), cihaz: cihazAdi(navigator.userAgent) }),
  })
  if (!kayitYaniti.ok) {
    await abonelik.unsubscribe()
    throw new BildirimHatasi('sunucu', 'Abonelik kaydedilemedi')
  }
}

export async function bildirimiKapat(): Promise<void> {
  const abonelik = await mevcutAbonelik()
  if (!abonelik) return
  await fetch('/api/bildirim/abonelik', {
    method: 'DELETE', credentials: 'include', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ endpoint: abonelik.endpoint }),
  })
  await abonelik.unsubscribe()
}

export async function denemeGonder(): Promise<number> {
  const yanit = await fetch('/api/bildirim/deneme', { method: 'POST', credentials: 'include' })
  if (!yanit.ok) throw new BildirimHatasi('sunucu', 'Deneme bildirimi gönderilemedi')
  return ((await yanit.json()) as { gonderilen: number }).gonderilen
}
