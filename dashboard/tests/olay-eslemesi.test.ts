/* eslint-disable @typescript-eslint/no-explicit-any -- testler Carbon parçalarının iç içe yapısında serbestçe gezinir */
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { akisBaslat, olayIsle, sonYanit, hataYaniti, taslakMetni, AkisHatasi, ALTBILGI_YUVASI }
  from '../src/asistan/olayEslemesi.ts'
import type { AkisDurumu, TedyOlayi } from '../src/asistan/olayEslemesi.ts'
import type { AssistantResponse } from '../src/types.ts'

const SEC = { geriBildirim: true, ogrenci: true }
const yuk = (p: Partial<AssistantResponse> = {}): AssistantResponse => ({
  answer: 'Cevap [S1].', citations: [{ id: 'S1', kind: 'mufredat', label: 'Mat 7 · s.5', locator: {}, snippet: 's', confidence: 1 }],
  safety_flags: [], plan_blocks: [], intent: 'qa', session_id: '', meta: { model: 'claude-sonnet-5', degraded: [] },
  mesaj_id: 'a'.repeat(32), ...p,
})
function oynat(olaylar: TedyOlayi[]) {
  let d: AkisDurumu = akisBaslat('y1')
  const tum: unknown[] = []
  for (const o of olaylar) { const r = olayIsle(d, o, SEC); d = r.durum; tum.push(...r.parcalar) }
  return { d, tum: tum as Record<string, any>[] }
}

test('taslak işaretleri gizler, yarım işareti de', () => {
  assert.equal(taslakMetni('Payda [S1] eşit [S'), 'Payda eşit')
})

test('delta parçaları biriktirir, yarım işaret sonra gelmez', () => {
  const { tum } = oynat([{ ad: 'answer_delta', veri: { text: 'Payda [S' } }, { ad: 'answer_delta', veri: { text: '1] eşit' } }])
  const metinler = tum.map(p => p.partial_item?.text)
  assert.deepEqual(metinler, ['Payda', ' eşit'])
  assert.equal(tum[0].partial_item.streaming_metadata.id, 'metin-0')
  assert.equal(tum[0].streaming_metadata.response_id, 'y1')
})

test('answer_reset taslağı boşaltır ve yeni öğeye geçer', () => {
  const { tum } = oynat([{ ad: 'answer_delta', veri: { text: 'Önce bakayım.' } }, { ad: 'answer_reset', veri: {} },
    { ad: 'answer_delta', veri: { text: 'Asıl' } }])
  assert.deepEqual(tum[1].complete_item, { response_type: 'text', text: '', streaming_metadata: { id: 'metin-0' } })
  assert.equal(tum[2].partial_item.streaming_metadata.id, 'metin-1')
})

test('araç adımları sürer ve özetle biter', () => {
  const { d, tum } = oynat([{ ad: 'tool_start', veri: { name: 'kitap_sayfa' } },
    { ad: 'tool_end', veri: { name: 'kitap_sayfa', ok: true, ozet: 'Mat 7 · s.5' } },
    { ad: 'tool_start', veri: { name: 'yeni_arac' } }, { ad: 'tool_end', veri: { name: 'yeni_arac', ok: false } }])
  const adimlar = tum[3].partial_response.message_options.chain_of_thought
  assert.deepEqual(adimlar[0], { title: 'Ders kitabı sayfası okunuyor', description: 'Mat 7 · s.5', tool_name: 'kitap_sayfa', status: 'success' })
  assert.equal(adimlar[1].title, 'Kaynaklar taranıyor')
  assert.equal(adimlar[1].status, 'failure')
  assert.equal(d.adimlar.length, 2)
})

test('answer final_response üretir: atıflı metin, altbilgi, geri bildirim, adımlar, kartlar', () => {
  const { tum } = oynat([{ ad: 'tool_start', veri: { name: 'mufredat_ara' } },
    { ad: 'tool_end', veri: { name: 'mufredat_ara', ok: true, ozet: 'Mat 7 · s.5' } },
    { ad: 'mode_suggestion', veri: { ogretmen: 'matematik', ogretmen_adi: 'Matematik öğretmeni', soru: 'x', gerekce: 'y', renk_ailesi: 'blue' } },
    { ad: 'mode_suggestion', veri: { ogretmen: 'fen' } },
    { ad: 'answer', veri: { payload: yuk() } }])
  const f = tum.at(-1)!.final_response
  assert.equal(f.id, 'y1')
  const [ana, kart] = f.output.generic
  assert.equal(ana.response_type, 'conversational_search')
  assert.equal(ana.text, 'Cevap.')
  assert.equal(ana.citations[0].title, 'Mat 7 · s.5')
  assert.equal(ana.message_item_options.feedback.id, 'a'.repeat(32))
  assert.equal(ana.message_item_options.feedback.placeholder, 'Ailen bunu görebilir.')
  assert.deepEqual(ana.message_item_options.feedback.categories.negative,
    ['Yanlış bilgi', 'Anlamadım', 'Seviyeme uygun değil', 'Kaynak göstermedi', 'Diğer'])
  assert.equal(ana.message_item_options.custom_footer_slot.slot_name, ALTBILGI_YUVASI)
  assert.equal(ana.message_item_options.custom_footer_slot.additional_data.metin, 'Cevap [S1].')
  assert.deepEqual(kart.user_defined.tedy, { tur: 'mod_onerisi', veri: { ogretmen: 'matematik', ogretmen_adi: 'Matematik öğretmeni', soru: 'x', gerekce: 'y', renk_ailesi: 'blue' } })
  assert.equal(f.message_options.chain_of_thought[0].status, 'success')
})

