import { test, expect } from '@playwright/test'
import type { Frame, Page } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import { mkdirSync, mkdtempSync, readFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'

// Modül Tasarım Kanunu M5.14 (KB-44, 2026-10-24): every icon-only button in the module frame is a Carbon ghost icon
// button — lg 48 px (3rem, so it follows the dashboard's root at 4K), icon 20 px, its name in a tooltip that opens on
// hover and on keyboard focus and closes with Escape (talimatname §4.3). The fixture is the real compiler's
// `ornekler.arac_ornegi()`: the two tools (sound, read aloud), the optional pacing disk's hide button, the concept
// map's "remove link" button, the per-text "Oku" buttons and the author's audio asset. Frames 272 and 342 (today's
// frames at screens 320 and 390) and 288 and 358 (§6.1's post-KB-31 phone frames) are opened directly; 320, 390,
// 1440 and 3840 (root 32) are screen widths in the dashboard's flow layout. The author's audio asset is drawn in a
// classed element inside the labelled Carbon layer, at least 48 px tall (M5.14's control: no classless `audio`).
// TEDY_KB_GORUNTU=<dir> also writes the screenshots used for the eye check.

const PORT = Number(process.env.TEDY_E2E_PORT ?? 8286)
const ORIGIN = `http://127.0.0.1:${PORT}`
const REPO = fileURLToPath(new URL('../../..', import.meta.url))
const PYTHON = process.env.TEDY_E2E_PYTHON ?? join(REPO, '.venv/bin/python')
const GORUNTU = process.env.TEDY_KB_GORUNTU
const SPEC_CSP = "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; " +
  "font-src data:; media-src data:; connect-src 'none'; frame-ancestors " + ORIGIN + "; base-uri 'none'; form-action 'none'"
const json = (b: unknown) => ({ status: 200, contentType: 'application/json', body: JSON.stringify(b) })
const MODUL = `https://modul.tedy.online/m/fen5-arac/v1?t=${'a'.repeat(64)}&e=1&u=${'b'.repeat(32)}`
const CARD = {
  slug: 'fen5-arac', version: 1, title: 'Araçlar ve Ses', subject: 'Fen Bilimleri', gradeLevel: '5. Sınıf',
  mode: 'MODULE', outcomes: ['FB.5.4.1.1'], ted_link: null, created_at: '2026-10-24T10:00:00+00:00',
  gates: { pass: 16, warn: 0, fail: 0 },
}
const ACIKLAMA = {
  baslik: CARD.title, ders: 'Fen Bilimleri', sinif: '5. Sınıf', kazanimlar: ['FB.5.4.1.1'],
  kitap: { ad: 'Fen Bilimleri 5', sayfalar: '112-120' }, iddia_durumu: 'kayit_yok', iddialar: [],
  medya: { yapay_zeka: 1, ders_kitabi: 0, fotograf_arsivi: 0 },
}

let moduleHtml = ''
let segmentSayisi = 0

test.beforeAll(() => {
  const out = join(mkdtempSync(join(tmpdir(), 'tedy-arac-')), 'modul.html')
  segmentSayisi = Number(execFileSync(PYTHON, ['-c', [
    'import sys', 'from src.mcp_server import derleme, ornekler',
    'd, v = ornekler.arac_ornegi()',
    `open(sys.argv[1], 'w').write(derleme.derle(d, v, ${JSON.stringify(ORIGIN)}))`,
    "print(len(d['segments']))",
  ].join('\n'), out], { cwd: REPO, encoding: 'utf8' }).trim())
  moduleHtml = readFileSync(out, 'utf8')
})

async function serveModule(page: Page) {
  await page.route('**/api/modules', r => r.fulfill(json({ moduller: [CARD] })))
  await page.route('**/api/modules/agac', r => r.fulfill(json({ hazir: [CARD], dersler: [], kapsam: {}, hata: null })))
  await page.route('**/api/modules/fen5-arac/v1/ticket', r => r.fulfill(json({ url: MODUL, exp: 1 })))
  await page.route('**/api/modules/fen5-arac/v1/aciklama', r => r.fulfill(json(ACIKLAMA)))
  await page.route('**/api/modules/fen5-arac/progress**', r => r.fulfill(json({ ok: true, state: { answers: [], done: [], xp: 0 } })))
  await page.route('https://modul.tedy.online/**', r => r.fulfill({
    status: 200, contentType: 'text/html; charset=utf-8', body: moduleHtml,
    headers: { 'content-security-policy': SPEC_CSP, 'x-content-type-options': 'nosniff', 'cache-control': 'no-store' },
  }))
}

type Dugme = { kim: string; en: number; boy: number; ad: string; ikon: number; kok: number }

/** Every visible icon-only button (no visible text of its own) in the document: its box, its accessible name,
 * its icon's size and the document's root size (3rem is the measure, so 4K's root 32 makes it 96 CSS px). */
async function ikonDugmeleri(f: Frame | Page): Promise<Dugme[]> {
  return f.evaluate(() => {
    const kok = parseFloat(getComputedStyle(document.documentElement).fontSize)
    return Array.from(document.querySelectorAll('button'))
      .filter(b => { const r = b.getBoundingClientRect(); return r.width > 0 && r.height > 0 })
      .filter(b => (b.textContent ?? '').trim() === '')
      .map(b => {
        const r = b.getBoundingClientRect()
        const etiketli = (b.getAttribute('aria-labelledby') ?? '').split(/\s+/).filter(Boolean)
          .map(id => document.getElementById(id)?.textContent ?? '').join(' ').trim()
        const ikon = b.querySelector('svg')?.getBoundingClientRect().width ?? 0
        return { kim: b.id || b.className, en: r.width, boy: r.height, ad: (b.getAttribute('aria-label') ?? '').trim() || etiketli, ikon, kok }
      })
  })
}

/** The icon buttons that break M5.14: under 3rem (and 48 px), unnamed, or an icon other than 20 px (1.25rem). */
function ihlaller(dugmeler: Dugme[]): string[] {
  return dugmeler.flatMap(d => {
    const olcu = Math.max(48, 3 * d.kok) - 0.5
    const out: string[] = []
    if (d.en < olcu || d.boy < olcu) out.push(`${d.kim}: ${d.en.toFixed(1)} × ${d.boy.toFixed(1)} < ${olcu + 0.5}`)
    if (!d.ad) out.push(`${d.kim}: adsız`)
    if (Math.abs(d.ikon - 1.25 * d.kok) > 0.5) out.push(`${d.kim}: ikon ${d.ikon.toFixed(1)} px (20 px = 1.25rem)`)
    return out
  })
}

/** The tooltip of an icon button: its text (the `::after` content) and its box, computed from the pseudo-element's
 * used size against the button (it hangs below, aligned to the button's inline end). */
async function ipucu(f: Frame | Page, secici: string) {
  return f.locator(secici).evaluate(b => {
    const cs = getComputedStyle(b, '::after')
    const r = b.getBoundingClientRect()
    const en = parseFloat(cs.width) + parseFloat(cs.paddingLeft) + parseFloat(cs.paddingRight)
    const icerik = cs.content && cs.content !== 'none' && cs.content !== 'normal' ? cs.content.replace(/^"|"$/g, '') : ''
    return {
      gorunur: cs.display !== 'none' && cs.visibility !== 'hidden' && icerik !== '',
      metin: icerik, ad: b.getAttribute('aria-label') ?? '',
      sol: r.right - en, sag: r.right, ust: r.bottom, genislik: document.documentElement.clientWidth,
      tasma: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    }
  })
}

/** Walks every segment with read-aloud on; on each, every icon button is ≥ 3rem, named and carries a 20 px icon,
 * and every visible "Oku" button is ≥ 3rem tall. On the concept map a link is made, so its remove button exists. */
async function herBolumuOlc(f: Frame | Page, ad: string) {
  await f.locator('#ttsBtn').click()
  await expect(f.locator('#ttsBtn')).toHaveAttribute('aria-pressed', 'true')
  const gorulen = new Set<string>()
  for (let i = 0; i < segmentSayisi; i++) {
    const bolum = await f.locator('#stage').getAttribute('data-seg')
    if (bolum === 'conceptMap') {
      // Keyboard, not the pointer: at the phone frames the map's nodes overlap (KB-6, M5.11), which is not this debt.
      const dugumler = f.locator('.cmap-node')
      await dugumler.nth(0).press('Enter')
      await dugumler.nth(1).press('Enter')
      await expect(f.locator('.cmap-edge__remove').first()).toBeVisible()
    }
    const dugmeler = await ikonDugmeleri(f)
    dugmeler.forEach(d => gorulen.add(String(d.kim).split(' ')[0]))
    expect(ihlaller(dugmeler), `${ad}: ${bolum} bölümünde M5.14'e uymayan ikon düğmesi`).toEqual([])
    const oku = await f.locator('.tts-oku:visible').evaluateAll(bs => bs.map(b => ({
      boy: b.getBoundingClientRect().height, kok: parseFloat(getComputedStyle(document.documentElement).fontSize),
    })))
    expect(oku.filter(o => o.boy < Math.max(48, 3 * o.kok) - 0.5), `${ad}: ${bolum} bölümünde 48 px altı "Oku" düğmesi`)
      .toEqual([])
    if (i < segmentSayisi - 1) await f.locator('#nextBtn').click()
  }
  // The two tools, the pacing disk's hide button and the concept map's remove button were all measured.
  for (const beklenen of ['soundBtn', 'ttsBtn', 'pacingDiskDismiss', 'cmap-edge__remove']) {
    expect([...gorulen], `${ad}: ${beklenen} ölçülmedi`).toContain(beklenen)
  }
}

/** The author's audio asset: no classless `audio`, inside the named Carbon layer, ≥ 3rem tall. */
async function sesOynaticisi(f: Frame | Page) {
  const sesler = await f.locator('audio').evaluateAll(as => as.map(a => ({
    sinif: a.getAttribute('class') ?? '', katman: !!a.closest('.edupedia-audio'), ad: a.getAttribute('aria-label') ?? '',
    gorunurAd: a.closest('.edupedia-audio')?.querySelector('.edupedia-audio__ad')?.textContent?.trim() ?? '',
    boy: a.getBoundingClientRect().height, kok: parseFloat(getComputedStyle(document.documentElement).fontSize),
  })))
  expect(sesler.length, 'ses oynatıcısı çizilmedi').toBeGreaterThan(0)
  for (const s of sesler) {
    expect(s.sinif.trim(), 'sınıfsız audio (M5.14)').not.toBe('')
    expect(s.katman && s.ad !== '' && s.gorunurAd === s.ad, JSON.stringify(s)).toBe(true)
    expect(s.boy).toBeGreaterThanOrEqual(Math.max(48, 3 * s.kok) - 0.5)
  }
}

/** Tooltip contract on the two tools: hover and keyboard focus show the button's own name below it, inside the
 * frame and without sideways scroll; Escape closes it while focus stays; it follows the name when the name changes. */
async function ipucuSozlesmesi(f: Frame | Page, page: Page, ad: string) {
  for (const secici of ['#soundBtn', '#ttsBtn']) {
    await expect.poll(async () => (await ipucu(f, secici)).gorunur, `${ad}: ${secici} ipucu kendiliğinden açık`).toBe(false)
    await f.locator(secici).hover()
    const acik = await ipucu(f, secici)
    expect(acik.gorunur, `${ad}: ${secici} üzerine gelince ipucu yok`).toBe(true)
    expect(acik.metin).toBe(acik.ad)
    expect(acik.sol, `${ad}: ${secici} ipucu çerçevenin solundan taşıyor`).toBeGreaterThanOrEqual(0)
    expect(acik.sag).toBeLessThanOrEqual(acik.genislik + 0.5)
    expect(acik.tasma, `${ad}: ${secici} ipucu yatay kaydırma açtı`).toBeLessThanOrEqual(0)
    await page.mouse.move(1, 1)
  }
  // Keyboard: focus from the sound button to the read-aloud button with Tab; Escape closes, focus stays put.
  await f.locator('#soundBtn').focus()
  await page.keyboard.press('Tab')
  await expect(f.locator('#ttsBtn')).toBeFocused()
  expect((await ipucu(f, '#ttsBtn')).gorunur, `${ad}: odakta ipucu yok`).toBe(true)
  await page.keyboard.press('Escape')
  await expect.poll(async () => (await ipucu(f, '#ttsBtn')).gorunur, `${ad}: Esc ipucunu kapatmadı`).toBe(false)
  await expect(f.locator('#ttsBtn')).toBeFocused()
  // The name changes with the state ("Sesi kapat" ↔ "Sesi aç"); the tooltip reads the live name.
  await f.locator('#soundBtn').focus()
  await page.keyboard.press('Enter')
  const sonra = await ipucu(f, '#soundBtn')
  expect(sonra.gorunur && sonra.metin === 'Sesi aç' && sonra.ad === 'Sesi aç', JSON.stringify(sonra)).toBe(true)
}

/** Opens the module directly as a frame of `genislik` (`dogrudan`) or in the dashboard's flow layout at screen `genislik`. */
async function ac(page: Page, genislik: number, dogrudan: boolean): Promise<Frame | Page> {
  await serveModule(page)
  await page.setViewportSize({ width: genislik, height: 900 })
  if (dogrudan) {
    await page.goto(MODUL)
    await expect(page.locator('#titleText')).toHaveText(CARD.title)
    expect(await page.evaluate(() => document.documentElement.clientWidth)).toBe(genislik)
    return page
  }
  await page.goto('/moduller/fen5-arac/v1')
  await expect.poll(() => page.frame({ url: /modul\.tedy\.online/ }) !== null).toBe(true)
  const f = page.frame({ url: /modul\.tedy\.online/ })!
  await expect(f.locator('html')).toHaveAttribute('data-host-layout', 'flow')
  if (genislik >= 2560) {
    await expect.poll(() => f.locator('html').evaluate(e => parseFloat(getComputedStyle(e).fontSize)))
      .toBeCloseTo(genislik / 120, 0)
  }
  return f
}

const GENISLIKLER: [number, boolean, string][] = [
  [272, true, 'çerçeve 272'], [288, true, 'çerçeve 288'], [342, true, 'çerçeve 342'], [358, true, 'çerçeve 358'],
  [320, false, 'ekran 320'], [390, false, 'ekran 390'], [1440, false, 'ekran 1440'], [3840, false, 'ekran 3840'],
]

for (const [genislik, dogrudan, ad] of GENISLIKLER) {
  test(`every icon button is 3rem, named, with a 20 px icon — ${ad}`, async ({ page }) => {
    await herBolumuOlc(await ac(page, genislik, dogrudan), ad)
  })
}

for (const [genislik, dogrudan, ad] of GENISLIKLER.filter(([g]) => [272, 342, 390, 1440, 3840].includes(g))) {
  test(`the tools name themselves in a tooltip on hover and focus, Escape closes it — ${ad}`, async ({ page }) => {
    await ipucuSozlesmesi(await ac(page, genislik, dogrudan), page, ad)
  })
}

for (const [genislik, dogrudan, ad] of GENISLIKLER.filter(([g]) => [272, 390, 3840].includes(g))) {
  test(`the author's audio is a classed, named, 3rem player in the Carbon layer — ${ad}`, async ({ page }) => {
    await sesOynaticisi(await ac(page, genislik, dogrudan))
  })
}

async function panodaAc(page: Page, genislik: number) {
  return ac(page, genislik, false)
}

test('the tools are exactly twice as large at 3840 as at 1920 (M5.8)', async ({ page }) => {
  const olc = async (genislik: number) => {
    const f = await panodaAc(page, genislik)
    return (await ikonDugmeleri(f)).filter(d => d.kim === 'soundBtn' || d.kim === 'ttsBtn').map(d => [d.en, d.boy, d.ikon])
  }
  const hd = await olc(1920)
  const k4 = await olc(3840)
  expect(hd.length).toBe(2)
  expect(k4.map(o => o.map(v => Math.round(v)))).toEqual(hd.map(o => o.map(v => Math.round(v * 2))))
})

if (GORUNTU) {
  for (const genislik of [390, 1440]) {
    test(`eye check screenshots of the toolbar at ${genislik} px`, async ({ page }) => {
      const f = await panodaAc(page, genislik)
      mkdirSync(GORUNTU, { recursive: true })
      const arac = f.locator('.topbar')
      await arac.scrollIntoViewIfNeeded()
      await page.screenshot({ path: join(GORUNTU, `arac-cubugu-${genislik}.png`) })
      await f.locator('#ttsBtn').hover()
      await page.screenshot({ path: join(GORUNTU, `arac-ipucu-${genislik}.png`) })
      await page.mouse.move(1, 1)
      await f.locator('#ttsBtn').click()
      await f.locator('.edupedia-audio').scrollIntoViewIfNeeded()
      await page.screenshot({ path: join(GORUNTU, `ses-ve-oku-${genislik}.png`), fullPage: true })
    })
  }
}
