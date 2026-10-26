# Sınav Kılavuzu Tasarım Kanunu

**Sürüm 1.0 · 2026-10-25**

Bu kanun Sınav Hazırlığı yüzeylerinin — ana sayfa (`/hazirlik`), ders sayfası (`/hazirlik/:ders`), kapsam kılavuzu
ekranı (`/hazirlik/:ders/:sinav`), baskı görünümü (`/baski.html`) ve üretilen A4 PDF — nasıl görüneceğini ve neye
dayanacağını bağlayıcı olarak yazar. Spec: `docs/superpowers/specs/2026-10-25-sinav-hazirligi-design.md` §6.

## 0. Yetki ve öncelik

- Kapsam: yukarıdaki yüzeyler ve onları çizen kod (`dashboard/src/hazirlik/`, `dashboard/src/baski/`,
  `src/sinav_kilavuzu.py`, `src/hazirlik_pdf.py`, `scripts/meb_kitap_haritasi.py`'nin ürettiği haritalar).
- Öncelik: değişmezler D1–D4 → ilkeler İ1–İ9 → **bu kanun** (yalnız kapsamında) → talimatname → yüzey tasarımları
  → bileşen rehberi → `tedy-carbon` → carbon-builder. Çelişen alt metin aynı commit'te düzeltilir ya da §3'e borç
  olarak yazılır.
- Talimatnamenin pano geneli kuralları (S38 başlık düzeni, B41 cümle düzeni, B44 Türkçe adlar, §4.4 Tag sınırları,
  §5.7 durum göstergesi) burada da geçerlidir; K4 ve K7 onları bu yüzeye uygular.

## 1. Maddeler

Kapı sütunundaki her ad gerçek bir testle birebir eşleşir. Henüz yazılmamış testler "(Görev N'de yazılır)" diye
işaretlidir; Görev 15 bu işaretleri depodaki gerçek adlara karşı doğrular.

| # | Madde | Hüküm | Kapı |
|---|---|---|---|
| K1 | Kaynak dürüstlüğü | Kitap başlıkları yalnız kitap haritasından, birebir yazım; sayfa = basılı sayfa; MEB çıktı metni birebir; bulunamayan "Kitapta karşılığı bulunamadı" ("yok" değil). Harita elle düzenlenmez. | `tests/test_pdf_kapilari.py::test_eksik_baslik_katlamayla_aranir` (PDF metni); `tests/test_kitap_haritasi_fen.py` (Görev 5'te yazılır); `tests/test_sinav_kilavuzu.py` (Görev 6'da yazılır) |
| K2 | Hiyerarşi | En çok dört düzey: ünite › içerik çerçevesi › çıktı › bölüm başlıkları. Blok iç sırası sabit: kod + kısa ad, soru (ve "her senaryoda"), MEB metni, Kitapta, Bu bölümde ele alınanlar, okulda, ödev/modül, hazırlık işareti. Senaryoda olmayan çıktı tek satır, soluk. | `dashboard/tests/e2e/hazirlik-kilavuz.spec.ts` "blok iç sırası sabit (K2)" |
| K3 | Tipografi | Carbon üretken tip ölçeği; IBM Plex Sans, kodlar Plex Mono; A4'te kök 14,857 px (body-01 ≈ 9,75 pt), en küçük metin label-01 ≈ 8,4 pt (≥ 7,5 pt). Plex dosyaları depodadır, PDF'e gömülür. | `tests/test_pdf_kapilari.py::test_en_kucuk_punto_kullanilan_yazi_tiplerinden`, `test_pdffonts_gomulu_ve_onek_atilir`, `test_kusurlar_rapordan_okunur` |
| K4 | Renk | Yalnız Carbon belirteçleri; ders rengi yalnız vurgu (karonun üst çizgisi, kılavuz başlığının kenarı). Durum ikon + metin (+ renk): kesin `CheckmarkFilled` + `--cds-support-success`, olası `InformationFilled` + `--cds-support-info`, ülke geneli/geçti düz `--cds-text-secondary`. Tag'de ders aileleri yasak; "her senaryoda" gri Tag. Mor yalnız YZ (Plan 2). Kontrast AA. | `tests/test_pano_tasarim_sistemi.py`; e2e axe + IBM: `hazirlik-kilavuz.spec.ts` "kılavuz ekranı: özet, yan içindekiler, bloklar; axe + IBM sıfır ihlal" |
| K5 | Kâğıt | A4 dikey; kenar 18/16/20 mm; üst bilgi ders · sınav · senaryo, alt bilgi damga + "s. n/N"; başlıktan sonra sayfa kesilmez (yetim başlık yok); bölünen blokta "(devam)"; İçindekiler gerçek sayfa numaralı; karşılaştırma tablosu bölünürse her parçada başlık satırı; ebeveyn özeti tek sayfa; siyah-beyaz baskıda anlam ikon ve metinle korunur. Ayrıntı: aşağıdaki "K5 — A metni". | `tests/test_pdf_kapilari.py::test_yetim_baslik_alt_bilgi_sayilmaz_son_sayfa_yetim_degil`, `test_yetim_baslik_yalniz_baslik_olarak_isaretli_ogeyi_sayar`, `test_yetim_baslik_iki_satira_bolunen_baslik_son_satirlardan_bulunur`, `test_icindekiler_gosterilen_sayfada_baslik_olmali`; üretilen PDF'te `scripts/kilavuz_pdf_kapilari.py` |
| K6 | Eksiksizlik | Kılavuz kısaltılmaz; bir bölümün haritadaki bütün başlıkları yazılır (etkinlikte amaç 70 karakterde kısaltılır, başlığın kendisi kısaltılmaz). | `tests/test_sinav_kilavuzu_belge.py::test_kilavuz_kitapta_ve_bolum_basliklari` (Görev 7'de yazılır) |
| K7 | Dil | Türkçe; ad bildiren başlıklar başlık düzeninde, diğer etiketler cümle düzeninde (panonun S38/B41 kuralı, aile kararı 2026-10-19); MEB terimleri birebir; öğrenciye "sen"; sayılar rakamla; başarı vaadi yok. | `tests/test_pano_talimatname_borclari.py` (kısmen: dilbilgisi elle, bkz. KK-0) |
| K8 | Durum dürüstlüğü | Senaryo duyurulmadıysa hiçbir yüzey tek senaryoyu "bu" diye sunmaz: bloklar "senaryoya göre a–b soru", özet aralık, durum "Olası: N senaryo". Kullanıcının seçtiği senaryo duyurulandan farklıysa bu açıkça yazılır. | `tests/test_sinav_kilavuzu_belge.py::test_kilavuz_olasi_kip_tek_senaryo_sunmaz` (Görev 7'de yazılır); `dashboard/tests/hazirlik.test.ts` "durumEtiketi: dört durum; olası tek senaryo adı taşımaz (K8)" (Görev 9'da yazılır); `hazirlik-kilavuz.spec.ts` "olası kip: tek senaryo sayısı yok (K8)" |
| K9 | YZ ayrımı | Carbon AI etiketi, ayrı başlık, cümle başına sayfa atfı, kapatılabilir; modele kişisel veri gitmez. Plan 1'de YZ bölümü yoktur (`yz.durum = "kapali"`). | Plan 2 |
| K10 | Erişilebilirlik | WCAG 2.2 AA; axe + IBM Equal Access sıfır ihlal; PDF etiketli, yer imli, dil `tr`. | e2e: K4'teki axe + IBM testi; `tests/test_pdf_kapilari.py::test_pdfinfo_etiket_ve_sayfa`, `test_qpdf_dil_ve_yer_imleri` |
| K11 | Ekran–kâğıt eşliği | Ekran ve kâğıt aynı `KilavuzBelgesi` bileşeni, aynı sıra; etkileşimli öğenin durağan karşılığı (işaret onay kutusu → Carbon `Checkbox`/`CheckboxChecked` ikonu; ☐ karakteri Plex'te yok). | `dashboard/tests/e2e/hazirlik-baski.spec.ts` "Paged.js yolu: sayfalar, gerçek İçindekiler numarası, etkileşimsiz kâğıt (K5, K11)" (Görev 13'te yazılır) |
| K12 | Güncellik | Damga (MEB tablosu tarihi, kitap baskısı ve sha256 kısası, üretim tarihi) her sayfada; harita eski bir tabloya göre kurulduysa ya da kitap PDF'i değiştiyse (`--denetle`) "güncel değil" uyarısı. | `tests/test_sinav_kilavuzu.py::test_guncellik_tablo_ve_kitap_degisti` (Görev 6'da yazılır); `tests/test_meb_kitap_haritasi.py::test_denetle_sha256_degisimini_yazar` (Görev 4'te yazılır); `hazirlik-kilavuz.spec.ts` "kitap güncellendi uyarısı (K12)" |

### K5 — A metni (ana yol Paged.js)

A4 dikey; kenar 18/16/20 mm; üst bilgi ders · sınav · senaryo (`string(ustbilgi)`), alt bilgi damga + "s. n/N"
(Paged.js kenar kutuları); kapak sayfasında üst bilgi yok; başlıktan sonra sayfa kesilmez (yetim başlık yok);
bölünen blokta "(devam)" (`data-split-from`); karşılaştırma tablosunda başlık satırı her parçada (Paged.js bölünen
tabloda başlık satırını kendiliğinden yinelemez, bkz. §2 Y5 ve KK-1); İçindekiler gerçek sayfa numaralı
(`target-counter`); ebeveyn özeti tek sayfa; siyah-beyaz baskıda anlam ikon ve metinle korunur.

Yetim başlık denetimi başlığı metinden tahmin etmez: PDF yer imi (Chrome bunu yalnız başlık öğelerinden, h1–h6,
yazar ve gösterdiği sayfayı taşır) başlık işaretidir. Yalnız yer imi olarak işaretli bir başlık, kendi sayfasının son
anlamlı satırlarıyla bitiyorsa ve son sayfada değilse yetimdir; konu adıyla biten düz satırlar (çalışma planı,
duyuru doğrulaması, ebeveyn özeti) kusur sayılmaz.

## 2. Yoklama kaydı (2026-10-25)

Yoklama belgesi (Görev 1, 6 sayfa) `scripts/kilavuz_pdf_kapilari.py` ile iki yoldan basıldı: A = Paged.js, B = düz
Chrome (`--duz`). Basım `ted-dashboard.service`'in ortamıyla koşar (`PATH=.venv/bin:/usr/bin:/bin`, `HOME`;
servis birimi `Environment=PATH=…/.venv/bin:/usr/bin:/bin`); süre duvar saati, bellek `/usr/bin/time %M`.

| Yol | Çıkış | Süre (s) | Bellek | Sayfa | Yazı tipleri | Kusurlar |
|---|---|---|---|---|---|---|
| A Paged.js | 0 | 2.9 | 178 MB | 6 | IBMPlexMono, IBMPlexSans, IBMPlexSans-Light | yok |
| B düz | 0 | 2.7 | 179 MB | 3 | DejaVuSans, IBMPlexSans, IBMPlexSans-Light | yok |

Üç koşunun A süreleri 2.9 / 2.9 / 2.6 s, B süreleri 2.7 / 2.5 / 2.4 s; bellek 178–180 MB. B'deki DejaVu Sans yalnız
Chrome'un üst/alt bilgi şablonundadır (9 metin parçası, 8 pt; gövde Plex'tir).

