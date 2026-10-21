import assert from 'node:assert/strict'
import { test } from 'node:test'
import { isleriGrupla, sinavZamani, teslimMetni } from '../src/utils/isler.ts'
import type { ExamItem, HomeworkItem } from '../src/types.ts'

// İşler yenilemesi (2026-10-15, spec 2026-10-15-isler-yenileme-design.md): the pure half of the page.
const SIMDI = new Date(2026, 8, 24, 10, 30)   // Perşembe 24.09.2026 10:30, Istanbul wall clock
const hw = (ders: string, baslik: string, teslim: string, ek: Partial<HomeworkItem> = {}) => ({
  'Ders Adı': ders, 'Ödev Başlığı': baslik, 'Ödev Son Teslim Tarihi': teslim,
  'Ödev Durumu': 'Değerlendirilmemiş', ...ek,
}) as HomeworkItem

test('the next thing is named once: it leads, and the list is the rest in deadline order', () => {
  const g = isleriGrupla([
    hw('Türkçe', 'Okuma', '29.09.2026 12:00'),
    hw('Matematik', 'Sayfa 165', '25.09.2026 12:00'),
    hw('Fen Bilimleri', '3 soru', '28.09.2026 08:55'),
  ], SIMDI.getTime())
  assert.equal(g.siradaki?.['Ödev Başlığı'], 'Sayfa 165')
  assert.deepEqual(g.sonra.map(h => h['Ödev Başlığı']), ['3 soru', 'Okuma'])
  assert.ok(!g.sonra.includes(g.siradaki!))
})

test('one active item is the next thing alone; nothing active is an empty list', () => {
  const tek = isleriGrupla([hw('Fen Bilimleri', '3 soru', '28.09.2026 08:55')], SIMDI.getTime())
  assert.equal(tek.siradaki?.['Ödev Başlığı'], '3 soru')
  assert.deepEqual(tek.sonra, [])
  const bos = isleriGrupla([], SIMDI.getTime())
  assert.equal(bos.siradaki, null)
  assert.deepEqual(bos.sonra, [])
})

test('settled work is grouped by who settled it, newest first', () => {
  const g = isleriGrupla([
    hw('Sosyal Bilgiler', 'Harita', '20.09.2026 12:00', { 'Ödev Durumu': 'Yaptı' }),
    hw('İngilizce', 'Unit 2', '19.09.2026 12:00', { 'Ödev Durumu': 'Yapmadı' }),
    hw('Bilişim', 'Algoritma', '21.09.2026 12:00'),                              // ran out, no mark
    hw('Din Kültürü', 'Sunum', '22.09.2026 12:00', { student_marked_done: true }),
    hw('Din Kültürü', 'Ödev 2', '30.09.2026 12:00', { student_marked_done: true }),
    hw('Matematik', 'Eksik iş', '18.09.2026 12:00', { 'Ödev Durumu': 'Eksik' }),
  ], SIMDI.getTime())
  assert.deepEqual(g.tamamlanan.map(h => h['Ödev Başlığı']), ['Harita'])
  assert.deepEqual(g.yapilmayan.map(h => h['Ödev Başlığı']), ['Algoritma', 'Unit 2', 'Eksik iş'])
  assert.deepEqual(g.yapilan.map(h => h['Ödev Başlığı']), ['Ödev 2', 'Sunum'])
  assert.equal(g.siradaki, null)
})

test('a teacher verdict wins over Işık’s own mark; a row with no readable deadline sinks', () => {
  const g = isleriGrupla([
    hw('Fen Bilimleri', 'Belirsiz', ''),
    hw('Matematik', 'Sayfa 165', '25.09.2026 12:00'),
    hw('Türkçe', 'Okuma', '20.09.2026 12:00', { student_marked_done: true, 'Ödev Durumu': 'Yaptı' }),
  ], SIMDI.getTime())
  assert.equal(g.siradaki?.['Ödev Başlığı'], 'Sayfa 165')
  assert.deepEqual(g.sonra.map(h => h['Ödev Başlığı']), ['Belirsiz'])
  assert.deepEqual(g.tamamlanan.map(h => h['Ödev Başlığı']), ['Okuma'])
  assert.deepEqual(g.yapilan, [])
})

test('a deadline reads as a day and a time, in sentence case', () => {
  assert.deepEqual(teslimMetni(new Date(2026, 8, 25, 12, 0), SIMDI), { metin: 'Yarın 12:00', bugun: false })
  assert.deepEqual(teslimMetni(new Date(2026, 8, 28, 8, 55), SIMDI), { metin: 'Pazartesi 08:55', bugun: false })
})

test('due today is the one real urgency, and says so in words', () => {
  assert.deepEqual(teslimMetni(new Date(2026, 8, 24, 17, 0), SIMDI), { metin: 'Bugün 17:00', bugun: true })
})

test('beyond the week the date carries its distance (İ2), and the past is a plain date', () => {
  assert.deepEqual(teslimMetni(new Date(2026, 9, 1, 9, 0), SIMDI), { metin: '1 Eki 09:00 · 7 gün sonra', bugun: false })
  assert.deepEqual(teslimMetni(new Date(2026, 8, 20, 12, 0), SIMDI), { metin: '20 Eyl 12:00', bugun: false })
})

// Ana dala taşıma (2026-10-20): main'in 2026-10-15'ten sonra sınav satırına eklediği zaman kuralları yeni satırda.
const sinav = (date: string | null, ek: Partial<ExamItem> = {}) => ({
  id: 's', course: 'Fen Bilimleri', title: 'Fen Bilimleri KTT', rawTitle: '', courseColor: '', examNumber: null,
  date, endDate: null, allDay: false, status: 'upcoming', grade: null, relatedHomework: [], relatedContent: [], ...ek,
}) as ExamItem

test('an all-day exam is its day alone — no invented hour (C11, C20)', () => {
  assert.deepEqual(sinavZamani(sinav('2026-09-28', { allDay: true }), SIMDI), { metin: 'Pazartesi', bugun: false })
  // A bare date is the local day even without the flag.
  assert.deepEqual(sinavZamani(sinav('2026-09-25'), SIMDI), { metin: 'Yarın', bugun: false })
  assert.deepEqual(sinavZamani(sinav('2026-09-24', { allDay: true }), SIMDI), { metin: 'Bugün', bugun: true })
  assert.deepEqual(sinavZamani(sinav('2026-10-05', { allDay: true }), SIMDI), { metin: '5 Eki · 11 gün sonra', bugun: false })
  assert.deepEqual(teslimMetni(new Date(2026, 8, 20), SIMDI, true), { metin: '20 Eyl', bugun: false })
})

test('a timed exam reads like a deadline; a week-only or undated one as the exam page says it', () => {
  assert.deepEqual(sinavZamani(sinav('2026-09-25T09:40:00'), SIMDI), { metin: 'Yarın 09:40', bugun: false })
  assert.deepEqual(sinavZamani(sinav(null, { hafta: '2026-09-28', tarihBelirsiz: true }), SIMDI),
    { metin: '28 Eyl haftası', bugun: false })
  assert.deepEqual(sinavZamani(sinav(null, { tarihBelirsiz: true }), SIMDI), { metin: 'Tarih belirsiz', bugun: false })
  assert.equal(sinavZamani(sinav(null), SIMDI), null)
})
