# Bugün yenilemesi (D3b, ilk sayfa) — tasarım

Tarih: 2026-10-10. Kullanıcı isteği: "anasayfa tasarımını yeni ilkelere göre tamamen yenile" ve "çelişkileri
en iyi Carbon uygulama standartlarına göre çöz". Kurallar: `docs/tedy-ui-ux-talimatnamesi.md` (özellikle §3, §4,
§5, §7, §8, §11 S1–S44, §13), anayasa D1–D4 / İ1–İ9, yüzey tasarımları §4.1. Ç1–Ç10 kararları bu dalda S35–S44
olarak yazıldı (Ç4 cümle düzeni, Ç10 başlık ağırlıkları, Ç2 iskelet/InlineLoading, Ç5 arıza rengi bu sayfayı
doğrudan etkiler).

## Değişmeyen davranış (ürün kuralları)

Tek şey zile göre değişir (okul sürerken o anki/sıradaki ders, son zilden sonra ödev kartı, borç yoksa okuma);
"Başla" kutuyu yerinde açar (`useZamanKutusu`, aynı anahtar); "Yaptım" `utils/odevYaptim.ts` ile; öğrencinin
işaretlediği iş aktif listeden çıkar; biten öğeler katlanır; akşam "Yarın" sıradaki okul gününü söyler ve
teslimleri tekrar etmez; yarınki sınav "Yarın"ın ilk satırıdır; sınavlar ana karta çıkmaz (İ4); odak kipi
okul saatinde yalnız şimdiki ders kartını bırakır; Gün Şeridi yalnız kalan günü çizer. Veri uçları aynı.

## Sayfa düzeni (yukarıdan aşağı)

