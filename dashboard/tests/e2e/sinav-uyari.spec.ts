import { test, expect, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { mock, LIVE } from './_audit-fixtures'
import { bildirimTaklidi, type Taklit } from './_bildirim-taklidi'

// Sınav uyarıları kartı: tarayıcının bildirim API'leri taklit edilir; sunucu
// uçları route ile karşılanır. Gerçek push servisine gidilmez.

async function sinavlarAc(page: Page, t: Taklit, sunucuAcik = true) {
  await bildirimTaklidi(page, t)
  await mock(page, { ...LIVE, 'bildirim/anahtar': { anahtar: 'BAAA', acik: sunucuAcik } })
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
    // Tıklanan düğme kalktı; odak gövdeye düşmemeli, durum satırına geçmeli.
    await expect(page.locator('.sinav-uyarilari__durum')).toBeFocused()
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

  test('abone ama sunucu uyarıları başlatmamış', async ({ page }) => {
    await sinavlarAc(page, { izin: 'granted', abone: true }, false)
    const kart = page.locator('#uyarilar')
    await expect(kart).toContainText('Bu cihazda açık; sınav uyarıları henüz başlatılmadı.')
    await expect(kart.getByRole('button', { name: 'Deneme bildirimi gönder' })).toHaveCount(0)
    await expect(kart.getByRole('button', { name: 'Bu cihazda kapat' })).toBeVisible()
  })

  test('kapatılan izin penceresi: genel hata değil, "izin verilmedi"', async ({ page }) => {
    await sinavlarAc(page, { izin: 'default', abone: false, istemYaniti: 'default' })
    const kart = page.locator('#uyarilar')
    await kart.getByRole('button', { name: 'Bu cihazda aç' }).click()
    await expect(kart.getByText('İzin verilmedi; bildirimler kapalı kaldı.')).toBeVisible()
    await expect(kart.getByText('Bu cihazda kapalı.', { exact: true })).toBeVisible()
    await expect(kart).not.toContainText('İşlem tamamlanamadı')
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
