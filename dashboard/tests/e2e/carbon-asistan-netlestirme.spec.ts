import { test, expect } from '@playwright/test'
import { mock, FULL, json } from './_audit-fixtures'
import { soruAlani, gonderDugmesi } from './_asistan-carbon'

// Eski asistan-netlestirme.spec.ts'in testi, aynı adla (Görev 19); seçenekler aynı bileşen (NetlestirmeSecenekleri).

for (const fallback of [false, true]) {
  test(`clarification options send a choice, preserve free text and disable old choices (${fallback ? 'JSON' : 'SSE'})`, async ({ page }) => {
    await mock(page, FULL)
    const calls: { messages: { content: string }[] }[] = []
    const question = { soru: 'Hangi konu?', secenekler: ['Kesirler', 'Üslü sayılar'] }
    function answer() { return { answer: calls.length === 1 ? question.soru : 'Kesirlerden başlayalım.',
      netlestirme: calls.length === 1 ? question : null, citations: [], safety_flags: [], plan_blocks: [], meta: {} } }
    await page.route('**/api/assistant/stream', route => {
      if (fallback) return route.abort()
      calls.push(route.request().postDataJSON())
      const payload = answer()
      return route.fulfill({ contentType: 'text/event-stream', body:
        (calls.length === 1 ? `event: clarify\ndata: ${JSON.stringify(question)}\n\n` : '')
        + `event: answer\ndata: ${JSON.stringify({ payload })}\n\n` })
    })
    await page.route('**/api/assistant/chat', route => { calls.push(route.request().postDataJSON()); return route.fulfill(json(answer())) })
    await page.goto('/asistan')
    const input = soruAlani(page)
    await input.fill('Matematik çalışalım')
    await gonderDugmesi(page).click()
    const group = page.getByRole('group', { name: 'Seçenekler', exact: true })
    await expect(group.getByRole('button', { name: 'Kesirler', exact: true })).toBeEnabled()
    await group.getByRole('button', { name: 'Başka bir şey yaz…' }).click()
    await expect(input).toBeFocused()
    expect(calls).toHaveLength(1)
    await group.getByRole('button', { name: 'Kesirler', exact: true }).click()
    await expect(page.getByText('Kesirlerden başlayalım.', { exact: true })).toBeVisible()
    expect(calls[1].messages.at(-1)?.content).toBe('Kesirler')
    await expect(group.getByRole('button', { name: 'Kesirler', exact: true })).toBeDisabled()
  })
}
