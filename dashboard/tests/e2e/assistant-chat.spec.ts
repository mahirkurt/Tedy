import { createServer } from 'node:http'
import type { IncomingMessage, ServerResponse } from 'node:http'
import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'

// Scopes to the answer body of the most recently added assistant message.
// `.ac-msg__content` also matches the welcome message and the user's own
// echoed prompt, so an unscoped locator hits Playwright's strict-mode "matched
// N elements" error rather than the assertion under test.
function lastAnswerBody(page: Page) {
  return page.locator('.ac-msg--assistant').last().locator('.ac-msg__content')
}

// A real, incrementally-delivered SSE responder. Unlike `page.route(...).fulfill()`
// — which hands the browser a single complete body — this is an actual local
// HTTP server that writes one frame, waits, writes the next, and so on. That
// difference is the whole point of the test that uses it: a fulfilled body
// arrives to the page as one chunk, so every event in it lands in the same
// synchronous pass and a test can never observe an *intermediate* render (the
// tool-progress label appearing before the answer). A genuinely staggered
// response can, because the frontend's `reader.read()` loop really does await
// between frames — the same way it would against the real backend.
//
// CORS is hand-rolled because this server listens on its own ephemeral port,
// which makes every request to it cross-origin from the page's perspective;
// AssistantChat.tsx always sends `credentials: 'include'`, so a wildcard
// `Access-Control-Allow-Origin` will not do — the browser requires the exact
// requesting origin plus `Access-Control-Allow-Credentials: true`, and a
// JSON POST triggers a real preflight this server must also answer.
function startStaggeredSseServer(frames: string[], delayMs = 120) {
  const server = createServer((req: IncomingMessage, res: ServerResponse) => {
    const origin = req.headers.origin
    if (origin) {
      res.setHeader('Access-Control-Allow-Origin', origin)
      res.setHeader('Access-Control-Allow-Credentials', 'true')
    }
    res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS')
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type')
    if (req.method === 'OPTIONS') {
      res.writeHead(204)
      res.end()
      return
    }
    res.writeHead(200, {
      'Content-Type': 'text/event-stream; charset=utf-8',
      'Cache-Control': 'no-cache',
    })
    let i = 0
    const sendNext = () => {
      if (i >= frames.length) {
        res.end()
        return
      }
      res.write(frames[i])
      i += 1
      setTimeout(sendNext, delayMs)
    }
    sendNext()
  })
  return new Promise<{ port: number; close: () => Promise<void> }>((resolve, reject) => {
    server.on('error', reject)
    server.listen(0, '127.0.0.1', () => {
      const address = server.address()
      const port = typeof address === 'object' && address ? address.port : 0
      resolve({
        port,
        close: () => new Promise<void>(r => server.close(() => r())),
      })
    })
  })
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
      meta: { model: 'claude-sonnet-5', degraded: [], dropped_citations: 0 },
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
      meta: { model: 'claude-sonnet-5', degraded: [], dropped_citations: 0 },
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
      meta: { model: 'claude-sonnet-5', degraded: [], dropped_citations: 0 },
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
      meta: { model: 'claude-sonnet-5', degraded: [], dropped_citations: 0 },
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
      meta: { model: 'claude-sonnet-5', degraded: ['maarif-mufredat'], dropped_citations: 0 },
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
      meta: { model: 'claude-sonnet-5', degraded: [], dropped_citations: 0 },
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
        model: 'claude-sonnet-5',
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
      meta: { model: 'claude-sonnet-5', degraded: [], dropped_citations: 0 },
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

// The eight tests above all abort '**/api/assistant/stream', which proves the
// suite is network-free but proves nothing about the stream *consumer* —
// AssistantChat.tsx's own SSE parsing, its progress indicator, and its
// "did the stream actually answer" check never run in any of them. This test
// closes that gap: it answers the stream request for real (via a genuinely
// staggered local server, not a single fulfilled body — see
// startStaggeredSseServer's comment for why that distinction matters) and
// asserts the reader saw the tool progress *and* the streamed answer, not the
// classic endpoint's mocked one.
test('the stream is genuinely consumed: tool progress renders, the streamed answer lands, and the classic endpoint is never called', async ({ page }) => {
  let classicCalls = 0
  await page.route('**/api/assistant/chat', route => {
    classicCalls += 1
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        answer: 'YEDEK YOLDAN GELEN CEVAP — bu görünüyorsa akış tüketilmedi demektir.',
        citations: [], safety_flags: [], plan_blocks: [], intent: 'qa', session_id: '',
        meta: { model: 'claude-sonnet-5', degraded: [], dropped_citations: 0 },
      }),
    })
  })

  const streamPayload = {
    answer: 'STREAMMARKERXYZ9K2: kesir çizgisi bir bölme işlemidir [S1].',
    citations: [{ id: 'S1', kind: 'mufredat', label: 'MEB · kesir', locator: {},
                  snippet: 'akıştan gelen kaynak', confidence: 0.9 }],
    safety_flags: [], plan_blocks: [], intent: 'qa', session_id: 'dashboard-default',
    meta: { model: 'claude-sonnet-5', degraded: [], dropped_citations: 0 },
  }
  const frames = [
    'event: tool_start\ndata: {"name":"kazanim_ara"}\n\n',
    'event: tool_end\ndata: {"name":"kazanim_ara","ok":true,"ms":40}\n\n',
    `event: answer\ndata: ${JSON.stringify({ payload: streamPayload })}\n\n`,
    'event: done\ndata: {}\n\n',
  ]
  const sse = await startStaggeredSseServer(frames, 150)
  try {
    await page.route('**/api/assistant/stream', route =>
      route.continue({ url: `http://127.0.0.1:${sse.port}/` }))

    await page.goto('/asistan')
    await page.fill('#ac-input', 'kesirler nasıl anlatılır')
    await page.getByLabel('Gönder').click()

    // Intermediate proof: the tool_start event was parsed and rendered as
    // visible progress *before* the answer arrived — only possible if the
    // frontend is genuinely reading frames as they come in, not just
    // reacting to one fully-buffered response.
    await expect(page.getByText('MEB kazanımları aranıyor')).toBeVisible()

    // Final proof: the rendered answer is the stream's, not the classic
    // endpoint's — and the classic endpoint was never hit.
    const answerBody = lastAnswerBody(page)
    await expect(answerBody).toContainText('STREAMMARKERXYZ9K2')
    await expect(answerBody).not.toContainText('YEDEK YOLDAN GELEN')
    expect(classicCalls).toBe(0)

    // Settled correctly after `done`: no lingering thinking indicator, no
    // error banner (a successful stream is not an error path at all).
    await expect(page.locator('.ac-msg--thinking')).toHaveCount(0)
    await expect(page.locator('.ac__error')).toHaveCount(0)
  } finally {
    await sse.close()
  }
})

