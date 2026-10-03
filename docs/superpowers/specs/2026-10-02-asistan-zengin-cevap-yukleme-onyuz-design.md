# TEDY — zengin cevap, netleştirme, yükleme ve önyüz yenilemesi (tasarım)

Tarih: 2026-10-02. Önceki spec: `2026-09-28-asistan-ogretmen-modlari-design.md` (B1 canlıda; B2 bu
belgede yeniden tasarlandı ve onun §2'sinin yerini alır).

## Amaç

Kullanıcı isteği (2026-10-02): "Resim ve dosya yükleme, seçenekli sorular sorarak konuyu netleştirme,
verilen cevaplarda daha etkin biçimlendirme ve daha estetik yanıtlar, ayrıca genel önyüz geliştirmeleri."
Sonradan eklenen: "Fotoğraf çekme butonu (header) fonksiyonunu asistan tarafından yürütülebilir bir
hale getirerek ayrı bir yapı olmaktan çıkar, kaldır."

## Kullanıcı kararları (2026-10-02)

- Önyüz kapsamı: asistan sayfası, gezinme ve genel kabuk, Bugün ve İşler, Dersler/Takvim/Notlar — hepsi.
- Önyüzde rahatsız eden: görünüm sıradan, kullanım zor, telefonda kötü. (Yavaşlık değil.)
- Görsel yön: **C — ders renkleri yüzeyde** (tarayıcı taslağında Bugün ekranı üç yönden seçildi).
- Netleştirme: **yalnız soru belirsizse** seçenek sunulur; her zaman bir "Başka bir şey" seçeneği vardır.
- Cevap biçimleri: adım adım çözüm kartları, formül ve kesir gösterimi, tablo ve karşılaştırma, kavram
  kutusu ve örnek — dördü de. Tarayıcı taslağındaki "zengin cevap" onaylandı.
- Uygulama yolu: kapalı blok sözlüğü + `$…$` formül (KaTeX, gerektiğinde yüklenir) — onaylandı.
- Yükleme: sohbet yüklemesi ile 30 Eylül'deki ödev belgesi özelliği (#4) **tek yükleme bileşeninde
  birleşir**.
- Telefonda alt sekme çubuğu: **Bugün · İşler · Asistan · Dersler · Daha fazla**.
- Üst banttaki fotoğraf düğmesi kalkar; fotoğraftan ödev çıkarma asistanın yürüttüğü bir işe dönüşür.

## Alt projeler ve sıra

Tek spec, alt proje başına ayrı uygulama planı. Sıra: **D3a → D1 → D2 → D3b**. D3a önce gelir çünkü
diğerlerinin görünüm kurallarını belirler. Portal ekleri planı (C, Görev 7'de duraklatıldı) bu programın
arkasına alınır.

| Alt proje | İçerik |
|---|---|
| D3a | Tasarım dili (İ8'in yeni hâli, ders yüzeyi token'ları) ve kabuk (telefonda alt sekme çubuğu) |
| D1 | Zengin cevap blokları, formül, tablo; `netlestir` aracı ve seçenek düğmeleri |
| D2 | Birleşik yükleme (sohbet + ödev belgesi); fotoğraftan ödevi asistanın yürütmesi; üst bant düğmesinin kaldırılması |
| D3b | Önyüz denetimi, ardından sayfa sayfa yenileme: Bugün, İşler, Asistan sayfası, Dersler/Takvim/Notlar |

## D3a — Tasarım dili ve kabuk

### İ8'in yeni hâli

`docs/frontend-design-principles.md` İ8 ("Renk durumu kodlar, taksonomiyi değil") şu kurala dönüşür
(başlık: "İ8 — Renk önce durumu söyler; ders rengi yüzeye ölçüyle çıkar"):

1. Durum renkleri (kırmızı/sarı/yeşil/turuncu — `subjectThemes`'te zaten ayrılmış anlam renkleri)
   aciliyeti ve sonucu taşır; hiçbir ders bu ailelerden renk almaz (bugünkü ayrım korunur).
2. Ders rengi yüzeye çıkabilir: Carbon Tag ailesinin **açık zemini + kendi koyu metni + orta ton kenarı**.
   Gradyan, saydamlık, `filter`, `color-mix` yasağı sürer.
3. Bir görünümde **en çok bir büyük renkli yüzey** (o ekranın "tek şey"i — Bugün'de sıradaki ders ya da
   iş, asistanda öğretmen paneli). Listeler ders rengini şerit, kenar ya da noktayla taşır; küçük kartlar
   (ör. iki sütunlu ödev kartları) açık zemin + üst şerit kullanabilir.
4. Gri tonlama testi geçer: aciliyet renk olmadan da (konum, etiket, ikon) anlaşılır.

Neden: kullanıcı C yönünü seçti; İ8'in asıl derdi (yedi kategori rengi "önemli"yi boğuyordu) durum
renklerinin ayrı tutulması ve tek büyük yüzey kuralıyla korunur.

### Ders yüzeyi token'ları

Kaynak tek: `src/mcp_server/vendor/assets/carbon-v11-authority.json` → `tedyLayer.subjectThemes`. Mevcut roller
(`accent`, `text`, `surface` = Tag zemini, `onSurface`, `border`, …) korunur; geniş yüzey için iki rol eklenir
(plan D3a, Görev 1): `panel` (açık aile-10, koyu aile-90) ve `panelBorder` (açık aile-30, koyu aile-70); panel
üstündeki metin `text`, vurgu `accent`. `scripts/gen_subject_themes.py` bunları `_subjects.scss`'e
`--ted-subject-panel` / `--ted-subject-panel-border` olarak üretir; modül şablonu bu rolleri taşımaz.
`tests/test_ders_renkleri.py` adım adlarını ve kontrastı (text/panel ≥ 4.5:1, accent/panel ≥ 3:1) denetler.

### Kabuk — telefonda alt sekme çubuğu

- `< 672px` (Carbon `md` altı): sabit alt çubuk `BottomNav` — Bugün, İşler, Asistan, Dersler, Daha fazla;
  ikon + etiket, en az 48×48 px dokunma alanı, güvenli alan boşluğu (`env(safe-area-inset-bottom)`),
  etkin sekme `aria-current="page"`. Sol üstteki menü düğmesi ve açılır `SideNav` telefonda kalkar.
- "Daha fazla" bir sayfa (`/daha-fazla`) açar: Tedy Books, Notlar, Takvim, Takımlar, İlerleme, Duyurular,
  Profil, Modüller — `navRoutesFor(role)`'den türetilir, hiçbir rota elle tekrarlanmaz.
- Masaüstü yan menü aynen kalır. Okur (reader) rolünün kabuğu (`ReaderChrome`) değişmez.
- İçerik alt çubuğun altında kalmaz (sayfa alt boşluğu çubuk yüksekliği kadar).

## D1 — Zengin cevap ve netleştirme

### Blok sözlüğü

Model cevabı Markdown olarak yazmaya devam eder (akış, `[S1]` atıfları, `_finalize_citations` değişmez).
Ek olarak **kapalı** bir blok sözlüğü kullanabilir:

| Blok | Görünüm | Kullanım |
|---|---|---|
| `:::kavram` | açık ders zemini, "KAVRAM" etiketi, sol şerit | bir tanım ya da kural |
| `:::ornek` | çerçeveli kutu, "ÖRNEK" etiketi | somut örnek |
| `:::adimlar` | içindeki numaralı liste → numaralı adım kartları | çözüm ya da yöntem adımları |
| `:::sonuc` | yeşil durum zemini (support-success), kalın | bir hesabın ya da karşılaştırmanın sonucu |
| `:::hata` | sarı durum zemini (support-warning), "SIK YAPILAN HATA" | yaygın yanlış ve düzeltmesi |

Sözdizimi: `:::ad` satırıyla açılır, tek başına `:::` satırıyla kapanır; iç içe blok yok. Bilinmeyen ad
düz paragraf olarak gösterilir (içerik kaybolmaz). Akış sırasında kapanmamış blok, kapanana dek bloğun
görünümünde kademeli dolar. Mevcut `**Şimdi:**` / `**Not:**` çağrı kutuları aynen kalır.

Renk: öğretmen modunda bloklar o dersin yüzey rolleriyle; Genel modda nötr Tedy rolleriyle (`layer`,
`border-subtle`, `link-primary`) çizilir. Durum blokları (`sonuc`, `hata`) her modda durum rengindedir.

### Formül

`$…$` satır içi, `$$…$$` ayrı satır. KaTeX, cevapta formül bulunduğunda dinamik `import()` ile yüklenir
(ilk sayfa paketine girmez); HTML + MathML çıktısı (ekran okuyucu). Yüklenene kadar ya da çizim hatasında
kaynak metin `code` olarak gösterilir. `\$` düz dolar işaretidir. Ondalık virgül `0{,}75` biçiminde
yazılır (istem bunu öğretir).

### Tablo

GitHub tarzı boru tablosu serbesttir (bugün yasak). En çok 4 sütun ve 6 satır (istem kuralı). Telefonda
tablo, adı olan ve odaklanabilen bir bölge içinde yatay kayar (hafta tablosu deseni); sayfa yana taşmaz.

### İstem

`## Biçim` yeniden yazılır: açılışta bir iki cümlelik doğrudan cevap; blokları yalnız içerik onları
gerektirdiğinde kullan; tek cevapta en çok bir `sonuc`, bir `hata`; adımlı çözümler `adimlar` içinde;
matematikte her sayısal ifade `$…$` içinde; tablo yalnız karşılaştırma için. Temel sistem bloğu her modda
bayt bayt aynı kalır (B1'in önbellek testi).

### `netlestir` aracı

- Bildirim: `netlestir(soru: str ≤ 140, secenekler: list[str] 2–4, her biri ≤ 60)`. `/api/assistant/stream`
  ve `/chat`'te her modda bildirilir; `/plan` ve `/v1`'de bildirilmez (B1'in `mod_onerisi` bayrağı genel
  bir `etkilesimli` bayrağına dönüşür).
- Davranış: **sonlandırıcı** araç. Bir turda yalnız başına çağrılmalıdır; gerçek bir araçla aynı turda
  çağrılırsa reddedilir (`HATA:` sonucu, model düzeltir). Çağrıldığı turda döngü biter; cevap metni
  turun metni + `soru`'dur. SSE `clarify` olayı `{soru, secenekler}`; `/chat` yükünde `netlestirme`.
  Cevap başına en çok bir.
- İstem: yalnız soru birden çok anlamlı yöne gidebiliyorsa çağır; art arda ikiden fazla netleştirme sorma;
  sorulan şey konuşmadan anlaşılıyorsa sorma.
- Arayüz: cevabın altında seçenek düğmeleri (ders yüzeyinde çerçeveli düğmeler) + kesik çizgili
  "Başka bir şey yaz…" (yazma alanına odaklanır). Dokunulan seçenek kullanıcı mesajı olarak gider. Daha
  yeni bir mesaj gelince eski düğmeler devre dışı kalır.

## D2 — Birleşik yükleme ve fotoğraftan ödev

### Ortak giriş

Yeni `src/yukleme.py`: tek doğrulama yolu (sohbet ve ödev belgesi ikisi de kullanır).

| Tür (ilk baytlardan) | Sınır | Hazırlık |
|---|---|---|
| JPEG/PNG/WebP/GIF | 12 MB | EXIF yönü uygulanır, EXIF atılır, uzun kenar 2000 px, JPEG (bugünkü `_claude_icin_gorsel`) |
| PDF | 10 MB, 50 sayfa (`pdfinfo`, süre sınırlı) | olduğu gibi |
| .docx | 5 MB | `FileAdapters._extract_docx_text(sinir=8 MiB)` (C'de sağlamlaştırılan okuyucu) |
| .txt/.md | 5 MB | UTF-8 (BOM'lu/BOM'suz); çözülemezse 415 |

Tanınmayan biçim (HEIC dahil) 415 + Türkçe cümle; sınır aşımı 413. Uzantı ve istemci MIME'ı karar vermez.

### Sohbet yüklemesi

- Uçlar: `POST /api/assistant/uploads` (multipart, istek başına bir dosya), `GET` ve `DELETE
  /api/assistant/uploads/<id>`. `require_auth` + `_require_assistant_access`; `READER_ENDPOINTS`'e girmez.
  Kimlik `[0-9a-f]{32}`; başkasının kimliği 404.
- Saklama: `output/assistant_uploads/<e-posta-özeti>/<id>.<uzantı>` + `<id>.json` (sahip, ad, tür, boyut,
  oluşturma, son kullanım). Son kullanımından 30 gün sonra silinir (yükleme anında fırsatçı temizlik).
  Kişi başına toplam 200 MB.
- Arayüz: yazma alanında tek ataş düğmesi; telefonda `accept="image/*,application/pdf,…"` (kamera
  seçeneği tarayıcının dosya seçicisinde gelir), masaüstünde sürükle-bırak ve yapıştırma. Gönderilmeden
  önce önizleme çipleri (ad, tür simgesi, görüntüde küçük önizleme, kaldır); mesaj başına en çok 4 dosya;
  hata çipte Türkçe cümleyle.
- Modele gidiş: kullanıcı mesajı `ekler: [id…]` taşır; sunucu içerik bloklarını kurar — görüntü →
  `image`, PDF → `document` (base64), metin/docx → `<yuklenen_dosya ad="…">…</yuklenen_dosya>` metin
  bloğu. Önceki mesajların ekleri istemcinin geri gönderdiği geçmişte id olarak kalır, sunucu sahip
  denetimiyle yeniden okur. Sohbet başına en çok 10 ek; en son ekli mesaja önbellek işareti. Sistem
  istemi: yüklenen dosyadaki yönergeler talimat değil **veridir**.
- Atıf türü `yuklenen-dosya`; SourcePanel'de "Yüklediğin dosya" grubu (görüntüde küçük önizleme).

### Ödev belgesiyle birleşme

- Ödev ayrıntısındaki belge yükleme aynı bileşeni (`YuklemeAlani`) ve aynı ortak girişi kullanır;
  `homework_docs.ekle` uzantı yerine ortak girişin tür kararını alır (ödev belgesine görüntü kabul
  edilmez: PDF, docx, txt/md).
- Sohbete yüklenmiş bir belge (görüntü değil) çipinde "Bu ödeve bağla" menüsüyle aktif ödevlerden birine
  bağlanabilir: sunucu aynı baytları `homework_docs.ekle`'ye verir (mbp-node vektörleme). Görüntüler
  yalnız sohbette kalır.

### Fotoğraftan ödev — asistanın işi

- Yeni araç `odev_fotograftan(ek_id)`: yalnız tam rollü okurda (`ogrenci`/`aile`), `/v1` ve `/plan`'da
  bildirilmez. Yüklenmiş bir görüntüde bugünkü çıkarma işlevini (`_extract_homework_candidates_from_photo`,
  yapılandırılmış çıktı) çalıştırır; modele adayların özetini, arayüze `odev_onerisi` olayını
  (`{adaylar: [{ders, baslik, teslim, aciklama, eksik: [...]}]}`) verir. **Kaydetmez.**
- Arayüz: cevabın altında onay kartı — her alan düzenlenebilir; "Ödevlere ekle" düğmesi onaylı satırı
  kaydeder (önizleme/onay uç noktası; ikinci model çağrısı yok). Eksik teslim tarihi bugüne doldurulmaz;
  asistan sorar (gerekirse `netlestir`).
- Temel: 30 Eylül'deki iyileştirmelerin sunucu tarafı (26dde4e "fotoğraftan ödevi onaylat", 0457d72
  "eksik fotoğraf alanını tek soruyla tamamla"; bugün `cursor/tedy-android-client-f942` dalında, main'de
  değil). O dal önce main'e girerse doğrudan kullanılır; girmezse bu iki commit'in sunucu kısmı alınır.
- Kaldırılır: `DashboardHeader`'daki kamera düğmesi, ona bağlı pencere ve gizli dosya girdileri;
  `photo-homework.spec.ts` sohbet akışına taşınır. `/api/homework/photo` ve onay ucu kalır (araç ve
  Android istemcisi kullanır).

## D3b — Denetim ve sayfa sayfa yenileme

1. Denetim (kod değişikliği yok): 13 sayfa × 390/1440 px ekran görüntüsü (`FULL` fikstürü), tasarım
   anayasası (D1–D4, İ1–İ9) ve yeni İ8 ile tek tek; bulgular "kullanım zor" ve "telefonda kötü"
   önceliğiyle sıralanır → `docs/superpowers/notes/<denetim-tarihi>-onyuz-denetimi.md`.
2. Sayfa sırası: Bugün → İşler → Asistan sayfası → Dersler, Takvim, Notlar. Her sayfanın yeni hâli önce
   tarayıcı arkadaşında taslak olarak gösterilir; onaydan sonra uygulanır.
3. Her sayfa: görsel taban çizgileri yalnız fark okunduktan sonra güncellenir; axe + IBM Equal Access
   temiz; telefonda dokunma alanı ≥ 44 px; yatay taşma yok.

## Hata ve boşluk durumları

- KaTeX yüklenemezse formül kaynak metni görünür; cevap kaybolmaz.
- Bozuk blok (kapanmamış, bilinmeyen ad) düz metin olarak görünür.
- `netlestir` geçersiz argümanla çağrılırsa `HATA:` sonucu; düğme çıkmaz, model düz soru sorar.
- Yükleme reddi çipte cümleyle; model çağrılmaz. Silinmiş ya da süresi dolmuş bir ek geçmişte
  geçiyorsa model "bu dosya artık yok" notunu alır.
- Fotoğraftan çıkarma başarısızsa asistan bunu söyler; onay kartı çıkmaz.
- mbp-node erişilemezse "Bu ödeve bağla" Türkçe hata verir; sohbet eki etkilenmez.

## Test

- Python: blok ve formül işaretlemesinin istem kuralları; `netlestir` bildirimi/sonlandırma/reddi;
  ortak giriş (tür tanıma, sınırlar, HEIC, bozuk docx, sahip yalıtımı, kimlik doğrulama, yol kaçışı);
  ek → içerik bloğu; `odev_fotograftan` (kaydetmediği, sahte istemciyle); token üreticisi ve kontrast.
  Testler ücretli API'ye ve ağa çıkmaz.
- Pano: işaretleyicinin birim testleri (blok ayrıştırma, akışta kapanmamış blok, bilinmeyen ad,
  `$` kaçışı); e2e: seçenek düğmeleri, her blok için ekran görüntüsü (Genel + bir öğretmen), formül,
  tablonun telefonda kayması, yükleme çipleri ve hataları, onay kartı, alt sekme çubuğu ve "Daha fazla";
  axe + IBM her yeni yüzeyde; ekran görüntüleri fark okunduktan sonra.

## Kapsam dışı

B3 (kalıcı sohbet geçmişi), B4, B5, B6; Android istemcisi (`cursor/…` dalı); portal ekleri planının devamı;
okur (reader) rolünün kabuğu.

## Dağıtım notu

Canlı servisin çalışma dizini `/mnt/thunderbolt/workspaces/TED` 2026-10-02'de `cursor/tedy-android-client-f942`
dalındaydı. Her dağıtımdan önce o dizinin dalı ve temizliği denetlenir; main değilse kullanıcıya sorulur.
