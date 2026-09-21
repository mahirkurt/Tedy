import { test, expect } from '@playwright/test'
import { mock, LIVE, FULL } from './_audit-fixtures'

// A grade is coloured by its band, and the colour has to survive the surface it
// lands on. Measured 2026-09-21 on the deployed build: an expanded Carbon row
// draws on layer-hover-01 (#e8e8e8), not layer-01, and there the whole -60
// family fell to 4.08-4.09 — while --status-warning, still bound to an
// indicator yellow, measured 1.37. The tokens' own comments said 5.02 and were
// not wrong; they were measured against a ground these numbers never touch.
// So this test measures in place rather than trusting a declaration.

// One row, four bands: gradeColor() splits at 85 / 70 / 50.
const GRADES = {
  semester: '1. Dönem',
  grades: [{
    Ders: 'Matematik',
    '1. Sınav': '95',            // success
    '2. Sınav': '75',            // info
    '3. Sınav': '65',            // warning — the 1.37 case
    'DİKP/Performans-1': '40',   // error
    'DİKP/Performans-2': '-',    // no band: inherits body colour
    'DİKP/Performans-3': '-',
  }],
}

/** Contrast of each matching element against the first opaque background above
 *  it — the ground the reader actually sees, not the one a token assumed. */
const OLC = (secici: string) => `(() => {
  const lum = c => { const [r,g,b] = c.map(v => { v /= 255
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4) })
    return 0.2126 * r + 0.7152 * g + 0.0722 * b }
  const ayir = s => (s.match(/\\d+/g) || []).slice(0, 3).map(Number)
  const zemin = el => { let n = el
    while (n && n !== document.documentElement) {
      const c = getComputedStyle(n).backgroundColor
      if (c && !/rgba\\(0, 0, 0, 0\\)|transparent/.test(c)) return c
      n = n.parentElement }
    return 'rgb(255, 255, 255)' }
  return [...document.querySelectorAll(${JSON.stringify(secici)})]
    .map(el => {
      const [a, b] = [lum(ayir(getComputedStyle(el).color)), lum(ayir(zemin(el)))]
        .sort((x, y) => y - x)
      return { metin: (el.textContent || '').trim(),
               oran: Math.round(((a + 0.05) / (b + 0.05)) * 100) / 100 }
    })
    .filter(o => o.metin && o.metin !== '-')
})()`

test.describe('not renkleri okunur kalır', () => {
  test.beforeEach(async ({ page }) => {
    await mock(page, { ...LIVE, grades: GRADES })
    await page.goto('/notlar')
    await page.locator('.grade-col-center').first().waitFor()
  })

  test('kapalı satırdaki her not bandı AA eşiğini geçer', async ({ page }) => {
    const olcumler = await page.evaluate(OLC('td.grade-col-center'))
    // Four bands, so four coloured numbers — if the fixture stops reaching the
    // table this count fails before the ratios can pass vacuously.
    expect(olcumler).toHaveLength(4)
    for (const o of olcumler) {
      expect(o.oran, `${o.metin} → ${o.oran}:1`).toBeGreaterThanOrEqual(4.5)
    }
  })

  test('açılmış satırdaki her not bandı AA eşiğini geçer', async ({ page }) => {
    // The darkest ground in the app: Carbon paints the expanded row on
    // layer-hover-01, which is where the -60 family was failing.
    await page.locator('button.cds--table-expand__button').first().click()
    await page.locator('.grade-detail__value').first().waitFor()

    const olcumler = await page.evaluate(OLC('.grade-detail__value'))
    expect(olcumler).toHaveLength(4)
    for (const o of olcumler) {
      expect(o.oran, `${o.metin} → ${o.oran}:1`).toBeGreaterThanOrEqual(4.5)
    }
  })

  test('50-69 bandı hâlâ diğerlerinden ayrı bir renk', async ({ page }) => {
    // Passing AA by turning every band the same dark colour would satisfy the
    // two tests above and destroy the signal. Four bands, four colours.
    const renkler = await page.evaluate(() =>
      [...document.querySelectorAll('td.grade-col-center')]
        .filter(el => (el.textContent || '').trim() !== '-')
        .map(el => getComputedStyle(el).color))
    expect(new Set(renkler).size).toBe(4)
  })
})

test('bölüm sayacı okunur', async ({ page }) => {
  // A count in a pill is 12px type, so it owes 4.5:1 like any other small
  // text. Measured 4.24 on 2026-09-21 — helper grey on a hand-written hex.
  await mock(page, { ...LIVE, ...FULL })
  await page.goto('/isler')
  await page.locator('.hw-section__count').first().waitFor()

  const olcumler = await page.evaluate(OLC('.hw-section__count'))
  expect(olcumler.length).toBeGreaterThan(0)
  for (const o of olcumler) {
    expect(o.oran, `sayaç "${o.metin}" → ${o.oran}:1`).toBeGreaterThanOrEqual(4.5)
  }
})
