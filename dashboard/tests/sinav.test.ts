import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  enYakinSinav, konuAnahtarlari, konuOzeti, sinavAni, sinavBitisi, sinavEtiketi, sinavGeriSayimi, zamanMetni,
} from '../src/utils/sinav.ts'
import { execFileSync } from 'node:child_process'
import { pathToFileURL } from 'node:url'
import type { ExamItem } from '../src/types.ts'

// İstanbul saatiyle sabit an: etiket damgaları +03:00 okunur (C18), test her TZ'de aynı sonucu verir.
const SIMDI = Date.parse('2026-10-16T10:00:00+03:00')
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

// C11: tüm gün sınavın geri sayımı yerel gün sonuna (23:59) göredir; sınav günü dolmuş görünmez.
test('C11 tüm gün sınav: bitiş yerel 23:59, sınav günü süresi dolmuş değil', () => {
  const tumGun = s({ date: '2026-10-20', allDay: true })
  const bitis = sinavBitisi(tumGun)!
  assert.deepEqual([bitis.getDate(), bitis.getHours(), bitis.getMinutes()], [20, 23, 59])
  const ogleden = new Date(2026, 9, 20, 15, 0).getTime()
  const g = sinavGeriSayimi(tumGun, ogleden)
  assert.notEqual(g.urgency, 'expired')
  assert.doesNotMatch(g.text, /Geçti|Süresi doldu/)
  // Ertesi gün dolmuştur.
  assert.equal(sinavGeriSayimi(tumGun, new Date(2026, 9, 21, 0, 1).getTime()).urgency, 'expired')
})

test('C11 saatli sınav: bitiş başlangıç saatidir', () => {
  const saatli = s({ date: '2026-10-20T09:00:00', allDay: false })
  assert.equal(sinavBitisi(saatli)!.getHours(), 9)
  assert.equal(sinavGeriSayimi(saatli, new Date(2026, 9, 20, 9, 30).getTime()).urgency, 'expired')
  assert.equal(sinavBitisi(s({ date: null })), null)
})

// C12: en yakın sınav başlamış olanı seçmez (saatli: saati geçmiş; tüm gün: gün bitmiş).
test('C12 en yakın sınav: başlamış saatli sınav ve bitmiş gün seçilmez, bugünkü tüm gün sınav seçilir', () => {
  const simdi = new Date(2026, 9, 16, 10, 0).getTime()
  const basladi = s({ id: 'basladi', date: '2026-10-16T09:00:00', allDay: false })
  const dun = s({ id: 'dun', date: '2026-10-15', allDay: true })
  const sonra = s({ id: 'sonra', date: '2026-10-18T09:00:00', allDay: false })
  assert.equal(enYakinSinav([basladi, dun, sonra], simdi, new Set())?.id, 'sonra')
  const bugunTumGun = s({ id: 'bugun', date: '2026-10-16', allDay: true })
  assert.equal(enYakinSinav([basladi, bugunTumGun, sonra], simdi, new Set())?.id, 'bugun')
  assert.equal(enYakinSinav([basladi, dun], simdi, new Set()), null)
})

// C17: yinelenen konu da kendi anahtarını alır.
test('C17 konu anahtarları yinelenen konuda benzersiz', () => {
  const liste = konuAnahtarlari(['Oran', 'Oran', 'Kesir'])
  assert.deepEqual(liste.map(x => x.konu), ['Oran', 'Oran', 'Kesir'])
  assert.equal(new Set(liste.map(x => x.anahtar)).size, 3)
  assert.deepEqual(konuAnahtarlari(undefined), [])
})

// C18: ilkTespit/degisti naive İstanbul saatidir; tarayıcı başka dilimde olsa da 48 saat doğru ölçülür.
test('C18 etiket damgaları +03:00 ile okunur (TZ=America/New_York)', () => {
  const kaynak = pathToFileURL(new URL('../src/utils/sinav.ts', import.meta.url).pathname).href
  const kod = `
    import { sinavEtiketi } from ${JSON.stringify(kaynak)}
    const e = (k) => ({ id: 'x', date: null, ...k })
    // 15.10 11:00 İstanbul = 08:00Z. 17.10 09:30Z: 49,5 saat sonra → etiket yok.
    // Yerel (New York) okunsaydı 15:00Z olur, 42,5 saat → yanlışlıkla "Yeni".
    const simdi = Date.parse('2026-10-17T09:30:00Z')
    const yeni = sinavEtiketi(e({ ilkTespit: '2026-10-15T11:00:00' }), simdi)
    // 15.10 14:00 İstanbul = 11:00Z → 46,5 saat → "Yeni".
    const sinirda = sinavEtiketi(e({ ilkTespit: '2026-10-15T14:00:00' }), simdi)
    const degisti = sinavEtiketi(e({ degisti: '2026-10-15T11:00:00' }), simdi)
    // Ofset taşıyan damga olduğu gibi okunur.
    const ofsetli = sinavEtiketi(e({ ilkTespit: '2026-10-15T11:00:00Z' }), simdi)
    console.log(JSON.stringify([yeni, sinirda, degisti, ofsetli]))
  `
  const cikti = execFileSync(process.execPath, ['--input-type=module', '-e', kod],
    { env: { ...process.env, TZ: 'America/New_York' }, encoding: 'utf8' })
  assert.deepEqual(JSON.parse(cikti.trim().split('\n').pop()!), [null, 'Yeni', null, 'Yeni'])
})
