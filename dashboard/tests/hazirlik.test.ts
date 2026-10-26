import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  baskiAdresi, baskiModelAdresi, baslikMetni, indirmeAdi, ciktiKimligi, dersAnahtari, durumEtiketi, kilavuzGirisi, ebeveynCumleleri, kalanGunMetni, kilavuzAdresi,
  enYakinYazili, kisaAmac, kitapYoluMetni, pdfAdresi, sayfaMetni, sayisalTarih, secenekleriOku, secenekleriYaz, soruMetni, tarihMetni, BASLIK_TURU,
  yaklasanAyrinti,
} from '../src/hazirlik/hazirlik.ts'
import type { KilavuzModeli, SinavDurumu } from '../src/hazirlik/tipler.ts'

const DURUM: SinavDurumu = {
  tur: 'kesin', senaryo: 2, senaryo_sayisi: 4, tarih: '2026-11-03', kalan_gun: 9, sinav_id: 'fen11',
  duyuru: 'Sınav 2. senaryoya göre uygulanacaktır.', uyari: null, anilan: [2], duyurulan_konu: 3,
}

test('durumEtiketi: dört durum; olası tek senaryo adı taşımaz (K8)', () => {
  assert.equal(durumEtiketi(DURUM), 'Kesin: 2. senaryo')
  const olasi = durumEtiketi({ ...DURUM, tur: 'olasi', senaryo: null })
  assert.equal(olasi, 'Olası: 4 senaryo')
  assert.doesNotMatch(olasi, /\d\. senaryo/)
  assert.equal(durumEtiketi({ ...DURUM, tur: 'ulke_geneli', senaryo: null, senaryo_sayisi: 0 }), 'Ülke geneli')
  assert.equal(durumEtiketi({ ...DURUM, tur: 'gecti', senaryo: 4 }), 'Geçti · 4. senaryoydu')
  assert.equal(durumEtiketi({ ...DURUM, tur: 'gecti', senaryo: null }), 'Geçti')
})

test('tarih, geri sayım ve yaklaşan satırı', () => {
  assert.equal(tarihMetni('2026-11-03'), '3 Kasım Salı')
  assert.equal(tarihMetni('2026-11-03', false), '3 Kasım')
  assert.equal(tarihMetni(null), 'tarih yok')
  assert.equal(sayisalTarih('2026-09-10T17:27'), '10.09.2026')
  assert.deepEqual([0, 1, 9, null].map(kalanGunMetni), ['bugün', 'yarın', '9 gün', null])
  assert.equal(yaklasanAyrinti(DURUM, 7), '3 Kasım Salı · 7 soru · 3 konu duyuruldu')
  assert.equal(yaklasanAyrinti({ ...DURUM, tur: 'ulke_geneli', tarih: '2027-01-05', duyurulan_konu: 0 }, null),
    '5 Ocak Salı · ülke geneli ortak sınav')
})

test('soruMetni: kesin tek sayı, olası aralık (K8)', () => {
  assert.equal(soruMetni({ soru: 3, aralik: null }), '3 soru')
  assert.equal(soruMetni({ soru: 0, aralik: null }), '0 soru')
  assert.equal(soruMetni({ soru: null, aralik: [0, 2] }), 'senaryoya göre 0–2 soru')
  assert.equal(soruMetni({ soru: null, aralik: [1, 1] }), 'her senaryoda 1 soru')
  // Olası kipte okurun seçtiği senaryo: tek sayı o senaryoyla nitelenir (K8, düzeltme 2).
  assert.equal(soruMetni({ soru: 2, aralik: null }, 3), '3. senaryoda 2 soru')
  assert.equal(soruMetni({ soru: null, aralik: [0, 2] }, 3), 'senaryoya göre 0–2 soru')
  assert.equal(BASLIK_TURU.diger, 'Alt başlık')
})

