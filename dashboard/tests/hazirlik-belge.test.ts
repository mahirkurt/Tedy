import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { bolumler, damgaMetni, tabloParcalari, tumBloklar, ustBilgi } from '../src/hazirlik/belge.ts'
import type { KilavuzModeli } from '../src/hazirlik/tipler.ts'

// Fikstür modelden üretilmiştir (scripts/hazirlik_fiksturleri.py): şekil varsayılmaz.
const oku = (ad: string): KilavuzModeli =>
  JSON.parse(readFileSync(new URL(`./e2e/fixtures/hazirlik/${ad}.json`, import.meta.url), 'utf8'))
const KESIN = oku('fen-bilimleri-1-kilavuz')
const OLASI = oku('fen-bilimleri-1-olasi-kilavuz')

test('bölümler sırası: özet, karşılaştırma, üniteler, doğrulama, plan, kaynaklar; ebeveyn başa', () => {
  assert.deepEqual(bolumler(KESIN).map(b => b.ad), ['Özet', 'Senaryo Karşılaştırması', '1. Ünite · Uzay Çağı',
    '2. Ünite · Kuvvet ve Enerjiyi Keşfedelim', 'Duyuru Doğrulaması', 'Çalışma Planı', 'Kaynaklar'])
  assert.equal(bolumler(oku('fen-bilimleri-1-kilavuz-ebeveyn'))[0].ad, 'Ebeveyn Özeti')
  assert.deepEqual(bolumler(KESIN).map(b => b.id).slice(0, 3), ['bolum-ozet', 'bolum-karsilastirma', 'bolum-unite-1'])
})

test('üst bilgi: olası kipte tek senaryo "bu" diye yazılmaz (K8)', () => {
  assert.equal(ustBilgi(KESIN), 'Fen Bilimleri · 1. yazılı · 2. senaryo')
  assert.equal(ustBilgi(OLASI), 'Fen Bilimleri · 1. yazılı · bütün senaryolar (olası)')
  assert.equal(ustBilgi({ ...OLASI, senaryo: 3 }), 'Fen Bilimleri · 1. yazılı · 3. senaryo (olası)')
})

test('damga TEDY ile başlar, tablo ve kitap sürümünü taşır (K12)', () => {
  const d = damgaMetni(KESIN)
  assert.match(d, /^TEDY · MEB tablosu 10\.09\.2026 · Fen Bilimleri 7 \(1\. Kitap\) 2026-2027 \([0-9a-f]{12}\) · üretim 25\.10\.2026$/)
  assert.match(damgaMetni(oku('matematik-1-kilavuz')), /kitap haritası yok/)
})

test('olası fikstürde hiçbir blok tek soru sayısı taşımaz (K8)', () => {
  assert.ok(tumBloklar(OLASI).length > 0)
  assert.ok(tumBloklar(OLASI).every(b => b.soru === null && b.aralik !== null))
  assert.deepEqual(tumBloklar(null), [])
})

test('tablo parçaları: ekranda tek tablo; baskıda ünite başına ayrı tablo ve toplam tek başına (Y5)', () => {
  const m = KESIN.matris
  const tek = tabloParcalari(m, false)
  assert.equal(tek.length, 1)
  assert.deepEqual(tek[0], { gruplar: m.gruplar, toplam: true })
  const unite = tabloParcalari(m, true)
  assert.equal(unite.length, m.gruplar.length + 1)
  assert.ok(unite.slice(0, -1).every(p => p.gruplar.length === 1 && !p.toplam))
  assert.deepEqual(unite.slice(0, -1).map(p => p.gruplar[0].baslik), m.gruplar.map(g => g.baslik))
  assert.deepEqual(unite[unite.length - 1], { gruplar: [], toplam: true })
  // Hiçbir satır kaybolmaz ve ikilenmez.
  const kodlar = (ps: typeof unite) => ps.flatMap(p => p.gruplar.flatMap(g => g.satirlar.map(s => s.kod)))
  assert.deepEqual(kodlar(unite), kodlar(tek))
})
