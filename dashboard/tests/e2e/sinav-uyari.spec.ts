import { test, expect, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { mock, LIVE } from './_audit-fixtures'

// Sınav uyarıları kartı: tarayıcının bildirim API'leri taklit edilir; sunucu
// uçları route ile karşılanır. Gerçek push servisine gidilmez.

type Taklit = { izin: 'default' | 'granted' | 'denied'; abone: boolean; destek?: boolean; ios?: boolean }

async function bildirimTaklidi(page: Page, t: Taklit) {
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
    w.Notification = { get permission() { return izin }, requestPermission: async () => { izin = 'granted'; return izin } }
  }, t)
}

async function sinavlarAc(page: Page, t: Taklit) {
  await bildirimTaklidi(page, t)
  await mock(page, { ...LIVE, 'bildirim/anahtar': { anahtar: 'BAAA', acik: true } })
  await page.route('**/api/bildirim/abonelik', r => r.fulfill({ status: 201, json: { ok: true } }))
  await page.route('**/api/bildirim/deneme', r => r.fulfill({ json: { gonderilen: 1 } }))
  await page.goto('/sinavlar')
  await page.locator('#uyarilar').waitFor()
}

test.describe('Sınav uyarıları kartı', () => {
  test('kapalıdan açığa, deneme ve kapatma', async ({ page }) => {
    await sinavlarAc(page, { izin: 'default', abone: false })
    const kart = page.locator('#uyarilar')
    await expect(kart.getByText('Bu cihazda kapalı.', { exact: true })).toBeVisible()
    const kayit = page.waitForRequest(r => r.url().endsWith('/api/bildirim/abonelik') && r.method() === 'POST')
    await kart.getByRole('button', { name: 'Bu cihazda aç' }).click()
    const govde = (await kayit).postDataJSON()
    expect(govde.endpoint).toBe('https://fcm.googleapis.com/fcm/send/test')
    expect(govde.cihaz).toBeTruthy()
    await expect(kart.getByText(/^Bu cihazda açık\./)).toBeVisible()
    await kart.getByRole('button', { name: 'Deneme bildirimi gönder' }).click()
    await expect(kart.getByText('Deneme bildirimi 1 cihaza gönderildi.')).toBeVisible()
    await kart.getByRole('button', { name: 'Bu cihazda kapat' }).click()
    await expect(kart.getByText('Bu cihazda kapalı.', { exact: true })).toBeVisible()
  })

  test('izin reddedilmiş', async ({ page }) => {
    await sinavlarAc(page, { izin: 'denied', abone: false })
    await expect(page.locator('#uyarilar')).toContainText('Tarayıcı ayarlarından')
    await expect(page.locator('#uyarilar').getByRole('button')).toHaveCount(0)
  })

  test('desteklenmiyor', async ({ page }) => {
    await sinavlarAc(page, { izin: 'default', abone: false, destek: false })
    await expect(page.locator('#uyarilar')).toContainText('Bu tarayıcı bildirim desteklemiyor.')
  })

  test('iPhone ana ekrana eklenmemiş', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await sinavlarAc(page, { izin: 'default', abone: false, ios: true })
    await expect(page.locator('#uyarilar')).toContainText('Paylaş → Ana Ekrana Ekle')
  })

  test('axe: kart ihlalsiz', async ({ page }) => {
    await sinavlarAc(page, { izin: 'default', abone: false })
    const sonuc = await new AxeBuilder({ page }).include('#uyarilar')
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa', 'best-practice']).analyze()
    expect(sonuc.violations).toEqual([])
  })

  test('manifest ve servis çalışanı sunuluyor', async ({ request }) => {
    const manifest = await request.get('/manifest.webmanifest')
    expect(manifest.ok()).toBeTruthy()
    expect((await manifest.json()).icons).toHaveLength(2)
    const sw = await request.get('/sw.js')
    expect(sw.ok()).toBeTruthy()
    expect(await sw.text()).toContain("addEventListener('push'")
    expect((await request.get('/tedy-192.png')).ok()).toBeTruthy()
  })
})
