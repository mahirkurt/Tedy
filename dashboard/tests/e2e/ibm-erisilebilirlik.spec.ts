import { test, expect } from '@playwright/test'
import { createRequire } from 'node:module'
import { SAYFALAR, sabitAc } from './_gorsel-yardim'

// IBM Equal Access (the engine behind IBM's Accessibility Checker, from the
// team that builds Carbon): a second rule set beside axe. Run on 2026-09-25 it
// found what axe had passed — a header button named "Senkron durumunu göster"
// while it read "15 dk önce" (WCAG 2.5.3), an empty textarea label, an
// unnamed <aside>, grade rows whose aria-controls pointed at no id, and a
// scroll region that was a tab stop while it scrolled nothing.
//
// Only definite failures (VIOLATION/FAIL) fail the test. "Potential" and
// "manual" results ask a person to look; they are for audits, not for CI.

test.use({ timezoneId: 'Europe/Istanbul', locale: 'tr-TR' })

const ACE = createRequire(import.meta.url).resolve('accessibility-checker-engine/ace.js')

// Carbon's Toggletip (inside AILabel) points aria-controls at its popover,
// which it renders only when open. It is Carbon's markup, not ours to fix.
const CARBON_ISTISNA = (kural: string, yol: string) =>
  kural === 'aria_id_unique' && /cds--ai-label|cds--toggletip/.test(yol)

type Sonuc = { ruleId: string; value: string[]; message: string; path: { dom: string }; snippet: string }

for (const [boy, w, h] of [['masaüstü', 1440, 900], ['telefon', 390, 844]] as const) {
  for (const [ad, yol] of SAYFALAR) {
    test(`${ad} on a ${boy}: no IBM Equal Access violations`, async ({ page }) => {
      await sabitAc(page, yol, w, h)
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
    })
  }
}
