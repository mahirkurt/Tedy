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
// The server keeps no device for this account (a dead or replaced subscription was dropped):
// a test that reached nobody is not a success.
export const CIHAZ_YOK_METNI =
  'Deneme bildirimi hiçbir cihaza ulaşmadı: bu cihazın kaydı sunucuda yok. Bildirimleri kapatıp yeniden açın.'

export function denemeBilgisi(gonderilen: number): { tur: 'success' | 'error'; metin: string } {
  return gonderilen > 0
    ? { tur: 'success', metin: `Deneme bildirimi ${gonderilen} cihaza gönderildi.` }
    : { tur: 'error', metin: CIHAZ_YOK_METNI }
}

// İzin penceresi kapatılırsa (requestPermission → 'default') sunucu hatası değil,
// yalnızca "izin verilmedi" söylenir.
export function hataMetni(kod: string): string {
  if (kod === 'reddedildi') return DURUM_METNI.reddedildi
  if (kod === 'kapali') return IZIN_VERILMEDI_METNI
  if (kod === 'cihaz-yok') return CIHAZ_YOK_METNI
  return GENEL_HATA_METNI
}

// ArrayBuffer-destekli dönüş tipi: pushManager.subscribe SharedArrayBuffer kabul etmez.
export function anahtarBaytlari(b64url: string): Uint8Array<ArrayBuffer> {
  const b64 = (b64url + '='.repeat((4 - (b64url.length % 4)) % 4)).replace(/-/g, '+').replace(/_/g, '/')
  const ham = atob(b64)
  return Uint8Array.from(ham, c => c.charCodeAt(0))
}

// Is the browser's subscription bound to the server's current VAPID key? A browser that does
// not expose the key (null) counts as the same: resubscribing on every opening would churn.
export function anahtarAyni(abonelikAnahtari: ArrayBuffer | null, sunucuAnahtari: Uint8Array): boolean {
  if (!abonelikAnahtari) return true
  const a = new Uint8Array(abonelikAnahtari)
  return a.length === sunucuAnahtari.length && a.every((b, i) => b === sunucuAnahtari[i])
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

async function aboneligiKaydet(abonelik: PushSubscription): Promise<Response> {
  return fetch('/api/bildirim/abonelik', {
    method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...abonelik.toJSON(), cihaz: cihazAdi(navigator.userAgent) }),
  })
}

export type TazelemeSonucu = 'yok' | 'bildirildi' | 'yenilendi' | 'hata'

// On opening the dashboard (once, full role): the server may have dropped this device without
// the browser knowing — a 403/404/410 from the push service, a VAPID key change, an unreadable
// store. If the browser still holds a subscription with permission granted, it is resubscribed
// when bound to another key, then posted again silently (the server replaces the same endpoint;
// a first device is seeded). Nothing is shown; a failure is retried at the next opening.
export async function aboneligiTazele(): Promise<TazelemeSonucu> {
  try {
    if (!destekVar() || Notification.permission !== 'granted') return 'yok'
    const kayit = await navigator.serviceWorker.getRegistration('/')
    let abonelik = kayit ? await kayit.pushManager.getSubscription() : null
    if (!kayit || !abonelik) return 'yok'
    const yanit = await fetch('/api/bildirim/anahtar', { credentials: 'include' })
    const { anahtar } = (yanit.ok ? await yanit.json() : {}) as { anahtar?: string | null }
    if (!anahtar) return 'hata'
    const baytlar = anahtarBaytlari(anahtar)
    let sonuc: TazelemeSonucu = 'bildirildi'
    const mevcutAnahtar = (abonelik.options?.applicationServerKey ?? null) as ArrayBuffer | null
    if (!anahtarAyni(mevcutAnahtar, baytlar)) {
      await abonelik.unsubscribe()
      abonelik = await kayit.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: baytlar })
      sonuc = 'yenilendi'
    }
    return (await aboneligiKaydet(abonelik)).ok ? sonuc : 'hata'
  } catch {
    return 'hata'
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
  const kayitYaniti = await aboneligiKaydet(abonelik)
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
  if (yanit.status === 404) throw new BildirimHatasi('cihaz-yok', 'Bu hesapta kayıtlı cihaz yok')
  if (!yanit.ok) throw new BildirimHatasi('sunucu', 'Deneme bildirimi gönderilemedi')
  return ((await yanit.json()) as { gonderilen: number }).gonderilen
}
