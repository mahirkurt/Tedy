import { test, expect } from '@playwright/test'
import { mock, FULL, LIVE, json } from './_audit-fixtures'

// Aesthetic findings from reading the captured surfaces. Each one is a thing
// the screenshots showed, not a thing the source suggested.

test('the calendar copy is spelled in Turkish', async ({ page }) => {
  await mock(page, LIVE)
  await page.goto('/takvim')
  await page.waitForLoadState('networkidle')
  const text = await page.locator('.app-shell-content').innerText()
  expect(text).toContain('Haftalık Takvim')
  expect(text).not.toContain('Haftalik')
})

test('a markdown list looks like a list', async ({ page }) => {
  // Carbon's reset sets `list-style: none` on every ul/ol, so the assistant's
  // answers rendered their steps as three unmarked lines.
  await page.route('**/api/assistant/stream', r => r.abort())
  await page.route('**/api/assistant/chat', r => r.fulfill(json({
    answer: 'Adımlar:\n\n- önce paydayı eşitle\n- sonra payları topla',
    citations: [], safety_flags: [], plan_blocks: [], intent: 'qa', session_id: '',
    meta: { model: 'gemini-3.7-flash', degraded: [], dropped_citations: 0 },
  })))
  await page.goto('/asistan')
  await page.waitForLoadState('networkidle')
  await page.fill('#ac-input', 'nasıl')
  await page.getByLabel('Gönder').click()
  await page.waitForTimeout(700)

  const style = await page.locator('.bookmd__list').first()
    .evaluate(el => getComputedStyle(el).listStyleType)
  expect(style, 'liste işareti yok').not.toBe('none')
})

test('the two empty sections on Dersler say which is which', async ({ page }) => {
  // Both rendered as bare grey sentences with nothing naming them, so the
  // page read as two unattributed statements.
  // Both sections genuinely empty — LIVE keeps real course content, which
  // would leave only one empty line on the page.
  await mock(page, { ...LIVE, content: {} })
  await page.goto('/dersler')
  await page.waitForLoadState('networkidle')
  await page.waitForTimeout(300)

  // The labels are upper-cased by CSS and innerText reports what is
  // rendered, so compare against the upper-cased forms rather than
  // round-tripping through a Turkish lowercase (where İ → i + combining dot
  // and no longer matches a plain i).
  const labels = await page.locator('.tedy-empty__label').allInnerTexts()
  expect(labels.map(s => s.trim()))
    .toEqual(['HAFTALIK PROGRAM', 'DERS İÇERİKLERİ'])
})

test('an empty grade table says it is empty instead of showing a bare header', async ({ page }) => {
  await mock(page, LIVE)
  await page.goto('/notlar')
  await page.waitForLoadState('networkidle')
  await page.waitForTimeout(300)

  // A header row with no rows under it claims data that is not there.
  const headerCells = await page.locator('th').count()
  const bodyRows = await page.locator('tbody tr').count()
  expect(headerCells === 0 || bodyRows > 0,
    `başlıksız gövde: ${headerCells} başlık hücresi, ${bodyRows} satır`).toBe(true)
  await expect(page.getByText('not girilmemiş', { exact: false })).toBeVisible()
})

test('the grade title has no dangling separator', async ({ page }) => {
  await page.route('**/api/assistant/stream', r => r.abort())
  await page.route('**/api/grades', r => r.fulfill(json({ grades: [], semester: '' })))
  await page.goto('/notlar')
  await page.waitForLoadState('networkidle')
  await page.waitForTimeout(300)
  const text = await page.locator('.app-shell-content').innerText()
  expect(text).not.toMatch(/Notlar\s+[—–-]\s*(\n|$)/)
})

test('the portal banner stays off surfaces that are not portal data', async ({ page }) => {
  await mock(page, LIVE)
  for (const path of ['/kitaplar', '/asistan']) {
    await page.goto(path)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(300)
    await expect(page.locator('.portal-status'),
      `${path} üzerinde portal banner'ı var`).toHaveCount(0)
  }
  // It still appears where the portal's own sections are shown.
  await page.goto('/takvim')
  await page.waitForLoadState('networkidle')
  await expect(page.locator('.portal-status')).toHaveCount(1)
})

test('the calendar legend names only the kinds in view', async ({ page }) => {
  // Seven chips rendered whatever the week held, so a week with two kinds of
  // event still opened with seven colours to read past.
  await mock(page, FULL)
  await page.goto('/takvim')
  await page.waitForLoadState('networkidle')
  await page.waitForTimeout(400)
  const chips = await page.locator('.calendar-legend__chip').count()
  const events = await page.locator('.calendar-grid__event').count()
  expect(chips, `${events} etkinlik için ${chips} çip`).toBeLessThanOrEqual(3)
})
