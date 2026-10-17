import { test } from 'node:test'
import assert from 'node:assert/strict'
import { enYakinSinav, konuOzeti, sinavAni, sinavEtiketi, zamanMetni } from '../src/utils/sinav.ts'
import { execFileSync } from 'node:child_process'
import { pathToFileURL } from 'node:url'
import type { ExamItem } from '../src/types.ts'

const SIMDI = new Date('2026-10-16T10:00:00').getTime()
const s = (kw: Partial<ExamItem>): ExamItem => ({
  id: 'x', course: 'Matematik', title: 'Matematik KTT', rawTitle: 'Matematik KTT', courseColor: '#000',
  examNumber: null, date: '2026-10-20', endDate: null, allDay: true, status: 'upcoming', grade: null,
  relatedHomework: [], relatedContent: [], ...kw,
})

test('Yeni: son 48 saatte tespit', () => {
  assert.equal(sinavEtiketi(s({ ilkTespit: '2026-10-15T11:00:00' }), SIMDI), 'Yeni')
  assert.equal(sinavEtiketi(s({ ilkTespit: '2026-10-14T09:00:00' }), SIMDI), null)
  assert.equal(sinavEtiketi(s({ ilkTespit: null }), SIMDI), null)
})

test('Değişti Yeni’den önce gelir', () => {
  assert.equal(sinavEtiketi(s({ ilkTespit: '2026-10-15T11:00:00', degisti: '2026-10-16T09:00:00' }), SIMDI), 'Değişti')
})

test('en yakın sınav: 7 gün içinde, tarihli, hariç tutulan dışında', () => {
  const liste = [s({ id: 'a', date: '2026-10-25' }), s({ id: 'b', date: '2026-10-19T09:00:00', allDay: false }),
    s({ id: 'c', date: null, tarihBelirsiz: true }), s({ id: 'd', date: '2026-10-17', status: 'past' })]
  assert.equal(enYakinSinav(liste, SIMDI, new Set())?.id, 'b')
  assert.equal(enYakinSinav(liste, SIMDI, new Set(['b'])), null)
})

test('konu özeti ilk üç', () => {
  assert.equal(konuOzeti(['A', 'B', 'C', 'D', 'E']), 'A, B, C +2 konu')
  assert.equal(konuOzeti(['A']), 'A')
  assert.equal(konuOzeti(undefined), '')
})

test('zaman metni: gün, hafta, belirsiz', () => {
  assert.equal(zamanMetni(s({ date: '2026-10-20' })), '20 Eki')
  assert.equal(zamanMetni(s({ date: '2026-10-20T09:30:00', allDay: false })), '20 Eki 09:30')
  assert.equal(zamanMetni(s({ date: null, hafta: '2026-10-19', tarihBelirsiz: true })), '19 Eki haftası')
  assert.equal(zamanMetni(s({ date: null, tarihBelirsiz: true })), 'Tarih belirsiz')
})

// A date-only exam ("2026-09-28", the shape the API sends for text-detected
// exams) is the LOCAL day. `new Date('2026-09-28')` is UTC midnight, which an
// Istanbul browser reads as 03:00. The host's zone is UTC, where both parses
// agree, so the zone is forced in a child process.
test('tarih-yalnız sınav yerel gece yarısıdır (TZ=Europe/Istanbul)', () => {
  const kaynak = pathToFileURL(new URL('../src/utils/sinav.ts', import.meta.url).pathname).href
  const kod = `
    import { sinavAni, enYakinSinav } from ${JSON.stringify(kaynak)}
    const d = sinavAni({ date: '2026-09-28' })
    const t = sinavAni({ date: '2026-09-28T09:00:00' })
    const e = { id: 'a', status: 'upcoming', date: '2026-09-28' }
    const simdi = new Date('2026-09-27T10:00:00').getTime()
    console.log(JSON.stringify([d.getHours(), d.getDate(), t.getHours(), enYakinSinav([e], simdi, new Set())?.id, sinavAni({ date: null })]))
  `
  const cikti = execFileSync(process.execPath, ['--input-type=module', '-e', kod],
    { env: { ...process.env, TZ: 'Europe/Istanbul' }, encoding: 'utf8' })
  assert.deepEqual(JSON.parse(cikti.trim().split('\n').pop()!), [0, 28, 9, 'a', null])
})

test('sinavAni: tarih-yalnız yerel gün, saatli olduğu gibi', () => {
  const d = sinavAni({ date: '2026-09-28' })!
  assert.equal(d.getHours(), 0)
  assert.equal(d.getDate(), 28)
  assert.equal(sinavAni({ date: '2026-09-28T09:30:00' })!.getHours(), 9)
  assert.equal(sinavAni({ date: 'bozuk' }), null)
})
