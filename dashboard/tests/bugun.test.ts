import assert from 'node:assert/strict'
import { test } from 'node:test'
import {
  windowVoice, okulGunuMu, yerSec, simdiUstu, bitenOzeti, sonrakiOkulGunu, yarinBasligi,
  rakamParcala, SCHOOL_END, VARSAYILAN_PENCERE, pencereCoz, pencereGovdesi,
  type AgendaSlot, type AgendaType,
} from '../src/utils/bugun.ts'

const dk = (s: string) => { const [h, m] = s.split(':').map(Number); return h * 60 + m }
const oge = (type: AgendaType, bas: string, bit: string, simdi: string): AgendaSlot => ({
  type, startMin: dk(bas), endMin: dk(bit),
  isActive: dk(simdi) >= dk(bas) && dk(simdi) < dk(bit),
  isPast: dk(simdi) >= dk(bit),
})

test('okul günü: ders sürerken iş "Okuldan sonra", 15:45\'e çapalı', () => {
  assert.deepEqual(windowVoice(dk('10:30'), 'work', true), {
    eyebrow: 'Okuldan sonra', hint: 'Bunu okuldan sonra yapmak daha kolay', anchorMin: SCHOOL_END,
  })
  assert.equal(windowVoice(dk('15:50'), 'work', true).eyebrow, 'Şimdi')
  assert.equal(windowVoice(dk('16:40'), 'work', true).eyebrow, 'Bu akşam')
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
    for (const saat of ['07:00', '10:00', '13:00', '15:50', '17:00', '23:00']) {
      const ses = windowVoice(dk(saat), kind, false)
      assert.ok(!/okul/i.test(ses.eyebrow + (ses.hint ?? '')), `${kind} ${saat}: ${ses.eyebrow}`)
      assert.equal(ses.anchorMin, undefined)
    }
    assert.equal(windowVoice(dk('10:00'), kind, false).eyebrow, 'Şimdi')
    assert.equal(windowVoice(dk('17:00'), kind, false).eyebrow, 'Bu akşam')
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

// B29 (2026-10-11): the focus window is read from the server (output/), today's
// values being the defaults.
test('odak penceresi sunucudan çözülür; bozuk ya da eksikse bugünkü değerler', () => {
  assert.deepEqual(VARSAYILAN_PENCERE, { okulBitisi: dk('15:45'), odakSonu: dk('16:00'), yatma: dk('22:30') })
  assert.deepEqual(pencereCoz({ okul_bitisi: '15:30', odak_sonu: '16:30', yatma: '21:45', varsayilan: false }),
    { okulBitisi: dk('15:30'), odakSonu: dk('16:30'), yatma: dk('21:45') })
  for (const bozuk of [{}, null, 'x', { okul_bitisi: '15:30', odak_sonu: '16:30' },
    { okul_bitisi: '25:00', odak_sonu: '16:30', yatma: '21:45' },
    { okul_bitisi: '17:00', odak_sonu: '16:30', yatma: '21:45' }]) {
    assert.deepEqual(pencereCoz(bozuk), VARSAYILAN_PENCERE, JSON.stringify(bozuk))
  }
  assert.deepEqual(pencereGovdesi(VARSAYILAN_PENCERE), { okul_bitisi: '15:45', odak_sonu: '16:00', yatma: '22:30' })
})

test('pencere değişince kartın sesi de değişir', () => {
  const gec = { okulBitisi: dk('16:30'), odakSonu: dk('17:00'), yatma: dk('21:30') }
  // 16:10 is "Bu akşam" with today's window, still school with a later bell.
  assert.equal(windowVoice(dk('16:10'), 'work', true).eyebrow, 'Bu akşam')
  assert.deepEqual(windowVoice(dk('16:10'), 'work', true, gec), {
    eyebrow: 'Okuldan sonra', hint: 'Bunu okuldan sonra yapmak daha kolay', anchorMin: dk('16:30'),
  })
  assert.equal(windowVoice(dk('16:40'), 'work', true, gec).eyebrow, 'Şimdi')
  assert.equal(windowVoice(dk('21:40'), 'work', true, gec).eyebrow, 'Yarın')
  assert.equal(windowVoice(dk('21:40'), 'reading', false, gec).eyebrow, 'Yarın')
})
