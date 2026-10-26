import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { arsivYonu } from '../src/utils/moduleLink.ts'

// GET /api/modules/<slug>/v<N>/ticket → 410 {arsivlendi: true, guncel} (src/dashboard_api.py, 2026-10-24).

test('arşivlenmiş sürüm güncel sürümün rotasına yönlenir', () => {
  assert.deepEqual(arsivYonu('fen5-su', 1, { arsivlendi: true, guncel: 3 }),
    { tur: 'yonlendir', yol: '/moduller/fen5-su/v3' })
})

test('güncel sürüm yoksa modül artık yayında değildir', () => {
  assert.deepEqual(arsivYonu('fen5-su', 1, { arsivlendi: true, guncel: null }), { tur: 'yayinda_degil' })
})

test('kendine ya da geçersiz sürüme yönlenmez: döngü ve uydurma rota yok', () => {
  assert.deepEqual(arsivYonu('fen5-su', 3, { arsivlendi: true, guncel: 3 }), { tur: 'yayinda_degil' })
  for (const guncel of [0, -1, 1.5, '3', 10000, undefined]) {
    assert.deepEqual(arsivYonu('fen5-su', 1, { arsivlendi: true, guncel }), { tur: 'yayinda_degil' })
  }
})

test('yalnız daha yeni sürüme yönlenir: güncel ≤ sürüm ise yayında değil (döngü garantisi, inceleme turu 1)', () => {
  // Arşivlenmiş v5 eski bir v3'ü "güncel" diye gösterirse v3 de arşivse v5'e geri gönderebilir: iki adres arasında
  // gidip gelme. Yönlenme yalnız ileri gider; zincir sonlu, döngü imkânsız.
  assert.deepEqual(arsivYonu('fen5-su', 5, { arsivlendi: true, guncel: 3 }), { tur: 'yayinda_degil' })
  assert.deepEqual(arsivYonu('fen5-su', 5, { arsivlendi: true, guncel: 4 }), { tur: 'yayinda_degil' })
  assert.deepEqual(arsivYonu('fen5-su', 5, { arsivlendi: true, guncel: 5 }), { tur: 'yayinda_degil' })
  assert.deepEqual(arsivYonu('fen5-su', 5, { arsivlendi: true, guncel: 6 }), { tur: 'yonlendir', yol: '/moduller/fen5-su/v6' })
  assert.deepEqual(arsivYonu('fen5-su', 1, { arsivlendi: true, guncel: 9999 }),
    { tur: 'yonlendir', yol: '/moduller/fen5-su/v9999' })
})

test('arşiv gövdesi değilse karar yok (genel hata cümlesi kalır)', () => {
  for (const govde of [null, undefined, 'x', {}, { error: 'not_found' }, { arsivlendi: 'true', guncel: 2 }]) {
    assert.equal(arsivYonu('fen5-su', 1, govde), null)
  }
})

test('yayında olmayan modülün sayfası başlığını korur ve Modüller sayfasına gerçek bağlantı verir (inceleme turu 1)', () => {
  // Davranışın ölçümü e2e'dedir (modul-arsivi.spec.ts); burası yapıyı sabitler: breadcrumb ve başlık (bilinmiyorsa
  // "Modül") yayında değil dalında da çizilir, cümle /moduller'e uygulama içi bağlantı (IcBaglanti) taşır.
  const kaynak = readFileSync(new URL('../src/components/ModuleViewer.tsx', import.meta.url), 'utf8')
  const bas = kaynak.indexOf("if (ticket.status === 'yayinda_degil')")
  const dal = kaynak.slice(bas, kaynak.indexOf("if (ticket.status === 'error')", bas))
  assert.ok(bas > 0 && dal.length > 0)
  assert.match(dal, /\{bas\}/)
  assert.match(dal, /<p className="module-viewer__yonlendirme">\s*Yayındaki modüller <IcBaglanti href="\/moduller" inline>Modüller<\/IcBaglanti> sayfasında\.\s*<\/p>/)
  // InlineNotification canlı bölgedir; Carbon içinde etkileşimli öğe görünce hata fırlatır (useNoInteractiveChildren).
  assert.match(dal, /title="Bu modül artık yayında değil\." \/>/)
  assert.match(kaynak, /yedekBaslik=\{ticket\.status === 'yayinda_degil' \? 'Modül' : undefined\}/)
  const baslik = readFileSync(new URL('../src/components/ModulBasligi.tsx', import.meta.url), 'utf8')
  assert.match(baslik, /veri\?\.baslik \? basliga\(veri\.baslik\) : yedekBaslik/)
  const ic = readFileSync(new URL('../src/components/patterns/IcBaglanti.tsx', import.meta.url), 'utf8')
  // Tıklama mantığı ortak kancadadır (useIcGezinme: kart düğmesiyle paylaşılır); bağlantı onu kullanır.
  assert.match(ic, /onClick=\{useIcGezinme\(href\)\}/)
  const kanca = readFileSync(new URL('../src/hooks/useIcGezinme.ts', import.meta.url), 'utf8')
  assert.match(kanca, /uygulamaIcindeAc\(e, href, e\.currentTarget\.getAttribute\('target'\)\)/)
})

test('içerik çizilmeyen görünümde AI etiketi yok: yayında değil ve hata dalları (inceleme turu 3)', () => {
  // Sayfada yapay zekâ yardımıyla yazılmış bir içerik yokken (çerçeve çizilmiyor) etiket ve "Yapay zekâ yardımıyla
  // hazırlanmış modül" notu da çizilmez; etiketin penceresi yalnız "Ayrıntılar şu an alınamadı" derdi.
  const kaynak = readFileSync(new URL('../src/components/ModuleViewer.tsx', import.meta.url), 'utf8')
  assert.match(kaynak, /const icerikYok = ticket\.status === 'yayinda_degil' \|\| ticket\.status === 'error'/)
  assert.match(kaynak, /aiEtiketi=\{icerikYok \? undefined : <ModulAiEtiketi durum=\{aciklama\} \/>\}/)
  const baslik = readFileSync(new URL('../src/components/ModulBasligi.tsx', import.meta.url), 'utf8')
  assert.match(baslik, /aiEtiketi\?: ReactNode/)
  assert.match(baslik, /\{aiEtiketi && \(\s*<div className="modul-baslik__ai">/)
})
