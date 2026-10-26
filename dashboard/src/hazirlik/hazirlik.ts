// Sınav Hazırlığı yüzeylerinin saf yardımcıları (plan Görev 9): metinler, adresler, seçenek deposu.
// tests/hazirlik.test.ts sınar; ekran ve kâğıt (KilavuzBelgesi, K11) aynı yardımcıları kullanır.
import { normalizeCourseDisplayName } from '../utils/formatters.ts'
import type { SinavSenaryosu } from '../types'
import type { Baslik, Blok, KilavuzModeli, KitapYolu, PdfSecenekleri, SinavDurumu } from './tipler'

const GUNLU = new Intl.DateTimeFormat('tr-TR', { day: 'numeric', month: 'long', weekday: 'long', timeZone: 'Etc/UTC' })
const GUNSUZ = new Intl.DateTimeFormat('tr-TR', { day: 'numeric', month: 'long', timeZone: 'Etc/UTC' })
const SAYISAL = new Intl.DateTimeFormat('tr-TR', { day: '2-digit', month: '2-digit', year: 'numeric', timeZone: 'Etc/UTC' })

function utc(iso: string): Date {
  const [y, a, g] = iso.slice(0, 10).split('-').map(Number)
  return new Date(Date.UTC(y, a - 1, g))
}

/** "2026-11-03" → "3 Kasım Salı" (gün adıyla) ya da "3 Kasım"; tarih yoksa "tarih yok". Tarih yerel gündür. */
export function tarihMetni(iso: string | null, gunAdi = true): string {
  return iso ? (gunAdi ? GUNLU : GUNSUZ).format(utc(iso)) : 'tarih yok'
}

/** "2026-09-10T17:27" → "10.09.2026". */
export function sayisalTarih(iso: string | null): string {
  return iso ? SAYISAL.format(utc(iso)) : ''
}

export function kalanGunMetni(n: number | null): string | null {
  if (n === null) return null
  if (n === 0) return 'bugün'
  if (n === 1) return 'yarın'
  return `${n} gün`
}

export function sinavAdi(no: number): string {
  return `${no}. yazılı`
}

/** K4, K8: durumun sözü. Olası durum hiçbir zaman tek bir senaryoyu adlandırmaz. */
export function durumEtiketi(d: SinavDurumu): string {
  switch (d.tur) {
    case 'kesin': return `Kesin: ${d.senaryo}. senaryo`
    case 'olasi': return d.senaryo_sayisi > 0 ? `Olası: ${d.senaryo_sayisi} senaryo` : 'Olası'
    case 'ulke_geneli': return 'Ülke geneli'
    case 'gecti': return d.senaryo !== null ? `Geçti · ${d.senaryo}. senaryoydu` : 'Geçti'
  }
}

/** Ders karosunun tek yazılısı (spec §3.1, taslak A): ilk geçmemiş yazılı; hepsi geçtiyse sonuncusu. Tarihsiz yazılı
 *  geçmemiştir. Öteki yazılı ders sayfasında görünür. */
export function enYakinYazili<T extends { durum: SinavDurumu }>(sinavlar: T[]): T | null {
  return sinavlar.find(s => s.durum.tur !== 'gecti') ?? sinavlar[sinavlar.length - 1] ?? null
}

/** Yaklaşan yazılının ikinci satırı: "3 Kasım Salı · 7 soru · 3 konu duyuruldu". */
export function yaklasanAyrinti(d: SinavDurumu, soru: number | null): string {
  const p = [tarihMetni(d.tarih)]
  if (d.tur === 'ulke_geneli') p.push('ülke geneli ortak sınav')
  else if (soru !== null) p.push(`${soru} soru`)
  if (d.duyurulan_konu > 0) p.push(`${d.duyurulan_konu} konu duyuruldu`)
  return p.join(' · ')
}

