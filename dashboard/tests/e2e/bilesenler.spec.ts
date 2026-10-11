import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { sabitAc } from './_gorsel-yardim'
import { json } from './_audit-fixtures'

// B20 (talimatname §7): TEDY's own components — DayStrip, NextThing, SubjectLabel, EmptyLine — held to the
// checklist Carbon applies to its own: their states beyond the default, axe-clean, at Carbon's narrowest
// breakpoint (sm, 320px; the audit suite runs 390px), with nothing scrolling sideways.

test.use({ timezoneId: 'Europe/Istanbul', locale: 'tr-TR' })

const ETIKETLER = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice']

async function bilesenDenetimi(page: Page, secici: string) {
  await expect(page.locator(secici).first()).toBeVisible()
  const { violations } = await new AxeBuilder({ page }).include(secici).withTags(ETIKETLER).analyze()
  expect(violations.map(v => `${v.id}: ${v.nodes.map(n => n.target.join(' ')).join(', ')}`)).toEqual([])
  const yatay = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  expect(yatay).toBeLessThanOrEqual(0)
  for (const kutu of await page.locator(secici).evaluateAll(els => els.map(e => e.getBoundingClientRect().right))) {
    expect(kutu).toBeLessThanOrEqual(320)
  }
}

test.describe('at 320px', () => {
  test('DayStrip and the quiet NextThing during school', async ({ page }) => {
    await sabitAc(page, '/', 320, 700)
    await bilesenDenetimi(page, '.day-strip')
    await bilesenDenetimi(page, '.next-thing--quiet')
    await bilesenDenetimi(page, '.ted-subject-label')
  })

  test('the NextThing card after the last bell, and its time box once started', async ({ page }) => {
    await sabitAc(page, '/', 320, 700)
    await page.clock.setFixedTime(new Date('2026-09-24T19:10:00+03:00'))
    await page.reload()
    const kart = page.locator('.next-thing:not(.next-thing--quiet)').first()
    await bilesenDenetimi(page, '.next-thing:not(.next-thing--quiet)')
    await kart.getByRole('button', { name: /Başla/ }).click()
    await expect(kart).toContainText('Başladın')
    await bilesenDenetimi(page, '.next-thing:not(.next-thing--quiet)')
  })

  test('NextThing inside İşler’s card, in its Carbon layer', async ({ page }) => {
    await sabitAc(page, '/isler', 320, 700)
    await bilesenDenetimi(page, '.dashboard-card .next-thing')
  })

  test('EmptyLine says what is missing', async ({ page }) => {
    await sabitAc(page, '/notlar', 320, 700)
    await page.route('**/api/grades', r => r.fulfill(json({ semester: '1. Dönem', grades: [] })))
    await page.reload()
    await bilesenDenetimi(page, '.tedy-empty')
    await expect(page.locator('.tedy-empty')).toContainText('1. Dönem döneminde henüz not girilmemiş.')
  })
})
