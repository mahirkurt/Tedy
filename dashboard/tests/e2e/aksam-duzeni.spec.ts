import { test, expect, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { createRequire } from 'node:module'
import { bugunAc } from './_bugun-fixtures'
import { AKSAM_VARSAYILAN } from './_audit-fixtures'

// B29 (anayasa §2: "the window is a parameter, not a constant; it is kept
// configurable in output/"), widened 2026-10-19 into the household's evening:
// Bugün reads it from /api/aksam-duzeni and Profil sets it. The family's own
// evening is the default: ready for homework 17:00, hard work until 19:00,
// bed at 21:00.

const json = (b: unknown) => ({ status: 200, contentType: 'application/json', body: JSON.stringify(b) })
const ACE = createRequire(import.meta.url).resolve('accessibility-checker-engine/ace.js')

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
    // A name heading is title case (S38, 2026-10-19); exact, because the default match ignores case.
    await expect(page.getByRole('heading', { name: 'Akşam Düzeni', exact: true })).toBeVisible()
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

  test('bağlantı kopunca ham İngilizce hata değil sabit Türkçe cümle gösterilir', async ({ page }) => {
    await profilAc(page)
    await page.route('**/api/aksam-duzeni', r => r.request().method() === 'PUT'
      ? r.abort('failed')
      : r.fulfill(json(AKSAM_VARSAYILAN)))
    await page.goto('/profil')
    const bolum = page.locator('.aksam-duzeni-formu')
    await bolum.getByRole('button', { name: 'Akşam düzenini kaydet' }).click()
    await expect(bolum.getByRole('alert')).toContainText('Akşam düzeni kaydedilemedi. Bağlantını kontrol edip yeniden dene.')
    await expect(bolum).not.toContainText('Failed to fetch')
  })

  test('Işık için salt okunur: değerler görünür, aile ayarlar, kaydetme yok (R28 I2)', async ({ page }) => {
    // The server sends Işık the setting without the family roster; the card shows who is told, read-only.
    const ayar: Record<string, unknown> = { ...AKSAM_VARSAYILAN, haber_alacaklar: ['anne@example.com'], varsayilan: false }
    delete ayar.aile_uyeleri
    const gelen = await profilAc(page, ayar)
    await page.route('**/api/auth/me', r => r.fulfill(json({
      email: 'isik@example.com', name: 'Işık', picture: '', role: 'full', student: true })))
    await page.goto('/profil')
    const bolum = page.locator('.aksam-duzeni-formu')

    await expect(bolum).toContainText('Bu saatleri ailen ayarlar.')
    const hazir = bolum.getByLabel('Ödeve hazır olduğun saat', { exact: true })
    await expect(hazir).toHaveValue('17:00')
    // readOnly, not disabled (B42): legible, focusable, not editable.
    await expect(hazir).toHaveAttribute('readonly', '')
    await expect(hazir).toBeEnabled()
    await expect(bolum.getByLabel('Yemek süresi (dakika)')).toHaveAttribute('readonly', '')
    const kutu = bolum.getByRole('checkbox', { name: 'anne@example.com' })
    await expect(kutu).toBeChecked()
    await expect(kutu).toHaveAttribute('aria-readonly', 'true')
    await expect(bolum.getByRole('checkbox')).toHaveCount(1)
    await expect(bolum.getByRole('button', { name: 'Akşam düzenini kaydet' })).toHaveCount(0)

    await hazir.press('End')
    await hazir.pressSequentially('9')
    await expect(hazir).toHaveValue('17:00')
    await kutu.click({ force: true })
    await expect(kutu).toBeChecked()
    await bolum.evaluate(f => (f as HTMLFormElement).requestSubmit())
    expect(gelen).toEqual([])
    // The read-only view is as clean as the family's (Carbon's group-level readOnly is not, see the card).
    const { violations } = await new AxeBuilder({ page }).include('.aksam-duzeni-formu')
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice']).analyze()
    expect(violations.map(v => `${v.impact} ${v.id}`)).toEqual([])
    await page.addScriptTag({ path: ACE })
    const ihlal: string[] = await page.evaluate(async () => {
      // @ts-expect-error — `ace` is the injected engine's global
      const rapor = await new window.ace.Checker().check(document.querySelector('.aksam-duzeni-formu'), ['IBM_Accessibility'])
      return (rapor.results as { ruleId: string; value: string[]; snippet: string }[])
        .filter(s => s.value[0] === 'VIOLATION' && s.value[1] === 'FAIL').map(s => `${s.ruleId} — ${s.snippet.slice(0, 120)}`)
    })
    expect(ihlal).toEqual([])
  })

  test('okunamayan düzen: sabit cümle, form yok, kaydetme yok (R28 I3)', async ({ page }) => {
    const gelen = await profilAc(page)
    await page.route('**/api/aksam-duzeni', r => r.request().method() === 'PUT'
      ? r.fulfill(json({}))
      : r.fulfill({ status: 500, contentType: 'text/html', body: '<html>Internal Server Error</html>' }))
    await page.goto('/profil')
    const kart = page.locator('.dashboard-card', { has: page.getByRole('heading', { name: 'Akşam Düzeni', exact: true }) })
    await expect(kart.getByRole('alert')).toContainText('Akşam düzeni şu an okunamadı')
    await expect(kart.getByRole('alert')).toContainText('Kayıtlı ayarların üzerine yazılmasın diye kaydetme kapalı.')
    await expect(kart).not.toContainText('Internal Server Error')
    // The defaults must not pass for the household's evening, nor a save made from them wipe the list.
    await expect(kart.locator('.aksam-duzeni-formu')).toHaveCount(0)
    await expect(kart.getByRole('button', { name: 'Akşam düzenini kaydet' })).toHaveCount(0)
    expect(gelen).toEqual([])
  })

  test('JSON olmayan ret gövdesi de sabit cümleyle gösterilir', async ({ page }) => {
    await profilAc(page)
    await page.route('**/api/aksam-duzeni', r => r.request().method() === 'PUT'
      ? r.fulfill({ status: 500, contentType: 'text/html', body: '<html>Internal Server Error</html>' })
      : r.fulfill(json(AKSAM_VARSAYILAN)))
    await page.goto('/profil')
    const bolum = page.locator('.aksam-duzeni-formu')
    await bolum.getByRole('button', { name: 'Akşam düzenini kaydet' }).click()
    await expect(bolum.getByRole('alert')).toContainText('Akşam düzeni kaydedilemedi.')
    await expect(bolum).not.toContainText('Internal Server Error')
  })
})
