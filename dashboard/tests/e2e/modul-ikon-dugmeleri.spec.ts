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

/** The tooltip of an icon button. Second review round: the tooltip is one separate `role="tooltip"` element at the end
 * of the body (`#aracIpucu`), outside every button, tied to its owner with `aria-describedby` — a click on it or on its
 * bridge can no longer activate the button. Its box is the element's own (border-box); it is "open for `secici`" when it
 * is shown and the button points at it. */
async function ipucu(f: Frame | Page, secici: string) {
  return f.locator(secici).first().evaluate(b => {
    const t = document.getElementById('aracIpucu')
    const r = b.getBoundingClientRect()
    const cs = t ? getComputedStyle(t) : null
    const k = t ? t.getBoundingClientRect() : new DOMRect()
    const bagli = (b.getAttribute('aria-describedby') ?? '').split(/\s+/).includes('aracIpucu')
    return {
      gorunur: !!t && !!cs && !t.hidden && cs.display !== 'none' && cs.visibility === 'visible' && parseFloat(cs.opacity) > 0
        && bagli,
      metin: (t?.textContent ?? '').trim(), ad: b.getAttribute('aria-label') ?? '', boxSizing: cs?.boxSizing ?? '',
      rol: t?.getAttribute('role') ?? '', dugmeninIcinde: !!t && b.contains(t),
      sol: k.left, sag: k.right, ust: k.top, alt: k.bottom, merkezX: k.left + k.width / 2, merkezY: k.top + k.height / 2,
      dugme: { x: r.left, y: r.top, w: r.width, h: r.height },
      genislik: document.documentElement.clientWidth,
      tasma: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    }
  })
}

