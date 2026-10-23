import { test, expect } from '@playwright/test'
import type { Frame, Page } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import { mkdirSync, mkdtempSync, readFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'

// Modül Tasarım Kanunu M5.6 (KB-5, 2026-10-23): the template draws every SVG text at ≥ 12 px on screen at
// every width — measured the law's way, `fontSize × getScreenCTM().a`, never the text box (the box is ~36 %
// taller than the drawn type). The fixture is the real compiler's `ornekler.gorsel_ornegi()`: every SVG the
// template draws (number line, bar and line chart, interactive number line, fraction bar, labelled diagram,
// three simulations) plus a raster figure with its caption (M3.7). Frame widths 288 and 358 are §6.1's
// post-KB-31 phone frames, opened directly; 320 (the edge case), 390, 1440, 2560 and 3840 (root 21.33 and
// 32) are screen widths in the dashboard's flow layout. On every segment no two SVG text boxes overlap, and
// on the "Çekirgenin Sıçrayışları" number line every point's value is a visible label (the review's
// decision for M5.6). TEDY_KB_GORUNTU=<dir> also writes the screenshots used for the eye check.

const PORT = Number(process.env.TEDY_E2E_PORT ?? 8286)
const ORIGIN = `http://127.0.0.1:${PORT}`
const REPO = fileURLToPath(new URL('../../..', import.meta.url))
const PYTHON = process.env.TEDY_E2E_PYTHON ?? join(REPO, '.venv/bin/python')
const GORUNTU = process.env.TEDY_KB_GORUNTU
const SPEC_CSP = "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; " +
  "font-src data:; media-src data:; connect-src 'none'; frame-ancestors " + ORIGIN + "; base-uri 'none'; form-action 'none'"
const json = (b: unknown) => ({ status: 200, contentType: 'application/json', body: JSON.stringify(b) })
const MODUL = `https://modul.tedy.online/m/fen5-su/v1?t=${'a'.repeat(64)}&e=1&u=${'b'.repeat(32)}`
const CARD = {
  slug: 'fen5-su', version: 1, title: 'Grafik, Sayı Doğrusu ve Figür', subject: 'Fen Bilimleri', gradeLevel: '5. Sınıf',
  mode: 'MODULE', outcomes: ['FB.5.4.1.1'], ted_link: null, created_at: '2026-10-23T10:00:00+00:00',
  gates: { pass: 15, warn: 1, fail: 0 },
}
const ACIKLAMA = {
  baslik: CARD.title, ders: 'Fen Bilimleri', sinif: '5. Sınıf', kazanimlar: ['FB.5.4.1.1'],
  kitap: { ad: 'Fen Bilimleri 5', sayfalar: '112-120' }, iddia_durumu: 'kayit_yok', iddialar: [],
  medya: { yapay_zeka: 0, ders_kitabi: 1, fotograf_arsivi: 0 },
}
const BASLIK = 'Görsel 1.30: İstiklal Yolu yürüyüşü'

let moduleHtml = ''
let segmentSayisi = 0

test.beforeAll(() => {
  const out = join(mkdtempSync(join(tmpdir(), 'tedy-svg-')), 'modul.html')
  execFileSync(PYTHON, ['-c', [
    'import sys', 'from src.mcp_server import derleme, ornekler',
    'd, v = ornekler.gorsel_ornegi()',
    `open(sys.argv[1], 'w').write(derleme.derle(d, v, ${JSON.stringify(ORIGIN)}))`,
    "print(len(d['segments']))",
  ].join('\n'), out], { cwd: REPO })
  moduleHtml = readFileSync(out, 'utf8')
  segmentSayisi = Number(execFileSync(PYTHON, ['-c',
    "from src.mcp_server import ornekler; print(len(ornekler.gorsel_ornegi()[0]['segments']))"],
  { cwd: REPO, encoding: 'utf8' }).trim())
})

async function serveModule(page: Page) {
  await page.route('**/api/modules', r => r.fulfill(json({ moduller: [CARD] })))
  await page.route('**/api/modules/agac', r => r.fulfill(json({ hazir: [CARD], dersler: [], kapsam: {}, hata: null })))
  await page.route('**/api/modules/fen5-su/v1/ticket', r => r.fulfill(json({ url: MODUL, exp: 1 })))
  await page.route('**/api/modules/fen5-su/v1/aciklama', r => r.fulfill(json(ACIKLAMA)))
  await page.route('**/api/modules/fen5-su/progress**', r => r.fulfill(json({ ok: true, state: { answers: [], done: [], xp: 0 } })))
  await page.route('https://modul.tedy.online/**', r => r.fulfill({
    status: 200, contentType: 'text/html; charset=utf-8', body: moduleHtml,
    headers: { 'content-security-policy': SPEC_CSP, 'x-content-type-options': 'nosniff', 'cache-control': 'no-store' },
  }))
}

type Olcum = { metin: string; px: number }

/** Uncaught errors and console errors (a ResizeObserver loop would show here) — the re-layout must be silent. */
function hatalariTopla(page: Page): string[] {
  const hatalar: string[] = []
  page.on('pageerror', e => hatalar.push(e.message))
  page.on('console', m => { if (m.type() === 'error') hatalar.push(m.text()) })
  return hatalar
}

/** Every visible SVG text in the document, as `fontSize × getScreenCTM().a` (Kanun M5.6's measure). */
async function svgMetinleri(f: Frame | Page): Promise<Olcum[]> {
  return f.evaluate(() => Array.from(document.querySelectorAll('svg text, svg tspan'))
    .filter(t => { const r = t.getBoundingClientRect(); return r.width > 0 && r.height > 0 })
    .map(t => {
      const m = (t as SVGGraphicsElement).getScreenCTM()
      return { metin: (t.textContent ?? '').trim(), px: parseFloat(getComputedStyle(t).fontSize) * (m ? m.a : 0) }
    }))
}

/** Pairs of SVG text boxes (leaf text or tspan) in the same SVG whose drawn boxes overlap. */
async function cakisanMetinler(f: Frame | Page): Promise<string[]> {
  return f.evaluate(() => {
    const out: string[] = []
    document.querySelectorAll('svg').forEach(svg => {
      const kutular = Array.from(svg.querySelectorAll('text, tspan'))
        .filter(t => t.tagName.toLowerCase() === 'tspan' || !t.querySelector('tspan'))
        .map(t => ({ m: (t.textContent ?? '').trim(), r: t.getBoundingClientRect() }))
        .filter(k => k.m && k.r.width > 0 && k.r.height > 0)
      for (let i = 0; i < kutular.length; i++) {
        for (let j = i + 1; j < kutular.length; j++) {
          const a = kutular[i].r, b = kutular[j].r
          const en = Math.min(a.right, b.right) - Math.max(a.left, b.left)
          const boy = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top)
          if (en > 0.5 && boy > 0.5) out.push(`${kutular[i].m} ↔ ${kutular[j].m} (${en.toFixed(1)} × ${boy.toFixed(1)})`)
        }
      }
    })
    return out
  })
}

