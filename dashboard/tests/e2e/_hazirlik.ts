// Sınav Hazırlığı e2e yardımcıları (plan Görev 9–14). Fikstürler modelden üretilir (scripts/hazirlik_fiksturleri.py).
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import AxeBuilder from '@axe-core/playwright'
import type { Page } from '@playwright/test'
import { mock, LIVE } from './_audit-fixtures'

export function fikstur<T = Record<string, unknown>>(ad: string): T {
  return JSON.parse(readFileSync(new URL(`./fixtures/hazirlik/${ad}.json`, import.meta.url), 'utf8')) as T
}

export const json = (veri: unknown, status = 200) => ({ status, contentType: 'application/json', body: JSON.stringify(veri) })

export const GENEL = /\/api\/hazirlik$/
export const DERS = (anahtar: string, no: number) => new RegExp(`/api/hazirlik/${anahtar}/${no}$`)
export const KILAVUZ = (anahtar: string, no: number) => new RegExp(`/api/hazirlik/${anahtar}/${no}/kilavuz(\\?.*)?$`)
export const PDF = (anahtar: string, no: number) => new RegExp(`/api/hazirlik/${anahtar}/${no}/kilavuz\\.pdf(\\?.*)?$`)

/** LIVE taklidi + verilen hazırlık uçları; sonra sayfayı açar. */
export async function hazirlikAc(page: Page, yol: string, rotalar: [RegExp, unknown][]) {
  await mock(page, LIVE)
  for (const [desen, govde] of rotalar) await page.route(desen, r => r.fulfill(json(govde)))
  await page.goto(yol)
}

const ACE = createRequire(import.meta.url).resolve('accessibility-checker-engine/ace.js')

/** axe (WCAG 2.2 AA + best practice) ve IBM Equal Access ihlalleri (Kanun K10); ikisi de boş olmalı. */
export async function erisilebilirlik(page: Page, secici: string): Promise<{ axe: string[]; ibm: string[] }> {
  const axe = await new AxeBuilder({ page }).include(secici)
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa', 'best-practice']).analyze()
  await page.addScriptTag({ path: ACE })
  const ibm = await page.evaluate(async s => {
    // @ts-expect-error — `ace` is the injected engine's global
    const rapor = await new window.ace.Checker().check(document.querySelector(s), ['IBM_Accessibility'])
    return rapor.results.filter((r: { value: string[] }) => r.value[0] === 'VIOLATION' && r.value[1] === 'FAIL')
      .map((r: { ruleId: string }) => r.ruleId)
  }, secici)
  return { axe: axe.violations.map(v => v.id), ibm }
}
