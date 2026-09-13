import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'

// The Ödevler page is judged against docs/frontend-surface-designs.md §4.2.
// Every assertion here pins a defect that was measured off a screenshot of the
// live page on 2026-08-31, so a regression fails here rather than in front of
// Işık.

const json = (b: unknown) => ({
  status: 200, contentType: 'application/json', body: JSON.stringify(b),
})

type Row = Record<string, unknown>

// The group the screenshot showed expanded was `yapilan` — work Işık marked
// done that the teacher has not resolved yet — not the teacher-confirmed
// `tamamlanan`, which already collapses. Reproducing the defect needs this one.
function done(over: Row = {}): Row {
  return {
    'Ders Adı': 'Matematik',
    'Ödev Başlığı': 'Sayfa 165',
    'Ödev Durumu': 'Değerlendirilmemiş',
    student_marked_done: true,
    'Ödev Son Teslim Tarihi': '20.03.2026 23:59',
    first_seen: '2026-03-11T23:29:16.752613',
    ...over,
  }
}

function pending(over: Row = {}): Row {
  return {
    'Ders Adı': 'Fen Bilimleri',
    'Ödev Başlığı': '3 soru',
    'Ödev Durumu': 'Değerlendirilmemiş',
    'Ödev Son Teslim Tarihi': '16.09.2026 23:59',
    first_seen: '2026-09-14T08:00:00.123456',
    ...over,
  }
}

async function open(page: Page, homework: Row[], summary = '') {
  await page.route('**/api/homework', r => r.fulfill(json({ summary, homework })))
  await page.route('**/api/enrichment', r => r.fulfill(json({})))
  await page.route('**/api/exams', r => r.fulfill(json({ exams: [] })))
  await page.route('**/api/health', r => r.fulfill(json({
    timestamp: '', success: true, scrape_errors: [], duration_seconds: 1,
  })))
  await page.clock.setFixedTime(new Date('2026-09-15T18:00:00'))
  await page.goto('/odevler')
  // '/odevler' redirects to '/isler', so this is navigate → redirect → fetch
  // → render. A blind 600ms covered that on an idle machine and lost the
  // race under parallel load — the assertions then read an empty list.
  // Wait for the surface to have settled into one of its two states instead.
  await page.waitForURL('**/isler')
  await page.locator('.homework-item, .tedy-empty, .hw-section').first()
    .waitFor({ state: 'attached', timeout: 15000 })
}

test('no machine timestamp reaches the reader', async ({ page }) => {
  await open(page, [pending(), done()])

  // formatTurkishDate only understood DD.MM.YYYY and returned anything else
  // unchanged, so an ISO first_seen printed verbatim — microseconds and all.
  const body = await page.locator('body').innerText()
  expect(body).not.toMatch(/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/)
  expect(body).not.toContain('752613')
})

test('the six-zero summary line is gone', async ({ page }) => {
  await open(page, [pending()],
    'Ödevler\nToplam Ödev: 0 Yaptı: 0 Geç: 0 Eksik: 0 Değerlendirilmemiş: 0 Teslim Edilmeyen: 0')

  const body = await page.locator('body').innerText()
  expect(body).not.toContain('Toplam Ödev:')
  expect(body).not.toContain('Değerlendirilmemiş: 0')
})

test('finished work does not open the page, and carries no expiry alarm', async ({ page }) => {
  // Twelve finished items from March filled the screen while nothing was due,
  // because every section started expanded.
  const finished = Array.from({ length: 12 }, (_, i) =>
    done({ 'Ödev Başlığı': `Sayfa ${160 + i}` }))
  await open(page, [pending(), ...finished])

  // The completed titles are reachable but not rendered until asked for.
  await expect(page.getByText('Sayfa 171', { exact: false })).toHaveCount(0)
  // "Süresi doldu" on work that is already done is true and meaningless.
  await expect(page.getByText('Süresi doldu')).toHaveCount(0)
  // What still needs doing is visible without opening anything.
  await expect(page.getByText('3 soru', { exact: false }).first()).toBeVisible()
})

test('the page names one next step before it lists anything', async ({ page }) => {
  await open(page, [pending(), pending({ 'Ödev Başlığı': '5 soru' })])

  const next = page.locator('.next-thing')
  await expect(next).toBeVisible()
  await expect(next).toContainText('Fen Bilimleri')
  await expect(next.getByRole('button')).toHaveCount(1)
})

test('the next step is the nearest deadline, not the first row', async ({ page }) => {
  // The list is deliberately ordered furthest-deadline-first (a documented
  // product decision), so taking aktif[0] names the least urgent work. The
  // card has to choose on its own.
  await open(page, [
    pending({ 'Ders Adı': 'Türkçe', 'Ödev Başlığı': 'Okuma',
              'Ödev Son Teslim Tarihi': '18.09.2026 23:59' }),
    pending({ 'Ders Adı': 'Fen Bilimleri', 'Ödev Başlığı': '3 soru',
              'Ödev Son Teslim Tarihi': '16.09.2026 23:59' }),
  ])

  await expect(page.locator('.next-thing')).toContainText('Fen Bilimleri')
  await expect(page.locator('.next-thing')).not.toContainText('Türkçe')
})

test('the work due soonest is at the top of the list, not the bottom', async ({ page }) => {
  // The list used to be ordered furthest-deadline-first, so the most urgent
  // item sat at the bottom of the screen. For a reader who overestimates how
  // long things take, the thing due tomorrow is the thing that has to be
  // visible without scrolling (İ2, İ3).
  await open(page, [
    pending({ 'Ders Adı': 'Türkçe', 'Ödev Başlığı': 'Okuma',
              'Ödev Son Teslim Tarihi': '25.09.2026 23:59' }),
    pending({ 'Ders Adı': 'Fen Bilimleri', 'Ödev Başlığı': '3 soru',
              'Ödev Son Teslim Tarihi': '16.09.2026 23:59' }),
    pending({ 'Ders Adı': 'Matematik', 'Ödev Başlığı': 'Sayfa 165',
              'Ödev Son Teslim Tarihi': '20.09.2026 23:59' }),
  ])

  const courses = await page.locator('.homework-item__course, .homework-item strong')
    .allInnerTexts()
  const seen = courses.map(c => c.trim()).filter(Boolean)
  expect(seen.slice(0, 3)).toEqual(['Fen Bilimleri', 'Matematik', 'Türkçe'])
})
