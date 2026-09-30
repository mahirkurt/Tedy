import { test, expect, type Page, type Route } from '@playwright/test'

// 1×1 PNG. The photo endpoint is intercepted, so the bytes are never read.
const PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
  'base64',
)

const READ_ROW = {
  'Ders Adı': 'Din Kültürü',
  'Ödev Başlığı': 'Sayfa 4',
  'Ödev Son Teslim Tarihi': '',
  odev_kaynagi: 'Fasikül',
  detail: { description: '1-5. sorular' },
}

function json(route: Route, body: unknown) {
  return route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(body),
  })
}

async function pickPhoto(page: Page, file: { name: string, mimeType: string, buffer: Buffer }) {
  await page.goto('/')
  await page.getByRole('button', { name: 'Ödev fotoğrafı ekle' }).click()
  const chooser = page.waitForEvent('filechooser')
  await page.getByRole('button', { name: 'Galeriden yükle' }).click()
  await (await chooser).setFiles(file)
}

test('reads the photo, then saves the edited row', async ({ page }) => {
  const stages: string[] = []
  let commitBody = ''
  await page.route('**/api/homework/photo', async route => {
    const body = route.request().postData() || ''
    const preview = body.includes('name="stage"') && body.includes('preview')
    stages.push(preview ? 'preview' : 'commit')
    if (preview) {
      await json(route, {
        preview: true,
        photo_hash: 'abc',
        added_count: 0,
        skipped_count: 0,
        homework: [READ_ROW],
      })
      return
    }
    commitBody = body
    await json(route, { added_count: 1, skipped_count: 0, homework: [] })
  })

  await pickPhoto(page, { name: 'odev.png', mimeType: 'image/png', buffer: PNG })
  await page.getByRole('button', { name: 'Fotoğrafı oku' }).click()
  await expect(page.getByRole('heading', { name: 'Okunan işler' })).toBeVisible()
  await expect(page.getByText('Kaynak: Fasikül')).toBeVisible()
  const title = page.getByLabel('Başlık')
  await expect(title).toHaveValue('Sayfa 4')
  await expect(page.getByLabel('Teslim')).toHaveValue('')
  await title.fill('Sayfa 5')
  await page.getByRole('button', { name: "İşler'e ekle" }).click()
  await expect(page.getByRole('heading', { name: 'Okunan işler' })).toBeHidden()
  expect(stages).toEqual(['preview', 'commit'])
  expect(commitBody).toContain('Sayfa 5')
  expect(commitBody).toContain('Fasikül')
  expect(commitBody).toContain('commit')
})

test('an empty read says the photo has no homework', async ({ page }) => {
  await page.route('**/api/homework/photo', route => json(route, {
    preview: true, photo_hash: 'abc', added_count: 0, skipped_count: 0, homework: [],
  }))
  await pickPhoto(page, { name: 'odev.png', mimeType: 'image/png', buffer: PNG })
  await page.getByRole('button', { name: 'Fotoğrafı oku' }).click()
  await expect(page.getByRole('alert')).toHaveText('Bu fotoğrafta ödev görünmüyor.')
  await expect(page.getByRole('heading', { name: 'Ödev fotoğrafı' })).toBeVisible()
  await expect(page.getByRole('button', { name: "İşler'e ekle" })).toHaveCount(0)
})

test('a duplicate stays open with a sentence', async ({ page }) => {
  await page.route('**/api/homework/photo', async route => {
    const body = route.request().postData() || ''
    if (body.includes('preview')) {
      await json(route, {
        preview: true, photo_hash: 'abc', added_count: 0, skipped_count: 0, homework: [READ_ROW],
      })
      return
    }
    await json(route, { added_count: 0, skipped_count: 1, homework: [] })
  })
  await pickPhoto(page, { name: 'odev.png', mimeType: 'image/png', buffer: PNG })
  await page.getByRole('button', { name: 'Fotoğrafı oku' }).click()
  await page.getByRole('button', { name: "İşler'e ekle" }).click()
  await expect(page.getByRole('alert')).toHaveText('Bu iş zaten listede. Yeni bir şey eklenmedi.')
  await expect(page.getByRole('heading', { name: 'Okunan işler' })).toBeVisible()
})

test('a non-image is refused in the modal, without a dialog', async ({ page }) => {
  page.on('dialog', dialog => {
    throw new Error(`unexpected dialog: ${dialog.message()}`)
  })
  await pickPhoto(page, { name: 'not.txt', mimeType: 'text/plain', buffer: Buffer.from('no') })
  await expect(page.getByRole('alert')).toHaveText('Lütfen bir görsel dosyası seçin.')
  await expect(page.getByRole('button', { name: 'Fotoğrafı oku' })).toBeDisabled()
})
