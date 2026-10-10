import { test, expect } from '@playwright/test'
import { json } from './_audit-fixtures'
import { PAYLOAD, carbonSabitAc, cevapla, gecmisiAc, ogretmenSecimi, soruAlani } from './_asistan-carbon'

// Eski asistan-sohbet.spec.ts'in testleri, aynı adlarla (Görev 15). Ekli tekrar testi Görev 16'da.
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
  await carbonSabitAc(page, '/asistan', 1440, 900)
  await page.route('**/api/assistant/sohbetler?*', r => r.fulfill(json({ sohbetler: [] })))
  await page.route('**/api/assistant/sohbetler', r => r.fulfill(json({ sohbetler: [SOHBET] })))
  await page.route(`**/api/assistant/sohbetler/${SOHBET.id}`, r => r.fulfill(json({
    sohbet: SOHBET, mesajlar: MESAJLAR,
  })))
  await page.goto('/asistan')
  // The history starts closed (history.startClosed) and opens from the header's "Sohbetler" action.
  await expect(soruAlani(page)).toBeVisible({ timeout: 15000 })
  await expect(page.getByRole('heading', { name: 'Sohbetler', exact: true })).toBeHidden()
  await gecmisiAc(page)
  await expect(page.getByRole('button', { name: 'Sohbetler', exact: true }).first()).toHaveAttribute('aria-pressed', 'true')
  await page.getByRole('button', { name: 'Payda eşitle', exact: true }).click()
  await expect(page.getByText('Paydalar toplanmaz.', { exact: true })).toBeVisible()
  await expect(page.locator('body')).toHaveJSProperty('scrollWidth', 1440)
  await page.screenshot({ path: 'test-results/sohbet-desktop.png', fullPage: true })
})

test('the open chat teacher beats localStorage', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('tedy-asistan-ogretmen::test@tedy.online', 'genel')
  })
  await page.setViewportSize({ width: 1440, height: 900 })
  await carbonSabitAc(page, '/asistan', 1440, 900)
  await page.route('**/api/assistant/sohbetler?*', r => r.fulfill(json({ sohbetler: [] })))
  await page.route('**/api/assistant/sohbetler', r => r.fulfill(json({ sohbetler: [SOHBET] })))
  await page.route(`**/api/assistant/sohbetler/${SOHBET.id}`, r => r.fulfill(json({
    sohbet: SOHBET, mesajlar: MESAJLAR,
  })))
  await page.goto('/asistan')
  await gecmisiAc(page)
  await page.getByRole('button', { name: 'Payda eşitle', exact: true }).click()
  await expect(ogretmenSecimi(page)).toContainText('Matematik')
})

test('an empty list says so once, in the reader’s voice, not in italics', async ({ page }) => {
  // Varsayılan e2e kullanıcısı ailedir: kendi listesi, Işık bölümü ve notlar — her boşluk kendi cümlesiyle, bir kez.
  await carbonSabitAc(page, '/asistan', 1440, 900)
  await page.route('**/api/assistant/sohbetler**', r => r.fulfill(json({ sohbetler: [] })))
  await page.goto('/asistan')
  await gecmisiAc(page)
  await expect(page.getByRole('heading', { name: "Işık'ın sohbetleri" })).toBeVisible()
  for (const cumle of ['Henüz sohbetiniz yok.', "Işık'ın henüz sohbeti yok.", 'Asistan henüz not almadı.']) {
    const p = page.getByText(cumle, { exact: true })
    await expect(p).toHaveCount(1)
    await expect(p).toHaveCSS('font-style', 'normal')
  }
})

