# Sınav Hazırlığı — Plan 1: Fen dikey dilimi — uygulama planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Spec'in 1–5. aşamalarını (PDF yoklaması + kanun, kitap haritası, kılavuz modeli + API + hazırlık işaretleri, pano yüzeyleri, A4 PDF hattı) yalnız Fen Bilimleri için uçtan uca kurmak; 3 Kasım 2026'daki Fen 1. yazılısına (duyurulan 2. senaryo) Işık kılavuzu ekranda açıp A4 PDF olarak indirebilsin. Diğer beş ders ana sayfada ve ders sayfasında senaryo verisiyle görünür; kılavuzları "Kitap bölümleri henüz eklenmedi" kipinde açılır.

**Architecture:** Bir betik (`scripts/meb_kitap_haritasi.py`) EBA PDF'inin İçindekiler'ini (`pdftotext -layout`) ve sayfa düzenini (`pdftohtml -xml`: yazı boyu, aile, kalınlık) okuyup `src/kitap_haritalari/fen-bilimleri.json`'u yazar. Saf bir model (`src/sinav_kilavuzu.py`) senaryo tablosu + harita + sınav kayıtları + ders kartları + ödevler + modüller + kişinin işaretlerinden deterministik JSON üretir; Flask `/api/hazirlik*` uçları onu sunar, işaretler `output/hazirlik_isaretleri.json`'a atomik yazılır. Pano üç yüzey çizer (`/hazirlik`, `/hazirlik/:ders`, `/hazirlik/:ders/:sinav`); kılavuz bileşeni (`KilavuzBelgesi`) ekranda ve kâğıtta aynıdır. PDF: ayrı bir Vite girişi (`baski.html`) aynı bileşeni çizer, depoya alınmış Paged.js 0.4.3 sayfalar; sunucu (`src/hazirlik_pdf.py`) bir Node betiğiyle (`dashboard/scripts/kilavuz-pdf.mjs`, pano `node_modules`'undaki Playwright, Chrome kanalı) sayfayı ağsız yükleyip basar; eşzamanlılık yuvası, zaman aşımı, düz Chrome yedeği ve önbellek Python'dadır.

**Tech Stack:** Python 3.12 (stdlib, `requests` yalnız betikte), poppler (`pdftotext`, `pdftohtml`, `pdfinfo`, `pdffonts`), `qpdf`, Flask, pytest; React 19 + Carbon (`@carbon/react`, `@carbon/icons-react`), node:test, Playwright (`@playwright/test` 1.58, `channel: 'chrome'`), axe + IBM Equal Access; Paged.js 0.4.3 (MIT, depoda), IBM Plex woff2 (OFL-1.1, depoda).

**Spec:** `docs/superpowers/specs/2026-10-25-sinav-hazirligi-design.md`

## Global Constraints

- Kapsam: spec §10'un 1–5. aşamaları **yalnız Fen Bilimleri** için; Fen 7 **1. Kitap**. Diğer beş ders (Türkçe, Matematik, Sosyal Bilgiler, İngilizce, Din Kültürü) yalnız senaryo verisiyle; kılavuzları "Kitap bölümleri henüz eklenmedi" (spec §7).
- Senaryo tablosu `src/sinav_senaryolari.json` değişmez; yalnız `sinav_senaryo.tablo_oku()` ile okunur.
- Kitap haritası `scripts/meb_kitap_haritasi.py` üretir, **elle düzenlenmez**; gürültü temizliği betiğin `KITAPLAR` ayarındadır (`atla`), sonra betik yeniden koşar.
- Ağ yalnız `scripts/meb_kitap_haritasi.py` (EBA PDF indirme) ve Görev 1'in depoya alma komutlarında. Model, API, pano ve PDF basımı ağa çıkmaz: Node betiği sahte kök dışındaki her isteği keser; yazı tipleri depodan gelir.
- Kanun maddeleri (spec §6, `docs/sinav-kilavuzu-kanunu.md`) her görevin gereğidir: K1 kitap başlıkları yalnız haritadan, birebir; sayfa = basılı sayfa; MEB çıktı metni birebir; bulunamayan "bulunamadı". K2 en çok dört düzey, blok iç sırası sabit. K3 Carbon üretken tip ölçeği, IBM Plex Sans/Mono, A4 gövde 9,5–10 pt, en küçük 7,5 pt. K4 yalnız Carbon belirteçleri; ders rengi yalnız vurgu; durum: yeşil kesin, mavi olası, gri ülke geneli/geçti; mor yalnız YZ; kontrast AA. K5 A4 dikey, kenar 18/16/20 mm, üst bilgi ders·sınav·senaryo, alt bilgi damga + "s. n/N", yetim başlık yok, bölünen blokta "(devam)", siyah-beyazda anlam korunur. K6 kısaltma yok. K7 Türkçe, MEB terimleri birebir, öğrenciye "sen", rakamla sayı, başarı vaadi yok. K8 senaryo duyurulmadıysa hiçbir yüzey tek senaryoyu "bu" diye sunmaz. K9 YZ ayrı ve etiketli (Plan 1'de YZ yok). K10 WCAG 2.2 AA, axe + IBM Equal Access sıfır ihlal, PDF etiketli, yer imli, dil `tr`. K11 aynı bileşen, aynı sıra, etkileşimli öğenin durağan karşılığı. K12 damgalar her sayfada; tablo ya da kitap değişince "güncel değil".
- Durum göstergesi ikon + metin (+ renk): kesin `CheckmarkFilled` + `--cds-support-success`, olası `InformationFilled` + `--cds-support-info`, ülke geneli/geçti düz `--cds-text-secondary` metin. Carbon Tag'de ders aileleri (`blue`, `teal`, `purple`, `magenta`, `cyan`) yasak (talimatname §4.4.2, `tests/test_pano_tasarim_sistemi.py::test_ders_rengi_etiket_olmaz`).
- Pano metin kuralları (Python testleri zorlar): `<h1>`–`<h4>` ve `ContainedList label` ad başlıkları başlık düzeninde (S38, `utils/baslik.ts`); başka her görünür etiket cümle düzeninde (B41); kaynakta tümü büyük dizge yok (B70; MEB, PDF, EBA kısaltma); `kind="secondary"` düğme yok (B58); `InlineNotification` `statusIconDescription` + (`hideCloseButton` ya da kapatma düğmesinin adı `aria-label`), `InlineLoading` `iconDescription`, `Modal` `closeButtonLabel` taşır (B44); ikon boyu 16/20/24/32 (B38); durum opaklıkla çizilmez (B34); stilde hex ve renk aritmetiği yok.
- Okuyucu (reader) default-deny: hazırlık uçları `READER_ENDPOINTS`'e **eklenmez**. İşaret yalnız oturumdaki tam roldeki kişi koyar; API anahtarının kişisi yoktur.
- Atomik yazım: `atomic_json_dump(veri, str(yol))` — `json_utils` `path + ".tmp"` yapar, `Path` geçilmez.
- Güvenilmeyen veri: EBA PDF'leri boş bir geçici dizine iner (`/tmp/meb-kitap-yoklama/fen7-1.pdf` hazır); betikler o dizinden koşmaz; kitabı okuyan Python `-I` ile koşar.
- Yeni Python bağımlılığı yok. Pano `node_modules` canlı checkout'a sembolik bağdır: **`npm install` / `npm ci` yasak**; Paged.js ve Plex dosya olarak depoya alınır (Görev 1).
- Komutlar (çalışma ağacı kökünden, ön planda; arka plan işi yok):
  - Python: `env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest -q -p no:cacheprovider <yol>`
  - Pano (`cd dashboard`): `npm run lint`, `npm run test:birim`, `npm run build` (çıkış kodu boruya verilmeden okunur: `npm run build; echo "çıkış: $?"`).
  - E2e (`cd dashboard`, önce `npm run build`; 8341 seçildi çünkü 8301 bu makinede mevzuat-mcp'nin, 8302–8311'in çoğu başka servislerin — ölçüldü): `TEDY_E2E_PORT=8341 TEDY_E2E_PYTHON=/mnt/thunderbolt/workspaces/TED/.venv/bin/python env -u ANTHROPIC_API_KEY npx playwright test --project= <dosya>`
- E2e'de sabit bekleme yok (`suite-hygiene.spec.ts`); her yokluk iddiasından önce yüzeyin çizildiği kanıtlanır; zaman biçimli her testte `test.use({ timezoneId: 'Europe/Istanbul', locale: 'tr-TR' })`.
- Commit: Türkçe mesaj, son satır `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; dosyalar **adıyla** stage edilir; commit'ten önce `git log --oneline -3` ve `git status --short`. Push, merge ve canlıya alma yok.
- Çalışma ağacı `/mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-hazirligi`, dal `feat/sinav-hazirligi`; canlı checkout'a dokunulmaz.

## Plan kararları (spec'ten sapmalar ve ölçümle verilen kararlar)

1. **Baskı görünümü ayrı bir Vite girişi** (`dashboard/baski.html` → `/baski.html?ders=…&sinav=…&senaryo=…&ebeveyn=…&isaret=…`), spec §5.1'deki SPA rotası `/hazirlik/:ders/:sinav/baski` değil: uygulama kabuğu, oturum açılışı ve gezinme yüklenmez; sunucudaki Chrome sayfayı ağsız yükleyebilir; ekrandaki "A4 önizleme" aynı adresi yeni sekmede açar (oturum çerezi ile modeli `/api/hazirlik/…/kilavuz`'dan alır).
2. **"İç bilet" yok** (spec §5.3): Node betiği `/api/hazirlik/**` isteğini Python'un yazdığı model dosyasıyla, varlıkları `dashboard-dist`'ten sahte bir kökte (`https://baski.tedy.yerel`) karşılar, başka her isteği keser. Flask'a geri bağlantı, bilet ve oturum gerekmez.
3. **Sunucu PDF sürücüsü: Node betiği** (Python Playwright değil). Gerekçe: (a) Playwright 1.58 zaten pano `node_modules`'unda ve e2e ile aynı sürüm; (b) Python Playwright paylaşılan `.venv`'e greenlet/pyee ve kendi Node sürücüsünü getirir — paylaşılan `.venv` değişikliği kullanıcı onayı ister (cryptography emsali); (c) Paged.js ve baskı paketi zaten Node/Chrome tarafında. Görev 2 yoklaması betiği `ted-dashboard.service`'in `PATH`'iyle (`.venv/bin:/usr/bin:/bin`) ölçer; karar kuralı aşağıda.
4. **Yazı tipleri depoda** (`dashboard/public/fonts/plex/`): baskı Google Fonts'a gitmez; Chrome gömer (K3, K10). Ekran Google Fonts CDN'ini kullanmaya devam eder.
5. **Bölüm içi başlıklar `pdftohtml -xml` ile** (`pdftotext -bbox-layout` değil; aynı poppler): `fontspec` yazı boyunu ve ailesini, metin öğesindeki `<b>` kalınlığı verir. Ölçüldü (2026-10-25, Fen 7-1): başlıklar `size="20"` (Arial, beyaz), gövde `size="17"`, içerik çerçevesi adı `Anton`; kalın tanım başlıkları `size="17"` + `<b>` + ":" ile biter ("Potansiyel Enerji:", "Çekim Potansiyel Enerjisi:" s. 68) → **tanım türü Plan 1'de var**.
6. **`cerceveler[].ciktilar` tablonun `konu` alanından** (spec §2.2 "çerçeve açılış sayfasındaki Öğrenme Çıktıları listesi" değil): ölçüldü, kitapta çıktı kodu yok; çıktı listesi ünite açılışında ("Bu ünitede • …") ve kodsuz. Tablonun `konu` alanı İçindekiler'deki çerçeve adıyla birebir ("Türkiye ve Uzay Araştırmaları").
7. **Çerçeve düzeyi başlık listesi** `cerceveler[].basliklar` eklendi: çerçeve açılış sayfasındaki "Bağlantı Noktası" hiçbir konuya ait değildir.
8. **Konu bitişi düzen sınırıyla genişler**: bir konunun son bloğu sonraki konunun başlangıç sayfasının üstüne taşabilir (ölçüldü: "Kontrol Noktası" s. 24 üstte, "Teknoloji ile Uzay Araştırmaları Arasındaki İlişki" aynı sayfanın altında). Başlık yerleşimi (sayfa, üst) sırasıyla yapılır; konunun `son_sayfa`'sı içine düşen son başlığın sayfasına uzar.
9. **Fen 7 2. Kitap Plan 1'de gerekmez**: ölçüldü, 1. Kitap üç üniteyi taşır (3. Ünite "Vücudumuzdaki Sistemler" s. 88–148); Fen 2. yazılı çıktıları (FB.7.2.x, FB.7.3.x) 1. Kitapta.
10. **Durum renkleri Tag değil ikon + metin**: talimatname §4.4.2 Tag'de `blue`'yu derslere ayırır; §5.7 yeni durum göstergesini ikon + metin (+ renk) ister. "Mavi olası" böyle karşılanır.
11. **K7 başlık düzeni panonun S38 kuralına uyar**: spec K7 "cümle düzeninde başlıklar" der; panonun 2026-10-19 S38 kuralı (aile isteği) adlandıran başlıkları başlık düzeninde yazdırır ve `tests/test_pano_talimatname_borclari.py::test_s38_ad_basliklari_baslik_duzeninde` bunu zorlar. Kanun K7 bunu yazar ("Senaryo Karşılaştırması"; cümle olan başlık cümle düzeninde); kitap ve MEB başlıkları birebir (K1).
12. **Model imzası** `genel_bakis(g: Girdiler)` (spec §2.4 `genel_bakis(kullanici, bugun)` yerine): model saf; API girdileri toplar.
13. **YZ alanı kapalı**: model `yz: {"durum": "kapali"}` taşır; PDF seçenek penceresinde YZ ve prova seçenekleri **yoktur** (yapılamayan eylem gizlenir, B42).
14. **Asistan girişi**: Plan 1'de `sinav_senaryosu` aracının metnine kılavuz adresi satırı eklenir; "Kılavuzu aç" öneri çipi Plan 2'de.
15. **`kaynak_sayfa` Fen için `null`**: EBA'nın kitap listesi sayfasının adresi ölçülmedi; kaynaklarda yalnız `pdf_url` gösterilir.
16. **Onaysız harita**: `denetim.kim` boşken model `harita_onayli: false` taşır, ekran "Kitap haritası henüz elle onaylanmadı" der. Plan 1'in haritası Görev 5'te onaylanır.
17. **Bloğun "ödev/modül/not" satırı** (spec §2.4, §4.4): Plan 1'de okul haftası (konu adı o dersin haftalık kartlarında geçen hafta), ödev (o dersin ödev başlığı/açıklamasında konu adı geçen) ve modül (yayındaki modülün `outcomes`'unda çıktı kodu) vardır; ayrı bir "not" kaynağı tanımlı olmadığından "not" ders kartının kendisiyle (okulda satırı) karşılanır.
18. **Paged.js'e yalnız `sayfa.css` verilir**: Carbon ve uygulama stilleri belgede normal `<link>` olarak kalır (ölçüldü: tam stil sayfası Paged.js 0.4.3'ün ayrıştırıcısını "item doesn't belong to list" ile düşürüyor). Kâğıt kuralları iki yerde durur: `sayfa.css` (Paged.js yolu) ve `baski.scss` (düz yol `@page` ve kırılmalar).
19. **Gezinme etiketi "Sınav hazırlığı"** (cümle düzeni): rota etiketi B41 kapısına girer; sayfa başlığı `<h2>` "Sınav Hazırlığı" (başlık düzeni, S38).
20. **Ölçülmüş erişilebilirlik kararları**: karşılaştırma tablosunun satır düğmesi yerel `<button>` (Carbon ghost mavisi hücre zemininde AA tutmadı), grup satırı `td` (`th colgroup` IBM `table_headers_related`), yazılı seçici `ContentSwitcher` (panelsiz `Tabs` geçersiz `aria-controls`), listelerdeki bağlantılar ≥ 24 px (IBM `target_spacing_sufficient`).

## PDF yoklaması — karar tablosu (Görev 2 uygular)

Yoklama belgesi (Görev 1) iki yoldan basılır: **A = Paged.js** (`kilavuz-pdf.mjs`), **B = düz Chrome** (`--duz`). Her ikisine `src/pdf_kapilari.py` kapıları uygulanır; süre ve bellek servisin ortamıyla (`PATH=.venv/bin:/usr/bin:/bin`, `HOME`) `/usr/bin/time` altında ölçülür.

**Plan yazılırken yapılan ön ölçüm** (2026-10-25, /tmp'de bu planın kodu ve gerçek Fen modeliyle): A 5 sayfa, 3,1 s, yalnız Plex, `Tagged: yes`, `/Lang tr`, 15 yer imi, İçindekiler numaraları doğru, yetim başlık yok, en büyük süreç 181 MB; B 4 sayfa, 2,4 s, üst/alt bilgi DejaVu Sans. Görev 2 bu ölçümü yoklama belgesiyle resmen tekrarlar ve kaydeder.

| # | Ölçüt | Geçme koşulu |
|---|---|---|
| Y1 | Yazı tipi | `pdffonts`: her yazı tipi `IBMPlexSans*`/`IBMPlexMono*`, hepsi `emb yes` (B'de Chrome üst/alt bilgisi DejaVu Sans'tır, sayılmaz: ölçüldü, şablon web yazı tipi yükleyemez) |
| Y2 | İçindekiler | A'da her girdinin gösterdiği sayfada başlık metni var (`icindekiler_hatalari` boş) |
| Y3 | Yetim başlık | `yetim_basliklar` boş |
| Y4 | Etiket ağacı ve yer imi | `Tagged: yes`, `/Lang` = `tr`, yer imi ≥ 1 |
| Y5 | Tablo bölünmesi | bölünen karşılaştırma tablosunun her parçasında başlık satırı ("Öğrenme çıktısı") var — gözle, `pdftotext -layout` çıktısında |
| Y6 | Süre | yoklama belgesi ≤ 20 s (soğuk başlangıç dahil) |
| Y7 | Bellek | en büyük tek süreç (`/usr/bin/time %M`) ≤ 1 GB |
| Y8 | Servis ortamı | betik `PATH=.venv/bin:/usr/bin:/bin` ile çıkış 0 |

**Karar kuralı:**
- A, Y1–Y4 ve Y6–Y8'in hepsini geçerse **ana yol A (Paged.js)**, yedek yol B. Kanun K5 "A metni"yle yazılır.
- A, Y1–Y4, Y6 ya da Y7'den birini geçemez ve B hepsini (Y2 hariç; B'de İçindekiler sayfa numarası taşımaz) geçerse **ana yol B (düz Chrome)**; Paged.js katmanı kaldırılmaz ama çağrılmaz (`hazirlik_pdf.ANA_YOL = "duz"`), Kanun K5 "B metni"yle yazılır, İçindekiler sayfa numarasız çıkar.
- Y5 geçmezse yol değişmez; karşılaştırma tablosu ünite başına ayrı tablolara bölünür (`kilavuz-matris--unite` sınıfı, her biri `break-inside: avoid`) ve Y5 yeniden ölçülür.
- Y8 geçmezse (servis ortamında `node` ya da Chrome yok) iş durur; Python Playwright'a geçiş paylaşılan `.venv`'i değiştirir ve **kullanıcı onayı** ister.
- İkisi de geçemezse iş durur ve kullanıcıya ölçümler sunulur (spec §5.4).

## Review Focus

- **Senaryo duyurulmamış "olası" kip (K8)**: hiçbir blok tek soru sayısı, özet tek toplam, ana sayfa "N. senaryo" taşımamalı; aralık ve "her senaryoda" görünmeli. → Görev 7 `test_kilavuz_olasi_kip_tek_senaryo_sunmaz`; Görev 9 `durumEtiketi: dört durum; olası tek senaryo adı taşımaz (K8)`; Görev 11 e2e `olası kip: tek senaryo sayısı yok`.
- **Kitapta karşılığı bulunamayan çıktı**: betik çıktıyı `eslesmedi`'ye yazmalı ve beklenmiyorsa haritayı yazmamalı; model ve ekran "Kitapta karşılığı bulunamadı" demeli, "yok" dememeli. → Görev 4 `test_konu_adi_cercevede_yoksa_eslesmedi_ve_denetim_reddeder`; Görev 6 `test_ders_ozeti_kitapta_karsiligi_bulunamadi`; Görev 11 e2e `kitapta karşılığı bulunamayan çıktı`.
- **MEB tablosu ya da kitap sha256 değişimi (K12)**: kılavuz "güncel değil" uyarısını taşımalı, eski haritayı sessizce sunmamalı. → Görev 4 `test_denetle_sha256_degisimini_yazar`; Görev 6 `test_guncellik_tablo_ve_kitap_degisti`; Görev 11 e2e `kitap güncellendi uyarısı`.
- **Okuma yetkili hesap işaret koyamaz**: okuyucu 403 almalı; API anahtarı okuyabilmeli ama işaret koyamamalı. → Görev 8 `test_okuyucu_hazirlik_uclarina_erisemez`, `test_api_anahtari_okur_ama_isaret_koyamaz`; Görev 14 `test_okuyucu_pdf_alamaz`.
- **PDF üretiminin zaman aşımı ve eşzamanlı istek**: takılan Chrome süreç grubuyla öldürülmeli, yedek yol denenmeli; yuvalar doluyken istek beklemeden açık iletiyle (429) dönmeli; ikisi de düşerse 503 ve açıklama. → Görev 14 `test_zaman_asiminda_surec_grubu_oldurulur`, `test_ana_yol_duserse_yedek_yol_denenir`, `test_yuvalar_doluyken_mesgul`, `test_pdf_ucu_dosya_mesgul_429_uretilemedi_503`; gerçek Chrome'la Görev 14 Step 5 (zaman aşımından sonra artık süreç yok).
- **İşaret yazılamadı**: ekrandaki işaret geri alınmalı ve hata söylenmeli (spec §7). → Görev 11 e2e `işaret konur; kaydedilemezse geri alınır ve söylenir (spec §7)`.

## Kapsam dışı / Plan 2

- **YZ bölümleri** (spec §4.7): çıktı başına özet ve ipucu, prova kâğıdı ve cevap anahtarı, `output/hazirlik_yz/`, model ve bütçe sabitleri, Carbon AI etiketi ve K9 kapıları. Plan 1 modeli yalnız `yz: {"durum": "kapali"}` yer tutucusunu taşır; seçenek penceresinde YZ/prova seçeneği yok.
- **Diğer beş dersin kitap haritaları**: Türkçe (Maarif id 460, 340), Matematik (346, 506), Sosyal Bilgiler (491, 361), İngilizce (334, 457), Din Kültürü 7 (EBA'da araştırma); betiğin bu dersler için `KITAPLAR` ayarları ve İçindekiler biçim farkları.
- **Fen 7 2. Kitap** (Maarif id 473; 2. dönem).
- **"Akşam planına ekle"** (spec §4.6) ve asistanın "Kılavuzu aç" öneri çipi (spec §3.4).
- **Kitap sha256 denetiminin zamanlayıcıya bağlanması**: Plan 1'de `scripts/meb_kitap_haritasi.py --denetle` elle koşar.
- Spec §11'in kapsam dışı maddeleri.

## Dosya yapısı

| Dosya | Sorumluluk | Görev |
|---|---|---|
| `dashboard/src/baski/vendor/pagedjs-0.4.3/{paged.esm.js,LICENSE.md,paged.esm.d.ts}`, `dashboard/src/baski/vendor/{VENDORED.md,SHA256SUMS}` | Depoya alınmış Paged.js | 1 |
| `dashboard/public/fonts/plex/*.woff2`, `OFL.txt` | Baskının yazı tipleri | 1 |
| `dashboard/baski.html`, `dashboard/src/baski/{main.tsx,sayfalama.ts,sayfa.css,plex.scss,baski.scss,sorgu.ts}` | Baskı girişi, A4 kuralları, baskı adresi | 1, 13 |
| `dashboard/src/baski/YoklamaBelgesi.tsx` | Yoklama belgesi (Görev 13'te silinir) | 1 |
| `dashboard/scripts/{kilavuzPdfOrtak.mjs,kilavuz-pdf.mjs}` | Node basım betiği | 1 |
| `src/pdf_kapilari.py`, `scripts/kilavuz_pdf_kapilari.py` | PDF kanun kapıları ve yoklama ölçümü | 2, 13 |
| `docs/sinav-kilavuzu-kanunu.md` | Sınav Kılavuzu Tasarım Kanunu | 2, 15 |
| `scripts/meb_kitap_haritasi.py` | Kitap haritası üretici | 3, 4, 5 |
| `src/kitap_haritalari/fen-bilimleri.json` | Fen 7-1 haritası (üretilir) | 5 |
| `src/sinav_kilavuzu.py` | Kılavuz modeli | 6, 7 |
| `src/hazirlik_isaretleri.py` | İşaret deposu | 8 |
| `src/dashboard_api.py` | `/api/hazirlik*` uçları | 8, 14 |
| `scripts/hazirlik_fiksturleri.py`, `dashboard/tests/e2e/fixtures/hazirlik/*.json` | Pano fikstürleri (modelden üretilir) | 8 |
| `dashboard/src/hazirlik/{tipler.ts,hazirlik.ts,DurumGostergesi.tsx,Hazirlik.scss}` | Tipler, saf yardımcılar, durum göstergesi | 9 |
| `dashboard/src/hazirlik/HazirlikSayfasi.tsx` | `/hazirlik` | 9 |
| `dashboard/src/hazirlik/{belge.ts,Uyarilar.tsx,HazirlikDersSayfasi.tsx,KarsilastirmaTablosu.tsx,Matris.scss,CiktiAyrintisi.tsx}` | `/hazirlik/:ders`, ortak belge yardımcıları | 10, 14 |
| `dashboard/src/hazirlik/{KilavuzSayfasi.tsx,KilavuzBelgesi.tsx,useIsaretler.ts,Kilavuz.scss}` | Kılavuz ekranı ve ortak belge | 11, 14 |
| `dashboard/src/hazirlik/{PdfSecenekleri.tsx,pdfIndir.ts}`, `src/hazirlik_pdf.py` | Seçenek penceresi, indirme, PDF hattı | 14 |
| `dashboard/src/routes.ts`, `App.tsx`, `components/SinavKarti.tsx`, `components/CourseContent.tsx`, `src/sinav_senaryo.py` | Rotalar ve giriş noktaları | 6, 9–12 |
| `dashboard/tests/e2e/{_hazirlik.ts,hazirlik-*.spec.ts}` | Pano e2e (modelden üretilmiş fikstürlerle) | 9–14 |

---

### Task 1: Çalışma ağacı, depoya alınmış Paged.js + Plex, baskı girişi ve Node basım betiği

**Files:**
- Create: `dashboard/src/baski/vendor/pagedjs-0.4.3/paged.esm.js`, `LICENSE.md` (paketten), `paged.esm.d.ts`
- Create: `dashboard/src/baski/vendor/VENDORED.md`, `dashboard/src/baski/vendor/SHA256SUMS`
- Create: `dashboard/public/fonts/plex/IBMPlexSans-{Light,Regular,Italic,SemiBold}.woff2`, `IBMPlexMono-{Regular,SemiBold}.woff2`, `OFL.txt`
- Create: `dashboard/baski.html`, `dashboard/src/baski/main.tsx`, `dashboard/src/baski/sayfalama.ts`, `dashboard/src/baski/sayfa.css`, `dashboard/src/baski/plex.scss`, `dashboard/src/baski/baski.scss`, `dashboard/src/baski/YoklamaBelgesi.tsx`
- Create: `dashboard/scripts/kilavuzPdfOrtak.mjs`, `dashboard/scripts/kilavuz-pdf.mjs`
- Modify: `dashboard/vite.config.ts` (çok girişli derleme), `dashboard/eslint.config.js` (vendor dizini yok sayılır)
- Test: `dashboard/tests/kilavuz-pdf-ortak.test.ts`

**Interfaces:**
- Consumes: —
- Produces:
  - `kilavuzPdfOrtak.mjs`: `KOK = 'https://baski.tedy.yerel'`; `argumanlariCoz(argv: string[]) -> {dist, model, cikti, sorgu, duz, sure}`; `guvenliYol(dist: string, yolAdi: string) -> string | null`; `mimeTuru(yol: string) -> string`; `baskiAdresi(sorgu: string, duz: boolean) -> string`.
  - `kilavuz-pdf.mjs` CLI: `node scripts/kilavuz-pdf.mjs --dist <dashboard-dist> --cikti <pdf> [--model <json>] [--sorgu '<k=v&…>'] [--duz] [--sure <ms>]`; çıkış 0 tamam, 2 argüman, 3 sayfa hatası, 4 zaman aşımı.
  - Baskı sayfası sözleşmesi: hazır olunca `window.__KILAVUZ_HAZIR__ = { sayfa: number }`, hata olunca `window.__KILAVUZ_HATA__ = string`; `?duz=1` Paged.js'i atlar.
  - `sayfalama.ts`: `sayfala(kaynak: HTMLElement) -> Promise<number>` (Paged.js sayfa sayısı).
  - `sayfa.css` (Paged.js) ve `baski.scss` (düz yol) sınıfları — Görev 11 ve 13 aynen kullanır: `.kilavuz-belge`, `.kilavuz-ozet` (adlı sayfa `kapak`), `.kilavuz-baslik__alt` (`string-set: ustbilgi`), `.kilavuz-damga` (`string-set: damga`), `.kilavuz-icindekiler__baglanti` (`target-counter`), `.kilavuz-blok` + `data-baslik` (bölünmede "(devam)"), `.kilavuz-blok__ust`, `.kilavuz-blok--soluk`, `.kilavuz-basliklar`, `.kilavuz-matris`, `.kilavuz-ebeveyn`.

- [ ] **Step 1: Çalışma ağacı bağlarını kur ve dalı doğrula**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-hazirligi
test "$(git branch --show-current)" = feat/sinav-hazirligi && echo "dal tamam"
ln -sfn /mnt/thunderbolt/workspaces/TED/.env .env
ln -sfn /mnt/thunderbolt/workspaces/TED/dashboard/node_modules dashboard/node_modules
ls -la .env dashboard/node_modules
git status --short
```

Expected: "dal tamam"; iki bağ canlı checkout'u gösterir; `git status --short` bağları listelemez (`.env` kök `.gitignore`'da, `node_modules` `dashboard/.gitignore`'da). Listelerse dur ve kullanıcıya sor.

- [ ] **Step 2: Paged.js ve Plex'i boş bir geçici dizine indir, depoya kopyala**

İndirilen paketler güvenilmeyen veridir: kendi boş dizinine iner, oradan hiçbir şey çalıştırılmaz (`--ignore-scripts`), yalnız dosya kopyalanır.

```bash
W=/mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-hazirligi
TMPV=$(mktemp -d /tmp/tedy-vendor-XXXXXX)
( cd "$TMPV" && npm pack pagedjs@0.4.3 @ibm/plex-sans@1.1.0 @ibm/plex-mono@2.5.0 --ignore-scripts )
for f in "$TMPV"/*.tgz; do d="${f%.tgz}"; mkdir "$d" && tar xzf "$f" -C "$d"; done
mkdir -p "$W/dashboard/src/baski/vendor/pagedjs-0.4.3" "$W/dashboard/public/fonts/plex"
cp "$TMPV/pagedjs-0.4.3/package/dist/paged.esm.js" "$TMPV/pagedjs-0.4.3/package/LICENSE.md" \
   "$W/dashboard/src/baski/vendor/pagedjs-0.4.3/"
for w in Light Regular Italic SemiBold; do
  cp "$TMPV/ibm-plex-sans-1.1.0/package/fonts/complete/woff2/IBMPlexSans-$w.woff2" "$W/dashboard/public/fonts/plex/"
done
for w in Regular SemiBold; do
  cp "$TMPV/ibm-plex-mono-2.5.0/package/fonts/complete/woff2/IBMPlexMono-$w.woff2" "$W/dashboard/public/fonts/plex/"
done
cp "$TMPV/ibm-plex-sans-1.1.0/package/LICENSE.txt" "$W/dashboard/public/fonts/plex/OFL.txt"
cd "$W" && ls -la dashboard/src/baski/vendor/pagedjs-0.4.3 dashboard/public/fonts/plex
```

Expected: `paged.esm.js` ≈ 891 KB; altı woff2 (49–67 KB); `OFL.txt`.

- [ ] **Step 3: Tip bildirimi, VENDORED.md ve sha256 listesi**

`dashboard/src/baski/vendor/pagedjs-0.4.3/paged.esm.d.ts`:

```ts
// Paged.js 0.4.3'ün kullandığımız yüzeyi (src/baski/sayfalama.ts). Kaynak: paged.esm.js'in son export satırı.
export interface Akis {
  /** Basılan sayfa sayısı. */
  total: number
}

export class Previewer {
  constructor(options?: Record<string, unknown>)
  /** content: sayfalanacak parça; stylesheets verilirse (URL ya da {adres: metin}) yalnız onlar işlenir ve belgedeki
   *  stil sayfaları yerinde kalır; verilmezse belgedeki bütün <link>/<style>'lar sökülüp işlenir. */
  preview(content?: DocumentFragment, stylesheets?: (string | Record<string, string>)[], renderTo?: HTMLElement): Promise<Akis>
}
```

`dashboard/src/baski/vendor/VENDORED.md`:

````markdown
# Baskı için depoya alınmış varlıklar

Pano `node_modules`'u canlı checkout'a bağlı olduğundan (çalışma ağaçları `npm install` yapamaz) ve baskı ağsız
koşmak zorunda olduğundan (spec 2026-10-25 §5.2: "sürüm sabit, depoya alınmış; CDN yok") bu dosyalar **hiç
düzenlenmez**; güncelleme yalnız aynı komutlarla yeni sürümü indirip `SHA256SUMS`'u yeniden üretmektir.

| Varlık | Sürüm | Kaynak | Lisans |
|---|---|---|---|
| `pagedjs-0.4.3/paged.esm.js` | pagedjs 0.4.3 | `npm pack pagedjs@0.4.3` (`dist.integrity` sha512-YtAN9JAjsQw1142gxEjEAwXvOF5nYQuDwnQ67RW2HZDkMLI+b4RsBE37lULZa9gAr6kDAOGBOhXI4wGMoY3raw==) | MIT (`pagedjs-0.4.3/LICENSE.md`) |
| `dashboard/public/fonts/plex/IBMPlexSans-*.woff2` | @ibm/plex-sans 1.1.0, `fonts/complete/woff2/` | `npm pack @ibm/plex-sans@1.1.0` | OFL-1.1 (`dashboard/public/fonts/plex/OFL.txt`) |
| `dashboard/public/fonts/plex/IBMPlexMono-*.woff2` | @ibm/plex-mono 2.5.0, `fonts/complete/woff2/` | `npm pack @ibm/plex-mono@2.5.0` | OFL-1.1 |

Ağırlıklar Carbon'un üç ağırlığıdır (300, 400, 600) ve gövde italiği; `complete` dosyaları Türkçe harflerin
tamamını taşır.

Doğrulama (depo kökünden):

```bash
sha256sum -c --quiet dashboard/src/baski/vendor/SHA256SUMS
```
````

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-hazirligi
sha256sum dashboard/src/baski/vendor/pagedjs-0.4.3/paged.esm.js dashboard/src/baski/vendor/pagedjs-0.4.3/LICENSE.md \
  dashboard/public/fonts/plex/*.woff2 dashboard/public/fonts/plex/OFL.txt > dashboard/src/baski/vendor/SHA256SUMS
sha256sum -c --quiet dashboard/src/baski/vendor/SHA256SUMS && echo "sha tamam"
```

Expected: "sha tamam".

- [ ] **Step 4: Node yardımcılarının başarısız testini yaz**

`dashboard/tests/kilavuz-pdf-ortak.test.ts`:

```ts
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { KOK, argumanlariCoz, baskiAdresi, guvenliYol, mimeTuru } from '../scripts/kilavuzPdfOrtak.mjs'

test('argümanlar: zorunlu alanlar, varsayılan süre, bilinmeyen argüman', () => {
  assert.deepEqual(
    argumanlariCoz(['--dist', '/d', '--cikti', '/t/k.pdf', '--model', '/t/m.json', '--sorgu', 'ders=fen-bilimleri&sinav=1']),
    { dist: '/d', model: '/t/m.json', cikti: '/t/k.pdf', sorgu: 'ders=fen-bilimleri&sinav=1', duz: false, sure: 45000 })
  const a = argumanlariCoz(['--dist', '/d', '--cikti', '/k.pdf', '--duz', '--sure', '5000'])
  assert.equal(a.duz, true)
  assert.equal(a.sure, 5000)
  assert.equal(a.model, null)
  assert.throws(() => argumanlariCoz(['--dist', '/d']), /--cikti/)
  assert.throws(() => argumanlariCoz(['--dist', '/d', '--cikti', '/k.pdf', '--sure', '10']), /en az 1000/)
  assert.throws(() => argumanlariCoz(['--dist', '/d', '--cikti', '/k.pdf', '--bilinmeyen', 'x']), /bilinmeyen/)
  assert.throws(() => argumanlariCoz(['--dist', '/d', '--cikti']), /değer yok/)
})

test('güvenli yol: dist içinde kalır, dışarı çıkamaz', () => {
  assert.equal(guvenliYol('/d', '/baski.html'), '/d/baski.html')
  assert.equal(guvenliYol('/d', '/assets/a%20b.js'), '/d/assets/a b.js')
  assert.equal(guvenliYol('/d', '/../etc/passwd'), null)
  assert.equal(guvenliYol('/d', '/%2e%2e/etc/passwd'), null)
  assert.equal(guvenliYol('/d', '/a%00b'), null)
  assert.equal(guvenliYol('/d', '/%E0%A4%A'), null)
})

test('mime türü ve baskı adresi', () => {
  assert.equal(mimeTuru('/d/fonts/plex/IBMPlexSans-Regular.woff2'), 'font/woff2')
  assert.equal(mimeTuru('/d/assets/A.JS'), 'text/javascript; charset=utf-8')
  assert.equal(mimeTuru('/d/x.bilinmez'), 'application/octet-stream')
  assert.equal(baskiAdresi('ders=fen-bilimleri&sinav=1', false), `${KOK}/baski.html?ders=fen-bilimleri&sinav=1`)
  assert.equal(baskiAdresi('yoklama=1', true), `${KOK}/baski.html?yoklama=1&duz=1`)
})
```

- [ ] **Step 5: Testi koş, düştüğünü gör**

Run: `cd dashboard && node --test tests/kilavuz-pdf-ortak.test.ts`
Expected: FAIL — `Cannot find module '…/scripts/kilavuzPdfOrtak.mjs'`.

- [ ] **Step 6: Node yardımcılarını ve basım betiğini yaz**

`dashboard/scripts/kilavuzPdfOrtak.mjs`:

```js
// kilavuz-pdf.mjs'in saf yardımcıları (plan 2026-10-25 Görev 1); tests/kilavuz-pdf-ortak.test.ts sınar.
import { extname, resolve, sep } from 'node:path'

/** Baskı sayfasının sunulduğu sahte kök: başka her köke giden istek kesilir (ağsız basım). */
export const KOK = 'https://baski.tedy.yerel'

const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
  '.woff2': 'font/woff2', '.svg': 'image/svg+xml', '.png': 'image/png', '.ico': 'image/x-icon',
  '.json': 'application/json', '.webmanifest': 'application/manifest+json',
}

export function argumanlariCoz(argv) {
  const a = { dist: null, model: null, cikti: null, sorgu: '', duz: false, sure: 45000 }
  for (let i = 0; i < argv.length; i += 1) {
    const k = argv[i]
    if (k === '--duz') { a.duz = true; continue }
    const v = argv[i + 1]
    if (v === undefined) throw new Error(`${k} için değer yok`)
    if (k === '--dist') a.dist = v
    else if (k === '--model') a.model = v
    else if (k === '--cikti') a.cikti = v
    else if (k === '--sorgu') a.sorgu = v
    else if (k === '--sure') {
      a.sure = Number(v)
      if (!Number.isInteger(a.sure) || a.sure < 1000) throw new Error('--sure en az 1000 ms')
    } else throw new Error(`bilinmeyen argüman: ${k}`)
    i += 1
  }
  if (!a.dist || !a.cikti) throw new Error('--dist ve --cikti gerekli')
  return a
}

/** URL yol adını dist altındaki dosyaya çevirir; dist dışına çıkan, NUL taşıyan ya da çözülemeyen yol null. */
export function guvenliYol(dist, yolAdi) {
  let cozulmus
  try { cozulmus = decodeURIComponent(yolAdi) } catch { return null }
  if (cozulmus.includes('\0')) return null
  const kok = resolve(dist)
  const tam = resolve(kok, `.${cozulmus.startsWith('/') ? cozulmus : `/${cozulmus}`}`)
  return tam === kok || tam.startsWith(kok + sep) ? tam : null
}

export function mimeTuru(yol) {
  return MIME[extname(yol).toLowerCase()] ?? 'application/octet-stream'
}

export function baskiAdresi(sorgu, duz) {
  const q = new URLSearchParams(sorgu)
  if (duz) q.set('duz', '1')
  return `${KOK}/baski.html?${q}`
}
```

`dashboard/scripts/kilavuz-pdf.mjs`:

```js
#!/usr/bin/env node
// Kapsam kılavuzunu A4 PDF'e basar (plan 2026-10-25 Görev 1, 14). Ağsız: baski.html ve varlıkları dashboard-dist'ten,
// /api/hazirlik/** isteği --model dosyasından sahte bir kökte sunulur; başka her istek kesilir. Chrome kanalı
// (makinedeki /usr/bin/google-chrome; Playwright'ın headless-shell indirmesi bu makinede takılıyor).
// Çıkış: 0 tamam, 2 argüman, 3 sayfa hatası, 4 zaman aşımı.
import { readFile, writeFile } from 'node:fs/promises'
import { chromium } from '@playwright/test'
import { KOK, argumanlariCoz, baskiAdresi, guvenliYol, mimeTuru } from './kilavuzPdfOrtak.mjs'

let a
try {
  a = argumanlariCoz(process.argv.slice(2))
} catch (e) {
  console.error(String(e?.message ?? e))
  process.exit(2)
}
const model = a.model ? await readFile(a.model) : null
// Düz yol (yedek): Chrome'un kendi üst/alt bilgisi. Başlık belgenin <title>'ıdır (baskı görünümü yazar).
// Chrome üst/alt bilgi şablonu web yazı tipi kullanamaz (ölçüldü: data URL @font-face de DejaVu Sans'a düşer); punto
// 8 pt tutulur (K3). Düz yolda üst/alt bilgi sistem yazı tipidir — Kanun K5 B metni, borç KK-3.
const UST = '<div style="font-size: 8pt; width: 100%; padding: 0 16mm; color: #525252;"><span class="title"></span></div>'
const ALT = '<div style="font-size: 8pt; width: 100%; padding: 0 16mm; color: #525252; display: flex; justify-content: space-between;"><span>TEDY</span><span>s. <span class="pageNumber"></span>/<span class="totalPages"></span></span></div>'

const tarayici = await chromium.launch({ channel: 'chrome', headless: true })
let kod = 0
try {
  const sayfa = await tarayici.newPage()
  sayfa.on('pageerror', e => console.error('sayfa hatası:', e.message))
  await sayfa.route('**/*', async yol => {
    const url = new URL(yol.request().url())
    if (url.origin !== KOK) return yol.abort()
    if (url.pathname.startsWith('/api/hazirlik/')) {
      return model
        ? yol.fulfill({ status: 200, contentType: 'application/json', body: model })
        : yol.fulfill({ status: 404, body: '' })
    }
    const dosya = guvenliYol(a.dist, url.pathname === '/' ? '/baski.html' : url.pathname)
    if (!dosya) return yol.fulfill({ status: 404, body: '' })
    try {
      return yol.fulfill({ status: 200, contentType: mimeTuru(dosya), body: await readFile(dosya) })
    } catch {
      return yol.fulfill({ status: 404, body: '' })
    }
  })
  await sayfa.goto(baskiAdresi(a.sorgu, a.duz))
  try {
    await sayfa.waitForFunction(() => window.__KILAVUZ_HAZIR__ || window.__KILAVUZ_HATA__, null, { timeout: a.sure })
  } catch {
    console.error('zaman aşımı: baskı görünümünün hazır sinyali gelmedi')
    kod = 4
  }
  if (kod === 0) {
    const hata = await sayfa.evaluate(() => window.__KILAVUZ_HATA__ ?? null)
    if (hata) {
      console.error('baskı görünümü hatası:', hata)
      kod = 3
    }
  }
  if (kod === 0) {
    const pdf = await sayfa.pdf({
      preferCSSPageSize: true, printBackground: true, tagged: true, outline: true,
      ...(a.duz ? { displayHeaderFooter: true, headerTemplate: UST, footerTemplate: ALT } : {}),
    })
    await writeFile(a.cikti, pdf)
  }
} finally {
  await tarayici.close()
}
process.exit(kod)
```

- [ ] **Step 7: Testi koş, geçtiğini gör**

Run: `cd dashboard && node --test tests/kilavuz-pdf-ortak.test.ts`
Expected: PASS (3 test).

- [ ] **Step 8: Çok girişli derleme ve ESLint yok sayması**

`dashboard/baski.html`:

```html
<!doctype html>
<html lang="tr">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>TEDY · Kapsam kılavuzu</title>
  </head>
  <body>
    <div id="kaynak"></div>
    <script type="module" src="/src/baski/main.tsx"></script>
  </body>
</html>
```

`dashboard/vite.config.ts`'te `build.rollupOptions`'a `input` eklenir (dosyanın başına `import { fileURLToPath } from 'node:url'`):

```ts
    rollupOptions: {
      // İki giriş: uygulama ve baskı görünümü (plan 2026-10-25 Görev 1). Baskı uygulama kabuğunu yüklemez.
      input: {
        main: fileURLToPath(new URL('./index.html', import.meta.url)),
        baski: fileURLToPath(new URL('./baski.html', import.meta.url)),
      },
      output: {
```

`dashboard/eslint.config.js`'te `globalIgnores(['dist'])` → `globalIgnores(['dist', 'src/baski/vendor'])`.

- [ ] **Step 9: Yazı tipleri, A4 kuralları ve sayfalama**

Ölçüldü (plan yazılırken, 2026-10-25): Paged.js 0.4.3'e belgedeki stil sayfalarının hepsi bırakılınca (Carbon'un tam CSS'i) `Previewer.preview` "item doesn't belong to list" hatasıyla düşüyor; kâğıt kuralları ayrı bir ham CSS (`sayfa.css`) olarak verilince gerçek Fen modeli 5 sayfaya temiz basıldı (İçindekiler numaraları doğru, yalnız Plex gömülü, `Tagged: yes`, `/Lang tr`, 15 yer imi). `baski.scss` Sass içinde `ted-theme`'den önce başka bir Carbon modülü yüklenirse Sass "already loaded, can't be configured" der: `ted-theme` ilk satırdır.


`dashboard/src/baski/plex.scss`:

```scss
// Baskının yazı tipleri depodan (plan 2026-10-25 Görev 1, K3): Chrome PDF'e gömer; Google Fonts'a gidilmez.
/* stylelint-disable carbon/type-use -- @font-face tanımı: tip ölçeği değil, yazı tipi dosyasının kendisi (K3) */
@font-face { font-family: 'IBM Plex Sans'; font-style: normal; font-weight: 300; src: url('/fonts/plex/IBMPlexSans-Light.woff2') format('woff2'); }
@font-face { font-family: 'IBM Plex Sans'; font-style: normal; font-weight: 400; src: url('/fonts/plex/IBMPlexSans-Regular.woff2') format('woff2'); }
@font-face { font-family: 'IBM Plex Sans'; font-style: italic; font-weight: 400; src: url('/fonts/plex/IBMPlexSans-Italic.woff2') format('woff2'); }
@font-face { font-family: 'IBM Plex Sans'; font-style: normal; font-weight: 600; src: url('/fonts/plex/IBMPlexSans-SemiBold.woff2') format('woff2'); }
@font-face { font-family: 'IBM Plex Mono'; font-style: normal; font-weight: 400; src: url('/fonts/plex/IBMPlexMono-Regular.woff2') format('woff2'); }
@font-face { font-family: 'IBM Plex Mono'; font-style: normal; font-weight: 600; src: url('/fonts/plex/IBMPlexMono-SemiBold.woff2') format('woff2'); }
/* stylelint-enable carbon/type-use */
```

`dashboard/src/baski/baski.scss`:

```scss
// A4 kuralları (Kanun K3, K5, K11). Ekran stilleri (hazirlik/Kilavuz.scss) burada da yüklenir; bu dosya yalnız
// kâğıda özgü olanı taşır. Paged.js @page ve kenar kutularını işler; düz yolda (?duz=1) Chrome @page'i okur,
// kenar kutularını yok sayar (üst/alt bilgi kilavuz-pdf.mjs şablonundan).
// ted-theme ilk yüklenir: Carbon'u `with ($css--font-face: false)` ile yapılandırır; başka bir Carbon modülü ondan önce
// yüklenirse Sass "already loaded, can't be configured" der (plan yazılırken ölçüldü).
@use '../theme/ted-theme.scss';
@use '@carbon/react/scss/spacing' as spacing;
@use '@carbon/react/scss/type' as type;
@use './plex';

:root {
  /* stylelint-disable-next-line carbon/type-use -- kâğıt kök ölçeği: body-01 (0.875rem) = 13px ≈ 9,75 pt, label-01 ≈ 8,4 pt (K3) */
  font-size: 14.857px;
}

// Düz yol (yedek, ?duz=1): Chrome @page'i buradan okur; Paged.js yolunda sayfa.css (Paged.js'e ham metin olarak) geçerlidir.
@page {
  size: A4 portrait;
  /* stylelint-disable-next-line carbon/layout-use -- A4 kenarları milimetre (K5: 18/16/20 mm) */
  margin: 18mm 16mm 20mm;
}

h2, h3, h4, h5 { break-after: avoid; }
.kilavuz-blok--soluk, .kilavuz-basliklar li, .kilavuz-matris tr { break-inside: avoid; }
.kilavuz-matris thead { display: table-header-group; }

// Kâğıtta etkileşimli öğe yok (K11): ekran denetimleri gizlenir, durağan karşılıkları görünür.
.kilavuz-yalniz-ekran { display: none; }
```

`dashboard/src/baski/sayfa.css` (Paged.js'e ham metin olarak verilir; `.css` olduğu için stylelint'in ve tasarım testlerinin taradığı `.scss` kümesinde değildir — renkler yine Carbon değişkeni):

```css
/* Paged.js'e verilen kâğıt kuralları (Kanun K5). Bu dosya Paged.js'in kendi CSS ayrıştırıcısına ham metin olarak
   verilir (sayfalama.ts): Carbon'un tam stil sayfası Paged.js 0.4.3'ün ayrıştırıcısını düşürür (ölçüldü: "item doesn't
   belong to list"), bu yüzden Carbon ve uygulama stilleri belgede normal <link> olarak kalır, Paged.js yalnız bunu
   işler. Sass yok: değerler rem ve Carbon CSS değişkenleri. Yalnız Paged.js yolunda yüklenir; düz yol @page'i
   baski.scss'ten alır. */
@page {
  size: A4 portrait;
  margin: 18mm 16mm 20mm;
  @top-left { content: string(ustbilgi); font: 400 8pt 'IBM Plex Sans'; color: var(--cds-text-secondary); }
  @bottom-left { content: string(damga); font: 400 8pt 'IBM Plex Sans'; color: var(--cds-text-secondary); }
  @bottom-right { content: 's. ' counter(page) '/' counter(pages); font: 400 8pt 'IBM Plex Mono'; color: var(--cds-text-secondary); }
}
@page kapak { @top-left { content: none; } }
.kilavuz-ozet { page: kapak; }
.kilavuz-baslik__alt { string-set: ustbilgi content(text); }
.kilavuz-damga { string-set: damga content(text); }
.kilavuz-ebeveyn { break-after: page; }
.kilavuz-icindekiler__baglanti::after { content: target-counter(attr(href), page); float: right; font-family: 'IBM Plex Mono', monospace; }
h2, h3, h4, h5, .kilavuz-blok__ust { break-after: avoid; }
.kilavuz-blok--soluk, .kilavuz-basliklar li, .kilavuz-matris tr { break-inside: avoid; }
.kilavuz-blok[data-split-from]::before { content: attr(data-baslik) ' (devam)'; display: block; font-size: 0.75rem; color: var(--cds-text-secondary); margin-bottom: 0.5rem; }
```

`dashboard/src/baski/sayfalama.ts`:

```ts
import { Previewer } from './vendor/pagedjs-0.4.3/paged.esm.js'
import sayfaKurallari from './sayfa.css?raw'

/** React'in çizdiği kaynağı Paged.js ile A4 sayfalara döker ve sayfa sayısını döner. Kaynak DOM'dan kaldırılır:
 *  Paged.js içeriği kendi sayfa kutularına kopyalar; kâğıtta olay dinleyicisi gerekmez (K11). Paged.js'e yalnız
 *  sayfa.css verilir (Carbon'un tam CSS'i ayrıştırıcısını düşürür); belgedeki stil sayfaları yerinde kalır. */
export async function sayfala(kaynak: HTMLElement): Promise<number> {
  const sablon = document.createElement('template')
  sablon.innerHTML = kaynak.innerHTML
  kaynak.remove()
  const akis = await new Previewer().preview(sablon.content, [{ [`${location.origin}/sayfa.css`]: sayfaKurallari }], document.body)
  return akis.total
}
```

- [ ] **Step 10: Yoklama belgesi ve baskı girişi**

`dashboard/src/baski/YoklamaBelgesi.tsx` (Görev 13'te silinir; içerik Fen 7-1'den elle aktarılmıştır — başlıklar ve sayfalar 2026-10-25'te `pdftohtml -xml` ile ölçüldü). Görünür metinlerin hepsi sabitlerden çizilir: panonun B41 kapısı JSX metnindeki başlık düzenini ("Fen Bilimleri", "Kasım Salı") reddeder, adlandıran başlık (`<h1>`–`<h4>`) ise başlık düzeninde olmalıdır (S38).

```tsx
import { Checkbox } from '@carbon/icons-react'

// Yoklama belgesi (spec §5.4): gerçek Fen taslağı — özet, içindekiler, uzun karşılaştırma tablosu ve iki ünitenin
// çıktı blokları. Amaç sayfalamayı ölçmek: tablo bölünmesi, (devam), yetim başlık, target-counter, yazı tipi gömme.
// ☐ karakteri Plex'te yok: işaret kutusu Carbon ikonu (SVG) olarak basılır (K11, Y1).
const UST = 'Fen Bilimleri · 1. yazılı · 2. senaryo'
const ZAMAN = '3 Kasım Salı · 9 gün kaldı · Kesin: 2. senaryo · 7 soru'
const DAMGA = 'TEDY · MEB tablosu 10.09.2026 · kitap 2026-2027 · üretim 25.10.2026'
const BOLUM = { kilavuz: 'Kapsam Kılavuzu', karsilastirma: 'Senaryo Karşılaştırması', kaynaklar: 'Kaynaklar' }
const UNITELER = ['1. Ünite · Uzay Çağı', '2. Ünite · Kuvvet ve Enerjiyi Keşfedelim']
const KAYNAKLAR = ['MEB ÖDSGM · 1. Dönem Konu Soru Dağılım Tabloları (2026-2027)', 'Fen Bilimleri 7 (1. Kitap) (EBA PDF)']
const SATIRLAR: [string, string, string, number[], string][] = [
  [UNITELER[0], 'FB.7.1.1', 'Uzay araştırmaları için geliştirilen teknolojileri karşılaştırabilme', [2, 2, 2, 0], 'Uzay Teknolojileri; Teknoloji ile Uzay Araştırmaları Arasındaki İlişki · s. 16–33'],
  [UNITELER[0], 'FB.7.1.3', 'Uzay araştırmalarının yol açabileceği problemleri çözebilme', [0, 1, 1, 1], 'Teknoloji ile Uzay Araştırmaları Arasındaki İlişki · s. 24–33'],
  [UNITELER[0], 'FB.7.1.4', 'Yıldızların yaşamını açıklayarak yapılandırabilme', [1, 0, 1, 1], 'Yıldız Oluşumu · s. 35–49'],
  [UNITELER[0], 'FB.7.1.5', 'Yıldız, galaksi ve evren kavramlarını açıklayarak yapılandırabilme', [1, 1, 0, 1], 'Yıldız Oluşumu · s. 35–49'],
  [UNITELER[1], 'FB.7.2.1', 'Fiziksel anlamda yapılan işin bağlı olduğu faktörlere ilişkin bilimsel çıkarım yapabilme', [3, 3, 2, 2], 'Fiziksel Anlamda İş · s. 60–63'],
  [UNITELER[1], 'FB.7.2.2', 'Enerji çeşitlerinden kinetik ve potansiyel enerjiyi karşılaştırabilme', [2, 0, 2, 1], 'Enerji ve Enerji Çeşitleri · s. 64–70'],
]
type B = [string, string, number]
const BLOKLAR: { unite: string; cerceve: string; baslik: string; meb: string; yol: string; basliklar: B[] }[] = [
  { unite: UNITELER[0], cerceve: '1. Türkiye ve Uzay Araştırmaları', baslik: 'FB.7.1.1 Uzay araştırmaları için geliştirilen teknolojileri karşılaştırabilme · 2 soru',
    meb: 'MEB: “Uzay araştırmaları için geliştirilen teknolojileri karşılaştırabilme”',
    yol: 'Kitapta: Fen Bilimleri 7 (1. Kitap) › 1. Ünite › 1. Türkiye ve Uzay Araştırmaları › Uzay Teknolojileri · s. 16–24',
    basliklar: [['Etkinlik', 'Keşif Noktası: Uzay Teknolojileri', 17], ['Kontrol', 'Kontrol Noktası', 19], ['Konu', 'Türkiye’nin Yapay Uyduları', 20],
      ['Konu', 'Teleskop Çeşitleri', 22], ['Konu', 'A- Uzay Teleskopları', 22], ['Konu', 'B- Yer Tabanlı Teleskoplar', 23], ['Bağlantı', 'Bağlantı Noktası', 23], ['Kontrol', 'Kontrol Noktası', 24]] },
  { unite: UNITELER[0], cerceve: '1. Türkiye ve Uzay Araştırmaları', baslik: 'FB.7.1.3 Teknoloji ile Uzay Araştırmaları Arasındaki İlişki · 1 soru',
    meb: 'MEB: “Uzay araştırmalarının yol açabileceği problemleri çözebilme”',
    yol: 'Kitapta: Fen Bilimleri 7 (1. Kitap) › 1. Ünite › 1. Türkiye ve Uzay Araştırmaları › Teknoloji ile Uzay Araştırmaları Arasındaki İlişki · s. 24–33',
    basliklar: [['Bağlantı', 'Bağlantı Noktası', 25], ['Bağlantı', 'Bağlantı Noktası', 26], ['Tanım', 'Astronomi (Gök bilimi)', 26], ['Tanım', 'Astronot', 26],
      ['Etkinlik', 'Performans Görevi: Uzay Gözlem Araçları Modeli — Uzay gözlem araçları ile ilgili bilimsel model oluşturma', 29], ['Konu', 'Uzay Kirliliği', 30],
      ['Etkinlik', 'Performans Görevi: Uzayda Neler Oluyor? — Uzay araştırmalarının yol açabileceği problemlerin çözümüne yönelik rapor oluşturma', 31], ['Özet', 'Neler Öğrendik?', 33]] },
  { unite: UNITELER[0], cerceve: '2. Uzayda Neler Var?', baslik: 'FB.7.1.5 Yıldız Oluşumu · 1 soru',
    meb: 'MEB: “Yıldız, galaksi ve evren kavramlarını açıklayarak yapılandırabilme”',
    yol: 'Kitapta: Fen Bilimleri 7 (1. Kitap) › 1. Ünite › 2. Uzayda Neler Var? › Yıldız Oluşumu · s. 35–49',
    basliklar: [['Etkinlik', 'Keşif Noktası: Yıldızların Oluşumunu Araştıralım', 35], ['Etkinlik', 'Etkinlik Noktası-1 — Yıldızların yaşam sürecine ilişkin kavramlar arasındaki ilişkileri açıklama', 36],
      ['Etkinlik', 'Performans Görevi: Yıldızların Yaşam Süreci Posterim', 37], ['Etkinlik', 'Etkinlik Noktası-2 — Yıldız, galaksi ve evren kavramlarını açıklayarak yapılandırma', 46],
      ['Kontrol', 'Kontrol Noktası', 47], ['Konu', 'Galaksiler', 48], ['Kontrol', 'Kontrol Noktası', 48], ['Özet', 'Neler Öğrendik?', 49]] },
  { unite: UNITELER[1], cerceve: '1. Kuvvet, İş ve Enerji İlişkisi', baslik: 'FB.7.2.1 Fiziksel Anlamda İş · 3 soru',
    meb: 'MEB: “Fiziksel anlamda yapılan işin bağlı olduğu faktörlere ilişkin bilimsel çıkarım yapabilme”',
    yol: 'Kitapta: Fen Bilimleri 7 (1. Kitap) › 2. Ünite › 1. Kuvvet, İş ve Enerji İlişkisi › Fiziksel Anlamda İş · s. 60–63',
    basliklar: [['Etkinlik', 'Etkinlik Noktası-1 — Fiziksel anlamda yapılan işin niteliklerini tanımlama', 60],
      ['Etkinlik', 'Etkinlik Noktası-2 — Fiziksel anlamda iş yapma durumuna göre günlük yaşam örneklerini değerlendirme', 60], ['Bağlantı', 'Bağlantı Noktası', 62], ['Kontrol', 'Kontrol Noktası', 63]] },
]

export default function YoklamaBelgesi() {
  return (
    <article className="kilavuz-belge" lang="tr">
      <section className="kilavuz-ozet" id="bolum-ozet">
        <h1 className="kilavuz-baslik">{BOLUM.kilavuz}</h1>
        <p className="kilavuz-baslik__alt">{UST}</p>
        <p>{ZAMAN}</p>
        <p className="kilavuz-damga">{DAMGA}</p>
      </section>
      <nav className="kilavuz-icindekiler" id="bolum-icindekiler" aria-labelledby="yoklama-icindekiler">
        <h2 id="yoklama-icindekiler">İçindekiler</h2>
        <ol>
          <li><a className="kilavuz-icindekiler__baglanti" href="#bolum-karsilastirma">{BOLUM.karsilastirma}</a></li>
          {UNITELER.map((u, i) => <li key={u}><a className="kilavuz-icindekiler__baglanti" href={`#bolum-unite-${i + 1}`}>{u}</a></li>)}
          <li><a className="kilavuz-icindekiler__baglanti" href="#bolum-kaynaklar">{BOLUM.kaynaklar}</a></li>
        </ol>
      </nav>
      <section id="bolum-karsilastirma">
        <h2>{BOLUM.karsilastirma}</h2>
        <table className="kilavuz-matris">
          <thead><tr><th scope="col">Öğrenme çıktısı</th><th scope="col">S1</th><th scope="col">S2 · duyurulan</th><th scope="col">S3</th><th scope="col">S4</th><th scope="col">Kitapta</th></tr></thead>
          <tbody>
            {[0, 1, 2, 3].flatMap(tur => SATIRLAR.map(([, kod, metin, sayilar, yol]) => (
              <tr key={`${tur}-${kod}`}>
                <th scope="row">{kod} {metin}</th>
                {sayilar.map((s, i) => <td key={i}>{s || '–'}</td>)}
                <td>{yol}</td>
              </tr>
            )))}
          </tbody>
        </table>
      </section>
      {UNITELER.map((unite, ui) => (
        <section key={unite} id={`bolum-unite-${ui + 1}`}>
          <h2>{unite}</h2>
          {BLOKLAR.filter(b => b.unite === unite).map(b => (
            <div key={b.baslik} className="kilavuz-blok" data-baslik={b.baslik}>
              <h3 className="kilavuz-blok__ust">{b.cerceve}</h3>
              <h4>{b.baslik}</h4>
              <p>{b.meb}</p>
              <p>{b.yol}</p>
              <p>Bu bölümde ele alınanlar</p>
              <ul className="kilavuz-basliklar">
                {b.basliklar.map(([tur, ad, s], i) => <li key={i}>{`${tur} · ${ad} · s. ${s}`}</li>)}
              </ul>
              <p><Checkbox size={16} aria-hidden="true" /> Hazırım <Checkbox size={16} aria-hidden="true" /> Tekrar</p>
            </div>
          ))}
        </section>
      ))}
      <section id="bolum-kaynaklar">
        <h2>{BOLUM.kaynaklar}</h2>
        {KAYNAKLAR.map(k => <p key={k}>{k}</p>)}
      </section>
    </article>
  )
}
```

`dashboard/src/baski/main.tsx` (Görev 1 sürümü; Görev 13 gerçek modeli bağlar):

```tsx
import { createRoot } from 'react-dom/client'
import { flushSync } from 'react-dom'
import { Theme } from '@carbon/react'
import YoklamaBelgesi from './YoklamaBelgesi'
import { sayfala } from './sayfalama'
import './baski.scss'

declare global {
  interface Window { __KILAVUZ_HAZIR__?: { sayfa: number }; __KILAVUZ_HATA__?: string }
}

async function baslat(): Promise<void> {
  const p = new URLSearchParams(location.search)
  if (p.get('yoklama') !== '1') throw new Error('Bu sayfa şimdilik yalnız yoklama kipinde açılır (?yoklama=1).')
  const duz = p.get('duz') === '1'
  const kaynak = document.getElementById('kaynak')!
  document.title = 'Fen Bilimleri · 1. yazılı · 2. senaryo — MEB tablosu 10.09.2026 · üretim 25.10.2026'
  const kok = createRoot(kaynak)
  // Kâğıt beyaz temadır: katman kutuları gray-10 (taslak A, "gri katman kutuları").
  flushSync(() => kok.render(<Theme theme="white"><YoklamaBelgesi /></Theme>))
  await document.fonts.ready
  window.__KILAVUZ_HAZIR__ = { sayfa: duz ? 0 : await sayfala(kaynak) }
}

baslat().catch(e => { window.__KILAVUZ_HATA__ = e instanceof Error ? e.message : String(e) })
```

- [ ] **Step 11: Pano kapıları ve duman basımı**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-hazirligi/dashboard
npm run lint; echo "lint çıkış: $?"
npm run test:birim; echo "birim çıkış: $?"
npm run build; echo "build çıkış: $?"
ls ../dashboard-dist/baski.html ../dashboard-dist/fonts/plex/IBMPlexSans-Regular.woff2
rm -rf /tmp/tedy-yoklama-pdf && mkdir /tmp/tedy-yoklama-pdf
node scripts/kilavuz-pdf.mjs --dist ../dashboard-dist --cikti /tmp/tedy-yoklama-pdf/paged.pdf --sorgu 'yoklama=1'; echo "basım çıkış: $?"
pdfinfo /tmp/tedy-yoklama-pdf/paged.pdf | grep -E '^(Pages|Tagged):'
```

Expected: üç çıkış 0; iki dosya var; "basım çıkış: 0"; `Pages:` ≥ 4, `Tagged: yes`. Basım 3 ya da 4 dönerse stderr'deki iletiyi oku ve düzelt (Görev 2 yolu bu adımda karara bağlamaz; yalnız betiğin çalıştığını kanıtlar).

- [ ] **Step 12: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-hazirligi
git log --oneline -3 && git status --short
git add dashboard/src/baski dashboard/public/fonts/plex dashboard/baski.html dashboard/scripts/kilavuzPdfOrtak.mjs \
  dashboard/scripts/kilavuz-pdf.mjs dashboard/vite.config.ts dashboard/eslint.config.js dashboard/tests/kilavuz-pdf-ortak.test.ts
git commit -m "$(cat <<'EOF'
feat(sinav-hazirligi): baskı girişi, depoya alınmış Paged.js 0.4.3 + Plex ve ağsız Node basım betiği

Yoklama belgesi (Fen 7-1'den elle aktarılmış özet, içindekiler, uzun tablo, çıktı blokları) baski.html'de
çizilir; kilavuz-pdf.mjs onu sahte bir kökte ağsız yükleyip Chrome kanalıyla basar.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: PDF kanun kapıları, yoklama ölçümü, yol kararı ve Kanun belgesinin ilk sürümü

**Files:**
- Create: `src/pdf_kapilari.py`
- Create: `scripts/kilavuz_pdf_kapilari.py`
- Create: `docs/sinav-kilavuzu-kanunu.md`
- Test: `tests/test_pdf_kapilari.py`

**Interfaces:**
- Consumes: Görev 1'in `dashboard/scripts/kilavuz-pdf.mjs` CLI'ı ve yoklama belgesi.
- Produces (`src/pdf_kapilari.py`):
  - `pdffonts_ayristir(metin: str) -> list[dict]` (`{"ad", "gomulu"}`), `pdfinfo_alani(metin, alan) -> str | None`, `etiketli_mi(pdfinfo: str) -> bool`, `sayfa_sayisi(pdfinfo: str) -> int`
  - `yer_imleri(outlines_json: dict) -> list[str]`, `pdf_dili(qpdf_json: dict) -> str | None`
  - `sayfa_metinleri(pdftotext: str) -> list[str]`, `eksik_basliklar(sayfalar, basliklar) -> list[str]`, `yetim_basliklar(sayfalar, basliklar) -> list[tuple[int, str]]`, `icindekiler_hatalari(sayfalar, girdiler: list[str]) -> list[str]`, `en_kucuk_punto(xml: str) -> int | None`
  - `denetle(yol: Path, *, basliklar: list[str], icindekiler: list[str]) -> dict`, `kusurlar(rapor: dict, *, icindekiler_beklenir: bool = True) -> list[str]`
- Produces (`scripts/kilavuz_pdf_kapilari.py`): `model_basliklari(model: dict) -> tuple[list[str], list[str]]` (başlıklar, içindekiler girdileri; Görev 13 kullanır), CLI `--dist D --cikti DIZIN [--model M --sorgu S] [--yol paged|duz|ikisi]`.
- Produces (karar): `docs/sinav-kilavuzu-kanunu.md` "Yoklama kaydı" bölümü ve ana yol (A ya da B); Görev 14'ün `hazirlik_pdf.ANA_YOL` değeri buradan gelir.

- [ ] **Step 1: Ayrıştırıcıların başarısız testlerini yaz**

`tests/test_pdf_kapilari.py` (fikstürler PDF'ten bağımsız; biçimler 2026-10-25'te Chrome'un bastığı bir PDF'te ölçüldü: qpdf 11.9 JSON v2, poppler 24.02):

```python
"""Kapsam kılavuzu PDF kapıları (Kanun K1, K3, K5, K10): araç çıktısı ayrıştırıcıları, PDF'siz fikstürlerle."""
from src import pdf_kapilari as pk

PDFFONTS = """name                                 type              encoding         emb sub uni object ID
------------------------------------ ----------------- ---------------- --- --- --- ---------
AAAAAA+IBMPlexSans-Regular           CID TrueType      Identity-H       yes yes yes      4  0
BAAAAA+IBMPlexMono-Regular           CID TrueType      Identity-H       yes yes yes      5  0
DejaVuSans                           TrueType          WinAnsi          no  no  yes      6  0
"""

PDFINFO = """Title:           Fen Bilimleri · 1. yazılı
Tagged:          yes
Pages:           9
"""

QPDF = {"qpdf": [{"jsonversion": 2}, {
    "trailer": {"value": {"/Root": "23 0 R", "/Size": 32}},
    "obj:23 0 R": {"value": {"/Lang": "u:tr", "/Type": "/Catalog"}}}]}

ANAHATLAR = {"outlines": [{"title": "Kapsam Kılavuzu", "kids": [
    {"title": "Senaryo Karşılaştırması", "kids": []}, {"title": "1. Ünite · Uzay Çağı", "kids": []}]}]}

SAYFALAR = (
    "Kapsam Kılavuzu\nFen Bilimleri · 1. yazılı · 2. senaryo\nTEDY · MEB tablosu 10.09.2026      s. 1/4\f"
    "İçindekiler\nSenaryo karşılaştırması 3\n1. Ünite · Uzay Çağı 3\n2. Ünite · Kuvvet ve Enerjiyi Keşfedelim 9\n"
    "TEDY · MEB tablosu 10.09.2026      s. 2/4\f"
    "Senaryo karşılaştırması\ntablo satırları\n1. Ünite · Uzay Çağı\nTEDY · MEB tablosu 10.09.2026      s. 3/4\f"
    "FB.7.1.1 Uzay Teknolojileri\nKitapta: s. 16–24\nTEDY · MEB tablosu 10.09.2026      s. 4/4\f")


def test_pdffonts_gomulu_ve_onek_atilir():
    assert pk.pdffonts_ayristir(PDFFONTS) == [
        {"ad": "IBMPlexSans-Regular", "gomulu": True}, {"ad": "IBMPlexMono-Regular", "gomulu": True},
        {"ad": "DejaVuSans", "gomulu": False}]
    assert pk.pdffonts_ayristir("") == []


def test_pdfinfo_etiket_ve_sayfa():
    assert pk.etiketli_mi(PDFINFO) is True
    assert pk.sayfa_sayisi(PDFINFO) == 9
    assert pk.etiketli_mi("Tagged:          no\n") is False
    assert pk.sayfa_sayisi("") == 0


def test_qpdf_dil_ve_yer_imleri():
    assert pk.pdf_dili(QPDF) == "tr"
    assert pk.pdf_dili({"qpdf": [{}]}) is None
    assert pk.yer_imleri(ANAHATLAR) == ["Kapsam Kılavuzu", "Senaryo Karşılaştırması", "1. Ünite · Uzay Çağı"]


def test_sayfa_metinleri_son_bos_parca_atilir():
    assert len(pk.sayfa_metinleri(SAYFALAR)) == 4


def test_eksik_baslik_katlamayla_aranir():
    sayfalar = pk.sayfa_metinleri(SAYFALAR)
    assert pk.eksik_basliklar(sayfalar, ["Uzay Teknolojileri", "uzay çağı"]) == []
    assert pk.eksik_basliklar(sayfalar, ["Fiziksel Anlamda İş"]) == ["Fiziksel Anlamda İş"]


def test_yetim_baslik_alt_bilgi_sayilmaz_son_sayfa_yetim_degil():
    sayfalar = pk.sayfa_metinleri(SAYFALAR)
    # 3. sayfanın son anlamlı satırı bir ünite başlığı: yetim. 4. (son) sayfa sayılmaz.
    assert pk.yetim_basliklar(sayfalar, ["1. Ünite · Uzay Çağı", "Uzay Teknolojileri"]) == [(3, "1. Ünite · Uzay Çağı")]


def test_icindekiler_gosterilen_sayfada_baslik_olmali():
    sayfalar = pk.sayfa_metinleri(SAYFALAR)
    assert pk.icindekiler_hatalari(sayfalar, ["Senaryo karşılaştırması", "1. Ünite · Uzay Çağı"]) == []
    hatalar = pk.icindekiler_hatalari(sayfalar, ["2. Ünite · Kuvvet ve Enerjiyi Keşfedelim", "Kaynaklar"])
    assert hatalar == ["2. Ünite · Kuvvet ve Enerjiyi Keşfedelim: İçindekiler s. 9 diyor, başlık o sayfada yok",
                       "İçindekiler'de sayfa numarası yok: Kaynaklar"]
    assert pk.icindekiler_hatalari(["metin"], ["x"]) == ["İçindekiler sayfası yok"]


def test_en_kucuk_punto_kullanilan_yazi_tiplerinden():
    xml = ('<page number="1"><fontspec id="0" size="10" family="A" color="#000"/>'
           '<fontspec id="1" size="6" family="A" color="#000"/><fontspec id="2" size="8" family="A" color="#000"/>'
           '<text top="1" left="1" width="1" height="1" font="0">a</text>'
           '<text top="2" left="1" width="1" height="1" font="2">b</text></page>')
    assert pk.en_kucuk_punto(xml) == 8
    assert pk.en_kucuk_punto("<page/>") is None


def test_kusurlar_rapordan_okunur():
    temiz = {"gomulu_degil": [], "yabanci_yazi_tipi": [], "etiketli": True, "dil": "tr", "yer_imi": 3, "yetim": [],
             "icindekiler": [], "eksik_baslik": [], "en_kucuk_punto": 8}
    assert pk.kusurlar(temiz) == []
    kirli = {**temiz, "gomulu_degil": ["DejaVuSans"], "yabanci_yazi_tipi": ["DejaVuSans"], "etiketli": False,
             "dil": None, "yer_imi": 0, "yetim": [(3, "1. Ünite")], "icindekiler": ["x"], "en_kucuk_punto": 7}
    assert pk.kusurlar(kirli) == [
        "gömülmemiş yazı tipi: DejaVuSans", "Plex dışı yazı tipi: DejaVuSans", "PDF etiketli değil",
        "PDF dili tr değil: None", "yer imi yok", "yetim başlık s. 3: 1. Ünite", "x", "en küçük punto 7 < 7,5"]
    assert pk.kusurlar({**temiz, "icindekiler": ["x"]}, icindekiler_beklenir=False) == []
```

- [ ] **Step 2: Testi koş, düştüğünü gör**

Run: `env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pdf_kapilari.py`
Expected: FAIL — `ImportError: cannot import name 'pdf_kapilari'`.

- [ ] **Step 3: `src/pdf_kapilari.py`'yi yaz**

```python
"""Kapsam kılavuzu PDF'inin kanun kapıları (docs/sinav-kilavuzu-kanunu.md): üretilen dosyanın kendisi ölçülür.

Ayrıştırıcılar saf (tests/test_pdf_kapilari.py fikstürle sınar); `denetle` poppler (pdfinfo, pdffonts, pdftotext,
pdftohtml) ve qpdf'i argüman listesiyle çağırır. pdftohtml `-zoom 1` ile yazı boyu yaklaşık punto olarak okunur
(tamsayıya yuvarlanır: 8,4 pt → 8)."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from src.sinav_tarihi import katla

# Alt bilgi satırı (damga "TEDY · …" ile başlar; sayfa numarası "s. n/N" ile biter): yetim denetimine girmez.
ALT_BILGI = re.compile(r"(^TEDY\b|s\.\s*\d+\s*/\s*\d+\s*$)")
PLEX_ONEKLERI = ("IBMPlexSans", "IBMPlexMono")
EN_KUCUK_PUNTO = 8   # K3: 7,5 pt; pdftohtml tamsayıya yuvarlar


def pdffonts_ayristir(metin: str) -> list[dict]:
    """`pdffonts` tablosu → [{"ad", "gomulu"}]; alt küme öneki ("AAAAAA+") atılır. Sütunlar sağdan okunur
    (tür "Type 1C" gibi iki sözcük olabilir): …, emb, sub, uni, nesne no, kuşak."""
    satirlar = metin.splitlines()
    bas = next((i + 1 for i, s in enumerate(satirlar) if s.startswith("---")), None)
    if bas is None:
        return []
    out = []
    for s in satirlar[bas:]:
        p = s.split()
        if len(p) < 7:
            continue
        out.append({"ad": p[0].split("+", 1)[-1], "gomulu": p[-5] == "yes"})
    return out


def pdfinfo_alani(metin: str, alan: str) -> str | None:
    m = re.search(rf"^{re.escape(alan)}:\s*(.*)$", metin, re.M)
    return m.group(1).strip() if m else None


def etiketli_mi(pdfinfo: str) -> bool:
    return pdfinfo_alani(pdfinfo, "Tagged") == "yes"


def sayfa_sayisi(pdfinfo: str) -> int:
    deger = pdfinfo_alani(pdfinfo, "Pages") or "0"
    return int(deger) if deger.isdigit() else 0


def yer_imleri(outlines_json: dict) -> list[str]:
    out: list[str] = []

    def gez(ogeler):
        for o in ogeler or []:
            out.append(str(o.get("title", "")))
            gez(o.get("kids"))
    gez(outlines_json.get("outlines"))
    return out


def pdf_dili(qpdf_json: dict) -> str | None:
    """qpdf JSON v2: qpdf[1]["trailer"]["value"]["/Root"] → "obj:<ref>" → value["/Lang"] ("u:tr")."""
    q = qpdf_json.get("qpdf")
    if not isinstance(q, list) or len(q) < 2 or not isinstance(q[1], dict):
        return None
    nesneler = q[1]
    kok = ((nesneler.get("trailer") or {}).get("value") or {}).get("/Root")
    dil = ((nesneler.get(f"obj:{kok}") or {}).get("value") or {}).get("/Lang")
    if not isinstance(dil, str):
        return None
    return dil[2:] if dil.startswith("u:") else dil


def sayfa_metinleri(pdftotext: str) -> list[str]:
    parcalar = pdftotext.split("\f")
    if parcalar and not parcalar[-1].strip():
        parcalar = parcalar[:-1]
    return parcalar


def _anlamli_satirlar(sayfa: str) -> list[str]:
    return [s.strip() for s in sayfa.splitlines() if s.strip() and not ALT_BILGI.search(s.strip())]


def eksik_basliklar(sayfalar: list[str], basliklar: list[str]) -> list[str]:
    """K1: kitap ve MEB başlıkları PDF metninde birebir (katlanmış) geçmeli."""
    tum = katla(" ".join(" ".join(s.split()) for s in sayfalar))
    return [b for b in basliklar if katla(b) not in tum]


def yetim_basliklar(sayfalar: list[str], basliklar: list[str]) -> list[tuple[int, str]]:
    """K5: bir sayfanın son anlamlı satırı (alt bilgi hariç; iki satıra bölünen başlık için son iki satır) bir başlıkla
    bitiyorsa yetimdir. Son sayfa sayılmaz."""
    katli = [(b, katla(b)) for b in basliklar if katla(b)]
    out = []
    for i, sayfa in enumerate(sayfalar[:-1], start=1):
        satirlar = _anlamli_satirlar(sayfa)
        if not satirlar:
            continue
        son = katla(" ".join(satirlar[-2:]))
        bulunan = next((b for b, k in katli if son.endswith(k)), None)
        if bulunan:
            out.append((i, bulunan))
    return out


def icindekiler_hatalari(sayfalar: list[str], girdiler: list[str]) -> list[str]:
    """K5, spec §4.2: İçindekiler'deki her girdinin gösterdiği sayfada o başlık geçmeli."""
    t = next((i for i, s in enumerate(sayfalar) if "icindekiler" in katla(s)), None)
    if t is None:
        return ["İçindekiler sayfası yok"]
    satirlar = [" ".join(s.split()) for s in sayfalar[t].splitlines() if s.strip()]
    hatalar = []
    for g in girdiler:
        k = katla(g)
        gosterilen = None
        for s in satirlar:
            m = re.search(r"(\d+)\s*$", s)
            if m and k in katla(s):
                gosterilen = int(m.group(1))
                break
        if gosterilen is None:
            hatalar.append(f"İçindekiler'de sayfa numarası yok: {g}")
        elif not (1 <= gosterilen <= len(sayfalar)) or k not in katla(" ".join(sayfalar[gosterilen - 1].split())):
            hatalar.append(f"{g}: İçindekiler s. {gosterilen} diyor, başlık o sayfada yok")
    return hatalar


def en_kucuk_punto(xml: str) -> int | None:
    boy = {m.group(1): int(m.group(2)) for m in re.finditer(r'<fontspec id="(\d+)" size="(\d+)"', xml)}
    kullanilan = {m.group(1) for m in re.finditer(r'<text [^>]*font="(\d+)"', xml)}
    degerler = [boy[f] for f in kullanilan if f in boy]
    return min(degerler) if degerler else None


def _calistir(*argv: str) -> str:
    return subprocess.run(list(argv), capture_output=True, text=True, check=True, timeout=120).stdout


def denetle(yol: Path, *, basliklar: list[str], icindekiler: list[str]) -> dict:
    y = str(yol)
    info = _calistir("pdfinfo", y)
    fontlar = pdffonts_ayristir(_calistir("pdffonts", y))
    sayfalar = sayfa_metinleri(_calistir("pdftotext", "-layout", y, "-"))
    qpdf = json.loads(_calistir("qpdf", "--json", "--json-key=qpdf", y))
    imler = yer_imleri(json.loads(_calistir("qpdf", "--json", "--json-key=outlines", y)))
    xml = _calistir("pdftohtml", "-xml", "-i", "-q", "-zoom", "1", "-stdout", y)
    return {
        "sayfa": sayfa_sayisi(info), "etiketli": etiketli_mi(info), "dil": pdf_dili(qpdf),
        "yazi_tipleri": sorted({f["ad"] for f in fontlar}),
        "gomulu_degil": sorted({f["ad"] for f in fontlar if not f["gomulu"]}),
        "yabanci_yazi_tipi": sorted({f["ad"] for f in fontlar if not f["ad"].startswith(PLEX_ONEKLERI)}),
        "yer_imi": len(imler), "yetim": yetim_basliklar(sayfalar, basliklar),
        "icindekiler": icindekiler_hatalari(sayfalar, icindekiler) if icindekiler else [],
        "eksik_baslik": eksik_basliklar(sayfalar, basliklar), "en_kucuk_punto": en_kucuk_punto(xml),
    }


def kusurlar(r: dict, *, icindekiler_beklenir: bool = True) -> list[str]:
    """Raporun kanun kusurları; boş liste kapıların geçtiği anlamına gelir. Düz yolda (B) İçindekiler sayfa numarası
    taşımadığı için `icindekiler_beklenir=False` verilir."""
    k = []
    if r["gomulu_degil"]:
        k.append("gömülmemiş yazı tipi: " + ", ".join(r["gomulu_degil"]))
    if r["yabanci_yazi_tipi"]:
        k.append("Plex dışı yazı tipi: " + ", ".join(r["yabanci_yazi_tipi"]))
    if not r["etiketli"]:
        k.append("PDF etiketli değil")
    if (r["dil"] or "").split("-")[0] != "tr":
        k.append(f"PDF dili tr değil: {r['dil']}")
    if r["yer_imi"] == 0:
        k.append("yer imi yok")
    k += [f"yetim başlık s. {s}: {b}" for s, b in r["yetim"]]
    if icindekiler_beklenir:
        k += r["icindekiler"]
    k += [f"başlık PDF metninde yok: {b}" for b in r["eksik_baslik"]]
    if r["en_kucuk_punto"] is not None and r["en_kucuk_punto"] < EN_KUCUK_PUNTO:
        k.append(f"en küçük punto {r['en_kucuk_punto']} < 7,5")
    return k
```

- [ ] **Step 4: Testi koş, geçtiğini gör**

Run: `env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pdf_kapilari.py`
Expected: PASS (9 test).

- [ ] **Step 5: Yoklama ve basım-denetim betiğini yaz**

`scripts/kilavuz_pdf_kapilari.py`:

```python
"""Kılavuz PDF'ini iki yoldan (A: Paged.js, B: düz Chrome) basar, kanun kapılarını uygular, süre ve belleği ölçer
(plan 2026-10-25 Görev 2 yoklaması; Görev 13'te gerçek Fen modeliyle). Basım ted-dashboard.service'in ortamıyla koşar
(`env -i`, PATH=.venv/bin:/usr/bin:/bin, HOME); bellek `/usr/bin/time %M` — beklenen en büyük tek sürecin tepe RSS'i
(node ve Chrome süreçleri). systemd-run'ın "Memory peak"i bu makinede güvenilmez (ölçüldü: 512K).

    env -u ANTHROPIC_API_KEY .venv/bin/python -I scripts/kilavuz_pdf_kapilari.py --dist dashboard-dist --cikti /tmp/tedy-yoklama-pdf
    env -u ANTHROPIC_API_KEY .venv/bin/python -I scripts/kilavuz_pdf_kapilari.py --dist dashboard-dist --cikti /tmp/k \\
        --model dashboard/tests/e2e/fixtures/hazirlik/fen-bilimleri-1-kilavuz.json --sorgu 'ders=fen-bilimleri&sinav=1'
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

from src.pdf_kapilari import denetle, kusurlar  # noqa: E402

VENV_BIN = "/mnt/thunderbolt/workspaces/TED/.venv/bin"
YOKLAMA_BASLIKLARI = [
    "1. Ünite · Uzay Çağı", "2. Ünite · Kuvvet ve Enerjiyi Keşfedelim", "1. Türkiye ve Uzay Araştırmaları",
    "2. Uzayda Neler Var?", "1. Kuvvet, İş ve Enerji İlişkisi", "Senaryo Karşılaştırması", "Kaynaklar",
    "Fiziksel Anlamda İş", "Uzay Teknolojileri", "Yıldız Oluşumu"]
YOKLAMA_ICINDEKILER = ["Senaryo Karşılaştırması", "1. Ünite · Uzay Çağı", "2. Ünite · Kuvvet ve Enerjiyi Keşfedelim",
                       "Kaynaklar"]


def model_basliklari(model: dict) -> tuple[list[str], list[str]]:
    """Kılavuz modelinden K1 başlıkları (ünite, çerçeve, konu, bölüm başlığı) ve İçindekiler girdileri (bölümler)."""
    basliklar: list[str] = []
    icindekiler = ["Senaryo Karşılaştırması"]
    for u in model.get("uniteler", []):
        basliklar.append(u["baslik"])
        icindekiler.append(u["baslik"])
        for c in u["cerceveler"]:
            if c.get("baslik"):
                basliklar.append(c["baslik"])
            for b in c["bloklar"]:
                if not b["senaryoda"]:
                    continue          # senaryoda olmayan çıktı tek satırdır, başlıkları basılmaz (K2)
                for y in b["kitapta"]:
                    if y.get("konu"):
                        basliklar.append(y["konu"])
                basliklar += [h["ad"] for h in b["basliklar"]]
    icindekiler.append("Kaynaklar")
    return list(dict.fromkeys(basliklar)), icindekiler


def bas(dist: Path, cikti: Path, sorgu: str, model: Path | None, duz: bool) -> dict:
    komut = ["/usr/bin/time", "-f", "TEDY_BELLEK_KB=%M", "node", "scripts/kilavuz-pdf.mjs",
             "--dist", str(dist.resolve()), "--cikti", str(cikti), "--sorgu", sorgu]
    if model:
        komut += ["--model", str(model.resolve())]
    if duz:
        komut.append("--duz")
    ortam = {"PATH": f"{VENV_BIN}:/usr/bin:/bin", "HOME": os.environ["HOME"]}   # ted-dashboard.service'in ortamı (Y8)
    bas_an = time.monotonic()
    p = subprocess.run(komut, capture_output=True, text=True, timeout=300, cwd=KOK / "dashboard", env=ortam)
    sure = time.monotonic() - bas_an
    m = re.search(r"TEDY_BELLEK_KB=(\d+)", p.stderr)
    return {"cikis": p.returncode, "sure_sn": round(sure, 1), "bellek": f"{int(m.group(1)) // 1024} MB" if m else "?",
            "stderr": p.stderr.strip()[-400:]}


def main(argv: list[str] | None = None) -> int:
    a = argparse.ArgumentParser(description="Kılavuz PDF yoklaması / kapı denetimi")
    a.add_argument("--dist", type=Path, required=True)
    a.add_argument("--cikti", type=Path, required=True)
    a.add_argument("--model", type=Path)
    a.add_argument("--sorgu", default="yoklama=1")
    a.add_argument("--yol", choices=("paged", "duz", "ikisi"), default="ikisi")
    g = a.parse_args(argv)
    g.cikti.mkdir(parents=True, exist_ok=True)
    if g.model:
        basliklar, icindekiler = model_basliklari(json.loads(g.model.read_text(encoding="utf-8")))
    else:
        basliklar, icindekiler = YOKLAMA_BASLIKLARI, YOKLAMA_ICINDEKILER
    yollar = {"paged": [False], "duz": [True], "ikisi": [False, True]}[g.yol]
    print("| Yol | Çıkış | Süre (s) | Bellek | Sayfa | Yazı tipleri | Kusurlar |")
    print("|---|---|---|---|---|---|---|")
    sonuc = 0
    for duz in yollar:
        ad = "B düz" if duz else "A Paged.js"
        pdf = g.cikti / ("duz.pdf" if duz else "paged.pdf")
        olcum = bas(g.dist, pdf, g.sorgu, g.model, duz)
        if olcum["cikis"] != 0 or not pdf.exists():
            print(f"| {ad} | {olcum['cikis']} | {olcum['sure_sn']} | {olcum['bellek']} | – | – | basılamadı: {olcum['stderr']} |")
            sonuc = 1
            continue
        rapor = denetle(pdf, basliklar=basliklar, icindekiler=icindekiler)
        if duz:
            # Chrome'un üst/alt bilgi şablonu web yazı tipi kullanamaz (ölçüldü): orada DejaVu Sans beklenir (borç KK-3).
            rapor["yabanci_yazi_tipi"] = [f for f in rapor["yabanci_yazi_tipi"] if not f.startswith("DejaVuSans")]
        k = kusurlar(rapor, icindekiler_beklenir=not duz)
        sonuc = sonuc or (1 if k else 0)
        print(f"| {ad} | 0 | {olcum['sure_sn']} | {olcum['bellek']} | {rapor['sayfa']} | "
              f"{', '.join(rapor['yazi_tipleri'])} | {'; '.join(k) or 'yok'} |")
    return sonuc


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Yoklamayı koş (Y1–Y4, Y6–Y8)**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-hazirligi
(cd dashboard && npm run build; echo "build çıkış: $?")
rm -rf /tmp/tedy-yoklama-pdf
env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -I scripts/kilavuz_pdf_kapilari.py \
  --dist dashboard-dist --cikti /tmp/tedy-yoklama-pdf | tee /tmp/tedy-yoklama-pdf.md
```

Expected: iki satırlı Markdown tablosu. Süre (Y6), bellek (Y7) ve servis ortamıyla çıkış 0 (Y8) bu satırlardan okunur; "Kusurlar" sütunu Y1–Y4'ü verir. Ön ölçümde (gerçek Fen modeli) satırlar "A Paged.js | 0 | 3.1 | … | 5 | IBMPlexMono, IBMPlexSans, IBMPlexSans-SmBld | yok" ve "B düz | 0 | 2.4 | … | 4 | DejaVuSans, … | yok" idi.

- [ ] **Step 7: Tablo bölünmesini gözle ölç (Y5)**

```bash
pdftotext -layout /tmp/tedy-yoklama-pdf/paged.pdf - | awk 'BEGIN{RS="\f"} /FB\.7\.2\.2 Enerji/ {print "--- sayfa", NR, (index($0,"Öğrenme çıktısı") ? "başlık satırı VAR" : "başlık satırı YOK")}'
```

Expected: karşılaştırma tablosunun bulunduğu her sayfa için "başlık satırı VAR". Birinde "YOK" varsa karar tablosundaki Y5 kuralı uygulanır (ünite başına tablo; Görev 11 `KarsilastirmaTablosu`'na `kilavuz-matris--unite` kipi ve Görev 13'te yeniden ölçüm).

- [ ] **Step 8: Karar kuralını uygula ve Kanun belgesini yaz**

Karar tablosu (planın başı) bu ölçümlerle uygulanır. `docs/sinav-kilavuzu-kanunu.md`'yi yaz; "Yoklama kaydı" bölümüne `/tmp/tedy-yoklama-pdf.md`'nin içeriğini ve Y5 sonucunu aynen koy; K5 için **seçilen yolun metnini** bırak, ötekini sil:

```markdown
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

| # | Madde | Hüküm | Kapı |
|---|---|---|---|
| K1 | Kaynak dürüstlüğü | Kitap başlıkları yalnız kitap haritasından, birebir yazım; sayfa = basılı sayfa; MEB çıktı metni birebir; bulunamayan "Kitapta karşılığı bulunamadı" ("yok" değil). Harita elle düzenlenmez. | `tests/test_kitap_haritasi_fen.py`; `pdf_kapilari.eksik_basliklar`; `tests/test_sinav_kilavuzu.py` |
| K2 | Hiyerarşi | En çok dört düzey: ünite › içerik çerçevesi › çıktı › bölüm başlıkları. Blok iç sırası sabit: kod + kısa ad, soru (ve "her senaryoda"), MEB metni, Kitapta, Bu bölümde ele alınanlar, okulda, ödev/modül, hazırlık işareti. Senaryoda olmayan çıktı tek satır, soluk. | `hazirlik-kilavuz.spec.ts` "blok sırası" |
| K3 | Tipografi | Carbon üretken tip ölçeği; IBM Plex Sans, kodlar Plex Mono; A4'te kök 14,857 px (body-01 ≈ 9,75 pt), en küçük metin label-01 ≈ 8,4 pt (≥ 7,5 pt). Plex dosyaları depodadır, PDF'e gömülür. | `pdf_kapilari.en_kucuk_punto`, `yabanci_yazi_tipi` |
| K4 | Renk | Yalnız Carbon belirteçleri; ders rengi yalnız vurgu (karonun üst çizgisi, kılavuz başlığının kenarı). Durum ikon + metin (+ renk): kesin `CheckmarkFilled` + `--cds-support-success`, olası `InformationFilled` + `--cds-support-info`, ülke geneli/geçti düz `--cds-text-secondary`. Tag'de ders aileleri yasak; "her senaryoda" gri Tag. Mor yalnız YZ (Plan 2). Kontrast AA. | `tests/test_pano_tasarim_sistemi.py`; e2e axe + IBM |
| K5 | Kâğıt | (Seçilen yolun metni — aşağıdaki iki metinden biri kalır.) | `pdf_kapilari.yetim_basliklar`, `icindekiler_hatalari` |
| K6 | Eksiksizlik | Kılavuz kısaltılmaz; bir bölümün haritadaki bütün başlıkları yazılır (etkinlikte amaç 70 karakterde kısaltılır, başlığın kendisi kısaltılmaz). | `hazirlik-kilavuz.spec.ts` |
| K7 | Dil | Türkçe; adlandıran başlık başlık düzeninde ("Senaryo Karşılaştırması"), cümle olan başlık ve her etiket cümle düzeninde (talimatname S38/B41); MEB terimleri birebir; öğrenciye "sen"; sayılar rakamla; başarı vaadi yok. | `tests/test_pano_talimatname_borclari.py` (kısmen: dilbilgisi elle) |
| K8 | Durum dürüstlüğü | Senaryo duyurulmadıysa hiçbir yüzey tek senaryoyu "bu" diye sunmaz: bloklar "senaryoya göre a–b soru", özet aralık, durum "Olası: N senaryo". Kullanıcının seçtiği senaryo duyurulandan farklıysa bu açıkça yazılır. | `test_kilavuz_olasi_kip_tek_senaryo_sunmaz`; `hazirlik.test.ts`; e2e |
| K9 | YZ ayrımı | Carbon AI etiketi, ayrı başlık, cümle başına sayfa atfı, kapatılabilir; modele kişisel veri gitmez. Plan 1'de YZ bölümü yoktur (`yz.durum = "kapali"`). | Plan 2 |
| K10 | Erişilebilirlik | WCAG 2.2 AA; axe + IBM Equal Access sıfır ihlal; PDF etiketli, yer imli, dil `tr`. | e2e; `pdf_kapilari` |
| K11 | Ekran–kâğıt eşliği | Ekran ve kâğıt aynı `KilavuzBelgesi` bileşeni, aynı sıra; etkileşimli öğenin durağan karşılığı (işaret onay kutusu → Carbon `Checkbox`/`CheckboxChecked` ikonu; ☐ karakteri Plex'te yok). | `hazirlik-kilavuz.spec.ts` "baskı eşliği" |
| K12 | Güncellik | Damga (MEB tablosu tarihi, kitap baskısı ve sha256 kısası, üretim tarihi) her sayfada; harita eski bir tabloya göre kurulduysa ya da kitap PDF'i değiştiyse (`--denetle`) "güncel değil" uyarısı. | `test_guncellik_tablo_ve_kitap_degisti`; e2e |

### K5 — A metni (ana yol Paged.js)

A4 dikey; kenar 18/16/20 mm; üst bilgi ders · sınav · senaryo (`string(ustbilgi)`), alt bilgi damga + "s. n/N"
(Paged.js kenar kutuları); kapak sayfasında üst bilgi yok; başlıktan sonra sayfa kesilmez (yetim başlık yok);
bölünen blokta "(devam)" (`data-split-from`); karşılaştırma tablosunda başlık satırı her parçada; İçindekiler gerçek
sayfa numaralı (`target-counter`); ebeveyn özeti tek sayfa; siyah-beyaz baskıda anlam ikon ve metinle korunur.

### K5 — B metni (ana yol düz Chrome)

A4 dikey; kenar 18/16/20 mm; üst bilgi ders · sınav · senaryo ve damga belge başlığından (Chrome üst bilgisi), alt
bilgi "s. n/N" (Chrome alt bilgisi); başlıktan sonra sayfa kesilmez; "(devam)" yok (borç KK-1); İçindekiler sayfa
numarasız (borç KK-2); üst/alt bilgi sistem yazı tipinde, 8 pt (borç KK-3: Chrome şablonu web yazı tipi yükleyemez;
Plex'in kullanıcı yazı tipi dizinine kurulması kullanıcı onayıyla çözer); ebeveyn özeti tek sayfa; siyah-beyaz
baskıda anlam ikon ve metinle korunur.

## 2. Yoklama kaydı (2026-10-25)

(`scripts/kilavuz_pdf_kapilari.py` tablosu ve Y5 sonucu buraya aynen; ardından seçilen yol ve gerekçesi tek
cümleyle: "Ana yol A — Y1–Y4, Y6–Y8 geçti" ya da "Ana yol B — A'da <kusur>".)

## 3. Borçlar

- KK-0: K7'nin dilbilgisi denetimi elle yapılır (otomatik kapı yok).
- (B yolu seçilirse) KK-1 "(devam)" ve KK-2 sayfa numaralı İçindekiler düz yolda yok; KK-3 üst/alt bilgi sistem yazı tipinde.
```

Belgedeki iki parantezli yönerge satırı (K5 satırı ve §2) bu adımda ölçümle değiştirilir: K5 satırının hücresine seçilen metnin tek cümlelik özeti, §2'ye tablo; seçilmeyen K5 alt başlığı silinir; B seçildiyse §3'teki B satırı kalır, A seçildiyse silinir.

- [ ] **Step 9: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-hazirligi
git log --oneline -3 && git status --short
git add src/pdf_kapilari.py scripts/kilavuz_pdf_kapilari.py tests/test_pdf_kapilari.py docs/sinav-kilavuzu-kanunu.md
git commit -m "$(cat <<'EOF'
feat(sinav-hazirligi): PDF kanun kapıları, yoklama ölçümü ve Sınav Kılavuzu Tasarım Kanunu 1.0

pdf_kapilari üretilen PDF'i ölçer (gömülü Plex, etiket, dil, yer imi, yetim başlık, İçindekiler numaraları,
K1 başlıkları, en küçük punto); yoklama iki yolu servis PATH'iyle basıp karar tablosunu uygular.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Kitap haritası betiği I — İçindekiler ayrıştırıcı ve sayfa sınırları

**Files:**
- Create: `scripts/meb_kitap_haritasi.py` (iskelet, sabitler, `YapiHatasi`, `icindekiler_ayristir`)
- Create: `tests/fixtures/kitap_haritasi/fen7_1_icindekiler.txt`
- Test: `tests/test_meb_kitap_haritasi.py`

**Interfaces:**
- Consumes: `src.sinav_tarihi.katla`.
- Produces: `class YapiHatasi(ValueError)`; `icindekiler_ayristir(metin: str) -> list[dict]` — `[{"no": int, "ad": str, "sayfa": int, "son_sayfa": int, "cerceveler": [{"no": int, "ad": str, "sayfa": int, "son_sayfa": int, "ciktilar": [], "basliklar": [], "konular": [{"ad": str, "sayfa": int, "son_sayfa": int, "basliklar": []}]}]}]` (sayfalar basılı sayfa). `UNITE_EKLERI`, `SURUM = 1`, `CIKTI_DIZINI`, `DENETIM_DOSYASI`.

- [ ] **Step 1: İçindekiler fikstürünü yaz**

`tests/fixtures/kitap_haritasi/fen7_1_icindekiler.txt` — Fen 7-1 PDF'inin 8. sayfası, `pdftotext -f 8 -l 8 -layout` çıktısı (2026-10-25; nokta dizileri kısaltıldı, `.24`, ` .34` ve boşluksuz `...81` biçimleri korundu):

```text
        İçindekiler
Kitabımızı Tanıyalım ..................................................... 8
Güvenlik Sembolleri ..................................................... 10
Fen, Mühendislik ve Girişimcilik Uygulamaları ........................... 11
1. Ünite             Uzay Çağı
Ön Değerlendirme......................................................... 14
1. Türkiye ve Uzay Araştırmaları......................................... 15
Uzay Teknolojileri ...................................................... 16
Teknoloji ile Uzay Araştırmaları Arasındaki İlişki ...................... .24
2. Uzayda Neler Var? .................................................... .34
Yıldız Oluşumu .......................................................... 35
İz Bırakanlar............................................................ 50
Ünite Sonu Değerlendirme ................................................ 51
2. Ünite             Kuvvet ve Enerjiyi Keşfedelim
Ön Değerlendirme ........................................................ 58
1. Kuvvet, İş ve Enerji İlişkisi ........................................ 59
Fiziksel Anlamda İş ..................................................... 60
Enerji ve Enerji Çeşitleri .............................................. 64
2. Enerji Dönüşümleri ................................................... 71
Enerjinin Korunumu ...................................................... 72
İz Bırakanlar ........................................................... 80
Ünite Sonu Değerlendirme ................................................81
3. Ünite             Vücudumuzdaki Sistemler
Ön Değerlendirme ........................................................ 88
1. Sindirim Sistemi ..................................................... 89
Sindirim Sistemini Oluşturan Yapı ve Organlar............................ 90
Sindirim Sisteminin Sağlığı ............................................. 96
2. Dolaşım Sistemi ..................................................... 101
Dolaşım Sistemini Oluşturan Yapı ve Organlar............................ 102
Kan Bağışının Toplum Açısından Önemi ................................... 109
Dolaşım Sisteminin Sağlığı .............................................113
3. Solunum Sistemi .....................................................117
Solunum Sistemini Oluşturan Yapı ve Organlar............................118
Solunum Sisteminin Sağlığı ............................................. 123
4. Boşaltım Sistemi .................................................... 129
Boşaltım Sistemini Oluşturan Yapı ve Organlar .......................... 130
Boşaltım Sisteminin Sağlığı ............................................ 135
İz Bırakanlar .......................................................... 140
Ünite Sonu Değerlendirme ............................................... 141
Sözlük ................................................................. 149
Kaynakça................................................................ 150
Cevap Anahtarı.......................................................... 150
Görsel ve Genel Ağ Kaynakçası........................................... 150
Türkiye’nin Mülki İdare Bölümleri ile Kara ve Deniz Komşuları Haritası .. 151
Türk Dünyası Haritası .................................................. 152
                                                                       77
```

- [ ] **Step 2: Başarısız testleri yaz**

`tests/test_meb_kitap_haritasi.py`:

```python
"""MEB kitap haritası betiği (spec 2026-10-25 §2.2, plan Görev 3–4): PDF'ten bağımsız fikstürlerle."""
from pathlib import Path

import pytest

from scripts import meb_kitap_haritasi as mkh

FIKSTUR = Path(__file__).parent / "fixtures" / "kitap_haritasi"
ICINDEKILER = (FIKSTUR / "fen7_1_icindekiler.txt").read_text(encoding="utf-8")


def _ozet(uniteler):
    return [(u["no"], u["ad"], u["sayfa"], u["son_sayfa"],
             [(c["no"], c["ad"], c["sayfa"], c["son_sayfa"], [(k["ad"], k["sayfa"], k["son_sayfa"]) for k in c["konular"]])
              for c in u["cerceveler"]]) for u in uniteler]


def test_icindekiler_fen_yapisi_ve_sinirlari():
    # Sonraki sayfanın metni form besleme karakterinden sonra gelir ve okunmaz.
    uniteler = mkh.icindekiler_ayristir(ICINDEKILER + "\f\nKitabımızı Tanıyalım\n1. Ünite Numarası ve Adı .... 9\n")
    o = _ozet(uniteler)
    assert [u[:4] for u in o] == [(1, "Uzay Çağı", 14, 57), (2, "Kuvvet ve Enerjiyi Keşfedelim", 58, 87),
                                  (3, "Vücudumuzdaki Sistemler", 88, 148)]
    assert o[0][4] == [
        (1, "Türkiye ve Uzay Araştırmaları", 15, 33,
         [("Uzay Teknolojileri", 16, 23), ("Teknoloji ile Uzay Araştırmaları Arasındaki İlişki", 24, 33)]),
        (2, "Uzayda Neler Var?", 34, 49, [("Yıldız Oluşumu", 35, 49)])]
    assert o[1][4] == [
        (1, "Kuvvet, İş ve Enerji İlişkisi", 59, 70, [("Fiziksel Anlamda İş", 60, 63), ("Enerji ve Enerji Çeşitleri", 64, 70)]),
        (2, "Enerji Dönüşümleri", 71, 79, [("Enerjinin Korunumu", 72, 79)])]
    assert o[2][4][1] == (2, "Dolaşım Sistemi", 101, 116,
                          [("Dolaşım Sistemini Oluşturan Yapı ve Organlar", 102, 108),
                           ("Kan Bağışının Toplum Açısından Önemi", 109, 112), ("Dolaşım Sisteminin Sağlığı", 113, 116)])
    assert o[2][4][3][:4] == (4, "Boşaltım Sistemi", 129, 139)
    # Ünite ekleri ve ön/arka kısım haritaya girmez.
    adlar = {k[0] for u in o for c in u[4] for k in c[4]} | {c[1] for u in o for c in u[4]}
    assert not adlar & {"Ön Değerlendirme", "İz Bırakanlar", "Ünite Sonu Değerlendirme", "Sözlük", "Kitabımızı Tanıyalım"}
    assert uniteler[0]["cerceveler"][0]["ciktilar"] == [] and uniteler[0]["cerceveler"][0]["basliklar"] == []


def test_iki_satira_bolunen_girdi_birlesir():
    metin = ("İçindekiler\n1. Ünite      Deneme\n1. Uzun Bir İçerik Çerçevesi Adı ki\n"
             "İki Satıra Bölünmüş ............ 15\nKonu Bir ..... 16\nÜnite Sonu Değerlendirme ...... 20\nSözlük ..... 21\n")
    u = mkh.icindekiler_ayristir(metin)[0]
    assert (u["sayfa"], u["son_sayfa"]) == (15, 20)
    c = u["cerceveler"][0]
    assert (c["no"], c["ad"], c["sayfa"], c["son_sayfa"]) == (1, "Uzun Bir İçerik Çerçevesi Adı ki İki Satıra Bölünmüş", 15, 19)
    assert [(k["ad"], k["sayfa"], k["son_sayfa"]) for k in c["konular"]] == [("Konu Bir", 16, 19)]


@pytest.mark.parametrize("metin,ileti", [
    ("Sayfa yok\n", "İçindekiler başlığı yok"),
    ("İçindekiler\n1. Ünite   A\n1. Ç ..... 10\nK ..... 9\n", "geriye gidiyor"),
    ("İçindekiler\n1. Ünite   A\nanlamsız satır\nbir anlamsız satır daha\n", "tanınmayan İçindekiler satırı"),
    ("İçindekiler\n1. Ünite   A\nK ..... 9\n", "çerçevesiz konu"),
    ("İçindekiler\nSözlük ..... 9\n", "ünite yok"),
])
def test_bozuk_icindekiler_reddedilir(metin, ileti):
    with pytest.raises(mkh.YapiHatasi, match=ileti):
        mkh.icindekiler_ayristir(metin)
```

- [ ] **Step 3: Testi koş, düştüğünü gör**

Run: `env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_meb_kitap_haritasi.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.meb_kitap_haritasi'`.

- [ ] **Step 4: Betiğin iskeletini ve ayrıştırıcıyı yaz**

`scripts/meb_kitap_haritasi.py`:

```python
"""MEB ders kitabı haritası üretici (spec 2026-10-25 §2.2): EBA PDF'inden ünite → içerik çerçevesi → konu → bölüm
içi başlıklar ve basılı sayfalar; çıktı → kitap bölümü eşlemesi. Çıktı src/kitap_haritalari/<anahtar>.json; elle
düzenlenmez (gürültü temizliği KITAPLAR ayarındadır, sonra betik yeniden koşar).

PDF güvenilmeyen veridir: boş bir geçici dizine iner, poppler araçları argüman listesiyle çağrılır, betik o
dizinden koşmaz ve Python `-I` ile çalışır.

    env -u ANTHROPIC_API_KEY .venv/bin/python -I scripts/meb_kitap_haritasi.py fen-bilimleri --pdf 1=/tmp/meb-kitap-yoklama/fen7-1.pdf --kuru
    env -u ANTHROPIC_API_KEY .venv/bin/python -I scripts/meb_kitap_haritasi.py fen-bilimleri --pdf 1=… --denetim-kim "…"
    env -u ANTHROPIC_API_KEY .venv/bin/python -I scripts/meb_kitap_haritasi.py fen-bilimleri --denetle
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

from src.json_utils import atomic_json_dump  # noqa: E402
from src.sinav_senaryo import tablo_oku  # noqa: E402
from src.sinav_tarihi import katla  # noqa: E402

SURUM = 1
CIKTI_DIZINI = KOK / "src" / "kitap_haritalari"
DENETIM_DOSYASI = KOK / "output" / "kitap_denetimi.json"
# Ünite içindeki ama konu olmayan girdiler (katlanmış): sayfa sınırı için okunur, haritaya girmez.
UNITE_EKLERI = ("on degerlendirme", "iz birakanlar", "unite sonu degerlendirme")
_UNITE = re.compile(r"^(\d+)\.\s*Ünite\s+(\S.*)$")
_GIRDI = re.compile(r"^(?:(\d+)\.\s+)?(.+?)\s*\.{2,}[\s.]*(\d{1,4})$")
_SAYI = re.compile(r"^\d+$")


class YapiHatasi(ValueError):
    """Kitap beklenen yapıda değil; harita yazılmaz, eskisi kalır."""


def icindekiler_ayristir(metin: str) -> list[dict]:
    """`pdftotext -layout` İçindekiler sayfası → üniteler (basılı sayfa). Ünite satırı "1. Ünite   Uzay Çağı"; numaralı
    girdi içerik çerçevesi, numarasız girdi konu. Ünite ekleri ve ön/arka kısım (Kitabımızı Tanıyalım, Sözlük…) yalnız
    bitiş sayfası için okunur. Bir satır noktalı sayfa numarasıyla bitmiyorsa sonraki satırla birleşir (iki satıra
    bölünmüş başlık); birleşince de tanınmayan satır YapiHatasi'dır — hiçbir girdi sessizce düşmez."""
    bas = metin.find("İçindekiler")
    if bas < 0:
        raise YapiHatasi("İçindekiler başlığı yok")
    govde = metin[bas + len("İçindekiler"):].split("\f", 1)[0]
    uniteler: list[dict] = []
    akis: list[dict] = []          # sayfası olan her girdi, okunuş sırasıyla: {"sayfa", "tur", "u", "c", "k"}
    bekleyen = ""
    kapali = True                  # henüz ünite yok ya da son ünitenin "Ünite Sonu Değerlendirme"si geçti
    for ham in govde.splitlines():
        s = " ".join(ham.split())
        if not s or _SAYI.fullmatch(s):
            continue
        if bekleyen:
            s = f"{bekleyen} {s}"
        m = _UNITE.match(s)
        if m:
            uniteler.append({"no": int(m.group(1)), "ad": m.group(2).strip(), "sayfa": None, "son_sayfa": None,
                             "cerceveler": []})
            bekleyen, kapali = "", False
            continue
        g = _GIRDI.match(s)
        if not g:
            if bekleyen:
                raise YapiHatasi(f"tanınmayan İçindekiler satırı: {s}")
            bekleyen = s
            continue
        bekleyen = ""
        no, ad, sayfa = g.group(1), g.group(2).strip(), int(g.group(3))
        if akis and sayfa < akis[-1]["sayfa"]:
            raise YapiHatasi(f"İçindekiler sayfaları geriye gidiyor: {ad} s. {sayfa}")
        if kapali:
            akis.append({"sayfa": sayfa, "tur": "dis", "u": None, "c": None, "k": None})
            continue
        u = len(uniteler) - 1
        unite = uniteler[u]
        if unite["sayfa"] is None:
            unite["sayfa"] = sayfa
        if katla(ad) in UNITE_EKLERI:
            akis.append({"sayfa": sayfa, "tur": "ek", "u": u, "c": None, "k": None})
            kapali = katla(ad) == "unite sonu degerlendirme"
            continue
        if no is not None:
            unite["cerceveler"].append({"no": int(no), "ad": ad, "sayfa": sayfa, "son_sayfa": None, "ciktilar": [],
                                        "basliklar": [], "konular": []})
            akis.append({"sayfa": sayfa, "tur": "cerceve", "u": u, "c": len(unite["cerceveler"]) - 1, "k": None})
            continue
        if not unite["cerceveler"]:
            raise YapiHatasi(f"çerçevesiz konu: {ad}")
        cer = unite["cerceveler"][-1]
        cer["konular"].append({"ad": ad, "sayfa": sayfa, "son_sayfa": None, "basliklar": []})
        akis.append({"sayfa": sayfa, "tur": "konu", "u": u, "c": len(unite["cerceveler"]) - 1, "k": len(cer["konular"]) - 1})
    if bekleyen:
        raise YapiHatasi(f"tanınmayan İçindekiler satırı: {bekleyen}")
    if not uniteler:
        raise YapiHatasi("İçindekiler'de ünite yok")

    def bitis(i: int, ayni) -> int:
        """i'den sonra `ayni` olmayan ilk girdinin sayfası − 1 (aynı sayfadaysa kendi sayfası)."""
        for j in range(i + 1, len(akis)):
            if not ayni(akis[j]):
                return max(akis[j]["sayfa"] - 1, akis[i]["sayfa"])
        raise YapiHatasi(f"bitiş sayfası okunamadı: s. {akis[i]['sayfa']}")

    for i, a in enumerate(akis):
        if a["tur"] == "konu":
            uniteler[a["u"]]["cerceveler"][a["c"]]["konular"][a["k"]]["son_sayfa"] = bitis(i, lambda b: False)
        elif a["tur"] == "cerceve":
            uniteler[a["u"]]["cerceveler"][a["c"]]["son_sayfa"] = bitis(
                i, lambda b, a=a: b["tur"] == "konu" and b["u"] == a["u"] and b["c"] == a["c"])
    for u, unite in enumerate(uniteler):
        if unite["sayfa"] is None or not unite["cerceveler"]:
            raise YapiHatasi(f"{unite['no']}. ünitede içerik çerçevesi yok")
        son = max(i for i, a in enumerate(akis) if a["u"] == u)
        unite["son_sayfa"] = bitis(son, lambda b: False)
    return uniteler
```

- [ ] **Step 5: Testi koş, geçtiğini gör**

Run: `env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_meb_kitap_haritasi.py`
Expected: PASS (7 test).

- [ ] **Step 6: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-hazirligi
git log --oneline -3 && git status --short
git add scripts/meb_kitap_haritasi.py tests/fixtures/kitap_haritasi/fen7_1_icindekiler.txt tests/test_meb_kitap_haritasi.py
git commit -m "$(cat <<'EOF'
feat(sinav-hazirligi): kitap haritası betiği — İçindekiler ayrıştırıcı ve sayfa sınırları

Ünite → içerik çerçevesi → konu, basılı sayfalar ve bitişler İçindekiler'den; tanınmayan satır, geriye giden
sayfa ve çerçevesiz konu reddedilir.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Kitap haritası betiği II — bölüm içi başlıklar, çıktı eşlemesi, yapı denetimi, CLI ve sha256 denetimi

**Files:**
- Modify: `scripts/meb_kitap_haritasi.py` (başlık ayrıştırma, yerleştirme, eşleme, denetim, kurma, CLI)
- Create: `tests/fixtures/kitap_haritasi/fen7_1_duzen.xml`
- Test: `tests/test_meb_kitap_haritasi.py` (ekleme)

**Interfaces:**
- Consumes: Görev 3'ün `icindekiler_ayristir`, `YapiHatasi`; `src.sinav_senaryo.tablo_oku`; `src.json_utils.atomic_json_dump`.
- Produces:
  - `KITAPLAR: dict[str, dict]` (ders anahtarı → `{"ders", "beklenen_eslesmeyen", "basliksiz_konular", "kitaplar": [{"baslik", "pdf_url", "kaynak_sayfa", "baski", "sayfa_kaymasi", "icindekiler_pdf_sayfalari", "duzen": {"baslik_boyu", "govde_boyu", "cerceve_ailesi", "baslik_sol_en_cok", "govde_sol", "tanim", "atla"}}]}`)
  - `basliklari_ayristir(xml: str, duzen: dict) -> list[dict]` — `[{"pdf_sayfa": int, "ust": int, "metin": str, "tur": "etkinlik"|"baglanti"|"kontrol"|"tanim"|"ozet"|"diger", "amac": str | None}]`, (sayfa, üst) sırasıyla
  - `basliklari_yerlestir(uniteler, adaylar, kayma: int) -> None` (çerçeve ve konu `basliklar`'ını doldurur: `{"ad", "tur", "amac", "sayfa"}`; konu `son_sayfa`'sı içine düşen son başlığa uzar)
  - `benzerlik(a: str, b: str) -> float`
  - `ciktilari_esle(uniteler, ciktilar: list[dict], kitap_no: int) -> tuple[dict[str, list[dict]], list[str]]` (`eslesme[kod] = [{"kitap", "unite", "cerceve", "konu": str | None}]`, eşleşmeyen kodlar; çerçeve `ciktilar`'ını doldurur)
  - `yapi_denetimi(harita, ciktilar, beklenen_eslesmeyen=(), basliksiz_konular=()) -> list[str]`
  - `harita_kur(anahtar, ayar, girdiler: list[dict], tablo, bugun: date) -> dict` (harita JSON biçimi spec §2.2 + `anahtar`, `uretildi`, `senaryo_tablosu`, `toplam_sayfa`, `cerceveler[].basliklar`, `eslesmedi`)
  - `pdf_girdisi(yol: Path, kitap: dict) -> {"sha256", "toplam_sayfa", "icindekiler", "xml"}`, `indir(url, dizin) -> Path`, `denetle(anahtar, yollar, harita_yolu, denetim_yolu) -> int`, `ozet_metni(harita, ayrinti=False) -> str`, `main(argv) -> int`

- [ ] **Step 1: Düzen fikstürünü yaz**

`tests/fixtures/kitap_haritasi/fen7_1_duzen.xml` — `pdftohtml -xml -i` biçiminde; değerler Fen 7-1'den ölçüldü (sayfa 24/25'teki konu sınırı, 60–71. sayfaların başlıkları, amaç satırlarının devamı ve tireyle bölünmesi), gürültü öğeleri bilerek eklendi: pusula "KUZEY", "Bilgi Bankası", "Haber", "Örnek:", sol kenardan içeride kalın satır, başlık boyunda liste girişi ("… şunlardır:", s. 111'den) ve amaç kutusunun hemen altında (26 px) gövde kenarından başlayan paragraf (s. 97'den):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE pdf2xml SYSTEM "pdf2xml.dtd">
<pdf2xml producer="poppler" version="24.02.0">
<page number="24" position="absolute" top="0" left="0" height="1169" width="829">
	<fontspec id="0" size="17" family="IUJFYC+ArialMT" color="#231f20"/>
	<fontspec id="3" size="20" family="IUJFYC+Arial" color="#ffffff"/>
	<fontspec id="5" size="17" family="IUJFYC+Arial" color="#231f20"/>
<text top="81" left="119" width="230" height="26" font="3"><b>B- Yer Tabanlı Teleskoplar</b></text>
<text top="120" left="119" width="600" height="22" font="0">Yer tabanlı teleskoplar yeryüzüne kurulur.</text>
<text top="200" left="354" width="230" height="26" font="3"><b>Uzay Gözlem Araçları Modeli</b></text>
<text top="202" left="119" width="176" height="26" font="3"><b>Performans Görevi</b></text>
<text top="236" left="120" width="55" height="23" font="5"><b>Amaç: </b></text>
<text top="236" left="178" width="500" height="22" font="0">Uzay gözlem araçları ile ilgili bilimsel model </text>
<text top="256" left="86" width="72" height="22" font="0">oluşturma</text>
<text top="282" left="116" width="618" height="22" font="0"> Bu performans görevinde sizden bir model hazırlamanız beklenmektedir.</text>
<text top="367" left="119" width="150" height="26" font="3"><b>Bağlantı Noktası</b></text>
</page>
<page number="25" position="absolute" top="0" left="0" height="1169" width="829">
<text top="72" left="119" width="140" height="26" font="3"><b>Kontrol Noktası</b></text>
<text top="110" left="119" width="400" height="22" font="0">Aşağıdaki soruları cevaplayınız.</text>
<text top="300" left="118" width="60" height="23" font="5"><b>Örnek:</b></text>
<text top="858" left="119" width="420" height="26" font="3"><b>Teknoloji ile Uzay Araştırmaları Arasındaki İlişki</b></text>
</page>
<page number="60" position="absolute" top="0" left="0" height="1169" width="829">
	<fontspec id="2" size="38" family="LUXIIW+Anton" color="#e06448"/>
<text top="64" left="249" width="400" height="48" font="2"><b>Kuvvet, İş ve Enerji İlişkisi</b></text>
<text top="160" left="119" width="150" height="26" font="3"><b>Bağlantı Noktası</b></text>
</page>
<page number="61" position="absolute" top="0" left="0" height="1169" width="829">
<text top="86" left="119" width="170" height="26" font="3"><b>Fiziksel Anlamda İş</b></text>
<text top="187" left="119" width="163" height="26" font="3"><b>Etkinlik Noktası-1</b></text>
<text top="223" left="120" width="50" height="23" font="5"><b>Amaç:</b></text>
<text top="223" left="171" width="378" height="22" font="0"> Fiziksel anlamda yapılan işin niteliklerini tanımlama</text>
<text top="258" left="119" width="620" height="22" font="0">Uygulama basamaklarını takip ederek etkinliği yapınız. Ardından değerlendirme soru</text>
<text top="924" left="119" width="163" height="26" font="3"><b>Etkinlik Noktası-2</b></text>
<text top="956" left="129" width="50" height="23" font="5"><b>Amaç:</b></text>
<text top="956" left="179" width="548" height="22" font="0"> Fiziksel anlamda iş yapma durumuna göre günlük yaşam örneklerini değer</text>
<text top="956" left="728" width="5" height="22" font="0">-</text>
<text top="976" left="95" width="63" height="22" font="0">lendirme</text>
<text top="1006" left="119" width="630" height="22" font="0">Günlük yaşam örneklerine ait görselleri inceleyerek fiziksel anlamda iş yapma durumunu </text>
</page>
<page number="63" position="absolute" top="0" left="0" height="1169" width="829">
<text top="74" left="119" width="150" height="26" font="3"><b>Bağlantı Noktası</b></text>
<text top="459" left="119" width="420" height="23" font="5"><b>Fiziksel anlamda iş yapılabilmesi için iki koşul gereklidir:</b></text>
</page>
<page number="64" position="absolute" top="0" left="0" height="1169" width="829">
<text top="73" left="119" width="140" height="26" font="3"><b>Kontrol Noktası</b></text>
</page>
<page number="65" position="absolute" top="0" left="0" height="1169" width="829">
<text top="87" left="119" width="220" height="26" font="3"><b>Enerji ve Enerji Çeşitleri</b></text>
</page>
<page number="66" position="absolute" top="0" left="0" height="1169" width="829">
<text top="141" left="119" width="163" height="26" font="3"><b>Etkinlik Noktası-3</b></text>
<text top="177" left="121" width="50" height="23" font="5"><b>Amaç:</b></text>
<text top="177" left="172" width="330" height="22" font="0"> Kinetik ve potansiyel enerjiyi karşılaştırma</text>
<text top="212" left="119" width="620" height="22" font="0">Uygulama basamaklarını takip ederek etkinliği yapınız. Ardından değerlendirme soru</text>
<text top="600" left="119" width="130" height="26" font="3"><b>Bilgi Bankası</b></text>
<text top="700" left="360" width="70" height="26" font="3"><b>KUZEY</b></text>
<text top="740" left="119" width="541" height="26" font="3"><b>Kan bağışında dikkat edilmesi gereken hususlar şunlardır:</b></text>
<text top="800" left="119" width="60" height="26" font="3"><b>Haber</b></text>
</page>
<page number="69" position="absolute" top="0" left="0" height="1169" width="829">
<text top="80" left="119" width="140" height="23" font="5"><b>Potansiyel Enerji: </b></text>
<text top="80" left="262" width="400" height="22" font="0">Cisimlerin konumlarından dolayı sahip olduğu enerjidir.</text>
<text top="434" left="119" width="220" height="23" font="5"><b>Çekim Potansiyel Enerjisi:</b></text>
<text top="515" left="119" width="240" height="23" font="5"><b>Esneklik Potansiyel Enerjisi:</b></text>
<text top="560" left="128" width="220" height="23" font="5"><b>Lacivert Resmî Ayakkabı:</b></text>
<text top="616" left="119" width="140" height="26" font="3"><b>Kontrol Noktası</b></text>
</page>
<page number="70" position="absolute" top="0" left="0" height="1169" width="829">
<text top="164" left="119" width="163" height="26" font="3"><b>Etkinlik Noktası-4</b></text>
<text top="200" left="120" width="50" height="23" font="5"><b>Amaç:</b></text>
<text top="200" left="171" width="470" height="22" font="0"> Enerji çeşitlerinden kinetik ve potansiyel enerjiyi karşılaştırma</text>
</page>
<page number="71" position="absolute" top="0" left="0" height="1169" width="829">
<text top="73" left="339" width="150" height="26" font="3"><b>Neler Öğrendik?</b></text>
</page>
</pdf2xml>
```

- [ ] **Step 2: Başarısız testleri ekle**

`tests/test_meb_kitap_haritasi.py`'nin sonuna:

```python
import hashlib  # noqa: E402
import json  # noqa: E402
from datetime import date  # noqa: E402

from src.sinav_senaryo import tablo_oku  # noqa: E402

DUZEN = (FIKSTUR / "fen7_1_duzen.xml").read_text(encoding="utf-8")
FEN_DUZENI = mkh.KITAPLAR["fen-bilimleri"]["kitaplar"][0]["duzen"]
FEN_CIKTILARI = tablo_oku()["dersler"]["Fen Bilimleri"]["ciktilar"]


def test_basliklar_etiket_amac_tanim_ve_gurultu():
    adaylar = [(a["pdf_sayfa"], a["tur"], a["metin"], a["amac"]) for a in mkh.basliklari_ayristir(DUZEN, FEN_DUZENI)]
    assert adaylar == [
        (24, "diger", "B- Yer Tabanlı Teleskoplar", None),
        (24, "etkinlik", "Performans Görevi: Uzay Gözlem Araçları Modeli",
         "Uzay gözlem araçları ile ilgili bilimsel model oluşturma"),
        (24, "baglanti", "Bağlantı Noktası", None),
        (25, "kontrol", "Kontrol Noktası", None),
        (25, "diger", "Teknoloji ile Uzay Araştırmaları Arasındaki İlişki", None),
        (60, "baglanti", "Bağlantı Noktası", None),
        (61, "diger", "Fiziksel Anlamda İş", None),
        (61, "etkinlik", "Etkinlik Noktası-1", "Fiziksel anlamda yapılan işin niteliklerini tanımlama"),
        (61, "etkinlik", "Etkinlik Noktası-2", "Fiziksel anlamda iş yapma durumuna göre günlük yaşam örneklerini değerlendirme"),
        (63, "baglanti", "Bağlantı Noktası", None),
        (64, "kontrol", "Kontrol Noktası", None),
        (65, "diger", "Enerji ve Enerji Çeşitleri", None),
        (66, "etkinlik", "Etkinlik Noktası-3", "Kinetik ve potansiyel enerjiyi karşılaştırma"),
        (69, "tanim", "Potansiyel Enerji", None),
        (69, "tanim", "Çekim Potansiyel Enerjisi", None),
        (69, "tanim", "Esneklik Potansiyel Enerjisi", None),
        (69, "kontrol", "Kontrol Noktası", None),
        (70, "etkinlik", "Etkinlik Noktası-4", "Enerji çeşitlerinden kinetik ve potansiyel enerjiyi karşılaştırma"),
        (71, "ozet", "Neler Öğrendik?", None),
    ]


def test_atla_listesi_basligi_dusurur():
    duzen = {**FEN_DUZENI, "atla": ("B- Yer Tabanlı Teleskoplar",)}
    assert "B- Yer Tabanlı Teleskoplar" not in [a["metin"] for a in mkh.basliklari_ayristir(DUZEN, duzen)]


def test_basliklar_konu_sinirina_gore_yerlesir_ve_konu_bitisi_uzar():
    uniteler = mkh.icindekiler_ayristir(ICINDEKILER)
    mkh.basliklari_yerlestir(uniteler, mkh.basliklari_ayristir(DUZEN, FEN_DUZENI), 1)
    uzay = uniteler[0]["cerceveler"][0]["konular"]
    assert [(b["tur"], b["ad"], b["sayfa"]) for b in uzay[0]["basliklar"]] == [
        ("diger", "B- Yer Tabanlı Teleskoplar", 23), ("etkinlik", "Performans Görevi: Uzay Gözlem Araçları Modeli", 23),
        ("baglanti", "Bağlantı Noktası", 23), ("kontrol", "Kontrol Noktası", 24)]
    assert uzay[0]["son_sayfa"] == 24          # İçindekiler 23 der; son blok s. 24'ün üstüne taşar
    assert uzay[1]["basliklar"] == []          # konunun kendi başlığı listeye girmez
    kuvvet = uniteler[1]["cerceveler"][0]
    assert [(b["tur"], b["ad"], b["sayfa"]) for b in kuvvet["basliklar"]] == [("baglanti", "Bağlantı Noktası", 59)]
    assert [(b["ad"], b["sayfa"]) for b in kuvvet["konular"][0]["basliklar"]] == [
        ("Etkinlik Noktası-1", 60), ("Etkinlik Noktası-2", 60), ("Bağlantı Noktası", 62), ("Kontrol Noktası", 63)]
    assert kuvvet["konular"][0]["basliklar"][0]["amac"] == "Fiziksel anlamda yapılan işin niteliklerini tanımlama"
    assert [(b["tur"], b["ad"], b["sayfa"]) for b in kuvvet["konular"][1]["basliklar"]] == [
        ("etkinlik", "Etkinlik Noktası-3", 65), ("tanim", "Potansiyel Enerji", 68),
        ("tanim", "Çekim Potansiyel Enerjisi", 68), ("tanim", "Esneklik Potansiyel Enerjisi", 68),
        ("kontrol", "Kontrol Noktası", 68), ("etkinlik", "Etkinlik Noktası-4", 69), ("ozet", "Neler Öğrendik?", 70)]


def test_cikti_eslemesi_cerceve_adindan_ve_konu_benzerliginden():
    uniteler = mkh.icindekiler_ayristir(ICINDEKILER)
    eslesme, eslesmedi = mkh.ciktilari_esle(uniteler, FEN_CIKTILARI, 0)
    assert eslesmedi == []
    konular = {kod: [e["konu"] for e in yollar] for kod, yollar in eslesme.items()}
    assert konular["FB.7.1.1"] == ["Uzay Teknolojileri", "Teknoloji ile Uzay Araştırmaları Arasındaki İlişki"]
    assert konular["FB.7.1.3"] == ["Teknoloji ile Uzay Araştırmaları Arasındaki İlişki"]
    assert konular["FB.7.2.1"] == ["Fiziksel Anlamda İş"]
    assert konular["FB.7.2.2"] == ["Enerji ve Enerji Çeşitleri"]
    assert konular["FB.7.3.4"] == ["Kan Bağışının Toplum Açısından Önemi"]
    assert eslesme["FB.7.2.1"] == [{"kitap": 0, "unite": 2, "cerceve": 1, "konu": "Fiziksel Anlamda İş"}]
    assert uniteler[1]["cerceveler"][0]["ciktilar"] == ["FB.7.2.1", "FB.7.2.2"]


def test_konu_adi_cercevede_yoksa_eslesmedi_ve_denetim_reddeder():
    """Review Focus: kitapta karşılığı bulunamayan çıktı açıkça eslesmedi'ye yazılır; beklenmiyorsa harita yazılmaz."""
    uniteler = mkh.icindekiler_ayristir(ICINDEKILER)
    ciktilar = [dict(c, konu="Olmayan Çerçeve") if c["kod"] == "FB.7.1.3" else c for c in FEN_CIKTILARI]
    eslesme, eslesmedi = mkh.ciktilari_esle(uniteler, ciktilar, 0)
    assert eslesmedi == ["FB.7.1.3"] and "FB.7.1.3" not in eslesme
    harita = {"kitaplar": [], "eslesme": eslesme, "eslesmedi": eslesmedi}
    assert mkh.yapi_denetimi(harita, ciktilar) == ["beklenmeyen eşleşmeyen çıktı: FB.7.1.3"]
    assert mkh.yapi_denetimi(harita, ciktilar, beklenen_eslesmeyen=("FB.7.1.3",)) == []


def _mini_harita(**konu_degisikligi):
    konu = {"ad": "Konu A", "sayfa": 10, "son_sayfa": 12,
            "basliklar": [{"ad": "Kontrol Noktası", "tur": "kontrol", "amac": None, "sayfa": 11}], **konu_degisikligi}
    return {"kitaplar": [{"toplam_sayfa": 100, "sayfa_kaymasi": 1, "uniteler": [{"no": 1, "ad": "Ü", "sayfa": 9, "son_sayfa": 20,
            "cerceveler": [{"no": 1, "ad": "Ç", "sayfa": 9, "son_sayfa": 20, "ciktilar": ["X.7.1.1"], "basliklar": [],
                            "konular": [konu]}]}]}],
            "eslesme": {"X.7.1.1": [{"kitap": 0, "unite": 1, "cerceve": 1, "konu": "Konu A"}]}, "eslesmedi": []}


def test_yapi_denetimi_sayfa_baslik_ve_eksik_cikti():
    ciktilar = [{"kod": "X.7.1.1"}]
    assert mkh.yapi_denetimi(_mini_harita(), ciktilar) == []
    assert mkh.yapi_denetimi(_mini_harita(basliklar=[]), ciktilar) == ["konunun başlığı yok: Konu A"]
    assert mkh.yapi_denetimi(_mini_harita(basliklar=[]), ciktilar, basliksiz_konular=("Konu A",)) == []
    assert mkh.yapi_denetimi(_mini_harita(son_sayfa=30), ciktilar) == ["konu çerçevenin dışında: Konu A"]
    assert mkh.yapi_denetimi(_mini_harita(), [{"kod": "X.7.1.1"}, {"kod": "X.7.1.2"}]) == ["çıktı haritada yok: X.7.1.2"]
    yarim = {**_mini_harita(), "eslesme": {}, "eslesmedi": ["X.7.1.1"]}
    assert mkh.yapi_denetimi(yarim, ciktilar, beklenen_eslesmeyen=("X.7.1.1",)) == [
        "çıktıların yarısından çoğu eşleşmedi (1/1)"]


MINI_ICINDEKILER = ("İçindekiler\n1. Ünite      Deneme Ünitesi\nÖn Değerlendirme ........ 9\n1. Çerçeve Bir ......... 10\n"
                    "Konu Bir Anlama ........ 11\nÜnite Sonu Değerlendirme ....... 15\nSözlük ...... 16\n")
MINI_DUZEN = ('<?xml version="1.0" encoding="UTF-8"?>\n<pdf2xml>\n<page number="12" position="absolute" top="0" left="0" '
              'height="1169" width="829">\n<fontspec id="3" size="20" family="IUJFYC+Arial" color="#ffffff"/>\n'
              '<text top="80" left="119" width="200" height="26" font="3"><b>Konu Bir Anlama</b></text>\n'
              '<text top="400" left="119" width="140" height="26" font="3"><b>Kontrol Noktası</b></text>\n</page>\n</pdf2xml>\n')


@pytest.fixture
def deneme_kitabi(monkeypatch):
    ayar = {"ders": "Deneme", "beklenen_eslesmeyen": (), "basliksiz_konular": (), "kitaplar": [{
        "baslik": "Deneme 7", "pdf_url": "https://ornek.invalid/d.pdf", "kaynak_sayfa": None, "baski": "2026-2027",
        "sayfa_kaymasi": 1, "icindekiler_pdf_sayfalari": (8, 8), "duzen": {**FEN_DUZENI, "atla": ()}}]}
    monkeypatch.setitem(mkh.KITAPLAR, "deneme", ayar)
    monkeypatch.setattr(mkh, "tablo_oku", lambda: {
        "kaynak": {"meb_guncelleme": "2026-09-10T17:27"},
        "dersler": {"Deneme": {"sha256": "ab" * 32, "ciktilar": [
            {"kod": "D.7.1.1", "metin": "Konu bir anlama", "alan": None, "konu": "Çerçeve Bir"}]}}})
    return ayar


def test_main_haritayi_yazar_ve_onayi_kaydeder(deneme_kitabi, monkeypatch, tmp_path):
    monkeypatch.setattr(mkh, "pdf_girdisi", lambda yol, kitap: {
        "sha256": "f" * 64, "toplam_sayfa": 30, "icindekiler": MINI_ICINDEKILER, "xml": MINI_DUZEN})
    cikti = tmp_path / "deneme.json"
    assert mkh.main(["deneme", "--pdf", "1=/yok.pdf", "--cikti", str(cikti), "--denetim-kim", "Test"]) == 0
    h = json.loads(cikti.read_text(encoding="utf-8"))
    assert h["surum"] == 1 and h["anahtar"] == "deneme" and h["ders"] == "Deneme"
    assert h["denetim"] == {"kim": "Test", "tarih": date.today().isoformat()}
    assert h["senaryo_tablosu"] == {"meb_guncelleme": "2026-09-10T17:27", "ders_sha256": "ab" * 32}
    assert h["eslesme"] == {"D.7.1.1": [{"kitap": 0, "unite": 1, "cerceve": 1, "konu": "Konu Bir Anlama"}]}
    kitap = h["kitaplar"][0]
    assert (kitap["sha256"], kitap["toplam_sayfa"], kitap["sayfa_kaymasi"]) == ("f" * 64, 30, 1)
    konu = kitap["uniteler"][0]["cerceveler"][0]["konular"][0]
    assert konu["basliklar"] == [{"ad": "Kontrol Noktası", "tur": "kontrol", "amac": None, "sayfa": 11}]


def test_main_yapi_denetiminde_yazmaz(deneme_kitabi, monkeypatch, tmp_path, capsys):
    bos_duzen = MINI_DUZEN.replace("Kontrol Noktası", "Haber")
    monkeypatch.setattr(mkh, "pdf_girdisi", lambda yol, kitap: {
        "sha256": "f" * 64, "toplam_sayfa": 30, "icindekiler": MINI_ICINDEKILER, "xml": bos_duzen})
    cikti = tmp_path / "deneme.json"
    assert mkh.main(["deneme", "--pdf", "1=/yok.pdf", "--cikti", str(cikti)]) == 1
    assert not cikti.exists()
    assert "konunun başlığı yok: Konu Bir Anlama" in capsys.readouterr().err


def test_denetle_sha256_degisimini_yazar(tmp_path, capsys):
    """Review Focus (K12): MEB kitabı sessizce değişirse denetim dosyası yeni sha256'yı taşır."""
    pdf = tmp_path / "k.pdf"
    pdf.write_bytes(b"%PDF yeni baski")
    harita = tmp_path / "h.json"
    harita.write_text(json.dumps({"kitaplar": [{"baslik": "Fen 7", "pdf_url": "https://ornek.invalid/fen.pdf",
                                                "sha256": "0" * 64}]}), encoding="utf-8")
    denetim = tmp_path / "out" / "kitap_denetimi.json"
    assert mkh.denetle("fen-bilimleri", [pdf], harita, denetim) == 0
    kayit = json.loads(denetim.read_text(encoding="utf-8"))["fen-bilimleri"]
    assert kayit["kitaplar"] == [{"pdf_url": "https://ornek.invalid/fen.pdf",
                                  "sha256": hashlib.sha256(b"%PDF yeni baski").hexdigest()}]
    assert kayit["denetlendi"] == date.today().isoformat()
    assert "değişti: Fen 7" in capsys.readouterr().out
```

- [ ] **Step 3: Testi koş, düştüğünü gör**

Run: `env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_meb_kitap_haritasi.py`
Expected: FAIL — `AttributeError: module 'scripts.meb_kitap_haritasi' has no attribute 'KITAPLAR'`.

- [ ] **Step 4: Ayarları ve başlık ayrıştırmayı yaz**

`scripts/meb_kitap_haritasi.py`'de `_SAYI` tanımının altına:

```python
# Ders başına ayar. Ölçüldü (2026-10-25, Fen 7-1): pdftohtml'de başlık size 20 (Arial, beyaz bant), gövde 17, içerik
# çerçevesi adı Anton; başlıklar sol 107–124 px'te, gövde 119 px'te; kalın tanım başlığı gövde boyunda ve ":" ile biter.
# "atla": onayda gürültü bulunan başlıklar (s. 49 kavram haritası kutusundaki "Bulutsu").
KITAPLAR: dict[str, dict] = {
    "fen-bilimleri": {
        "ders": "Fen Bilimleri",
        "beklenen_eslesmeyen": (),
        "basliksiz_konular": (),
        "kitaplar": [{
            "baslik": "Fen Bilimleri 7 (1. Kitap)",
            "pdf_url": "https://cdn.eba.gov.tr/temel-egitim/yayin/2026-2027/ktp/fenbilimleri7-1_v3.pdf",
            "kaynak_sayfa": None,
            "baski": "2026-2027",
            "sayfa_kaymasi": 1,
            "icindekiler_pdf_sayfalari": (8, 8),
            "duzen": {"baslik_boyu": 20, "govde_boyu": 17, "cerceve_ailesi": "Anton", "baslik_sol_en_cok": 130,
                      "govde_sol": 119, "tanim": True, "atla": ("Bulutsu",)},
        }],
    },
}
# Pedagojik bloklar (katlanmış önek → tür) ve başlık sayılmayan kutu etiketleri / tanım dışı kalın satırlar.
ETIKETLER = (("etkinlik noktasi", "etkinlik"), ("kesif noktasi", "etkinlik"), ("performans gorevi", "etkinlik"),
             ("baglanti noktasi", "baglanti"), ("kontrol noktasi", "kontrol"), ("neler ogrendik", "ozet"))
KUTU_ETIKETLERI = ("haber", "bilgi bankasi", "tarihe not dusenler")
TANIM_DISI = ("ornek", "ornek problem", "amac", "amaci", "islevi", "sorunlar", "cozum onerileri")
_DURAK = frozenset({"ile", "ve", "veya", "icin", "ilgili", "yonelik", "olan", "gibi", "bir", "bu", "da", "de"})
YAKINLIK = 0.1


def _ogeler(xml: str) -> list[dict]:
    """pdftohtml -xml → metin öğeleri (sayfa, üst, sol sırasıyla); fontspec kimlikleri sayfalar arasında geçerlidir."""
    kok = ET.fromstring(xml.encode("utf-8"))
    boylar: dict[str, tuple[int, str]] = {}
    out = []
    for sayfa in kok.iter("page"):
        no = int(sayfa.get("number"))
        for el in sayfa:
            if el.tag == "fontspec":
                boylar[el.get("id")] = (int(el.get("size")), el.get("family") or "")
            elif el.tag == "text":
                boy, aile = boylar.get(el.get("font"), (0, ""))
                metin = " ".join("".join(el.itertext()).split())
                if metin:
                    out.append({"sayfa": no, "ust": int(el.get("top")), "sol": int(el.get("left")), "boy": boy,
                                "aile": aile, "kalin": el.find(".//b") is not None, "metin": metin})
    out.sort(key=lambda o: (o["sayfa"], o["ust"], o["sol"]))
    return out


def _etiket_turu(katli: str) -> str | None:
    return next((tur for on, tur in ETIKETLER if katli.startswith(on)), None)


def _amac(ogeler: list[dict], baslik: dict) -> str | None:
    """Etkinlik başlığının altındaki "Amaç:" satırı ve hemen alttaki (≤ 26 px, etiketin 15 px'ten fazla solunda — kutunun
    kenarına taşan) en çok iki devam satırı; tireyle bölünen sözcük birleşir. Paragraf gövde kenarında (etiketle aynı
    hizada) başlar, alınmaz (ölçüldü: devam satırı sol 86–95 px, etiket 120–129 px, paragraf 119 px)."""
    etiketler = [o for o in ogeler if o["sayfa"] == baslik["sayfa"] and o["kalin"]
                 and 0 < o["ust"] - baslik["ust"] <= 120 and katla(o["metin"]).rstrip(": ") == "amac"]
    if not etiketler:
        return None
    e = etiketler[0]
    ayni = sorted((o for o in ogeler if o["sayfa"] == e["sayfa"] and abs(o["ust"] - e["ust"]) <= 3 and o["sol"] > e["sol"]),
                  key=lambda o: o["sol"])
    satirlar = [" ".join(o["metin"] for o in ayni)]
    ust = e["ust"]
    for _ in range(2):
        alt = sorted((o for o in ogeler if o["sayfa"] == e["sayfa"] and 12 < o["ust"] - ust <= 26
                      and o["sol"] < e["sol"] - 15), key=lambda o: o["sol"])
        if not alt:
            break
        satirlar.append(" ".join(o["metin"] for o in alt))
        ust = alt[0]["ust"]
    metin = ""
    for s in satirlar:
        s = s.strip()
        metin = metin[:-1].rstrip() + s if metin.endswith("-") else f"{metin} {s}".strip()
    return " ".join(metin.split()) or None


def basliklari_ayristir(xml: str, duzen: dict) -> list[dict]:
    """Bölüm içi başlık adayları: başlık boyundaki (çerçeve ailesi dışı) satırlar — aynı satırdaki parçalar birleşir
    ("Performans Görevi" + adı) —, pedagojik etiketler türleriyle; kutu etiketleri, sol kenardan içerideki şekil
    yazıları ve ":" ile biten liste girişleri atılır; `tanim` açıksa gövde boyunda kalın, ":" ile biten, ≤ 4 sözcüklük, gövde kenarındaki satırlar."""
    ogeler = _ogeler(xml)
    atla = {katla(a) for a in duzen.get("atla", ())}
    buyuk = [o for o in ogeler if o["boy"] == duzen["baslik_boyu"] and duzen["cerceve_ailesi"] not in o["aile"]]
    kullanildi: set[int] = set()
    adaylar = []
    for i, o in enumerate(buyuk):
        if i in kullanildi:
            continue
        satir = [j for j in range(i, len(buyuk)) if j not in kullanildi and buyuk[j]["sayfa"] == o["sayfa"]
                 and abs(buyuk[j]["ust"] - o["ust"]) <= 8]
        kullanildi.update(satir)
        parcalar = sorted((buyuk[j] for j in satir), key=lambda p: p["sol"])
        ilk = parcalar[0]
        tur = _etiket_turu(katla(ilk["metin"]))
        if tur is None:
            if katla(ilk["metin"]) in KUTU_ETIKETLERI or ilk["sol"] > duzen["baslik_sol_en_cok"] or len(ilk["metin"]) < 4:
                continue
            tur, metin = "diger", " ".join(p["metin"] for p in parcalar)
            if metin.endswith(":"):
                continue          # liste girişi ("… hususlar şunlardır:"), başlık değil
        else:
            ek = " ".join(p["metin"] for p in parcalar[1:])
            metin = f"{ilk['metin']}: {ek}" if ek else ilk["metin"]
        if katla(metin) in atla:
            continue
        adaylar.append({"pdf_sayfa": ilk["sayfa"], "ust": min(p["ust"] for p in parcalar), "metin": metin, "tur": tur,
                        "amac": _amac(ogeler, ilk) if tur == "etkinlik" else None})
    if duzen.get("tanim"):
        for o in ogeler:
            if o["boy"] != duzen["govde_boyu"] or not o["kalin"] or not o["metin"].endswith(":"):
                continue
            ad = " ".join(o["metin"].rstrip(":").split())
            if abs(o["sol"] - duzen["govde_sol"]) > 3 or len(ad.split()) > 4 or katla(ad) in TANIM_DISI or katla(ad) in atla:
                continue
            adaylar.append({"pdf_sayfa": o["sayfa"], "ust": o["ust"], "metin": ad, "tur": "tanim", "amac": None})
    adaylar.sort(key=lambda a: (a["pdf_sayfa"], a["ust"]))
    return adaylar


def basliklari_yerlestir(uniteler: list[dict], adaylar: list[dict], kayma: int) -> None:
    """Adayları (sayfa, üst) sırasıyla çerçeve ve konulara dağıtır. Konunun sınırı kendi başlığının konumudur (bulunamazsa
    başlangıç sayfasının tepesi): sonraki konunun başlangıç sayfasında, onun başlığının üstünde kalan blok önceki konuya
    aittir. Konu adının kendisi listeye girmez; konunun bitişi içine düşen son başlığın sayfasına uzar."""
    for u in uniteler:
        for f in u["cerceveler"]:
            f["basliklar"] = []
            f_bas, f_son = (f["sayfa"] + kayma, -1), f["son_sayfa"] + kayma
            adlar = {katla(k["ad"]) for k in f["konular"]}
            sinirlar = []
            for k in f["konular"]:
                k["basliklar"] = []
                p = k["sayfa"] + kayma
                ust = next((a["ust"] for a in adaylar if a["pdf_sayfa"] == p and katla(a["metin"]) == katla(k["ad"])), -1)
                sinirlar.append(((p, ust), k))
            for a in adaylar:
                konum = (a["pdf_sayfa"], a["ust"])
                if konum < f_bas or a["pdf_sayfa"] > f_son or katla(a["metin"]) in adlar:
                    continue
                hedef = f
                for sinir, k in sinirlar:
                    if konum >= sinir:
                        hedef = k
                hedef["basliklar"].append({"ad": a["metin"], "tur": a["tur"], "amac": a["amac"], "sayfa": a["pdf_sayfa"] - kayma})
            for k in f["konular"]:
                k["son_sayfa"] = max([k["son_sayfa"], *(b["sayfa"] for b in k["basliklar"])])
```

- [ ] **Step 5: Eşleme, denetim, kurma ve CLI'ı yaz**

Aynı dosyaya, `basliklari_yerlestir`'in altına:

```python
def _kokler(metin: str) -> set[str]:
    return {s[:5] for s in re.findall(r"[a-z0-9]+", katla(metin)) if len(s) >= 3 and s not in _DURAK}


def benzerlik(a: str, b: str) -> float:
    """sinav_senaryo._puan ile aynı ölçü: biri ötekinin ≥ 10 harflik parçasıysa 1; değilse 5 harflik kök Dice'ı."""
    x, y = katla(a), katla(b)
    if len(min(x, y, key=len)) >= 10 and (x in y or y in x):
        return 1.0
    ka, kb = _kokler(x), _kokler(y)
    return 2 * len(ka & kb) / (len(ka) + len(kb)) if ka and kb else 0.0


def ciktilari_esle(uniteler: list[dict], ciktilar: list[dict], kitap_no: int) -> tuple[dict[str, list[dict]], list[str]]:
    """Çıktı → çerçeve: tablonun `konu` alanı İçindekiler'deki çerçeve adıyla katlanmış eşit. Çerçeve içinde konu: çıktı
    metnine en benzer konular (en iyiye YAKINLIK kadar yakın olanlar, okunuş sırasıyla); hiçbir konuya benzemiyorsa
    çerçevenin tamamı (`konu: None`). Çerçevesi bulunamayan çıktı eşleşmeyendir."""
    eslesme: dict[str, list[dict]] = {}
    eslesmedi: list[str] = []
    for c in ciktilar:
        hedef = katla(c.get("konu") or "")
        bulunan = next(((u, f) for u in uniteler for f in u["cerceveler"] if hedef and katla(f["ad"]) == hedef), None)
        if bulunan is None:
            eslesmedi.append(c["kod"])
            continue
        u, f = bulunan
        f["ciktilar"].append(c["kod"])
        puanlar = [(k["ad"], benzerlik(c["metin"], k["ad"])) for k in f["konular"]]
        en = max((p for _, p in puanlar), default=0.0)
        secilen = [ad for ad, p in puanlar if en > 0 and p >= en - YAKINLIK] or [None]
        eslesme[c["kod"]] = [{"kitap": kitap_no, "unite": u["no"], "cerceve": f["no"], "konu": ad} for ad in secilen]
    return eslesme, eslesmedi


def yapi_denetimi(harita: dict, ciktilar: list[dict], beklenen_eslesmeyen=(), basliksiz_konular=()) -> list[str]:
    """Spec §2.2 yapı denetimi; boş liste geçti demektir. Geçmezse harita yazılmaz."""
    hatalar = []
    for kitap in harita["kitaplar"]:
        sinir = kitap["toplam_sayfa"] - kitap["sayfa_kaymasi"]
        onceki = 0
        for u in kitap["uniteler"]:
            for f in u["cerceveler"]:
                if not (1 <= f["sayfa"] <= f["son_sayfa"] <= sinir):
                    hatalar.append(f"çerçeve sayfaları geçersiz: {f['ad']} s. {f['sayfa']}–{f['son_sayfa']}")
                if f["sayfa"] < onceki:
                    hatalar.append(f"sayfalar geriye gidiyor: {f['ad']}")
                onceki = f["sayfa"]
                for k in f["konular"]:
                    if not (f["sayfa"] <= k["sayfa"] <= k["son_sayfa"] <= f["son_sayfa"]):
                        hatalar.append(f"konu çerçevenin dışında: {k['ad']}")
                    if not k["basliklar"] and k["ad"] not in basliksiz_konular:
                        hatalar.append(f"konunun başlığı yok: {k['ad']}")
                    for b in k["basliklar"]:
                        if not (k["sayfa"] <= b["sayfa"] <= k["son_sayfa"]):
                            hatalar.append(f"başlık konunun dışında: {k['ad']} › {b['ad']} s. {b['sayfa']}")
    kodlar = [c["kod"] for c in ciktilar]
    eslesmedi = set(harita["eslesmedi"])
    hatalar += [f"çıktı haritada yok: {kod}" for kod in kodlar if kod not in harita["eslesme"] and kod not in eslesmedi]
    hatalar += [f"beklenmeyen eşleşmeyen çıktı: {kod}" for kod in sorted(eslesmedi - set(beklenen_eslesmeyen))]
    if kodlar and len(eslesmedi) * 2 > len(kodlar):
        hatalar.append(f"çıktıların yarısından çoğu eşleşmedi ({len(eslesmedi)}/{len(kodlar)})")
    return hatalar


def _kod_sirasi(kod: str) -> tuple:
    return tuple((0, int(p), "") if p.isdigit() else (1, 0, p) for p in kod.split("."))


def harita_kur(anahtar: str, ayar: dict, girdiler: list[dict], tablo: dict, bugun: date) -> dict:
    """Kitap girdilerinden harita (denetimsiz; `main` yapı denetimini uygular). Bir çıktı ilk eşleştiği kitapta kalır."""
    dt = tablo["dersler"][ayar["ders"]]
    kitaplar, eslesme = [], {}
    kalan = list(dt["ciktilar"])
    for no, (kitap, girdi) in enumerate(zip(ayar["kitaplar"], girdiler)):
        uniteler = icindekiler_ayristir(girdi["icindekiler"])
        basliklari_yerlestir(uniteler, basliklari_ayristir(girdi["xml"], kitap["duzen"]), kitap["sayfa_kaymasi"])
        bulunan, _ = ciktilari_esle(uniteler, kalan, no)
        eslesme.update(bulunan)
        kalan = [c for c in kalan if c["kod"] not in bulunan]
        kitaplar.append({"baslik": kitap["baslik"], "pdf_url": kitap["pdf_url"], "kaynak_sayfa": kitap["kaynak_sayfa"],
                         "sha256": girdi["sha256"], "baski": kitap["baski"], "sayfa_kaymasi": kitap["sayfa_kaymasi"],
                         "toplam_sayfa": girdi["toplam_sayfa"], "uniteler": uniteler})
    return {"surum": SURUM, "ders": ayar["ders"], "anahtar": anahtar, "uretildi": bugun.isoformat(),
            "senaryo_tablosu": {"meb_guncelleme": tablo["kaynak"].get("meb_guncelleme"), "ders_sha256": dt.get("sha256")},
            "kitaplar": kitaplar, "eslesme": {k: eslesme[k] for k in sorted(eslesme, key=_kod_sirasi)},
            "eslesmedi": sorted((c["kod"] for c in kalan), key=_kod_sirasi), "denetim": {"kim": None, "tarih": None}}


def _arac(*argv: str) -> str:
    return subprocess.run(list(argv), capture_output=True, text=True, check=True, timeout=300).stdout


def _sha256(yol: Path) -> str:
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        for parca in iter(lambda: f.read(1 << 20), b""):
            h.update(parca)
    return h.hexdigest()


def pdf_girdisi(yol: Path, kitap: dict) -> dict:
    """PDF'ten İçindekiler metni (-layout) ve ünitelerin sayfa aralığının düzeni (pdftohtml -xml)."""
    y = str(yol)
    toplam = int(re.search(r"^Pages:\s*(\d+)", _arac("pdfinfo", y), re.M).group(1))
    a, b = kitap["icindekiler_pdf_sayfalari"]
    icindekiler = _arac("pdftotext", "-f", str(a), "-l", str(b), "-layout", y, "-")
    uniteler = icindekiler_ayristir(icindekiler)
    ilk = uniteler[0]["sayfa"] + kitap["sayfa_kaymasi"]
    son = uniteler[-1]["son_sayfa"] + kitap["sayfa_kaymasi"]
    xml = _arac("pdftohtml", "-xml", "-i", "-q", "-f", str(ilk), "-l", str(son), "-stdout", y)
    return {"sha256": _sha256(yol), "toplam_sayfa": toplam, "icindekiler": icindekiler, "xml": xml}


def indir(url: str, dizin: Path, sinir: int = 300 * 1024 * 1024) -> Path:
    import requests
    hedef = dizin / "kitap.pdf"
    toplam = 0
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(hedef, "wb") as f:
            for parca in r.iter_content(1 << 20):
                toplam += len(parca)
                if toplam > sinir:
                    raise YapiHatasi(f"PDF {sinir // 2**20} MB sınırını aşıyor: {url}")
                f.write(parca)
    return hedef


def denetle(anahtar: str, yollar: list[Path], harita_yolu: Path, denetim_yolu: Path = DENETIM_DOSYASI) -> int:
    """K12: PDF'lerin sha256'sını haritadakiyle karşılaştırır, output/kitap_denetimi.json'a yazar (model okur)."""
    try:
        harita = json.loads(Path(harita_yolu).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        print(f"harita okunamadı: {harita_yolu}", file=sys.stderr)
        return 1
    kayit = {"denetlendi": date.today().isoformat(), "kitaplar": []}
    degisen = []
    for kitap, yol in zip(harita["kitaplar"], yollar):
        sha = _sha256(yol)
        kayit["kitaplar"].append({"pdf_url": kitap["pdf_url"], "sha256": sha})
        if sha != kitap["sha256"]:
            degisen.append(kitap["baslik"])
    try:
        tum = json.loads(Path(denetim_yolu).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        tum = {}
    if not isinstance(tum, dict):
        tum = {}
    tum[anahtar] = kayit
    atomic_json_dump(tum, str(denetim_yolu))
    print("değişti: " + ", ".join(degisen) if degisen else "kitaplar haritadakiyle aynı")
    return 0


def ozet_metni(harita: dict, ayrinti: bool = False) -> str:
    satirlar = []
    for kitap in harita["kitaplar"]:
        cer = [f for u in kitap["uniteler"] for f in u["cerceveler"]]
        kon = [k for f in cer for k in f["konular"]]
        bas = sum(len(k["basliklar"]) for k in kon) + sum(len(f["basliklar"]) for f in cer)
        satirlar.append(f"{kitap['baslik']}: {len(kitap['uniteler'])} ünite, {len(cer)} çerçeve, {len(kon)} konu, {bas} başlık")
        if not ayrinti:
            continue
        for u in kitap["uniteler"]:
            satirlar.append(f"{u['no']}. Ünite {u['ad']} · s. {u['sayfa']}–{u['son_sayfa']}")
            for f in u["cerceveler"]:
                satirlar.append(f"  {f['no']}. {f['ad']} · s. {f['sayfa']}–{f['son_sayfa']} · çıktılar: {', '.join(f['ciktilar']) or '—'}")
                satirlar += [f"      [{b['tur']}] {b['ad']} · s. {b['sayfa']}" for b in f["basliklar"]]
                for k in f["konular"]:
                    satirlar.append(f"    {k['ad']} · s. {k['sayfa']}–{k['son_sayfa']}")
                    satirlar += [f"      [{b['tur']}] {b['ad']}{' — ' + b['amac'] if b['amac'] else ''} · s. {b['sayfa']}"
                                 for b in k["basliklar"]]
    satirlar.append(f"eşleşmeyen çıktı: {', '.join(harita['eslesmedi']) or 'yok'}")
    return "\n".join(satirlar)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="MEB ders kitabı haritası → src/kitap_haritalari/<anahtar>.json")
    p.add_argument("anahtar", choices=sorted(KITAPLAR))
    p.add_argument("--pdf", action="append", default=[], metavar="N=YOL", help="N. kitap için yerel PDF (1'den)")
    p.add_argument("--cikti", type=Path)
    p.add_argument("--denetle", action="store_true", help="yalnız sha256'yı mevcut haritayla karşılaştır")
    p.add_argument("--denetim-kim", help="elle onayı yapan; denetim alanına bugünün tarihiyle yazılır")
    p.add_argument("--kuru", action="store_true", help="yazma; ayrıntılı ağacı ve denetimi yazdır")
    a = p.parse_args(argv)
    ayar = KITAPLAR[a.anahtar]
    yerel: dict[int, Path] = {}
    for s in a.pdf:
        n, _, yol = s.partition("=")
        if not n.isdigit() or not yol:
            p.error(f"--pdf N=YOL bekleniyor: {s}")
        yerel[int(n) - 1] = Path(yol)
    cikti = a.cikti or CIKTI_DIZINI / f"{a.anahtar}.json"
    with tempfile.TemporaryDirectory(prefix="tedy-kitap-") as gecici:
        yollar = []
        for i, kitap in enumerate(ayar["kitaplar"]):
            if i in yerel:
                yollar.append(yerel[i])
            else:
                d = Path(gecici) / str(i)
                d.mkdir()
                yollar.append(indir(kitap["pdf_url"], d))
        if a.denetle:
            return denetle(a.anahtar, yollar, cikti)
        tablo = tablo_oku()
        if tablo is None:
            print("senaryo tablosu okunamadı", file=sys.stderr)
            return 1
        try:
            harita = harita_kur(a.anahtar, ayar, [pdf_girdisi(y, k) for y, k in zip(yollar, ayar["kitaplar"])], tablo,
                                date.today())
        except YapiHatasi as h:
            print(f"yapı hatası, {cikti} yazılmadı: {h}", file=sys.stderr)
            return 1
    hatalar = yapi_denetimi(harita, tablo["dersler"][ayar["ders"]]["ciktilar"], ayar.get("beklenen_eslesmeyen", ()),
                            ayar.get("basliksiz_konular", ()))
    print(ozet_metni(harita, ayrinti=a.kuru))
    if hatalar:
        print(f"yapı denetimi geçmedi, {cikti} yazılmadı:\n  " + "\n  ".join(hatalar), file=sys.stderr)
        return 1
    if a.denetim_kim:
        harita["denetim"] = {"kim": a.denetim_kim, "tarih": date.today().isoformat()}
    if not a.kuru:
        atomic_json_dump(harita, str(cikti))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Testi koş, geçtiğini gör**

Run: `env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_meb_kitap_haritasi.py`
Expected: PASS (16 test).

- [ ] **Step 7: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-hazirligi
git log --oneline -3 && git status --short
git add scripts/meb_kitap_haritasi.py tests/fixtures/kitap_haritasi/fen7_1_duzen.xml tests/test_meb_kitap_haritasi.py
git commit -m "$(cat <<'EOF'
feat(sinav-hazirligi): kitap haritası — bölüm içi başlıklar, çıktı eşlemesi, yapı denetimi ve sha256 denetimi

pdftohtml -xml düzeninden pedagojik bloklar (amaçlarıyla), alt başlıklar ve kalın tanımlar; çıktı → çerçeve
tablonun konu alanından, çerçeve içinde konu kök benzerliğinden; denetim geçmezse harita yazılmaz.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Fen 7-1 haritasının üretimi, elle onayı ve değişmez testleri

**Files:**
- Create: `src/kitap_haritalari/fen-bilimleri.json` (betik üretir)
- Modify: `scripts/meb_kitap_haritasi.py` (yalnız onayda bulunan gürültü için `KITAPLAR["fen-bilimleri"]` `atla` / `basliksiz_konular`)
- Test: `tests/test_kitap_haritasi_fen.py`

**Interfaces:**
- Consumes: Görev 4'ün CLI'ı ve `yapi_denetimi`; `/tmp/meb-kitap-yoklama/fen7-1.pdf` (86,8 MB, indirilmiş).
- Produces: `src/kitap_haritalari/fen-bilimleri.json` — Görev 6–8'in modeli ve Görev 8'in pano fikstürleri bunu okur. Ölçülmüş değerler: `FB.7.2.1` → `{"kitap": 0, "unite": 2, "cerceve": 1, "konu": "Fiziksel Anlamda İş"}` (s. 60–63); `toplam_sayfa` 153; `sayfa_kaymasi` 1.

- [ ] **Step 1: Kuru koşu — ağacı ve denetimi oku**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-hazirligi
sha256sum /tmp/meb-kitap-yoklama/fen7-1.pdf
env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -I scripts/meb_kitap_haritasi.py fen-bilimleri \
  --pdf 1=/tmp/meb-kitap-yoklama/fen7-1.pdf --kuru > /tmp/tedy-fen-harita-agac.txt; echo "çıkış: $?"
head -40 /tmp/tedy-fen-harita-agac.txt
```

Expected: çıkış 0 (ya da 1 ve stderr'de denetim satırları); ilk satır "Fen Bilimleri 7 (1. Kitap): 3 ünite, 8 çerçeve, 15 konu, … başlık" (plan yazılırken ölçüldü: 95 başlık); "eşleşmeyen çıktı: yok".

- [ ] **Step 2: Kitapla tek tek karşılaştır (spec §2.2 onayı)**

Her konu için ağaçtaki başlıkları kitabın o sayfalarıyla karşılaştır:

```bash
PDF=/tmp/meb-kitap-yoklama/fen7-1.pdf
for aralik in "15 33" "34 49" "59 70" "71 79" "89 100" "101 116" "117 128" "129 139"; do
  set -- $aralik
  echo "=== s. $1–$2"
  pdftohtml -xml -i -q -f $(($1 + 1)) -l $(($2 + 1)) -stdout "$PDF" | grep -E 'font="[0-9]+"' | \
    /mnt/thunderbolt/workspaces/TED/.venv/bin/python -I -c '
import re, sys
x = sys.stdin.read()
for m in re.finditer(r"<text top=\"(\d+)\" left=\"(\d+)\"[^>]*>(.*?)</text>", x):
    t = re.sub("<[^>]+>", "", m.group(3)).strip()
    if "<b>" in m.group(3) and len(t) > 3: print(m.group(1), m.group(2), t)'
done > /tmp/tedy-fen-kalin-satirlar.txt
wc -l /tmp/tedy-fen-kalin-satirlar.txt
```

Bu dökümü ağaçla (`/tmp/tedy-fen-harita-agac.txt`) yan yana oku. Kurallar:
- Ağaçta olup kitapta başlık olmayan satır (şekil yazısı, kavram haritası kutusu, kişi adı) → `KITAPLAR["fen-bilimleri"]["kitaplar"][0]["duzen"]["atla"]`'ya birebir yazımıyla eklenir.
- Kitapta başlık olup ağaçta olmayan blok → `duzen` eşikleri (`baslik_sol_en_cok`, `govde_sol`) ölçülerek düzeltilir; tahminle değil, dökümdeki `left` değerleriyle.
- Denetim "konunun başlığı yok: X" diyorsa o konunun sayfaları dökümde açılır; gerçekten başlıksızsa ad `basliksiz_konular`'a yazılır.
- Her değişiklikten sonra Step 1 yeniden koşulur; ağaç kitapla örtüşene kadar.

- [ ] **Step 3: Haritayı yaz ve onayı kaydet**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-hazirligi
env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -I scripts/meb_kitap_haritasi.py fen-bilimleri \
  --pdf 1=/tmp/meb-kitap-yoklama/fen7-1.pdf \
  --denetim-kim "Claude (asistan) — İçindekiler ve bölüm içi başlıklar Fen 7-1 PDF'iyle sayfa sayfa karşılaştırıldı"
echo "çıkış: $?"
/mnt/thunderbolt/workspaces/TED/.venv/bin/python -I -c "import json; h=json.load(open('src/kitap_haritalari/fen-bilimleri.json')); print(h['denetim'], h['kitaplar'][0]['toplam_sayfa'], len(h['eslesme']), h['eslesmedi'])"
```

Expected: çıkış 0; `{'kim': 'Claude (asistan) — …', 'tarih': '2026-10-2x'} 153 14 []`.

- [ ] **Step 4: Değişmez testini yaz**

`tests/test_kitap_haritasi_fen.py`:

```python
"""Fen 7-1 kitap haritasının değişmezleri (spec §2.2, Kanun K1): gerçek dosya, betiğin kendi denetimi ve ölçülmüş
bölümler. Harita yeniden üretilirse bu test neyin değiştiğini söyler."""
import json
import re
from pathlib import Path

from scripts.meb_kitap_haritasi import KITAPLAR, yapi_denetimi
from src.sinav_senaryo import tablo_oku

KOK = Path(__file__).resolve().parents[1]
HARITA = json.loads((KOK / "src" / "kitap_haritalari" / "fen-bilimleri.json").read_text(encoding="utf-8"))
TABLO = tablo_oku()
CIKTILAR = TABLO["dersler"]["Fen Bilimleri"]["ciktilar"]
KITAP = HARITA["kitaplar"][0]


def _konu(ad):
    return next(k for u in KITAP["uniteler"] for c in u["cerceveler"] for k in c["konular"] if k["ad"] == ad)


def test_betigin_kendi_denetimi_gecer_ve_her_cikti_bagli():
    ayar = KITAPLAR["fen-bilimleri"]
    assert yapi_denetimi(HARITA, CIKTILAR, ayar["beklenen_eslesmeyen"], ayar["basliksiz_konular"]) == []
    assert set(HARITA["eslesme"]) == {c["kod"] for c in CIKTILAR}
    assert HARITA["eslesmedi"] == []


def test_olculen_bolumler():
    assert HARITA["eslesme"]["FB.7.2.1"] == [{"kitap": 0, "unite": 2, "cerceve": 1, "konu": "Fiziksel Anlamda İş"}]
    assert {e["konu"] for e in HARITA["eslesme"]["FB.7.1.1"]} == {
        "Uzay Teknolojileri", "Teknoloji ile Uzay Araştırmaları Arasındaki İlişki"}
    assert (_konu("Fiziksel Anlamda İş")["sayfa"], _konu("Fiziksel Anlamda İş")["son_sayfa"]) == (60, 63)
    assert (_konu("Enerji ve Enerji Çeşitleri")["sayfa"], _konu("Enerji ve Enerji Çeşitleri")["son_sayfa"]) == (64, 70)


def test_fiziksel_anlamda_is_basliklari_kitaptaki_gibi():
    b = _konu("Fiziksel Anlamda İş")["basliklar"]
    assert [(x["tur"], x["ad"], x["sayfa"]) for x in b] == [
        ("etkinlik", "Etkinlik Noktası-1", 60), ("etkinlik", "Etkinlik Noktası-2", 60),
        ("baglanti", "Bağlantı Noktası", 62), ("kontrol", "Kontrol Noktası", 63)]
    assert b[0]["amac"] == "Fiziksel anlamda yapılan işin niteliklerini tanımlama"
    assert b[1]["amac"] == "Fiziksel anlamda iş yapma durumuna göre günlük yaşam örneklerini değerlendirme"


def test_tanimlar_var_gurultu_yok():
    enerji = [(x["tur"], x["ad"], x["sayfa"]) for x in _konu("Enerji ve Enerji Çeşitleri")["basliklar"]]
    assert ("tanim", "Potansiyel Enerji", 68) in enerji
    tum = [x["ad"] for u in KITAP["uniteler"] for c in u["cerceveler"]
           for x in c["basliklar"] + [y for k in c["konular"] for y in k["basliklar"]]]
    assert not set(tum) & {"KUZEY", "DOĞU", "GÜNEY", "4,24 ışık yılı", "Bulutsu", "Haber", "Bilgi Bankası"}


def test_onay_damgalar_ve_kaynak():
    assert HARITA["denetim"]["kim"] and re.fullmatch(r"\d{4}-\d{2}-\d{2}", HARITA["denetim"]["tarih"])
    assert re.fullmatch(r"[0-9a-f]{64}", KITAP["sha256"])
    assert (KITAP["toplam_sayfa"], KITAP["sayfa_kaymasi"], KITAP["baski"]) == (153, 1, "2026-2027")
    assert KITAP["pdf_url"] == "https://cdn.eba.gov.tr/temel-egitim/yayin/2026-2027/ktp/fenbilimleri7-1_v3.pdf"
    assert HARITA["senaryo_tablosu"]["ders_sha256"] == TABLO["dersler"]["Fen Bilimleri"]["sha256"]
```

- [ ] **Step 5: Testi koş**

Run: `env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_kitap_haritasi_fen.py tests/test_meb_kitap_haritasi.py`
Expected: PASS. `test_tanimlar_var_gurultu_yok` düşerse Step 2'ye dön (gürültü `atla`'ya, tahmin değil döküm).

- [ ] **Step 6: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-hazirligi
git log --oneline -3 && git status --short
git add src/kitap_haritalari/fen-bilimleri.json tests/test_kitap_haritasi_fen.py scripts/meb_kitap_haritasi.py
git commit -m "$(cat <<'EOF'
feat(sinav-hazirligi): Fen 7 (1. Kitap) haritası — üretildi, kitapla sayfa sayfa onaylandı

14 Fen çıktısının hepsi bir kitap bölümüne bağlı; bölüm içi başlıklar, amaçlar ve tanımlar betiğin denetiminden
geçti; değişmez testi ölçülmüş bölümleri sabitler.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Kılavuz modeli I — ders anahtarları, sınav durumu (K8), genel bakış, ders özeti, güncellik (K12)

**Files:**
- Modify: `src/sinav_senaryo.py` (`DERS_ANAHTARLARI`)
- Create: `src/sinav_kilavuzu.py` (çekirdek)
- Create: `tests/hazirlik_fikstur.py`
- Test: `tests/test_sinav_kilavuzu.py`

**Interfaces:**
- Consumes: `src.sinav_senaryo.tablo_oku`, `donem_no`, `ogretim_yili_adi`, `konu_eslestir`; Görev 5'in harita biçimi.
- Produces:
  - `sinav_senaryo.DERS_ANAHTARLARI: dict[str, str]` (ders adı → anahtar; sıra yüzey sırasıdır: turkce, matematik, fen-bilimleri, sosyal-bilgiler, ingilizce, din-kulturu)
  - `sinav_kilavuzu`: `SURUM = 1`, `HARITA_DIZINI`, `ANAHTAR_DERSLERI`, `KESIN_DURUMLAR`, `class KilavuzHatasi(kod)`, `@dataclass Girdiler(tablo, haritalar, sinavlar, bugun, kitap_denetimi={}, haftalar={}, odevler=[], moduller=[], isaretler={})`, `harita_oku(anahtar, dizin=None) -> dict | None`, `tablo_durumu(tablo, bugun) -> None | "tablo_yok" | "tablo_eski"`, `sinav_durumu(g, ders, no) -> SinavDurumu`, `genel_bakis(g) -> GenelBakis`, `ders_ozeti(g, anahtar, no) -> DersOzeti`
  - JSON biçimleri (Görev 9'un `tipler.ts`'i birebir yansıtır):
    - `SinavDurumu = {tur: "kesin"|"olasi"|"ulke_geneli"|"gecti", senaryo: int|None, senaryo_sayisi: int, tarih: "YYYY-MM-DD"|None, kalan_gun: int|None, sinav_id: str|None, duyuru: str|None, uyari: None|"kismen"|"senaryo_yok", anilan: [int], duyurulan_konu: int}`
    - `GenelBakis = {durum: "hazir"|"tablo_yok"|"tablo_eski", kaynak: {baslik, sayfa, meb_guncelleme, ogretim_yili, donem, sinif}|None, yaklasan: [{ders, anahtar, sinav_no, durum, soru}], dersler: [{ders, anahtar, kitap_bolumleri: bool, sinavlar: [{sinav_no, durum, soru}]}]}`
    - `KitapYolu = {kitap, unite: "2. Ünite", unite_no, unite_ad, cerceve: "1. Kuvvet, İş ve Enerji İlişkisi", cerceve_no, konu: str|None, sayfa, son_sayfa, baglanti: "<pdf_url>#page=<pdf sayfası>"}`
    - `MatrisSatiri = {kod, kisa_ad, metin, sayilar: {"1": int, …}, her_senaryoda: bool, kitapta: [KitapYolu], kitap_durumu: "var"|"bulunamadi"|"harita_yok"}`
    - `DersOzeti = {ders, anahtar, sinav_no, tur: "senaryolu"|"ulke_geneli", not: str|None, sinavlar: [{sinav_no, durum}], durum, senaryolar: [int], duyurulan: int|None, gruplar: [{baslik, satirlar: [MatrisSatiri]}], toplamlar: {"1": int, …}, kitap_bolumleri: bool, harita_onayli: bool, guncellik: {tablo_degisti: bool, kitap_degisti: bool}}`

- [ ] **Step 1: Ortak test fikstürünü yaz**

`tests/hazirlik_fikstur.py` (harita gerçek dosyadan bağımsızdır; değerler Fen 7-1'den ölçülmüş olanlardır):

```python
"""Sınav hazırlığı testlerinin ortak fikstürleri (plan Görev 6–8): gerçek senaryo tablosu, Fen 7-1'den ölçülmüş
değerlerle kurulmuş küçük bir harita (gerçek dosyadan bağımsız) ve /api/exams biçiminde sınav kayıtları."""
from __future__ import annotations

from datetime import date

from src import sinav_kilavuzu as sk
from src.sinav_senaryo import tablo_oku

TABLO = tablo_oku()
BUGUN = date(2026, 10, 25)
PDF = "https://cdn.eba.gov.tr/temel-egitim/yayin/2026-2027/ktp/fenbilimleri7-1_v3.pdf"
DUYURU = "Sınav, İstanbul İl MEB tarafından belirlenen 2. senaryoya göre uygulanacaktır."
FEN_KONULARI = ("Uzay teknolojileri", "Uzay araştırmalarının sorunları", "Fiziksel anlamda iş")


def _b(tur, ad, sayfa, amac=None):
    return {"ad": ad, "tur": tur, "amac": amac, "sayfa": sayfa}


def _k(ad, sayfa, son, *basliklar):
    return {"ad": ad, "sayfa": sayfa, "son_sayfa": son, "basliklar": list(basliklar)}


def _c(no, ad, sayfa, son, ciktilar, konular, basliklar=()):
    return {"no": no, "ad": ad, "sayfa": sayfa, "son_sayfa": son, "ciktilar": list(ciktilar),
            "basliklar": list(basliklar), "konular": list(konular)}


def fen_haritasi() -> dict:
    uniteler = [
        {"no": 1, "ad": "Uzay Çağı", "sayfa": 14, "son_sayfa": 57, "cerceveler": [
            _c(1, "Türkiye ve Uzay Araştırmaları", 15, 33, ["FB.7.1.1", "FB.7.1.2", "FB.7.1.3"], [
                _k("Uzay Teknolojileri", 16, 24, _b("etkinlik", "Keşif Noktası: Uzay Teknolojileri", 17),
                   _b("kontrol", "Kontrol Noktası", 19), _b("diger", "Teleskop Çeşitleri", 22),
                   _b("kontrol", "Kontrol Noktası", 24)),
                _k("Teknoloji ile Uzay Araştırmaları Arasındaki İlişki", 24, 33, _b("baglanti", "Bağlantı Noktası", 25),
                   _b("tanim", "Astronot", 26),
                   _b("etkinlik", "Performans Görevi: Uzay Gözlem Araçları Modeli", 29,
                      "Uzay gözlem araçları ile ilgili bilimsel model oluşturma"),
                   _b("ozet", "Neler Öğrendik?", 33))],
               [_b("baglanti", "Bağlantı Noktası", 15)]),
            _c(2, "Uzayda Neler Var?", 34, 49, ["FB.7.1.4", "FB.7.1.5"], [
                _k("Yıldız Oluşumu", 35, 49,
                   _b("etkinlik", "Etkinlik Noktası-1", 36,
                      "Yıldızların yaşam sürecine ilişkin kavramlar arasındaki ilişkileri açıklama"),
                   _b("diger", "Galaksiler", 48), _b("ozet", "Neler Öğrendik?", 49))],
               [_b("baglanti", "Bağlantı Noktası", 34)])]},
        {"no": 2, "ad": "Kuvvet ve Enerjiyi Keşfedelim", "sayfa": 58, "son_sayfa": 87, "cerceveler": [
            _c(1, "Kuvvet, İş ve Enerji İlişkisi", 59, 70, ["FB.7.2.1", "FB.7.2.2"], [
                _k("Fiziksel Anlamda İş", 60, 63,
                   _b("etkinlik", "Etkinlik Noktası-1", 60, "Fiziksel anlamda yapılan işin niteliklerini tanımlama"),
                   _b("etkinlik", "Etkinlik Noktası-2", 60,
                      "Fiziksel anlamda iş yapma durumuna göre günlük yaşam örneklerini değerlendirme"),
                   _b("baglanti", "Bağlantı Noktası", 62), _b("kontrol", "Kontrol Noktası", 63)),
                _k("Enerji ve Enerji Çeşitleri", 64, 70,
                   _b("etkinlik", "Etkinlik Noktası-3", 65, "Kinetik ve potansiyel enerjiyi karşılaştırma"),
                   _b("tanim", "Potansiyel Enerji", 68), _b("ozet", "Neler Öğrendik?", 70))],
               [_b("baglanti", "Bağlantı Noktası", 59)]),
            _c(2, "Enerji Dönüşümleri", 71, 79, ["FB.7.2.3"], [
                _k("Enerjinin Korunumu", 72, 79, _b("ozet", "Neler Öğrendik?", 78))])]},
        {"no": 3, "ad": "Vücudumuzdaki Sistemler", "sayfa": 88, "son_sayfa": 148, "cerceveler": [
            _c(1, "Sindirim Sistemi", 89, 100, ["FB.7.3.1", "FB.7.3.2"], [
                _k("Sindirim Sistemini Oluşturan Yapı ve Organlar", 90, 95, _b("kontrol", "Kontrol Noktası", 93)),
                _k("Sindirim Sisteminin Sağlığı", 96, 100, _b("ozet", "Neler Öğrendik?", 100))]),
            _c(2, "Dolaşım Sistemi", 101, 116, ["FB.7.3.3", "FB.7.3.4", "FB.7.3.5"], [
                _k("Dolaşım Sistemini Oluşturan Yapı ve Organlar", 102, 109, _b("diger", "Kanın Yapısı ve Görevleri", 107)),
                _k("Kan Bağışının Toplum Açısından Önemi", 109, 112, _b("baglanti", "Bağlantı Noktası", 112)),
                _k("Dolaşım Sisteminin Sağlığı", 113, 116, _b("ozet", "Neler Öğrendik?", 116))]),
            _c(3, "Solunum Sistemi", 117, 128, ["FB.7.3.6"], [
                _k("Solunum Sistemini Oluşturan Yapı ve Organlar", 118, 122, _b("baglanti", "Bağlantı Noktası", 122)),
                _k("Solunum Sisteminin Sağlığı", 123, 128, _b("ozet", "Neler Öğrendik?", 128))])]},
    ]

    def e(u, c, konu):
        return {"kitap": 0, "unite": u, "cerceve": c, "konu": konu}
    teknoloji = "Teknoloji ile Uzay Araştırmaları Arasındaki İlişki"
    eslesme = {
        "FB.7.1.1": [e(1, 1, "Uzay Teknolojileri"), e(1, 1, teknoloji)],
        "FB.7.1.2": [e(1, 1, "Uzay Teknolojileri"), e(1, 1, teknoloji)],
        "FB.7.1.3": [e(1, 1, teknoloji)],
        "FB.7.1.4": [e(1, 2, "Yıldız Oluşumu")], "FB.7.1.5": [e(1, 2, "Yıldız Oluşumu")],
        "FB.7.2.1": [e(2, 1, "Fiziksel Anlamda İş")], "FB.7.2.2": [e(2, 1, "Enerji ve Enerji Çeşitleri")],
        "FB.7.2.3": [e(2, 2, "Enerjinin Korunumu")],
        "FB.7.3.1": [e(3, 1, "Sindirim Sistemini Oluşturan Yapı ve Organlar")],
        "FB.7.3.2": [e(3, 1, "Sindirim Sisteminin Sağlığı")],
        "FB.7.3.3": [e(3, 2, "Dolaşım Sistemini Oluşturan Yapı ve Organlar")],
        "FB.7.3.4": [e(3, 2, "Kan Bağışının Toplum Açısından Önemi")],
        "FB.7.3.5": [e(3, 2, "Dolaşım Sisteminin Sağlığı")],
        "FB.7.3.6": [e(3, 3, "Solunum Sistemini Oluşturan Yapı ve Organlar")]}
    return {"surum": 1, "ders": "Fen Bilimleri", "anahtar": "fen-bilimleri", "uretildi": "2026-10-25",
            "senaryo_tablosu": {"meb_guncelleme": "2026-09-10T17:27",
                                "ders_sha256": TABLO["dersler"]["Fen Bilimleri"]["sha256"]},
            "kitaplar": [{"baslik": "Fen Bilimleri 7 (1. Kitap)", "pdf_url": PDF, "kaynak_sayfa": None, "sha256": "a" * 64,
                          "baski": "2026-2027", "sayfa_kaymasi": 1, "toplam_sayfa": 153, "uniteler": uniteler}],
            "eslesme": eslesme, "eslesmedi": [], "denetim": {"kim": "test", "tarih": "2026-10-25"}}


def sinav_kaydi(ders="Fen Bilimleri", no=1, *, durum="dogrulandi", senaryo=2, tarih="2026-11-03", status="upcoming",
                konular=(), anilan=None, sid="fen11", eslesmeyen=(), senaryo_disi=(),
                duyuruda=("FB.7.1.1", "FB.7.1.3", "FB.7.2.1")) -> dict:
    """/api/exams kaydının hazırlık modelinin okuduğu alanları; senaryo bloğu sinav_senaryo.senaryo_blogu biçiminde."""
    dt = TABLO["dersler"][ders]
    sinav = dt["sinavlar"][str(no)]
    kesin = durum in sk.KESIN_DURUMLAR
    dagilim = []
    if kesin and senaryo:
        d = sinav["senaryolar"][str(senaryo)]
        dagilim = [{"kod": c["kod"], "metin": c["metin"], "soru": d[c["kod"]], "duyuruda": c["kod"] in duyuruda}
                   for c in dt["ciktilar"] if c["kod"] in d]
    blok = {"durum": durum, "ders": ders, "sinav_no": no, "donem": 1,
            "anilan": list(anilan if anilan is not None else ([senaryo] if senaryo else [])),
            "cumle": DUYURU if senaryo else None, "senaryo": senaryo if kesin else None,
            "toplam": sum(x["soru"] for x in dagilim) if dagilim else None, "dagilim": dagilim,
            "eslesen_konu_sayisi": len(konular) - len(eslesmeyen), "eslesmeyen_konular": list(eslesmeyen),
            "senaryo_disi_konular": list(senaryo_disi), "adaylar": [], "senaryo_sayisi": len(sinav.get("senaryolar", {})),
            "kaynak": TABLO["kaynak"]["sayfa"], "meb_guncelleme": TABLO["kaynak"]["meb_guncelleme"]}
    return {"id": sid, "course": ders, "title": f"{ders} {no}. Yazılı", "date": tarih, "status": status,
            "konular": list(konular), "senaryo": blok}


def girdiler(**degisiklik) -> sk.Girdiler:
    taban = {"tablo": TABLO, "haritalar": {"fen-bilimleri": fen_haritasi()},
             "sinavlar": [sinav_kaydi(konular=FEN_KONULARI)], "bugun": BUGUN}
    taban.update(degisiklik)
    return sk.Girdiler(**taban)
```

- [ ] **Step 2: Başarısız testleri yaz**

`tests/test_sinav_kilavuzu.py`:

```python
"""Kılavuz modeli (plan Görev 6–7): ders anahtarları, sınav durumu (K8), genel bakış, ders özeti, güncellik (K12)."""
from datetime import date

import pytest

from src import sinav_kilavuzu as sk
from tests.hazirlik_fikstur import BUGUN, TABLO, fen_haritasi, girdiler, sinav_kaydi

TR_GECTI = dict(senaryo=4, tarih="2026-10-22", status="past", sid="tr11")
TR_ULKE = dict(durum="ulke_geneli", senaryo=None, tarih="2027-01-05", sid="tr12")


def test_ders_anahtarlari_alti_ders_ve_tablo_ile_ayni():
    assert list(sk.ANAHTAR_DERSLERI) == ["turkce", "matematik", "fen-bilimleri", "sosyal-bilgiler", "ingilizce",
                                         "din-kulturu"]
    assert set(sk.ANAHTAR_DERSLERI.values()) == set(TABLO["dersler"])


def test_tablo_durumu_yil_ve_donem():
    assert sk.tablo_durumu(TABLO, BUGUN) is None
    assert sk.tablo_durumu(TABLO, date(2027, 1, 20)) is None      # Ocak hâlâ 1. dönem
    assert sk.tablo_durumu(TABLO, date(2027, 2, 10)) == "tablo_eski"
    assert sk.tablo_durumu(TABLO, date(2027, 10, 1)) == "tablo_eski"
    assert sk.tablo_durumu(None, BUGUN) == "tablo_yok"


def test_harita_oku_bozuk_ya_da_eski_surum_none(tmp_path):
    (tmp_path / "fen-bilimleri.json").write_text("{", encoding="utf-8")
    assert sk.harita_oku("fen-bilimleri", tmp_path) is None
    (tmp_path / "fen-bilimleri.json").write_text('{"surum": 2, "kitaplar": [], "eslesme": {}}', encoding="utf-8")
    assert sk.harita_oku("fen-bilimleri", tmp_path) is None
    assert sk.harita_oku("matematik", tmp_path) is None


def test_sinav_durumu_kesin_tarih_ve_geri_sayim():
    d = sk.sinav_durumu(girdiler(), "Fen Bilimleri", 1)
    assert (d["tur"], d["senaryo"], d["senaryo_sayisi"], d["tarih"], d["kalan_gun"]) == ("kesin", 2, 4, "2026-11-03", 9)
    assert d["duyuru"].startswith("Sınav, İstanbul İl MEB") and d["sinav_id"] == "fen11"
    assert (d["duyurulan_konu"], d["uyari"]) == (3, None)


def test_sinav_durumu_kismen_uyari_tasir():
    g = girdiler(sinavlar=[sinav_kaydi(durum="kismen", konular=("a", "b"), senaryo_disi=("b",))])
    d = sk.sinav_durumu(g, "Fen Bilimleri", 1)
    assert (d["tur"], d["senaryo"], d["uyari"]) == ("kesin", 2, "kismen")


@pytest.mark.parametrize("kayitlar", [[], [sinav_kaydi(durum="belirtilmedi", senaryo=None)]])
def test_sinav_durumu_olasi_tek_senaryo_tasimaz(kayitlar):
    d = sk.sinav_durumu(girdiler(sinavlar=kayitlar), "Fen Bilimleri", 1)
    assert (d["tur"], d["senaryo"], d["senaryo_sayisi"]) == ("olasi", None, 4)


def test_sinav_durumu_senaryo_yok_uyarisi():
    g = girdiler(sinavlar=[sinav_kaydi(durum="senaryo_yok", senaryo=None, anilan=[9])])
    d = sk.sinav_durumu(g, "Fen Bilimleri", 1)
    assert (d["tur"], d["senaryo"], d["uyari"], d["anilan"]) == ("olasi", None, "senaryo_yok", [9])


def test_sinav_durumu_gecti_ve_ulke_geneli():
    g = girdiler(sinavlar=[sinav_kaydi("Türkçe", 1, **TR_GECTI), sinav_kaydi("Türkçe", 2, **TR_ULKE)])
    gecti = sk.sinav_durumu(g, "Türkçe", 1)
    assert (gecti["tur"], gecti["senaryo"], gecti["kalan_gun"]) == ("gecti", 4, None)
    ulke = sk.sinav_durumu(g, "Türkçe", 2)
    assert (ulke["tur"], ulke["senaryo_sayisi"], ulke["kalan_gun"]) == ("ulke_geneli", 0, 72)


def test_genel_bakis_once_zaman_sonra_alti_ders():
    g = girdiler(sinavlar=[sinav_kaydi(konular=("a", "b", "c")), sinav_kaydi("Türkçe", 1, **TR_GECTI),
                           sinav_kaydi("Türkçe", 2, **TR_ULKE)])
    gb = sk.genel_bakis(g)
    assert gb["durum"] == "hazir" and gb["kaynak"]["meb_guncelleme"] == "2026-09-10T17:27"
    assert [(y["anahtar"], y["sinav_no"], y["durum"]["tur"], y["soru"]) for y in gb["yaklasan"]] == [
        ("fen-bilimleri", 1, "kesin", 7), ("turkce", 2, "ulke_geneli", None)]
    assert [d["anahtar"] for d in gb["dersler"]] == list(sk.ANAHTAR_DERSLERI)
    fen = next(d for d in gb["dersler"] if d["anahtar"] == "fen-bilimleri")
    assert fen["kitap_bolumleri"] is True
    assert [(s["sinav_no"], s["durum"]["tur"], s["soru"]) for s in fen["sinavlar"]] == [(1, "kesin", 7), (2, "olasi", None)]
    tr = next(d for d in gb["dersler"] if d["anahtar"] == "turkce")
    assert [(s["durum"]["tur"], s["soru"]) for s in tr["sinavlar"]] == [("gecti", 7), ("ulke_geneli", None)]
    mat = next(d for d in gb["dersler"] if d["anahtar"] == "matematik")
    assert mat["kitap_bolumleri"] is False and mat["sinavlar"][0]["durum"]["tarih"] is None


def test_genel_bakis_tablo_eski_ders_listelemez():
    gb = sk.genel_bakis(girdiler(bugun=date(2027, 2, 10)))
    assert (gb["durum"], gb["yaklasan"], gb["dersler"]) == ("tablo_eski", [], [])
    assert sk.genel_bakis(girdiler(tablo=None))["durum"] == "tablo_yok"


def test_ders_ozeti_matris_fen_1():
    oz = sk.ders_ozeti(girdiler(), "fen-bilimleri", 1)
    assert (oz["ders"], oz["tur"], oz["senaryolar"], oz["duyurulan"]) == ("Fen Bilimleri", "senaryolu", [1, 2, 3, 4], 2)
    assert oz["toplamlar"] == {"1": 9, "2": 7, "3": 8, "4": 6}
    assert [g["baslik"] for g in oz["gruplar"]] == ["1. Ünite · Uzay Çağı", "2. Ünite · Kuvvet ve Enerjiyi Keşfedelim"]
    satirlar = {s["kod"]: s for g in oz["gruplar"] for s in g["satirlar"]}
    # FB.7.1.2 1. yazılının hiçbir senaryosunda yok: satır olmaz.
    assert list(satirlar) == ["FB.7.1.1", "FB.7.1.3", "FB.7.1.4", "FB.7.1.5", "FB.7.2.1", "FB.7.2.2"]
    is_ = satirlar["FB.7.2.1"]
    assert (is_["kisa_ad"], is_["sayilar"], is_["her_senaryoda"], is_["kitap_durumu"]) == (
        "Fiziksel Anlamda İş", {"1": 3, "2": 3, "3": 2, "4": 2}, True, "var")
    assert is_["kitapta"] == [{
        "kitap": "Fen Bilimleri 7 (1. Kitap)", "unite": "2. Ünite", "unite_no": 2,
        "unite_ad": "Kuvvet ve Enerjiyi Keşfedelim", "cerceve": "1. Kuvvet, İş ve Enerji İlişkisi", "cerceve_no": 1,
        "konu": "Fiziksel Anlamda İş", "sayfa": 60, "son_sayfa": 63,
        "baglanti": "https://cdn.eba.gov.tr/temel-egitim/yayin/2026-2027/ktp/fenbilimleri7-1_v3.pdf#page=61"}]
    assert satirlar["FB.7.1.1"]["kisa_ad"] == "Uzay araştırmaları için geliştirilen teknolojileri karşılaştırabilme"
    assert satirlar["FB.7.1.1"]["her_senaryoda"] is False
    assert [s["sinav_no"] for s in oz["sinavlar"]] == [1, 2]
    assert (oz["kitap_bolumleri"], oz["harita_onayli"]) == (True, True)
    assert oz["guncellik"] == {"tablo_degisti": False, "kitap_degisti": False}


def test_ders_ozeti_haritasiz_ders_kitap_bolumu_yok():
    oz = sk.ders_ozeti(girdiler(), "matematik", 1)
    assert oz["kitap_bolumleri"] is False and oz["gruplar"][0]["baslik"] == "1. Ünite"
    assert all(s["kitap_durumu"] == "harita_yok" and s["kitapta"] == [] for g in oz["gruplar"] for s in g["satirlar"])


def test_ders_ozeti_turkce_alan_grubu_ve_ulke_geneli():
    oz = sk.ders_ozeti(girdiler(), "turkce", 1)
    assert [g["baslik"] for g in oz["gruplar"]] == ["Okuma", "Yazma"]
    ulke = sk.ders_ozeti(girdiler(), "turkce", 2)
    assert (ulke["tur"], ulke["senaryolar"], ulke["gruplar"], ulke["toplamlar"]) == ("ulke_geneli", [], [], {})
    assert ulke["not"].startswith("1. Dönem 2. Ortak Yazılı")


def test_ders_ozeti_kitapta_karsiligi_bulunamadi():
    """Review Focus: haritada eşleşmeyen çıktı 'bulunamadi' — 'yok' değil; kodundaki ünite numarasıyla aynı ünite
    grubunda kalır."""
    h = fen_haritasi()
    h["eslesme"].pop("FB.7.1.3")
    h["eslesmedi"] = ["FB.7.1.3"]
    oz = sk.ders_ozeti(girdiler(haritalar={"fen-bilimleri": h}), "fen-bilimleri", 1)
    s = next(s for g in oz["gruplar"] for s in g["satirlar"] if s["kod"] == "FB.7.1.3")
    assert (s["kitap_durumu"], s["kitapta"]) == ("bulunamadi", [])
    uzay = next(g for g in oz["gruplar"] if g["baslik"] == "1. Ünite · Uzay Çağı")
    assert "FB.7.1.3" in [s["kod"] for s in uzay["satirlar"]]


def test_guncellik_tablo_ve_kitap_degisti():
    """Review Focus (K12): harita eski tabloya göre kurulmuşsa ya da kitap PDF'i değiştiyse güncel değil."""
    h = fen_haritasi()
    h["senaryo_tablosu"]["ders_sha256"] = "0" * 64
    oz = sk.ders_ozeti(girdiler(haritalar={"fen-bilimleri": h}), "fen-bilimleri", 1)
    assert oz["guncellik"] == {"tablo_degisti": True, "kitap_degisti": False}

    def denetim(sha):
        return {"fen-bilimleri": {"denetlendi": "2026-10-26", "kitaplar": [{"pdf_url": h["kitaplar"][0]["pdf_url"],
                                                                             "sha256": sha}]}}
    oz = sk.ders_ozeti(girdiler(kitap_denetimi=denetim("b" * 64)), "fen-bilimleri", 1)
    assert oz["guncellik"] == {"tablo_degisti": False, "kitap_degisti": True}
    assert sk.ders_ozeti(girdiler(kitap_denetimi=denetim("a" * 64)), "fen-bilimleri", 1)["guncellik"]["kitap_degisti"] is False


def test_onaysiz_harita():
    h = fen_haritasi()
    h["denetim"] = {"kim": None, "tarih": None}
    assert sk.ders_ozeti(girdiler(haritalar={"fen-bilimleri": h}), "fen-bilimleri", 1)["harita_onayli"] is False


@pytest.mark.parametrize("anahtar,no,kod", [("fizik", 1, "bilinmeyen_ders"), ("fen-bilimleri", 3, "bilinmeyen_sinav")])
def test_ders_ozeti_bilinmeyen(anahtar, no, kod):
    with pytest.raises(sk.KilavuzHatasi) as h:
        sk.ders_ozeti(girdiler(), anahtar, no)
    assert h.value.kod == kod


@pytest.mark.parametrize("degisiklik,kod", [({"bugun": date(2027, 2, 10)}, "tablo_eski"), ({"tablo": None}, "tablo_yok")])
def test_ders_ozeti_tablo_eski_ve_yok(degisiklik, kod):
    with pytest.raises(sk.KilavuzHatasi) as h:
        sk.ders_ozeti(girdiler(**degisiklik), "fen-bilimleri", 1)
    assert h.value.kod == kod
```

- [ ] **Step 3: Testi koş, düştüğünü gör**

Run: `env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_sinav_kilavuzu.py`
Expected: FAIL — `ImportError: cannot import name 'sinav_kilavuzu'` (ya da `DERS_ANAHTARLARI`).

- [ ] **Step 4: `DERS_ANAHTARLARI`'nı ekle**

`src/sinav_senaryo.py`'de `GOVDE_SINIRI = 3900` satırının altına:

```python
# Sınav Hazırlığı yüzeylerinin ders anahtarı: pano adresi (/hazirlik/<anahtar>) ve kitap haritası dosya adı
# (src/kitap_haritalari/<anahtar>.json). Sıra yüzeylerdeki ders sırasıdır (spec 2026-10-25 §2.2, §3.1).
DERS_ANAHTARLARI = {"Türkçe": "turkce", "Matematik": "matematik", "Fen Bilimleri": "fen-bilimleri",
                    "Sosyal Bilgiler": "sosyal-bilgiler", "İngilizce": "ingilizce", "Din Kültürü": "din-kulturu"}
```

- [ ] **Step 5: Model çekirdeğini yaz**

`src/sinav_kilavuzu.py`:

```python
"""Sınav Hazırlığı kılavuz modeli (spec 2026-10-25 §2.4, §3, §4, §7; plan Görev 6–7).

Saf işlevler: girdiler `Girdiler` ile gelir (API toplar), ağ ve yazım yok — yalnız `harita_oku` dosya okur.
Senaryo tablosu `sinav_senaryo.tablo_oku()`, kitap haritaları `src/kitap_haritalari/<anahtar>.json`
(scripts/meb_kitap_haritasi.py üretir). Kanun K8: senaryo duyurulmadıysa hiçbir alan tek senaryoyu "bu" diye
taşımaz. Kanun K1: kitap başlıkları yalnız haritadan; haritada karşılığı olmayan çıktı "bulunamadi" (yok değil)."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from src.course_names import normalize_course
from src.sinav_senaryo import DERS_ANAHTARLARI, donem_no, konu_eslestir, ogretim_yili_adi
from src.sinav_tarihi import katla

SURUM = 1
HARITA_DIZINI = Path(__file__).with_name("kitap_haritalari")
ANAHTAR_DERSLERI = {anahtar: ders for ders, anahtar in DERS_ANAHTARLARI.items()}
KESIN_DURUMLAR = ("dogrulandi", "kismen")
KISA_AD_SOZCUK = 6
_UNITE_KODU = re.compile(r"^(?:[A-ZÇĞİÖŞÜ]+\.)+7\.(\d+)\.|^E7\.(\d+)\.")


class KilavuzHatasi(ValueError):
    """`kod`: bilinmeyen_ders | bilinmeyen_sinav | bilinmeyen_senaryo | tablo_yok | tablo_eski (API durum koduna çevirir)."""

    def __init__(self, kod: str):
        super().__init__(kod)
        self.kod = kod


@dataclass(frozen=True)
class Girdiler:
    tablo: dict | None
    haritalar: dict[str, dict]
    sinavlar: list[dict]                    # /api/exams "exams" kayıtları (senaryo bloğu olanlar kullanılır)
    bugun: date
    kitap_denetimi: dict = field(default_factory=dict)   # output/kitap_denetimi.json
    haftalar: dict = field(default_factory=dict)         # ders_icerikleri_haftalar (temizlenmiş)
    odevler: list = field(default_factory=list)          # _combined_homework_rows
    moduller: list = field(default_factory=list)         # module_store.latest_active
    isaretler: dict = field(default_factory=dict)        # {ders anahtarı: {çıktı kodu: "hazirim"|"tekrar"}}


def harita_oku(anahtar: str, dizin: Path | None = None) -> dict | None:
    try:
        h = json.loads(((dizin or HARITA_DIZINI) / f"{anahtar}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(h, dict) or h.get("surum") != SURUM or not isinstance(h.get("kitaplar"), list) \
            or not isinstance(h.get("eslesme"), dict):
        return None
    return h


def tablo_durumu(tablo: dict | None, bugun: date) -> str | None:
    """None (kullanılabilir) | "tablo_yok" | "tablo_eski" (bugünün öğretim yılı ya da dönemi tablonunki değil)."""
    if tablo is None:
        return "tablo_yok"
    k = tablo.get("kaynak") or {}
    if ogretim_yili_adi(bugun) != k.get("ogretim_yili") or donem_no(bugun) != k.get("donem"):
        return "tablo_eski"
    return None


def _ders(anahtar: str) -> str:
    ders = ANAHTAR_DERSLERI.get(anahtar)
    if ders is None:
        raise KilavuzHatasi("bilinmeyen_ders")
    return ders


def _gun(deger: Any) -> date | None:
    try:
        return date.fromisoformat(str(deger)[:10]) if deger else None
    except ValueError:
        return None


def _sinav_kaydi(g: Girdiler, ders: str, no: int) -> dict | None:
    """O dersin o yazılısına ait sınav kaydı; birden çoksa kesin duyurulu, tarihli, yaklaşan olan."""
    adaylar = [e for e in g.sinavlar if isinstance(e, dict) and isinstance(e.get("senaryo"), dict)
               and e["senaryo"].get("ders") == ders and e["senaryo"].get("sinav_no") == no]
    if not adaylar:
        return None
    return max(adaylar, key=lambda e: (e["senaryo"].get("durum") in KESIN_DURUMLAR, bool(e.get("date")),
                                       e.get("status") == "upcoming"))


def sinav_durumu(g: Girdiler, ders: str, no: int) -> dict:
    """Kesin (duyurulan senaryo tabloda var) | olası | ülke geneli | geçti. Olası durum tek senaryo taşımaz (K8)."""
    tablo_sinavi = g.tablo["dersler"][ders]["sinavlar"][str(no)]
    senaryolar = tablo_sinavi.get("senaryolar") or {}
    kayit = _sinav_kaydi(g, ders, no)
    blok = kayit["senaryo"] if kayit else {}
    tarih = _gun(kayit.get("date")) if kayit else None
    gecti = bool(kayit) and kayit.get("status") == "past"
    d = {"tur": "olasi", "senaryo": None, "senaryo_sayisi": len(senaryolar),
         "tarih": tarih.isoformat() if tarih else None,
         "kalan_gun": (tarih - g.bugun).days if tarih and not gecti and tarih >= g.bugun else None,
         "sinav_id": kayit.get("id") if kayit else None, "duyuru": blok.get("cumle"), "uyari": None,
         "anilan": [int(n) for n in blok.get("anilan") or []],
         "duyurulan_konu": int(blok.get("eslesen_konu_sayisi") or 0)}
    if gecti:
        d.update(tur="gecti", senaryo=blok.get("senaryo"))
    elif tablo_sinavi["tur"] == "ulke_geneli":
        d["tur"] = "ulke_geneli"
    elif blok.get("durum") in KESIN_DURUMLAR and str(blok.get("senaryo")) in senaryolar:
        d.update(tur="kesin", senaryo=int(blok["senaryo"]), uyari="kismen" if blok["durum"] == "kismen" else None)
    elif blok.get("durum") == "senaryo_yok":
        d["uyari"] = "senaryo_yok"
    return d


def _soru(g: Girdiler, ders: str, no: int, durum: dict) -> int | None:
    if durum["tur"] not in ("kesin", "gecti") or durum["senaryo"] is None:
        return None
    dagilim = (g.tablo["dersler"][ders]["sinavlar"][str(no)].get("senaryolar") or {}).get(str(durum["senaryo"]))
    return sum(dagilim.values()) if dagilim else None


def genel_bakis(g: Girdiler) -> dict:
    """Ana sayfa (spec §3.1): önce tarihi belli yaklaşan yazılılar, sonra altı dersin karosu."""
    durum = tablo_durumu(g.tablo, g.bugun)
    kaynak = None
    if g.tablo is not None:
        k = g.tablo.get("kaynak") or {}
        kaynak = {a: k.get(a) for a in ("baslik", "sayfa", "meb_guncelleme", "ogretim_yili", "donem", "sinif")}
    sonuc = {"durum": durum or "hazir", "kaynak": kaynak, "yaklasan": [], "dersler": []}
    if durum:
        return sonuc
    for ders, anahtar in DERS_ANAHTARLARI.items():
        dt = g.tablo["dersler"].get(ders)
        if dt is None:
            continue
        sinavlar = []
        for no in sorted(int(n) for n in dt["sinavlar"]):
            d = sinav_durumu(g, ders, no)
            soru = _soru(g, ders, no, d)
            sinavlar.append({"sinav_no": no, "durum": d, "soru": soru})
            if d["tarih"] and d["kalan_gun"] is not None:
                sonuc["yaklasan"].append({"ders": ders, "anahtar": anahtar, "sinav_no": no, "durum": d, "soru": soru})
        sonuc["dersler"].append({"ders": ders, "anahtar": anahtar, "kitap_bolumleri": anahtar in g.haritalar,
                                 "sinavlar": sinavlar})
    sonuc["yaklasan"].sort(key=lambda y: (y["durum"]["tarih"], y["ders"]))
    return sonuc


def _kod_sirasi(kod: str) -> tuple:
    return tuple((0, int(p), "") if p.isdigit() else (1, 0, p) for p in kod.split("."))


def _eslesen_bolumler(harita: dict | None, kod: str):
    """Haritanın bu çıktı için gösterdiği bölümler: (kitap, ünite, çerçeve, konu | None)."""
    if not harita:
        return
    for e in harita.get("eslesme", {}).get(kod, []):
        try:
            kitap = harita["kitaplar"][e["kitap"]]
            unite = next(u for u in kitap["uniteler"] if u["no"] == e["unite"])
            cer = next(c for c in unite["cerceveler"] if c["no"] == e["cerceve"])
        except (IndexError, KeyError, TypeError, StopIteration):
            continue
        konu = next((k for k in cer["konular"] if k["ad"] == e.get("konu")), None) if e.get("konu") else None
        yield kitap, unite, cer, konu


def _kitap_yollari(harita: dict | None, kod: str) -> list[dict]:
    yollar = []
    for kitap, unite, cer, konu in _eslesen_bolumler(harita, kod):
        hedef = konu or cer
        pdf = hedef["sayfa"] + int(kitap.get("sayfa_kaymasi") or 0)
        yollar.append({"kitap": kitap["baslik"], "unite": f"{unite['no']}. Ünite", "unite_no": unite["no"],
                       "unite_ad": unite["ad"], "cerceve": f"{cer['no']}. {cer['ad']}", "cerceve_no": cer["no"],
                       "konu": konu["ad"] if konu else None, "sayfa": hedef["sayfa"], "son_sayfa": hedef["son_sayfa"],
                       "baglanti": f"{kitap['pdf_url']}#page={pdf}"})
    return yollar


def _kisa_ad(cikti: dict, yollar: list[dict]) -> str:
    """Tek bir kitap konusuna bağlıysa konunun kitaptaki adı (K1); değilse MEB metninin ilk altı sözcüğü."""
    if len(yollar) == 1 and yollar[0]["konu"]:
        return yollar[0]["konu"]
    sozcukler = cikti["metin"].split()
    return " ".join(sozcukler[:KISA_AD_SOZCUK]) + ("…" if len(sozcukler) > KISA_AD_SOZCUK else "")


def _cumle_duzeni(s: str) -> str:
    k = s.replace("İ", "i").replace("I", "ı").lower()
    return (k[:1].replace("i", "İ").replace("ı", "I").upper() + k[1:]) if k else k


def _grup(cikti: dict, yollar: list[dict]) -> tuple[tuple, str]:
    """Karşılaştırma tablosunun grubu: haritadan ünite; yoksa tablonun alanı (Türkçe); yoksa koddaki ünite no."""
    if yollar:
        y = yollar[0]
        return (0, y["unite_no"], ""), f"{y['unite']} · {y['unite_ad']}"
    if cikti.get("alan"):
        return (1, 0, cikti["alan"]), _cumle_duzeni(cikti["alan"])
    m = _UNITE_KODU.match(cikti["kod"])
    if m:
        n = int(m.group(1) or m.group(2))
        return (0, n, ""), f"{n}. Ünite"
    return (2, 0, ""), "Diğer"


def _hazir_mi(g: Girdiler) -> None:
    durum = tablo_durumu(g.tablo, g.bugun)
    if durum:
        raise KilavuzHatasi(durum)


def _sinav_tablosu(g: Girdiler, ders: str, no: int) -> tuple[dict, dict]:
    dt = g.tablo["dersler"][ders]
    if str(no) not in dt["sinavlar"]:
        raise KilavuzHatasi("bilinmeyen_sinav")
    return dt, dt["sinavlar"][str(no)]


def _guncellik(g: Girdiler, anahtar: str, harita: dict | None, dt: dict) -> dict:
    """K12: harita başka bir tablo sürümüne göre kurulduysa ya da `--denetle` kitabın değiştiğini yazdıysa."""
    tablo_degisti = bool(harita) and (harita.get("senaryo_tablosu") or {}).get("ders_sha256") != dt.get("sha256")
    denetim = g.kitap_denetimi.get(anahtar) if isinstance(g.kitap_denetimi, dict) else None
    guncel = {k.get("pdf_url"): k.get("sha256") for k in (denetim or {}).get("kitaplar", []) if isinstance(k, dict)}
    kitap_degisti = bool(harita) and any(k.get("pdf_url") in guncel and guncel[k["pdf_url"]] != k.get("sha256")
                                         for k in harita["kitaplar"])
    return {"tablo_degisti": tablo_degisti, "kitap_degisti": kitap_degisti}


def ders_ozeti(g: Girdiler, anahtar: str, no: int) -> dict:
    """Ders sayfası (spec §3.2): bu yazılının çıktı × senaryo matrisi, ünite gruplu, kitap yollarıyla."""
    ders = _ders(anahtar)
    _hazir_mi(g)
    dt, sinav = _sinav_tablosu(g, ders, no)
    harita = g.haritalar.get(anahtar)
    durum = sinav_durumu(g, ders, no)
    senaryolar = sorted(int(n) for n in (sinav.get("senaryolar") or {}))
    gruplar: dict[tuple, dict] = {}
    for c in sorted(dt["ciktilar"], key=lambda c: _kod_sirasi(c["kod"])):
        sayilar = {str(n): int(sinav["senaryolar"][str(n)].get(c["kod"], 0)) for n in senaryolar}
        if not any(sayilar.values()):
            continue
        yollar = _kitap_yollari(harita, c["kod"])
        grup_anahtari, baslik = _grup(c, yollar)
        gruplar.setdefault(grup_anahtari, {"baslik": baslik, "satirlar": []})["satirlar"].append({
            "kod": c["kod"], "kisa_ad": _kisa_ad(c, yollar), "metin": c["metin"], "sayilar": sayilar,
            "her_senaryoda": all(sayilar.values()), "kitapta": yollar,
            "kitap_durumu": ("var" if yollar else "bulunamadi") if harita else "harita_yok"})
    return {"ders": ders, "anahtar": anahtar, "sinav_no": no, "tur": sinav["tur"], "not": sinav.get("not"),
            "sinavlar": [{"sinav_no": int(n), "durum": sinav_durumu(g, ders, int(n))}
                         for n in sorted(dt["sinavlar"], key=int)],
            "durum": durum, "senaryolar": senaryolar, "duyurulan": durum["senaryo"] if durum["tur"] == "kesin" else None,
            "gruplar": [gruplar[k] for k in sorted(gruplar)],
            "toplamlar": {str(n): sum(sinav["senaryolar"][str(n)].values()) for n in senaryolar},
            "kitap_bolumleri": harita is not None,
            "harita_onayli": bool(harita and (harita.get("denetim") or {}).get("kim")),
            "guncellik": _guncellik(g, anahtar, harita, dt)}

```

- [ ] **Step 6: Testleri koş, geçtiğini gör**

Run: `env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_sinav_kilavuzu.py tests/test_sinav_senaryo.py tests/test_assistant_sinav_senaryosu.py`
Expected: PASS (yeni 21 test; senaryo testleri değişmeden geçer).

- [ ] **Step 7: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-hazirligi
git log --oneline -3 && git status --short
git add src/sinav_senaryo.py src/sinav_kilavuzu.py tests/hazirlik_fikstur.py tests/test_sinav_kilavuzu.py
git commit -m "$(cat <<'EOF'
feat(sinav-hazirligi): kılavuz modeli — sınav durumu, genel bakış, ders özeti ve güncellik

Kesin/olası/ülke geneli/geçti durumu duyurulan senaryodan; olası durum tek senaryo taşımaz (K8). Ders özeti
çıktı × senaryo matrisini kitap yollarıyla verir; haritasız ders "harita_yok", eşleşmeyen çıktı "bulunamadi";
harita eski tabloya göre kurulduysa ya da kitap değiştiyse güncellik bayrağı (K12).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: Kılavuz modeli II — bloklar, olası kip, bölüm başlıkları, okul/ödev/modül bağlamı, doğrulama, plan, ebeveyn özeti, damgalar

**Files:**
- Modify: `src/sinav_kilavuzu.py` (sona ekleme)
- Test: `tests/test_sinav_kilavuzu_belge.py`

**Interfaces:**
- Consumes: Görev 6'nın `Girdiler`, `ders_ozeti`, `_eslesen_bolumler`, `_sinav_kaydi`, `_sinav_tablosu`, `_kod_sirasi`, `_gun`, `KilavuzHatasi`; Görev 5'in gerçek haritası (son test).
- Produces:
  - `kilavuz(g, anahtar, no, senaryo: int | None, secenekler: {"ebeveyn": bool, "isaret": bool}) -> KilavuzModeli`; `calisma_plani(bloklar, bugun, tarih) -> dict | None`; `okulda(haftalar, ders, terimler)`, `ilgili_odevler(odevler, ders, terimler)`, `ilgili_moduller(moduller, kod)`; `icerik_ozeti(model) -> str` (sha256 hex)
  - `Baslik = {ad, tur: "etkinlik"|"baglanti"|"kontrol"|"tanim"|"ozet"|"diger", amac: str|None, sayfa}`
  - `Blok = {kod, kisa_ad, metin, senaryoda: bool, soru: int|None, aralik: [a, b]|None, her_senaryoda, kitapta: [KitapYolu], kitap_durumu, basliklar: [Baslik], okulda: [{hafta}], odevler: [{baslik, teslim}], moduller: [{baslik, yol: "/moduller/<slug>/v<N>"}], isaret: "hazirim"|"tekrar"|None}`
  - `KilavuzModeli = {surum: 1, ders, anahtar, sinav_no, durum: SinavDurumu, kip: "kesin"|"olasi"|"ulke_geneli", senaryo: int|None, duyurulan: int|None, secilen_duyurulan_degil: bool, not, ozet: {toplam_soru: int|None, soru_araligi: [a, b]|None, cikti_sayisi, her_senaryoda: [kod]}, matris: {senaryolar, duyurulan, gruplar, toplamlar}, uniteler: [{baslik, cerceveler: [{baslik: str|None, sayfa: int|None, son_sayfa: int|None, bloklar: [Blok]}]}], dogrulama: {duyurulan_konular: [{konu, kodlar}], senaryo_disi, karsiligi_yok, duyurunun_saymadigi}|None, plan: {gunler: [{tarih, ciktilar: [kod], genel_tekrar}]}|None, ebeveyn: {cikti_sayisi, toplam_soru, soru_araligi, hazirim, tekrar, isaretsiz, en_agir: [kod]}|None, kaynaklar: [{etiket, adres}], damgalar: {meb_guncelleme, tablo_alindi, kitaplar: [{baslik, baski, sha256_kisa}], uretim}, guncellik, kitap_bolumleri, harita_onayli, yz: {durum: "kapali"}, secenekler: {ebeveyn, isaret}, icerik_ozeti}`

- [ ] **Step 1: Başarısız testleri yaz**

`tests/test_sinav_kilavuzu_belge.py`:

```python
"""Kılavuz modeli II (plan Görev 7): kılavuz blokları, olası kip (K8), bağlam, doğrulama, plan, ebeveyn, damgalar."""
from datetime import date

import pytest

from src import sinav_kilavuzu as sk
from tests.hazirlik_fikstur import fen_haritasi, girdiler, sinav_kaydi

SEC = {"ebeveyn": False, "isaret": True}


def _bloklar(model):
    return {b["kod"]: b for u in model["uniteler"] for c in u["cerceveler"] for b in c["bloklar"]}


def test_kilavuz_kesin_bloklar_ve_soru():
    m = sk.kilavuz(girdiler(), "fen-bilimleri", 1, None, SEC)
    assert (m["kip"], m["senaryo"], m["duyurulan"], m["secilen_duyurulan_degil"]) == ("kesin", 2, 2, False)
    assert m["ozet"] == {"toplam_soru": 7, "soru_araligi": None, "cikti_sayisi": 4, "her_senaryoda": ["FB.7.2.1"]}
    b = _bloklar(m)
    assert (b["FB.7.2.1"]["soru"], b["FB.7.2.1"]["senaryoda"], b["FB.7.2.1"]["aralik"]) == (3, True, None)
    assert (b["FB.7.2.2"]["soru"], b["FB.7.2.2"]["senaryoda"]) == (0, False)    # 2. senaryoda yok: soluk satır
    assert [u["baslik"] for u in m["uniteler"]] == ["1. Ünite · Uzay Çağı", "2. Ünite · Kuvvet ve Enerjiyi Keşfedelim"]
    kuvvet = m["uniteler"][1]["cerceveler"][0]
    assert (kuvvet["baslik"], kuvvet["sayfa"], kuvvet["son_sayfa"]) == ("1. Kuvvet, İş ve Enerji İlişkisi", 59, 70)
    assert [x["kod"] for x in kuvvet["bloklar"]] == ["FB.7.2.1", "FB.7.2.2"]
    assert m["yz"] == {"durum": "kapali"} and m["surum"] == 1


def test_kilavuz_olasi_kip_tek_senaryo_sunmaz():
    """Review Focus (K8): duyuru yokken hiçbir blok tek soru sayısı, özet tek toplam taşımaz."""
    m = sk.kilavuz(girdiler(sinavlar=[]), "fen-bilimleri", 1, None, SEC)
    assert (m["kip"], m["senaryo"], m["duyurulan"], m["durum"]["tur"]) == ("olasi", None, None, "olasi")
    assert m["ozet"]["toplam_soru"] is None and m["ozet"]["soru_araligi"] == [6, 9]
    b = _bloklar(m)
    assert all(x["soru"] is None and x["senaryoda"] for x in b.values())
    assert b["FB.7.2.1"]["aralik"] == [2, 3] and b["FB.7.1.1"]["aralik"] == [0, 2]


def test_kilavuz_secilen_senaryo_duyurulan_degil():
    m = sk.kilavuz(girdiler(), "fen-bilimleri", 1, 3, SEC)
    assert (m["kip"], m["senaryo"], m["duyurulan"], m["secilen_duyurulan_degil"]) == ("olasi", 3, 2, True)
    assert m["ozet"]["toplam_soru"] == 8


def test_kilavuz_bilinmeyen_senaryo_hata():
    with pytest.raises(sk.KilavuzHatasi) as h:
        sk.kilavuz(girdiler(), "fen-bilimleri", 1, 9, SEC)
    assert h.value.kod == "bilinmeyen_senaryo"


def test_kilavuz_kitapta_ve_bolum_basliklari():
    b = _bloklar(sk.kilavuz(girdiler(), "fen-bilimleri", 1, None, SEC))
    assert b["FB.7.2.1"]["kitapta"][0]["baglanti"].endswith("#page=61")
    assert [(x["tur"], x["ad"], x["sayfa"]) for x in b["FB.7.2.1"]["basliklar"]] == [
        ("etkinlik", "Etkinlik Noktası-1", 60), ("etkinlik", "Etkinlik Noktası-2", 60),
        ("baglanti", "Bağlantı Noktası", 62), ("kontrol", "Kontrol Noktası", 63)]
    # İki konuya bağlı çıktı: iki konunun başlıkları sırayla.
    assert [x["ad"] for x in b["FB.7.1.1"]["basliklar"]][:2] == ["Keşif Noktası: Uzay Teknolojileri", "Kontrol Noktası"]
    assert "Neler Öğrendik?" in [x["ad"] for x in b["FB.7.1.1"]["basliklar"]]


def test_cerceveye_bagli_cikti_cercevenin_butun_basliklarini_alir():
    h = fen_haritasi()
    h["eslesme"]["FB.7.2.1"] = [{"kitap": 0, "unite": 2, "cerceve": 1, "konu": None}]
    b = _bloklar(sk.kilavuz(girdiler(haritalar={"fen-bilimleri": h}), "fen-bilimleri", 1, None, SEC))
    adlar = [x["ad"] for x in b["FB.7.2.1"]["basliklar"]]
    assert adlar[0] == "Bağlantı Noktası" and "Potansiyel Enerji" in adlar
    assert b["FB.7.2.1"]["kitapta"][0]["konu"] is None and b["FB.7.2.1"]["kitapta"][0]["sayfa"] == 59


def test_kilavuz_bulunamayan_cikti_blokta_bulunamadi():
    h = fen_haritasi()
    h["eslesme"].pop("FB.7.1.3")
    h["eslesmedi"] = ["FB.7.1.3"]
    m = sk.kilavuz(girdiler(haritalar={"fen-bilimleri": h}), "fen-bilimleri", 1, None, SEC)
    b = _bloklar(m)["FB.7.1.3"]
    assert (b["kitap_durumu"], b["kitapta"], b["basliklar"]) == ("bulunamadi", [], [])


def test_kilavuz_haritasiz_ders_kitap_bolumleri_yok():
    m = sk.kilavuz(girdiler(), "matematik", 1, None, SEC)
    assert (m["kitap_bolumleri"], m["kip"]) == (False, "olasi")
    assert [u["baslik"] for u in m["uniteler"]] == ["1. Ünite"]
    assert m["uniteler"][0]["cerceveler"][0]["baslik"] is None
    assert all(b["kitap_durumu"] == "harita_yok" for b in _bloklar(m).values())
    assert m["damgalar"]["kitaplar"] == [] and len(m["kaynaklar"]) == 2


def test_okulda_odev_ve_modul_baglami():
    haftalar = {"4. Hafta 05 Eki. - 11 Eki.": {"Fen Bilimleri": {"cards": ["Bu hafta fiziksel anlamda iş konusunu işledik."]}},
                "2. Hafta 21 Eyl. - 27 Eyl.": {"Fen Bilimleri": {"cards": ["Uzay teknolojileri sunumları"]}},
                "3. Hafta 28 Eyl. - 04 Eki.": {"Matematik": {"cards": ["Fiziksel anlamda iş"]}}}
    odevler = [{"Ders Adı": "Fen Bilimleri", "Ödev Başlığı": "İş ve enerji", "Ödev Son Teslim Tarihi": "30.10.2026 23:59",
                "detail": {"description": "Fiziksel anlamda iş sorularını çöz"}},
               {"Ders Adı": "Matematik", "Ödev Başlığı": "Fiziksel anlamda iş", "detail": {}}]
    moduller = [{"slug": "fen7-is", "version": 2, "title": "İş ve Enerji", "outcomes": ["FB.7.2.1"]},
                {"slug": "fen7-uzay", "version": 1, "title": "Uzay", "outcomes": ["FB.7.1.1"]}]
    b = _bloklar(sk.kilavuz(girdiler(haftalar=haftalar, odevler=odevler, moduller=moduller), "fen-bilimleri", 1, None, SEC))
    assert b["FB.7.2.1"]["okulda"] == [{"hafta": "4. Hafta 05 Eki. - 11 Eki."}]
    assert b["FB.7.1.1"]["okulda"] == [{"hafta": "2. Hafta 21 Eyl. - 27 Eyl."}]
    assert b["FB.7.2.1"]["odevler"] == [{"baslik": "İş ve enerji", "teslim": "30.10.2026 23:59"}]
    assert b["FB.7.2.1"]["moduller"] == [{"baslik": "İş ve Enerji", "yol": "/moduller/fen7-is/v2"}]
    assert b["FB.7.2.2"]["okulda"] == [] and b["FB.7.2.2"]["moduller"] == []


def test_dogrulama_duyuru_konulari():
    is_ = "Fiziksel anlamda yapılan işin bağlı olduğu faktörlere ilişkin bilimsel çıkarım yapabilme"
    g = girdiler(sinavlar=[sinav_kaydi(durum="kismen", konular=(is_, "Mısır tarihi"),
                                       eslesmeyen=("Mısır tarihi",), senaryo_disi=(), duyuruda=("FB.7.2.1",))])
    d = sk.kilavuz(g, "fen-bilimleri", 1, None, SEC)["dogrulama"]
    assert d["duyurulan_konular"][0] == {"konu": is_, "kodlar": ["FB.7.2.1"]}
    assert d["duyurulan_konular"][1] == {"konu": "Mısır tarihi", "kodlar": []}
    assert d["karsiligi_yok"] == ["Mısır tarihi"]
    assert d["duyurunun_saymadigi"] == ["FB.7.1.1", "FB.7.1.3", "FB.7.1.5"]
    assert sk.kilavuz(girdiler(sinavlar=[sinav_kaydi()]), "fen-bilimleri", 1, None, SEC)["dogrulama"] is None


def test_calisma_plani_dagilimi_ve_isaret_onceligi():
    g = girdiler(bugun=date(2026, 10, 30), isaretler={"fen-bilimleri": {"FB.7.1.5": "tekrar", "FB.7.2.1": "hazirim"}})
    plan = sk.kilavuz(g, "fen-bilimleri", 1, None, SEC)["plan"]
    # 30.10–02.11 dört gün: ilk üçü çalışma, 02.11 genel tekrar. Sıra: tekrar, işaretsizler (ağırlık), hazırım.
    assert plan["gunler"] == [
        {"tarih": "2026-10-30", "ciktilar": ["FB.7.1.5", "FB.7.2.1"], "genel_tekrar": False},
        {"tarih": "2026-10-31", "ciktilar": ["FB.7.1.1"], "genel_tekrar": False},
        {"tarih": "2026-11-01", "ciktilar": ["FB.7.1.3"], "genel_tekrar": False},
        {"tarih": "2026-11-02", "ciktilar": ["FB.7.1.5", "FB.7.1.1", "FB.7.1.3", "FB.7.2.1"], "genel_tekrar": True}]
    assert sk.calisma_plani([], date(2026, 11, 3), date(2026, 11, 3)) is None
    assert sk.kilavuz(girdiler(sinavlar=[]), "fen-bilimleri", 1, None, SEC)["plan"] is None   # tarih yok


def test_ebeveyn_ozeti_ve_isaret_secenegi():
    g = girdiler(isaretler={"fen-bilimleri": {"FB.7.2.1": "tekrar", "FB.7.1.1": "hazirim"}})
    m = sk.kilavuz(g, "fen-bilimleri", 1, None, {"ebeveyn": True, "isaret": True})
    assert m["ebeveyn"] == {"cikti_sayisi": 4, "toplam_soru": 7, "soru_araligi": None, "hazirim": 1, "tekrar": 1,
                            "isaretsiz": 2, "en_agir": ["FB.7.2.1", "FB.7.1.1", "FB.7.1.3"]}
    assert _bloklar(m)["FB.7.2.1"]["isaret"] == "tekrar"
    kapali = sk.kilavuz(g, "fen-bilimleri", 1, None, {"ebeveyn": False, "isaret": False})
    assert kapali["ebeveyn"] is None and all(b["isaret"] is None for b in _bloklar(kapali).values())
    assert kapali["secenekler"] == {"ebeveyn": False, "isaret": False}


def test_damgalar_kaynaklar_ve_icerik_ozeti():
    m = sk.kilavuz(girdiler(), "fen-bilimleri", 1, None, SEC)
    assert m["damgalar"] == {"meb_guncelleme": "2026-09-10T17:27", "tablo_alindi": "2026-10-20",
                             "kitaplar": [{"baslik": "Fen Bilimleri 7 (1. Kitap)", "baski": "2026-2027",
                                           "sha256_kisa": "a" * 12}], "uretim": "2026-10-25"}
    assert [k["etiket"] for k in m["kaynaklar"]] == [
        "MEB ÖDSGM · 1. Dönem Konu Soru Dağılım Tabloları (2026-2027)", "Fen Bilimleri konu-soru dağılım tablosu",
        "Fen Bilimleri 7 (1. Kitap) (EBA PDF)"]
    assert m["icerik_ozeti"] == sk.icerik_ozeti(m) == sk.kilavuz(girdiler(), "fen-bilimleri", 1, None, SEC)["icerik_ozeti"]
    isaretli = sk.kilavuz(girdiler(isaretler={"fen-bilimleri": {"FB.7.2.1": "tekrar"}}), "fen-bilimleri", 1, None, SEC)
    assert isaretli["icerik_ozeti"] != m["icerik_ozeti"]


def test_ulke_geneli_kilavuz_ve_tablo_eski():
    m = sk.kilavuz(girdiler(sinavlar=[sinav_kaydi("Türkçe", 2, durum="ulke_geneli", senaryo=None, tarih="2027-01-05")]),
                   "turkce", 2, None, SEC)
    assert (m["kip"], m["uniteler"], m["plan"], m["ozet"]["cikti_sayisi"]) == ("ulke_geneli", [], None, 0)
    assert m["not"].startswith("1. Dönem 2. Ortak Yazılı")
    with pytest.raises(sk.KilavuzHatasi) as h:
        sk.kilavuz(girdiler(bugun=date(2027, 2, 10)), "fen-bilimleri", 1, None, SEC)
    assert h.value.kod == "tablo_eski"


def test_gercek_fen_haritasiyla_kilavuz_kurulur():
    """Görev 5'in gerçek haritası modelin şemasına uyar (harita yeniden üretilirse burada düşer)."""
    h = sk.harita_oku("fen-bilimleri")
    assert h is not None
    m = sk.kilavuz(girdiler(haritalar={"fen-bilimleri": h}), "fen-bilimleri", 1, None, SEC)
    b = _bloklar(m)
    assert all(x["kitap_durumu"] == "var" and x["basliklar"] for x in b.values())
    assert b["FB.7.2.1"]["kitapta"][0]["konu"] == "Fiziksel Anlamda İş"
```

- [ ] **Step 2: Testi koş, düştüğünü gör**

Run: `env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_sinav_kilavuzu_belge.py`
Expected: FAIL — `AttributeError: module 'src.sinav_kilavuzu' has no attribute 'kilavuz'`.

- [ ] **Step 3: Kılavuz modelini yaz**

`src/sinav_kilavuzu.py`'nin sonuna:

```python
# ── Kılavuz (spec §2.4, §4; plan Görev 7) ──────────────────────────────────────────────────────────────────────

def _bolum_basliklari(harita: dict | None, kod: str) -> list[dict]:
    """Çıktının kitap bölümlerinde ele alınan başlıklar (K6: hepsi). Konuya bağlıysa konunun, çerçeveye bağlıysa
    çerçevenin ve bütün konularının başlıkları; aynı bölüm iki kez yazılmaz."""
    out: list[dict] = []
    gorulen: set[int] = set()
    for _, _, cer, konu in _eslesen_bolumler(harita, kod):
        for bolum in ([konu] if konu else [cer, *cer["konular"]]):
            if id(bolum) in gorulen:
                continue
            gorulen.add(id(bolum))
            out += [{"ad": b["ad"], "tur": b["tur"], "amac": b.get("amac"), "sayfa": b["sayfa"]}
                    for b in bolum.get("basliklar", [])]
    return out


def _terimler(yollar: list[dict]) -> list[str]:
    """Okul kartı ve ödev metninde aranacak katlanmış adlar: konu adları, yoksa çerçeve adları."""
    adlar = [y["konu"] for y in yollar if y["konu"]] or [y["cerceve"].split(". ", 1)[-1] for y in yollar]
    return [katla(a) for a in dict.fromkeys(adlar) if len(katla(a)) >= 4]


def _hafta_no(etiket: str) -> int:
    m = re.match(r"\s*(\d+)\.\s*Hafta", etiket)
    return int(m.group(1)) if m else 999


def okulda(haftalar: dict, ders: str, terimler: list[str]) -> list[dict]:
    """Konunun adı o dersin haftalık kartlarında geçtiği haftalar (spec §4.4 "okulda işlendiği hafta")."""
    if not terimler or not isinstance(haftalar, dict):
        return []
    out = []
    for etiket in sorted(haftalar, key=_hafta_no):
        dersler = haftalar[etiket] if isinstance(haftalar[etiket], dict) else {}
        for ad, icerik in dersler.items():
            if normalize_course(ad) != ders or not isinstance(icerik, dict):
                continue
            parcalar = [str(x) for x in (icerik.get("cards") or []) + (icerik.get("items") or [])]
            metin = katla(" ".join(parcalar + [str(icerik.get("text") or "")]))
            if any(t in metin for t in terimler):
                out.append({"hafta": etiket})
                break
    return out


def ilgili_odevler(odevler: list, ders: str, terimler: list[str]) -> list[dict]:
    if not terimler:
        return []
    out = []
    for r in odevler:
        if not isinstance(r, dict) or normalize_course(str(r.get("Ders Adı") or "")) != ders:
            continue
        ayrinti = r.get("detail") if isinstance(r.get("detail"), dict) else {}
        metin = katla(f"{r.get('Ödev Başlığı') or ''} {ayrinti.get('description') or ''}")
        if any(t in metin for t in terimler):
            out.append({"baslik": str(r.get("Ödev Başlığı") or ""), "teslim": r.get("Ödev Son Teslim Tarihi")})
    return out


def ilgili_moduller(moduller: list, kod: str) -> list[dict]:
    return [{"baslik": str(m.get("title") or m["slug"]), "yol": f"/moduller/{m['slug']}/v{m['version']}"}
            for m in moduller if isinstance(m, dict) and m.get("slug") and isinstance(m.get("version"), int)
            and kod in (m.get("outcomes") or [])]


def calisma_plani(bloklar: list[dict], bugun: date, tarih: date | None) -> dict | None:
    """Kalan günlere çıktıları dağıtan deterministik plan (spec §4.6): önce "tekrar" işaretliler, sonra işaretsizler,
    en son "hazırım"lar; her grupta soru ağırlığı büyükten küçüğe. Sınavdan önceki gün genel tekrardır."""
    if tarih is None or tarih <= bugun:
        return None
    adaylar = [b for b in bloklar if b["senaryoda"]]
    if not adaylar:
        return None
    sira = {"tekrar": 0, None: 1, "hazirim": 2}

    def agirlik(b):
        return b["soru"] if b["soru"] is not None else b["aralik"][1]
    adaylar.sort(key=lambda b: (sira[b["isaret"]], -agirlik(b), _kod_sirasi(b["kod"])))
    gunler = [bugun + timedelta(days=i) for i in range((tarih - bugun).days)]
    calisma = gunler[:-1] if len(gunler) >= 2 else gunler
    plan = [{"tarih": g.isoformat(), "ciktilar": [], "genel_tekrar": False} for g in calisma]
    for i, b in enumerate(adaylar):
        plan[i % len(plan)]["ciktilar"].append(b["kod"])
    if len(gunler) >= 2:
        plan.append({"tarih": gunler[-1].isoformat(), "ciktilar": [b["kod"] for b in adaylar], "genel_tekrar": True})
    return {"gunler": [p for p in plan if p["ciktilar"]]}


def _ozet(bloklar: list[dict], dagilim: dict | None, sinav: dict) -> dict:
    kapsam = [b for b in bloklar if b["senaryoda"]]
    toplamlar = [sum(d.values()) for d in (sinav.get("senaryolar") or {}).values()]
    return {"toplam_soru": sum(b["soru"] for b in kapsam) if dagilim is not None else None,
            "soru_araligi": [min(toplamlar), max(toplamlar)] if dagilim is None and toplamlar else None,
            "cikti_sayisi": len(kapsam), "her_senaryoda": [b["kod"] for b in bloklar if b["her_senaryoda"]]}


def _dogrulama(kayit: dict | None, dt: dict) -> dict | None:
    """Duyuru doğrulaması (spec §4.5): duyurudaki konuların karşılığı, senaryo dışı ve karşılıksız konular,
    duyurunun saymadığı senaryo çıktıları."""
    if not kayit:
        return None
    blok = kayit["senaryo"]
    konular = [str(k) for k in kayit.get("konular") or []]
    if not konular:
        return None
    kesin = blok.get("durum") in KESIN_DURUMLAR
    return {"duyurulan_konular": [{"konu": k, "kodlar": konu_eslestir(k, dt["ciktilar"])} for k in konular],
            "senaryo_disi": list(blok.get("senaryo_disi_konular") or []),
            "karsiligi_yok": list(blok.get("eslesmeyen_konular") or []),
            "duyurunun_saymadigi": [d["kod"] for d in blok.get("dagilim") or [] if kesin and not d.get("duyuruda")]}


def _ebeveyn(bloklar: list[dict], ozet: dict) -> dict:
    kapsam = [b for b in bloklar if b["senaryoda"]]

    def agirlik(b):
        return b["soru"] if b["soru"] is not None else b["aralik"][1]
    return {"cikti_sayisi": len(kapsam), "toplam_soru": ozet["toplam_soru"], "soru_araligi": ozet["soru_araligi"],
            "hazirim": sum(b["isaret"] == "hazirim" for b in kapsam), "tekrar": sum(b["isaret"] == "tekrar" for b in kapsam),
            "isaretsiz": sum(b["isaret"] is None for b in kapsam),
            "en_agir": [b["kod"] for b in sorted(kapsam, key=lambda b: (-agirlik(b), _kod_sirasi(b["kod"])))[:3]]}


def _kaynaklar(tablo: dict, dt: dict, harita: dict | None, ders: str) -> list[dict]:
    k = tablo["kaynak"]
    out = [{"etiket": f"MEB ÖDSGM · {k['baslik']}", "adres": k["sayfa"]}]
    if dt.get("adres"):
        out.append({"etiket": f"{ders} konu-soru dağılım tablosu", "adres": dt["adres"]})
    out += [{"etiket": f"{kt['baslik']} (EBA PDF)", "adres": kt["pdf_url"]} for kt in (harita or {}).get("kitaplar", [])]
    return out


def _damgalar(g: Girdiler, harita: dict | None) -> dict:
    k = g.tablo["kaynak"]
    return {"meb_guncelleme": k.get("meb_guncelleme"), "tablo_alindi": k.get("alindi"),
            "kitaplar": [{"baslik": kt["baslik"], "baski": kt.get("baski"), "sha256_kisa": str(kt.get("sha256") or "")[:12]}
                         for kt in (harita or {}).get("kitaplar", [])],
            "uretim": g.bugun.isoformat()}


def icerik_ozeti(model: dict) -> str:
    """Modelin sha256 özeti (PDF önbellek anahtarı): aynı girdi, aynı özet."""
    govde = {k: v for k, v in model.items() if k != "icerik_ozeti"}
    return hashlib.sha256(json.dumps(govde, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def kilavuz(g: Girdiler, anahtar: str, no: int, senaryo: int | None, secenekler: dict) -> dict:
    """Kapsam kılavuzu modeli (spec §2.4, §4). `senaryo` verilmezse duyurulan senaryo; o da yoksa olası kip: bloklar
    tek sayı değil senaryolar arası aralık taşır (K8). `secenekler`: {"ebeveyn": bool, "isaret": bool}."""
    oz = ders_ozeti(g, anahtar, no)
    ders = oz["ders"]
    dt, sinav = _sinav_tablosu(g, ders, no)
    harita = g.haritalar.get(anahtar)
    duyurulan = oz["duyurulan"]
    if sinav["tur"] == "ulke_geneli":
        senaryo, kip = None, "ulke_geneli"
    else:
        if senaryo is not None and str(senaryo) not in sinav["senaryolar"]:
            raise KilavuzHatasi("bilinmeyen_senaryo")
        senaryo = senaryo if senaryo is not None else duyurulan
        kip = "kesin" if senaryo is not None and senaryo == duyurulan else "olasi"
    isaret_acik = bool(secenekler.get("isaret", True))
    isaretler = (g.isaretler.get(anahtar) or {}) if isaret_acik else {}
    dagilim = sinav["senaryolar"][str(senaryo)] if senaryo is not None else None
    bloklar: list[dict] = []
    uniteler: dict[tuple, dict] = {}
    for grup in oz["gruplar"]:
        for s in grup["satirlar"]:
            sayilar = list(s["sayilar"].values())
            terimler = _terimler(s["kitapta"])
            b = {"kod": s["kod"], "kisa_ad": s["kisa_ad"], "metin": s["metin"],
                 "senaryoda": dagilim.get(s["kod"], 0) > 0 if dagilim is not None else True,
                 "soru": int(dagilim.get(s["kod"], 0)) if dagilim is not None else None,
                 "aralik": None if dagilim is not None else [min(sayilar), max(sayilar)],
                 "her_senaryoda": s["her_senaryoda"], "kitapta": s["kitapta"], "kitap_durumu": s["kitap_durumu"],
                 "basliklar": _bolum_basliklari(harita, s["kod"]),
                 "okulda": okulda(g.haftalar, ders, terimler), "odevler": ilgili_odevler(g.odevler, ders, terimler),
                 "moduller": ilgili_moduller(g.moduller, s["kod"]), "isaret": isaretler.get(s["kod"])}
            bloklar.append(b)
            bolum = next(_eslesen_bolumler(harita, s["kod"]), None)
            if bolum:
                _, u, cer, _ = bolum
                unite = uniteler.setdefault((0, u["no"]), {"baslik": f"{u['no']}. Ünite · {u['ad']}", "cerceveler": {}})
                cerceve = unite["cerceveler"].setdefault(cer["no"], {
                    "baslik": f"{cer['no']}. {cer['ad']}", "sayfa": cer["sayfa"], "son_sayfa": cer["son_sayfa"], "bloklar": []})
            else:
                unite = uniteler.setdefault((1, grup["baslik"]), {"baslik": grup["baslik"], "cerceveler": {}})
                cerceve = unite["cerceveler"].setdefault(0, {"baslik": None, "sayfa": None, "son_sayfa": None, "bloklar": []})
            cerceve["bloklar"].append(b)
    ozet = _ozet(bloklar, dagilim, sinav)
    tarih = _gun(oz["durum"]["tarih"])
    model = {
        "surum": SURUM, "ders": ders, "anahtar": anahtar, "sinav_no": no, "durum": oz["durum"], "kip": kip,
        "senaryo": senaryo, "duyurulan": duyurulan,
        "secilen_duyurulan_degil": duyurulan is not None and senaryo != duyurulan, "not": sinav.get("not"),
        "ozet": ozet, "matris": {k: oz[k] for k in ("senaryolar", "duyurulan", "gruplar", "toplamlar")},
        "uniteler": [{"baslik": u["baslik"], "cerceveler": [u["cerceveler"][c] for c in sorted(u["cerceveler"])]}
                     for _, u in sorted(uniteler.items(), key=lambda x: (x[0][0], str(x[0][1]).zfill(4)))],
        "dogrulama": _dogrulama(_sinav_kaydi(g, ders, no), dt),
        "plan": calisma_plani(bloklar, g.bugun, tarih) if oz["durum"]["tur"] != "gecti" else None,
        "ebeveyn": _ebeveyn(bloklar, ozet) if secenekler.get("ebeveyn") else None,
        "kaynaklar": _kaynaklar(g.tablo, dt, harita, ders), "damgalar": _damgalar(g, harita),
        "guncellik": oz["guncellik"], "kitap_bolumleri": oz["kitap_bolumleri"], "harita_onayli": oz["harita_onayli"],
        "yz": {"durum": "kapali"},
        "secenekler": {"ebeveyn": bool(secenekler.get("ebeveyn")), "isaret": isaret_acik},
    }
    model["icerik_ozeti"] = icerik_ozeti(model)
    return model
```

- [ ] **Step 4: Testleri koş, geçtiğini gör**

Run: `env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_sinav_kilavuzu_belge.py tests/test_sinav_kilavuzu.py`
Expected: PASS (15 + 21 test). `test_gercek_fen_haritasiyla_kilavuz_kurulur` Görev 5'in dosyasını okur.

- [ ] **Step 5: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-hazirligi
git log --oneline -3 && git status --short
git add src/sinav_kilavuzu.py tests/test_sinav_kilavuzu_belge.py
git commit -m "$(cat <<'EOF'
feat(sinav-hazirligi): kılavuz modeli — bloklar, olası kip, bölüm başlıkları, bağlam, plan ve damgalar

Bloklar ünite › çerçeve › çıktı düzeninde; olası kipte soru yerine senaryolar arası aralık (K8); kitap
bölümünün bütün başlıkları (K6); okul haftası, ödev ve modül bağlamı; duyuru doğrulaması, deterministik
çalışma planı, ebeveyn özeti, kaynaklar ve damgalar; içerik özeti PDF önbelleğinin anahtarıdır. YZ kapalı.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: Hazırlık işaretleri deposu, `/api/hazirlik*` uçları ve modelden üretilen pano fikstürleri

**Files:**
- Create: `src/hazirlik_isaretleri.py`
- Modify: `src/dashboard_api.py` (`# --- Sınav uyarıları: web push abonelikleri` bölümünün hemen önüne)
- Create: `scripts/hazirlik_fiksturleri.py`, `dashboard/tests/e2e/fixtures/hazirlik/*.json` (betik üretir)
- Test: `tests/test_hazirlik_api.py`, `tests/test_hazirlik_fiksturleri.py`

**Interfaces:**
- Consumes: Görev 6–7'nin `sinav_kilavuzu` yüzeyi; `dashboard_api._sinav_api_listesi`, `_scraped`, `_load_json`, `_icerik_haftalari`, `_combined_homework_rows`, `module_store`, `_bildirim_kisisi`, `require_auth`.
- Produces:
  - `HazirlikIsaretleri(yol)`: `.kisi(email) -> {ders: {kod: durum}}`, `.yaz(email, ders, kod, durum | None) -> {kod: durum}`; `DURUMLAR = ("hazirim", "tekrar")`
  - Uçlar (hepsi `@require_auth`, hiçbiri `READER_ENDPOINTS`'te): `GET /api/hazirlik` → GenelBakis; `GET /api/hazirlik/<anahtar>/<int:sinav_no>` → DersOzeti; `GET /api/hazirlik/<anahtar>/<int:sinav_no>/kilavuz?senaryo=N&ebeveyn=1&isaret=0` → KilavuzModeli; `PUT /api/hazirlik/isaret` `{ders, kod, durum: "hazirim"|"tekrar"|null}` → `{ders, isaretler}`. Hatalar `{error, mesaj}`: bilinmeyen ders/sınav/senaryo 404, `tablo_yok` 503, `tablo_eski` 409, geçersiz gövde 400, kişisiz istek 403, yazılamayan dosya 503.
  - Test kancaları (Görev 14 de kullanır): `_hazirlik_bugun()`, `_hazirlik_sinavlari()`, `_hazirlik_girdileri(email=None)`, `_hazirlik_modeli(anahtar, sinav_no) -> (model, None) | (None, yanıt)`, `_hazirlik_hatasi(kod)`, `_hazirlik_kisisi()`
  - Fikstürler (Görev 9–14'ün e2e'leri okur): `genel`, `fen-bilimleri-1`, `fen-bilimleri-2`, `fen-bilimleri-1-kilavuz`, `fen-bilimleri-1-kilavuz-ebeveyn`, `fen-bilimleri-1-olasi`, `fen-bilimleri-1-olasi-kilavuz`, `fen-bilimleri-1-k12-kilavuz`, `fen-bilimleri-1-bulunamadi-kilavuz`, `matematik-1`, `matematik-1-kilavuz` (bugün 2026-10-25; Fen 1. yazılı 3 Kasım, 2. senaryo duyurulu, 3 konu; Türkçe 1. yazılı geçti, 4. senaryoydu; Türkçe 2. yazılı 5 Ocak, ülke geneli; FB.7.2.1 "tekrar" işaretli).

- [ ] **Step 1: Başarısız testleri yaz**

`tests/test_hazirlik_api.py`:

```python
"""Sınav hazırlığı uçları ve işaret deposu (plan Görev 8): yetki, 404'ler, senaryo parametresi, işaretler."""
import json
import os
from datetime import date

import pytest

os.environ.setdefault("TEST_AUTH_BYPASS", "1")
import src.dashboard_api as api  # noqa: E402
from src import sinav_kilavuzu  # noqa: E402
from src.hazirlik_isaretleri import HazirlikIsaretleri  # noqa: E402
from tests.hazirlik_fikstur import FEN_KONULARI, fen_haritasi, sinav_kaydi  # noqa: E402

AILE = "drmahirkurt@gmail.com"
OKUYUCU = next(e for e, r in api.USER_ROLES.items() if r == api.ROLE_READER)


@pytest.fixture
def c(tmp_path, monkeypatch):
    out = tmp_path / "output"
    out.mkdir()
    monkeypatch.setattr(api, "TEST_AUTH_BYPASS", False)
    monkeypatch.setattr(api, "OUTPUT_DIR", str(out))
    monkeypatch.setattr(api, "PHOTO_HOMEWORK_FILE", str(out / "photo_homework.json"))
    monkeypatch.setattr(api, "_ek_kayitlari", lambda: {})
    monkeypatch.setattr(api, "_scraped", lambda: {})
    monkeypatch.setattr(api, "_hazirlik_bugun", lambda: date(2026, 10, 25))
    monkeypatch.setattr(api, "_hazirlik_sinavlari", lambda: [sinav_kaydi(konular=FEN_KONULARI)])
    monkeypatch.setattr(sinav_kilavuzu, "harita_oku",
                        lambda anahtar, dizin=None: fen_haritasi() if anahtar == "fen-bilimleri" else None)
    api.app.config["TESTING"] = True
    with api.app.test_client() as istemci:
        yield istemci


def giris(c, email):
    with c.session_transaction() as s:
        s["user_email"] = email


def test_genel_bakis_ucu(c):
    giris(c, AILE)
    r = c.get("/api/hazirlik")
    assert r.status_code == 200
    j = r.get_json()
    assert j["durum"] == "hazir" and j["yaklasan"][0]["anahtar"] == "fen-bilimleri"
    assert len(j["dersler"]) == 6


def test_ders_ucu_ve_404ler(c):
    giris(c, AILE)
    assert c.get("/api/hazirlik/fen-bilimleri/1").get_json()["toplamlar"] == {"1": 9, "2": 7, "3": 8, "4": 6}
    r = c.get("/api/hazirlik/fizik/1")
    assert (r.status_code, r.get_json()["error"]) == (404, "bilinmeyen_ders")
    assert c.get("/api/hazirlik/fen-bilimleri/3").status_code == 404
    assert c.get("/api/hazirlik/fen-bilimleri/x").status_code == 404


def test_kilavuz_ucu_senaryo_ve_secenek_parametreleri(c):
    giris(c, AILE)
    assert c.get("/api/hazirlik/fen-bilimleri/1/kilavuz").get_json()["senaryo"] == 2
    j = c.get("/api/hazirlik/fen-bilimleri/1/kilavuz?senaryo=3&ebeveyn=1&isaret=0").get_json()
    assert (j["senaryo"], j["secilen_duyurulan_degil"], j["secenekler"]) == (3, True, {"ebeveyn": True, "isaret": False})
    for kotu in ("9", "abc", "-1"):
        r = c.get(f"/api/hazirlik/fen-bilimleri/1/kilavuz?senaryo={kotu}")
        assert (r.status_code, r.get_json()["error"]) == (404, "bilinmeyen_senaryo")


def test_tablo_eski_409(c, monkeypatch):
    giris(c, AILE)
    monkeypatch.setattr(api, "_hazirlik_bugun", lambda: date(2027, 2, 10))
    assert c.get("/api/hazirlik").get_json()["durum"] == "tablo_eski"
    r = c.get("/api/hazirlik/fen-bilimleri/1/kilavuz")
    assert (r.status_code, r.get_json()["mesaj"]) == (409, "Yeni yılın tabloları bekleniyor.")


def test_okuyucu_hazirlik_uclarina_erisemez(c):
    """Review Focus: okuma yetkili hesap hazırlık uçlarına erişemez, işaret koyamaz (default-deny)."""
    giris(c, OKUYUCU)
    assert c.get("/api/hazirlik").status_code == 403
    assert c.get("/api/hazirlik/fen-bilimleri/1/kilavuz").status_code == 403
    r = c.put("/api/hazirlik/isaret", json={"ders": "fen-bilimleri", "kod": "FB.7.2.1", "durum": "hazirim"})
    assert r.status_code == 403
    assert not os.path.exists(os.path.join(api.OUTPUT_DIR, "hazirlik_isaretleri.json"))


def test_api_anahtari_okur_ama_isaret_koyamaz(c, monkeypatch):
    """Review Focus: anahtarın kişisi yok — okuyabilir, işaret koyamaz."""
    monkeypatch.setattr(api, "API_KEYS", [("test", "tdyK_deneme")])
    baslik = {"Authorization": "Bearer tdyK_deneme"}
    assert c.get("/api/hazirlik", headers=baslik).status_code == 200
    r = c.put("/api/hazirlik/isaret", headers=baslik, json={"ders": "fen-bilimleri", "kod": "FB.7.2.1", "durum": "hazirim"})
    assert (r.status_code, r.get_json()["error"]) == (403, "yalnız oturumla")


def test_isaret_yaz_kilavuzda_gorunur_ve_kaldirilir(c):
    giris(c, AILE)
    r = c.put("/api/hazirlik/isaret", json={"ders": "fen-bilimleri", "kod": "FB.7.2.1", "durum": "tekrar"})
    assert r.get_json() == {"ders": "fen-bilimleri", "isaretler": {"FB.7.2.1": "tekrar"}}
    m = c.get("/api/hazirlik/fen-bilimleri/1/kilavuz").get_json()
    blok = next(b for u in m["uniteler"] for cer in u["cerceveler"] for b in cer["bloklar"] if b["kod"] == "FB.7.2.1")
    assert blok["isaret"] == "tekrar"
    r = c.put("/api/hazirlik/isaret", json={"ders": "fen-bilimleri", "kod": "FB.7.2.1", "durum": None})
    assert r.get_json()["isaretler"] == {}


@pytest.mark.parametrize("govde", [
    {"ders": "fizik", "kod": "FB.7.2.1", "durum": "tekrar"}, {"ders": "fen-bilimleri", "kod": "MAT.7.1.1", "durum": "tekrar"},
    {"ders": "fen-bilimleri", "kod": "FB.7.2.1", "durum": "belki"}, {"ders": "fen-bilimleri", "kod": ["FB.7.2.1"]}, {}])
def test_isaret_gecersiz_girdi_400(c, govde):
    giris(c, AILE)
    assert c.put("/api/hazirlik/isaret", json=govde).status_code == 400


def test_isaret_deposu_kisi_ayri_ve_bozuk_dosya_kenara_alinir(tmp_path):
    yol = tmp_path / "hazirlik_isaretleri.json"
    d = HazirlikIsaretleri(yol)
    assert d.yaz("A@x.com", "fen-bilimleri", "FB.7.2.1", "hazirim") == {"FB.7.2.1": "hazirim"}
    d.yaz("b@x.com", "fen-bilimleri", "FB.7.1.1", "tekrar")
    assert d.kisi("a@x.com") == {"fen-bilimleri": {"FB.7.2.1": "hazirim"}}
    with pytest.raises(ValueError):
        d.yaz("a@x.com", "fen-bilimleri", "FB.7.2.1", "belki")
    yol.write_text("{", encoding="utf-8")
    assert d.kisi("a@x.com") == {}
    d.yaz("a@x.com", "fen-bilimleri", "FB.7.2.2", "tekrar")
    assert len(list(tmp_path.glob("hazirlik_isaretleri.json.bozuk-*"))) == 1
    assert json.loads(yol.read_text(encoding="utf-8"))["kisiler"] == {"a@x.com": {"fen-bilimleri": {"FB.7.2.2": "tekrar"}}}
```

- [ ] **Step 2: Testi koş, düştüğünü gör**

Run: `env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_hazirlik_api.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.hazirlik_isaretleri'`.

- [ ] **Step 3: İşaret deposunu yaz**

`src/hazirlik_isaretleri.py`:

```python
"""Kişi başına hazırlık işaretleri (spec 2026-10-25 §2.3): output/hazirlik_isaretleri.json.

{"surum": 1, "kisiler": {email: {ders anahtarı: {çıktı kodu: "hazirim" | "tekrar"}}}}. İki gunicorn işçisi aynı
dosyaya yazar: okuma-değiştirme-yazma `fcntl.flock` altında ve atomik; okunamayan dosya yazmadan önce
`.bozuk-<YYYYmmddHHMMSS>` olarak kenara alınır (silinmez)."""
from __future__ import annotations

import fcntl
import json
import os
from datetime import datetime
from pathlib import Path

from src.json_utils import atomic_json_dump

SURUM = 1
DURUMLAR = ("hazirim", "tekrar")


class HazirlikIsaretleri:
    def __init__(self, yol: Path | str):
        self.yol = Path(yol)

    def _oku(self) -> tuple[dict, bool]:
        """(veri, bozuk_mu). Dosya yoksa boş veri, bozuk değil."""
        bos = {"surum": SURUM, "kisiler": {}}
        try:
            veri = json.loads(self.yol.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return bos, False
        except (OSError, ValueError):
            return bos, True
        if not isinstance(veri, dict) or veri.get("surum") != SURUM or not isinstance(veri.get("kisiler"), dict):
            return bos, True
        return veri, False

    def kisi(self, email: str) -> dict[str, dict[str, str]]:
        kayit = self._oku()[0]["kisiler"].get(email.lower())
        if not isinstance(kayit, dict):
            return {}
        return {ders: {kod: d for kod, d in kodlar.items() if d in DURUMLAR}
                for ders, kodlar in kayit.items() if isinstance(kodlar, dict)}

    def yaz(self, email: str, ders: str, kod: str, durum: str | None) -> dict[str, str]:
        """İşareti koyar (`durum` None ise kaldırır); kişinin o dersteki işaretlerini döner."""
        if durum is not None and durum not in DURUMLAR:
            raise ValueError(f"geçersiz işaret: {durum}")
        self.yol.parent.mkdir(parents=True, exist_ok=True)
        with open(self.yol.with_name(f".{self.yol.name}.kilit"), "w") as kilit:
            fcntl.flock(kilit, fcntl.LOCK_EX)
            veri, bozuk = self._oku()
            if bozuk and self.yol.exists():
                os.replace(self.yol, self.yol.with_name(f"{self.yol.name}.bozuk-{datetime.now():%Y%m%d%H%M%S}"))
            kisiler = veri["kisiler"]
            kisi = kisiler.get(email.lower())
            if not isinstance(kisi, dict):
                kisi = kisiler[email.lower()] = {}
            kodlar = kisi.get(ders)
            if not isinstance(kodlar, dict):
                kodlar = kisi[ders] = {}
            if durum is None:
                kodlar.pop(kod, None)
            else:
                kodlar[kod] = durum
            if not kodlar:
                kisi.pop(ders, None)
            atomic_json_dump(veri, str(self.yol))
            return dict(kodlar)
```

- [ ] **Step 4: Uçları yaz**

`src/dashboard_api.py`'de `# --- Sınav uyarıları: web push abonelikleri (spec 2026-10-16 §7) ---` satırının hemen önüne (`_bildirim_kisisi` aynı modülde aşağıda tanımlıdır; çağrı anında çözülür):

```python
# --- Sınav hazırlığı (spec 2026-10-25 §2.5, plan Görev 8) ---
# Oturum + tam rol: okuyucu default-deny (READER_ENDPOINTS'e eklenmez). API anahtarı okuyabilir ama işaret koyamaz:
# anahtarın kişisi yok, işaretler kişi başınadır.

def _hazirlik_bugun():
    return datetime.now().date()


def _hazirlik_sinavlari():
    return _sinav_api_listesi(_scraped())["exams"]


def _hazirlik_isaret_deposu():
    from src.hazirlik_isaretleri import HazirlikIsaretleri
    return HazirlikIsaretleri(os.path.join(OUTPUT_DIR, "hazirlik_isaretleri.json"))


def _hazirlik_kisisi():
    """İşaretin sahibi: oturumdaki tam roldeki kişi; API anahtarı ve okuyucu None (bildirim uçlarıyla aynı kural)."""
    return _bildirim_kisisi()


def _hazirlik_girdileri(email=None):
    from src import sinav_kilavuzu, sinav_senaryo
    data = _scraped()
    try:
        denetim = _load_json("kitap_denetimi.json")
    except (OSError, ValueError):
        denetim = {}
    haritalar = {}
    for anahtar in sinav_kilavuzu.ANAHTAR_DERSLERI:
        harita = sinav_kilavuzu.harita_oku(anahtar)
        if harita is not None:
            haritalar[anahtar] = harita
    return sinav_kilavuzu.Girdiler(
        tablo=sinav_senaryo.tablo_oku(), haritalar=haritalar, sinavlar=_hazirlik_sinavlari(), bugun=_hazirlik_bugun(),
        kitap_denetimi=denetim if isinstance(denetim, dict) else {}, haftalar=_icerik_haftalari(data)["weeks"],
        odevler=_combined_homework_rows(data),
        moduller=module_store.latest_active(module_store.read_catalog(OUTPUT_DIR)),
        isaretler=_hazirlik_isaret_deposu().kisi(email) if email else {})


_HAZIRLIK_HATALARI = {
    "bilinmeyen_ders": (404, "Bu ders için MEB senaryosu yok."),
    "bilinmeyen_sinav": (404, "Bu yazılı MEB tablosunda yok."),
    "bilinmeyen_senaryo": (404, "Bu senaryo MEB tablosunda yok."),
    "tablo_yok": (503, "MEB konu-soru dağılım tablosu okunamadı."),
    "tablo_eski": (409, "Yeni yılın tabloları bekleniyor."),
}


def _hazirlik_hatasi(kod):
    durum, mesaj = _HAZIRLIK_HATALARI.get(kod, (400, "İstek anlaşılamadı."))
    return jsonify({"error": kod, "mesaj": mesaj}), durum


def _hazirlik_modeli(anahtar, sinav_no):
    """(model, None) ya da (None, hata yanıtı): ?senaryo=N (1–2 rakam; başka değer bilinmeyen senaryo),
    ?ebeveyn=1, ?isaret=0."""
    from src import sinav_kilavuzu
    ham = (request.args.get("senaryo") or "").strip()
    if ham and not re.fullmatch(r"\d{1,2}", ham):
        return None, _hazirlik_hatasi("bilinmeyen_senaryo")
    secenekler = {"ebeveyn": request.args.get("ebeveyn") == "1", "isaret": request.args.get("isaret", "1") != "0"}
    try:
        return sinav_kilavuzu.kilavuz(_hazirlik_girdileri(_hazirlik_kisisi()), anahtar, sinav_no,
                                      int(ham) if ham else None, secenekler), None
    except sinav_kilavuzu.KilavuzHatasi as hata:
        return None, _hazirlik_hatasi(hata.kod)


@app.route("/api/hazirlik")
@require_auth
def hazirlik_genel():
    from src import sinav_kilavuzu
    return jsonify(sinav_kilavuzu.genel_bakis(_hazirlik_girdileri()))


@app.route("/api/hazirlik/<anahtar>/<int:sinav_no>")
@require_auth
def hazirlik_ders(anahtar, sinav_no):
    from src import sinav_kilavuzu
    try:
        return jsonify(sinav_kilavuzu.ders_ozeti(_hazirlik_girdileri(), anahtar, sinav_no))
    except sinav_kilavuzu.KilavuzHatasi as hata:
        return _hazirlik_hatasi(hata.kod)


@app.route("/api/hazirlik/<anahtar>/<int:sinav_no>/kilavuz")
@require_auth
def hazirlik_kilavuz(anahtar, sinav_no):
    model, hata = _hazirlik_modeli(anahtar, sinav_no)
    return hata if hata else jsonify(model)


@app.route("/api/hazirlik/isaret", methods=["PUT"])
@require_auth
def hazirlik_isaret():
    from src import sinav_kilavuzu, sinav_senaryo
    email = _hazirlik_kisisi()
    if not email:
        return jsonify({"error": "yalnız oturumla", "mesaj": "İşareti yalnız oturum açmış aile üyesi koyabilir."}), 403
    govde = request.get_json(silent=True) or {}
    anahtar, kod, durum = govde.get("ders"), govde.get("kod"), govde.get("durum")
    ders = sinav_kilavuzu.ANAHTAR_DERSLERI.get(anahtar) if isinstance(anahtar, str) else None
    tablo = sinav_senaryo.tablo_oku()
    kodlar = {c["kod"] for c in tablo["dersler"].get(ders, {}).get("ciktilar", [])} if tablo and ders else set()
    if not ders or not isinstance(kod, str) or kod not in kodlar or durum not in (None, "hazirim", "tekrar"):
        return jsonify({"error": "gecersiz", "mesaj": "Ders, çıktı kodu ya da işaret geçersiz."}), 400
    try:
        isaretler = _hazirlik_isaret_deposu().yaz(email, anahtar, kod, durum)
    except OSError:
        app.logger.warning("hazırlık işareti yazılamadı", exc_info=True)
        return jsonify({"error": "yazilamadi", "mesaj": "İşaret kaydedilemedi."}), 503
    return jsonify({"ders": anahtar, "isaretler": isaretler})
```

- [ ] **Step 5: Testleri koş, geçtiğini gör**

Run: `env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_hazirlik_api.py tests/test_dashboard_api.py`
Expected: PASS (13 yeni test; mevcut API testleri değişmeden).

- [ ] **Step 6: Fikstür üreticisini ve tazelik testini yaz, fikstürleri üret**

`scripts/hazirlik_fiksturleri.py`:

```python
"""Pano e2e fikstürleri modelin kendisinden üretilir (plan Görev 8): elle yazılmış, şekli varsayılmış fikstür
yüzeyi boş çizdirir ve testi boşuna geçirir. Girdiler: gerçek senaryo tablosu, gerçek Fen haritası
(src/kitap_haritalari/fen-bilimleri.json), 2026-10-25'e sabitlenmiş örnek sınav kayıtları.

    env -u ANTHROPIC_API_KEY .venv/bin/python -I scripts/hazirlik_fiksturleri.py      # dashboard/tests/e2e/fixtures/hazirlik/*.json
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

from src import sinav_kilavuzu as sk  # noqa: E402
from src.sinav_senaryo import tablo_oku  # noqa: E402

HEDEF = KOK / "dashboard" / "tests" / "e2e" / "fixtures" / "hazirlik"
BUGUN = date(2026, 10, 25)
DUYURU = "Sınav, İstanbul İl MEB tarafından belirlenen 2. senaryoya göre uygulanacaktır."


def _kayit(tablo, ders, no, *, durum, senaryo, tarih, status, sid, konular=(), duyuruda=()):
    dt = tablo["dersler"][ders]
    sinav = dt["sinavlar"][str(no)]
    kesin = durum in sk.KESIN_DURUMLAR
    d = sinav.get("senaryolar", {}).get(str(senaryo), {}) if kesin else {}
    dagilim = [{"kod": c["kod"], "metin": c["metin"], "soru": d[c["kod"]], "duyuruda": c["kod"] in duyuruda}
               for c in dt["ciktilar"] if c["kod"] in d]
    blok = {"durum": durum, "ders": ders, "sinav_no": no, "donem": 1, "anilan": [senaryo] if senaryo else [],
            "cumle": DUYURU if kesin else None, "senaryo": senaryo if kesin else None,
            "toplam": sum(d.values()) if d else None, "dagilim": dagilim, "eslesen_konu_sayisi": len(konular),
            "eslesmeyen_konular": [], "senaryo_disi_konular": [], "adaylar": [],
            "senaryo_sayisi": len(sinav.get("senaryolar", {})), "kaynak": tablo["kaynak"]["sayfa"],
            "meb_guncelleme": tablo["kaynak"]["meb_guncelleme"]}
    return {"id": sid, "course": ders, "title": f"{ders} {no}. Yazılı", "date": tarih, "status": status,
            "konular": list(konular), "senaryo": blok}


def fiksturler() -> dict[str, dict]:
    tablo = tablo_oku()
    harita = sk.harita_oku("fen-bilimleri")
    if tablo is None or harita is None:
        raise SystemExit("senaryo tablosu ya da Fen haritası okunamadı")
    fen_konulari = ("Uzay araştırmaları için geliştirilen teknolojileri karşılaştırabilme",
                    "Uzay araştırmalarının yol açabileceği problemleri çözebilme",
                    "Fiziksel anlamda yapılan işin bağlı olduğu faktörlere ilişkin bilimsel çıkarım yapabilme")
    sinavlar = [
        _kayit(tablo, "Fen Bilimleri", 1, durum="dogrulandi", senaryo=2, tarih="2026-11-03", status="upcoming",
               sid="fen11", konular=fen_konulari, duyuruda=("FB.7.1.1", "FB.7.1.3", "FB.7.2.1")),
        _kayit(tablo, "Türkçe", 1, durum="dogrulandi", senaryo=4, tarih="2026-10-22", status="past", sid="tr11"),
        _kayit(tablo, "Türkçe", 2, durum="ulke_geneli", senaryo=None, tarih="2027-01-05", status="upcoming", sid="tr12"),
    ]
    taban = dict(tablo=tablo, haritalar={"fen-bilimleri": harita}, sinavlar=sinavlar, bugun=BUGUN,
                 isaretler={"fen-bilimleri": {"FB.7.2.1": "tekrar"}})
    g = sk.Girdiler(**taban)
    olasi = sk.Girdiler(**{**taban, "sinavlar": sinavlar[1:]})
    k12 = sk.Girdiler(**{**taban, "kitap_denetimi": {"fen-bilimleri": {"denetlendi": "2026-10-25", "kitaplar": [
        {"pdf_url": harita["kitaplar"][0]["pdf_url"], "sha256": "0" * 64}]}}})
    eksik = json.loads(json.dumps(harita))
    eksik["eslesme"].pop("FB.7.1.3")
    eksik["eslesmedi"] = ["FB.7.1.3"]
    bulunamadi = sk.Girdiler(**{**taban, "haritalar": {"fen-bilimleri": eksik}})
    acik = {"ebeveyn": False, "isaret": True}
    return {
        "genel": sk.genel_bakis(g),
        "fen-bilimleri-1": sk.ders_ozeti(g, "fen-bilimleri", 1),
        "fen-bilimleri-2": sk.ders_ozeti(g, "fen-bilimleri", 2),
        "fen-bilimleri-1-kilavuz": sk.kilavuz(g, "fen-bilimleri", 1, None, acik),
        "fen-bilimleri-1-kilavuz-ebeveyn": sk.kilavuz(g, "fen-bilimleri", 1, None, {"ebeveyn": True, "isaret": True}),
        "fen-bilimleri-1-olasi": sk.ders_ozeti(olasi, "fen-bilimleri", 1),
        "fen-bilimleri-1-olasi-kilavuz": sk.kilavuz(olasi, "fen-bilimleri", 1, None, acik),
        "fen-bilimleri-1-k12-kilavuz": sk.kilavuz(k12, "fen-bilimleri", 1, None, acik),
        "fen-bilimleri-1-bulunamadi-kilavuz": sk.kilavuz(bulunamadi, "fen-bilimleri", 1, None, acik),
        "matematik-1": sk.ders_ozeti(g, "matematik", 1),
        "matematik-1-kilavuz": sk.kilavuz(g, "matematik", 1, None, acik),
    }


def yaz(hedef: Path = HEDEF) -> list[Path]:
    hedef.mkdir(parents=True, exist_ok=True)
    yollar = []
    for ad, veri in fiksturler().items():
        yol = hedef / f"{ad}.json"
        yol.write_text(json.dumps(veri, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        yollar.append(yol)
    return yollar


if __name__ == "__main__":
    for y in yaz():
        print(y.relative_to(KOK))
```

`tests/test_hazirlik_fiksturleri.py`:

```python
"""Pano fikstürleri modelden üretilmiş hâliyle aynı olmalı (plan Görev 8): model ya da harita değişince bu test düşer
ve `scripts/hazirlik_fiksturleri.py` yeniden koşulur."""
import json

from scripts.hazirlik_fiksturleri import HEDEF, fiksturler


def test_pano_fiksturleri_guncel():
    beklenen = fiksturler()
    assert sorted(p.stem for p in HEDEF.glob("*.json")) == sorted(beklenen)
    for ad, veri in beklenen.items():
        assert json.loads((HEDEF / f"{ad}.json").read_text(encoding="utf-8")) == json.loads(json.dumps(veri)), ad
```

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-hazirligi
env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -I scripts/hazirlik_fiksturleri.py
env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_hazirlik_fiksturleri.py
```

Expected: 11 dosya yazılır; test PASS. `genel.json`'un `yaklasan`'ı `fen-bilimleri 1 kesin kalan_gun 9 soru 7 duyurulan_konu 3` ve `turkce 2 ulke_geneli kalan_gun 72`'dir.

- [ ] **Step 7: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-hazirligi
git log --oneline -3 && git status --short
git add src/hazirlik_isaretleri.py src/dashboard_api.py scripts/hazirlik_fiksturleri.py dashboard/tests/e2e/fixtures/hazirlik \
  tests/test_hazirlik_api.py tests/test_hazirlik_fiksturleri.py
git commit -m "$(cat <<'EOF'
feat(sinav-hazirligi): /api/hazirlik uçları, kişi başına hazırlık işaretleri ve modelden pano fikstürleri

Okuyucu default-deny ile reddedilir; API anahtarı okur ama işaret koyamaz; işaretler flock altında atomik
yazılır, bozuk dosya kenara alınır. E2e fikstürleri modelin kendisinden üretilir ve tazelik testiyle bağlıdır.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 9: Pano I — tipler, saf yardımcılar, durum göstergesi ve Sınav Hazırlığı ana sayfası

**Files:**
- Create: `dashboard/src/hazirlik/tipler.ts`, `dashboard/src/hazirlik/hazirlik.ts`, `dashboard/src/hazirlik/DurumGostergesi.tsx`, `dashboard/src/hazirlik/HazirlikSayfasi.tsx`, `dashboard/src/hazirlik/Hazirlik.scss`
- Modify: `dashboard/src/routes.ts` (rota), `dashboard/src/App.tsx` (`COMPONENTS`)
- Create: `dashboard/tests/e2e/_hazirlik.ts`
- Test: `dashboard/tests/hazirlik.test.ts`, `dashboard/tests/e2e/hazirlik-ana-sayfa.spec.ts`
- Modify (görsel taban): `dashboard/tests/e2e/gorsel-regresyon.spec.ts-snapshots/daha-fazla-telefon.png` (yeni "Sınav hazırlığı" satırı)

**Interfaces:**
- Consumes: Görev 6–8'in JSON biçimleri ve fikstürleri; `hooks/useApi`, `utils/apiHatasi.apiHataCumlesi(tur, ne)`, `utils/subject.subjectClass`, `components/patterns/IcBaglanti`.
- Produces: `tipler.ts` (`SinavDurumu`, `GenelBakis`, `KitapYolu`, `MatrisSatiri`, `Matris`, `DersOzeti`, `Baslik`, `Blok`, `KilavuzModeli`, `IsaretDurumu`, `PdfSecenekleri`); `hazirlik.ts` (`tarihMetni(iso, gunAdi?)`, `sayisalTarih`, `kalanGunMetni`, `sinavAdi`, `durumEtiketi`, `yaklasanAyrinti`, `soruMetni`, `sayfaMetni`, `kitapYoluMetni`, `kisaAmac`, `baslikMetni`, `BASLIK_TURU`, `ciktiKimligi`, `kilavuzAdresi`, `modelAdresi`, `pdfAdresi`, `baskiAdresi`, `VARSAYILAN_SECENEKLER`, `secenekAnahtari`, `secenekleriOku`, `secenekleriYaz`, `dersAnahtari`, `ebeveynCumleleri`); `DurumGostergesi`; rota `/hazirlik` (etiket "Sınav hazırlığı", `secondary`, `offPortal`, ikon `ExamMode`); e2e yardımcıları `fikstur`, `json`, `GENEL`, `DERS`, `KILAVUZ`, `PDF`, `hazirlikAc`, `erisilebilirlik`.
- Not: gezinme etiketi cümle düzenindedir ("Sınav hazırlığı", B41 kapısı rota etiketini görünür etiket sayar); sayfanın `<h2>`'si başlık düzenindedir ("Sınav Hazırlığı", S38).

- [ ] **Step 1: Başarısız birim testini yaz**

`dashboard/tests/hazirlik.test.ts`:

```ts
import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  baskiAdresi, baslikMetni, ciktiKimligi, dersAnahtari, durumEtiketi, ebeveynCumleleri, kalanGunMetni, kilavuzAdresi,
  kisaAmac, kitapYoluMetni, pdfAdresi, sayfaMetni, sayisalTarih, secenekleriOku, secenekleriYaz, soruMetni, tarihMetni,
  yaklasanAyrinti,
} from '../src/hazirlik/hazirlik.ts'
import type { KilavuzModeli, SinavDurumu } from '../src/hazirlik/tipler.ts'

const DURUM: SinavDurumu = {
  tur: 'kesin', senaryo: 2, senaryo_sayisi: 4, tarih: '2026-11-03', kalan_gun: 9, sinav_id: 'fen11',
  duyuru: 'Sınav 2. senaryoya göre uygulanacaktır.', uyari: null, anilan: [2], duyurulan_konu: 3,
}

test('durumEtiketi: dört durum; olası tek senaryo adı taşımaz (K8)', () => {
  assert.equal(durumEtiketi(DURUM), 'Kesin: 2. senaryo')
  const olasi = durumEtiketi({ ...DURUM, tur: 'olasi', senaryo: null })
  assert.equal(olasi, 'Olası: 4 senaryo')
  assert.doesNotMatch(olasi, /\d\. senaryo/)
  assert.equal(durumEtiketi({ ...DURUM, tur: 'ulke_geneli', senaryo: null, senaryo_sayisi: 0 }), 'Ülke geneli')
  assert.equal(durumEtiketi({ ...DURUM, tur: 'gecti', senaryo: 4 }), 'Geçti · 4. senaryoydu')
  assert.equal(durumEtiketi({ ...DURUM, tur: 'gecti', senaryo: null }), 'Geçti')
})

test('tarih, geri sayım ve yaklaşan satırı', () => {
  assert.equal(tarihMetni('2026-11-03'), '3 Kasım Salı')
  assert.equal(tarihMetni('2026-11-03', false), '3 Kasım')
  assert.equal(tarihMetni(null), 'tarih yok')
  assert.equal(sayisalTarih('2026-09-10T17:27'), '10.09.2026')
  assert.deepEqual([0, 1, 9, null].map(kalanGunMetni), ['bugün', 'yarın', '9 gün', null])
  assert.equal(yaklasanAyrinti(DURUM, 7), '3 Kasım Salı · 7 soru · 3 konu duyuruldu')
  assert.equal(yaklasanAyrinti({ ...DURUM, tur: 'ulke_geneli', tarih: '2027-01-05', duyurulan_konu: 0 }, null),
    '5 Ocak Salı · ülke geneli ortak sınav')
})

test('soruMetni: kesin tek sayı, olası aralık (K8)', () => {
  assert.equal(soruMetni({ soru: 3, aralik: null }), '3 soru')
  assert.equal(soruMetni({ soru: 0, aralik: null }), '0 soru')
  assert.equal(soruMetni({ soru: null, aralik: [0, 2] }), 'senaryoya göre 0–2 soru')
  assert.equal(soruMetni({ soru: null, aralik: [1, 1] }), 'her senaryoda 1 soru')
})

test('kitap yolu, sayfa, amaç ve başlık metni (K1, K6)', () => {
  const yol = { kitap: 'Fen Bilimleri 7 (1. Kitap)', unite: '2. Ünite', unite_no: 2, unite_ad: 'Kuvvet ve Enerjiyi Keşfedelim',
    cerceve: '1. Kuvvet, İş ve Enerji İlişkisi', cerceve_no: 1, konu: 'Fiziksel Anlamda İş', sayfa: 60, son_sayfa: 63, baglanti: 'x#page=61' }
  assert.equal(kitapYoluMetni(yol), 'Fen Bilimleri 7 (1. Kitap) › 2. Ünite › 1. Kuvvet, İş ve Enerji İlişkisi › Fiziksel Anlamda İş')
  assert.equal(kitapYoluMetni({ ...yol, konu: null }), 'Fen Bilimleri 7 (1. Kitap) › 2. Ünite › 1. Kuvvet, İş ve Enerji İlişkisi')
  assert.equal(sayfaMetni(60, 63), 's. 60–63')
  assert.equal(sayfaMetni(62, 62), 's. 62')
  const uzun = 'Fiziksel anlamda iş yapma durumuna göre günlük yaşam örneklerini değerlendirme ve tartışma'
  assert.equal(kisaAmac(uzun), 'Fiziksel anlamda iş yapma durumuna göre günlük yaşam örneklerini…')
  assert.equal(baslikMetni({ ad: 'Etkinlik Noktası-1', tur: 'etkinlik', amac: 'İşi tanımlama', sayfa: 60 }), 'Etkinlik Noktası-1 — İşi tanımlama')
  assert.equal(baslikMetni({ ad: 'Kontrol Noktası', tur: 'kontrol', amac: null, sayfa: 63 }), 'Kontrol Noktası')
  assert.equal(ciktiKimligi('FB.7.2.1'), 'cikti-FB-7-2-1')
})

test('adresler', () => {
  const s = { ebeveyn: true, isaret: false }
  assert.equal(kilavuzAdresi('fen-bilimleri', 1, 2), '/hazirlik/fen-bilimleri/1?senaryo=2')
  assert.equal(kilavuzAdresi('fen-bilimleri', 1, null), '/hazirlik/fen-bilimleri/1')
  assert.equal(pdfAdresi('fen-bilimleri', 1, 2, s), '/api/hazirlik/fen-bilimleri/1/kilavuz.pdf?senaryo=2&ebeveyn=1&isaret=0')
  assert.equal(baskiAdresi('fen-bilimleri', 1, null, s), '/baski.html?ebeveyn=1&isaret=0&ders=fen-bilimleri&sinav=1')
  assert.equal(dersAnahtari('Fen Bilimleri'), 'fen-bilimleri')
  assert.equal(dersAnahtari('Beden Eğitimi'), null)
  assert.equal(dersAnahtari(undefined), null)
})

test('PDF seçenekleri kişi başına hatırlanır; bozuk kayıt varsayılana düşer', () => {
  const depo = new Map<string, string>()
  const d = { getItem: (k: string) => depo.get(k) ?? null, setItem: (k: string, v: string) => { depo.set(k, v) } }
  assert.deepEqual(secenekleriOku('A@x.com', d), { ebeveyn: false, isaret: true })
  secenekleriYaz('A@x.com', { ebeveyn: true, isaret: false }, d)
  assert.deepEqual(secenekleriOku('a@x.com', d), { ebeveyn: true, isaret: false })
  assert.deepEqual(secenekleriOku('b@x.com', d), { ebeveyn: false, isaret: true })
  depo.set('tedy-hazirlik-pdf::c@x.com', '{bozuk')
  assert.deepEqual(secenekleriOku('c@x.com', d), { ebeveyn: false, isaret: true })
})

test('ebeveyn cümleleri', () => {
  const m = { ders: 'Fen Bilimleri', sinav_no: 1, durum: DURUM, kip: 'kesin', senaryo: 2,
    ebeveyn: { cikti_sayisi: 4, toplam_soru: 7, soru_araligi: null, hazirim: 1, tekrar: 1, isaretsiz: 2, en_agir: [] } } as unknown as KilavuzModeli
  assert.deepEqual(ebeveynCumleleri(m), ['Fen Bilimleri 1. yazılı: 3 Kasım Salı, 9 gün kaldı.', 'Okul 2. senaryoyu duyurdu.',
    '4 öğrenme çıktısı, toplam 7 soru.', 'Hazırlık işaretleri: 1 hazır, 1 tekrar, 2 işaretsiz.'])
  const olasi = { ...m, kip: 'olasi', durum: { ...DURUM, tarih: null, kalan_gun: null },
    ebeveyn: { ...m.ebeveyn!, toplam_soru: null, soru_araligi: [6, 9] } } as KilavuzModeli
  assert.deepEqual(ebeveynCumleleri(olasi).slice(0, 3), ['Fen Bilimleri 1. yazılı: tarihi henüz belli değil.',
    'Senaryo henüz duyurulmadı; kılavuz bütün senaryoları kapsar.', '4 öğrenme çıktısı; senaryoya göre 6–9 soru.'])
  assert.deepEqual(ebeveynCumleleri({ ...m, ebeveyn: null }), [])
})
```

- [ ] **Step 2: Testi koş, düştüğünü gör**

Run: `cd dashboard && node --test tests/hazirlik.test.ts`
Expected: FAIL — `Cannot find module '…/src/hazirlik/hazirlik.ts'`.

- [ ] **Step 3: Tipleri ve yardımcıları yaz**

`dashboard/src/hazirlik/tipler.ts`:

```ts
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

export interface Blok {
  kod: string
  kisa_ad: string
  metin: string
  senaryoda: boolean
  soru: number | null
  aralik: [number, number] | null
  her_senaryoda: boolean
  kitapta: KitapYolu[]
  kitap_durumu: KitapDurumu
  basliklar: Baslik[]
  okulda: { hafta: string }[]
  odevler: { baslik: string; teslim: string | null }[]
  moduller: { baslik: string; yol: string }[]
  isaret: IsaretDurumu
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
             tekrar: number; isaretsiz: number; en_agir: string[] } | null
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
```

`dashboard/src/hazirlik/hazirlik.ts` (tarih biçimleyicisi `Etc/UTC` kullanır: B70 kapısı tümü büyük "UTC" dizgesini reddeder; tarih bir yerel gündür, saat dilimi kaydırmaz):

```ts
// Sınav Hazırlığı yüzeylerinin saf yardımcıları (plan Görev 9): metinler, adresler, seçenek deposu.
// tests/hazirlik.test.ts sınar; ekran ve kâğıt (KilavuzBelgesi, K11) aynı yardımcıları kullanır.
import type { Baslik, Blok, KilavuzModeli, KitapYolu, PdfSecenekleri, SinavDurumu } from './tipler'

const GUNLU = new Intl.DateTimeFormat('tr-TR', { day: 'numeric', month: 'long', weekday: 'long', timeZone: 'Etc/UTC' })
const GUNSUZ = new Intl.DateTimeFormat('tr-TR', { day: 'numeric', month: 'long', timeZone: 'Etc/UTC' })
const SAYISAL = new Intl.DateTimeFormat('tr-TR', { day: '2-digit', month: '2-digit', year: 'numeric', timeZone: 'Etc/UTC' })

function utc(iso: string): Date {
  const [y, a, g] = iso.slice(0, 10).split('-').map(Number)
  return new Date(Date.UTC(y, a - 1, g))
}

/** "2026-11-03" → "3 Kasım Salı" (gün adıyla) ya da "3 Kasım"; tarih yoksa "tarih yok". Tarih yerel gündür. */
export function tarihMetni(iso: string | null, gunAdi = true): string {
  return iso ? (gunAdi ? GUNLU : GUNSUZ).format(utc(iso)) : 'tarih yok'
}

/** "2026-09-10T17:27" → "10.09.2026". */
export function sayisalTarih(iso: string | null): string {
  return iso ? SAYISAL.format(utc(iso)) : ''
}

export function kalanGunMetni(n: number | null): string | null {
  if (n === null) return null
  if (n === 0) return 'bugün'
  if (n === 1) return 'yarın'
  return `${n} gün`
}

export function sinavAdi(no: number): string {
  return `${no}. yazılı`
}

/** K4, K8: durumun sözü. Olası durum hiçbir zaman tek bir senaryoyu adlandırmaz. */
export function durumEtiketi(d: SinavDurumu): string {
  switch (d.tur) {
    case 'kesin': return `Kesin: ${d.senaryo}. senaryo`
    case 'olasi': return d.senaryo_sayisi > 0 ? `Olası: ${d.senaryo_sayisi} senaryo` : 'Olası'
    case 'ulke_geneli': return 'Ülke geneli'
    case 'gecti': return d.senaryo !== null ? `Geçti · ${d.senaryo}. senaryoydu` : 'Geçti'
  }
}

/** Yaklaşan yazılının ikinci satırı: "3 Kasım Salı · 7 soru · 3 konu duyuruldu". */
export function yaklasanAyrinti(d: SinavDurumu, soru: number | null): string {
  const p = [tarihMetni(d.tarih)]
  if (d.tur === 'ulke_geneli') p.push('ülke geneli ortak sınav')
  else if (soru !== null) p.push(`${soru} soru`)
  if (d.duyurulan_konu > 0) p.push(`${d.duyurulan_konu} konu duyuruldu`)
  return p.join(' · ')
}

/** K8: tek sayı yalnız senaryo belliyken; olası kipte senaryolar arası aralık. */
export function soruMetni(b: Pick<Blok, 'soru' | 'aralik'>): string {
  if (b.soru !== null) return `${b.soru} soru`
  const [a, z] = b.aralik ?? [0, 0]
  return a === z ? `her senaryoda ${a} soru` : `senaryoya göre ${a}–${z} soru`
}

export function sayfaMetni(a: number, b: number): string {
  return a === b ? `s. ${a}` : `s. ${a}–${b}`
}

/** K1: kitap › ünite › içerik çerçevesi › konu, kitaptaki adlarıyla. */
export function kitapYoluMetni(y: KitapYolu): string {
  return [y.kitap, y.unite, y.cerceve, ...(y.konu ? [y.konu] : [])].join(' › ')
}

const AMAC_SINIRI = 70

/** Etkinliğin amacı en çok 70 karakter, sözcük ortasında kesilmez (K6: başlığın kendisi kısaltılmaz). */
export function kisaAmac(amac: string): string {
  const t = amac.trim()
  if (t.length <= AMAC_SINIRI) return t
  const kes = t.slice(0, AMAC_SINIRI)
  const bosluk = kes.lastIndexOf(' ')
  return `${(bosluk > 0 ? kes.slice(0, bosluk) : kes).replace(/[,;:]$/, '')}…`
}

export function baslikMetni(b: Baslik): string {
  return b.amac ? `${b.ad} — ${kisaAmac(b.amac)}` : b.ad
}

export const BASLIK_TURU: Record<Baslik['tur'], string> = {
  etkinlik: 'Etkinlik', baglanti: 'Bağlantı', kontrol: 'Kontrol', tanim: 'Tanım', ozet: 'Özet', diger: 'Konu',
}

/** Bloğun çapası: "FB.7.2.1" → "cikti-FB-7-2-1". */
export function ciktiKimligi(kod: string): string {
  return `cikti-${kod.replace(/[^A-Za-z0-9]+/g, '-')}`
}

export function kilavuzAdresi(anahtar: string, no: number, senaryo: number | null): string {
  return `/hazirlik/${anahtar}/${no}${senaryo !== null ? `?senaryo=${senaryo}` : ''}`
}

function secenekSorgusu(senaryo: number | null, s: PdfSecenekleri): URLSearchParams {
  const q = new URLSearchParams()
  if (senaryo !== null) q.set('senaryo', String(senaryo))
  q.set('ebeveyn', s.ebeveyn ? '1' : '0')
  q.set('isaret', s.isaret ? '1' : '0')
  return q
}

export function modelAdresi(anahtar: string, no: number, senaryo: number | null, s: PdfSecenekleri): string {
  return `/api/hazirlik/${anahtar}/${no}/kilavuz?${secenekSorgusu(senaryo, s)}`
}

export function pdfAdresi(anahtar: string, no: number, senaryo: number | null, s: PdfSecenekleri): string {
  return `/api/hazirlik/${anahtar}/${no}/kilavuz.pdf?${secenekSorgusu(senaryo, s)}`
}

/** A4 önizleme (spec §3.3): baskı girişi, aynı seçeneklerle; oturum çereziyle modeli kendisi alır. */
export function baskiAdresi(anahtar: string, no: number, senaryo: number | null, s: PdfSecenekleri): string {
  const q = secenekSorgusu(senaryo, s)
  q.set('ders', anahtar)
  q.set('sinav', String(no))
  return `/baski.html?${q}`
}

export const VARSAYILAN_SECENEKLER: PdfSecenekleri = { ebeveyn: false, isaret: true }

export function secenekAnahtari(email: string): string {
  return `tedy-hazirlik-pdf::${email.toLowerCase()}`
}

/** Son seçim kişi başına hatırlanır (spec §4); bozuk ya da yoksa varsayılan. */
export function secenekleriOku(email: string, depo: Pick<Storage, 'getItem'>): PdfSecenekleri {
  try {
    const v: unknown = JSON.parse(depo.getItem(secenekAnahtari(email)) ?? 'null')
    if (v && typeof v === 'object') {
      const o = v as Record<string, unknown>
      return { ebeveyn: o.ebeveyn === true, isaret: o.isaret !== false }
    }
  } catch { /* bozuk kayıt varsayılana düşer */ }
  return { ...VARSAYILAN_SECENEKLER }
}

export function secenekleriYaz(email: string, s: PdfSecenekleri, depo: Pick<Storage, 'setItem'>): void {
  try { depo.setItem(secenekAnahtari(email), JSON.stringify(s)) } catch { /* depolama kapalı: yalnız bu oturum */ }
}

const ANAHTARLAR: Record<string, string> = {
  'Türkçe': 'turkce', 'Matematik': 'matematik', 'Fen Bilimleri': 'fen-bilimleri', 'Sosyal Bilgiler': 'sosyal-bilgiler',
  'İngilizce': 'ingilizce', 'Din Kültürü': 'din-kulturu',
}

/** Kanonik ders adı → hazırlık anahtarı (src/sinav_senaryo.DERS_ANAHTARLARI'nın eşi); bilinmeyen ad null. */
export function dersAnahtari(ders: string | null | undefined): string | null {
  return ders ? ANAHTARLAR[ders] ?? null : null
}

/** Ebeveyn özetinin cümleleri (spec §4.8): aileye, üçüncü kişiyle. */
export function ebeveynCumleleri(m: KilavuzModeli): string[] {
  const e = m.ebeveyn
  if (!e) return []
  const d = m.durum
  const zaman = d.tarih === null ? 'tarihi henüz belli değil'
    : `${tarihMetni(d.tarih)}${d.kalan_gun === 0 ? ', bugün' : d.kalan_gun !== null ? `, ${d.kalan_gun} gün kaldı` : ''}`
  const c = [`${m.ders} ${sinavAdi(m.sinav_no)}: ${zaman}.`]
  if (m.kip === 'kesin') c.push(`Okul ${m.senaryo}. senaryoyu duyurdu.`)
  else if (m.kip === 'ulke_geneli') c.push('Sınav ülke genelinde ortak yapılır; MEB senaryo vermedi.')
  else c.push('Senaryo henüz duyurulmadı; kılavuz bütün senaryoları kapsar.')
  if (e.toplam_soru !== null) c.push(`${e.cikti_sayisi} öğrenme çıktısı, toplam ${e.toplam_soru} soru.`)
  else if (e.soru_araligi) c.push(`${e.cikti_sayisi} öğrenme çıktısı; senaryoya göre ${e.soru_araligi[0]}–${e.soru_araligi[1]} soru.`)
  c.push(`Hazırlık işaretleri: ${e.hazirim} hazır, ${e.tekrar} tekrar, ${e.isaretsiz} işaretsiz.`)
  return c
}
```

- [ ] **Step 4: Birim testini koş, geçtiğini gör**

Run: `cd dashboard && node --test tests/hazirlik.test.ts`
Expected: PASS (7 test).

- [ ] **Step 5: Durum göstergesi, ana sayfa ve stil**

`dashboard/src/hazirlik/DurumGostergesi.tsx`:

```tsx
import { CheckmarkFilled, InformationFilled } from '@carbon/icons-react'
import { durumEtiketi } from './hazirlik'
import type { SinavDurumu } from './tipler'

/** Kanun K4, talimatname §5.7: ikon + metin (+ renk). Yeşil kesin, mavi olası; ülke geneli ve geçti eylem istemez,
 *  düz gri metin. Tag değil: Tag'in mavisi derslere ayrılmış (§4.4.2). Metin durumu söylediği için ikon gizlidir. */
export default function DurumGostergesi({ durum }: { durum: SinavDurumu }) {
  const metin = durumEtiketi(durum)
  if (durum.tur === 'kesin') {
    return <span className="hazirlik-durum hazirlik-durum--kesin"><CheckmarkFilled size={16} aria-hidden="true" className="hazirlik-durum__ikon" />{metin}</span>
  }
  if (durum.tur === 'olasi') {
    return <span className="hazirlik-durum hazirlik-durum--olasi"><InformationFilled size={16} aria-hidden="true" className="hazirlik-durum__ikon" />{metin}</span>
  }
  return <span className="hazirlik-durum hazirlik-durum--notr">{metin}</span>
}
```

`dashboard/src/hazirlik/HazirlikSayfasi.tsx`:

```tsx
import { ContainedList, ContainedListItem, InlineNotification, SkeletonText, Tile } from '@carbon/react'
import { useApi } from '../hooks/useApi'
import { apiHataCumlesi } from '../utils/apiHatasi'
import { subjectClass } from '../utils/subject'
import IcBaglanti from '../components/patterns/IcBaglanti'
import DurumGostergesi from './DurumGostergesi'
import { kalanGunMetni, sayisalTarih, sinavAdi, tarihMetni, yaklasanAyrinti } from './hazirlik'
import type { GenelBakis } from './tipler'
import './Hazirlik.scss'

/** Sınav Hazırlığı ana sayfası (spec §3.1, taslak A "önce zaman"): tarihi belli ortak yazılılar geri sayımla,
 *  sonra altı dersin karosu. */
export default function HazirlikSayfasi() {
  const { data, loading, iskelet, hataTuru } = useApi<GenelBakis | null>('/api/hazirlik', null)
  if (loading) {
    return iskelet ? <section className="hazirlik" aria-busy="true"><SkeletonText heading /><SkeletonText paragraph lineCount={4} /></section> : null
  }
  if (!data) {
    const h = apiHataCumlesi(hataTuru ?? 'sunucu', 'Sınav hazırlığı')
    return <section className="hazirlik"><InlineNotification kind="error" lowContrast hideCloseButton statusIconDescription="Hata" title={h.baslik} subtitle={h.ayrinti} /></section>
  }
  const k = data.kaynak
  return (
    <section className="hazirlik" aria-labelledby="hazirlik-baslik">
      <header>
        <h2 id="hazirlik-baslik" className="hazirlik__baslik">Sınav Hazırlığı</h2>
        {k && <p className="hazirlik__kaynak">{`MEB konu-soru dağılım tabloları · ${k.sinif}. sınıf · ${k.donem}. dönem (güncelleme ${sayisalTarih(k.meb_guncelleme)})`}</p>}
      </header>
      {data.durum === 'tablo_eski' && <InlineNotification kind="info" lowContrast hideCloseButton statusIconDescription="Bilgi" title="Yeni yılın tabloları bekleniyor." subtitle="MEB bu dönemin konu-soru dağılım tablolarını yayımlayınca burada görünür." />}
      {data.durum === 'tablo_yok' && <InlineNotification kind="error" lowContrast hideCloseButton statusIconDescription="Hata" title="MEB konu-soru dağılım tablosu okunamadı." subtitle="Sayfayı birkaç dakika sonra yeniden aç." />}
      {data.durum === 'hazir' && (
        <>
          {data.yaklasan.length > 0 && (
            <ContainedList kind="on-page" size="lg" label="Yaklaşan Ortak Yazılılar" className="hazirlik-yaklasan">
              {data.yaklasan.map(y => (
                <ContainedListItem key={`${y.anahtar}-${y.sinav_no}`} className={`hazirlik-yaklasan__oge ${subjectClass(y.ders)}`}>
                  <span className="hazirlik-yaklasan__ust">
                    <IcBaglanti href={`/hazirlik/${y.anahtar}?sinav=${y.sinav_no}`}>{`${y.ders} · ${sinavAdi(y.sinav_no)}`}</IcBaglanti>
                    <span className="hazirlik-yaklasan__kalan">{kalanGunMetni(y.durum.kalan_gun)}</span>
                  </span>
                  <span className="hazirlik-yaklasan__ayrinti">{yaklasanAyrinti(y.durum, y.soru)}</span>
                  <DurumGostergesi durum={y.durum} />
                </ContainedListItem>
              ))}
            </ContainedList>
          )}
          <section aria-labelledby="hazirlik-dersler">
            <h3 id="hazirlik-dersler" className="hazirlik__bolum-baslik">Dersler</h3>
            <ul className="hazirlik-dersler">
              {data.dersler.map(d => (
                <li key={d.anahtar}>
                  <Tile className={`hazirlik-karo ${subjectClass(d.ders)}`}>
                    <IcBaglanti href={`/hazirlik/${d.anahtar}`}>{d.ders}</IcBaglanti>
                    {d.sinavlar.map(s => (
                      <span key={s.sinav_no} className="hazirlik-karo__sinav">
                        <span>{`${sinavAdi(s.sinav_no)} · ${s.durum.tur === 'gecti' ? 'geçti' : tarihMetni(s.durum.tarih, false)}`}</span>
                        <DurumGostergesi durum={s.durum} />
                      </span>
                    ))}
                  </Tile>
                </li>
              ))}
            </ul>
          </section>
        </>
      )}
    </section>
  )
}
```

`dashboard/src/hazirlik/Hazirlik.scss`:

```scss
// Sınav Hazırlığı yüzeyleri (plan Görev 9–11). Yalnız Carbon belirteçleri; ders rengi yalnız vurgu (Kanun K4).
@use '@carbon/react/scss/spacing' as spacing;
@use '@carbon/react/scss/type' as type;
@use '@carbon/react/scss/breakpoint' as bp;

.hazirlik {
  display: flex;
  flex-direction: column;
  gap: spacing.$spacing-07;
}

.hazirlik__baslik { @include type.type-style('heading-04'); }

.hazirlik__kaynak {
  @include type.type-style('helper-text-01');
  color: var(--cds-text-secondary);
  margin-block-start: spacing.$spacing-02;
}

.hazirlik__bolum-baslik {
  @include type.type-style('heading-03');
  margin-block-end: spacing.$spacing-04;
}

.hazirlik-durum {
  display: inline-flex;
  align-items: center;
  gap: spacing.$spacing-02;
  @include type.type-style('label-01');
}

.hazirlik-durum__ikon { flex: none; }
.hazirlik-durum--kesin .hazirlik-durum__ikon { fill: var(--cds-support-success); }
.hazirlik-durum--olasi .hazirlik-durum__ikon { fill: var(--cds-support-info); }
.hazirlik-durum--notr { color: var(--cds-text-secondary); }

.hazirlik-yaklasan__oge .cds--contained-list-item__content {
  display: flex;
  flex-direction: column;
  gap: spacing.$spacing-02;
}

.hazirlik-yaklasan__ust {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: spacing.$spacing-03;
}

.hazirlik-yaklasan__kalan {
  @include type.type-style('heading-03');
  font-variant-numeric: tabular-nums;
}

.hazirlik-yaklasan__ayrinti {
  @include type.type-style('body-compact-01');
  color: var(--cds-text-secondary);
}

.hazirlik-dersler {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: spacing.$spacing-05;
}

@include bp.breakpoint('md') {
  .hazirlik-dersler { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}

.hazirlik-karo {
  display: flex;
  flex-direction: column;
  gap: spacing.$spacing-03;
  block-size: 100%;
  border-block-start: spacing.$spacing-02 solid var(--ted-subject-accent);
}

.hazirlik-karo__sinav {
  display: flex;
  flex-direction: column;
  gap: spacing.$spacing-01;
  @include type.type-style('body-compact-01');
}
```

- [ ] **Step 6: Rotayı ve bileşeni bağla**

`dashboard/src/routes.ts`'te Modüller satırının altına:

```ts
  // Sınav Hazırlığı (spec 2026-10-25 §3): MEB senaryoları, ders sayfası, kapsam kılavuzu. Portal kapalıyken de açılır.
  { path: '/hazirlik', label: 'Sınav hazırlığı', icon: ExamMode, componentName: 'HazirlikSayfasi', secondary: true, offPortal: true },
```

`dashboard/src/App.tsx`'te `import DahaFazla from './components/DahaFazla'` satırının altına `import HazirlikSayfasi from './hazirlik/HazirlikSayfasi'`; `COMPONENTS` sözlüğünde `DahaFazla,` satırının altına `HazirlikSayfasi,`.

- [ ] **Step 7: E2e yardımcısını ve ana sayfa e2e'sini yaz**

`dashboard/tests/e2e/_hazirlik.ts`:

```ts
// Sınav Hazırlığı e2e yardımcıları (plan Görev 9–14). Fikstürler modelden üretilir (scripts/hazirlik_fiksturleri.py).
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import AxeBuilder from '@axe-core/playwright'
import type { Page } from '@playwright/test'
import { mock, LIVE } from './_audit-fixtures'

export function fikstur<T = Record<string, unknown>>(ad: string): T {
  return JSON.parse(readFileSync(new URL(`./fixtures/hazirlik/${ad}.json`, import.meta.url), 'utf8')) as T
}

export const json = (veri: unknown, status = 200) => ({ status, contentType: 'application/json', body: JSON.stringify(veri) })

export const GENEL = /\/api\/hazirlik$/
export const DERS = (anahtar: string, no: number) => new RegExp(`/api/hazirlik/${anahtar}/${no}$`)
export const KILAVUZ = (anahtar: string, no: number) => new RegExp(`/api/hazirlik/${anahtar}/${no}/kilavuz(\\?.*)?$`)
export const PDF = (anahtar: string, no: number) => new RegExp(`/api/hazirlik/${anahtar}/${no}/kilavuz\\.pdf(\\?.*)?$`)

/** LIVE taklidi + verilen hazırlık uçları; sonra sayfayı açar. */
export async function hazirlikAc(page: Page, yol: string, rotalar: [RegExp, unknown][]) {
  await mock(page, LIVE)
  for (const [desen, govde] of rotalar) await page.route(desen, r => r.fulfill(json(govde)))
  await page.goto(yol)
}

const ACE = createRequire(import.meta.url).resolve('accessibility-checker-engine/ace.js')

/** axe (WCAG 2.2 AA + best practice) ve IBM Equal Access ihlalleri (Kanun K10); ikisi de boş olmalı. */
export async function erisilebilirlik(page: Page, secici: string): Promise<{ axe: string[]; ibm: string[] }> {
  const axe = await new AxeBuilder({ page }).include(secici)
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa', 'best-practice']).analyze()
  await page.addScriptTag({ path: ACE })
  const ibm = await page.evaluate(async s => {
    // @ts-expect-error — `ace` is the injected engine's global
    const rapor = await new window.ace.Checker().check(document.querySelector(s), ['IBM_Accessibility'])
    return rapor.results.filter((r: { value: string[] }) => r.value[0] === 'VIOLATION' && r.value[1] === 'FAIL')
      .map((r: { ruleId: string }) => r.ruleId)
  }, secici)
  return { axe: axe.violations.map(v => v.id), ibm }
}
```

`dashboard/tests/e2e/hazirlik-ana-sayfa.spec.ts`:

```ts
import { test, expect } from '@playwright/test'
import { GENEL, erisilebilirlik, fikstur, hazirlikAc } from './_hazirlik'

test.use({ timezoneId: 'Europe/Istanbul', locale: 'tr-TR' })

test('ana sayfa: önce zaman, sonra altı ders (spec §3.1, taslak A)', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik', [[GENEL, fikstur('genel')]])
  await expect(page.getByRole('heading', { name: 'Sınav Hazırlığı', level: 2 })).toBeVisible()
  await expect(page.locator('.hazirlik__kaynak')).toHaveText('MEB konu-soru dağılım tabloları · 7. sınıf · 1. dönem (güncelleme 10.09.2026)')
  const yaklasan = page.locator('.hazirlik-yaklasan__oge')
  await expect(yaklasan).toHaveCount(2)
  await expect(yaklasan.nth(0)).toContainText('Fen Bilimleri · 1. yazılı')
  await expect(yaklasan.nth(0)).toContainText('9 gün')
  await expect(yaklasan.nth(0)).toContainText('3 Kasım Salı · 7 soru · 3 konu duyuruldu')
  await expect(yaklasan.nth(0)).toContainText('Kesin: 2. senaryo')
  await expect(yaklasan.nth(1)).toContainText('Türkçe · 2. yazılı')
  await expect(yaklasan.nth(1)).toContainText('72 gün')
  await expect(yaklasan.nth(1)).toContainText('5 Ocak Salı · ülke geneli ortak sınav')
  const karolar = page.locator('.hazirlik-karo')
  await expect(karolar).toHaveCount(6)
  const tr = karolar.filter({ hasText: 'Türkçe' })
  await expect(tr).toContainText('1. yazılı · geçti')
  await expect(tr).toContainText('Geçti · 4. senaryoydu')
  await expect(tr).toContainText('2. yazılı · 5 Ocak')
  const mat = karolar.filter({ hasText: 'Matematik' })
  await expect(mat).toContainText('1. yazılı · tarih yok')
  await expect(mat).toContainText('Olası: 4 senaryo')
  // K4: kesin yeşil ikon, olası mavi ikon; ülke geneli ve geçti ikonsuz düz metin.
  await expect(yaklasan.nth(0).locator('.hazirlik-durum--kesin svg')).toHaveCount(1)
  await expect(yaklasan.nth(1).locator('.hazirlik-durum--notr svg')).toHaveCount(0)
  expect(await erisilebilirlik(page, '.hazirlik')).toEqual({ axe: [], ibm: [] })
})

test('ana sayfa: klavyeyle ders sayfasına geçilir; gezinmede "Sınav hazırlığı" var', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik', [[GENEL, fikstur('genel')]])
  const bag = page.locator('.hazirlik-yaklasan__oge').first().getByRole('link', { name: 'Fen Bilimleri · 1. yazılı' })
  await bag.focus()
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/\/hazirlik\/fen-bilimleri\?sinav=1$/)
  await page.goto('/daha-fazla')
  await expect(page.locator('section.daha-fazla').getByRole('link', { name: 'Sınav hazırlığı' })).toHaveAttribute('href', '/hazirlik')
})

test('ana sayfa: yeni yılın tabloları bekleniyor', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik', [[GENEL, { ...fikstur('genel'), durum: 'tablo_eski', yaklasan: [], dersler: [] }]])
  await expect(page.getByText('Yeni yılın tabloları bekleniyor.')).toBeVisible()
  await expect(page.locator('.hazirlik-karo')).toHaveCount(0)
})
```

- [ ] **Step 8: Kapıları koş; görsel tabanın tek değişikliğini oku ve güncelle**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-hazirligi/dashboard
npm run lint; echo "lint: $?"
npm run test:birim; echo "birim: $?"
npm run build; echo "build: $?"
TEDY_E2E_PORT=8341 TEDY_E2E_PYTHON=/mnt/thunderbolt/workspaces/TED/.venv/bin/python env -u ANTHROPIC_API_KEY npx playwright test --project= hazirlik-ana-sayfa alt-gezinme dersler tasarim-denetimi ibm-erisilebilirlik aria-yapisi gorsel-regresyon ekran-4k suite-hygiene
```

Expected: lint/birim/build 0; `hazirlik-ana-sayfa` 3 test PASS; eski süitlerde yalnız `gorsel-regresyon › daha-fazla looks as it did (telefon)` düşer (plan yazılırken ölçüldü; `aria-yapisi` geçer: "Daha fazla" menüsü kapalıdır). Farkın yalnız yeni "Sınav hazırlığı" satırı olduğunu `test-results/…/daha-fazla-…-diff.png`'de gördükten sonra:

```bash
TEDY_E2E_PORT=8341 TEDY_E2E_PYTHON=/mnt/thunderbolt/workspaces/TED/.venv/bin/python env -u ANTHROPIC_API_KEY npx playwright test --project= gorsel-regresyon -g "daha-fazla" --update-snapshots
git status --short dashboard/tests/e2e/gorsel-regresyon.spec.ts-snapshots
```

- [ ] **Step 9: Python tasarım kapıları**

Run: `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-hazirligi && env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pano_tasarim_sistemi.py tests/test_pano_talimatname_borclari.py`
Expected: PASS (58 test; S38/B41/B70/B44 kapıları yeni dosyaları da tarar).

- [ ] **Step 10: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-hazirligi
git log --oneline -3 && git status --short
git add dashboard/src/hazirlik dashboard/src/routes.ts dashboard/src/App.tsx dashboard/tests/hazirlik.test.ts \
  dashboard/tests/e2e/_hazirlik.ts dashboard/tests/e2e/hazirlik-ana-sayfa.spec.ts dashboard/tests/e2e/gorsel-regresyon.spec.ts-snapshots/daha-fazla-telefon.png
git commit -m "$(cat <<'EOF'
feat(sinav-hazirligi): Sınav Hazırlığı ana sayfası — önce zaman, sonra altı ders

Yaklaşan ortak yazılılar geri sayım, soru ve duyurulan konu sayısıyla; durum ikon + metin (yeşil kesin, mavi
olası, gri ülke geneli/geçti; Tag değil). "Daha fazla" altında "Sınav hazırlığı"; daha-fazla telefon tabanı
bu satır için güncellendi.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 10: Pano II — ders sayfası, karşılaştırma tablosu, satır ayrıntısı, ortak belge yardımcıları

**Files:**
- Create: `dashboard/src/hazirlik/belge.ts`, `dashboard/src/hazirlik/Uyarilar.tsx`, `dashboard/src/hazirlik/KarsilastirmaTablosu.tsx`, `dashboard/src/hazirlik/Matris.scss`, `dashboard/src/hazirlik/CiktiAyrintisi.tsx`, `dashboard/src/hazirlik/HazirlikDersSayfasi.tsx`
- Modify: `dashboard/src/hazirlik/Hazirlik.scss` (sona ekleme), `dashboard/src/routes.ts`, `dashboard/src/App.tsx`
- Test: `dashboard/tests/hazirlik-belge.test.ts`, `dashboard/tests/e2e/hazirlik-ders.spec.ts`

**Interfaces:**
- Consumes: Görev 9'un tipleri, yardımcıları, `DurumGostergesi`, e2e yardımcıları; `components/Kaydirilabilir`; fikstürler `fen-bilimleri-1`, `fen-bilimleri-2`, `fen-bilimleri-1-olasi`, `matematik-1`, `fen-bilimleri-1-kilavuz`, `fen-bilimleri-1-kilavuz-ebeveyn`, `fen-bilimleri-1-olasi-kilavuz`, `matematik-1-kilavuz`.
- Produces: `belge.ts` (`BOLUM`, `bolumler(m) -> {id, ad}[]`, `ustBilgi(m)`, `damgaMetni(m)` — "TEDY · …" ile başlar, PDF kapıları alt bilgiyi buradan tanır —, `tumBloklar(m)`, `hazirlikUyarilari(g) -> string[]`); `Uyarilar({metinler, kip})`; `KarsilastirmaTablosu({matris, vurgu, kip, secili?, sec?, vurguEtiketi?})` (Görev 11–13 kılavuzda kâğıt kipinde kullanır); `CiktiAyrintisi({satir, kilavuz, kapat})`; rota `/hazirlik/:ders?sinav=1|2`.
- Ölçülmüş tuzaklar: Carbon ghost düğmesinin mavisi tablo hücresinde AA kontrastı tutmadı (axe `color-contrast`) → satır düğmesi yerel `<button>`; grup satırı `th colgroup` olunca IBM `table_headers_related` verdi → grup hücresi `td`; Carbon `Tabs` panelsiz `aria-controls` üretir → yazılı seçici `ContentSwitcher`.

- [ ] **Step 1: Başarısız testleri yaz**

`dashboard/tests/hazirlik-belge.test.ts` (fikstür modelden üretilmiştir; `belge.ts` çalışma anında `./hazirlik.ts` uzantısıyla içe aktarır, `node --test` uzantısız yolu çözmez):

```ts
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { bolumler, damgaMetni, tumBloklar, ustBilgi } from '../src/hazirlik/belge.ts'
import type { KilavuzModeli } from '../src/hazirlik/tipler.ts'

// Fikstür modelden üretilmiştir (scripts/hazirlik_fiksturleri.py): şekil varsayılmaz.
const oku = (ad: string): KilavuzModeli =>
  JSON.parse(readFileSync(new URL(`./e2e/fixtures/hazirlik/${ad}.json`, import.meta.url), 'utf8'))
const KESIN = oku('fen-bilimleri-1-kilavuz')
const OLASI = oku('fen-bilimleri-1-olasi-kilavuz')

test('bölümler sırası: özet, karşılaştırma, üniteler, doğrulama, plan, kaynaklar; ebeveyn başa', () => {
  assert.deepEqual(bolumler(KESIN).map(b => b.ad), ['Özet', 'Senaryo Karşılaştırması', '1. Ünite · Uzay Çağı',
    '2. Ünite · Kuvvet ve Enerjiyi Keşfedelim', 'Duyuru Doğrulaması', 'Çalışma Planı', 'Kaynaklar'])
  assert.equal(bolumler(oku('fen-bilimleri-1-kilavuz-ebeveyn'))[0].ad, 'Ebeveyn Özeti')
  assert.deepEqual(bolumler(KESIN).map(b => b.id).slice(0, 3), ['bolum-ozet', 'bolum-karsilastirma', 'bolum-unite-1'])
})

test('üst bilgi: olası kipte tek senaryo "bu" diye yazılmaz (K8)', () => {
  assert.equal(ustBilgi(KESIN), 'Fen Bilimleri · 1. yazılı · 2. senaryo')
  assert.equal(ustBilgi(OLASI), 'Fen Bilimleri · 1. yazılı · bütün senaryolar (olası)')
  assert.equal(ustBilgi({ ...OLASI, senaryo: 3 }), 'Fen Bilimleri · 1. yazılı · 3. senaryo (olası)')
})

test('damga TEDY ile başlar, tablo ve kitap sürümünü taşır (K12)', () => {
  const d = damgaMetni(KESIN)
  assert.match(d, /^TEDY · MEB tablosu 10\.09\.2026 · Fen Bilimleri 7 \(1\. Kitap\) 2026-2027 \([0-9a-f]{12}\) · üretim 25\.10\.2026$/)
  assert.match(damgaMetni(oku('matematik-1-kilavuz')), /kitap haritası yok/)
})

test('olası fikstürde hiçbir blok tek soru sayısı taşımaz (K8)', () => {
  assert.ok(tumBloklar(OLASI).length > 0)
  assert.ok(tumBloklar(OLASI).every(b => b.soru === null && b.aralik !== null))
  assert.deepEqual(tumBloklar(null), [])
})
```

`dashboard/tests/e2e/hazirlik-ders.spec.ts`:

```ts
import { test, expect } from '@playwright/test'
import { DERS, erisilebilirlik, fikstur, hazirlikAc } from './_hazirlik'

test.use({ timezoneId: 'Europe/Istanbul', locale: 'tr-TR' })

test('ders sayfası: duyuru aynen, karşılaştırma tablosu, duyurulan sütun, toplam', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik/fen-bilimleri?sinav=1', [[DERS('fen-bilimleri', 1), fikstur('fen-bilimleri-1')]])
  await expect(page.getByRole('heading', { name: 'Fen Bilimleri', level: 2 })).toBeVisible()
  await expect(page.getByText('Okul 2. senaryoyu duyurdu.')).toBeVisible()
  await expect(page.getByText('«Sınav, İstanbul İl MEB tarafından belirlenen 2. senaryoya göre uygulanacaktır.»')).toBeVisible()
  const tablo = page.locator('table.kilavuz-matris')
  await expect(tablo.getByRole('columnheader', { name: 'S2 · duyurulan' })).toBeVisible()
  await expect(tablo.locator('.kilavuz-matris__grup')).toHaveText(['1. Ünite · Uzay Çağı', '2. Ünite · Kuvvet ve Enerjiyi Keşfedelim'])
  await expect(tablo.locator('.kilavuz-matris__toplam td')).toHaveText(['9', '7', '8', '6'])
  const is_ = tablo.getByRole('row').filter({ hasText: 'FB.7.2.1' })
  await expect(is_).toContainText('Fiziksel Anlamda İş')
  await expect(is_).toContainText('her senaryoda')
  await expect(page.getByRole('button', { name: 'Kapsam kılavuzunu aç (2. senaryo)' })).toBeVisible()
  expect(await erisilebilirlik(page, '.hazirlik-ders')).toEqual({ axe: [], ibm: [] })
})

test('satır ayrıntısı: tam MEB metni ve kitap bölümü; Esc kapatır, odak satıra döner', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik/fen-bilimleri?sinav=1', [[DERS('fen-bilimleri', 1), fikstur('fen-bilimleri-1')]])
  const dugme = page.getByRole('button', { name: /FB\.7\.2\.1 Fiziksel Anlamda İş/ })
  await dugme.click()
  const panel = page.locator('aside.cikti-ayrinti')
  await expect(panel.getByRole('heading', { level: 3 })).toBeFocused()
  await expect(panel).toContainText('MEB: “Fiziksel anlamda yapılan işin bağlı olduğu faktörlere ilişkin bilimsel çıkarım yapabilme”')
  const kitap = panel.getByRole('link', { name: /Fen Bilimleri 7 \(1\. Kitap\) › 2\. Ünite › 1\. Kuvvet, İş ve Enerji İlişkisi › Fiziksel Anlamda İş/ })
  await expect(kitap).toHaveAttribute('href', /#page=61$/)
  await expect(panel).toContainText('s. 60–63')
  await expect(panel.getByRole('link', { name: 'Kılavuzda aç' })).toHaveAttribute('href', '/hazirlik/fen-bilimleri/1#cikti-FB-7-2-1')
  await page.keyboard.press('Escape')
  await expect(panel).toHaveCount(0)
  await expect(dugme).toBeFocused()
})

test('olası kip: senaryo seçilebilir, kılavuz o senaryoyla ve "olası" diye açılır (K8)', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik/fen-bilimleri?sinav=1', [[DERS('fen-bilimleri', 1), fikstur('fen-bilimleri-1-olasi')]])
  await expect(page.getByText('Senaryo duyurulmadı.')).toBeVisible()
  await expect(page.getByText('Olası: 4 senaryo')).toBeVisible()
  await expect(page.getByRole('columnheader', { name: /duyurulan/ })).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Kapsam kılavuzunu aç (bütün senaryolar)' })).toBeVisible()
  await page.getByText('3. senaryo', { exact: true }).click()
  await expect(page.getByRole('columnheader', { name: 'S3 · seçilen' })).toBeVisible()
  await page.getByRole('button', { name: 'Kapsam kılavuzunu aç (3. senaryo, olası)' }).click()
  await expect(page).toHaveURL(/\/hazirlik\/fen-bilimleri\/1\?senaryo=3$/)
})

test('yazılı seçici 2. yazılıyı yükler; haritasız ders "kitap bölümleri henüz eklenmedi" (spec §7)', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik/fen-bilimleri?sinav=1', [[DERS('fen-bilimleri', 1), fikstur('fen-bilimleri-1')],
    [DERS('fen-bilimleri', 2), fikstur('fen-bilimleri-2')], [DERS('matematik', 1), fikstur('matematik-1')]])
  await page.getByRole('tab', { name: '2. yazılı · tarih yok' }).click()
  await expect(page).toHaveURL(/sinav=2$/)
  // 2. yazılıda FB.7.1.3 yalnız 4. senaryoda var: üç ünite grubu.
  await expect(page.locator('.kilavuz-matris__grup')).toHaveText(['1. Ünite · Uzay Çağı', '2. Ünite · Kuvvet ve Enerjiyi Keşfedelim',
    '3. Ünite · Vücudumuzdaki Sistemler'])
  await page.goto('/hazirlik/matematik')
  await expect(page.getByText('Kitap bölümleri henüz eklenmedi; bu dersin MEB metinleri ve senaryoları burada.')).toBeVisible()
  await page.getByRole('button', { name: /MAT\.7\.1\.1/ }).click()
  await expect(page.locator('aside.cikti-ayrinti')).toContainText('Kitap bölümleri henüz eklenmedi.')
})
```

- [ ] **Step 2: Birim testini koş, düştüğünü gör**

Run: `cd dashboard && node --test tests/hazirlik-belge.test.ts`
Expected: FAIL — `Cannot find module '…/src/hazirlik/belge.ts'`.

- [ ] **Step 3: Belge yardımcılarını ve uyarıları yaz**

`dashboard/src/hazirlik/belge.ts`:

```ts
// Kılavuz belgesinin saf yardımcıları (plan Görev 11): bölümler, üst bilgi, damga. Ekran ve kâğıt aynı metni kullanır (K11).
import { sayisalTarih, sinavAdi } from './hazirlik.ts'
import type { Guncellik, KilavuzModeli } from './tipler.ts'

/** Adlandıran bölüm başlıkları (talimatname S38: başlık düzeninde). İçindekiler ve yan menü aynı adları taşır. */
export const BOLUM = {
  kilavuz: 'Kapsam Kılavuzu', ozet: 'Özet', icindekiler: 'İçindekiler', karsilastirma: 'Senaryo Karşılaştırması',
  dogrulama: 'Duyuru Doğrulaması', plan: 'Çalışma Planı', ebeveyn: 'Ebeveyn Özeti', kaynaklar: 'Kaynaklar',
} as const

/** Kılavuzun bölümleri, sırasıyla (spec §4): çapa kimliği ve adı. */
export function bolumler(m: KilavuzModeli): { id: string; ad: string }[] {
  return [
    ...(m.ebeveyn ? [{ id: 'bolum-ebeveyn', ad: BOLUM.ebeveyn }] : []),
    { id: 'bolum-ozet', ad: BOLUM.ozet },
    ...(m.matris.senaryolar.length ? [{ id: 'bolum-karsilastirma', ad: BOLUM.karsilastirma }] : []),
    ...m.uniteler.map((u, i) => ({ id: `bolum-unite-${i + 1}`, ad: u.baslik })),
    ...(m.dogrulama ? [{ id: 'bolum-dogrulama', ad: BOLUM.dogrulama }] : []),
    ...(m.plan ? [{ id: 'bolum-plan', ad: BOLUM.plan }] : []),
    { id: 'bolum-kaynaklar', ad: BOLUM.kaynaklar },
  ]
}

/** Üst bilgi (K5): ders · sınav · senaryo. Olası kipte tek senaryo "bu" diye yazılmaz (K8). */
export function ustBilgi(m: KilavuzModeli): string {
  const senaryo = m.kip === 'ulke_geneli' ? 'ülke geneli'
    : m.kip === 'kesin' ? `${m.senaryo}. senaryo`
    : m.senaryo !== null ? `${m.senaryo}. senaryo (olası)` : 'bütün senaryolar (olası)'
  return `${m.ders} · ${sinavAdi(m.sinav_no)} · ${senaryo}`
}

/** Damga (K12): her sayfanın alt bilgisi; "TEDY" ile başlar (PDF kapıları alt bilgiyi buradan tanır). */
export function damgaMetni(m: KilavuzModeli): string {
  const kitap = m.damgalar.kitaplar.map(k => `${k.baslik} ${k.baski} (${k.sha256_kisa})`).join(', ') || 'kitap haritası yok'
  return `TEDY · MEB tablosu ${sayisalTarih(m.damgalar.meb_guncelleme)} · ${kitap} · üretim ${sayisalTarih(m.damgalar.uretim)}`
}

export function tumBloklar(m: KilavuzModeli | null) {
  return m ? m.uniteler.flatMap(u => u.cerceveler.flatMap(c => c.bloklar)) : []
}

/** Kâğıtla ekranın ortak uyarıları (K12 güncellik, K1 onay, spec §7 harita yok). */
export function hazirlikUyarilari(g: { guncellik: Guncellik; harita_onayli: boolean; kitap_bolumleri: boolean }): string[] {
  const out: string[] = []
  if (!g.kitap_bolumleri) out.push('Kitap bölümleri henüz eklenmedi; bu dersin MEB metinleri ve senaryoları burada.')
  if (g.guncellik.kitap_degisti) out.push('MEB ders kitabının PDF’i değişti; kitap bölümleri güncel değil, harita yenilenmeli.')
  if (g.guncellik.tablo_degisti) out.push('MEB tablosu kitap haritasından sonra değişti; kitap bölümleri güncel değil, harita yenilenmeli.')
  if (g.kitap_bolumleri && !g.harita_onayli) out.push('Kitap haritası henüz elle onaylanmadı.')
  return out
}
```

`dashboard/src/hazirlik/Uyarilar.tsx`:

```tsx
import { InlineNotification } from '@carbon/react'

/** Uyarı satırları (metinler `belge.hazirlikUyarilari`'ndan): ekranda InlineNotification, kâğıtta çerçeveli paragraf (K11). */
export default function Uyarilar({ metinler, kip }: { metinler: string[]; kip: 'ekran' | 'baski' }) {
  if (metinler.length === 0) return null
  if (kip === 'baski') return <>{metinler.map(m => <p key={m} className="kilavuz-uyari">{m}</p>)}</>
  return (
    <>
      {metinler.map(m => (
        <InlineNotification key={m} kind={m.startsWith('Kitap bölümleri henüz') ? 'info' : 'warning'} lowContrast
          hideCloseButton statusIconDescription={m.startsWith('Kitap bölümleri henüz') ? 'Bilgi' : 'Uyarı'} title={m} />
      ))}
    </>
  )
}
```

- [ ] **Step 4: Birim testini koş, geçtiğini gör**

Run: `cd dashboard && node --test tests/hazirlik-belge.test.ts tests/hazirlik.test.ts`
Expected: PASS (4 + 7 test).

- [ ] **Step 5: Tablo, ayrıntı ve ders sayfası**

`dashboard/src/hazirlik/KarsilastirmaTablosu.tsx`:

```tsx
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow, Tag } from '@carbon/react'
import type { Matris } from './tipler'
import './Matris.scss'

/** Senaryo karşılaştırması (spec §3.2, taslak A): satırlar ünite gruplu çıktılar, sütunlar senaryolar; vurgulanan
 *  sütun duyurulan (ya da seçilen) senaryodur; sıfır "–"; toplam satırı. Ekranda satırın çıktısı bir düğmedir
 *  (ayrıntı paneli), kâğıtta düz metin (K11). Aynı bileşen kılavuzun içinde de kullanılır. */
export default function KarsilastirmaTablosu({ matris, vurgu, kip, secili, sec, vurguEtiketi = 'duyurulan' }: {
  matris: Matris
  vurgu: number | null
  kip: 'ekran' | 'baski'
  secili?: string | null
  sec?: (kod: string, dugme: HTMLButtonElement) => void
  vurguEtiketi?: string
}) {
  const sutun = (n: number) => (n === vurgu ? 'kilavuz-matris__vurgu' : undefined)
  return (
    <Table size="md" className="kilavuz-matris" aria-label="Senaryo karşılaştırması">
      <TableHead>
        <TableRow>
          <TableHeader scope="col">Öğrenme çıktısı</TableHeader>
          {matris.senaryolar.map(n => (
            <TableHeader key={n} scope="col" className={sutun(n)}>{n === vurgu ? `S${n} · ${vurguEtiketi}` : `S${n}`}</TableHeader>
          ))}
        </TableRow>
      </TableHead>
      <TableBody>
        {matris.gruplar.map(g => [
          <TableRow key={g.baslik} className="kilavuz-matris__grup">
            {/* Grup satırı başlık hücresi değil: th colgroup tabloyu "karmaşık" yapar, IBM her hücre için headers ister. */}
            <TableCell colSpan={matris.senaryolar.length + 1}>{g.baslik}</TableCell>
          </TableRow>,
          ...g.satirlar.map(s => (
            <TableRow key={s.kod} className={s.kod === secili ? 'kilavuz-matris__secili' : undefined}>
              <th scope="row" className="kilavuz-matris__cikti">
                {kip === 'ekran' && sec ? (
                  // Yerel düğme: Carbon ghost düğmesinin mavisi tablo hücresinin zemininde AA kontrastı tutmuyor (ölçüldü, axe).
                  <button type="button" className="kilavuz-matris__dugme" aria-expanded={s.kod === secili}
                    onClick={e => sec(s.kod, e.currentTarget)}>
                    <span className="kilavuz-kod">{s.kod}</span> {s.kisa_ad}
                  </button>
                ) : (
                  <span><span className="kilavuz-kod">{s.kod}</span> {s.kisa_ad}</span>
                )}
                {s.her_senaryoda && <Tag type="gray" size="sm" className="kilavuz-matris__her">her senaryoda</Tag>}
              </th>
              {matris.senaryolar.map(n => {
                const sayi = s.sayilar[String(n)] ?? 0
                return (
                  <TableCell key={n} className={sutun(n)}>
                    {sayi > 0 ? sayi : <><span aria-hidden="true">–</span><span className="cds--visually-hidden">soru yok</span></>}
                  </TableCell>
                )
              })}
            </TableRow>
          )),
        ])}
        <TableRow className="kilavuz-matris__toplam">
          <th scope="row">Toplam soru</th>
          {matris.senaryolar.map(n => <TableCell key={n} className={sutun(n)}>{matris.toplamlar[String(n)]}</TableCell>)}
        </TableRow>
      </TableBody>
    </Table>
  )
}
```

`dashboard/src/hazirlik/Matris.scss`:

```scss
// Senaryo karşılaştırması tablosu (spec §3.2): ders sayfası, kılavuz ekranı ve kâğıt aynı stili kullanır (K11).
@use '@carbon/react/scss/spacing' as spacing;
@use '@carbon/react/scss/type' as type;

.kilavuz-kod { @include type.type-style('code-02'); }

.kilavuz-matris {
  font-variant-numeric: tabular-nums;

  td { text-align: center; }

  th[scope='row'] { text-align: start; }
}

.kilavuz-matris__grup td {
  @include type.type-style('heading-compact-01');
  background-color: var(--cds-layer-accent-01);
}

.kilavuz-matris__vurgu { background-color: var(--cds-highlight); }
.kilavuz-matris__secili th { background-color: var(--cds-layer-selected-01); }

.kilavuz-matris__toplam th,
.kilavuz-matris__toplam td { @include type.type-style('heading-compact-01'); }

.kilavuz-matris__dugme {
  @include type.type-style('body-compact-01');
  min-block-size: spacing.$spacing-07;
  padding: 0;
  border: 0;
  background-color: transparent;
  color: var(--cds-text-primary);
  text-align: start;
  cursor: pointer;

  &:focus-visible { outline: 2px solid var(--cds-focus); }
}

@media (any-hover: hover) {
  .kilavuz-matris__dugme:hover { color: var(--cds-link-primary-hover); }
}

.kilavuz-matris__her { margin-inline-start: spacing.$spacing-03; }
```

`dashboard/src/hazirlik/CiktiAyrintisi.tsx`:

```tsx
import { useEffect, useRef } from 'react'
import { IconButton, Link as CarbonLink } from '@carbon/react'
import { Close, Launch } from '@carbon/icons-react'
import IcBaglanti from '../components/patterns/IcBaglanti'
import { ciktiKimligi, kitapYoluMetni, sayfaMetni } from './hazirlik'
import type { MatrisSatiri } from './tipler'

/** Satırın ayrıntısı (spec §3.2): tam MEB metni ve kitap bölümü. Masaüstünde tablonun yanında, telefonda alttan
 *  (Hazirlik.scss). Açılınca odak başlığa gelir; Esc ve "Ayrıntıyı kapat" kapatır, odak satıra döner (çağıran). */
export default function CiktiAyrintisi({ satir, kilavuz, kapat }: { satir: MatrisSatiri; kilavuz: string; kapat: () => void }) {
  const baslik = useRef<HTMLHeadingElement>(null)
  useEffect(() => { baslik.current?.focus() }, [satir.kod])
  useEffect(() => {
    const tus = (e: KeyboardEvent) => { if (e.key === 'Escape') kapat() }
    document.addEventListener('keydown', tus)
    return () => document.removeEventListener('keydown', tus)
  }, [kapat])
  return (
    <aside className="cikti-ayrinti" aria-labelledby="cikti-ayrinti-baslik">
      <div className="cikti-ayrinti__ust">
        <h3 id="cikti-ayrinti-baslik" ref={baslik} tabIndex={-1} className="cikti-ayrinti__baslik">
          <span className="kilavuz-kod">{satir.kod}</span> {satir.kisa_ad}
        </h3>
        <IconButton kind="ghost" size="lg" label="Ayrıntıyı kapat" onClick={kapat}><Close size={20} /></IconButton>
      </div>
      <blockquote className="cikti-ayrinti__meb">{`MEB: “${satir.metin}”`}</blockquote>
      <p className="cikti-ayrinti__etiket">Kitapta</p>
      {satir.kitap_durumu === 'var' ? (
        <ul className="cikti-ayrinti__yollar">
          {satir.kitapta.map(y => (
            <li key={`${y.cerceve}-${y.konu}`}>
              <CarbonLink href={y.baglanti} target="_blank" rel="noreferrer" renderIcon={Launch}>{kitapYoluMetni(y)}</CarbonLink>
              <span className="cikti-ayrinti__sayfa">{sayfaMetni(y.sayfa, y.son_sayfa)}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p>{satir.kitap_durumu === 'bulunamadi' ? 'Kitapta karşılığı bulunamadı.' : 'Kitap bölümleri henüz eklenmedi.'}</p>
      )}
      <IcBaglanti href={`${kilavuz}#${ciktiKimligi(satir.kod)}`}>Kılavuzda aç</IcBaglanti>
    </aside>
  )
}
```

`dashboard/src/hazirlik/HazirlikDersSayfasi.tsx`:

```tsx
import { useCallback, useRef, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { Breadcrumb, BreadcrumbItem, Button, ContentSwitcher, InlineNotification, RadioButton, RadioButtonGroup,
         SkeletonText, Switch } from '@carbon/react'
import { useApi } from '../hooks/useApi'
import { apiHataCumlesi } from '../utils/apiHatasi'
import { subjectClass } from '../utils/subject'
import Kaydirilabilir from '../components/Kaydirilabilir'
import KarsilastirmaTablosu from './KarsilastirmaTablosu'
import CiktiAyrintisi from './CiktiAyrintisi'
import DurumGostergesi from './DurumGostergesi'
import Uyarilar from './Uyarilar'
import { hazirlikUyarilari } from './belge'
import { kilavuzAdresi, sinavAdi, tarihMetni } from './hazirlik'
import type { DersOzeti } from './tipler'
import './Hazirlik.scss'

/** Duyurunun durumuna göre sayfanın tek bildirimi (spec §3.2): kesin yeşil ve öğretmenin sözü aynen. */
function DuyuruBildirimi({ oz }: { oz: DersOzeti }) {
  const d = oz.durum
  if (d.tur === 'kesin') {
    return <InlineNotification kind="success" lowContrast hideCloseButton statusIconDescription="Onay"
      title={`Okul ${d.senaryo}. senaryoyu duyurdu.`} subtitle={d.duyuru ? `«${d.duyuru}»` : undefined} />
  }
  if (d.tur === 'ulke_geneli') {
    return <InlineNotification kind="info" lowContrast hideCloseButton statusIconDescription="Bilgi"
      title="Bu yazılı ülke genelinde ortak yapılır; senaryo yok." subtitle={oz.not ?? undefined} />
  }
  if (d.tur === 'gecti') {
    return <InlineNotification kind="info" lowContrast hideCloseButton statusIconDescription="Bilgi" title="Bu yazılı geçti." />
  }
  if (d.uyari === 'senaryo_yok') {
    return <InlineNotification kind="warning" lowContrast hideCloseButton statusIconDescription="Uyarı"
      title={`Duyuru ${d.anilan.join(', ')}. senaryo diyor; MEB tablosunda bu yazılı için 1–${d.senaryo_sayisi} var.`} />
  }
  return <InlineNotification kind="info" lowContrast hideCloseButton statusIconDescription="Bilgi" title="Senaryo duyurulmadı."
    subtitle="Tablodan bir senaryo seçebilir ya da kılavuzu bütün senaryolarla açabilirsin." />
}

/** Ders sayfası (spec §3.2, taslak A "karşılaştırma tablosu"): yazılı seçici, duyuru, tablo, satır ayrıntısı,
 *  kılavuza geçiş. Kitap haritası olmayan ders senaryo verisiyle açılır (spec §7). */
export default function HazirlikDersSayfasi() {
  const { ders: anahtar = '' } = useParams()
  const [arama, setArama] = useSearchParams()
  const gezin = useNavigate()
  const no = arama.get('sinav') === '2' ? 2 : 1
  const { data: oz, loading, iskelet, hataTuru } = useApi<DersOzeti | null>(`/api/hazirlik/${anahtar}/${no}`, null)
  const [secili, setSecili] = useState<string | null>(null)
  const [secim, setSecim] = useState<string>('olasi')
  const satirDugmesi = useRef<HTMLButtonElement | null>(null)
  const kapat = useCallback(() => { setSecili(null); satirDugmesi.current?.focus() }, [])
  if (loading) {
    return iskelet ? <section className="hazirlik-ders" aria-busy="true"><SkeletonText heading /><SkeletonText paragraph lineCount={6} /></section> : null
  }
  if (!oz) {
    const h = apiHataCumlesi(hataTuru ?? 'sunucu', 'Ders sayfası')
    return <section className="hazirlik-ders"><InlineNotification kind="error" lowContrast hideCloseButton statusIconDescription="Hata" title={h.baslik} subtitle={h.ayrinti} /></section>
  }
  const duyurulan = oz.duyurulan
  const secilen = duyurulan ?? (secim === 'olasi' ? null : Number(secim))
  const vurgu = secilen ?? (oz.durum.tur === 'gecti' ? oz.durum.senaryo : null)
  const kilavuz = kilavuzAdresi(anahtar, no, duyurulan === null ? secilen : null)
  const ek = duyurulan !== null ? ` (${duyurulan}. senaryo)` : secilen !== null ? ` (${secilen}. senaryo, olası)` : ' (bütün senaryolar)'
  const satir = oz.gruplar.flatMap(g => g.satirlar).find(s => s.kod === secili) ?? null
  const yazili = (n: number) => () => { setSecili(null); setArama({ sinav: String(n) }) }
  return (
    <section className="hazirlik-ders" aria-labelledby="hazirlik-ders-baslik">
      <Breadcrumb aria-label="Konum">
        <BreadcrumbItem href="/hazirlik" onClick={(e: React.MouseEvent) => { e.preventDefault(); gezin('/hazirlik') }}>Sınav hazırlığı</BreadcrumbItem>
      </Breadcrumb>
      <h2 id="hazirlik-ders-baslik" className={`hazirlik-ders__baslik ${subjectClass(oz.ders)}`}>{oz.ders}</h2>
      <ContentSwitcher size="lg" selectedIndex={no - 1} onChange={({ index }) => yazili((index ?? 0) + 1)()}
        aria-label="Yazılı seçimi" className="hazirlik-ders__yazililar">
        {oz.sinavlar.map(s => (
          <Switch key={s.sinav_no} name={String(s.sinav_no)} text={`${sinavAdi(s.sinav_no)} · ${s.durum.tur === 'gecti' ? 'geçti' : tarihMetni(s.durum.tarih, false)}`} />
        ))}
      </ContentSwitcher>
      <DurumGostergesi durum={oz.durum} />
      <DuyuruBildirimi oz={oz} />
      <Uyarilar metinler={hazirlikUyarilari(oz)} kip="ekran" />
      {oz.tur === 'senaryolu' && duyurulan === null && oz.durum.tur !== 'gecti' && (
        <RadioButtonGroup legendText="Kılavuzun senaryosu" name="kilavuz-senaryosu" orientation="horizontal"
          valueSelected={secim} onChange={v => setSecim(String(v))}>
          {[<RadioButton key="olasi" id="senaryo-olasi" value="olasi" labelText="Bütün senaryolar (olası)" />,
            ...oz.senaryolar.map(n => <RadioButton key={n} id={`senaryo-${n}`} value={String(n)} labelText={`${n}. senaryo`} />)]}
        </RadioButtonGroup>
      )}
      {oz.tur === 'senaryolu' && (
        <div className={`hazirlik-ders__govde${satir ? ' hazirlik-ders__govde--acik' : ''}`}>
          <Kaydirilabilir className="hazirlik-ders__tablo" etiket="Senaryo karşılaştırması tablosu">
            <KarsilastirmaTablosu matris={oz} vurgu={vurgu} kip="ekran" secili={secili}
              vurguEtiketi={duyurulan !== null ? 'duyurulan' : oz.durum.tur === 'gecti' ? 'yapılan' : 'seçilen'}
              sec={(kod, dugme) => { satirDugmesi.current = dugme; setSecili(kod === secili ? null : kod) }} />
          </Kaydirilabilir>
          {satir && <CiktiAyrintisi satir={satir} kilavuz={kilavuz} kapat={kapat} />}
        </div>
      )}
      {oz.tur === 'senaryolu' && (
        <div className="hazirlik-ders__eylemler">
          <Button kind="primary" size="lg" onClick={() => gezin(kilavuz)}>Kapsam kılavuzunu aç{ek}</Button>
        </div>
      )}
    </section>
  )
}
```

`dashboard/src/hazirlik/Hazirlik.scss`'in sonuna:

```scss
// ── Ders sayfası ve karşılaştırma tablosu (plan Görev 10) ──────────────────────────────────────────────
.hazirlik-ders {
  display: flex;
  flex-direction: column;
  gap: spacing.$spacing-06;
}

.hazirlik-ders__baslik {
  @include type.type-style('heading-04');
  border-inline-start: spacing.$spacing-02 solid var(--ted-subject-accent);
  padding-inline-start: spacing.$spacing-04;
}

.hazirlik-ders__govde {
  display: grid;
  gap: spacing.$spacing-06;
}

@include bp.breakpoint('lg') {
  .hazirlik-ders__govde--acik { grid-template-columns: minmax(0, 2fr) minmax(0, 1fr); }
}

.hazirlik-ders__tablo { overflow-x: auto; }

.hazirlik-ders__eylemler {
  display: flex;
  flex-wrap: wrap;
  gap: spacing.$spacing-04;
}

.cikti-ayrinti {
  display: flex;
  flex-direction: column;
  gap: spacing.$spacing-03;
  padding: spacing.$spacing-05;
  background-color: var(--cds-layer-01);
  border: 1px solid var(--cds-border-subtle-01);
}

.cikti-ayrinti__ust {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: spacing.$spacing-03;
}

.cikti-ayrinti__baslik { @include type.type-style('heading-02'); }
.cikti-ayrinti__meb { @include type.type-style('body-01'); }

.cikti-ayrinti__etiket {
  @include type.type-style('label-01');
  color: var(--cds-text-secondary);
}

.cikti-ayrinti__yollar {
  display: flex;
  flex-direction: column;
  gap: spacing.$spacing-02;
}

.cikti-ayrinti__yollar a {
  display: inline-flex;
  align-items: center;
  min-block-size: spacing.$spacing-06;
}

.cikti-ayrinti__sayfa {
  margin-inline-start: spacing.$spacing-03;
  color: var(--cds-text-secondary);
}

@include bp.breakpoint('lg') {
  .cikti-ayrinti {
    position: sticky;
    inset-block-start: spacing.$spacing-10;
    align-self: start;
  }
}

// Telefonda alttan açılan panel (spec §3.2).
@include bp.breakpoint-down('lg') {
  .cikti-ayrinti {
    position: fixed;
    inset-inline: 0;
    inset-block-end: 0;
    z-index: 8000;
    max-block-size: 60vh;
    overflow-y: auto;
  }
}
```

`dashboard/src/routes.ts`'te `/hazirlik` satırının altına:

```ts
  { path: '/hazirlik/:ders', label: 'Sınav hazırlığı', icon: ExamMode, componentName: 'HazirlikDersSayfasi', showInNav: false, offPortal: true },
```

`dashboard/src/App.tsx`: `import HazirlikDersSayfasi from './hazirlik/HazirlikDersSayfasi'` ve `COMPONENTS`'e `HazirlikDersSayfasi,`.

- [ ] **Step 6: Kapılar ve e2e**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-hazirligi/dashboard
npm run lint; echo "lint: $?"
npm run test:birim; echo "birim: $?"
npm run build; echo "build: $?"
TEDY_E2E_PORT=8341 TEDY_E2E_PYTHON=/mnt/thunderbolt/workspaces/TED/.venv/bin/python env -u ANTHROPIC_API_KEY npx playwright test --project= hazirlik-ders hazirlik-ana-sayfa
```

Expected: üç çıkış 0; `hazirlik-ders` 4 test, `hazirlik-ana-sayfa` 3 test PASS (axe + IBM sıfır ihlal dahil).

- [ ] **Step 7: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-hazirligi
git log --oneline -3 && git status --short
git add dashboard/src/hazirlik dashboard/src/routes.ts dashboard/src/App.tsx dashboard/tests/hazirlik-belge.test.ts \
  dashboard/tests/e2e/hazirlik-ders.spec.ts
git commit -m "$(cat <<'EOF'
feat(sinav-hazirligi): ders sayfası — senaryo karşılaştırma tablosu ve satır ayrıntısı

Yazılı seçici, duyurunun cümlesi aynen, ünite gruplu çıktı × senaryo tablosu (duyurulan sütun vurgulu, "her
senaryoda", toplam), satıra dokununca MEB metni ve kitap bölümü; duyuru yoksa senaryo seçimi ve olası kılavuz.
Kitap haritası olmayan ders "kitap bölümleri henüz eklenmedi" der.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 11: Pano III — kapsam kılavuzu ekranı, ortak KilavuzBelgesi, hazırlık işaretleri

**Files:**
- Create: `dashboard/src/hazirlik/useIsaretler.ts`, `dashboard/src/hazirlik/KilavuzBelgesi.tsx`, `dashboard/src/hazirlik/Kilavuz.scss`, `dashboard/src/hazirlik/KilavuzSayfasi.tsx`
- Modify: `dashboard/src/routes.ts`, `dashboard/src/App.tsx`
- Test: `dashboard/tests/e2e/hazirlik-kilavuz.spec.ts`

**Interfaces:**
- Consumes: Görev 9–10'un yardımcıları, `belge.ts`, `KarsilastirmaTablosu`, `Uyarilar`, `DurumGostergesi`; `asistan/sayfaBaglami.asistanaSor({tur: 'sinav', id, etiket})`; `PUT /api/hazirlik/isaret`.
- Produces: `KilavuzBelgesi({model, kip: 'ekran' | 'baski', isaretler?, isaretle?})` — Görev 13'ün baskı girişi `kip="baski"` ile aynen çizer (K11); `useIsaretler(anahtar, model) -> {isaretler, isaretle(kod, durum, onceki), hata, hatayiKapat}`; çapalar `bolum-ozet`, `bolum-karsilastirma`, `bolum-unite-N`, `bolum-dogrulama`, `bolum-plan`, `bolum-ebeveyn`, `bolum-kaynaklar`, `cikti-<kod>`; rota `/hazirlik/:ders/:sinav?senaryo=N`.
- Başlık düzeyleri: belge başlığı `h2` ("Kapsam Kılavuzu"), bölümler ve üniteler `h3`, içerik çerçevesi `h4`, çıktı `h5`; sabit adlar `BOLUM`'dan (S38), kitap ve MEB adları veriden (K1).
- Ölçülmüş tuzak: alt alta iki kitap yolu bağlantısı IBM `target_spacing_sufficient` verdi → listelerdeki bağlantılar en az 24 px (`Kilavuz.scss` sonu).

- [ ] **Step 1: Başarısız e2e'yi yaz**

`dashboard/tests/e2e/hazirlik-kilavuz.spec.ts`:

```ts
import { test, expect } from '@playwright/test'
import { KILAVUZ, erisilebilirlik, fikstur, hazirlikAc, json } from './_hazirlik'

test.use({ timezoneId: 'Europe/Istanbul', locale: 'tr-TR' })

const KESIN = () => fikstur('fen-bilimleri-1-kilavuz')

test('kılavuz ekranı: özet, yan içindekiler, bloklar; axe + IBM sıfır ihlal', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik/fen-bilimleri/1', [[KILAVUZ('fen-bilimleri', 1), KESIN()]])
  await expect(page.getByRole('heading', { name: 'Kapsam Kılavuzu', level: 2 })).toBeVisible()
  await expect(page.locator('.kilavuz-baslik__alt')).toHaveText('Fen Bilimleri · 1. yazılı · 2. senaryo')
  await expect(page.locator('.kilavuz-ozet__zaman')).toHaveText('3 Kasım Salı · 9 gün kaldı')
  await expect(page.getByRole('navigation', { name: 'Kılavuzun bölümleri' }).getByRole('link'))
    .toHaveText(['Özet', 'Senaryo Karşılaştırması', '1. Ünite · Uzay Çağı', '2. Ünite · Kuvvet ve Enerjiyi Keşfedelim',
      'Duyuru Doğrulaması', 'Çalışma Planı', 'Kaynaklar'])
  const is_ = page.locator('#cikti-FB-7-2-1')
  await expect(is_.locator('.kilavuz-blok__soru')).toContainText('3 soru')
  await expect(is_.locator('.kilavuz-basliklar li').first()).toContainText('Etkinlik Noktası-1 — Fiziksel anlamda yapılan işin niteliklerini tanımlama · s. 60')
  await expect(page.locator('#cikti-FB-7-2-2')).toHaveText(/^FB\.7\.2\.2 Enerji ve Enerji Çeşitleri · 2\. senaryoda yok$/)
  await expect(page.locator('#bolum-icindekiler')).toHaveCount(0)   // kâğıdın içindekileri ekranda yok
  expect(await erisilebilirlik(page, '.kilavuz-sayfa')).toEqual({ axe: [], ibm: [] })
})

test('blok iç sırası sabit (K2)', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik/fen-bilimleri/1', [[KILAVUZ('fen-bilimleri', 1), KESIN()]])
  await page.locator('#cikti-FB-7-2-1').waitFor()
  const sira = await page.locator('#cikti-FB-7-2-1').evaluate(el => [...el.children].map(c => c.className.split(' ')[0]))
  expect(sira).toEqual(['kilavuz-blok__ust', 'kilavuz-blok__soru', 'kilavuz-blok__meb', 'kilavuz-blok__etiket',
    'kilavuz-blok__yollar', 'kilavuz-blok__etiket', 'kilavuz-basliklar', 'kilavuz-blok__baglam', 'kilavuz-isaret'])
})

test('olası kip: tek senaryo sayısı yok (K8)', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik/fen-bilimleri/1', [[KILAVUZ('fen-bilimleri', 1), fikstur('fen-bilimleri-1-olasi-kilavuz')]])
  await expect(page.locator('.kilavuz-baslik__alt')).toHaveText('Fen Bilimleri · 1. yazılı · bütün senaryolar (olası)')
  const sorular = page.locator('.kilavuz-blok__soru')
  await expect(sorular.first()).toBeVisible()
  for (const metin of await sorular.allInnerTexts()) expect(metin).toMatch(/^(senaryoya göre \d–\d soru|her senaryoda \d soru)/)
  await expect(page.locator('.kilavuz-ozet__sayilar')).toContainText('senaryoya göre 6–9')
  await expect(page.getByText(/Kesin:/)).toHaveCount(0)
})

test('kitapta karşılığı bulunamayan çıktı "bulunamadı" der, "yok" demez', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik/fen-bilimleri/1', [[KILAVUZ('fen-bilimleri', 1), fikstur('fen-bilimleri-1-bulunamadi-kilavuz')]])
  const blok = page.locator('#cikti-FB-7-1-3')
  await expect(blok.locator('.kilavuz-blok__yok')).toHaveText('Kitapta karşılığı bulunamadı.')
  await expect(blok.locator('.kilavuz-basliklar')).toHaveCount(0)
})

test('kitap güncellendi uyarısı (K12)', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik/fen-bilimleri/1', [[KILAVUZ('fen-bilimleri', 1), fikstur('fen-bilimleri-1-k12-kilavuz')]])
  await expect(page.getByText('MEB ders kitabının PDF’i değişti; kitap bölümleri güncel değil, harita yenilenmeli.')).toBeVisible()
})

test('işaret konur; kaydedilemezse geri alınır ve söylenir (spec §7)', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik/fen-bilimleri/1', [[KILAVUZ('fen-bilimleri', 1), KESIN()]])
  const gonderilen: unknown[] = []
  await page.route('**/api/hazirlik/isaret', r => {
    gonderilen.push(r.request().postDataJSON())
    return r.fulfill(json({ ders: 'fen-bilimleri', isaretler: { 'FB.7.1.1': 'hazirim' } }))
  })
  const blok = page.locator('#cikti-FB-7-1-1')
  const hazirim = blok.getByRole('checkbox', { name: 'Hazırım' })
  await hazirim.check({ force: true })
  await expect(hazirim).toBeChecked()
  expect(gonderilen).toEqual([{ ders: 'fen-bilimleri', kod: 'FB.7.1.1', durum: 'hazirim' }])
  // FB.7.2.1 fikstürde "tekrar": Hazırım'a geçince Tekrar kalkar; sunucu düşerse ikisi de eski hâline döner.
  await page.unroute('**/api/hazirlik/isaret')
  await page.route('**/api/hazirlik/isaret', r => r.fulfill(json({ error: 'yazilamadi' }, 503)))
  const is_ = page.locator('#cikti-FB-7-2-1')
  await expect(is_.getByRole('checkbox', { name: 'Tekrar' })).toBeChecked()
  await is_.getByRole('checkbox', { name: 'Hazırım' }).check({ force: true })
  await expect(page.getByRole('alert')).toContainText('İşaret kaydedilemedi; geri alındı.')
  await expect(is_.getByRole('checkbox', { name: 'Tekrar' })).toBeChecked()
  await expect(is_.getByRole('checkbox', { name: 'Hazırım' })).not.toBeChecked()
})
```

- [ ] **Step 2: Koş, düştüğünü gör**

Run: `cd dashboard && npm run build && TEDY_E2E_PORT=8341 TEDY_E2E_PYTHON=/mnt/thunderbolt/workspaces/TED/.venv/bin/python env -u ANTHROPIC_API_KEY npx playwright test --project= hazirlik-kilavuz`
Expected: FAIL — `/hazirlik/fen-bilimleri/1` bilinmeyen rota olduğu için ana sayfaya yönlenir; "Kapsam Kılavuzu" başlığı bulunamaz.

- [ ] **Step 3: İşaret kancası, belge, ekran ve stil**

`dashboard/src/hazirlik/useIsaretler.ts`:

```ts
import { useCallback, useMemo, useState } from 'react'
import { tumBloklar } from './belge'
import type { IsaretDurumu, KilavuzModeli } from './tipler'

/** Hazırlık işaretleri (spec §2.3, §7): iyimser güncelleme; PUT düşerse işaret eski hâline döner ve hata söylenir. */
export function useIsaretler(anahtar: string, model: KilavuzModeli | null) {
  const [yerel, setYerel] = useState<Record<string, IsaretDurumu>>({})
  const [hata, setHata] = useState<string | null>(null)
  const sunucu = useMemo(() => Object.fromEntries(tumBloklar(model).map(b => [b.kod, b.isaret])), [model])
  const isaretler = useMemo(() => ({ ...sunucu, ...yerel }), [sunucu, yerel])
  const isaretle = useCallback(async (kod: string, durum: IsaretDurumu, onceki: IsaretDurumu) => {
    setYerel(y => ({ ...y, [kod]: durum }))
    setHata(null)
    try {
      const r = await fetch('/api/hazirlik/isaret', {
        method: 'PUT', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ders: anahtar, kod, durum }),
      })
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
    } catch {
      setYerel(y => ({ ...y, [kod]: onceki }))
      setHata('İşaret kaydedilemedi; geri alındı.')
    }
  }, [anahtar])
  return { isaretler, isaretle, hata, hatayiKapat: () => setHata(null) }
}
```

`dashboard/src/hazirlik/KilavuzBelgesi.tsx`:

```tsx
import { Checkbox, Link as CarbonLink, Tag } from '@carbon/react'
import { Checkbox as KutuIkonu, CheckboxChecked, Launch } from '@carbon/icons-react'
import IcBaglanti from '../components/patterns/IcBaglanti'
import { subjectClass } from '../utils/subject'
import DurumGostergesi from './DurumGostergesi'
import KarsilastirmaTablosu from './KarsilastirmaTablosu'
import Uyarilar from './Uyarilar'
import { BOLUM, bolumler, damgaMetni, hazirlikUyarilari, ustBilgi } from './belge'
import { BASLIK_TURU, baslikMetni, ciktiKimligi, ebeveynCumleleri, kalanGunMetni, kitapYoluMetni, sayfaMetni,
         soruMetni, tarihMetni } from './hazirlik'
import type { Blok, IsaretDurumu, KilavuzModeli } from './tipler'
import './Kilavuz.scss'

type Kip = 'ekran' | 'baski'
type Isaretle = (kod: string, durum: IsaretDurumu, onceki: IsaretDurumu) => void

function KagitKutusu({ dolu, ad }: { dolu: boolean; ad: string }) {
  return (
    <span className="kilavuz-isaret__kutu">
      {dolu ? <CheckboxChecked size={16} aria-hidden="true" /> : <KutuIkonu size={16} aria-hidden="true" />}
      {ad}{dolu && <span className="cds--visually-hidden"> (işaretli)</span>}
    </span>
  )
}

/** Hazırlık işareti: ekranda iki Carbon onay kutusu (biri seçilince öteki kalkar), kâğıtta durağan karşılığı (K11). */
function IsaretAlani({ b, kip, isaret, isaretle }: { b: Blok; kip: Kip; isaret: IsaretDurumu; isaretle?: Isaretle }) {
  if (kip === 'baski' || !isaretle) {
    return <p className="kilavuz-isaret"><KagitKutusu dolu={isaret === 'hazirim'} ad="Hazırım" /><KagitKutusu dolu={isaret === 'tekrar'} ad="Tekrar" /></p>
  }
  return (
    <fieldset className="kilavuz-isaret">
      <legend className="cds--visually-hidden">{`${b.kod} hazırlık işareti`}</legend>
      <Checkbox id={`isaret-${ciktiKimligi(b.kod)}-hazirim`} labelText="Hazırım" checked={isaret === 'hazirim'}
        onChange={(_, { checked }) => isaretle(b.kod, checked ? 'hazirim' : null, isaret)} />
      <Checkbox id={`isaret-${ciktiKimligi(b.kod)}-tekrar`} labelText="Tekrar" checked={isaret === 'tekrar'}
        onChange={(_, { checked }) => isaretle(b.kod, checked ? 'tekrar' : null, isaret)} />
    </fieldset>
  )
}

/** Çıktı bloğu (K2, sıra sabit): kod + kısa ad, soru, MEB metni, Kitapta, ele alınanlar, okulda, ödev/modül, işaret. */
function CiktiBlogu({ b, m, kip, isaret, isaretle }: { b: Blok; m: KilavuzModeli; kip: Kip; isaret: IsaretDurumu; isaretle?: Isaretle }) {
  const baslik = `${b.kod} ${b.kisa_ad}`
  if (!b.senaryoda) {
    return <p id={ciktiKimligi(b.kod)} className="kilavuz-blok kilavuz-blok--soluk">{`${baslik} · ${m.senaryo}. senaryoda yok`}</p>
  }
  return (
    <div id={ciktiKimligi(b.kod)} className="kilavuz-blok" data-baslik={baslik}>
      <h5 className="kilavuz-blok__ust"><span className="kilavuz-kod">{b.kod}</span> {b.kisa_ad}</h5>
      <p className="kilavuz-blok__soru">
        {soruMetni(b)}
        {b.her_senaryoda && <Tag type="gray" size="sm" className="kilavuz-blok__her">her senaryoda</Tag>}
      </p>
      <blockquote className="kilavuz-blok__meb">{`MEB: “${b.metin}”`}</blockquote>
      <p className="kilavuz-blok__etiket">Kitapta</p>
      {b.kitap_durumu === 'var' ? (
        <ul className="kilavuz-blok__yollar">
          {b.kitapta.map(y => (
            <li key={`${y.cerceve}-${y.konu}`}>
              {kip === 'ekran'
                ? <CarbonLink href={y.baglanti} target="_blank" rel="noreferrer" renderIcon={Launch}>{kitapYoluMetni(y)}</CarbonLink>
                : <span>{kitapYoluMetni(y)}</span>}
              <span className="kilavuz-blok__sayfa">{sayfaMetni(y.sayfa, y.son_sayfa)}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="kilavuz-blok__yok">{b.kitap_durumu === 'bulunamadi' ? 'Kitapta karşılığı bulunamadı.' : 'Kitap bölümleri henüz eklenmedi.'}</p>
      )}
      {b.basliklar.length > 0 && (
        <>
          <p className="kilavuz-blok__etiket">Bu bölümde ele alınanlar</p>
          <ul className="kilavuz-basliklar">
            {b.basliklar.map((h, i) => (
              <li key={i}><span className="kilavuz-basliklar__tur">{BASLIK_TURU[h.tur]}</span>{` ${baslikMetni(h)} · s. ${h.sayfa}`}</li>
            ))}
          </ul>
        </>
      )}
      <p className="kilavuz-blok__baglam">{`Okulda: ${b.okulda.map(h => h.hafta).join(', ') || 'ders kartlarında geçmiyor'}`}</p>
      {b.odevler.length > 0 && <p className="kilavuz-blok__baglam">{`Ödev: ${b.odevler.map(o => o.baslik).join(', ')}`}</p>}
      {b.moduller.length > 0 && (
        <p className="kilavuz-blok__baglam">
          {'Modül: '}
          {b.moduller.map((md, i) => (
            <span key={md.yol}>{i > 0 && ', '}{kip === 'ekran' ? <IcBaglanti href={md.yol} inline>{md.baslik}</IcBaglanti> : md.baslik}</span>
          ))}
        </p>
      )}
      <IsaretAlani b={b} kip={kip} isaret={isaret} isaretle={isaretle} />
    </div>
  )
}

/** Kapsam kılavuzu (spec §4): ekranda ve kâğıtta aynı bileşen, aynı sıra (K11). */
export default function KilavuzBelgesi({ model: m, kip, isaretler = {}, isaretle }: {
  model: KilavuzModeli
  kip: Kip
  isaretler?: Record<string, IsaretDurumu>
  isaretle?: Isaretle
}) {
  const bloklar = m.uniteler.flatMap(u => u.cerceveler.flatMap(c => c.bloklar))
  const adi = (kod: string) => bloklar.find(b => b.kod === kod)?.kisa_ad ?? kod
  const kalan = kalanGunMetni(m.durum.kalan_gun)
  const notlar = [
    ...(m.secilen_duyurulan_degil ? [`Okul ${m.duyurulan}. senaryoyu duyurdu; bu kılavuz ${m.senaryo}. senaryoya göre.`] : []),
    ...(m.durum.uyari === 'kismen' ? ['Duyurudaki bazı konular bu senaryoda yok; Duyuru Doğrulaması bölümüne bak.'] : []),
    ...hazirlikUyarilari(m),
    ...(m.kip === 'ulke_geneli' && m.not ? [m.not] : []),
  ]
  return (
    <article className={`kilavuz-belge kilavuz-belge--${kip}`} lang="tr">
      {m.ebeveyn && (
        <section id="bolum-ebeveyn" className="kilavuz-ebeveyn" aria-labelledby="baslik-ebeveyn">
          <h3 id="baslik-ebeveyn">{BOLUM.ebeveyn}</h3>
          <ul className="kilavuz-liste">{ebeveynCumleleri(m).map(c => <li key={c}>{c}</li>)}</ul>
          <p>{`En çok soru: ${m.ebeveyn.en_agir.map(k => `${k} ${adi(k)}`).join('; ')}`}</p>
        </section>
      )}
      <section id="bolum-ozet" className={`kilavuz-ozet ${subjectClass(m.ders)}`} aria-labelledby="baslik-ozet">
        <h2 id="baslik-ozet" className="kilavuz-baslik">{BOLUM.kilavuz}</h2>
        <p className="kilavuz-baslik__alt">{ustBilgi(m)}</p>
        <p className="kilavuz-ozet__zaman">{`${tarihMetni(m.durum.tarih)}${kalan ? ` · ${kalan}${m.durum.kalan_gun && m.durum.kalan_gun > 1 ? ' kaldı' : ''}` : ''}`}</p>
        <DurumGostergesi durum={m.durum} />
        <Uyarilar metinler={notlar} kip={kip} />
        <dl className="kilavuz-ozet__sayilar">
          <div><dt>Toplam soru</dt><dd>{m.ozet.toplam_soru ?? (m.ozet.soru_araligi ? `senaryoya göre ${m.ozet.soru_araligi[0]}–${m.ozet.soru_araligi[1]}` : '–')}</dd></div>
          <div><dt>Öğrenme çıktısı</dt><dd>{m.ozet.cikti_sayisi}</dd></div>
          <div><dt>Her senaryoda</dt><dd>{m.ozet.her_senaryoda.map(k => `${k} ${adi(k)}`).join('; ') || '–'}</dd></div>
        </dl>
        {bloklar.some(b => b.senaryoda) && (
          <ul className="kilavuz-ozet__dagilim">
            {bloklar.filter(b => b.senaryoda).map(b => <li key={b.kod}><span className="kilavuz-kod">{b.kod}</span>{` ${b.kisa_ad} · ${soruMetni(b)}`}</li>)}
          </ul>
        )}
        <p className="kilavuz-damga">{damgaMetni(m)}</p>
      </section>
      {kip === 'baski' && (
        <nav id="bolum-icindekiler" className="kilavuz-icindekiler" aria-labelledby="baslik-icindekiler">
          <h3 id="baslik-icindekiler">{BOLUM.icindekiler}</h3>
          <ol>{bolumler(m).map(b => <li key={b.id}><a className="kilavuz-icindekiler__baglanti" href={`#${b.id}`}>{b.ad}</a></li>)}</ol>
        </nav>
      )}
      {m.matris.senaryolar.length > 0 && (
        <section id="bolum-karsilastirma" aria-labelledby="baslik-karsilastirma">
          <h3 id="baslik-karsilastirma">{BOLUM.karsilastirma}</h3>
          <KarsilastirmaTablosu matris={m.matris} vurgu={m.senaryo} kip="baski"
            vurguEtiketi={m.kip === 'kesin' ? 'duyurulan' : 'seçilen'} />
        </section>
      )}
      {m.uniteler.map((u, i) => (
        <section key={u.baslik} id={`bolum-unite-${i + 1}`} aria-labelledby={`baslik-unite-${i + 1}`}>
          <h3 id={`baslik-unite-${i + 1}`}>{u.baslik}</h3>
          {u.cerceveler.map(c => (
            <div key={c.baslik ?? 'cerceve'} className="kilavuz-cerceve">
              {c.baslik && <h4 className="kilavuz-cerceve__baslik">{c.baslik}{c.sayfa !== null && c.son_sayfa !== null && <span className="kilavuz-cerceve__sayfa">{` · ${sayfaMetni(c.sayfa, c.son_sayfa)}`}</span>}</h4>}
              {c.bloklar.map(b => <CiktiBlogu key={b.kod} b={b} m={m} kip={kip} isaret={isaretler[b.kod] ?? b.isaret} isaretle={isaretle} />)}
            </div>
          ))}
        </section>
      ))}
      {m.dogrulama && (
        <section id="bolum-dogrulama" aria-labelledby="baslik-dogrulama">
          <h3 id="baslik-dogrulama">{BOLUM.dogrulama}</h3>
          <ul className="kilavuz-liste">
            {m.dogrulama.duyurulan_konular.map(d => (
              <li key={d.konu}>{`«${d.konu}» → ${d.kodlar.length ? d.kodlar.map(k => `${k} ${adi(k)}`).join('; ') : 'MEB tablosunda karşılığı bulunamadı'}`}</li>
            ))}
          </ul>
          {m.dogrulama.senaryo_disi.length > 0 && <p>{`Bu senaryoda olmayan duyuru konusu: ${m.dogrulama.senaryo_disi.join('; ')}`}</p>}
          {m.dogrulama.duyurunun_saymadigi.length > 0 && <p>{`Senaryoda olup duyurunun saymadığı çıktılar: ${m.dogrulama.duyurunun_saymadigi.map(k => `${k} ${adi(k)}`).join('; ')}`}</p>}
        </section>
      )}
      {m.plan && (
        <section id="bolum-plan" aria-labelledby="baslik-plan">
          <h3 id="baslik-plan">{BOLUM.plan}</h3>
          <ol className="kilavuz-liste">
            {m.plan.gunler.map(g => (
              <li key={g.tarih}>{`${tarihMetni(g.tarih)} · ${g.genel_tekrar ? 'genel tekrar: ' : ''}${g.ciktilar.map(k => `${k} ${adi(k)}`).join('; ')}`}</li>
            ))}
          </ol>
        </section>
      )}
      <section id="bolum-kaynaklar" aria-labelledby="baslik-kaynaklar">
        <h3 id="baslik-kaynaklar">{BOLUM.kaynaklar}</h3>
        <ul className="kilavuz-liste">
          {m.kaynaklar.map(k => (
            <li key={k.adres}>{kip === 'ekran'
              ? <CarbonLink href={k.adres} target="_blank" rel="noreferrer" renderIcon={Launch}>{k.etiket}</CarbonLink>
              : `${k.etiket} — ${k.adres}`}</li>
          ))}
        </ul>
      </section>
    </article>
  )
}
```

`dashboard/src/hazirlik/Kilavuz.scss`:

```scss
// Kapsam kılavuzu belgesi: ekran ve kâğıt (Kanun K2–K5, K11). Kâğıda özgü kurallar src/baski/baski.scss'te.
@use '@carbon/react/scss/spacing' as spacing;
@use '@carbon/react/scss/type' as type;
@use '@carbon/react/scss/breakpoint' as bp;

.kilavuz-belge {
  display: flex;
  flex-direction: column;
  gap: spacing.$spacing-08;

  h3 { @include type.type-style('heading-03'); }
}

.kilavuz-baslik { @include type.type-style('heading-05'); }

.kilavuz-baslik__alt {
  @include type.type-style('heading-02');
  color: var(--cds-text-secondary);
}

.kilavuz-ozet {
  display: flex;
  flex-direction: column;
  gap: spacing.$spacing-03;
  border-inline-start: spacing.$spacing-02 solid var(--ted-subject-accent);
  padding-inline-start: spacing.$spacing-05;
}

.kilavuz-ozet__sayilar {
  display: grid;
  gap: spacing.$spacing-02;

  dt {
    @include type.type-style('label-01');
    color: var(--cds-text-secondary);
  }

  dd { @include type.type-style('body-compact-01'); }
}

.kilavuz-damga,
.kilavuz-uyari {
  @include type.type-style('helper-text-01');
  color: var(--cds-text-secondary);
}

.kilavuz-uyari {
  border: 1px solid var(--cds-border-strong-01);
  padding: spacing.$spacing-03;
}

.kilavuz-liste {
  display: flex;
  flex-direction: column;
  gap: spacing.$spacing-02;
  @include type.type-style('body-compact-01');
}

.kilavuz-cerceve {
  display: flex;
  flex-direction: column;
  gap: spacing.$spacing-04;
  margin-block-start: spacing.$spacing-05;
}

.kilavuz-cerceve__baslik { @include type.type-style('heading-02'); }
.kilavuz-cerceve__sayfa { color: var(--cds-text-secondary); }

.kilavuz-blok {
  display: flex;
  flex-direction: column;
  gap: spacing.$spacing-03;
  padding: spacing.$spacing-05;
  background-color: var(--cds-layer-01);
}

.kilavuz-blok__ust { @include type.type-style('heading-compact-02'); }

.kilavuz-blok__soru {
  display: flex;
  align-items: center;
  gap: spacing.$spacing-03;
  @include type.type-style('body-compact-01');
}

.kilavuz-blok__meb { @include type.type-style('body-01'); }

.kilavuz-blok__etiket,
.kilavuz-basliklar__tur {
  @include type.type-style('label-01');
  color: var(--cds-text-secondary);
}

.kilavuz-blok__sayfa {
  margin-inline-start: spacing.$spacing-03;
  color: var(--cds-text-secondary);
}

.kilavuz-blok--soluk {
  @include type.type-style('body-compact-01');
  color: var(--cds-text-secondary);
  background-color: transparent;
  padding-block: spacing.$spacing-02;
}

.kilavuz-basliklar {
  display: flex;
  flex-direction: column;
  gap: spacing.$spacing-02;

  li { @include type.type-style('body-compact-01'); }
}

.kilavuz-blok__baglam { @include type.type-style('body-compact-01'); }

.kilavuz-isaret {
  display: flex;
  flex-wrap: wrap;
  gap: spacing.$spacing-05;
  border: 0;
  padding: 0;
}

.kilavuz-isaret__kutu {
  display: inline-flex;
  align-items: center;
  gap: spacing.$spacing-02;
}

.kilavuz-sayfa {
  display: flex;
  flex-direction: column;
  gap: spacing.$spacing-06;
}

.kilavuz-sayfa__eylemler {
  display: flex;
  flex-wrap: wrap;
  gap: spacing.$spacing-04;
}

.kilavuz-sayfa__duzen {
  display: grid;
  gap: spacing.$spacing-07;
}

.kilavuz-sayfa__icindekiler ul {
  display: flex;
  flex-direction: column;
  gap: spacing.$spacing-03;
  @include type.type-style('body-compact-01');
}

@include bp.breakpoint('lg') {
  .kilavuz-sayfa__duzen {
    /* stylelint-disable-next-line carbon/layout-use -- yan içindekiler sütununun genişliği, aralık değil */
    grid-template-columns: 12rem minmax(0, 1fr);
  }

  .kilavuz-sayfa__icindekiler {
    position: sticky;
    inset-block-start: spacing.$spacing-10;
    align-self: start;
  }
}

@include bp.breakpoint-down('lg') {
  .kilavuz-sayfa__icindekiler { display: none; }
}

// WCAG 2.5.8 / IBM target_spacing_sufficient: alt alta duran bağlantılar en az 24 px (ölçüldü: iki kitap yolu bağlantısı
// birbirine 12 px'ten yakındı).
.kilavuz-blok__yollar a,
.kilavuz-liste a,
.kilavuz-sayfa__icindekiler a,
.kilavuz-blok__baglam a {
  display: inline-flex;
  align-items: center;
  min-block-size: spacing.$spacing-06;
}

.kilavuz-blok__yollar {
  display: flex;
  flex-direction: column;
  gap: spacing.$spacing-02;
}
```

`dashboard/src/hazirlik/KilavuzSayfasi.tsx`:

```tsx
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { Breadcrumb, BreadcrumbItem, Button, InlineNotification, SkeletonText } from '@carbon/react'
import { useApi } from '../hooks/useApi'
import { apiHataCumlesi } from '../utils/apiHatasi'
import { asistanaSor } from '../asistan/sayfaBaglami'
import KilavuzBelgesi from './KilavuzBelgesi'
import { bolumler } from './belge'
import { modelAdresi, sinavAdi } from './hazirlik'
import { useIsaretler } from './useIsaretler'
import type { KilavuzModeli } from './tipler'
import './Hazirlik.scss'

/** Kapsam kılavuzu ekranı (spec §3.3): yapışkan yan içindekiler, belge, işaretler, asistana sor. */
export default function KilavuzSayfasi() {
  const { ders: anahtar = '', sinav = '1' } = useParams()
  const [arama] = useSearchParams()
  const gezin = useNavigate()
  const no = sinav === '2' ? 2 : 1
  const ham = arama.get('senaryo')
  const senaryo = ham && /^\d{1,2}$/.test(ham) ? Number(ham) : null
  const { data: m, loading, iskelet, hataTuru } = useApi<KilavuzModeli | null>(
    modelAdresi(anahtar, no, senaryo, { ebeveyn: false, isaret: true }), null)
  const { isaretler, isaretle, hata, hatayiKapat } = useIsaretler(anahtar, m)
  if (loading) {
    return iskelet ? <section className="kilavuz-sayfa" aria-busy="true"><SkeletonText heading /><SkeletonText paragraph lineCount={8} /></section> : null
  }
  if (!m) {
    const h = apiHataCumlesi(hataTuru ?? 'sunucu', 'Kapsam kılavuzu')
    return <section className="kilavuz-sayfa"><InlineNotification kind="error" lowContrast hideCloseButton statusIconDescription="Hata" title={h.baslik} subtitle={h.ayrinti} /></section>
  }
  const sor = () => {
    const karsilandi = m.durum.sinav_id !== null
      && asistanaSor({ tur: 'sinav', id: m.durum.sinav_id, etiket: `${m.ders} — ${sinavAdi(no)}` })
    if (!karsilandi) gezin('/asistan?sayfa=sinavlar')
  }
  const dersSayfasi = `/hazirlik/${anahtar}?sinav=${no}`
  return (
    <div className="kilavuz-sayfa">
      <Breadcrumb aria-label="Konum">
        <BreadcrumbItem href="/hazirlik" onClick={(e: React.MouseEvent) => { e.preventDefault(); gezin('/hazirlik') }}>Sınav hazırlığı</BreadcrumbItem>
        <BreadcrumbItem href={dersSayfasi} onClick={(e: React.MouseEvent) => { e.preventDefault(); gezin(dersSayfasi) }}>{m.ders}</BreadcrumbItem>
      </Breadcrumb>
      <div className="kilavuz-sayfa__eylemler">
        <Button kind="ghost" size="lg" onClick={sor}>Asistana sor</Button>
      </div>
      {hata && <InlineNotification kind="error" lowContrast role="alert" statusIconDescription="Hata" aria-label="Bildirimi kapat"
        title={hata} onCloseButtonClick={hatayiKapat} />}
      <div className="kilavuz-sayfa__duzen">
        <nav className="kilavuz-sayfa__icindekiler" aria-label="Kılavuzun bölümleri">
          <ul>{bolumler(m).map(b => <li key={b.id}><a href={`#${b.id}`}>{b.ad}</a></li>)}</ul>
        </nav>
        <KilavuzBelgesi model={m} kip="ekran" isaretler={isaretler} isaretle={isaretle} />
      </div>
    </div>
  )
}
```

`dashboard/src/routes.ts`'te `/hazirlik/:ders` satırının altına:

```ts
  { path: '/hazirlik/:ders/:sinav', label: 'Sınav hazırlığı', icon: ExamMode, componentName: 'KilavuzSayfasi', showInNav: false, offPortal: true },
```

`dashboard/src/App.tsx`: `import KilavuzSayfasi from './hazirlik/KilavuzSayfasi'` ve `COMPONENTS`'e `KilavuzSayfasi,`.

- [ ] **Step 4: Kapılar ve e2e**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-hazirligi/dashboard
npm run lint; echo "lint: $?"
npm run test:birim; echo "birim: $?"
npm run build; echo "build: $?"
TEDY_E2E_PORT=8341 TEDY_E2E_PYTHON=/mnt/thunderbolt/workspaces/TED/.venv/bin/python env -u ANTHROPIC_API_KEY npx playwright test --project= hazirlik-kilavuz hazirlik-ders hazirlik-ana-sayfa
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-hazirligi && env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pano_tasarim_sistemi.py tests/test_pano_talimatname_borclari.py
```

Expected: hepsi 0 / PASS; `hazirlik-kilavuz` 6 test (K2 sırası, K8 olası kip, "bulunamadı", K12 uyarısı, işaretin geri alınması, axe + IBM).

- [ ] **Step 5: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-hazirligi
git log --oneline -3 && git status --short
git add dashboard/src/hazirlik dashboard/src/routes.ts dashboard/src/App.tsx dashboard/tests/e2e/hazirlik-kilavuz.spec.ts
git commit -m "$(cat <<'EOF'
feat(sinav-hazirligi): kapsam kılavuzu ekranı — ortak KilavuzBelgesi, yan içindekiler, hazırlık işaretleri

Özet, senaryo karşılaştırması, ünite › çerçeve › çıktı blokları (sıra sabit, K2), duyuru doğrulaması, çalışma
planı ve kaynaklar; olası kipte tek senaryo sayısı yok (K8); işaret iyimser, kaydedilemezse geri alınır.
Aynı bileşen kâğıt kipinde baskı görünümünü çizer (K11).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 12: Giriş noktaları — Sınavlar kartı, Dersler sekmesi, asistan aracı

**Files:**
- Modify: `dashboard/src/components/SinavKarti.tsx`, `dashboard/src/components/CourseContent.tsx`, `src/sinav_senaryo.py` (`arac_metni`)
- Test: `dashboard/tests/e2e/hazirlik-giris.spec.ts`, `tests/test_sinav_senaryo.py` (ekleme)
- Modify (görsel taban): `dashboard/tests/e2e/gorsel-regresyon.spec.ts-snapshots/dersler-masaustu.png`, `dersler-telefon.png`

**Interfaces:**
- Consumes: Görev 9'un `dersAnahtari`, `kilavuzAdresi`; Görev 6'nın `DERS_ANAHTARLARI`.
- Produces: Sınavlar kartının "MEB konu-soru dağılımı" bölümünde "Kapsam kılavuzu" bağlantısı (duyurulan senaryoyla; senaryo yoksa olası; ülke genelinde ders sayfası); Dersler'in her eşlenen ders sekmesinde "MEB senaryoları"; `sinav_senaryosu` araç metninde "Kapsam kılavuzu panoda: Sınav Hazırlığı › <ders> › <no>. yazılı (/hazirlik/<anahtar>/<no>)." satırı. "Daha fazla" ve kenar menüsü girişi Görev 9'dadır; "Kılavuzu aç" öneri çipi Plan 2.

- [ ] **Step 1: Başarısız testleri yaz**

`tests/test_sinav_senaryo.py`'nin sonuna:

```python
def test_arac_metni_kapsam_kilavuzunun_yerini_soyler():
    """Sınav Hazırlığı girişi (spec 2026-10-25 §3.4, plan Görev 12)."""
    govde, _ = ss.arac_metni(TABLO, [], {"ders": "Fen", "sinav_no": 1}, BUGUN)
    assert "Kapsam kılavuzu panoda: Sınav Hazırlığı › Fen Bilimleri › 1. yazılı (/hazirlik/fen-bilimleri/1)." in govde
    govde, _ = ss.arac_metni(TABLO, [], {"ders": "Türkçe", "sinav_no": 2}, BUGUN)
    assert "(/hazirlik/turkce/2)" in govde
```

`dashboard/tests/e2e/hazirlik-giris.spec.ts`:

```ts
import { test, expect } from '@playwright/test'
import { mock, LIVE } from './_audit-fixtures'

test.use({ timezoneId: 'Europe/Istanbul', locale: 'tr-TR' })

// Sınav Hazırlığı giriş noktaları (spec §3.4, plan Görev 12): Sınavlar kartı ve Dersler sekmesi.
const blok = (durum: string, senaryo: number | null) => ({
  durum, ders: 'Türkçe', sinav_no: 1, anilan: senaryo ? [senaryo] : [], cumle: null, senaryo, toplam: null, dagilim: [],
  eslesen_konu_sayisi: 0, eslesmeyen_konular: [], senaryo_disi_konular: [], adaylar: [], senaryo_sayisi: 6,
  kaynak: 'https://odsgm.meb.gov.tr/x', meb_guncelleme: '2026-09-10T17:27',
})
const sinav = (senaryo: Record<string, unknown>) => ({ exams: { exams: [{
  id: 'tr11', course: 'Türkçe', title: '1.1 Ara Değerlendirme Sınavı', rawTitle: '1.1 Ara Değerlendirme Sınavı',
  courseColor: '#9f1853', examNumber: null, date: '2026-12-22', endDate: null, allDay: true, status: 'upcoming',
  grade: null, relatedHomework: [], relatedContent: [], tur: 'ortak_sinav', konular: [], kaynaklar: [], senaryo,
}], stats: { upcoming: 1, past: 0, averageGrade: null } } })

test('Sınavlar kartı "Kapsam kılavuzu"na bağlanır; senaryo duyurulmuşsa o senaryoyla', async ({ page }) => {
  await mock(page, { ...LIVE, ...sinav(blok('dogrulandi', 4)) })
  await page.goto('/sinavlar')
  await page.getByRole('button', { name: 'Detaylar' }).first().click()
  await expect(page.locator('.meb-senaryo').getByRole('link', { name: 'Kapsam kılavuzu' }))
    .toHaveAttribute('href', '/hazirlik/turkce/1?senaryo=4')
})

test('Sınavlar kartı: senaryo belirtilmediyse olası kılavuza bağlanır (K8)', async ({ page }) => {
  await mock(page, { ...LIVE, ...sinav(blok('belirtilmedi', null)) })
  await page.goto('/sinavlar')
  await page.getByRole('button', { name: 'Detaylar' }).first().click()
  await expect(page.locator('.meb-senaryo').getByRole('link', { name: 'Kapsam kılavuzu' })).toHaveAttribute('href', '/hazirlik/turkce/1')
})

test('Dersler sekmesi "MEB senaryoları"na bağlanır', async ({ page }) => {
  await mock(page, LIVE)
  await page.goto('/dersler')
  const panel = page.getByRole('tabpanel')
  await expect(panel.getByRole('link', { name: 'MEB senaryoları' })).toHaveAttribute('href', /^\/hazirlik\/(matematik|turkce|fen-bilimleri)$/)
})
```

- [ ] **Step 2: Koş, düştüğünü gör**

Run: `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-hazirligi && env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_sinav_senaryo.py -k kapsam_kilavuzunun`
Expected: FAIL — satır gövdede yok.

- [ ] **Step 3: Araç metnine satırı ekle**

`src/sinav_senaryo.py`'de `arac_metni` içinde `f"Bu tablo {k['ogretim_yili']} {k['donem']}. dönem ortak yazılıları içindir."]` satırının hemen altına:

```python
    if ders in DERS_ANAHTARLARI:
        # Sınav Hazırlığı girişi (spec 2026-10-25 §3.4): model okura kılavuzun yerini söyleyebilir.
        satirlar.append(f"Kapsam kılavuzu panoda: Sınav Hazırlığı › {ders} › {no}. yazılı "
                        f"(/hazirlik/{DERS_ANAHTARLARI[ders]}/{no}).")
```

- [ ] **Step 4: Kart ve sekme bağlantıları**

`dashboard/src/components/SinavKarti.tsx` — içe aktarmalara `import { dersAnahtari, kilavuzAdresi } from '../hazirlik/hazirlik'`; `MebSenaryoBolumu`'nda `const g = senaryoGorunumu(exam.senaryo)` satırının altına:

```tsx
  // Sınav Hazırlığı girişi (spec 2026-10-25 §3.4): ülke geneli yazılının kılavuzu yok, ders sayfası açılır.
  const anahtar = dersAnahtari(exam.senaryo.ders)
  const kilavuz = anahtar === null ? null : exam.senaryo.durum === 'ulke_geneli'
    ? `/hazirlik/${anahtar}?sinav=${exam.senaryo.sinav_no}`
    : kilavuzAdresi(anahtar, exam.senaryo.sinav_no, exam.senaryo.senaryo)
```

ve "MEB tablosu" bağlantısının `</p>`'sinden sonra:

```tsx
      {kilavuz && <p className="meb-senaryo__alt"><IcBaglanti href={kilavuz} size="sm">Kapsam kılavuzu</IcBaglanti></p>}
```

`dashboard/src/components/CourseContent.tsx` — içe aktarmalara `import IcBaglanti from './patterns/IcBaglanti'` ve `import { dersAnahtari } from '../hazirlik/hazirlik'`; `<TabPanel key={name}>`'in hemen içine:

```tsx
                {/* Sınav Hazırlığı girişi (spec 2026-10-25 §3.4): dersin MEB senaryoları ve kılavuzu. */}
                {dersAnahtari(name) && (
                  <p className="course-content__senaryo"><IcBaglanti href={`/hazirlik/${dersAnahtari(name)}`} size="sm">MEB senaryoları</IcBaglanti></p>
                )}
```

- [ ] **Step 5: Kapılar, e2e ve görsel taban**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-hazirligi && env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_sinav_senaryo.py tests/test_assistant_sinav_senaryosu.py
cd dashboard && npm run lint && npm run test:birim && npm run build; echo "pano: $?"
TEDY_E2E_PORT=8341 TEDY_E2E_PYTHON=/mnt/thunderbolt/workspaces/TED/.venv/bin/python env -u ANTHROPIC_API_KEY npx playwright test --project= hazirlik-giris sinav-senaryo dersler gorsel-regresyon aria-yapisi tasarim-denetimi ibm-erisilebilirlik
```

Expected: Python PASS; pano 0; `hazirlik-giris` 3 test PASS; `gorsel-regresyon › dersler looks as it did` (masaüstü ve telefon) düşer — yalnız "MEB senaryoları" satırı (plan yazılırken ölçüldü). Farkı `test-results/…-diff.png`'de gördükten sonra:

```bash
TEDY_E2E_PORT=8341 TEDY_E2E_PYTHON=/mnt/thunderbolt/workspaces/TED/.venv/bin/python env -u ANTHROPIC_API_KEY npx playwright test --project= gorsel-regresyon -g "dersler looks" --update-snapshots
```

- [ ] **Step 6: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-hazirligi
git log --oneline -3 && git status --short
git add src/sinav_senaryo.py tests/test_sinav_senaryo.py dashboard/src/components/SinavKarti.tsx dashboard/src/components/CourseContent.tsx \
  dashboard/tests/e2e/hazirlik-giris.spec.ts dashboard/tests/e2e/gorsel-regresyon.spec.ts-snapshots/dersler-masaustu.png \
  dashboard/tests/e2e/gorsel-regresyon.spec.ts-snapshots/dersler-telefon.png
git commit -m "$(cat <<'EOF'
feat(sinav-hazirligi): giriş noktaları — Sınavlar kartında kapsam kılavuzu, Dersler'de MEB senaryoları

Kart duyurulan senaryonun kılavuzuna, duyuru yoksa olası kılavuza, ülke genelinde ders sayfasına bağlanır;
asistanın sinav_senaryosu aracı kılavuzun yerini söyler. Dersler görsel tabanı yeni satır için güncellendi.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 13: PDF hattı I — baskı görünümü gerçek kılavuzu çizer, yoklama belgesi kalkar, kapılar gerçek modelle

**Files:**
- Create: `dashboard/src/baski/sorgu.ts`
- Modify: `dashboard/src/baski/main.tsx` (son hâli)
- Delete: `dashboard/src/baski/YoklamaBelgesi.tsx`
- Test: `dashboard/tests/baski-sorgu.test.ts`, `dashboard/tests/e2e/hazirlik-baski.spec.ts`

**Interfaces:**
- Consumes: Görev 1'in `sayfala`, `sayfa.css`, `baski.scss`, `kilavuz-pdf.mjs`; Görev 9–11'in `KilavuzBelgesi`, `belge.ustBilgi`, `belge.damgaMetni`, `hazirlik.modelAdresi`; Görev 2'nin `scripts/kilavuz_pdf_kapilari.py`.
- Produces: `baskiSorgusuCoz(arama) -> {ders, sinav, senaryo, secenekler, duz} | null`; baskı adresi `/baski.html?ders=<anahtar>&sinav=1|2[&senaryo=N][&ebeveyn=1][&isaret=0][&duz=1]` (Görev 14'ün "A4 önizleme"si ve sunucu basımı bunu açar); belge başlığı Paged.js yolunda `ustBilgi`, düz yolda `ustBilgi — damgaMetni`.

- [ ] **Step 1: Başarısız testleri yaz**

`dashboard/tests/baski-sorgu.test.ts`:

```ts
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { baskiSorgusuCoz } from '../src/baski/sorgu.ts'

test('baskı adresi çözülür; seçenekler varsayılanla', () => {
  assert.deepEqual(baskiSorgusuCoz('?ders=fen-bilimleri&sinav=1'),
    { ders: 'fen-bilimleri', sinav: 1, senaryo: null, secenekler: { ebeveyn: false, isaret: true }, duz: false })
  assert.deepEqual(baskiSorgusuCoz('?ders=fen-bilimleri&sinav=2&senaryo=3&ebeveyn=1&isaret=0&duz=1'),
    { ders: 'fen-bilimleri', sinav: 2, senaryo: 3, secenekler: { ebeveyn: true, isaret: false }, duz: true })
  assert.equal(baskiSorgusuCoz('?ders=fen-bilimleri&sinav=3'), null)
  assert.equal(baskiSorgusuCoz('?ders=../x&sinav=1'), null)
  assert.equal(baskiSorgusuCoz('?yoklama=1'), null)
  assert.equal(baskiSorgusuCoz('?ders=fen-bilimleri&sinav=1&senaryo=abc')?.senaryo, null)
})
```

`dashboard/tests/e2e/hazirlik-baski.spec.ts`:

```ts
import { test, expect } from '@playwright/test'
import { KILAVUZ, fikstur, json } from './_hazirlik'

test.use({ timezoneId: 'Europe/Istanbul', locale: 'tr-TR' })

// Baskı görünümü (spec §5.1–5.2, plan Görev 13): aynı KilavuzBelgesi kâğıt kipinde; Paged.js sayfalar.
async function bekle(page: import('@playwright/test').Page) {
  await page.waitForFunction(() => {
    const w = window as unknown as { __KILAVUZ_HAZIR__?: unknown; __KILAVUZ_HATA__?: unknown }
    return w.__KILAVUZ_HAZIR__ || w.__KILAVUZ_HATA__
  })
  return page.evaluate(() => {
    const w = window as unknown as { __KILAVUZ_HAZIR__?: { sayfa: number }; __KILAVUZ_HATA__?: string }
    return { hazir: w.__KILAVUZ_HAZIR__ ?? null, hata: w.__KILAVUZ_HATA__ ?? null }
  })
}

test('Paged.js yolu: sayfalar, gerçek İçindekiler numarası, etkileşimsiz kâğıt (K5, K11)', async ({ page }) => {
  await page.route(KILAVUZ('fen-bilimleri', 1), r => r.fulfill(json(fikstur('fen-bilimleri-1-kilavuz'))))
  await page.goto('/baski.html?ders=fen-bilimleri&sinav=1')
  const s = await bekle(page)
  expect(s.hata).toBeNull()
  expect(s.hazir!.sayfa).toBeGreaterThan(2)
  await expect(page.locator('.pagedjs_page')).toHaveCount(s.hazir!.sayfa)
  await expect(page.locator('.kilavuz-icindekiler__baglanti').first()).toHaveText('Özet')
  await expect(page.locator('input[type="checkbox"]')).toHaveCount(0)
  await expect(page.locator('.kilavuz-isaret__kutu')).not.toHaveCount(0)
  expect(await page.title()).toBe('Fen Bilimleri · 1. yazılı · 2. senaryo')
})

test('düz yol: Paged.js çalışmaz, başlık damgayı taşır', async ({ page }) => {
  await page.route(KILAVUZ('fen-bilimleri', 1), r => r.fulfill(json(fikstur('fen-bilimleri-1-kilavuz'))))
  await page.goto('/baski.html?ders=fen-bilimleri&sinav=1&duz=1')
  const s = await bekle(page)
  expect(s.hazir).toEqual({ sayfa: 0 })
  await expect(page.locator('article.kilavuz-belge--baski')).toBeVisible()
  await expect(page.locator('.pagedjs_page')).toHaveCount(0)
  expect(await page.title()).toMatch(/^Fen Bilimleri · 1\. yazılı · 2\. senaryo — TEDY · MEB tablosu 10\.09\.2026/)
})

test('model alınamazsa sinyal hatadır (basım betiği 3 ile çıkar)', async ({ page }) => {
  await page.route(KILAVUZ('fen-bilimleri', 1), r => r.fulfill(json({ error: 'bilinmeyen_senaryo' }, 404)))
  await page.goto('/baski.html?ders=fen-bilimleri&sinav=1&senaryo=9')
  expect((await bekle(page)).hata).toBe('Kılavuz alınamadı (HTTP 404).')
})
```

- [ ] **Step 2: Birim testini koş, düştüğünü gör**

Run: `cd dashboard && node --test tests/baski-sorgu.test.ts`
Expected: FAIL — `Cannot find module '…/src/baski/sorgu.ts'`.

- [ ] **Step 3: Sorgu çözücüsü ve baskı girişinin son hâli; yoklama belgesini sil**

`dashboard/src/baski/sorgu.ts`:

```ts
// Baskı adresinin çözümü (plan Görev 13): /baski.html?ders=<anahtar>&sinav=1|2[&senaryo=N][&ebeveyn=1][&isaret=0][&duz=1]
import type { PdfSecenekleri } from '../hazirlik/tipler.ts'

export interface BaskiSorgusu {
  ders: string
  sinav: number
  senaryo: number | null
  secenekler: PdfSecenekleri
  duz: boolean
}

const ANAHTAR = /^[a-z]+(?:-[a-z]+)*$/

export function baskiSorgusuCoz(arama: string): BaskiSorgusu | null {
  const p = new URLSearchParams(arama)
  const ders = p.get('ders') ?? ''
  const sinav = p.get('sinav')
  if (!ANAHTAR.test(ders) || (sinav !== '1' && sinav !== '2')) return null
  const s = p.get('senaryo')
  return {
    ders, sinav: Number(sinav), senaryo: s && /^\d{1,2}$/.test(s) ? Number(s) : null,
    secenekler: { ebeveyn: p.get('ebeveyn') === '1', isaret: p.get('isaret') !== '0' }, duz: p.get('duz') === '1',
  }
}
```

`dashboard/src/baski/main.tsx` (tamamen):

```tsx
import { createRoot } from 'react-dom/client'
import { flushSync } from 'react-dom'
import { Theme } from '@carbon/react'
import KilavuzBelgesi from '../hazirlik/KilavuzBelgesi'
import { damgaMetni, ustBilgi } from '../hazirlik/belge'
import { modelAdresi } from '../hazirlik/hazirlik'
import type { KilavuzModeli } from '../hazirlik/tipler'
import { baskiSorgusuCoz } from './sorgu'
import { sayfala } from './sayfalama'
import './baski.scss'

declare global {
  interface Window { __KILAVUZ_HAZIR__?: { sayfa: number }; __KILAVUZ_HATA__?: string }
}

/** Baskı görünümü (spec §5.1, plan kararı 1): ekrandaki KilavuzBelgesi kâğıt kipinde; model API'den (tarayıcıda oturum
 *  çereziyle, sunucuda kilavuz-pdf.mjs'in sahte kökünden). Hazır olunca kilavuz-pdf.mjs'e sinyal verir. */
async function baslat(): Promise<void> {
  const s = baskiSorgusuCoz(location.search)
  if (!s) throw new Error('Baskı adresi eksik: ?ders=<ders>&sinav=1|2 gerekli.')
  const r = await fetch(modelAdresi(s.ders, s.sinav, s.senaryo, s.secenekler), { credentials: 'include' })
  if (!r.ok) throw new Error(`Kılavuz alınamadı (HTTP ${r.status}).`)
  const m = await r.json() as KilavuzModeli
  // Düz yolda (yedek) Chrome'un üst bilgisi belge başlığını basar: damga da başlığa girer (K5 B metni, K12).
  document.title = s.duz ? `${ustBilgi(m)} — ${damgaMetni(m)}` : ustBilgi(m)
  const kaynak = document.getElementById('kaynak')!
  flushSync(() => createRoot(kaynak).render(<Theme theme="white"><KilavuzBelgesi model={m} kip="baski" /></Theme>))
  await document.fonts.ready
  window.__KILAVUZ_HAZIR__ = { sayfa: s.duz ? 0 : await sayfala(kaynak) }
}

baslat().catch(e => { window.__KILAVUZ_HATA__ = e instanceof Error ? e.message : String(e) })
```

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-hazirligi && git rm dashboard/src/baski/YoklamaBelgesi.tsx
```

`scripts/kilavuz_pdf_kapilari.py`'nin yoklama sabitleri (`YOKLAMA_BASLIKLARI`, `YOKLAMA_ICINDEKILER`) kalır: `--model` verilmeden koşulduğunda baskı sayfası artık "Baskı adresi eksik" hatası verir ve betik "basılamadı" yazar — yoklama Görev 2'de kaydedilmiştir; bundan sonra betik hep `--model` ile koşulur.

- [ ] **Step 4: Birim ve e2e**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-hazirligi/dashboard
node --test tests/baski-sorgu.test.ts
npm run lint && npm run test:birim && npm run build; echo "pano: $?"
TEDY_E2E_PORT=8341 TEDY_E2E_PYTHON=/mnt/thunderbolt/workspaces/TED/.venv/bin/python env -u ANTHROPIC_API_KEY npx playwright test --project= hazirlik-baski
```

Expected: PASS; `hazirlik-baski` 3 test (Paged.js sayfaları ve gerçek İçindekiler, düz yol, hata sinyali).

- [ ] **Step 5: Gerçek Fen modeliyle kanun kapıları (K1, K3, K5, K10, K12)**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-hazirligi
rm -rf /tmp/tedy-kilavuz-kapi
env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -I scripts/kilavuz_pdf_kapilari.py --dist dashboard-dist \
  --cikti /tmp/tedy-kilavuz-kapi --model dashboard/tests/e2e/fixtures/hazirlik/fen-bilimleri-1-kilavuz.json --sorgu 'ders=fen-bilimleri&sinav=1'
echo "çıkış: $?"
pdftotext -layout /tmp/tedy-kilavuz-kapi/paged.pdf - | sed -n 1,40p
```

Expected: çıkış 0; ana yolun satırında "Kusurlar: yok" (plan yazılırken ölçüldü: A 5 sayfa, 3,2 s, 178 MB, yalnız Plex; B 4 sayfa). Metinde kapakta üst bilgi yok, ikinci sayfada "İçindekiler" ve her girdinin sağında sayfa numarası, alt bilgide "TEDY · MEB tablosu 10.09.2026 · … s. n/5". Ana yolda kusur çıkarsa iş durur; kusur metni hangi kanun maddesini söylüyorsa (`yetim başlık` → `sayfa.css` `break-after`, `Plex dışı yazı tipi` → ☐ benzeri karakter, `başlık PDF metninde yok` → `KilavuzBelgesi`) orası düzeltilir ve adım yeniden koşulur.

- [ ] **Step 6: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-hazirligi
git log --oneline -3 && git status --short
git add dashboard/src/baski/sorgu.ts dashboard/src/baski/main.tsx dashboard/tests/baski-sorgu.test.ts dashboard/tests/e2e/hazirlik-baski.spec.ts
git commit -m "$(cat <<'EOF'
feat(sinav-hazirligi): baskı görünümü gerçek kılavuzu çizer; yoklama belgesi kalktı

baski.html aynı KilavuzBelgesi'ni kâğıt kipinde çizer (K11), modeli API'den alır ve Paged.js ile sayfalar;
gerçek Fen modeliyle kanun kapıları geçti (gömülü Plex, etiket, dil, yer imi, İçindekiler numaraları).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 14: PDF hattı II — sunucu basımı (yuva, zaman aşımı, yedek yol, önbellek), PDF ucu, seçenek penceresi, A4 önizleme

**Files:**
- Create: `src/hazirlik_pdf.py`
- Modify: `src/dashboard_api.py` (`PUT /api/hazirlik/isaret`'in hemen önüne PDF ucu)
- Create: `dashboard/src/hazirlik/pdfIndir.ts`, `dashboard/src/hazirlik/PdfSecenekleri.tsx`
- Modify: `dashboard/src/hazirlik/HazirlikDersSayfasi.tsx`, `dashboard/src/hazirlik/KilavuzSayfasi.tsx` (son hâlleri)
- Test: `tests/test_hazirlik_pdf.py`, `tests/test_hazirlik_api.py` (ekleme), `dashboard/tests/e2e/hazirlik-pdf.spec.ts`

**Interfaces:**
- Consumes: Görev 1'in `kilavuz-pdf.mjs` (çıkış kodları 0/2/3/4, `--sure` ms); Görev 2'nin kararı (`ANA_YOL`); Görev 8'in `_hazirlik_modeli`; Görev 9'un `pdfAdresi`, `baskiAdresi`, `secenekleriOku/Yaz`.
- Produces: `hazirlik_pdf`: `ESZAMANLI = 2`, `SURE_SN = 90`, `ONBELLEK_SINIRI = 60`, `ANA_YOL`, `Mesgul`, `Uretilemedi`, `Zamanasimi`, `BasimHatasi`, `baski_imzasi(dist)`, `onbellek_anahtari(model, sorgu, imza)`, `node_calistir(model, sorgu, *, duz, sure, dist, betik=BETIK, yorumlayici="node") -> bytes`, `pdf_getir(model, sorgu, *, dizin, dist, calistir=node_calistir, ana_yol=None) -> Path`; uç `GET /api/hazirlik/<anahtar>/<int:sinav_no>/kilavuz.pdf?senaryo=N&ebeveyn=1&isaret=0` → `application/pdf` ek (ad `kapsam-kilavuzu-<anahtar>-<no>-<senaryo|olasi>.pdf`), 429 `{error: "mesgul", mesaj}` + `Retry-After: 30`, 503 `{error: "pdf_uretilemedi", mesaj}`; `pdfIndir(adres) -> Promise<string | null>`; `PdfSecenekleri({anahtar, no, senaryo, kapat})`.
- Eşzamanlılık bütçesi: gunicorn 2 işçi × 4 iş parçacığı, `--timeout 360`; en kötü istek 2 × 90 s (ana + yedek) < 360 s.

- [ ] **Step 1: Başarısız testleri yaz**

`tests/test_hazirlik_pdf.py`:

```python
"""Kılavuz PDF hattı (plan Görev 14): yuva, zaman aşımında süreç grubunun öldürülmesi, yedek yol, önbellek, uç."""
import fcntl
import json
import os
import sys
import time
from pathlib import Path

import pytest

from src import hazirlik_pdf as hp

MODEL = {"icerik_ozeti": "a" * 64, "senaryo": 2, "secenekler": {"ebeveyn": False, "isaret": True}}
SORGU = {"ders": "fen-bilimleri", "sinav": "1", "senaryo": "2"}


@pytest.fixture
def dist(tmp_path):
    d = tmp_path / "dist"
    d.mkdir()
    (d / "baski.html").write_text("<html>baski</html>", encoding="utf-8")
    return d


class SahteBasim:
    def __init__(self, *sonuclar):
        self.sonuclar, self.cagrilar = list(sonuclar), []

    def __call__(self, model, sorgu, *, duz, sure, dist):
        self.cagrilar.append(duz)
        s = self.sonuclar.pop(0)
        if isinstance(s, Exception):
            raise s
        return s


def test_onbellek_ikinci_istekte_basmaz(tmp_path, dist):
    basim = SahteBasim(b"%PDF-1")
    a = hp.pdf_getir(MODEL, SORGU, dizin=tmp_path / "o", dist=dist, calistir=basim)
    b = hp.pdf_getir(MODEL, SORGU, dizin=tmp_path / "o", dist=dist, calistir=basim)
    assert a == b and a.read_bytes() == b"%PDF-1" and basim.cagrilar == [False]
    (dist / "baski.html").write_text("<html>yeni derleme</html>", encoding="utf-8")
    basim.sonuclar.append(b"%PDF-2")
    assert hp.pdf_getir(MODEL, SORGU, dizin=tmp_path / "o", dist=dist, calistir=basim).read_bytes() == b"%PDF-2"


def test_ana_yol_duserse_yedek_yol_denenir(tmp_path, dist):
    """Review Focus: Paged.js yolu zaman aşımına düşerse düz Chrome baskısı denenir."""
    basim = SahteBasim(hp.Zamanasimi("90 sn"), b"%PDF-duz")
    yol = hp.pdf_getir(MODEL, SORGU, dizin=tmp_path, dist=dist, calistir=basim)
    assert basim.cagrilar == [False, True] and yol.read_bytes() == b"%PDF-duz"


def test_iki_yol_duserse_uretilemedi_ve_dosya_yazilmaz(tmp_path, dist):
    basim = SahteBasim(hp.BasimHatasi("sayfa hatası"), hp.Zamanasimi("90 sn"))
    with pytest.raises(hp.Uretilemedi):
        hp.pdf_getir(MODEL, SORGU, dizin=tmp_path, dist=dist, calistir=basim)
    assert list(tmp_path.glob("*.pdf")) == []


def test_ana_yol_duz_ise_yalniz_duz(tmp_path, dist):
    basim = SahteBasim(b"%PDF")
    hp.pdf_getir(MODEL, SORGU, dizin=tmp_path, dist=dist, calistir=basim, ana_yol="duz")
    assert basim.cagrilar == [True]


def test_yuvalar_doluyken_mesgul(tmp_path, dist):
    """Review Focus: eşzamanlı istek sınırı aşılınca beklemeden Mesgul; basım çağrılmaz."""
    tutulan = []
    for i in range(hp.ESZAMANLI):
        f = open(tmp_path / f".yuva-{i}", "w")
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        tutulan.append(f)
    basim = SahteBasim(b"%PDF")
    with pytest.raises(hp.Mesgul):
        hp.pdf_getir(MODEL, SORGU, dizin=tmp_path, dist=dist, calistir=basim)
    assert basim.cagrilar == []
    for f in tutulan:
        f.close()
    assert hp.pdf_getir(MODEL, SORGU, dizin=tmp_path, dist=dist, calistir=basim).exists()


def test_onbellek_en_yeni_dosyalari_tutar(tmp_path, monkeypatch):
    monkeypatch.setattr(hp, "ONBELLEK_SINIRI", 2)
    for i in range(3):
        (tmp_path / f"{i}.pdf").write_bytes(b"%PDF")
        os.utime(tmp_path / f"{i}.pdf", (1000 + i, 1000 + i))
    hp._buda(tmp_path)
    assert sorted(p.name for p in tmp_path.glob("*.pdf")) == ["1.pdf", "2.pdf"]


SAHTE_BETIK = r'''
import json, subprocess, sys, time
a = sys.argv[1:]
deger = lambda k: a[a.index(k) + 1]
if "--uyu" in deger("--sorgu"):
    torun = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    open(deger("--dist") + "/torun.pid", "w").write(str(torun.pid))
    time.sleep(60)
open(deger("--cikti"), "wb").write(b"%PDF-sahte " + json.dumps(a).encode())
'''


def _yasiyor(pid):
    try:
        return Path(f"/proc/{pid}/stat").read_text().split()[2] != "Z"
    except FileNotFoundError:
        return False


def test_basim_betigi_argumanlari_ve_ciktisi(tmp_path, dist):
    betik = tmp_path / "sahte.py"
    betik.write_text(SAHTE_BETIK, encoding="utf-8")
    veri = hp.node_calistir(MODEL, SORGU, duz=True, sure=20, dist=dist, betik=betik, yorumlayici=sys.executable)
    assert veri.startswith(b"%PDF-sahte ")
    argv = json.loads(veri[len(b"%PDF-sahte "):])
    assert argv[argv.index("--sorgu") + 1] == "ders=fen-bilimleri&sinav=1&senaryo=2"
    assert argv[argv.index("--dist") + 1] == str(dist) and "--duz" in argv
    assert argv[argv.index("--sure") + 1] == "16000"


def test_zaman_asiminda_surec_grubu_oldurulur(tmp_path, dist):
    """Review Focus: takılan basım süreç grubuyla öldürülür; torun süreç (Chrome'un yerine) yaşamaz."""
    betik = tmp_path / "sahte.py"
    betik.write_text(SAHTE_BETIK, encoding="utf-8")
    with pytest.raises(hp.Zamanasimi):
        hp.node_calistir(MODEL, {"sorgu": "--uyu"}, duz=False, sure=2, dist=dist, betik=betik, yorumlayici=sys.executable)
    pid = int((dist / "torun.pid").read_text())
    son = time.monotonic() + 5
    while _yasiyor(pid) and time.monotonic() < son:
        time.sleep(0.05)
    assert not _yasiyor(pid)
```

`tests/test_hazirlik_api.py`'nin sonuna:

```python
def test_pdf_ucu_dosya_mesgul_429_uretilemedi_503(c, monkeypatch, tmp_path):
    """Review Focus: PDF zaman aşımı/eşzamanlılık uca açık iletiyle yansır; başarıda indirilen dosya."""
    from src import hazirlik_pdf
    giris(c, AILE)
    pdf = tmp_path / "k.pdf"
    pdf.write_bytes(b"%PDF-1.7 deneme")
    gelen = {}

    def basari(model, sorgu, *, dizin, dist):
        gelen.update(sorgu=sorgu, dizin=dizin)
        return pdf
    monkeypatch.setattr(hazirlik_pdf, "pdf_getir", basari)
    r = c.get("/api/hazirlik/fen-bilimleri/1/kilavuz.pdf?ebeveyn=1")
    assert (r.status_code, r.mimetype, r.data) == (200, "application/pdf", b"%PDF-1.7 deneme")
    assert 'filename=kapsam-kilavuzu-fen-bilimleri-1-2.pdf' in r.headers["Content-Disposition"]
    assert gelen["sorgu"] == {"ders": "fen-bilimleri", "sinav": "1", "ebeveyn": "1", "isaret": "1", "senaryo": "2"}
    assert str(gelen["dizin"]).endswith("hazirlik_pdf")

    def mesgul(*a, **k):
        raise hazirlik_pdf.Mesgul()
    monkeypatch.setattr(hazirlik_pdf, "pdf_getir", mesgul)
    r = c.get("/api/hazirlik/fen-bilimleri/1/kilavuz.pdf")
    assert (r.status_code, r.headers["Retry-After"], r.get_json()["error"]) == (429, "30", "mesgul")

    def dustu(*a, **k):
        raise hazirlik_pdf.Uretilemedi("iki yol da düştü")
    monkeypatch.setattr(hazirlik_pdf, "pdf_getir", dustu)
    r = c.get("/api/hazirlik/fen-bilimleri/1/kilavuz.pdf")
    assert (r.status_code, r.get_json()["error"]) == (503, "pdf_uretilemedi")
    assert c.get("/api/hazirlik/fen-bilimleri/1/kilavuz.pdf?senaryo=9").status_code == 404


def test_okuyucu_pdf_alamaz(c):
    giris(c, OKUYUCU)
    assert c.get("/api/hazirlik/fen-bilimleri/1/kilavuz.pdf").status_code == 403
```

`dashboard/tests/e2e/hazirlik-pdf.spec.ts`:

```ts
import { test, expect } from '@playwright/test'
import { DERS, KILAVUZ, PDF, fikstur, hazirlikAc, json } from './_hazirlik'

test.use({ timezoneId: 'Europe/Istanbul', locale: 'tr-TR' })

test('PDF seçenekleri: indirme, seçim kişi başına hatırlanır (spec §4)', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik/fen-bilimleri/1', [[KILAVUZ('fen-bilimleri', 1), fikstur('fen-bilimleri-1-kilavuz')]])
  const istekler: string[] = []
  await page.route(PDF('fen-bilimleri', 1), r => {
    istekler.push(r.request().url())
    return r.fulfill({ status: 200, contentType: 'application/pdf', body: '%PDF-1.7 deneme',
      headers: { 'Content-Disposition': 'attachment; filename=kapsam-kilavuzu-fen-bilimleri-1-2.pdf' } })
  })
  await page.getByRole('button', { name: 'PDF olarak indir' }).click()
  const pencere = page.getByRole('dialog')
  await expect(pencere.getByRole('heading', { name: 'Kılavuzu PDF olarak indir' })).toBeVisible()
  await expect(pencere.getByRole('checkbox', { name: 'Ebeveyn özetini başa ekle' })).not.toBeChecked()
  await expect(pencere.getByRole('checkbox', { name: 'Hazırlık işaretlerimi ekle' })).toBeChecked()
  await expect(pencere.getByText(/yapay zekâ/i)).toHaveCount(0)        // YZ seçenekleri Plan 2'de (B42)
  await pencere.getByText('Ebeveyn özetini başa ekle').click()
  const indirme = page.waitForEvent('download')
  await pencere.getByRole('button', { name: "PDF'i indir" }).click()
  expect((await indirme).suggestedFilename()).toBe('kapsam-kilavuzu-fen-bilimleri-1-2.pdf')
  expect(istekler[0]).toMatch(/kilavuz\.pdf\?senaryo=2&ebeveyn=1&isaret=1$/)
  await expect(pencere).toHaveCount(0)
  await page.getByRole('button', { name: 'PDF olarak indir' }).click()
  await expect(page.getByRole('checkbox', { name: 'Ebeveyn özetini başa ekle' })).toBeChecked()
})

test('PDF hazırlanamazsa sunucunun cümlesi pencerede görünür (429 / 503)', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik/fen-bilimleri/1', [[KILAVUZ('fen-bilimleri', 1), fikstur('fen-bilimleri-1-kilavuz')]])
  await page.route(PDF('fen-bilimleri', 1), r => r.fulfill(json({ error: 'mesgul',
    mesaj: 'Şu an başka bir kılavuz hazırlanıyor; bir dakika sonra yeniden dene.' }, 429)))
  await page.getByRole('button', { name: 'PDF olarak indir' }).click()
  await page.getByRole('button', { name: "PDF'i indir" }).click()
  await expect(page.getByRole('dialog')).toContainText('Şu an başka bir kılavuz hazırlanıyor; bir dakika sonra yeniden dene.')
})

test('A4 önizleme baskı görünümünü yeni sekmede açar; ders sayfasında da PDF düğmesi var', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik/fen-bilimleri/1', [[KILAVUZ('fen-bilimleri', 1), fikstur('fen-bilimleri-1-kilavuz')],
    [DERS('fen-bilimleri', 1), fikstur('fen-bilimleri-1')]])
  const onizleme = page.getByRole('link', { name: 'A4 önizleme' })
  await expect(onizleme).toHaveAttribute('href', '/baski.html?senaryo=2&ebeveyn=0&isaret=1&ders=fen-bilimleri&sinav=1')
  await expect(onizleme).toHaveAttribute('target', '_blank')
  await page.goto('/hazirlik/fen-bilimleri?sinav=1')
  await expect(page.getByRole('button', { name: 'PDF olarak indir' })).toBeVisible()
})
```

- [ ] **Step 2: Koş, düştüğünü gör**

Run: `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-hazirligi && env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_hazirlik_pdf.py tests/test_hazirlik_api.py`
Expected: FAIL — `ImportError: cannot import name 'hazirlik_pdf'`.

- [ ] **Step 3: PDF hattını yaz**

`src/hazirlik_pdf.py` (`ANA_YOL` Görev 2'nin kararıdır; B seçildiyse `"duz"` yazılır):

```python
"""Kapsam kılavuzu A4 PDF hattı (spec 2026-10-25 §5.3, plan Görev 14).

`dashboard/scripts/kilavuz-pdf.mjs` (pano node_modules'undaki Playwright, Chrome kanalı) baskı görünümünü ağsız
basar; bu modül yuvayı, zaman aşımını, yedek yolu ve önbelleği yönetir:
- Eşzamanlılık: `ESZAMANLI` yuva, `fcntl.flock` ile (iki gunicorn işçisi arasında da geçerli); yuva yoksa
  beklemeden `Mesgul` (API 429 + Retry-After).
- Zaman aşımı: Node süreci kendi süreç grubunda başlar; süre dolunca grup SIGKILL alır (takılan Chrome yığılmaz).
- Yedek yol: ana yol (Görev 2 kararı: `ANA_YOL`) düşerse düz Chrome baskısı; o da düşerse `Uretilemedi` (API 503).
- Önbellek: `output/hazirlik_pdf/<sha256>.pdf`; anahtar modelin `icerik_ozeti` + sorgu + baskı paketinin imzası
  (yeni derleme önbelleği kendiliğinden geçersiz kılar); en yeni `ONBELLEK_SINIRI` dosya kalır."""
from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
import signal
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlencode

KOK = Path(__file__).resolve().parents[1]
DASHBOARD_DIZINI = KOK / "dashboard"
BETIK = DASHBOARD_DIZINI / "scripts" / "kilavuz-pdf.mjs"
ESZAMANLI = 2
SURE_SN = 90
ONBELLEK_SINIRI = 60
ANA_YOL = "paged"          # Görev 2 yoklamasının kararı: "paged" (A) ya da "duz" (B)


class Mesgul(Exception):
    """Bütün basım yuvaları dolu."""


class Uretilemedi(Exception):
    """Ana yol da yedek yol da düştü."""


class Zamanasimi(Exception):
    pass


class BasimHatasi(Exception):
    pass


def baski_imzasi(dist: Path) -> str:
    try:
        return hashlib.sha256((Path(dist) / "baski.html").read_bytes()).hexdigest()[:16]
    except OSError:
        return "yok"


def onbellek_anahtari(model: dict, sorgu: dict, imza: str) -> str:
    govde = json.dumps({"m": model["icerik_ozeti"], "s": sorgu, "b": imza}, sort_keys=True)
    return hashlib.sha256(govde.encode("utf-8")).hexdigest()


def node_calistir(model: dict, sorgu: dict, *, duz: bool, sure: float, dist: Path, betik: Path = BETIK,
                  yorumlayici: str = "node") -> bytes:
    """Basım betiğini kendi süreç grubunda koşar; süre dolarsa grubu öldürür ve `Zamanasimi` yükseltir."""
    with tempfile.TemporaryDirectory(prefix="tedy-kilavuz-") as d:
        model_yolu = Path(d) / "model.json"
        model_yolu.write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
        cikti = Path(d) / "kilavuz.pdf"
        komut = [yorumlayici, str(betik), "--dist", str(dist), "--model", str(model_yolu), "--cikti", str(cikti),
                 "--sorgu", urlencode(sorgu), "--sure", str(max(1000, int(sure * 800)))]
        if duz:
            komut.append("--duz")
        p = subprocess.Popen(komut, cwd=str(DASHBOARD_DIZINI), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                             start_new_session=True)
        try:
            _, hata = p.communicate(timeout=sure)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(p.pid, signal.SIGKILL)
            p.communicate()
            raise Zamanasimi(f"basım {sure} sn'de bitmedi") from None
        if p.returncode != 0 or not cikti.exists():
            raise BasimHatasi((hata or b"").decode("utf-8", "replace")[-500:] or f"çıkış {p.returncode}")
        return cikti.read_bytes()


@contextlib.contextmanager
def _yuva(dizin: Path):
    dizin.mkdir(parents=True, exist_ok=True)
    for i in range(ESZAMANLI):
        f = open(dizin / f".yuva-{i}", "w")
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            f.close()
            continue
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
            f.close()
        return
    raise Mesgul("bütün basım yuvaları dolu")


def _buda(dizin: Path) -> None:
    pdfler = sorted(dizin.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)
    for p in pdfler[ONBELLEK_SINIRI:]:
        with contextlib.suppress(OSError):
            p.unlink()


def pdf_getir(model: dict, sorgu: dict, *, dizin: Path, dist: Path, calistir=node_calistir,
              ana_yol: str | None = None) -> Path:
    """Önbellekteki PDF ya da yeni basım. `Mesgul` / `Uretilemedi` yükseltebilir."""
    yol = Path(dizin) / f"{onbellek_anahtari(model, sorgu, baski_imzasi(dist))}.pdf"
    if yol.exists():
        return yol
    with _yuva(Path(dizin)):
        if yol.exists():
            return yol
        son_hata: Exception | None = None
        veri = None
        for duz in ([True] if (ana_yol or ANA_YOL) == "duz" else [False, True]):
            try:
                veri = calistir(model, sorgu, duz=duz, sure=SURE_SN, dist=dist)
                break
            except (Zamanasimi, BasimHatasi, OSError) as h:
                son_hata = h
        if veri is None:
            raise Uretilemedi(str(son_hata))
        gecici = yol.with_name(yol.name + ".tmp")
        gecici.write_bytes(veri)
        os.replace(gecici, yol)
    _buda(Path(dizin))
    return yol
```

`src/dashboard_api.py`'de `@app.route("/api/hazirlik/isaret", methods=["PUT"])` satırının hemen önüne:

```python
@app.route("/api/hazirlik/<anahtar>/<int:sinav_no>/kilavuz.pdf")
@require_auth
def hazirlik_kilavuz_pdf(anahtar, sinav_no):
    """A4 PDF (spec §5.3): aynı model, sunucudaki Chrome; yuva doluysa 429, iki yol da düşerse 503 (spec §7)."""
    from src import hazirlik_pdf
    model, hata = _hazirlik_modeli(anahtar, sinav_no)
    if hata:
        return hata
    sorgu = {"ders": anahtar, "sinav": str(sinav_no), "ebeveyn": "1" if model["secenekler"]["ebeveyn"] else "0",
             "isaret": "1" if model["secenekler"]["isaret"] else "0"}
    if model["senaryo"] is not None:
        sorgu["senaryo"] = str(model["senaryo"])
    try:
        yol = hazirlik_pdf.pdf_getir(model, sorgu, dizin=Path(OUTPUT_DIR) / "hazirlik_pdf", dist=Path(DIST_DIR))
    except hazirlik_pdf.Mesgul:
        yanit = jsonify({"error": "mesgul", "mesaj": "Şu an başka bir kılavuz hazırlanıyor; bir dakika sonra yeniden dene."})
        yanit.status_code = 429
        yanit.headers["Retry-After"] = "30"
        return yanit
    except hazirlik_pdf.Uretilemedi:
        app.logger.warning("kılavuz PDF'i üretilemedi: %s %s", anahtar, sinav_no, exc_info=True)
        return jsonify({"error": "pdf_uretilemedi",
                        "mesaj": "PDF hazırlanamadı. Ekrandaki kılavuzu tarayıcının yazdır komutuyla da kaydedebilirsin."}), 503
    ad = f"kapsam-kilavuzu-{anahtar}-{sinav_no}-{model['senaryo'] if model['senaryo'] is not None else 'olasi'}.pdf"
    return send_file(str(yol), mimetype="application/pdf", as_attachment=True, download_name=ad, max_age=0)
```

- [ ] **Step 4: Python testlerini koş, geçtiğini gör**

Run: `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-hazirligi && env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_hazirlik_pdf.py tests/test_hazirlik_api.py`
Expected: PASS (8 + 15 test; zaman aşımı testinde sahte betiğin torun süreci 5 sn içinde ölür).

- [ ] **Step 5: Gerçek Chrome'la zaman aşımı sonrası artık süreç kalmadığını ölç**

Playwright tarayıcıyı ayrı süreç grubunda başlatır; Node SIGKILL alınca Chrome'u boru kapanması bitirir. Bunu gerçek basımla ölç:

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-hazirligi
pgrep -fc '[r]emote-debugging-pipe' || true
env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -I -c "
import json, sys; sys.path.insert(0, '.')
from pathlib import Path
from src import hazirlik_pdf as hp
m = json.loads(Path('dashboard/tests/e2e/fixtures/hazirlik/fen-bilimleri-1-kilavuz.json').read_text())
try:
    hp.node_calistir(m, {'ders': 'fen-bilimleri', 'sinav': '1'}, duz=False, sure=1.0, dist=Path('dashboard-dist').resolve())
except hp.Zamanasimi as h:
    print('zaman aşımı:', h)"
for i in 1 2 3 4 5 6 7 8 9 10; do n=$(pgrep -fc '[r]emote-debugging-pipe' || true); [ "$n" = "0" ] && break; sleep 1; done; echo "kalan Chrome: $n"
```

Expected: "zaman aşımı: basım 1.0 sn'de bitmedi"; "kalan Chrome: 0" (ilk satırdaki sayı 0 değilse — başka bir oturumun tarayıcısı — son sayı ona eşit olmalı). Artık süreç kalırsa `node_calistir` zaman aşımında `pkill -KILL -f -- "--user-data-dir=<geçici dizin>"` benzeri ek temizlik ister: dur ve kullanıcıya ölçümü bildir.

- [ ] **Step 6: Seçenek penceresi ve düğmeler**

`dashboard/src/hazirlik/pdfIndir.ts`:

```ts
/** Kılavuz PDF'ini indirir (plan Görev 14). null: indirildi; dize: okura söylenecek cümle (sunucunun `mesaj`'ı ya da
 *  genel cümle; ham HTTP metni okura gitmez, D4). */
export async function pdfIndir(adres: string): Promise<string | null> {
  let r: Response
  try {
    r = await fetch(adres, { credentials: 'include' })
  } catch {
    return 'Bağlantı kurulamadı; yeniden dene.'
  }
  if (!r.ok) {
    try {
      const j = await r.json() as { mesaj?: unknown }
      return typeof j.mesaj === 'string' ? j.mesaj : 'PDF hazırlanamadı.'
    } catch {
      return 'PDF hazırlanamadı.'
    }
  }
  const blob = await r.blob()
  const ad = /filename="?([^";]+)"?/.exec(r.headers.get('Content-Disposition') ?? '')?.[1] ?? 'kapsam-kilavuzu.pdf'
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = ad
  document.body.append(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 60_000)
  return null
}
```

`dashboard/src/hazirlik/PdfSecenekleri.tsx`:

```tsx
import { useContext, useState } from 'react'
import { Checkbox, ComposedModal, InlineNotification, ModalBody, ModalFooter, ModalHeader } from '@carbon/react'
import { SessionContext } from '../contexts/session'
import { pdfAdresi, secenekleriOku, secenekleriYaz } from './hazirlik'
import { pdfIndir } from './pdfIndir'

/** PDF seçenekleri penceresi (spec §4): ebeveyn özeti ve hazırlık işaretleri; son seçim kişi başına hatırlanır.
 *  YZ ve prova seçenekleri Plan 2'dedir ve burada yoktur (yapılamayan eylem gizlenir, B42). Yalnız açıkken
 *  bağlanır: kapalı ComposedModal başlığını belge ağacında tutar. */
export default function PdfSecenekleri({ anahtar, no, senaryo, kapat }: {
  anahtar: string; no: number; senaryo: number | null; kapat: () => void
}) {
  const kisi = useContext(SessionContext)!
  const [s, setS] = useState(() => secenekleriOku(kisi.email, localStorage))
  const [hazirlaniyor, setHazirlaniyor] = useState(false)
  const [hata, setHata] = useState<string | null>(null)
  const indir = async () => {
    secenekleriYaz(kisi.email, s, localStorage)
    setHazirlaniyor(true)
    setHata(null)
    const sonuc = await pdfIndir(pdfAdresi(anahtar, no, senaryo, s))
    setHazirlaniyor(false)
    if (sonuc === null) kapat()
    else setHata(sonuc)
  }
  return (
    <ComposedModal open size="sm" onClose={() => { if (!hazirlaniyor) kapat() }}>
      <ModalHeader title="Kılavuzu PDF olarak indir" iconDescription="Kapat" />
      <ModalBody>
        <Checkbox id="pdf-ebeveyn" labelText="Ebeveyn özetini başa ekle" checked={s.ebeveyn}
          onChange={(_, { checked }) => setS({ ...s, ebeveyn: checked })} />
        <Checkbox id="pdf-isaret" labelText="Hazırlık işaretlerimi ekle" checked={s.isaret}
          onChange={(_, { checked }) => setS({ ...s, isaret: checked })} />
        {hata && <InlineNotification kind="error" lowContrast hideCloseButton statusIconDescription="Hata" title={hata} />}
      </ModalBody>
      <ModalFooter primaryButtonText="PDF'i indir" secondaryButtonText="Vazgeç"
        loadingStatus={hazirlaniyor ? 'active' : 'inactive'} loadingDescription="PDF hazırlanıyor…"
        loadingIconDescription="Hazırlanıyor" onRequestClose={() => { if (!hazirlaniyor) kapat() }}
        onRequestSubmit={() => { if (!hazirlaniyor) void indir() }}>{null}</ModalFooter>
    </ComposedModal>
  )
}
```

`dashboard/src/hazirlik/HazirlikDersSayfasi.tsx` (son hâli; Görev 10'dakine "PDF olarak indir" tertiary düğmesi ve pencere eklendi — B58: `kind="secondary"` yok):

```tsx
import { useCallback, useRef, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { Breadcrumb, BreadcrumbItem, Button, ContentSwitcher, InlineNotification, RadioButton, RadioButtonGroup,
         SkeletonText, Switch } from '@carbon/react'
import { useApi } from '../hooks/useApi'
import { apiHataCumlesi } from '../utils/apiHatasi'
import { subjectClass } from '../utils/subject'
import Kaydirilabilir from '../components/Kaydirilabilir'
import KarsilastirmaTablosu from './KarsilastirmaTablosu'
import CiktiAyrintisi from './CiktiAyrintisi'
import DurumGostergesi from './DurumGostergesi'
import PdfSecenekleri from './PdfSecenekleri'
import Uyarilar from './Uyarilar'
import { hazirlikUyarilari } from './belge'
import { kilavuzAdresi, sinavAdi, tarihMetni } from './hazirlik'
import type { DersOzeti } from './tipler'
import './Hazirlik.scss'

/** Duyurunun durumuna göre sayfanın tek bildirimi (spec §3.2): kesin yeşil ve öğretmenin sözü aynen. */
function DuyuruBildirimi({ oz }: { oz: DersOzeti }) {
  const d = oz.durum
  if (d.tur === 'kesin') {
    return <InlineNotification kind="success" lowContrast hideCloseButton statusIconDescription="Onay"
      title={`Okul ${d.senaryo}. senaryoyu duyurdu.`} subtitle={d.duyuru ? `«${d.duyuru}»` : undefined} />
  }
  if (d.tur === 'ulke_geneli') {
    return <InlineNotification kind="info" lowContrast hideCloseButton statusIconDescription="Bilgi"
      title="Bu yazılı ülke genelinde ortak yapılır; senaryo yok." subtitle={oz.not ?? undefined} />
  }
  if (d.tur === 'gecti') {
    return <InlineNotification kind="info" lowContrast hideCloseButton statusIconDescription="Bilgi" title="Bu yazılı geçti." />
  }
  if (d.uyari === 'senaryo_yok') {
    return <InlineNotification kind="warning" lowContrast hideCloseButton statusIconDescription="Uyarı"
      title={`Duyuru ${d.anilan.join(', ')}. senaryo diyor; MEB tablosunda bu yazılı için 1–${d.senaryo_sayisi} var.`} />
  }
  return <InlineNotification kind="info" lowContrast hideCloseButton statusIconDescription="Bilgi" title="Senaryo duyurulmadı."
    subtitle="Tablodan bir senaryo seçebilir ya da kılavuzu bütün senaryolarla açabilirsin." />
}

/** Ders sayfası (spec §3.2, taslak A "karşılaştırma tablosu"): yazılı seçici, duyuru, tablo, satır ayrıntısı,
 *  kılavuza geçiş. Kitap haritası olmayan ders senaryo verisiyle açılır (spec §7). */
export default function HazirlikDersSayfasi() {
  const { ders: anahtar = '' } = useParams()
  const [arama, setArama] = useSearchParams()
  const gezin = useNavigate()
  const no = arama.get('sinav') === '2' ? 2 : 1
  const { data: oz, loading, iskelet, hataTuru } = useApi<DersOzeti | null>(`/api/hazirlik/${anahtar}/${no}`, null)
  const [secili, setSecili] = useState<string | null>(null)
  const [secim, setSecim] = useState<string>('olasi')
  const [pdfAcik, setPdfAcik] = useState(false)
  const satirDugmesi = useRef<HTMLButtonElement | null>(null)
  const kapat = useCallback(() => { setSecili(null); satirDugmesi.current?.focus() }, [])
  if (loading) {
    return iskelet ? <section className="hazirlik-ders" aria-busy="true"><SkeletonText heading /><SkeletonText paragraph lineCount={6} /></section> : null
  }
  if (!oz) {
    const h = apiHataCumlesi(hataTuru ?? 'sunucu', 'Ders sayfası')
    return <section className="hazirlik-ders"><InlineNotification kind="error" lowContrast hideCloseButton statusIconDescription="Hata" title={h.baslik} subtitle={h.ayrinti} /></section>
  }
  const duyurulan = oz.duyurulan
  const secilen = duyurulan ?? (secim === 'olasi' ? null : Number(secim))
  const vurgu = secilen ?? (oz.durum.tur === 'gecti' ? oz.durum.senaryo : null)
  const kilavuz = kilavuzAdresi(anahtar, no, duyurulan === null ? secilen : null)
  const ek = duyurulan !== null ? ` (${duyurulan}. senaryo)` : secilen !== null ? ` (${secilen}. senaryo, olası)` : ' (bütün senaryolar)'
  const satir = oz.gruplar.flatMap(g => g.satirlar).find(s => s.kod === secili) ?? null
  const yazili = (n: number) => () => { setSecili(null); setArama({ sinav: String(n) }) }
  return (
    <section className="hazirlik-ders" aria-labelledby="hazirlik-ders-baslik">
      <Breadcrumb aria-label="Konum">
        <BreadcrumbItem href="/hazirlik" onClick={(e: React.MouseEvent) => { e.preventDefault(); gezin('/hazirlik') }}>Sınav hazırlığı</BreadcrumbItem>
      </Breadcrumb>
      <h2 id="hazirlik-ders-baslik" className={`hazirlik-ders__baslik ${subjectClass(oz.ders)}`}>{oz.ders}</h2>
      <ContentSwitcher size="lg" selectedIndex={no - 1} onChange={({ index }) => yazili((index ?? 0) + 1)()}
        aria-label="Yazılı seçimi" className="hazirlik-ders__yazililar">
        {oz.sinavlar.map(s => (
          <Switch key={s.sinav_no} name={String(s.sinav_no)} text={`${sinavAdi(s.sinav_no)} · ${s.durum.tur === 'gecti' ? 'geçti' : tarihMetni(s.durum.tarih, false)}`} />
        ))}
      </ContentSwitcher>
      <DurumGostergesi durum={oz.durum} />
      <DuyuruBildirimi oz={oz} />
      <Uyarilar metinler={hazirlikUyarilari(oz)} kip="ekran" />
      {oz.tur === 'senaryolu' && duyurulan === null && oz.durum.tur !== 'gecti' && (
        <RadioButtonGroup legendText="Kılavuzun senaryosu" name="kilavuz-senaryosu" orientation="horizontal"
          valueSelected={secim} onChange={v => setSecim(String(v))}>
          {[<RadioButton key="olasi" id="senaryo-olasi" value="olasi" labelText="Bütün senaryolar (olası)" />,
            ...oz.senaryolar.map(n => <RadioButton key={n} id={`senaryo-${n}`} value={String(n)} labelText={`${n}. senaryo`} />)]}
        </RadioButtonGroup>
      )}
      {oz.tur === 'senaryolu' && (
        <div className={`hazirlik-ders__govde${satir ? ' hazirlik-ders__govde--acik' : ''}`}>
          <Kaydirilabilir className="hazirlik-ders__tablo" etiket="Senaryo karşılaştırması tablosu">
            <KarsilastirmaTablosu matris={oz} vurgu={vurgu} kip="ekran" secili={secili}
              vurguEtiketi={duyurulan !== null ? 'duyurulan' : oz.durum.tur === 'gecti' ? 'yapılan' : 'seçilen'}
              sec={(kod, dugme) => { satirDugmesi.current = dugme; setSecili(kod === secili ? null : kod) }} />
          </Kaydirilabilir>
          {satir && <CiktiAyrintisi satir={satir} kilavuz={kilavuz} kapat={kapat} />}
        </div>
      )}
      {oz.tur === 'senaryolu' && (
        <div className="hazirlik-ders__eylemler">
          <Button kind="primary" size="lg" onClick={() => gezin(kilavuz)}>Kapsam kılavuzunu aç{ek}</Button>
          <Button kind="tertiary" size="lg" onClick={() => setPdfAcik(true)}>PDF olarak indir</Button>
        </div>
      )}
      {pdfAcik && <PdfSecenekleri anahtar={anahtar} no={no} senaryo={duyurulan === null ? secilen : null} kapat={() => setPdfAcik(false)} />}
    </section>
  )
}
```

`dashboard/src/hazirlik/KilavuzSayfasi.tsx` (son hâli; "PDF olarak indir", yeni sekmede "A4 önizleme" ve pencere eklendi):

```tsx
import { useContext, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { Breadcrumb, BreadcrumbItem, Button, InlineNotification, SkeletonText } from '@carbon/react'
import { Launch } from '@carbon/icons-react'
import { useApi } from '../hooks/useApi'
import { apiHataCumlesi } from '../utils/apiHatasi'
import { asistanaSor } from '../asistan/sayfaBaglami'
import KilavuzBelgesi from './KilavuzBelgesi'
import PdfSecenekleri from './PdfSecenekleri'
import { bolumler } from './belge'
import { SessionContext } from '../contexts/session'
import { baskiAdresi, modelAdresi, secenekleriOku, sinavAdi } from './hazirlik'
import { useIsaretler } from './useIsaretler'
import type { KilavuzModeli } from './tipler'
import './Hazirlik.scss'

/** Kapsam kılavuzu ekranı (spec §3.3): yapışkan yan içindekiler, belge, işaretler, asistana sor. */
export default function KilavuzSayfasi() {
  const { ders: anahtar = '', sinav = '1' } = useParams()
  const [arama] = useSearchParams()
  const gezin = useNavigate()
  const no = sinav === '2' ? 2 : 1
  const ham = arama.get('senaryo')
  const senaryo = ham && /^\d{1,2}$/.test(ham) ? Number(ham) : null
  const { data: m, loading, iskelet, hataTuru } = useApi<KilavuzModeli | null>(
    modelAdresi(anahtar, no, senaryo, { ebeveyn: false, isaret: true }), null)
  const { isaretler, isaretle, hata, hatayiKapat } = useIsaretler(anahtar, m)
  const [pdfAcik, setPdfAcik] = useState(false)
  const kisi = useContext(SessionContext)!
  if (loading) {
    return iskelet ? <section className="kilavuz-sayfa" aria-busy="true"><SkeletonText heading /><SkeletonText paragraph lineCount={8} /></section> : null
  }
  if (!m) {
    const h = apiHataCumlesi(hataTuru ?? 'sunucu', 'Kapsam kılavuzu')
    return <section className="kilavuz-sayfa"><InlineNotification kind="error" lowContrast hideCloseButton statusIconDescription="Hata" title={h.baslik} subtitle={h.ayrinti} /></section>
  }
  const sor = () => {
    const karsilandi = m.durum.sinav_id !== null
      && asistanaSor({ tur: 'sinav', id: m.durum.sinav_id, etiket: `${m.ders} — ${sinavAdi(no)}` })
    if (!karsilandi) gezin('/asistan?sayfa=sinavlar')
  }
  const dersSayfasi = `/hazirlik/${anahtar}?sinav=${no}`
  return (
    <div className="kilavuz-sayfa">
      <Breadcrumb aria-label="Konum">
        <BreadcrumbItem href="/hazirlik" onClick={(e: React.MouseEvent) => { e.preventDefault(); gezin('/hazirlik') }}>Sınav hazırlığı</BreadcrumbItem>
        <BreadcrumbItem href={dersSayfasi} onClick={(e: React.MouseEvent) => { e.preventDefault(); gezin(dersSayfasi) }}>{m.ders}</BreadcrumbItem>
      </Breadcrumb>
      <div className="kilavuz-sayfa__eylemler">
        <Button kind="primary" size="lg" onClick={() => setPdfAcik(true)}>PDF olarak indir</Button>
        <Button kind="ghost" size="lg" renderIcon={Launch} href={baskiAdresi(anahtar, no, m.senaryo, secenekleriOku(kisi.email, localStorage))}
          target="_blank" rel="noreferrer">A4 önizleme</Button>
        <Button kind="ghost" size="lg" onClick={sor}>Asistana sor</Button>
      </div>
      {pdfAcik && <PdfSecenekleri anahtar={anahtar} no={no} senaryo={m.senaryo} kapat={() => setPdfAcik(false)} />}
      {hata && <InlineNotification kind="error" lowContrast role="alert" statusIconDescription="Hata" aria-label="Bildirimi kapat"
        title={hata} onCloseButtonClick={hatayiKapat} />}
      <div className="kilavuz-sayfa__duzen">
        <nav className="kilavuz-sayfa__icindekiler" aria-label="Kılavuzun bölümleri">
          <ul>{bolumler(m).map(b => <li key={b.id}><a href={`#${b.id}`}>{b.ad}</a></li>)}</ul>
        </nav>
        <KilavuzBelgesi model={m} kip="ekran" isaretler={isaretler} isaretle={isaretle} />
      </div>
    </div>
  )
}
```

- [ ] **Step 7: Pano kapıları ve e2e**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-hazirligi/dashboard
npm run lint && npm run test:birim && npm run build; echo "pano: $?"
TEDY_E2E_PORT=8341 TEDY_E2E_PYTHON=/mnt/thunderbolt/workspaces/TED/.venv/bin/python env -u ANTHROPIC_API_KEY npx playwright test --project= hazirlik-pdf hazirlik-kilavuz hazirlik-ders
```

Expected: pano 0; `hazirlik-pdf` 3 test (indirme ve hatırlanan seçim, 429 cümlesi, A4 önizleme adresi) PASS.

- [ ] **Step 8: Uç uca gerçek basım (servis yolu)**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-hazirligi
env -u ANTHROPIC_API_KEY DASHBOARD_SECRET_KEY=test-only TEST_AUTH_BYPASS=1 /mnt/thunderbolt/workspaces/TED/.venv/bin/python -I -c "
import sys; sys.path.insert(0, '.')
from datetime import date
from pathlib import Path
import tempfile
import src.dashboard_api as api
api.OUTPUT_DIR = tempfile.mkdtemp(prefix='tedy-pdf-uc-')
api._hazirlik_bugun = lambda: date(2026, 10, 25)
from tests.hazirlik_fikstur import sinav_kaydi, FEN_KONULARI
api._hazirlik_sinavlari = lambda: [sinav_kaydi(konular=FEN_KONULARI)]
api._scraped = lambda: {}
c = api.app.test_client()
r = c.get('/api/hazirlik/fen-bilimleri/1/kilavuz.pdf')
print(r.status_code, r.mimetype, len(r.data), r.data[:8])
r2 = c.get('/api/hazirlik/fen-bilimleri/1/kilavuz.pdf')
print('önbellek:', r2.status_code, len(r2.data) == len(r.data))"
```

Expected: `200 application/pdf <bayt> b'%PDF-1.4'` ve `önbellek: 200 True` (ikinci istek önbellekten; gerçek Fen haritası ve `dashboard-dist` kullanılır).

- [ ] **Step 9: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-hazirligi
git log --oneline -3 && git status --short
git add src/hazirlik_pdf.py src/dashboard_api.py tests/test_hazirlik_pdf.py tests/test_hazirlik_api.py dashboard/src/hazirlik \
  dashboard/tests/e2e/hazirlik-pdf.spec.ts
git commit -m "$(cat <<'EOF'
feat(sinav-hazirligi): A4 PDF — sunucu basımı, seçenek penceresi ve A4 önizleme

İki yuvalı flock, süre dolunca süreç grubunun öldürülmesi, Paged.js düşerse düz Chrome, ikisi de düşerse açık
ileti (503); yuva doluysa beklemeden 429. PDF içerik özeti ve baskı paketi imzasıyla önbelleklenir. Pencere
ebeveyn özeti ve işaret seçeneklerini kişi başına hatırlar; YZ seçenekleri Plan 2'de.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 15: Belgeler, tam doğrulama ve dal hazır — canlıya alma kullanıcı onayıyla

**Files:**
- Modify: `CLAUDE.md` (Dashboard bölümüne "Sınav Hazırlığı" maddesi; Core Modules tablosuna üç satır)
- Modify: `docs/sinav-kilavuzu-kanunu.md` (kapı sütunlarının dosya adları gerçek testlerle eşleşir; sürüm 1.0 tarihi)

**Interfaces:**
- Consumes: Görev 1–14'ün bütün çıktıları.
- Produces: incelenmeye hazır `feat/sinav-hazirligi` dalı; canlıya alma adımları (kullanıcı onayıyla).

- [ ] **Step 1: CLAUDE.md maddesi**

Core Modules tablosuna (sınav satırlarının altına):

```markdown
| `src/sinav_kilavuzu.py` | Sınav Hazırlığı modeli (saf): genel bakış, ders özeti (çıktı × senaryo matrisi, kitap yolları), kapsam kılavuzu (bloklar, olası kip K8, bağlam, plan, damgalar, içerik özeti). |
| `src/hazirlik_isaretleri.py` | Kişi başına hazırlık işaretleri (`output/hazirlik_isaretleri.json`, flock + atomik). |
| `src/hazirlik_pdf.py` | Kılavuz A4 PDF hattı: Node/Chrome basımı, 2 yuva, 90 s zaman aşımı, düz Chrome yedeği, `output/hazirlik_pdf/` önbelleği. |
```

Dashboard bölümüne (MEB senaryoları maddesinin altına):

```markdown
- **Sınav Hazırlığı (2026-10-25, Plan 1 Fen)** (spec `docs/superpowers/specs/2026-10-25-sinav-hazirligi-design.md`, plan `docs/superpowers/plans/2026-10-25-sinav-hazirligi-plan1-fen.md`, kanun `docs/sinav-kilavuzu-kanunu.md`): `/hazirlik` (önce tarihi belli ortak yazılılar, sonra altı dersin karosu), `/hazirlik/:ders?sinav=1|2` (karşılaştırma tablosu, satır ayrıntısı), `/hazirlik/:ders/:sinav?senaryo=N` (kapsam kılavuzu, hazırlık işaretleri); "Daha fazla" altında "Sınav hazırlığı", Sınavlar kartında "Kapsam kılavuzu", Dersler sekmesinde "MEB senaryoları". Uçlar `GET /api/hazirlik`, `/api/hazirlik/<anahtar>/<no>`, `…/kilavuz`, `…/kilavuz.pdf`, `PUT /api/hazirlik/isaret` — `require_auth`, okuyucu default-deny, API anahtarı okur ama işaret koyamaz. Kitap haritası `scripts/meb_kitap_haritasi.py` üretir (`pdftotext -layout` İçindekiler + `pdftohtml -xml` düzen: başlık boyu 20, kalın tanım); elle düzenlenmez, gürültü `KITAPLAR[...]["duzen"]["atla"]`'ya yazılır; Plan 1'de yalnız `src/kitap_haritalari/fen-bilimleri.json` (Fen 7 1. Kitap; 1. dönemin iki yazılısı da bu kitapta). Kitap değişimi `--denetle` ile `output/kitap_denetimi.json`'a yazılır, kılavuz "güncel değil" der (K12). Baskı ayrı Vite girişi `baski.html`: aynı `KilavuzBelgesi` kâğıt kipinde; Paged.js 0.4.3 ve IBM Plex woff2 depoda (`dashboard/src/baski/vendor/`, `dashboard/public/fonts/plex/`, `sha256sum -c`); Paged.js'e yalnız `sayfa.css` verilir — Carbon'un tam CSS'i onun ayrıştırıcısını düşürür. Sunucu basımı `dashboard/scripts/kilavuz-pdf.mjs` (pano node_modules'undaki Playwright, Chrome kanalı, sahte kökte ağsız). Pano fikstürleri modelden üretilir: `scripts/hazirlik_fiksturleri.py` (tazelik testi `tests/test_hazirlik_fiksturleri.py`). YZ bölümleri ve öbür beş dersin haritaları Plan 2.
```

- [ ] **Step 2: Kanun belgesinin kapı sütununu gerçek test adlarıyla eşle**

`docs/sinav-kilavuzu-kanunu.md` §1 tablosunda: K2 → `dashboard/tests/e2e/hazirlik-kilavuz.spec.ts` "blok iç sırası sabit (K2)"; K6 → `tests/test_sinav_kilavuzu_belge.py::test_kilavuz_kitapta_ve_bolum_basliklari`; K8 → `tests/test_sinav_kilavuzu_belge.py::test_kilavuz_olasi_kip_tek_senaryo_sunmaz`, `dashboard/tests/hazirlik.test.ts`, `hazirlik-kilavuz.spec.ts` "olası kip"; K11 → `dashboard/tests/e2e/hazirlik-baski.spec.ts`; K12 → `tests/test_sinav_kilavuzu.py::test_guncellik_tablo_ve_kitap_degisti`, `tests/test_meb_kitap_haritasi.py::test_denetle_sha256_degisimini_yazar`. Her adın depoda geçtiğini doğrula:

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-hazirligi
for ad in test_kilavuz_olasi_kip_tek_senaryo_sunmaz test_guncellik_tablo_ve_kitap_degisti test_denetle_sha256_degisimini_yazar test_kilavuz_kitapta_ve_bolum_basliklari; do
  grep -rq "$ad" tests && echo "var: $ad" || echo "YOK: $ad"
done
```

Expected: dört satır "var:".

- [ ] **Step 3: Tam doğrulama**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-hazirligi
sha256sum -c --quiet dashboard/src/baski/vendor/SHA256SUMS && echo "depodaki varlıklar özgün"
env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest -q -p no:cacheprovider; echo "pytest: $?"
cd dashboard && npm run lint; echo "lint: $?"
npm run test:birim; echo "birim: $?"
npm run build; echo "build: $?"
TEDY_E2E_PORT=8341 TEDY_E2E_PYTHON=/mnt/thunderbolt/workspaces/TED/.venv/bin/python env -u ANTHROPIC_API_KEY npx playwright test --project= ; echo "e2e: $?"
```

Expected: varlıklar özgün; pytest, lint, birim, build ve tam e2e çıkışı 0. Tam e2e'de Sınav Hazırlığı dosyalarına dokunmayan bir test düşerse, aynı test `main`'in kendi çalışma ağacında da düşüyor mu diye bakılır (eşzamanlı koşu, port çakışması, eski paket); bu dalın bozduğu her şey düzeltilmeden geçilmez, dalın bozmadığı kırmızı rapora yazılır.

- [ ] **Step 4: Belgeleri commit'le**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-hazirligi
git log --oneline -3 && git status --short
git add CLAUDE.md docs/sinav-kilavuzu-kanunu.md
git commit -m "$(cat <<'EOF'
docs(sinav-hazirligi): CLAUDE.md'ye Sınav Hazırlığı; kanunun kapıları gerçek testlere bağlandı

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
git log --oneline main..HEAD
```

- [ ] **Step 5: Dal hazır — canlıya alma kullanıcı onayıyla**

Push, merge ve canlıya alma bu planda **yapılmaz**. Kullanıcıya şu raporu ver ve onay bekle:
- dal `feat/sinav-hazirligi`, `git log --oneline main..HEAD` listesi, tam doğrulamanın sonuçları;
- yoklamanın kararı (A ya da B) ve Kanun'un §2 kaydı;
- Fen haritasının onay kaydı (`denetim.kim`, `denetim.tarih`) ve `scripts/meb_kitap_haritasi.py --kuru` ağacı;
- canlıya alma adımları (her biri onayla): canlı checkout temiz ve `main`'deyken birleştirme (bellek notu "Merge onayı açık olmalı": dalları adıyla anan açık "evet"); `cd dashboard && npm run build` (çıkış kodu okunarak); `systemctl --user restart ted-dashboard`; canlıda `/hazirlik` ve Fen kılavuzunun PDF'i bir kez elle denenir;
- geri dönüş: birleştirme commit'inin `git revert`'ü + `npm run build` + `ted-dashboard` yeniden başlatma (yeni uçlar ve sayfalar kalkar; `output/hazirlik_isaretleri.json` ve `output/hazirlik_pdf/` kalır, zararsızdır).

---
