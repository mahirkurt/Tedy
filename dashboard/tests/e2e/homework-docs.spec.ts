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

// B23 (S40): bir belgeyi silmek geri alınamaz; önce soran, belgeyi adlandıran tehlike onayı gelir, ilk odak
// "Vazgeç"tedir ve DELETE yalnız onaydan sonra gider. İç içe modal yok: ödev penceresi aynı yerde onaya döner.
test('removing a document asks first, names it and deletes only after confirmation', async ({ page }) => {
  const silinen: string[] = []
  let basarisiz = true
  let belgeler = [{ id: 'abc', name: 'not.txt', ready: true, error: '' }]
  await page.route('**/api/homework', route => route.fulfill({
    json: { summary: '', homework: [{ ...ROW, documents: belgeler }] },
  }))
  await page.route('**/api/homework/documents/abc', route => {
    if (route.request().method() !== 'DELETE') return route.continue()
    silinen.push(route.request().url())
    if (basarisiz) return route.fulfill({ status: 500, json: { error: 'Internal Server Error' } })
    belgeler = []
    return route.fulfill({ json: { ok: true } })
  })
  await page.clock.setFixedTime(new Date('2026-10-01T10:00:00Z'))
  await page.goto('/isler')
  await page.getByText('Kesirler', { exact: true }).click()
  await expect(page.getByRole('link', { name: 'not.txt' })).toBeVisible()

  const kaldir = page.getByRole('button', { name: 'Kaldır: not.txt' })
  await kaldir.click()
  const dialog = page.getByRole('dialog')
  await expect(dialog.getByRole('heading', { name: 'Bu belge silinsin mi?' })).toBeVisible()
  await expect(dialog).toContainText('“not.txt”')
  await expect(dialog.getByRole('button', { name: 'Vazgeç' })).toBeFocused()
  await expect(dialog.getByRole('button', { name: 'Belgeyi sil' })).toHaveClass(/cds--btn--danger/)
  expect(silinen).toEqual([])

  await dialog.getByRole('button', { name: 'Vazgeç' }).click()
  await expect(page.getByRole('heading', { name: 'Kesirler', exact: true })).toBeVisible()
  await expect(page.getByRole('link', { name: 'not.txt' })).toBeVisible()
  expect(silinen).toEqual([])

  // Escape onayı kapatır, ödev penceresini değil.
  await kaldir.click()
  await expect(dialog.getByRole('heading', { name: 'Bu belge silinsin mi?' })).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('heading', { name: 'Kesirler', exact: true })).toBeVisible()
  expect(silinen).toEqual([])

  // Başarısız silme doğru fiille söylenir, ham HTTP metni okura gitmez (D4).
  await kaldir.click()
  await dialog.getByRole('button', { name: 'Belgeyi sil' }).click()
  await expect(page.getByRole('alert').filter({ hasText: 'Belge silinemedi.' })).toBeVisible()
  await expect(page.getByText('Internal Server Error')).toHaveCount(0)
  await expect(page.getByRole('link', { name: 'not.txt' })).toBeVisible()
  expect(silinen).toHaveLength(1)

  basarisiz = false
  await kaldir.click()
  await dialog.getByRole('button', { name: 'Belgeyi sil' }).click()
  await expect(page.getByRole('link', { name: 'not.txt' })).toHaveCount(0)
  await expect(page.getByRole('heading', { name: 'Kesirler', exact: true })).toBeVisible()
  expect(silinen).toHaveLength(2)
})
