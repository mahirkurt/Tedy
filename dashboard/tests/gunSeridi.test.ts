import assert from 'node:assert/strict'
import { test } from 'node:test'
import { gunParcalari, odevAraligi, type GunGirdisi } from '../src/utils/gunSeridi.ts'

const dk = (s: string) => { const [h, m] = s.split(':').map(Number); return h * 60 + m }
const ozet = (g: GunGirdisi) =>
  gunParcalari(g).map(p => `${p.tur} ${String(p.bas / 60 | 0).padStart(2, '0')}:${String(p.bas % 60).padStart(2, '0')}`)

const okulGunu = (simdi: string): GunGirdisi => ({
  simdi: dk(simdi), yatma: dk('22:30'), odakSonu: dk('16:00'), gunBasi: dk('08:00'),
  okul: { bas: dk('08:00'), bit: dk('15:45') },
})

test('okul sabahı: sabah, okul, ödev zamanı, akşam — sırayla', () => {
  assert.deepEqual(ozet(okulGunu('06:42')), ['sabah 06:42', 'okul 08:00', 'odev 15:45', 'aksam 16:00'])
})

test('ders sırasında sabah ve geçen okul çizilmez; okul şimdi başlar', () => {
  assert.deepEqual(ozet(okulGunu('10:15')), ['okul 10:15', 'odev 15:45', 'aksam 16:00'])
})

test('ödev zamanının içinde ödev şimdi başlar', () => {
  assert.deepEqual(ozet(okulGunu('15:50')), ['odev 15:50', 'aksam 16:00'])
})

test('pencere geçince yalnız akşam kalır; yatmadan sonra hiçbir şey', () => {
  assert.deepEqual(ozet(okulGunu('17:00')), ['aksam 17:00'])
  assert.deepEqual(ozet(okulGunu('23:00')), [])
})

test('okulsuz günde ödev zamanı günün başından odak sonuna', () => {
  const g: GunGirdisi = { ...okulGunu('07:00'), okul: null }
  assert.deepEqual(ozet(g), ['sabah 07:00', 'odev 08:00', 'aksam 16:00'])
  assert.deepEqual(odevAraligi(g), { bas: dk('08:00'), bit: dk('16:00') })
})

test('odak sonu son zilden önceyse ödev zamanı yok, akşam zilden başlar', () => {
  const g: GunGirdisi = { ...okulGunu('09:00'), odakSonu: dk('15:00') }
  assert.equal(odevAraligi(g), null)
  assert.deepEqual(ozet(g), ['okul 09:00', 'aksam 15:45'])
})

test('cuma: geç biten son zil ödev zamanını kaydırır', () => {
  const g: GunGirdisi = { ...okulGunu('12:00'), okul: { bas: dk('08:00'), bit: dk('15:55') } }
  assert.deepEqual(ozet(g), ['okul 12:00', 'odev 15:55', 'aksam 16:00'])
})
