import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'

// On 2026-08-31 the portal rolled into 2026-2027 and closed two modules. The
// dashboard went blank and said only "Ödev bulunamadı." — indistinguishable
// from a broken sync. The reason was in /api/health all along, reachable only
// by opening a popover and hovering a row. This banner lifts it into view.

function mockHealth(page: Page, unavailable: Record<string, { reason: string; detail: string }>) {
  return page.route('**/api/health', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      timestamp: '2026-08-31T00:00:00', success: true,
      scrape_errors: [], duration_seconds: 120,
      academic_year: '2026-2027',
      unavailable,
      sections: {
        ders_programi: { count: 0, prev_count: 0, status: 'unavailable' },
        takvim: { count: 0, prev_count: 0, status: 'unavailable' },
      },
    }),
  }))
}

test('a section the portal closed is named in a banner, with the portal\'s own words', async ({ page }) => {
  await mockHealth(page, {
    ders_programi: {
      reason: 'modul_kapali',
      detail: 'Haftalık Ders Programı: Akademi Modülü kısa bir süre erişime kapalıdır.',
    },
    takvim: {
      reason: 'yetkisiz',
      detail: 'Akademik Takvim: portal bu sayfaya yetki vermiyor',
    },
  })
  await page.goto('/dersler')

  const banner = page.locator('.portal-status')
  await expect(banner).toBeVisible()
  // Names both sections in Turkish, not as raw keys.
  await expect(banner).toContainText('Ders Programı')
  await expect(banner).toContainText('Takvim')
  await expect(banner).not.toContainText('ders_programi')
  // Carries the portal's own explanation, so "closed upstream" cannot be
  // mistaken for "our sync broke".
  await expect(banner).toContainText('Akademi Modülü')
})

test('nothing is shown when the portal is serving every section', async ({ page }) => {
  await mockHealth(page, {})
  await page.goto('/dersler')
  await expect(page.locator('.portal-status')).toHaveCount(0)
})

test('the banner stays off pages that do not show those sections', async ({ page }) => {
  await mockHealth(page, {
    ders_programi: {
      reason: 'modul_kapali',
      detail: 'Haftalık Ders Programı: Akademi Modülü kısa bir süre erişime kapalıdır.',
    },
    takvim: {
      reason: 'yetkisiz',
      detail: 'Akademik Takvim: portal bu sayfaya yetki vermiyor',
    },
  })
  for (const path of ['/', '/isler', '/notlar']) {
    await page.goto(path)
    await expect(page.locator('.portal-status'), `${path} üzerinde banner`).toHaveCount(0)
  }
})
