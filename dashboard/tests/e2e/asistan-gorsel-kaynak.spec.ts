import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { createRequire } from 'node:module'

// Görev 4. A textbook figure the assistant opened with figur_getir reaches the reader: its citation
// carries `locator.figure_id`, and the Kaynaklar panel shows the image from
// /api/assistant/figure/<id> with the figure's caption as alt text. The chat and figure endpoints
// are fulfilled in-browser, so nothing reaches the model or the curriculum server. Every absence
// below follows proof that the surface it is absent from rendered (TEDY traps 3-5).

const json = (body: unknown) => ({ status: 200, contentType: 'application/json', body: JSON.stringify(body) })

// A 96x48 PNG: real bytes, so the test can prove the image decoded (naturalWidth), not just that
// an <img> tag exists.
const PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAGAAAAAwCAIAAABhdOiYAAABcUlEQVR42u2a0RHCIAyGW84BXMJhXMIX5/LFJRzGJdygvnleaUsS+AOB5LHXg/zfEQgh87Isk9u+BUfggBwQ0k61Jj7f2Xvf5zHr+zkrbNICFu1QQwGCQtGEVRgQnYtADHRwLKBj16FRgJ46F9Cef1U2VIQzckCb3lThAvVNAiievhEuCFfZgFZTNoumlM8MQBbR5PsfBqET+0xMGkgr6H8si2hy5ITR6KxUJNdREC/RbhhlhdgPMJrO5XmNP75vL51YO1B3BEiHziYaNUxJjZULZkk6xH9wFirWK+jKFRjt6U2vIFB8cTWDGBU45gc3B+SAHFBlQKDjjJvdgLIh+VVD4WJB14xOqdtNFCnKFej4XQxzF1NmpGxEXUEwYk90CpxirPKSOTrJsKAW7TuoSctUUENMVvG2Tmfyd7HygCZ/Wc05CPxtnnpeencHI60Yuj9InICN1WHWSNptoEdRH5bVLlcEtW77pE2b16QdUJ59ASYIFwqVkAxfAAAAAElFTkSuQmCC',
  'base64',
)

const CAPTION = 'Bitki hücresinin kesit çizimi: hücre duvarı, hücre zarı ve çekirdek.'

// The citation shape src/assistant_tools.py McpRegistry.dispatch builds for figur_getir.
const FIGURE_CITATION = {
  id: 'S1', kind: 'kitap', label: 'Fen Bilimleri 7.Sınıf Ders Kitabı · s.114 · görsel',
  locator: { tool: 'figur_getir', server: 'maarif-mufredat', args: { figure_id: 1875 }, figure_id: 1875, caption: CAPTION },
  snippet: CAPTION, confidence: 0.9,
}
const UNCAPTIONED = {
  ...FIGURE_CITATION, id: 'S2', label: 'Fen Bilimleri 7.Sınıf Ders Kitabı · s.120 · görsel',
  locator: { tool: 'figur_getir', figure_id: 1876 }, snippet: '',
}
const BROKEN = {
  ...FIGURE_CITATION, id: 'S3', label: 'Fen Bilimleri 7.Sınıf Ders Kitabı · s.130 · görsel',
  locator: { tool: 'figur_getir', figure_id: 1877, caption: 'Kırık görsel' }, snippet: 'Kırık görsel',
}
// A figure id that is not a positive integer must never become a URL segment.
const UNSAFE = {
  ...FIGURE_CITATION, id: 'S4', label: 'Kaçak görsel',
  locator: { tool: 'figur_getir', figure_id: '../1875' }, snippet: 'kaçak özet',
}

function answer(citations: unknown[], text: string) {
  return {
    answer: text, citations, safety_flags: [], plan_blocks: [], intent: 'qa', session_id: '',
    meta: { model: 'claude-sonnet-5', degraded: [], dropped_citations: 0 },
  }
}

async function ask(page: Page, prompt: string) {
  await page.goto('/asistan')
  await page.fill('#ac-input', prompt)
  await page.getByLabel('Gönder').click()
}

async function mockFigures(page: Page) {
  const requested: string[] = []
  await page.route('**/api/assistant/figure/**', route => {
    const url = route.request().url()
    requested.push(new URL(url).pathname)
    if (url.endsWith('/1877')) {
      return route.fulfill({ status: 502, contentType: 'application/json',
        body: JSON.stringify({ error: 'Ders kitabı görseline şu an ulaşılamadı; biraz sonra yeniden deneyin.' }) })
    }
    return route.fulfill({ status: 200, contentType: 'image/png', body: PNG })
  })
  return requested
}

