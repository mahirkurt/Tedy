import assert from 'node:assert/strict'
import { test } from 'node:test'
import {
  kartDurumu, tahminMetni, bulunmaHali, sonParcaMi, isSayisi, planCoz, planHataCumlesi,
  odevTahminDk, yarinaKaldiMetni, plandaOlmayanMetni, sigmayanMetni, blokSatiri,
  type PlanBlogu, type PlanYaniti,
} from '../src/utils/aksamPlani.ts'

// Spec 2026-10-19 §6.7: the evening plan card on Bugün. These pin what the card
// says in each state, from the shape /api/plan/bugun serves (Task 5).

const dk = (s: string) => { const [h, m] = s.split(':').map(Number); return h * 60 + m }

function blok(id: string, bas: string, bit: string, ek: Partial<PlanBlogu> = {}): PlanBlogu {
  return {
    id, tur: 'calisma', bas: dk(bas), bit: dk(bit), bas_saat: bas, bit_saat: bit,
    odev_anahtari: `odev-${id}`, ders: 'Fen Bilimleri', baslik: 'Kuvvet çalışma kâğıdı',
    adim: 'İlk 2 soruyu çöz', parca: 0, parca_sayisi: 1, tahmin_dk: dk(bit) - dk(bas), zorluk: 'orta',
    durum: 'bekliyor', ham_dk: 16, ...ek,
  }
}
const mola = (id: string, bas: string, bit: string): PlanBlogu =>
  blok(id, bas, bit, { tur: 'mola', odev_anahtari: null, ders: null, baslik: 'Mola', adim: '', tahmin_dk: 0, ham_dk: 0 })

function plan(durum: PlanYaniti['durum'], bloklar: PlanBlogu[], ek: Partial<PlanYaniti> = {}): PlanYaniti {
  const calisma = bloklar.filter(b => b.tur === 'calisma')
  return {
    gun: '2026-09-24', durum, bloklar,
    simdiki: calisma.find(b => b.durum === 'suruyor') ?? null,
    siradaki: calisma.find(b => b.durum === 'bekliyor' || b.durum === 'ertelendi') ?? null,
    tasinan: [], sigmayan: [], planda_olmayan: 0, haber_metni: null, ...ek,
  }
}

const UC_IS = [
  blok('a', '17:00', '17:25', { ders: 'Matematik', baslik: 'Hafta içi ödevi', adim: 'Sayfa 165, ilk 4 soru' }),
  mola('m1', '17:25', '17:30'),
  blok('b', '17:30', '17:50', { odev_anahtari: 'odev-b' }),
  blok('c', '17:55', '18:15', { odev_anahtari: 'odev-c', ders: 'Türkçe', baslik: 'Okuma günlüğü' }),
]

test('önizleme: "Bu akşam 3 iş · 17:00\'de başlıyor" ve ilk işin adı', () => {
  const k = kartDurumu(plan('onizleme', UC_IS), dk('16:30'))
  assert.equal(k.tur, 'onizleme')
  assert.equal(k.baslik, "Bu akşam 3 iş · 17:00'de başlıyor")
  assert.equal(k.alt, 'İlk iş: Matematik — Hafta içi ödevi')
})

test('önizleme: iş, ödev sayısıdır, parça sayısı değil', () => {
  const parcali = [
    blok('a0', '17:00', '17:20', { odev_anahtari: 'x', parca: 0, parca_sayisi: 2 }),
    blok('a1', '17:25', '17:45', { odev_anahtari: 'x', parca: 1, parca_sayisi: 2 }),
  ]
  assert.equal(isSayisi(plan('onizleme', parcali)), 1)
  assert.equal(kartDurumu(plan('onizleme', parcali), dk('16:00')).baslik, "Bu akşam 1 iş · 17:00'de başlıyor")
})

test('önizleme planda iş yoksa kart yok', () => {
  assert.equal(kartDurumu(plan('onizleme', []), dk('16:00')).tur, 'yok')
})

