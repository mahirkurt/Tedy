// Sınav uyarıları: bu cihazda web push aç/kapat (spec 2026-10-16 §7, §8).
// Saf kısım (durum, metin, anahtar çözme, cihaz adı) node:test ile; tarayıcı
// akışları e2e ile sınanır. Servis çalışanı yalnız bildirim içindir.

export type BildirimDurumu =
  'acik' | 'acik-bekliyor' | 'baska-sahip' | 'kapali' | 'reddedildi' | 'desteklenmiyor' | 'ios-ana-ekran'

export interface BildirimOrtami {
  destek: boolean
  izin: 'default' | 'granted' | 'denied'
  abone: boolean
  ios: boolean
  ekranda: boolean
  // Sunucunun uyarı bayrağı (/api/bildirim/anahtar `acik`); bilinmiyorsa undefined.
  sunucuAcik?: boolean
  // Açılıştaki sessiz yeniden kayıt 409 `sahip_baska` aldıysa: bu cihaz başka bir aile üyesine kayıtlı.
  baskaSahip?: boolean
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
  'baska-sahip': 'Bu cihaz başka bir aile üyesine kayıtlı; sınav uyarıları ona gelir.',
  kapali: 'Bu cihazda kapalı.',
  reddedildi: 'Bildirim izni reddedilmiş. Tarayıcı ayarlarından bu siteye bildirim izni verilmeli.',
  desteklenmiyor: 'Bu tarayıcı bildirim desteklemiyor.',
  'ios-ana-ekran': "iPhone'da bildirim için TEDY ana ekrana eklenmeli: Paylaş → Ana Ekrana Ekle, sonra oradan açılır.",
}

export function bildirimDurumu(o: BildirimOrtami): BildirimDurumu {
  if (o.ios && !o.ekranda) return 'ios-ana-ekran'
  if (!o.destek) return 'desteklenmiyor'
  if (o.izin === 'denied') return 'reddedildi'
  if (o.izin === 'granted' && o.abone) {
    if (o.baskaSahip) return 'baska-sahip'
    return o.sunucuAcik === false ? 'acik-bekliyor' : 'acik'
  }
  return 'kapali'
}

export const IZIN_VERILMEDI_METNI = 'İzin verilmedi; bildirimler kapalı kaldı.'
export const GENEL_HATA_METNI = 'İşlem tamamlanamadı; biraz sonra yeniden denenebilir.'
// The server keeps no device for this account (a dead or replaced subscription was dropped):
// a test that reached nobody is not a success.
export const CIHAZ_YOK_METNI =
  'Deneme bildirimi hiçbir cihaza ulaşmadı: bu cihazın kaydı sunucuda yok. Bildirimleri kapatıp yeniden açın.'

// Devices exist but every push service failed this time (5xx, timeout): not the device's fault.
export const PUSH_ULASILAMADI_METNI =
  'Deneme bildirimi gönderilemedi: push servisine ulaşılamadı. Biraz sonra yeniden deneyin.'
// DELETE failed (network or 5xx): the browser's subscription is released anyway, but the server may
// still hold the endpoint until its next send finds it dead.
export const SUNUCU_SILINEMEDI_METNI =
  'Sunucudaki kayıt silinemedi; bildirimler bu cihaza gelmeye devam edebilir.'
export const BANA_GECTI_METNI = 'Bu cihaz artık sizin hesabınıza kayıtlı.'

/** `POST /api/bildirim/deneme` yanıtı: `cihaz` toplam, `basarisiz` geçici hata, `olu` silinen kayıt. */
export interface DenemeYaniti { gonderilen: number; basarisiz: number; olu: number; cihaz: number }

export type Bilgi = { tur: 'success' | 'error' | 'warning'; metin: string }

export function denemeBilgisi(y: DenemeYaniti): Bilgi {
  if (y.gonderilen > 0) return { tur: 'success', metin: `Deneme bildirimi ${y.gonderilen} cihaza gönderildi.` }
  if (y.basarisiz > 0) return { tur: 'error', metin: PUSH_ULASILAMADI_METNI }
  return { tur: 'error', metin: CIHAZ_YOK_METNI }
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

// Hata sayfası (vekil ya da Flask HTML'i) JSON değildir: önce `ok`, sonra gövde; çözülemeyen gövde sunucu hatasıdır.
async function jsonOku<T>(yanit: Response, hata: string): Promise<T> {
  if (!yanit.ok) throw new BildirimHatasi('sunucu', hata)
  try {
    return (await yanit.json()) as T
  } catch {
    throw new BildirimHatasi('sunucu', hata)
  }
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

export type TazelemeSonucu = 'yok' | 'bildirildi' | 'yenilendi' | 'baska-sahip' | 'hata'

// The last silent re-registration of this page load (App.tsx starts it once). The card awaits it:
// "this device belongs to another member" is known only from its 409.
let sonTazeleme: Promise<TazelemeSonucu> | null = null

export async function ortamiOku(): Promise<BildirimOrtami> {
  const destek = destekVar()
  const abone = destek ? (await mevcutAbonelik()) !== null : false
  const izin = destek ? Notification.permission : 'default'
  return {
    destek,
    izin,
    abone,
    ios: iosMu(),
    ekranda: ekrandaMi(),
    // Bayrak yalnız abone cihazda anlamlı; okunamazsa "açık" varsayılır.
    sunucuAcik: abone ? await sunucuBayragi() : undefined,
    baskaSahip: abone && izin === 'granted' && sonTazeleme ? (await sonTazeleme) === 'baska-sahip' : false,
  }
}

// `yenile: true` is the silent re-registration: the server keeps a device another full-role member
// holds and answers 409 `sahip_baska` instead of moving it. "Bu cihazda aç"/"bana geçir" send none.
async function aboneligiKaydet(abonelik: PushSubscription, yenile = false): Promise<Response> {
  return fetch('/api/bildirim/abonelik', {
    method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...abonelik.toJSON(), cihaz: cihazAdi(navigator.userAgent), ...(yenile ? { yenile: true } : {}) }),
  })
}

