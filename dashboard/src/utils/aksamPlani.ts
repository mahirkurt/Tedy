/**
 * The evening study plan on Bugün (spec 2026-10-19 §6.7, §6.8): what the card
 * says, from the shape `/api/plan/bugun` serves (src/dashboard_api.py,
 * `_plan_yaniti`). Free of React and the browser so node:test can pin it
 * (tests/aksamPlani.test.ts); `components/AksamPlani.tsx` draws it.
 *
 * Every string is sentence case (S38) and calm: no alarm words, no points or
 * streaks. A work duration is only ever an estimate and is said with the word
 * "tahmin" — the portal never says how long homework takes (D4, İ3).
 */

export type PlanDurumu = 'plansiz' | 'onizleme' | 'akis' | 'bitti' | 'okulsuz' | 'kapali'
export type BlokTuru = 'calisma' | 'mola' | 'yemek' | 'olay'
export type BlokDurumu = 'bekliyor' | 'suruyor' | 'bitti' | 'ertelendi'

export interface PlanBlogu {
  id: string
  tur: BlokTuru
  /** Minutes since midnight; for a running block `bit` is its start plus the estimate. */
  bas: number
  bit: number
  bas_saat?: string
  bit_saat?: string
  odev_anahtari: string | null
  ders: string | null
  baslik: string
  adim: string
  parca: number
  parca_sayisi: number
  tahmin_dk: number
  zorluk: string
  durum: BlokDurumu
  ham_dk: number
}

/** A homework that did not fit tonight: moved to tomorrow, or due too soon to move. */
export interface PlanKaydi {
  odev_anahtari: string
  ders: string | null
  baslik: string
  teslim: string
  kalan_dk: number
}

export interface PlanYaniti {
  gun: string
  durum: PlanDurumu
  bloklar: PlanBlogu[]
  simdiki: PlanBlogu | null
  siradaki: PlanBlogu | null
  tasinan: PlanKaydi[]
  sigmayan: PlanKaydi[]
  planda_olmayan: number
  /** "17:15'e kadar başlamazsan ailene haber gider." — or null, then nothing is drawn. */
  haber_metni: string | null
  /** The family's "Bu akşam plan yok" switch for today (R18). A holiday is also `kapali`, with this false. */
  aksam_yok: boolean
}

export type KartTuru = 'onizleme' | 'calisma' | 'mola' | 'bekliyor' | 'bitti' | 'kapali' | 'yok'

export interface KartDurumu {
  tur: KartTuru
  /** The line above the title: "Sürüyor · tahminen 12 dk kaldı", "Şimdi", "Planda 18:00". */
  ust: string
  /** The card's largest text: the step itself (P1). */
  baslik: string
  /** One quiet line under it: "Sırada: …", "İlk iş: …". */
  alt: string
  /** Minutes left of the running block's estimate or of the break. */
  kalanDk?: number
  /** The block the card's buttons act on. */
  blok?: PlanBlogu
}

/** A holiday closes the evening's plan; said once, quietly. */
export const TATIL_METNI = 'Bugün tatil, akşam planı yok.'

const iki = (n: number) => String(n).padStart(2, '0')

/** 1025 → "17:05". */
export function dakikaSaat(dk: number): string {
  const n = Math.max(0, Math.min(1439, Math.round(dk)))
  return `${iki(Math.floor(n / 60))}:${iki(n % 60)}`
}

const saatYaz = (b: PlanBlogu, uc: 'bas' | 'bit') =>
  (uc === 'bas' ? b.bas_saat : b.bit_saat) || dakikaSaat(b[uc])

/** The one way a work duration is written: "tahmin 20 dk". */
export function tahminMetni(dk: number): string {
  return `tahmin ${Math.max(0, Math.round(dk))} dk`
}

// The word a time is read with ends it: "on yedi" (17:00), "on beş" (17:15).
const BIRIMLER = ['', 'bir', 'iki', 'üç', 'dört', 'beş', 'altı', 'yedi', 'sekiz', 'dokuz']
const ONLAR = ['', 'on', 'yirmi', 'otuz', 'kırk', 'elli']
const INCE = new Set(['e', 'i', 'ö', 'ü'])
const UNLU = new Set(['a', 'e', 'ı', 'i', 'o', 'ö', 'u', 'ü'])
const SERT = new Set(['ç', 'f', 'h', 'k', 'p', 's', 'ş', 't'])

