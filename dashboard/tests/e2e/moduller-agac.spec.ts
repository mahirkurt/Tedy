import { test, expect } from '@playwright/test'
import { sabitAc } from './_gorsel-yardim'

type Sayfa = Parameters<typeof sabitAc>[0]

/** Dersi ve ünitesini açar; ağaç hepsi kapalı başlar (Carbon varsayılanı). */
async function konulariAc(page: Sayfa) {
  await page.getByRole('treeitem', { name: /Matematik/ }).click()
  await page.getByRole('treeitem', { name: /Sayılar ve Nicelikler/ }).click()
}

/**
 * Sayfayı başka bir `/api/modules/agac` gövdesiyle açar.
 *
 * Route `sabitAc`'tan SONRA kurulmalı: Playwright en son kurulan route'u önce denetler ve
 * `sabitAc` içindeki `mock(page, GORSEL)` bu ucu da karşılıyor; önce kurulan override
 * sessizce gölgede kalıyordu.
 */
async function baskaGovdeyleAc(page: Sayfa, govde: unknown) {
  await sabitAc(page, '/moduller', 1440, 900)
  await page.route('**/api/modules/agac', r => r.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify(govde),
  }))
  await page.reload()
  await expect(page.locator('.app-shell-content')).toBeVisible()
}

