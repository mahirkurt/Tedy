import { test, expect, type Page } from '@playwright/test'
import { bugunAc } from './_bugun-fixtures'

// B29 (anayasa §2: "the window is a parameter, not a constant; it is kept
// configurable in output/"): Bugün reads the household's focus window from
// /api/odak-penceresi and Profil sets it. Today's values are the defaults.

const json = (b: unknown) => ({ status: 200, contentType: 'application/json', body: JSON.stringify(b) })

async function pencere(page: Page, govde: Record<string, unknown>) {
  await page.route('**/api/odak-penceresi', r => r.fulfill(json(govde)))
}

test.describe('Bugün', () => {
  test('sunucunun penceresiyle konuşur: 16:10 pencere içinde "Şimdi"', async ({ page }) => {
    await pencere(page, { okul_bitisi: '15:45', odak_sonu: '16:30', yatma: '21:45', varsayilan: false })
    await bugunAc(page, '2026-09-24T16:10')
    await expect(page.locator('.next-thing .next-thing__eyebrow')).toHaveText('Şimdi')
    const serit = page.locator('.day-strip')
    await expect(serit).toContainText('Ödev zamanı 15:45–16:30')
    await expect(serit).toContainText('Yatma 21:45')
  })

  test('ayar yoksa bugünkü değerler: 16:10 "Bu akşam", odak sonu 16:00 geçti', async ({ page }) => {
    await pencere(page, { okul_bitisi: '15:45', odak_sonu: '16:00', yatma: '22:30', varsayilan: true })
    await bugunAc(page, '2026-09-24T16:10')
    await expect(page.locator('.next-thing .next-thing__eyebrow')).toHaveText('Bu akşam')
    await expect(page.locator('.day-strip')).toContainText('Yatma 22:30')
    // The homework slot is behind; only the evening is left on the strip.
    await expect(page.locator('.day-strip__homework')).toHaveCount(0)
    await expect(page.locator('.day-strip__part')).toHaveCount(1)
    await expect(page.locator('.day-strip__part--aksam')).toBeVisible()
  })

  test('okunamayan pencere sayfayı durdurmaz; bugünkü değerler geçer', async ({ page }) => {
    await page.route('**/api/odak-penceresi', r => r.fulfill({ status: 500, body: 'x' }))
    await bugunAc(page, '2026-09-24T16:10')
    await expect(page.locator('.next-thing .next-thing__eyebrow')).toHaveText('Bu akşam')
  })
})

test.describe('Profil', () => {
  async function profilAc(page: Page) {
    await page.route('**/api/student/profile', r => r.fulfill(json({
      name: 'Işık', student_no: '', class_name: '', branch: '', photo_data_url: '', fields: {}, scraped_at: '' })))
    await page.route('**/api/private-lessons', r => r.fulfill(json({ lessons: [] })))
    await page.route('**/api/health', r => r.fulfill(json({
      timestamp: '', success: true, scrape_errors: [], duration_seconds: 1 })))
  }

  test('pencere kaydedilir ve sonuç sayfada söylenir', async ({ page }) => {
    await profilAc(page)
    const gelen: unknown[] = []
    await page.route('**/api/odak-penceresi', r => {
      if (r.request().method() === 'PUT') {
        gelen.push(JSON.parse(r.request().postData() || '{}'))
        return r.fulfill(json({ okul_bitisi: '15:30', odak_sonu: '16:15', yatma: '22:00', varsayilan: false }))
      }
      return r.fulfill(json({ okul_bitisi: '15:45', odak_sonu: '16:00', yatma: '22:30', varsayilan: true }))
    })
    await page.goto('/profil')

    const bolum = page.locator('.odak-penceresi-formu')
    await expect(bolum.getByLabel('Son zil', { exact: true })).toHaveValue('15:45')
    await bolum.getByLabel('Son zil', { exact: true }).fill('15:30')
    await bolum.getByLabel('Odak penceresinin sonu', { exact: true }).fill('16:15')
    await bolum.getByLabel('Yatma saati', { exact: true }).fill('22:00')
    await bolum.getByRole('button', { name: 'Pencereyi kaydet' }).click()

    await expect.poll(() => gelen).toEqual([{ okul_bitisi: '15:30', odak_sonu: '16:15', yatma: '22:00' }])
    await expect(bolum.getByRole('status')).toContainText('Odak penceresi kaydedildi.')
  })

  test('sırası bozuk ya da biçimsiz saat gönderilmez, alanın altında söylenir', async ({ page }) => {
    await profilAc(page)
    let put = 0
    await page.route('**/api/odak-penceresi', r => {
      if (r.request().method() === 'PUT') put++
      return r.fulfill(json({ okul_bitisi: '15:45', odak_sonu: '16:00', yatma: '22:30', varsayilan: true }))
    })
    await page.goto('/profil')
    const bolum = page.locator('.odak-penceresi-formu')

    await bolum.getByLabel('Yatma saati', { exact: true }).fill('15:00')
    await bolum.getByRole('button', { name: 'Pencereyi kaydet' }).click()
    await expect(bolum).toContainText('Saatler sırayla olmalı: son zil, odak penceresinin sonu, sonra yatma saati.')

    await bolum.getByLabel('Yatma saati', { exact: true }).fill('9pm')
    await bolum.getByRole('button', { name: 'Pencereyi kaydet' }).click()
    await expect(bolum).toContainText('Saati SS:DD biçiminde yaz (örneğin 15:45).')
    expect(put).toBe(0)
  })
})
