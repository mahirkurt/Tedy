import { test } from 'node:test'
import assert from 'node:assert/strict'
import { anahtarBaytlari, bildirimDurumu, cihazAdi, DURUM_METNI, GENEL_HATA_METNI, hataMetni, IZIN_VERILMEDI_METNI } from '../src/utils/bildirim.ts'
import type { BildirimOrtami } from '../src/utils/bildirim.ts'

const TAM: BildirimOrtami = { destek: true, izin: 'granted', abone: true, ios: false, ekranda: false }

test('açık: izin verilmiş ve abone', () => {
  assert.equal(bildirimDurumu(TAM), 'acik')
})

test('kapalı: izin var ama abonelik yok ya da izin sorulmamış', () => {
  assert.equal(bildirimDurumu({ ...TAM, abone: false }), 'kapali')
  assert.equal(bildirimDurumu({ ...TAM, izin: 'default', abone: false }), 'kapali')
})

test('reddedildi', () => {
  assert.equal(bildirimDurumu({ ...TAM, izin: 'denied', abone: false }), 'reddedildi')
})

test('desteklenmiyor', () => {
  assert.equal(bildirimDurumu({ ...TAM, destek: false }), 'desteklenmiyor')
})

test('iPhone ana ekrana eklenmemiş: destek olmasa da önce bu söylenir', () => {
  assert.equal(bildirimDurumu({ ...TAM, destek: false, ios: true, ekranda: false }), 'ios-ana-ekran')
  assert.equal(bildirimDurumu({ ...TAM, ios: true, ekranda: true }), 'acik')
})

test('her durumun metni var ve renk değil sözcük taşır', () => {
  for (const d of ['acik', 'acik-bekliyor', 'kapali', 'reddedildi', 'desteklenmiyor', 'ios-ana-ekran'] as const) {
    assert.ok(DURUM_METNI[d].length > 10)
  }
  assert.match(DURUM_METNI['ios-ana-ekran'], /Ana Ekrana Ekle/)
  assert.match(DURUM_METNI.reddedildi, /tarayıcı ayarlarından/i)
})

test('anahtar baytları: base64url → 65 bayt', () => {
  const b64 = Buffer.from(Uint8Array.from([4, ...Array(64).fill(7)])).toString('base64url')
  const sonuc = anahtarBaytlari(b64)
  assert.equal(sonuc.length, 65)
  assert.equal(sonuc[0], 4)
  assert.equal(sonuc[64], 7)
})

test('cihaz adı kullanıcı aracısından', () => {
  assert.equal(cihazAdi('Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X)'), 'iPhone')
  assert.equal(cihazAdi('Mozilla/5.0 (Linux; Android 14; Pixel 8)'), 'Android')
  assert.equal(cihazAdi('Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4)'), 'Mac')
  assert.equal(cihazAdi('Mozilla/5.0 (Windows NT 10.0; Win64; x64)'), 'Windows')
  assert.equal(cihazAdi('curl/8'), 'Tarayıcı')
})

test('abone ama sunucu uyarı bayrağı kapalı: açık, uyarılar başlatılmadı', () => {
  assert.equal(bildirimDurumu({ ...TAM, sunucuAcik: false }), 'acik-bekliyor')
  assert.equal(DURUM_METNI['acik-bekliyor'], 'Bu cihazda açık; sınav uyarıları henüz başlatılmadı.')
})

test('sunucu bayrağı açık ya da bilinmiyorsa durum açık kalır', () => {
  assert.equal(bildirimDurumu({ ...TAM, sunucuAcik: true }), 'acik')
  assert.equal(bildirimDurumu({ ...TAM, sunucuAcik: undefined }), 'acik')
})

test('sunucu bayrağı kapalıyken abone olmayan cihaz yine kapalı; iOS ve izin önceliği bozulmaz', () => {
  assert.equal(bildirimDurumu({ ...TAM, abone: false, sunucuAcik: false }), 'kapali')
  assert.equal(bildirimDurumu({ ...TAM, izin: 'denied', abone: false, sunucuAcik: false }), 'reddedildi')
  assert.equal(bildirimDurumu({ ...TAM, ios: true, ekranda: false, sunucuAcik: false }), 'ios-ana-ekran')
})

test('hata metni: kapatılan izin penceresi genel hata sayılmaz', () => {
  assert.equal(hataMetni('kapali'), IZIN_VERILMEDI_METNI)
  assert.equal(IZIN_VERILMEDI_METNI, 'İzin verilmedi; bildirimler kapalı kaldı.')
  assert.equal(hataMetni('reddedildi'), DURUM_METNI.reddedildi)
  assert.equal(hataMetni('sunucu'), GENEL_HATA_METNI)
  assert.equal(hataMetni(''), GENEL_HATA_METNI)
})
