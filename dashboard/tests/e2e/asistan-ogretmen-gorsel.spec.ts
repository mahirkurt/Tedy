import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { createRequire } from 'node:module'
import { sabitAc } from './_gorsel-yardim'

// Every teacher mode, pinned as the other pages are: a screenshot per teacher at
// a desktop and a phone width (spec "Test": "her öğretmen için görsel regresyon
// taban çizgisi"), and both accessibility rule sets on each mode — a subject's
// colours on the send button, the chips and the reader's bubble have to hold
// WCAG 2.2 AA as Genel's do.
//
// A change you meant: `npx playwright test asistan-ogretmen-gorsel --update-snapshots`,
// then look at every new PNG before committing it.

test.use({ timezoneId: 'Europe/Istanbul', locale: 'tr-TR' })

const ANAHTAR = 'tedy-asistan-ogretmen::test@tedy.online'
const MODLAR = ['genel', 'turkce', 'fen', 'sosyal', 'matematik']
const ACE = createRequire(import.meta.url).resolve('accessibility-checker-engine/ace.js')
const CARBON_ISTISNA = (kural: string, yol: string) =>
  kural === 'aria_id_unique' && /cds--ai-label|cds--toggletip/.test(yol)
type Sonuc = { ruleId: string; value: string[]; message: string; path: { dom: string }; snippet: string }

async function modda(page: Page, id: string, w: number, h: number) {
  await page.addInitScript(([k, v]) => localStorage.setItem(k, v), [ANAHTAR, id])
  await sabitAc(page, '/asistan', w, h)
  await expect(page.locator('section.ac')).toHaveAttribute('data-ogretmen', id)
  // The reader's own bubble is part of the theme: put one on the page.
  await page.route('**/api/assistant/stream', r => r.abort())
  await page.route('**/api/assistant/chat', r => r.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify({
      answer: 'Bir cevap.', citations: [], safety_flags: [], plan_blocks: [], intent: 'qa',
      session_id: '', mode_suggestion: null, meta: { model: 'claude-sonnet-5', degraded: [] } }),
  }))
  await page.fill('#ac-input', 'Bir soru')
  await page.getByRole('button', { name: 'Gönder' }).click()
  await expect(page.locator('.ac-msg--user')).toHaveCount(1)
  await expect(page.locator('.ac-msg--assistant')).toHaveCount(2)
}

// Final-fix item 6: a mode_suggestion (ModOnerisi) carrying its longest legal
// reason (MOD_GEREKCE_SINIRI = 200 chars, src/assistant_tools.py) must not
// overflow the page at a phone width, and must stay axe/IBM clean like every
// other mode's screenshot.
const GEREKCE_200 = (
  'Bu soru Türkiye’nin bölgesel farklılıklarını, nüfus hareketlerini, tarihsel dönüm ' +
  'noktalarını ve toplumsal yaşamı bir arada ele alıyor; harita okuma, kronoloji kurma ve ' +
  'neden-sonuç ilişkisi kurma becerisi istiyor, bunun için Sosyal Bilgiler öğretmeni konuyu ' +
  'örneklerle çok daha iyi anlatabilir ve adım adım ilerleyebilir bence, denemeye değer olur.'
).slice(0, 200)

const ONERI_TASMA = {
  ogretmen: 'sosyal', ogretmen_adi: 'Sosyal Bilgiler öğretmeni',
  soru: 'Sosyal Bilgiler öğretmenine geçelim mi?',
  gerekce: GEREKCE_200, renk_ailesi: 'cyan',
}

async function oneriyle(page: Page, w: number, h: number) {
  await sabitAc(page, '/asistan', w, h)
  await page.route('**/api/assistant/stream', r => r.abort())
  await page.route('**/api/assistant/chat', r => r.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify({
      answer: 'Bir cevap.', citations: [], safety_flags: [], plan_blocks: [], intent: 'qa',
      session_id: '', mode_suggestion: ONERI_TASMA,
      meta: { model: 'claude-sonnet-5', degraded: [], ogretmen: 'genel' } }),
  }))
  await page.fill('#ac-input', 'Bir soru')
  await page.getByRole('button', { name: 'Gönder' }).click()
  await expect(page.getByRole('button', { name: ONERI_TASMA.soru })).toBeVisible()
}

for (const [boy, w, h] of [['masaustu', 1440, 900], ['telefon', 390, 844]] as const) {
  test(`mod_oner önerisi, en uzun gerekçe (${boy}): looks as it did`, async ({ page }) => {
    await oneriyle(page, w, h)
    await expect(page).toHaveScreenshot(`asistan-oneri-tasma-${boy}.png`, {
      fullPage: true, animations: 'disabled', caret: 'hide', maxDiffPixelRatio: 0.002,
    })
  })

  test(`mod_oner önerisi, en uzun gerekçe (${boy}): axe, IBM ve taşma yok`, async ({ page }) => {
    await oneriyle(page, w, h)
    const { violations } = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice'])
      .analyze()
    expect(violations.map(v =>
      `${v.impact} ${v.id}: ${v.nodes.slice(0, 3).map(n => n.target.join(' ')).join(' | ')}`)).toEqual([])
    await page.addScriptTag({ path: ACE })
    const sonuclar: Sonuc[] = await page.evaluate(async () => {
      // @ts-expect-error — `ace` is the injected engine's global
      const rapor = await new window.ace.Checker().check(document, ['IBM_Accessibility'])
      return rapor.results
    })
    const ihlal = sonuclar
      .filter(s => s.value[0] === 'VIOLATION' && s.value[1] === 'FAIL')
      .filter(s => !CARBON_ISTISNA(s.ruleId, s.snippet + ' ' + s.path.dom))
      .map(s => `${s.ruleId}: ${s.message} — ${s.snippet.slice(0, 120)}`)
    expect(ihlal).toEqual([])
    const tasma = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
    expect(tasma, 'yatay taşma (px)').toBeLessThanOrEqual(0)
  })
}

for (const [boy, w, h] of [['masaustu', 1440, 900], ['telefon', 390, 844]] as const) {
  for (const id of MODLAR) {
    test(`${id} (${boy}): looks as it did`, async ({ page }) => {
      await modda(page, id, w, h)
      await expect(page).toHaveScreenshot(`asistan-${id}-${boy}.png`, {
        fullPage: true, animations: 'disabled', caret: 'hide', maxDiffPixelRatio: 0.002,
      })
    })

    test(`${id} (${boy}): axe and IBM Equal Access find nothing`, async ({ page }) => {
      await modda(page, id, w, h)
      const { violations } = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice'])
        .analyze()
      expect(violations.map(v =>
        `${v.impact} ${v.id}: ${v.nodes.slice(0, 3).map(n => n.target.join(' ')).join(' | ')}`)).toEqual([])
      await page.addScriptTag({ path: ACE })
      const sonuclar: Sonuc[] = await page.evaluate(async () => {
        // @ts-expect-error — `ace` is the injected engine's global
        const rapor = await new window.ace.Checker().check(document, ['IBM_Accessibility'])
        return rapor.results
      })
      const ihlal = sonuclar
        .filter(s => s.value[0] === 'VIOLATION' && s.value[1] === 'FAIL')
        .filter(s => !CARBON_ISTISNA(s.ruleId, s.snippet + ' ' + s.path.dom))
        .map(s => `${s.ruleId}: ${s.message} — ${s.snippet.slice(0, 120)}`)
      expect(ihlal).toEqual([])
      const tasma = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
      expect(tasma, 'yatay taşma (px)').toBeLessThanOrEqual(0)
    })
  }
}
