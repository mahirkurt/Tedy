import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'
import { json } from './_audit-fixtures'
import { OGRETMENLER } from './_gorsel-fixtures'
import { sabitAc } from './_gorsel-yardim'

// Öğretmen modları (spec §1, plan B1): the selector, its memory, each teacher's
// theme, greeting and quick prompts, and the request carrying the mode.

test.use({ timezoneId: 'Europe/Istanbul', locale: 'tr-TR' })

// The fixture's auth/me is test@tedy.online, a family member (student: false).
const ANAHTAR = 'tedy-asistan-ogretmen::test@tedy.online'
// The send button's fill: Carbon's button-primary (blue-60) in Genel, the
// family's accent (the -60 palette step, theme/_subjects.scss) in a teacher mode.
const VURGU: Record<string, string> = {
  genel: 'rgb(15, 98, 254)',
  turkce: 'rgb(208, 38, 112)',
  fen: 'rgb(0, 125, 121)',
  sosyal: 'rgb(0, 114, 195)',
  matematik: 'rgb(138, 63, 252)',
}
const ADLAR = ['Genel', 'Türkçe', 'Fen', 'Sosyal', 'Matematik']

// A canned answer: no test here may let a question reach the real model.
function cevap(extra: Record<string, unknown> = {}) {
  return {
    answer: 'Oran, iki çokluğun bölme yoluyla karşılaştırılmasıdır.', citations: [], safety_flags: [],
    plan_blocks: [], intent: 'qa', session_id: '',
    meta: { model: 'claude-sonnet-5', degraded: [], ogretmen: 'genel' }, ...extra,
  }
}

async function hatirla(page: Page, id: string) {
  await page.addInitScript(([k, v]) => localStorage.setItem(k, v), [ANAHTAR, id])
}

async function asistan(page: Page, w = 1440, h = 900) {
  await sabitAc(page, '/asistan', w, h)
  await expect(page.getByRole('group', { name: 'Öğretmen' })).toBeVisible()
}

const kok = (page: Page) => page.locator('section.ac')
// The chip, as a reader clicks it (the radio itself is visually hidden).
const sec = (page: Page, ad: string) =>
  page.getByRole('group', { name: 'Öğretmen' }).getByText(ad, { exact: true }).click()

test('five teachers in order, Genel chosen at first', async ({ page }) => {
  await asistan(page)
  const secenekler = page.getByRole('group', { name: 'Öğretmen' }).getByRole('radio')
  await expect(secenekler).toHaveCount(5)
  for (const [i, ad] of ADLAR.entries()) await expect(secenekler.nth(i)).toHaveAccessibleName(ad)
  await expect(page.getByRole('radio', { name: 'Genel' })).toBeChecked()
  await expect(kok(page)).toHaveAttribute('data-ogretmen', 'genel')
})

test('arrow keys move through the teachers and the choice is remembered', async ({ page }) => {
  await asistan(page)
  await page.getByRole('radio', { name: 'Genel' }).focus()
  await page.keyboard.press('ArrowRight')
  await expect(page.getByRole('radio', { name: 'Türkçe' })).toBeChecked()
  await page.keyboard.press('ArrowRight')
  await expect(page.getByRole('radio', { name: 'Fen' })).toBeChecked()
  await expect(kok(page)).toHaveAttribute('data-ogretmen', 'fen')
  expect(await page.evaluate(k => localStorage.getItem(k), ANAHTAR)).toBe('fen')
  await page.reload()
  await expect(page.getByRole('radio', { name: 'Fen' })).toBeChecked()
})

for (const id of Object.keys(VURGU)) {
  test(`${id}: the theme follows the teacher, the brand band does not`, async ({ page }) => {
    await asistan(page)
    const bant = await page.locator('.cds--header').evaluate(el => getComputedStyle(el).backgroundColor)
    await sec(page, ADLAR[Object.keys(VURGU).indexOf(id)])
    await expect(kok(page)).toHaveAttribute('data-ogretmen', id)
    // A disabled button draws Carbon's disabled fill; type to enable it. toHaveCSS
    // retries: Carbon's button eases its fill in from the disabled grey.
    await page.fill('#ac-input', 'x')
    await expect(page.getByRole('button', { name: 'Gönder' })).toHaveCSS('background-color', VURGU[id])
    expect(await page.locator('.cds--header').evaluate(el => getComputedStyle(el).backgroundColor)).toBe(bant)
  })
}

test('a teacher brings its own greeting and quick prompts', async ({ page }) => {
  await hatirla(page, 'matematik')
  await asistan(page)
  const mat = OGRETMENLER.ogretmenler[3]
  await expect(page.locator('.ac-msg--assistant').first()).toContainText(mat.karsilama.aile)
  await expect(page.locator('.ac__prompt-chip')).toHaveText(mat.hizli_sorular.aile)
  await expect(page.locator('.ac__subtitle')).toHaveText('Matematik öğretmeni — konuyu adım adım anlatır')
})

