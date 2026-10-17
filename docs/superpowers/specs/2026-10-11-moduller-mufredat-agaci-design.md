# Modüller — müfredat ağacı ve içerik yer tutucuları — tasarım

Tarih: 2026-10-11. Kullanıcı isteği: "modüller bölümünün içeriklerini artık burada edupedia ile birlikte
oluşturacağız. bu modüller bölümü için Türkçe, matematik, fen bilimleri ve sosyal bilimler için ilgili ders
kitapları ve müfredat başlıklarını çekerek ünite ünite ve her ünite içi alt başlıklar için içerik
placeholder'ları yerleştirelim. tam carbon mcp uyumlu bir tasarım yapalım."

Kurallar: anayasa D1–D4 / İ1–İ9 (`docs/frontend-design-principles.md`), talimatname
(`docs/tedy-ui-ux-talimatnamesi.md`) §0.2 öncelik, §4 bileşen seçimi, §10 Carbon sorgu protokolü, §11 sapmalar,
§12 kapılar, §13 borçlar; yüzey tasarımları (`docs/frontend-surface-designs.md`) §2 ortak kalıplar.

Oturumda verilen üç karar: **yaprak = ders kitabı alt başlığı** · **tek ağaç, kademeli açılım** ·
**modülü olmayan konu "Asistana sor" taşır**.

---

## 0. Ölçümler ve kaynakları

Bu tasarımdaki her sayı ölçülmüştür. Sapma kaydı ve uygulama bu tabloya dayanır; "ölçüm varsayımı yener"
(talimatname §0.2).

| Değer | Kaynak |
|---|---|
| Müfredat korpusu sürümü 1.6 | `CLAUDE.md` — "Coverage: since 2026-09-27 the live corpus is 1.6" |
| Program `document_id` ve 7. sınıf sayfa aralıkları: Matematik 24 (115–172), Türkçe 51 (126–161), Fen 54 (146–183), Sosyal 100 (93–122) | `scripts/skill_unite_haritasi.py` `DERSLER` tablosu ("ölçüldü 2026-09-27" notuyla) |
| 7. sınıf ders kitapları: Fen 439 / 473, Matematik 346 / 506, Türkçe 460 / 340, Sosyal 491 / 361 | 2026-10-11 DB sorgusu (`document` ⨝ `subject`, `grades_csv like '%7%'`) |
| 7. sınıf kazanım sayısı: Türkçe 121, Matematik 37, Fen 35, Sosyal 17 | 2026-10-11 DB sorgusu (`learning_outcome`, `fragment_type='outcome'`) |
| İçindekiler nokta öncüllü eşleşme: Fen 1 → 37, Fen 2 → 35, Mat 1 → 33, Mat 2 → 33; Türkçe 1/2 ve Sosyal 1/2 → 0 | 2026-10-11 sonda (atıldı); yöntem: `^(ad)\s*\.{4,}\s*(\d{1,3})$`, içindekiler sayfası ilk 14 sayfada aranır |
| Basılı → PDF sayfa kayması: Fen 439 **+1** (21/23), Fen 473 **+1** (22/23), Mat 346 **0** (35/35), Mat 506 **0** (32/32) | 2026-10-11 sonda (atıldı); yer gerçeği içindekilerin basılı numarası ↔ başlığın gövdede geçtiği sayfa |
| Gövde eşleştirmesinin tek başına tutarlılığı %50–71 | 2026-10-11 sonda (atıldı); bu yüzden Türkçe/Sosyal'de sayfa aralığı **üretilmez** |
| Yayınlanmış üç modülün `outcomes` alanı: `MAT.7.1.1`, `FB.7.1.1`, `SB.7.1.3` | `output/modules/index.json` |
| `TreeView` / `TreeNode` prop'ları (`label: React.ReactNode`, `href?: string`, `onSelect`, `isExpanded`, `size?: 'xs' \| 'sm'`, `label: string` zorunlu) | `dashboard/node_modules/@carbon/react/lib/components/TreeView/{TreeView,TreeNode}.d.ts` — yerel 1.114.0 |
| Ders → ünite → konu için `TreeView size="sm"` kararı | `docs/carbon-bilesen-rehberi.md` §1.39 "TEDY durumu" |
| Carbon: tek düzey iç içelik için ağaç **kullanılmaz** (→ accordion) | https://carbondesignsystem.com/building-blocks/core/components/tree-view/guidelines/#when-not-to-use |
| Ağaç düğümü yüksekliği sm 32 / xs 24 px | `docs/carbon-bilesen-rehberi.md` §1.39 "Ölçüler ve token'lar" |
| Telefonda dokunma hedefi ≥ 44 px | `CLAUDE.md` B79; kapı `dashboard/tests/e2e/d3b-dokunma.spec.ts` |
| Sütun 60rem, md kırılımı 672 px, görsel temeller 1440/390, 14 sayfa | `CLAUDE.md` "One column, audited" ve "4K screens" |
| `output/modules/**` tek yazarı ted-mcp | `CLAUDE.md` "Tek yazar" |

