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
  await page.route('**/api/homework', route => {
    if (route.request().method() === 'GET') {
      return route.fulfill({ json: { summary: '', homework: [ROW] } })
    }
    return route.continue()
  })
  await page.route('**/api/homework/documents', async route => {
    posted = route.request().postData() || ''
    await route.fulfill({
      json: {
        document: { id: 'abc', name: 'not.txt', ready: true, error: '' },
        documents: [{ id: 'abc', name: 'not.txt', ready: true, error: '' }],
      },
    })
  })

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
  expect(posted).toContain('matematik|kesirler|02.10.2026 23:59')
  expect(posted).toContain('not.txt')
})

test('the assistant can be aimed at one homework', async ({ page }) => {
  await page.route('**/api/homework', route => route.fulfill({
    json: { summary: '', homework: [ROW] },
  }))
  await page.goto('/asistan')
  const secim = page.getByLabel('Ödev', { exact: true })
  await expect(secim).toBeVisible()
  await secim.selectOption({ label: 'Matematik — Kesirler' })
  await expect(secim).toHaveValue(ROW.homework_key)
})