test('Işık’s own empty list speaks to her', async ({ page }) => {
  await carbonSabitAc(page, '/asistan', 1440, 900)
  await page.route('**/api/auth/me', r => r.fulfill(json({
    email: 'student@example.test', name: 'Deneme Öğrenci', picture: '', role: 'full', student: true,
  })))
  await page.route('**/api/assistant/sohbetler*', r => r.fulfill(json({ sohbetler: [] })))
  await page.goto('/asistan')
  await gecmisiAc(page)
  await expect(page.getByText('Henüz sohbetin yok.', { exact: true })).toHaveCount(1)
  await expect(page.getByRole('heading', { name: "Işık'ın sohbetleri" })).toHaveCount(0)
})

test('deleting a chat asks first, names it, and only then sends DELETE', async ({ page }) => {
  await carbonSabitAc(page, '/asistan', 1440, 900)
  const silinen: string[] = []
  let liste = [SOHBET]
  await page.route('**/api/assistant/sohbetler?*', r => r.fulfill(json({ sohbetler: [] })))
  await page.route('**/api/assistant/sohbetler', r => r.fulfill(json({ sohbetler: liste })))
  await page.route(`**/api/assistant/sohbetler/${SOHBET.id}`, r => {
    if (r.request().method() === 'DELETE') { silinen.push(SOHBET.id); liste = []; return r.fulfill(json({ ok: true })) }
    return r.fulfill(json({ sohbet: SOHBET, mesajlar: MESAJLAR }))
  })
  await page.goto('/asistan')
  await gecmisiAc(page)
  await page.getByRole('button', { name: 'Sil: Payda eşitle', exact: true }).click()
  const pencere = page.getByRole('dialog')
  await expect(pencere).toBeVisible()
  await expect(pencere.getByRole('heading', { name: 'Sohbeti sil' })).toBeVisible()
  await expect(pencere).toContainText('“Payda eşitle” sohbeti, ona bağlı ekler ve alıştırmalarla birlikte silinir.')
  // Focus starts on "Vazgeç"; Carbon's danger button names the object.
  await expect(pencere.getByRole('button', { name: 'Vazgeç' })).toBeFocused()
  await expect(pencere.getByRole('button', { name: 'Sohbeti sil' })).toHaveClass(/cds--btn--danger/)
  expect(silinen).toEqual([])
  await pencere.getByRole('button', { name: 'Vazgeç' }).click()
  await expect(pencere).toBeHidden()
  expect(silinen).toEqual([])
  await page.getByRole('button', { name: 'Sil: Payda eşitle', exact: true }).click()
  await page.getByRole('dialog').getByRole('button', { name: 'Sohbeti sil' }).click()
  await expect.poll(() => silinen).toEqual([SOHBET.id])
  await expect(page.getByRole('button', { name: 'Payda eşitle', exact: true })).toHaveCount(0)
})

test('a failed delete says "silinemedi"', async ({ page }) => {
  await carbonSabitAc(page, '/asistan', 1440, 900)
  await page.route('**/api/assistant/sohbetler?*', r => r.fulfill(json({ sohbetler: [] })))
  await page.route('**/api/assistant/sohbetler', r => r.fulfill(json({ sohbetler: [SOHBET] })))
  await page.route(`**/api/assistant/sohbetler/${SOHBET.id}`, r => r.request().method() === 'DELETE'
    ? r.fulfill({ status: 500, json: { error: 'x' } }) : r.fulfill(json({ sohbet: SOHBET, mesajlar: MESAJLAR })))
  await page.goto('/asistan')
  await gecmisiAc(page)
  await page.getByRole('button', { name: 'Sil: Payda eşitle', exact: true }).click()
  await page.getByRole('dialog').getByRole('button', { name: 'Sohbeti sil' }).click()
  await expect(page.getByRole('alert').filter({ hasText: 'Sohbet silinemedi.' })).toBeVisible()
  await expect(page.getByText('Sohbet kaydedilemedi.', { exact: true })).toHaveCount(0)
})