test('kitap yolu, sayfa, amaç ve başlık metni (K1, K6)', () => {
  const yol = { kitap: 'Fen Bilimleri 7 (1. Kitap)', unite: '2. Ünite', unite_no: 2, unite_ad: 'Kuvvet ve Enerjiyi Keşfedelim',
    cerceve: '1. Kuvvet, İş ve Enerji İlişkisi', cerceve_no: 1, konu: 'Fiziksel Anlamda İş', sayfa: 60, son_sayfa: 63, baglanti: 'x#page=61' }
  assert.equal(kitapYoluMetni(yol), 'Fen Bilimleri 7 (1. Kitap) › 2. Ünite › 1. Kuvvet, İş ve Enerji İlişkisi › Fiziksel Anlamda İş')
  assert.equal(kitapYoluMetni({ ...yol, konu: null }), 'Fen Bilimleri 7 (1. Kitap) › 2. Ünite › 1. Kuvvet, İş ve Enerji İlişkisi')
  assert.equal(sayfaMetni(60, 63), 's. 60–63')
  assert.equal(sayfaMetni(62, 62), 's. 62')
  const uzun = 'Fiziksel anlamda iş yapma durumuna göre günlük yaşam örneklerini değerlendirme ve tartışma'
  assert.equal(kisaAmac(uzun), 'Fiziksel anlamda iş yapma durumuna göre günlük yaşam örneklerini…')
  assert.equal(baslikMetni({ ad: 'Etkinlik Noktası-1', tur: 'etkinlik', amac: 'İşi tanımlama', sayfa: 60 }), 'Etkinlik Noktası-1 — İşi tanımlama')
  assert.equal(baslikMetni({ ad: 'Kontrol Noktası', tur: 'kontrol', amac: null, sayfa: 63 }), 'Kontrol Noktası')
  assert.equal(ciktiKimligi('FB.7.2.1'), 'cikti-FB-7-2-1')
})

test('adresler', () => {
  const s = { ebeveyn: true, isaret: false }
  assert.equal(kilavuzAdresi('fen-bilimleri', 1, 2), '/hazirlik/fen-bilimleri/1?senaryo=2')
  assert.equal(kilavuzAdresi('fen-bilimleri', 1, null), '/hazirlik/fen-bilimleri/1')
  assert.equal(pdfAdresi('fen-bilimleri', 1, 2, s), '/api/hazirlik/fen-bilimleri/1/kilavuz.pdf?senaryo=2&ebeveyn=1&isaret=0')
  assert.equal(baskiAdresi('fen-bilimleri', 1, null, s), '/baski.html?ebeveyn=1&isaret=0&ders=fen-bilimleri&sinav=1')
  assert.equal(dersAnahtari('Fen Bilimleri'), 'fen-bilimleri')
  assert.equal(dersAnahtari('Beden Eğitimi'), null)
  assert.equal(dersAnahtari(undefined), null)
})

test('baskı görünümü modeli PDF ile aynı işaretlerle (öğrencinin) ister; A4 önizleme adresi parametresiz', () => {
  const s = { ebeveyn: false, isaret: true }
  assert.equal(baskiModelAdresi('fen-bilimleri', 1, 2, s),
    '/api/hazirlik/fen-bilimleri/1/kilavuz?senaryo=2&ebeveyn=0&isaret=1&isaret_kaynagi=ogrenci')
  assert.ok(!baskiAdresi('fen-bilimleri', 1, 2, s).includes('isaret_kaynagi'))
})

test('indirmeAdi: önce filename* (RFC 5987), sonra filename; yol taşıyan ad ya da başlıksız yanıt genel ad', () => {
  assert.equal(indirmeAdi("attachment; filename=kapsam-kilavuzu-fen-bilimleri-1-s2.pdf; filename*=UTF-8''kapsam-kilavuzu-fen-bilimleri-1-s2.pdf"),
    'kapsam-kilavuzu-fen-bilimleri-1-s2.pdf')
  assert.equal(indirmeAdi("attachment; filename=ascii.pdf; filename*=UTF-8''kapsam-k%C4%B1lavuzu.pdf"), 'kapsam-kılavuzu.pdf')
  assert.equal(indirmeAdi('attachment; filename="kapsam-kilavuzu-fen-bilimleri-1-olasi.pdf"'), 'kapsam-kilavuzu-fen-bilimleri-1-olasi.pdf')
  assert.equal(indirmeAdi('attachment; filename=../../etc/passwd'), 'kapsam-kilavuzu.pdf')
  assert.equal(indirmeAdi(null), 'kapsam-kilavuzu.pdf')
})