test.describe('Modüller — müfredat ağacı', () => {
  test('hazır modül listesi ve ağaç birlikte çiziliyor', async ({ page }) => {
    await sabitAc(page, '/moduller', 1440, 900)
    await expect(page.getByRole('link', { name: /Tam Sayılar: Sıfırın İki Yanı/ })).toBeVisible()
    await expect(page.getByRole('tree', { name: 'Tüm müfredat' })).toBeVisible()
  })

  test('ünite kapalı başlar, açılınca konular görünür', async ({ page }) => {
    await sabitAc(page, '/moduller', 1440, 900)
    const ders = page.getByRole('treeitem', { name: /Matematik/ })
    await expect(ders).toHaveAttribute('aria-expanded', 'false')
    await ders.click()
    const unite = page.getByRole('treeitem', { name: /Sayılar ve Nicelikler/ })
    await expect(unite).toBeVisible()
    await unite.click()
    await expect(page.getByRole('treeitem', { name: /Mutlak Değer/ })).toBeVisible()
  })

  test('hazır olmayan konu "Hazır değil" diyor, sayfa uydurmuyor', async ({ page }) => {
    await sabitAc(page, '/moduller', 1440, 900)
    await konulariAc(page)
    const yaprak = page.getByRole('treeitem', { name: /Mutlak Değer/ })
    await expect(yaprak).toContainText('Hazır değil')
    await expect(yaprak).toContainText('1. Kitap')
    // sayfa_kaynak "yok": sayfa aralığı hiç yazılmaz (D4).
    await expect(yaprak).not.toContainText('s.')
  })

  test('modülü olan konu bağlantıdır (yeni sekme, geçmiş çalışır)', async ({ page }) => {
    await sabitAc(page, '/moduller', 1440, 900)
    await konulariAc(page)
    // Carbon 1.114.0: href'li düğümde role="treeitem" <a>'nın üzerindedir, <li> role="none".
    await expect(page.getByRole('treeitem', { name: /Tam Sayılar/ }))
      .toHaveAttribute('href', '/moduller/mat7-tam-sayilar/v1')
  })

  test('hazır konu sayfasını ve kazanımını yazıyor', async ({ page }) => {
    await sabitAc(page, '/moduller', 1440, 900)
    await konulariAc(page)
    const yaprak = page.getByRole('treeitem', { name: /Tam Sayılar/ })
    await expect(yaprak).toContainText('s.17–24')
    await expect(yaprak).toContainText('MAT.7.1.1')
  })

  test('dal etiketi konu ve hazır sayısını söylüyor', async ({ page }) => {
    await sabitAc(page, '/moduller', 1440, 900)
    await expect(page.getByRole('treeitem', { name: /Matematik/ })).toContainText('2 konu · 1 hazır')
  })

  test('hazır olmayan konu asistana sorulur', async ({ page }) => {
    await sabitAc(page, '/moduller', 1440, 900)
    await page.evaluate(() => {
      ;(window as unknown as { __sorulan?: string }).__sorulan = undefined
      window.addEventListener('tedy:asistana-sor', (olay: Event) => {
        const detay = (olay as CustomEvent<{ etiket: string; tur: string }>).detail
        ;(window as unknown as { __sorulan?: string }).__sorulan = `${detay.tur}|${detay.etiket}`
      })
    })
    await konulariAc(page)
    await page.getByRole('treeitem', { name: /Mutlak Değer/ }).click()
    await expect.poll(() => page.evaluate(
      () => (window as unknown as { __sorulan?: string }).__sorulan,
    )).toBe('konu|Matematik · Mutlak Değer')
  })

  test('açık dallar sayfa yenilenince kalıyor (İ5)', async ({ page }) => {
    await sabitAc(page, '/moduller', 1440, 900)
    await page.getByRole('treeitem', { name: /Matematik/ }).click()
    await expect(page.getByRole('treeitem', { name: /Matematik/ }))
      .toHaveAttribute('aria-expanded', 'true')
    await page.reload()
    await expect(page.getByRole('treeitem', { name: /Matematik/ }))
      .toHaveAttribute('aria-expanded', 'true')
  })

  test('harita okunamazsa hazır liste kalıyor, cümle açıklıyor (D3)', async ({ page }) => {
    await baskaGovdeyleAc(page, {
      hazir: [{ slug: 'mat7-tam-sayilar', version: 1, title: 'Tam Sayılar: Sıfırın İki Yanı',
        subject: 'Matematik', gradeLevel: '7. Sınıf', mode: 'MODULE', outcomes: ['MAT.7.1.1'],
        ted_link: null, created_at: null, gates: { pass: 17, warn: 0, fail: 0 } }],
      dersler: [], kapsam: {}, hata: 'harita_okunamadi',
    })
    await expect(page.getByText('Müfredat haritası şu an okunamıyor.')).toBeVisible()
    await expect(page.getByRole('link', { name: /Tam Sayılar: Sıfırın İki Yanı/ })).toBeVisible()
    await expect(page.getByRole('tree')).toHaveCount(0)
  })

  // Telefon ölçümü: `tasarim-denetimi` ağacı kapalı gezer, yana kaydırma riski ise üç düzey
  // açıkken doğar. S48 (düğüm ≥ 44 px) ve S50 (girinti) kapısı burada.
  test('390 px: üç düzey açıkken yana kaydırma yok ve düğümler ≥ 44 px', async ({ page }) => {
    await sabitAc(page, '/moduller', 390, 844)
    await konulariAc(page)
    await expect(page.getByRole('treeitem', { name: /Mutlak Değer/ })).toBeVisible()
    const kayma = await page.evaluate(() => {
      const kok = document.scrollingElement
      return kok ? kok.scrollWidth - kok.clientWidth : 0
    })
    expect(kayma).toBeLessThanOrEqual(0)
    const dusukler = await page.evaluate(() => {
      const etiketler = [...document.querySelectorAll('.module-tree .cds--tree-node__label')]
      return etiketler
        .filter(e => (e as HTMLElement).offsetParent !== null)
        .map(e => ({ metin: (e.textContent ?? '').slice(0, 28), h: e.getBoundingClientRect().height }))
        .filter(o => o.h < 44)
    })
    expect(dusukler).toEqual([])
  })

  test('haritası olmayan ders tek cümleyle açıklanıyor (D3)', async ({ page }) => {
    await baskaGovdeyleAc(page, {
      hazir: [], kapsam: {}, hata: null,
      dersler: [{ ders: 'Türkçe', slug: 'turkce', program: { document_id: 51, sayfa: '126-161' },
        kitaplar: [], uniteler: [], konu_sayisi: 0, hazir_sayisi: 0 }],
    })
    await page.getByRole('treeitem', { name: /Türkçe/ }).click()
    await expect(page.getByRole('treeitem', { name: /henüz hazır değil/ })).toBeVisible()
  })
})
