import assert from 'node:assert/strict'
import { test } from 'node:test'
import { sayfaAdi, baslaticiGorunur, sayfaEtiketi, SAYFA_ETIKETLERI } from '../src/asistan/sayfaBaglami.ts'
import { sayfaSorulari } from '../src/asistan/sayfaSorulari.ts'

test('yoldan sayfa adı; ayrıntı yolları ve bilinmeyenler', () => {
  assert.equal(sayfaAdi('/'), 'bugun')
  assert.equal(sayfaAdi('/isler'), 'isler')
  assert.equal(sayfaAdi('/kitaplar/lotr'), 'kitaplar')
  assert.equal(sayfaAdi('/asistan'), null)
  assert.equal(sayfaAdi('/xyz'), null)
  assert.equal(SAYFA_ETIKETLERI.kitaplar, 'Tedy Books')
})

test('başlatıcı nerede görünür', () => {
  assert.equal(baslaticiGorunur('/isler', 'full', false, true), true)
  for (const yol of ['/asistan', '/moduller/kesir/v2', '/moduller/taslak/abc', '/kitaplar/lotr/b01'])
    assert.equal(baslaticiGorunur(yol, 'full', false, true), false, yol)
  assert.equal(baslaticiGorunur('/isler', 'reader', false, true), false)
  assert.equal(baslaticiGorunur('/isler', 'full', true, true), false)
  assert.equal(baslaticiGorunur('/isler', 'full', false, false), false)
  assert.equal(baslaticiGorunur('/moduller', 'full', false, true), true)
})

test('her sayfanın iki hitapta 2-3 sorusu var', () => {
  for (const ad of Object.keys(SAYFA_ETIKETLERI)) for (const okur of ['ogrenci', 'aile'] as const) {
    const s = sayfaSorulari(ad, okur)
    assert.ok(s.length >= 2 && s.length <= 3, `${ad}/${okur}`)
  }
  assert.ok(sayfaSorulari('isler', 'aile').every(s => !/\b(başlayayım|yapayım)\b/.test(s)))
})

test('adresten gelen sayfa adı yalnız bilinen adlardan biri olabilir (nesne prototipi adları dahil değil)', () => {
  assert.equal(sayfaEtiketi('notlar'), 'Notlar')
  for (const ad of ['xyz', 'toString', 'constructor', '__proto__', '', null]) assert.equal(sayfaEtiketi(ad), null, String(ad))
})
