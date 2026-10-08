import { expect } from '@playwright/test'
import type { Page } from '@playwright/test'
import { mockSohbetler } from './_audit-fixtures'

export const sse = (...c: [string, unknown][]) => c.map(([a, v]) => `event: ${a}\ndata: ${JSON.stringify(v)}\n\n`).join('')
export const PAYLOAD = (p: Record<string, unknown> = {}) => ({ answer: 'Cevap metni.', citations: [], safety_flags: [], plan_blocks: [],
  intent: 'qa', session_id: '', meta: { model: 'claude-sonnet-5', degraded: [] }, ...p })

/** Her soru gönderen test iki ucu da kendisi yanıtlar: yanıtsız akış /chat'e düşer ve oyun sunucusunda
 *  gerçek çalışma zamanına ulaşır (bilinen tuzak). */
export async function cevapla(page: Page, payload: Record<string, unknown>, olaylar: [string, unknown][] = []) {
  const istekler: Record<string, unknown>[] = []
  await page.route('**/api/assistant/stream', async r => {
    istekler.push(r.request().postDataJSON())
    await r.fulfill({ status: 200, contentType: 'text/event-stream', body: sse(...olaylar, ['answer', { payload }], ['done', {}]) })
  })
  await page.route('**/api/assistant/chat', async r => { istekler.push(r.request().postDataJSON()); await r.fulfill({ json: payload }) })
  return istekler
}
export const soruAlani = (page: Page) => page.getByRole('textbox', { name: 'Sorunu yaz' })
export const gonderDugmesi = (page: Page) => page.getByRole('button', { name: 'Gönder', exact: true })
export async function asistanAc(page: Page, yol = '/asistan') {
  await mockSohbetler(page)
  await page.goto(yol)
  await expect(soruAlani(page)).toBeVisible({ timeout: 15000 })
}
export async function sor(page: Page, metin: string) {
  await soruAlani(page).fill(metin)
  await gonderDugmesi(page).click()
}
