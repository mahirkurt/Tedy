import { test, expect } from '@playwright/test'
import { sabitAc } from './_gorsel-yardim'
import { json } from './_audit-fixtures'

const SOHBET = {
  id: 'ab'.repeat(16), baslik: 'Payda eşitle', ogretmen: 'matematik',
  olusturma: '2026-10-03T08:00:00Z', guncelleme: '2026-10-03T08:00:00Z',
}
const MESAJLAR = [
  { id: 'cd'.repeat(16), rol: 'user', icerik: 'Payda neden eşitlenir?',
    atiflar_json: '[]', ekler_json: '[]', ogretmen: 'matematik', zaman: '2026-10-03T08:00:00Z' },
  { id: 'ef'.repeat(16), rol: 'assistant', icerik: 'Paydalar toplanmaz.',
    atiflar_json: '[]', ekler_json: '[]', ogretmen: 'matematik', zaman: '2026-10-03T08:01:00Z' },
]

test('desktop lists the chat and loads it', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await sabitAc(page, '/asistan', 1440, 900)
  await page.route('**/api/assistant/sohbetler?*', r => r.fulfill(json({ sohbetler: [] })))
  await page.route('**/api/assistant/sohbetler', r => r.fulfill(json({ sohbetler: [SOHBET] })))
  await page.route(`**/api/assistant/sohbetler/${SOHBET.id}`, r => r.fulfill(json({
    sohbet: SOHBET, mesajlar: MESAJLAR,
  })))
  await page.goto('/asistan')
  await expect(page.getByRole('heading', { name: 'Sohbetler', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Payda eşitle' }).click()
  await expect(page.getByText('Paydalar toplanmaz.')).toBeVisible()
  await expect(page.locator('body')).toHaveJSProperty('scrollWidth', 1440)
  await page.screenshot({ path: 'test-results/sohbet-desktop.png', fullPage: true })
})

test('the open chat teacher beats localStorage', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('tedy-asistan-ogretmen::test@tedy.online', 'genel')
  })
  await page.setViewportSize({ width: 1440, height: 900 })
  await sabitAc(page, '/asistan', 1440, 900)
  await page.route('**/api/assistant/sohbetler?*', r => r.fulfill(json({ sohbetler: [] })))
  await page.route('**/api/assistant/sohbetler', r => r.fulfill(json({ sohbetler: [SOHBET] })))
  await page.route(`**/api/assistant/sohbetler/${SOHBET.id}`, r => r.fulfill(json({
    sohbet: SOHBET, mesajlar: MESAJLAR,
  })))
  await page.goto('/asistan')
  await page.getByRole('button', { name: 'Payda eşitle' }).click()
  await expect(page.locator('input[name="ac-ogretmen"][value="matematik"]')).toBeChecked()
})

test('an empty list uses the spec sentence', async ({ page }) => {
  // Varsayılan e2e kullanıcısı ailedir: kendi listesi ve Işık bölümü, aynı cümle iki kez.
  await sabitAc(page, '/asistan', 1440, 900)
  await page.route('**/api/assistant/sohbetler**', r => r.fulfill(json({ sohbetler: [] })))
  await page.goto('/asistan')
  await expect(page.getByRole('heading', { name: "Işık'ın sohbetleri" })).toBeVisible()
  await expect(page.getByText('Henüz sohbet yok — bir soru sorarak başla')).toHaveCount(2)
})

test('phone hides the list until Sohbetler', async ({ page }) => {
  await sabitAc(page, '/asistan', 390, 844)
  await page.route('**/api/assistant/sohbetler**', r => {
    const url = r.request().url()
    if (url.includes('kisi=')) return r.fulfill(json({ sohbetler: [] }))
    return r.fulfill(json({ sohbetler: [SOHBET] }))
  })
  await page.goto('/asistan')
  await expect(page.getByRole('heading', { name: 'Sohbetler', exact: true })).toBeHidden()
  await page.getByRole('button', { name: 'Sohbetler', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Sohbetler', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Payda eşitle' })).toBeVisible()
  await page.screenshot({ path: 'test-results/sohbet-phone.png', fullPage: true })
})

test('new conversation sends only the current user turn and a stable retry id', async ({ page }) => {
  await sabitAc(page, '/asistan', 1440, 900)
  let posted: Record<string, unknown> | null = null
  await page.route('**/api/assistant/stream', r => {
    posted = r.request().postDataJSON()
    return r.abort()
  })
  await page.route('**/api/assistant/chat', r => {
    expect(r.request().postDataJSON()).toEqual(posted)
    return r.fulfill(json({ answer: 'Örnek cevap', citations: [], meta: {} }))
  })
  await page.getByRole('button', { name: 'Yeni sohbet', exact: true }).click()
  await page.fill('#ac-input', 'Yeni soru')
  await page.getByRole('button', { name: 'Gönder', exact: true }).click()
  await expect(page.getByText('Örnek cevap')).toBeVisible()
  expect(posted).toMatchObject({ sohbet_id: 'ab'.repeat(16), messages: [{ role: 'user', content: 'Yeni soru' }] })
  expect(posted?.['request_id']).toBeTruthy()
})

