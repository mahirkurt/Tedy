import { test, expect } from '@playwright/test'
import { sabitAc } from './_gorsel-yardim'
import { DERS, GENEL, KILAVUZ, fikstur } from './_hazirlik'

// Sınav Hazırlığı yüzeylerinin görsel tabanı (D13, spec §9): ana sayfa, ders sayfası ve kapsam kılavuzu, masaüstü ve
// telefon. gorsel-regresyon.spec.ts ile aynı sabit açılış (saat, taklit, yazı tipleri); veri modelden üretilmiş
// fikstürlerden (scripts/hazirlik_fiksturleri.py). Bilinçli bir değişiklikte:
// `npx playwright test hazirlik-gorsel --update-snapshots=all`, sonra yeni PNG'leri gözle oku.

test.use({ timezoneId: 'Europe/Istanbul', locale: 'tr-TR' })

const ROTALAR: [RegExp, unknown][] = [
  [GENEL, fikstur('genel')],
  [DERS('fen-bilimleri', 1), fikstur('fen-bilimleri-1')],
  [KILAVUZ('fen-bilimleri', 1), fikstur('fen-bilimleri-1-kilavuz')],
]

const YUZEYLER: [string, string, string][] = [
  ['hazirlik', '/hazirlik', '.hazirlik-yaklasan__oge'],
  ['hazirlik-ders', '/hazirlik/fen-bilimleri?sinav=1', 'table.kilavuz-matris'],
  ['hazirlik-kilavuz', '/hazirlik/fen-bilimleri/1', '#cikti-FB-7-2-1'],
]

for (const [boy, w, h] of [['masaustu', 1440, 900], ['telefon', 390, 844]] as const) {
  for (const [ad, yol, hazir] of YUZEYLER) {
    test(`${ad} görünüşü değişmedi (${boy})`, async ({ page }) => {
      await sabitAc(page, yol, w, h, ROTALAR)
      await expect(page.locator(hazir).first()).toBeVisible()
      await expect(page).toHaveScreenshot(`${ad}-${boy}.png`, {
        fullPage: true,
        animations: 'disabled',
        caret: 'hide',
        maxDiffPixelRatio: 0.002,
      })
    })
  }
}
