# Asistan sayfası yenilemesi (D3b, ikinci sayfa) — tasarım

Tarih: 2026-10-10. Kullanıcı isteği: "Asistan sayfasının tasarımını yeni ilkelerimizle baştan aşağıya tekrardan
yapalım." Kurallar: `docs/tedy-ui-ux-talimatnamesi.md` (§3, §4, §5, §6 K1–K14, §7, §11 S1–S45, §13), anayasa,
2026-10-08 Carbon AI Chat spec'i ("Carbon AI kazanır, çekirdek kurallar korunur") ve Bugün yenilemesi
(`2026-10-10-bugun-yenileme-design.md`) — iki sayfa aynı ürün gibi okunmalı. Yön: keşifteki **C — odaklı öğretmen**,
Carbon AI Chat 1.22'nin kendi yuvaları üzerine (A).

## Değişmeyen davranış

Akış (SSE → Carbon parçaları), atıflar ve kaynak paneli, yedek model, durdurma/yeniden üretme, öğretmen modu isteği
(`ogretmen`), B2 yükleme, B3 geçmiş (salt okunur aile görünümü dahil), B4 kartları, B5 ses, D1 netleştirme, D2
fotoğraftan ödev, sayfa bağlamı çipi, XSS kuralı (ham HTML kapalı), S13 onarımları, S7 (`injectCarbonTheme` yok),
telemetri kapalı, Carbon AI Chat yalnız asistan açılınca yüklenir, okura "sen"/"siz". Davranış testleri korunur.

## Karar: S46 — sohbet yüzeyi AI yüzeyidir

Carbon AI Chat `aiEnabled` ile AI degradesini mesaj yüzeyinin tamamına uygular; gölge DOM içindeki kural yüzey
başına ya hep ya hiçtir (keşif §2). En iyi Carbon pratiği gereği kabul edilir: **sohbet paneli Carbon'un AI
yüzeyidir**. Panelin dışındaki her TEDY öğesi nötrdür — öğretmen seçici, sohbet geçmişi, kaynak paneli (B54),
okurun kendi balonu (zaten nötr), kartlar. Talimatname §11'e S46 olarak yazılır; K1 bu sınırla okunur.

## Düzen (yukarıdan aşağı)

1. **Sohbet başlığı (Carbon header)** — başlık o anki öğretmenin adı: "Genel asistan" / "Matematik öğretmeni" vb.
   (ürün adı tekrarlanmaz; `name` boş). Eylemler: "Sohbetler" (geçmişi açar/kapatır), yeniden başlat. AI etiketi:
   önce Carbon'un kendi `showAiLabel` + `EXPLAINABILITY_POPOVER_CONTENT/ACTIONS` yolu denenir; axe ya da IBM ihlali
   verirse `AiAciklama` kalır ama erişilebilir adı düzeltilir (B53: `slugLabel=""` + `aria-label="Yapay zekâ
   açıklaması"`). Açıklama içeriği: hangi model (okunur ad; B55 — Gemma "Evdeki model (Gemma)"), öğretmen modu,
   denetim durumu, kaynakların denetlenebilirliği, yanılabilirlik; başlık heading-04 Regular (§6.2).
2. **Başlık altı satırı (`HEADER_BOTTOM_ELEMENT`)** — öğretmen seçimi tek kontrol: Carbon `Dropdown` (lg, 48px),
   etiket "Öğretmen", seçenekler ders işaretiyle (`SubjectLabel`); telefonda tek satır. Radyo çip grubu kalkar
   (telefonda iki satır ≈ 100px idi). Hatırlama (`useOgretmen`, `localStorage`) ve istekteki `ogretmen` aynı.
3. **Sohbet geçmişi** — Carbon geçmiş paneli `startClosed: true`; "Sohbetler" eylemiyle açılır. Boş durum tek cümle,
   okurun sesiyle (Işık: "Henüz sohbetin yok."; aile: "Işık'ın henüz sohbeti yok."), italik değil, bir kez; notlar
   boşsa onların da tek cümlelik boş durumu var. Silme geri dönüşsüz: Carbon tehlike modalı, nesneyi adlandırır
   ("Sohbeti sil", bağlı ekler ve alıştırmalar da gider; S40, B23). Hata fiili doğru ("silinemedi").