async function sahipBaskaMi(yanit: Response): Promise<boolean> {
  if (yanit.status !== 409) return false
  try {
    return ((await yanit.json()) as { sahip_baska?: unknown }).sahip_baska === true
  } catch {
    return false
  }
}

// On opening the dashboard (once, full role): the server may have dropped this device without
// the browser knowing — a 403/404/410 from the push service, a VAPID key change, an unreadable
// store. If the browser still holds a subscription with permission granted, it is resubscribed
// when bound to another key, then posted again silently (the server replaces the same endpoint;
// a first device is seeded). Nothing is shown; a failure is retried at the next opening.
// The card listens for this: the silent re-registration may finish after the card has read its state.
export const BILDIRIM_DEGISTI = 'tedy:bildirim-degisti'

// A 409 `sahip_baska` changes nothing on this device: the card says whose it is and offers "bana geçir".
export function aboneligiTazele(): Promise<TazelemeSonucu> {
  sonTazeleme = tazele().then(sonuc => {
    if (typeof window !== 'undefined') window.dispatchEvent?.(new Event(BILDIRIM_DEGISTI))
    return sonuc
  })
  return sonTazeleme
}

async function tazele(): Promise<TazelemeSonucu> {
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
    const kayitYaniti = await aboneligiKaydet(abonelik, true)
    if (kayitYaniti.ok) return sonuc
    return (await sahipBaskaMi(kayitYaniti)) ? 'baska-sahip' : 'hata'
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
  const { anahtar } = await jsonOku<{ anahtar?: string | null }>(yanit, 'Bildirim anahtarı alınamadı')
  if (!anahtar) throw new BildirimHatasi('sunucu', 'Bildirim anahtarı alınamadı')
  const abonelik = await kayit.pushManager.subscribe({
    userVisibleOnly: true, applicationServerKey: anahtarBaytlari(anahtar),
  })
  const kayitYaniti = await aboneligiKaydet(abonelik)
  if (!kayitYaniti.ok) {
    await abonelik.unsubscribe()
    throw new BildirimHatasi('sunucu', 'Abonelik kaydedilemedi')
  }
}

/** "Bu cihazda bana geçir": the silent path was refused (another member holds this device); the
 *  person asks for it, so the subscription is posted without `yenile` and the server moves it. */
export async function bildirimiBanaGecir(): Promise<void> {
  const abonelik = await mevcutAbonelik()
  if (!abonelik) throw new BildirimHatasi('sunucu', 'Bu cihazda abonelik yok')
  const yanit = await aboneligiKaydet(abonelik)
  if (!yanit.ok) throw new BildirimHatasi('sunucu', 'Abonelik kaydedilemedi')
  sonTazeleme = Promise.resolve('bildirildi')
}

export type KapatmaSonucu = 'tamam' | 'sunucu-silinemedi'

// The browser's subscription is released whatever the server says. A 404 is "already gone" — fine;
// a network failure or a 5xx leaves the record on the server, and the card says so.
export async function bildirimiKapat(): Promise<KapatmaSonucu> {
  const abonelik = await mevcutAbonelik()
  if (!abonelik) return 'tamam'
  let sonuc: KapatmaSonucu = 'tamam'
  try {
    const yanit = await fetch('/api/bildirim/abonelik', {
      method: 'DELETE', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ endpoint: abonelik.endpoint }),
    })
    if (!yanit.ok && yanit.status !== 404) sonuc = 'sunucu-silinemedi'
  } catch {
    sonuc = 'sunucu-silinemedi'
  }
  await abonelik.unsubscribe()
  return sonuc
}

export async function denemeGonder(): Promise<DenemeYaniti> {
  const yanit = await fetch('/api/bildirim/deneme', { method: 'POST', credentials: 'include' })
  if (yanit.status === 404) throw new BildirimHatasi('cihaz-yok', 'Bu hesapta kayıtlı cihaz yok')
  const y = await jsonOku<Partial<DenemeYaniti>>(yanit, 'Deneme bildirimi gönderilemedi')
  const sayi = (n: unknown) => (typeof n === 'number' && Number.isFinite(n) ? n : 0)
  return { gonderilen: sayi(y.gonderilen), basarisiz: sayi(y.basarisiz), olu: sayi(y.olu), cihaz: sayi(y.cihaz) }
}
