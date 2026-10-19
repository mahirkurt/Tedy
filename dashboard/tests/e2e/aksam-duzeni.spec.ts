import { test, expect, type Page } from '@playwright/test'
import { bugunAc } from './_bugun-fixtures'
import { AKSAM_VARSAYILAN } from './_audit-fixtures'

// B29 (anayasa §2: "the window is a parameter, not a constant; it is kept
// configurable in output/"), widened 2026-10-19 into the household's evening:
// Bugün reads it from /api/aksam-duzeni and Profil sets it. The family's own
// evening is the default: ready for homework 17:00, hard work until 19:00,
// bed at 21:00.

const json = (b: unknown) => ({ status: 200, contentType: 'application/json', body: JSON.stringify(b) })

const AYARLI = {
  ...AKSAM_VARSAYILAN, odeve_hazir: '16:00', zor_is_sonu: '17:30', hafif_is_sonu: '18:00',
  yemek: '18:30', hazirlik: '20:00', yatma: '21:45', varsayilan: false,
}

test.describe('Bugün', () => {
  test('sunucunun düzeniyle konuşur: 16:10 ödeve hazırdan sonra "Şimdi"', async ({ page }) => {
    await bugunAc(page, '2026-09-24T16:10', { 'aksam-duzeni': AYARLI })
    await expect(page.locator('.next-thing .next-thing__eyebrow')).toHaveText('Şimdi')
    const serit = page.locator('.day-strip')
    await expect(serit).toContainText('Ödev zamanı 16:00–17:30')
    await expect(serit).toContainText('Yatma 21:45')
  })

  test('ayar yoksa varsayılan akşam: 16:10 hâlâ "Okuldan sonra", ödev 17:00–19:00', async ({ page }) => {
    await bugunAc(page, '2026-09-24T16:10')
    await expect(page.locator('.next-thing .next-thing__eyebrow')).toHaveText('Okuldan sonra')
    const serit = page.locator('.day-strip')
    await expect(serit).toContainText('Ödev zamanı 17:00–19:00')
    await expect(serit).toContainText('Yatma 21:00')
    // The way home is a named part between the last bell and homework.
    await expect(serit.locator('.day-strip__part')).toHaveCount(3)
    await expect(serit.locator('.day-strip__part--yol')).toContainText('Yol')
  })

  test('zor işler bitti: "Bu akşam", yalnız akşam çizilir', async ({ page }) => {
    await bugunAc(page, '2026-09-24T19:10')
    await expect(page.locator('.next-thing .next-thing__eyebrow')).toHaveText('Bu akşam')
    await expect(page.locator('.day-strip__homework')).toHaveCount(0)
    await expect(page.locator('.day-strip__part')).toHaveCount(1)
    await expect(page.locator('.day-strip__part--aksam')).toBeVisible()
  })

  test('okunamayan düzen sayfayı durdurmaz; varsayılan akşam geçer', async ({ page }) => {
    await bugunAc(page, '2026-09-24T19:10', { 'aksam-duzeni': null })
    // `null` mocks a body of "null": not an evening, so the defaults stand.
    await expect(page.locator('.next-thing .next-thing__eyebrow')).toHaveText('Bu akşam')
    await expect(page.locator('.day-strip')).toContainText('Yatma 21:00')
  })
})

test.describe('Profil', () => {
  async function profilAc(page: Page, aksam: unknown = AKSAM_VARSAYILAN) {
    await page.route('**/api/student/profile', r => r.fulfill(json({
      name: 'Işık', student_no: '', class_name: '', branch: '', photo_data_url: '', fields: {}, scraped_at: '' })))
    await page.route('**/api/private-lessons', r => r.fulfill(json({ lessons: [] })))
    await page.route('**/api/health', r => r.fulfill(json({
      timestamp: '', success: true, scrape_errors: [], duration_seconds: 1 })))
    const gelen: unknown[] = []
    await page.route('**/api/aksam-duzeni', r => {
      if (r.request().method() === 'PUT') {
        gelen.push(JSON.parse(r.request().postData() || '{}'))
        return r.fulfill(json({ ...(aksam as object), varsayilan: false }))
      }
      return r.fulfill(json(aksam))
    })
    return gelen
  }

  test('düzen kaydedilir, e-postalar listelenir ve sonuç sayfada söylenir', async ({ page }) => {
    const gelen = await profilAc(page)
    await page.goto('/profil')

    const bolum = page.locator('.aksam-duzeni-formu')
    await expect(page.getByRole('heading', { name: 'Akşam düzeni' })).toBeVisible()
    await expect(bolum.getByLabel('Ödeve hazır olduğun saat', { exact: true })).toHaveValue('17:00')
    await expect(bolum.getByLabel('Yemek süresi (dakika)')).toHaveValue('30')
    await expect(bolum).toContainText('Liste boşken TEDY kimseye haber vermez.')
    await expect(bolum).toContainText('Işık\'ın bildirimleri yalnız onun hesabıyla açılmış cihazlara gider.')

    await bolum.getByLabel('Ödeve hazır olduğun saat', { exact: true }).fill('16:30')
    await bolum.getByLabel('Zor işlerin sonu', { exact: true }).fill('18:30')
    await bolum.getByLabel('Yatma saati', { exact: true }).fill('21:30')
    await bolum.getByRole('checkbox', { name: 'anne@example.com' }).check({ force: true })
    await bolum.getByRole('button', { name: 'Akşam düzenini kaydet' }).click()

    await expect.poll(() => gelen).toEqual([{
      okul_bitisi: '15:45', odeve_hazir: '16:30', zor_is_sonu: '18:30', hafif_is_sonu: '19:30', yemek: '18:30',
      yemek_dk: 30, hazirlik: '20:30', yatma: '21:30', baslamadi_esik_dk: 15, takildi_esik_dk: 15,
      haber_alacaklar: ['anne@example.com'],
    }])
    await expect(bolum.getByRole('status')).toContainText('Akşam düzeni kaydedildi.')
  })

  test('sırası bozuk ya da biçimsiz saat gönderilmez, alanın altında söylenir', async ({ page }) => {
    const gelen = await profilAc(page)
    await page.goto('/profil')
    const bolum = page.locator('.aksam-duzeni-formu')

    await bolum.getByLabel('Yatma saati', { exact: true }).fill('15:00')
    await bolum.getByRole('button', { name: 'Akşam düzenini kaydet' }).click()
    await expect(bolum).toContainText('Saatler sırayla olmalı: okul bitişi, ödeve hazır, zor işlerin sonu, hafif işlerin sonu, hazırlık, sonra yatma.')

    await bolum.getByLabel('Yatma saati', { exact: true }).fill('9pm')
    await bolum.getByRole('button', { name: 'Akşam düzenini kaydet' }).click()
    await expect(bolum).toContainText('Saati SS:DD biçiminde yaz (örneğin 17:00).')
    expect(gelen).toEqual([])
  })

  test('sunucunun reddi cümleyle gösterilir', async ({ page }) => {
    await profilAc(page)
    await page.route('**/api/aksam-duzeni', r => r.request().method() === 'PUT'
      ? r.fulfill({ status: 400, contentType: 'application/json', body: JSON.stringify({ error: 'Haber yalnız aile üyelerine gönderilebilir.' }) })
      : r.fulfill(json(AKSAM_VARSAYILAN)))
    await page.goto('/profil')
    const bolum = page.locator('.aksam-duzeni-formu')
    await bolum.getByRole('button', { name: 'Akşam düzenini kaydet' }).click()
    await expect(bolum.getByRole('alert')).toContainText('Haber yalnız aile üyelerine gönderilebilir.')
  })
})
