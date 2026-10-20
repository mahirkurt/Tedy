import { test } from 'node:test'
import assert from 'node:assert/strict'
import { basliga } from '../src/utils/baslik.ts'

// Shared with the module template's `basliga` (tests/test_modul_baslik_duzeni.py runs the same
// table through the template's JavaScript).
export const ORNEKLER: [string, string][] = [
  ['Tam sayılar: sıfırın iki yanı', 'Tam Sayılar: Sıfırın İki Yanı'],
  ['Uzay araçları (1): sonda, roket, uydu', 'Uzay Araçları (1): Sonda, Roket, Uydu'],
  ['Teleskop uzayda mı, yerde mi?', 'Teleskop Uzayda mı, Yerde mi?'],
  ["Türkiye'nin uydu yolculuğu", "Türkiye'nin Uydu Yolculuğu"],
  ['Sınıf ve okul duyuruları', 'Sınıf ve Okul Duyuruları'],
  ['ve ile başlayan', 'Ve ile Başlayan'],
  ['MAT.7.1.1 kazanımı', 'MAT.7.1.1 Kazanımı'],
  ['UTC+3 ile saat', 'UTC+3 ile Saat'],
  ['“içinde” tırnak', '“İçinde” Tırnak'],
  ['ışık ve ılık', 'Işık ve Ilık'],
  ['Zaten Büyük', 'Zaten Büyük'],
  ['  boşluk  korunur ', '  Boşluk  Korunur '],
  ['', ''],
]

test('başlık düzeni Türkçe kurallarla uygulanır', () => {
  for (const [girdi, beklenen] of ORNEKLER) assert.equal(basliga(girdi), beklenen, girdi)
})

test('başlık düzeni bir harfi asla küçültmez', () => {
  assert.equal(basliga('TEDY ve MEB'), 'TEDY ve MEB')
  assert.equal(basliga('KTT sonuçları'), 'KTT Sonuçları')
})
