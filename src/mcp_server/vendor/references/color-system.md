# İşlevsel Renk Sistemi (color-system.md)

`carbon-edupedia` rengi **işlevsel** kullanır: her renk bir görevi temsil eder, nötr bir
Carbon tuvali üzerinde. Amaç, DEHB-sakin sınırını korurken renkle **odak, buton ve
öğrenme süreçlerini** güçlendirmektir. Kanıt ve gerekçe için `adhd-pedagogy.md` §12.

## 1. Renk rolleri (hepsi `--cds-*`/token tabanlı)

| Rol | Token | Kullanım |
| --- | --- | --- |
| **Kimlik** | `--tedy-brand` (Blue 80) + `--cds-text-on-color` | Yalnız üst kimlik bandı ve Tedy işareti (panoyla aynı). Eylem rengi değildir. |
| **Eylem** | `--cds-button-primary` (Blue 60), `--cds-link-primary`, `--cds-interactive` | Birincil buton, bağlantı, ilerleme göstergesi. Kontrast için **mavi** sabittir (aksan değil). |
| **Ders çapası** | `--accent` / `--accent-tint` / `--accent-strong` | Yalnız Kanun M1.5'in çapaları: kavram yüzeylerinin (`.lead`, merak kartı) 4 px kenarı, vurgulu terimin ve kavram çipinin tint zemini, kavram çipinin ders kenarı, segment ikonunun tint zemini. Hover, seçili ve odak durumları ders rengi almaz (M1.6); şablonda borç KB-17. Büyük yüzey boyamaz. |
| **Durum: başarı** | `--cds-support-success` + `--cds-notification-background-success` (+ metin `--tedy-text-success`) | Doğru yanıt, ustalık, tamamlama. |
| **Durum: bilgi** | `--cds-support-info` + `--cds-notification-background-info` (+ `--tedy-text-info`) | İpucu, "hatırla", nötr geri bildirim. |
| **Durum: uyarı** | `--cds-support-warning` + `--cds-notification-background-warning` (+ `--tedy-text-warning`) | Dikkat çekme (cezalandırıcı değil). |
| **Durum: hata** | `--cds-support-error` + `--cds-notification-background-error` (+ `--tedy-text-error`) | Yalnız yanlış şıkkı **işaretlemek** için; metin daima yapıcı ("tekrar dene"). Kırmızı ders aksanı olmaz. |
| **Kategori** | `--viz-1..5` | Grafik serileri, sıralama/gruplama kategorileri, diyagram parçaları. Anlam renklerinden kaçınan TEDY alt kümesi (§7). |
| **İllüstrasyon** | `--viz-sun/water/cloud` | Doğa/şema anlamsal renkleri. |
| **İlerleme** | `--cds-text-primary` / `--cds-text-secondary`, ray `--cds-interactive` | İlerleme sessiz ve etiketlidir ("Bölüm 3 / 7"). Ödül rolü (`--reward`, `--reward-bg`) 2026-10-11'de kalktı: XP sayacı, seri ve rozet ekranda yok (talimatname S43, B73). |
| **Devre dışı** | `--cds-button-disabled`, `--cds-text-on-color-disabled`, `--cds-text-disabled`, `--cds-icon-disabled`, `--cds-border-disabled` | Carbon'un devre dışı token'ları; durum opaklıkla çizilmez (talimatname S24, B34). Okunacak içerik (çözülmüş adımın cevabı, denenmiş kelime) devre dışı değil salt okunurdur. |
| **Tuval** | `--tedy-page-background` (sayfa), `--cds-layer-01/02/03` | Sayfa zemini Tedy cool-gray; kartlar ve iç yüzeyler Carbon katmanı (nötr, katmanlı derinlik). |

## 2. Beş kural

1. **İşlevle ata, süsleme yapma.** Renk yoksa bir işi temsil etmiyordur → kullanma.
2. **Nötr tuval.** Büyük doygun alan yok; sayfa `--tedy-page-background`, kartlar Carbon layer'ı.
   Tek doygun alan üst bandın Tedy laciverdidir.
3. **Artıklık + CVD.** Renk tek ayırt edici olamaz; metin/ikon/şekil ile birlikte.
4. **Wayfinding.** Etkinlik türünü ikon ve kicker metni taşır; segment ikonu ders renginin tint
   zeminidir, mola nötr. Dolu ders rengi karo yoktur (Kanun M1.4).
5. **Sakinlik.** Bölüm girişinde hareket yok (Kanun M2.10); doygunluk ölçülü; WCAG AA.

## 3. Wayfinding tonu (tek modül, tek renk)
Kanun M1.4 ve M1.5'e göre segment ikon karosu her segmentte ders renginin tint zeminidir;
dolu ders rengi karo ve renkli kicker yoktur. Etkinlik türünü ikon ve kicker metni taşır:

| Segment | `.seg-ic` karo | İkon | `kicker` |
|---|---|---|---|
| Etkileşim ve anlatım (`mcq`, `checkpoint`, `teach`, `chart` …) | `--subject-surface` (Carbon tag zemini) | `--subject-on-surface` | `--cds-text-secondary` |
| Mola (`brainbreak`) | `--cds-layer-accent-01` (nötr) | `--cds-icon-secondary` | `--cds-text-secondary` |

Şablon bugün etkileşim segmentlerinde dolu `--subject-accent` karo (borç KB-16) ve
`--subject-text` kicker (borç KB-17) çizer.

Eski `--seg-accent` eşlemesi (anlatım=info mavisi, mola=başarı yeşili) kaldırıldı: anlam renkleri
kategori olarak kullanılınca "doğru" ve "bilgi" sinyalleri sulanıyordu, açık temada yeşil kicker
3,3:1 ile AA'nın altındaydı. Etkinlik tipi artık ton + ikon + kicker metniyle okunur.