test.use({ timezoneId: 'Europe/Istanbul', locale: 'tr-TR' })

test('a figure citation shows the textbook image in the source panel, captioned as its alt', async ({ page }) => {
  const requested = await mockFigures(page)
  await page.route('**/api/assistant/stream', route => route.abort())
  await page.route('**/api/assistant/chat', route => route.fulfill(json(answer(
    [FIGURE_CITATION, UNCAPTIONED, BROKEN, UNSAFE],
    'Bitki hücresinde hücre duvarı vardır [S1]. İkinci çizim [S2], üçüncüsü [S3], dördüncüsü [S4].'))))

  await ask(page, 'bitki hücresinin şeklini göster')

  // The fixture really produces the chips and the group this test is about.
  await expect(page.locator('.ac-msg--assistant').last().locator('.ac-cite')).toHaveCount(4)
  const items = page.locator('.ac__ref-group--kitap .ac__ref-item')
  await expect(items).toHaveCount(4)
  await expect(items.locator('.ac__ref-path')).toHaveText([
    FIGURE_CITATION.label, UNCAPTIONED.label, BROKEN.label, 'Kaçak görsel'])

  // 1. The captioned figure: the image loaded, from the dashboard's own endpoint, alt = caption.
  const first = items.nth(0).locator('img.ac__ref-figure')
  await expect(first).toBeVisible()
  await expect(first).toHaveAttribute('src', '/api/assistant/figure/1875')
  await expect(first).toHaveAttribute('alt', CAPTION)
  await expect.poll(() => first.evaluate((img: HTMLImageElement) => img.complete && img.naturalWidth)).toBe(96)
  // The caption is the alt text; printing it again as a snippet would read it twice.
  await expect(items.nth(0).locator('.ac__ref-snippet')).toHaveCount(0)

  // 2. No caption: the generic alt the brief names.
  await expect(items.nth(1).locator('img.ac__ref-figure')).toHaveAttribute('alt', 'Ders kitabı görseli')

  // 3. The endpoint failed: said in words, no broken-image box.
  await expect(items.nth(2).locator('.ac__ref-unlinked')).toHaveText('Görsel yüklenemedi')
  await expect(items.nth(2).locator('img')).toHaveCount(0)

  // 4. An unsafe id renders as an ordinary citation and never reaches the endpoint.
  await expect(items.nth(3).locator('.ac__ref-snippet')).toHaveText('kaçak özet')
  await expect(items.nth(3).locator('img')).toHaveCount(0)
  expect(requested.sort()).toEqual([
    '/api/assistant/figure/1875', '/api/assistant/figure/1876', '/api/assistant/figure/1877'])
})

test('the source panel with a figure passes axe and IBM Equal Access', async ({ page }) => {
  await mockFigures(page)
  await page.route('**/api/assistant/stream', route => route.abort())
  await page.route('**/api/assistant/chat', route => route.fulfill(json(answer(
    [FIGURE_CITATION, UNCAPTIONED], 'Bitki hücresinde hücre duvarı vardır [S1] ve zar [S2].'))))

  await ask(page, 'bitki hücresinin şeklini göster')
  const images = page.locator('.ac__ref-group--kitap img.ac__ref-figure')
  await expect(images).toHaveCount(2)
  await expect(images.first()).toBeVisible()

  const { violations } = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice'])
    .analyze()
  expect(violations.map(v => `${v.id}: ${v.nodes.map(n => n.target.join(' ')).join(', ')}`)).toEqual([])

  // IBM Equal Access, as ibm-erisilebilirlik.spec.ts runs it: definite violations only, with the
  // same Carbon Toggletip exception.
  await page.addScriptTag({ path: createRequire(import.meta.url).resolve('accessibility-checker-engine/ace.js') })
  type Sonuc = { ruleId: string; value: string[]; message: string; path: { dom: string }; snippet: string }
  const sonuclar: Sonuc[] = await page.evaluate(async () => {
    // @ts-expect-error — `ace` is the injected engine's global
    const rapor = await new window.ace.Checker().check(document, ['IBM_Accessibility'])
    return rapor.results
  })
  const ihlal = sonuclar
    .filter(s => s.value[0] === 'VIOLATION' && s.value[1] === 'FAIL')
    .filter(s => !(s.ruleId === 'aria_id_unique' && /cds--ai-label|cds--toggletip/.test(s.snippet + ' ' + s.path.dom)))
    .map(s => `${s.ruleId}: ${s.message} — ${s.snippet.slice(0, 120)}`)
  expect(ihlal).toEqual([])
})
