import assert from 'node:assert/strict'
import { test } from 'node:test'
import {
  windowVoice, okulGunuMu, yerSec, simdiUstu, bitenOzeti, sonrakiOkulGunu, yarinBasligi,
  rakamParcala, VARSAYILAN_DUZEN, duzenCoz, duzenGovdesi, duzenHatasi,
  type AgendaSlot, type AgendaType,
} from '../src/utils/bugun.ts'

const dk = (s: string) => { const [h, m] = s.split(':').map(Number); return h * 60 + m }
const oge = (type: AgendaType, bas: string, bit: string, simdi: string): AgendaSlot => ({
  type, startMin: dk(bas), endMin: dk(bit),
  isActive: dk(simdi) >= dk(bas) && dk(simdi) < dk(bit),
  isPast: dk(simdi) >= dk(bit),
})

test('okul günü: ödeve hazır saatinden önce iş "Okuldan sonra", o saate çapalı', () => {
  assert.deepEqual(windowVoice(dk('10:30'), 'work', true), {
    eyebrow: 'Okuldan sonra', hint: 'Bunu okuldan sonra yapmak daha kolay', anchorMin: VARSAYILAN_DUZEN.odeveHazir,
  })
  assert.equal(windowVoice(dk('15:50'), 'work', true).eyebrow, 'Okuldan sonra')
  assert.equal(windowVoice(dk('17:10'), 'work', true).eyebrow, 'Şimdi')
  assert.equal(windowVoice(dk('19:30'), 'work', true).eyebrow, 'Bu akşam')
  assert.equal(windowVoice(dk('23:00'), 'work', true).eyebrow, 'Yarın')
  assert.equal(windowVoice(dk('03:15'), 'work', true).eyebrow, 'Okuldan sonra')
})

test('okul günü: okuma önizlemesi okuldan önce "Bugün", ders sırasında "Okuldan sonra"', () => {
  assert.equal(windowVoice(dk('07:00'), 'reading', true).eyebrow, 'Bugün')
  assert.equal(windowVoice(dk('11:00'), 'reading', true).eyebrow, 'Okuldan sonra')
  assert.equal(windowVoice(dk('20:30'), 'reading', true).eyebrow, 'Bu akşam')
})

test('okul olmayan gün "Okuldan sonra" demez ve şeride çapa koymaz', () => {
  for (const kind of ['work', 'reading'] as const) {
    for (const saat of ['07:00', '10:00', '13:00', '15:50', '19:30', '23:00']) {
      const ses = windowVoice(dk(saat), kind, false)
      assert.ok(!/okul/i.test(ses.eyebrow + (ses.hint ?? '')), `${kind} ${saat}: ${ses.eyebrow}`)
      assert.equal(ses.anchorMin, undefined)
    }
    assert.equal(windowVoice(dk('10:00'), kind, false).eyebrow, 'Şimdi')
    assert.equal(windowVoice(dk('19:30'), kind, false).eyebrow, 'Bu akşam')
    assert.equal(windowVoice(dk('23:00'), kind, false).eyebrow, 'Yarın')
    assert.equal(windowVoice(dk('06:30'), kind, false).eyebrow, 'Bugün')
  }
})

test('bütün sesler cümle düzeninde (S38)', () => {
  for (const okul of [true, false]) {
    for (const kind of ['work', 'reading'] as const) {
      for (let m = 0; m < 24 * 60; m += 15) {
        const { eyebrow } = windowVoice(m, kind, okul)
        assert.notEqual(eyebrow, eyebrow.toLocaleUpperCase('tr'), eyebrow)
      }
    }
  }
})

test('okul günü programdan okunur; program yoksa hafta içi', () => {
  const cumartesi = new Date(2026, 8, 26)
  const persembe = new Date(2026, 8, 24)
  assert.equal(okulGunuMu(0, persembe, true), false)
  assert.equal(okulGunuMu(7, persembe, true), true)
  assert.equal(okulGunuMu(0, persembe, false), true)
  assert.equal(okulGunuMu(0, cumartesi, false), false)
})