/** Keyboard focus on `secici` (focus, then Shift+Tab and Tab back, so the focus is :focus-visible). */
async function klavyeyleOdakla(f: Frame | Page, page: Page, secici: string) {
  await f.locator(secici).first().focus()
  await page.keyboard.press('Shift+Tab')
  await page.keyboard.press('Tab')
  await expect(f.locator(secici).first()).toBeFocused()
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

/** Tooltip contract on the two tools (talimatname §4.3, WCAG 1.4.13; review fix round): opens 100 ms after the pointer
 * arrives and closes 100 ms after it leaves (@carbon/react IconButton enterDelayMs / leaveDelayMs); the pointer can move
 * down onto the tooltip and it stays open; activating the button closes it (Carbon closeOnActivation) and it stays
 * closed until the pointer leaves; keyboard focus opens it, Escape closes it and focus stays; it reads the live name. */
async function ipucuSozlesmesi(f: Frame | Page, page: Page, ad: string) {
  // Delay, measured inside the page so the timing is deterministic: a check timer due before the 100 ms opening timer
  // runs before it, whatever the load.
  const gecikme = await f.locator('#ttsBtn').evaluate(async b => {
    const acik = () => {
      const t = document.getElementById('aracIpucu')
      return !!t && !t.hidden && t.classList.contains('arac-ipucu--acik')
        && (b.getAttribute('aria-describedby') ?? '').split(/\s+/).includes('aracIpucu')
    }
    b.dispatchEvent(new MouseEvent('mouseover', { bubbles: true, relatedTarget: document.body }))
    const hemen = acik()
    const ms60 = await new Promise<boolean>(r => setTimeout(() => r(acik()), 60))
    const ms160 = await new Promise<boolean>(r => setTimeout(() => r(acik()), 100))
    b.dispatchEvent(new MouseEvent('mouseout', { bubbles: true, relatedTarget: document.body }))
    const cikisHemen = acik()
    const cikis160 = await new Promise<boolean>(r => setTimeout(() => r(acik()), 160))
    return { hemen, ms60, ms160, cikisHemen, cikis160 }
  })
  expect(gecikme, `${ad}: ipucu 100 ms gecikmeyle açılıp kapanmıyor`).toEqual(
    { hemen: false, ms60: false, ms160: true, cikisHemen: true, cikis160: false })

  for (const secici of ['#soundBtn', '#ttsBtn']) {
    await expect.poll(async () => (await ipucu(f, secici)).gorunur, `${ad}: ${secici} ipucu kendiliğinden açık`).toBe(false)
    await f.locator(secici).hover()
    await expect.poll(async () => (await ipucu(f, secici)).gorunur, `${ad}: ${secici} üzerine gelince ipucu yok`).toBe(true)
    const acik = await ipucu(f, secici)
    expect(acik.metin).toBe(acik.ad)
    expect(acik.boxSizing).toBe('border-box')
    expect(acik.sol, `${ad}: ${secici} ipucu çerçevenin solundan taşıyor`).toBeGreaterThanOrEqual(0)
    expect(acik.sag, `${ad}: ${secici} ipucu çerçevenin sağından taşıyor`).toBeLessThanOrEqual(acik.genislik + 0.5)
    expect(acik.tasma, `${ad}: ${secici} ipucu yatay kaydırma açtı`).toBeLessThanOrEqual(0)
    await page.mouse.move(1, 1)
    await expect.poll(async () => (await ipucu(f, secici)).gorunur, `${ad}: ${secici} ipucu kapanmadı`).toBe(false)
  }

  // Hoverable: the pointer walks from the button's centre down onto the tooltip's centre in 2 px steps; the tooltip
  // never closes on the way, and stays open while the pointer rests on it. The frame's offset is added for the dashboard.
  // Coordinates are frame-relative (getBoundingClientRect); in the dashboard the iframe's own box is added.
  const ofset = 'frameElement' in f ? (await (await (f as Frame).frameElement()).boundingBox())! : { x: 0, y: 0 }
  const once = await ipucu(f, '#ttsBtn')
  const kutu = once.dugme
  const x = kutu.x + kutu.w / 2
  await page.mouse.move(ofset.x + x, ofset.y + kutu.y + kutu.h / 2)
  await expect.poll(async () => (await ipucu(f, '#ttsBtn')).gorunur).toBe(true)
  const hedef = await ipucu(f, '#ttsBtn')
  const kapananlar: number[] = []
  for (let y = kutu.y + kutu.h / 2; y <= hedef.merkezY; y += 2) {
    await page.mouse.move(ofset.x + Math.min(Math.max(x, hedef.sol + 4), hedef.sag - 4), ofset.y + y)
    if (!(await ipucu(f, '#ttsBtn')).gorunur) kapananlar.push(Math.round(y - kutu.y - kutu.h))
  }
  await page.waitForTimeout(300)
  expect(kapananlar, `${ad}: işaretçi ipucuna inerken ipucu kapandı (düğmenin altından px)`).toEqual([])
  expect((await ipucu(f, '#ttsBtn')).gorunur, `${ad}: işaretçi ipucunun üstündeyken ipucu kapandı`).toBe(true)
  await page.mouse.move(1, 1)
  await expect.poll(async () => (await ipucu(f, '#ttsBtn')).gorunur).toBe(false)

  // Activation closes it and it stays closed while the pointer rests; leaving and returning shows the new name.
  await f.locator('#soundBtn').hover()
  await expect.poll(async () => (await ipucu(f, '#soundBtn')).gorunur).toBe(true)
  await f.locator('#soundBtn').click()
  await expect.poll(async () => (await ipucu(f, '#soundBtn')).gorunur, `${ad}: etkinleştirme ipucunu kapatmadı`).toBe(false)
  await page.waitForTimeout(250)
  expect((await ipucu(f, '#soundBtn')).gorunur, `${ad}: etkinleştirmeden sonra ipucu yeniden açıldı`).toBe(false)
  await page.mouse.move(1, 1)
  await f.locator('#soundBtn').hover()
  await expect.poll(async () => (await ipucu(f, '#soundBtn')).gorunur).toBe(true)
  const sonra = await ipucu(f, '#soundBtn')
  expect(sonra.metin === 'Sesi aç' && sonra.ad === 'Sesi aç', JSON.stringify(sonra)).toBe(true)
  await page.mouse.move(1, 1)

  // Keyboard: Tab from the sound button opens the read-aloud tooltip; Escape closes it, focus stays put.
  await klavyeyleOdakla(f, page, '#soundBtn')
  await page.keyboard.press('Tab')
  await expect(f.locator('#ttsBtn')).toBeFocused()
  await expect.poll(async () => (await ipucu(f, '#ttsBtn')).gorunur, `${ad}: odakta ipucu yok`).toBe(true)
  await page.keyboard.press('Escape')
  await expect.poll(async () => (await ipucu(f, '#ttsBtn')).gorunur, `${ad}: Esc ipucunu kapatmadı`).toBe(false)
  await expect(f.locator('#ttsBtn')).toBeFocused()
}

/** Every icon button's tooltip opened by keyboard stays inside the frame (left ≥ 0, right ≤ width), no sideways
 * scroll: the two tools, the pacing disk's hide button and — after a link is made — the concept map's remove button. */
async function ipucuKutulari(f: Frame | Page, page: Page, ad: string) {
  const olc = async (secici: string) => {
    await klavyeyleOdakla(f, page, secici)
    await expect.poll(async () => (await ipucu(f, secici)).gorunur, `${ad}: ${secici} odakta ipucu yok`).toBe(true)
    const k = await ipucu(f, secici)
    expect({ secici, sol: k.sol >= -0.5, sag: k.sag <= k.genislik + 0.5, tasma: k.tasma <= 0 },
      `${ad}: ${secici} ipucu çerçeveden taşıyor (sol ${k.sol.toFixed(1)}, sağ ${k.sag.toFixed(1)}, çerçeve ${k.genislik})`)
      .toEqual({ secici, sol: true, sag: true, tasma: true })
    expect(k.boxSizing).toBe('border-box')
    expect(k.metin).toBe(k.ad)
    expect(k.rol).toBe('tooltip')
    expect(k.dugmeninIcinde, `${ad}: ${secici} ipucu düğmenin içinde (tıklama düğmeye gider)`).toBe(false)
    await page.keyboard.press('Escape')
  }
  for (const secici of ['#pacingDiskDismiss', '#soundBtn', '#ttsBtn']) await olc(secici)
  for (let i = 0; i < segmentSayisi - 1; i++) await f.locator('#nextBtn').click()
  await expect(f.locator('#stage')).toHaveAttribute('data-seg', 'conceptMap')
  const dugumler = f.locator('.cmap-node')
  await dugumler.nth(0).press('Enter')
  await dugumler.nth(1).press('Enter')
  await olc('.cmap-edge__remove')
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

for (const genislik of [272, 320, 342, 390]) {
  for (const akis of [false, true]) {
    const ad = `${akis ? 'akış benzetimi' : 'çerçeve'} ${genislik}`
    test(`every icon button's tooltip stays inside the frame — ${ad}`, async ({ page }) => {
      const f = await ac(page, genislik, true)
      // Flow simulation (the review's probe): the dashboard's layout attribute on a frame of that width.
      if (akis) await page.evaluate(() => document.documentElement.setAttribute('data-host-layout', 'flow'))
      await ipucuKutulari(f, page, ad)
    })
  }
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

// Second review round (Önemli): the open tooltip and its bridge took hits as their own button, so a click on the
// concept map's second "remove" button, under the first one's tooltip, removed the first link (measured at 342, 390,
// 1024), and a click on the content under the sound tooltip toggled the sound. A click there must never activate the
// tooltip's button.
for (const genislik of [342, 390, 1024]) {
  test(`a click under the first remove button's open tooltip leaves the first link — frame ${genislik}`, async ({ page }) => {
    const f = await ac(page, genislik, true)
    for (let i = 0; i < segmentSayisi - 1; i++) await f.locator('#nextBtn').click()
    const dugumler = f.locator('.cmap-node')
    for (const i of [0, 1, 2, 3]) await dugumler.nth(i).press('Enter')
    const baglantilar = () => f.locator('.cmap-edge__text').allTextContents()
    const once = await baglantilar()
    expect(once.length).toBe(2)
    const kaldir = f.locator('.cmap-edge__remove')
    await kaldir.nth(1).scrollIntoViewIfNeeded()
    const r1 = (await kaldir.nth(0).boundingBox())!, r2 = (await kaldir.nth(1).boundingBox())!
    const x = r1.x + r1.width / 2
    // A fixed wait rather than a poll on the tooltip element, so the same steps also run against the earlier
    // pseudo-element tooltip (the review's reproduction) and fail there for the right reason.
    await page.mouse.move(x, r1.y + r1.height / 2)
    await page.waitForTimeout(250)
    for (let y = r1.y + r1.height / 2; y <= r2.y + 8; y += 2) await page.mouse.move(x, y)
    await page.mouse.down()
    await page.mouse.up()
    await page.waitForTimeout(250)
    const sonra = await baglantilar()
    expect(sonra, `çerçeve ${genislik}: ipucunun altına tıklama 1. bağlantıyı sildi`).toContain(once[0])
  })
}

test('a click on the content under the open sound tooltip leaves the sound as it was', async ({ page }) => {
  const f = await ac(page, 390, true)
  await expect(f.locator('#soundBtn')).toHaveAttribute('aria-label', 'Sesi kapat')
  const d = (await f.locator('#soundBtn').boundingBox())!
  await page.mouse.move(d.x + d.width / 2, d.y + d.height / 2)
  await page.waitForTimeout(250)
  // Down through the bridge onto the tooltip (over the content below the button: 8 px gap + half its height), click.
  const hedefY = d.y + d.height + 8 + 11
  for (let y = d.y + d.height / 2; y <= hedefY; y += 2) await page.mouse.move(d.x + d.width / 2, y)
  await page.mouse.down()
  await page.mouse.up()
  await page.waitForTimeout(250)
  await expect(f.locator('#soundBtn')).toHaveAttribute('aria-label', 'Sesi kapat')
  // Lower, on the content under where the tooltip ends: still no toggle.
  await page.mouse.click(d.x + d.width / 2, hedefY + 16)
  await page.waitForTimeout(150)
  await expect(f.locator('#soundBtn')).toHaveAttribute('aria-label', 'Sesi kapat')
})

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
      await expect.poll(async () => (await ipucu(f, '#ttsBtn')).gorunur).toBe(true)  // 100 ms açılış gecikmesi
      await page.screenshot({ path: join(GORUNTU, `arac-ipucu-${genislik}.png`) })
      await page.mouse.move(1, 1)
      await f.locator('#ttsBtn').click()
      await f.locator('.edupedia-audio').scrollIntoViewIfNeeded()
      await page.screenshot({ path: join(GORUNTU, `ses-ve-oku-${genislik}.png`), fullPage: true })
    })
  }
}

