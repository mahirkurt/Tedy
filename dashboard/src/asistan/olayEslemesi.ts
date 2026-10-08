// TEDY SSE olayları → Carbon AI Chat mesaj parçaları (spec §2). Saf: React'e, DOM'a ve
// @carbon/ai-chat'in çalışma zamanına dokunmaz; yalnız türlerini kullanır.
import type { AssistantCitation, AssistantPlanBlock, AssistantResponse, ModOnerisi, Netlestirme } from '../types'
import type { Alistirma } from '../components/AlistirmaKarti'
import type { OdevOnerisi } from '../components/OdevOnayKarti'
import type { GenericItem, MessageResponse, ReasoningSteps, StreamChunk } from '@carbon/ai-chat'
import { atiflariAyikla } from './atiflar.ts'

export const ARAC_ETIKETI: Record<string, string> = {
  ogrenci_verisi_ara: 'Okul verilerin taranıyor', kazanim_ara: 'MEB kazanımları aranıyor',
  kazanim_listele: 'Kazanım listesi alınıyor', mufredat_ara: 'Müfredat aranıyor',
  kitap_listele: 'Ders kitapları listeleniyor', kitap_sayfa: 'Ders kitabı sayfası okunuyor',
  figur_ara: 'Görsel aranıyor', figur_getir: 'Görsel getiriliyor', oer_ara: 'Açık kaynaklar taranıyor',
  oer_kazanima_gore: 'Kazanıma bağlı kaynaklar alınıyor', modul_ara: 'Yayınlanmış modüller aranıyor',
  odev_listesi: 'Ödev listen okunuyor', odev_belgesi: 'Ödev belgesi aranıyor', odev_tamamla: 'Eksik alan kaydediliyor',
  skill_kaynagi: 'Öğretmen notları açılıyor', mod_oner: 'Öğretmen önerisi hazırlanıyor',
  netlestir: 'Seçenekler hazırlanıyor', alistirma_hazirla: 'Alıştırma hazırlanıyor',
  odev_fotograftan: 'Fotoğraftaki ödev okunuyor', yuklenen_dosya_oku: 'Ek okunuyor',
}
export const VARSAYILAN_ADIM = 'Kaynaklar taranıyor'
export const ALTBILGI_YUVASI = 'tedy-altbilgi'
export const GERI_BILDIRIM_KATEGORILERI = ['Yanlış bilgi', 'Anlamadım', 'Seviyeme uygun değil', 'Kaynak göstermedi', 'Diğer']

export type OzelKart =
  | { tur: 'alistirma'; veri: Alistirma; akista?: boolean }
  | { tur: 'odev_onerisi'; veri: OdevOnerisi }
  | { tur: 'netlestirme'; veri: Netlestirme }
  | { tur: 'mod_onerisi'; veri: ModOnerisi }
  | { tur: 'plan'; veri: AssistantPlanBlock[] }
  | { tur: 'hata'; veri: { mesaj: string } }

export interface Adim { arac: string; baslik: string; durum: 'processing' | 'success' | 'failure'; ozet?: string }
export interface TedyOlayi { ad: string; veri: Record<string, unknown> }
export interface SonYanitSecenekleri { geriBildirim: boolean; ogrenci: boolean }
export interface AltbilgiVerisi {
  mesajId?: string; model?: string; bayraklar: string[]; kaynakSorunlari: string[]
  ogretmen?: string; denetim?: string; metin: string; atiflar: AssistantCitation[]
}
export interface AkisDurumu {
  yanitId: string; ogeNo: number; ham: string; gorunen: string; adimlar: Adim[]
  alistirmalar: Alistirma[]; netlestirme: Netlestirme | null; modOnerisi: ModOnerisi | null
  odevOnerisi: OdevOnerisi | null; bitti: boolean
}

export class AkisHatasi extends Error {}

// Carbon'un dize enum'ları çalışma zamanında içe aktarılmaz (node testleri paketi yüklemez).
const tur = <T>(s: string) => s as unknown as T

