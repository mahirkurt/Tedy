import { test, expect } from '@playwright/test'
import { json, mockSohbetler } from './_audit-fixtures'
import { asistanAc, sor, sonCevap } from './_asistan-carbon'

test.beforeEach(async ({ page }) => { await mockSohbetler(page) })

// Eski assistant-ai.spec.ts'in testleri, aynı adlarla (Görev 19). Carbon for AI'da AI işlemesi mesaj başına
// değil, sohbet yüzeyinin kendisindedir (ai-theme kabı, main-chat gradyanı — ölçüldü); kullanıcı balonu ve
// kaynak paneli bu işlemenin dışında kalır. Açıklama başlıktaki kendi AILabel'ımızdadır (Görev 14).

const ANSWER = {
  answer: 'Paydaları eşitleyerek başlarsın [S1].',
  citations: [{ id: 'S1', kind: 'mufredat', label: 'MEB · kesirler',
                locator: {}, snippet: 'Payda eşitlenir.', confidence: 0.9 }],
  safety_flags: [], plan_blocks: [], intent: 'qa', session_id: '',
  meta: { model: 'claude-sonnet-5', degraded: [], dropped_citations: 0 },
}

async function ask(page: import('@playwright/test').Page) {
  await page.route('**/api/assistant/stream', r => r.abort())
  await page.route('**/api/assistant/chat', r => r.fulfill(json(ANSWER)))
  await asistanAc(page)
  await sor(page, 'kesirler')
  // Cevabın çizildiğinin kanıtı: atıf düğmesi. Sonraki evaluate() çağrıları yeniden denemez.
  await expect(page.getByRole('button', { name: 'Kaynaklar', exact: true })).toBeVisible()
}

const etiket = (page: import('@playwright/test').Page) => page.locator('.asistan .cds--ai-label__button').first()
const aciklama = (page: import('@playwright/test').Page) => page.locator('.asistan .cds--ai-label-content')

test('the AI label explains itself instead of just marking', async ({ page }) => {
  await page.route('**/api/assistant/stream', r => r.abort())
  await asistanAc(page)
  await expect(etiket(page)).toBeVisible()
  await etiket(page).click()
  await expect(aciklama(page)).toBeVisible()
  // Turkish softens the final k: the copy says "kaynağı"/"kaynağa", never the bare "kaynak".
  await expect(aciklama(page)).toContainText(/kayna[kğ]/i)
})

test('the model that answered is disclosed', async ({ page }) => {
  await ask(page)
  await etiket(page).click()
  // Named the way a person would say it, not as an API identifier (D4).
  await expect(aciklama(page)).toContainText('Son yanıtı Claude Sonnet 5 yazdı.')
  await expect(aciklama(page)).not.toContainText('claude-sonnet-5')
})

test('the AI aura marks what the model wrote, not what Işık wrote', async ({ page }) => {
  await ask(page)
  // Işık'ın kendi sorusunu taşıyan balon: zemini AI hâlesi (g10 ai-aura-hover-background #edf5ff) ya da
  // gradyan değildir.
  const balon = await page.locator('.cds-aichat--message--request').filter({ visible: true }).first()
    .getByText('kesirler', { exact: true }).evaluate(el => {
      let n: Element | null = el
      // Gölge kök sınırında sahibine çıkılır (balon Carbon'un iç içe öğelerinde).
      while (n && getComputedStyle(n).backgroundColor === 'rgba(0, 0, 0, 0)')
        n = n.parentElement ?? ((n.getRootNode() as ShadowRoot).host ?? null)
      return n ? [getComputedStyle(n).backgroundColor, getComputedStyle(n).backgroundImage] : ['yok', 'yok']
    })
  expect(balon[0].replace(/\s/g, '')).not.toBe('rgb(237,245,255)')
  expect(balon[0]).not.toBe('yok')
  expect(balon[1]).toBe('none')
})

test('the AI aura stays off the sources, which are quotes', async ({ page }) => {
  await ask(page)
  await page.getByRole('button', { name: 'Kaynak ayrıntıları' }).click()
  // Satırların var olduğu önce kanıtlanır: hiç satır yoksa test yoklukla geçerdi.
  const satirlar = page.locator('.ac__ref-item')
  await expect(satirlar).toHaveCount(1)
  for (const bg of await satirlar.evaluateAll(els => els.map(el => getComputedStyle(el).backgroundImage))) {
    expect(bg, 'kaynak satırında AI gradyanı').toBe('none')
  }
})

test('the assistant answer keeps its AI treatment', async ({ page }) => {
  await ask(page)
  // Cevap Carbon'un AI temalı sohbet yüzeyinde: kap ai-theme sınıfını, mesaj alanı gradyanı taşır.
  await expect(sonCevap(page)).toContainText('Paydaları eşitleyerek başlarsın')
  await expect(page.locator('.asistan .cds-aichat--ai-theme')).toHaveCount(1)
  const bg = await page.locator('.asistan .main-chat').first().evaluate(el => getComputedStyle(el).backgroundImage)
  expect(bg, 'üretilen yanıtın yüzeyinde AI gradyanı yok').toContain('gradient')
})

test('the assistant stylesheet names no colour of its own', async () => {
  // D1: tokens are mandatory — checked against the sources (Carbon AI Chat's own styles are exempt).
  const fs = await import('node:fs/promises')
  const dizin = new URL('../../src/asistan/', import.meta.url)
  const dosyalar = (await fs.readdir(dizin)).filter(f => f.endsWith('.scss'))
  expect(dosyalar.length).toBeGreaterThan(0)
  const offenders: string[] = []
  for (const f of dosyalar) {
    const src = await fs.readFile(new URL(f, dizin), 'utf8')
    src.split('\n').forEach((line, i) => {
      const kod = line.replace(/\/\/.*$/, '')
      if (/(#[0-9a-fA-F]{3,8}\b|\brgba?\()/.test(kod)) offenders.push(`${f}:${i + 1}: ${kod.trim()}`)
    })
  }
  expect(offenders, 'token yerine değişmez renk').toEqual([])
})