// The fallback-on-failure behavior is exercised incidentally by every other
// test in this file (all eight abort the stream) but none of them *asserts*
// it — they only assert the end state, which would look identical if the
// fallback logic silently broke and simply happened to render something.
// This test pins the fallback path directly: a stream that starts, narrates
// a tool, and then closes without ever emitting `answer` must still leave
// the reader with a real answer, sourced from the classic endpoint, with no
// error banner shown (per AssistantChat.tsx's own contract: a successful
// fallback is not a user-facing error) and a console warning left as the
// only trace.
test('a stream that closes mid-flight without an answer falls back to the classic endpoint and still answers the reader', async ({ page }) => {
  const consoleWarnings: string[] = []
  page.on('console', msg => {
    if (msg.type() === 'warning') consoleWarnings.push(msg.text())
  })

  // Truncated on purpose: tool_start and tool_end arrive, then the response
  // ends — no `answer`, no `done`. AssistantChat.tsx's `answered` flag stays
  // false and it must treat this exactly like a network failure.
  await page.route('**/api/assistant/stream', route => route.fulfill({
    status: 200,
    contentType: 'text/event-stream',
    body: 'event: tool_start\ndata: {"name":"kazanim_ara"}\n\n'
        + 'event: tool_end\ndata: {"name":"kazanim_ara","ok":true,"ms":40}\n\n',
  }))

  let classicCalls = 0
  await page.route('**/api/assistant/chat', route => {
    classicCalls += 1
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        answer: 'FALLBACKMARKERABC7Q: yedek uçtan gelen cevap.',
        citations: [], safety_flags: [], plan_blocks: [], intent: 'qa', session_id: '',
        meta: { model: 'claude-sonnet-5', degraded: [], dropped_citations: 0 },
      }),
    })
  })

  await page.goto('/asistan')
  await page.fill('#ac-input', 'yarıda kesilen akış')
  await page.getByLabel('Gönder').click()

  const answerBody = lastAnswerBody(page)
  await expect(answerBody).toContainText('FALLBACKMARKERABC7Q')
  expect(classicCalls).toBe(1)

  // A successful fallback is not a user-facing error — no error banner.
  await expect(page.locator('.ac__error')).toHaveCount(0)
  await expect(page.locator('.ac-msg--thinking')).toHaveCount(0)

  // But it must not be silent either: a console warning is the one trace
  // this took the fallback path rather than the primary one.
  await expect.poll(() => consoleWarnings.some(w => w.includes('akış başarısız'))).toBe(true)
})

