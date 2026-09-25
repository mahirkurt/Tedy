import { test, expect } from '@playwright/test'
import { SAYFALAR, sabitAc } from './_gorsel-yardim'

// The operating system's display preferences, which the dashboard used to
// ignore outside Tedy Books (measured 2026-09-25):
//   - "reduce motion": every card still faded in, the timeline staggered and
//     popovers slid — the design system allows one entrance, off under this
//     preference (color-system.md §2.5);
//   - Windows high contrast (forced colors): cards separated from the page by
//     shadow and fill alone, both of which forced colors removes, so every
//     card melted into the page.

test.use({ timezoneId: 'Europe/Istanbul', locale: 'tr-TR' })

for (const [ad, yol] of SAYFALAR) {
  test(`${ad}: nothing animates when the reader asked for less motion`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' })
    await sabitAc(page, yol, 1440, 900)
    const hareketli = await page.evaluate(() => {
      const sn = (v: string) => Math.max(...v.split(',').map(x => parseFloat(x) * (x.trim().endsWith('ms') ? 0.001 : 1)))
      return Array.from(document.querySelectorAll('body *')).flatMap(el => {
        const cs = getComputedStyle(el)
        const out: string[] = []
        if (cs.animationName !== 'none' && sn(cs.animationDuration) > 0.01) out.push(`animation ${cs.animationName} ${cs.animationDuration}`)
        if (sn(cs.transitionDuration) > 0.01) out.push(`transition ${cs.transitionProperty} ${cs.transitionDuration}`)
        return out.map(o => `${el.tagName.toLowerCase()}.${String(el.className).split(' ')[0]}: ${o}`)
      })
    })
    expect([...new Set(hareketli)]).toEqual([])
  })
}

test('cards keep an edge in Windows high contrast', async ({ page }) => {
  await page.emulateMedia({ forcedColors: 'active' })
  for (const yol of ['/', '/isler', '/dersler']) {
    await sabitAc(page, yol, 1440, 900)
    const kenarsiz = await page.evaluate(() =>
      Array.from(document.querySelectorAll('.dashboard-card, .next-thing:not(.next-thing--quiet), .today-now, .cds--tile, .today-tl__card'))
        .filter(el => {
          const cs = getComputedStyle(el)
          return ['Top', 'Right', 'Bottom', 'Left'].every(k =>
            cs.getPropertyValue(`border-${k.toLowerCase()}-style`) === 'none' || parseFloat(cs.getPropertyValue(`border-${k.toLowerCase()}-width`)) === 0)
        })
        .map(el => String(el.className).split(' ').slice(0, 2).join('.')))
    expect(kenarsiz, yol).toEqual([])
  }
})

test('Bugün in Windows high contrast looks as it did', async ({ page }) => {
  await page.emulateMedia({ forcedColors: 'active' })
  await sabitAc(page, '/', 1440, 900)
  await expect(page).toHaveScreenshot('bugun-yuksek-kontrast.png', { fullPage: true, animations: 'disabled', maxDiffPixelRatio: 0.002 })
})