/** Akan taslakta `[S1]` görünmez; kaynaklar ancak son cevapla gelir (D4). Yarım işaret de gizlenir. */
export function taslakMetni(text: string): string {
  return text.replace(/\s?\[S\d+\]/g, '').replace(/\s?\[(S\d*)?$/, '')
}

export function akisBaslat(yanitId: string): AkisDurumu {
  return { yanitId, ogeNo: 0, ham: '', gorunen: '', adimlar: [], alistirmalar: [], netlestirme: null,
    modOnerisi: null, odevOnerisi: null, bitti: false }
}

const meta = (d: AkisDurumu) => ({ streaming_metadata: { response_id: d.yanitId } })
const metinId = (d: AkisDurumu) => `metin-${d.ogeNo}`
// Carbon'un kullanıcıya dönük adım bileşeni (reasoning): akış sürerken açık durur, ilk cevap öğesi gelince
// kendiliğinden kapanır (eski "düşünüyor" göstergesi gibi); chain_of_thought ise hep katlı başlıyordu.
const ULASILAMADI = 'Bu kaynağa şu an ulaşılamadı.'
const adimlar = (d: AkisDurumu): ReasoningSteps => ({ steps: d.adimlar.map(a => ({
  title: a.baslik,
  ...(a.ozet ? { content: a.ozet } : a.durum === 'failure' ? { content: ULASILAMADI } : {}),
})) })

function kismi(d: AkisDurumu, text: string, adimlarla = false): StreamChunk {
  return {
    partial_item: { response_type: tur('text'), text, streaming_metadata: { id: metinId(d) } },
    ...(adimlarla ? { partial_response: { message_options: { reasoning: adimlar(d) } } } : {}),
    ...meta(d),
  } as StreamChunk
}
function tam(d: AkisDurumu, item: Record<string, unknown>, id: string): StreamChunk {
  return { complete_item: { ...item, streaming_metadata: { id } }, ...meta(d) } as unknown as StreamChunk
}
const kartOgesi = (kart: OzelKart) => ({ response_type: tur('user_defined'), user_defined: { tedy: kart } })

export function olayIsle(d: AkisDurumu, o: TedyOlayi, sec: SonYanitSecenekleri):
  { durum: AkisDurumu; parcalar: StreamChunk[]; kaldir?: string[] } {
  const v = o.veri
  switch (o.ad) {
    case 'tool_start': {
      const arac = String(v.name ?? '')
      const durum = { ...d, adimlar: [...d.adimlar, { arac, baslik: ARAC_ETIKETI[arac] ?? VARSAYILAN_ADIM, durum: 'processing' as const }] }
      return { durum, parcalar: [kismi(durum, '', true)] }
    }
    case 'tool_end': {
      const arac = String(v.name ?? '')
      const yeni = [...d.adimlar]
      const i = yeni.map(a => a.arac === arac && a.durum === 'processing').lastIndexOf(true)
      if (i >= 0) yeni[i] = { ...yeni[i], durum: v.ok ? 'success' : 'failure', ...(v.ozet ? { ozet: String(v.ozet) } : {}) }
      const durum = { ...d, adimlar: yeni }
      return { durum, parcalar: [kismi(durum, '', true)] }
    }
    case 'answer_delta': {
      const ham = d.ham + String(v.text ?? '')
      const gorunur = taslakMetni(ham)
      const durum = { ...d, ham, gorunen: gorunur }
      if (gorunur.startsWith(d.gorunen)) {
        const parca = gorunur.slice(d.gorunen.length)
        return { durum, parcalar: parca ? [kismi(durum, parca)] : [] }
      }
      return { durum, parcalar: [tam(durum, { response_type: tur('text'), text: gorunur }, metinId(durum))] }
    }
    case 'answer_reset': {
      const bos = tam(d, { response_type: tur('text'), text: '' }, metinId(d))
      return { durum: { ...d, ogeNo: d.ogeNo + 1, ham: '', gorunen: '' }, parcalar: [bos] }
    }
    case 'quiz': {
      const veri = v as unknown as Alistirma
      const durum = { ...d, alistirmalar: [...d.alistirmalar, veri] }
      const kart: OzelKart = { tur: 'alistirma', veri, akista: true }
      return { durum, parcalar: [tam(durum, kartOgesi(kart), `kart-alistirma-${d.alistirmalar.length}`)] }
    }
    case 'mode_suggestion':
      return { durum: d.modOnerisi ? d : { ...d, modOnerisi: v as unknown as ModOnerisi }, parcalar: [] }
    case 'clarify':
      return { durum: { ...d, netlestirme: v as unknown as Netlestirme }, parcalar: [] }
    case 'odev_onerisi':
      return { durum: { ...d, odevOnerisi: v as unknown as OdevOnerisi }, parcalar: [] }
    case 'akis_dustu': {
      // Yarım taslak eski mesajla gider; araç adımları yeni mesajda sürer (yedek cevap beklenirken görünür).
      const durum = { ...akisBaslat(String(v.yeniId ?? `${d.yanitId}-yedek`)), adimlar: d.adimlar }
      return { durum, parcalar: durum.adimlar.length ? [kismi(durum, '', true)] : [], kaldir: [d.yanitId] }
    }
    case 'answer': {
      const payload = v.payload as AssistantResponse
      return { durum: { ...d, bitti: true }, parcalar: [{ final_response: sonYanit(d, payload, sec) } as StreamChunk] }
    }
    case 'error':
      throw new AkisHatasi(String(v.error ?? 'akış hatası'))
    default:
      return { durum: d, parcalar: [] }
  }
}

export function sonYanit(d: AkisDurumu, payload: AssistantResponse, sec: SonYanitSecenekleri): MessageResponse {
  const ham = (payload.answer || '').trim() || 'Yanıt üretilemedi.'
  const { metin, atiflar } = atiflariAyikla(ham, payload.citations ?? [])
  const altbilgi: AltbilgiVerisi = {
    mesajId: payload.mesaj_id, model: payload.meta?.model, bayraklar: payload.safety_flags ?? [],
    kaynakSorunlari: payload.meta?.degraded ?? [], ogretmen: payload.meta?.ogretmen,
    denetim: payload.meta?.denetim?.durum, metin: ham, atiflar: payload.citations ?? [],
  }
  const geriBildirim = sec.geriBildirim && payload.mesaj_id ? {
    is_on: true, id: payload.mesaj_id, show_positive_details: false, show_negative_details: true,
    show_text_area: true, show_prompt: true, max_length: 500,
    placeholder: sec.ogrenci ? 'Ailen bunu görebilir.' : 'Yorum ekle',
    categories: { negative: GERI_BILDIRIM_KATEGORILERI },
  } : undefined
  // Akıştaki öğe kimlikleri korunur: son yanıt akışta gelen öğelerin yerine geçer, yanlarına eklenmez.
  const ana = {
    response_type: tur(atiflar.length ? 'conversational_search' : 'text'), text: metin,
    streaming_metadata: { id: metinId(d) },
    ...(atiflar.length ? { citations: atiflar } : {}),
    message_item_options: {
      ...(geriBildirim ? { feedback: geriBildirim } : {}),
      custom_footer_slot: { slot_name: ALTBILGI_YUVASI, is_on: true, additional_data: altbilgi as unknown as Record<string, unknown> },
    },
  }
  const alistirmalar = d.alistirmalar.length ? d.alistirmalar : (payload.quiz ? [payload.quiz] : [])
  const kartlar: OzelKart[] = [
    ...alistirmalar.map(veri => ({ tur: 'alistirma' as const, veri })),
    ...((payload.odev_onerisi ?? d.odevOnerisi) ? [{ tur: 'odev_onerisi' as const, veri: (payload.odev_onerisi ?? d.odevOnerisi)! }] : []),
    ...((payload.netlestirme ?? d.netlestirme) ? [{ tur: 'netlestirme' as const, veri: (payload.netlestirme ?? d.netlestirme)! }] : []),
    ...((payload.mode_suggestion ?? d.modOnerisi) ? [{ tur: 'mod_onerisi' as const, veri: (payload.mode_suggestion ?? d.modOnerisi)! }] : []),
    ...(payload.plan_blocks?.length ? [{ tur: 'plan' as const, veri: payload.plan_blocks }] : []),
  ]
  return {
    id: d.yanitId,
    output: { generic: [ana, ...kartlar.map((k, i) => ({ ...kartOgesi(k),
      ...(k.tur === 'alistirma' && i < d.alistirmalar.length ? { streaming_metadata: { id: `kart-alistirma-${i}` } } : {}) }))] as unknown as GenericItem[] },
    ...(d.adimlar.length ? { message_options: { reasoning: adimlar(d) } } : {}),
  }
}

export function hataYaniti(yanitId: string, mesaj: string): MessageResponse {
  return { id: yanitId, output: { generic: [kartOgesi({ tur: 'hata', veri: { mesaj } })] as unknown as GenericItem[] } }
}