test('uzun bir takvim etkinliği şimdi kartını almaz', () => {
  // A school-day-long event (08:00–15:45) and the lessons inside it.
  const simdi = '10:40'
  const gun = [
    oge('event', '08:00', '15:45', simdi),
    oge('lesson', '08:00', '08:40', simdi),
    oge('lesson', '10:35', '11:15', simdi),
    oge('lesson', '11:20', '12:00', simdi),
  ]
  const s = yerSec(gun)
  assert.equal(s.simdiki, gun[2])
  assert.equal(s.sonraki, gun[3])
  assert.equal(s.kalanDers, 1)
  assert.equal(s.sonZil, dk('12:00'))
})

test('etkinlik sıradaki yer de olmaz; özel ders ve ÖGEP olur', () => {
  const simdi = '09:00'
  const gun = [
    oge('lesson', '08:55', '09:35', simdi),
    oge('event', '09:40', '10:00', simdi),
    oge('ogep', '10:00', '10:40', simdi),
  ]
  assert.equal(yerSec(gun).sonraki, gun[2])
  const cumartesi = [oge('private_lesson', '12:00', '13:00', '10:00')]
  assert.equal(yerSec(cumartesi).simdiki, cumartesi[0])
  assert.equal(yerSec(cumartesi).dersSayisi, 0)
})

test('kart üst etiketi', () => {
  const simdi = '07:30'
  const ilk = oge('lesson', '08:00', '08:40', simdi)
  assert.equal(simdiUstu(ilk, dk(simdi), true), 'İlk ders · 08:00')
  assert.equal(simdiUstu(oge('lesson', '10:35', '11:15', '10:30'), dk('10:30'), false), 'Sıradaki · 5 dk sonra')
  assert.equal(simdiUstu(oge('lesson', '14:15', '14:55', '12:10'), dk('12:10'), false), 'Sıradaki · 14:15')
  assert.equal(simdiUstu(oge('lesson', '09:45', '10:25', '10:15'), dk('10:15'), false), 'Şu an · 10 dk kaldı')
})

test('katlama özeti', () => {
  const s = '16:40'
  assert.equal(bitenOzeti([
    oge('lesson', '08:00', '08:40', s), oge('lesson', '08:55', '09:35', s),
    oge('event', '12:40', '14:10', s), oge('deadline', '12:00', '12:00', s),
  ]), '2 ders, 1 etkinlik, 1 teslim bitti')
})

test('cuma akşamı sıradaki okul günü pazartesi', () => {
  const cuma = new Date(2026, 8, 25, 17, 0)
  const sonraki = sonrakiOkulGunu(cuma, g => g.getDay() >= 1 && g.getDay() <= 5)
  assert.deepEqual(sonraki && { k: sonraki.k, gun: sonraki.tarih.getDate() }, { k: 3, gun: 28 })
  assert.equal(yarinBasligi(sonraki!.k, sonraki!.tarih), 'Pazartesi')
  assert.equal(yarinBasligi(1, new Date(2026, 8, 25)), 'Yarın · Cuma')
  assert.equal(sonrakiOkulGunu(cuma, () => false), null)
})

test('yalnız rakamlar mono parçaya ayrılır', () => {
  assert.deepEqual(rakamParcala('Sonra: Fen Bilimleri 11:20'), [
    { metin: 'Sonra: Fen Bilimleri ', rakam: false }, { metin: '11:20', rakam: true },
  ])
  assert.deepEqual(rakamParcala('4 ders kaldı'), [
    { metin: '4', rakam: true }, { metin: ' ders kaldı', rakam: false },
  ])
  assert.deepEqual(rakamParcala('Teslim'), [{ metin: 'Teslim', rakam: false }])
})