test('süren blok: kalanDk tahmini bitişe göre, başlık şimdiki adım', () => {
  const bloklar = [blok('a', '17:05', '17:30', { durum: 'suruyor' }), ...UC_IS.slice(2)]
  const k = kartDurumu(plan('akis', bloklar), dk('17:18'))
  assert.equal(k.tur, 'calisma')
  assert.equal(k.kalanDk, 12)
  assert.equal(k.baslik, 'İlk 2 soruyu çöz')
  assert.equal(k.blok?.id, 'a')
  assert.match(k.ust, /^Sürüyor · tahminen 12 dk kaldı$/)
  assert.equal(k.alt, 'Sırada: Fen Bilimleri · İlk 2 soruyu çöz')
})

test('süren blok tahmini aşınca kalan sıfır ve sakin bir soru', () => {
  const k = kartDurumu(plan('akis', [blok('a', '17:05', '17:30', { durum: 'suruyor' })]), dk('17:50'))
  assert.equal(k.kalanDk, 0)
  assert.equal(k.ust, 'Tahmin doldu · bitti mi?')
})

test('süren blok her durumda kartı alır (anlık görüntüden gelen blok da)', () => {
  // The running block's homework may already have left the list: it still comes
  // back as `simdiki`, and the card must offer "Bitti" for it (ruling).
  const p = plan('onizleme', [blok('eski', '16:40', '17:00', { durum: 'suruyor' })])
  const k = kartDurumu(p, dk('16:50'))
  assert.equal(k.tur, 'calisma')
  assert.equal(k.blok?.id, 'eski')
})

test('mola: "Mola · 5 dk", kalan dakika ve sıradaki adım', () => {
  const bloklar = [
    blok('a', '17:00', '17:22', { durum: 'bitti' }),
    mola('m1', '17:22', '17:27'),
    blok('b', '17:27', '17:47', { ders: 'Türkçe', adim: 'Bir sayfa oku' }),
  ]
  const k = kartDurumu(plan('akis', bloklar), dk('17:24'))
  assert.equal(k.tur, 'mola')
  assert.equal(k.baslik, 'Mola · 5 dk')
  assert.equal(k.kalanDk, 3)
  assert.equal(k.alt, 'Sırada: Türkçe · Bir sayfa oku')
})

test('mola bitince "bekliyor": başlık sıradaki adım', () => {
  const bloklar = [
    blok('a', '17:00', '17:22', { durum: 'bitti' }),
    mola('m1', '17:22', '17:27'),
    blok('b', '17:27', '17:47', { ders: 'Türkçe', adim: 'Bir sayfa oku' }),
    blok('c', '17:52', '18:10', { odev_anahtari: 'odev-c', adim: 'Tabloyu doldur' }),
  ]
  const k = kartDurumu(plan('akis', bloklar), dk('17:28'))
  assert.equal(k.tur, 'bekliyor')
  assert.equal(k.baslik, 'Bir sayfa oku')
  assert.equal(k.blok?.id, 'b')
  assert.equal(k.alt, 'Sırada: Fen Bilimleri · Tabloyu doldur')
})

test('akış başında (17:05) sıradaki blok "bekliyor"', () => {
  const k = kartDurumu(plan('akis', UC_IS), dk('17:05'))
  assert.equal(k.tur, 'bekliyor')
  assert.equal(k.baslik, 'Sayfa 165, ilk 4 soru')
  assert.equal(k.ust, 'Şimdi')
})

test('ertelenen blok sıradaki olabilir; kart onu taşır', () => {
  const k = kartDurumu(plan('akis', [blok('b', '18:00', '18:20', { durum: 'ertelendi' })]), dk('17:40'))
  assert.equal(k.tur, 'bekliyor')
  assert.equal(k.blok?.durum, 'ertelendi')
  // A block whose forecast start is still ahead says so, as a forecast.
  assert.equal(k.ust, 'Planda 18:00')
})

test('durum "bitti" → "Bugünlük bu kadar"', () => {
  assert.equal(kartDurumu(plan('bitti', []), dk('20:40')).baslik, 'Bugünlük bu kadar')
  assert.equal(kartDurumu(plan('bitti', []), dk('20:40')).tur, 'bitti')
})