4. **Karşılama** — tek cümle + en çok 3 hızlı soru; hiçbiri `primary` değil (ghost/tertiary, ≥ 44px); ekranın tek
   birincil eylemi "Gönder"dir (S12, B17'nin sayfa içi kısmı).
5. **Yazma alanı** — giriş üstündeki yığın (ataş + "Ödev" seçici + etiket ≈ 150px, mesajları kesiyordu) kalkar:
   ek, ses ve çalışma planı giriş satırının eylemleridir (Carbon `input.actions`/`input.expanded` ya da mevcut
   `PROMPT_LINE_SEND_BUTTON_START` — hangisi telefonda ≥ 44px veriyorsa; MCP + `node_modules` ile doğrula). Ödeve
   bağlama bir eylem ("Ödeve bağla") → küçük Carbon menüsü/popover, seçilen ödev mevcut bağlam çipi olur (aynı istek
   alanı). Yer tutucu "Bir soru sor ya da çalışma planı iste…" (aile: "sorun … isteyin…"), "…" tek karakter. Yükleme
   sınırları ilk açılışta görünür (B59).
6. **Mesajlar** — sütun genişliği rem ile (`--cds-aichat-messages-max-width: 42rem`, geçmiş `20rem`) → 4K'da ölçeklenir
   (B28'in genişlik kısmı). Kalan kutuları (`:::kavram` vb.) cümle düzeninde, büyük harf ve elle harf aralığı yok
   (S38, B70); başlık ağırlıkları token'dan (S44). Adım rozetleri nötr, ders aksanı değil (B32).
7. **Mesaj altbilgisi** — bozulmuş durum rozetleri gri Tag değil, uyarı ikonu + metin (S45, B75); "Kaynaksız cevap"
   bilgi. Hata kartı kırmızı Tag içinde cümle değil `InlineNotification` (B45). Eylemler ≥ 44px telefonda.
8. **Öğretmen rengi** — yalnız yüzeyde: sohbet çerçevesinin 1px ders kenarı + 4px üst aksan; `--cds-button-primary`
   ve `--cds-interactive` asla boyanmaz (S35, B68). Kullanıcı balonunun ders yüzeyi kalabilir (kontrast ölçülür).
9. **Kayan başlatıcı (diğer sayfalar)** — aynı bileşenler; başlatıcı düğmesi birincil değil (sayfanın kendi birincili
   kalır; `kind="secondary"` ya da Carbon AI Chat'in kendi başlatıcısı — S12/B17), ödev penceresinin altında kalır
   (B61, z-index ölçülür).

## Stil temizliği

Yeni arayüz `components/AssistantChat.scss`'e bağımlı olmaz: kullandığı canlı `ac*` aileleri (öğretmen, sohbetler,
kaynak paneli, ekler, plan, AI açıklaması, ses hatası, callout'lar, öneri) `asistan/*.scss`'e taşınır ve kurallara
göre yeniden yazılır (token, rem, `any-hover`, köşe 8/0/tam, gölgesiz, cümle düzeni). Stili olmayan
`asistan__altbilgi/rozetler/eylemler/kaynaklar/hata/...` sınıfları ya stillenir ya kalkar. Eski `AssistantChat.tsx`
geri dönüş yolu olarak kalır (2026-10-08 spec'i Görev 21) ama yeni arayüz onun stil dosyasına dayanmaz.

## Testler

Davranış testleri korunur. Değişen sunum sözleşmeleri bilinçli güncellenir: `carbon-asistan-ogretmen.spec.ts` (gönder
düğmesi her kipte `rgb(15, 98, 254)`; radyo yerine Dropdown sırası ve klavyesi), `carbon-asistan-sohbet.spec.ts`
(boş durum bir kez, okurun sesi; telefonda geçmiş "Sohbetler" eylemiyle), `asistan.aria.yml`, bütün asistan PNG'leri.
Yeni: bütün asistan denetimleri telefonda ≥ 44px (`d3b-dokunma`), AI etiketi erişilebilir adı ve klavye (B57),
sohbet dışı TEDY öğelerinde AI degradesi yok, silme modalı, gemma okunur adı. `suite-hygiene`'yi kıran üç
`waitForTimeout` koşula çevrilir. Kapılar: lint, `tsc -b`, `test:birim`, tasarım pytest'leri, bütün
`carbon-asistan-*` + denetim üçlüsü + `ekran-4k` + `alt-gezinme` + `d3b-dokunma` + `suite-hygiene`.
