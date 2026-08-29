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
  // The stream endpoint is real backend code, not mocked here — a bare
  // page.route on '**/api/assistant/chat' does not intercept it, so an
  // unmocked stream call would reach the actual dashboard server (and, in
  // this worktree, its real GEMINI_API_KEY) on every one of these tests.
  // Aborting it in-browser keeps the suite network-free and deterministic;
  // AssistantChat.tsx's own catch block sends the request on to the
  // classic endpoint mocked immediately below, which is what every
  // assertion in this file is actually pinned to.
  await page.route('**/api/assistant/stream', route => route.abort())
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

  // The stream endpoint is real backend code, not mocked here — a bare
  // page.route on '**/api/assistant/chat' does not intercept it, so an
  // unmocked stream call would reach the actual dashboard server (and, in
  // this worktree, its real GEMINI_API_KEY) on every one of these tests.
  // Aborting it in-browser keeps the suite network-free and deterministic;
  // AssistantChat.tsx's own catch block sends the request on to the
  // classic endpoint mocked immediately below, which is what every
  // assertion in this file is actually pinned to.
  await page.route('**/api/assistant/stream', route => route.abort())
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

  // The stream endpoint is real backend code, not mocked here — a bare
  // page.route on '**/api/assistant/chat' does not intercept it, so an
  // unmocked stream call would reach the actual dashboard server (and, in
  // this worktree, its real GEMINI_API_KEY) on every one of these tests.
  // Aborting it in-browser keeps the suite network-free and deterministic;
  // AssistantChat.tsx's own catch block sends the request on to the
  // classic endpoint mocked immediately below, which is what every
  // assertion in this file is actually pinned to.
  await page.route('**/api/assistant/stream', route => route.abort())
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

test('sources are grouped by kind and the cited one highlights', async ({ page }) => {
  // The stream endpoint is real backend code, not mocked here — a bare
  // page.route on '**/api/assistant/chat' does not intercept it, so an
  // unmocked stream call would reach the actual dashboard server (and, in
  // this worktree, its real GEMINI_API_KEY) on every one of these tests.
  // Aborting it in-browser keeps the suite network-free and deterministic;
  // AssistantChat.tsx's own catch block sends the request on to the
  // classic endpoint mocked immediately below, which is what every
  // assertion in this file is actually pinned to.
  await page.route('**/api/assistant/stream', route => route.abort())
  await page.route('**/api/assistant/chat', route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({
      answer: 'Ödevin [S1] ve kazanım [S2].',
      citations: [
        { id: 'S1', kind: 'ogrenci', label: 'scraped_data.json', locator: {}, snippet: 'ödev', confidence: 0.8 },
        { id: 'S2', kind: 'mufredat', label: 'MEB · kesir', locator: {}, snippet: 'kazanım', confidence: 0.9 },
      ],
      safety_flags: [], plan_blocks: [], intent: 'qa', session_id: '',
      meta: { model: 'gemini-3.7-flash', degraded: [], dropped_citations: 0 },
    }),
  }))

  await page.goto('/asistan')
  await page.fill('#ac-input', 'ödevim ne')
  await page.getByLabel('Gönder').click()

  await expect(page.locator('.ac__ref-group')).toHaveCount(2)
  await expect(page.locator('.ac__ref-group-title').first()).toContainText('okul verisi')

  await page.locator('.ac-cite').first().click()
  await expect(page.locator('.ac__ref-item--active')).toHaveCount(1)
})

test('a degraded answer says so', async ({ page }) => {
  // The stream endpoint is real backend code, not mocked here — a bare
  // page.route on '**/api/assistant/chat' does not intercept it, so an
  // unmocked stream call would reach the actual dashboard server (and, in
  // this worktree, its real GEMINI_API_KEY) on every one of these tests.
  // Aborting it in-browser keeps the suite network-free and deterministic;
  // AssistantChat.tsx's own catch block sends the request on to the
  // classic endpoint mocked immediately below, which is what every
  // assertion in this file is actually pinned to.
  await page.route('**/api/assistant/stream', route => route.abort())
  await page.route('**/api/assistant/chat', route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({
      answer: 'Yalnız okul verisiyle yanıt.', citations: [],
      safety_flags: [], plan_blocks: [], intent: 'qa', session_id: '',
      meta: { model: 'gemini-3.7-flash', degraded: ['maarif-mufredat'], dropped_citations: 0 },
    }),
  }))

  await page.goto('/asistan')
  await page.fill('#ac-input', 'kesir')
  await page.getByLabel('Gönder').click()

  await expect(page.locator('.ac-msg__degraded')).toContainText('Müfredat kaynağına ulaşılamadı')
})

