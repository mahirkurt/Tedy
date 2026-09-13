import { test, expect } from '@playwright/test'
import { json } from './_audit-fixtures'

// Carbon for AI treats the AI mark as a claim about provenance that must be
// explainable. This surface carried the mark without the explanation, and
// carried it in places nothing was generated.

const ANSWER = {
  answer: 'Paydaları eşitleyerek başlarsın [S1].',
  citations: [{ id: 'S1', kind: 'mufredat', label: 'MEB · kesirler',
                locator: {}, snippet: 'Payda eşitlenir.', confidence: 0.9 }],
  safety_flags: [], plan_blocks: [], intent: 'qa', session_id: '',
  meta: { model: 'gemini-3.7-flash', degraded: [], dropped_citations: 0 },
}

async function ask(page: import('@playwright/test').Page) {
  await page.route('**/api/assistant/stream', r => r.abort())
  await page.route('**/api/assistant/chat', r => r.fulfill(json(ANSWER)))
  await page.goto('/asistan')
  await page.waitForLoadState('networkidle')
  await page.fill('#ac-input', 'kesirler')
  await page.getByLabel('Gönder').click()
  // The answer carries [S1], so its chip existing is the proof the reply has
  // rendered. Callers read computed styles straight after this, and
  // evaluate() does not retry.
  await page.locator('.ac-cite').first().waitFor()
}

test('the AI label explains itself instead of just marking', async ({ page }) => {
  // <AILabel size="xl" /> rendered Carbon's AI slug with no content at all:
  // a badge saying "AI" that answered no question about what the AI is.
  await page.route('**/api/assistant/stream', r => r.abort())
  await page.goto('/asistan')
  await page.waitForLoadState('networkidle')

  const slug = page.locator('.ac__header .cds--ai-label__button').first()
  await expect(slug).toBeVisible()
  await slug.click()

  // Both expects below retry until the popover has opened.
  const pop = page.locator('.ac__header .cds--ai-label-content')
  await expect(pop).toBeVisible()
  // It has to say what the thing is and that its answers are checkable.
  // Match the stem, not the word: Turkish softens the final k, so the copy
  // says "kaynağı" and "kaynağa" and never the bare "kaynak".
  await expect(pop).toContainText(/kayna[kğ]/i)
})

test('the model that answered is disclosed', async ({ page }) => {
  // meta.model came back on every response and was shown to nobody, while
  // the backend actually cycles through a chain of models.
  await ask(page)
  // Disclosure lives in the AI label's explanation rather than on screen at
  // all times — the model name is something to be able to find, not
  // something to read past on every answer (İ6).
  await page.locator('.ac__header .cds--ai-label__button').click()
  await expect(page.locator('.ac__header .cds--ai-label-content'))
    .toContainText('gemini-3.7-flash')
})

test('the AI aura marks what the model wrote, not what Işık wrote', async ({ page }) => {
  // The user's own bubble was painted in ai-aura-hover-background — the
  // child's words marked as machine output.
  await ask(page)
  const bg = await page.locator('.ac-msg--user .ac-msg__body').first()
    .evaluate(el => getComputedStyle(el).backgroundColor)
  // g10 ai-aura-hover-background is #edf5ff.
  expect(bg.replace(/\s/g, '')).not.toBe('rgb(237,245,255)')
})

test('the AI aura stays off the sources, which are quotes', async ({ page }) => {
  // An active citation is a line from the MEB curriculum or a textbook. The
  // AI aura on it is a false claim about where the words came from.
  await ask(page)
  await page.locator('.ac-cite').first().click()
  // Assert the state exists before asserting anything about it — otherwise
  // a citation that never activates makes this pass by absence. This expect
  // retries, so it is also the wait for the click to take effect.
  const active = page.locator('.ac__ref-item--active')
  await expect(active).toHaveCount(1)
  const bg = await active.evaluate(el => getComputedStyle(el).backgroundImage)
  expect(bg, 'kaynak satırında AI gradyanı').toBe('none')
})

test('the assistant answer keeps its AI treatment', async ({ page }) => {
  // The one place the mark belongs.
  await ask(page)
  const bg = await page.locator('.ac-msg--assistant .ac-msg__body').last()
    .evaluate(el => getComputedStyle(el).backgroundImage)
  expect(bg, 'üretilen yanıtta AI gradyanı yok').toContain('gradient')
})

test('the assistant stylesheet names no colour of its own', async () => {
  // D1: tokens are mandatory. Checked against the source rather than the
  // bundle — a bundle necessarily contains literals, because that is what a
  // token definition is (Carbon itself ships #001d6c as --cds-highlight), so
  // scanning the built CSS only measured whether the scan was wide enough.
  const fs = await import('node:fs/promises')
  const src = await fs.readFile(
    new URL('../../src/components/AssistantChat.scss', import.meta.url), 'utf8')
  const offenders = src
    .split('\n')
    .map((line, i) => ({ line: line.replace(/\/\/.*$/, ''), n: i + 1 }))
    .filter(x => /(#[0-9a-fA-F]{3,8}\b|\brgba?\()/.test(x.line))
    .map(x => `${x.n}: ${x.line.trim()}`)
  expect(offenders, 'token yerine değişmez renk').toEqual([])
})
