import { test, expect, type Page } from '@playwright/test'
import { SCHEDULE, HOMEWORK, CALENDAR } from './_bugun-fixtures'
import { mock, LIVE } from './_audit-fixtures'

// B48 (yüzey tasarımları §2.4, talimatname S36): a load shorter than 400 ms
// shows nothing — a skeleton that blinks for a frame is noise. Past 400 ms the
// page's own shape in Carbon skeletons. The threshold lives in useApi
// (`iskelet`), so every page that draws a skeleton follows it.

/** Records whether a Carbon skeleton was ever in the DOM, from the first frame. */
async function iskeletGozcusu(page: Page) {
  await page.addInitScript(() => {
    const w = window as unknown as { __iskeletGoruldu: boolean }
    w.__iskeletGoruldu = false
    new MutationObserver(() => {
      if (document.querySelector('.cds--skeleton__text, .cds--skeleton__placeholder')) w.__iskeletGoruldu = true
    }).observe(document, { childList: true, subtree: true })
  })
}

const goruldu = (page: Page) =>
  page.evaluate(() => (window as unknown as { __iskeletGoruldu: boolean }).__iskeletGoruldu)

/** Bugün with /api/schedule answering `ms` late. The delay is registered after
 *  the fixtures, so it runs first and then falls back to their answer. */
async function gecikmeliAc(page: Page, ms: number) {
  await page.clock.setFixedTime(new Date('2026-09-24T16:40:00'))
  await mock(page, {
    ...LIVE, schedule: SCHEDULE, homework: HOMEWORK, calendar: CALENDAR,
    teams: { ogep: [] }, books: { books: [] },
  })
  await page.route('**/api/schedule', async r => {
    await new Promise(t => setTimeout(t, ms))
    await r.fallback()
  })
  await page.goto('/')
}

test('400 ms altındaki yükleme hiç iskelet göstermez', async ({ page }) => {
  await iskeletGozcusu(page)
  await gecikmeliAc(page, 100)
  await expect(page.locator('.next-thing')).toBeVisible()
  expect(await goruldu(page)).toBe(false)
})

test('uzun yüklemede 400 ms sonra sayfanın şeklinde iskelet görünür', async ({ page }) => {
  await iskeletGozcusu(page)
  await gecikmeliAc(page, 2500)
  await expect(page.locator('.today--yukleniyor[aria-busy="true"]')).toBeVisible({ timeout: 2000 })
  await expect(page.locator('.next-thing')).toBeVisible({ timeout: 10000 })
  expect(await goruldu(page)).toBe(true)
  await expect(page.locator('.today--yukleniyor')).toHaveCount(0)
})