// The load-bearing assertion for this task: a risk:* flag (genuine crisis
// escalation) must render visibly distinct from a warning:* flag (routine,
// tool-free "no sources" note) — same red Tag for both would let a common,
// harmless warning desensitise readers to the rare, serious one. Also pins
// that the warning's label is the friendly Turkish string, not the raw
// "warning:limited_confidence" token a 6th-grader would otherwise see.
test('risk and warning safety flags render with different severity, not as raw tokens', async ({ page }) => {
  // The stream endpoint is real backend code, not mocked here — a bare
  // page.route on '**/api/assistant/chat' does not intercept it, so an
  // unmocked stream call would reach the actual dashboard server (and, in
  // this worktree, its real GEMINI_API_KEY) on every one of these tests.
  // Aborting it in-browser keeps the suite network-free and deterministic;
  // AssistantChat.tsx's own catch block sends the request on to the
  // classic endpoint mocked immediately below, which is what every
  // assertion in this file is actually pinned to.
  await page.route('**/api/assistant/stream', route => route.abort())
  await page.route('**/api/assistant/chat', route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({
      answer: 'Bu konuda dikkatli olmalıyız.',
      citations: [],
      safety_flags: ['risk:mental_health_crisis', 'warning:limited_confidence'],
      plan_blocks: [], intent: 'qa', session_id: '',
      meta: { model: 'gemini-3.7-flash', degraded: [], dropped_citations: 0 },
    }),
  }))

  await page.goto('/asistan')
  await page.fill('#ac-input', 'zor bir gün geçiriyorum')
  await page.getByLabel('Gönder').click()

  const flags = page.locator('.ac-msg--assistant').last().locator('.ac-msg__flags .cds--tag')
  await expect(flags).toHaveCount(2)

  const riskTag = flags.filter({ hasText: 'mental_health_crisis' })
  const warningTag = flags.filter({ hasText: 'Kaynaksız cevap' })
  await expect(riskTag).toHaveCount(1)
  await expect(warningTag).toHaveCount(1)

  // Different severity → different Carbon Tag `type` → different modifier class.
  await expect(riskTag).toHaveClass(/cds--tag--red/)
  await expect(warningTag).not.toHaveClass(/cds--tag--red/)
  await expect(warningTag).toHaveClass(/cds--tag--gray/)

  // The raw token must never reach the reader.
  await expect(page.locator('.ac-msg--assistant').last()).not.toContainText('warning:limited_confidence')
})

// Fix round 1, Bulgu 1: `meta.degraded` is a list, and the UI was treating it
// like a boolean by rendering a single Tag. When two servers failed
// independently, the second one's name and existence had no trace on
// screen. Every degraded server must surface — the known one with its
// friendly Turkish label, the unrecognised one by its own raw name rather
// than being silently dropped or folded into the known message.
test('every degraded source surfaces, not just the first', async ({ page }) => {
  // The stream endpoint is real backend code, not mocked here — a bare
  // page.route on '**/api/assistant/chat' does not intercept it, so an
  // unmocked stream call would reach the actual dashboard server (and, in
  // this worktree, its real GEMINI_API_KEY) on every one of these tests.
  // Aborting it in-browser keeps the suite network-free and deterministic;
  // AssistantChat.tsx's own catch block sends the request on to the
  // classic endpoint mocked immediately below, which is what every
  // assertion in this file is actually pinned to.
  await page.route('**/api/assistant/stream', route => route.abort())
  await page.route('**/api/assistant/chat', route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({
      answer: 'Kısmi yanıt.', citations: [],
      safety_flags: [], plan_blocks: [], intent: 'qa', session_id: '',
      meta: {
        model: 'gemini-3.7-flash',
        degraded: ['maarif-mufredat', 'some-other-server'],
        dropped_citations: 0,
      },
    }),
  }))

  await page.goto('/asistan')
  await page.fill('#ac-input', 'kesir')
  await page.getByLabel('Gönder').click()

  const degraded = page.locator('.ac-msg--assistant').last().locator('.ac-msg__degraded')
  await expect(degraded.locator('.cds--tag')).toHaveCount(2)
  await expect(degraded).toContainText('Müfredat kaynağına ulaşılamadı')
  // The unmapped server is not swallowed by the known one's badge — it gets
  // its own badge, named.
  await expect(degraded).toContainText('some-other-server')
})

