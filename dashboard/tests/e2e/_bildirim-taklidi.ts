// Tarayıcının bildirim, push ve servis çalışanı API'lerini taklit eder. Sınav
// uyarıları kartı bunları okur; taklit olmadan kartın metni tarayıcının varsayılan
// izin durumuna bağlı kalır (headless Chromium "denied" okur) ve görsel
// taban çizgileri ortama göre değişirdi.
import type { Page } from '@playwright/test'

export type Taklit = { izin: 'default' | 'granted' | 'denied'; abone: boolean; destek?: boolean; ios?: boolean
  // requestPermission() yanıtı; varsayılan 'granted'. 'default' kapatılan izin penceresidir.
  istemYaniti?: 'default' | 'granted' | 'denied' }

export async function bildirimTaklidi(page: Page, t: Taklit) {
  await page.addInitScript((t: Taklit) => {
    const w = window as unknown as Record<string, unknown>
    if (t.ios) Object.defineProperty(navigator, 'userAgent', { value: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X)' })
    if (t.destek === false) { delete w.PushManager; return }
    let abone = t.abone
    const abonelik = {
      endpoint: 'https://fcm.googleapis.com/fcm/send/test',
      toJSON: () => ({ endpoint: 'https://fcm.googleapis.com/fcm/send/test', keys: { p256dh: 'p', auth: 'a' } }),
      unsubscribe: async () => { abone = false; return true },
    }
    const pushManager = {
      getSubscription: async () => (abone ? abonelik : null),
      subscribe: async () => { abone = true; return abonelik },
    }
    const kayit = { pushManager }
    Object.defineProperty(navigator, 'serviceWorker', { value: {
      getRegistration: async () => kayit, register: async () => kayit, ready: Promise.resolve(kayit),
    } })
    w.PushManager = function PushManager() {}
    let izin = t.izin
    w.Notification = { get permission() { return izin }, requestPermission: async () => { izin = t.istemYaniti ?? 'granted'; return izin } }
  }, t)
}
