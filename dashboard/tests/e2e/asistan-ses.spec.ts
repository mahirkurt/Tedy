import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'
import { sabitAc } from './_gorsel-yardim'
import { json } from './_audit-fixtures'

const CEVAP = { answer: 'Payda **eşitlenir** [S1].', citations: [{ id: 'S1', kind: 'mufredat', label: 'Payda', locator: {}, snippet: 'Paydalar eşitlenir.', confidence: 0.9 }], safety_flags: [], plan_blocks: [], intent: 'qa', session_id: '', meta: { model: 'test', degraded: [] } }

async function sesKur(page: Page, dil = 'tr-TR', mikrofon = true) {
  await page.addInitScript(({ dil, mikrofon }) => {
    const state = { spoken: [] as { text: string; lang: string; rate: number; pitch: number; volume: number }[], canceled: 0, started: 0, stopped: 0 }
    Object.assign(window, { __ses: state })
    Object.defineProperty(window, 'SpeechSynthesisUtterance', { configurable: true, value: class {
      text: string
      constructor(text: string) { this.text = text }
    } })
    Object.defineProperty(window, 'speechSynthesis', { configurable: true, value: {
      getVoices: () => [{ lang: dil }], cancel: () => { state.canceled++ },
      speak: (u: SpeechSynthesisUtterance) => { state.spoken.push({ text: u.text, lang: u.lang, rate: u.rate, pitch: u.pitch, volume: u.volume }) },
      addEventListener: () => {}, removeEventListener: () => {},
    } })
    Object.assign(window, { SpeechRecognition: undefined, webkitSpeechRecognition: mikrofon ? class {
      onend?: () => void
      constructor() { Object.assign(window, { __rec: this }) }
      start() { state.started++ }
      stop() { state.stopped++; this.onend?.() }
      abort() { this.onend?.() }
    } : undefined })
  }, { dil, mikrofon })
}

async function hazir(page: Page) {
  await sabitAc(page, '/asistan', 1440, 900)
  await page.route('**/api/assistant/stream', r => r.abort())
  await page.route('**/api/assistant/chat', r => r.fulfill(json(CEVAP)))
}

test('read-aloud strips marks, stops, and replaces the previous utterance', async ({ page }) => {
  await sesKur(page)
  await hazir(page)
  await expect(page.getByRole('button', { name: 'Sesli oku' })).toHaveCount(0)
  await page.fill('#ac-input', 'Payda?')
  await page.getByRole('button', { name: 'Gönder', exact: true }).click()
  const read = page.getByRole('button', { name: 'Sesli oku' })
  await read.click()
  await expect(page.getByRole('button', { name: 'Durdur', exact: true })).toHaveAttribute('aria-pressed', 'true')
  const state = await page.evaluate(() => (window as unknown as { __ses: { spoken: unknown[] } }).__ses)
  expect(state.spoken).toEqual([{ text: 'Payda eşitlenir.', lang: 'tr-TR', rate: 1, pitch: 1, volume: 1 }])
  await page.getByRole('button', { name: 'Durdur', exact: true }).click()
  await expect(read).toBeVisible()
})

test('unsupported voices and recognition hide controls', async ({ page }) => {
  await sesKur(page, 'en-US', false)
  await hazir(page)
  await page.fill('#ac-input', 'Payda?')
  await page.getByRole('button', { name: 'Gönder', exact: true }).click()
  await expect(page.getByText('Payda eşitlenir', { exact: false })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Sesli oku' })).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Sesle sor' })).toHaveCount(0)
})

test('microphone waits for consent, replaces interim text, and never auto-sends', async ({ page }) => {
  await sesKur(page)
  await hazir(page)
  let sent = 0
  await page.route('**/api/assistant/stream', r => { sent++; return r.fulfill({ contentType: 'text/event-stream', body: `event: answer\ndata: ${JSON.stringify({ payload: CEVAP })}\n\n` }) })
  await page.getByRole('button', { name: 'Sesle sor', exact: true }).click()
  await expect(page.getByText("Chrome ve Android'de konuşma tanıma sesi Google'a gönderir.")).toBeVisible()
  expect(await page.evaluate(() => (window as unknown as { __ses: { started: number } }).__ses.started)).toBe(0)
  await page.getByRole('button', { name: 'Vazgeç', exact: true }).click()
  await page.getByRole('button', { name: 'Sesle sor', exact: true }).click()
  await page.getByRole('button', { name: 'Onayla', exact: true }).click()
  expect(await page.evaluate(() => localStorage.getItem('tedy-ses-onay::test@tedy.online'))).toBe('1')
  for (const text of ['kesir', 'kesir kaçtır']) {
    await page.evaluate(text => (window as unknown as { __rec: { onresult: (e: unknown) => void } }).__rec.onresult({ results: [[{ transcript: text }]] }), text)
    await expect(page.locator('#ac-input')).toHaveValue(text)
  }
  expect(sent).toBe(0)
  await page.getByRole('button', { name: 'Dinlemeyi bitir', exact: true }).click()
  await expect(page.locator('#ac-input')).toBeFocused()
  await page.getByRole('button', { name: 'Gönder', exact: true }).click()
  await expect.poll(() => sent).toBe(1)
})

test('denied permission is a separate Turkish error', async ({ page }) => {
  await sesKur(page)
  await page.addInitScript(() => localStorage.setItem('tedy-ses-onay::test@tedy.online', '1'))
  await hazir(page)
  await page.getByRole('button', { name: 'Sesle sor', exact: true }).click()
  await page.evaluate(() => (window as unknown as { __rec: { onerror: (e: unknown) => void } }).__rec.onerror({ error: 'not-allowed' }))
  await expect(page.getByText('Mikrofon açılamadı.')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Tekrar dene' })).toHaveCount(0)
})

test('family can read aloud but cannot dictate into a student conversation', async ({ page }) => {
  await sesKur(page)
  await hazir(page)
  const row = { id: 'cd'.repeat(16), baslik: 'Kesirler', ogretmen: 'matematik' }
  await page.route('**/api/assistant/sohbetler?*', r => r.fulfill(json({ sohbetler: [row] })))
  await page.route(`**/api/assistant/sohbetler/${row.id}`, r => r.fulfill(json({ sohbet: row, read_only: true,
    mesajlar: [{ id: 'ef'.repeat(16), rol: 'assistant', icerik: CEVAP.answer, atiflar_json: JSON.stringify(CEVAP.citations), ekler_json: '[]' }] })))
  await page.reload()
  await page.getByRole('button', { name: 'Kesirler', exact: true }).click()
  await expect(page.locator('#ac-input')).toBeDisabled()
  await expect(page.getByText('Bu sohbet salt okunur.')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Sesle sor' })).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Sesli oku' })).toBeVisible()
})
