import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'
import { json } from './_audit-fixtures'
import { sabitAc } from './_gorsel-yardim'

// How an answer is set. Until 2026-09-25 the assistant borrowed Tedy Books'
// chapter styles: serif headings, a printed book's indent on every paragraph
// after the first, and short lines folded into italic verse. On a phone a
// homework answer read as a ragged mix of a serif heading, indented bold
// lines standing in for headings and a chip reading "1" after every sentence.

const KAYNAK = [{ id: 'S1', kind: 'ogrenci', label: 'Ödev listesi',
                  locator: {}, snippet: 'Pazartesi 28.09', confidence: 0.9 }]

function cevap(answer: string) {
  return {
    answer, citations: KAYNAK, safety_flags: [], plan_blocks: [], intent: 'qa',
    session_id: '', meta: { model: 'claude-sonnet-5', degraded: [], dropped_citations: 0 },
  }
}

// What the model wrote on 2026-09-25, before the prompt's "## Biçim" — the
// renderer has to give even this a clean shape (repeated markers are the
// backend's to collapse, tests/test_assistant_citations.py).
const ESKI = [
  '## Bugünün önceliği',
  '',
  'Şu an listede en yakın teslim tarihi **Pazartesi (28.09)** [S1].',
  '**Öncelik sırası (Pazartesi\'ye 3 ödev var):**',
  '',
  '1. **Matematik – Hafta Sonu Ödevi** (Test 1 s.5-6) — işlemsiz kabul edilmiyor.',
  '2. **Türkçe – 2. Hafta HS Ödevi** (s.9-12) — ilk derste kontrol edilecek.',
  '',
  '3. **Fransızca – Les verbes** — daha kısa bir ödev gibi görünüyor.',
  '',
  '**Sonra (Salı-Çarşamba\'ya kadar zaman var):**',
  '',
  '- Fen Bilimleri (Hibrit Kitap s.10-16)',
  '- Din Kültürü (Eker Test s.8-11)',
  '',
  '**Öneri:** Işık\'la bugün Matematik\'e 10 dakikalık bir başlangıç yapabilirsiniz.',
].join('\n')

// The shape the prompt now asks for.
const YENI = [
  'En yakın teslim **Pazartesi 28.09** — üç ödev aynı gün bitiyor [S1].',
  '',
  '### Pazartesiye üç ödev',
  '1. **Matematik** — Test 1 s.5-6; işlemsiz kabul edilmiyor',
  '   - Test 2 s.7-8 de aynı ödevde',
  '2. **Türkçe** — s.9-12, Test 2-3',
  '3. **Fransızca** — Les verbes',
  '',
  '### Sonra',
  '- **Fen Bilimleri** — Hibrit Kitap s.10-16',
  '- **Din Kültürü** — Eker Test s.8-11',
  '',
  '**Not:** Matematik hafta içi ödevini Işık "Yaptım" diye işaretlemiş.',
  '',
  '**Şimdi:** Matematik\'in ilk sayfasına 10 dakika ayırın.',
].join('\n')

test.use({ timezoneId: 'Europe/Istanbul', locale: 'tr-TR' })

async function sor(page: Page, answer: string, w = 1440, h = 900) {
  await sabitAc(page, '/asistan', w, h)
  await page.route('**/api/assistant/stream', r => r.abort())
  await page.route('**/api/assistant/chat', r => r.fulfill(json(cevap(answer))))
  await page.fill('#ac-input', 'Bugün neye öncelik vermeli?')
  await page.getByLabel('Gönder').click()
  const msg = page.locator('.ac-msg--assistant').last()
  await msg.locator('.ac-cite').first().waitFor()
  return msg
}

test('an answer is set in Carbon type, without a book\'s indent', async ({ page }) => {
  const msg = await sor(page, ESKI)
  const bicim = await msg.locator('.ac-md').evaluate(el => ({
    girintili: [...el.querySelectorAll('p')].filter(p => getComputedStyle(p).textIndent !== '0px').length,
    basliklar: [...el.querySelectorAll('h3, h4')].map(h => [h.tagName, h.textContent, getComputedStyle(h).fontFamily]),
    kitapSinifi: el.querySelectorAll('[class*="bookmd"]').length,
  }))
  expect(bicim.girintili).toBe(0)
  expect(bicim.kitapSinifi).toBe(0)
  // The model's bold lines are headings under its own heading; no colon, no
  // serif.
  expect(bicim.basliklar.map(([t, x]) => [t, x])).toEqual([
    ['H3', 'Bugünün önceliği'],
    ['H4', 'Öncelik sırası (Pazartesi\'ye 3 ödev var)'],
    ['H4', 'Sonra (Salı-Çarşamba\'ya kadar zaman var)'],
  ])
  for (const [, , font] of bicim.basliklar) expect(font).toContain('IBM Plex Sans')
})

test('a blank line between numbered items does not restart the count', async ({ page }) => {
  const msg = await sor(page, ESKI)
  // Before, "3." after a blank line became its own list and read "1.".
  await expect(msg.locator('ol.ac-md__list')).toHaveCount(1)
  await expect(msg.locator('ol.ac-md__list > li')).toHaveCount(3)
})

test('the closing step and caveat are set apart', async ({ page }) => {
  const msg = await sor(page, YENI)
  await expect(msg.locator('.ac-md__callout--eylem .ac-md__callout-label')).toHaveText('Şimdi')
  await expect(msg.locator('.ac-md__callout--not .ac-md__callout-label')).toHaveText('Not')
  await expect(msg.locator('.ac-md__callout--eylem')).toContainText('10 dakika ayırın')
  // A sub-item stays inside its item instead of breaking the numbered list.
  await expect(msg.locator('ol.ac-md__list > li')).toHaveCount(3)
  await expect(msg.locator('ol.ac-md__list > li').first().locator('ul.ac-md__list > li'))
    .toHaveText('Test 2 s.7-8 de aynı ödevde')
})

for (const [boy, w, h] of [['masaustu', 1440, 900], ['telefon', 390, 844]] as const) {
  test(`an answer looks as it did (${boy})`, async ({ page }) => {
    const msg = await sor(page, YENI, w, h)
    await expect(msg).toHaveScreenshot(`asistan-cevap-${boy}.png`, {
      animations: 'disabled', caret: 'hide', maxDiffPixelRatio: 0.002,
    })
  })
}
