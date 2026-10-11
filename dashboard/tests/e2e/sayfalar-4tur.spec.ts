import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'
import { SAYFALAR, sabitAc } from './_gorsel-yardim'
import { json } from './_audit-fixtures'

// Talimatname §13, 4th round (2026-10-11): the page rebuilds, each pinned on the fixed fixture.

const yonlendir = async (page: Page, uc: string, govde: unknown) =>
  page.route(`**/api/${uc}`, r => r.fulfill(json(govde)))

// B25 (İ3, S15): no number strip; the counts live in the section headings.
test('Sınavlar: no number strip, the counts are in the headings', async ({ page }) => {
  await sabitAc(page, '/sinavlar', 1440, 900)
  await expect(page.locator('.exam-stats')).toHaveCount(0)
  await expect(page.getByRole('heading', { name: 'Yaklaşan sınavlar (2)' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Geçmiş sınavlar (1)' })).toBeVisible()
  const not = await page.locator('.exam-card__grade').evaluate(el => getComputedStyle(el).color)
  expect(not).toBe('rgb(22, 22, 22)')   // S42: a grade is neutral text
})

// B49 (§5.4): Carbon's Popover — focus moves in, Esc closes and returns focus to the event.
test('Takvim: an event opens a popover that takes focus and gives it back on Esc', async ({ page }) => {
  await sabitAc(page, '/takvim', 1440, 900)
  const olay = page.locator('.calendar-grid button.calendar-event', { hasText: 'Matematik' })
  await olay.click()
  const kutu = page.getByRole('dialog', { name: 'Matematik' })
  await expect(kutu).toBeVisible()
  await expect(olay).toHaveAttribute('aria-expanded', 'true')
  await expect(kutu.getByRole('button', { name: 'Kapat' })).toBeFocused()
  await page.keyboard.press('Escape')
  await expect(kutu).toHaveCount(0)
  await expect(olay).toBeFocused()
  await expect(olay).toHaveAttribute('aria-expanded', 'false')
})

test('the sync box takes focus, closes on Esc and on Tab away', async ({ page }) => {
  await sabitAc(page, '/', 1440, 900)
  const tetik = page.getByRole('button', { name: /^Senkron durumu:/ })
  await tetik.click()
  const kutu = page.getByRole('dialog', { name: 'Senkron sağlık bilgisi' })
  await expect(kutu).toBeVisible()
  await expect(tetik).toHaveAttribute('aria-controls', 'senkron-durumu-kutusu')
  await expect(kutu).toBeFocused()
  await page.keyboard.press('Escape')
  await expect(kutu).toHaveCount(0)
  await expect(tetik).toBeFocused()
  await tetik.click()
  await expect(kutu).toBeVisible()
  await page.keyboard.press('Tab')
  await expect(kutu).toHaveCount(0)
})

// B50: Carbon's xl table, no row-height or type patch.
test('Dersler: the weekly table is Carbon\'s xl size at its own type', async ({ page }) => {
  await sabitAc(page, '/dersler', 1440, 900)
  const tablo = page.locator('.schedule-table table.cds--data-table')
  await expect(tablo).toHaveClass(/cds--data-table--xl/)
  const hucre = await tablo.locator('tbody td').nth(1).evaluate(el => ({
    yukseklik: el.getBoundingClientRect().height, boyut: getComputedStyle(el).fontSize,
  }))
  expect(hucre.yukseklik).toBeGreaterThanOrEqual(64)
  expect(hucre.boyut).toBe('14px')
})

// B64 (§4.3): a lesson in the grid opens its content on the same page.
test('Dersler: a lesson in the grid opens its content below and focuses its tab', async ({ page }) => {
  await sabitAc(page, '/dersler', 1440, 900)
  const sekmeler = page.getByRole('tab')
  await expect(sekmeler.first()).toBeVisible()
  const hedef = (await sekmeler.nth(1).innerText()).trim()
  await page.locator('.schedule-table button.schedule-lesson', { hasText: hedef }).first().click()
  const sekme = page.getByRole('tab', { name: hedef })
  await expect(sekme).toHaveAttribute('aria-selected', 'true')
  await expect(sekme).toBeFocused()
})

test('Dersler: a lesson without content says so instead of doing nothing', async ({ page }) => {
  await sabitAc(page, '/dersler', 1440, 900)
  await expect(page.getByRole('tab').first()).toBeVisible()
  await page.evaluate(() => window.dispatchEvent(new CustomEvent('tedy:ders-ac', { detail: 'Olmayan Ders' })))
  await expect(page.getByRole('status').filter({ hasText: 'Olmayan Ders için bu hafta içerik yok.' })).toBeVisible()
})

// B62 (§5.3): a closed module and an unread section on the same page are one warning.
test('Dersler: a closed and an unread section make one warning, not two bands', async ({ page }) => {
  await sabitAc(page, '/dersler', 1440, 900)
  await yonlendir(page, 'health', {
    timestamp: '2026-09-24T10:15:00', success: true, scrape_errors: [], duration_seconds: 1,
    unavailable: { takvim: { reason: 'yetkisiz', detail: 'Akademik Takvim: portal bu sayfaya yetki vermiyor' } },
    okunamadi: { ders_icerikleri: { son_okuma: '2026-09-24T09:45:00' } },
  })
  await page.reload()
  const bantlar = page.locator('.app-shell-content .cds--inline-notification')
  await expect(bantlar).toHaveCount(1)
  await expect(bantlar).toHaveClass(/cds--inline-notification--warning/)
  await expect(bantlar).toContainText('bu turda okunamadı')
  await expect(bantlar).toContainText('sunmuyor')
})

// B51, B66 (§4.7): one list in words, one skeleton, no ProgressBar, no success banner.
test('İlerleme: one list said in words, no progress bars and no celebration', async ({ page }) => {
  await sabitAc(page, '/ilerleme', 1440, 900)
  await expect(page.locator('.cds--progress-bar')).toHaveCount(0)
  await expect(page.locator('.cds--inline-notification--success')).toHaveCount(0)
  const satirlar = page.locator('.platform-list .cds--contained-list-item')
  await expect(satirlar).toHaveCount(3)
  await expect(satirlar.nth(1)).toContainText('3/5 ders')
  await expect(satirlar.nth(2)).toContainText('Tamamlandı · 1/1 ödev')
})

test('İlerleme: while the three platforms load there is one skeleton', async ({ page }) => {
  for (const uc of ['progress/ec', 'progress/a3k', 'sebit']) {
    await page.route(`**/api/${uc}`, async r => { await new Promise(t => setTimeout(t, 1500)); await r.fulfill(json({})) })
  }
  await page.goto('/ilerleme')
  await expect(page.locator('.dashboard-card > [aria-busy="true"]')).toHaveCount(1)
  await expect(page.locator('.dashboard-card > [aria-busy="true"] .cds--skeleton__text').first()).toBeVisible()
})

// B65 (§4.6, §2.2): one-line work rows, not a three-column table.
test('Takımlar: one-line rows, not a structured list', async ({ page }) => {
  await yonlendir(page, 'teams', {
    activities: [{ 'Academy+': 'Robotik kulübü', 'Çalışma Başlangıç': '25.09.2026 14:00', 'Katılım Durumu': 'Katıldı',
      'Teams Link': 'Teams' }],
    ogep: [{ 'ÖGEP (Öğrenci Gelişim Programı)': 'Hedef belirleme', 'Çalışma Başlangıç': '26.09.2026 10:00',
      'Katılım Durumu': '' }],
  })
  await page.clock.setFixedTime(new Date('2026-09-24T10:30:00+03:00'))
  await page.goto('/takimlar')
  await expect(page.locator('.cds--structured-list')).toHaveCount(0)
  await expect(page.locator('.team-list')).toHaveCount(2)
  const satir = page.locator('.is-satiri').first()
  await expect(satir.locator('.is-satiri__ad')).toHaveText('Robotik kulübü')
  await expect(satir.locator('.is-satiri__zaman')).toHaveText('25.09 14:00')
  await expect(satir.locator('.is-satiri__durum')).toHaveText('Katıldı')
  await expect(satir.locator('.is-satiri__durum svg')).toHaveCount(1)
})

// B67 (§4.8, İ5): unread is marked and open on the first visit, quiet after.
test('Duyurular: an unread announcement is open and says "Yeni"; on the next visit it is read', async ({ page }) => {
  await yonlendir(page, 'announcements', { announcements: [
    { 'e-Posta Başlık': 'Veli toplantısı', 'Yayın Tarihi': '22.09.2026 09:00', 'e-Posta İçerik': 'Cuma 18:00.' },
    { 'e-Posta Başlık': 'Kütüphane saatleri', 'Yayın Tarihi': '15.09.2026 09:00', 'e-Posta İçerik': 'Değişti.' },
  ] })
  await page.goto('/duyurular')
  await expect(page.getByText('2 yeni duyuru')).toBeVisible()
  const ilk = page.locator('.announcements-item').first()
  await expect(ilk).toContainText('Veli toplantısı')   // newest first
  await expect(ilk.locator('.announcements-item__yeni')).toHaveText('Yeni')
  await expect(ilk.locator('.cds--accordion__heading')).toHaveAttribute('aria-expanded', 'true')
  await page.reload()
  await expect(page.locator('.announcements-item__yeni')).toHaveCount(0)
  await expect(page.locator('.announcements-item').first().locator('.cds--accordion__heading'))
    .toHaveAttribute('aria-expanded', 'false')
})

// B40 (D2): the rest of the accessibility list.
test('B40: one navigation name, a named grade table, an event says its kind, ÖGEP is spelled out', async ({ page }) => {
  await sabitAc(page, '/notlar', 1440, 900)
  await expect(page.getByRole('navigation', { name: 'Ana gezinme' })).toHaveCount(1)
  await expect(page.getByRole('navigation', { name: 'Navigasyon' })).toHaveCount(0)
  await expect(page.getByRole('table', { name: 'Notlar' })).toBeVisible()
  await page.goto('/takvim')
  await expect(page.getByRole('button', { name: 'Ders: Matematik' })).toBeVisible()
  await page.goto('/takimlar')
  await expect(page.locator('abbr[title="Öğrenci Gelişim Programı"]').first()).toHaveText('ÖGEP')
})

test('B40: every skeleton says the region is busy', async ({ page }) => {
  for (const uc of ['schedule', 'modules']) {
    await page.route(`**/api/${uc}`, async r => { await new Promise(t => setTimeout(t, 1500)); await r.fulfill(json({})) })
  }
  await page.goto('/dersler')
  await expect(page.locator('[aria-busy="true"] .cds--skeleton__text').first()).toBeVisible()
  await page.goto('/moduller')
  await expect(page.locator('[aria-busy="true"] .cds--skeleton__text').first()).toBeVisible()
})

test('B40: after "Yaptım" on İşler focus lands on what was recorded', async ({ page }) => {
  await sabitAc(page, '/isler', 1440, 900)
  await page.route('**/api/homework/mark-done', r => r.fulfill(json({ ok: true })))
  await page.locator('.homework-item').first().getByRole('button', { name: 'Yaptım' }).click()
  await expect(page.locator('.yaptin-satiri__metin')).toBeFocused()
})

// B36 (S22, [3.3-5]): `.tedy-time` wraps only figures; the words around them stay in Sans.
test('every .tedy-time on every page holds figures only', async ({ page }) => {
  test.setTimeout(120_000)
  const ihlal: string[] = []
  for (const [ad, yol] of SAYFALAR) {
    await sabitAc(page, yol, 1440, 900)
    for (const metin of await page.locator('.tedy-time').allInnerTexts()) {
      if (/[A-Za-zÇĞİÖŞÜçğıöşü]/.test(metin)) ihlal.push(`${ad}: "${metin}"`)
    }
  }
  expect(ihlal).toEqual([])
})

// B60 (§5.6): Carbon's own controls, sentence-case labels, a phone stacks the two times.
test('Profil: the private-lesson form is Carbon controls and one column on a phone', async ({ page }) => {
  await sabitAc(page, '/profil', 390, 844)
  const form = page.locator('form.private-lesson-form')
  await expect(form.locator('select.cds--select-input')).toHaveCount(2)
  await expect(form.getByLabel('Öğretmen adı')).toHaveClass(/cds--text-input/)
  await expect(form.getByRole('checkbox', { name: 'Ders her hafta tekrar ediyor' })).toBeChecked()
  const bas = (await form.getByLabel('Başlangıç').boundingBox())!
  const bit = (await form.getByLabel('Bitiş').boundingBox())!
  expect(bit.y).toBeGreaterThan(bas.y + bas.height)
  await form.getByRole('checkbox', { name: 'Ders her hafta tekrar ediyor' }).uncheck({ force: true })
  await expect(form.getByText('Bugünden sonraki bir gün, gg.aa.yyyy biçiminde.')).toBeVisible()
})
