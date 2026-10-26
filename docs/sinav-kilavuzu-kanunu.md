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
| K1 | Kaynak dürüstlüğü | Kitap başlıkları yalnız kitap haritasından, birebir yazım; sayfa = basılı sayfa; MEB çıktı metni birebir; bulunamayan "Kitapta karşılığı bulunamadı" ("yok" değil). Harita elle düzenlenmez. | `tests/test_pdf_kapilari.py::test_eksik_baslik_katlamayla_aranir`, `test_eksik_baslik_icindekiler_sayfasini_saymaz`, `test_denetle_k1_aramasi_okuma_sirasindaki_metinde` (PDF metni, İçindekiler sayfası hariç); `tests/test_kitap_haritasi_fen.py` (Görev 5'te yazılır); `tests/test_sinav_kilavuzu.py` (Görev 6'da yazılır) |
| K2 | Hiyerarşi | En çok dört düzey: ünite › içerik çerçevesi › çıktı › bölüm başlıkları. Blok iç sırası sabit: kod + kısa ad, soru (ve "her senaryoda"), MEB metni, Kitapta, Bu bölümde ele alınanlar, okulda, ödev/modül, hazırlık işareti. Senaryoda olmayan çıktı tek satır, soluk. | `dashboard/tests/e2e/hazirlik-kilavuz.spec.ts` "blok iç sırası sabit (K2)" |
| K3 | Tipografi | Carbon üretken tip ölçeği; IBM Plex Sans, kodlar Plex Mono; A4'te kök 14,857 px (body-01 ≈ 9,75 pt), en küçük metin label-01 ≈ 8,4 pt (≥ 7,5 pt). Plex dosyaları depodadır, PDF'e gömülür. | `tests/test_pdf_kapilari.py::test_en_kucuk_punto_kullanilan_yazi_tiplerinden`, `test_pdffonts_gomulu_ve_onek_atilir`, `test_kusurlar_rapordan_okunur`, `test_kusurlar_olculemeyen_deger_gecer_sayilmaz`, `test_yabanci_yazi_tipi_kenarda_izinli_olan_yalniz_ust_alt_bilgide`; sunucu basımında kapı bekçisi: `tests/test_hazirlik_pdf.py::test_kapi_bekcisi_kusurlu_basimi_dusurur`, `test_bekci_ana_yolu_dusurur_duz_denenir_o_da_kusurluysa_uretilemedi`, `test_kapi_bekcisi_uzun_metinli_fikstur_gercek_basim_temiz`, `test_kapi_bekcisi_sigmayan_parcayi_yakalar_duz_yol_basar` |
| K4 | Renk | Yalnız Carbon belirteçleri; ders rengi yalnız vurgu (karonun üst çizgisi, kılavuz başlığının kenarı). Durum ikon + metin (+ renk): kesin `CheckmarkFilled` + `--cds-support-success`, olası `InformationFilled` + `--cds-support-info`, ülke geneli/geçti düz `--cds-text-secondary`. Tag'de ders aileleri yasak; "her senaryoda" gri Tag. Mor yalnız YZ (Plan 2). Kontrast AA. | `tests/test_pano_tasarim_sistemi.py`; e2e axe + IBM: `hazirlik-kilavuz.spec.ts` "kılavuz ekranı: özet, yan içindekiler, bloklar; axe + IBM sıfır ihlal" |
| K5 | Kâğıt | A4 dikey; kenar 18/16/20 mm; üst bilgi ders · sınav · senaryo, alt bilgi damga + "s. n/N"; başlıktan sonra sayfa kesilmez (yetim başlık yok); bölünen blokta "(devam)"; İçindekiler gerçek sayfa numaralı; karşılaştırma tablosu bölünürse her parçada başlık satırı; ebeveyn özeti tek sayfa; siyah-beyaz baskıda anlam ikon ve metinle korunur. Ayrıntı: aşağıdaki "K5 — A metni". | Üretilen PDF'te `scripts/kilavuz_pdf_kapilari.py` (`pdf_kapilari.denetle` + `kusurlar`) şunları ölçer: her sayfanın alt bilgisinde damga ("TEDY") ve doğru "s. n/N" (`test_alt_bilgi_her_sayfada_damga_ve_dogru_sayfa_numarasi`); kapakta üst bilgi yok, öbür her sayfada (ebeveyn özetli basımda 1. sayfa dahil) dolu (`test_ust_bilgi_kapakta_yok_diger_her_sayfada_dolu`); İçindekiler'in `bolumler(m)` ile aynı her girdisi gösterdiği sayfada (`test_icindekiler_gosterilen_sayfada_baslik_olmali`, `test_icindekiler_girdisi_tam_satirla_ve_sayfadaki_karsiligiyla`); yer imi olarak işaretli başlık sayfa sonunda yetim değil (`test_yetim_baslik_alt_bilgi_sayilmaz_son_sayfa_yetim_degil`, `test_yetim_baslik_yalniz_baslik_olarak_isaretli_ogeyi_sayar`, `test_yetim_baslik_iki_satira_bolunen_baslik_son_satirlardan_bulunur`). Baskı görünümünde `dashboard/tests/e2e/hazirlik-baski.spec.ts` "Paged.js yolu: sayfalar, gerçek İçindekiler numarası, etkileşimsiz kâğıt (K5, K11)": İçindekiler numarası (`::after` counter-reset) hedef başlığın sayfası, bölünen blokta `::before` "(devam)", kâğıtta içerikte damga yok, "Kitapta" kutusu gray-10. `dashboard/tests/baski-kagit-kurallari.test.ts`: iki kâğıt kopyasında @page boyutu/kenarı ve kesme kuralları eşit (D17); `dashboard/tests/hazirlik-belge.test.ts` "tablo parçaları: uzun ünite kâğıtta sayfaya sığan parçalara bölünür, her parça kendi başlık satırıyla (Y5, KK-1)". Makineyle denetlenmeyenler: kenar ölçüleri (yalnız CSS eşitliği), ebeveyn özetinin tek sayfa olduğu, siyah-beyaz okunurluk ve tablo parçalarında başlık satırının basılı varlığı (Görev 13'te elle ölçüldü) |
| K6 | Eksiksizlik | Kılavuz kısaltılmaz; bir bölümün haritadaki bütün başlıkları yazılır (etkinlikte amaç 70 karakterde kısaltılır, başlığın kendisi kısaltılmaz). | `tests/test_sinav_kilavuzu_belge.py::test_kilavuz_kitapta_ve_bolum_basliklari` (Görev 7'de yazılır) |
| K7 | Dil | Türkçe; ad bildiren başlıklar başlık düzeninde, diğer etiketler cümle düzeninde (panonun S38/B41 kuralı, aile kararı 2026-10-19); MEB terimleri birebir; öğrenciye "sen"; sayılar rakamla; başarı vaadi yok. | `tests/test_pano_talimatname_borclari.py` (kısmen: dilbilgisi elle, bkz. KK-0) |
| K8 | Durum dürüstlüğü | Senaryo duyurulmadıysa hiçbir yüzey tek senaryoyu "bu" diye sunmaz: bloklar "senaryoya göre a–b soru", özet aralık, durum "Olası: N senaryo". Kullanıcının seçtiği senaryo duyurulandan farklıysa bu açıkça yazılır. | `tests/test_sinav_kilavuzu_belge.py::test_kilavuz_olasi_kip_tek_senaryo_sunmaz` (Görev 7'de yazılır); `dashboard/tests/hazirlik.test.ts` "durumEtiketi: dört durum; olası tek senaryo adı taşımaz (K8)" (Görev 9'da yazılır); `hazirlik-kilavuz.spec.ts` "olası kip: tek senaryo sayısı yok (K8)" |
| K9 | YZ ayrımı | Carbon AI etiketi, ayrı başlık, cümle başına sayfa atfı, kapatılabilir; modele kişisel veri gitmez. Plan 1'de YZ bölümü yoktur (`yz.durum = "kapali"`). | Plan 2 |
| K10 | Erişilebilirlik | WCAG 2.2 AA; axe + IBM Equal Access sıfır ihlal; PDF etiketli, yer imli, dil `tr`. | e2e: K4'teki axe + IBM testi; `tests/test_pdf_kapilari.py::test_pdfinfo_etiket_ve_sayfa`, `test_qpdf_dil_ve_yer_imleri` |
| K11 | Ekran–kâğıt eşliği | Ekran ve kâğıt aynı `KilavuzBelgesi` bileşeni, aynı sıra; etkileşimli öğenin durağan karşılığı (işaret onay kutusu → Carbon `Checkbox`/`CheckboxChecked` ikonu; ☐ karakteri Plex'te yok). | `dashboard/tests/e2e/hazirlik-baski.spec.ts` "Paged.js yolu: sayfalar, gerçek İçindekiler numarası, etkileşimsiz kâğıt (K5, K11)" |
| K12 | Güncellik | Damga (MEB tablosu tarihi, kitap baskısı ve sha256 kısası, üretim tarihi) her sayfada; harita eski bir tabloya göre kurulduysa ya da kitap PDF'i değiştiyse (`--denetle`) "güncel değil" uyarısı. | `tests/test_sinav_kilavuzu.py::test_guncellik_tablo_ve_kitap_degisti` (Görev 6'da yazılır); `tests/test_meb_kitap_haritasi.py::test_denetle_sha256_degisimini_yazar` (Görev 4'te yazılır); `hazirlik-kilavuz.spec.ts` "kitap güncellendi uyarısı (K12)" |

### K5 — A metni (ana yol Paged.js)

A4 dikey; kenar 18/16/20 mm; üst bilgi ders · sınav · senaryo (`string(ustbilgi)`), alt bilgi damga + "s. n/N"
(Paged.js kenar kutuları); ikisinin kaynağı ilk bölümün başındaki görünmez `.kilavuz-kagit-bilgi` öğesidir (ebeveyn
özeti sayfası da dolu); kapak sayfasında üst bilgi yok; başlıktan sonra sayfa kesilmez (yetim başlık yok: h2–h5,
blok kodundan sonraki soru satırı, "Kitapta" ve "Bu bölümde ele alınanlar" etiketleri `break-after: avoid`; işaret
satırı önceki satırla gider); bölünen blokta "(devam)" (`data-split-from`; Paged.js'in kendi kuralı bölünen öğenin
`::before`'unu daha özgül bir seçiciyle sildiği için `!important`); kâğıtta blok düz akıştır (grid değil), kod
satırı ile soru satırı alt alta; karşılaştırma tablosu ünite başına ayrı, bölünmez tablolardır, ünite 8 satırdan
uzunsa sayfaya sığan parçalara ayrılır ve her parça kendi başlık satırını taşır (Paged.js bölünen tabloda başlık
satırını kendiliğinden yinelemez, bkz. §2 Y5 ve KK-1); İçindekiler gerçek sayfa numaralı (`target-counter`); ebeveyn
özeti tek sayfa; siyah-beyaz baskıda anlam ikon ve metinle korunur. Kâğıt kuralları iki kopyadır (`sayfa.css`
Paged.js'e, `baski.scss` düz yola); eşitliklerini `baski-kagit-kurallari.test.ts` sınar.

Yetim başlık denetimi başlığı metinden tahmin etmez: PDF yer imi (Chrome bunu yalnız başlık öğelerinden, h1–h6,
yazar ve gösterdiği sayfayı taşır) başlık işaretidir. Yalnız yer imi olarak işaretli bir başlık, kendi sayfasının son
anlamlı satırlarıyla bitiyorsa ve son sayfada değilse yetimdir; konu adıyla biten düz satırlar (çalışma planı,
duyuru doğrulaması, ebeveyn özeti) kusur sayılmaz.

## 2. Yoklama kaydı (2026-10-25)

Yoklama belgesi (Görev 1, 6 sayfa) `scripts/kilavuz_pdf_kapilari.py` ile iki yoldan basıldı: A = Paged.js, B = düz
Chrome (`--duz`). Basım `ted-dashboard.service`'in ortamıyla koşar (`PATH=.venv/bin:/usr/bin:/bin`, `HOME`;
servis birimi `Environment=PATH=…/.venv/bin:/usr/bin:/bin`); süre duvar saati, bellek `/usr/bin/time %M` — bekleyen süreç ağacındaki en büyük TEK sürecin (node ya da Chrome
süreçlerinden biri) tepe RSS'i; süreçlerin toplamı değildir (Y7 bu sayıyla okunur).

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

### Gerçek model kaydı (Görev 13, 2026-10-26)

Yoklama belgesi kalktı; baskı görünümü `KilavuzBelgesi`'ni (`kip="baski"`) API modeliyle çizer. Kapılar
`dashboard/tests/e2e/fixtures/hazirlik/fen-bilimleri-1-kilavuz.json` (gerçek Fen 7-1 haritasından üretilmiş model)
ile koşuldu; basım ortamı servisinkine `TZ=Europe/Istanbul` eklenerek.

| Yol | Çıkış | Süre (s) | Bellek | Sayfa | Yazı tipleri | Kusurlar |
|---|---|---|---|---|---|---|
| A Paged.js | 0 | 2.1–3.2 | 177–179 MB | 7 | IBMPlexMono, IBMPlexMono-SmBld, IBMPlexSans, IBMPlexSans-SmBld | yok |
| B düz | 0 | 1.7–2.9 | 176–179 MB | 5 | DejaVuSans (yalnız üst/alt bilgi), IBMPlexMono, IBMPlexMono-SmBld, IBMPlexSans, IBMPlexSans-SmBld | yok |

Süreler makine yükü düşükken; yedekleme koşarken (yük ortalaması 13) A 5.0–5.9 s, B 4.2–5.3 s. Ebeveyn özetli
basım (A) 8 sayfa, kusur yok; ebeveyn sayfasında üst bilgi ve damga dolu. A: `Tagged: yes`, `/Lang tr`, 15 yer imi,
İçindekiler'in yedi girdisi de gösterdiği sayfada (kapı dördünü denetler, üçü elle okundu); gerçek modelde üç blok sayfa arasında bölünüyor ve üçünde de
"(devam)" var.

## 3. Borçlar ve kararlar

- KK-0: K7'nin dilbilgisi denetimi elle yapılır (otomatik kapı yok).
- KK-1: Paged.js bölünen karşılaştırma tablosunda başlık satırını yinelemez (§2, Y5 sınama ölçümü). Karar (Y5):
  kâğıtta karşılaştırma tablosu koşulsuz ünite başına bölünmeyen tablolardır — `KilavuzBelgesi` `kip="baski"`
  `KarsilastirmaTablosu`'nu `uniteBasina` ile çizer (`kilavuz-matris--unite`, her biri kendi başlık satırıyla);
  ekranda tek tablo. **Görev 13 ölçümü (2026-10-26):** gerçek Fen modelinde (ünite başına 4 ve 2 satır) üç tablo da
  s. 3'te bölünmeden, her biri başlık satırıyla. Yapay ünitelerde bölünmez tablo yetmedi: 12 satırlık ünite tablosu
  A4 gövdesinden (979 px) 24 px uzundu, Paged.js sayfayı taşırdı ve Chrome bütün belgeyi küçülttü (en küçük punto
  5 — punto kapısı yakaladı); 40 satırlık ünitede s. 3 boş kaldı, tablo dört sayfaya başlık satırı kimi parçada var
  kimi parçada yok bölündü (İçindekiler kapısı yakaladı). MEB tablosunda bir dersin bir ünitesinde 11 çıktı var
  (Türkçe `T.O.7`). Çare (`belge.tabloParcalari`): ünite en çok 8 satırlık parçalara ayrılır, sonraki parçaların
  grup satırı "<ünite> (devam)", her parça kendi başlık satırıyla ve bölünmez; sabit tablo düzeni sütunları
  parçalar arasında hizalar. Yeniden ölçüm: 12 satır → 8 + 4, 40 satır → 5 × 8; tablo satırı taşıyan her sayfada
  başlık satırı VAR, kapılar temiz. Sınır: tek satırı yarım sayfadan uzun (8 satır × 3 satırlık metin ≈ gövde) bir
  parça yine sığmayabilir; ölçülen en uzun MEB metni 2 satırdır.
- Yetim başlık kapısı yalnız başlık olarak işaretli (PDF yer imi) öğeleri sayar ve başlığın sayfanın son anlamlı
  satırlarıyla bitip bitmediğine metinden bakar. Ölçüm (Görev 13): gerçek Fen modeliyle basılan belgeye bilerek
  iki yetim yerleştirildi (dist kopyasında `#baslik-unite-2` ve `#cikti-FB-7-1-5 > .kilavuz-blok__ust` için
  `break-after: page`); kapı ikisini de buldu ("yetim başlık s. 5: FB.7.1.5", "s. 6: 2. Ünite · Kuvvet ve Enerjiyi
  Keşfedelim"), yerleştirilmemiş belgede sıfır. Görünmez önek ("Öğrenme Çıktısı ") Chrome'un yer imine girmez
  (ölçüldü: yer imi "FB.7.1.1"); çerçeve yer imi görünen " · s. 15–33"ü taşır, metinle aynı. Sınırlar: (1) aynı
  sayfada hem işaretli bir başlık hem de aynı yazıyla biten düz bir satır varsa ikisi ayırt edilemez, kapı yanlış
  alarm verir; (2) başlıkla aynı satırda sağda başka metin varsa (eski ızgara düzeninde blok kodunun yanındaki
  "2 soru") satır başlıkla bitmez ve yetim kaçabilir — bu yüzden kâğıtta kod satırı yalnız başlığı taşır. Kapı
  yerleştirilmiş iki yetimi buldu; her yetimi bulacağı kanıtlanmış değildir.
- K1 başlık araması (`eksik_basliklar`) `pdftotext`'in okuma sırasındaki metninde yapılır: `-layout` kırılan bir
  satırın arasına sağ sütunu sokar (ölçüldü: "… Teknoloji ile Uzay / s. 24–33 / Araştırmaları Arasındaki İlişki"
  yanlış "başlık PDF metninde yok" verdi). İçindekiler sayfası aranmaz: ünite başlığı orada geçer, gövdede yoksa yine eksiktir.
- İçindekiler kapısı panonun `bolumler(m)` listesinin yedi girdisini de denetler (Görev 13 düzeltme turu; önce dördü);
  girdi satırla birebir eşleşir ("Özet" "Ebeveyn Özeti"ni almaz), Özet'in sayfasında "Kapsam Kılavuzu" aranır.
- Kapılarda ölçülemeyen değer kusurdur: sayfa sayısı 0, boş `pdffonts`, okunamayan punto; araç zaman aşımı
  "denetlenemedi" diye yazılır. Düz yolda (B) DejaVu Sans yalnız üst/alt bilgi kenar boşluğundaysa sayılmaz (borç
  KK-3); gövde metni DejaVu'ya düşerse kusurdur.
- PDF seçenekleri (senaryo, ebeveyn özeti, işaretler) cihazda saklanır (tarayıcı `localStorage`); hesaba bağlı
  değildir, başka cihazda yeniden seçilir.
- Sunucu basımı (Görev 14, `src/hazirlik_pdf.py`): iki yuva (`flock`); bütçe Cloudflare tünelinin ~100 sn kenar
  sınırının altında: ana yol A 40 sn, düz yol B 30 sn, her biri basım + 8 sn kapı denetimi (gerçek Fen basımı +
  denetim 4,4 sn). A düşerse B, ikisi de düşerse 503 + Türkçe cümle; yuva doluysa beklemeden 429. Zaman aşımında
  Node'un bütün soy ağacı öldürülür: Playwright Chrome'u ayrı süreç grubunda başlatır (D6). Ölçüm (2026-10-26): hazır
  sinyali hiç gelmeyen bir sayfada Chrome 8 süreçle canlıyken 4 sn'de öldürüldü, artık süreç kalmadı. Basım ortamının
  `TMPDIR`'ı koşunun geçici dizinidir: Chrome profili zorla öldürmede /tmp'ye sızmaz.
- **Kapı bekçisi** (düzeltme turu 1): sunucu her basımı bu kanunun kapılarının hepsinden geçirir
  (`pdf_kapilari.denetle` + `kusurlar`: yetim, İçindekiler, K1, alt/üst bilgi, yazı tipi, punto; başlıklar ve
  İçindekiler girdileri modelden, `pdf_kapilari.model_basliklari` — betikle aynı işlev). Kusurlu ya da denetlenemeyen
  yol düşer. Ölçüm: 8 satırlık parçalarla uzun metin Chrome'u küçültmüyor (8 × 170 karakter — en uzun MEB metni — ve
  8 × 200 temiz). 8 × 205+ karakterde parça gövdeye sığmaz, s. 3 boş kalır, İçindekiler numarası kayar: bekçi A'yı
  düşürür ("İçindekiler s. 3 diyor, başlık o sayfada yok"), B sunulur (gerçek basımla sınandı). Tek satırı bir
  sayfadan uzun (6.000 karakter) tabloda Paged.js içerik düşürür; K1 kapısı yakalar.
- A4 önizleme PDF'in birebir önizlemesidir: baskı görünümü modeli PDF ile aynı işaretlerle (öğrencinin, D16)
  `?isaret_kaynagi=ogrenci` ile ister; parametre yalnız oturumdaki tam roldeki kişiye açıktır (API anahtarı 403,
  okuyucu default-deny) ve yalnız okur. PDF ucu da aynı nedenle API anahtarına kapalıdır.
