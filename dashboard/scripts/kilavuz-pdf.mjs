#!/usr/bin/env node
// Kapsam kılavuzunu A4 PDF'e basar (plan 2026-10-25 Görev 1, 14). Ağsız: baski.html ve varlıkları dashboard-dist'ten,
// /api/hazirlik/** isteği --model dosyasından sahte bir kökte sunulur; başka her istek kesilir. Chrome kanalı
// (makinedeki /usr/bin/google-chrome; Playwright'ın headless-shell indirmesi bu makinede takılıyor).
// Çıkış: 0 tamam, 2 argüman, 3 sayfa hatası, 4 zaman aşımı.
import { readFile, writeFile } from 'node:fs/promises'
import { chromium } from '@playwright/test'
import { KOK, argumanlariCoz, baskiAdresi, guvenliYol, mimeTuru } from './kilavuzPdfOrtak.mjs'

let a
try {
  a = argumanlariCoz(process.argv.slice(2))
} catch (e) {
  console.error(String(e?.message ?? e))
  process.exit(2)
}
const model = a.model ? await readFile(a.model) : null
// Düz yol (yedek): Chrome'un kendi üst/alt bilgisi. Başlık belgenin <title>'ıdır (baskı görünümü yazar).
// Chrome üst/alt bilgi şablonu web yazı tipi kullanamaz (ölçüldü: data URL @font-face de DejaVu Sans'a düşer); punto
// 8 pt tutulur (K3). Düz yolda üst/alt bilgi sistem yazı tipidir — Kanun K5 B metni, borç KK-3.
// Şablon CSS değişkeni okuyamaz: #525252 Carbon gray-70'tir (--cds-text-secondary), kâğıttaki ikincil metin rengi.
const UST = '<div style="font-size: 8pt; width: 100%; padding: 0 16mm; color: #525252;"><span class="title"></span></div>'
const ALT = '<div style="font-size: 8pt; width: 100%; padding: 0 16mm; color: #525252; display: flex; justify-content: space-between;"><span>TEDY</span><span>s. <span class="pageNumber"></span>/<span class="totalPages"></span></span></div>'

const tarayici = await chromium.launch({ channel: 'chrome', headless: true })
let kod = 0
try {
  const sayfa = await tarayici.newPage()
  sayfa.on('pageerror', e => console.error('sayfa hatası:', e.message))
  await sayfa.route('**/*', async yol => {
    const url = new URL(yol.request().url())
    if (url.origin !== KOK) return yol.abort()
    if (url.pathname.startsWith('/api/hazirlik/')) {
      return model
        ? yol.fulfill({ status: 200, contentType: 'application/json', body: model })
        : yol.fulfill({ status: 404, body: '' })
    }
    const dosya = guvenliYol(a.dist, url.pathname === '/' ? '/baski.html' : url.pathname)
    if (!dosya) return yol.fulfill({ status: 404, body: '' })
    try {
      return yol.fulfill({ status: 200, contentType: mimeTuru(dosya), body: await readFile(dosya) })
    } catch {
      return yol.fulfill({ status: 404, body: '' })
    }
  })
  await sayfa.goto(baskiAdresi(a.sorgu, a.duz))
  try {
    await sayfa.waitForFunction(() => window.__KILAVUZ_HAZIR__ || window.__KILAVUZ_HATA__, null, { timeout: a.sure })
  } catch {
    console.error('zaman aşımı: baskı görünümünün hazır sinyali gelmedi')
    kod = 4
  }
  if (kod === 0) {
    const hata = await sayfa.evaluate(() => window.__KILAVUZ_HATA__ ?? null)
    if (hata) {
      console.error('baskı görünümü hatası:', hata)
      kod = 3
    }
  }
  if (kod === 0) {
    const pdf = await sayfa.pdf({
      preferCSSPageSize: true, printBackground: true, tagged: true, outline: true,
      ...(a.duz ? { displayHeaderFooter: true, headerTemplate: UST, footerTemplate: ALT } : {}),
    })
    await writeFile(a.cikti, pdf)
  }
} finally {
  await tarayici.close()
}
process.exit(kod)
