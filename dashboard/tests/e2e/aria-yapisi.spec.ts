import { test, expect } from '@playwright/test'
import { SAYFALAR, sabitAc } from './_gorsel-yardim'
import { girisAc } from './_gsi-sahte'

// What a screen reader is given, page by page: headings, landmarks, button
// and link names, list structure — pinned as an accessibility-tree snapshot.
// axe checks that the tree is valid; this checks that it did not change. A
// renamed button, a heading that lost its level or a list that became divs
// fails here even when every page still looks the same.
//
// A change you meant: `npx playwright test aria-yapisi --update-snapshots`,
// then read the .aria.yml diff before committing it.

test.use({ timezoneId: 'Europe/Istanbul', locale: 'tr-TR' })

for (const [ad, yol] of SAYFALAR) {
  test(`${ad}: the accessible structure is unchanged`, async ({ page }) => {
    await sabitAc(page, yol, 1440, 900)
    await expect(page.locator('.app-shell-content')).toMatchAriaSnapshot({ name: `${ad}.aria.yml` })
  })
}

// Giriş sayfası (2026-10-15): banner, the sign-in region as main, the footer as contentinfo.
test('the sign-in page: the accessible structure is unchanged', async ({ page }) => {
  await girisAc(page)
  await expect(page.locator('.login-page')).toMatchAriaSnapshot({ name: 'giris.aria.yml' })
})
