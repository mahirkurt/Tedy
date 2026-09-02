import { test, expect } from '@playwright/test'

test.describe('API smoke tests', () => {
  const endpoints = [
    '/api/schedule',
    '/api/homework',
    '/api/sebit',
    '/api/grades',
    '/api/calendar',
    '/api/teams',
    '/api/content',
    '/api/announcements',
    '/api/health',
    '/api/progress/ec',
    '/api/progress/a3k',
  ]

  for (const ep of endpoints) {
    test(`${ep} returns 200`, async ({ request }) => {
      const resp = await request.get(ep)
      expect(resp.status()).toBe(200)
    })
  }

  test('schedule has expected structure', async ({ request }) => {
    const resp = await request.get('/api/schedule')
    const data = await resp.json()
    expect(data).toHaveProperty('weeks')
    expect(data).toHaveProperty('latest')
    expect(data).toHaveProperty('today')
    expect(Array.isArray(data.weeks)).toBe(true)
  })

  test('homework has expected structure', async ({ request }) => {
    const resp = await request.get('/api/homework')
    const data = await resp.json()
    expect(data).toHaveProperty('summary')
    expect(data).toHaveProperty('homework')
  })

  test('calendar has events array', async ({ request }) => {
    const resp = await request.get('/api/calendar')
    const data = await resp.json()
    expect(data).toHaveProperty('events')
    expect(Array.isArray(data.events)).toBe(true)
  })

  test('teams has expected structure', async ({ request }) => {
    const resp = await request.get('/api/teams')
    const data = await resp.json()
    expect(data).toHaveProperty('activities')
    expect(data).toHaveProperty('ogep')
  })

  test('health has expected structure', async ({ request }) => {
    const resp = await request.get('/api/health')
    const data = await resp.json()
    expect(data).toHaveProperty('timestamp')
    expect(data).toHaveProperty('success')
  })

  test('private-lessons has expected structure', async ({ request }) => {
    const resp = await request.get('/api/private-lessons')
    const data = await resp.json()
    expect(data).toHaveProperty('lessons')
    expect(Array.isArray(data.lessons)).toBe(true)
  })

  test('calendar unified has events array', async ({ request }) => {
    const resp = await request.get('/api/calendar/unified')
    const data = await resp.json()
    expect(data).toHaveProperty('events')
    expect(Array.isArray(data.events)).toBe(true)
  })

  test('/api/auth/me returns bypass test user in e2e env', async ({ request }) => {
    const resp = await request.get('/api/auth/me')
    expect(resp.status()).toBe(200)
    const data = await resp.json()
    expect(data.email).toBe('test@tedy.online')
  })
})

test.describe('SPA serving', () => {
  test('root serves HTML', async ({ request }) => {
    const resp = await request.get('/')
    expect(resp.status()).toBe(200)
    const text = await resp.text()
    expect(text.toLowerCase()).toContain('<!doctype html>')
  })

  test('page loads in browser', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('body')).toBeVisible()
  })

  test('header shows sync tag and popover details', async ({ page }) => {
    await page.goto('/')
    const syncTrigger = page.getByRole('button', { name: 'Senkron durumunu göster' })
    await expect(syncTrigger).toBeVisible()
    await syncTrigger.click()
    await expect(page.getByRole('dialog', { name: 'Senkron sağlık bilgisi' })).toBeVisible()
    await expect(page.getByText('Senkron Sağlığı')).toBeVisible()
    await expect(page.getByText('Son Sync:')).toBeVisible()
    await expect(page.getByText('Son Başarılı Tam Sync:')).toBeVisible()
  })

  test('header remains usable on mobile viewport', async ({ browser }) => {
    const context = await browser.newContext({
      viewport: { width: 375, height: 812 },
      userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
      isMobile: true,
      hasTouch: true,
      deviceScaleFactor: 3,
    })
    const page = await context.newPage()
    await page.goto('/')

    await expect(page.getByRole('banner')).toBeVisible()
    await expect(page.getByAltText('TEDY')).toBeVisible()
    // Sync status moved to the footer on a phone so Odak can stay in the
    // header. The header's job here is the working-state switch.
    await expect(page.getByRole('switch', { name: 'Odak' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Çıkış' })).toBeVisible()

    await context.close()
  })

  test('all side nav routes are reachable and render main content', async ({ page }) => {
    const routes = [
      '/',
      '/program',
      '/odevler',
      '/notlar',
      '/takvim',
      '/takimlar',
      '/dersler',
      '/ilerleme',
      '/duyurular',
      '/profil',
    ]

    for (const route of routes) {
      const resp = await page.goto(route)
      expect(resp?.ok()).toBeTruthy()
      await expect(page.getByRole('banner')).toBeVisible()
      await expect(page.locator('.app-shell-content')).toBeVisible()
    }
  })

  test('health popover opens and closes with Escape', async ({ page }) => {
    await page.goto('/')
    const trigger = page.getByRole('button', { name: 'Senkron durumunu göster' })
    await trigger.click()
    await expect(page.getByRole('dialog', { name: 'Senkron sağlık bilgisi' })).toBeVisible()
    await page.keyboard.press('Escape')
    await expect(page.getByRole('dialog', { name: 'Senkron sağlık bilgisi' })).toBeHidden()
  })

  test('focus mode toggle is visible and operable via keyboard', async ({ page }) => {
    await page.goto('/')
    const content = page.locator('.app-shell-content')
    const beforeClass = await content.getAttribute('class')
    const focusSwitch = page
      .locator('.dashboard-header__focus-toggle .cds--toggle__switch')
      .first()

    await expect(focusSwitch).toBeVisible()
    await focusSwitch.click()

    await expect
      .poll(async () => content.getAttribute('class'))
      .not.toBe(beforeClass)
  })

  test('photo homework modal opens and can be closed without upload', async ({ page }) => {
    await page.goto('/')
    const trigger = page.getByRole('button', { name: 'Ödev fotoğrafı ekle' })
    await trigger.click()
    const modal = page.locator('.cds--modal').filter({ hasText: 'Ödev Fotoğrafı Ekle' })
    await expect(modal).toBeVisible()
    await page.getByRole('button', { name: 'İptal' }).click()
    await expect(modal).toBeHidden()
  })
})