test('atıfsız cevap düz metin; mesaj kimliği yoksa geri bildirim yok; aile için yer tutucu', () => {
  const m = sonYanit(akisBaslat('y2'), yuk({ citations: [], answer: 'Merhaba', mesaj_id: undefined }), { geriBildirim: true, ogrenci: false })
  const ana = m.output.generic![0] as Record<string, any>
  assert.equal(ana.response_type, 'text')
  assert.equal(ana.message_item_options.feedback, undefined)
  const m2 = sonYanit(akisBaslat('y3'), yuk(), { geriBildirim: true, ogrenci: false }).output.generic![0] as Record<string, any>
  assert.equal(m2.message_item_options.feedback.placeholder, 'Yorum ekle')
})

test('boş cevap okura cümleyle; payload kartları akıştakinin önüne geçer; plan blokları kart olur', () => {
  let d = akisBaslat('y4')
  d = olayIsle(d, { ad: 'clarify', veri: { soru: 'akış', secenekler: ['a', 'b'] } }, SEC).durum
  d = olayIsle(d, { ad: 'quiz', veri: { id: 'q1', sorular: [] } }, SEC).durum
  const m = sonYanit(d, yuk({ answer: '  ', citations: [], netlestirme: { soru: 'yük', secenekler: ['c', 'd'] },
    plan_blocks: [{ day: 'Pzt', title: 't', actions: ['a'], estimated_minutes: 20 } as never] }), SEC)
  const g = m.output.generic as Record<string, any>[]
  assert.equal(g[0].text, 'Yanıt üretilemedi.')
  const turler = g.slice(1).map(x => x.user_defined.tedy.tur)
  assert.deepEqual(turler, ['alistirma', 'netlestirme', 'plan'])
  assert.equal(g.find(x => x.user_defined?.tedy.tur === 'netlestirme')!.user_defined.tedy.veri.soru, 'yük')
})

test('quiz akışta hemen kart olarak gelir', () => {
  const { tum } = oynat([{ ad: 'quiz', veri: { id: 'q1', sorular: [] } }])
  assert.deepEqual(tum[0].complete_item.user_defined.tedy, { tur: 'alistirma', veri: { id: 'q1', sorular: [] }, akista: true })
  assert.equal(tum[0].complete_item.streaming_metadata.id, 'kart-alistirma-0')
})

test('akis_dustu: eski mesaj kaldırılır, yeni kimlikle baştan başlanır', () => {
  let d = akisBaslat('y5')
  d = olayIsle(d, { ad: 'answer_delta', veri: { text: 'yarım' } }, SEC).durum
  const r = olayIsle(d, { ad: 'akis_dustu', veri: { yeniId: 'y6' } }, SEC)
  assert.deepEqual(r.kaldir, ['y5'])
  assert.equal(r.durum.yanitId, 'y6')
  assert.equal(r.durum.gorunen, '')
})

test('error olayı AkisHatasi fırlatır; hata yanıtı kart taşır', () => {
  assert.throws(() => olayIsle(akisBaslat('y7'), { ad: 'error', veri: { error: 'Asistan yanıtı alınamadı.' } }, SEC), AkisHatasi)
  const h = hataYaniti('y8', 'Oturumun sona ermiş; sayfayı yenileyip yeniden giriş yap.')
  assert.deepEqual((h.output.generic![0] as Record<string, any>).user_defined.tedy,
    { tur: 'hata', veri: { mesaj: 'Oturumun sona ermiş; sayfayı yenileyip yeniden giriş yap.' } })
})

test('yerel yedek ve kaynak sorunları altbilgiye geçer', () => {
  const m = sonYanit(akisBaslat('y9'), yuk({ citations: [], safety_flags: ['warning:yerel_yedek'],
    meta: { model: 'gemma4-e4b-cpu', degraded: ['maarif-mufredat'], ogretmen: 'fen', denetim: { durum: 'duzeltildi' } } }), SEC)
  const a = (m.output.generic![0] as Record<string, any>).message_item_options.custom_footer_slot.additional_data
  assert.deepEqual([a.bayraklar, a.kaynakSorunlari, a.model, a.ogretmen, a.denetim], [['warning:yerel_yedek'], ['maarif-mufredat'], 'gemma4-e4b-cpu', 'fen', 'duzeltildi'])
})

test('son yanıt öğeleri akıştaki kimlikleri taşır (kart iki kez çizilmez)', () => {
  let d = akisBaslat('y10')
  d = olayIsle(d, { ad: 'quiz', veri: { id: 'q1', sorular: [] } }, SEC).durum
  d = olayIsle(d, { ad: 'answer_reset', veri: {} }, SEC).durum
  const g = sonYanit(d, yuk({ citations: [] }), SEC).output.generic as Record<string, any>[]
  assert.equal(g[0].streaming_metadata.id, 'metin-1')
  assert.equal(g.find(x => x.user_defined?.tedy.tur === 'alistirma')!.streaming_metadata.id, 'kart-alistirma-0')
})
