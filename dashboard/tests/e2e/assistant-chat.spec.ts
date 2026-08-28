import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'

// Scopes to the answer body of the most recently added assistant message.
// `.ac-msg__content` also matches the welcome message and the user's own
// echoed prompt, so an unscoped locator hits Playwright's strict-mode "matched
// N elements" error rather than the assertion under test.
function lastAnswerBody(page: Page) {
  return page.locator('.ac-msg--assistant').last().locator('.ac-msg__content')
}

test('assistant answers render markdown rather than raw syntax', async ({ page }) => {
  await page.route('**/api/assistant/chat', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      answer: '## Başlık\n\n- birinci madde\n- ikinci madde [S1]',
      citations: [{ id: 'S1', kind: 'mufredat', label: 'MEB · kesir',
                    locator: {}, snippet: 'kazanım metni', confidence: 0.9 }],
      safety_flags: [], plan_blocks: [], intent: 'qa', session_id: '',
      meta: { model: 'gemini-3.7-flash', degraded: [], dropped_citations: 0 },
    }),
  }))

  await page.goto('/asistan')
  await page.fill('#ac-input', 'kesirler')
  await page.getByLabel('Gönder').click()

  const answerBody = lastAnswerBody(page)
  // markdown.tsx's parseBlocks maps `##` (2 hashes) to <h3>, not <h2> — level
  // is heading[1].length + 1, clamped to [2, 4]. Confirmed by reading the
  // renderer (dashboard/src/utils/markdown.tsx:57) rather than assumed.
  await expect(answerBody.locator('h3')).toHaveText('Başlık')
  await expect(answerBody.locator('li')).toHaveCount(2)
  await expect(answerBody).not.toContainText('##')
  await expect(answerBody.locator('.ac-cite')).toHaveText('1')
})

// renderMarkdown() has four separate renderInline(...) call sites — one each
// for heading, verse line, list item and paragraph — and every one of them
// must be given the citation token hook. Missing even one makes a [S1]
// marker in that block type vanish silently (or, before this task, leaves
// raw "[S1]" text in the DOM once stripInlineCitations() is gone). This test
// puts a distinct citation in a heading, a paragraph, a list item, and a
// verse block in a single answer and checks each renders its chip inside the
// right element, so a regression in any one of the four call sites is caught
// rather than masked by the other three still working.
test('citation chips render inside every markdown block type, not just one', async ({ page }) => {
  const answer = [
    '## Başlık [S4]',
    '',
    'Bu açıklama seksen karakterden uzun bir cümle olduğu için mısra olarak katlanmaz ve paragraf kalır [S2].',
    '',
    '- birinci madde',
    '- ikinci madde [S1]',
    '',
    '> ilk mısra [S3]',
    '> ikinci mısra',
  ].join('\n')

  await page.route('**/api/assistant/chat', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      answer,
      citations: [
        { id: 'S1', kind: 'mufredat', label: 'MEB · kesir', locator: {}, snippet: 'liste kaynağı', confidence: 0.9 },
        { id: 'S2', kind: 'kitap', label: 'Ders Kitabı · s.12', locator: {}, snippet: 'paragraf kaynağı', confidence: 0.8 },
        { id: 'S3', kind: 'oer', label: 'Açık kaynak', locator: {}, snippet: 'mısra kaynağı', confidence: 0.7 },
        { id: 'S4', kind: 'mufredat', label: 'MEB · başlık', locator: {}, snippet: 'başlık kaynağı', confidence: 0.6 },
      ],
      safety_flags: [], plan_blocks: [], intent: 'qa', session_id: '',
      meta: { model: 'gemini-3.7-flash', degraded: [], dropped_citations: 0 },
    }),
  }))

  await page.goto('/asistan')
  await page.fill('#ac-input', 'blok tipleri')
  await page.getByLabel('Gönder').click()

  const answerBody = lastAnswerBody(page)
  await expect(answerBody.locator('h3 .ac-cite')).toHaveText('4')
  await expect(answerBody.locator('p .ac-cite')).toHaveText('2')
  await expect(answerBody.locator('li .ac-cite')).toHaveText('1')
  await expect(answerBody.locator('.bookmd__verse .ac-cite')).toHaveText('3')
  await expect(answerBody).not.toContainText('[S1]')
  await expect(answerBody).not.toContainText('[S2]')
  await expect(answerBody).not.toContainText('[S3]')
  await expect(answerBody).not.toContainText('[S4]')
})

// Bugfix pin (fix round 1): renderInline() matched **bold**/*italic*/_italic_
// as a whole token and pushed the inner text straight into <strong>/<em> via
// token.slice(...), bypassing pushText() entirely. A [S1] marker written
// inside emphasis — "**this is important [S1]**", ordinary model prose —
// never reached CITATION_RE and rendered as dead bracket text instead of a
// chip, which is exactly the failure this task exists to remove. Code spans
// are the deliberate exception: a "[S1]"-shaped string inside `code` is
// sample text, not a citation, and must stay literal.
test('citation chips render inside bold and italic emphasis, but not inside code spans', async ({ page }) => {
  const answer = [
    'Bu satırda kalın vurgulu bir metin epeyce uzun tutuldu ki mısra olarak katlanmasın **önemli bir uyarı [S1]** böyle görünür.',
    '',
    'Bu satırda italik vurgulu bir metin de epeyce uzun tutuldu ki mısra olarak katlanmasın *ikinci bir vurgu [S2]* böyle görünür.',
    '',
    'Bu satırda kod aralığı içeren bir metin de epeyce uzun tutuldu ki mısra olarak katlanmasın `örnek kod [S3]` böyle görünür.',
  ].join('\n')

  await page.route('**/api/assistant/chat', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      answer,
      citations: [
        { id: 'S1', kind: 'mufredat', label: 'MEB · kalın', locator: {}, snippet: 'kalın kaynağı', confidence: 0.9 },
        { id: 'S2', kind: 'mufredat', label: 'MEB · italik', locator: {}, snippet: 'italik kaynağı', confidence: 0.8 },
        { id: 'S3', kind: 'mufredat', label: 'MEB · kod', locator: {}, snippet: 'kod kaynağı', confidence: 0.7 },
      ],
      safety_flags: [], plan_blocks: [], intent: 'qa', session_id: '',
      meta: { model: 'gemini-3.7-flash', degraded: [], dropped_citations: 0 },
    }),
  }))

  await page.goto('/asistan')
  await page.fill('#ac-input', 'vurgu içinde atıf')
  await page.getByLabel('Gönder').click()

  const answerBody = lastAnswerBody(page)
  await expect(answerBody.locator('strong .ac-cite')).toHaveText('1')
  await expect(answerBody.locator('em .ac-cite')).toHaveText('2')
  // Code spans are verbatim by design — no chip, and the raw marker stays.
  await expect(answerBody.locator('code .ac-cite')).toHaveCount(0)
  await expect(answerBody.locator('code')).toContainText('[S3]')
  await expect(answerBody).not.toContainText('[S1]')
  await expect(answerBody).not.toContainText('[S2]')
})