/** "17:00" → "17:00'de", "17:15" → "17:15'te": the locative case, by the last word the time is read with
 *  (the minute, or the hour when the minute is 00) — vowel harmony and the hard consonants (ç f h k p s ş t). */
export function bulunmaHali(saat: string): string {
  const [s, d] = saat.split(':').map(Number)
  const n = d || s
  const kelime = n === 0 ? 'sıfır' : n % 10 ? BIRIMLER[n % 10] : ONLAR[n / 10]
  const sonUnlu = [...kelime].reverse().find(h => UNLU.has(h)) ?? 'e'
  const unsuz = SERT.has(kelime[kelime.length - 1]) ? 't' : 'd'
  return `${saat}'${unsuz}${INCE.has(sonUnlu) ? 'e' : 'a'}`
}

/** The homework's last normal part: its "Bitti" asks whether the whole homework is done. */
export function sonParcaMi(b: PlanBlogu): boolean {
  return b.parca === b.parca_sayisi - 1
}

const calismalar = (p: PlanYaniti) =>
  [...p.bloklar].filter(b => b.tur === 'calisma').sort((a, b) => a.bas - b.bas || a.bit - b.bit)

/** How many homeworks tonight's plan holds (a homework in three parts is one). */
export function isSayisi(p: PlanYaniti): number {
  return new Set(calismalar(p).map(b => b.odev_anahtari ?? b.id)).size
}

/** "Matematik — Hafta içi ödevi": the homework as İşler names it (İ9). */
export function odevAdi(b: { ders: string | null; baslik: string }): string {
  return [b.ders, b.baslik].filter(Boolean).join(' — ')
}

/** "Fen Bilimleri · İlk 2 soruyu çöz": a step, with its course. */
function adimAdi(b: PlanBlogu): string {
  return [b.ders, b.adim || b.baslik].filter(Boolean).join(' · ')
}

/** The work block waiting after `sonra` (or the first one waiting at all). */
function sonrakiCalisma(p: PlanYaniti, sonra?: PlanBlogu | null): PlanBlogu | null {
  return calismalar(p).find(b =>
    (b.durum === 'bekliyor' || b.durum === 'ertelendi') && b.id !== sonra?.id
    && (!sonra || b.bas >= sonra.bas)) ?? null
}

const sirada = (b: PlanBlogu | null) => (b ? `Sırada: ${adimAdi(b)}` : '')

/**
 * What the card says at `simdiMin` (minutes since midnight). The running block
 * always takes the card, whatever the plan's state: it can come from a stored
 * snapshot after its homework left the list, and only its "Bitti" frees "Başla"
 * for the next one (the server answers 409 otherwise).
 */
