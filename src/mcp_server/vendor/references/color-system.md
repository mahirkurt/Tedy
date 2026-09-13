# İşlevsel Renk Sistemi (color-system.md)

`carbon-edupedia` rengi **işlevsel** kullanır: her renk bir görevi temsil eder, nötr bir
Carbon tuvali üzerinde. Amaç, DEHB-sakin sınırını korurken renkle **odak, buton ve
öğrenme süreçlerini** güçlendirmektir. Kanıt ve gerekçe için `adhd-pedagogy.md` §12.

## 1. Renk rolleri (hepsi `--cds-*`/token tabanlı)

| Rol | Token | Kullanım |
| --- | --- | --- |
| **Eylem** | `--cds-button-primary` (Blue 60), `--cds-link-primary` | Birincil buton, bağlantı. Kontrast için **mavi** sabittir (aksan değil). |
| **Odak çıpası** | `--accent` / `--accent-tint` / `--accent-strong` | Geçerli adım, seçili şık, etkin başlık — "buraya bak" sinyali. Derse göre değişir. |
| **Durum: başarı** | `--cds-support-success` + `--cds-notif-success-bg` | Doğru yanıt, ustalık, tamamlama. |
| **Durum: bilgi** | `--cds-support-info` + `--cds-notif-info-bg` | İpucu, "hatırla", nötr geri bildirim. |
| **Durum: uyarı** | `--cds-support-warning` + `--cds-notif-warning-bg` | Dikkat çekme (cezalandırıcı değil). |
| **Durum: hata** | `--cds-support-error` + `--cds-notif-error-bg` | Yalnız yanlış şıkkı **işaretlemek** için; metin daima yapıcı ("tekrar dene"). |
| **Kategori** | `--viz-1..5` | Grafik serileri, sıralama/gruplama kategorileri, diyagram parçaları. |
| **İllüstrasyon** | `--viz-sun/water/cloud` | Doğa/şema anlamsal renkleri. |
| **İlerleme/ödül** | `--reward` + `--reward-bg` | XP, yıldız, rozet — pozitif sıcak vurgu. |
| **Tuval** | `--cds-background`, `--cds-layer-01/02/03` | Zemin ve yüzeyler (nötr, katmanlı derinlik). |

## 2. Beş kural

1. **İşlevle ata, süsleme yapma.** Renk yoksa bir işi temsil etmiyordur → kullanma.
2. **Nötr tuval.** Büyük doygun alan yok; arka plan Carbon layer'ı.
3. **Artıklık + CVD.** Renk tek ayırt edici olamaz; metin/ikon/şekil ile birlikte.
4. **Wayfinding aksanı.** Etkinlik türü (anlatım=bilgi, quiz/etkileşim=aksan, mola=başarı,
   grafik/tablo=kategori) segment başlığında `--seg-accent` ile imlenir.
5. **Sakinlik.** Tek, `prefers-reduced-motion` ile kapalı giriş; doygunluk ölçülü; WCAG AA.

## 3. Wayfinding aksanı (`--seg-accent`)
Motor, `.stage[data-seg="…"]` üzerinde `--seg-accent` tanımlar; `seg-ic`, `kicker` ve
başlık alt-çizgisi bunu kullanır. Eşleme: `teach`→info, etkileşim türleri→accent,
`brainbreak`→success, `chart`/`table`→`--viz-2`. Böylece çocuk etkinlik türünü renkten de okur.

## 4. Derse göre kimlik aksanı
`meta.accent` verilmemişse aksan **konudan** türetilir (bkz. `subject-packs.md`): matematik
mor, fen teal, sosyal/tarih mor-pembe, Türkçe kırmızı, dil mavi. Aksan yalnız odak/yapı/
başlık tonunu etkiler; **butonlar mavi kalır** (kontrast güvenliği). Tema değişiminde
`setAccent` tonu yeniden hesaplar (açık/koyu uyumu).

## 5. Kontrast ve doğrulama
- Küçük metin daima `--cds-text-primary`/`secondary`; aksan büyük/dolgu/çizgi öğelerinde.
- Notification yüzeyleri düşük-kontrast token'dır; üzerine `text-primary`.
- `validate_module.py`: **G-CONTRAST** (metin token'ı), **G-CARBON** (token kullanımı),
  **G-SVG** (figürlerde token renk). Renk asla emoji/animasyonla telafi edilmez.
