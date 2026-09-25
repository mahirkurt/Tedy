// Shared by the visual regression and ARIA snapshot specs (a spec file may
// not import another spec file).
import { expect } from '@playwright/test'
import type { Page } from '@playwright/test'
import { mock } from './_audit-fixtures'
import { GORSEL, SABIT_SAAT } from './_gorsel-fixtures'

export const SAYFALAR: [string, string][] = [
  ['bugun', '/'], ['isler', '/isler'], ['asistan', '/asistan'], ['dersler', '/dersler'],
  ['kitaplar', '/kitaplar'], ['notlar', '/notlar'], ['takvim', '/takvim'], ['takimlar', '/takimlar'],
  ['ilerleme', '/ilerleme'], ['duyurular', '/duyurular'], ['profil', '/profil'],
  ['moduller', '/moduller'], ['sinavlar', '/sinavlar'],
]

// "No request in flight for half a second", counted from the page's own
// request events. Not waitForLoadState('networkidle'): under the full suite's
// load Firefox sometimes never raised it — measured 2026-09-25, a page stuck
// 25 s with zero requests open, while the same page alone settled in 2.5 s.
async function agSakinlesir(page: Page, acik: Set<unknown>, sakin = 500, sinir = 30_000) {
  const bitis = Date.now() + sinir
  let bosSince = acik.size ? 0 : Date.now()
  while (Date.now() < bitis) {
    await page.waitForTimeout(50)
    if (acik.size) bosSince = 0
    else if (!bosSince) bosSince = Date.now()
    else if (Date.now() - bosSince >= sakin) return
  }
  throw new Error(`ağ ${sinir} ms içinde sakinleşmedi; açık istek: ${acik.size}`)
}

export async function sabitAc(page: Page, yol: string, w: number, h: number) {
  await page.clock.setFixedTime(new Date(SABIT_SAAT))
  await mock(page, GORSEL)
  await page.setViewportSize({ width: w, height: h })
  const acik = new Set<unknown>()
  page.on('request', r => { acik.add(r) })
  page.on('requestfinished', r => { acik.delete(r) })
  page.on('requestfailed', r => { acik.delete(r) })
  await page.goto(yol)
  await agSakinlesir(page, acik)
  await expect(page.locator('.app-shell-content')).toBeVisible()
  await page.evaluate(() => document.fonts.ready.then(() => undefined))
}
