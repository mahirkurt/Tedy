import { test, expect } from '@playwright/test'
import { mock, FULL, LIVE, json } from './_audit-fixtures'

// Measured findings from a Playwright audit of the deployed bundle, pinned so
// they cannot come back. Each one was verified against the rendered page, not
// inferred from the source.

test('a component crash leaves the shell standing and says what happened', async ({ page }) => {
  // Any endpoint answering 200 with an unexpected shape used to take the
  // whole dashboard to a white screen: no chrome, no navigation, no words.
  // For a reader who cannot tell "broken" from "empty", a blank page is the
  // worst possible failure — and there was no route back.
  await page.route('**/api/assistant/stream', r => r.abort())
  for (const ep of Object.keys(LIVE)) {
    await page.route(`**/api/${ep}`, r => r.fulfill(json({})))
  }
  await page.goto('/isler')
  await page.waitForLoadState('networkidle')

  // The navigation survives, so there is somewhere to go. This is also the
  // white-screen check: a crash that unmounts the tree takes the navigation
  // with it, so this expect fails on a blank page — and because it retries,
  // it replaces the fixed wait that used to precede a one-shot body read.
  await expect(page.locator('nav').first().getByText('Bugün', { exact: true })).toBeVisible()
  await expect(page.getByText('Bu bölüm açılamadı', { exact: false })).toBeVisible()
})

test('the focus toggle label is readable on the header', async ({ page }) => {
  // The rule styling it targeted `.cds--toggle__label-text`; Carbon v11 emits
  // `.cds--toggle__text`. The selector matched nothing, so the one control
  // this product is named around rendered in near-black on the blue header.
  await mock(page, FULL)
  await page.goto('/')
  await page.waitForLoadState('networkidle')

  const ratio = await page.evaluate(() => {
    const el = document.querySelector('.cds--toggle__text') as HTMLElement
    if (!el) return null
    const lum = (c: number[]) => { const [r, g, b] = c.map(v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4) }); return 0.2126 * r + 0.7152 * g + 0.0722 * b }
    const p = (s: string) => (s.match(/\d+/g) || []).slice(0, 3).map(Number)
    const fg = p(getComputedStyle(el).color)
    // The header paints a gradient, so sample its darkest declared stop.
    const header = document.querySelector('.cds--header') as HTMLElement
    const grad = getComputedStyle(header).backgroundImage
    const stop = (grad.match(/rgb\(\d+,\s*\d+,\s*\d+\)/) || ['rgb(0,45,156)'])[0]
    const [a, b] = [lum(fg), lum(p(stop))].sort((x, y) => y - x)
    return (a + 0.05) / (b + 0.05)
  })
  expect(ratio, '.cds--toggle__text bulunamadı').not.toBeNull()
  expect(ratio!).toBeGreaterThanOrEqual(4.5)
})

const PAGES = ['/', '/isler', '/dersler', '/notlar', '/takvim', '/takimlar',
               '/ilerleme', '/duyurular', '/profil']

for (const path of PAGES) {
  test(`${path} has one page heading and no level skips`, async ({ page }) => {
    // Every page opened its heading outline with two headings belonging to a
    // closed modal, then jumped h2 → h4, and named no page at all.
    await mock(page, FULL)
    await page.goto(path)
    await page.waitForLoadState('networkidle')
    // The skip check passes on a page that has rendered only its shell — one
    // h1 and nothing after it to skip to. Wait until the surface itself is on
    // screen, in whichever shape it takes, before reading the outline once.
    await page.locator('.app-shell-content')
      .locator('.dashboard-card, .tedy-empty, .next-thing, .day-strip, .route-boundary')
      .first().waitFor()

    const hs = await page.evaluate(() =>
      [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')]
        .filter(h => h.getBoundingClientRect().height > 0)
        .map(h => ({ lvl: +h.tagName[1], text: h.textContent!.trim().slice(0, 40) })))

    expect(hs.filter(h => h.lvl === 1), 'tam olarak bir h1 olmalı').toHaveLength(1)
    expect(hs[0].lvl, `ilk başlık h1 değil: ${JSON.stringify(hs.slice(0, 2))}`).toBe(1)
    let prev = 0
    for (const h of hs) {
      expect(h.lvl, `h${prev} → h${h.lvl} atlaması: “${h.text}”`).toBeLessThanOrEqual(prev + 1)
      prev = h.lvl
    }
  })
}

test('the profile fields fit the phone', async ({ page }) => {
  // The two-column field grid did not collapse, so the second column ran off
  // the right edge and its values were clipped mid-word.
  await page.setViewportSize({ width: 390, height: 844 })
  await mock(page, FULL)
  await page.goto('/profil')
  await page.waitForLoadState('networkidle')
  // Both reads below are absences — no overflow, no clipped field — and an
  // unrendered profile has neither. Wait until there are fields to measure.
  await expect(page.locator('.student-profile__field').first()).toBeVisible()

  const overflow = await page.evaluate(() =>
    document.documentElement.scrollWidth - document.documentElement.clientWidth)
  expect(overflow, 'sayfa yatay taşıyor').toBeLessThanOrEqual(0)

  const clipped = await page.evaluate(() => {
    const vw = document.documentElement.clientWidth
    return [...document.querySelectorAll('.student-profile__field')]
      .filter(el => el.getBoundingClientRect().right > vw + 1).length
  })
  expect(clipped, 'ekran dışına taşan profil alanı').toBe(0)
})

test('the footer sits at the bottom, not halfway down an empty page', async ({ page }) => {
  await mock(page, LIVE)
  await page.goto('/')
  await page.waitForLoadState('networkidle')
  // The evaluate below dereferences the footer without a guard.
  await page.locator('.dashboard-footer, footer').first().waitFor()

  const gap = await page.evaluate(() => {
    const f = document.querySelector('.dashboard-footer, footer') as HTMLElement
    return window.innerHeight - f.getBoundingClientRect().bottom
  })
  expect(gap, `altbilginin altında ${Math.round(gap)}px ölü boşluk`).toBeLessThanOrEqual(8)
})

test('every header control is big enough to hit', async ({ page }) => {
  await mock(page, FULL)
  await page.goto('/')
  await page.waitForLoadState('networkidle')

  const small = await page.evaluate(() =>
    [...document.querySelectorAll('.cds--header button, .cds--header a')]
      .map(el => ({ r: el.getBoundingClientRect(), label: (el.textContent || el.getAttribute('aria-label') || '').trim().slice(0, 24) }))
      .filter(x => x.r.width > 1 && x.r.height > 1 && (x.r.height < 24 || x.r.width < 24))
      .map(x => `${x.label} ${Math.round(x.r.width)}x${Math.round(x.r.height)}`))
  expect(small, 'WCAG 2.2 asgari 24x24').toEqual([])
})