Veritabanı **yalnız** şu URI ile açılır (salt okunur, değişmez):
`file:/home/mahirkurt/mcp-data/mufredat/mufredat.sqlite?mode=ro&immutable=1`.

---

## 1. Kapsam

7. sınıf, dört ders: Türkçe, Matematik, Fen Bilimleri, Sosyal Bilgiler. Üretici sınıfı parametre alır
(`--sinif 7`), ama bu dalda yalnız 7 üretilir — pano 7. sınıf bir öğrenci için çalışıyor.

**Kapsam dışı (bu dalda yapılmaz):** modül derlemek ya da yayınlamak (edupedia akışı, ted-mcp, kullanıcıyla
birlikte), konu başına ayrı sayfa, diğer sınıflar, diğer dersler, ağaçtan modül üretimini başlatan bir düğme.

Yer tutucu bir **iş emri**dir: ders, ünite, konu adı, kazanım kodu, kitap ve (varsa) sayfa aralığı. edupedia'nın
kendi çerçeve bulucusu (`kapsam._frame`) sayfayı kanıta göre yine kendisi seçer; ağaçtaki sayfa aralığı bir
**ipucu**dur, sözleşme değil — bu yüzden yanlış bir ipucu, ipucu olmamasından kötüdür.

---

## 2. Veri — `src/mufredat_agaci.json`

Üretici `scripts/mufredat_agaci.py <ders|tumu> --sinif 7`, `output/modules/` altına **yazmaz** (tek yazar
ted-mcp). Dosya depoda izlenir: `git diff`'te gözden geçirilir, `scripts/skill_unite_haritasi.py` çıktısı olan
`references/unite-haritasi.md` dosyalarıyla aynı "üretilir, elle düzenlenmez" kuralına girer.

Okuyucu `src/mufredat_agaci.py`: **yalnız stdlib**, `src/module_store.py` gibi — pano `src/mcp_server`'ı,
ted-mcp `src/dashboard_api`'yi import etmez.

```json
{ "surum": 1, "korpus_surumu": "1.6", "sinif": "7. Sınıf",
  "dersler": [{
    "ders": "Fen Bilimleri", "slug": "fen",
    "program": { "document_id": 54, "sayfa": "146-183" },
    "kitaplar": [{ "document_id": 439, "kisa": "1. Kitap",
                   "sayfa_kaymasi": 1, "kayma_uyumu": "21/23" }],
    "uniteler": [{
      "no": 3, "ad": "Vücudumuzdaki Sistemler", "program_sayfa": 156,
      "konular": [{
        "id": "fen-u3-sindirim-sisteminin-sagligi",
        "ad": "Sindirim Sisteminin Sağlığı",
        "ad_kaynak": "Sindirim Sisteminin Sağlığı",
        "kitap": 439, "sayfa": [97, 101], "sayfa_kaynak": "icindekiler",
        "kazanimlar": ["FB.7.3.2"], "kazanim_kaynak": "metin-ortusmesi"
      }]
    }]
  }],
  "kapsam": { "fen": { "konu": 0, "sayfasi_olan": 0, "kazanimi_eslenen": 0 } } }
```

