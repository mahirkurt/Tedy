import { test, expect } from '@playwright/test'

// docs/frontend-surface-designs.md §5. Focus mode is a working state, not a
// dimmer switch: it shows the one named thing and puts the rest one click
// away. What it must never do is leave a row on screen that cannot be
// identified — "Türkçe" with a Yaptım button next to it asks the reader to
// confirm work she cannot see the name of.

const json = (b: unknown) => ({
  status: 200, contentType: 'application/json', body: JSON.stringify(b),
})

const HW = (c: string, t: string, d: string) => ({
  'Ders Adı': c, 'Ödev Başlığı': t,
  'Ödev Durumu': 'Değerlendirilmemiş', 'Ödev Son Teslim Tarihi': d,
})

test('focus mode never shows work it will not name', async ({ page }) => {
  await page.route('**/api/homework', r => r.fulfill(json({
    summary: '', homework: [
      HW('Fen Bilimleri', '3 soru', '16.09.2026 23:59'),
      HW('Türkçe', 'Okuma', '18.09.2026 23:59'),
    ],
  })))
  await page.route('**/api/enrichment', r => r.fulfill(json({})))
  await page.route('**/api/exams', r => r.fulfill(json({ exams: [] })))
  await page.route('**/api/health', r => r.fulfill(json({
    timestamp: '', success: true, scrape_errors: [], duration_seconds: 1,
  })))
  await page.clock.setFixedTime(new Date('2026-09-15T18:00:00'))
  await page.addInitScript(() => localStorage.setItem('tedy-focus-mode', 'true'))

  await page.goto('/isler')
  await page.waitForLoadState('networkidle')

  // The one thing is still named in full. This expect retries, and it has to
  // pass before the row loop below calls count(), which does not.
  await expect(page.locator('.next-thing')).toContainText('Fen Bilimleri — 3 soru')

  // Every homework row on screen carries the name of its work. A row that
  // shows only a course is a row that cannot be acted on.
  const rows = page.locator('.homework-item')
  for (let i = 0; i < await rows.count(); i++) {
    const row = rows.nth(i)
    if (!(await row.isVisible())) continue
    const text = await row.innerText()
    expect(text).toMatch(/3 soru|Okuma/)
  }
})

test('focus keeps the counts so nothing feels lost', async ({ page }) => {
  await page.route('**/api/homework', r => r.fulfill(json({
    summary: '', homework: [HW('Fen Bilimleri', '3 soru', '16.09.2026 23:59')],
  })))
  await page.route('**/api/enrichment', r => r.fulfill(json({})))
  await page.route('**/api/exams', r => r.fulfill(json({ exams: [] })))
  await page.route('**/api/health', r => r.fulfill(json({
    timestamp: '', success: true, scrape_errors: [], duration_seconds: 1,
  })))
  await page.clock.setFixedTime(new Date('2026-09-15T18:00:00'))
  await page.addInitScript(() => localStorage.setItem('tedy-focus-mode', 'true'))

  await page.goto('/isler')
  await page.waitForLoadState('networkidle')

  // The list is closed, but its size is still on screen: focus puts the rest
  // one click away rather than pretending it is not there.
  await expect(page.getByText('Aktif Ödevler', { exact: false })).toBeVisible()
  await expect(page.locator('.hw-section__count').first()).toBeVisible()
})

test('focus hides finished work rather than leading with it', async ({ page }) => {
  await page.route('**/api/homework', r => r.fulfill(json({
    summary: '', homework: [
      { ...HW('Fen Bilimleri', '3 soru', '16.09.2026 23:59'), 'Ödev Durumu': 'Yaptı' },
    ],
  })))
  await page.route('**/api/enrichment', r => r.fulfill(json({})))
  await page.route('**/api/exams', r => r.fulfill(json({ exams: [] })))
  await page.route('**/api/health', r => r.fulfill(json({
    timestamp: '', success: true, scrape_errors: [], duration_seconds: 1,
  })))
  await page.addInitScript(() => localStorage.setItem('tedy-focus-mode', 'true'))

  await page.goto('/isler')
  await page.waitForLoadState('networkidle')

  await expect(page.getByText('Şu an teslim bekleyen bir işin yok.')).toBeVisible()
  await expect(page.getByText('Tamamlandı', { exact: true })).toHaveCount(0)
  await expect(page.getByText('Yapılan', { exact: true })).toHaveCount(0)
})