test('akışta bütün bloklar bittiyse de "Bugünlük bu kadar"', () => {
  const k = kartDurumu(plan('akis', [blok('a', '17:00', '17:20', { durum: 'bitti' })]), dk('18:00'))
  assert.equal(k.tur, 'bitti')
  assert.equal(k.baslik, 'Bugünlük bu kadar')
})

test('kapalı, plansız ve okulsuz', () => {
  assert.equal(kartDurumu(plan('kapali', []), dk('17:10')).tur, 'kapali')
  assert.equal(kartDurumu(plan('plansiz', []), dk('17:10')).tur, 'yok')
  assert.equal(kartDurumu(plan('okulsuz', []), dk('17:10')).tur, 'yok')
})

test('süre metni her zaman "tahmin N dk" biçiminde', () => {
  assert.equal(tahminMetni(20), 'tahmin 20 dk')
  assert.equal(tahminMetni(7), 'tahmin 7 dk')
  // Every work duration the card composes carries the word "tahmin"; only the
  // break states its own length ("Mola · 5 dk") and what is left of it.
  const durumlar = [
    kartDurumu(plan('akis', [blok('a', '17:05', '17:30', { durum: 'suruyor' })]), dk('17:10')),
    kartDurumu(plan('akis', UC_IS), dk('17:05')),
    kartDurumu(plan('onizleme', UC_IS), dk('16:00')),
    kartDurumu(plan('bitti', []), dk('20:40')),
  ]
  for (const k of durumlar) {
    for (const metin of [k.ust, k.baslik, k.alt]) {
      for (const m of metin.matchAll(/\d+ dk/g)) {
        assert.match(metin.slice(0, m.index), /tahmin\w*\s*$/, `"${metin}" süreyi tahmin demeden söylüyor`)
      }
    }
  }
})

test('kopyada alarm dili yok', () => {
  const yasak = /geç kaldın|yetiştiremeyeceksin|acele|hemen|uyarı/i
  const metinler: string[] = []
  const ekle = (k: ReturnType<typeof kartDurumu>) => metinler.push(k.ust, k.baslik, k.alt)
  ekle(kartDurumu(plan('akis', [blok('a', '17:05', '17:30', { durum: 'suruyor' })]), dk('19:59')))
  ekle(kartDurumu(plan('akis', UC_IS), dk('17:05')))
  ekle(kartDurumu(plan('onizleme', UC_IS), dk('16:00')))
  ekle(kartDurumu(plan('bitti', []), dk('20:40')))
  ekle(kartDurumu(plan('kapali', []), dk('17:00')))
  metinler.push(
    yarinaKaldiMetni([{ odev_anahtari: 'x', ders: 'Fen Bilimleri', baslik: 'Proje', teslim: '30.09.2026', kalan_dk: 40 }]),
    sigmayanMetni([{ odev_anahtari: 'y', ders: 'Türkçe', baslik: 'Okuma', teslim: '25.09.2026', kalan_dk: 20 }]),
    plandaOlmayanMetni(2),
  )
  for (const m of metinler) assert.doesNotMatch(m, yasak, m)
})

test('bulunma hâli saatin okunuşuna göre', () => {
  assert.equal(bulunmaHali('17:00'), "17:00'de")
  assert.equal(bulunmaHali('17:15'), "17:15'te")
  assert.equal(bulunmaHali('17:30'), "17:30'da")
  assert.equal(bulunmaHali('17:40'), "17:40'ta")
  assert.equal(bulunmaHali('19:00'), "19:00'da")
  assert.equal(bulunmaHali('18:00'), "18:00'de")
  assert.equal(bulunmaHali('14:00'), "14:00'te")
  assert.equal(bulunmaHali('16:50'), "16:50'de")
  assert.equal(bulunmaHali('16:06'), "16:06'da")
})

test('son parça: yalnız normal son parça', () => {
  assert.equal(sonParcaMi(blok('a', '17:00', '17:20', { parca: 0, parca_sayisi: 1 })), true)
  assert.equal(sonParcaMi(blok('a', '17:00', '17:20', { parca: 0, parca_sayisi: 2 })), false)
  assert.equal(sonParcaMi(blok('a', '17:00', '17:20', { parca: 1, parca_sayisi: 2 })), true)
})