/** K8: tek sayı yalnız senaryo belliyken; olası kipte senaryolar arası aralık. `secilen`: olası kipte okurun seçtiği
 *  (duyurulmamış) senaryo — tek sayı o senaryoyla nitelenir ("3. senaryoda 2 soru"), "bu senaryo" diye okunmasın. */
export function soruMetni(b: Pick<Blok, 'soru' | 'aralik'>, secilen: number | null = null): string {
  if (b.soru !== null) return secilen !== null ? `${secilen}. senaryoda ${b.soru} soru` : `${b.soru} soru`
  const [a, z] = b.aralik ?? [0, 0]
  return a === z ? `her senaryoda ${a} soru` : `senaryoya göre ${a}–${z} soru`
}

export function sayfaMetni(a: number, b: number): string {
  return a === b ? `s. ${a}` : `s. ${a}–${b}`
}

/** K1: kitap › ünite › içerik çerçevesi › konu, kitaptaki adlarıyla. */
export function kitapYoluMetni(y: KitapYolu): string {
  return [y.kitap, y.unite, y.cerceve, ...(y.konu ? [y.konu] : [])].join(' › ')
}

const AMAC_SINIRI = 70

/** Etkinliğin amacı en çok 70 karakter, sözcük ortasında kesilmez (K6: başlığın kendisi kısaltılmaz). */
export function kisaAmac(amac: string): string {
  const t = amac.trim()
  if (t.length <= AMAC_SINIRI) return t
  const kes = t.slice(0, AMAC_SINIRI)
  const bosluk = kes.lastIndexOf(' ')
  return `${(bosluk > 0 ? kes.slice(0, bosluk) : kes).replace(/[,;:]$/, '')}…`
}

export function baslikMetni(b: Baslik): string {
  return b.amac ? `${b.ad} — ${kisaAmac(b.amac)}` : b.ad
}

export const BASLIK_TURU: Record<Baslik['tur'], string> = {
  etkinlik: 'Etkinlik', baglanti: 'Bağlantı', kontrol: 'Kontrol', tanim: 'Tanım', ozet: 'Özet', diger: 'Alt başlık',
}

/** Bloğun çapası: "FB.7.2.1" → "cikti-FB-7-2-1". */
export function ciktiKimligi(kod: string): string {
  return `cikti-${kod.replace(/[^A-Za-z0-9]+/g, '-')}`
}

export function kilavuzAdresi(anahtar: string, no: number, senaryo: number | null): string {
  return `/hazirlik/${anahtar}/${no}${senaryo !== null ? `?senaryo=${senaryo}` : ''}`
}

function secenekSorgusu(senaryo: number | null, s: PdfSecenekleri): URLSearchParams {
  const q = new URLSearchParams()
  if (senaryo !== null) q.set('senaryo', String(senaryo))
  q.set('ebeveyn', s.ebeveyn ? '1' : '0')
  q.set('isaret', s.isaret ? '1' : '0')
  return q
}

export function modelAdresi(anahtar: string, no: number, senaryo: number | null, s: PdfSecenekleri): string {
  return `/api/hazirlik/${anahtar}/${no}/kilavuz?${secenekSorgusu(senaryo, s)}`
}

export function pdfAdresi(anahtar: string, no: number, senaryo: number | null, s: PdfSecenekleri): string {
  return `/api/hazirlik/${anahtar}/${no}/kilavuz.pdf?${secenekSorgusu(senaryo, s)}`
}

/** Baskı görünümünün model adresi: PDF ile aynı işaretlerle — öğrencinin (D16; A4 önizleme PDF'in birebir
 *  önizlemesidir). Sunucu `isaret_kaynagi`'nı yalnız oturumdaki tam roldeki kişiye açar; sunucu basımında
 *  kilavuz-pdf.mjs bu isteği modelden karşılar. */
export function baskiModelAdresi(anahtar: string, no: number, senaryo: number | null, s: PdfSecenekleri): string {
  return `${modelAdresi(anahtar, no, senaryo, s)}&isaret_kaynagi=ogrenci`
}

