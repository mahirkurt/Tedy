// Tarayıcının bildirim, push ve servis çalışanı API'lerini taklit eder. Sınav
// uyarıları kartı bunları okur; taklit olmadan kartın metni tarayıcının varsayılan
// izin durumuna bağlı kalır (headless Chromium "denied" okur) ve görsel
// taban çizgileri ortama göre değişirdi.
import type { Page } from '@playwright/test'

export type Taklit = { izin: 'default' | 'granted' | 'denied'; abone: boolean; destek?: boolean; ios?: boolean
  // requestPermission() yanıtı; varsayılan 'granted'. 'default' kapatılan izin penceresidir.
  istemYaniti?: 'default' | 'granted' | 'denied'
  // Var olan aboneliğin bağlı olduğu VAPID anahtarı (options.applicationServerKey); verilmezse
  // sunucu fikstürünün 'BAAA' anahtarı ([4, 0, 0]).
  abonelikAnahtari?: number[]
  // getRegistration() bu sıradaki çağrıdan (1'den sayılır) başlayarak reddeder: tarayıcının kendi
  // kaydını okuyamadığı durum.
  okumaReddi?: number }

// İzni kartın dışından değiştirir (tarayıcı ayarı, başka sekme). `olay` false ise yalnız değer değişir:
// tarayıcının change olayı göndermediği durum, sekmeye dönüşte okunur.
export async function izinDegistir(page: Page, izin: 'default' | 'granted' | 'denied', olay = true) {
  await page.evaluate(([izin, olay]) => {
    (window as unknown as { __izinDegistir: (i: string, o: boolean) => void }).__izinDegistir(izin as string, olay as boolean)
  }, [izin, olay] as const)
}

// Taklidin kaç kez getRegistration() okuduğu (window.__kayitOkuma): kart ve sessiz kayıt her okumada
// buradan geçer, yani "olay işlendi" kanıtı budur — "hiçbir şey olmadı" iddiası süreye değil buna dayanır.
export async function kayitOkumaSayisi(page: Page): Promise<number> {
  return page.evaluate(() => (window as unknown as { __kayitOkuma?: () => number }).__kayitOkuma?.() ?? 0)
}

// İki kare: kanıtlanmış bir okumadan sonra onun eşzamanlı tepkileri (render, yakalanmamış ret) yüzeye çıkar.
export async function karelerGecsin(page: Page) {
  await page.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))))
}

// Taklidin gördüğü abone olma/çıkma adımları, sırasıyla (window.__bildirimOlaylari).
export async function bildirimOlaylari(page: Page): Promise<string[]> {
  return page.evaluate(() => [...((window as unknown as { __bildirimOlaylari?: string[] }).__bildirimOlaylari ?? [])])
}

export async function bildirimTaklidi(page: Page, t: Taklit) {
  await page.addInitScript((t: Taklit) => {
    const w = window as unknown as Record<string, unknown>
    if (t.ios) Object.defineProperty(navigator, 'userAgent', { value: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X)' })
    if (t.destek === false) { delete w.PushManager; return }
    let abone = t.abone
    const olaylar: string[] = []
    w.__bildirimOlaylari = olaylar
    let anahtar = Uint8Array.from(t.abonelikAnahtari ?? [4, 0, 0]).buffer
    const abonelik = {
      endpoint: 'https://fcm.googleapis.com/fcm/send/test',
      get options() { return { applicationServerKey: anahtar, userVisibleOnly: true } },
      toJSON: () => ({ endpoint: 'https://fcm.googleapis.com/fcm/send/test', keys: { p256dh: 'p', auth: 'a' } }),
      unsubscribe: async () => { abone = false; olaylar.push('unsubscribe'); return true },
    }
    const pushManager = {
      getSubscription: async () => (abone ? abonelik : null),
      subscribe: async (s: { applicationServerKey: Uint8Array }) => {
        abone = true
        anahtar = Uint8Array.from(s.applicationServerKey).buffer
        olaylar.push(`subscribe ${[...s.applicationServerKey].join(',')}`)
        return abonelik
      },
    }
    const kayit = { pushManager }
    let okuma = 0
    w.__kayitOkuma = () => okuma
    Object.defineProperty(navigator, 'serviceWorker', { value: {
      getRegistration: async () => {
        okuma += 1
        if (t.okumaReddi && okuma >= t.okumaReddi) throw new DOMException('kayıt okunamadı', 'InvalidStateError')
        return kayit
      },
      register: async () => kayit, ready: Promise.resolve(kayit),
    } })
    w.PushManager = function PushManager() {}
    let izin = t.izin
    w.Notification = { get permission() { return izin }, requestPermission: async () => { izin = t.istemYaniti ?? 'granted'; return izin } }
    // navigator.permissions: bildirim izninin PermissionStatus'u; change olayı izinDegistir ile.
    const izinDurumu = new EventTarget() as EventTarget & { onchange: ((e: Event) => void) | null; state: string }
    izinDurumu.onchange = null
    Object.defineProperty(izinDurumu, 'state', { get: () => (izin === 'default' ? 'prompt' : izin) })
    Object.defineProperty(navigator, 'permissions', { value: {
      query: async (d: { name: string }) => (d.name === 'notifications' ? izinDurumu : { state: 'prompt', addEventListener() {}, removeEventListener() {} }),
    } })
    w.__izinDegistir = (yeni: 'default' | 'granted' | 'denied', olay: boolean) => {
      izin = yeni
      if (!olay) return
      const e = new Event('change')
      izinDurumu.dispatchEvent(e)
      izinDurumu.onchange?.(e)
    }
  }, t)
}
