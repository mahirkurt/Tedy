import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { mock, FULL } from './_audit-fixtures'

// Pinned from a Playwright + axe audit of every surface at four widths
// (2026-09-25). What it found, each measured on the rendered page:
//   - the shell took its content's width, so every page had its own column:
//     Bugün 736px, Dersler 912px, İlerleme 290px, the cards of Profil 369px;
//   - on a phone every page began 56px lower than on a desktop (Carbon's
//     margin-top on .cds--content, which the desktop rule happened to reset);
//   - opening Asistan on a phone scrolled the window past its own title
//     (scrollIntoView moves every scrollable ancestor);
//   - past calendar events were 3.03:1 (opacity), the week table cut
//     "Matematik" to "Matema" on a phone and overflowed a tablet by 159px,
//     and its sideways scroll region was unreachable by keyboard.

const SAYFALAR = ['/', '/isler', '/asistan', '/dersler', '/kitaplar', '/notlar', '/takvim',
  '/takimlar', '/ilerleme', '/duyurular', '/profil', '/moduller', '/sinavlar']
const BOYUTLAR = [['masaüstü', 1440, 900], ['telefon', 390, 844]] as const

async function ac(page: import('@playwright/test').Page, yol: string, w: number, h: number) {
  await mock(page, FULL)
  await page.setViewportSize({ width: w, height: h })
  await page.goto(yol)
  await page.waitForLoadState('networkidle')
  await expect(page.locator('.app-shell-content')).toBeVisible()
}

for (const [boy, w, h] of BOYUTLAR) {
  for (const yol of SAYFALAR) {
    test(`${yol} on a ${boy}: axe finds nothing and nothing scrolls sideways`, async ({ page }) => {
      await ac(page, yol, w, h)
      const { violations } = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice'])
        .analyze()
      expect(violations.map(v =>
        `${v.impact} ${v.id}: ${v.nodes.slice(0, 3).map(n => n.target.join(' ')).join(' | ')}`)).toEqual([])
      const tasma = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
      expect(tasma, 'yatay taşma (px)').toBeLessThanOrEqual(0)
    })
  }
}

test('every page has the same column', async ({ page }) => {
  const genislik: Record<string, number> = {}
  for (const yol of SAYFALAR) {
    await ac(page, yol, 1440, 900)
    genislik[yol] = await page.locator('.app-shell-content').evaluate(el => Math.round(el.getBoundingClientRect().width))
  }
  // 960px: the shell's max-width, reached on every page, not only the wide ones.
  expect(new Set(Object.values(genislik)), JSON.stringify(genislik)).toEqual(new Set([960]))
})

test('a phone page begins under the header, as a desktop one does', async ({ page }) => {
  for (const [w, h] of [[1440, 900], [390, 844]]) {
    await ac(page, '/ilerleme', w, h)
    const ust = await page.locator('.app-shell-content .dashboard-card').first()
      .evaluate(el => Math.round(el.getBoundingClientRect().top))
    expect(ust, `${w}px`).toBeLessThanOrEqual(80)
  }
})

test('opening Asistan on a phone does not scroll the page', async ({ page }) => {
  await ac(page, '/asistan', 390, 844)
  await expect(page.getByRole('heading', { name: 'TEDY Asistan' })).toBeInViewport()
  expect(await page.evaluate(() => window.scrollY)).toBe(0)
})