/** İndirilen dosyanın adı `Content-Disposition`'dan: önce RFC 5987 `filename*` (UTF-8), yoksa `filename`; ikisi de
 *  yoksa ya da ad yol taşıyorsa genel ad. */
export function indirmeAdi(baslik: string | null): string {
  const yildiz = /filename\*\s*=\s*UTF-8''([^;]+)/i.exec(baslik ?? '')?.[1]
  let ad: string | undefined
  if (yildiz) {
    try { ad = decodeURIComponent(yildiz.trim()) } catch { ad = undefined }
  }
  ad ??= /filename\s*=\s*"?([^";]+)"?/i.exec(baslik ?? '')?.[1]?.trim()
  return ad && !/[\\/]/.test(ad) ? ad : 'kapsam-kilavuzu.pdf'
}

/** PDF penceresinin yardımcı metni: PDF öğrencinin işaretlerini basar (D16). Ad ilgi ekini ünlü uyumuyla alır
 *  ("Işık'ın", "Ayşe'nin", "Doğu'nun", "Bülbül'ün"); ünlüyle bitene kaynaştırma n'si girer. Ad yoksa genel söz. */
export function isaretSahibiMetni(ad: string | null): string {
  const t = (ad ?? '').trim()
  if (!t) return 'Öğrencinin işaretleri'
  const kucuk = t.toLocaleLowerCase('tr-TR')
  const unluler = kucuk.match(/[aeıioöuü]/g)
  const son = unluler ? unluler[unluler.length - 1] : 'e'
  const ek = ({ a: 'ın', ı: 'ın', e: 'in', i: 'in', o: 'un', u: 'un', ö: 'ün', ü: 'ün' } as Record<string, string>)[son]
  const kaynastirma = /[aeıioöuü]$/.test(kucuk) ? 'n' : ''
  return `${t}'${kaynastirma}${ek} işaretleri`
}

/** A4 önizleme (spec §3.3): baskı girişi, aynı seçeneklerle; oturum çereziyle modeli kendisi alır. */
export function baskiAdresi(anahtar: string, no: number, senaryo: number | null, s: PdfSecenekleri): string {
  const q = secenekSorgusu(senaryo, s)
  q.set('ders', anahtar)
  q.set('sinav', String(no))
  return `/baski.html?${q}`
}

export const VARSAYILAN_SECENEKLER: PdfSecenekleri = { ebeveyn: false, isaret: true }

export function secenekAnahtari(email: string): string {
  return `tedy-hazirlik-pdf::${email.toLowerCase()}`
}

/** Son seçim kişi başına hatırlanır (spec §4); bozuk ya da yoksa varsayılan. */
export function secenekleriOku(email: string, depo: Pick<Storage, 'getItem'>): PdfSecenekleri {
  try {
    const v: unknown = JSON.parse(depo.getItem(secenekAnahtari(email)) ?? 'null')
    if (v && typeof v === 'object') {
      const o = v as Record<string, unknown>
      return { ebeveyn: o.ebeveyn === true, isaret: o.isaret !== false }
    }
  } catch { /* bozuk kayıt varsayılana düşer */ }
  return { ...VARSAYILAN_SECENEKLER }
}

export function secenekleriYaz(email: string, s: PdfSecenekleri, depo: Pick<Storage, 'setItem'>): void {
  try { depo.setItem(secenekAnahtari(email), JSON.stringify(s)) } catch { /* depolama kapalı: yalnız bu oturum */ }
}

const ANAHTARLAR: Record<string, string> = {
  'Türkçe': 'turkce', 'Matematik': 'matematik', 'Fen Bilimleri': 'fen-bilimleri', 'Sosyal Bilgiler': 'sosyal-bilgiler',
  'İngilizce': 'ingilizce', 'Din Kültürü': 'din-kulturu',
}

