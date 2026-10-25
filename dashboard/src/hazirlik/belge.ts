// Kılavuz belgesinin saf yardımcıları (plan Görev 11): bölümler, üst bilgi, damga. Ekran ve kâğıt aynı metni kullanır (K11).
import { sayisalTarih, sinavAdi } from './hazirlik.ts'
import type { Guncellik, KilavuzModeli, Matris } from './tipler.ts'

/** Adlandıran bölüm başlıkları (talimatname S38: başlık düzeninde). İçindekiler ve yan menü aynı adları taşır. */
export const BOLUM = {
  kilavuz: 'Kapsam Kılavuzu', ozet: 'Özet', icindekiler: 'İçindekiler', karsilastirma: 'Senaryo Karşılaştırması',
  dogrulama: 'Duyuru Doğrulaması', plan: 'Çalışma Planı', ebeveyn: 'Ebeveyn Özeti', kaynaklar: 'Kaynaklar',
} as const

/** Kılavuzun bölümleri, sırasıyla (spec §4): çapa kimliği ve adı. */
export function bolumler(m: KilavuzModeli): { id: string; ad: string }[] {
  return [
    ...(m.ebeveyn ? [{ id: 'bolum-ebeveyn', ad: BOLUM.ebeveyn }] : []),
    { id: 'bolum-ozet', ad: BOLUM.ozet },
    ...(m.matris.senaryolar.length ? [{ id: 'bolum-karsilastirma', ad: BOLUM.karsilastirma }] : []),
    ...m.uniteler.map((u, i) => ({ id: `bolum-unite-${i + 1}`, ad: u.baslik })),
    ...(m.dogrulama ? [{ id: 'bolum-dogrulama', ad: BOLUM.dogrulama }] : []),
    ...(m.plan ? [{ id: 'bolum-plan', ad: BOLUM.plan }] : []),
    { id: 'bolum-kaynaklar', ad: BOLUM.kaynaklar },
  ]
}

/** Üst bilgi (K5): ders · sınav · senaryo. Olası kipte tek senaryo "bu" diye yazılmaz (K8). */
export function ustBilgi(m: KilavuzModeli): string {
  const senaryo = m.kip === 'ulke_geneli' ? 'ülke geneli'
    : m.kip === 'kesin' ? `${m.senaryo}. senaryo`
    : m.senaryo !== null ? `${m.senaryo}. senaryo (olası)` : 'bütün senaryolar (olası)'
  return `${m.ders} · ${sinavAdi(m.sinav_no)} · ${senaryo}`
}

/** Damga (K12): her sayfanın alt bilgisi; "TEDY" ile başlar (PDF kapıları alt bilgiyi buradan tanır). */
export function damgaMetni(m: KilavuzModeli): string {
  const kitap = m.damgalar.kitaplar.map(k => `${k.baslik} ${k.baski} (${k.sha256_kisa})`).join(', ') || 'kitap haritası yok'
  return `TEDY · MEB tablosu ${sayisalTarih(m.damgalar.meb_guncelleme)} · ${kitap} · üretim ${sayisalTarih(m.damgalar.uretim)}`
}

export function tumBloklar(m: KilavuzModeli | null) {
  return m ? m.uniteler.flatMap(u => u.cerceveler.flatMap(c => c.bloklar)) : []
}

/** Kâğıtla ekranın ortak uyarıları (K12 güncellik, K1 onay, spec §7 harita yok). */
export function hazirlikUyarilari(g: { guncellik: Guncellik; harita_onayli: boolean; kitap_bolumleri: boolean }): string[] {
  const out: string[] = []
  if (!g.kitap_bolumleri) out.push('Kitap bölümleri henüz eklenmedi; bu dersin MEB metinleri ve senaryoları burada.')
  if (g.guncellik.kitap_degisti) out.push('MEB ders kitabının PDF’i değişti; kitap bölümleri güncel değil, harita yenilenmeli.')
  if (g.guncellik.tablo_degisti) out.push('MEB tablosu kitap haritasından sonra değişti; kitap bölümleri güncel değil, harita yenilenmeli.')
  if (g.kitap_bolumleri && !g.harita_onayli) out.push('Kitap haritası henüz elle onaylanmadı.')
  return out
}

/** Karşılaştırma tablosunun parçası: bir ünite grubu ya da yalnız toplam satırı. */
export interface TabloParcasi { gruplar: Matris['gruplar']; toplam: boolean }

/** Y5: Paged.js bölünen tabloda başlık satırını yinelemez; baskıda tablo ünite başına ayrı tablolar olarak çizilir
 *  (her biri kendi başlık satırıyla), toplam satırı sonda tek başına. Ekranda tek tablo. */
export function tabloParcalari(m: Matris, uniteBasina: boolean): TabloParcasi[] {
  if (!uniteBasina) return [{ gruplar: m.gruplar, toplam: true }]
  return [...m.gruplar.map(g => ({ gruplar: [g], toplam: false })), { gruplar: [], toplam: true }]
}