test('dersAnahtari sunucudaki altı tablo adını ve Dersler sekmelerinin adlarını tanır', () => {
  const tablo: [string, string][] = [['Türkçe', 'turkce'], ['Matematik', 'matematik'], ['Fen Bilimleri', 'fen-bilimleri'],
    ['Sosyal Bilgiler', 'sosyal-bilgiler'], ['İngilizce', 'ingilizce'], ['Din Kültürü', 'din-kulturu']]
  for (const [ad, anahtar] of tablo) assert.equal(dersAnahtari(ad), anahtar, ad)
  // Dersler sekmelerinde görünen adlar (COURSE_CONTENT_ORDER): Din Kültürü "Din Kültürü ve Ahlak" diye gelir.
  const sekmeler: [string, string | null][] = [['Matematik', 'matematik'], ['Fen Bilimleri', 'fen-bilimleri'],
    ['Sosyal Bilgiler', 'sosyal-bilgiler'], ['Türkçe', 'turkce'], ['İngilizce', 'ingilizce'],
    ['Din Kültürü ve Ahlak', 'din-kulturu'], ['Din Kültürü ve Ahlak Bilgisi', 'din-kulturu'], ['Fransızca', null], ['Genel', null]]
  for (const [ad, anahtar] of sekmeler) assert.equal(dersAnahtari(ad), anahtar, ad)
})

test('PDF seçenekleri kişi başına hatırlanır; bozuk kayıt varsayılana düşer', () => {
  const depo = new Map<string, string>()
  const d = { getItem: (k: string) => depo.get(k) ?? null, setItem: (k: string, v: string) => { depo.set(k, v) } }
  assert.deepEqual(secenekleriOku('A@x.com', d), { ebeveyn: false, isaret: true })
  secenekleriYaz('A@x.com', { ebeveyn: true, isaret: false }, d)
  assert.deepEqual(secenekleriOku('a@x.com', d), { ebeveyn: true, isaret: false })
  assert.deepEqual(secenekleriOku('b@x.com', d), { ebeveyn: false, isaret: true })
  depo.set('tedy-hazirlik-pdf::c@x.com', '{bozuk')
  assert.deepEqual(secenekleriOku('c@x.com', d), { ebeveyn: false, isaret: true })
})

test('ebeveyn cümleleri', () => {
  const m = { ders: 'Fen Bilimleri', sinav_no: 1, durum: DURUM, kip: 'kesin', senaryo: 2,
    ebeveyn: { cikti_sayisi: 4, toplam_soru: 7, soru_araligi: null, hazirim: 1, tekrar: 1, isaretsiz: 2, en_agir: [] } } as unknown as KilavuzModeli
  assert.deepEqual(ebeveynCumleleri(m), ['Fen Bilimleri 1. yazılı: 3 Kasım Salı, 9 gün kaldı.', 'Okul 2. senaryoyu duyurdu.',
    '4 öğrenme çıktısı, toplam 7 soru.', 'Hazırlık işaretleri: 1 hazır, 1 tekrar, 2 işaretsiz.'])
  const olasi = { ...m, kip: 'olasi', senaryo: null, durum: { ...DURUM, tarih: null, kalan_gun: null },
    ebeveyn: { ...m.ebeveyn!, toplam_soru: null, soru_araligi: [6, 9] } } as KilavuzModeli
  assert.deepEqual(ebeveynCumleleri(olasi).slice(0, 3), ['Fen Bilimleri 1. yazılı: tarihi henüz belli değil.',
    'Senaryo henüz duyurulmadı; kılavuz bütün senaryoları kapsar.', '4 öğrenme çıktısı; senaryoya göre 6–9 soru.'])
  // Okurun seçtiği (duyurulmamış) senaryo: toplam o senaryoyla nitelenir, "bütün senaryolar" denmez (K8, düzeltme 2).
  const secilen = { ...m, kip: 'olasi', senaryo: 3, ebeveyn: { ...m.ebeveyn!, toplam_soru: 8 } } as KilavuzModeli
  assert.deepEqual(ebeveynCumleleri(secilen).slice(1, 3), ['Senaryo henüz duyurulmadı; kılavuz seçilen 3. senaryoya göre.',
    '4 öğrenme çıktısı; 3. senaryoda toplam 8 soru.'])
  assert.deepEqual(ebeveynCumleleri({ ...m, ebeveyn: null }), [])
})

