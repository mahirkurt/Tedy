#!/usr/bin/env node
// Kapsam kılavuzunu A4 PDF'e basar (plan 2026-10-25 Görev 1, 14). Ağsız: baski.html ve varlıkları dashboard-dist'ten,
// /api/hazirlik/** isteği --model dosyasından sahte bir kökte sunulur; başka her istek kesilir. Chrome kanalı
// (makinedeki /usr/bin/google-chrome; Playwright'ın headless-shell indirmesi bu makinede takılıyor).
// Çıkış: 0 tamam, 2 argüman (dist'te baski.html yoksa da), 3 sayfa hatası, 4 zaman aşımı. Yakalanmayan istisna Node'u
// 1 ile bitirir; çağıran (src/hazirlik_pdf.py) sıfırdan farklı her çıkışı hata sayar.
// Çalışma zamanı bağımlılığı: `@playwright/test` package.json'da devDependency'dir ama sunucu PDF basımı ona dayanır.
// Canlı node_modules `npm install --omit=dev` ile kurulmamalı (kurulursa PDF ucu 503 verir).
import { statSync } from 'node:fs'
import { readFile, writeFile } from 'node:fs/promises'
import { join } from 'node:path'
import { chromium } from '@playwright/test'
import { KOK, argumanlariCoz, baskiAdresi, guvenliYol, mimeTuru } from './kilavuzPdfOrtak.mjs'

let a
try {
  a = argumanlariCoz(process.argv.slice(2))
} catch (e) {
  console.error(String(e?.message ?? e))
  process.exit(2)
}
// Derlenmemiş dist: hazır sinyalini (--sure, 45 sn'ye kadar) beklemeden açıkça söyle.
if (!(() => { try { return statSync(join(a.dist, 'baski.html')).isFile() } catch { return false } })()) {
  console.error(`dist'te baski.html yok: ${join(a.dist, 'baski.html')} (önce npm run build)`)
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
  // Sayfa açılamazsa hazır sinyali beklenmez. Chrome boş gövdeli hata yanıtında goto'yu düşürür (yanıt nesnesi
  // gelmez): durum kodu ana belgenin yanıt olayından okunur.
  let anaDurum = null
  sayfa.on('response', r => { if (r.request().isNavigationRequest() && r.frame() === sayfa.mainFrame()) anaDurum = r.status() })
  try {
    const yanit = await sayfa.goto(baskiAdresi(a.sorgu, a.duz))
    if (!yanit?.ok()) throw new Error('yanıt başarısız')
  } catch (e) {
    console.error(`baskı sayfası açılamadı (HTTP ${anaDurum ?? '?'}): ${String(e?.message ?? e).split('\n')[0]}`)
    kod = 3
  }
  if (kod === 0) {
    try {
      await sayfa.waitForFunction(() => window.__KILAVUZ_HAZIR__ || window.__KILAVUZ_HATA__, null, { timeout: a.sure })
    } catch {
      console.error('zaman aşımı: baskı görünümünün hazır sinyali gelmedi')
      kod = 4
    }
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