test('a remembered teacher that no longer exists reads as Genel', async ({ page }) => {
  await hatirla(page, 'tarih')
  await asistan(page)
  await expect(page.getByRole('radio', { name: 'Genel' })).toBeChecked()
  await expect(kok(page)).toHaveAttribute('data-ogretmen', 'genel')
})

test('the request carries the chosen teacher', async ({ page }) => {
  await hatirla(page, 'fen')
  await asistan(page)
  // Both answered here: an unanswered stream falls back to /chat, and /chat
  // must never reach the real model.
  await page.route('**/api/assistant/stream', r => r.abort())
  await page.route('**/api/assistant/chat', r => r.fulfill(json(cevap())))
  const akis = page.waitForRequest('**/api/assistant/stream')
  const klasik = page.waitForRequest('**/api/assistant/chat')
  await page.fill('#ac-input', 'Mercek nedir?')
  await page.getByRole('button', { name: 'Gönder' }).click()
  expect((await akis).postDataJSON().ogretmen).toBe('fen')
  expect((await klasik).postDataJSON().ogretmen).toBe('fen')
})

test('a list that failed says so and Genel still works', async ({ page }) => {
  await sabitAc(page, '/asistan', 1440, 900)
  await page.route('**/api/assistant/ogretmenler', r => r.fulfill({ status: 503, body: '{}' }))
  await page.reload()
  await expect(page.getByRole('group', { name: 'Öğretmen' }).getByRole('radio')).toHaveCount(1)
  await expect(page.getByText('Öğretmen modları şu an yüklenemedi; Genel modda sorabilirsiniz.')).toBeVisible()
})

// ── mod_oner: a suggestion is a button, never a switch ─────────────────────

const ONERI = {
  ogretmen: 'matematik', ogretmen_adi: 'Matematik öğretmeni',
  soru: 'Matematik öğretmenine geçelim mi?',
  gerekce: 'Bu bir oran-orantı sorusu; Matematik öğretmeni adım adım çözer.',
  renk_ailesi: 'purple',
}


const sse = (...olaylar: [string, unknown][]) =>
  olaylar.map(([ad, veri]) => `event: ${ad}\ndata: ${JSON.stringify(veri)}\n\n`).join('')

async function sor(page: Page) {
  await page.fill('#ac-input', 'Oran nedir?')
  await page.getByRole('button', { name: 'Gönder' }).click()
  await expect(page.locator('.ac-msg--assistant')).toHaveCount(2)
}

test('a suggestion from the stream shows a button and changes nothing by itself', async ({ page }) => {
  await asistan(page)
  await page.route('**/api/assistant/stream', r => r.fulfill({
    status: 200, contentType: 'text/event-stream',
    body: sse(['tool_start', { name: 'mod_oner' }], ['tool_end', { name: 'mod_oner', ok: true }],
      ['mode_suggestion', ONERI], ['answer', { payload: cevap() }], ['done', {}]),
  }))
  await sor(page)
  const dugme = page.getByRole('button', { name: 'Matematik öğretmenine geçelim mi?' })
  await expect(dugme).toBeVisible()
  await expect(page.getByText(ONERI.gerekce)).toBeVisible()
  // Nothing switched on its own.
  await expect(kok(page)).toHaveAttribute('data-ogretmen', 'genel')
  await expect(page.getByRole('radio', { name: 'Genel' })).toBeChecked()
  expect(await page.evaluate(k => localStorage.getItem(k), ANAHTAR)).toBeNull()

  await dugme.click()
  await expect(kok(page)).toHaveAttribute('data-ogretmen', 'matematik')
  await expect(page.getByRole('radio', { name: 'Matematik' })).toBeChecked()
  expect(await page.evaluate(k => localStorage.getItem(k), ANAHTAR)).toBe('matematik')
  await expect(dugme).toHaveCount(0)          // in a teacher mode there is nothing to suggest
})

test('the classic endpoint carries the suggestion too', async ({ page }) => {
  await asistan(page)
  await page.route('**/api/assistant/stream', r => r.abort())
  await page.route('**/api/assistant/chat', r => r.fulfill(json(cevap({ mode_suggestion: ONERI }))))
  await sor(page)
  await expect(page.getByRole('button', { name: 'Matematik öğretmenine geçelim mi?' })).toBeVisible()
  await expect(kok(page)).toHaveAttribute('data-ogretmen', 'genel')
})

test('no suggestion, no button', async ({ page }) => {
  await asistan(page)
  await page.route('**/api/assistant/stream', r => r.fulfill({
    status: 200, contentType: 'text/event-stream',
    body: sse(['answer', { payload: cevap() }], ['done', {}]),
  }))
  await sor(page)
  await expect(page.locator('.ac-msg--assistant').last()).toContainText('Oran, iki çokluğun')
  await expect(page.locator('.ac-msg__oneri')).toHaveCount(0)
})