| Ölçüt | A (Paged.js) | B (düz Chrome) |
|---|---|---|
| Y1 Yazı tipi | geçti: yalnız IBMPlexSans/Mono, hepsi gömülü | geçti: gövde Plex gömülü; DejaVu Sans yalnız üst/alt bilgide (sayılmaz) |
| Y2 İçindekiler | geçti: dört girdi doğru sayfada | beklenmez: sayfa numarası yok |
| Y3 Yetim başlık | geçti: yok (14 yer imi) | geçti: yok |
| Y4 Etiket ve yer imi | geçti: `Tagged: yes`, `/Lang tr`, 14 yer imi | geçti |
| Y5 Tablo bölünmesi | geçti, ama sınanmadı: yoklamadaki tablo bölünmüyor (s. 3'te 24 satır, başlık satırı VAR) | geçti: tablo s. 1–2'ye bölünüyor, ikisinde de başlık satırı VAR |
| Y6 Süre (≤ 20 s) | geçti: 2.6–2.9 s | geçti: 2.4–2.7 s |
| Y7 Bellek (≤ 1 GB) | geçti: 178–180 MB | geçti: 178–179 MB |
| Y8 Servis ortamı | geçti: servis `PATH`'i ve yalnız `HOME` ile çıkış 0 | geçti |

**Y5 sınama ölçümü (yoklama dışı).** Yoklamadaki tablo bir sayfaya sığdığı için Paged.js'in bölünen tablodaki
davranışı yoklamayla görülemez. Yoklama paketinin bir kopyasında tablo 72 satıra çıkarılıp (yalnız `/tmp`, depoya
girmedi) iki yol yeniden basıldı: A'da tablo s. 3–5'e bölündü ve başlık satırı ("Öğrenme çıktısı") yalnız ilk
parçada (s. 3) var; s. 4 ve 5'te yok. B'de tablo s. 1–3'e bölündü ve her parçada başlık satırı VAR. Sonuç: Paged.js
yolu bölünen tabloda başlık satırını yinelemez. Karar kuralı gereği yol değişmez; çare karşılaştırma tablosunu ünite
başına bölünmeyen tablolara ayırmaktır (`kilavuz-matris--unite`, `break-inside: avoid`) ve Görev 13 gerçek modelle
Y5'i yeniden ölçer (KK-1).

**Karar: ana yol A (Paged.js), yedek yol B (düz Chrome).** Y1–Y4 ve Y6–Y8 A'da geçti (Y5 yoklama belgesinde geçti,
bölünen tabloda sınama ölçümü KK-1'e yazıldı). `hazirlik_pdf.ANA_YOL = "paged"`.

## 3. Borçlar ve kararlar

- KK-0: K7'nin dilbilgisi denetimi elle yapılır (otomatik kapı yok).
- KK-1: Paged.js bölünen karşılaştırma tablosunda başlık satırını yinelemez (§2, Y5 sınama ölçümü). Karar (Y5):
  kâğıtta karşılaştırma tablosu koşulsuz ünite başına bölünmeyen tablolardır — `KilavuzBelgesi` `kip="baski"`
  `KarsilastirmaTablosu`'nu `uniteBasina` ile çizer (`kilavuz-matris--unite`, her biri kendi başlık satırıyla);
  ekranda tek tablo. Görev 13 gerçek Fen modeliyle Y5'i yeniden ölçer.
- Yetim başlık kapısı yalnız başlık olarak işaretli (PDF yer imi) öğeleri sayar; aynı sayfada hem işaretli bir
  başlık hem de aynı yazıyla biten düz bir satır varsa ikisi ayırt edilemez ve kapı yanlış alarm verir (kusuru
  kaçırmaz).
- PDF seçenekleri (senaryo, ebeveyn özeti, işaretler) cihazda saklanır (tarayıcı `localStorage`); hesaba bağlı
  değildir, başka cihazda yeniden seçilir.