Yukarıdaki `sayfa: [97, 101]`, doc 439 içindekilerindeki basılı 96–100 aralığına ölçülen +1 kayması
eklenerek türetilmiştir (§0). `kapsam` sayıları örnekte sıfırdır çünkü **henüz ölçülmedi** — üretici
koştuğunda dolar.

### 2.1 Dürüstlük alanları

Üç alan boş kalabilir ve boş kalması tasarımın parçasıdır:

- **`sayfa` + `sayfa_kaynak`** — `"icindekiler"` ya da `"yok"`. `"yok"` ise `sayfa` anahtarı hiç yazılmaz;
  yüzey yalnız "1. Kitap" der. Sayfa uydurulmaz (D4).
- **`kazanim_kaynak`** — `"metin-ortusmesi"` ya da `"eslenmedi"`. Başka değer yoktur. **Kod sırasına göre
  eşleme yasaktır:** Fen'de alt başlıkla kazanım 1:1 göründüğü için sırayla dizmek, alt başlıkların kazanımdan
  ince olduğu Matematik'te sessizce yanlış olur.
- **`ad` / `ad_kaynak`** — `ad` okunabilir başlık düzeni, `ad_kaynak` kitaptaki ham metin. İkisi aynıysa da
  ikisi de yazılır (köken kaybolmaz).

**`id` kararlı olmalıdır.** `<ders slug>-u<ünite no>-<konu adının slug'ı>` biçiminde üretilir; **sırasal sayı
kullanılmaz**. Kimlik iki yerde dışa sızar: okurun açık dalları (`localStorage`) ve asistana sabitlenen bağlam
(§4.1). İçindekiler ayrıştırması bir konuyu kaydırdığında `k2` → `k3` olurdu ve okurun açık dalı sessizce başka
bir konuya bağlanırdı. Slug `src/module_store.py`'ın `SLUG_RE` kuralıyla aynı alfabeyi kullanır; çakışma
olursa sonuna `-2` eklenir ve çakışma `kapsam`a yazılır.

### 2.2 Kayma ve eşik

Kayma uydurulmaz: içindekilerdeki basılı numara ile başlığın gövdede gerçekten geçtiği sayfanın farkının
**modu** alınır, uyum oranı `kayma_uyumu` olarak dosyaya yazılır. Uyum %80'in altındaysa o kitabın bütün
konuları `sayfa_kaynak: "yok"` olur.

Bir dersin konularının %60'ından çoğu başlıksız kalırsa o ders **yarım yazılmaz, hiç yazılmaz**; üretici
sıfırdan farklı çıkar ve nedenini yazar. Eksik veriyle dolu bir ağaç, boş bir ağaçtan kötüdür (D3).

### 2.3 Başlık harf düzeni

Ders kitabı alt başlıkları kaynakta büyük harftir ("TAM SAYILAR", "MİLLÎ MESELELER…"). Bunlar etiket değil
**veri**, ama bağıran bir ağaç okunmaz. Üretici Türkçe'ye duyarlı başlık düzenine çevirir — `I`→`ı`, `İ`→`i`
tuzağı adıyla vardır ve `skill_unite_haritasi.py` bu katlamayı zaten yapıyor — ve ham metni `ad_kaynak`'ta
saklar. Yüzeyde `text-transform` **kullanılmaz** (B70). Kaynaktaki harf aralığı bozulmaları
(`SOSY AL` → `SOSYAL`) adlandırılmış bir düzeltme tablosuyla giderilir, `OCR_DUZELTME` gibi.

---

## 3. Eşleme — kanıta dayalı, boşluk görünür