test('family section is read only and has no student note', async ({ page }) => {
  await sabitAc(page, '/asistan', 1440, 900)
  await page.route('**/api/assistant/sohbetler**', r => {
    const url = r.request().url()
    if (url.includes('kisi=ogrenci')) return r.fulfill(json({ sohbetler: [SOHBET] }))
    return r.fulfill(json({ sohbetler: [] }))
  })
  await page.route('**/api/assistant/notlar', r => r.fulfill(json({
    notlar: [{ id: 'aa'.repeat(16), metin: 'Paydada zorlanıyor', kaynak_sohbet: null, zaman: '2026-10-03T08:00:00Z' }],
  })))
  await page.goto('/asistan')
  await expect(page.getByRole('heading', { name: "Işık'ın sohbetleri" })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Yeniden adlandır' })).toHaveCount(0)
  await expect(page.getByText('Sohbetlerini ailen de görebilir.')).toHaveCount(0)
  await expect(page.getByRole('heading', { name: 'Asistanın notları' })).toBeVisible()
  await expect(page.getByText('Paydada zorlanıyor')).toBeVisible()
  // Only the family note is deletable; the student conversation has no actions.
  await expect(page.getByRole('button', { name: 'Sil', exact: true })).toHaveCount(1)
})

test('Işık sees the family note and no notes panel', async ({ page }) => {
  await sabitAc(page, '/asistan', 1440, 900)
  await page.route('**/api/auth/me', r => r.fulfill(json({
    email: 'student@example.test', name: 'Deneme Öğrenci', picture: '', role: 'full', student: true,
  })))
  await page.route('**/api/assistant/sohbetler*', r => r.fulfill(json({ sohbetler: [] })))
  await page.goto('/asistan')
  await expect(page.getByText('Sohbetlerini ailen de görebilir.')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Asistanın notları' })).toHaveCount(0)
})


test('a stream error after its answer never appends a second reply', async ({ page }) => {
  await sabitAc(page, '/asistan', 1440, 900)
  let fallback = 0
  const payload = { answer: 'Tek yanıt.', citations: [], safety_flags: [], plan_blocks: [], meta: {} }
  await page.route('**/api/assistant/chat', r => { fallback += 1; return r.fulfill(json(payload)) })
  await page.route('**/api/assistant/stream', r => r.fulfill({ contentType: 'text/event-stream',
    body: `event: answer\ndata: ${JSON.stringify({ payload })}\n\nevent: error\ndata: {"error":"bağlantı kapandı"}\n\n` }))
  await page.fill('#ac-input', 'Yanıtla')
  await page.getByRole('button', { name: 'Gönder', exact: true }).click()
  await expect(page.getByText('Tek yanıt.', { exact: true })).toHaveCount(1)
  await expect(page.locator('#ac-input')).toBeEnabled()
  expect(fallback).toBe(0)
})

test('retry preserves the request id and uploads without another user bubble', async ({ page }) => {
  await sabitAc(page, '/asistan', 1440, 900)
  const bodies: { request_id: string; messages: { ekler?: string[] }[] }[] = []
  await page.route('**/api/assistant/uploads', r => r.fulfill(json({ id: 'cd'.repeat(16), ad: 'not.txt', tur: 'txt' })))
  await page.route('**/api/assistant/stream', r => r.abort())
  await page.route('**/api/assistant/chat', r => {
    bodies.push(r.request().postDataJSON())
    return r.fulfill(bodies.length === 1 ? { status: 503, json: { error: 'Geçici hata' } } : json({
      answer: 'Ekli yanıt.', citations: [], safety_flags: [], plan_blocks: [], meta: {},
    }))
  })
  await page.locator('input[type=file]').first().setInputFiles({ name: 'not.txt', mimeType: 'text/plain', buffer: Buffer.from('Kesir') })
  await expect(page.locator('.ac__ek')).toContainText('Metin')
  await page.fill('#ac-input', 'Bu eki açıkla')
  await page.getByRole('button', { name: 'Gönder', exact: true }).click()
  await page.getByRole('button', { name: 'Tekrar dene', exact: true }).click()
  await expect(page.getByText('Ekli yanıt.', { exact: true })).toBeVisible()
  expect(bodies).toHaveLength(2)
  expect(bodies[0]).toEqual(bodies[1])
  expect(bodies[0].request_id).toBeTruthy()
  expect(bodies[0].messages[0].ekler).toEqual(['cd'.repeat(16)])
  await expect(page.locator('.ac-msg--user')).toHaveCount(1)
})