// D2, the accessibility floor. The chip's accessible name carries the source
// kind and label, but what the source actually SAYS lives only in the hover
// popover — so a screen-reader user reaching the citation hears which book
// was cited and never a word of what it claimed. The snippet has to be
// associated with the control, not merely positioned next to it.
test('a citation chip is described by the snippet, not just named by its label', async ({ page }) => {
  await page.route('**/api/assistant/stream', route => route.abort())
  await page.route('**/api/assistant/chat', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      answer: 'Kesirler böyle çalışır [S1].',
      citations: [{
        id: 'S1', kind: 'mufredat', label: 'MEB · kesirler',
        locator: {}, snippet: 'Payda eşitlenerek toplanır.', confidence: 0.9,
      }],
      safety_flags: [], plan_blocks: [], intent: 'qa', session_id: '',
      meta: { model: 'claude-sonnet-5', degraded: [], dropped_citations: 0 },
    }),
  }))

  await page.goto('/asistan')
  await page.fill('#ac-input', 'kesirler')
  await page.getByLabel('Gönder').click()

  const chip = lastAnswerBody(page).locator('.ac-cite')
  await expect(chip).toHaveAttribute('aria-label', 'MEB müfredatı: MEB · kesirler')

  // Resolve the description the way an assistive technology would: follow
  // aria-describedby to the element it names and read that element's text.
  const describedBy = await chip.getAttribute('aria-describedby')
  expect(describedBy, 'chip has no aria-describedby').toBeTruthy()
  const description = page.locator(`#${describedBy}`)
  await expect(description).toHaveText('Payda eşitlenerek toplanır.')
})