// B29 (2026-10-11), widened 2026-10-19 (akşam düzeni): the household's evening
// is read from the server (output/), the defaults being the family's own.
test('akşam düzeni sunucudan çözülür; bozuk ya da eksikse varsayılanlar', () => {
  assert.deepEqual(VARSAYILAN_DUZEN, {
    okulBitisi: dk('15:45'), odeveHazir: dk('17:00'), zorIsSonu: dk('19:00'), hafifIsSonu: dk('19:30'),
    yemek: dk('18:30'), yemekDk: 30, hazirlik: dk('20:30'), yatma: dk('21:00'),
    baslamadiEsikDk: 15, takildiEsikDk: 15, haberAlacaklar: [],
  })
  assert.deepEqual(duzenCoz({}), VARSAYILAN_DUZEN)
  const sunucu = {
    odeve_hazir: '16:30', zor_is_sonu: '18:30', hafif_is_sonu: '19:00', yemek: '18:00', yemek_dk: 40,
    hazirlik: '20:00', yatma: '21:30', okul_bitisi: '15:30', baslamadi_esik_dk: 10, takildi_esik_dk: 20,
    haber_alacaklar: ['anne@example.com'], varsayilan: false,
  }
  assert.deepEqual(duzenCoz(sunucu), {
    okulBitisi: dk('15:30'), odeveHazir: dk('16:30'), zorIsSonu: dk('18:30'), hafifIsSonu: dk('19:00'),
    yemek: dk('18:00'), yemekDk: 40, hazirlik: dk('20:00'), yatma: dk('21:30'),
    baslamadiEsikDk: 10, takildiEsikDk: 20, haberAlacaklar: ['anne@example.com'],
  })
  for (const bozuk of [null, 'x', { ...sunucu, odeve_hazir: '25:00' }, { ...sunucu, zor_is_sonu: '16:00' },
    { ...sunucu, yemek_dk: 5 }, { ...sunucu, yatma: undefined }]) {
    assert.deepEqual(duzenCoz(bozuk), VARSAYILAN_DUZEN, JSON.stringify(bozuk))
  }
  // Gövde sunucunun anahtarlarıyla, saatler SS:DD.
  assert.deepEqual(duzenGovdesi(duzenCoz(sunucu)), {
    okul_bitisi: '15:30', odeve_hazir: '16:30', zor_is_sonu: '18:30', hafif_is_sonu: '19:00',
    yemek: '18:00', yemek_dk: 40, hazirlik: '20:00', yatma: '21:30',
    baslamadi_esik_dk: 10, takildi_esik_dk: 20, haber_alacaklar: ['anne@example.com'],
  })
})

test('akşam düzeni sırası sunucununkiyle aynı denetlenir', () => {
  assert.equal(duzenHatasi(VARSAYILAN_DUZEN), null)
  assert.match(duzenHatasi({ ...VARSAYILAN_DUZEN, zorIsSonu: dk('16:00') })!, /sırayla/)
  assert.match(duzenHatasi({ ...VARSAYILAN_DUZEN, yatma: dk('20:30') })!, /sırayla/)
  assert.match(duzenHatasi({ ...VARSAYILAN_DUZEN, yemek: dk('16:00') })!, /Yemek/)
  assert.match(duzenHatasi({ ...VARSAYILAN_DUZEN, yemek: dk('20:20') })!, /Yemek/)
  assert.match(duzenHatasi({ ...VARSAYILAN_DUZEN, yemekDk: 5 })!, /Yemek süresi/)
  assert.match(duzenHatasi({ ...VARSAYILAN_DUZEN, takildiEsikDk: 70 })!, /Haber verme/)
})

test('kartın sesi akşam düzenini izler: ödeve hazırdan zor iş sonuna "Şimdi"', () => {
  assert.equal(windowVoice(dk('17:10'), 'work', true, VARSAYILAN_DUZEN).eyebrow, 'Şimdi')
  assert.deepEqual(windowVoice(dk('16:00'), 'work', true, VARSAYILAN_DUZEN), {
    eyebrow: 'Okuldan sonra', hint: 'Bunu okuldan sonra yapmak daha kolay', anchorMin: dk('17:00'),
  })
  assert.equal(windowVoice(dk('10:00'), 'work', true, VARSAYILAN_DUZEN).eyebrow, 'Okuldan sonra')
  assert.equal(windowVoice(dk('19:00'), 'work', true, VARSAYILAN_DUZEN).eyebrow, 'Bu akşam')
  assert.equal(windowVoice(dk('21:00'), 'work', true, VARSAYILAN_DUZEN).eyebrow, 'Yarın')
  assert.equal(windowVoice(dk('16:00'), 'reading', true, VARSAYILAN_DUZEN).eyebrow, 'Okuldan sonra')
  assert.equal(windowVoice(dk('21:10'), 'reading', false, VARSAYILAN_DUZEN).eyebrow, 'Yarın')
  const gec = { ...VARSAYILAN_DUZEN, odeveHazir: dk('16:30'), zorIsSonu: dk('17:00'), yatma: dk('21:30') }
  assert.equal(windowVoice(dk('16:40'), 'work', true, gec).eyebrow, 'Şimdi')
})
