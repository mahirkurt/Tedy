import { test, expect, type Page } from '@playwright/test'
import { SAYFALAR, sabitAc } from './_gorsel-yardim'

// 4K (2026-10-06): above 1920 px the root font size grows with the window (ted-theme.scss `html`),
// so a 3840 px screen shows the full-HD layout at twice the sharpness. Before, every page was a
// 960 px strip with 14 px text in the top-left quarter of the screen. This pins that everything
// scales together: the column, the nav and every icon — a leftover px size or an icon sized by its
// width="16" attribute would stay put while the text doubled.

test.use({ timezoneId: 'Europe/Istanbul', locale: 'tr-TR' })

async function olc(page: Page, yol: string, w: number, h: number) {
  await sabitAc(page, yol, w, h)
  return page.evaluate(() => {
    const kutu = (s: string) => { const e = document.querySelector(s); return e ? e.getBoundingClientRect().width : 0 }
    const ikonlar: number[] = []
    for (const svg of document.querySelectorAll('svg')) {
      const r = svg.getBoundingClientRect()
      if (r.width >= 4 && getComputedStyle(svg).visibility !== 'hidden') ikonlar.push(r.width)
    }
    return {
      kok: parseFloat(getComputedStyle(document.documentElement).fontSize),
      kolon: kutu('.app-shell-content'),
      nav: kutu('.cds--side-nav'),
      baslik: document.querySelector('.cds--header')?.getBoundingClientRect().height ?? 0,
      ikonlar,
      kaydirma: document.documentElement.scrollWidth - innerWidth,
    }
  })
}

for (const [ad, yol] of SAYFALAR) {
  test(`${ad} scales as one piece on a 4K screen`, async ({ page }) => {
    const hd = await olc(page, yol, 1920, 1080)
    const uhd = await olc(page, yol, 3840, 2160)
    expect(hd.kok).toBe(16)
    expect(uhd.kok).toBe(32)
    expect(uhd.kaydirma).toBeLessThanOrEqual(0)
    expect(uhd.kolon).toBeCloseTo(hd.kolon * 2, 0)
    expect(uhd.nav).toBeCloseTo(hd.nav * 2, 0)
    expect(uhd.baslik).toBeCloseTo(hd.baslik * 2, 0)
    expect(uhd.ikonlar.length).toBe(hd.ikonlar.length)
    const sabitKalan = hd.ikonlar.filter((g, i) => uhd.ikonlar[i] / g < 1.8 || uhd.ikonlar[i] / g > 2.2)
    expect(sabitKalan, 'icons that did not scale with the text').toEqual([])
  })
}

test('a 2560 px screen gets the in-between scale, no sideways scroll', async ({ page }) => {
  for (const [, yol] of SAYFALAR) {
    const m = await olc(page, yol, 2560, 1440)
    expect(m.kok).toBeCloseTo(2560 / 120, 1)
    expect(m.kaydirma).toBeLessThanOrEqual(0)
  }
})

test('up to 1920 px nothing changes', async ({ page }) => {
  for (const w of [1440, 1920]) {
    const m = await olc(page, '/', w, 900)
    expect(m.kok).toBe(16)
    expect(m.kolon).toBeLessThanOrEqual(960)
  }
})
