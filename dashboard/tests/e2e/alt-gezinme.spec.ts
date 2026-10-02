import { test, expect } from '@playwright/test'
import { sabitAc } from './_gorsel-yardim'

// The phone shell (D3a, 2026-10-02): five tabs at the bottom instead of a menu
// button behind the brand band. One navigation in the accessibility tree at a
// time — the side nav and its button are hidden on a phone, the bar on a desktop.

test.use({ timezoneId: 'Europe/Istanbul', locale: 'tr-TR' })

const SEKMELER = ['Bugün', 'İşler', 'Asistan', 'Dersler', 'Daha fazla']

test('a phone gets the bottom bar and no menu button', async ({ page }) => {
  await sabitAc(page, '/', 390, 844)
  const bar = page.getByRole('navigation', { name: 'Ana gezinme' })
  await expect(bar).toBeVisible()
  await expect(bar.getByRole('link')).toHaveText(SEKMELER)
  await expect(page.getByRole('button', { name: 'Menü' })).toBeHidden()
  await expect(page.getByRole('navigation', { name: 'Navigasyon' })).toBeHidden()
  await expect(bar.getByRole('link', { name: 'Bugün' })).toHaveAttribute('aria-current', 'page')
  for (const link of await bar.getByRole('link').all()) {
    const box = await link.boundingBox()
    expect(box!.height).toBeGreaterThanOrEqual(48)
  }
})

test('a tab goes where it says and marks itself', async ({ page }) => {
  await sabitAc(page, '/', 390, 844)
  const bar = page.getByRole('navigation', { name: 'Ana gezinme' })
  await bar.getByRole('link', { name: 'İşler' }).click()
  await expect(page).toHaveURL(/\/isler$/)
  await expect(bar.getByRole('link', { name: 'İşler' })).toHaveAttribute('aria-current', 'page')
  await expect(bar.getByRole('link', { name: 'Bugün' })).not.toHaveAttribute('aria-current', 'page')
})

test('Daha fazla lists every secondary page and marks itself on one of them', async ({ page }) => {
  await sabitAc(page, '/', 390, 844)
  const bar = page.getByRole('navigation', { name: 'Ana gezinme' })
  await bar.getByRole('link', { name: 'Daha fazla' }).click()
  await expect(page).toHaveURL(/\/daha-fazla$/)
  const liste = page.locator('section.daha-fazla')
  for (const ad of ['Tedy Books', 'Notlar', 'Takvim', 'Takımlar', 'İlerleme', 'Duyurular', 'Profil', 'Modüller']) {
    await expect(liste.getByRole('link', { name: ad })).toBeVisible()
  }
  await liste.getByRole('link', { name: 'Notlar' }).click()
  await expect(page).toHaveURL(/\/notlar$/)
  await expect(bar.getByRole('link', { name: 'Daha fazla' })).toHaveAttribute('aria-current', 'page')
})

test('the bar never covers the end of a page', async ({ page }) => {
  await sabitAc(page, '/isler', 390, 844)
  await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight))
  const bar = await page.getByRole('navigation', { name: 'Ana gezinme' }).boundingBox()
  const footer = await page.locator('.dashboard-footer').boundingBox()
  expect(footer!.y + footer!.height).toBeLessThanOrEqual(bar!.y + 1)
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390)
})

test('a desktop keeps the side nav and shows no bar', async ({ page }) => {
  await sabitAc(page, '/', 1440, 900)
  await expect(page.getByRole('navigation', { name: 'Ana gezinme' })).toBeHidden()
  await expect(page.getByRole('navigation', { name: 'Navigasyon' })).toBeVisible()
})

test('focus mode keeps the four daily tabs and drops Daha fazla', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('tedy-focus-mode', 'true'))
  await sabitAc(page, '/', 390, 844)
  const bar = page.getByRole('navigation', { name: 'Ana gezinme' })
  await expect(bar.getByRole('link')).toHaveText(SEKMELER.slice(0, 4))
})