export function kartDurumu(plan: PlanYaniti, simdiMin: number): KartDurumu {
  const simdiki = plan.simdiki
  if (simdiki) {
    const kalanDk = Math.max(0, simdiki.bit - simdiMin)
    return {
      tur: 'calisma',
      ust: kalanDk > 0 ? `Sürüyor · tahminen ${kalanDk} dk kaldı` : 'Tahmin doldu · bitti mi?',
      baslik: simdiki.adim || simdiki.baslik,
      alt: sirada(plan.siradaki ?? sonrakiCalisma(plan, simdiki)),
      kalanDk,
      blok: simdiki,
    }
  }
  if (plan.durum === 'kapali') {
    // Off by the family's switch, or by a holiday on the school calendar: the switch tells them apart.
    return { tur: 'kapali', ust: '', baslik: plan.aksam_yok ? 'Bu akşam plan yok' : TATIL_METNI, alt: '' }
  }
  if (plan.durum === 'bitti') return { tur: 'bitti', ust: '', baslik: 'Bugünlük bu kadar', alt: '' }
  if (plan.durum !== 'onizleme' && plan.durum !== 'akis') return { tur: 'yok', ust: '', baslik: '', alt: '' }

  const isler = calismalar(plan)
  if (!isler.length) return { tur: 'yok', ust: '', baslik: '', alt: '' }

  if (plan.durum === 'onizleme') {
    const ilk = isler[0]
    return {
      tur: 'onizleme',
      ust: '',
      baslik: `Bu akşam ${isSayisi(plan)} iş · ${bulunmaHali(saatYaz(ilk, 'bas'))} başlıyor`,
      alt: `İlk iş: ${odevAdi(ilk)}`,
      blok: ilk,
    }
  }

  const siradaki = plan.siradaki ?? sonrakiCalisma(plan)
  const mola = plan.bloklar.find(b => b.tur === 'mola' && b.bas <= simdiMin && simdiMin < b.bit)
  if (mola && siradaki) {
    return {
      tur: 'mola',
      ust: `${Math.max(0, mola.bit - simdiMin)} dk kaldı`,
      baslik: `Mola · ${mola.bit - mola.bas} dk`,
      alt: sirada(siradaki),
      kalanDk: Math.max(0, mola.bit - simdiMin),
      blok: siradaki,
    }
  }
  if (siradaki) {
    return {
      tur: 'bekliyor',
      // "Sırada:" names the one after; this one is now, or the plan's forecast time.
      ust: siradaki.bas > simdiMin ? `Planda ${saatYaz(siradaki, 'bas')}` : 'Şimdi',
      baslik: siradaki.adim || siradaki.baslik,
      alt: sirada(sonrakiCalisma(plan, siradaki)),
      blok: siradaki,
    }
  }
  return { tur: 'bitti', ust: '', baslik: 'Bugünlük bu kadar', alt: '' }
}

/** The minutes a homework's estimate stands at, for the correction field: its normal parts' raw share
 *  (R12: they sum to the estimate before buffer and calibration), 5–120; 20 when nothing is known. */
export function odevTahminDk(p: PlanYaniti, anahtar: string): number {
  const parcalar = p.bloklar.filter(b => b.tur === 'calisma' && b.odev_anahtari === anahtar)
  if (!parcalar.length) return 20
  const ham = parcalar.reduce((t, b) => t + (b.ham_dk > 0 ? b.ham_dk : 0), 0)
  const dk = ham > 0 ? ham : parcalar[0].tahmin_dk
  return Math.max(5, Math.min(120, Math.round(dk)))
}

const kayitlar = (l: PlanKaydi[]) => l.map(odevAdi).join(' · ')

/** "Yarına kaldı: Fen Bilimleri — Proje" — moved, never silently dropped (§6.4). */
export function yarinaKaldiMetni(l: PlanKaydi[]): string {
  return `Yarına kaldı: ${kayitlar(l)}`
}

/** Due tomorrow, so not moved; the plan says so plainly (§6.4). */
export function sigmayanMetni(l: PlanKaydi[]): string {
  return `Bu akşama sığmıyor: ${kayitlar(l)}`
}

/** Older work left out of the plan, still owed: one line pointing at İşler (§6.8). */
export function plandaOlmayanMetni(n: number): string {
  return `Planda olmayan ${n} eski ödev · İşler'de`
}

const DURUM_ADI: Record<BlokDurumu, string> = { bekliyor: '', suruyor: 'Sürüyor', bitti: 'Bitti', ertelendi: 'Ertelendi' }

/** One row of "Bu akşamın tamamı". */
export function blokSatiri(b: PlanBlogu): { saat: string; ad: string; sure: string; durum: string } {
  const saat = `${saatYaz(b, 'bas')}–${saatYaz(b, 'bit')}`
  if (b.tur !== 'calisma') return { saat, ad: b.baslik || (b.tur === 'mola' ? 'Mola' : 'Etkinlik'), sure: '', durum: '' }
  return { saat, ad: adimAdi(b), sure: tahminMetni(b.tahmin_dk), durum: DURUM_ADI[b.durum] ?? '' }
}

// ── reading the answer ──────────────────────────────────────────────────────

const DURUMLAR: PlanDurumu[] = ['plansiz', 'onizleme', 'akis', 'bitti', 'okulsuz', 'kapali']
const sayi = (v: unknown, yedek = 0) => (typeof v === 'number' && Number.isFinite(v) ? v : yedek)
const yazi = (v: unknown) => (typeof v === 'string' ? v : '')
const nesne = (v: unknown): Record<string, unknown> | null =>
  v && typeof v === 'object' && !Array.isArray(v) ? (v as Record<string, unknown>) : null