// İ8: colour encodes state, not taxonomy. A citation whose kind the frontend
// does not recognise already gets its own labelled group, but it was styled
// exactly like a verified authority — so "MEB says so" and "we do not know
// where this came from" were distinguishable only by reading the group
// header, which is the first thing an inattentive reader skips.
test('an unrecognised source group looks different from a verified one', async ({ page }) => {
  await page.route('**/api/assistant/stream', route => route.abort())
  await page.route('**/api/assistant/chat', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      answer: 'Bilinen [S1] ve bilinmeyen [S2].',
      citations: [
        { id: 'S1', kind: 'mufredat', label: 'MEB · kesirler',
          locator: {}, snippet: 'kazanım', confidence: 0.9 },
        { id: 'S2', kind: 'yepyeni_kaynak', label: 'Bilinmeyen',
          locator: {}, snippet: 'içerik', confidence: 0.5 },
      ],
      safety_flags: [], plan_blocks: [], intent: 'qa', session_id: '',
      meta: { model: 'claude-sonnet-5', degraded: [], dropped_citations: 0 },
    }),
  }))

  await page.goto('/asistan')
  await page.fill('#ac-input', 'kesirler')
  await page.getByLabel('Gönder').click()

  const panel = page.locator('.ac__panel')
  await expect(panel.getByText('Sınıflandırılmamış kaynak')).toBeVisible()

  // Both groups render, and the unclassified one carries a distinct marker
  // rather than relying on its heading text alone.
  await expect(panel.locator('.ac__ref-group')).toHaveCount(2)
  const unknown = panel.locator('.ac__ref-group--unclassified')
  await expect(unknown).toHaveCount(1)
  await expect(unknown).toContainText('Bilinmeyen')

  // The difference has to be visible, not merely present in the class list.
  const knownBorder = await panel.locator('.ac__ref-group').first()
    .evaluate(el => getComputedStyle(el).borderLeftColor)
  const unknownBorder = await unknown
    .evaluate(el => getComputedStyle(el).borderLeftColor)
  expect(unknownBorder).not.toBe(knownBorder)
})

