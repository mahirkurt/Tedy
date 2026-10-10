import { test, expect } from '@playwright/test'

const ROW = {
  'Ders Adı': 'Matematik',
  'Ödev Başlığı': 'Kesirler',
  'Ödev Kaynağı': '',
  'Ödev Son Teslim Tarihi': '02.10.2026 23:59',
  'Ödev Durumu': 'Değerlendirilmemiş',
  homework_key: 'matematik|kesirler|02.10.2026 23:59',
  normalized_course: 'Matematik',
  detail: { description: 'Payda altta.', attachments: [] },
  documents: [] as { id: string, name: string, ready: boolean, error: string }[],
}

test('a document added on the homework is named there', async ({ page }) => {
  let posted = ''
  let bound = ''
  let documents = ROW.documents
  await page.route('**/api/homework', route => {
    if (route.request().method() === 'GET') {
      return route.fulfill({ json: { summary: '', homework: [{ ...ROW, documents } ] } })
    }
    return route.continue()
  })
  await page.route('**/api/assistant/uploads', async route => {
    posted = route.request().postData() || ''
    await route.fulfill({ json: { id: 'ab'.repeat(16), ad: 'not.txt', tur: 'txt' } })
  })
  await page.route('**/api/assistant/uploads/*/odeve-bagla', async route => {
    bound = route.request().postData() || ''
    documents = [{ id: 'abc', name: 'not.txt', ready: true, error: '' }]
    await route.fulfill({
      json: {
        document: { id: 'abc', name: 'not.txt', ready: true, error: '' },
        documents: [{ id: 'abc', name: 'not.txt', ready: true, error: '' }],
      },
    })
  })

  await page.clock.setFixedTime(new Date('2026-10-01T10:00:00Z'))
  await page.goto('/isler')
  await page.getByText('Kesirler', { exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Kesirler', exact: true })).toBeVisible()
  await expect(page.getByText('yalnız bu ödev sorulurken')).toBeVisible()

  const chooser = page.waitForEvent('filechooser')
  await page.getByRole('button', { name: 'Belge ekle' }).click()
  await (await chooser).setFiles({
    name: 'not.txt',
    mimeType: 'text/plain',
    buffer: Buffer.from('Kesirlerde payda.'),
  })
  await expect(page.getByRole('link', { name: 'not.txt' })).toBeVisible()
  expect(bound).toContain('matematik|kesirler|02.10.2026 23:59')
  expect(posted).toContain('not.txt')
})

test('the assistant can be aimed at one homework', async ({ page }) => {
  await page.route('**/api/homework', route => route.fulfill({
    json: { summary: '', homework: [ROW] },
  }))
  await page.goto('/asistan')
  // Asistan yenilemesi (2026-10-10): ödev seçimi giriş satırının bir eylemidir ("Ödeve bağla" menüsü); seçilen ödev
  // giriş üstündeki bağlam çipi olur ve kaldırılabilir.
  const ac = page.getByRole('button', { name: 'Ödeve bağla', exact: true })
  await expect(ac).toBeVisible({ timeout: 15000 })
  await ac.click()
  await page.getByRole('menuitem', { name: 'Matematik — Kesirler' }).click()
  await expect(page.getByText('Ödev: Matematik — Kesirler', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Ödevi kaldır' }).click()
  await expect(page.getByText('Ödev: Matematik — Kesirler', { exact: true })).toHaveCount(0)
})