1. **Gün satırı** — kap dışı sayfa düzeyi satır (S16: fluid/expressive yalnız burada): gün adı + tarih
   (`fluid-heading-04` ya da `heading-05`; başlık etiketi değil `<p>`, sayfanın h1'i kabuktadır). Önceki/sonraki
   gün: `IconButton kind="ghost" size="lg"` (48px, her genişlikte; `label` "Önceki gün"/"Sonraki gün" — erişilebilir
   ad değişmez). Başka gün açıkken "Bugüne dön": `Button kind="ghost" size="lg"`.
2. **Gün Şeridi** — imza öğe, yeniden boyanır (B9, İ8 anlam renkleri): pencere alanı nötr (`$layer-accent-01`),
   pencere sınırı 2px `$border-strong-01`, ray `$layer-01` + 1px `$border-subtle-01`, "şimdi" işareti
   `$border-inverse` (ya da `$icon-primary`) 2px, çapa opak `$border-interactive` 2px (yarı saydamlık yok). Bütün
   grafik işaretler zemine karşı ≥ 3:1 (ölçülür). Sarı `--ted-day-window*` token'ları kalkar ya da nötre bağlanır
   (tedyLayer otoritesinde değillerse kaldır; varsa otoriteyle aynı commit). Etiketler cümle düzeninde:
   "Şimdi 10:30", "12 saatin var", "Yatma 22:30", "Odak sonu 16:00"; rakamlar `.tedy-time` (mono, tabular).
3. **Tek şey kartı** — sayfanın tek büyük ders paneli (İ8.3; ≤ 1 panel > 7.5rem):
   - Zemin `--ted-subject-panel`, 1px `--ted-subject-panel-border`, satır başı 4px `--ted-subject-accent` kenarı
     (talimatname [3.2-15]: panel sayfa zemininden yalnız kenarla ayrılır), köşe `--ted-radius-card` (8px), gölge
     yok (S11), iç boşluk `$spacing-06` (telefonda `$spacing-05`). Ders yoksa (etkinlik, ÖGEP, okuma) nötr:
     `$layer-01` + 1px `$border-subtle-01` + 4px `$border-strong-01` kenar.
   - Üst etiket `label-01`, cümle düzeni: "Şu an · 10 dk kaldı" / "İlk ders · 08:00" / "Sıradaki · 5 dk sonra" /
     "Okuldan sonra" / "Bu akşam" / "Yarın" / "Başladın · 9 dk kaldı" / "Süre doldu".
   - Başlık `heading-04` (28px, ağırlık token'dan: 400 — S44); sayfanın en büyük metni (P1). Öğretmen satırı
     `body-compact-01`; "Sonra: Fen Bilimleri 11:20" ve "4 ders kaldı" alt satırda, saatler mono.
   - İş kartı: tek birincil eylem `Button kind="primary" size="lg"` "Başla" (Carbon mavisi, S35); "10 dakikayla
     başla" (rakam mono); "Teslim yarın 12:00". Kutu açıkken: öğretmenin talimatı `body-01`, ekler
     (`EkBaglantisi`), "Yaptım" secondary + "Bırak" ghost; süre dolunca "10 dakika daha" primary, "Yaptım"
     secondary, "Şimdilik bu kadar" ghost. Kaydederken düğmenin yerinde tek `InlineLoading` "Kaydediliyor…" (S36).
     Hata: `InlineNotification kind="error" lowContrast hideCloseButton` "Kaydedilemedi." / "Bağlantını kontrol
     edip yeniden dene." (role alert, kutu açık kalır).
   - Okul saatinde ödev önizlemesi: kartın altında tek satır, düğmesiz, panel değil (`.next-thing--quiet`).
4. **Ayrıca / Sınavlar** — Carbon `ContainedList kind="on-page" size="lg"` (48px satır, B8), etiket "Ayrıca" /
   "Sınavlar" (cümle düzeni, S38), başlık eylemi "+N iş daha" (`Link`/ghost, ≥ 44px). Satır: `SubjectLabel`
   (ders işareti) + başlık, sağda gün/saat (`kisaTeslim`, mono). Satır tıklanır (İşler / Sınavlar). Tag yok.
5. **Yarın** — nötr bölüm (`$layer-01`, 1px kenar, 8px köşe), başlık `heading-02` "Yarın · Cuma" (cümle düzeni);
   ilk satır varsa "Sınav · 09:00 · …", sonra "İlk ders 08:00 · Sosyal Bilgiler", "5 ders: …", etkinlikler.
6. **Zaman çizelgesi** — anlamsal `<ol>`; her öğe `<li>`: saat (mono), ders noktası (ders aksanı; dersi yoksa
   nötr), kart (`$layer-01`, 1px `$border-subtle-01`, 8px köşe, gölge yok, eylemsiz kartta hover yok). Teslim
   satırı İşler'e giden gerçek bir düğme/bağlantıdır (klavye, B7). "Şimdi" işareti erişilebilir metinle. Durum
   etiketleri cümle düzeninde: "Devam ediyor", "Teslim" (bugünün teslimi; kırmızı — gerçek aciliyet), "ÖGEP",
   "Özel ders", "Etkinlik". Geçmişin katlanması: `Button kind="ghost" size="lg"` + `aria-expanded` +
   `aria-controls` + ChevronDown/Up, "3 ders bitti · Göster". Ölü stagger animasyonu kalkar.
7. **Yükleniyor** — içeriğin şeklinde iskelet: gün satırı `SkeletonText heading`, şerit ve kart
   `SkeletonPlaceholder`, liste satırları `SkeletonText` (B5). 400 ms altında hiçbir şey gösterme isteğe bağlı.
8. **Arıza** — `useApi` hatası (okul programı, ödevler, takvim, sınavlar) sessiz geçmez (D3, B6):
   `InlineNotification kind="warning" lowContrast hideCloseButton`, "Bazı bilgiler şu an alınamadı" / "Sayfa
   birkaç dakika içinde kendini yeniler." — ham HTTP metni yok (D4), gri yok (S39).

## Mantık düzeltmeleri (testle)

- `windowVoice` okul gününü bilir: bugün dersi yoksa "Okuldan sonra" demez (sabah/öğlen "Şimdi", 16:00–22:30
  "Bu akşam", sonrası "Yarın"; okuma için de aynı). Okul günü davranışı aynı kalır.
- "Şimdi" kartı yalnız ders, ÖGEP ve özel dersten seçilir; takvim etkinlikleri (dönem boyu ya da uzun etkinlikler
  dahil) zaman çizelgesinde kalır, tek şey kartını almaz (canlı takvim 48–55 olay taşıyor).
- Saf zaman mantığı (`windowVoice`, yer seçimi, katlama özeti, sonraki okul günü) `src/utils/bugun.ts`'e taşınır ve
  `tests/*.test.ts` (node:test) ile sınanır.

## Kurallar (uygulama)

Token'lar: `spacing.$spacing-NN`, `type.type-style()`, `motion`, rol token'ları; elle hex/px yok, boyutlar rem;
hover `@media (any-hover: hover)` içinde; yarıçap kart 8 / kontrol 0 / etiket tam; satır içi stil yalnız çalışma
anında hesaplanan değer (şerit yüzdeleri); Carbon bileşen ve ikon adları MCP ya da `node_modules` ile doğrulanır
(talimatname §10). Cümle düzeni (S38): bu sayfa ve paylaşılan `NextThing`'in bütün dizgeleri; İşler'in `NextThing`
üst etiketleri de aynı sözlüğe geçer.

## Testler ve taban çizgileri

Davranış testleri korunur, metinleri cümle düzenine geçer (`today`, `bugun-duzen`, `bugun-yarin-yaptim`,
`sinav-ve-hata`, `gunluk-program`, `portal-ekleri`, `odak`, `d3b-dokunma` — artık bütün Bugün denetimleri ≥ 44px),
yeni testler: arıza bandı, okul olmayan gün sesi, uzun etkinliğin şimdi kartını almaması, klavyeyle teslim satırı,
Gün Şeridi işaret kontrastı ≥ 3:1. Görsel/ARIA taban çizgileri (Bugün, İşler, yüksek kontrast) fark okunduktan
sonra güncellenir. Kapılar: `npm run lint`, `npm run test:birim`, tasarım pytest'leri, Playwright denetim üçlüsü +
Bugün davranış testleri, axe + IBM Equal Access.
