import { test } from 'node:test'
import assert from 'node:assert/strict'
import { senaryoGorunumu } from '../src/utils/sinavSenaryosu.ts'
import type { SinavSenaryosu } from '../src/types.ts'

const TABAN: SinavSenaryosu = {
  durum: 'dogrulandi', ders: 'Türkçe', sinav_no: 1, anilan: [4], cumle: '4. senaryo ağırlıklı',
  senaryo: 4, toplam: 7,
  dagilim: [
    { kod: 'T.O.7.4', metin: 'Söz varlığı', soru: 1, duyuruda: true },
    { kod: 'T.O.7.5', metin: 'Metnin yüzey anlamını belirleyebilme', soru: 2, duyuruda: true },
    { kod: 'T.Y.7.21', metin: 'Yazım kuralları', soru: 1, duyuruda: false },
  ],
  eslesen_konu_sayisi: 2, eslesmeyen_konular: [], senaryo_disi_konular: [], adaylar: [], senaryo_sayisi: 6,
  kaynak: 'https://odsgm.meb.gov.tr/x', meb_guncelleme: '2026-09-10T17:27',
}

test('doğrulandı: onay, tek cümle, açılır liste', () => {
  const g = senaryoGorunumu(TABAN)
  assert.equal(g.ikon, 'onay')
  assert.deepEqual(g.cumleler, ['Duyurudaki 4. senaryo MEB tablosunda var: 7 soru. Duyurudaki 2 konu bu senaryoda.'])
  assert.equal(g.dugme, 'Senaryonun 3 çıktısını göster')
  assert.deepEqual(g.satirlar[1], { metin: '2 soru · T.O.7.5 Metnin yüzey anlamını belirleyebilme', duyuruda: true })
  assert.equal(g.kaynak, 'MEB, 10.09.2026')
})

test('birden çok senaryo anıldı', () => {
  const g = senaryoGorunumu({ ...TABAN, anilan: [3, 4], senaryo: 3 })
  assert.equal(g.cumleler[0], 'Duyuru 3. ve 4. senaryo diyor; 3. senaryo MEB tablosunda var: 7 soru. Duyurudaki 2 konu bu senaryoda.')
})

test('kısmen: uyarı ve senaryo dışı konu', () => {
  const g = senaryoGorunumu({ ...TABAN, durum: 'kismen', eslesen_konu_sayisi: 3, senaryo_disi_konular: ['Derin anlam'] })
  assert.equal(g.ikon, 'uyari')
  assert.deepEqual(g.cumleler, [
    'Duyurudaki 4. senaryo MEB tablosunda var: 7 soru. Duyurudaki 2 konu bu senaryoda.',
    'Şu konu 4. senaryoda yok: Derin anlam.',
  ])
})

test('senaryo yok', () => {
  const g = senaryoGorunumu({ ...TABAN, durum: 'senaryo_yok', anilan: [9], senaryo: null, toplam: null, dagilim: [] })
  assert.equal(g.ikon, 'uyari')
  assert.deepEqual(g.cumleler, ['Duyuru 9. senaryo diyor; MEB tablosunda bu sınav için 1–6 var.'])
  assert.equal(g.dugme, null)
})

test('ülke geneli', () => {
  const g = senaryoGorunumu({ ...TABAN, durum: 'ulke_geneli', anilan: [], senaryo: null, dagilim: [], senaryo_sayisi: 0 })
  assert.equal(g.ikon, null)
  assert.deepEqual(g.cumleler, ['Bu sınav ülke genelinde ortak yapılır; senaryo yok.'])
})

test('belirtilmedi: tahmin etiketi, tekil ve çoğul', () => {
  const b = { ...TABAN, durum: 'belirtilmedi' as const, anilan: [], senaryo: null, toplam: null, dagilim: [] }
  assert.deepEqual(senaryoGorunumu({ ...b, adaylar: [] }).cumleler,
    ['Duyuruda senaryo belirtilmedi · MEB tablosunda 6 senaryo var.'])
  assert.deepEqual(senaryoGorunumu({ ...b, adaylar: [4] }).cumleler[1],
    'Duyurudaki konular 4. senaryoyla uyumlu (TEDY’nin tahmini).')
  assert.deepEqual(senaryoGorunumu({ ...b, adaylar: [2, 3, 4] }).cumleler[1],
    'Duyurudaki konular 2., 3. ve 4. senaryolarla uyumlu (TEDY’nin tahmini).')
})

test('eşleşmeyen konu cümlesi', () => {
  const g = senaryoGorunumu({ ...TABAN, eslesmeyen_konular: ['Osmanlı'] })
  assert.equal(g.cumleler.at(-1), 'MEB tablosunda karşılığı bulunamayan konu: Osmanlı.')
})

// Spec §3.2/§10: "ağırlıklı" gibi nüans kartta kaybolmasın — duyurunun cümlesi aynen gösterilir.
test('duyurunun cümlesi doğrulandı, kısmen ve senaryo yok durumlarında "Duyuru: «…»" satırıdır', () => {
  assert.equal(senaryoGorunumu(TABAN).duyuru, 'Duyuru: «4. senaryo ağırlıklı»')
  const kismen = senaryoGorunumu({ ...TABAN, durum: 'kismen', eslesen_konu_sayisi: 3, senaryo_disi_konular: ['Derin anlam'] })
  assert.equal(kismen.duyuru, 'Duyuru: «4. senaryo ağırlıklı»')
  const yok = senaryoGorunumu({ ...TABAN, durum: 'senaryo_yok', anilan: [9], cumle: 'Sınav 9. senaryo ağırlıklı olacak.',
    senaryo: null, toplam: null, dagilim: [] })
  assert.equal(yok.duyuru, 'Duyuru: «Sınav 9. senaryo ağırlıklı olacak.»')
})

test('duyuru satırı yalnız cümle doluysa ve yalnız bu üç durumda çıkar', () => {
  assert.equal(senaryoGorunumu({ ...TABAN, cumle: null }).duyuru, null)
  assert.equal(senaryoGorunumu({ ...TABAN, cumle: '' }).duyuru, null)
  assert.equal(senaryoGorunumu({ ...TABAN, cumle: '   ' }).duyuru, null)
  const bos = { anilan: [], senaryo: null, toplam: null, dagilim: [] }
  assert.equal(senaryoGorunumu({ ...TABAN, ...bos, durum: 'belirtilmedi', cumle: null }).duyuru, null)
  assert.equal(senaryoGorunumu({ ...TABAN, ...bos, durum: 'ulke_geneli', cumle: 'Sınav 3. senaryo olacak.' }).duyuru, null)
})