const CEKIRGE = ['-5', '-3', '-1', '1', '3', '5', '7']

/** Walks every segment; on each, all SVG text is ≥ 12 px, no two text boxes overlap, and something was measured. */
async function herBolumuOlc(f: Frame | Page, ad: string) {
  const olculen: Record<string, number> = {}
  for (let i = 0; i < segmentSayisi; i++) {
    const bolum = await f.locator('#stage').getAttribute('data-seg')
    // The figure must have been re-laid out for this width before it is measured (resize path included).
    await expect.poll(async () => (await svgMetinleri(f)).filter(o => o.px < 12 - 1e-6), {
      message: `${ad}: ${bolum} bölümünde 12 px altında SVG metni`, timeout: 4000,
    }).toEqual([])
    expect(await cakisanMetinler(f), `${ad}: ${bolum} bölümünde üst üste binen SVG metni`).toEqual([])
    const tumu = await svgMetinleri(f)
    if ((await f.locator('#stage h2').textContent())?.includes('Çekirgenin')) {
      const gorunen = tumu.map(o => o.metin)
      expect(CEKIRGE.filter(d => !gorunen.includes(d)), `${ad}: nokta değeri okunmuyor`).toEqual([])
    }
    olculen[`${i}:${bolum}`] = tumu.length
    if (i < segmentSayisi - 1) await f.locator('#nextBtn').click()
  }
  // The number line, both charts, the fraction, the diagram and the simulations all drew text.
  expect(Object.values(olculen).filter(n => n > 0).length, JSON.stringify(olculen)).toBeGreaterThanOrEqual(8)
}

for (const genislik of [288, 358]) {
  test(`SVG text is at least 12 px in a ${genislik} px module frame`, async ({ page }) => {
    const hatalar = hatalariTopla(page)
    await serveModule(page)
    await page.setViewportSize({ width: genislik, height: 900 })
    await page.goto(MODUL)
    await expect(page.locator('#titleText')).toHaveText(CARD.title)
    expect(await page.evaluate(() => document.documentElement.clientWidth)).toBe(genislik)
    await herBolumuOlc(page, `çerçeve ${genislik}`)
    expect(hatalar).toEqual([])
  })
}

