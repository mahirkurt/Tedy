import assert from 'node:assert/strict'
import { test } from 'node:test'
import { apiHataCumlesi, apiHataTuru, sunucuMesaji } from '../src/utils/apiHatasi.ts'

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

// D15: bir hata yanıtının gövdesi sunucunun kendi cümlesini taşıyabilir (`{error, mesaj}`); yalnız o cümle ekrana çıkar.
test('sunucuMesaji: gövdedeki `mesaj` cümlesi; başka her şey null', () => {
  assert.equal(sunucuMesaji('{"error":"tablo_eski","mesaj":"Yeni yılın tabloları bekleniyor."}'), 'Yeni yılın tabloları bekleniyor.')
  assert.equal(sunucuMesaji('{"error":"tablo_eski"}'), null)
  assert.equal(sunucuMesaji('{"mesaj":""}'), null)
  assert.equal(sunucuMesaji('{"mesaj":42}'), null)
  assert.equal(sunucuMesaji('<html>502 Bad Gateway</html>'), null)
  assert.equal(sunucuMesaji(''), null)
  assert.equal(sunucuMesaji('null'), null)
  assert.equal(sunucuMesaji(JSON.stringify({ mesaj: 'a'.repeat(400) })), null)
})