Strateji ders başına farklıdır, çünkü **dersler gerçekten farklıdır**: `CLAUDE.md` Türkçe'nin bu farkını
zaten kaydetmiş ("Türkçe codes its outcomes by skill, not by theme").

| Ders | Konu adı | Ünite ataması | Kazanım |
|---|---|---|---|
| Fen, Matematik | içindekiler, nokta öncüllü (138 satır) | içindekilerdeki ünite başlığı | FTS: kazanımın içerik terimleri konunun sayfa aralığında aranır |
| Sosyal | içindekiler — başlık okunur, numara kopuk | **kazanım kodundan**: `SB.7.`**`1`**`.3` → 1. öğrenme alanı | başlık ↔ kazanım metni örtüşmesi (doc 491 s.8'deki "MİLLÎ MESELELER KARŞISINDA TÜRK TOPLUMUNUN TUTUM VE DAVRANIŞLARI" ↔ `SB.7.1.3`) |
| Türkçe | içindekiler — tema metinleri; tema sırası korunuyor (doc 460 s.8) | içindekilerdeki tema sırası | **eşlenmez** |

Türkçe yaprağı kazanım kodu taşımaz; kazanım beceriye kodlu olduğu için tema metnine kazanım atamak uydurma
olur. Onun yerine beceri alanını taşır ("Okuma", "Dinleme/İzleme" — `TURKCE_BECERILER` adlandırması,
`src/assistant_skills/turkce/references/unite-haritasi.md`).

### 3.1 Yayınlanmış modül ↔ konu

Katalog satırının `outcomes` alanı ile konunun `kazanimlar` alanının kesişimi. Bir modülün kazanımı birkaç
konuya düşerse (Matematik'te olabilir) modül **tek** konuya bağlanır: `frame_source` sayfalarıyla örtüşmesi en
iyi olana, o da yoksa sıradaki ilkine. Gerisi "Hazır değil" kalır, belirsizlik `kapsam`a yazılır. Aynı modül
iki satırda görünmez.

---

## 4. API

`GET /api/modules/agac` → `{ hazir, dersler, kapsam, hata }`. Tek uç, tek getirme: sayfa iki yükleme durumu
yönetmez. `kapsam` **yalnız** ders slug'ı → sayaç eşlemesidir; arıza ayrı bir alanda durur (`hata`), karışmaz.

`hazir`, kataloğun **bütün** yayınlanmış modüllerini listeler — ağaca eşlenmeyen biri (başka sınıf, dört ders
dışı bir ders, kazanımı eşlenmemiş bir modül) de listede görünür. Yoksa yayınlanmış bir modül yüzeyden
kaybolurdu.

- `@require_auth`, full rol. `READER_ENDPOINTS`'e **eklenmez** — okur yalnız Tedy Books'a erişir ve
  `require_auth` varsayılan-reddet olduğu için yeni rota ihmalle sızmaz (`CLAUDE.md` "Roles").
- Mevcut `/api/modules` **dokunulmaz**.
- Ağaç dosyası süreç içinde `stat` imzasıyla önbelleklenir — `src/assistant_modules.py`'ın kataloğu izlemesiyle
  aynı desen. Dosya değişince yenilenir; `ted-dashboard` yeniden başlatılması gerekmez.
- Dosya yok ya da bozuksa uç `dersler: []`, `kapsam: {}` ve `hata: "harita_okunamadi"` döner, 500 vermez:
  hazır modül listesi çalışmaya devam eder. Başka her durumda `hata: null`.

### 4.1 Asistan bağlamı

`SAYFA_OGE_TURLERI`'ne `"konu"` eklenir ve `_sayfa_ogesi_basligi`'na bir dal: kimliği `mufredat_agaci.json`'da
çözer, "Fen Bilimleri · Sindirim Sisteminin Sağlığı" döner, bilinmeyen kimlikte `""`. Sunucu istemcinin
etiketine **güvenmez** — mevcut kural budur ve korunur. Bağlam satırı hiçbir zaman cevabı düşürmez (mevcut
`except` kuralı).

---

## 5. Yüzey — `/moduller`

```
Modüller                                        ← h2, bugünkü başlık

Hazır olanlar                                3  ← ContainedList on-page lg
  ▪Matematik  Tam Sayılar: Sıfırın İki Yanı   Modül
  ▪Fen        Türkiye ve Uzay Araştırmaları   Müfredat
  ▪Sosyal     Millî Meseleler ve Türk Toplumu Modül

Tüm müfredat                                    ← TreeView size="sm"
  ▸ ▪Matematik                    45 konu · 1 hazır
  ▾ ▪Fen Bilimleri                25 konu · 1 hazır
      ▸ 1. Uzay Çağı               4 konu · 1 hazır
      ▾ 3. Vücudumuzdaki Sistemler 8 konu · 0 hazır
          Sindirim Sisteminin Sağlığı
          1. Kitap · s.97–101 · FB.7.3.2 · Hazır değil
  ▸ ▪Sosyal Bilgiler              17 konu · 1 hazır
  ▸ ▪Türkçe                       36 konu · 0 hazır
```

Yukarıdaki konu sayıları (45/25/17/36) **beklenen büyüklük sırasıdır, ölçülmemiştir**; gerçek sayılar üretici
koştuğunda `kapsam`dan gelir ve yüzey onları çizer.

### 5.1 Bileşenler

- **"Hazır olanlar"**: `ContainedList` + `ContainedListItem`, `kind="on-page" size="lg"` — talimatname §4.1
  "sessiz liste (tek sütun, satır içi eylem)"; `TodaySchedule.tsx` aynı biçimi kullanıyor. Boşsa `EmptyLine`:
  "Henüz yayınlanmış modül yok."
- **Ağaç**: `TreeView size="sm" label="Tüm müfredat"` + `TreeNode`. Carbon tek düzey iç içelikte ağacı
  dışlıyor; bizdeki hiyerarşi iki düzey (ders → ünite → konu) ve bileşen rehberi bu vakayı adıyla önceden
  karara bağlamış.
- **Yaprak etiketi iki satır**: ad + üst veri. `TreeNode.label` tipi `React.ReactNode` olduğu için izinli.
- **Ders rengi**: ders düğümünde `SubjectLabel` — İ8: listelerde ders rengi leke/kenar/noktadır; bu görünümde
  büyük ders paneli yoktur.
- **Mod etiketi**: bugünkü `MODE_LABEL` eşlemesiyle `Tag type="cool-gray" size="sm"`; `MODULE`/`CURRICULUM`
  kodu okura gitmez (D4).
- **"Hazır değil"**: düz ikincil metin. `Tag` değil (B45 — cümle rozet olmaz), durum rengi değil: yokluk hata
  değildir, kırmızı/sarı/yeşil anlam renkleri ayrılmıştır.
- **Dal sayacı**: "8 konu · 0 hazır", cümle düzeninde (S38); yüzey tasarımları §2.5'in `Başlık (n)` kalıbı —
  sayı, katlanmış içeriğin büyüklüğünü söyler.

### 5.2 Yaprağın tek eylemi — iç içe düğme yok

ARIA ağacında `li role="treeitem"` içine düğme koymak deseni bozar. Bu yüzden eylem **düğümün
etkinleştirilmesidir**:

- **Modülü olan yaprak** → `TreeNode href="/moduller/<slug>/vN"` + `onSelect` → `navigate(...)`. B58: modül
  açmak gezinmedir, bağlantı olur (geçmiş ve yeni sekme çalışır). `href` prop'u 1.114.0'da vardır (§0).
- **Modülü olmayan yaprak** → `onSelect` → `asistanaSor({ tur: 'konu', id, etiket })`; karşılayan yoksa
  `navigate('/asistan?sayfa=moduller')`. `HomeworkTracker.odeviAsistanaSor` ile birebir aynı akış (B78).

`AcikOge['tur']` birleşimine `'konu'` eklenir; sunucu tarafı §4.1.

### 5.3 Açılma durumu ve odak kipi

Hepsi kapalı başlar (Carbon varsayılanı; talimatname modül ve geçmiş bölümleri için bunu zaten izliyor).
Okurun açtığı dallar `localStorage` `tedy-mufredat-acik` ile **kalır** (İ5: seçim kullanıcı değiştirene dek
sürer), Carbon'un denetimli `isExpanded`'ı ile. **Odak kipinde "Tüm müfredat" hiç çizilmez** — yalnız hazır
olanlar kalır (İ1).

### 5.4 Üç yeni bilinçli sapma (talimatname §11 → S48, S49, S50)

Sessizce yapılmaz; aynı commit'te §11'e yazılır.

1. **S48 — telefonda düğüm yüksekliği.** Carbon'un iki boyu 32 ve 24 px; TEDY telefonda ≥ 44 px istiyor.
   `md` altında `.module-tree .cds--tree-node` en az 44 px. Akordeondaki S18 yamasıyla aynı biçim
   (`.cds--` seçicisi: S3'ün izin verdiği kategori).
2. **S49 — etiket kırpılmaz, sarar.** Carbon taşmayı üç nokta ile kesiyor; bileşen rehberi bunu kendisi
   "tercih edilmez" diye işaretlemiş. "Sindirim Sistemini Oluşturan Yapı ve Organlar"ı "Sindirim Sistemini
   Olu…" yapmak satırın anlamını yok eder (D4). `white-space: normal`, üst veri alt satırda.
3. **S50 — derinlik girintisi.** 390 px'te üçüncü düzey girinti + sarma ile yana kaydırma çıkabilir;
   `tasarim-denetimi.spec.ts` yana kaydırmada hata verir. Girintinin `md` altında daraltılması **ölçülerek**
   karara bağlanır; sayı şimdi uydurulmaz, ölçüm sonucu S50'ye yazılır. Ölçümde yana kaydırma çıkmazsa S50
   yazılmaz ve bu madde düşer.

### 5.5 Hata, boşluk, yükleme (D3)

- Getirme düşerse bugünkü hata `InlineNotification`'ı: "Modüller yüklenemedi." / "Sayfayı birkaç dakika sonra
  yeniden aç." Ham HTTP metni okura gitmez (B43).
- Ağaç okunamazsa "Hazır olanlar" yine çizilir; ağaç yerine `EmptyLine`: "Müfredat haritası şu an okunamıyor."
- §2.2 eşiğine takılıp yazılmayan bir ders ağaçta **yine listelenir** ve tek satır der: "Bu dersin haritası
  henüz hazır değil." Sessizce eksilmez.
- Yükleme sayfanın şeklinde iskeletlerle (`SkeletonText`), tam ekran `Loading` yok.

### 5.6 4K

Bütün yeni ölçüler `rem`; ikonlar `size={…}` ile mevcut kuralı olan boylardan. `ekran-4k.spec.ts` 14 sayfayı
denetliyor, Modüller onlardan biri.

---

## 6. Testler ve kapılar

### 6.1 Python

- `tests/test_mufredat_agaci.py` — şema: `sayfa_kaynak == "yok"` ⇒ `sayfa` anahtarı **yok**; `kazanim_kaynak`
  yalnız iki değerden biri; Fen/Mat/Sosyal'de her kazanım kodunun ünite numarası düğümün numarasıyla aynı;
  **Türkçe satırları kazanım kodu taşımaz**; her listelenen ders için `kapsam` var; `ad_kaynak` her konuda var;
  her `id` benzersiz ve sırasal sayı taşımıyor.
- Kimlik kararlılığı: bir ünitenin konu sırası değiştirildiğinde kalan konuların `id`'leri **değişmiyor**.
- Ayrıştırıcı **altın verilerle** sınanır (DB'den kopyalanmış birkaç sayfa metni), böylece makineye bağlı DB
  yolu olmadan da koşar. Üretici ucu DB yoksa atlanır (`pytest.skip`), ayrıştırıcı testi atlanmaz.
- **Bugünün ölçümü kapıya dönüşür:** üretici doc 439 için kayma 1, doc 346 için 0 türetmezse test düşer.
- `tests/test_dashboard_api.py` — `/api/modules/agac`: full rol 200, okur 403; `MAT.7.1.1` taşıyan konuya
  `mat7-tam-sayilar` bağlanıyor; bir kazanım birkaç konuya düşerse bağlama belirlenimci; ağaca eşlenmeyen bir
  modül `hazir`'da yine görünüyor; dosya bozukken uç 500 vermiyor ve `hata: "harita_okunamadi"` dönüyor;
  `_sayfa_ogesi_basligi("konu", …)` gerçek konuyu çözüyor ve bilinmeyen kimlikte `""` dönüyor.

### 6.2 Dashboard

- `_gorsel-fixtures.ts`'e `/api/modules/agac` sabit verisi; `sabitAc` onu da karşılar.
- Geçmesi gereken takım: `gorsel-regresyon` (Modüller 1440/390 — anlık görüntüler **değişecek**, fark okunarak
  güncellenir), `aria-yapisi` (`/moduller`'in `.aria.yml`'i ağaç rolüyle değişir), `tasarim-denetimi` (axe +
  yana kaydırma yok), `ibm-erisilebilirlik`, `ekran-4k`, `d3b-dokunma` (≥ 44 px), `gorunum-kipleri` (hareket
  azaltma, `forced-colors` kenarı), `capraz-tarayici`.
- `npm run lint` + `npm run lint:css`: token dışı her değer gerekçeli `stylelint-disable-next-line` ile.
- `tests/test_pano_tasarim_sistemi.py` yeni `.scss`'i denetler (rol token'ı, elle hex yok);
  `tests/test_pano_talimatname_borclari.py` cümle düzenini ve `text-transform` yokluğunu denetler.
- Carbon `code_audit` (`framework: "react"`, `ibmProducts: "no"`) tavsiye niteliğinde okunur (§10.3).

### 6.3 Belge kapıları (aynı commit)

- `docs/frontend-surface-designs.md`'e **§4.12 Modüller** (bugün yok; §4 listesi 4.11'de bitiyor).
- `docs/tedy-ui-ux-talimatnamesi.md` §11.1 tablosuna S48–S50 (S50 yalnız ölçüm gerektirirse).
  Numaralar 2026-10-11'de kontrol edildi: tablo S1–S46 ve değişiklik kaydı S47'yi "gerekmedi"
  diye anıyor, bu yüzden S47 atlanır.
- `CLAUDE.md`'nin "Modüller (edupedia)" maddesi ağaç, üretici ve yeni uçla güncellenir.

---

## 7. Riskler

| Risk | Karşılığı |
|---|---|
| Türkçe/Sosyal içindekileri iki sütunlu; başlık sırası bozuk çıkabilir | Sıra bozulursa o ders §2.2 eşiğine takılır ve yazılmaz; yüzey "haritası henüz hazır değil" der |
| Korpus sürümü değişince ağaç bayatlar | `korpus_surumu` dosyada; üretici elle koşulur, `unite-haritasi.md` ile aynı kural |
| Üç düzey ağaç telefonda dar | S48–S50; `tasarim-denetimi` ve `d3b-dokunma` kapıları ölçer |
| Başlık düzeni çevirisi kısaltmaları bozabilir | Ham metin `ad_kaynak`'ta kalır; dönüşüm testle sabitlenir |
| Yeniden üretim okurun açık dallarını kaydırır | `id` sırasal değil, konu adının slug'ı (§2.1) |
| Yüzeyin çoğu "Hazır değil" | Hepsi kapalı başlar; "Hazır olanlar" üstte; odak kipinde ağaç yok; her yaprağın "Asistana sor"u var |
