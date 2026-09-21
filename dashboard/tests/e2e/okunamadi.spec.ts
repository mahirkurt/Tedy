import { test, expect } from '@playwright/test'
import { mock, LIVE } from './_audit-fixtures'

// "The school closed this module" and "we could not read it" both leave a
// page empty, and the second was being told as the first. Measured
// 2026-09-21: for nearly two hours every sync failed the ogrenci_istekler
// pages, so the dashboard showed Işık no homework, no timetable and no
// grades — and each surface said "portalda kayıt yok", which was false.

const health = (extra: Record<string, unknown>) => ({
  timestamp: '2026-09-21T10:17:50', success: false, scrape_errors: [],
  duration_seconds: 168, validation_warnings: [], unavailable: {},
  academic_year: '2026-2027', ...extra,
})

test('an unread section says it was unread, not that there is nothing', async ({ page }) => {
  await mock(page, {
    ...LIVE,
    health: health({ okunamadi: { odevlerim: { detail: 'sayfa beklenen içeriği vermedi' } } }),
  })
  await page.goto('/isler')
  await page.waitForLoadState('networkidle')

  const uyari = page.locator('.portal-unread')
  await expect(uyari).toHaveCount(1)
  await expect(uyari).toContainText('okunamadı')
  await expect(uyari).toContainText('Ödevler')
  // The reassurance matters as much as the fact: an empty list is not proof
  // there is no homework.
  await expect(uyari).toContainText('veri olmadığı anlamına gelmiyor')
})

test('several unread sections are named together where both belong', async ({ page }) => {
  // Bugün shows homework and the timetable, so both names belong there.
  await mock(page, {
    ...LIVE,
    health: health({
      okunamadi: {
        odevlerim: { detail: 'sayfa beklenen içeriği vermedi' },
        ders_programi: { detail: 'sayfa beklenen içeriği vermedi' },
      },
    }),
  })
  await page.goto('/')
  await page.waitForLoadState('networkidle')

  const uyari = page.locator('.portal-unread')
  await expect(uyari).toContainText('Ödevler')
  await expect(uyari).toContainText('Program')
})

test('an unread section is not announced on a page that never showed it', async ({ page }) => {
  // İ6: telling Işık on Takvim that her homework could not be read is noise.
  await mock(page, {
    ...LIVE,
    health: health({ okunamadi: { odevlerim: { detail: 'x' } } }),
  })
  await page.goto('/takvim')
  await page.waitForLoadState('networkidle')
  await page.locator('#root h1').waitFor({ state: 'attached' })

  await expect(page.locator('.portal-unread')).toHaveCount(0)
})

test('nothing unread means no warning at all', async ({ page }) => {
  // İ6: a banner that is always there stops being read.
  await mock(page, { ...LIVE, health: health({ okunamadi: {} }) })
  await page.goto('/isler')
  await page.waitForLoadState('networkidle')
  await page.locator('#root h1').waitFor({ state: 'attached' })

  await expect(page.locator('.portal-unread')).toHaveCount(0)
})

test('the portal refusing a page keeps its own, different sentence', async ({ page }) => {
  // That sentence names Takvim, so it belongs on Takvim — not on İşler.
  await mock(page, {
    ...LIVE,
    health: health({
      unavailable: { takvim: { reason: 'yetkisiz', detail: 'portal bu sayfaya yetki vermiyor' } },
      okunamadi: {},
    }),
  })
  await page.goto('/takvim')
  await page.waitForLoadState('networkidle')

  await expect(page.locator('.portal-status')).toHaveCount(1)
  await expect(page.locator('.portal-status')).toContainText('sunmuyor')
  await expect(page.locator('.portal-unread')).toHaveCount(0)
})
