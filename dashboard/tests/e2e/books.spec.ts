import { test, expect } from '@playwright/test'

const externalBaseUrl = process.env.TEDY_E2E_BASE_URL ?? ''
const appUrl = (path: string) => `${externalBaseUrl}${path}`

test.describe('Tedy Books mobile experience', () => {
  test.use({ viewport: { width: 320, height: 568 } })

  test('keeps the library full width while the menu overlays it', async ({ page }) => {
    await page.goto(appUrl('/kitaplar'))
    await expect(page.getByRole('heading', { name: 'Kitaplık' })).toBeVisible()

    const content = page.locator('.app-shell-content')
    const navigation = page.getByRole('navigation', { name: 'Navigasyon' })
    const closedContentBox = await content.boundingBox()
    const closedNavBox = await navigation.boundingBox()

    expect(closedContentBox?.x).toBe(0)
    expect(closedContentBox?.width).toBe(320)
    expect(closedNavBox).not.toBeNull()
    expect(closedNavBox!.x + closedNavBox!.width).toBeLessThanOrEqual(0)
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(320)

    await page.getByRole('button', { name: 'Menü' }).click()
    await expect(page.getByRole('button', { name: 'Menüyü kapat' })).toBeVisible()
    await expect.poll(async () => (await navigation.boundingBox())?.x).toBe(0)

    const openContentBox = await content.boundingBox()
    const openNavBox = await navigation.boundingBox()
    expect(openContentBox?.x).toBe(0)
    expect(openContentBox?.width).toBe(320)
    expect(openNavBox?.x).toBe(0)
    expect(openNavBox?.width).toBe(256)
  })

  test('keeps every header action inside a narrow phone viewport', async ({ page }) => {
    await page.goto(appUrl('/kitaplar'))

    for (const name of ['Yenile', 'Ödev fotoğrafı ekle', 'Çıkış']) {
      const box = await page.getByRole('button', { name }).boundingBox()
      expect(box).not.toBeNull()
      expect(box!.x).toBeGreaterThanOrEqual(0)
      expect(box!.x + box!.width).toBeLessThanOrEqual(320)
    }
  })

  test('sends the selected word with its sentence context', async ({ page }) => {
    let translationRequest: { text?: string; context?: string } = {}
    await page.route('**/api/books/translate', route => {
      translationRequest = route.request().postDataJSON()
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          sourceText: 'tunnel',
          translatedText: 'tünel',
          alternatives: ['topu rakibinin bacağının arasından geçirme'],
          sourceLanguage: 'en',
          targetLanguage: 'tr',
          provider: 'DeepL',
        }),
      })
    })
    await page.goto(appUrl('/kitaplar/hobbit-eng/B01'))

    await page.locator('.bookmd__p', { hasText: 'tunnel' }).first().evaluate(element => {
      const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT)
      let node = walker.nextNode()
      while (node && !node.textContent?.includes('tunnel')) {
        node = walker.nextNode()
      }
      if (!node?.textContent) throw new Error('Book paragraph has no tunnel text')
      const start = node.textContent.indexOf('tunnel')
      const range = document.createRange()
      range.setStart(node, start)
      range.setEnd(node, start + 'tunnel'.length)
      const selection = window.getSelection()
      selection?.removeAllRanges()
      selection?.addRange(range)
      document.dispatchEvent(new Event('selectionchange'))
    })

    const dialog = page.getByRole('dialog', { name: 'Türkçe çeviri' })
    await expect(dialog).toBeVisible()
    await expect(dialog.getByText('tünel')).toBeVisible()
    await expect(dialog.getByText('DeepL')).toBeVisible()
    await expect(dialog.getByText('Diğer karşılıklar')).toHaveCount(0)
    expect(translationRequest).toEqual({
      text: 'tunnel',
      context: 'The hall was like a tunnel.',
    })

    const box = await dialog.boundingBox()
    expect(box?.x).toBe(0)
    expect(box?.width).toBe(320)
    expect(box!.height).toBeLessThanOrEqual(320)
  })

  for (const viewport of [
    { width: 390, height: 844 },
    { width: 768, height: 1024 },
  ]) {
    test(`keeps every books surface inside a ${viewport.width}px viewport`, async ({ page }) => {
      await page.setViewportSize(viewport)

      for (const path of [
        '/kitaplar',
        '/kitaplar/hobbit-eng',
        '/kitaplar/hobbit-eng/B01',
      ]) {
        await page.goto(appUrl(path))
        await expect.poll(
          () => page.evaluate(() => document.documentElement.scrollWidth),
        ).toBeLessThanOrEqual(viewport.width)
      }

      await page.goto(appUrl('/kitaplar'))
      for (const name of ['Yenile', 'Ödev fotoğrafı ekle', 'Çıkış']) {
        const box = await page.getByRole('button', { name }).boundingBox()
        expect(box).not.toBeNull()
        expect(box!.x).toBeGreaterThanOrEqual(0)
        expect(box!.x + box!.width).toBeLessThanOrEqual(viewport.width)
      }
    })
  }
})
