import { test, expect } from '@playwright/test'
import type { Locator } from '@playwright/test'
import { mock } from './_audit-fixtures'
import { GORSEL } from './_gorsel-fixtures'
import { sabitAc } from './_gorsel-yardim'

// D3b page gate after the audit: on a phone, a control the reader taps is at
// least 44px. spacing-09 is 48px. The English library defaults named in the
// audit fail here too.

test.use({ timezoneId: 'Europe/Istanbul', locale: 'tr-TR' })

async function enAz(locator: Locator, px = 44) {
  const n = await locator.count()
  expect(n).toBeGreaterThan(0)
  for (let i = 0; i < n; i++) {
    const box = await locator.nth(i).boundingBox()
    expect(box, `kontrol ${i}`).not.toBeNull()
    expect(box!.width).toBeGreaterThanOrEqual(px)
    expect(box!.height).toBeGreaterThanOrEqual(px)
  }
}

test('Bugün day arrows are at least 44px on a phone', async ({ page }) => {
  await sabitAc(page, '/', 390, 844)
  await enAz(page.getByRole('button', { name: 'Önceki gün', exact: true }))
  await enAz(page.getByRole('button', { name: 'Sonraki gün', exact: true }))
})

test('Asistan prompt chips are at least 44px on a phone', async ({ page }) => {
  await sabitAc(page, '/asistan', 390, 844)
  // Carbon AI asistanı: hızlı sorular giriş üstündeki karşılamada (Karsilama.tsx).
  await enAz(page.locator('.asistan__hizli-sorular button'))
})

test('Takvim week arrows say Önceki and are at least 44px on a phone', async ({ page }) => {
  await sabitAc(page, '/takvim', 390, 844)
  await expect(page.getByRole('button', { name: 'Onceki hafta', exact: true })).toHaveCount(0)
  await enAz(page.getByRole('button', { name: 'Önceki hafta', exact: true }))
  await enAz(page.getByRole('button', { name: 'Sonraki hafta', exact: true }))
})

test('Notlar row detail control is Turkish and at least 44px on a phone', async ({ page }) => {
  await sabitAc(page, '/notlar', 390, 844)
  await expect(page.getByRole('button', { name: 'Expand current row', exact: true })).toHaveCount(0)
  await enAz(page.getByRole('button', { name: 'Ayrıntı', exact: true }))
})

test('İşler section headers are at least 44px on a phone', async ({ page }) => {
  await sabitAc(page, '/isler', 390, 844)
  await enAz(page.getByRole('button', { name: 'Aktif Ödevler' }))
})

test('Dersler shows a short lesson note once', async ({ page }) => {
  await sabitAc(page, '/dersler', 390, 844)
  const note = 'Kesirlerde toplama ve çıkarma işlendi. Payda eşitleme üzerinde duruldu.'
  await expect(page.getByText(note, { exact: true })).toHaveCount(1)
})

test('a longer Dersler note keeps a 44px heading and one body', async ({ page }) => {
  const uzun = 'Kuvvet ve hareket ünitesine giriş yapıldı. '.repeat(4)
  await mock(page, {
    ...GORSEL,
    content: { 'Fen Bilimleri': { text: uzun, cards: [], items: [] } },
  })
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/dersler')
  await page.waitForLoadState('networkidle')
  await enAz(page.locator('.course-content .cds--accordion__heading:visible'))
  await expect(page.locator('.course-content-text').filter({ hasText: uzun.slice(0, 40) })).toHaveCount(1)
})