// Alias haritasının kanonik adlarıyla: tablodaki "Din Kültürü" ve sekmedeki "Din Kültürü ve Ahlak" aynı anahtara varır.
const NORMAL_ANAHTARLAR: Record<string, string> = Object.fromEntries(
  Object.entries(ANAHTARLAR).map(([ad, anahtar]) => [normalizeCourseDisplayName(ad), anahtar]))

/** Ders adı → hazırlık anahtarı (src/sinav_senaryo.DERS_ANAHTARLARI'nın eşi); bilinmeyen ad null. Tablonun kanonik adı
 *  ("Din Kültürü") ya da Dersler sekmesinin adı ("Din Kültürü ve Ahlak") olabilir: ikincisi alias haritasından geçer. */
export function dersAnahtari(ders: string | null | undefined): string | null {
  if (!ders) return null
  return ANAHTARLAR[ders] ?? NORMAL_ANAHTARLAR[normalizeCourseDisplayName(ders)] ?? null
}

/** Ebeveyn özetinin cümleleri (spec §4.8): aileye, üçüncü kişiyle. */
export function ebeveynCumleleri(m: KilavuzModeli): string[] {
  const e = m.ebeveyn
  if (!e) return []
  const d = m.durum
  const zaman = d.tarih === null ? 'tarihi henüz belli değil'
    : `${tarihMetni(d.tarih)}${d.kalan_gun === 0 ? ', bugün' : d.kalan_gun !== null ? `, ${d.kalan_gun} gün kaldı` : ''}`
  const c = [`${m.ders} ${sinavAdi(m.sinav_no)}: ${zaman}.`]
  const secilen = m.kip === 'olasi' ? m.senaryo : null
  if (m.kip === 'kesin') c.push(`Okul ${m.senaryo}. senaryoyu duyurdu.`)
  else if (m.kip === 'ulke_geneli') c.push('Sınav ülke genelinde ortak yapılır; MEB senaryo vermedi.')
  else if (secilen !== null) c.push(`Senaryo henüz duyurulmadı; kılavuz seçilen ${secilen}. senaryoya göre.`)
  else c.push('Senaryo henüz duyurulmadı; kılavuz bütün senaryoları kapsar.')
  if (e.toplam_soru !== null && secilen !== null) c.push(`${e.cikti_sayisi} öğrenme çıktısı; ${secilen}. senaryoda toplam ${e.toplam_soru} soru.`)
  else if (e.toplam_soru !== null) c.push(`${e.cikti_sayisi} öğrenme çıktısı, toplam ${e.toplam_soru} soru.`)
  else if (e.soru_araligi) c.push(`${e.cikti_sayisi} öğrenme çıktısı; senaryoya göre ${e.soru_araligi[0]}–${e.soru_araligi[1]} soru.`)
  c.push(`Hazırlık işaretleri: ${e.hazirim} hazır, ${e.tekrar} tekrar, ${e.isaretsiz} işaretsiz.`)
  return c
}

/** Sınavlar kartının Sınav Hazırlığı girişi (spec 2026-10-25 §3.4): adres ve düğme etiketi; dersin kılavuzu yoksa null.
 *  Kesin senaryoda o senaryonun kılavuzu; duyuru yoksa ya da tabloda olmayan senaryo duyurulduysa olası kılavuz
 *  (hiçbir senaryo adrese girmez, K8); ülke genelinde kılavuz yok, o yazılının ders sayfası (`?sinav=N`). */
export function kilavuzGirisi(s: SinavSenaryosu): { href: string; etiket: string } | null {
  const anahtar = dersAnahtari(s.ders)
  if (anahtar === null) return null
  if (s.durum === 'ulke_geneli') return { href: `/hazirlik/${anahtar}?sinav=${s.sinav_no}`, etiket: 'MEB senaryolarını aç' }
  return {
    href: kilavuzAdresi(anahtar, s.sinav_no, s.senaryo),
    etiket: s.senaryo !== null ? `Kapsam kılavuzunu aç (${s.senaryo}. senaryo)` : 'Kapsam kılavuzunu aç',
  }
}
