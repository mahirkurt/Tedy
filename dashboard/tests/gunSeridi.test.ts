import assert from 'node:assert/strict'
import { test } from 'node:test'
import { gunParcalari, odevAraligi, type GunGirdisi } from '../src/utils/gunSeridi.ts'

const dk = (s: string) => { const [h, m] = s.split(':').map(Number); return h * 60 + m }
const ozet = (g: GunGirdisi) =>
  gunParcalari(g).map(p => `${p.tur} ${String(p.bas / 60 | 0).padStart(2, '0')}:${String(p.bas % 60).padStart(2, '0')}`)

const okulGunu = (simdi: string): GunGirdisi => ({
  simdi: dk(simdi), yatma: dk('21:00'), odeveHazir: dk('17:00'), zorIsSonu: dk('19:00'),
  okul: { bas: dk('08:00'), bit: dk('15:45') },
})

test('okul sabahı: sabah, okul, yol, ödev zamanı, akşam — sırayla', () => {
  assert.deepEqual(ozet(okulGunu('06:42')), ['sabah 06:42', 'okul 08:00', 'yol 15:45', 'odev 17:00', 'aksam 19:00'])
})

test('ders sırasında sabah ve geçen okul çizilmez; okul şimdi başlar', () => {
  assert.deepEqual(ozet(okulGunu('10:15')), ['okul 10:15', 'yol 15:45', 'odev 17:00', 'aksam 19:00'])
})

test('son zilden sonra yol şimdi başlar', () => {
  assert.deepEqual(ozet(okulGunu('16:10')), ['yol 16:10', 'odev 17:00', 'aksam 19:00'])
})

test('ödev zamanının içinde ödev şimdi başlar', () => {
  assert.deepEqual(ozet(okulGunu('17:30')), ['odev 17:30', 'aksam 19:00'])
})

test('zor iş bitince yalnız akşam kalır; yatmadan sonra hiçbir şey', () => {
  assert.deepEqual(ozet(okulGunu('19:30')), ['aksam 19:30'])
  assert.deepEqual(ozet(okulGunu('21:30')), [])
})

test('okulsuz günde ödev zamanı ödeve hazır saatinden zor iş sonuna', () => {
  const g: GunGirdisi = { ...okulGunu('07:00'), okul: null }
  assert.deepEqual(ozet(g), ['sabah 07:00', 'odev 17:00', 'aksam 19:00'])
  assert.deepEqual(odevAraligi(g), { bas: dk('17:00'), bit: dk('19:00') })
})

test('zor iş sonu son zilden önceyse ödev zamanı yok, akşam zilden başlar', () => {
  const g: GunGirdisi = { ...okulGunu('09:00'), odeveHazir: dk('14:00'), zorIsSonu: dk('15:00') }
  assert.equal(odevAraligi(g), null)
  assert.deepEqual(ozet(g), ['okul 09:00', 'aksam 15:45'])
})

test('cuma: ödeve hazır saati zilden önceyse geç biten zil ödev zamanını kaydırır, yol çizilmez', () => {
  const g: GunGirdisi = { ...okulGunu('12:00'), odeveHazir: dk('15:50'), okul: { bas: dk('08:00'), bit: dk('15:55') } }
  assert.deepEqual(ozet(g), ['okul 12:00', 'odev 15:55', 'aksam 19:00'])
})