test('ödevin tahmini: normal parçaların ham payı, 5–120 arasına', () => {
  const p = plan('akis', [
    blok('a0', '17:00', '17:20', { odev_anahtari: 'x', ham_dk: 16 }),
    blok('a1', '17:25', '17:45', { odev_anahtari: 'x', ham_dk: 14.4 }),
    blok('a2', '17:50', '18:00', { odev_anahtari: 'x', ham_dk: 0, tahmin_dk: 10 }),
    blok('b', '18:05', '18:25', { odev_anahtari: 'y', ham_dk: 2, tahmin_dk: 3 }),
  ])
  assert.equal(odevTahminDk(p, 'x'), 30)
  assert.equal(odevTahminDk(p, 'y'), 5)
  assert.equal(odevTahminDk(p, 'yok'), 20)
})

test('tek satırlar', () => {
  assert.equal(yarinaKaldiMetni([
    { odev_anahtari: 'x', ders: 'Fen Bilimleri', baslik: 'Proje', teslim: '30.09.2026', kalan_dk: 40 },
    { odev_anahtari: 'y', ders: null, baslik: 'Okuma', teslim: '', kalan_dk: 10 },
  ]), 'Yarına kaldı: Fen Bilimleri — Proje · Okuma')
  assert.equal(sigmayanMetni([{ odev_anahtari: 'y', ders: 'Türkçe', baslik: 'Okuma', teslim: '', kalan_dk: 20 }]),
    'Bu akşama sığmıyor: Türkçe — Okuma')
  assert.equal(plandaOlmayanMetni(2), "Planda olmayan 2 eski ödev · İşler'de")
  assert.equal(plandaOlmayanMetni(1), "Planda olmayan 1 eski ödev · İşler'de")
})

test('planın tamamındaki satır', () => {
  assert.deepEqual(blokSatiri(blok('a', '17:00', '17:25')),
    { saat: '17:00–17:25', ad: 'Fen Bilimleri · İlk 2 soruyu çöz', sure: 'tahmin 25 dk', durum: '' })
  assert.deepEqual(blokSatiri(blok('a', '17:00', '17:25', { durum: 'bitti' })).durum, 'Bitti')
  assert.deepEqual(blokSatiri(mola('m', '17:25', '17:30')),
    { saat: '17:25–17:30', ad: 'Mola', sure: '', durum: '' })
  assert.equal(blokSatiri(blok('y', '18:30', '19:00', { tur: 'yemek', baslik: 'Yemek' })).ad, 'Yemek')
})

test('planCoz yanlış şekli reddeder, doğru şekli geçirir', () => {
  assert.equal(planCoz(null), null)
  assert.equal(planCoz({ kapali: true }), null)
  assert.equal(planCoz({ durum: 'akis', bloklar: 'x' }), null)
  const p = plan('akis', UC_IS)
  assert.deepEqual(planCoz(JSON.parse(JSON.stringify(p))), p)
  // Missing optional lists read as empty; a missing haber_metni as null.
  const eksik = planCoz({ gun: '2026-09-24', durum: 'plansiz', bloklar: [] })
  assert.deepEqual(eksik?.tasinan, [])
  assert.equal(eksik?.haber_metni, null)
  assert.equal(eksik?.simdiki, null)
})

test('hata cümlesi: sunucunun cümlesi, yoksa sakin bir genel cümle; ham HTTP asla', () => {
  assert.deepEqual(planHataCumlesi(409, { error: 'Önce süren bloğu bitir.' }),
    { tur: 'uyari', baslik: 'Önce süren bloğu bitir.' })
  assert.deepEqual(planHataCumlesi(403, { error: 'Bunu yalnız aile değiştirebilir.' }),
    { tur: 'uyari', baslik: 'Bunu yalnız aile değiştirebilir.' })
  for (const [durum, govde] of [[500, { error: 'Traceback' }], [502, null], [null, null], [404, '<html>']] as const) {
    const c = planHataCumlesi(durum, govde)
    assert.equal(c.tur, 'hata')
    assert.equal(c.baslik, 'Kaydedilemedi')
    assert.doesNotMatch(`${c.baslik} ${c.alt ?? ''}`, /HTTP|\d{3}|Traceback|html/)
  }
})