test('phone opens the list from Sohbetler and closes it from inside', async ({ page }) => {
  await carbonSabitAc(page, '/asistan', 390, 844)
  await page.route('**/api/assistant/sohbetler**', r => {
    const url = r.request().url()
    if (url.includes('kisi=')) return r.fulfill(json({ sohbetler: [] }))
    return r.fulfill(json({ sohbetler: [SOHBET] }))
  })
  await page.route(`**/api/assistant/sohbetler/${SOHBET.id}`, r => r.fulfill(json({ sohbet: SOHBET, mesajlar: MESAJLAR })))
  await page.goto('/asistan')
  await expect(soruAlani(page)).toBeVisible({ timeout: 15000 })
  await expect(page.getByRole('heading', { name: 'Sohbetler', exact: true })).toBeHidden()
  // Carbon'un mobil menüsü ("≡") kapalı: tek yol başlıktaki "Sohbetler" eylemi.
  await expect(page.getByText('Sohbetleri gör', { exact: true })).toHaveCount(0)
  await gecmisiAc(page)
  await expect(page.getByRole('button', { name: 'Payda eşitle', exact: true })).toBeVisible()
  // Telefonda panel sohbet başlığını da örter: kapatma panelin içindedir, 48 px.
  const kapat = page.getByRole('button', { name: 'Sohbetleri kapat' })
  expect((await kapat.boundingBox())!.height).toBeGreaterThanOrEqual(44)
  await kapat.click()
  await expect(page.getByRole('heading', { name: 'Sohbetler', exact: true })).toBeHidden()
  await gecmisiAc(page)
  await page.getByRole('button', { name: 'Payda eşitle', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Sohbetler', exact: true })).toBeHidden()
  await expect(page.getByText('Paydalar toplanmaz.', { exact: true })).toBeVisible()
})

test('new conversation sends only the current user turn and a stable retry id', async ({ page }) => {
  await carbonSabitAc(page, '/asistan', 1440, 900)
  let posted: Record<string, unknown> | null = null
  await page.route('**/api/assistant/stream', r => {
    posted = r.request().postDataJSON()
    return r.abort()
  })
  await page.route('**/api/assistant/chat', r => {
    expect(r.request().postDataJSON()).toEqual(posted)
    return r.fulfill(json({ answer: 'Örnek cevap', citations: [], meta: {} }))
  })
  await gecmisiAc(page)
  await page.getByRole('button', { name: 'Yeni sohbet', exact: true }).click()
  await soruAlani(page).fill('Yeni soru')
  await page.getByRole('button', { name: 'Gönder', exact: true }).click()
  await expect(page.getByText('Örnek cevap', { exact: true })).toBeVisible()
  expect(posted).toMatchObject({ sohbet_id: 'ab'.repeat(16), messages: [{ role: 'user', content: 'Yeni soru' }] })
  expect(posted?.['request_id']).toBeTruthy()
})

test('family section is read only and has no student note', async ({ page }) => {
  await carbonSabitAc(page, '/asistan', 1440, 900)
  await page.route('**/api/assistant/sohbetler**', r => {
    const url = r.request().url()
    if (url.includes('kisi=ogrenci')) return r.fulfill(json({ sohbetler: [SOHBET] }))
    return r.fulfill(json({ sohbetler: [] }))
  })
  await page.route('**/api/assistant/notlar', r => r.fulfill(json({
    notlar: [{ id: 'aa'.repeat(16), metin: 'Paydada zorlanıyor', kaynak_sohbet: null, zaman: '2026-10-03T08:00:00Z' }],
  })))
  await page.goto('/asistan')
  await gecmisiAc(page)
  await expect(page.getByRole('heading', { name: "Işık'ın sohbetleri" })).toBeVisible()
  await expect(page.getByRole('button', { name: /^Yeniden adlandır/ })).toHaveCount(0)
  await expect(page.getByText('Sohbetlerini ailen de görebilir.', { exact: true })).toHaveCount(0)
  await expect(page.getByRole('heading', { name: 'Asistanın notları' })).toBeVisible()
  await expect(page.getByText('Paydada zorlanıyor', { exact: true })).toBeVisible()
  // Only the family note is deletable; the student conversation has no actions.
  await expect(page.getByRole('button', { name: /^(Sil|Notu sil)/ })).toHaveCount(1)
  await expect(page.getByRole('button', { name: 'Notu sil', exact: true })).toHaveCount(1)
})

test('Işık sees the family note and no notes panel', async ({ page }) => {
  await carbonSabitAc(page, '/asistan', 1440, 900)
  await page.route('**/api/auth/me', r => r.fulfill(json({
    email: 'student@example.test', name: 'Deneme Öğrenci', picture: '', role: 'full', student: true,
  })))
  await page.route('**/api/assistant/sohbetler*', r => r.fulfill(json({ sohbetler: [] })))
  await page.goto('/asistan')
  await expect(page.getByText('Sohbetlerini ailen de görebilir.', { exact: true })).toBeVisible()
  await gecmisiAc(page)
  await expect(page.getByRole('heading', { name: 'Asistanın notları' })).toHaveCount(0)
})


test('a stream error after its answer never appends a second reply', async ({ page }) => {
  await carbonSabitAc(page, '/asistan', 1440, 900)
  let fallback = 0
  const payload = { answer: 'Tek yanıt.', citations: [], safety_flags: [], plan_blocks: [], meta: {} }
  await page.route('**/api/assistant/chat', r => { fallback += 1; return r.fulfill(json(payload)) })
  await page.route('**/api/assistant/stream', r => r.fulfill({ contentType: 'text/event-stream',
    body: `event: answer\ndata: ${JSON.stringify({ payload })}\n\nevent: error\ndata: {"error":"bağlantı kapandı"}\n\n` }))
  await soruAlani(page).fill('Yanıtla')
  await page.getByRole('button', { name: 'Gönder', exact: true }).click()
  await expect(page.getByText('Tek yanıt.', { exact: true })).toHaveCount(1)
  await expect(soruAlani(page)).toBeEditable()
  expect(fallback).toBe(0)
})


test('salt okunur aile sohbetinde giriş kapalı, geri bildirim yok', async ({ page }) => {
  await carbonSabitAc(page, '/asistan', 1440, 900)
  await page.route('**/api/assistant/sohbetler**', r => r.request().url().includes('kisi=ogrenci')
    ? r.fulfill(json({ sohbetler: [SOHBET] })) : r.fulfill(json({ sohbetler: [] })))
  await page.route(`**/api/assistant/sohbetler/${SOHBET.id}`, r => r.fulfill(json({ sohbet: SOHBET, mesajlar: MESAJLAR, read_only: true })))
  await page.goto('/asistan')
  await gecmisiAc(page)
  await page.getByRole('button', { name: 'Payda eşitle', exact: true }).click()
  await expect(page.getByText('Paydalar toplanmaz.', { exact: true })).toBeVisible()
  await expect(soruAlani(page)).not.toBeEditable()
  await expect(page.locator('button[aria-label="Bu yanıtı beğenmedim"]')).toHaveCount(0)
})

test('Carbon yeni sohbet düğmesi yeni kayıt açar ve konuşmayı boşaltır', async ({ page }) => {
  let yeni = 0
  await carbonSabitAc(page, '/asistan', 1440, 900)
  await page.route('**/api/assistant/sohbetler', r => {
    if (r.request().method() === 'POST') { yeni += 1; return r.fulfill(json({ id: 'cd'.repeat(16), ogretmen: 'genel', baslik: '' })) }
    return r.fulfill(json({ sohbetler: [SOHBET] }))
  })
  await page.route(`**/api/assistant/sohbetler/${SOHBET.id}`, r => r.fulfill(json({ sohbet: SOHBET, mesajlar: MESAJLAR })))
  await page.goto('/asistan')
  await gecmisiAc(page)
  await page.getByRole('button', { name: 'Payda eşitle', exact: true }).click()
  await expect(page.getByText('Paydalar toplanmaz.', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Sohbeti yeniden başlat' }).click()
  await expect(page.getByText('Paydalar toplanmaz.', { exact: true })).toHaveCount(0)
  expect(yeni).toBe(1)
})

test('retry preserves the request id and uploads without another user bubble', async ({ page }) => {
  await carbonSabitAc(page, '/asistan', 1440, 900)
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
  await expect(page.locator('.asistan__ek')).toContainText('Metin')
  await soruAlani(page).fill('Bu eki açıkla')
  await page.getByRole('button', { name: 'Gönder', exact: true }).click()
  await page.getByRole('button', { name: 'Tekrar dene', exact: true }).click()
  await expect(page.getByText('Ekli yanıt.', { exact: true })).toBeVisible()
  expect(bodies).toHaveLength(2)
  expect(bodies[0]).toEqual(bodies[1])
  expect(bodies[0].request_id).toBeTruthy()
  expect(bodies[0].messages[0].ekler).toEqual(['cd'.repeat(16)])
  await expect(page.getByText('Bu eki açıkla', { exact: true })).toHaveCount(1)
})

test('başka yerde silinmiş etkin sohbet kilitlemez: yeni soru yeni sohbet açar', async ({ page }) => {
  const OLU = 'de'.repeat(16)
  const YENI = 'fa'.repeat(16)
  await page.addInitScript(id => sessionStorage.setItem('tedy-asistan-etkin::test@tedy.online', JSON.stringify({ id, salt: false })), OLU)
  const istekler = await cevapla(page, PAYLOAD({ answer: 'Yeni sohbette cevap.' }))
  await carbonSabitAc(page, '/asistan', 1440, 900)
  await page.route('**/api/assistant/sohbetler', r => r.request().method() === 'POST'
    ? r.fulfill(json({ id: YENI, ogretmen: 'genel', baslik: '' })) : r.fulfill(json({ sohbetler: [] })))
  await page.route(`**/api/assistant/sohbetler/${OLU}`, r => r.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ error: 'Sohbet bulunamadı.' }) }))
  await page.goto('/asistan')
  await soruAlani(page).fill('Merhaba')
  await page.getByRole('button', { name: 'Gönder', exact: true }).click()
  await expect(page.getByText('Yeni sohbette cevap.', { exact: true })).toBeVisible()
  expect(istekler[0]).toMatchObject({ sohbet_id: YENI })
})

