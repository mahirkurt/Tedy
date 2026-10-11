import assert from 'node:assert/strict'
import { test } from 'node:test'
import { apiHataCumlesi, apiHataTuru } from '../src/utils/apiHatasi.ts'

// B43 (D3, D4): useApi reports a failure by kind; the reader gets a sentence, never the fetch's own text.
test('the kind follows the status', () => {
  assert.equal(apiHataTuru(null), 'baglanti')
  assert.equal(apiHataTuru(401), 'oturum')
  assert.equal(apiHataTuru(403), 'yetki')
  assert.equal(apiHataTuru(404), 'bulunamadi')
  assert.equal(apiHataTuru(500), 'sunucu')
  assert.equal(apiHataTuru(200, true), 'bicim')
})

test('every kind is a Turkish sentence with no status code or English', () => {
  for (const tur of ['baglanti', 'oturum', 'yetki', 'bulunamadi', 'sunucu', 'bicim'] as const) {
    const { baslik, ayrinti } = apiHataCumlesi(tur, 'Modüller')
    assert.equal(baslik, 'Modüller yüklenemedi.')
    assert.match(ayrinti, /\.$/)
    assert.doesNotMatch(`${baslik} ${ayrinti}`, /HTTP|JSON|\d{3}|Failed|fetch|response/i)
  }
})
