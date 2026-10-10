import assert from 'node:assert/strict'
import { test } from 'node:test'
import { girisHatasi } from '../src/utils/girisHatasi.ts'

// B43 (D3, D4): the sign-in page says what happened in Turkish, never the server's internal string
// ("Invalid token: …", "No credential provided") or a Turkish written without its letters ("Giris basarisiz").
test('a refused account is told so, in full Turkish', () => {
  assert.equal(girisHatasi(403), 'Bu Google hesabıyla giriş yapılamaz. Ailenin tanımlı hesabıyla dene.')
})

test('any other refusal is one human sentence, no server text', () => {
  for (const durum of [400, 401, 500, 502]) {
    const metin = girisHatasi(durum)
    assert.equal(metin, 'Giriş yapılamadı. Yeniden dene.')
    assert.doesNotMatch(metin, /Invalid|token|credential|HTTP|\d{3}/)
  }
})

test('no connection is its own sentence', () => {
  assert.equal(girisHatasi(null), 'Bağlantı kurulamadı. İnternetini kontrol edip yeniden dene.')
})