function blokCoz(v: unknown): PlanBlogu | null {
  const o = nesne(v)
  if (!o || typeof o.id !== 'string' || typeof o.bas !== 'number' || typeof o.bit !== 'number') return null
  const tur = (['calisma', 'mola', 'yemek', 'olay'] as const).find(t => t === o.tur)
  const durum = (['bekliyor', 'suruyor', 'bitti', 'ertelendi'] as const).find(t => t === o.durum) ?? 'bekliyor'
  if (!tur) return null
  return {
    id: o.id, tur, bas: o.bas, bit: o.bit,
    ...(typeof o.bas_saat === 'string' ? { bas_saat: o.bas_saat } : {}),
    ...(typeof o.bit_saat === 'string' ? { bit_saat: o.bit_saat } : {}),
    odev_anahtari: typeof o.odev_anahtari === 'string' ? o.odev_anahtari : null,
    ders: typeof o.ders === 'string' && o.ders ? o.ders : null,
    baslik: yazi(o.baslik), adim: yazi(o.adim),
    parca: sayi(o.parca), parca_sayisi: sayi(o.parca_sayisi, 1), tahmin_dk: sayi(o.tahmin_dk),
    zorluk: yazi(o.zorluk) || 'orta', durum, ham_dk: sayi(o.ham_dk),
  }
}

function kayitCoz(v: unknown): PlanKaydi | null {
  const o = nesne(v)
  if (!o) return null
  return {
    odev_anahtari: yazi(o.odev_anahtari), ders: typeof o.ders === 'string' && o.ders ? o.ders : null,
    baslik: yazi(o.baslik), teslim: yazi(o.teslim), kalan_dk: sayi(o.kalan_dk),
  }
}

const liste = <T>(v: unknown, coz: (x: unknown) => T | null): T[] =>
  Array.isArray(v) ? v.map(coz).filter((x): x is T => x !== null) : []

/** The plan, or null for anything that is not one (the flag's `{"kapali": true}` included). */
export function planCoz(v: unknown): PlanYaniti | null {
  const o = nesne(v)
  const durum = o && DURUMLAR.find(d => d === o.durum)
  if (!o || !durum || !Array.isArray(o.bloklar)) return null
  return {
    gun: yazi(o.gun), durum, bloklar: liste(o.bloklar, blokCoz),
    simdiki: blokCoz(o.simdiki), siradaki: blokCoz(o.siradaki),
    tasinan: liste(o.tasinan, kayitCoz), sigmayan: liste(o.sigmayan, kayitCoz),
    planda_olmayan: Math.max(0, sayi(o.planda_olmayan)),
    haber_metni: typeof o.haber_metni === 'string' && o.haber_metni.trim() ? o.haber_metni : null,
    aksam_yok: o.aksam_yok === true,
  }
}

export interface PlanHatasi {
  tur: 'uyari' | 'hata'
  baslik: string
  alt?: string
}

/** The plan routes' own refusals the reader may see, by status (src/dashboard_api.py, /api/plan/*).
 *  Only these: the app's other handlers answer in English ("Unauthorized", "forbidden", Flask's
 *  "Not Found"), and an expired session must not put that on the card (D3, D4). */
const BILINEN_RETLER: Record<number, readonly string[]> = {
  409: ['Önce süren bloğu bitir.', 'Bu bloğu bir kez erteledin.', 'Süren ya da biten bir blok ertelenemez.'],
  403: ['Bunu yalnız aile değiştirebilir.'],
}

/** What the card says when a touch is refused: one of the plan routes' own Turkish sentences, word for
 *  word, or a calm general one — never the HTTP status or body (D3, D4). */
export function planHataCumlesi(durum: number | null, govde: unknown): PlanHatasi {
  const hata = nesne(govde)?.error
  const cumle = typeof hata === 'string' ? hata.trim() : ''
  if (durum !== null && BILINEN_RETLER[durum]?.includes(cumle)) return { tur: 'uyari', baslik: cumle }
  return { tur: 'hata', baslik: 'Kaydedilemedi', alt: 'Bağlantını kontrol edip yeniden dene.' }
}