for (const genislik of [320, 390, 1440, 2560, 3840]) {
  test(`SVG text is at least 12 px in the dashboard at ${genislik} px`, async ({ page }) => {
    await serveModule(page)
    await page.setViewportSize({ width: genislik, height: 900 })
    await page.goto('/moduller/fen5-su/v1')
    await expect.poll(() => page.frame({ url: /modul\.tedy\.online/ }) !== null).toBe(true)
    const f = page.frame({ url: /modul\.tedy\.online/ })!
    await expect(f.locator('html')).toHaveAttribute('data-host-layout', 'flow')
    // 4K: the dashboard reports its root (21.33 / 32 px); the module re-lays out at the same rem width.
    if (genislik >= 2560) {
      await expect.poll(() => f.locator('html').evaluate(e => parseFloat(getComputedStyle(e).fontSize)))
        .toBeCloseTo(genislik / 120, 0)
    }
    await herBolumuOlc(f, `ekran ${genislik}`)
  })
}

test('a figure laid out wide re-lays its SVG out when the frame narrows', async ({ page }) => {
  // The module keeps its state: the reader's number on the interactive number line survives the resize.
  const hatalar = hatalariTopla(page)
  await serveModule(page)
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto(MODUL)
  for (let i = 0; i < 4; i++) await page.locator('#nextBtn').click()
  await expect(page.locator('#stage')).toHaveAttribute('data-seg', 'numberline')
  const kol = page.locator('.nl-handle')
  await kol.focus()
  await page.keyboard.press('ArrowRight')
  await expect(kol).toHaveAttribute('aria-valuenow', '8')
  await page.setViewportSize({ width: 300, height: 900 })
  await expect.poll(async () => (await svgMetinleri(page)).filter(o => o.px < 12 - 1e-6)).toEqual([])
  await expect(page.locator('.nl-handle')).toHaveAttribute('aria-valuenow', '8')
  await expect(page.locator('.nl-readout__val')).toHaveText('8')
  // The rebuilt handle still answers the keyboard from its new scale.
  await page.locator('.nl-handle').focus()
  await page.keyboard.press('ArrowRight')
  await expect(page.locator('.nl-handle')).toHaveAttribute('aria-valuenow', '9')
  // Back to wide: the figure follows again and nothing threw on the way (no ResizeObserver loop).
  await page.setViewportSize({ width: 1440, height: 900 })
  await expect.poll(() => page.locator('svg.viz[data-nl-handle]').getAttribute('viewBox')).toBe('0 0 480 110')
  await expect(page.locator('.nl-handle')).toHaveAttribute('aria-valuenow', '9')
  expect(hatalar).toEqual([])
})

test('the raster figure carries a visible caption and the reader-facing alt text', async ({ page }) => {
  await serveModule(page)
  await page.setViewportSize({ width: 390, height: 900 })
  await page.goto('/moduller/fen5-su/v1')
  await expect.poll(() => page.frame({ url: /modul\.tedy\.online/ }) !== null).toBe(true)
  const f = page.frame({ url: /modul\.tedy\.online/ })!
  await f.locator('#nextBtn').click()
  const figur = f.locator('figure.viz--varlik')
  await expect(figur.locator('img')).toHaveAttribute('alt', /Kağnıların yanında yürüyen halk/)
  await expect(figur.locator('figcaption')).toHaveText(BASLIK)
  await expect(figur.locator('figcaption')).toBeVisible()
  await expect(f.locator('.edupedia-audio')).toContainText('Seslendirme')
  const atif = f.locator('#edupedia-atif')
  await expect(atif).toContainText(`${BASLIK} — Görsel: T.C. Millî Eğitim Bakanlığı`)
  if (GORUNTU) {
    mkdirSync(GORUNTU, { recursive: true })
    await figur.scrollIntoViewIfNeeded()
    await page.screenshot({ path: join(GORUNTU, 'figur-390.png'), fullPage: true })
  }
})

if (GORUNTU) {
  for (const genislik of [390, 1440]) {
    test(`eye check screenshots at ${genislik} px`, async ({ page }) => {
      await serveModule(page)
      await page.setViewportSize({ width: genislik, height: 1000 })
      await page.goto('/moduller/fen5-su/v1')
      await expect.poll(() => page.frame({ url: /modul\.tedy\.online/ }) !== null).toBe(true)
      const f = page.frame({ url: /modul\.tedy\.online/ })!
      mkdirSync(GORUNTU, { recursive: true })
      const adlar = ['sayi-dogrusu', 'figur', 'cubuk-grafik', 'cizgi-grafik', 'etkilesimli-sayi-dogrusu', 'cekirge',
        'kesir', 'sema', 'olcek', 'sarkac', 'atis']
      for (let i = 0; i < adlar.length; i++) {
        await expect.poll(async () => (await svgMetinleri(f)).filter(o => o.px < 12 - 1e-6)).toEqual([])
        await f.locator('#stage').scrollIntoViewIfNeeded()
        await page.screenshot({ path: join(GORUNTU, `${adlar[i]}-${genislik}.png`), fullPage: true })
        if (i < adlar.length - 1) await f.locator('#nextBtn').click()
      }
    })
  }
}