test('enYakinYazili: ilk geçmemiş yazılı; hepsi geçtiyse sonuncusu (spec §3.1)', () => {
  const y = (no: number, tur: SinavDurumu['tur'], tarih: string | null) => ({ sinav_no: no, durum: { ...DURUM, tur, tarih } })
  const [a, b] = [y(1, 'gecti', '2026-10-22'), y(2, 'ulke_geneli', '2027-01-05')]
  assert.equal(enYakinYazili([a, b])?.sinav_no, 2, 'geçmiş + gelecek: gelecek olan')
  const [c, d] = [y(1, 'kesin', '2026-11-03'), y(2, 'olasi', '2027-01-05')]
  assert.equal(enYakinYazili([c, d])?.sinav_no, 1, 'ikisi de gelecek: ilki')
  const [e, f] = [y(1, 'gecti', '2026-10-22'), y(2, 'gecti', '2027-01-05')]
  assert.equal(enYakinYazili([e, f])?.sinav_no, 2, 'ikisi de geçmiş: sonuncusu')
  const [g, h] = [y(1, 'olasi', null), y(2, 'olasi', null)]
  assert.equal(enYakinYazili([g, h])?.sinav_no, 1, 'tarihsiz: geçmemiş sayılır, ilki')
  assert.equal(enYakinYazili([y(1, 'gecti', '2026-10-22'), y(2, 'olasi', null)])?.sinav_no, 2, 'geçmiş + tarihsiz: tarihsiz')
  assert.equal(enYakinYazili([]), null)
})

test('kilavuzGirisi: kesin senaryo adlanır; olası ve tabloda olmayan senaryo adrese ve etikete girmez; ülke geneli ders sayfası', () => {
  const blok = (durum: string, senaryo: number | null, ders = 'Fen Bilimleri', sinav_no = 1) =>
    ({ durum, ders, sinav_no, senaryo }) as Parameters<typeof kilavuzGirisi>[0]
  assert.deepEqual(kilavuzGirisi(blok('dogrulandi', 2)), { href: '/hazirlik/fen-bilimleri/1?senaryo=2', etiket: 'Kapsam kılavuzunu aç (2. senaryo)' })
  assert.deepEqual(kilavuzGirisi(blok('kismen', 4)), { href: '/hazirlik/fen-bilimleri/1?senaryo=4', etiket: 'Kapsam kılavuzunu aç (4. senaryo)' })
  assert.deepEqual(kilavuzGirisi(blok('belirtilmedi', null)), { href: '/hazirlik/fen-bilimleri/1', etiket: 'Kapsam kılavuzunu aç' })
  assert.deepEqual(kilavuzGirisi(blok('senaryo_yok', null, 'Türkçe', 2)), { href: '/hazirlik/turkce/2', etiket: 'Kapsam kılavuzunu aç' })
  assert.deepEqual(kilavuzGirisi(blok('ulke_geneli', null, 'Türkçe', 2)), { href: '/hazirlik/turkce?sinav=2', etiket: 'MEB senaryolarını aç' })
  assert.equal(kilavuzGirisi(blok('dogrulandi', 1, 'Beden Eğitimi')), null)
})
