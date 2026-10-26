// Sınav Hazırlığı API'sinin biçimleri (src/sinav_kilavuzu.py, plan Görev 6–7). Model değişirse bu dosya aynı commit'te
// değişir; e2e fikstürleri (tests/e2e/fixtures/hazirlik) modelden üretildiği için sapma e2e'de görünür.

export type DurumTuru = 'kesin' | 'olasi' | 'ulke_geneli' | 'gecti'

export interface SinavDurumu {
  tur: DurumTuru
  senaryo: number | null
  senaryo_sayisi: number
  tarih: string | null
  kalan_gun: number | null
  sinav_id: string | null
  duyuru: string | null
  uyari: null | 'kismen' | 'senaryo_yok'
  anilan: number[]
  duyurulan_konu: number
}

export interface GenelBakis {
  durum: 'hazir' | 'tablo_yok' | 'tablo_eski'
  kaynak: { baslik: string; sayfa: string; meb_guncelleme: string; ogretim_yili: string; donem: number; sinif: number } | null
  yaklasan: { ders: string; anahtar: string; sinav_no: number; durum: SinavDurumu; soru: number | null }[]
  dersler: { ders: string; anahtar: string; kitap_bolumleri: boolean;
             sinavlar: { sinav_no: number; durum: SinavDurumu; soru: number | null }[] }[]
}

export interface KitapYolu {
  kitap: string
  unite: string
  unite_no: number
  unite_ad: string
  cerceve: string
  cerceve_no: number
  konu: string | null
  sayfa: number
  son_sayfa: number
  baglanti: string
}

export type KitapDurumu = 'var' | 'bulunamadi' | 'harita_yok'

export interface MatrisSatiri {
  kod: string
  kisa_ad: string
  metin: string
  sayilar: Record<string, number>
  her_senaryoda: boolean
  kitapta: KitapYolu[]
  kitap_durumu: KitapDurumu
}

export interface Matris {
  senaryolar: number[]
  duyurulan: number | null
  gruplar: { baslik: string; satirlar: MatrisSatiri[] }[]
  toplamlar: Record<string, number>
}

export interface Guncellik { tablo_degisti: boolean; kitap_degisti: boolean }

export interface DersOzeti extends Matris {
  ders: string
  anahtar: string
  sinav_no: number
  tur: 'senaryolu' | 'ulke_geneli'
  not: string | null
  sinavlar: { sinav_no: number; durum: SinavDurumu }[]
  durum: SinavDurumu
  kitap_bolumleri: boolean
  harita_onayli: boolean
  guncellik: Guncellik
}

export type BaslikTuru = 'etkinlik' | 'baglanti' | 'kontrol' | 'tanim' | 'ozet' | 'diger'
export interface Baslik { ad: string; tur: BaslikTuru; amac: string | null; sayfa: number }

export type IsaretDurumu = 'hazirim' | 'tekrar' | null

/** Kılavuz bloğunun kitap yolu: o bölümde ele alınan başlıklar yolun kendisinde, sayfaya göre sıralı (düzeltme 1:
 *  iki konuya bağlı çıktıda konu sınırı kaybolmaz). Ders sayfasının yolları (`KitapYolu`) başlık taşımaz. */
export interface KilavuzYolu extends KitapYolu { basliklar: Baslik[] }

export interface Blok {
  kod: string
  kisa_ad: string
  metin: string
  senaryoda: boolean
  soru: number | null
  aralik: [number, number] | null
  her_senaryoda: boolean
  kitapta: KilavuzYolu[]
  kitap_durumu: KitapDurumu
  okulda: { hafta: string }[]
  odevler: { baslik: string; teslim: string | null }[]
  moduller: { baslik: string; yol: string }[]
  isaret: IsaretDurumu
  /** Başlık düzeyi, sıçramasız: ünite 1, çerçeve 2, blok 3; çerçevesiz blok 2 (U4). */
  duzey: number
}

export interface KilavuzModeli {
  surum: number
  ders: string
  anahtar: string
  sinav_no: number
  durum: SinavDurumu
  kip: 'kesin' | 'olasi' | 'ulke_geneli'
  senaryo: number | null
  duyurulan: number | null
  secilen_duyurulan_degil: boolean
  not: string | null
  ozet: { toplam_soru: number | null; soru_araligi: [number, number] | null; cikti_sayisi: number; her_senaryoda: string[] }
  matris: Matris
  uniteler: { baslik: string; cerceveler: { baslik: string | null; sayfa: number | null; son_sayfa: number | null; bloklar: Blok[] }[] }[]
  dogrulama: { duyurulan_konular: { konu: string; kodlar: string[] }[]; senaryo_disi: string[]; karsiligi_yok: string[];
               duyurunun_saymadigi: string[] } | null
  plan: { gunler: { tarih: string; ciktilar: string[]; genel_tekrar: boolean }[] } | null
  ebeveyn: { cikti_sayisi: number; toplam_soru: number | null; soru_araligi: [number, number] | null; hazirim: number;
             tekrar: number; isaretsiz: number; en_agir: string[]; isaret_sahibi: string | null } | null
  /** İşaretlerin sahibinin gösterim adı (D16; e-posta değil). Kâğıtta işaretlerin kime ait olduğu bununla yazılır. */
  isaret_sahibi: string | null
  kaynaklar: { etiket: string; adres: string }[]
  damgalar: { meb_guncelleme: string; tablo_alindi: string; kitaplar: { baslik: string; baski: string; sha256_kisa: string }[];
              uretim: string }
  guncellik: Guncellik
  kitap_bolumleri: boolean
  harita_onayli: boolean
  yz: { durum: 'kapali' }
  secenekler: { ebeveyn: boolean; isaret: boolean }
  icerik_ozeti: string
}

export interface PdfSecenekleri { ebeveyn: boolean; isaret: boolean }