// Fix round 1, Bulgu 2: an unrecognised `kind` used to vanish from the
// source panel entirely (GROUP_ORDER.map + filter dropped anything outside
// the four known kinds) while its inline [S#] chip kept rendering in the
// answer — a dead click with zero signal. It must now get its own,
// separately labelled group (never folded into `ogrenci` or `mufredat`,
// since that authority split is load-bearing), and clicking its chip must
// still highlight the matching card. CitationChip's popover/aria-label must
// not leak the literal string "undefined" for the same unrecognised kind.
test('citations with an unknown kind get their own group, not folded into ogrenci or mufredat, and their chip still highlights', async ({ page }) => {
  // The stream endpoint is real backend code, not mocked here — a bare
  // page.route on '**/api/assistant/chat' does not intercept it, so an
  // unmocked stream call would reach the actual dashboard server (and, in
  // this worktree, its real GEMINI_API_KEY) on every one of these tests.
  // Aborting it in-browser keeps the suite network-free and deterministic;
  // AssistantChat.tsx's own catch block sends the request on to the
  // classic endpoint mocked immediately below, which is what every
  // assertion in this file is actually pinned to.
  await page.route('**/api/assistant/stream', route => route.abort())
  await page.route('**/api/assistant/chat', route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({
      answer: 'Bilinen kaynak [S1] ve tanınmayan kaynak [S2].',
      citations: [
        { id: 'S1', kind: 'ogrenci', label: 'scraped_data.json', locator: {}, snippet: 'ödev', confidence: 0.8 },
        { id: 'S2', kind: 'harici', label: 'Bilinmeyen kaynak', locator: {}, snippet: 'harici parça', confidence: 0.5 },
      ],
      safety_flags: [], plan_blocks: [], intent: 'qa', session_id: '',
      meta: { model: 'gemini-3.7-flash', degraded: [], dropped_citations: 0 },
    }),
  }))

  await page.goto('/asistan')
  await page.fill('#ac-input', 'karışık kaynaklar')
  await page.getByLabel('Gönder').click()

  // Two groups: the known `ogrenci` group and a separate unclassified group.
  await expect(page.locator('.ac__ref-group')).toHaveCount(2)
  const groupTitles = page.locator('.ac__ref-group-title')
  await expect(groupTitles.first()).toContainText('okul verisi')
  await expect(groupTitles.last()).toContainText('Sınıflandırılmamış')

  // The unknown-kind citation must not be listed under the known group.
  const knownGroup = page.locator('.ac__ref-group').first()
  await expect(knownGroup).not.toContainText('Bilinmeyen kaynak')

  // Clicking its chip is not a dead click — the matching card highlights.
  await page.locator('.ac-cite').nth(1).click()
  await expect(page.locator('.ac__ref-item--active')).toHaveCount(1)
  await expect(page.locator('.ac__ref-item--active')).toContainText('Bilinmeyen kaynak')

  // CitationChip must never leak the literal "undefined" string for an
  // unrecognised kind, in the accessible name or the popover body.
  const unknownChip = page.locator('.ac-cite').nth(1)
  const ariaLabel = await unknownChip.getAttribute('aria-label')
  expect(ariaLabel).not.toContain('undefined')
  await unknownChip.hover()
  // Both citations' popovers exist in the DOM (Carbon's Popover keeps its
  // content mounted and toggles visibility), so scope to the one the hover
  // just opened rather than an unscoped locator that matches both.
  await expect(page.locator('.ac-cite__pop').getByText('Bilinmeyen kaynak')).toBeVisible()
  await expect(page.locator('.ac-cite__pop').last()).not.toContainText('undefined')
})
