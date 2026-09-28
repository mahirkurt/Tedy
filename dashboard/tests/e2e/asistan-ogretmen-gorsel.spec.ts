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
