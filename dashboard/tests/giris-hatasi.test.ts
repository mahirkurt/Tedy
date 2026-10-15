import assert from 'node:assert/strict'
import { test } from 'node:test'
import { girisBildirimi } from '../src/utils/girisHatasi.ts'

// B43 (D3, D4): the sign-in page says what happened in Turkish, never the server's internal string
// ("Invalid token: …", "No credential provided") or a Turkish written without its letters ("Giris basarisiz").
// 2026-10-15 (giriş sayfası yenilemesi): the notification's title names the reason and the sentence says what
// to do; the sentence never repeats the title.
test('a refused account is told so, in full Turkish', () => {
  assert.deepEqual(girisBildirimi(403), {
    baslik: 'Bu hesap tanımlı değil',
    metin: 'Bu Google hesabıyla giriş yapılamaz. Ailenin tanımlı hesabıyla dene.',
  })
})

test('any other refusal is one human sentence, no server text', () => {
  for (const durum of [400, 401, 500, 502]) {
    const { baslik, metin } = girisBildirimi(durum)
    assert.equal(baslik, 'Giriş yapılamadı')
    assert.equal(metin, 'Google girişi doğrulanamadı. Yeniden dene.')
    assert.doesNotMatch(baslik + metin, /Invalid|token|credential|HTTP|\d{3}/)
  }
})

test('no connection is its own sentence', () => {
  assert.deepEqual(girisBildirimi(null), {
    baslik: 'Bağlantı kurulamadı',
    metin: 'İnternetini kontrol edip yeniden dene.',
  })
})

test('a title never ends in a full stop and the sentence never repeats it', () => {
  for (const durum of [null, 400, 403, 500]) {
    const { baslik, metin } = girisBildirimi(durum)
    assert.doesNotMatch(baslik, /[.!]$/)
    assert.ok(!metin.startsWith(baslik), `${durum}: ${metin}`)
  }
})