// An SSE responder the test drives frame by frame. The staggered server above
// sends on a timer, so an intermediate state lasts one gap; Playwright polls
// assertions at up to one-second intervals and can miss a state that lasts
// less (measured: the draft below, visible ~0.9 s, was missed three runs out
// of three). Here each frame goes out only when the test sends it, after the
// previous state has been asserted.
function startManualSseServer() {
  let res: ServerResponse | null = null
  let connected!: () => void
  const ready = new Promise<void>(r => { connected = r })
  const server = createServer((req: IncomingMessage, response: ServerResponse) => {
    const origin = req.headers.origin
    if (origin) {
      response.setHeader('Access-Control-Allow-Origin', origin)
      response.setHeader('Access-Control-Allow-Credentials', 'true')
    }
    response.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS')
    response.setHeader('Access-Control-Allow-Headers', 'Content-Type')
    if (req.method === 'OPTIONS') {
      response.writeHead(204)
      response.end()
      return
    }
    response.writeHead(200, {
      'Content-Type': 'text/event-stream; charset=utf-8',
      'Cache-Control': 'no-cache',
    })
    res = response
    connected()
  })
  return new Promise<{
    port: number
    ready: Promise<void>
    send: (event: string, data: unknown) => void
    end: () => void
    close: () => Promise<void>
  }>((resolve, reject) => {
    server.on('error', reject)
    server.listen(0, '127.0.0.1', () => {
      const address = server.address()
      resolve({
        port: typeof address === 'object' && address ? address.port : 0,
        ready,
        send: (event, data) => { res?.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`) },
        end: () => { res?.end() },
        close: () => new Promise<void>(r => { res?.end(); server.close(() => r()) }),
      })
    })
  })
}

// The answer is shown while it is written (2026-09-24). At medium effort a
// normal question takes ~17 s; for this reader a blank wait that long is where
// attention leaves. Three things are pinned: text written before a tool call
// is dropped when `answer_reset` arrives (it is not part of the answer), a
// citation marker never shows as bare "[S1]" while its source is not yet
// known (D4), and the final `answer` replaces the draft with chips.
test('the answer appears while it is written, and the final answer replaces the draft', async ({ page }) => {
  await page.route('**/api/assistant/chat', route => route.abort())

  const payload = {
    answer: 'KESİRYAZIMI bir bölme işlemidir [S1].',
    citations: [{ id: 'S1', kind: 'mufredat', label: 'MEB · kesir', locator: {},
                  snippet: 'kaynak', confidence: 0.9 }],
    safety_flags: [], plan_blocks: [], intent: 'qa', session_id: 'dashboard-default',
    meta: { model: 'claude-sonnet-5', degraded: [], dropped_citations: 0 },
  }
  const sse = await startManualSseServer()
  try {
    await page.route('**/api/assistant/stream', route =>
      route.continue({ url: `http://127.0.0.1:${sse.port}/` }))
    await page.goto('/asistan')
    await page.fill('#ac-input', 'kesir nedir')
    await page.getByLabel('Gönder').click()
    await sse.ready

    const taslak = page.locator('.ac-msg--writing')
    sse.send('answer_delta', { text: 'ÖNMETİN bakıyorum.' })
    await expect(taslak).toContainText('ÖNMETİN')
    await expect(taslak).toHaveAttribute('aria-busy', 'true')

    sse.send('answer_reset', {})
    sse.send('tool_start', { name: 'kazanim_ara' })
    await expect(page.getByText('MEB kazanımları aranıyor')).toBeVisible()
    await expect(page.getByText('ÖNMETİN')).toHaveCount(0)

    sse.send('tool_end', { name: 'kazanim_ara', ok: true })
    sse.send('answer_delta', { text: 'KESİRYAZIMI bir ' })
    sse.send('answer_delta', { text: 'bölme işlemidir [S1' })
    await expect(taslak).toContainText('bölme işlemidir')
    await expect(taslak).not.toContainText('[S')

    sse.send('answer_delta', { text: '].' })
    await expect(taslak).toContainText('işlemidir.')
    await expect(taslak).not.toContainText('[S')

    sse.send('answer', { payload })
    sse.send('done', {})
    sse.end()
    const answerBody = lastAnswerBody(page)
    await expect(answerBody.locator('.ac-cite')).toHaveText('1')
    await expect(taslak).toHaveCount(0)
    await expect(page.locator('.ac-msg--thinking')).toHaveCount(0)
    await expect(page.getByText('KESİRYAZIMI')).toHaveCount(1)
  } finally {
    await sse.close()
  }
})

// One voice per reader (İ9). The assistant is used by Işık and by the family;
// until 2026-09-24 every question was labelled "Işık" under a greeting written
// to Işık, whoever had asked it. The page now speaks as the model is told to:
// "sen" to Işık's own account, "siz" to anyone else, with Işık in the third person.
test('the page addresses Işık as "sen" and the family as "siz"', async ({ page }) => {
  await page.route('**/api/assistant/stream', route => route.abort())
  await page.route('**/api/assistant/chat', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      answer: 'Tamam.', citations: [], safety_flags: [], plan_blocks: [], intent: 'qa',
      session_id: '', meta: { model: 'claude-sonnet-5', degraded: [], dropped_citations: 0 },
    }),
  }))

  // The e2e server's bypass user is not Işık: family voice.
  await page.goto('/asistan')
  await expect(page.locator('.ac-msg--assistant').first()).toContainText("Işık'ın ödevleri")
  await expect(page.getByRole('button', { name: 'Işık bugün neye öncelik vermeli?' })).toBeVisible()
  await expect(page.locator('#ac-input')).toHaveAttribute('placeholder', /sorun/)
  await page.fill('#ac-input', 'ödevler')
  await page.getByLabel('Gönder').click()
  await expect(page.locator('.ac-msg--user .ac-msg__role')).toHaveText('Test')

  await page.route('**/api/auth/me', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ email: 'isikkurtx@gmail.com', name: 'Işık Kurt', picture: '',
                           role: 'full', student: true }),
  }))
  await page.goto('/asistan')
  await expect(page.locator('.ac-msg--assistant').first()).toContainText('sana yardımcı')
  await expect(page.getByRole('button', { name: 'Bugün neye öncelik vermeliyim?' })).toBeVisible()
  await page.fill('#ac-input', 'ödevlerim')
  await page.getByLabel('Gönder').click()
  await expect(page.locator('.ac-msg--user .ac-msg__role')).toHaveText('Işık')
})