// Review fix round (Küçük 12): a hotspot region's accessible name used to be the answer itself (`spots[].label`), so a
// screen reader announced "Çekirdek, düğme" right under the question "Bul ve tıkla: Çekirdek". WCAG 1.1.1's test
// exception asks for a descriptive identification, not the answer: "Bölge n / N". Second round: n is the region's
// spatial order (left to right, then top to bottom, by its box centre), not its DOM order — otherwise "question k =
// region k" would leak the answer — and a found region keeps its found state (name + aria-disabled) in later questions.
test.describe('hotspot regions', () => {
  let hotspotHtml = ''
  test.beforeAll(() => {
    const out = join(mkdtempSync(join(tmpdir(), 'tedy-hotspot-')), 'modul.html')
    execFileSync(PYTHON, ['-c', [
      'import sys', 'from src.mcp_server import derleme, ornekler',
      "d = ornekler.ornek('MODULE')",
      // DOM order c, a, b; spatial order (left to right) a, b, c; question order b, c, a.
      "svg = ('<svg viewBox=\"0 0 480 200\" role=\"img\" aria-label=\"Üç kutu\">'",
      "       '<g data-spot=\"c\"><rect x=\"360\" y=\"60\" width=\"80\" height=\"80\" fill=\"var(--viz-2)\"/></g>'",
      "       '<g data-spot=\"a\"><rect x=\"40\" y=\"60\" width=\"80\" height=\"80\" fill=\"var(--viz-2)\"/></g>'",
      "       '<g data-spot=\"b\"><rect x=\"200\" y=\"60\" width=\"80\" height=\"80\" fill=\"var(--viz-2)\"/></g></svg>')",
      "d['segments'] = [{'type': 'hotspot', 'id': 'h1', 'title': 'Kutuları Bul', 'svg': svg, 'spots': [",
      "    {'id': 'b', 'label': 'Orta kutu', 'info': 'Ortada.'}, {'id': 'c', 'label': 'Sağ kutu', 'info': 'Sağda.'},",
      "    {'id': 'a', 'label': 'Sol kutu', 'info': 'Solda.'}]}]",
      "d['curriculum']['outcomes'][0]['mappedTo'] = ['h1']",
      `open(sys.argv[1], 'w').write(derleme.derle(d, {}, ${JSON.stringify(ORIGIN)}))`,
    ].join('\n'), out], { cwd: REPO })
    hotspotHtml = readFileSync(out, 'utf8')
  })

  test('region names follow space, never the answer, and a found region stays found', async ({ page }) => {
    await serveModule(page)
    await page.route('https://modul.tedy.online/**', r => r.fulfill({
      status: 200, contentType: 'text/html; charset=utf-8', body: hotspotHtml,
      headers: { 'content-security-policy': SPEC_CSP, 'x-content-type-options': 'nosniff', 'cache-control': 'no-store' },
    }))
    await page.setViewportSize({ width: 390, height: 900 })
    await page.goto(MODUL)
    const ad = (id: string) => page.locator(`[data-spot="${id}"]`)
    await expect(page.locator('.q-stem')).toContainText('Orta kutu')
    // Spatial numbering: a (left) 1, b (middle) 2, c (right) 3 — although the DOM holds c, a, b.
    await expect(ad('a')).toHaveAttribute('aria-label', 'Bölge 1 / 3')
    await expect(ad('b')).toHaveAttribute('aria-label', 'Bölge 2 / 3')
    await expect(ad('c')).toHaveAttribute('aria-label', 'Bölge 3 / 3')
    // A wrong region keeps its neutral name; the right one takes the answer and is no longer an open target.
    await ad('a').press('Enter')
    await expect(page.locator('#hfb')).toContainText('Burası değil')
    await expect(ad('a')).toHaveAttribute('aria-label', 'Bölge 1 / 3')
    await ad('b').press('Enter')
    await expect(page.locator('#hfb')).toContainText('Buldun')
    await expect(ad('b')).toHaveAttribute('aria-label', 'Bölge 2 / 3: Orta kutu, bulundu')
    await expect(ad('b')).toHaveAttribute('aria-disabled', 'true')
    // Next question: the found region is still marked found; the others are neutral and open.
    await page.getByRole('button', { name: /Sonraki/ }).click()
    await expect(page.locator('.q-stem')).toContainText('Sağ kutu')
    await expect(ad('b')).toHaveAttribute('aria-label', 'Bölge 2 / 3: Orta kutu, bulundu')
    await expect(ad('b')).toHaveAttribute('aria-disabled', 'true')
    await expect(ad('a')).toHaveAttribute('aria-label', 'Bölge 1 / 3')
    await expect(ad('c')).not.toHaveAttribute('aria-disabled', 'true')
  })
})
