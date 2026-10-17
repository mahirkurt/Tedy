import { test } from 'node:test'
import assert from 'node:assert/strict'
import { enYakinSinav, konuOzeti, sinavEtiketi, zamanMetni } from '../src/utils/sinav.ts'
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
