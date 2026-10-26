import { test, expect } from '@playwright/test'
import { KILAVUZ, fikstur, json } from './_hazirlik'

test.use({ timezoneId: 'Europe/Istanbul', locale: 'tr-TR' })

// Baskı görünümü (spec §5.1–5.2, plan Görev 13): aynı KilavuzBelgesi kâğıt kipinde; Paged.js sayfalar.
async function bekle(page: import('@playwright/test').Page) {
  await page.waitForFunction(() => {
    const w = window as unknown as { __KILAVUZ_HAZIR__?: unknown; __KILAVUZ_HATA__?: unknown }
    return w.__KILAVUZ_HAZIR__ || w.__KILAVUZ_HATA__
  })
  return page.evaluate(() => {
    const w = window as unknown as { __KILAVUZ_HAZIR__?: { sayfa: number }; __KILAVUZ_HATA__?: string }
    return { hazir: w.__KILAVUZ_HAZIR__ ?? null, hata: w.__KILAVUZ_HATA__ ?? null }
  })
}

test('Paged.js yolu: sayfalar, gerçek İçindekiler numarası, etkileşimsiz kâğıt (K5, K11)', async ({ page }) => {
  await page.route(KILAVUZ('fen-bilimleri', 1), r => r.fulfill(json(fikstur('fen-bilimleri-1-kilavuz'))))
  await page.goto('/baski.html?ders=fen-bilimleri&sinav=1')
  const s = await bekle(page)
  expect(s.hata).toBeNull()
  expect(s.hazir!.sayfa).toBeGreaterThan(2)
  await expect(page.locator('.pagedjs_page')).toHaveCount(s.hazir!.sayfa)
  await expect(page.locator('.kilavuz-icindekiler__baglanti').first()).toHaveText('Özet')
  await expect(page.locator('input[type="checkbox"]')).toHaveCount(0)
  await expect(page.locator('.kilavuz-isaret__kutu')).not.toHaveCount(0)
  expect(await page.title()).toBe('Fen Bilimleri · 1. yazılı · 2. senaryo')
})

test('düz yol: Paged.js çalışmaz, başlık damgayı taşır', async ({ page }) => {
  await page.route(KILAVUZ('fen-bilimleri', 1), r => r.fulfill(json(fikstur('fen-bilimleri-1-kilavuz'))))
  await page.goto('/baski.html?ders=fen-bilimleri&sinav=1&duz=1')
  const s = await bekle(page)
  expect(s.hazir).toEqual({ sayfa: 0 })
  await expect(page.locator('article.kilavuz-belge--baski')).toBeVisible()
  await expect(page.locator('.pagedjs_page')).toHaveCount(0)
  expect(await page.title()).toMatch(/^Fen Bilimleri · 1\. yazılı · 2\. senaryo — TEDY · MEB tablosu 10\.09\.2026/)
})

test('model alınamazsa sinyal hatadır (basım betiği 3 ile çıkar)', async ({ page }) => {
  await page.route(KILAVUZ('fen-bilimleri', 1), r => r.fulfill(json({ error: 'bilinmeyen_senaryo' }, 404)))
  await page.goto('/baski.html?ders=fen-bilimleri&sinav=1&senaryo=9')
  expect((await bekle(page)).hata).toBe('Kılavuz alınamadı (HTTP 404).')
})
