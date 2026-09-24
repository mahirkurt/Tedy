# İşlevsel Renk Sistemi (color-system.md)

`carbon-edupedia` rengi **işlevsel** kullanır: her renk bir görevi temsil eder, nötr bir
Carbon tuvali üzerinde. Amaç, DEHB-sakin sınırını korurken renkle **odak, buton ve
öğrenme süreçlerini** güçlendirmektir. Kanıt ve gerekçe için `adhd-pedagogy.md` §12.

## 1. Renk rolleri (hepsi `--cds-*`/token tabanlı)

| Rol | Token | Kullanım |
| --- | --- | --- |
| **Kimlik** | `--tedy-brand` (Blue 80) + `--cds-text-on-color` | Yalnız üst kimlik bandı ve Tedy işareti (panoyla aynı). Eylem rengi değildir. |
| **Eylem** | `--cds-button-primary` (Blue 60), `--cds-link-primary`, `--cds-interactive` | Birincil buton, bağlantı, ilerleme göstergesi. Kontrast için **mavi** sabittir (aksan değil). |
| **Odak çıpası** | `--accent` / `--accent-tint` / `--accent-strong` | Seçili/hover şık, bölüm ikonu, bölüm başlığı çizgisi, anlatım kutusu sol çizgisi — "buraya bak" sinyali. Derse göre değişir; büyük yüzey boyamaz. |
| **Durum: başarı** | `--cds-support-success` + `--cds-notification-background-success` (+ metin `--tedy-text-success`) | Doğru yanıt, ustalık, tamamlama. |
| **Durum: bilgi** | `--cds-support-info` + `--cds-notification-background-info` (+ `--tedy-text-info`) | İpucu, "hatırla", nötr geri bildirim. |
| **Durum: uyarı** | `--cds-support-warning` + `--cds-notification-background-warning` (+ `--tedy-text-warning`) | Dikkat çekme (cezalandırıcı değil). |
| **Durum: hata** | `--cds-support-error` + `--cds-notification-background-error` (+ `--tedy-text-error`) | Yalnız yanlış şıkkı **işaretlemek** için; metin daima yapıcı ("tekrar dene"). Kırmızı ders aksanı olmaz. |
| **Kategori** | `--viz-1..5` | Grafik serileri, sıralama/gruplama kategorileri, diyagram parçaları. |
| **İllüstrasyon** | `--viz-sun/water/cloud` | Doğa/şema anlamsal renkleri. |
| **İlerleme/ödül** | `--reward` (= `--tedy-text-warning`) + `--reward-bg` (= `notification-background-warning`) | XP, seri — sakin sıcak vurgu; ham altın hex yok. Kazanılan rozet nötr `layer-selected-01`. |
| **Tuval** | `--tedy-page-background` (sayfa), `--cds-layer-01/02/03` | Sayfa zemini Tedy cool-gray; kartlar ve iç yüzeyler Carbon katmanı (nötr, katmanlı derinlik). |

## 2. Beş kural

1. **İşlevle ata, süsleme yapma.** Renk yoksa bir işi temsil etmiyordur → kullanma.
2. **Nötr tuval.** Büyük doygun alan yok; sayfa `--tedy-page-background`, kartlar Carbon layer'ı.
   Tek doygun alan üst bandın Tedy laciverdidir.
3. **Artıklık + CVD.** Renk tek ayırt edici olamaz; metin/ikon/şekil ile birlikte.
4. **Wayfinding tonu.** Etkinlik türü renk ailesiyle değil, dersin kendi ailesinin tonuyla
   imlenir: "senin sıran" segmentleri dolu aksan karo, anlatım/veri tag karosu, mola nötr.
5. **Sakinlik.** Tek, `prefers-reduced-motion` ile kapalı giriş; doygunluk ölçülü; WCAG AA.

## 3. Wayfinding tonu (tek modül, tek renk)
Motor, `.stage[data-seg="…"]` üzerinde bölüm ikon karosunun tonunu seçer; renk ailesi her
segmentte dersin ailesidir:

| Segment | `.seg-ic` karo | İkon | `kicker` |
|---|---|---|---|
| Etkileşim ("senin sıran": `mcq`, `checkpoint`, `fillblank`, `match`, `order`, `sorting`, `hotspot`, `conceptMap`, `flashcards`) | `--subject-accent` (dolu) | `--subject-on-accent` | `--subject-text` |
| Anlatım ve veri (`teach`, `chart`, `table`, diğerleri) | `--subject-surface` (Carbon tag zemini) | `--subject-on-surface` | `--subject-text` |
| Mola (`brainbreak`) | `--cds-layer-accent-01` (nötr) | `--cds-icon-secondary` | `--cds-text-secondary` |

Eski `--seg-accent` eşlemesi (anlatım=info mavisi, mola=başarı yeşili) kaldırıldı: anlam renkleri
kategori olarak kullanılınca "doğru" ve "bilgi" sinyalleri sulanıyordu, açık temada yeşil kicker
3,3:1 ile AA'nın altındaydı. Etkinlik tipi artık ton + ikon + kicker metniyle okunur.

## 4. Derse göre kimlik (Tedy ders renk sistemi)
Ders rengi `meta.subject`'ten türetilir ve Tedy'nin tüm yüzeylerinde (modül, pano, katalog) aynıdır.
Tek kaynak `assets/carbon-v11-authority.json` → `tedyLayer.subjectThemes`; kurallar ve tablo
`tedy-integration.md` §3'tedir. Özet: Türkçe ve edebiyat **magenta**, matematik **mor**, fen **teal**,
sosyal bilimler **camgöbeği**, yabancı diller **mavi**, din ve değerler **sıcak gri**, bilişim
**soğuk gri**, sanat-spor ve genel **gri**. Rolleri Carbon Tag token'ları ve palet adımları verir;
tema değişince CSS kendiliğinden geçer (JavaScript renk hesabı yok). Kırmızı, yeşil, sarı ve
turuncu anlam renkleridir, ders rengi olamaz. Üst bant Tedy laciverdidir; **butonlar ve ilerleme
göstergesi Carbon mavisi kalır**.

## 5. Kontrast ve doğrulama
- Küçük metin daima `--cds-text-primary`/`secondary`; aksan büyük/dolgu/çizgi öğelerinde.
- Notification yüzeyleri düşük-kontrast token'dır; üzerine `text-primary`.
- `validate_module.py`: **G-CONTRAST** (metin token'ı), **G-CARBON** (token kullanımı),
  **G-SVG** (figürlerde token renk), **G-TOKEN** (g10 · white · g100 otoritesi). Renk asla
  emoji/animasyonla telafi edilmez.

## 6. Tedy ile bütünlük
Tema, kimlik bandı, köşe, gölge ve oyunlaştırma kuralları: `tedy-integration.md`.
