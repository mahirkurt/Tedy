import { test, expect } from '@playwright/test'
import type { Frame, Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { execFileSync } from 'node:child_process'
import { createRequire } from 'node:module'
import { mkdtempSync, readFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'

// Modül Tasarım Kanunu M5.14 (KB-49, 2026-10-24): the author's audio asset is played by the template's own player,
// composed of Carbon components because Carbon has no audio player: a ghost IconButton to play/pause (48 px, icon
// 20 px, named "Oynat"/"Duraklat"), Carbon Slider anatomy for the position (role=slider, aria-valuemin/max/now and a
// spoken valuetext; ← → ±5 s, PageUp/PageDown ±10 %, Home/End; a 48 px tall hit area), elapsed/total time in
// Plex Mono tabular figures, a ghost IconButton to mute, a loading state and an InlineNotification-styled error
// ("Ses dosyası açılamadı", role=alert). The browser's own <audio controls> is gone — its 32 px controls were KB-49.
// The fixture is the real compiler's `ornekler.arac_ornegi()`: a 20-second silent WAV on the first section and a
// broken file on the second. Measured at frame 390 directly and in the dashboard at 390, 1440 and 3840 (root 32).
// Review round 1: the two live regions (role=status loading, role=alert error) are always in the document, rendered
// and empty; a state writes its text into them and its end empties them.

const PORT = Number(process.env.TEDY_E2E_PORT ?? 8286)
const ORIGIN = `http://127.0.0.1:${PORT}`
const REPO = fileURLToPath(new URL('../../..', import.meta.url))
const PYTHON = process.env.TEDY_E2E_PYTHON ?? join(REPO, '.venv/bin/python')
const ACE = createRequire(import.meta.url).resolve('accessibility-checker-engine/ace.js')
const SPEC_CSP = "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; " +
  "font-src data:; media-src data:; connect-src 'none'; frame-ancestors " + ORIGIN + "; base-uri 'none'; form-action 'none'"
const json = (b: unknown) => ({ status: 200, contentType: 'application/json', body: JSON.stringify(b) })
const MODUL = `https://modul.tedy.online/m/fen5-ses/v1?t=${'a'.repeat(64)}&e=1&u=${'b'.repeat(32)}`
const CARD = {
  slug: 'fen5-ses', version: 1, title: 'Araçlar ve Ses', subject: 'Fen Bilimleri', gradeLevel: '5. Sınıf',
  mode: 'MODULE', outcomes: ['FB.5.4.1.1'], ted_link: null, created_at: '2026-10-24T10:00:00+00:00',
  gates: { pass: 16, warn: 0, fail: 0 },
}
const ACIKLAMA = {
  baslik: CARD.title, ders: 'Fen Bilimleri', sinif: '5. Sınıf', kazanimlar: ['FB.5.4.1.1'],
  kitap: { ad: 'Fen Bilimleri 5', sayfalar: '112-120' }, iddia_durumu: 'kayit_yok', iddialar: [],
  medya: { yapay_zeka: 1, ders_kitabi: 0, fotograf_arsivi: 0 },
}

let moduleHtml = ''

test.beforeAll(() => {
  const out = join(mkdtempSync(join(tmpdir(), 'tedy-ses-')), 'modul.html')
  execFileSync(PYTHON, ['-c', [
    'import sys', 'from src.mcp_server import derleme, ornekler',
    'd, v = ornekler.arac_ornegi()',
    `open(sys.argv[1], 'w').write(derleme.derle(d, v, ${JSON.stringify(ORIGIN)}))`,
  ].join('\n'), out], { cwd: REPO })
  moduleHtml = readFileSync(out, 'utf8')
})

async function ac(page: Page, genislik: number, dogrudan: boolean): Promise<Frame | Page> {
  await page.route('**/api/modules', r => r.fulfill(json({ moduller: [CARD] })))
  await page.route('**/api/modules/agac', r => r.fulfill(json({ hazir: [CARD], dersler: [], kapsam: {}, hata: null })))
  await page.route('**/api/modules/fen5-ses/v1/ticket', r => r.fulfill(json({ url: MODUL, exp: 1 })))
  await page.route('**/api/modules/fen5-ses/v1/aciklama', r => r.fulfill(json(ACIKLAMA)))
  await page.route('**/api/modules/fen5-ses/progress**', r => r.fulfill(json({ ok: true, state: { answers: [], done: [], xp: 0 } })))
  await page.route('https://modul.tedy.online/**', r => r.fulfill({
    status: 200, contentType: 'text/html; charset=utf-8', body: moduleHtml,
    headers: { 'content-security-policy': SPEC_CSP, 'x-content-type-options': 'nosniff', 'cache-control': 'no-store' },
  }))
  await page.setViewportSize({ width: genislik, height: 900 })
  if (dogrudan) {
    await page.goto(MODUL)
    await expect(page.locator('#titleText')).toHaveText(CARD.title)
    return page
  }
  await page.goto('/moduller/fen5-ses/v1')
  await expect.poll(() => page.frame({ url: /modul\.tedy\.online/ }) !== null).toBe(true)
  const f = page.frame({ url: /modul\.tedy\.online/ })!
  await expect(f.locator('html')).toHaveAttribute('data-host-layout', 'flow')
  if (genislik >= 2560) {
    await expect.poll(() => f.locator('html').evaluate(e => parseFloat(getComputedStyle(e).fontSize)))
      .toBeCloseTo(genislik / 120, 0)
  }
  return f
}

const oynatici = (f: Frame | Page) => f.locator('.edupedia-audio').first()

/** Sizes, names and roles of the first player, against the document's root (3rem = 48 px at root 16, 96 at 32). */
async function olc(f: Frame | Page) {
  return oynatici(f).evaluate(k => {
    const kok = parseFloat(getComputedStyle(document.documentElement).fontSize)
    const kutu = (s: string) => { const e = k.querySelector(s) as HTMLElement | null; const r = e?.getBoundingClientRect(); return r ? { w: r.width, h: r.height } : null }
    const kay = k.querySelector('[role="slider"]') as HTMLElement | null
    const sure = k.querySelector('.ses-sure') as HTMLElement | null
    const grupAdi = (k.getAttribute('aria-labelledby') ?? '').split(/\s+/).map(id => document.getElementById(id)?.textContent ?? '').join(' ').trim()
    return {
      kok, rol: k.getAttribute('role'), grupAdi,
      oynat: kutu('.ses-oynat'), oynatAdi: k.querySelector('.ses-oynat')?.getAttribute('aria-label') ?? '',
      oynatIkon: kutu('.ses-oynat svg'),
      sessiz: kutu('.ses-sessiz'), sessizAdi: k.querySelector('.ses-sessiz')?.getAttribute('aria-label') ?? '',
      kaydirici: kutu('[role="slider"]'),
      kaydiriciAria: kay ? ['aria-label', 'aria-valuemin', 'aria-valuemax', 'aria-valuenow', 'aria-valuetext']
        .map(a => [a, kay.getAttribute(a)]) : [],
      kaydiriciOdak: kay?.tabIndex ?? -1,
      sureYazi: sure ? getComputedStyle(sure).fontFamily : '', sureRakam: sure ? getComputedStyle(sure).fontVariantNumeric : '',
      // Review round 1, finding 2: both live regions exist, are rendered (not hidden) and start empty.
      bolgeler: ['status', 'alert'].map(rol => {
        const b = k.querySelector(`[role="${rol}"]`) as HTMLElement | null
        if (!b) return [rol, 'yok']
        const cs = getComputedStyle(b)
        return [rol, b.hidden || cs.display === 'none' || cs.visibility === 'hidden' ? 'gizli' : `görünür:${b.textContent}`]
      }),
      yerliDenetim: k.querySelectorAll('audio[controls]').length,
      audioGorunur: Array.from(k.querySelectorAll('audio')).some(a => a.getBoundingClientRect().height > 0),
      tasma: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    }
  })
}

const GENISLIKLER: [number, boolean, string][] = [
  [390, true, 'çerçeve 390'], [390, false, 'ekran 390'], [1440, false, 'ekran 1440'], [3840, false, 'ekran 3840'],
]

for (const [genislik, dogrudan, ad] of GENISLIKLER) {
  test(`the player is Carbon composed, 48 px and named — ${ad}`, async ({ page }) => {
    const f = await ac(page, genislik, dogrudan)
    await expect(oynatici(f).locator('[role="slider"]')).toHaveAttribute('aria-valuemax', '20')  // metadata read
    const o = await olc(f)
    const lg = Math.max(48, 3 * o.kok) - 0.5
    expect(o.rol).toBe('group')
    expect(o.grupAdi).toBe('Seslendirme')
    expect(o.yerliDenetim, 'tarayıcının kendi oynatıcısı çizilmez (KB-49)').toBe(0)
    expect(o.audioGorunur).toBe(false)
    expect(o.oynatAdi).toBe('Oynat')
    expect(o.sessizAdi).toBe('Seslendirmenin sesini kapat')
    for (const [adi, k] of [['oynat', o.oynat], ['sessiz', o.sessiz]] as const) {
      expect(k!.w >= lg && k!.h >= lg, `${ad}: ${adi} ${k!.w}×${k!.h} < ${lg + 0.5}`).toBe(true)
    }
    expect(Math.abs(o.oynatIkon!.w - 1.25 * o.kok)).toBeLessThan(0.6)
    expect(o.kaydirici!.h, `${ad}: kaydırıcının vuruş alanı`).toBeGreaterThanOrEqual(lg)
    expect(Object.fromEntries(o.kaydiriciAria)).toEqual({
      'aria-label': 'Konum', 'aria-valuemin': '0', 'aria-valuemax': '20', 'aria-valuenow': '0',
      'aria-valuetext': '0 saniye / 20 saniye',
    })
    expect(o.kaydiriciOdak).toBe(0)
    expect(o.bolgeler, 'canlı bölgeler DOM\'da, görünür ve boş').toEqual([['status', 'görünür:'], ['alert', 'görünür:']])
    expect(o.sureYazi).toContain('IBM Plex Mono')
    expect(o.sureRakam).toContain('tabular-nums')
    expect(o.tasma, `${ad}: yatay kaydırma`).toBeLessThanOrEqual(0)
  })
}

test('the slider answers the keyboard: ← → ±5 s, PageUp/PageDown ±10 %, Home/End', async ({ page }) => {
  const f = await ac(page, 390, true)
  const kay = oynatici(f).locator('[role="slider"]')
  await expect(kay).toHaveAttribute('aria-valuemax', '20')
  await kay.focus()
  const deger = () => kay.getAttribute('aria-valuenow')
  await page.keyboard.press('ArrowRight'); await expect.poll(deger).toBe('5')
  await page.keyboard.press('ArrowUp'); await expect.poll(deger).toBe('10')
  await page.keyboard.press('PageUp'); await expect.poll(deger).toBe('12')
  await page.keyboard.press('ArrowLeft'); await expect.poll(deger).toBe('7')
  await page.keyboard.press('PageDown'); await expect.poll(deger).toBe('5')
  await page.keyboard.press('End'); await expect.poll(deger).toBe('20')
  await expect(kay).toHaveAttribute('aria-valuetext', '20 saniye / 20 saniye')
  await expect(oynatici(f).locator('.ses-sure')).toHaveText('0:20 / 0:20')
  await page.keyboard.press('Home'); await expect.poll(deger).toBe('0')
  await page.keyboard.press('ArrowLeft'); await expect.poll(deger).toBe('0')
  // A pointer on the track seeks there.
  const r = (await kay.boundingBox())!
  await page.mouse.click(r.x + r.width * 0.5, r.y + r.height / 2)
  await expect.poll(async () => Number(await deger())).toBeGreaterThanOrEqual(9)
  await expect.poll(async () => Number(await deger())).toBeLessThanOrEqual(11)
})

test('playing is the reader\'s act: the time advances, pause stops it, nothing starts by itself', async ({ page }) => {
  const f = await ac(page, 390, false)
  const k = oynatici(f)
  const kay = k.locator('[role="slider"]')
  await page.waitForTimeout(600)
  expect(await k.locator('audio').evaluate(a => (a as HTMLAudioElement).paused), 'kendiliğinden çalmamalı').toBe(true)
  await k.locator('.ses-oynat').click()
  await expect(k.locator('.ses-oynat')).toHaveAttribute('aria-label', 'Duraklat')
  await expect.poll(async () => Number(await kay.getAttribute('aria-valuenow')), { timeout: 5000 }).toBeGreaterThanOrEqual(1)
  await expect(k.locator('.ses-sure')).toHaveText(/^0:0[1-9] \/ 0:20$/)
  await expect(k.locator('[role="status"]')).toHaveText('')   // playing: the loading region is empty again
  await k.locator('.ses-oynat').click()
  await expect(k.locator('.ses-oynat')).toHaveAttribute('aria-label', 'Oynat')
  const durdu = await kay.getAttribute('aria-valuenow')
  await page.waitForTimeout(1300)
  expect(await kay.getAttribute('aria-valuenow')).toBe(durdu)
  // Mute is a toggle with its name.
  await k.locator('.ses-sessiz').click()
  await expect(k.locator('.ses-sessiz')).toHaveAttribute('aria-label', 'Seslendirmenin sesini aç')
  expect(await k.locator('audio').evaluate(a => (a as HTMLAudioElement).muted)).toBe(true)
})

test('a file that cannot be opened says so in an InlineNotification and disables the controls', async ({ page }) => {
  const f = await ac(page, 390, true)
  // Review round 1, finding 2: a screen reader announces a live region whose content changes; toggling `hidden`
  // is not reliably announced. Record what happens to the player's alert region once it is in the document.
  await f.evaluate(() => {
    const w = window as unknown as { bolgeKaydi: string[] }
    w.bolgeKaydi = []
    new MutationObserver(kayitlar => kayitlar.forEach(m => {
      const t = m.target as Element
      if (t.nodeType !== 1 || !t.closest('.edupedia-audio')) return
      if (m.type === 'childList' && t.getAttribute('role') === 'alert' && m.addedNodes.length) w.bolgeKaydi.push('icerik')
      if (m.type === 'attributes' && m.attributeName === 'hidden') w.bolgeKaydi.push('hidden')
    })).observe(document.body, { subtree: true, childList: true, attributes: true, attributeFilter: ['hidden'] })
  })
  await f.locator('#nextBtn').click()
  const k = oynatici(f)
  await expect(k).toBeVisible()
  const bolge = k.locator('[role="alert"]')
  await expect(bolge).toHaveText('Ses dosyası açılamadı')
  await expect(bolge).toHaveClass('ses-uyari')
  const hata = bolge.locator('.ses-hata')   // the visual InlineNotification box lives inside the region
  await expect(hata).toBeVisible()
  await expect(hata).toHaveText('Ses dosyası açılamadı')
  expect(await f.evaluate(() => (window as unknown as { bolgeKaydi: string[] }).bolgeKaydi)).toEqual(['icerik'])
  await expect(k.locator('.ses-oynat')).toBeDisabled()
  await expect(k.locator('[role="slider"]')).toHaveAttribute('aria-disabled', 'true')
  await expect(k.locator('[role="status"]')).toHaveText('')
  await expect(k.locator('[role="status"]')).toBeAttached()
})

for (const [genislik, dogrudan, ad] of [[390, true, 'çerçeve 390'], [1440, true, 'çerçeve 1440']] as const) {
  test(`axe and IBM Equal Access find nothing in the player — ${ad}`, async ({ page }) => {
    const f = await ac(page, genislik, dogrudan) as Page
    await expect(oynatici(f).locator('[role="slider"]')).toHaveAttribute('aria-valuemax', '20')
    const { violations } = await new AxeBuilder({ page: f })
      .include('.edupedia-audio')
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice'])
      .analyze()
    expect(violations.map(v => `${v.id}: ${v.nodes.map(n => n.target.join(' ')).join(', ')}`)).toEqual([])
    await f.addScriptTag({ path: ACE })
    const ihlal: string[] = await f.evaluate(async () => {
      // @ts-expect-error — `ace` is the injected engine's global
      const rapor = await new window.ace.Checker().check(document, ['IBM_Accessibility'])
      return (rapor.results as { ruleId: string; value: string[]; message: string; path: { dom: string }; snippet: string }[])
        .filter(s => s.value[0] === 'VIOLATION' && s.value[1] === 'FAIL')
        .filter(s => (document.evaluate(s.path.dom, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null)
          .singleNodeValue as Element | null)?.closest?.('.edupedia-audio'))
        .map(s => `${s.ruleId}: ${s.message} — ${s.snippet.slice(0, 120)}`)
    })
    expect(ihlal).toEqual([])
  })
}
