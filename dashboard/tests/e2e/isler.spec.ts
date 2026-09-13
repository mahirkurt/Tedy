import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'

// docs/frontend-surface-designs.md §1 and §4.2: homework and exams are one
// thing in Işık's head — work she owes — and two only in ours. They live on one
// surface now, and the old paths keep working.

const json = (b: unknown) => ({
  status: 200, contentType: 'application/json', body: JSON.stringify(b),
})

const HW = {
  'Ders Adı': 'Fen Bilimleri', 'Ödev Başlığı': '3 soru',
  'Ödev Durumu': 'Değerlendirilmemiş', 'Ödev Son Teslim Tarihi': '16.09.2026 23:59',
}

const EXAM = {
  id: 'e1', course: 'Matematik', title: 'Matematik 1. yazılı', rawTitle: '',
  courseColor: '', examNumber: 1, date: '2026-09-25T09:00:00', endDate: null,
  allDay: false, status: 'upcoming', grade: null, studyGuide: null,
}

async function mock(page: Page) {
  await page.route('**/api/homework', r => r.fulfill(json({ summary: '', homework: [HW] })))
  await page.route('**/api/enrichment', r => r.fulfill(json({})))
  await page.route('**/api/exams', r => r.fulfill(json({ exams: [EXAM] })))
  await page.route('**/api/health', r => r.fulfill(json({
    timestamp: '', success: true, scrape_errors: [], duration_seconds: 1,
  })))
  await page.clock.setFixedTime(new Date('2026-09-15T18:00:00'))
}

test('work owed lives on one surface: homework and the exams ahead', async ({ page }) => {
  await mock(page)
  await page.goto('/isler')

  // Assert the surface, not just the strings: Bugün also lists homework and
  // upcoming exams, so an unrouted /isler falling back to it would pass a test
  // that only looked for the text.
  // The label is title case in the DOM; the shouting is CSS. Waiting on it
  // first is also what makes the URL read meaningful: the fallback would be a
  // client-side redirect, which happens only after the app has mounted — and
  // page.url() does not retry.
  await expect(page.getByText('Aktif Ödevler', { exact: false })).toBeVisible()
  expect(new URL(page.url()).pathname).toBe('/isler')

  await expect(page.getByText('3 soru', { exact: false }).first()).toBeVisible()
  await expect(page.getByText('Matematik 1. yazılı', { exact: false }).first()).toBeVisible()
})

test('the old paths still land somewhere sensible', async ({ page }) => {
  await mock(page)

  // Nothing that was bookmarked breaks; it redirects rather than 404s.
  await page.goto('/odevler')
  // Wait on the condition, not on a guess about how long the redirect takes.
  await page.waitForURL('**/isler')
  expect(new URL(page.url()).pathname).toBe('/isler')

  await page.goto('/sinavlar')
  await page.waitForLoadState('networkidle')
  // The exam detail keeps its own page — grades, past papers and study guides
  // are real content and compressing them into a section would lose them. It
  // just stops taking a slot in the primary navigation.
  expect(new URL(page.url()).pathname).toBe('/sinavlar')
})

test('the navigation lost a decision', async ({ page }) => {
  await mock(page)
  await page.goto('/isler')

  const nav = page.locator('nav').first()
  // Visible, not merely present. On the rail Carbon kept each label in the DOM
  // for screen readers and hid it from sight, so the navigation read as a
  // column of unlabelled glyphs — a memory tax on the reader who has least to
  // spare. The rail is gone.
  // The positive expect comes first and retries, so the two absences after it
  // are read from a mounted navigation rather than from an empty page.
  await expect(nav.getByText('İşler', { exact: true })).toBeVisible()
  await expect(nav.getByText('Sınavlar', { exact: true })).toHaveCount(0)
  await expect(nav.getByText('Ödevler', { exact: true })).toHaveCount(0)
})