## 4. Derse göre kimlik (Tedy ders renk sistemi)
Ders rengi `meta.subject`'ten türetilir ve Tedy'nin her yüzeyinde (modül ve pano) aynıdır; emekli
katalog sitesi artık bir yüzey değildir, panonun Modüller listesi dersi metinle gösterir.
Tek kaynak `assets/carbon-v11-authority.json` → `tedyLayer.subjectThemes`; kurallar ve tablo
`tedy-integration.md` §3'tedir. Özet: Türkçe ve edebiyat **magenta**, matematik **mor**, fen **teal**,
sosyal bilimler **camgöbeği**, yabancı diller **mavi**, din ve değerler **sıcak gri**, bilişim
**soğuk gri**, sanat-spor ve genel **gri**. Rolleri Carbon Tag token'ları ve palet adımları verir;
tema değişince CSS kendiliğinden geçer (JavaScript renk hesabı yok). Kırmızı, yeşil, sarı ve
turuncu anlam renkleridir, ders rengi olamaz; Carbon'un uyarı paleti de aynı anlamları taşır
(kırmızı hata, turuncu ciddi uyarı, sarı uyarı, yeşil başarı:
https://carbondesignsystem.com/building-blocks/data-visualization/color-palettes/#alert-palette).
Üst bant Tedy laciverdidir; modülde **butonlar ve ilerleme göstergesi Carbon mavisi kalır**;
istisnası yoktur (S35, Kanun M1.6).
Otorite aile ve mod başına 9 rol taşır; `panel` ve `panelBorder` yalnız panonun tek büyük ders
yüzeyi içindir (İ8), şablon 7 rol üretir.

## 5. Kontrast ve doğrulama
- Küçük metin daima `--cds-text-primary`/`secondary`; aksan büyük/dolgu/çizgi öğelerinde.
- Notification yüzeyleri düşük-kontrast token'dır; üzerine `text-primary`.
- `validate_module.py`: **G-CONTRAST** (metin token'ı), **G-CARBON** (token kullanımı),
  **G-SVG** (figürlerde token renk), **G-TOKEN** (g10 · white · g100 otoritesi). Renk asla
  emoji/animasyonla telafi edilmez.

## 6. Tedy ile bütünlük
Tema, kimlik bandı, köşe, gölge ve oyunlaştırma kuralları: `tedy-integration.md`. Tasarım
kararında TEDY Modül Tasarım Kanunu (`edupedia_rehber('kanun')`) önceliklidir.

## 7. Veri görselleştirme renkleri (`--viz`)

- **Ne oldukları (2026-10-15'ten beri).** `--viz-1..5` bir **nötr gri rampadır** ve kategori
  taşıyıcısı **değildir** (S19): açık temada gray100 · gray90 · gray80 · gray70 · gray60, g100'de
  gray10 · gray20 · gray30 · gray40 · gray50. Kategoriyi yazı taşır — grafikte her çubuğun/noktanın
  yanındaki yerinde etiket, dilbilgisi çözümlemesinde alt çizginin biçimi.
  **Neden renk değil:** ders aileleri ders işaretine, kırmızı/yeşil/sarı/turuncu anlama ayrılmıştır
  (İ8); ikisini çıkarınca kategorik palete yedek hue kalmaz. Önceki beş yuva
  (purple70 · blue80 · cyan50 · teal70 · magenta70 ve g100'de aynı ailelerin 40 adımı) tam olarak
  ders aileleriydi, yani grafik kategorisi ile ders işareti aynı görünüme düşüyordu (§7.5 P5).
  Her yuva kendi temasının `--cds-layer-01` zeminine karşı ≥ 3:1 taşır; kapı
  `test_s19_viz_zemine_karsi_3_1`.
- **Sıra.** Seriler `--viz-1`'den başlayarak sırayla atanır; sıra keyfi değiştirilmez. Tek seri
  `--viz-1` kullanır. 5 seriyi aşan veri doğrudan etiket ya da desenle ayrışır; anlam renkleri
  hiçbir zaman seri rengi olmaz. Grafik verisinde `color` yazılmaz (Kanun M4.7; şablon ve G-SVG
  bugün kabul ediyor: borç KB-25).
- **Lejant.** Tek veri kategorisinde lejant yoktur; mümkünse veri doğrudan etiketlenir
  (https://carbondesignsystem.com/building-blocks/data-visualization/legends/#usage).
- **Eksik veri.** Enterpolasyon ve sıfır yok; boşluğun başı ve sonu etiketlenir
  (https://carbondesignsystem.com/building-blocks/data-visualization/axes-and-labels/#gaps-in-data).
  Motor `vizChart` eksik değeri bugün 0 çizer — açık madde (B52); yazar eksik noktayı veriye koymaz.
- **Kontrast.** Grafik öğesi ve bilgi taşıyan SVG parçası zemine karşı ≥ 3:1
  (https://carbondesignsystem.com/building-blocks/foundations/color/overview/#contrast-ratios).
  Açık temada `--viz-sun` (1,68:1) ve `--viz-cloud` (1,70:1) bunu geçemez; dolgu olarak
  kullanıldıklarında 3:1'i geçen kontur ya da etiket eşlik eder — açık madde.
- **İkon rengi.** İkon komşu metnin rengini taşır, tek renktir ve 4,5:1 sağlar
  (https://carbondesignsystem.com/building-blocks/foundations/icons/guidelines/#color).

Ayrıntı: `carbon-excellence.md` §2.7 ve §2.9; kanonik kılavuz `docs/tedy-ui-ux-talimatnamesi.md` §8–§9.