// B77: Carbon dar/geniş kararını `--cds-aichat-history-width`'i px sanarak verir ("20rem" → 20); değer kök yazıdan
// px hesaplanır (useGecmisGenisligi). Telefonda panel sohbeti örter (yan sütun değil), masaüstünde 20rem = 320 px,
// 4K'da 640 px.
for (const [w, h, bicim] of [[390, 844, 'telefon'], [1440, 900, 'masaustu'], [3840, 2160, '4k']] as const) {
  test(`history width and layout hold at ${w}px (B77)`, async ({ page }) => {
    await carbonSabitAc(page, '/asistan', w, h)
    await gecmisiAc(page)
    const gecmis = (await page.locator('.asistan-gecmis').boundingBox())!
    const sohbet = (await page.locator('.asistan__sohbet').boundingBox())!
    if (bicim === 'telefon') {
      // Örten panel: sohbetin tamamı kadar geniş; sohbet ekran dışına itilmez.
      expect(gecmis.width).toBeGreaterThan(sohbet.width - 4)
      expect(sohbet.x + sohbet.width).toBeLessThanOrEqual(w)
    } else {
      expect(gecmis.width).toBeCloseTo(bicim === '4k' ? 640 : 320, -1)
      // Yan sütun: giriş alanı görünür kalır.
      await expect(soruAlani(page)).toBeInViewport()
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(0)
  })
}
