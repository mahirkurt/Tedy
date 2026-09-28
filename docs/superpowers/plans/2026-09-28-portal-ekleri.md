# Portal Ekleri — İndirme, Sunma, Asistan Bağlamı ve Portal Süsü Temizliği

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Portal verisindeki her dosya eki TEDY'ye indirilir, TEDY'den ek olarak sunulur ve asistanın bağlamına girer; portal arayüzünden sızan, TEDY'yle ilgisi olmayan süs (başka çocukların adları ve yorumları dahil) kazınan bilgiden atılır.

**Architecture:** Saf bir toplayıcı (`src/portal_ekleri.py`) kazınan veriden bütün ek bağlantılarını toplar, her birine kanonik adresin karmasından kararlı bir kimlik verir ve izleyiciyi (`output/portal_ekleri.json`) okur/yazar. Ağ yarısı (`src/portal_ekleri_indir.py`) `run_sync` içinde, kazıyıcılardan sonra ve sağlık/yeniden indekslemeden önce, açık bir süre ve bayt bütçesiyle çalışır: akışla geçici parça dosyasına indirir, türü baytlardan okur, HTML'i asla dosya diye saklamaz, 300 MB'ı reddeder, bütçe biterse parçayı saklar ve sonraki turda Range ile sürdürür; indirdiği her dosyanın metnini aynı bütçe içinde bir kez çıkarıp `<id>.txt` + `<id>.meta.json` yan dosyalarına yazar. Pano `GET /api/ekler/<id>` ile dosyayı Range destekli, satır içi sunar; ödev/sayfa/duyuru yükleri her eke `tedyUrl` ve `status` ekler. Asistan yalnız `<id>.txt`'yi BM25'e alır, `ek_oku(id, sayfa)` ile eki sayfa sayfa okur, `odev_listesi` ekleri kimlikleriyle listeler. Süs kuralları tek modülde (`src/portal_susu.py`) toplanır ve kazıyıcıda, API sınırında ve tarayıcıda (savunma) uygulanır.

**Tech Stack:** Python 3 / Flask 3.1 (`send_file` + werkzeug Range), `requests` 2.32, `bs4`, stdlib `zipfile` + `xml.etree`, poppler `pdfinfo`/`pdftotext`/`pdftoppm`, Claude Haiku 4.5 görüsü (OCR, `src/claude_api.py` istemcisiyle) + Tesseract `tur+eng` (`pytesseract`), pytest 9; React 19 + TypeScript + Carbon + SCSS, Playwright (+ `@axe-core/playwright`).

**Spec:** Ayrı spec dosyası yok. Kullanıcının 2026-09-28'de onayladığı tasarım (C) aşağıdaki "Onaylı tasarım (C)" bölümünde birebirdir ve bağlayıcıdır; kapsam odur.

## Global Constraints

- **Çalışma ağacı ve dal:** yalnız `/mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri`, dal `feat/portal-ekleri` (main `f7cad72`'den). Her commit'ten önce `test "$(git -C /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri branch --show-current)" = feat/portal-ekleri && echo dal-dogru` çıktısı `dal-dogru` olmalı.
- **Ana checkout paylaşımlıdır:** `/mnt/thunderbolt/workspaces/TED` başka oturumlarca kullanılır. Oraya yazma, orada git komutu koşma. `output/` ve `content/` yalnız orada vardır; biçim için **salt-okunur** okunabilir (yalnız sayım/şekil yazdır, içerik yazdırma).
- **Kişisel veri yok:** plan, test, fixture ve commit mesajlarında gerçek öğrenci/öğretmen adı, gerçek SharePoint yolu, gerçek Drive kimliği, gerçek not yok. Fixture'lar gerçek biçimi taşır, değerler uydurmadır (`Kurgu Öğrenci Bir`, `ornekokul-my.sharepoint.com`, `ogretmen_ornekokul_k12_tr`).
- **OCR testleri ücretli API'yi asla çağırmaz:** görü okuyucusu her testte `tests/sahte_ocr.py`'deki sahte okuyucudur; `ClaudeGorselOkuyucu`'nun kendi testi sahte bir Anthropic istemcisiyle koşar. `tests/conftest.py` `ANTHROPIC_API_KEY`'i siler ve (Görev 15'ten sonra) `ASSISTANT_PDF_OCR=0` koyar; OCR'u yalnız onu sınayan testler açar. Gerçek Tesseract testlerde çalışmaz (sayfa başına ~20 s ölçüldü); yerine sahte bir işlev verilir. `pdfinfo`/`pdftotext`/`pdftoppm` yerel ve ağsızdır, testlerde gerçek çalışır.
- **Testler ağa ve ücretli API'ye asla çıkmaz.** İndirmeler yalnız `tests/sahte_http.py` sahte HTTP katmanıyla sınanır (SharePoint, Drive, Docs yanıt biçimleri; HTML giriş duvarı, Drive onay sayfası, Range, 300 MB tavan benzetimi, bütçe tükenmesi). `tests/conftest.py` `ANTHROPIC_API_KEY`'i zaten siler. Şüphede `unshare -rn` altında koş.
- **Python testleri:** `DASHBOARD_SECRET_KEY=yerel-test-anahtari-portal-ekleri .venv/bin/python -m pytest -q -p no:cacheprovider …`. Çalışma ağacında `.env` yok (ölçüldü 2026-09-28); önek olmadan `src.dashboard_api` içe aktarılırken `RuntimeError` atar. `.env` oluşturma, symlink kurma.
- **Pano:** `dashboard/node_modules` yoksa önce `cd dashboard && npm ci`. Sonra `npm run lint` ve `npm run build`; çıkış kodunu **boru olmadan** oku (`npm run build; echo "build çıkış: $?"`). Playwright `dashboard-dist/`'i sunar: her e2e koşusundan önce build. Playwright `env -u ANTHROPIC_API_KEY TEDY_E2E_PORT=8297 DASHBOARD_SECRET_KEY=yerel-test-anahtari-portal-ekleri npx playwright test …` ile koşar.
- **Görsel taban çizgisi yalnız fark okunduktan sonra:** önce güncellemesiz koş; kırmızıysa `test-results/` altındaki `*-actual.png` / `*-expected.png` / `*-diff.png`'yi Read ile aç, değişikliğin yalnız beklenen bölgede olduğunu yaz, sonra `--update-snapshots`. Bu planın hiçbir fixture'ı görsel sayfalara ek koymaz; taban çizgisi değişmemesi beklenir.
- **Her koşu ön planda.** Arka plan kabuk işi yok. Yavaş koşularda Bash `timeout` 600000 ms.
- **Staging adla:** `git add <yol> <yol>`; `git add -A` / `git add .` yok. Çıplak `git stash` yok. `git push` yok.
- **Carbon token kuralları** (CLAUDE.md, `tests/test_pano_tasarim_sistemi.py`): boşluk/tip/hareket Carbon token'ı (`$spacing-NN`, `@include type.type-style(...)`), renk rol token'ı (`theme.$link-primary` vb.); el yazısı hex, alfa, gradyan, `filter`, `color-mix` yok. `npm run lint` temiz.
- **Kod stili:** kullanıcıya dönük metin Türkçe; kod yorumları İngilizce ve çevredeki "measured …" gerekçeli üslupta. Commit mesajları Türkçe, son satır `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- **Plan metnine `\u`/`\x` kaçışı yazma:** araç girdisinde çözülüp dosyaya ham karakter olarak düşer. Bu yüzden kod `chr(0xA0)`, `chr(12)`, `bytes.fromhex(...)` kullanır; öyle bırak.
- **Başlangıç kırmızıları:** Görev 1'in ilk adımı tam Python paketini bir kez koşar ve önceden kırmızı olanları not eder; hiçbir görev yeni kırmızı bırakmaz.
- **Dağıtım bu planın görevi değildir.** Sondaki "Controller: dağıtım" bölümünü controller yapar: birleştir, build, restart, ardından ilk gerçek indirme turu canlı izlenir.

## Onaylı tasarım (C) — 2026-09-28, bağlayıcı

Hedef: portal verisinde bulunan her dosya eki TEDY'ye çekilir, ek olarak sunulur ve asistanın bağlamında kullanılabilir. TEDY'yle ilgisi olmayan portal arayüz süsü kazınan bilgiden atılır.

Ölçülen gerçekler:
- Ekler bugün: ödevlerde `detail.attachments[] = {name, url}` (`src/scrape_all.py` ~608-653 `_scrape_homework_detail`); sunucular SharePoint kişisel paylaşım bağlantıları (`…-my.sharepoint.com/:b:/g/personal/…?e=…`) ve bir docs.google.com bağlantısı. `ek_sayfalar.documents` Google Drive `/file/d/<id>/preview` bağlantıları (scrape_all ~1246-1268). Duyurular `<sütun>_url` taşır (~1229-1234); şu an 0 duyuru. Ders içeriği, takvim ve `sebit_homework.json`'da ek bağlantısı yok.
- Bugün hiçbir şey indirilmiyor; `HomeworkTracker.tsx` ~529-537 ve `NextThing.tsx` ~104-114 doğrudan dış sunucuya bağlanıyor.
- 2026-09-28 girişsiz yoklama: SharePoint + `download=1` 5 bağlantının 4'ünde 200 `application/pdf` (bazıları 100 MB üstü: 112 MB, 101 MB), birinde `text/html` (giriş duvarı ya da klasör). Drive `https://drive.google.com/uc?export=download&id=<id>` 4/4 200 octet-stream, 28 MB'a kadar; büyük dosyada onay (confirm) akışı gerekebilir. docs.google.com `text/html`; `/export?format=pdf` biçimi kullanılır.
- Asistan ekleri hiç görmüyor: `_fmt_scraped_data`'nın ödevler paragrafında ek adı yok. `FileAdapters` (assistant_core ~942-1116) pdf'yi pdftotext, görseli tesseract ile okuyor; `.docx` yok.
- Portal süsü: "Daha fazla oku … Yorum Ekle" blokları (aralarında BAŞKA ÖĞRENCİLERİN adları ve yorumları), "İlk yorum yapan sen olmak ister misin?", "N Yorum yapıldı!". Yalnız `assistant_tools` `_ICERIK_SUSU` / `_temiz_icerik` (~798-818) ayıklıyor; ham `scraped_data.json`'a, `/api/content` ve `/api/content/weeks`'e (dashboard_api ~1591-1653, ham dönüyor) ve `CourseContent.tsx` `parseCard`'a sızıyor. Sayılar: ders_icerikleri'nde 9, ders_icerikleri_haftalar'da 215, çoğu "Genel" okul akışı sekmesinde.

Tasarım:
1. **Toplayıcı.** Yeni modül (ör. `src/portal_ekleri.py`). Her senkron sonrası bütün bölümlerden ek bağlantılarını toplar: ödev ayrıntıları, ek_sayfalar belgeleri, duyuruların `_url` sütunları ve gelecekteki eklerin yakalanması için öteki bölümlerde genel dosya bağlantısı taraması. Her birini sunucuya göre indirme adresine çözer: SharePoint `download=1`; Drive `uc?export=download` (büyük dosyada onay akışıyla); Google Docs/Slides/Sheets `/export?format=pdf`; portalın kendi dosyası çıkarsa Selenium çerez oturumuyla. Dosyalar `content/portal-ekleri/`'ye kararlı kimlikle (kanonik adresin karması) + saptanan uzantıyla iner. İzleyici `output/portal_ekleri.json`: url, id, name, type, size, sha256, kaynak bölüm ve öğe kimliği, status, reason, fetched_at. Kurallar: idempotent; başarısız indirme sonraki turda yeniden denenir; dosya beklenen yerde gelen HTML asla dosya diye saklanmaz, nedeniyle `erisilemedi` olur; tür sihirli baytlarla denetlenir; dosya başına 300 MB tavan; geçici dosyaya akışla indirme, sonra atomik yeniden adlandırma.
2. **Bütçe.** Cron `run_sync`'i `timeout 600` altında koşar. İndirmeler `run_sync` içinde, kazıyıcılardan sonra, en iyi çabayla, tur başına açık süre ve bayt bütçesiyle çalışır; kalan sonraki turlara kalır. Senkron eklerden ötürü asla zaman aşımına düşmez. Mevcut senkron kilidi altında çalışırlar.
3. **Sunma.** `GET /api/ekler/<id>` `require_auth` altında, yalnız full rol; okurlar default-deny listesiyle reddedilir. Dosyayı doğru content-type ve `Content-Disposition: inline` ile akıtır, büyük PDF'ler için HTTP Range destekler. Ödev, sayfa ve duyuru API yükleri her eke `tedyUrl` (indirilmediyse null) ve `status` ekler. Arayüz (HomeworkTracker, NextThing ve eklerin çizildiği her yer) TEDY kopyasını açar, özgün bağlantıyı ikincil "Kaynağında aç" olarak tutar, kopya yoksa durumu gösterir ("İndirilemedi — kaynağında aç"). Yalnız Carbon token'ları.
4. **Asistan.** İndirilen ekler BM25 indeksine girer (`content/portal-ekleri` `content/` altındadır; keşif, dışlama kuralları ve parça tavanları denetlenir). Atıflar yan meta veriyle "<ek adı> · <ödev başlığı>" gösterir, asla iç yol değil. `FileAdapters`'a stdlib `zipfile` + `word/document.xml` ile `.docx` metin çıkarma, yeni bağımlılık yok. Yeni araç `ek_oku(id, sayfa)` eki 4.000 karakterlik araç sonucu sınırı içinde sayfa sayfa okur. `odev_listesi` her ödevin eklerini adı ve kimliğiyle listeler. Sistem istemindeki yönlendirme satırı güncellenir; her araç tam bir kez yönlendirilir (bunu sayan test var). Metin katmanı olmayan büyük taranmış PDF'ler: pdftotext boş döner; araç bunu dürüstçe söyler ("metin katmanı yok"). OCR, mevcut tesseract yolunu zaman bütçesi içinde sayfa sayfa ucuzca yeniden kullanmak mümkün değilse kapsam dışıdır; karar ve gerekçe yazılır.
5. **Süs temizliği.** `_temiz_icerik` kuralları tek ortak temizleyici modüle taşınır ve uygulanır: (a) kazıyıcı çıktısında (yeni veri temiz saklanır); (b) API sınırında `/api/content`, `/api/content/weeks`, ödev açıklamaları ve süsü taşıyabilecek her metin alanı için (mevcut veri temiz sunulur); (c) savunma olarak `CourseContent.tsx` `parseCard`'da. Başka öğrencilerin adları ve yorumları hiçbir yüzeye ve indekse ulaşmaz. "Genel" akışın okul gönderileri kalır; yorum blokları gider. Temizleyici gerçek süs biçimleri (yalnız uydurma adlar) ve bilinen süs dizgeleri üzerinde testlerle sabitlenir.
6. **Belgeler.** CLAUDE.md bölümleri: veri akışı, temel desenler, asistan araçları.

### Genişletme — OCR (kullanıcı onayı, 2026-09-28, bağlayıcı)

Taranmış PDF'ler için gelişmiş OCR artık kapsamda:
- Ortak bir OCR katmanı (ör. `src/ocr_katmani.py`). Metin katmanı olmayan PDF sayfaları görüntüye çevrilir (`pdftoppm` var; çözünürlük/maliyet dengesi denetlenir); her sayfa mevcut `src/claude_api.py` istemcisiyle, TEDY'nin anahtarıyla Claude Haiku 4.5 görüsüne gönderilir; model başlıkları, tabloları ve formülleri koruyan Markdown döndürür.
- Sayfa başına sonuç önbelleği; anahtar (dosya sha256, sayfa, motor ve istem sürümü) — bir sayfa bir kez okunur.
- Aylık 10 USD tavanı: `output/` altında bir defter, `response.usage`'dan ölçülen kullanım ve fiyat sabitleriyle. Tavana varınca ya da API hatasında yerel Tesseract'a (`tur+eng`, `FileAdapters`'ta zaten var) düşülür.
- Her sayfa motorunu ve bir güven tahminini taşır; asistan düşük güvenli sayfaları "OCR, güven düşük" etiketiyle görür.
- Mevcut ek eşitlemesinin süre ve bayt bütçesi içinde çalışır: sayfa sayfa, turlar arası sürdürülebilir.
- Asistanın BM25 indeksindeki taranmış PDF'lere de genel olarak hizmet eder (`FileAdapters`'ın PDF yolu, pdftotext boş döndüğünde), yeniden indekslemenin kendi süre sınırları içinde.
- `ek_oku` ve metin yan dosyası OCR metnini içerir.
- Testler ücretli API'yi hiç çağırmaz: sahte görü istemcisi; tavan ve düşüş için testler.

## Uygulama sırası

Görev 1–12, sonra **14 ve 15**, en son **13** (tam doğrulama ve CLAUDE.md her şeyin üstünde koşar). Görev 13'ün metni buna göre yazılmıştır.

## Karara bağlanan belirsizlikler

1. **Metin yan dosyası.** İkili dosya `content/portal-ekleri/<id><uzantı>`'da durur. Metni indirme anında, aynı bütçe içinde, bir kez `<id>.txt`'ye çıkarılır (ilk paragraf `PORTAL EKİ · <ek adı> · <bağlam> · <ders>` başlığı; BM25 eki adıyla da bulur), yan meta `<id>.meta.json`'a yazılır. BM25 `content/portal-ekleri/` altında **yalnız** `<id>.txt`'yi alır; ikili dosyalar, `.meta.json` ve `.parca/` parça dosyaları dışlanır. Gerekçe: 112 MB'lık bir PDF'in pdftotext'i yeniden indekslemede bütçe dışında koşmaz, `ek_oku` her çağrıda pdftotext çalıştırmaz.
2. **OCR kapsamda (Görev 14–15; önceki "kapsam dışı" kararının yerine).** Kullanıcı 2026-09-28'de genişletti. Ölçülenler ve kararlar:
   - **Çizim:** `pdftoppm -scale-to 1568 -jpeg` (uzun kenar 1568 px). Claude uzun kenarı ~1568 px'i aşan görseli zaten küçültür; daha büyüğü yalnız çizim süresi getirir. Ölçüldü (2026-09-28, 70 MB'lık bir PDF'in 5. sayfası): 150 dpi 1214×1650 3,2 s, 200 dpi 1619×2200 5,3 s. 1568 px A4'te ~190 dpi'dir; görsel ≈ w·h/750 ≈ 2.400 girdi token'ı.
   - **Maliyet:** Haiku 4.5 1 $/5 $ MTok (claude-api başvurusu, önbellek 2026-06-24). Sayfa başına ~2.700 girdi + ~1.000 çıktı ≈ 0,008 $; 10 $ ≈ 1.250 sayfa/ay. Çağrıdan önce en kötü durum (4.000 girdi + 4.096 çıktı ≈ 0,0245 $) sığmıyorsa Claude çağrılmaz; kullanım `response.usage`'dan deftere yazılır. Eşzamanlı iki süreç (cron + panonun `/api/assistant/reindex`'i) tavanı en çok süreç başına bir sayfa (≤ 0,025 $) aşabilir; rezervasyon yerine bu sınır, çöken bir süreç tavanı kalıcı olarak yemesin diye seçildi.
   - **Güven:** Claude sayfa sonunda `<!-- okunabilirlik: yuksek|orta|dusuk -->` yazar (0,9/0,7/0,4; satır yoksa orta; `max_tokens` ile kesildiyse düşük). Tesseract için kelime güvenlerinin ortalaması. 0,6 altı "OCR, güven düşük". Yapılandırılmış çıktı (JSON) seçilmedi: kesilen bir JSON bütün sayfayı kaybettirir, kesilen Markdown'ın okunan kısmı kalır.
   - **Boş sayfa:** Çizilen sayfanın gri tonu sapması 2'nin altındaysa API çağrılmaz (`bos` motoru, önbelleğe girer). Bir ders kitabının kapak arkası için para ödenmez.
   - **Düşüş:** Tavanda, API hatasında, rette ya da anahtar yoksa Tesseract. Tesseract ile okunmuş **düşük güvenli** bir sayfa, tavan izin verdiğinde (ör. yeni ay) Claude ile bir kez daha denenir; yüksek güvenli Tesseract sonucu kalır.
   - **Kapsam:** Genel indekste yalnız pdftotext tümüyle boş dönen PDF'ler (tasarımdaki gibi; bir ders kitabının resimli sayfaları OCR'a gitmez). Eklerde metinsiz her sayfa.
   - **Süre:** Eklerde eşitleme bütçesinin kalanı (`min(180 s, kalan)`); indekslemede indeksleyici başına `ASSISTANT_OCR_SURE` (45 s). `perform_incremental_reindex` iki indeksleyici koşar (ana + aile), en kötü 90 s; bu, `run_sync`'in 150 s'lik yedeğinin içindedir. 15 s'den az kalmışsa Claude çağrısı, 10 s'den az kalmışsa Tesseract başlatılmaz; Claude istemcisi `max_retries=0` ve kalan süre kadar zaman aşımıyla kurulur, böylece taşma en çok bir çağrıdır.
   - **Sürdürme:** Okunan her sayfa hemen önbelleğe yazılır. Yarım kalan PDF indekste `PdfExtractionError("ocr_suruyor")` olur (manifest kaydı yok, sonraki turda yeniden); eklerde `text: "bekliyor"` + `ocr_ilerleme: "12/40"` olur ve bu, 3 denemelik metin hatası sınırını tüketmez.
   - **Eski indeks kayıtları:** Canlı indekste 3 `pdf_no_text` parçası var (`content/yabanci-dil`, 2026-09-28). OCR açıkken `pdf_no_text` parçası taşıyan dosya sha'sı aynı olsa da yeniden çıkarılır; `INDEX_FORMAT_VERSION` artırılmaz (bütün kitapları yeniden okutmak gereksiz).
   - **Model:** `claude-haiku-4-5` (tasarım adıyla istedi); `OCR_CLAUDE_MODEL` ile değişir, ama fiyat sabitleri Haiku 4.5 içindir. Model değişirse sabitler de değişmeli. Düşünme ve `temperature` gönderilmez.
   - **Defter ve önbellek BM25 dışında:** `output/ocr_onbellek/` dizini ve `ocr_defteri.json` dışlanır. Kilit dosyası `*.lock` kuralına zaten takılır.
3. **"Range" iki yerde:** sunmada (`send_file(conditional=True)` → 206) ve indirmede: bütçe biten dosya `content/portal-ekleri/.parca/<id>.part` olarak kalır, sonraki tur `Range: bytes=<n>-` ile sürdürür (206 başlangıcı uymazsa ya da 416 gelirse parça atılıp baştan; sunucu Range'i yok sayıp 200 dönerse baştan yazılır; 416 ile toplam = parça boyu ise dosya tamamdır).
4. **Durumlar:** `bekliyor`, `indirildi`, `erisilemedi`, `cok_buyuk`, `hata`, `baglanti`. `baglanti` dosya olmayan bağlantılardır (YouTube, SharePoint `:f:` klasörü, form): asla indirilmez, arayüzde uyarısız "kaynağa git" bağlantısıdır. Yeniden deneme: `bekliyor` ve `hata` her tur; `erisilemedi` 24 saat sonra (öğretmen paylaşımı açabilir); `cok_buyuk` ve `baglanti` hiç; `indirildi` yalnız kopya silinmişse. Metin çıkarma hatası en çok 3 kez denenir.
5. **API anahtarları:** `/api/ekler/<id>` her veri rotası gibi `require_auth`'u izler (full rol oturumu ya da API anahtarı); okur rolü 403 alır (READER_ENDPOINTS'e eklenmez).
6. **Bilinmeyen ikili tür** `.bin` / `application/octet-stream` olarak saklanır ve **attachment** (satır içi değil) + `nosniff` ile sunulur; tanınan türler (pdf, görseller, office) `inline`. HTML hiçbir koşulda saklanmaz.
7. **İzleyici alanları** tasarımın saydığı İngilizce adlarla: `url, id, name, type, size, sha256, source{section,item,title,course}, sources, status, reason, fetched_at` + `canonical, file, ext, mime, attempts, last_attempt, next_attempt, partial_bytes, text, text_chars, text_attempts, first_seen, last_seen`. Durum değerleri Türkçe.
8. **Sayfaların arayüzü yok** (`/api/pages`'i okuyan bileşen yok, ölçüldü): sayfa ekleri yalnız API yüküne (`attachments`) girer. Duyurular `ekler` alanını çizer, yoksa eski `Ekleri_url`'e düşer.
9. **Bütçe değerleri:** süre = `min(180 s, başlangıç + 600 − 150 − şimdi)`; 150 s sağlık + yeniden indeksleme + pay. Son 40 koşu ölçüldü: p50 244 s, en uzun 393 s → bütçe en kötü ~57 s. 15 s'nin altında adım atlanır. Bayt 250 MB/tur. `TEDY_EK_SURE_BUTCESI`, `TEDY_EK_BAYT_BUTCESI_MB` ile değiştirilir.
10. **`INDEX_FORMAT_VERSION` artırılmaz:** yeni kurallar yalnız daha önce hiç var olmamış yolları (`content/portal-ekleri/`, `output/portal_ekleri.json`) etkiler; `scraped_data.json` her senkronda değiştiği için yeni biçimlendirmesi kendiliğinden yeniden çıkarılır.
11. **Temizleyici kuralları sıkılaşır:** yorum bloğu yalnız "Yorum Ekle" ile biter; boş satır bitirmez (eski kural bitiriyordu, bir yorumdaki boş satır sonrakileri sızdırırdı); kapanmayan blok metnin sonuna kadar atılır (87 kart "Daha fazla oku" ile bitiyor ölçüldü ve kazıyıcı metni 8.000 karakterde kesiyor — kesik blok da yorumdur). Satırlar boşluk-normalize edilir (NBSP). `run_sync` önceki turların haftalarını birleştirirken de temizler; ilk senkronla dosyanın tamamı temizlenir.
12. **Aynı paylaşım bağlantısının arkasında değişen içerik yeniden saptanmaz** (yeniden doğrulama yok); yeni bağlantı yeni kimliktir. Yıl devrinde ek izleyicisi sıfırlanmaz.
13. **Portal dosyası çerezleri** `run_sync`'te sürücünün kendi oturumundan (`driver.get_cookies()`), elle CLI'da önbellekteki `output/portal_cookies.json`'dan alınır; yalnız portal alan adına kapsamlı bir kavanozla ve yalnız `type == "portal"` isteklerine gider.
14. `.gitignore`'a `content/portal-ekleri/` eklenir: `.txt`/`.docx`/`.meta.json` mevcut `content/**/*.pdf` kuralına takılmaz ve öğretmen belgeleri ana checkout'ta izlenmemiş dosya olarak görünürdü.

## Dosya haritası

| Dosya | Sorumluluk | Görev |
|---|---|---|
| `src/portal_susu.py` (yeni) | Süs + yorum bloğu temizleyicisi; içerik kaydı/ders/hafta sarmalayıcıları | 1 |
| `src/assistant_tools.py` | `_temiz_icerik` → `portal_susu`; `ek_oku`, `odev_listesi` ekleri, BM25 ek etiketi | 1, 10 |
| `src/scrape_all.py` | Sekme kaydı temizliği (kırpmadan önce), ödev açıklaması, ek sayfa metni | 2 |
| `src/run_sync.py` | `_icerik_birlestir` (temizleyerek birleştirme); ek adımı, bütçe, çerezler, sağlık `ekler` | 2, 7 |
| `src/dashboard_api.py` | API sınırında temizlik; `/api/ekler/<id>`; yüklere `tedyUrl`/`status` | 2, 8 |
| `src/portal_ekleri.py` (yeni) | Sınıflama, kimlik, indirme adresi, toplayıcı, `EkDeposu`, `ek_ozeti`, `ek_basligi` | 3 |
| `.gitignore` | `content/portal-ekleri/` | 3 |
| `src/assistant_core.py` | `.docx` çıkarma; portal-ekleri indeks kuralı, keşif önceliği, izleyici dışlama; ödev paragrafında ek adları; runtime `ek_deposu` | 4, 9, 10 |
| `src/portal_ekleri_indir.py` (yeni) | `ek_indir` (tek dosya), `ekleri_esitle` (tur), `metin_cikar`, CLI | 5, 6, 7 |
| `tests/sahte_http.py` (yeni) | Sahte HTTP katmanı | 5 |
| `tests/test_portal_susu.py`, `tests/test_portal_susu_uygulama.py` (yeni) | Temizleyici ve uygulandığı yerler | 1, 2 |
| `tests/test_portal_ekleri.py`, `tests/test_portal_ekleri_indir.py`, `tests/test_portal_ekleri_esitle.py`, `tests/test_portal_ekleri_sync.py`, `tests/test_portal_ekleri_api.py`, `tests/test_portal_ekleri_indeks.py`, `tests/test_assistant_docx.py`, `tests/test_assistant_ek_oku.py` (yeni) | Görev testleri | 3–10 |
| `tests/test_assistant_core.py` | Yönlendirme testleri: `ek_oku`, 27 araç | 10 |
| `dashboard/src/types.ts`, `components/patterns/EkBaglantisi.{tsx,scss}` (yeni), `HomeworkTracker.tsx`, `NextThing.{tsx,scss}`, `Announcements.tsx`, `theme/ted-theme.scss` | Ek bağlantısı yüzeyleri | 11 |
| `dashboard/tests/e2e/portal-ekleri.spec.ts` (yeni) | Ek e2e | 11 |
| `dashboard/src/utils/portalSusu.ts` (yeni), `CourseContent.tsx`, `dashboard/tests/e2e/dersler-portal-susu.spec.ts` (yeni) | Tarayıcı savunması | 12 |
| `src/ocr_katmani.py` (yeni) | Metinsiz PDF sayfası → `pdftoppm` → Claude Haiku 4.5 görüsü (Markdown) ya da Tesseract; sayfa önbelleği, aylık USD defteri, güven etiketi | 14 |
| `tests/sahte_ocr.py`, `tests/test_ocr_katmani.py`, `tests/test_ocr_baglanti.py` (yeni) | Sahte görü okuyucusu, sahte Tesseract, taranmış PDF üreticisi; OCR testleri | 14, 15 |
| `src/assistant_core.py`, `src/portal_ekleri_indir.py`, `src/assistant_tools.py`, `tests/conftest.py` | OCR bağlantısı: `FileAdapters`/indeksleyici, ek metni, `ek_oku`, testlerde OCR kapalı | 15 |
| `CLAUDE.md` | Veri akışı, modüller, desenler, asistan araçları, komut; OCR maddesi | 13, 15 |

---

### Görev 1: Ortak portal süsü temizleyicisi

**Files:**
- Create: `src/portal_susu.py`
- Modify: `src/assistant_tools.py:794-818` (`_ICERIK_SUSU`/`_temiz_icerik` silinir), `src/assistant_tools.py:825-856` (`icerik_ozeti` içindeki iki çağrı)
- Modify: `src/dashboard_api.py:1900,1915` (`_find_related_content` içe aktarması)
- Test: `tests/test_portal_susu.py`

**Interfaces:**
- Consumes: yok.
- Produces: `src.portal_susu` → `YORUM_BASI: str`, `YORUM_SONU: str`, `SUS_ISARETLERI: tuple[str, ...]`, `temiz_metin(metin: Any) -> str`, `temiz_icerik_kaydi(kayit: Any) -> Any`, `temiz_dersler(dersler: Any) -> Any`, `temiz_haftalar(haftalar: Any) -> Any`. `tests.test_portal_susu` → `GENEL: str`, `YORUMCULAR: tuple[str, ...]`, `YORUMLAR: tuple[str, ...]`, `sizinti(metin: str) -> list[str]` (Görev 2 ve 12 kullanır).

- [ ] **Step 1: Başlangıç kırmızılarını kaydet**

Run: `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && DASHBOARD_SECRET_KEY=yerel-test-anahtari-portal-ekleri .venv/bin/python -m pytest -q -p no:cacheprovider 2>&1 | tail -15` (Bash timeout 600000)
Expected: özet satırı (~6 dakika). Kırmızı test varsa adlarını görev raporuna yaz; bunlar "önceden kırmızı" sayılır.

- [ ] **Step 2: Başarısız testi yaz**

`tests/test_portal_susu.py`:

```python
"""Portal UI residue (plan docs/superpowers/plans/2026-09-28-portal-ekleri.md, Görev 1).

The shapes are the real ones measured in output/scraped_data.json on
2026-09-28 — "N Yorum yapıldı!" / "Daha fazla oku", then per comment a name
line, a like-count line and the comment, then "Yorum Ekle" — with invented
names and words. No real student appears here.
"""
import json

from src.portal_susu import (SUS_ISARETLERI, temiz_dersler, temiz_haftalar,
                             temiz_icerik_kaydi, temiz_metin)

YORUMCULAR = ("Kurgu Öğrenci Bir", "Uydurma Öğrenci İki", "Deneme Öğrenci Üç")
YORUMLAR = ("çok güzel olmuş", "harika bir etkinlik", "ben de katılacağım")

GENEL = (
    "Okulumuzda Bilim Şenliği Başlıyor\n"
    "TED Rönesans Koleji | 22.09.2026\n"
    "  3 Yorum yapıldı!\n"
    "  Daha fazla oku\n"
    "Kurgu Öğrenci Bir\n3\nçok güzel olmuş\n"
    "Uydurma Öğrenci İki\n0\nharika bir etkinlik \n"
    "Deneme Öğrenci Üç\n1\nben de katılacağım\n"
    "Yorum Ekle\n"
    "\n"
    "Veli Toplantısı Duyurusu\n"
    "TED Rönesans Koleji | 21.09.2026\n"
    "Toplantı perşembe 19:00'da konferans salonunda.\n"
    "  İlk yorum yapan sen olmak ister misin?\n"
    "  Daha fazla oku\n"
    "Yorum Ekle"
)


def sizinti(metin):
    """Every name, comment or chrome string still present in `metin`."""
    return [s for s in (*YORUMCULAR, *YORUMLAR, *SUS_ISARETLERI) if s in metin]


def test_okul_gonderisi_kalir_yorum_blogu_gider():
    temiz = temiz_metin(GENEL)
    assert sizinti(temiz) == []
    assert temiz == (
        "Okulumuzda Bilim Şenliği Başlıyor\n"
        "TED Rönesans Koleji | 22.09.2026\n"
        "\n"
        "Veli Toplantısı Duyurusu\n"
        "TED Rönesans Koleji | 21.09.2026\n"
        "Toplantı perşembe 19:00'da konferans salonunda."
    )


def test_kapanmayan_yorum_blogu_metnin_sonuna_kadar_atilir():
    # 87 cards were measured ending right at "Daha fazla oku", and the scraper
    # cuts a tab's text at 8,000 characters: an unclosed block is a cut one.
    kesik = ("Kitap Fuarı\nTED Rönesans Koleji | 23.09.2026\n  2 Yorum yapıldı!\n"
             "  Daha fazla oku\nKurgu Öğrenci Bir\n4\nçok güz")
    assert temiz_metin(kesik) == "Kitap Fuarı\nTED Rönesans Koleji | 23.09.2026"


def test_yorum_icindeki_bos_satir_blogu_bitirmez():
    # The old rule ended the block at any blank line; a comment holding one
    # leaked every comment after it.
    metin = ("Duyuru\n  Daha fazla oku\nKurgu Öğrenci Bir\n2\nilk satır\n\n"
             "Uydurma Öğrenci İki\n1\nharika bir etkinlik\nYorum Ekle\nSonraki paragraf")
    temiz = temiz_metin(metin)
    assert sizinti(temiz) == []
    assert temiz == "Duyuru\nSonraki paragraf"


def test_bosluk_farki_isareti_gizlemez():
    # Selenium hands over rendered text: NBSPs and doubled spaces included.
    nbsp = chr(0xA0)
    metin = f"Başlık\n{nbsp} Daha  fazla oku{nbsp}\nKurgu Öğrenci Bir\nYorum{nbsp}Ekle\nGövde"
    assert temiz_metin(metin) == "Başlık\nGövde"


def test_iki_kez_uygulamak_degistirmez():
    bir = temiz_metin(GENEL)
    assert temiz_metin(bir) == bir


def test_bos_ve_metin_olmayan_girdi():
    assert temiz_metin(None) == ""
    assert temiz_metin("") == ""
    assert temiz_metin(42) == "42"


def test_icerik_kaydi_her_metin_alanini_temizler_yalniz_yorum_karti_atar():
    kayit = {
        "tab_id": "tab_genel",
        "text": GENEL,
        "cards": [GENEL,
                  "  Daha fazla oku\nKurgu Öğrenci Bir\n3\nçok güzel olmuş\nYorum Ekle",
                  "TED Rönesans Koleji | 22.09.2026"],
        "items": ["Kurgu madde", "  Daha fazla oku\nUydurma Öğrenci İki\nYorum Ekle"],
        "tables": [{"headers": ["Başlık"],
                    "rows": [["Şenlik\n  Daha fazla oku\nDeneme Öğrenci Üç\nYorum Ekle"]]}],
    }
    temiz = temiz_icerik_kaydi(kayit)
    assert sizinti(json.dumps(temiz, ensure_ascii=False)) == []
    assert temiz["tab_id"] == "tab_genel"
    assert len(temiz["cards"]) == 2          # the comments-only card is gone
    assert temiz["items"] == ["Kurgu madde"]
    assert temiz["tables"][0]["rows"] == [["Şenlik"]]
    assert kayit["cards"][0] == GENEL        # the input is not mutated


def test_hata_kaydi_ve_bicimsiz_girdi_oldugu_gibi_doner():
    assert temiz_icerik_kaydi({"tab_id": "ders_2", "error": "x"}) == {"tab_id": "ders_2", "error": "x"}
    assert temiz_icerik_kaydi("x") == "x"


def test_dersler_ve_haftalar():
    haftalar = {"1. Hafta 14 Eyl. - 20 Eyl.": {
        "Genel": {"tab_id": "tab_genel", "text": GENEL, "cards": [GENEL], "items": [], "tables": []}}}
    temiz = temiz_haftalar(haftalar)
    assert sizinti(json.dumps(temiz, ensure_ascii=False)) == []
    assert temiz_dersler({"Genel": {"text": GENEL}})["Genel"]["text"].startswith("Okulumuzda")
    assert temiz_haftalar([]) == []
    assert temiz_dersler(None) is None
```

- [ ] **Step 3: Kırmızı olduğunu gör**

Run: `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && DASHBOARD_SECRET_KEY=yerel-test-anahtari-portal-ekleri .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_portal_susu.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.portal_susu'`.

- [ ] **Step 4: Modülü yaz**

`src/portal_susu.py`:

```python
"""Portal UI residue, removed from scraped text in one place.

The portal renders a course tab's posts with its own chrome — "N Yorum
yapıldı!", "Daha fazla oku", "Yorum Ekle", "İlk yorum yapan sen olmak ister
misin?" — and, between "Daha fazla oku" and "Yorum Ekle", the comment block:
per comment another child's name, a like count and the comment. Measured
2026-09-28 in output/scraped_data.json: 445 such blocks, mostly in the
"Genel" school feed. None of it is the teacher's or the school's content and
the names are not ours to pass on, so it is dropped before storage
(scrape_all, run_sync), at the API boundary (dashboard_api) and again in the
browser (dashboard/src/utils/portalSusu.ts, a port of this file).
"""
from __future__ import annotations

import re
from typing import Any

YORUM_BASI = "Daha fazla oku"
YORUM_SONU = "Yorum Ekle"
# The chrome strings, as tests and the frontend port assert against.
SUS_ISARETLERI = (YORUM_BASI, YORUM_SONU,
                  "İlk yorum yapan sen olmak ister misin?", "Yorum yapıldı!")
_SUS_SATIRI = re.compile(
    r"^(?:Daha fazla oku|Yorum Ekle|İlk yorum yapan sen olmak ister misin\?|\d+ Yorum yapıldı!)$")


def temiz_metin(metin: Any) -> str:
    """`metin` without the portal's chrome and without any comment block.

    A block runs from "Daha fazla oku" to "Yorum Ekle". A blank line does not
    end it (a comment can hold one), and a block that never closes runs to
    the end of the text: 87 cards were measured ending right after "Daha
    fazla oku" and the scraper cuts a tab at 8,000 characters, so an unclosed
    block is a cut one — dropping the tail is the side that never leaks a
    name. Lines are whitespace-normalised (the portal renders NBSPs and
    doubled spaces) and runs of blank lines collapse to one.
    """
    satirlar: list[str] = []
    yorumda = False
    for ham in str("" if metin is None else metin).split("\n"):
        s = " ".join(ham.split())
        if yorumda:
            if s == YORUM_SONU:
                yorumda = False
            continue
        if s == YORUM_BASI:
            yorumda = True
            continue
        if _SUS_SATIRI.match(s):
            continue
        if not s:
            if satirlar and satirlar[-1]:
                satirlar.append("")
            continue
        satirlar.append(s)
    return "\n".join(satirlar).strip()


def _temiz_hucre(deger: Any) -> Any:
    return temiz_metin(deger) if isinstance(deger, str) else deger


def _temiz_tablo(tablo: Any) -> Any:
    if not isinstance(tablo, dict) or "rows" not in tablo:
        return tablo
    satirlar = []
    for satir in tablo.get("rows") or []:
        if isinstance(satir, list):
            satirlar.append([_temiz_hucre(h) for h in satir])
        elif isinstance(satir, dict):
            satirlar.append({k: _temiz_hucre(v) for k, v in satir.items()})
        else:
            satirlar.append(_temiz_hucre(satir))
    return {**tablo, "rows": satirlar}


def temiz_icerik_kaydi(kayit: Any) -> Any:
    """One course tab ({tab_id, text, tables, items, cards}) cleaned; a card
    or item that was nothing but a comment block is dropped. A non-dict comes
    back unchanged, and a failed tab ({tab_id, error}) has nothing to clean.
    Never mutates its input."""
    if not isinstance(kayit, dict):
        return kayit
    temiz = dict(kayit)
    if "text" in kayit:
        temiz["text"] = temiz_metin(kayit.get("text"))
    for alan in ("items", "cards"):
        if isinstance(kayit.get(alan), list):
            temiz[alan] = [t for t in (_temiz_hucre(x) for x in kayit[alan]) if t != ""]
    if isinstance(kayit.get("tables"), list):
        temiz["tables"] = [_temiz_tablo(t) for t in kayit["tables"]]
    return temiz


def temiz_dersler(dersler: Any) -> Any:
    """{course: tab} — ders_icerikleri, /api/content."""
    if not isinstance(dersler, dict):
        return dersler
    return {ad: temiz_icerik_kaydi(kayit) for ad, kayit in dersler.items()}


def temiz_haftalar(haftalar: Any) -> Any:
    """{week label: {course: tab}} — ders_icerikleri_haftalar, /api/content/weeks."""
    if not isinstance(haftalar, dict):
        return haftalar
    return {etiket: temiz_dersler(dersler) for etiket, dersler in haftalar.items()}
```

- [ ] **Step 5: Eski kopyayı kaldır, çağıranları taşı**

`src/assistant_tools.py`: 794-818 arasındaki blok (yorum satırları "# Course content cards carry the portal's own chrome …", `_ICERIK_SUSU = re.compile(...)` ve `def _temiz_icerik(...)` gövdesi) tamamen silinir. İçe aktarmaların sonuna (`from src import assistant_kitaplar, assistant_modules` satırının altına) ekle:

```python
from src.portal_susu import temiz_metin
```

`icerik_ozeti` içinde iki yer:

```python
    govde = temiz_metin(kayit.get("text"))
```

```python
        ekle(temiz_metin(kart))
```

`src/dashboard_api.py` `_find_related_content` içinde:

```python
    from src.portal_susu import temiz_metin
```

ve kart döngüsünde:

```python
            ilk = next((s for s in temiz_metin(kart).split("\n") if s.strip()), "")
```

Doğrula: `grep -rn "_temiz_icerik\|_ICERIK_SUSU" src/ tests/` çıktısı boş olmalı.

- [ ] **Step 6: Yeşil olduğunu gör**

Run: `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && DASHBOARD_SECRET_KEY=yerel-test-anahtari-portal-ekleri .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_portal_susu.py tests/test_assistant_ogrenci_araclari.py tests/test_exams.py`
Expected: PASS (mevcut `test_yorum_blogu_ve_portal_susu_atilir` ve `relatedContent` testleri dahil).

- [ ] **Step 7: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && test "$(git branch --show-current)" = feat/portal-ekleri && echo dal-dogru
git add src/portal_susu.py src/assistant_tools.py src/dashboard_api.py tests/test_portal_susu.py
git commit -m "$(cat <<'EOF'
Portal süsü temizleyicisini tek modüle taşı (src/portal_susu.py)

Yorum bloğu yalnız "Yorum Ekle" ile biter; kapanmayan blok metnin sonuna
kadar atılır; satırlar boşluk-normalize edilir. Gerçek biçim, uydurma adlarla
sabitlendi.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Görev 2: Temizleyiciyi kazıyıcıda, birleştirmede ve API sınırında uygula

**Files:**
- Modify: `src/scrape_all.py:19-20` (içe aktarma), `:608-653` (`_scrape_homework_detail` açıklaması), `:935-1012` (`_icerik_acik_hafta` + yeni `_icerik_kaydi`), `:1375` (ek sayfa metni)
- Modify: `src/run_sync.py` (içe aktarma; `:405-416` birleştirme bloğu → `_icerik_birlestir`)
- Modify: `src/dashboard_api.py` (içe aktarma; `_combined_homework_rows` `:804`, `content` `:1593`, `portal_pages` `:1600`, `_icerik_haftalari` `:1638`, `announcements` `:1658`, `_canli_ders_icerikleri` `:909`)
- Modify: `src/assistant_core.py:740` (ödev açıklaması), `:881` (ek sayfa metni)
- Test: `tests/test_portal_susu_uygulama.py`

**Interfaces:**
- Consumes: Görev 1 `temiz_metin`, `temiz_icerik_kaydi`, `temiz_dersler`, `temiz_haftalar`; `tests.test_portal_susu.GENEL`, `sizinti`.
- Produces: `scrape_all._icerik_kaydi(tab_id: str, panel_text: str, tables_data: list, items: list[str], cards: list[str]) -> dict`; `run_sync._icerik_birlestir(data: dict, onceki: dict) -> None` (yerinde değiştirir); `dashboard_api._duyuru_satiri(satir: Any) -> Any` (Görev 8 imzasını `(satir, ekler)` yapar).

- [ ] **Step 1: Başarısız testi yaz**

`tests/test_portal_susu_uygulama.py`:

```python
"""Where the residue cleaner runs (plan 2026-09-28-portal-ekleri, Görev 2):
storage (scrape_all, run_sync's merge), the API boundary and the BM25 text.
Invented names only — see tests/test_portal_susu.py."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["TEST_AUTH_BYPASS"] = "1"

import src.run_sync as run_sync  # noqa: E402
import src.scrape_all as scrape_all  # noqa: E402
from src.assistant_core import _fmt_scraped_data  # noqa: E402
from tests.test_portal_susu import GENEL, sizinti  # noqa: E402

HAFTA = "2. Hafta 21 Eyl. - 27 Eyl."


def _kayit(metin=GENEL):
    return {"tab_id": "tab_genel", "text": metin, "tables": [], "items": [], "cards": [metin]}


# ── (a) storage ──────────────────────────────────────────────────────────────

def test_sekme_kaydi_saklanmadan_once_temizlenir_tavanlar_kalir():
    uzun = "Gövde cümlesi. " * 700                     # ~10,500 chars
    kayit = scrape_all._icerik_kaydi("tab_genel", uzun + "\n" + GENEL, [],
                                     ["Kurgu madde"], [GENEL, "x" * 3000])
    assert sizinti(json.dumps(kayit, ensure_ascii=False)) == []
    assert len(kayit["text"]) == 8000
    assert kayit["items"] == ["Kurgu madde"]
    assert [len(k) for k in kayit["cards"]][1] == 2000


class _Popup:
    """The homework popup: a description after <hr>, no links."""
    def __init__(self, html):
        self.page_source = html

    def get(self, url):
        pass

    def find_elements(self, by, sel):
        return []


def test_odev_aciklamasi_temiz_saklanir(monkeypatch):
    monkeypatch.setattr(scrape_all.time, "sleep", lambda *_: None)
    html = ('<div class="col-md-12"><label>Ödev Detayı</label><hr>'
            "<p>Sayfa 12-13 okunacak.</p><p>Daha fazla oku</p><p>Kurgu Öğrenci Bir</p>"
            "<p>Yorum Ekle</p></div>")
    detay = scrape_all._scrape_homework_detail(_Popup(html), "1", "2")
    assert detay["description"] == "Sayfa 12-13 okunacak."


def test_onceki_turlarin_haftalari_birlestirirken_temizlenir():
    onceki = {"ders_icerikleri_haftalar": {"1. Hafta 14 Eyl. - 20 Eyl.": {"Genel": _kayit()}}}
    data = {"ders_icerikleri": {"guncel": {"Genel": _kayit()}, "guncel_hafta": HAFTA,
                                "haftalar": {HAFTA: {"Genel": _kayit()}}}}
    run_sync._icerik_birlestir(data, onceki)
    assert set(data["ders_icerikleri_haftalar"]) == {"1. Hafta 14 Eyl. - 20 Eyl.", HAFTA}
    assert data["ders_icerikleri"]["Genel"]["text"].startswith("Okulumuzda")
    assert sizinti(json.dumps(data, ensure_ascii=False)) == []


def test_okunamayan_icerik_onceki_okumayi_temiz_tutar():
    # A failed tab keeps last run's reading (_son_okuma) in the split shape.
    onceki = {"ders_icerikleri": {"Genel": _kayit()},
              "ders_icerikleri_haftalar": {HAFTA: {"Genel": _kayit()}}}
    data = {"ders_icerikleri": onceki["ders_icerikleri"]}
    run_sync._icerik_birlestir(data, onceki)
    assert sizinti(json.dumps(data, ensure_ascii=False)) == []
    assert list(data["ders_icerikleri_haftalar"]) == [HAFTA]


# ── (b) API boundary ─────────────────────────────────────────────────────────

VERI = {
    "ders_programi": [],
    "ders_icerikleri": {"Genel": _kayit()},
    "ders_icerikleri_haftalar": {HAFTA: {"Genel": _kayit()}},
    "odevlerim": {"summary": "", "homework": {"headers": [], "rows": [{
        "Ders Adı": "Türkçe", "Ödev Başlığı": "Okuma", "Ödev Son Teslim Tarihi": "30.09.2026 12:00",
        "Ödev Durumu": "Değerlendirilmemiş",
        "detail": {"description": "Sayfa 12\n  Daha fazla oku\nKurgu Öğrenci Bir\nYorum Ekle",
                   "attachments": []}}]}},
    "duyurular": {"announcements": [{"e-Posta Başlık": "Gezi",
                                     "e-Posta İçerik": "Gezi cuma.\n  Daha fazla oku\nKurgu Öğrenci Bir\nYorum Ekle",
                                     "Ekleri": "-", "Yayın Tarihi": "22.09.2026"}]},
    "ek_sayfalar": {"mla_kaynakca": {"title": "MLA", "empty": False, "documents": [],
                                     "text": "Rehber\n  Daha fazla oku\nKurgu Öğrenci Bir\nYorum Ekle"}},
}


@pytest.fixture
def api(monkeypatch, tmp_path):
    import src.dashboard_api as api
    monkeypatch.setattr(api, "_scraped", lambda: json.loads(json.dumps(VERI)))
    monkeypatch.setattr(api, "_load_photo_homework_rows", lambda: [])
    monkeypatch.setattr(api, "OUTPUT_DIR", str(tmp_path))
    api.app.config["TESTING"] = True
    return api


@pytest.mark.parametrize("yol", ["/api/content", "/api/content/weeks", "/api/homework",
                                 "/api/announcements", "/api/pages"])
def test_api_ham_veriyi_temiz_sunar(api, yol):
    with api.app.test_client() as c:
        cevap = c.get(yol)
    assert cevap.status_code == 200
    assert sizinti(cevap.get_data(as_text=True)) == []
    assert sizinti(json.dumps(cevap.get_json(), ensure_ascii=False)) == []


def test_okul_gonderisi_api_de_kalir(api):
    with api.app.test_client() as c:
        genel = c.get("/api/content").get_json()["Genel"]
    assert genel["text"].startswith("Okulumuzda Bilim Şenliği Başlıyor")


def test_asistanin_canli_kaynaklari_da_temiz(api):
    assert sizinti(json.dumps(api._canli_ders_icerikleri(), ensure_ascii=False)) == []
    assert sizinti(json.dumps(api._canli_odevler(), ensure_ascii=False)) == []


# ── the BM25 text ───────────────────────────────────────────────────────────

def test_indeks_metni_odev_ve_sayfa_susunu_tasimaz():
    assert sizinti(_fmt_scraped_data(json.loads(json.dumps(VERI)))) == []
```

- [ ] **Step 2: Kırmızı olduğunu gör**

Run: `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && DASHBOARD_SECRET_KEY=yerel-test-anahtari-portal-ekleri .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_portal_susu_uygulama.py`
Expected: FAIL — `_icerik_kaydi`/`_icerik_birlestir` yok; API testleri "Kurgu Öğrenci Bir" sızıntısıyla kırmızı.

- [ ] **Step 3: Kazıyıcı**

`src/scrape_all.py` 20. satırın altına:

```python
from src.portal_susu import temiz_icerik_kaydi, temiz_metin
```

`_scrape_homework_detail` içinde iki atama:

```python
                detail["description"] = temiz_metin("\n".join(parts))
```

```python
                detail["description"] = temiz_metin(full.replace(lbl_text, "", 1).strip())
```

`_icerik_acik_hafta`'nın hemen üstüne yeni yardımcı:

```python
def _icerik_kaydi(tab_id, panel_text, tables_data, items, cards):
    """One course tab as stored: portal chrome and comment blocks out
    (src/portal_susu.py) *before* the length caps, so a cap can no longer cut
    a block open and keep the half that holds other children's names."""
    kayit = temiz_icerik_kaydi({
        "tab_id": tab_id,
        "text": panel_text,
        "tables": tables_data,
        "items": items,
        "cards": cards,
    })
    kayit["text"] = kayit["text"][:8000]
    kayit["items"] = [t[:2000] for t in kayit["items"]]
    kayit["cards"] = [t[:2000] for t in kayit["cards"] if len(t) > 5]
    return kayit
```

`_icerik_acik_hafta` içinde: `items.append(text[:2000])` → `items.append(text)`; `cards.append(text[:2000])` → `cards.append(text)`; ve

```python
            all_content[ders_name] = _icerik_kaydi(tab_id, panel_text, tables_data, items, cards)
```

(eski `all_content[ders_name] = {"tab_id": …, "text": panel_text[:8000], …}` sözlüğünün yerine; `except` dalındaki `{"tab_id": tab_id, "error": str(e)}` değişmez).

`scrape_ek_sayfalar` içinde:

```python
                "text": temiz_metin(veri.get("metin", "")),
```

- [ ] **Step 4: run_sync birleştirmesi**

`src/run_sync.py` içe aktarmalarına (`from src.archive_year import archive_year_local` altına):

```python
from src.portal_susu import temiz_dersler, temiz_haftalar  # noqa: E402
```

`_okunamadi_kaydi`'nın altına:

```python
def _icerik_birlestir(data, onceki):
    """Split scrape_ders_icerikleri's two shapes and keep the weeks earlier
    runs collected — cleaned (src/portal_susu.py), so weeks stored before
    the cleaner existed lose their comment blocks on the first run after
    deploy instead of carrying other children's names forever.

    `ders_programi` is not merged: it holds the open week only, because every
    week the portal offers renders the same grid.
    """
    icerik = data.get("ders_icerikleri")
    if isinstance(icerik, dict) and "haftalar" in icerik:
        data["ders_icerikleri"] = icerik.get("guncel") or {}
        data["ders_icerikleri_haftalar"] = {
            **(onceki.get("ders_icerikleri_haftalar") or {}),
            **(icerik.get("haftalar") or {}),
        }
    elif onceki.get("ders_icerikleri_haftalar"):
        data["ders_icerikleri_haftalar"] = onceki["ders_icerikleri_haftalar"]
    data["ders_icerikleri"] = temiz_dersler(data.get("ders_icerikleri") or {})
    if "ders_icerikleri_haftalar" in data:
        data["ders_icerikleri_haftalar"] = temiz_haftalar(data["ders_icerikleri_haftalar"])
```

`main()` içindeki birleştirme bloğunu (yorum `# \`ders_programi\` is not merged …` ile başlayıp `data["ders_icerikleri_haftalar"] = onceki["ders_icerikleri_haftalar"]` ile biten, ~402-413) tek satırla değiştir; `[HAFTA]` print'i kalır:

```python
        _icerik_birlestir(data, onceki)
```

- [ ] **Step 5: API sınırı ve indeks metni**

`src/dashboard_api.py` içe aktarmalarına (`from src.hafta_secici import …` altına):

```python
from src.portal_susu import temiz_dersler, temiz_haftalar, temiz_metin
```

`_combined_homework_rows` döngüsünde `rows.append(r)`'den hemen önce:

```python
        detay = r.get("detail")
        if isinstance(detay, dict):
            # Portal chrome and comment blocks never reach a surface
            # (src/portal_susu.py); a description is cleaned like course content.
            r["detail"] = {**detay, "description": temiz_metin(detay.get("description"))}
```

`content()`:

```python
    return jsonify(temiz_dersler(data.get("ders_icerikleri", {})))
```

`_icerik_haftalari` içinde `if not isinstance(haftalar, dict): haftalar = {}`'den sonra:

```python
    haftalar = temiz_haftalar(haftalar)
```

`_canli_ders_icerikleri` içinde:

```python
    guncel = temiz_dersler(data.get("ders_icerikleri"))
```

`portal_pages` içindeki `dolu` sözlüğü:

```python
    dolu = {
        k: {**v, "text": temiz_metin(v.get("text"))} for k, v in sayfalar.items()
        if isinstance(v, dict) and not v.get("empty")
    }
```

`announcements` ve yeni yardımcı:

```python
def _duyuru_satiri(satir):
    """An announcement row with every text field cleaned; links untouched."""
    if not isinstance(satir, dict):
        return satir
    return {k: (temiz_metin(v) if isinstance(v, str) and not k.endswith("_url") else v)
            for k, v in satir.items()}


@app.route("/api/announcements")
@require_auth
def announcements():
    data = _scraped()
    ann = data.get("duyurular", {}).get("announcements", [])
    return jsonify({"announcements": [_duyuru_satiri(a) for a in ann]})
```

`src/assistant_core.py` `_fmt_scraped_data` içinde, içe aktarmalara:

```python
    from src.portal_susu import temiz_metin
```

ödev döngüsünde:

```python
                desc = temiz_metin(detail.get("description", ""))
```

ek sayfalar döngüsünde:

```python
        if str(kayit.get("text") or "").strip():
            satirlar.append(temiz_metin(kayit["text"]))
```

- [ ] **Step 6: Yeşil olduğunu gör**

Run: `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && DASHBOARD_SECRET_KEY=yerel-test-anahtari-portal-ekleri .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_portal_susu_uygulama.py tests/test_portal_susu.py tests/test_okunamadi_koruma.py tests/test_hafta_kapsami.py tests/test_ek_sayfalar.py tests/test_dashboard_api.py tests/test_assistant_ogrenci_araclari.py tests/test_exams.py`
Expected: PASS.

- [ ] **Step 7: Gerçek veriye karşı salt-okunur doğrula**

Run (yalnız sayı yazdırır; ana checkout'a yazmaz):

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && .venv/bin/python - <<'EOF'
import json
from src.portal_susu import SUS_ISARETLERI, temiz_dersler, temiz_haftalar
d = json.load(open("/mnt/thunderbolt/workspaces/TED/output/scraped_data.json", encoding="utf-8"))
ham = json.dumps({k: d.get(k) for k in ("ders_icerikleri", "ders_icerikleri_haftalar")}, ensure_ascii=False)
temiz = json.dumps({"a": temiz_dersler(d.get("ders_icerikleri")),
                    "b": temiz_haftalar(d.get("ders_icerikleri_haftalar"))}, ensure_ascii=False)
for m in SUS_ISARETLERI:
    print(f"{m}: {ham.count(m)} -> {temiz.count(m)}")
EOF
```

Expected: her satırda sağdaki sayı `0` (soldakiler 2026-09-28'de "Daha fazla oku" için 445 ölçüldü; artmış olabilir). Çıktıyı görev raporuna yaz.

- [ ] **Step 8: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && test "$(git branch --show-current)" = feat/portal-ekleri && echo dal-dogru
git add src/scrape_all.py src/run_sync.py src/dashboard_api.py src/assistant_core.py tests/test_portal_susu_uygulama.py
git commit -m "$(cat <<'EOF'
Portal süsünü kazıyıcıda, birleştirmede ve API sınırında temizle

Sekme kaydı kırpılmadan önce temizlenir; run_sync önceki haftaları da
temizleyerek birleştirir; /api/content, /api/content/weeks, ödev açıklaması,
duyuru ve ek sayfa metinleri ile BM25 metni temiz sunulur.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Görev 3: Ek toplayıcısı ve deposu (`src/portal_ekleri.py`)

**Files:**
- Create: `src/portal_ekleri.py`
- Modify: `.gitignore` (sona)
- Test: `tests/test_portal_ekleri.py`

**Interfaces:**
- Consumes: `src.json_utils.atomic_json_dump(data, path: str)`.
- Produces (`src.portal_ekleri`):
  - Sabitler: `EK_DIZINI`, `IZLEYICI`, `PORTAL_HOST = "portal.tedronesans.k12.tr"`, `KIMLIK_DESENI` (16 hex), `DOSYA_UZANTILARI`, `METIN_ONEKI = "PORTAL EKİ · "`; durumlar `DURUM_BEKLIYOR="bekliyor"`, `DURUM_INDIRILDI="indirildi"`, `DURUM_ERISILEMEDI="erisilemedi"`, `DURUM_COK_BUYUK="cok_buyuk"`, `DURUM_HATA="hata"`, `DURUM_BAGLANTI="baglanti"`; metin durumları `METIN_VAR="var"`, `METIN_YOK="yok"`, `METIN_DESTEKLENMIYOR="desteklenmiyor"`, `METIN_BEKLIYOR="bekliyor"`, `METIN_HATA="hata"`.
  - `ek_turu(url) -> str` (`"sharepoint"|"drive"|"google-docs"|"portal"|"dosya"|"baglanti"`), `kanonik_adres(url) -> str`, `ek_kimligi(url) -> str`, `indirme_adresi(url) -> str | None`.
  - `tahmini_ad(url) -> str`, `sayfa_belgesi_adi(baslik: str, sira: int, toplam: int) -> str`, `duyuru_eki_adi(satir: dict, anahtar: str) -> str`, `odev_kaynagi(satir: dict) -> dict[str, str]`.
  - `@dataclass EkAdayi(url: str, ad: str, kaynaklar: list[dict[str, str]])` + özellikler `kimlik`, `tur`; `ekleri_topla(veri) -> list[EkAdayi]`.
  - `class EkDeposu(proje_koku)`: `.dizin: Path`, `.izleyici_yolu: Path`, `oku() -> dict[str, dict]`, `yaz(ekler) -> None`, `kayit(kimlik) -> dict | None`, `dosya_yolu(kayit) -> Path | None`, `metin_yolu(kimlik) -> Path`, `meta_yolu(kimlik) -> Path`, `meta(kimlik) -> dict`.
  - `ek_basligi(kayit_ya_da_meta: dict) -> str`, `ek_ozeti(ekler: dict, url, ad) -> dict` (`{name, url, id, tedyUrl, status[, reason]}`), `metin_govdesi(ham: str) -> str`.

- [ ] **Step 1: Başarısız testi yaz**

`tests/test_portal_ekleri.py`:

```python
"""Attachment links: recognise, name, locate, collect (plan 2026-09-28-portal-ekleri,
Görev 3). Hosts, paths and ids are invented; the shapes are the measured ones."""
import json
from pathlib import Path

import pytest

from src.portal_ekleri import (DURUM_BAGLANTI, DURUM_BEKLIYOR, DURUM_ERISILEMEDI,
                               DURUM_INDIRILDI, KIMLIK_DESENI, METIN_ONEKI, EkDeposu,
                               ek_basligi, ek_kimligi, ek_ozeti, ek_turu, ekleri_topla,
                               indirme_adresi, metin_govdesi, sayfa_belgesi_adi)

SP_URL = ("https://ornekokul-my.sharepoint.com/:b:/g/personal/ogretmen_ornekokul_k12_tr/"
          "EaBcDeFgHiJkLmNoPqRsTuV?e=AbC123")
DRIVE_KIMLIK = "1AbCdEfGhIjKlMnOpQrStUvWxYz012345"
DRIVE_URL = f"https://drive.google.com/file/d/{DRIVE_KIMLIK}/preview"
DOCS_URL = ("https://docs.google.com/document/d/1ZyXwVuTsRqPoNmLkJiHgFeDcBa98765/edit"
            "?usp=sharing&ouid=100000000000000000000")
PORTAL_URL = "https://portal.tedronesans.k12.tr/dosyalar/odev/ornek-calisma.pdf"
YOUTUBE = "https://www.youtube.com/watch?v=ornekvideo01"


@pytest.mark.parametrize("url,tur", [
    (SP_URL, "sharepoint"),
    ("https://ornekokul-my.sharepoint.com/:f:/g/personal/ogretmen_ornekokul_k12_tr/EkLaSoR?e=q1", "baglanti"),
    ("https://ornekokul-my.sharepoint.com/personal/ogretmen/Documents/calisma.docx", "sharepoint"),
    (DRIVE_URL, "drive"),
    (f"https://drive.google.com/open?id={DRIVE_KIMLIK}", "drive"),
    ("https://drive.google.com/drive/folders/1KlAsOr0000000000", "baglanti"),
    (DOCS_URL, "google-docs"),
    ("https://docs.google.com/presentation/d/1SuNuM0000000000000/edit", "google-docs"),
    ("https://docs.google.com/forms/d/e/1FAIpQLSornek/viewform", "baglanti"),
    (PORTAL_URL, "portal"),
    ("https://portal.tedronesans.k12.tr/pages/proje_istekler/p_ders_projeler", "baglanti"),
    ("https://ornek.edu.tr/belgeler/K%C4%B1lavuz%20Sayfa.pdf", "dosya"),
    ("https://teams.microsoft.com/l/meetup-join/19%3aornek", "baglanti"),
    (YOUTUBE, "baglanti"),
    ("javascript:void(0)", "baglanti"),
    ("", "baglanti"),
])
def test_ek_turu(url, tur):
    assert ek_turu(url) == tur


def test_ayni_drive_dosyasinin_her_bicimi_ayni_kimlik():
    bicimler = [DRIVE_URL, DRIVE_URL.replace("/preview", "/view?usp=sharing"),
                f"https://drive.google.com/open?id={DRIVE_KIMLIK}",
                f"https://drive.google.com/uc?export=download&id={DRIVE_KIMLIK}"]
    assert len({ek_kimligi(u) for u in bicimler}) == 1
    assert KIMLIK_DESENI.match(ek_kimligi(DRIVE_URL))


def test_sharepoint_kimligi_e_parametresinden_bagimsiz():
    assert ek_kimligi(SP_URL) == ek_kimligi(SP_URL.replace("e=AbC123", "e=ZzZ999"))
    assert ek_kimligi(SP_URL) != ek_kimligi(SP_URL.replace("EaBcDe", "EzYxWv"))


def test_indirme_adresleri():
    assert indirme_adresi(SP_URL) == SP_URL + "&download=1"
    assert indirme_adresi(SP_URL + "&download=1") == SP_URL + "&download=1"
    assert indirme_adresi(DRIVE_URL) == f"https://drive.google.com/uc?export=download&id={DRIVE_KIMLIK}"
    assert indirme_adresi(DOCS_URL) == ("https://docs.google.com/document/d/"
                                        "1ZyXwVuTsRqPoNmLkJiHgFeDcBa98765/export?format=pdf")
    assert indirme_adresi(PORTAL_URL) == PORTAL_URL
    assert indirme_adresi(YOUTUBE) is None


VERI = {
    "odevlerim": {"summary": "", "homework": {"headers": [], "rows": [{
        "Ders Adı": "Sosyal Bilgiler", "Ödev Başlığı": "Kitap okuma ödevi",
        "Ödev Son Teslim Tarihi": "25.09.2026 12:00",
        "detail": {"description": "Sayfa 12-13", "attachments": [
            {"name": "Sayfa 12-13.pdf", "url": SP_URL},
            {"name": "Konu videosu", "url": YOUTUBE}]}}]}},
    "ek_sayfalar": {
        "mla_kaynakca": {"title": "MLA Kaynakça Hazırlama Rehberi", "empty": False,
                         "url": "https://portal.tedronesans.k12.tr/pages/proje_istekler/p_kaynakca",
                         "documents": [DRIVE_URL, DRIVE_URL.replace("/preview", "/view")]},
        "akademik_durustluk": {"title": "Akademik Dürüstlük Politikası", "empty": False,
                               "documents": [DRIVE_URL]},
    },
    "duyurular": {"announcements": [{"e-Posta Başlık": "Gezi izni", "Yayın Tarihi": "22.09.2026",
                                     "Ekleri": "izin-formu.pdf",
                                     "Ekleri_url": "https://ornek.edu.tr/formlar/izin-formu.pdf"}]},
    "takim_calismalari": {"activities": {"rows": [
        {"Teams Link": "https://teams.microsoft.com/l/meetup-join/19%3aornek"}]}},
    "ders_icerikleri": {"Matematik": {"tab_id": "ders_2", "text":
                        "Çalışma kağıdı: https://ornek.edu.tr/kagitlar/kesirler.pdf, iyi çalışmalar.",
                        "cards": [], "items": [], "tables": []}},
}


def test_toplayici_her_bolumu_okur_bir_kimlige_bir_aday():
    adaylar = {a.kimlik: a for a in ekleri_topla(VERI)}
    sp = adaylar[ek_kimligi(SP_URL)]
    assert sp.ad == "Sayfa 12-13.pdf" and sp.tur == "sharepoint"
    assert sp.kaynaklar == [{"section": "odevler",
                             "item": "Sosyal Bilgiler|Kitap okuma ödevi|25.09.2026 12:00",
                             "title": "Kitap okuma ödevi", "course": "Sosyal Bilgiler"}]
    assert adaylar[ek_kimligi(YOUTUBE)].tur == "baglanti"       # the teacher put it there
    drive = adaylar[ek_kimligi(DRIVE_URL)]
    # Two URL shapes on one page and the same file on a second page: one candidate.
    assert drive.ad == "MLA Kaynakça Hazırlama Rehberi (1. belge)"
    assert [k["item"] for k in drive.kaynaklar] == ["mla_kaynakca", "akademik_durustluk"]
    duyuru = adaylar[ek_kimligi("https://ornek.edu.tr/formlar/izin-formu.pdf")]
    assert duyuru.ad == "izin-formu.pdf" and duyuru.kaynaklar[0]["section"] == "duyurular"
    genel = adaylar[ek_kimligi("https://ornek.edu.tr/kagitlar/kesirler.pdf")]
    assert genel.ad == "kesirler.pdf"
    assert genel.kaynaklar[0] == {"section": "ders_icerikleri", "item": "ders_icerikleri/Matematik/text",
                                  "title": "Matematik", "course": "Matematik"}
    # The generic scan takes files only: no Teams meeting, no portal page.
    assert all("teams.microsoft.com" not in a.url and "/pages/" not in a.url for a in adaylar.values())
    assert len(adaylar) == 5


def test_toplayici_bicimsiz_veride_patlamaz():
    assert ekleri_topla(None) == []
    assert ekleri_topla({"odevlerim": [], "ek_sayfalar": "x", "duyurular": None}) == []


def test_sayfa_belgesi_adi():
    assert sayfa_belgesi_adi("MLA", 1, 1) == "MLA"
    assert sayfa_belgesi_adi("MLA", 2, 3) == "MLA (2. belge)"


def test_depo_gidis_donus_ve_bozuk_izleyici(tmp_path):
    depo = EkDeposu(tmp_path)
    assert depo.oku() == {}
    kimlik = ek_kimligi(SP_URL)
    depo.yaz({kimlik: {"id": kimlik, "status": DURUM_BEKLIYOR}, "../kotu": {"id": "x"}})
    assert list(depo.oku()) == [kimlik]
    assert depo.kayit(kimlik)["status"] == DURUM_BEKLIYOR
    assert depo.kayit("../kotu") is None
    depo.izleyici_yolu.write_text("{bozuk", encoding="utf-8")
    assert depo.oku() == {}


def test_dosya_yolu_yalniz_kendi_dosyasini_verir(tmp_path):
    depo = EkDeposu(tmp_path)
    kimlik = ek_kimligi(SP_URL)
    depo.dizin.mkdir(parents=True)
    (depo.dizin / f"{kimlik}.pdf").write_bytes(b"%PDF-1.7")
    assert depo.dosya_yolu({"id": kimlik, "file": f"{kimlik}.pdf"}) == depo.dizin / f"{kimlik}.pdf"
    for kotu in ("../../etc/passwd", f"{kimlik}.pdf/../x", "0123456789abcdef.pdf", f"{kimlik}.pdfx1"):
        assert depo.dosya_yolu({"id": kimlik, "file": kotu}) is None
    assert depo.dosya_yolu({"id": kimlik, "file": f"{kimlik}.docx"}) is None     # not on disk
    assert depo.dosya_yolu(None) is None


def test_meta_ve_baslik(tmp_path):
    depo = EkDeposu(tmp_path)
    kimlik = ek_kimligi(SP_URL)
    depo.dizin.mkdir(parents=True)
    depo.meta_yolu(kimlik).write_text(json.dumps(
        {"id": kimlik, "name": "Sayfa 12-13.pdf", "title": "Kitap okuma ödevi"}), encoding="utf-8")
    assert ek_basligi(depo.meta(kimlik)) == "Sayfa 12-13.pdf · Kitap okuma ödevi"
    assert depo.meta("../x") == {}
    assert ek_basligi({"name": "Rehber", "source": {"title": "Rehber"}}) == "Rehber"
    assert ek_basligi({}) == "Portal eki"


def test_ek_ozeti_durumlari():
    kimlik = ek_kimligi(SP_URL)
    ekler = {kimlik: {"id": kimlik, "status": DURUM_INDIRILDI, "file": f"{kimlik}.pdf"}}
    assert ek_ozeti(ekler, SP_URL, "Sayfa 12-13.pdf") == {
        "name": "Sayfa 12-13.pdf", "url": SP_URL, "id": kimlik,
        "tedyUrl": f"/api/ekler/{kimlik}", "status": DURUM_INDIRILDI}
    ekler[kimlik] = {"id": kimlik, "status": DURUM_ERISILEMEDI, "reason": "kaynak giriş istiyor"}
    ozet = ek_ozeti(ekler, SP_URL, "Sayfa 12-13.pdf")
    assert ozet["tedyUrl"] is None and ozet["status"] == DURUM_ERISILEMEDI
    assert ozet["reason"] == "kaynak giriş istiyor"
    assert ek_ozeti({}, SP_URL, "x")["status"] == DURUM_BEKLIYOR          # not collected yet
    assert ek_ozeti({}, YOUTUBE, "Video") == {"name": "Video", "url": YOUTUBE, "id": None,
                                               "tedyUrl": None, "status": DURUM_BAGLANTI}


def test_metin_govdesi_baslik_paragrafini_atar():
    assert metin_govdesi(f"{METIN_ONEKI}Ek · Ödev\n\nSoru 1\n\nSoru 2\n") == "Soru 1\n\nSoru 2"
    assert metin_govdesi(f"{METIN_ONEKI}Ek · Ödev\n(Metin katmanı yok.)\n") == ""
    assert metin_govdesi("başlıksız metin") == "başlıksız metin"


def test_ek_kopyalari_git_disinda():
    kurallar = (Path(__file__).resolve().parents[1] / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "content/portal-ekleri/" in kurallar
```

- [ ] **Step 2: Kırmızı olduğunu gör**

Run: `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && DASHBOARD_SECRET_KEY=yerel-test-anahtari-portal-ekleri .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_portal_ekleri.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.portal_ekleri'`.

- [ ] **Step 3: Modülü yaz**

`src/portal_ekleri.py`:

```python
"""Portal attachments: what the portal links to, and where TEDY keeps its copies.

Measured 2026-09-28 in output/scraped_data.json: homework details carry
`detail.attachments[] = {name, url}` — SharePoint personal share links
(`…-my.sharepoint.com/:b:/g/personal/…?e=…`) and one Google Docs link — and
two ek_sayfalar pages carry Google Drive `/file/d/<id>/preview` iframes.
Announcements can carry `<column>_url` (0 announcements that day). Nothing
was downloaded: every surface linked straight to the host.

This module is the pure half: it recognises a link, names it with a stable
id (a hash of its canonical URL), says how to fetch it, collects every link
the scrape holds and reads/writes the tracker (output/portal_ekleri.json).
The network half is src/portal_ekleri_indir.py.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Iterator
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit

from src.json_utils import atomic_json_dump

EK_DIZINI = PurePosixPath("content/portal-ekleri")
IZLEYICI = PurePosixPath("output/portal_ekleri.json")
PORTAL_HOST = "portal.tedronesans.k12.tr"
KIMLIK_DESENI = re.compile(r"^[0-9a-f]{16}$")
_DOSYA_ADI = re.compile(r"^([0-9a-f]{16})\.[a-z0-9]{1,5}$")

DURUM_BEKLIYOR = "bekliyor"
DURUM_INDIRILDI = "indirildi"
DURUM_ERISILEMEDI = "erisilemedi"
DURUM_COK_BUYUK = "cok_buyuk"
DURUM_HATA = "hata"
DURUM_BAGLANTI = "baglanti"

METIN_VAR = "var"
METIN_YOK = "yok"
METIN_DESTEKLENMIYOR = "desteklenmiyor"
METIN_BEKLIYOR = "bekliyor"
METIN_HATA = "hata"
# First line of every <id>.txt: the index finds an attachment by its name
# too, and ek_oku drops this paragraph before paging the body.
METIN_ONEKI = "PORTAL EKİ · "

DOSYA_UZANTILARI = frozenset({".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx",
                              ".odt", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".zip"})
_DRIVE_DOSYA = re.compile(r"^/file/d/([A-Za-z0-9_-]{10,})")
_DRIVE_KIMLIK = re.compile(r"^[A-Za-z0-9_-]{10,}$")
_DOCS = re.compile(r"^/(document|presentation|spreadsheets)/d/([A-Za-z0-9_-]{10,})")
_SP_PAYLASIM = re.compile(r"^/:([a-z]):/")
_URL = re.compile(r"https?://[^\s\"'<>]+")
_KAYNAK_SINIRI = 5
_TUR_ADI = {"sharepoint": "SharePoint dosyası", "drive": "Google Drive dosyası",
            "google-docs": "Google dokümanı", "portal": "Portal dosyası", "dosya": "Dosya"}


def _drive_kimligi(p) -> str | None:
    m = _DRIVE_DOSYA.match(p.path)
    if m:
        return m.group(1)
    if p.path in ("/open", "/uc"):
        kimlik = dict(parse_qsl(p.query)).get("id", "")
        return kimlik if _DRIVE_KIMLIK.match(kimlik) else None
    return None


def ek_turu(url: Any) -> str:
    """What a link is, decided from the URL alone. `baglanti` is a link that
    is not one file — a folder share, a form, a video page — opened at its
    source and never downloaded."""
    p = urlsplit(str(url or "").strip())
    if p.scheme not in ("http", "https") or not p.hostname:
        return "baglanti"
    host = p.hostname
    uzanti = PurePosixPath(unquote(p.path)).suffix.lower()
    if host.endswith(".sharepoint.com"):
        m = _SP_PAYLASIM.match(p.path)
        if m:
            # ":f:" is a folder share: many files, not one.
            return "baglanti" if m.group(1) == "f" else "sharepoint"
        return "sharepoint" if uzanti in DOSYA_UZANTILARI else "baglanti"
    if host == "drive.google.com":
        return "drive" if _drive_kimligi(p) else "baglanti"
    if host == "docs.google.com":
        if _DOCS.match(p.path):
            return "google-docs"
        return "drive" if _DRIVE_DOSYA.match(p.path) else "baglanti"
    if uzanti in DOSYA_UZANTILARI:
        return "portal" if host == PORTAL_HOST else "dosya"
    return "baglanti"


def kanonik_adres(url: Any) -> str:
    """One spelling per file: Drive's preview/view/open/uc forms collapse to
    /file/d/<id>, a Docs link loses /edit and its query, a SharePoint share
    link loses `?e=` (a per-recipient token; the path names the file)."""
    ham = str(url or "").strip()
    p = urlsplit(ham)
    tur = ek_turu(ham)
    if tur == "drive":
        return f"https://drive.google.com/file/d/{_drive_kimligi(p)}"
    if tur == "google-docs":
        m = _DOCS.match(p.path)
        return f"https://docs.google.com/{m.group(1)}/d/{m.group(2)}"
    if tur == "sharepoint":
        return urlunsplit(("https", p.netloc.lower(), p.path, "", ""))
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path, p.query, ""))


def ek_kimligi(url: Any) -> str:
    return hashlib.sha256(kanonik_adres(url).encode("utf-8")).hexdigest()[:16]


def indirme_adresi(url: Any) -> str | None:
    """Where the file itself answers (probe 2026-09-28): SharePoint with
    `download=1`, Drive's `uc?export=download`, Docs/Slides/Sheets as
    `/export?format=pdf`, anything else as it is. None for a `baglanti`."""
    ham = str(url or "").strip()
    p = urlsplit(ham)
    tur = ek_turu(ham)
    if tur == "sharepoint":
        sorgu = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if k != "download"]
        return urlunsplit((p.scheme, p.netloc, p.path, urlencode(sorgu + [("download", "1")]), ""))
    if tur == "drive":
        return f"https://drive.google.com/uc?export=download&id={_drive_kimligi(p)}"
    if tur == "google-docs":
        m = _DOCS.match(p.path)
        return f"https://docs.google.com/{m.group(1)}/d/{m.group(2)}/export?format=pdf"
    if tur in ("portal", "dosya"):
        return urlunsplit((p.scheme, p.netloc, p.path, p.query, ""))
    return None


def tahmini_ad(url: Any) -> str:
    son = PurePosixPath(unquote(urlsplit(str(url or "")).path)).name
    if PurePosixPath(son).suffix.lower() in DOSYA_UZANTILARI:
        return son
    return _TUR_ADI.get(ek_turu(url), "Bağlantı")


def sayfa_belgesi_adi(baslik: str, sira: int, toplam: int) -> str:
    baslik = " ".join(str(baslik or "").split()) or "Portal sayfası"
    return baslik if toplam <= 1 else f"{baslik} ({sira}. belge)"


def duyuru_eki_adi(satir: dict[str, Any], anahtar: str) -> str:
    sutun = anahtar[: -len("_url")]
    deger = " ".join(str(satir.get(sutun) or "").split())
    return deger if deger and deger != "-" else (sutun or "Duyuru eki")


def odev_kaynagi(satir: dict[str, Any]) -> dict[str, str]:
    ders = str(satir.get("Ders Adı") or "").strip()
    baslik = str(satir.get("Ödev Başlığı") or "").strip()
    teslim = str(satir.get("Ödev Son Teslim Tarihi") or "").strip()
    return {"section": "odevler", "item": f"{ders}|{baslik}|{teslim}", "title": baslik, "course": ders}


@dataclass
class EkAdayi:
    url: str
    ad: str
    kaynaklar: list[dict[str, str]] = field(default_factory=list)

    @property
    def kimlik(self) -> str:
        return ek_kimligi(self.url)

    @property
    def tur(self) -> str:
        return ek_turu(self.url)


def _metinler(deger: Any, yol: list[str]) -> Iterator[tuple[list[str], str]]:
    if isinstance(deger, str):
        yield yol, deger
    elif isinstance(deger, dict):
        for k, v in deger.items():
            yield from _metinler(v, yol + [str(k)])
    elif isinstance(deger, list):
        for i, v in enumerate(deger):
            yield from _metinler(v, yol + [str(i)])


def _genel_kaynak(yol: list[str]) -> dict[str, str]:
    bolum, ders, baslik = yol[0], "", ""
    if bolum == "ders_icerikleri" and len(yol) > 1:
        ders = baslik = yol[1]
    elif bolum == "ders_icerikleri_haftalar" and len(yol) > 2:
        ders, baslik = yol[2], f"{yol[2]} · {yol[1]}"
    return {"section": bolum, "item": "/".join(yol), "title": baslik, "course": ders}


def ekleri_topla(veri: Any) -> list[EkAdayi]:
    """Every attachment link the scrape holds, one candidate per id: homework
    first, then portal pages, announcements, and whatever a generic scan of
    every other string finds (so a future section's files are caught).
    Homework, page and announcement links are taken whatever they point at —
    the teacher put them there — and a non-file one becomes `baglanti`; the
    generic scan takes file-looking links only, so a Teams meeting or a
    portal page is never mistaken for a document."""
    veri = veri if isinstance(veri, dict) else {}
    adaylar: dict[str, EkAdayi] = {}

    def ekle(url: Any, ad: Any, kaynak: dict[str, str], yalniz_dosya: bool) -> None:
        url = str(url or "").strip().rstrip(".,;:)")
        if not url.lower().startswith(("http://", "https://")):
            return
        if yalniz_dosya and ek_turu(url) == "baglanti":
            return
        kimlik = ek_kimligi(url)
        aday = adaylar.get(kimlik)
        if aday is None:
            adaylar[kimlik] = EkAdayi(url=url, ad=" ".join(str(ad or "").split()) or tahmini_ad(url),
                                      kaynaklar=[kaynak])
        elif kaynak not in aday.kaynaklar and len(aday.kaynaklar) < _KAYNAK_SINIRI:
            aday.kaynaklar.append(kaynak)

    odevlerim = veri.get("odevlerim") if isinstance(veri.get("odevlerim"), dict) else {}
    odevler = odevlerim.get("homework") if isinstance(odevlerim.get("homework"), dict) else {}
    for satir in odevler.get("rows") or []:
        if not isinstance(satir, dict):
            continue
        detay = satir.get("detail") if isinstance(satir.get("detail"), dict) else {}
        for ek in detay.get("attachments") or []:
            if isinstance(ek, dict):
                ekle(ek.get("url"), ek.get("name"), odev_kaynagi(satir), yalniz_dosya=False)

    sayfalar = veri.get("ek_sayfalar") if isinstance(veri.get("ek_sayfalar"), dict) else {}
    for anahtar, sayfa in sayfalar.items():
        if not isinstance(sayfa, dict):
            continue
        belgeler = [b for b in sayfa.get("documents") or [] if isinstance(b, str)]
        baslik = str(sayfa.get("title") or anahtar)
        for i, url in enumerate(belgeler, 1):
            ekle(url, sayfa_belgesi_adi(baslik, i, len(belgeler)),
                 {"section": "ek_sayfalar", "item": str(anahtar), "title": baslik, "course": ""},
                 yalniz_dosya=False)

    duyurular = veri.get("duyurular") if isinstance(veri.get("duyurular"), dict) else {}
    for satir in duyurular.get("announcements") or []:
        if not isinstance(satir, dict):
            continue
        baslik = str(satir.get("e-Posta Başlık") or satir.get("Başlık") or "").strip()
        oge = f"{satir.get('Yayın Tarihi', '')}|{baslik}"
        for anahtar, url in satir.items():
            if str(anahtar).endswith("_url"):
                ekle(url, duyuru_eki_adi(satir, str(anahtar)),
                     {"section": "duyurular", "item": oge, "title": baslik, "course": ""},
                     yalniz_dosya=False)

    bilinen = set(adaylar)
    for bolum, deger in veri.items():
        for yol, metin in _metinler(deger, [str(bolum)]):
            for url in _URL.findall(metin):
                url = url.rstrip(".,;:)")
                if ek_turu(url) == "baglanti" or ek_kimligi(url) in bilinen:
                    continue
                ekle(url, tahmini_ad(url), _genel_kaynak(yol), yalniz_dosya=True)
    return list(adaylar.values())


class EkDeposu:
    """content/portal-ekleri (the copies, <id>.txt text, <id>.meta.json
    sidecars, .parca/ part files) and output/portal_ekleri.json (the
    tracker), resolved under one project root."""

    def __init__(self, proje_koku: str | Path):
        self.koku = Path(proje_koku)
        self.dizin = self.koku / EK_DIZINI
        self.izleyici_yolu = self.koku / IZLEYICI

    def oku(self) -> dict[str, dict[str, Any]]:
        try:
            veri = json.loads(self.izleyici_yolu.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        ekler = veri.get("ekler") if isinstance(veri, dict) else None
        if not isinstance(ekler, dict):
            return {}
        return {k: v for k, v in ekler.items() if KIMLIK_DESENI.match(str(k)) and isinstance(v, dict)}

    def yaz(self, ekler: dict[str, dict[str, Any]]) -> None:
        atomic_json_dump({"surum": 1, "guncellendi": datetime.now().isoformat(timespec="seconds"),
                          "ekler": ekler}, str(self.izleyici_yolu))

    def kayit(self, kimlik: Any) -> dict[str, Any] | None:
        kimlik = str(kimlik or "")
        return self.oku().get(kimlik) if KIMLIK_DESENI.match(kimlik) else None

    def dosya_yolu(self, kayit: dict[str, Any] | None) -> Path | None:
        """The record's own copy, or None. The name is checked against the
        record's id and a strict pattern, so no stored value can point
        outside the directory."""
        kayit = kayit if isinstance(kayit, dict) else {}
        m = _DOSYA_ADI.match(str(kayit.get("file") or ""))
        if not m or m.group(1) != kayit.get("id"):
            return None
        yol = self.dizin / m.group(0)
        return yol if yol.is_file() else None

    def metin_yolu(self, kimlik: str) -> Path:
        return self.dizin / f"{kimlik}.txt"

    def meta_yolu(self, kimlik: str) -> Path:
        return self.dizin / f"{kimlik}.meta.json"

    def meta(self, kimlik: Any) -> dict[str, Any]:
        if not KIMLIK_DESENI.match(str(kimlik or "")):
            return {}
        try:
            veri = json.loads(self.meta_yolu(str(kimlik)).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return veri if isinstance(veri, dict) else {}


def ek_basligi(kayit: dict[str, Any]) -> str:
    """"<ek adı> · <ödev başlığı>" — how a citation and ek_oku name an
    attachment; never a path. Takes a tracker record or a .meta.json."""
    kayit = kayit if isinstance(kayit, dict) else {}
    ad = " ".join(str(kayit.get("name") or "").split()) or "Portal eki"
    kaynak = kayit.get("source") if isinstance(kayit.get("source"), dict) else {}
    baglam = " ".join(str(kaynak.get("title") or kayit.get("title") or "").split())
    return f"{ad} · {baglam}" if baglam and baglam != ad else ad


def ek_ozeti(ekler: dict[str, dict[str, Any]], url: Any, ad: Any) -> dict[str, Any]:
    """One attachment as an API payload carries it: `tedyUrl` only when TEDY
    holds the copy; `status` always, so a surface can say why there is none."""
    url = str(url or "")
    ozet: dict[str, Any] = {"name": str(ad or ""), "url": url, "id": None,
                            "tedyUrl": None, "status": DURUM_BAGLANTI}
    if ek_turu(url) == "baglanti":
        return ozet
    kimlik = ek_kimligi(url)
    kayit = ekler.get(kimlik) or {}
    durum = str(kayit.get("status") or DURUM_BEKLIYOR)
    ozet.update(id=kimlik, status=durum)
    if durum == DURUM_INDIRILDI and kayit.get("file"):
        ozet["tedyUrl"] = f"/api/ekler/{kimlik}"
    elif kayit.get("reason"):
        ozet["reason"] = str(kayit["reason"])
    return ozet


def metin_govdesi(ham: str) -> str:
    """An <id>.txt without its METIN_ONEKI header paragraph."""
    if ham.startswith(METIN_ONEKI):
        return ham.partition("\n\n")[2].strip("\n")
    return ham
```

`.gitignore` sonuna:

```
# Portal attachment copies, extracted text and sidecars (src/portal_ekleri.py)
content/portal-ekleri/
```

- [ ] **Step 4: Yeşil olduğunu gör**

Run: `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && DASHBOARD_SECRET_KEY=yerel-test-anahtari-portal-ekleri .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_portal_ekleri.py`
Expected: PASS.

- [ ] **Step 5: Gerçek veriye karşı salt-okunur toplayıcı sayımı**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && .venv/bin/python - <<'EOF'
import collections, json
from src.portal_ekleri import ekleri_topla
d = json.load(open("/mnt/thunderbolt/workspaces/TED/output/scraped_data.json", encoding="utf-8"))
adaylar = ekleri_topla(d)
print(len(adaylar), collections.Counter(a.tur for a in adaylar),
      collections.Counter(a.kaynaklar[0]["section"] for a in adaylar))
EOF
```

Expected (2026-09-28 ölçümüne göre): SharePoint 5 + google-docs 1 ödevlerden, Drive 2 ya da 4 ek_sayfalar'dan (aynı dosya iki sayfada ise tek aday). Yalnız sayıları raporla; URL yazdırma.

- [ ] **Step 6: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && test "$(git branch --show-current)" = feat/portal-ekleri && echo dal-dogru
git add src/portal_ekleri.py .gitignore tests/test_portal_ekleri.py
git commit -m "$(cat <<'EOF'
Portal ekleri toplayıcısı ve deposu

Bağlantıyı sınıflar, kanonik adresin karmasıyla kararlı kimlik verir,
indirme adresini çözer; ödev, ek sayfa, duyuru ve genel taramadan adayları
toplar; izleyiciyi (output/portal_ekleri.json) okur/yazar.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Görev 4: `FileAdapters`'a `.docx` metin çıkarma

**Files:**
- Modify: `src/assistant_core.py:13-27` (içe aktarmalar), `:51-53` (uzantı kümeleri), `:1005` civarı (`extract` içinde görsel dalından önce), `FileAdapters`'a yeni yöntem
- Test: `tests/test_assistant_docx.py`

**Interfaces:**
- Consumes: yok.
- Produces: `assistant_core.DOCX_EXTENSIONS = {".docx"}`, `assistant_core.DOCX_XML_SINIRI: int`, `FileAdapters._extract_docx_text(file_path: Path) -> str`; `FileAdapters.extract(...)` `.docx` için `source_kind` `"docx"` ya da (metin yoksa) `"metadata"` + `warnings ["docx_no_text"]` döner. Görev 6 `metin_cikar` bunu kullanır.

- [ ] **Step 1: Başarısız testi yaz**

`tests/test_assistant_docx.py`:

```python
""".docx text through the assistant's FileAdapters (plan 2026-09-28-portal-ekleri,
Görev 4): stdlib zipfile + word/document.xml, no new dependency."""
import zipfile

import src.assistant_core as core
from src.assistant_core import AssistantConfig, FileAdapters

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def docx_yaz(yol, govde_xml):
    xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           f'<w:document xmlns:w="{W}"><w:body>{govde_xml}</w:body></w:document>')
    with zipfile.ZipFile(yol, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("word/document.xml", xml)
    return yol


def _adaptor(tmp_path):
    return FileAdapters(AssistantConfig.from_project_root(tmp_path))


def test_paragraflar_sekme_ve_satir_sonu_okunur(tmp_path):
    yol = docx_yaz(tmp_path / "odev.docx",
                   "<w:p><w:r><w:t>Bumerang kitabı çalışması</w:t></w:r></w:p>"
                   "<w:p><w:r><w:t>Soru 1</w:t><w:tab/><w:t>(10 puan)</w:t><w:br/>"
                   "<w:t xml:space=\"preserve\">Açıkla.</w:t></w:r></w:p>"
                   "<w:p></w:p>")
    sonuc = _adaptor(tmp_path).extract(yol, "content/portal-ekleri/odev.docx")
    assert sonuc["source_kind"] == "docx"
    assert sonuc["text"] == "Bumerang kitabı çalışması\n\nSoru 1\t(10 puan)\nAçıkla."


def test_bozuk_docx_metadata_olur_cop_metin_degil(tmp_path):
    yol = tmp_path / "bozuk.docx"
    yol.write_bytes(b"PK" + b"0" * 200)
    sonuc = _adaptor(tmp_path).extract(yol, "content/portal-ekleri/bozuk.docx")
    assert sonuc["source_kind"] == "metadata" and sonuc["warnings"] == ["docx_no_text"]
    assert "PK00" not in sonuc["text"]


def test_document_xml_yoksa_metadata(tmp_path):
    yol = tmp_path / "bos.docx"
    with zipfile.ZipFile(yol, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
    assert _adaptor(tmp_path).extract(yol, "x.docx")["source_kind"] == "metadata"


def test_asiri_buyuk_document_xml_okunmaz(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "DOCX_XML_SINIRI", 10)
    yol = docx_yaz(tmp_path / "buyuk.docx", "<w:p><w:r><w:t>uzun metin</w:t></w:r></w:p>")
    assert _adaptor(tmp_path).extract(yol, "x.docx")["source_kind"] == "metadata"


def test_dtd_tasiyan_document_xml_ayristirilmaz(tmp_path):
    # An attachment is someone else's file: entity expansion ("billion laughs")
    # or an external entity must never run. A real .docx declares no DTD.
    xml = ('<?xml version="1.0"?><!DOCTYPE w:document [<!ENTITY a "Bumerang">]>'
           f'<w:document xmlns:w="{W}"><w:body><w:p><w:r><w:t>&a;</w:t></w:r></w:p></w:body></w:document>')
    yol = tmp_path / "dtd.docx"
    with zipfile.ZipFile(yol, "w") as z:
        z.writestr("word/document.xml", xml)
    sonuc = _adaptor(tmp_path).extract(yol, "x.docx")
    assert sonuc["source_kind"] == "metadata" and "Bumerang" not in sonuc["text"]
```

- [ ] **Step 2: Kırmızı olduğunu gör**

Run: `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && DASHBOARD_SECRET_KEY=yerel-test-anahtari-portal-ekleri .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_assistant_docx.py`
Expected: FAIL — `.docx` bugün "unknown extension" dalına düşüyor (`source_kind` `"text"`/`"metadata"`, `"docx"` değil) ve `DOCX_XML_SINIRI` yok.

- [ ] **Step 3: Uygula**

`src/assistant_core.py` içe aktarmalarına (`import time` altına):

```python
import zipfile
from xml.etree import ElementTree
```

`IMAGE_EXTENSIONS` satırının altına:

```python
DOCX_EXTENSIONS = {".docx"}
# word/document.xml is read whole; a real homework sheet is kilobytes. The cap
# keeps a hostile or broken archive (a zip bomb) from ballooning in memory.
DOCX_XML_SINIRI = 50 * 1024 * 1024
_WORD_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
```

`FileAdapters.extract` içinde `if ext in IMAGE_EXTENSIONS:` satırından hemen önce:

```python
        if ext in DOCX_EXTENSIONS:
            text = self._extract_docx_text(file_path)
            return {
                "text": text or self._metadata_only_text(rel_path, file_path, reason="docx_no_text"),
                "source_kind": "docx" if text else "metadata",
                "confidence": 0.8 if text else 0.2,
                "warnings": [] if text else ["docx_no_text"],
            }
```

`_extract_image_text`'in üstüne yeni yöntem:

```python
    def _extract_docx_text(self, file_path: Path) -> str:
        """A .docx's paragraphs, from word/document.xml, with the stdlib only.

        Teachers attach Word sheets as often as PDFs (plan 2026-09-28
        portal-ekleri). Before this a .docx fell through to the unknown-
        extension branch and its zip bytes were read as text. Tabs and line
        breaks inside a paragraph are kept; paragraphs are blank-line
        separated so the chunker keeps them apart. An unreadable archive is
        "" (metadata only), never garbage."""
        try:
            with zipfile.ZipFile(file_path) as arsiv:
                bilgi = arsiv.getinfo("word/document.xml")
                if bilgi.file_size > DOCX_XML_SINIRI:
                    return ""
                veri = arsiv.read(bilgi)
            # No defusedxml (not installed; the design allows no new
            # dependency). A real document.xml never declares a DTD, so one
            # that does is refused before parsing — no entity of any kind is
            # expanded. Behind that, ElementTree fetches no external entity and
            # the bundled expat (2.6.1, measured 2026-09-28) refuses entity
            # amplification ("billion laughs") on its own.
            if b"<!DOCTYPE" in veri[:4096].upper():
                return ""
            kok = ElementTree.fromstring(veri)
        except (KeyError, zipfile.BadZipFile, ElementTree.ParseError, OSError, ValueError):
            return ""
        paragraflar: list[str] = []
        for p in kok.iter(f"{_WORD_NS}p"):
            parcalar: list[str] = []
            for el in p.iter():
                if el.tag == f"{_WORD_NS}t" and el.text:
                    parcalar.append(el.text)
                elif el.tag == f"{_WORD_NS}tab":
                    parcalar.append("\t")
                elif el.tag in (f"{_WORD_NS}br", f"{_WORD_NS}cr"):
                    parcalar.append("\n")
            satir = "".join(parcalar).strip()
            if satir:
                paragraflar.append(satir)
        return "\n\n".join(paragraflar)
```

- [ ] **Step 4: Yeşil olduğunu gör**

Run: `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && DASHBOARD_SECRET_KEY=yerel-test-anahtari-portal-ekleri .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_assistant_docx.py tests/test_assistant_indeks_hijyeni.py tests/test_assistant_core.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && test "$(git branch --show-current)" = feat/portal-ekleri && echo dal-dogru
git add src/assistant_core.py tests/test_assistant_docx.py
git commit -m "$(cat <<'EOF'
Asistanın dosya okuyucusuna .docx metin çıkarma ekle

Stdlib zipfile + word/document.xml; yeni bağımlılık yok. Bozuk arşiv ve
aşırı büyük XML çöp metin değil, yalnız metadata olur.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Görev 5: Tek dosya indirici ve sahte HTTP katmanı

**Files:**
- Create: `src/portal_ekleri_indir.py` (bu görevde yalnız tek-dosya kısmı)
- Create: `tests/sahte_http.py`
- Test: `tests/test_portal_ekleri_indir.py`

**Interfaces:**
- Consumes: Görev 3 `indirme_adresi`, `PORTAL_HOST`, `DURUM_*`.
- Produces (`src.portal_ekleri_indir`): `MB`, `EK_BOYUT_SINIRI = 300 * MB`, `PARCA_BOYUTU`, `DOCX_MIME`, `XLSX_MIME`, `PPTX_MIME`; `class Butce(son_an: float, bayt: int, saat=time.monotonic)` → `bayt_harca(n)`, `kalan_sure() -> float`, `bitti() -> bool`, alan `harcanan`; `@dataclass Sonuc(durum, neden="", dosya=None, uzanti="", mime="", boyut=0, sha256="", parca_bayt=0)`; `portal_cerez_kavanozu(cerezler) -> RequestsCookieJar | None`; `html_mi(bas: bytes, icerik_turu: str) -> bool`; `tur_bul(bas: bytes, yol: Path) -> tuple[str, str]`; `drive_onay_adresi(html: str, yanit_url: str) -> str | None`; `ek_indir(oturum, kayit: dict, dizin: Path, butce: Butce, cerezler=None, sinir=EK_BOYUT_SINIRI) -> Sonuc`. `kayit` en az `{"id", "url", "type"}` taşır. Parça dosyası `dizin/.parca/<id>.part`; sonuç dosyası `dizin/<id><uzantı>`.
- Produces (`tests.sahte_http`): `MB`, `PDF`, `SP_URL`, `SP_DUVAR_URL`, `DRIVE_URL`, `DRIVE_KIMLIK`, `DOCS_URL`, `PORTAL_URL`, `YOUTUBE`, `GIRIS_DUVARI`, `DRIVE_ONAY`, `SahteYanit`, `SahteOturum`, `SahteSaat`, `aralikli(govde, icerik_turu="application/pdf")`, `docx_bayt(paragraflar)` (Görev 6 ve 7 kullanır).

- [ ] **Step 1: Sahte HTTP katmanını yaz**

`tests/sahte_http.py`:

```python
"""A fake HTTP layer for src/portal_ekleri_indir.py — no test reaches the network.

Response shapes follow what the 2026-09-28 probe measured, with invented hosts
and ids: SharePoint `download=1` (200 application/pdf, or a login wall that
ends on login.microsoftonline.com as text/html), Drive `uc?export=download`
(octet-stream, or the virus-scan confirm page with a download form), Google
Docs `/export?format=pdf`. An unplanned URL fails the test.
"""
from __future__ import annotations

import io
import zipfile
from typing import Any, Callable

from requests.structures import CaseInsensitiveDict

MB = 1024 * 1024
PDF = b"%PDF-1.7\n" + b"1 0 obj << /Type /Catalog >> endobj\n" * 60 + b"%%EOF\n"

SP_URL = ("https://ornekokul-my.sharepoint.com/:b:/g/personal/ogretmen_ornekokul_k12_tr/"
          "EaBcDeFgHiJkLmNoPqRsTuV?e=AbC123")
SP_DUVAR_URL = ("https://ornekokul-my.sharepoint.com/:b:/g/personal/ogretmen_ornekokul_k12_tr/"
                "EzYxWvUtSrQpOnMlKjIhGfE?e=XyZ789")
DRIVE_KIMLIK = "1AbCdEfGhIjKlMnOpQrStUvWxYz012345"
DRIVE_URL = f"https://drive.google.com/file/d/{DRIVE_KIMLIK}/preview"
DOCS_URL = ("https://docs.google.com/document/d/1ZyXwVuTsRqPoNmLkJiHgFeDcBa98765/edit"
            "?usp=sharing&ouid=100000000000000000000")
PORTAL_URL = "https://portal.tedronesans.k12.tr/dosyalar/odev/ornek-calisma.pdf"
YOUTUBE = "https://www.youtube.com/watch?v=ornekvideo01"

GIRIS_DUVARI = ("<!DOCTYPE html><html><head><title>Hesabınızda oturum açın</title></head>"
                "<body>Microsoft</body></html>").encode("utf-8")
DRIVE_ONAY = (
    "<!DOCTYPE html><html><body><p>Google Drive bu dosyayı virüs için tarayamıyor.</p>"
    '<form id="download-form" action="https://drive.usercontent.google.com/download" method="get">'
    '<input type="submit" value="Yine de indir">'
    f'<input type="hidden" name="id" value="{DRIVE_KIMLIK}">'
    '<input type="hidden" name="export" value="download">'
    '<input type="hidden" name="confirm" value="t">'
    '<input type="hidden" name="uuid" value="0000aaaa-11bb-22cc-33dd-444444eeeeee">'
    "</form></body></html>").encode("utf-8")


class SahteYanit:
    """What ek_indir reads from a requests.Response, and nothing more."""

    def __init__(self, status_code: int = 200, govde: bytes = b"",
                 headers: dict[str, str] | None = None, url: str = "",
                 bloklar: list[Any] | None = None):
        self.status_code = status_code
        self.govde = govde
        self.headers = CaseInsensitiveDict(headers or {})
        self.url = url
        # Explicit chunks; a callable in the list is called (to raise).
        self.bloklar = bloklar
        self.kapandi = False

    def iter_content(self, chunk_size: int = 1):
        if self.bloklar is not None:
            for blok in self.bloklar:
                yield blok() if callable(blok) else blok
            return
        for i in range(0, len(self.govde), chunk_size):
            yield self.govde[i:i + chunk_size]

    def close(self) -> None:
        self.kapandi = True


class SahteOturum:
    """Routes by URL prefix, in insertion order; records every request."""

    def __init__(self, rotalar: dict[str, Any]):
        self.rotalar = rotalar
        self.istekler: list[dict[str, Any]] = []

    def get(self, url, headers=None, stream=False, timeout=None, allow_redirects=True, cookies=None):
        self.istekler.append({"url": url, "headers": dict(headers or {}), "cookies": cookies,
                              "stream": stream, "timeout": timeout})
        for onek, yanit in self.rotalar.items():
            if url.startswith(onek):
                y = yanit(url, headers or {}) if callable(yanit) else yanit
                if not y.url:
                    y.url = url
                return y
        raise AssertionError(f"beklenmeyen istek: {url}")


class SahteSaat:
    """A monotonic clock that moves `adim` seconds every time it is read."""

    def __init__(self, adim: float):
        self.adim = adim
        self.an = 0.0

    def __call__(self) -> float:
        self.an += self.adim
        return self.an


def aralikli(govde: bytes, icerik_turu: str = "application/pdf") -> Callable[[str, dict], SahteYanit]:
    """A host that honours `Range: bytes=<n>-` (206) and says 416 past the end."""
    def yanitla(url: str, headers: dict) -> SahteYanit:
        aralik = headers.get("Range")
        if aralik:
            bas = int(aralik.split("=", 1)[1].rstrip("-"))
            if bas >= len(govde):
                return SahteYanit(416, b"", {"Content-Range": f"bytes */{len(govde)}"})
            parca = govde[bas:]
            return SahteYanit(206, parca, {"Content-Type": icerik_turu, "Content-Length": str(len(parca)),
                                           "Content-Range": f"bytes {bas}-{len(govde) - 1}/{len(govde)}"})
        return SahteYanit(200, govde, {"Content-Type": icerik_turu, "Content-Length": str(len(govde))})
    return yanitla


def docx_bayt(paragraflar: list[str]) -> bytes:
    w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    govde = "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paragraflar)
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("word/document.xml",
                   f'<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="{w}"><w:body>{govde}</w:body></w:document>')
    return tampon.getvalue()
```

- [ ] **Step 2: Başarısız testi yaz**

`tests/test_portal_ekleri_indir.py`:

```python
"""One attachment download (plan 2026-09-28-portal-ekleri, Görev 5), against the
fake HTTP layer in tests/sahte_http.py only."""
import hashlib

import pytest
import requests

from src.portal_ekleri import ek_kimligi, ek_turu
from src.portal_ekleri_indir import (DOCX_MIME, EK_BOYUT_SINIRI, MB, Butce, ek_indir,
                                     portal_cerez_kavanozu)
from tests.sahte_http import (DOCS_URL, DRIVE_KIMLIK, DRIVE_ONAY, DRIVE_URL, GIRIS_DUVARI, PDF,
                              PORTAL_URL, SP_DUVAR_URL, SP_URL, SahteOturum, SahteSaat,
                              SahteYanit, aralikli, docx_bayt)

SP = "https://ornekokul-my.sharepoint.com/"


def _kayit(url):
    return {"id": ek_kimligi(url), "url": url, "type": ek_turu(url)}


def _sinirsiz():
    return Butce(son_an=float("inf"), bayt=10 * EK_BOYUT_SINIRI)


def _bol(govde, n=MB):
    return [govde[i:i + n] for i in range(0, len(govde), n)]


def _parcalar(dizin):
    return sorted((dizin / ".parca").iterdir()) if (dizin / ".parca").exists() else []


def test_sharepoint_download_1_ile_istenir_pdf_saklanir(tmp_path):
    oturum = SahteOturum({SP: lambda u, h: SahteYanit(200, PDF, {"Content-Type": "application/pdf",
                                                                 "Content-Length": str(len(PDF))})})
    sonuc = ek_indir(oturum, _kayit(SP_URL), tmp_path, _sinirsiz())
    assert (sonuc.durum, sonuc.uzanti, sonuc.mime) == ("indirildi", ".pdf", "application/pdf")
    assert sonuc.sha256 == hashlib.sha256(PDF).hexdigest() and sonuc.boyut == len(PDF)
    istek = oturum.istekler[0]
    assert "download=1" in istek["url"] and "e=AbC123" in istek["url"]
    assert istek["cookies"] is None and istek["stream"] is True and "Range" not in istek["headers"]
    assert (tmp_path / sonuc.dosya).read_bytes() == PDF
    assert _parcalar(tmp_path) == []


def test_giris_duvari_dosya_olarak_saklanmaz(tmp_path):
    duvar = SahteYanit(200, GIRIS_DUVARI, {"Content-Type": "text/html; charset=utf-8"},
                       url="https://login.microsoftonline.com/common/oauth2/authorize?client_id=ornek")
    sonuc = ek_indir(SahteOturum({SP: duvar}), _kayit(SP_DUVAR_URL), tmp_path, _sinirsiz())
    assert sonuc.durum == "erisilemedi" and "giriş istiyor" in sonuc.neden
    assert [p.name for p in tmp_path.iterdir()] == [".parca"] and _parcalar(tmp_path) == []


def test_octet_stream_diyen_html_de_web_sayfasidir(tmp_path):
    sayfa = SahteYanit(200, b"  <!DOCTYPE html><html>klasör</html>", {"Content-Type": "application/octet-stream"})
    sonuc = ek_indir(SahteOturum({SP: sayfa}), _kayit(SP_URL), tmp_path, _sinirsiz())
    assert sonuc.durum == "erisilemedi" and "web sayfası" in sonuc.neden


def test_drive_onay_sayfasi_formdaki_ikinci_istekle_gecilir(tmp_path):
    oturum = SahteOturum({
        f"https://drive.google.com/uc?export=download&id={DRIVE_KIMLIK}":
            lambda u, h: SahteYanit(200, DRIVE_ONAY, {"Content-Type": "text/html; charset=utf-8"}),
        "https://drive.usercontent.google.com/download?":
            lambda u, h: SahteYanit(200, PDF, {"Content-Type": "application/octet-stream"}),
    })
    sonuc = ek_indir(oturum, _kayit(DRIVE_URL), tmp_path, _sinirsiz())
    assert sonuc.durum == "indirildi" and sonuc.uzanti == ".pdf"
    ikinci = oturum.istekler[1]["url"]
    assert f"id={DRIVE_KIMLIK}" in ikinci and "confirm=t" in ikinci and "uuid=" in ikinci


def test_drive_onay_sayfasi_ikinci_kez_gelirse_dongu_yok(tmp_path):
    def onay(u, h):
        return SahteYanit(200, DRIVE_ONAY, {"Content-Type": "text/html"})
    oturum = SahteOturum({"https://drive.google.com/": onay, "https://drive.usercontent.google.com/": onay})
    sonuc = ek_indir(oturum, _kayit(DRIVE_URL), tmp_path, _sinirsiz())
    assert sonuc.durum == "erisilemedi" and len(oturum.istekler) == 2


def test_google_dokumani_pdf_olarak_disari_aktarilir(tmp_path):
    oturum = SahteOturum({
        "https://docs.google.com/document/d/1ZyXwVuTsRqPoNmLkJiHgFeDcBa98765/export?format=pdf":
            SahteYanit(200, PDF, {"Content-Type": "application/pdf"})})
    sonuc = ek_indir(oturum, _kayit(DOCS_URL), tmp_path, _sinirsiz())
    assert sonuc.durum == "indirildi" and sonuc.uzanti == ".pdf"


@pytest.mark.parametrize("govde,uzanti,mime", [
    (docx_bayt(["Soru 1"]), ".docx", DOCX_MIME),
    (bytes.fromhex("89504e470d0a1a0a") + b"0" * 64, ".png", "image/png"),
    (bytes.fromhex("ffd8ffe0") + b"0" * 64, ".jpg", "image/jpeg"),
    (b"GIF89a" + b"0" * 64, ".gif", "image/gif"),
    (b"bilinmeyen ikili veri", ".bin", "application/octet-stream"),
])
def test_tur_basliktan_degil_baytlardan_okunur(tmp_path, govde, uzanti, mime):
    yanit = SahteYanit(200, govde, {"Content-Type": "application/pdf"})
    sonuc = ek_indir(SahteOturum({SP: yanit}), _kayit(SP_URL), tmp_path, _sinirsiz())
    assert (sonuc.durum, sonuc.uzanti, sonuc.mime) == ("indirildi", uzanti, mime)
    assert (tmp_path / f"{ek_kimligi(SP_URL)}{uzanti}").is_file()


@pytest.mark.parametrize("kod,durum", [(403, "erisilemedi"), (404, "erisilemedi"), (503, "hata")])
def test_http_hatalari(tmp_path, kod, durum):
    sonuc = ek_indir(SahteOturum({SP: SahteYanit(kod, b"")}), _kayit(SP_URL), tmp_path, _sinirsiz())
    assert sonuc.durum == durum and str(kod) in sonuc.neden


def test_ag_hatasi_hata_olur_istisna_kacmaz(tmp_path):
    def kopuk(u, h):
        raise requests.ConnectionError("bağlantı koptu")
    sonuc = ek_indir(SahteOturum({SP: kopuk}), _kayit(SP_URL), tmp_path, _sinirsiz())
    assert sonuc.durum == "hata" and "ConnectionError" in sonuc.neden


def test_baglanti_indirilmez(tmp_path):
    kayit = {"id": "0" * 16, "url": "https://www.youtube.com/watch?v=x", "type": "baglanti"}
    sonuc = ek_indir(SahteOturum({}), kayit, tmp_path, _sinirsiz())
    assert sonuc.durum == "erisilemedi"


def test_300_mb_ustu_govdesi_okunmadan_reddedilir(tmp_path):
    def patla():
        raise AssertionError("gövde okunmamalıydı")
    yanit = SahteYanit(200, headers={"Content-Type": "application/pdf",
                                     "Content-Length": str(EK_BOYUT_SINIRI + 1)}, bloklar=[patla])
    sonuc = ek_indir(SahteOturum({SP: yanit}), _kayit(SP_URL), tmp_path, _sinirsiz())
    assert EK_BOYUT_SINIRI == 300 * MB
    assert sonuc.durum == "cok_buyuk" and "300 MB" in sonuc.neden
    assert yanit.kapandi


def test_uzunluk_bildirmeyen_akis_sinirda_kesilir_parca_silinir(tmp_path):
    yanit = SahteYanit(200, headers={"Content-Type": "application/pdf"},
                       bloklar=_bol(PDF + b"0" * (4 * MB)))
    sonuc = ek_indir(SahteOturum({SP: yanit}), _kayit(SP_URL), tmp_path, _sinirsiz(), sinir=3 * MB)
    assert sonuc.durum == "cok_buyuk" and _parcalar(tmp_path) == []


def test_bayt_butcesi_dolunca_parca_kalir_sonraki_tur_range_ile_surer(tmp_path):
    govde = PDF + bytes(range(256)) * (4 * 4096)          # ~4 MB after a PDF head
    kayit = _kayit(SP_URL)
    oturum = SahteOturum({SP: aralikli(govde)})
    ilk = ek_indir(oturum, kayit, tmp_path, Butce(float("inf"), 2 * MB))
    assert ilk.durum == "bekliyor" and ilk.parca_bayt == 2 * MB
    assert "Range" not in oturum.istekler[0]["headers"]
    ikinci = ek_indir(oturum, kayit, tmp_path, Butce(float("inf"), 100 * MB))
    assert ikinci.durum == "indirildi"
    assert oturum.istekler[1]["headers"]["Range"] == f"bytes={2 * MB}-"
    assert (tmp_path / ikinci.dosya).read_bytes() == govde
    assert ikinci.sha256 == hashlib.sha256(govde).hexdigest() and _parcalar(tmp_path) == []


def test_sure_butcesi_dolunca_da_durur(tmp_path):
    butce = Butce(son_an=3.5, bayt=10 ** 12, saat=SahteSaat(adim=1.0))
    govde = PDF + b"0" * (5 * MB)
    sonuc = ek_indir(SahteOturum({SP: aralikli(govde)}), _kayit(SP_URL), tmp_path, butce)
    assert sonuc.durum == "bekliyor" and 0 < sonuc.parca_bayt < len(govde)


def test_onceki_tur_tam_sonda_durduysa_416_dosyayi_tamamlar(tmp_path):
    kayit = _kayit(SP_URL)
    (tmp_path / ".parca").mkdir(parents=True)
    (tmp_path / ".parca" / f"{kayit['id']}.part").write_bytes(PDF)
    sonuc = ek_indir(SahteOturum({SP: aralikli(PDF)}), kayit, tmp_path, _sinirsiz())
    assert sonuc.durum == "indirildi" and (tmp_path / sonuc.dosya).read_bytes() == PDF


def test_uyusmayan_aralik_parcayi_atar(tmp_path):
    kayit = _kayit(SP_URL)
    (tmp_path / ".parca").mkdir(parents=True)
    (tmp_path / ".parca" / f"{kayit['id']}.part").write_bytes(PDF[:100])
    yanlis = SahteYanit(206, PDF[:100], {"Content-Range": f"bytes 0-99/{len(PDF)}"})
    sonuc = ek_indir(SahteOturum({SP: yanlis}), kayit, tmp_path, _sinirsiz())
    assert sonuc.durum == "hata" and _parcalar(tmp_path) == []


def test_range_yok_sayilirsa_bastan_yazilir(tmp_path):
    kayit = _kayit(SP_URL)
    (tmp_path / ".parca").mkdir(parents=True)
    (tmp_path / ".parca" / f"{kayit['id']}.part").write_bytes(b"eski yarim")
    sonuc = ek_indir(SahteOturum({SP: SahteYanit(200, PDF, {"Content-Type": "application/pdf"})}),
                     kayit, tmp_path, _sinirsiz())
    assert sonuc.durum == "indirildi" and (tmp_path / sonuc.dosya).read_bytes() == PDF


def test_portal_cerezleri_yalniz_portal_istegine_gider(tmp_path):
    kavanoz = portal_cerez_kavanozu([
        {"name": "ASP.NET_SessionId", "value": "ornek-oturum", "domain": "portal.tedronesans.k12.tr", "path": "/"},
        {"name": "izci", "value": "x", "domain": ".google.com", "path": "/"},
    ])
    assert [c.name for c in kavanoz] == ["ASP.NET_SessionId"]
    oturum = SahteOturum({
        "https://portal.tedronesans.k12.tr/": lambda u, h: SahteYanit(200, PDF, {"Content-Type": "application/pdf"}),
        SP: lambda u, h: SahteYanit(200, PDF, {"Content-Type": "application/pdf"}),
    })
    ek_indir(oturum, _kayit(PORTAL_URL), tmp_path, _sinirsiz(), cerezler=kavanoz)
    ek_indir(oturum, _kayit(SP_URL), tmp_path, _sinirsiz(), cerezler=kavanoz)
    assert oturum.istekler[0]["cookies"] is kavanoz
    assert oturum.istekler[1]["cookies"] is None
    assert portal_cerez_kavanozu([]) is None and portal_cerez_kavanozu(None) is None
```

- [ ] **Step 3: Kırmızı olduğunu gör**

Run: `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && DASHBOARD_SECRET_KEY=yerel-test-anahtari-portal-ekleri .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_portal_ekleri_indir.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.portal_ekleri_indir'`.

- [ ] **Step 4: İndiriciyi yaz**

`src/portal_ekleri_indir.py`:

```python
"""Portal attachments, the network half: fetch a file safely, within a budget.

What the probe measured on 2026-09-28 without a login: SharePoint share links
with `download=1` answered 200 application/pdf for 4 of 5 (two over 100 MB:
112 and 101 MB) and text/html for the fifth — a login wall or a folder;
Drive's `uc?export=download` answered octet-stream for 4 of 4 up to 28 MB,
and a large file answers with a confirm page first; docs.google.com answered
HTML until asked for `/export?format=pdf`. So: a web page where a file was
expected is never stored, the type is read from the bytes, a file over 300 MB
is refused, and a download that runs out of this run's budget is kept as a
part file and resumed with a Range request on the next run.
"""
from __future__ import annotations

import hashlib
import itertools
import os
import re
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

from src.portal_ekleri import (DURUM_BEKLIYOR, DURUM_COK_BUYUK, DURUM_ERISILEMEDI, DURUM_HATA,
                               DURUM_INDIRILDI, PORTAL_HOST, indirme_adresi)

MB = 1024 * 1024
EK_BOYUT_SINIRI = 300 * MB
PARCA_BOYUTU = 1 * MB
HTML_OKUMA_SINIRI = 512 * 1024
# (connect, read) per socket operation: a stalled read is noticed in 30 s,
# which the run's reserve absorbs (run_sync.EK_YEDEK_SURE).
ZAMAN_ASIMI = (10.0, 30.0)
TARAYICI = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/129.0 Safari/537.36")
GIRIS_SAYFALARI = ("login.microsoftonline.com", "login.live.com", "accounts.google.com")
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
_PNG = bytes.fromhex("89504e470d0a1a0a")
_JPG = bytes.fromhex("ffd8ff")
_OLE = bytes.fromhex("d0cf11e0a1b11ae1")
_ZIP = bytes.fromhex("504b0304")
_ARALIK = re.compile(r"bytes\s+(\d+)-(\d+)/(\d+|\*)")
_TOPLAM = re.compile(r"bytes\s+\*/(\d+)")
_YENIDEN = "kaldığı yerden sürdürülemedi; baştan indirilecek"


class Butce:
    """One run's allowance: a monotonic deadline and a byte count. Whatever
    is left when either runs out continues on a later run."""

    def __init__(self, son_an: float, bayt: int, saat: Callable[[], float] = time.monotonic):
        self.son_an = son_an
        self.bayt = bayt
        self.saat = saat
        self.harcanan = 0

    def bayt_harca(self, n: int) -> None:
        self.harcanan += n

    def kalan_sure(self) -> float:
        return max(0.0, self.son_an - self.saat())

    def bitti(self) -> bool:
        return self.saat() >= self.son_an or self.harcanan >= self.bayt


@dataclass
class Sonuc:
    durum: str
    neden: str = ""
    dosya: str | None = None
    uzanti: str = ""
    mime: str = ""
    boyut: int = 0
    sha256: str = ""
    parca_bayt: int = 0


def portal_cerez_kavanozu(cerezler: Iterable[dict[str, Any]] | None) -> requests.cookies.RequestsCookieJar | None:
    """Selenium's cookies as a jar scoped to the portal's own domain, so a
    redirect to SharePoint or Google can never carry the portal session."""
    kavanoz = requests.cookies.RequestsCookieJar()
    for c in cerezler or []:
        if not isinstance(c, dict) or not c.get("name"):
            continue
        alan = str(c.get("domain") or PORTAL_HOST).lstrip(".")
        if alan != PORTAL_HOST and not PORTAL_HOST.endswith("." + alan):
            continue
        kavanoz.set(str(c["name"]), str(c.get("value") or ""), domain=alan, path=str(c.get("path") or "/"))
    return kavanoz if len(kavanoz) else None


def html_mi(bas: bytes, icerik_turu: str) -> bool:
    tur = (icerik_turu or "").split(";")[0].strip().lower()
    if tur in ("text/html", "application/xhtml+xml"):
        return True
    return bas.lstrip()[:15].lower().startswith((b"<!doctype html", b"<html"))


def tur_bul(bas: bytes, yol: Path) -> tuple[str, str]:
    """(extension, mime) from the first bytes — never from the host's
    Content-Type, which SharePoint and Drive set to octet-stream at will.
    Unknown bytes are `.bin`, which the dashboard only ever serves as a
    download."""
    if bas.startswith(b"%PDF-"):
        return ".pdf", "application/pdf"
    if bas.startswith(_PNG):
        return ".png", "image/png"
    if bas.startswith(_JPG):
        return ".jpg", "image/jpeg"
    if bas.startswith((b"GIF87a", b"GIF89a")):
        return ".gif", "image/gif"
    if bas[:4] == b"RIFF" and bas[8:12] == b"WEBP":
        return ".webp", "image/webp"
    if bas.startswith(_OLE):
        return ".doc", "application/msword"      # legacy Office; may be .xls/.ppt
    if bas.startswith(_ZIP):
        try:
            with zipfile.ZipFile(yol) as arsiv:
                adlar = set(arsiv.namelist())
        except (zipfile.BadZipFile, OSError):
            return ".bin", "application/octet-stream"
        if "word/document.xml" in adlar:
            return ".docx", DOCX_MIME
        if "xl/workbook.xml" in adlar:
            return ".xlsx", XLSX_MIME
        if "ppt/presentation.xml" in adlar:
            return ".pptx", PPTX_MIME
        return ".zip", "application/zip"
    return ".bin", "application/octet-stream"


def drive_onay_adresi(html: str, yanit_url: str) -> str | None:
    """The URL behind Drive's "can't scan for viruses" page: its download
    form's action plus hidden fields (id, export, confirm, uuid), or an older
    page's `confirm=<token>` link. None when the page offers neither."""
    soup = BeautifulSoup(html, "html.parser")
    form = soup.find("form", id="download-form") or next(
        (f for f in soup.find_all("form") if "download" in str(f.get("action") or "")), None)
    if form is not None:
        eylem = urljoin(yanit_url, str(form.get("action") or ""))
        alanlar = [(str(i.get("name")), str(i.get("value") or "")) for i in form.find_all("input")
                   if i.get("type") == "hidden" and i.get("name")]
        if eylem and alanlar:
            return eylem + ("&" if "?" in eylem else "?") + urlencode(alanlar)
    m = re.search(r"confirm=([0-9A-Za-z_-]+)", html)
    if m:
        p = urlsplit(yanit_url)
        sorgu = [(k, v) for k, v in parse_qsl(p.query) if k != "confirm"] + [("confirm", m.group(1))]
        return urlunsplit((p.scheme, p.netloc, p.path, urlencode(sorgu), ""))
    return None


def _html_nedeni(son_url: str) -> str:
    host = (urlsplit(son_url).hostname or "").lower()
    if any(host == g or host.endswith("." + g) for g in GIRIS_SAYFALARI):
        return "kaynak giriş istiyor; paylaşım herkese açık değil"
    return "dosya yerine bir web sayfası döndü (klasör ya da erişim sayfası)"


def _boyut(yol: Path) -> int:
    try:
        return yol.stat().st_size
    except OSError:
        return 0


def _iste(oturum: Any, url: str, baslangic: int, kavanoz: Any) -> Any:
    basliklar = {"User-Agent": TARAYICI}
    if baslangic:
        basliklar["Range"] = f"bytes={baslangic}-"
    return oturum.get(url, headers=basliklar, stream=True, timeout=ZAMAN_ASIMI,
                      allow_redirects=True, cookies=kavanoz)


def _html_oku(ilk: bytes, akis: Any) -> str:
    parcalar, toplam = [ilk], len(ilk)
    for blok in akis:
        if toplam >= HTML_OKUMA_SINIRI:
            break
        parcalar.append(blok)
        toplam += len(blok)
    return b"".join(parcalar)[:HTML_OKUMA_SINIRI].decode("utf-8", errors="replace")


def ek_indir(oturum: Any, kayit: dict[str, Any], dizin: Path, butce: Butce,
             cerezler: Any = None, sinir: int = EK_BOYUT_SINIRI) -> Sonuc:
    """Fetch one attachment into `dizin` as `<id><ext>`. Never raises for a
    network or HTTP problem — that is a Sonuc the tracker records. The portal
    cookie jar goes only to a `portal` record's request."""
    url = indirme_adresi(kayit.get("url"))
    if url is None:
        return Sonuc(DURUM_ERISILEMEDI, "dosya bağlantısı değil")
    dizin = Path(dizin)
    parca = dizin / ".parca" / f"{kayit['id']}.part"
    parca.parent.mkdir(parents=True, exist_ok=True)
    kavanoz = cerezler if kayit.get("type") == "portal" else None
    try:
        return _indir(oturum, kayit, url, parca, dizin, butce, kavanoz, sinir, onaylandi=False)
    except (requests.RequestException, OSError) as exc:
        return Sonuc(DURUM_HATA, f"ağ hatası ({type(exc).__name__})", parca_bayt=_boyut(parca))


def _indir(oturum: Any, kayit: dict[str, Any], url: str, parca: Path, dizin: Path, butce: Butce,
           kavanoz: Any, sinir: int, onaylandi: bool) -> Sonuc:
    baslangic = _boyut(parca)
    yanit = _iste(oturum, url, baslangic, kavanoz)
    try:
        kod = yanit.status_code
        aralik = str(yanit.headers.get("Content-Range", ""))
        if baslangic and kod == 416:
            m = _TOPLAM.match(aralik)
            if m and int(m.group(1)) == baslangic:
                yanit.close()
                return _tamamla(kayit, parca, dizin)   # the last run stopped exactly at the end
            parca.unlink(missing_ok=True)
            return Sonuc(DURUM_HATA, _YENIDEN)
        if baslangic and kod == 206:
            m = _ARALIK.match(aralik)
            if not m or int(m.group(1)) != baslangic:
                parca.unlink(missing_ok=True)
                return Sonuc(DURUM_HATA, _YENIDEN)
            kip = "ab"
        elif kod == 200:
            baslangic, kip = 0, "wb"                   # a host that ignores Range starts over
        elif kod in (401, 403, 404, 410):
            parca.unlink(missing_ok=True)
            return Sonuc(DURUM_ERISILEMEDI, f"kaynak {kod} döndü (paylaşım kapalı ya da dosya kaldırılmış)")
        else:
            return Sonuc(DURUM_HATA, f"kaynak {kod} döndü", parca_bayt=baslangic)

        try:
            uzunluk = int(yanit.headers.get("Content-Length") or 0)
        except ValueError:
            uzunluk = 0
        if baslangic + uzunluk > sinir:
            parca.unlink(missing_ok=True)
            return Sonuc(DURUM_COK_BUYUK, f"dosya {(baslangic + uzunluk) // MB} MB; sınır {sinir // MB} MB")

        akis = yanit.iter_content(PARCA_BOYUTU)
        ilk = next(akis, b"") if kip == "wb" else b""
        if kip == "wb" and html_mi(ilk, str(yanit.headers.get("Content-Type", ""))):
            html = _html_oku(ilk, akis)
            if kayit.get("type") == "drive" and not onaylandi:
                onay = drive_onay_adresi(html, yanit.url or url)
                if onay:
                    yanit.close()
                    return _indir(oturum, kayit, onay, parca, dizin, butce, kavanoz, sinir, onaylandi=True)
            parca.unlink(missing_ok=True)
            return Sonuc(DURUM_ERISILEMEDI, _html_nedeni(yanit.url or url))

        yazilan = baslangic
        tasti = False
        with parca.open(kip) as f:
            for blok in itertools.chain((ilk,), akis):
                if not blok:
                    continue
                if butce.bitti():
                    return Sonuc(DURUM_BEKLIYOR, "bu turun bütçesi doldu; sonraki eşitlemede "
                                                 "kaldığı yerden sürecek", parca_bayt=yazilan)
                yazilan += len(blok)
                if yazilan > sinir:
                    tasti = True
                    break
                f.write(blok)
                butce.bayt_harca(len(blok))
        if tasti:
            parca.unlink(missing_ok=True)
            return Sonuc(DURUM_COK_BUYUK, f"dosya {sinir // MB} MB sınırını aştı")
    finally:
        yanit.close()
    return _tamamla(kayit, parca, dizin)


def _tamamla(kayit: dict[str, Any], parca: Path, dizin: Path) -> Sonuc:
    """Check the finished part file and rename it into place atomically."""
    kimlik = kayit["id"]
    boyut = _boyut(parca)
    if boyut == 0:
        parca.unlink(missing_ok=True)
        return Sonuc(DURUM_HATA, "kaynak boş bir dosya döndü")
    with parca.open("rb") as f:
        bas = f.read(4096)
    if html_mi(bas, ""):
        parca.unlink(missing_ok=True)
        return Sonuc(DURUM_ERISILEMEDI, "dosya yerine bir web sayfası döndü")
    uzanti, mime = tur_bul(bas, parca)
    ozet = hashlib.sha256()
    with parca.open("rb") as f:
        for blok in iter(lambda: f.read(PARCA_BOYUTU), b""):
            ozet.update(blok)
    hedef = dizin / f"{kimlik}{uzanti}"
    for eski in dizin.glob(f"{kimlik}.*"):
        if eski != hedef and not eski.name.endswith((".txt", ".meta.json")):
            eski.unlink(missing_ok=True)
    os.replace(parca, hedef)
    return Sonuc(DURUM_INDIRILDI, "", dosya=hedef.name, uzanti=uzanti, mime=mime,
                 boyut=boyut, sha256=ozet.hexdigest())
```

- [ ] **Step 5: Yeşil olduğunu gör**

Run: `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && DASHBOARD_SECRET_KEY=yerel-test-anahtari-portal-ekleri unshare -rn .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_portal_ekleri_indir.py`
Expected: PASS (ağsız ad alanında da).

- [ ] **Step 6: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && test "$(git branch --show-current)" = feat/portal-ekleri && echo dal-dogru
git add src/portal_ekleri_indir.py tests/sahte_http.py tests/test_portal_ekleri_indir.py
git commit -m "$(cat <<'EOF'
Portal eki indiricisi: akışla parça dosyası, tür baytlardan, 300 MB tavanı

HTML (giriş duvarı, klasör) asla dosya diye saklanmaz; Drive onay sayfası
formdan geçilir; bütçe biten indirme Range ile sonraki turda sürer; portal
çerezleri yalnız portal isteğine gider. Sahte HTTP katmanıyla sınandı.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Görev 6: Eşitleme turu, metin çıkarma ve yan dosyalar

**Files:**
- Modify: `src/portal_ekleri_indir.py` (sona ekle)
- Test: `tests/test_portal_ekleri_esitle.py`

**Interfaces:**
- Consumes: Görev 3 `EkDeposu`, `ekleri_topla`, `ek_kimligi`, `kanonik_adres`, `ek_basligi`, `METIN_*`, `METIN_ONEKI`, `DURUM_*`; Görev 4 `FileAdapters` (`.docx`); Görev 5 `ek_indir`, `Butce`, `Sonuc`, `EK_BOYUT_SINIRI`, `MB`; `tests.sahte_http`.
- Produces: `metin_cikar(yol: Path, sure: float) -> tuple[str, str]`; `metin_dosyasi(kayit: dict, durum: str, metin: str) -> str`; `ekleri_esitle(proje_koku, veri, oturum, butce, cerezler=None, simdi=datetime.now, metin_cikarici=metin_cikar) -> dict[str, Any]` (özet anahtarları: `toplam`, `indirildi`, `bekliyor`, `erisilemedi`, `cok_buyuk`, `hata`, `baglanti`, `bu_tur_indirilen`, `bu_tur_bayt`, `bu_tur_metin`, `kalan_is`); sabitler `EK_YENIDEN_DENEME = timedelta(hours=24)`, `METIN_SURE_TAVANI = 180.0`, `METIN_DENEME_SINIRI = 3`. Görev 7 `ekleri_esitle`'yi çağırır.

- [ ] **Step 1: Başarısız testi yaz**

`tests/test_portal_ekleri_esitle.py`:

```python
"""One attachment sync run (plan 2026-09-28-portal-ekleri, Görev 6): idempotent,
retrying, budgeted, text extracted once into <id>.txt with a .meta.json sidecar.
Fake HTTP only (tests/sahte_http.py)."""
import json
from datetime import datetime, timedelta

from src.portal_ekleri import EkDeposu, METIN_ONEKI, ek_kimligi
from src.portal_ekleri_indir import MB, Butce, ekleri_esitle, metin_cikar
from tests.sahte_http import (DRIVE_URL, GIRIS_DUVARI, PDF, SP_DUVAR_URL, SP_URL, YOUTUBE,
                              SahteOturum, SahteYanit, aralikli, docx_bayt)

AN = datetime(2026, 9, 28, 10, 0, 0)
SP = "https://ornekokul-my.sharepoint.com/"


def _odev(ekler):
    return {"Ders Adı": "Sosyal Bilgiler", "Ödev Başlığı": "Kitap okuma ödevi",
            "Ödev Son Teslim Tarihi": "25.09.2026 12:00",
            "detail": {"description": "Sayfa 12-13", "attachments": ekler}}


VERI = {
    "odevlerim": {"homework": {"rows": [_odev([{"name": "Sayfa 12-13.pdf", "url": SP_URL},
                                               {"name": "Konu videosu", "url": YOUTUBE}])]}},
    "ek_sayfalar": {"mla_kaynakca": {"title": "MLA Kaynakça Hazırlama Rehberi", "empty": False,
                                     "documents": [DRIVE_URL]}},
}


def _rotalar():
    return {SP: lambda u, h: SahteYanit(200, PDF, {"Content-Type": "application/pdf"}),
            "https://drive.google.com/uc?": lambda u, h: SahteYanit(200, PDF, {"Content-Type": "application/octet-stream"})}


def _metin(yol, sure):
    return "var", "Soru 1: Bumerang kitabının 12. sayfasını oku."


def _butce(bayt=100 * MB):
    return Butce(float("inf"), bayt)


def _esitle(tmp_path, oturum, veri=VERI, an=AN, butce=None, cikarici=_metin):
    return ekleri_esitle(tmp_path, veri, oturum, butce or _butce(), simdi=lambda: an,
                         metin_cikarici=cikarici)


def test_ilk_tur_indirir_izleyici_tasarimin_alanlarini_tutar(tmp_path):
    oturum = SahteOturum(_rotalar())
    ozet = _esitle(tmp_path, oturum)
    depo = EkDeposu(tmp_path)
    ekler = depo.oku()
    sp = ekler[ek_kimligi(SP_URL)]
    for alan in ("url", "id", "name", "type", "size", "sha256", "source", "status", "reason", "fetched_at"):
        assert alan in sp, alan
    assert (sp["status"], sp["type"], sp["size"], sp["text"]) == ("indirildi", "sharepoint", len(PDF), "var")
    assert sp["source"] == {"section": "odevler",
                            "item": "Sosyal Bilgiler|Kitap okuma ödevi|25.09.2026 12:00",
                            "title": "Kitap okuma ödevi", "course": "Sosyal Bilgiler"}
    assert ekler[ek_kimligi(YOUTUBE)]["status"] == "baglanti"
    assert ekler[ek_kimligi(DRIVE_URL)]["source"]["section"] == "ek_sayfalar"
    metin = depo.metin_yolu(sp["id"]).read_text(encoding="utf-8")
    assert metin.startswith(f"{METIN_ONEKI}Sayfa 12-13.pdf · Kitap okuma ödevi · Sosyal Bilgiler\n\n")
    assert "Bumerang" in metin
    assert depo.meta(sp["id"]) == {"id": sp["id"], "name": "Sayfa 12-13.pdf", "title": "Kitap okuma ödevi",
                                   "section": "odevler", "course": "Sosyal Bilgiler"}
    assert (ozet["bu_tur_indirilen"], ozet["indirildi"], ozet["baglanti"], ozet["kalan_is"]) == (2, 2, 1, 0)
    assert all("youtube" not in i["url"] for i in oturum.istekler)


def test_ikinci_tur_hicbir_istek_yapmaz(tmp_path):
    oturum = SahteOturum(_rotalar())
    _esitle(tmp_path, oturum)
    n = len(oturum.istekler)
    ozet = _esitle(tmp_path, oturum, an=AN + timedelta(minutes=15))
    assert len(oturum.istekler) == n and ozet["bu_tur_indirilen"] == 0


def test_hata_sonraki_turda_yeniden_denenir(tmp_path):
    cevaplar = [SahteYanit(503, b""), SahteYanit(200, PDF, {"Content-Type": "application/pdf"})]
    oturum = SahteOturum({SP: lambda u, h: cevaplar.pop(0)})
    veri = {"odevlerim": {"homework": {"rows": [_odev([{"name": "a.pdf", "url": SP_URL}])]}}}
    _esitle(tmp_path, oturum, veri)
    assert EkDeposu(tmp_path).kayit(ek_kimligi(SP_URL))["status"] == "hata"
    _esitle(tmp_path, oturum, veri, an=AN + timedelta(minutes=15))
    kayit = EkDeposu(tmp_path).kayit(ek_kimligi(SP_URL))
    assert kayit["status"] == "indirildi" and kayit["attempts"] == 2


def test_erisilemeyen_24_saat_bekler(tmp_path):
    duvar = SahteYanit(200, GIRIS_DUVARI, {"Content-Type": "text/html"}, url="https://login.microsoftonline.com/x")
    oturum = SahteOturum({SP: lambda u, h: duvar})
    veri = {"odevlerim": {"homework": {"rows": [_odev([{"name": "b.pdf", "url": SP_DUVAR_URL}])]}}}
    _esitle(tmp_path, oturum, veri)
    kayit = EkDeposu(tmp_path).kayit(ek_kimligi(SP_DUVAR_URL))
    assert kayit["status"] == "erisilemedi" and "giriş istiyor" in kayit["reason"]
    assert kayit["next_attempt"] == (AN + timedelta(hours=24)).isoformat(timespec="seconds")
    _esitle(tmp_path, oturum, veri, an=AN + timedelta(hours=1))
    assert len(oturum.istekler) == 1
    _esitle(tmp_path, oturum, veri, an=AN + timedelta(hours=25))
    assert len(oturum.istekler) == 2


def test_butce_tukenince_kalan_sonraki_tura_kalir(tmp_path):
    govde = PDF + b"0" * (3 * MB)
    ikinci = SP_URL.replace("EaBcDe", "EkInCi")
    veri = {"odevlerim": {"homework": {"rows": [_odev([{"name": "a.pdf", "url": SP_URL},
                                                       {"name": "b.pdf", "url": ikinci}])]}}}
    oturum = SahteOturum({SP: aralikli(govde)})
    ozet = _esitle(tmp_path, oturum, veri, butce=_butce(4 * MB))
    durumlar = sorted(k["status"] for k in EkDeposu(tmp_path).oku().values())
    assert durumlar == ["bekliyor", "indirildi"] and ozet["kalan_is"] >= 1
    ozet = _esitle(tmp_path, oturum, veri, an=AN + timedelta(minutes=15))
    assert sorted(k["status"] for k in EkDeposu(tmp_path).oku().values()) == ["indirildi", "indirildi"]
    assert any(i["headers"].get("Range") for i in oturum.istekler)
    assert ozet["kalan_is"] == 0


def test_silinen_kopya_yeniden_indirilir(tmp_path):
    oturum = SahteOturum(_rotalar())
    _esitle(tmp_path, oturum)
    depo = EkDeposu(tmp_path)
    depo.dosya_yolu(depo.kayit(ek_kimligi(SP_URL))).unlink()
    n = len(oturum.istekler)
    _esitle(tmp_path, oturum, an=AN + timedelta(minutes=15))
    assert len(oturum.istekler) == n + 1
    assert depo.dosya_yolu(depo.kayit(ek_kimligi(SP_URL))) is not None


def test_metin_cikarma_hatasi_uc_denemede_durur(tmp_path):
    cagrilar = []

    def bozuk(yol, sure):
        cagrilar.append(yol.name)
        return "hata", ""
    veri = {"odevlerim": {"homework": {"rows": [_odev([{"name": "a.pdf", "url": SP_URL}])]}}}
    oturum = SahteOturum(_rotalar())
    for i in range(5):
        _esitle(tmp_path, oturum, veri, an=AN + timedelta(minutes=15 * i), cikarici=bozuk)
    assert len(cagrilar) == 3
    kayit = EkDeposu(tmp_path).kayit(ek_kimligi(SP_URL))
    assert kayit["text"] == "hata" and not EkDeposu(tmp_path).metin_yolu(kayit["id"]).exists()


def test_metin_katmani_yoksa_baslik_ve_not_yazilir(tmp_path):
    veri = {"odevlerim": {"homework": {"rows": [_odev([{"name": "tarama.pdf", "url": SP_URL}])]}}}
    _esitle(tmp_path, SahteOturum(_rotalar()), veri, cikarici=lambda y, s: ("yok", ""))
    depo = EkDeposu(tmp_path)
    metin = depo.metin_yolu(ek_kimligi(SP_URL)).read_text(encoding="utf-8")
    assert metin.startswith(METIN_ONEKI) and "Metin katmanı yok" in metin


def test_gercek_metin_cikarici(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSISTANT_ENABLE_OCR", "0")
    docx = tmp_path / "a.docx"
    docx.write_bytes(docx_bayt(["Bumerang kitabı", "Soru 1"]))
    assert metin_cikar(docx, 30) == ("var", "Bumerang kitabı\n\nSoru 1")
    ikili = tmp_path / "b.bin"
    ikili.write_bytes(b"xx")
    assert metin_cikar(ikili, 30) == ("desteklenmiyor", "")
    gorsel = tmp_path / "c.png"
    gorsel.write_bytes(bytes.fromhex("89504e470d0a1a0a") + b"0" * 32)
    assert metin_cikar(gorsel, 30) == ("yok", "")
```

- [ ] **Step 2: Kırmızı olduğunu gör**

Run: `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && DASHBOARD_SECRET_KEY=yerel-test-anahtari-portal-ekleri .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_portal_ekleri_esitle.py`
Expected: FAIL — `ImportError: cannot import name 'ekleri_esitle'`.

- [ ] **Step 3: Uygula**

`src/portal_ekleri_indir.py` içe aktarmalarına ekle (mevcut satırları genişlet):

```python
from collections import Counter
from datetime import datetime, timedelta
```

ve `from src.portal_ekleri import (...)` satırını şuna çevir:

```python
from src.json_utils import atomic_json_dump
from src.portal_ekleri import (DURUM_BAGLANTI, DURUM_BEKLIYOR, DURUM_COK_BUYUK, DURUM_ERISILEMEDI,
                               DURUM_HATA, DURUM_INDIRILDI, METIN_BEKLIYOR, METIN_DESTEKLENMIYOR,
                               METIN_HATA, METIN_ONEKI, METIN_VAR, METIN_YOK, PORTAL_HOST, EkDeposu,
                               ek_basligi, ekleri_topla, indirme_adresi, kanonik_adres)
```

Dosyanın sonuna:

```python
# ── One sync run ────────────────────────────────────────────────────────────
# A link that answered a login wall is tried again a day later: a teacher can
# open the share. A failed request (hata) is tried on the next run; a file
# over the cap, or a plain link, never.
EK_YENIDEN_DENEME = timedelta(hours=24)
METIN_SURE_TAVANI = 180.0
METIN_DENEME_SINIRI = 3
_METIN_UZANTILARI = frozenset({".pdf", ".docx", ".png", ".jpg", ".jpeg", ".gif", ".webp"})
_METIN_NOTU = {METIN_YOK: "(Metin katmanı yok: taranmış belge ya da görsel.)",
               METIN_DESTEKLENMIYOR: "(Bu ek türünün metni okunmuyor.)"}


@dataclass
class _CikarmaAyari:
    """The four settings FileAdapters reads, without building an
    AssistantConfig (which creates the index directory as a side effect)."""
    max_file_size_mb: int
    pdf_max_pages: int
    pdf_timeout: int
    enable_ocr: bool


def metin_cikar(yol: Path, sure: float) -> tuple[str, str]:
    """(text status, text) through the assistant's own FileAdapters:
    pdftotext for a PDF, stdlib zip/XML for a .docx, tesseract for an image
    only when ASSISTANT_ENABLE_OCR=1, as for every other image TEDY indexes.

    A PDF without a text layer is METIN_YOK — reported, never OCR'd here:
    rasterising and OCR'ing a scan costs seconds per page, and one 100-page
    book would outlast the whole 600 s cron run (plan 2026-09-28, decision 2).
    """
    from src.assistant_core import FileAdapters
    if yol.suffix.lower() not in _METIN_UZANTILARI:
        return METIN_DESTEKLENMIYOR, ""
    ayar = _CikarmaAyari(max_file_size_mb=EK_BOYUT_SINIRI // MB + 1, pdf_max_pages=400,
                         pdf_timeout=max(5, int(sure)),
                         enable_ocr=os.environ.get("ASSISTANT_ENABLE_OCR", "0") == "1")
    sonuc = FileAdapters(ayar).extract(yol, yol.name)
    if sonuc.get("extraction_error"):
        return METIN_HATA, ""
    if sonuc.get("source_kind") == "metadata":
        return METIN_YOK, ""
    return METIN_VAR, str(sonuc.get("text") or "")


def metin_dosyasi(kayit: dict[str, Any], durum: str, metin: str) -> str:
    """<id>.txt: a METIN_ONEKI header paragraph (so the index finds an
    attachment by its name), a note when there is no text, then the text."""
    kaynak = kayit.get("source") if isinstance(kayit.get("source"), dict) else {}
    parcalar = [ek_basligi(kayit)] + ([kaynak["course"]] if kaynak.get("course") else [])
    bas = METIN_ONEKI + " · ".join(parcalar)
    not_ = _METIN_NOTU.get(durum, "")
    govde = metin.strip()
    return "\n".join(x for x in (bas, not_) if x) + (f"\n\n{govde}" if govde else "") + "\n"


def _zaman(deger: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(str(deger)) if deger else None
    except ValueError:
        return None


def _indirilmeli(kayit: dict[str, Any], depo: EkDeposu, an: datetime) -> bool:
    durum = kayit.get("status")
    if durum in (DURUM_BEKLIYOR, DURUM_HATA):
        return True
    if durum == DURUM_INDIRILDI:
        return depo.dosya_yolu(kayit) is None          # the copy went missing
    if durum == DURUM_ERISILEMEDI:
        sonraki = _zaman(kayit.get("next_attempt"))
        return sonraki is None or an >= sonraki
    return False                                       # cok_buyuk, baglanti


def _metin_gerekli(kayit: dict[str, Any], depo: EkDeposu) -> bool:
    return (kayit.get("status") == DURUM_INDIRILDI
            and kayit.get("text") in (None, "", METIN_BEKLIYOR, METIN_HATA)
            and int(kayit.get("text_attempts") or 0) < METIN_DENEME_SINIRI
            and depo.dosya_yolu(kayit) is not None)


def _is_sirasi(ekler: dict[str, dict[str, Any]], depo: EkDeposu, an: datetime) -> list[dict[str, Any]]:
    """Part files first (finish what is started), then homework, newest first."""
    isler = [k for k in ekler.values() if _indirilmeli(k, depo, an) or _metin_gerekli(k, depo)]
    isler.sort(key=lambda k: str(k.get("first_seen") or ""), reverse=True)
    isler.sort(key=lambda k: (0 if int(k.get("partial_bytes") or 0) > 0 else 1,
                              0 if (k.get("source") or {}).get("section") == "odevler" else 1))
    return isler


def _sonucu_yaz(kayit: dict[str, Any], sonuc: Sonuc, an: datetime) -> None:
    zaman = an.isoformat(timespec="seconds")
    kayit["attempts"] = int(kayit.get("attempts") or 0) + 1
    kayit.update(status=sonuc.durum, reason=sonuc.neden, last_attempt=zaman, partial_bytes=sonuc.parca_bayt)
    if sonuc.durum == DURUM_INDIRILDI:
        kayit.update(file=sonuc.dosya, ext=sonuc.uzanti, mime=sonuc.mime, size=sonuc.boyut,
                     sha256=sonuc.sha256, fetched_at=zaman, text=METIN_BEKLIYOR, text_attempts=0,
                     next_attempt=None, partial_bytes=0)
        return
    kayit["file"] = None
    kayit["next_attempt"] = ((an + EK_YENIDEN_DENEME).isoformat(timespec="seconds")
                             if sonuc.durum == DURUM_ERISILEMEDI else None)


def _atomik_yaz(yol: Path, metin: str) -> None:
    gecici = yol.with_name(yol.name + ".tmp")
    gecici.write_text(metin, encoding="utf-8")
    os.replace(gecici, yol)


def _metni_hazirla(depo: EkDeposu, kayit: dict[str, Any], sure: float,
                   cikarici: Callable[[Path, float], tuple[str, str]]) -> None:
    yol = depo.dosya_yolu(kayit)
    kayit["text_attempts"] = int(kayit.get("text_attempts") or 0) + 1
    durum, metin = cikarici(yol, sure)
    kayit.update(text=durum, text_chars=len(metin))
    kaynak = kayit.get("source") if isinstance(kayit.get("source"), dict) else {}
    atomic_json_dump({"id": kayit["id"], "name": kayit.get("name", ""), "title": kaynak.get("title", ""),
                      "section": kaynak.get("section", ""), "course": kaynak.get("course", "")},
                     str(depo.meta_yolu(kayit["id"])))
    if durum != METIN_HATA:
        _atomik_yaz(depo.metin_yolu(kayit["id"]), metin_dosyasi(kayit, durum, metin))


def ekleri_esitle(proje_koku: str | Path, veri: Any, oturum: Any, butce: Butce, cerezler: Any = None,
                  simdi: Callable[[], datetime] = datetime.now,
                  metin_cikarici: Callable[[Path, float], tuple[str, str]] = metin_cikar) -> dict[str, Any]:
    """One run: collect every link in `veri`, merge into the tracker, then
    download and extract text in priority order until the budget runs out.
    The tracker is written after every file, so a run killed mid-way keeps
    what it finished. Idempotent: a second run over the same data with the
    copies in place makes no request."""
    depo = EkDeposu(proje_koku)
    an = simdi()
    zaman = an.isoformat(timespec="seconds")
    ekler = depo.oku()
    for aday in ekleri_topla(veri):
        kayit = ekler.setdefault(aday.kimlik, {"id": aday.kimlik, "status": DURUM_BEKLIYOR, "reason": "",
                                               "attempts": 0, "first_seen": zaman, "text": ""})
        kayit.update(url=aday.url, canonical=kanonik_adres(aday.url), type=aday.tur, name=aday.ad,
                     source=aday.kaynaklar[0], sources=aday.kaynaklar, last_seen=zaman)
        if aday.tur == "baglanti":
            kayit.update(status=DURUM_BAGLANTI, reason="dosya değil, bir bağlantı")
    depo.dizin.mkdir(parents=True, exist_ok=True)
    depo.yaz(ekler)

    bu_tur = {"indirilen": 0, "bayt": 0, "metin": 0}
    for kayit in _is_sirasi(ekler, depo, an):
        if butce.bitti():
            break
        if _indirilmeli(kayit, depo, an):
            sonuc = ek_indir(oturum, kayit, depo.dizin, butce, cerezler)
            _sonucu_yaz(kayit, sonuc, an)
            depo.yaz(ekler)
            if sonuc.durum == DURUM_INDIRILDI:
                bu_tur["indirilen"] += 1
                bu_tur["bayt"] += sonuc.boyut
        if _metin_gerekli(kayit, depo) and not butce.bitti():
            _metni_hazirla(depo, kayit, min(METIN_SURE_TAVANI, butce.kalan_sure()), metin_cikarici)
            depo.yaz(ekler)
            bu_tur["metin"] += 1

    sayim = Counter(str(k.get("status")) for k in ekler.values())
    return {"toplam": len(ekler),
            **{d: sayim.get(d, 0) for d in (DURUM_INDIRILDI, DURUM_BEKLIYOR, DURUM_ERISILEMEDI,
                                            DURUM_COK_BUYUK, DURUM_HATA, DURUM_BAGLANTI)},
            "bu_tur_indirilen": bu_tur["indirilen"], "bu_tur_bayt": bu_tur["bayt"],
            "bu_tur_metin": bu_tur["metin"],
            "kalan_is": sum(1 for k in ekler.values()
                            if (_indirilmeli(k, depo, an) and k.get("status") != DURUM_ERISILEMEDI)
                            or _metin_gerekli(k, depo))}
```

- [ ] **Step 4: Yeşil olduğunu gör**

Run: `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && DASHBOARD_SECRET_KEY=yerel-test-anahtari-portal-ekleri unshare -rn .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_portal_ekleri_esitle.py tests/test_portal_ekleri_indir.py tests/test_portal_ekleri.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && test "$(git branch --show-current)" = feat/portal-ekleri && echo dal-dogru
git add src/portal_ekleri_indir.py tests/test_portal_ekleri_esitle.py
git commit -m "$(cat <<'EOF'
Portal ekleri eşitleme turu: yeniden deneme, bütçe, metin yan dosyası

İzleyici her dosyadan sonra yazılır; hata sonraki tur, erişilemedi 24 saat
sonra denenir; metin indirme anında bir kez <id>.txt'ye çıkarılır, yan meta
<id>.meta.json'a yazılır. Taranmış PDF'e OCR yapılmaz, "metin yok" olur.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Görev 7: `run_sync` bağlantısı ve elle CLI

**Files:**
- Modify: `src/run_sync.py` (sabitler + iki yardımcı; `main()` içinde `prev_data = {}` yanında `portal_cerezleri`, kazıyıcı döngüsünden sonra çerez yakalama, "# 5. SEBİT" bloğundan sonra ek adımı, `health`'e `"ekler"`)
- Modify: `src/portal_ekleri_indir.py` (sona CLI `main`)
- Modify: `tests/conftest.py` (sona autouse bekçi: `main()`'i süren hiçbir test gerçek ek indirmez)
- Test: `tests/test_portal_ekleri_sync.py`

**Interfaces:**
- Consumes: Görev 5 `Butce`, `portal_cerez_kavanozu`, `MB`; Görev 6 `ekleri_esitle`; `src.session_manager.load_cookies() -> list[dict] | None`.
- Produces: `run_sync.SYNC_SURE_SINIRI = 600`, `EK_YEDEK_SURE = 150`, `EK_SURE_BUTCESI` (env `TEDY_EK_SURE_BUTCESI`, varsayılan 180), `EK_BAYT_BUTCESI` (env `TEDY_EK_BAYT_BUTCESI_MB`, varsayılan 250 MB), `EK_EN_AZ_SURE = 15`; `_ek_butcesi(start_time: float, simdi: float | None = None) -> float`; `_ekleri_esitle_adimi(start_time: float, portal_cerezleri: list[dict], simdi: float | None = None) -> dict`. `portal_ekleri_indir.main(argv: list[str] | None = None, kok: Path | None = None) -> int`. Sağlık dosyasına `ekler` (özet ya da `{"atlandi": "sure_yok"}` ya da `{"hata": "..."}`).

- [ ] **Step 1: Başarısız testi yaz**

`tests/test_portal_ekleri_sync.py`:

```python
"""Attachments inside the sync (plan 2026-09-28-portal-ekleri, Görev 7): after the
scrapers, before health and reindex, in an explicit budget, under the lock."""
import fcntl
import inspect
import json
import time

import pytest

import src.portal_ekleri_indir as indir
import src.run_sync as run_sync


def test_butce_hesabi():
    bas = 1000.0
    assert run_sync._ek_butcesi(bas, simdi=bas + 100) == run_sync.EK_SURE_BUTCESI
    assert run_sync._ek_butcesi(bas, simdi=bas + 400) == pytest.approx(50.0)
    assert run_sync._ek_butcesi(bas, simdi=bas + 440) == pytest.approx(10.0)
    assert (run_sync.SYNC_SURE_SINIRI, run_sync.EK_YEDEK_SURE) == (600, 150)


@pytest.fixture
def kok(tmp_path, monkeypatch):
    (tmp_path / "output").mkdir()
    (tmp_path / "output" / "scraped_data.json").write_text(json.dumps({"odevlerim": {}}), encoding="utf-8")
    monkeypatch.setattr(run_sync, "PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(run_sync, "OUTPUT_DIR", str(tmp_path / "output"))
    return tmp_path


def test_sure_yoksa_adim_atlanir(kok, monkeypatch):
    def cagrilmamali(*a, **k):
        raise AssertionError("çağrılmamalıydı")
    monkeypatch.setattr(indir, "ekleri_esitle", cagrilmamali)
    bas = time.time()
    assert run_sync._ekleri_esitle_adimi(bas, [], simdi=bas + 445) == {"atlandi": "sure_yok"}


def test_adim_butce_ve_kapsamli_cerezle_calisir(kok, monkeypatch):
    alinan = {}

    def sahte(proje_koku, veri, oturum, butce, cerezler=None, **kw):
        alinan.update(kok=proje_koku, veri=veri, butce=butce, cerezler=cerezler)
        return {"toplam": 0, "bu_tur_indirilen": 0, "bu_tur_bayt": 0, "kalan_is": 0}
    monkeypatch.setattr(indir, "ekleri_esitle", sahte)
    bas = time.time()
    ozet = run_sync._ekleri_esitle_adimi(bas, [
        {"name": "ASP.NET_SessionId", "value": "x", "domain": "portal.tedronesans.k12.tr"},
        {"name": "izci", "value": "y", "domain": ".google.com"}], simdi=bas + 300)
    assert ozet["toplam"] == 0
    assert str(alinan["kok"]) == str(kok) and alinan["veri"] == {"odevlerim": {}}
    kalan = alinan["butce"].son_an - time.monotonic()
    assert 140 <= kalan <= 150                      # 600 - 150 - 300
    assert alinan["butce"].bayt == run_sync.EK_BAYT_BUTCESI
    assert [c.name for c in alinan["cerezler"]] == ["ASP.NET_SessionId"]


def test_adim_hatasi_senkronu_dusurmez(kok, monkeypatch):
    def patlak(*a, **k):
        raise OSError("disk dolu")
    monkeypatch.setattr(indir, "ekleri_esitle", patlak)
    bas = time.time()
    assert run_sync._ekleri_esitle_adimi(bas, [], simdi=bas) == {"hata": "disk dolu"}


def test_main_ekleri_saglik_ve_indekslemeden_once_calistirir():
    kaynak = inspect.getsource(run_sync.main)
    adim = kaynak.index("_ekleri_esitle_adimi(")
    # rindex: the failed-login branch writes its own, earlier health file.
    assert kaynak.index("scrape_sebit_hw()") < adim < kaynak.rindex("atomic_json_dump(health")
    assert adim < kaynak.index("perform_incremental_reindex(")
    assert '"ekler": ekler_ozeti' in kaynak
    assert "driver.get_cookies()" in kaynak


def test_cli_kilit_tutuluyken_calismaz(tmp_path, monkeypatch):
    (tmp_path / "output").mkdir()
    (tmp_path / "output" / "scraped_data.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(indir, "ekleri_esitle", lambda *a, **k: {"toplam": 0})
    with open(tmp_path / "output" / ".sync.lock", "w") as kilit:
        fcntl.flock(kilit, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert indir.main(["--sure", "5"], kok=tmp_path) == 1
    assert indir.main(["--sure", "5"], kok=tmp_path) == 0
```

- [ ] **Step 2: Kırmızı olduğunu gör**

Run: `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && DASHBOARD_SECRET_KEY=yerel-test-anahtari-portal-ekleri .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_portal_ekleri_sync.py`
Expected: FAIL — `AttributeError: module 'src.run_sync' has no attribute '_ek_butcesi'`.

- [ ] **Step 3: run_sync**

`src/run_sync.py`'de `SYNC_LOCK_PATH` tanımının altına:

```python
# ── Portal attachments inside the run ───────────────────────────────────────
# Cron runs this file under `timeout 600`. Measured over the last 40 runs on
# 2026-09-28: p50 244 s, longest 393 s. Attachments get what is left after a
# 150 s reserve for health and the incremental reindex, capped at 180 s and
# 250 MB per run; under 15 s they wait for the next run. A file that does not
# finish keeps its part file and resumes (src/portal_ekleri_indir.py).
SYNC_SURE_SINIRI = 600
EK_YEDEK_SURE = 150
EK_SURE_BUTCESI = int(os.environ.get("TEDY_EK_SURE_BUTCESI", "180"))
EK_BAYT_BUTCESI = int(os.environ.get("TEDY_EK_BAYT_BUTCESI_MB", "250")) * 1024 * 1024
EK_EN_AZ_SURE = 15


def _ek_butcesi(start_time, simdi=None):
    """Seconds the attachments may take this run; below EK_EN_AZ_SURE, none."""
    simdi = time.time() if simdi is None else simdi
    return min(EK_SURE_BUTCESI, start_time + SYNC_SURE_SINIRI - EK_YEDEK_SURE - simdi)


def _ekleri_esitle_adimi(start_time, portal_cerezleri, simdi=None):
    """Download and extract portal attachments, best effort. Never raises:
    an attachment problem must not cost the run its health file or its
    reindex. Runs inside main(), so under the same sync lock."""
    sure = _ek_butcesi(start_time, simdi)
    if sure < EK_EN_AZ_SURE:
        print(f"[EKLER] Süre kalmadı ({max(sure, 0):.0f} s); ekler sonraki eşitlemede.")
        return {"atlandi": "sure_yok"}
    try:
        import requests
        from src import portal_ekleri_indir as indir
        with open(os.path.join(OUTPUT_DIR, "scraped_data.json"), encoding="utf-8") as f:
            veri = json.load(f)
        butce = indir.Butce(time.monotonic() + sure, EK_BAYT_BUTCESI)
        ozet = indir.ekleri_esitle(PROJECT_ROOT, veri, requests.Session(), butce,
                                   cerezler=indir.portal_cerez_kavanozu(portal_cerezleri))
        print(f"[EKLER] indirilen={ozet.get('bu_tur_indirilen', 0)}"
              f" bayt={ozet.get('bu_tur_bayt', 0)} metin={ozet.get('bu_tur_metin', 0)}"
              f" kalan_iş={ozet.get('kalan_is', 0)} toplam={ozet.get('toplam', 0)}"
              f" (bütçe {sure:.0f} s)")
        return ozet
    except Exception as e:
        print(f"[WARN] Portal ekleri: {_kisa_hata(e)}")
        return {"hata": _kisa_hata(e)}
```

`main()` içinde, `prev_data = {}` satırının (ilk olan, `validation = …` yanındaki) altına:

```python
    portal_cerezleri = []
```

Kazıyıcı döngüsünden (`for name, fn in scrapers:` bloğu) hemen sonra, `_icerik_birlestir(data, onceki)`'den önce:

```python
        # The portal session, for an attachment the portal serves itself;
        # src/portal_ekleri_indir.py scopes it to the portal's own domain.
        try:
            portal_cerezleri = driver.get_cookies() or []
        except Exception:
            portal_cerezleri = []
```

"# 5. SEBİT homework scrape" bloğunun (`print(f"[WARN] SEBİT homework scrape failed: {e}")` satırı dahil) hemen altına:

```python

    # 5b. Portal attachments — after every scraper, before health and the
    # reindex (so a new attachment's text is indexed this run), in a budget.
    ekler_ozeti = _ekleri_esitle_adimi(start_time, portal_cerezleri)
```

`health` sözlüğünde `"okunamadi": okunamadi,` satırının altına:

```python
        "ekler": ekler_ozeti,
```

- [ ] **Step 4: CLI**

`src/portal_ekleri_indir.py` sonuna:

```python
def main(argv: list[str] | None = None, kok: Path | None = None) -> int:
    """By hand: `flock`-free, it takes output/.sync.lock itself and refuses
    while a sync runs. Uses the cached portal cookies (output/portal_cookies.json).

        .venv/bin/python -m src.portal_ekleri_indir --sure 300 --bayt-mb 250 --indeksle
    """
    import argparse
    import fcntl
    import json as _json
    from src.session_manager import load_cookies

    ap = argparse.ArgumentParser(description="Portal eklerini indir (senkron kilidiyle).")
    ap.add_argument("--sure", type=int, default=300, help="süre bütçesi, saniye")
    ap.add_argument("--bayt-mb", type=int, default=250, help="bayt bütçesi, MB")
    ap.add_argument("--indeksle", action="store_true", help="bitince asistan indeksini artımlı yenile")
    arg = ap.parse_args(argv)
    kok = Path(kok) if kok is not None else Path(__file__).resolve().parents[1]
    kilit_yolu = kok / "output" / ".sync.lock"
    kilit_yolu.parent.mkdir(parents=True, exist_ok=True)
    with open(kilit_yolu, "a") as kilit:
        try:
            fcntl.flock(kilit, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            print("Başka bir senkron koşuyor; ekler şimdi indirilmedi.")
            return 1
        veri = _json.loads((kok / "output" / "scraped_data.json").read_text(encoding="utf-8"))
        butce = Butce(time.monotonic() + arg.sure, arg.bayt_mb * MB)
        ozet = ekleri_esitle(kok, veri, requests.Session(), butce,
                             cerezler=portal_cerez_kavanozu(load_cookies() or []))
        print(_json.dumps(ozet, ensure_ascii=False))
        if arg.indeksle:
            from src.assistant_core import perform_incremental_reindex
            meta = perform_incremental_reindex(kok)
            print(_json.dumps({k: meta.get(k) for k in ("files_indexed", "chunks_indexed",
                                                         "changed_files", "dusen_dosyalar")},
                              ensure_ascii=False))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
```

- [ ] **Step 5: Test bekçisi**

`tests/test_year_rollover_sync.py` ve benzerleri `run_sync.main()`'i baştan sona sürer; artık o yol ek adımından geçer ve (dağıtımdan sonra ana checkout'ta koşulursa) gerçek `output/scraped_data.json`'daki SharePoint/Drive bağlantılarına istek atıp gerçek `content/portal-ekleri`'ye yazabilirdi. `tests/conftest.py` sonuna ekle:

```python
@pytest.fixture(autouse=True)
def _canli_ek_indirmesi_yok(monkeypatch):
    """run_sync.main() downloads portal attachments since 2026-09-28 (plan
    portal-ekleri, Görev 7). A test that drives main() must never reach
    SharePoint or Drive, nor write content/portal-ekleri: the step's network
    entry point refuses here, and _ekleri_esitle_adimi turns that into
    {"hata": …} as it does any failure. Tests of the step patch it again on
    purpose; tests of ekleri_esitle import the function by name at
    collection, which this does not touch."""
    import src.portal_ekleri_indir as indir

    def _yasak(*a, **k):
        raise RuntimeError("testte gerçek ek indirmesi yok")
    monkeypatch.setattr(indir, "ekleri_esitle", _yasak)
```

- [ ] **Step 6: Yeşil olduğunu gör**

Run: `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && DASHBOARD_SECRET_KEY=yerel-test-anahtari-portal-ekleri unshare -rn .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_portal_ekleri_sync.py tests/test_portal_ekleri_esitle.py tests/test_portal_ekleri_indir.py tests/test_sync_kilidi.py tests/test_year_rollover_sync.py tests/test_okunamadi_koruma.py tests/test_giris_yeniden_deneme.py tests/test_hafta_kapsami.py`
Expected: PASS, ağsız ad alanında.

- [ ] **Step 7: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && test "$(git branch --show-current)" = feat/portal-ekleri && echo dal-dogru
git add src/run_sync.py src/portal_ekleri_indir.py tests/conftest.py tests/test_portal_ekleri_sync.py
git commit -m "$(cat <<'EOF'
Portal eklerini senkron içinde bütçeyle indir; elle CLI

Kazıyıcılardan sonra, sağlık ve yeniden indekslemeden önce, senkron
kilidi altında: süre min(180 s, başlangıç+600-150-şimdi), 250 MB/tur;
15 s altında atlanır. Sağlık dosyası "ekler" özetini taşır. CLI kilidi
kendisi alır.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Görev 8: `/api/ekler/<id>` ve yüklerde `tedyUrl` / `status`

**Files:**
- Modify: `src/dashboard_api.py:20` (`send_file`), sabitler + yardımcılar (`_load_json`'ın üstüne), `_combined_homework_rows`, `portal_pages`, `_duyuru_satiri` + `announcements`, yeni rota (`/api/exams`'ın üstüne)
- Test: `tests/test_portal_ekleri_api.py`

**Interfaces:**
- Consumes: Görev 3 `EkDeposu`, `ek_ozeti`, `sayfa_belgesi_adi`, `duyuru_eki_adi`, `KIMLIK_DESENI`, `DURUM_INDIRILDI`, `ek_kimligi`; Görev 2 `_duyuru_satiri`, `temiz_metin`.
- Produces: `dashboard_api.EK_PROJE_KOKU`, `EK_YOK`, `EK_BILINMEYEN_MIME`, `_ek_deposu()`, `_ek_kayitlari() -> dict`, `_ek_dosya_adi(kayit) -> str`, rota `portal_eki(ek_id)` (`GET /api/ekler/<ek_id>`), `_odev_ekleri(detay, ekler) -> list[dict]`, `_duyuru_satiri(satir, ekler) -> Any`. Yük biçimleri: ödev `detail.attachments[] = {name, url, id, tedyUrl, status[, reason]}`; sayfa `pages[k].attachments[]` aynı biçim; duyuru satırı `ekler[]` aynı biçim. `_canli_odevler()` satırları da bu ekleri taşır (Görev 10 kullanır).

- [ ] **Step 1: Başarısız testi yaz**

`tests/test_portal_ekleri_api.py`:

```python
"""Serving portal attachments (plan 2026-09-28-portal-ekleri, Görev 8): the file,
with Range, for the full role only; and tedyUrl/status in every payload."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["TEST_AUTH_BYPASS"] = "1"

from src.portal_ekleri import EkDeposu, ek_kimligi  # noqa: E402
from tests.sahte_http import DRIVE_URL, PDF, SP_DUVAR_URL, SP_URL, YOUTUBE  # noqa: E402

KIMLIK = ek_kimligi(SP_URL)
DUVAR = ek_kimligi(SP_DUVAR_URL)
DRIVE = ek_kimligi(DRIVE_URL)

VERI = {
    "odevlerim": {"summary": "", "homework": {"headers": [], "rows": [{
        "Ders Adı": "Sosyal Bilgiler", "Ödev Başlığı": "Kitap okuma ödevi",
        "Ödev Son Teslim Tarihi": "30.09.2026 12:00", "Ödev Durumu": "Değerlendirilmemiş",
        "detail": {"description": "Sayfa 12-13", "attachments": [
            {"name": "Sayfa 12-13.pdf", "url": SP_URL},
            {"name": "Kitap sayfaları", "url": SP_DUVAR_URL},
            {"name": "Konu videosu", "url": YOUTUBE}]}}]}},
    "ek_sayfalar": {"mla_kaynakca": {"title": "MLA Kaynakça Hazırlama Rehberi", "empty": False,
                                     "text": "Rehber", "documents": [DRIVE_URL]}},
    "duyurular": {"announcements": [{"e-Posta Başlık": "Gezi izni", "Yayın Tarihi": "22.09.2026",
                                     "Ekleri": "izin-formu.pdf", "Ekleri_url": SP_URL}]},
}


@pytest.fixture
def api(tmp_path, monkeypatch):
    import src.dashboard_api as api
    depo = EkDeposu(tmp_path)
    depo.dizin.mkdir(parents=True)
    (depo.dizin / f"{KIMLIK}.pdf").write_bytes(PDF)
    (depo.dizin / f"{DRIVE}.bin").write_bytes(b"bilinmeyen")
    depo.yaz({
        KIMLIK: {"id": KIMLIK, "status": "indirildi", "file": f"{KIMLIK}.pdf", "ext": ".pdf",
                 "mime": "application/pdf", "name": "Sayfa 12-13.pdf"},
        DUVAR: {"id": DUVAR, "status": "erisilemedi", "reason": "kaynak giriş istiyor; paylaşım herkese açık değil"},
        DRIVE: {"id": DRIVE, "status": "indirildi", "file": f"{DRIVE}.bin", "ext": ".bin",
                "mime": "application/octet-stream", "name": "MLA Kaynakça Hazırlama Rehberi"},
    })
    monkeypatch.setattr(api, "EK_PROJE_KOKU", str(tmp_path))
    monkeypatch.setattr(api, "OUTPUT_DIR", str(tmp_path / "output"))
    monkeypatch.setattr(api, "_scraped", lambda: json.loads(json.dumps(VERI)))
    monkeypatch.setattr(api, "_load_photo_homework_rows", lambda: [])
    api.app.config["TESTING"] = True
    return api


def test_dosyayi_satir_ici_ve_dogru_turle_sunar(api):
    with api.app.test_client() as c:
        cevap = c.get(f"/api/ekler/{KIMLIK}")
    assert cevap.status_code == 200 and cevap.data == PDF
    assert cevap.mimetype == "application/pdf"
    assert cevap.headers["Content-Disposition"].startswith("inline")
    assert "Sayfa" in cevap.headers["Content-Disposition"]
    assert cevap.headers["X-Content-Type-Options"] == "nosniff"
    assert cevap.headers["Cache-Control"] == "private, max-age=3600"


def test_range_ile_parca_sunar(api):
    with api.app.test_client() as c:
        cevap = c.get(f"/api/ekler/{KIMLIK}", headers={"Range": "bytes=0-3"})
    assert cevap.status_code == 206 and cevap.data == b"%PDF"
    assert cevap.headers["Content-Range"] == f"bytes 0-3/{len(PDF)}"


def test_bilinmeyen_tur_indirme_olarak_sunulur(api):
    with api.app.test_client() as c:
        cevap = c.get(f"/api/ekler/{DRIVE}")
    assert cevap.status_code == 200
    assert cevap.headers["Content-Disposition"].startswith("attachment")


@pytest.mark.parametrize("ek_id", [DUVAR, "0123456789abcdef", "ABCDEF0123456789"])
def test_olmayan_ya_da_indirilmemis_ek_404(api, ek_id):
    with api.app.test_client() as c:
        cevap = c.get(f"/api/ekler/{ek_id}")
    assert cevap.status_code == 404 and cevap.get_json()["error"] == api.EK_YOK


def test_okur_reddedilir_full_rol_alir(api, monkeypatch):
    monkeypatch.setattr(api, "TEST_AUTH_BYPASS", False)
    okur = next(e for e, r in api.USER_ROLES.items() if r == api.ROLE_READER)
    tam = next(e for e, r in api.USER_ROLES.items() if r == api.ROLE_FULL)
    with api.app.test_client() as c:
        assert c.get(f"/api/ekler/{KIMLIK}").status_code == 401
        with c.session_transaction() as s:
            s["user_email"] = okur
        assert c.get(f"/api/ekler/{KIMLIK}").status_code == 403
        with c.session_transaction() as s:
            s["user_email"] = tam
        assert c.get(f"/api/ekler/{KIMLIK}").status_code == 200
    assert "portal_eki" not in api.READER_ENDPOINTS


def test_odev_yuku_ek_durumunu_tasir(api):
    with api.app.test_client() as c:
        ekler = c.get("/api/homework").get_json()["homework"][0]["detail"]["attachments"]
    assert ekler[0] == {"name": "Sayfa 12-13.pdf", "url": SP_URL, "id": KIMLIK,
                        "tedyUrl": f"/api/ekler/{KIMLIK}", "status": "indirildi"}
    assert ekler[1]["tedyUrl"] is None and ekler[1]["status"] == "erisilemedi"
    assert "giriş istiyor" in ekler[1]["reason"]
    assert ekler[2]["status"] == "baglanti" and ekler[2]["id"] is None


def test_sayfa_ve_duyuru_yukleri(api):
    with api.app.test_client() as c:
        sayfa = c.get("/api/pages").get_json()["pages"]["mla_kaynakca"]
        duyuru = c.get("/api/announcements").get_json()["announcements"][0]
    assert sayfa["documents"] == [DRIVE_URL]                      # unchanged for old readers
    assert sayfa["attachments"][0]["tedyUrl"] == f"/api/ekler/{DRIVE}"
    assert sayfa["attachments"][0]["name"] == "MLA Kaynakça Hazırlama Rehberi"
    assert duyuru["Ekleri_url"] == SP_URL
    assert duyuru["ekler"] == [{"name": "izin-formu.pdf", "url": SP_URL, "id": KIMLIK,
                                "tedyUrl": f"/api/ekler/{KIMLIK}", "status": "indirildi"}]


def test_asistanin_odev_kaynagi_da_ek_kimligini_tasir(api):
    ekler = api._canli_odevler()[0]["detail"]["attachments"]
    assert [e["id"] for e in ekler] == [KIMLIK, DUVAR, None]


def test_izleyici_bozuksa_yuk_bozulmaz(api, tmp_path):
    EkDeposu(tmp_path).izleyici_yolu.write_text("{bozuk", encoding="utf-8")
    with api.app.test_client() as c:
        ekler = c.get("/api/homework").get_json()["homework"][0]["detail"]["attachments"]
    assert ekler[0]["status"] == "bekliyor" and ekler[0]["tedyUrl"] is None
```

- [ ] **Step 2: Kırmızı olduğunu gör**

Run: `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && DASHBOARD_SECRET_KEY=yerel-test-anahtari-portal-ekleri .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_portal_ekleri_api.py`
Expected: FAIL — `AttributeError: … has no attribute 'EK_PROJE_KOKU'`.

- [ ] **Step 3: Uygula**

`src/dashboard_api.py` 20. satır:

```python
from flask import Flask, Response, jsonify, request, send_file, send_from_directory, session
```

`# --- Data helpers ---` satırının üstüne:

```python
# --- Portal attachments (plan docs/superpowers/plans/2026-09-28-portal-ekleri.md) ---
# TEDY's own copies under content/portal-ekleri, tracked in
# output/portal_ekleri.json by src/portal_ekleri_indir.py inside run_sync.
EK_PROJE_KOKU = PROJECT_ROOT
EK_YOK = "Bu ek TEDY'de yok; kaynağında açabilirsiniz."
# Everything recognised is served inline (a PDF or an image opens in the
# browser's viewer; an Office file downloads anyway). Unknown bytes (.bin)
# are forced to download so nothing of unknown type ever renders here.
EK_BILINMEYEN_MIME = "application/octet-stream"
_EK_YASAK_KARAKTER = re.compile("[" + re.escape('\\/:*?"<>|' + "".join(map(chr, range(32)))) + "]+")


def _ek_deposu():
    from src.portal_ekleri import EkDeposu
    return EkDeposu(EK_PROJE_KOKU)


def _ek_kayitlari():
    """The tracker's records; an unreadable tracker means "not downloaded yet",
    never a 500 on /api/homework."""
    try:
        return _ek_deposu().oku()
    except Exception as exc:  # noqa: BLE001
        app.logger.error("portal ekleri izleyicisi okunamadı: %s", type(exc).__name__)
        return {}


def _ek_dosya_adi(kayit):
    ad = _EK_YASAK_KARAKTER.sub(" ", str(kayit.get("name") or "")).strip()[:120] or str(kayit["id"])
    uzanti = str(kayit.get("ext") or "")
    return ad if ad.lower().endswith(uzanti.lower()) else ad + uzanti


def _odev_ekleri(detay, ekler):
    from src.portal_ekleri import ek_ozeti
    return [ek_ozeti(ekler, a.get("url"), a.get("name"))
            for a in detay.get("attachments") or [] if isinstance(a, dict) and a.get("url")]
```

`_combined_homework_rows` (tam hâli):

```python
def _combined_homework_rows(scraped_data):
    """Merge scraped and photo-extracted homework rows. Each attachment
    carries its TEDY copy (tedyUrl) and status (plan 2026-09-28 portal-ekleri);
    the description is cleaned of portal chrome (src/portal_susu.py)."""
    scraped_rows = (
        scraped_data.get("odevlerim", {})
        .get("homework", {})
        .get("rows", [])
    )
    ekler = _ek_kayitlari()
    rows = []
    for row in [*(scraped_rows or []), *_load_photo_homework_rows()]:
        if not isinstance(row, dict):
            continue
        r = dict(row)
        if "Ders Adı" in r:
            r["normalized_course"] = normalize_course(r["Ders Adı"])
        detay = r.get("detail")
        if isinstance(detay, dict):
            r["detail"] = {**detay, "description": temiz_metin(detay.get("description")),
                           "attachments": _odev_ekleri(detay, ekler)}
        rows.append(r)
    return _dedupe_homework_rows(rows)
```

`portal_pages` içindeki `dolu` hesabı:

```python
    from src.portal_ekleri import ek_ozeti, sayfa_belgesi_adi
    ekler = _ek_kayitlari()
    dolu = {}
    for k, v in sayfalar.items():
        if not isinstance(v, dict) or v.get("empty"):
            continue
        belgeler = [b for b in v.get("documents") or [] if isinstance(b, str)]
        baslik = str(v.get("title") or k)
        dolu[k] = {**v, "text": temiz_metin(v.get("text")),
                   "attachments": [ek_ozeti(ekler, u, sayfa_belgesi_adi(baslik, i, len(belgeler)))
                                   for i, u in enumerate(belgeler, 1)]}
```

`_duyuru_satiri` ve `announcements` (tam hâli):

```python
def _duyuru_satiri(satir, ekler):
    """An announcement row: text fields cleaned, links untouched, and each
    `<column>_url` as an attachment with its TEDY copy and status."""
    from src.portal_ekleri import duyuru_eki_adi, ek_ozeti
    if not isinstance(satir, dict):
        return satir
    temiz = {k: (temiz_metin(v) if isinstance(v, str) and not k.endswith("_url") else v)
             for k, v in satir.items()}
    temiz["ekler"] = [ek_ozeti(ekler, v, duyuru_eki_adi(satir, k)) for k, v in satir.items()
                      if k.endswith("_url") and isinstance(v, str) and v.strip()]
    return temiz


@app.route("/api/announcements")
@require_auth
def announcements():
    data = _scraped()
    ann = data.get("duyurular", {}).get("announcements", [])
    ekler = _ek_kayitlari()
    return jsonify({"announcements": [_duyuru_satiri(a, ekler) for a in ann]})
```

`@app.route("/api/exams")`'ın üstüne yeni rota:

```python
@app.route("/api/ekler/<ek_id>")
@require_auth
def portal_eki(ek_id):
    """One downloaded portal attachment, streamed from TEDY's copy.

    Full role (and the API keys every data route accepts); a reader is
    refused by require_auth's default-deny list. send_file(conditional=True)
    answers Range with 206, which a PDF viewer uses to open a 100 MB book
    without fetching all of it first."""
    from src.portal_ekleri import DURUM_INDIRILDI, KIMLIK_DESENI
    if not KIMLIK_DESENI.match(ek_id):
        return jsonify({"error": EK_YOK}), 404
    depo = _ek_deposu()
    kayit = depo.kayit(ek_id)
    yol = depo.dosya_yolu(kayit) if kayit and kayit.get("status") == DURUM_INDIRILDI else None
    if yol is None:
        return jsonify({"error": EK_YOK}), 404
    mime = str(kayit.get("mime") or EK_BILINMEYEN_MIME)
    yanit = send_file(yol, mimetype=mime, as_attachment=(mime == EK_BILINMEYEN_MIME),
                      download_name=_ek_dosya_adi(kayit), conditional=True)
    yanit.headers["X-Content-Type-Options"] = "nosniff"
    yanit.headers["Cache-Control"] = "private, max-age=3600"
    return yanit
```

- [ ] **Step 4: Yeşil olduğunu gör**

Run: `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && DASHBOARD_SECRET_KEY=yerel-test-anahtari-portal-ekleri .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_portal_ekleri_api.py tests/test_portal_susu_uygulama.py tests/test_reader_role.py tests/test_dashboard_api.py tests/test_assistant_odev_listesi.py tests/test_exams.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && test "$(git branch --show-current)" = feat/portal-ekleri && echo dal-dogru
git add src/dashboard_api.py tests/test_portal_ekleri_api.py
git commit -m "$(cat <<'EOF'
/api/ekler/<id>: TEDY kopyasını Range destekli sun; yüklere tedyUrl/status

Yalnız full rol (okur default-deny ile 403); tanınan tür satır içi,
bilinmeyen ikili indirme olarak, nosniff ile. Ödev, sayfa ve duyuru
yükleri her eke tedyUrl, status ve varsa reason ekler.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Görev 9: Asistan indeksi — yalnız ek metni, öncelik, ödev paragrafında ek adları

**Files:**
- Modify: `src/assistant_core.py` (`DEFAULT_EXCLUDED_FILE_PATTERNS` `:89`, yeni sabit `PORTAL_EKLERI_DIZINI`, `_discover_files` `:1407` sıralama, `_is_excluded_file` `:1456`, `_fmt_scraped_data` ödev döngüsü `:728-750`)
- Test: `tests/test_portal_ekleri_indeks.py`

**Interfaces:**
- Consumes: Görev 3 `METIN_ONEKI`.
- Produces: `assistant_core.PORTAL_EKLERI_DIZINI = "content/portal-ekleri"`; indeks `content/portal-ekleri/<id>.txt` dosyalarını (yalnız doğrudan altındakileri) alır; `output/portal_ekleri.json` dışlanır; `_fmt_scraped_data` ödev satırı `| Ekler: <ad>; <ad>` taşır. `INDEX_FORMAT_VERSION` değişmez (belirsizlik 10).

- [ ] **Step 1: Başarısız testi yaz**

`tests/test_portal_ekleri_indeks.py`:

```python
"""Portal attachments in the BM25 index (plan 2026-09-28-portal-ekleri, Görev 9):
only the extracted <id>.txt, never the binaries, sidecars, part files or tracker."""
from src.assistant_core import (INDEX_FORMAT_VERSION, AssistantConfig, AssistantIndexer,
                                HybridRetriever, _fmt_scraped_data)
from src.portal_ekleri import METIN_ONEKI

KIMLIK = "a1b2c3d4e5f60718"


def _yaz(kok, rel, veri="veri"):
    yol = kok / rel
    yol.parent.mkdir(parents=True, exist_ok=True)
    (yol.write_bytes if isinstance(veri, bytes) else yol.write_text)(veri)
    return yol


def _indeksleyici(kok, monkeypatch):
    for k in ("ASSISTANT_INCLUDE_DIRS", "ASSISTANT_EXCLUDED_DIRS", "ASSISTANT_EXCLUDED_FILES", "ASSISTANT_MAX_CHUNKS"):
        monkeypatch.delenv(k, raising=False)
    return AssistantIndexer(AssistantConfig.from_project_root(kok))


def test_yalniz_metin_yan_dosyasi_indekslenir(tmp_path, monkeypatch):
    ix = _indeksleyici(tmp_path, monkeypatch)
    alinir = f"content/portal-ekleri/{KIMLIK}.txt"
    for rel in (f"content/portal-ekleri/{KIMLIK}.pdf", f"content/portal-ekleri/{KIMLIK}.docx",
                f"content/portal-ekleri/{KIMLIK}.meta.json", f"content/portal-ekleri/{KIMLIK}.bin",
                f"content/portal-ekleri/.parca/{KIMLIK}.part", f"content/portal-ekleri/alt/{KIMLIK}.txt",
                "output/portal_ekleri.json"):
        assert ix._is_excluded_file(rel), rel
        assert not ix.is_path_currently_included(rel), rel
    assert not ix._is_excluded_file(alinir) and ix.is_path_currently_included(alinir)
    assert INDEX_FORMAT_VERSION == 2


def test_ekler_icerikte_ders_kitaplarindan_once_kesfedilir(tmp_path, monkeypatch):
    _yaz(tmp_path, "content/eba/Matematik 7 1. Kitap.md", "kitap")
    _yaz(tmp_path, f"content/portal-ekleri/{KIMLIK}.txt", "ek")
    _yaz(tmp_path, "output/scraped_data.json", "{}")
    sira = [p.relative_to(tmp_path).as_posix() for p in _indeksleyici(tmp_path, monkeypatch)._discover_files()]
    assert sira.index("output/scraped_data.json") < sira.index(f"content/portal-ekleri/{KIMLIK}.txt") \
        < sira.index("content/eba/Matematik 7 1. Kitap.md")


def test_ek_metni_adiyla_ve_icerigiyle_bulunur(tmp_path, monkeypatch):
    _yaz(tmp_path, f"content/portal-ekleri/{KIMLIK}.txt",
         f"{METIN_ONEKI}Sayfa 12-13.pdf · Kitap okuma ödevi · Sosyal Bilgiler\n\n"
         "Soru 1: Bumerang kitabının 12. sayfasındaki haritayı açıkla.\n")
    _yaz(tmp_path, f"content/portal-ekleri/{KIMLIK}.pdf", b"%PDF-1.7 ikili")
    ix = _indeksleyici(tmp_path, monkeypatch)
    meta = ix.reindex(incremental=False)
    import json
    parcalar = json.loads(ix.config.chunks_path.read_text(encoding="utf-8"))
    yollar = {p["path"] for p in parcalar}
    assert f"content/portal-ekleri/{KIMLIK}.txt" in yollar
    assert f"content/portal-ekleri/{KIMLIK}.pdf" not in yollar and meta["dusen_dosyalar"] == []
    bulunan = HybridRetriever(chunks=parcalar).search("Bumerang haritası", top_k=3)
    assert bulunan and bulunan[0]["path"] == f"content/portal-ekleri/{KIMLIK}.txt"


def test_odev_paragrafi_ek_adlarini_tasir():
    veri = {"odevlerim": {"homework": {"rows": [{
        "Ders Adı": "Sosyal Bilgiler", "Ödev Başlığı": "Kitap okuma ödevi",
        "detail": {"description": "Sayfa 12-13", "attachments": [
            {"name": "Sayfa 12-13.pdf", "url": "https://ornek.edu.tr/a.pdf"},
            {"name": "Konu videosu", "url": "https://www.youtube.com/watch?v=x"}]}}]}}}
    assert "Ekler: Sayfa 12-13.pdf; Konu videosu" in _fmt_scraped_data(veri)
```

- [ ] **Step 2: Kırmızı olduğunu gör**

Run: `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && DASHBOARD_SECRET_KEY=yerel-test-anahtari-portal-ekleri .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_portal_ekleri_indeks.py`
Expected: FAIL — `.pdf`/`.meta.json`/izleyici dışlanmıyor; sıralama alfabetik; "Ekler:" yok.

- [ ] **Step 3: Uygula**

`src/assistant_core.py`'de `DEFAULT_EXCLUDED_DIRS` tanımının üstüne:

```python
# Portal attachments (src/portal_ekleri.py): only the text TEDY extracted at
# download time, content/portal-ekleri/<id>.txt, is indexed. The binaries
# would be re-extracted here outside the sync's attachment budget (a 112 MB
# PDF, measured 2026-09-28); the .meta.json sidecars and .parca/ part files
# are bookkeeping. The citation label comes from the sidecar
# (assistant_tools.McpRegistry._yerel_etiket), never from this path.
PORTAL_EKLERI_DIZINI = "content/portal-ekleri"
```

`DEFAULT_EXCLUDED_FILE_PATTERNS` içinde `"achieve3000_progress.json",` satırının altına:

```python
    # The attachment tracker: URLs (teachers' SharePoint paths), statuses and
    # hashes — bookkeeping, readable through the attachments themselves.
    "portal_ekleri.json",
```

`_is_excluded_file` içinde `base = Path(normalized).name` satırının altına:

```python
        if normalized.startswith(PORTAL_EKLERI_DIZINI + "/"):
            ic = normalized[len(PORTAL_EKLERI_DIZINI) + 1:]
            return "/" in ic or not ic.endswith(".txt")
```

`_discover_files` içinde `group.sort(...)` satırını değiştir:

```python
            # Işık's own school attachments lead content/, as output/ leads the
            # whole walk: a chunk-cap overrun then drops textbooks first.
            group.sort(key=lambda p: (
                not p.relative_to(root).as_posix().startswith(PORTAL_EKLERI_DIZINI + "/"),
                p.relative_to(root).as_posix()))
```

`_fmt_scraped_data` ödev döngüsünde, `if desc:` satırından önce:

```python
            ek_adlari = [" ".join(str(a.get("name") or "").split())
                         for a in (detail.get("attachments") or [] if isinstance(detail, dict) else [])
                         if isinstance(a, dict) and str(a.get("name") or "").strip()]
            if ek_adlari:
                line += " | Ekler: " + "; ".join(ek_adlari)
```

- [ ] **Step 4: Yeşil olduğunu gör**

Run: `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && DASHBOARD_SECRET_KEY=yerel-test-anahtari-portal-ekleri .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_portal_ekleri_indeks.py tests/test_assistant_indeks_hijyeni.py tests/test_assistant_indeks_dislama.py tests/test_assistant_core.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && test "$(git branch --show-current)" = feat/portal-ekleri && echo dal-dogru
git add src/assistant_core.py tests/test_portal_ekleri_indeks.py
git commit -m "$(cat <<'EOF'
Asistan indeksi portal eklerinin yalnız metnini alır

content/portal-ekleri altında yalnız <id>.txt; ikili, yan meta, parça ve
izleyici dışlanır; ekler content/ içinde ders kitaplarından önce keşfedilir;
ödev paragrafı ek adlarını taşır.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Görev 10: `ek_oku` aracı, `odev_listesi` ekleri, atıf etiketi, istem

**Files:**
- Modify: `src/assistant_tools.py` (sabitler; `odev_listesi_metni` `satir()`; `_EK_OKU_BILDIRIMI`; `ek_oku_metni`; `McpRegistry.__init__`/`declarations`/`_yerel_aciklama`/`dispatch`/`_dispatch_local`/yeni `_yerel_etiket`, `_dispatch_ek`; `build_registry`)
- Modify: `src/assistant_core.py` (`AssistantRuntime.__init__` `build_registry` çağrısı; `SYSTEM_PROMPT` ödev maddesinden sonra)
- Modify: `tests/test_assistant_core.py:363-410` (iki yönlendirme testi)
- Test: `tests/test_assistant_ek_oku.py`

**Interfaces:**
- Consumes: Görev 3 `EkDeposu`, `KIMLIK_DESENI`, `DURUM_*`, `METIN_*`, `ek_basligi`, `ek_kimligi`, `ek_turu`, `metin_govdesi`; Görev 8 rows `detail.attachments[].{id,status}`.
- Produces: `assistant_tools.EK_TOOL = "ek_oku"`, `EK_SAYFA_KARAKTER = 3300`, `PORTAL_EKLERI_ONEKI = "content/portal-ekleri/"`, `ek_oku_metni(depo, kimlik, sayfa=1) -> tuple[str, str, str]` (gövde, etiket, kimlik; düzeltilebilir argümanda `ValueError`), `McpRegistry(..., ek_deposu=None)`, `build_registry(..., ek_deposu=None)`. `AssistantRuntime` her zaman `EkDeposu(project_root)` bağlar → çalışan asistanın 27 aracı var.

- [ ] **Step 1: Başarısız testi yaz**

`tests/test_assistant_ek_oku.py`:

```python
"""The assistant and portal attachments (plan 2026-09-28-portal-ekleri, Görev 10):
ek_oku pages an attachment's text inside the 4,000-char tool-result cut,
odev_listesi names attachments with their ids, BM25 hits carry the sidecar label."""
import json
from datetime import datetime

from src.assistant_tools import (EK_TOOL, GOVDE_SINIRI, McpRegistry, build_registry,
                                 odev_listesi_metni)
from src.portal_ekleri import METIN_ONEKI, EkDeposu, ek_kimligi

SIMDI = datetime(2026, 9, 24, 16, 10)
SP_URL = "https://ornekokul-my.sharepoint.com/:b:/g/personal/ogretmen_ornekokul_k12_tr/EaBcDeFgHiJ?e=AbC123"
KIMLIK = ek_kimligi(SP_URL)
FF = chr(12)
GOVDE = FF.join(f"Sayfa {i} başlığı\n" + ("Bumerang kitabındaki soruyu cevapla. " * 70) for i in range(1, 5))


def _depo(tmp_path, **kayit):
    depo = EkDeposu(tmp_path)
    depo.dizin.mkdir(parents=True, exist_ok=True)
    (depo.dizin / f"{KIMLIK}.pdf").write_bytes(b"%PDF-1.7")
    temel = {"id": KIMLIK, "status": "indirildi", "file": f"{KIMLIK}.pdf", "ext": ".pdf", "text": "var",
             "name": "Sayfa 12-13.pdf", "source": {"section": "odevler", "title": "Kitap okuma ödevi"}}
    depo.yaz({KIMLIK: {**temel, **kayit}})
    depo.metin_yolu(KIMLIK).write_text(
        f"{METIN_ONEKI}Sayfa 12-13.pdf · Kitap okuma ödevi · Sosyal Bilgiler\n\n{GOVDE}\n", encoding="utf-8")
    depo.meta_yolu(KIMLIK).write_text(json.dumps(
        {"id": KIMLIK, "name": "Sayfa 12-13.pdf", "title": "Kitap okuma ödevi"}), encoding="utf-8")
    return depo


def _reg(depo, **kw):
    return McpRegistry(clients={}, local_search=kw.pop("local_search", lambda q, k: []), ek_deposu=depo, **kw)


def test_arac_yalniz_depo_verilince_ilan_edilir(tmp_path):
    assert EK_TOOL not in {d["name"] for d in build_registry(lambda q, k: []).declarations()}
    assert EK_TOOL in {d["name"] for d in _reg(_depo(tmp_path)).declarations()}
    out = build_registry(lambda q, k: []).dispatch(EK_TOOL, {"id": KIMLIK})
    assert not out.ok and "bilinmeyen araç" in out.error


def test_ilk_sayfa_sinir_altinda_devamini_soyler(tmp_path):
    out = _reg(_depo(tmp_path)).dispatch(EK_TOOL, {"id": KIMLIK})
    assert out.ok and len(out.text) <= GOVDE_SINIRI
    assert out.text.startswith("Ek: Sayfa 12-13.pdf · Kitap okuma ödevi\nMetin sayfası 1/")
    assert "PDF s.1" in out.text and f"(Devamı: ek_oku id={KIMLIK} sayfa=2)" in out.text
    assert METIN_ONEKI not in out.text and FF not in out.text
    atif = out.citations[0]
    assert atif["label"] == "Sayfa 12-13.pdf · Kitap okuma ödevi" and atif["kind"] == "ogrenci"
    assert "content/" not in atif["label"] and atif["locator"]["id"] == KIMLIK


def test_son_sayfa_ve_aralik_disi(tmp_path):
    reg = _reg(_depo(tmp_path))
    ilk = reg.dispatch(EK_TOOL, {"id": KIMLIK}).text
    toplam = int(ilk.split("Metin sayfası 1/")[1].split()[0])
    son = reg.dispatch(EK_TOOL, {"id": f"ek:{KIMLIK}", "sayfa": toplam})
    assert son.ok and "(Ekin sonu.)" in son.text
    disari = reg.dispatch(EK_TOOL, {"id": KIMLIK, "sayfa": toplam + 1})
    assert not disari.ok and "metin sayfası var" in disari.error


def test_gecersiz_ve_bilinmeyen_kimlik(tmp_path):
    reg = _reg(_depo(tmp_path))
    assert "16 karakterlik" in reg.dispatch(EK_TOOL, {"id": "../x"}).error
    assert "böyle bir ek yok" in reg.dispatch(EK_TOOL, {"id": "0123456789abcdef"}).error


def test_durumlar_durustce_soylenir(tmp_path):
    out = _reg(_depo(tmp_path, status="erisilemedi", reason="kaynak giriş istiyor; paylaşım herkese açık değil")
               ).dispatch(EK_TOOL, {"id": KIMLIK})
    assert out.ok and "indirilemedi" in out.text and "giriş istiyor" in out.text
    assert "metin katmanı yok" in _reg(_depo(tmp_path, text="yok")).dispatch(EK_TOOL, {"id": KIMLIK}).text
    assert ".xlsx" in _reg(_depo(tmp_path, text="desteklenmiyor", ext=".xlsx")).dispatch(EK_TOOL, {"id": KIMLIK}).text
    assert "henüz çıkarılmadı" in _reg(_depo(tmp_path, text="bekliyor")).dispatch(EK_TOOL, {"id": KIMLIK}).text


def test_bm25_isabeti_yan_meta_etiketini_tasir(tmp_path):
    satirlar = [{"path": f"content/portal-ekleri/{KIMLIK}.txt", "chunk_index": 0, "text": "Bumerang",
                 "snippet": "Bumerang", "confidence": 0.8},
                {"path": "content/portal-ekleri/0123456789abcdef.txt", "chunk_index": 0, "text": "x",
                 "snippet": "x", "confidence": 0.5}]
    out = _reg(_depo(tmp_path), local_search=lambda q, k: satirlar).dispatch("ogrenci_verisi_ara", {"query": "Bumerang"})
    assert [a["label"] for a in out.citations] == ["Sayfa 12-13.pdf · Kitap okuma ödevi", "Portal eki"]


def _hw(ekler):
    return {"Ders Adı": "Sosyal Bilgiler", "normalized_course": "Sosyal Bilgiler",
            "Ödev Başlığı": "Kitap okuma ödevi", "Ödev Son Teslim Tarihi": "25.09.2026 12:00",
            "Ödev Durumu": "Değerlendirilmemiş", "detail": {"description": "Sayfa 12-13", "attachments": ekler}}


def test_odev_listesi_ekleri_kimlikleriyle_listeler():
    duvar = SP_URL.replace("EaBcDe", "EzYxWv")
    metin = odev_listesi_metni([_hw([
        {"name": "Sayfa 12-13.pdf", "url": SP_URL, "id": KIMLIK, "status": "indirildi"},
        {"name": "Kitap sayfaları", "url": duvar, "id": ek_kimligi(duvar), "status": "erisilemedi"},
        {"name": "Konu videosu", "url": "https://www.youtube.com/watch?v=x", "id": None, "status": "baglanti"}])], SIMDI)
    assert (f"Ekler: Sayfa 12-13.pdf [ek:{KIMLIK}]; Kitap sayfaları [ek:{ek_kimligi(duvar)} · indirilemedi]; "
            "Konu videosu (bağlantı)") in metin


def test_zenginlestirilmemis_satirda_kimlik_url_den_turetilir():
    metin = odev_listesi_metni([_hw([{"name": "Sayfa 12-13.pdf", "url": SP_URL}])], SIMDI)
    assert f"[ek:{KIMLIK}]" in metin


def test_calisan_asistan_araci_her_zaman_bagli(tmp_path):
    from src.assistant_core import AssistantRuntime
    (tmp_path / "output").mkdir()
    assert EK_TOOL in {d["name"] for d in AssistantRuntime(tmp_path).registry.declarations()}
```

`tests/test_assistant_core.py`'de `test_system_prompt_routing_order_matches_the_consolidated_plan` içindeki `sira`:

```python
    sira = ["`ders_programi`", "`odev_listesi`", "`ek_oku`", "`ogrenci_verisi_ara`",
            "`kazanim_ara`", "`kazanim_listele`", "`figur_ara`", "`video_listele`",
            "`oer_ara`", "`oer_kazanima_gore`", "`modul_ara`", "`kitap_ara`",
            "`platform_ilerlemesi`", "`video_oner`", "`aile_kaynak_ara`"]
```

`test_system_prompt_routing_names_every_declared_tool_exactly_once` içinde `yerel_araclar`'a `"ek_oku",` (`"odev_listesi",`'ın yanına) ve `assert len(tum_araclar) == 26` → `== 27` (yorumdaki "26-tool" → "27-tool").

- [ ] **Step 2: Kırmızı olduğunu gör**

Run: `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && DASHBOARD_SECRET_KEY=yerel-test-anahtari-portal-ekleri .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_assistant_ek_oku.py tests/test_assistant_core.py -k "ek_oku or ek_ or routing or odev_listesi"`
Expected: FAIL — `ImportError: cannot import name 'EK_TOOL'`.

- [ ] **Step 3: Araç ve metin**

`src/assistant_tools.py` içe aktarmalarına (Görev 1'in `temiz_metin` satırının altına):

```python
from src.portal_ekleri import (DURUM_BAGLANTI, DURUM_BEKLIYOR, DURUM_COK_BUYUK, DURUM_ERISILEMEDI,
                               DURUM_HATA, DURUM_INDIRILDI, KIMLIK_DESENI, METIN_DESTEKLENMIYOR,
                               METIN_VAR, METIN_YOK, ek_basligi, ek_kimligi, ek_turu, metin_govdesi)
```

`ODEV_ATIF` tanımının altına:

```python
# Portal attachments (plan 2026-09-28-portal-ekleri): ek_oku pages the text
# TEDY extracted at download time; odev_listesi names each attachment with
# the id ek_oku takes.
EK_TOOL = "ek_oku"
EK_SAYFA_KARAKTER = 3300
PORTAL_EKLERI_ONEKI = "content/portal-ekleri/"
_EK_SATIR_SINIRI = 4
_EK_DURUM_KISA = {DURUM_BEKLIYOR: "henüz indirilmedi", DURUM_ERISILEMEDI: "indirilemedi",
                  DURUM_COK_BUYUK: "çok büyük, indirilmedi", DURUM_HATA: "indirilemedi"}


def _ek_satiri(r: dict[str, Any]) -> str:
    """"Ekler: <ad> [ek:<id>]; …" — the id is what ek_oku takes. A copy TEDY
    does not hold says so; a plain link is marked as one."""
    ekler = [a for a in ((r.get("detail") or {}).get("attachments") or [])
             if isinstance(a, dict) and a.get("url")]
    parcalar = []
    for a in ekler[:_EK_SATIR_SINIRI]:
        ad = _kirp(" ".join(str(a.get("name") or "ek").split()), 60)
        durum = a.get("status")
        if durum == DURUM_BAGLANTI or ek_turu(a["url"]) == "baglanti":
            parcalar.append(f"{ad} (bağlantı)")
            continue
        kimlik = a.get("id") or ek_kimligi(a["url"])
        not_ = f" · {_EK_DURUM_KISA[durum]}" if durum in _EK_DURUM_KISA else ""
        parcalar.append(f"{ad} [ek:{kimlik}{not_}]")
    if len(ekler) > _EK_SATIR_SINIRI:
        parcalar.append(f"+{len(ekler) - _EK_SATIR_SINIRI} ek")
    return "; ".join(parcalar)
```

Not: `_kirp` bu noktada henüz tanımlı değilse (`_kirp` dosyada ~1400. satırda), `_ek_satiri` çağrı anında çözüldüğü için sorun yoktur; Python adı çalışma zamanında arar.

`odev_listesi_metni` içindeki `satir()` iç fonksiyonunda `return metin`'den önce:

```python
        ekler = _ek_satiri(r)
        if ekler:
            metin += f"\n  Ekler: {ekler}"
```

`_AILE_ARAMA_BILDIRIMI`'nin altına:

```python
_EK_OKU_BILDIRIMI: dict[str, Any] = {
    "name": EK_TOOL,
    "description": (
        "Bir ödevin ya da portal sayfasının ekini (öğretmenin PDF'i, Word belgesi, Google "
        "dokümanı) TEDY'deki kopyasından metin sayfası metin sayfası okur. `id`, ödev "
        "listesindeki 'Ekler' satırında [ek:…] olarak yazan 16 karakterlik koddur. Ekin "
        "içeriği sorulduğunda (hangi sorular, hangi sayfalar, ne isteniyor) BU aracı kullan; "
        "ilk çağrıda sayfa=1, devamı gerekirse sonuçtaki sayfa numarasıyla."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "id": {"type": "string", "description": "Ekin kimliği, ör. 'a1b2c3d4e5f60718'."},
            "sayfa": {"type": "integer", "description": "Kaçıncı metin sayfası (1'den başlar; varsayılan 1)."},
        },
        "required": ["id"],
    },
}


def _ek_sayfa_sinirlari(govde: str, boyut: int = EK_SAYFA_KARAKTER) -> list[tuple[int, int]]:
    """Deterministic text pages of at most `boyut` characters, cut at the
    last line break, form feed or space in the second half of a page."""
    sinirlar: list[tuple[int, int]] = []
    i = 0
    while i < len(govde):
        son = min(len(govde), i + boyut)
        if son < len(govde):
            kes = max(govde.rfind("\n", i, son), govde.rfind(" ", i, son), govde.rfind(chr(12), i, son))
            if kes > i + boyut // 2:
                son = kes
        if govde[i:son].strip():
            sinirlar.append((i, son))
        i = son
    return sinirlar


def ek_oku_metni(depo: Any, kimlik: Any, sayfa: Any = 1) -> tuple[str, str, str]:
    """(body, citation label, id) for ek_oku. A ValueError is an argument the
    model can correct. Honest about every state: not downloaded (with the
    reason), no text layer (a scan — no OCR, plan decision 2), a type whose
    text is not read, text not extracted yet."""
    kimlik = str(kimlik or "").strip().lower()
    if kimlik.startswith("ek:"):
        kimlik = kimlik[3:]
    if not KIMLIK_DESENI.match(kimlik):
        raise ValueError("ek kimliği 16 karakterlik bir koddur; ödev listesindeki [ek:…] değerini ver")
    kayit = depo.kayit(kimlik)
    if kayit is None:
        raise ValueError(f"böyle bir ek yok: {kimlik}")
    etiket = ek_basligi(kayit)
    bas = f"Ek: {etiket}"
    if kayit.get("status") != DURUM_INDIRILDI:
        neden = str(kayit.get("reason") or _EK_DURUM_KISA.get(kayit.get("status"), "dosya değil"))
        return (f"{bas}\nBu ek TEDY'ye indirilemedi ({neden}). İçeriğini okuyamıyorum; "
                "okur eki kaynağında açabilir."), etiket, kimlik
    metin_durumu = kayit.get("text")
    if metin_durumu == METIN_YOK:
        return (f"{bas}\nBu ekin metin katmanı yok (taranmış belge ya da görsel); içeriğini "
                "okuyamıyorum. Okur dosyayı TEDY'de açabilir."), etiket, kimlik
    if metin_durumu == METIN_DESTEKLENMIYOR:
        return (f"{bas}\nBu ek türünün ({kayit.get('ext') or 'bilinmeyen tür'}) metnini okuyamıyorum; "
                "okur dosyayı TEDY'de açabilir."), etiket, kimlik
    ham = ""
    if metin_durumu == METIN_VAR:
        try:
            ham = depo.metin_yolu(kimlik).read_text(encoding="utf-8")
        except OSError:
            ham = ""
    govde = metin_govdesi(ham)
    sinirlar = _ek_sayfa_sinirlari(govde)
    if not sinirlar:
        return f"{bas}\nEkin metni henüz çıkarılmadı; bir sonraki eşitlemede hazır olur.", etiket, kimlik
    try:
        n = int(sayfa or 1)
    except (TypeError, ValueError):
        n = 1
    toplam = len(sinirlar)
    if not 1 <= n <= toplam:
        raise ValueError(f"bu ekin {toplam} metin sayfası var; sayfa 1–{toplam} arası olmalı")
    bas_i, son_i = sinirlar[n - 1]
    ff = chr(12)
    pdf = ""
    if ff in govde:
        ilk_s, son_s = govde.count(ff, 0, bas_i) + 1, govde.count(ff, 0, son_i) + 1
        pdf = f" · PDF s.{ilk_s}" + (f"–{son_s}" if son_s != ilk_s else "")
    parca = govde[bas_i:son_i].replace(ff, "\n").strip()
    kuyruk = f"\n\n(Devamı: ek_oku id={kimlik} sayfa={n + 1})" if n < toplam else "\n\n(Ekin sonu.)"
    return f"{bas}\nMetin sayfası {n}/{toplam}{pdf}\n\n{parca}{kuyruk}", etiket, kimlik
```

- [ ] **Step 4: Kayıt defteri**

`McpRegistry.__init__` imzasına `saat` parametresinden önce:

```python
                 ek_deposu: Any = None,
```

gövdeye (`self.aile_kaynak_arama = aile_kaynak_arama` altına):

```python
        # Portal attachments (src/portal_ekleri.EkDeposu): ek_oku reads it and
        # BM25 hits under content/portal-ekleri take its sidecar label. None
        # leaves ek_oku undeclared.
        self.ek_deposu = ek_deposu
```

`declarations()` içinde `odev_listesi` bloğundan hemen sonra:

```python
        if self.ek_deposu is not None:
            decls.append(copy.deepcopy(_EK_OKU_BILDIRIMI))
```

`_yerel_aciklama` içindeki `yonlendirme` listesine ilk öğeden sonra:

```python
        yonlendirme = [(self.odev_kaynagi, "ödevlerin durumu → `odev_listesi`"),
                       (self.ek_deposu, "bir ödev ya da sayfa ekinin içeriği → `ek_oku`")] + [
```

(kalan liste aynen). `dispatch()` içinde `if name == ODEV_TOOL …` satırının altına:

```python
        if name == EK_TOOL and self.ek_deposu is not None:
            return self._dispatch_ek(args or {})
```

`_dispatch_local`:

```python
    def _dispatch_local(self, args: dict[str, Any]) -> ToolOutcome:
        query = str(args.get("query", "")).strip()
        return _dispatch_bm25_arama(
            self.local_search, query, kind="ogrenci",
            etiket_fn=self._yerel_etiket, hata_onek="yerel arama hatası")

    def _yerel_etiket(self, path: str) -> str:
        """An attachment hit is named "<ek adı> · <ödev başlığı>" from its
        .meta.json sidecar — never by its internal path."""
        if path.startswith(PORTAL_EKLERI_ONEKI):
            meta = self.ek_deposu.meta(os.path.splitext(os.path.basename(path))[0]) \
                if self.ek_deposu is not None else {}
            return ek_basligi(meta) if meta else "Portal eki"
        return _yerel_isabet_etiketi(path)

    def _dispatch_ek(self, args: dict[str, Any]) -> ToolOutcome:
        try:
            metin, etiket, kimlik = ek_oku_metni(self.ek_deposu, args.get("id"), args.get("sayfa", 1))
        except ValueError as exc:
            return ToolOutcome(ok=False, error=str(exc))
        except Exception as exc:  # noqa: BLE001 — told to the model, never raised through the loop
            logger.error("ek_oku failed: %s", type(exc).__name__)
            return ToolOutcome(ok=False, error=f"ek okunamadı: {type(exc).__name__}")
        metin = _kirp(metin, GOVDE_SINIRI)
        return ToolOutcome(ok=True, text=metin, citations=[{
            "kind": "ogrenci",
            "label": etiket,
            "locator": {"tool": EK_TOOL, "id": kimlik, "sayfa": args.get("sayfa", 1)},
            "snippet": metin[:400],
            "confidence": 1.0,
        }])
```

`build_registry` imzasına `saat`'ten önce `ek_deposu: Any = None,` ve `McpRegistry(...)` çağrısına `ek_deposu=ek_deposu,` ekle.

- [ ] **Step 5: Runtime ve istem**

`src/assistant_core.py` `AssistantRuntime.__init__` içinde `from src.assistant_tools import build_registry` satırının altına:

```python
        from src.portal_ekleri import EkDeposu
```

`build_registry(...)` çağrısına `aile_kaynak_arama=self._aile_search`'ten sonra:

```python
                                       ek_deposu=EkDeposu(self.config.project_root),
```

`SYSTEM_PROMPT` içinde ödev maddesinin sonu olan `"sorudaki 'Bugün:' satırına göre çöz.\n"` satırının hemen altına (araç adını ters tırnaksız anmak şart: yönlendirme testi her aracı tam bir kez sayar):

```python
        "- Bir ödevin ya da portal sayfasının ekinin içeriği (hangi sorular, hangi sayfalar, "
        "ne isteniyor) → `ek_oku`; kimlik, ödev listesindeki 'Ekler' satırında [ek:…] olarak "
        "yazar. Ek indirilemediyse ya da metin katmanı yoksa bunu açıkça söyle; ekin "
        "içeriğini tahmin etme.\n"
```

- [ ] **Step 6: Yeşil olduğunu gör**

Run: `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && DASHBOARD_SECRET_KEY=yerel-test-anahtari-portal-ekleri .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_assistant_ek_oku.py tests/test_assistant_core.py tests/test_assistant_odev_listesi.py tests/test_assistant_tools.py tests/test_assistant_ogrenci_araclari.py tests/test_assistant_yerel_kaynaklar.py tests/test_assistant_aile_kaynaklari.py tests/test_assistant_gorseller.py tests/test_assistant_modul_araci.py tests/test_assistant_indeks_hijyeni.py tests/test_assistant_arac_sonuc_kesme.py`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && test "$(git branch --show-current)" = feat/portal-ekleri && echo dal-dogru
git add src/assistant_tools.py src/assistant_core.py tests/test_assistant_ek_oku.py tests/test_assistant_core.py
git commit -m "$(cat <<'EOF'
Asistan ekleri okur: ek_oku, odev_listesi'nde ek kimlikleri, atıf etiketi

ek_oku eki 3.900 karakter içinde metin sayfalarıyla okur, PDF sayfa
aralığını söyler; indirilemeyen, metin katmanı olmayan ve desteklenmeyen
ekleri dürüstçe bildirir. BM25 isabeti yan meta etiketiyle ("<ek> · <ödev>")
anılır. İstem her aracı tam bir kez yönlendirir (27 araç).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Görev 11: Pano — ek bağlantısı (İşler, Bugün, Duyurular)

**Files:**
- Modify: `dashboard/src/types.ts:3-22` (`HomeworkItem`), `:117-129` (`Announcement`)
- Create: `dashboard/src/components/patterns/EkBaglantisi.tsx`, `dashboard/src/components/patterns/EkBaglantisi.scss`
- Modify: `dashboard/src/components/HomeworkTracker.tsx:3,528-539`, `dashboard/src/components/NextThing.tsx:2,32,104-114`, `dashboard/src/components/NextThing.scss:82-95`, `dashboard/src/components/Announcements.tsx:81-96`, `dashboard/src/theme/ted-theme.scss:1048-1061,1696` civarı
- Test: `dashboard/tests/e2e/portal-ekleri.spec.ts`

**Interfaces:**
- Consumes: Görev 8 yük biçimi `{name, url, id, tedyUrl, status, reason?}`.
- Produces: `types.ts` → `export type EkDurumu`, `export interface PortalEki`; `components/patterns/EkBaglantisi.tsx` → `export function EkBaglantisi({ ek }: { ek: PortalEki })`. Sınıflar: `.tedy-ek`, `.tedy-ek__ana`, `.tedy-ek__kaynak`, `.tedy-ek__durum`, `.homework-modal__attachment-list`, `.announcements-detail__ekler`.

- [ ] **Step 1: Bağımlılıklar**

Run: `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri/dashboard && (test -d node_modules || npm ci) ; echo "npm ci çıkış: $?"`
Expected: `0`.

- [ ] **Step 2: Başarısız e2e testini yaz**

`dashboard/tests/e2e/portal-ekleri.spec.ts`:

```ts
import { test, expect, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { bugunAc, HW } from './_bugun-fixtures'

// Plan docs/superpowers/plans/2026-09-28-portal-ekleri.md, Görev 11: an
// attachment opens TEDY's copy, keeps a secondary "Kaynağında aç" link to the
// original, and says so when there is no copy. Hosts and ids are invented.

const json = (b: unknown) => ({
  status: 200, contentType: 'application/json', body: JSON.stringify(b),
})

const INDIRILDI = {
  name: 'Sayfa 12-13.pdf',
  url: 'https://ornekokul-my.sharepoint.com/:b:/g/personal/ogretmen_ornekokul_k12_tr/EaBcDeF?e=AbC123',
  id: 'a1b2c3d4e5f60718', tedyUrl: '/api/ekler/a1b2c3d4e5f60718', status: 'indirildi',
}
const INDIRILEMEDI = {
  name: 'Kitap sayfaları',
  url: 'https://ornekokul-my.sharepoint.com/:b:/g/personal/ogretmen_ornekokul_k12_tr/EzYxWvU?e=XyZ789',
  id: '0f1e2d3c4b5a6978', tedyUrl: null, status: 'erisilemedi',
  reason: 'kaynak giriş istiyor; paylaşım herkese açık değil',
}
const BAGLANTI = {
  name: 'Konu videosu', url: 'https://www.youtube.com/watch?v=ornekvideo01',
  id: null, tedyUrl: null, status: 'baglanti',
}
const ODEV = HW('Sosyal Bilgiler', 'Kitap okuma ödevi', '25.09.2026 12:00', 'Sayfa 12-13 okunacak.', {
  detail: { description: 'Sayfa 12-13 okunacak.', attachments: [INDIRILDI, INDIRILEMEDI, BAGLANTI] },
})

async function islerModali(page: Page) {
  await page.route('**/api/homework', r => r.fulfill(json({ summary: '', homework: [ODEV] })))
  await page.route('**/api/enrichment', r => r.fulfill(json({})))
  await page.route('**/api/exams', r => r.fulfill(json({ exams: [] })))
  await page.route('**/api/health', r => r.fulfill(json({
    timestamp: '', success: true, scrape_errors: [], duration_seconds: 1,
  })))
  await page.clock.setFixedTime(new Date('2026-09-24T18:00:00'))
  await page.goto('/isler')
  await page.locator('.homework-item').first().waitFor()
  await page.locator('.homework-item').first().click()
  const ekler = page.locator('.homework-modal__attachments')
  await ekler.waitFor()
  return ekler
}

test.describe('Portal ekleri', () => {
  test('İşler: indirilen ek TEDY kopyasını açar, kaynağı ikincil kalır', async ({ page }) => {
    const ekler = await islerModali(page)
    await expect(ekler.getByRole('link', { name: 'Sayfa 12-13.pdf', exact: true }))
      .toHaveAttribute('href', '/api/ekler/a1b2c3d4e5f60718')
    await expect(ekler.getByRole('link', { name: 'Kaynağında aç: Sayfa 12-13.pdf' }))
      .toHaveAttribute('href', INDIRILDI.url)
  })

  test('İşler: indirilemeyen ek bunu söyler; düz bağlantı uyarı taşımaz', async ({ page }) => {
    const ekler = await islerModali(page)
    await expect(ekler.getByRole('link', { name: 'Kitap sayfaları', exact: true }))
      .toHaveAttribute('href', INDIRILEMEDI.url)
    await expect(ekler.locator('li', { hasText: 'Kitap sayfaları' }))
      .toContainText('İndirilemedi — kaynağında aç')
    const video = ekler.locator('li', { hasText: 'Konu videosu' })
    await expect(video.getByRole('link', { name: 'Konu videosu', exact: true }))
      .toHaveAttribute('href', BAGLANTI.url)
    await expect(video).not.toContainText('İndirilemedi')
  })

  test('İşler: ek listesi erişilebilir', async ({ page }) => {
    await islerModali(page)
    const sonuc = await new AxeBuilder({ page })
      .include('.homework-modal__attachments')
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
      .analyze()
    expect(sonuc.violations).toEqual([])
  })

  test('Bugün: Başla kutusunda aynı ek bağlantısı', async ({ page }) => {
    await bugunAc(page, '2026-09-24T16:40', { homework: { summary: '', homework: [ODEV] } })
    const kart = page.locator('.next-thing')
    await kart.getByRole('button', { name: 'Başla' }).click()
    await expect(kart.getByRole('link', { name: 'Sayfa 12-13.pdf', exact: true }))
      .toHaveAttribute('href', '/api/ekler/a1b2c3d4e5f60718')
    await expect(kart).toContainText('İndirilemedi — kaynağında aç')
  })
})
```

- [ ] **Step 3: Kırmızı olduğunu gör**

Run: `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri/dashboard && npm run build; echo "build çıkış: $?"` ardından `env -u ANTHROPIC_API_KEY TEDY_E2E_PORT=8297 DASHBOARD_SECRET_KEY=yerel-test-anahtari-portal-ekleri npx playwright test portal-ekleri` (Bash timeout 600000)
Expected: build `0`; spec FAIL (bağlantı `href`'i özgün adres, "Kaynağında aç" yok).

- [ ] **Step 4: Tipler**

`dashboard/src/types.ts` başına (import'un altına):

```ts
/** Where TEDY stands with one portal attachment (backend src/portal_ekleri.py). */
export type EkDurumu = 'indirildi' | 'bekliyor' | 'erisilemedi' | 'cok_buyuk' | 'hata' | 'baglanti'

/** An attachment as /api/homework, /api/pages and /api/announcements serve it:
 *  `tedyUrl` only when TEDY holds the copy; `url` is always the original. */
export interface PortalEki {
  name: string
  url: string
  id?: string | null
  tedyUrl?: string | null
  status?: EkDurumu
  reason?: string
}
```

`HomeworkItem.detail`:

```ts
  detail?: {
    description: string
    attachments: PortalEki[]
  }
```

`Announcement` içinde `"Ekleri_url"?: string` altına ve dizin imzasını değiştir:

```ts
  /** Each `<column>_url`, as an attachment with its TEDY copy (plan 2026-09-28). */
  ekler?: PortalEki[]
  [key: string]: string | PortalEki[] | undefined
```

- [ ] **Step 5: Bileşen**

`dashboard/src/components/patterns/EkBaglantisi.tsx`:

```tsx
import { Document, Launch } from '@carbon/icons-react'
import type { PortalEki } from '../../types'
import './EkBaglantisi.scss'

// What to say when TEDY holds no copy. A plain link (a video, a folder) is not
// a failed download and says nothing (docs/frontend-design-principles.md D3:
// no silent failure — and no false alarm either).
const DURUM_SOZU: Record<string, string> = {
  bekliyor: 'Henüz indirilmedi — kaynağında aç',
  erisilemedi: 'İndirilemedi — kaynağında aç',
  cok_buyuk: 'İndirilemedi (çok büyük) — kaynağında aç',
  hata: 'İndirilemedi — kaynağında aç',
}

/**
 * One portal attachment. With a TEDY copy the name opens it and the original
 * stays one quiet step away ("Kaynağında aç"); without one the name opens the
 * original and the line says why there is no copy.
 */
export function EkBaglantisi({ ek }: { ek: PortalEki }) {
  if (ek.tedyUrl) {
    return (
      <span className="tedy-ek">
        <a className="tedy-ek__ana" href={ek.tedyUrl} target="_blank" rel="noopener">
          <Document size={16} aria-hidden="true" /> {ek.name}
        </a>
        <a
          className="tedy-ek__kaynak"
          href={ek.url}
          target="_blank"
          rel="noopener noreferrer"
          aria-label={`Kaynağında aç: ${ek.name}`}
        >
          Kaynağında aç
        </a>
      </span>
    )
  }
  const soz = ek.status && ek.status !== 'baglanti'
    ? (DURUM_SOZU[ek.status] ?? DURUM_SOZU.hata)
    : null
  return (
    <span className="tedy-ek">
      <a className="tedy-ek__ana" href={ek.url} target="_blank" rel="noopener noreferrer">
        {ek.status === 'baglanti' ? <Launch size={16} aria-hidden="true" /> : <Document size={16} aria-hidden="true" />}
        {' '}{ek.name}
      </a>
      {soz && <span className="tedy-ek__durum">{soz}</span>}
    </span>
  )
}
```

`dashboard/src/components/patterns/EkBaglantisi.scss`:

```scss
@use '@carbon/react/scss/theme' as theme;
@use '@carbon/react/scss/type' as type;
@use '@carbon/react/scss/spacing' as *;

// One portal attachment (plan 2026-09-28-portal-ekleri): the copy TEDY holds
// is the primary link; the original is a quieter second one, or the status
// says why there is no copy. Carbon tokens only.
.tedy-ek {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: baseline;
  column-gap: $spacing-04;
  row-gap: $spacing-01;
}

.tedy-ek__ana {
  display: inline-flex;
  align-items: center;
  gap: $spacing-02;
  min-block-size: $spacing-07;
  @include type.type-style('body-compact-01');
  color: theme.$link-primary;
}

.tedy-ek__kaynak {
  @include type.type-style('helper-text-01');
  color: theme.$link-secondary;
}

.tedy-ek__durum {
  @include type.type-style('helper-text-01');
  color: theme.$text-secondary;
}
```

- [ ] **Step 6: Yüzeyler**

`HomeworkTracker.tsx` 3. satır (`Document` artık kullanılmıyor):

```tsx
import { Timer, CheckmarkFilled, CloseFilled, ChevronDown, ChevronUp } from '@carbon/icons-react'
```

ve içe aktarmalara:

```tsx
import { EkBaglantisi } from './patterns/EkBaglantisi'
```

Ek bloğu (528-539):

```tsx
      {/* Attachments: TEDY's copy first, the original one step away */}
      {(hw.detail?.attachments?.length ?? 0) > 0 && (
        <div className="homework-modal__attachments">
          <h5 className="homework-modal__attachments-title">Ekler</h5>
          <ul className="homework-modal__attachment-list">
            {hw.detail!.attachments.map((ek, i) => (
              <li key={ek.id ?? `${i}-${ek.url}`}><EkBaglantisi ek={ek} /></li>
            ))}
          </ul>
        </div>
      )}
```

`NextThing.tsx` 2. satır ve içe aktarmalar:

```tsx
import { ArrowRight } from '@carbon/icons-react'
import type { PortalEki } from '../types'
import { EkBaglantisi } from './patterns/EkBaglantisi'
```

prop tipi:

```tsx
  attachments?: PortalEki[]
```

ek listesi (104-114):

```tsx
        {suruyor && (attachments?.length ?? 0) > 0 && (
          <ul className="next-thing__attachments">
            {attachments!.map((ek, i) => (
              <li key={ek.id ?? `${i}-${ek.url}`}><EkBaglantisi ek={ek} /></li>
            ))}
          </ul>
        )}
```

`NextThing.scss` `.next-thing__attachments` bloğu (82-95) tamamen:

```scss
.next-thing__attachments {
  list-style: none;
  margin: $spacing-03 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: $spacing-02;
}
```

`Announcements.tsx` içe aktarmalara `import { EkBaglantisi } from './patterns/EkBaglantisi'`; `{ann["Ekleri_url"] && ( … )}` bloğunun yerine:

```tsx
                  {(ann.ekler?.length ?? 0) > 0 ? (
                    <ul className="announcements-detail__ekler">
                      {ann.ekler!.map((ek, j) => (
                        <li key={ek.id ?? `${j}-${ek.url}`}><EkBaglantisi ek={ek} /></li>
                      ))}
                    </ul>
                  ) : ann["Ekleri_url"] && (
                    <a
                      className="announcements-detail__link"
                      href={ann["Ekleri_url"]}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      Eki aç
                    </a>
                  )}
```

`ted-theme.scss`: `.homework-modal__attachment-link { … }` ve `.homework-modal__attachment-link:hover { … }` bloklarını (1048-1061) sil, yerine:

```scss
.homework-modal__attachment-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--ted-space-2xs);
}
```

`.announcements-detail__link { … }` bloğunun hemen üstüne:

```scss
.announcements-detail__ekler {
  list-style: none;
  margin: 0;
  padding: 0;
}
```

- [ ] **Step 7: Lint, build, e2e**

Run: `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri/dashboard && npm run lint; echo "lint çıkış: $?"`
Expected: `0`.

Run: `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri/dashboard && npm run build; echo "build çıkış: $?"`
Expected: `0`.

Run (Bash timeout 600000): `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri/dashboard && env -u ANTHROPIC_API_KEY TEDY_E2E_PORT=8297 DASHBOARD_SECRET_KEY=yerel-test-anahtari-portal-ekleri npx playwright test portal-ekleri homework isler bugun-yarin-yaptim today gorsel-regresyon aria-yapisi`
Expected: PASS. Görsel/aria taban çizgileri değişmemeli (fixture'larda ek yok); kırmızıysa Global Constraints'teki fark okuma yordamını uygula ve rapora yaz.

Run: `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && DASHBOARD_SECRET_KEY=yerel-test-anahtari-portal-ekleri .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pano_tasarim_sistemi.py tests/test_tedy_tasarim_tutarliligi.py`
Expected: PASS (yeni SCSS token kurallarına uyar).

- [ ] **Step 8: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && test "$(git branch --show-current)" = feat/portal-ekleri && echo dal-dogru
git add dashboard/src/types.ts dashboard/src/components/patterns/EkBaglantisi.tsx dashboard/src/components/patterns/EkBaglantisi.scss dashboard/src/components/HomeworkTracker.tsx dashboard/src/components/NextThing.tsx dashboard/src/components/NextThing.scss dashboard/src/components/Announcements.tsx dashboard/src/theme/ted-theme.scss dashboard/tests/e2e/portal-ekleri.spec.ts
git commit -m "$(cat <<'EOF'
Pano ekleri TEDY kopyasından açar; kaynak ikincil, durum görünür

İşler modalı, Bugün kutusu ve duyurular tek EkBaglantisi bileşenini
kullanır: kopya varsa ad TEDY'yi açar ve "Kaynağında aç" ikincil kalır;
yoksa "İndirilemedi — kaynağında aç" der; düz bağlantı uyarı taşımaz.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Görev 12: Pano — Ders İçerikleri'nde süs savunması

**Files:**
- Create: `dashboard/src/utils/portalSusu.ts`
- Modify: `dashboard/src/components/CourseContent.tsx:1-7` (içe aktarma), `:26-53` (`parseCard`), `:131-150` (birleştirme döngüsü)
- Test: `dashboard/tests/e2e/dersler-portal-susu.spec.ts`

**Interfaces:**
- Consumes: Görev 1'in kuralları (birebir TS portu).
- Produces: `utils/portalSusu.ts` → `export function portalSusunuAyikla(metin: string): string`.

- [ ] **Step 1: Başarısız e2e testini yaz**

`dashboard/tests/e2e/dersler-portal-susu.spec.ts`:

```ts
import { test, expect } from '@playwright/test'

// Plan 2026-09-28-portal-ekleri, Görev 12: the API already serves course
// content clean (src/portal_susu.py); this proves the page is safe on its own
// if raw data ever reaches it. Invented names — the shape is the real one.

const json = (b: unknown) => ({
  status: 200, contentType: 'application/json', body: JSON.stringify(b),
})

const GENEL_KART = [
  'Okulumuzda Bilim Şenliği Başlıyor',
  'TED Rönesans Koleji | 22.09.2026',
  '  3 Yorum yapıldı!',
  '  Daha fazla oku',
  'Kurgu Öğrenci Bir', '3', 'çok güzel olmuş',
  'Uydurma Öğrenci İki', '0', 'harika bir etkinlik',
  'Yorum Ekle',
].join('\n')
const YALNIZ_YORUM = ['  Daha fazla oku', 'Deneme Öğrenci Üç', '1', 'ben de katılacağım', 'Yorum Ekle'].join('\n')
const SIZINTI = ['Daha fazla oku', 'Yorum Ekle', 'Yorum yapıldı', 'İlk yorum yapan',
  'Kurgu Öğrenci Bir', 'Uydurma Öğrenci İki', 'Deneme Öğrenci Üç',
  'çok güzel olmuş', 'harika bir etkinlik', 'ben de katılacağım']

test('Ders İçerikleri ham portal süsünü ve başka çocukların yorumlarını göstermez', async ({ page }) => {
  await page.route('**/api/schedule', r => r.fulfill(json({
    weeks: [], latest: { week_label: '15-19 Eylül', schedule: { headers: ['Saat', 'Pazartesi'], rows: [['08:30', 'Matematik']] } },
    today: null,
  })))
  await page.route('**/api/content', r => r.fulfill(json({
    Genel: { tab_id: 'tab_genel', text: GENEL_KART, cards: [GENEL_KART, YALNIZ_YORUM], items: [] },
  })))
  await page.route('**/api/content/weeks', r => r.fulfill(json({ weeks: {}, current: '' })))
  await page.route('**/api/health', r => r.fulfill(json({
    timestamp: '', success: true, scrape_errors: [], duration_seconds: 1,
  })))
  await page.goto('/dersler')
  // Prove the school post rendered before asserting what is absent.
  await expect(page.getByText('Okulumuzda Bilim Şenliği Başlıyor').first()).toBeVisible()
  // textContent, not innerText: closed accordion bodies must be clean too.
  const metin = (await page.locator('body').textContent()) ?? ''
  for (const s of SIZINTI) expect(metin, s).not.toContain(s)
})
```

- [ ] **Step 2: Kırmızı olduğunu gör**

Run: `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri/dashboard && npm run build; echo "build çıkış: $?"` ardından `env -u ANTHROPIC_API_KEY TEDY_E2E_PORT=8297 DASHBOARD_SECRET_KEY=yerel-test-anahtari-portal-ekleri npx playwright test dersler-portal-susu`
Expected: FAIL — metin "Daha fazla oku" / "Kurgu Öğrenci Bir" içeriyor.

- [ ] **Step 3: Temizleyicinin TS portu**

`dashboard/src/utils/portalSusu.ts`:

```ts
// A port of src/portal_susu.py `temiz_metin`, kept rule for rule: the API
// already serves course content clean, and this is the page's own defence if
// raw scraped text ever reaches it. Between "Daha fazla oku" and "Yorum Ekle"
// the portal renders other children's names and comments; a blank line does
// not end the block and an unclosed block runs to the end of the text.

const YORUM_BASI = 'Daha fazla oku'
const YORUM_SONU = 'Yorum Ekle'
const SUS = /^(?:Daha fazla oku|Yorum Ekle|İlk yorum yapan sen olmak ister misin\?|\d+ Yorum yapıldı!)$/

export function portalSusunuAyikla(metin: string): string {
  const satirlar: string[] = []
  let yorumda = false
  for (const ham of (metin ?? '').split('\n')) {
    const s = ham.split(/\s+/).filter(Boolean).join(' ')
    if (yorumda) {
      if (s === YORUM_SONU) yorumda = false
      continue
    }
    if (s === YORUM_BASI) {
      yorumda = true
      continue
    }
    if (SUS.test(s)) continue
    if (!s) {
      if (satirlar.length > 0 && satirlar[satirlar.length - 1]) satirlar.push('')
      continue
    }
    satirlar.push(s)
  }
  return satirlar.join('\n').trim()
}
```

- [ ] **Step 4: Bileşen**

`CourseContent.tsx` içe aktarmalara:

```tsx
import { portalSusunuAyikla } from '../utils/portalSusu'
```

`parseCard`'ın ilk satırı:

```tsx
function parseCard(card: string): ParsedCard {
  const temiz = portalSusunuAyikla(card)
  const lines = temiz.split('\n').map(l => l.trim()).filter(Boolean)

  // Extract week number
  const weekMatch = temiz.match(/(\d+)\.\s*HAFTA/i)
```

ve dönüş:

```tsx
  return { raw: temiz, weekNum, teacher, date, body: bodyLines.join('\n') }
```

Birleştirme döngüsünün başı (`for (const [rawName, content] of Object.entries(kaynak)) {` içinde, `if (!content) continue` altına):

```tsx
    // Defence in depth (plan 2026-09-28): portal chrome and comment blocks
    // are dropped before anything below reads text, cards or items.
    const temizText = portalSusunuAyikla(content.text || '')
    const temizCards = (content.cards || []).map(portalSusunuAyikla).filter(Boolean)
    const temizItems = (content.items || [])
      .map(x => (typeof x === 'string' ? portalSusunuAyikla(x) : x))
      .filter(x => x !== '')
```

ve döngüdeki `content.text` / `content.cards` / `content.items` kullanımlarını bu üçüyle değiştir:

```tsx
    if (!existing) {
      mergedCourses.set(normalized, {
        ...content,
        text: temizText,
        cards: [...temizCards],
        items: [...temizItems],
      })
      continue
    }

    const mergedText = [existing.text, temizText].filter(Boolean).join('\n\n').trim()
    const mergedCards = [...(existing.cards || []), ...temizCards]
    const mergedItems = [...(existing.items || []), ...temizItems]
```

- [ ] **Step 5: Lint, build, e2e**

Run: `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri/dashboard && npm run lint; echo "lint çıkış: $?"` → `0`.
Run: `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri/dashboard && npm run build; echo "build çıkış: $?"` → `0`.
Run (Bash timeout 600000): `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri/dashboard && env -u ANTHROPIC_API_KEY TEDY_E2E_PORT=8297 DASHBOARD_SECRET_KEY=yerel-test-anahtari-portal-ekleri npx playwright test dersler-portal-susu dersler dersler-haftalar gorsel-regresyon aria-yapisi`
Expected: PASS; görsel/aria değişmemeli (kırmızıysa fark okuma yordamı).

- [ ] **Step 6: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && test "$(git branch --show-current)" = feat/portal-ekleri && echo dal-dogru
git add dashboard/src/utils/portalSusu.ts dashboard/src/components/CourseContent.tsx dashboard/tests/e2e/dersler-portal-susu.spec.ts
git commit -m "$(cat <<'EOF'
Ders İçerikleri portal süsünü kendisi de ayıklar (savunma)

src/portal_susu.py'nin kural kural TS portu; metin, kart ve maddeler
her şeyden önce temizlenir, parseCard da temiz metinle çalışır.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Görev 13: CLAUDE.md ve tam doğrulama

> **Sıra:** bu görev Görev 14 ve 15'ten **sonra** koşar (bkz. "Uygulama sırası"); CLAUDE.md metinleri ve doğrulama OCR'u içerir.

**Files:**
- Modify: `CLAUDE.md` (Commands bloğu, Deployment "Cron" maddesi, Core Modules tablosu, Data Flow, Key Patterns → Scraping & Data, Dashboard asistan maddeleri)

**Interfaces:**
- Consumes: Görev 1–12'nin adları ve sayıları.
- Produces: belge.

- [ ] **Step 1: Komut**

`CLAUDE.md` Commands bloğunda `python src/scrape_sebitv_interactive.py …` satırının altına:

```bash
flock -n output/.sync.lock .venv/bin/python -m src.portal_ekleri_indir --sure 300 --bayt-mb 250 --indeksle  # portal attachments by hand (the sync does this itself, in its budget)
```

- [ ] **Step 2: Cron maddesi**

Deployment → **Cron** maddesinin sonuna (son cümle "…backed up in `output/crontab_yedek/`." sonrasına):

```
Portal attachments download inside the same run and under the same lock — after every scraper, before `health.json` and the reindex — in a budget of `min(180 s, start + 600 − 150 − now)` and 250 MB (`TEDY_EK_SURE_BUTCESI`, `TEDY_EK_BAYT_BUTCESI_MB`); under 15 s the step is skipped, and `health.json` carries its summary as `ekler`. Measured 2026-09-28 over 40 runs: p50 244 s, longest 393 s. OCR of scanned attachments runs inside that same budget; the reindex after it gives OCR 45 s per indexer (`ASSISTANT_OCR_SURE`, two indexers), inside the 150 s reserve.
```

- [ ] **Step 3: Modüller ve veri akışı**

Core Modules tablosunda `src/ocr_pdf_to_md.py` satırının altına:

```
| `src/portal_susu.py` | Portal UI residue — "Daha fazla oku … Yorum Ekle" comment blocks (other children's names), "N Yorum yapıldı!", "İlk yorum yapan…" — removed in one place; used by the scraper, run_sync's week merge, the API boundary and the index (TS port `dashboard/src/utils/portalSusu.ts`) |
| `src/portal_ekleri.py` | Attachment links: classify, stable id (sha256 of the canonical URL), download URL per host, collector over `scraped_data.json`, `EkDeposu` (copies + tracker), `ek_ozeti` payloads |
| `src/portal_ekleri_indir.py` | Attachment downloads inside `run_sync` (budgeted, resumable, HTML never stored, 300 MB cap), one-time text extraction to `<id>.txt`, CLI |
| `src/ocr_katmani.py` | OCR for PDF pages without a text layer: `pdftoppm` → Claude Haiku 4.5 vision (Markdown) under a 10 USD/month ledger, Tesseract fallback, per-page cache, engine + confidence per page |
```

Data Flow bloğunda `SEBİTV …` satırının altına:

```
Portal ekleri → portal_ekleri_indir.py (inside run_sync, budgeted) → content/portal-ekleri/<id>.<ext> + <id>.txt + <id>.meta.json, output/portal_ekleri.json → /api/ekler/<id>, BM25 (<id>.txt only), ek_oku
```

- [ ] **Step 4: Temel desenler**

Key Patterns → Scraping & Data'da **Ek sayfalar** maddesinin altına iki madde:

```
- **Portal attachments** (plan `docs/superpowers/plans/2026-09-28-portal-ekleri.md`): every attachment link in the scrape — homework `detail.attachments`, `ek_sayfalar.documents`, announcements' `<column>_url`, plus a generic scan of every other string for file-looking links — is collected by `src/portal_ekleri.py` under a stable id (first 16 hex of sha256 of the canonical URL: Drive's preview/view/open/uc collapse to `/file/d/<id>`, SharePoint drops `?e=`) and fetched by `src/portal_ekleri_indir.py`: SharePoint with `download=1`, Drive `uc?export=download` (its virus-scan confirm page is passed through its download form), Docs/Slides/Sheets `/export?format=pdf`, a portal-hosted file with the driver's cookies scoped to the portal's own domain. Measured 2026-09-28 without a login: SharePoint 4 of 5 PDFs (112 and 101 MB among them), the fifth a login wall; Drive 4 of 4. Rules: streamed into `content/portal-ekleri/.parca/<id>.part`, renamed atomically to `<id><ext>`; type from the magic bytes (unknown → `.bin`); a web page where a file was expected is never stored — `erisilemedi` with a reason; over 300 MB → `cok_buyuk`; a download that runs out of the run's budget keeps its part file and resumes with `Range` next run. Statuses `bekliyor`/`indirildi`/`erisilemedi`/`cok_buyuk`/`hata`/`baglanti` (a link that is not one file — a video, a folder — never downloaded); `hata` retries next run, `erisilemedi` after 24 h, `cok_buyuk`/`baglanti` never. Text is extracted once at download time into `<id>.txt` (header `PORTAL EKİ · <name> · <context> · <course>`) with a `<id>.meta.json` sidecar; a scanned page is read by the OCR layer inside the same budget (see the OCR bullet); a scan read part-way is `text: "bekliyor"` with `ocr_ilerleme` and continues next run, and a PDF with no readable text even after OCR is `text: "yok"`. Tracker `output/portal_ekleri.json` (`url, id, name, type, size, sha256, source{section,item,title,course}, status, reason, fetched_at` …). `GET /api/ekler/<id>` serves the copy (full role, readers 403 by default-deny, `send_file(conditional=True)` so Range → 206, known types inline, `.bin` as attachment, `nosniff`); `/api/homework`, `/api/pages` and `/api/announcements` give each attachment `{name, url, id, tedyUrl, status[, reason]}` and `components/patterns/EkBaglantisi.tsx` renders it: TEDY's copy first, "Kaynağında aç" secondary, "İndirilemedi — kaynağında aç" without a copy. Copies are gitignored (`content/portal-ekleri/`).
- **Portal residue and other children's comments**: the portal renders a post's comment block — per comment another child's name, a like count and the comment — between "Daha fazla oku" and "Yorum Ekle"; measured 445 blocks on 2026-09-28, mostly in the "Genel" school feed. `src/portal_susu.py` drops it and the chrome lines; a blank line does not end a block and an unclosed block runs to the end of the text (87 cards end at "Daha fazla oku"; the scraper cuts a tab at 8,000 chars). It runs in `scrape_all` (before the length caps), in `run_sync._icerik_birlestir` (so earlier weeks are cleaned too), at the API boundary (`/api/content`, `/api/content/weeks`, homework descriptions, `/api/pages`, `/api/announcements`) and in the BM25 text; `CourseContent.tsx` applies the TS port as defence. School posts stay; their comment blocks go.
```

- [ ] **Step 5: Asistan maddesi**

**Asistan ve ödevler** maddesinin altına:

```
- **Asistan ve portal ekleri** (plan `docs/superpowers/plans/2026-09-28-portal-ekleri.md`): the BM25 index takes only `content/portal-ekleri/<id>.txt` (binaries, `.meta.json`, `.parca/` and `output/portal_ekleri.json` excluded — the binaries would be re-extracted outside the sync's budget), and those files lead `content/` in discovery. A hit is labelled "<ek adı> · <ödev başlığı>" from the sidecar (`McpRegistry._yerel_etiket`), never by path. `ek_oku(id, sayfa)` pages an attachment's text in ≤ 3,300-character text pages inside the 3,900 body budget, says which PDF pages a text page spans, and is honest about every state: not downloaded (with the reason), no text even after OCR, OCR under way ("12/40 sayfa okundu"), a type whose text is not read, text not extracted yet; an OCR'd page keeps its `[PDF s.N · OCR …]` line, and "OCR, güven düşük" pages come with a note not to treat them as certain. `odev_listesi` names each homework's attachments as `Ekler: <ad> [ek:<id>]` (or `· indirilemedi`, or `(bağlantı)`); the ödevler paragraph of `_fmt_scraped_data` carries attachment names. `FileAdapters` reads `.docx` with the stdlib (`zipfile` + `word/document.xml`). The runtime always wires `EkDeposu`, so 27 tools are routed, each exactly once (`test_system_prompt_routing_names_every_declared_tool_exactly_once`).
```

- [ ] **Step 6: Tam Python paketi**

Run (Bash timeout 600000): `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && DASHBOARD_SECRET_KEY=yerel-test-anahtari-portal-ekleri .venv/bin/python -m pytest -q -p no:cacheprovider 2>&1 | tail -15`
Expected: Görev 1 Step 1'deki başlangıçla aynı kırmızılar (ya da hiç), yeni kırmızı yok; geçen sayısı yeni testler kadar artmış.

Run: `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && DASHBOARD_SECRET_KEY=yerel-test-anahtari-portal-ekleri unshare -rn .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_portal_susu.py tests/test_portal_susu_uygulama.py tests/test_portal_ekleri.py tests/test_portal_ekleri_indir.py tests/test_portal_ekleri_esitle.py tests/test_portal_ekleri_sync.py tests/test_portal_ekleri_api.py tests/test_portal_ekleri_indeks.py tests/test_assistant_docx.py tests/test_assistant_ek_oku.py tests/test_ocr_katmani.py tests/test_ocr_baglanti.py`
Expected: PASS ağsız ad alanında (hiçbir yeni test ağa dokunmaz; OCR testleri yalnız sahte okuyucu ve sahte Tesseract kullanır, gerçek `pdfinfo`/`pdftotext`/`pdftoppm` yereldir).

Run (ücretli çağrı olmadığının kanıtı): `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && grep -n "ClaudeGorselOkuyucu()" tests/*.py; ls output/ocr_defteri.json 2>&1`
Expected: tek eşleşme `tests/test_ocr_katmani.py`'deki sahte Anthropic istemcili test; `output/ocr_defteri.json` çalışma ağacında yok (hiçbir test gerçek defteri yazmadı).

- [ ] **Step 7: Pano paketi**

Run: `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri/dashboard && npm run lint; echo "lint çıkış: $?"` → `0`; `npm run build; echo "build çıkış: $?"` → `0`.
Run (Bash timeout 600000): `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri/dashboard && env -u ANTHROPIC_API_KEY TEDY_E2E_PORT=8297 DASHBOARD_SECRET_KEY=yerel-test-anahtari-portal-ekleri npx playwright test`
Expected: bütün Chromium spec'leri yeşil (görsel ve aria dahil, güncellemesiz; `suite-hygiene` yeni spec'lerde sabit bekleme bulmaz). `capraz-tarayici`'nin webkit/firefox koşularında mesajı `Executable doesn't exist` olan kırmızılar ortamdır (CLAUDE.md: bu tarayıcılar sabitlenmiş kurulumda yok), gerileme değildir; rapora ayrı yaz. Görsel farkta fark okuma yordamı.

- [ ] **Step 8: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && test "$(git branch --show-current)" = feat/portal-ekleri && echo dal-dogru
git add CLAUDE.md
git commit -m "$(cat <<'EOF'
CLAUDE.md: portal ekleri, portal süsü ve ek_oku belgelendi

Veri akışı, çekirdek modüller, cron bütçesi, temel desenler ve asistan
araçları güncellendi; elle indirme komutu eklendi.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Görev 14: OCR katmanı, sayfa önbelleği, aylık tavan defteri ve Tesseract düşüşü

**Files:**
- Create: `src/ocr_katmani.py`
- Create: `tests/sahte_ocr.py`
- Test: `tests/test_ocr_katmani.py`

**Interfaces:**
- Consumes: `src.claude_api.istemci(timeout: float, max_retries: int) -> anthropic.Anthropic`, `src.claude_api.metin(yanit) -> str`, `src.claude_api.okunur_ad(model) -> str`; `src.json_utils.atomic_json_dump`; poppler `pdfinfo`/`pdftotext`/`pdftoppm`; `pytesseract` + Pillow (production venv'de var, ölçüldü).
- Produces (`src.ocr_katmani`):
  - Sabitler: `OCR_VARSAYILAN_MODEL = "claude-haiku-4-5"`, `GIRDI_USD_MTOK = 1.00`, `CIKTI_USD_MTOK = 5.00`, `ISTEM_SURUMU = "1"`, `ISTEM`, `MOTOR_TESSERACT = "tesseract-tur+eng"`, `MOTOR_BOS = "bos"`, `AYLIK_TAVAN_USD` (env `TEDY_OCR_AYLIK_USD`, varsayılan 10), `UZUN_KENAR = 1568`, `CIKTI_SINIRI = 4096`, `SAYFA_TAHMINI_USD`, `DUSUK_GUVEN = 0.6`, `CLAUDE_EN_AZ_SURE = 15.0`, `TESSERACT_EN_AZ_SURE = 10.0`, `ONBELLEK = PurePosixPath("output/ocr_onbellek")`, `DEFTER = PurePosixPath("output/ocr_defteri.json")`.
  - `class OcrHatasi(RuntimeError)`.
  - `pdf_sayfa_sayisi(pdf, sure) -> int`, `pdf_sayfa_metinleri(pdf, sure) -> list[str]`, `metin_katmani_var(metin: str) -> bool`, `sayfa_gorseli(pdf, sayfa, sure) -> bytes` (JPEG), `bos_sayfa_mi(jpeg: bytes) -> bool`.
  - `@dataclass GorselOkuma(markdown: str, okunabilirlik: str, girdi_token: int, cikti_token: int, kesildi: bool = False, reddedildi: bool = False)`.
  - `class ClaudeGorselOkuyucu(model: str | None = None)`: `.model`, `.motor -> "claude:<model>"`, `oku(jpeg: bytes, sure: float) -> GorselOkuma`. Bir okuyucu, bu iki üyeyi (`motor`, `oku`) taşıyan her nesnedir; testler sahtesini verir.
  - `tesseract_verisinden(veri: dict) -> tuple[str, float]`, `tesseract_oku(jpeg: bytes, sure: float) -> tuple[str, float]`.
  - `@dataclass SayfaOkumasi(sayfa: int, metin: str, motor: str, guven: float, usd: float = 0.0)` + `dusuk_guven: bool`, `etiket() -> str`.
  - `class OcrOnbellegi(dizin)`: `al(sha, sayfa, motor) -> SayfaOkumasi | None`, `koy(sha, okuma) -> None`.
  - `class OcrDefteri(yol, tavan=AYLIK_TAVAN_USD, simdi=datetime.now)`: `harcanan() -> float`, `izin_var() -> bool`, `yaz(motor, girdi_token, cikti_token) -> float`.
  - `@dataclass PdfOcrSonucu(metin: str, toplam_sayfa: int, metinsiz: int, ocr_sayfalari: list[int], eksik: list[int], dusuk_guvenli: list[int])` + `ilerleme -> "okunan/toplam"`. `metin` sayfaları `chr(12)` ile birleştirir (pdftotext gibi); OCR'lı her sayfa `SayfaOkumasi.etiket()` satırıyla başlar.
  - `class OcrKatmani(proje_koku, okuyucu=None, tesseract=tesseract_oku, saat=time.monotonic, simdi=datetime.now, tavan=None)`: `.saat`, `.defter`, `.onbellek`, `.okuyucu`, `pdf_oku(pdf, son_an: float, sayfa_metinleri: list[str] | None = None) -> PdfOcrSonucu`. `son_an` `.saat()` ile aynı saattedir.
- Produces (`tests.sahte_ocr`): `MARKDOWN`, `Saat`, `SahteOkuyucu`, `SahteTesseract`, `taranmis_pdf(yol, icerikli=1, bos=0) -> Path` (Görev 15 kullanır).

- [ ] **Step 1: Sahte OCR yardımcılarını yaz**

`tests/sahte_ocr.py`:

```python
"""Fakes for the OCR layer (plan 2026-09-28-portal-ekleri, Görev 14–15).

No test calls the paid API or spends ~20 s in real Tesseract (measured
2026-09-28 per A4 page at 150 dpi). A scanned PDF is made with Pillow: image
pages, no text layer — exactly what pdftotext returns nothing for.
"""
from __future__ import annotations

from pathlib import Path

from src.ocr_katmani import GorselOkuma

MARKDOWN = "# Soru 1\n\nKesirleri topla: $x^2 + y^2$\n\n| a | b |\n|---|---|\n| 1 | 2 |"


class Saat:
    """A monotonic clock that moves only when a test moves it."""

    def __init__(self, an: float = 0.0):
        self.an = an

    def __call__(self) -> float:
        return self.an


class SahteOkuyucu:
    """Stands in for ClaudeGorselOkuyucu: records calls, returns a fixed page."""

    motor = "claude:claude-haiku-4-5"

    def __init__(self, markdown: str = MARKDOWN, okunabilirlik: str = "yuksek", girdi: int = 2400,
                 cikti: int = 300, hata: Exception | None = None, reddet: bool = False,
                 saat: Saat | None = None, adim: float = 0.0):
        self.markdown, self.okunabilirlik = markdown, okunabilirlik
        self.girdi, self.cikti = girdi, cikti
        self.hata, self.reddet = hata, reddet
        self.saat, self.adim = saat, adim
        self.cagrilar: list[int] = []

    def oku(self, jpeg: bytes, sure: float) -> GorselOkuma:
        self.cagrilar.append(len(jpeg))
        if self.saat is not None:
            self.saat.an += self.adim
        if self.hata is not None:
            raise self.hata
        return GorselOkuma(markdown="" if self.reddet else self.markdown,
                           okunabilirlik=self.okunabilirlik, girdi_token=self.girdi,
                           cikti_token=self.cikti, kesildi=False, reddedildi=self.reddet)


class SahteTesseract:
    def __init__(self, metin: str = "Soru 1 kesirleri topla", guven: float = 0.45):
        self.metin, self.guven = metin, guven
        self.cagrilar = 0

    def __call__(self, jpeg: bytes, sure: float) -> tuple[str, float]:
        self.cagrilar += 1
        return self.metin, self.guven


def taranmis_pdf(yol: Path, icerikli: int = 1, bos: int = 0) -> Path:
    """`icerikli` drawn pages, then `bos` white ones; no text layer at all."""
    from PIL import Image, ImageDraw
    sayfalar = []
    for i in range(icerikli):
        img = Image.new("RGB", (620, 877), "white")
        cizim = ImageDraw.Draw(img)
        cizim.rectangle([40, 40, 580, 120], outline="black", width=3)
        cizim.text((60, 70), f"Soru {i + 1}: Kesirleri topla.", fill="black")
        for y in range(160, 800, 40):
            cizim.line([60, y, 560, y], fill="black", width=2)
        sayfalar.append(img)
    sayfalar += [Image.new("RGB", (620, 877), "white") for _ in range(bos)]
    sayfalar[0].save(yol, "PDF", save_all=True, append_images=sayfalar[1:], resolution=72)
    return Path(yol)
```

- [ ] **Step 2: Başarısız testi yaz**

`tests/test_ocr_katmani.py`:

```python
"""OCR layer (plan 2026-09-28-portal-ekleri, Görev 14): Claude Haiku 4.5 vision per
textless page, a per-page cache, a monthly USD cap and the Tesseract fallback.
The paid API is never called: the reader is tests/sahte_ocr.SahteOkuyucu, and
ClaudeGorselOkuyucu's own test runs against a fake Anthropic client."""
from datetime import datetime
from types import SimpleNamespace

import pytest

import src.ocr_katmani as ocr
from src.ocr_katmani import (AYLIK_TAVAN_USD, SAYFA_TAHMINI_USD, ClaudeGorselOkuyucu, OcrDefteri,
                             OcrKatmani, pdf_sayfa_metinleri, tesseract_verisinden)
from tests.sahte_ocr import MARKDOWN, Saat, SahteOkuyucu, SahteTesseract, taranmis_pdf

EYLUL = datetime(2026, 9, 28, 10, 0)
EKIM = datetime(2026, 10, 1, 9, 0)
FF = chr(12)


def _katman(kok, okuyucu, tesseract=None, simdi=lambda: EYLUL, **kw):
    return OcrKatmani(kok, okuyucu=okuyucu, tesseract=tesseract or SahteTesseract(), simdi=simdi, **kw)


def test_taranmis_pdf_metin_katmani_tasimaz(tmp_path):
    pdf = taranmis_pdf(tmp_path / "t.pdf", icerikli=2, bos=1)
    assert [s.strip() for s in pdf_sayfa_metinleri(pdf, 30)] == ["", "", ""]


def test_metinsiz_sayfa_claude_ile_okunur_bos_sayfa_para_harcamaz(tmp_path):
    pdf = taranmis_pdf(tmp_path / "t.pdf", icerikli=1, bos=1)
    okuyucu = SahteOkuyucu()
    katman = _katman(tmp_path, okuyucu)
    sonuc = katman.pdf_oku(pdf, katman.saat() + 60)
    assert len(okuyucu.cagrilar) == 1                    # the white page cost nothing
    assert (sonuc.ocr_sayfalari, sonuc.eksik, sonuc.metinsiz, sonuc.ilerleme) == ([1], [], 2, "2/2")
    ilk, ikinci = sonuc.metin.split(FF)
    assert ilk == "[PDF s.1 · OCR · Claude Haiku 4.5 · güven %90]\n" + MARKDOWN
    assert ikinci == ""
    assert katman.defter.harcanan() == pytest.approx((2400 * 1.0 + 300 * 5.0) / 1_000_000)


def test_bir_sayfa_bir_kez_okunur(tmp_path):
    pdf = taranmis_pdf(tmp_path / "t.pdf")
    okuyucu = SahteOkuyucu()
    katman = _katman(tmp_path, okuyucu)
    katman.pdf_oku(pdf, katman.saat() + 60)
    harcanan = katman.defter.harcanan()
    ikinci = katman.pdf_oku(pdf, katman.saat() + 60)
    assert len(okuyucu.cagrilar) == 1 and katman.defter.harcanan() == harcanan
    assert MARKDOWN in ikinci.metin


def test_istem_surumu_degisince_yeniden_okunur(tmp_path, monkeypatch):
    pdf = taranmis_pdf(tmp_path / "t.pdf")
    okuyucu = SahteOkuyucu()
    katman = _katman(tmp_path, okuyucu)
    katman.pdf_oku(pdf, katman.saat() + 60)
    monkeypatch.setattr(ocr, "ISTEM_SURUMU", "2")
    katman.pdf_oku(pdf, katman.saat() + 60)
    assert len(okuyucu.cagrilar) == 2


def test_aylik_tavanda_tesseract_a_duser_defter_degismez(tmp_path):
    assert AYLIK_TAVAN_USD == 10.0
    pdf = taranmis_pdf(tmp_path / "t.pdf")
    okuyucu, tesseract = SahteOkuyucu(), SahteTesseract()
    katman = _katman(tmp_path, okuyucu, tesseract)
    katman.defter.yaz("claude:claude-haiku-4-5", 10_000_000, 0)      # 10.00 USD spent this month
    assert not katman.defter.izin_var()
    sonuc = katman.pdf_oku(pdf, katman.saat() + 60)
    assert okuyucu.cagrilar == [] and tesseract.cagrilar == 1
    assert sonuc.metin.startswith("[PDF s.1 · OCR, güven düşük · Tesseract]\n")
    assert sonuc.dusuk_guvenli == [1]
    assert katman.defter.harcanan() == pytest.approx(10.0)


def test_tavan_bir_sayfanin_en_kotu_maliyetine_yer_birakir(tmp_path):
    defter = OcrDefteri(tmp_path / "d.json", tavan=10.0, simdi=lambda: EYLUL)
    defter.yaz("m", int((10.0 - SAYFA_TAHMINI_USD) * 1_000_000) + 1, 0)
    assert not defter.izin_var()
    assert OcrDefteri(tmp_path / "d.json", tavan=10.0, simdi=lambda: EKIM).izin_var()   # a new month


def test_defter_olcumu_ay_ay_kaydeder(tmp_path):
    defter = OcrDefteri(tmp_path / "ocr_defteri.json", simdi=lambda: EYLUL)
    assert defter.yaz("claude:claude-haiku-4-5", 2400, 300) == pytest.approx(0.0039)
    import json
    ay = json.loads((tmp_path / "ocr_defteri.json").read_text(encoding="utf-8"))["aylar"]["2026-09"]
    assert ay == {"usd": pytest.approx(0.0039), "sayfa": 1, "girdi_token": 2400, "cikti_token": 300}


def test_api_hatasinda_tesseract_a_duser_para_yazilmaz(tmp_path):
    pdf = taranmis_pdf(tmp_path / "t.pdf")
    okuyucu, tesseract = SahteOkuyucu(hata=RuntimeError("529 overloaded")), SahteTesseract(guven=0.8)
    katman = _katman(tmp_path, okuyucu, tesseract)
    sonuc = katman.pdf_oku(pdf, katman.saat() + 60)
    assert len(okuyucu.cagrilar) == 1 and tesseract.cagrilar == 1
    assert sonuc.metin.startswith("[PDF s.1 · OCR · Tesseract · güven %80]\n")
    assert katman.defter.harcanan() == 0.0


def test_ret_kullanimini_yazar_ve_tesseract_a_duser(tmp_path):
    pdf = taranmis_pdf(tmp_path / "t.pdf")
    okuyucu, tesseract = SahteOkuyucu(reddet=True), SahteTesseract()
    katman = _katman(tmp_path, okuyucu, tesseract)
    katman.pdf_oku(pdf, katman.saat() + 60)
    assert tesseract.cagrilar == 1 and katman.defter.harcanan() > 0


def test_yeni_ay_dusuk_guvenli_tesseract_sayfasini_claude_ile_yeniler(tmp_path):
    pdf = taranmis_pdf(tmp_path / "t.pdf")
    an = {"t": EYLUL}
    okuyucu, tesseract = SahteOkuyucu(), SahteTesseract(guven=0.45)
    katman = _katman(tmp_path, okuyucu, tesseract, simdi=lambda: an["t"])
    katman.defter.yaz("claude:claude-haiku-4-5", 10_000_000, 0)
    katman.pdf_oku(pdf, katman.saat() + 60)
    an["t"] = EKIM
    sonuc = katman.pdf_oku(pdf, katman.saat() + 60)
    assert len(okuyucu.cagrilar) == 1 and tesseract.cagrilar == 1
    assert "Claude Haiku 4.5" in sonuc.metin and sonuc.dusuk_guvenli == []


def test_yuksek_guvenli_tesseract_sonucu_kalir(tmp_path):
    pdf = taranmis_pdf(tmp_path / "t.pdf")
    an = {"t": EYLUL}
    okuyucu, tesseract = SahteOkuyucu(), SahteTesseract(guven=0.85)
    katman = _katman(tmp_path, okuyucu, tesseract, simdi=lambda: an["t"])
    katman.defter.yaz("claude:claude-haiku-4-5", 10_000_000, 0)
    katman.pdf_oku(pdf, katman.saat() + 60)
    an["t"] = EKIM
    katman.pdf_oku(pdf, katman.saat() + 60)
    assert okuyucu.cagrilar == [] and tesseract.cagrilar == 1


def test_sure_dolunca_kalan_sayfa_sonraki_turda_surer(tmp_path):
    pdf = taranmis_pdf(tmp_path / "t.pdf", icerikli=3)
    saat = Saat()
    okuyucu, tesseract = SahteOkuyucu(saat=saat, adim=10.0), SahteTesseract()
    katman = _katman(tmp_path, okuyucu, tesseract, saat=saat)
    sonuc = katman.pdf_oku(pdf, son_an=25.0)              # pages 1–2 fit; 5 s left for page 3
    assert sonuc.eksik == [3] and sonuc.ilerleme == "2/3" and tesseract.cagrilar == 0
    sonuc = katman.pdf_oku(pdf, son_an=saat() + 100)
    assert sonuc.eksik == [] and len(okuyucu.cagrilar) == 3   # pages 1–2 came from the cache


def test_claude_okuyucusu_istegi_ve_okunabilirligi(monkeypatch):
    gonderilen, alinan = {}, {}

    def yanit(stop="end_turn", metin=MARKDOWN + "\n<!-- okunabilirlik: yuksek -->"):
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=metin)], stop_reason=stop,
                               usage=SimpleNamespace(input_tokens=2412, output_tokens=180))
    cevaplar = [yanit(), yanit(stop="max_tokens", metin="# Yarım"), yanit(stop="refusal", metin="")]

    class Istemci:
        def __init__(self):
            self.messages = SimpleNamespace(create=self.create)

        def create(self, **kw):
            gonderilen.update(kw)
            return cevaplar.pop(0)

    def istemci(timeout, max_retries=1):
        alinan.update(timeout=timeout, max_retries=max_retries)
        return Istemci()
    monkeypatch.setattr("src.claude_api.istemci", istemci)
    monkeypatch.delenv("OCR_CLAUDE_MODEL", raising=False)
    okuyucu = ClaudeGorselOkuyucu()
    bir = okuyucu.oku(b"jpeg-baytlari", 40.0)
    assert (bir.markdown, bir.okunabilirlik, bir.girdi_token, bir.cikti_token) == (MARKDOWN, "yuksek", 2412, 180)
    assert gonderilen["model"] == "claude-haiku-4-5" and okuyucu.motor == "claude:claude-haiku-4-5"
    gorsel = gonderilen["messages"][0]["content"][0]
    assert gorsel["type"] == "image" and gorsel["source"]["media_type"] == "image/jpeg"
    assert "thinking" not in gonderilen and "temperature" not in gonderilen
    assert gonderilen["max_tokens"] == ocr.CIKTI_SINIRI
    assert alinan == {"timeout": 40.0, "max_retries": 0}
    iki = okuyucu.oku(b"x", 40.0)
    assert iki.kesildi and iki.okunabilirlik == "dusuk" and iki.markdown == "# Yarım"
    assert okuyucu.oku(b"x", 40.0).reddedildi


def test_tesseract_verisinden_satirlar_ve_guven():
    veri = {"text": ["", "Soru", "1", "", "Kesirleri", "topla"],
            "conf": ["-1", "90", "80", "-1", "40", "30"],
            "block_num": [1, 1, 1, 2, 2, 2], "par_num": [1, 1, 1, 1, 1, 1],
            "line_num": [0, 1, 1, 0, 1, 1]}
    metin, guven = tesseract_verisinden(veri)
    assert metin == "Soru 1\n\nKesirleri topla"
    assert guven == pytest.approx(0.6)
```

- [ ] **Step 3: Kırmızı olduğunu gör**

Run: `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && DASHBOARD_SECRET_KEY=yerel-test-anahtari-portal-ekleri .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_ocr_katmani.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.ocr_katmani'`.

- [ ] **Step 4: Katmanı yaz**

`src/ocr_katmani.py`:

```python
"""OCR for PDF pages without a text layer (plan 2026-09-28-portal-ekleri, Görev 14).

pdftotext returns nothing for a scanned page: measured 2026-09-28, three
chunks of the live index were "pdf_no_text" (content/yabanci-dil), and a
scanned homework attachment would read "metin katmanı yok". Each such page is
rendered with pdftoppm and read by Claude Haiku 4.5's vision into Markdown
(headings, tables and formulas kept). A page is read once — cached by (file
sha256, page, engine, prompt version). Spend is held under a monthly cap in a
ledger fed by each response's `usage`; at the cap, on an API error or a
refusal, the page falls back to local Tesseract (tur+eng). Every page carries
its engine and a confidence estimate, and a low one is labelled for the model.
"""
from __future__ import annotations

import base64
import fcntl
import hashlib
import io
import json
import logging
import os
import re
import subprocess
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterator

from src.json_utils import atomic_json_dump

logger = logging.getLogger(__name__)

OCR_VARSAYILAN_MODEL = "claude-haiku-4-5"
# Anthropic first-party list price of Claude Haiku 4.5, USD per million tokens
# (claude-api reference, cached 2026-06-24). An OCR_CLAUDE_MODEL override must
# bring its own prices here, or the ledger under-counts.
GIRDI_USD_MTOK = 1.00
CIKTI_USD_MTOK = 5.00
# Part of every cache key: a new prompt re-reads pages; a new engine too.
ISTEM_SURUMU = "1"
MOTOR_TESSERACT = "tesseract-tur+eng"
MOTOR_BOS = "bos"
AYLIK_TAVAN_USD = float(os.environ.get("TEDY_OCR_AYLIK_USD", "10"))
# Claude downsizes an image whose long edge passes ~1568 px, so rendering
# bigger buys nothing but render time: measured 2026-09-28 on page 5 of a
# 70 MB PDF, 150 dpi rendered 1214x1650 in 3.2 s and 200 dpi 1619x2200 in
# 5.3 s. 1568 px is ~190 dpi on A4 and costs about w*h/750 ≈ 2,400 input tokens.
UZUN_KENAR = 1568
CIKTI_SINIRI = 4096
# One page's worst case: the image (≤ 1568²/750 ≈ 3,300 tokens) plus the
# prompt, rounded to 4,000 input tokens, and CIKTI_SINIRI output tokens.
# Claude is called only while this still fits under the cap.
SAYFA_TAHMINI_USD = (4000 * GIRDI_USD_MTOK + CIKTI_SINIRI * CIKTI_USD_MTOK) / 1_000_000
DUSUK_GUVEN = 0.6
# No new Claude call with less than this left (its timeout is the time left,
# no retries, so a call can overrun its deadline by at most one call); no
# Tesseract run with less than this left (~20 s a page measured at 150 dpi).
CLAUDE_EN_AZ_SURE = 15.0
TESSERACT_EN_AZ_SURE = 10.0
ONBELLEK = PurePosixPath("output/ocr_onbellek")
DEFTER = PurePosixPath("output/ocr_defteri.json")
_METIN_ESIGI = 20          # fewer non-space characters than this: no text layer
_BOS_SAPMA = 2.0           # grey-level stddev under this: a white page
_GUVEN = {"yuksek": 0.9, "orta": 0.7, "dusuk": 0.4}
_OKUNABILIRLIK = re.compile(r"\s*<!--\s*okunabilirlik:\s*(yuksek|orta|dusuk)\s*-->\s*$")

ISTEM = (
    "Bu görsel, bir okul belgesinin taranmış tek bir sayfası. Sayfadaki bütün metni, "
    "göründüğü sırayla ve olduğu gibi Markdown olarak yaz:\n"
    "- Başlıkları # ve ## ile, listeleri madde olarak, tabloları Markdown tablosu olarak koru.\n"
    "- Matematik ve fen ifadelerini LaTeX ile yaz ($...$ ya da $$...$$).\n"
    "- Metni özetleme, çevirme, düzeltme ya da tamamlama. Okuyamadığın yeri [okunamadı] diye işaretle.\n"
    "- Şekil ve fotoğrafları yalnız kısa bir notla an: [şekil: kısa açıklama].\n"
    "- Markdown'dan başka bir şey yazma. En son satıra, sayfanın ne kadar net okunduğunu şu "
    "biçimde ekle: <!-- okunabilirlik: yuksek --> (yuksek, orta ya da dusuk)."
)


class OcrHatasi(RuntimeError):
    """A page or file could not be rendered or measured; nothing is cached."""


def _sha256(yol: Path) -> str:
    h = hashlib.sha256()
    with yol.open("rb") as f:
        for blok in iter(lambda: f.read(1024 * 1024), b""):
            h.update(blok)
    return h.hexdigest()


def _kos(komut: list[str], sure: float) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(komut, capture_output=True, timeout=max(1.0, sure), check=False)
    except (subprocess.TimeoutExpired, OSError) as exc:
        raise OcrHatasi(f"{komut[0]}: {type(exc).__name__}") from exc


def pdf_sayfa_sayisi(pdf: Path, sure: float) -> int:
    proc = _kos(["pdfinfo", str(pdf)], sure)
    m = re.search(r"^Pages:\s+(\d+)", proc.stdout.decode("utf-8", "replace"), re.M)
    if proc.returncode != 0 or not m:
        raise OcrHatasi("pdfinfo sayfa sayısını okuyamadı")
    return int(m.group(1))


def pdf_sayfa_metinleri(pdf: Path, sure: float) -> list[str]:
    """One string per page, as pdftotext renders it (pages end in a form feed)."""
    n = pdf_sayfa_sayisi(pdf, sure)
    proc = _kos(["pdftotext", "-layout", str(pdf), "-"], sure)
    if proc.returncode != 0:
        raise OcrHatasi("pdftotext okuyamadı")
    sayfalar = proc.stdout.decode("utf-8", "replace").split(chr(12))
    return (sayfalar + [""] * n)[:n]


def metin_katmani_var(metin: str) -> bool:
    return len("".join(str(metin or "").split())) >= _METIN_ESIGI


def sayfa_gorseli(pdf: Path, sayfa: int, sure: float) -> bytes:
    """Page `sayfa` (1-based) as a JPEG whose long edge is UZUN_KENAR."""
    with tempfile.TemporaryDirectory() as dizin:
        kok = os.path.join(dizin, "sayfa")
        proc = _kos(["pdftoppm", "-f", str(sayfa), "-l", str(sayfa), "-scale-to", str(UZUN_KENAR),
                     "-jpeg", "-jpegopt", "quality=85", "-singlefile", str(pdf), kok], sure)
        yol = Path(kok + ".jpg")
        if proc.returncode != 0 or not yol.is_file():
            raise OcrHatasi("pdftoppm sayfayı çizemedi")
        return yol.read_bytes()


def bos_sayfa_mi(jpeg: bytes) -> bool:
    from PIL import Image, ImageStat
    with Image.open(io.BytesIO(jpeg)) as img:
        return ImageStat.Stat(img.convert("L")).stddev[0] < _BOS_SAPMA


@dataclass
class GorselOkuma:
    markdown: str
    okunabilirlik: str
    girdi_token: int
    cikti_token: int
    kesildi: bool = False
    reddedildi: bool = False


class ClaudeGorselOkuyucu:
    """One page image → Markdown, through src/claude_api.py with TEDY's key.

    No thinking and no temperature (Haiku 4.5 needs neither for transcription).
    Markdown rather than structured JSON output: a reply cut at CIKTI_SINIRI
    keeps the part it read, where a cut JSON would lose the page. The model
    rates its own reading on the last line; a cut reply is rated low."""

    def __init__(self, model: str | None = None):
        self.model = model or os.environ.get("OCR_CLAUDE_MODEL", "").strip() or OCR_VARSAYILAN_MODEL

    @property
    def motor(self) -> str:
        return f"claude:{self.model}"

    def oku(self, jpeg: bytes, sure: float) -> GorselOkuma:
        from src import claude_api
        istemci = claude_api.istemci(timeout=max(10.0, sure), max_retries=0)
        yanit = istemci.messages.create(
            model=self.model,
            max_tokens=CIKTI_SINIRI,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                             "data": base64.b64encode(jpeg).decode("ascii")}},
                {"type": "text", "text": ISTEM},
            ]}],
        )
        kullanim = getattr(yanit, "usage", None)
        durdu = str(getattr(yanit, "stop_reason", "") or "")
        metin = claude_api.metin(yanit)
        m = _OKUNABILIRLIK.search(metin)
        okunabilirlik = "dusuk" if durdu == "max_tokens" else (m.group(1) if m else "orta")
        return GorselOkuma(markdown=_OKUNABILIRLIK.sub("", metin).strip(), okunabilirlik=okunabilirlik,
                           girdi_token=int(getattr(kullanim, "input_tokens", 0) or 0),
                           cikti_token=int(getattr(kullanim, "output_tokens", 0) or 0),
                           kesildi=durdu == "max_tokens", reddedildi=durdu == "refusal")


def tesseract_verisinden(veri: dict[str, Any]) -> tuple[str, float]:
    """pytesseract's image_to_data dict → (text, mean word confidence 0..1).
    Lines keep their words; a new block or paragraph starts after a blank line."""
    satirlar: dict[tuple[Any, Any, Any], list[str]] = {}
    guvenler: list[float] = []
    for i, kelime in enumerate(veri.get("text") or []):
        kelime = str(kelime or "").strip()
        if not kelime:
            continue
        try:
            guven = float(veri["conf"][i])
        except (KeyError, IndexError, TypeError, ValueError):
            guven = -1.0
        if guven >= 0:
            guvenler.append(guven)
        anahtar = (veri["block_num"][i], veri["par_num"][i], veri["line_num"][i])
        satirlar.setdefault(anahtar, []).append(kelime)
    parcalar: list[str] = []
    onceki = None
    for (blok, par, _satir), kelimeler in satirlar.items():
        if onceki is not None and (blok, par) != onceki:
            parcalar.append("")
        parcalar.append(" ".join(kelimeler))
        onceki = (blok, par)
    return "\n".join(parcalar).strip(), (sum(guvenler) / len(guvenler) / 100.0 if guvenler else 0.0)


def tesseract_oku(jpeg: bytes, sure: float) -> tuple[str, float]:
    """The existing local path (FileAdapters' images use it too), tur+eng."""
    import pytesseract
    from PIL import Image
    with Image.open(io.BytesIO(jpeg)) as img:
        veri = pytesseract.image_to_data(img, lang=os.environ.get("ASSISTANT_OCR_LANG", "tur+eng"),
                                         output_type=pytesseract.Output.DICT, timeout=max(5, int(sure)))
    return tesseract_verisinden(veri)


@dataclass
class SayfaOkumasi:
    sayfa: int
    metin: str
    motor: str
    guven: float
    usd: float = 0.0

    @property
    def dusuk_guven(self) -> bool:
        return self.guven < DUSUK_GUVEN

    def etiket(self) -> str:
        """The line the model reads above an OCR'd page."""
        if self.motor.startswith("claude:"):
            from src.claude_api import okunur_ad
            ad = okunur_ad(self.motor.split(":", 1)[1])
        else:
            ad = "Tesseract"
        if self.dusuk_guven:
            return f"[PDF s.{self.sayfa} · OCR, güven düşük · {ad}]"
        return f"[PDF s.{self.sayfa} · OCR · {ad} · güven %{round(self.guven * 100)}]"


class OcrOnbellegi:
    """output/ocr_onbellek/<sha[:2]>/<sha[:16]>-s<page>-<key>.json, key over
    (file sha256, page, engine, ISTEM_SURUMU)."""

    def __init__(self, dizin: str | Path):
        self.dizin = Path(dizin)

    def _yol(self, sha: str, sayfa: int, motor: str) -> Path:
        anahtar = hashlib.sha256(f"{sha}|{sayfa}|{motor}|{ISTEM_SURUMU}".encode("utf-8")).hexdigest()[:24]
        return self.dizin / sha[:2] / f"{sha[:16]}-s{sayfa}-{anahtar}.json"

    def al(self, sha: str, sayfa: int, motor: str) -> SayfaOkumasi | None:
        try:
            veri = json.loads(self._yol(sha, sayfa, motor).read_text(encoding="utf-8"))
            return SayfaOkumasi(int(veri["sayfa"]), str(veri["metin"]), str(veri["motor"]),
                                float(veri["guven"]), float(veri.get("usd", 0.0)))
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def koy(self, sha: str, okuma: SayfaOkumasi) -> None:
        atomic_json_dump({"sayfa": okuma.sayfa, "metin": okuma.metin, "motor": okuma.motor,
                          "guven": okuma.guven, "usd": okuma.usd, "istem_surumu": ISTEM_SURUMU,
                          "okundu": datetime.now().isoformat(timespec="seconds")},
                         str(self._yol(sha, okuma.sayfa, okuma.motor)))


class OcrDefteri:
    """output/ocr_defteri.json: measured spend per month (Istanbul wall clock).

    A Claude call is made only while the month's spend plus one page's worst
    case (SAYFA_TAHMINI_USD) fits under the cap, and the real cost is written
    from response.usage afterwards. Two processes checking at once (the cron
    reindex and a dashboard reindex) can pass the cap by at most one page each
    (≤ 0.025 USD); a reservation scheme would instead let a crashed process
    eat the cap for the rest of the month."""

    def __init__(self, yol: str | Path, tavan: float = AYLIK_TAVAN_USD,
                 simdi: Callable[[], datetime] = datetime.now):
        self.yol = Path(yol)
        self.tavan = float(tavan)
        self.simdi = simdi

    @contextmanager
    def _kilitli(self) -> Iterator[None]:
        self.yol.parent.mkdir(parents=True, exist_ok=True)
        with open(self.yol.with_name(self.yol.name + ".lock"), "a") as kilit:
            fcntl.flock(kilit, fcntl.LOCK_EX)
            yield

    def _oku(self) -> dict[str, Any]:
        try:
            veri = json.loads(self.yol.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return veri if isinstance(veri, dict) else {}

    def _ay(self) -> str:
        return self.simdi().strftime("%Y-%m")

    def harcanan(self) -> float:
        ay = (self._oku().get("aylar") or {}).get(self._ay()) or {}
        return float(ay.get("usd", 0.0))

    def izin_var(self) -> bool:
        return self.harcanan() + SAYFA_TAHMINI_USD <= self.tavan

    def yaz(self, motor: str, girdi_token: int, cikti_token: int) -> float:
        usd = (girdi_token * GIRDI_USD_MTOK + cikti_token * CIKTI_USD_MTOK) / 1_000_000
        with self._kilitli():
            veri = self._oku()
            ay = veri.setdefault("aylar", {}).setdefault(
                self._ay(), {"usd": 0.0, "sayfa": 0, "girdi_token": 0, "cikti_token": 0})
            ay["usd"] = round(float(ay.get("usd", 0.0)) + usd, 6)
            ay["sayfa"] = int(ay.get("sayfa", 0)) + 1
            ay["girdi_token"] = int(ay.get("girdi_token", 0)) + int(girdi_token)
            ay["cikti_token"] = int(ay.get("cikti_token", 0)) + int(cikti_token)
            veri["tavan_usd"] = self.tavan
            veri["son_motor"] = motor
            atomic_json_dump(veri, str(self.yol))
        return usd


@dataclass
class PdfOcrSonucu:
    metin: str
    toplam_sayfa: int
    metinsiz: int
    ocr_sayfalari: list[int] = field(default_factory=list)
    eksik: list[int] = field(default_factory=list)
    dusuk_guvenli: list[int] = field(default_factory=list)

    @property
    def ilerleme(self) -> str:
        return f"{self.metinsiz - len(self.eksik)}/{self.metinsiz}"


class OcrKatmani:
    """The shared layer: the attachment sync and the BM25 indexer both call
    pdf_oku with a deadline on `saat`; whatever is not read by then stays
    `eksik` and is read on a later run, the pages done coming from the cache."""

    def __init__(self, proje_koku: str | Path, okuyucu: Any = None,
                 tesseract: Callable[[bytes, float], tuple[str, float]] = tesseract_oku,
                 saat: Callable[[], float] = time.monotonic,
                 simdi: Callable[[], datetime] = datetime.now,
                 tavan: float | None = None):
        kok = Path(proje_koku)
        self.onbellek = OcrOnbellegi(kok / ONBELLEK)
        self.defter = OcrDefteri(kok / DEFTER, tavan=AYLIK_TAVAN_USD if tavan is None else tavan, simdi=simdi)
        self.okuyucu = okuyucu if okuyucu is not None else ClaudeGorselOkuyucu()
        self.tesseract = tesseract
        self.saat = saat

    def _kalan(self, son_an: float) -> float:
        return son_an - self.saat()

    def pdf_oku(self, pdf: str | Path, son_an: float,
                sayfa_metinleri: list[str] | None = None) -> PdfOcrSonucu:
        pdf = Path(pdf)
        if sayfa_metinleri is None:
            sayfa_metinleri = pdf_sayfa_metinleri(pdf, max(5.0, self._kalan(son_an)))
        sha = _sha256(pdf)
        parcalar: list[str] = []
        ocr_sayfalari: list[int] = []
        eksik: list[int] = []
        dusuk: list[int] = []
        metinsiz = 0
        for i, metin in enumerate(sayfa_metinleri, 1):
            if metin_katmani_var(metin):
                parcalar.append(metin)
                continue
            metinsiz += 1
            okuma = self._sayfa(pdf, sha, i, son_an)
            if okuma is None:
                eksik.append(i)
                parcalar.append("")
                continue
            if okuma.motor == MOTOR_BOS or not okuma.metin.strip():
                parcalar.append("")
                continue
            ocr_sayfalari.append(i)
            if okuma.dusuk_guven:
                dusuk.append(i)
            parcalar.append(f"{okuma.etiket()}\n{okuma.metin.strip()}")
        return PdfOcrSonucu(chr(12).join(parcalar), len(sayfa_metinleri), metinsiz,
                            ocr_sayfalari, eksik, dusuk)

    def _sayfa(self, pdf: Path, sha: str, sayfa: int, son_an: float) -> SayfaOkumasi | None:
        for motor in (self.okuyucu.motor, MOTOR_BOS):
            okuma = self.onbellek.al(sha, sayfa, motor)
            if okuma is not None:
                return okuma
        tesseract = self.onbellek.al(sha, sayfa, MOTOR_TESSERACT)
        # A Tesseract reading stays unless it is low and Claude may be asked
        # (e.g. a new month): checked before rendering, so a full cap does not
        # cost a render per low page per run.
        if tesseract is not None and (not tesseract.dusuk_guven or not self.defter.izin_var()):
            return tesseract
        if self._kalan(son_an) <= 0:
            return tesseract
        return self._oku(pdf, sha, sayfa, son_an, tesseract)

    def _sakla(self, sha: str, okuma: SayfaOkumasi) -> SayfaOkumasi:
        self.onbellek.koy(sha, okuma)
        return okuma

    def _oku(self, pdf: Path, sha: str, sayfa: int, son_an: float,
             onceki: SayfaOkumasi | None) -> SayfaOkumasi | None:
        try:
            jpeg = sayfa_gorseli(pdf, sayfa, max(5.0, self._kalan(son_an)))
        except OcrHatasi as exc:
            logger.warning("OCR: %s s.%d çizilemedi (%s)", pdf.name, sayfa, exc)
            return onceki
        if bos_sayfa_mi(jpeg):
            return self._sakla(sha, SayfaOkumasi(sayfa, "", MOTOR_BOS, 1.0))
        if self._kalan(son_an) >= CLAUDE_EN_AZ_SURE and self.defter.izin_var():
            okuma = self._claude(jpeg, sha, sayfa, son_an)
            if okuma is not None:
                return okuma
        if onceki is not None:
            return onceki
        if self._kalan(son_an) < TESSERACT_EN_AZ_SURE:
            return None
        try:
            metin, guven = self.tesseract(jpeg, self._kalan(son_an))
        except Exception as exc:  # noqa: BLE001 — a page left unread is retried next run
            logger.warning("OCR: Tesseract %s s.%d okuyamadı (%s)", pdf.name, sayfa, type(exc).__name__)
            return None
        return self._sakla(sha, SayfaOkumasi(sayfa, metin, MOTOR_TESSERACT, guven))

    def _claude(self, jpeg: bytes, sha: str, sayfa: int, son_an: float) -> SayfaOkumasi | None:
        try:
            sonuc = self.okuyucu.oku(jpeg, self._kalan(son_an))
        except Exception as exc:  # noqa: BLE001 — API error, no key, network: fall back
            logger.warning("OCR: Claude okuyamadı (%s); Tesseract'a düşülüyor", type(exc).__name__)
            return None
        usd = self.defter.yaz(self.okuyucu.motor, sonuc.girdi_token, sonuc.cikti_token)
        if sonuc.reddedildi:
            return None
        return self._sakla(sha, SayfaOkumasi(sayfa, sonuc.markdown, self.okuyucu.motor,
                                             _GUVEN.get(sonuc.okunabilirlik, 0.7), usd))
```

- [ ] **Step 5: Yeşil olduğunu gör**

Run: `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && DASHBOARD_SECRET_KEY=yerel-test-anahtari-portal-ekleri unshare -rn .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_ocr_katmani.py`
Expected: PASS, ağsız ad alanında (poppler yereldir; okuyucu sahtedir).

- [ ] **Step 6: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && test "$(git branch --show-current)" = feat/portal-ekleri && echo dal-dogru
git add src/ocr_katmani.py tests/sahte_ocr.py tests/test_ocr_katmani.py
git commit -m "$(cat <<'EOF'
OCR katmanı: Claude Haiku 4.5 görüsü, sayfa önbelleği, aylık tavan, Tesseract

Metin katmanı olmayan sayfa 1568 px'e çizilip Markdown'a okunur; sonuç
(sha256, sayfa, motor, istem sürümü) anahtarıyla önbelleğe girer. Aylık
10 USD tavanı response.usage'dan beslenen defterle tutulur; tavanda, API
hatasında ya da retle Tesseract'a düşülür. Boş sayfa ücretsizdir; her sayfa
motorunu ve güvenini taşır. Testler sahte okuyucuyla, ücretli API'siz.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Görev 15: OCR'u ek eşitlemesine, `FileAdapters`'a ve `ek_oku`'ya bağla; CLAUDE.md notu

**Files:**
- Modify: `src/assistant_core.py` (`DEFAULT_EXCLUDED_DIRS`, `DEFAULT_EXCLUDED_FILE_PATTERNS`, `AssistantConfig` + `from_project_root`, `PdfExtractionError`, `FileAdapters.__init__` + PDF dalı + yeni `_pdf_ocr`, `AssistantIndexer.__init__` + `reindex` başı + `can_reuse`, `SYSTEM_PROMPT` "Uydurma yasağı")
- Modify: `src/portal_ekleri_indir.py` (`metin_cikar`, `_METIN_NOTU`, `_metni_hazirla`, `ekleri_esitle` imzası + çıkarıcı + özet, yeni `_varsayilan_ocr`)
- Modify: `src/assistant_tools.py` (içe aktarma; `ek_oku_metni` iki ileti + OCR notu)
- Modify: `tests/conftest.py` (autouse: `ASSISTANT_PDF_OCR=0`)
- Modify: `CLAUDE.md` (OCR maddesi)
- Test: `tests/test_ocr_baglanti.py`

**Interfaces:**
- Consumes: Görev 14 `OcrKatmani`, `OcrDefteri`, `OcrHatasi`, `metin_katmani_var`, `DEFTER`; Görev 6 `metin_cikar`, `_metni_hazirla`, `ekleri_esitle`; Görev 10 `ek_oku_metni`; `tests.sahte_ocr`, `tests.sahte_http`.
- Produces: `AssistantConfig.pdf_ocr: bool` (env `ASSISTANT_PDF_OCR`, üretimde varsayılan açık), `AssistantConfig.ocr_sure: int` (env `ASSISTANT_OCR_SURE`, 45); `PdfExtractionError(reason, ilerleme="")` + `.ilerleme`; `FileAdapters(config, ocr=None)` + `.ocr`, `.ocr_son_an`, `.ocr_her_sayfa`; `extract()` OCR'lı PDF için `source_kind "pdf_ocr"`, yarımda `extraction_error "ocr_suruyor"` + `ocr_ilerleme`; `AssistantIndexer(config, ocr=None)`; `metin_cikar(yol, sure, ocr=None)` — yarımda `(METIN_BEKLIYOR, "okunan/toplam")`; ek kaydında `ocr_ilerleme`; `ekleri_esitle(..., ocr=None)` ve özette `ocr_bu_ay_usd`.

- [ ] **Step 1: Başarısız testi yaz**

`tests/test_ocr_baglanti.py`:

```python
"""OCR wired in (plan 2026-09-28-portal-ekleri, Görev 15): the general index reads
scanned PDFs, attachments are read page by page inside the sync budget, ek_oku
and the text sidecar carry the OCR text and its labels. Fake reader only."""
from src.assistant_core import AssistantConfig, AssistantIndexer, AssistantRuntime, FileAdapters, HybridRetriever
from src.assistant_tools import EK_TOOL, McpRegistry
from src.ocr_katmani import OcrKatmani
from src.portal_ekleri import EkDeposu, ek_kimligi
from src.portal_ekleri_indir import MB, Butce, ekleri_esitle, metin_cikar
from tests.sahte_http import SP_URL, SahteOturum, SahteYanit
from tests.sahte_ocr import MARKDOWN, Saat, SahteOkuyucu, SahteTesseract, taranmis_pdf

ETIKET = "[PDF s.1 · OCR · Claude Haiku 4.5 · güven %90]"


def _katman(kok, okuyucu=None, tesseract=None, **kw):
    return OcrKatmani(kok, okuyucu=okuyucu or SahteOkuyucu(), tesseract=tesseract or SahteTesseract(), **kw)


def _adaptor(kok, katman, son=60.0):
    ad = FileAdapters(AssistantConfig.from_project_root(kok), ocr=katman)
    if katman is not None:
        ad.ocr_son_an = katman.saat() + son
    return ad


def test_testlerde_ocr_kapali_uretimde_acik(tmp_path, monkeypatch):
    assert AssistantConfig.from_project_root(tmp_path).pdf_ocr is False       # tests/conftest.py
    monkeypatch.delenv("ASSISTANT_PDF_OCR")
    assert AssistantConfig.from_project_root(tmp_path).pdf_ocr is True
    assert AssistantConfig.from_project_root(tmp_path).ocr_sure == 45


def test_genel_indekste_bos_pdf_ocr_ile_okunur(tmp_path):
    pdf = taranmis_pdf(tmp_path / "tarama.pdf")
    sonuc = _adaptor(tmp_path, _katman(tmp_path)).extract(pdf, "content/yabanci-dil/tarama.pdf")
    assert sonuc["source_kind"] == "pdf_ocr" and sonuc["warnings"] == ["ocr"]
    assert sonuc["text"].startswith(f"{ETIKET}\n{MARKDOWN}")


def test_metin_katmanli_pdf_genel_indekste_ocr_a_gitmez(tmp_path, monkeypatch):
    pdf = taranmis_pdf(tmp_path / "kitap.pdf")
    monkeypatch.setattr(FileAdapters, "_extract_pdf_text",
                        lambda self, yol: "Bu sayfada okunur bir metin katmanı var.\n" + chr(12))
    okuyucu = SahteOkuyucu()
    sonuc = _adaptor(tmp_path, _katman(tmp_path, okuyucu)).extract(pdf, "content/eba/kitap.pdf")
    assert sonuc["source_kind"] == "pdf" and okuyucu.cagrilar == []


def test_ocr_verilmezse_eski_davranis(tmp_path):
    pdf = taranmis_pdf(tmp_path / "tarama.pdf")
    sonuc = _adaptor(tmp_path, None).extract(pdf, "content/x/tarama.pdf")
    assert sonuc["source_kind"] == "metadata" and sonuc["warnings"] == ["pdf_no_text"]


def test_sure_yetmezse_ocr_suruyor_ve_ilerleme(tmp_path):
    pdf = taranmis_pdf(tmp_path / "tarama.pdf", icerikli=2)
    saat = Saat()
    katman = _katman(tmp_path, SahteOkuyucu(saat=saat, adim=10.0), saat=saat)
    sonuc = _adaptor(tmp_path, katman, son=18.0).extract(pdf, "content/x/tarama.pdf")
    assert sonuc["extraction_error"] == "ocr_suruyor" and sonuc["ocr_ilerleme"] == "1/2"


def test_indeks_eski_metinsiz_pdf_kaydini_ocr_ile_yeniler(tmp_path):
    taranmis_pdf(_dizin(tmp_path / "content" / "yabanci-dil") / "tarama.pdf")
    config = AssistantConfig.from_project_root(tmp_path)
    AssistantIndexer(config).reindex(incremental=True)            # conftest: OCR off
    import json
    once = json.loads(config.chunks_path.read_text(encoding="utf-8"))
    assert once[0]["warnings"] == ["pdf_no_text"]
    ix = AssistantIndexer(config, ocr=_katman(tmp_path))
    meta = ix.reindex(incremental=True)
    sonra = json.loads(config.chunks_path.read_text(encoding="utf-8"))
    assert meta["changed_files"] == 1 and sonra[0]["source_kind"] == "pdf_ocr"
    assert HybridRetriever(chunks=sonra).search("Kesirleri topla", top_k=1)[0]["path"] == \
        "content/yabanci-dil/tarama.pdf"


def _dizin(yol):
    yol.mkdir(parents=True, exist_ok=True)
    return yol


def test_ocr_defteri_ve_onbellegi_indekse_girmez(tmp_path):
    ix = AssistantIndexer(AssistantConfig.from_project_root(tmp_path))
    assert ix._is_excluded_file("output/ocr_defteri.json")
    assert ix._is_excluded_file("output/ocr_defteri.json.lock")
    assert ix._is_excluded_dir("output/ocr_onbellek/ab")


def test_ek_metni_ocr_ile_cikar(tmp_path):
    pdf = taranmis_pdf(tmp_path / "ek.pdf")
    durum, metin = metin_cikar(pdf, 30.0, ocr=_katman(tmp_path))
    assert durum == "var" and metin.startswith(f"{ETIKET}\n{MARKDOWN}")


def test_yarim_ek_metni_bekliyor_ve_ilerleme(tmp_path):
    pdf = taranmis_pdf(tmp_path / "ek.pdf", icerikli=2)
    saat = Saat()
    katman = _katman(tmp_path, SahteOkuyucu(saat=saat, adim=10.0), saat=saat)
    # The 5 s floor is too little for a Claude call (15 s) or Tesseract (10 s):
    # nothing is read, nothing is lost, and the next run starts again.
    assert metin_cikar(pdf, 0.0, ocr=katman) == ("bekliyor", "0/2")


VERI = {"odevlerim": {"homework": {"rows": [{
    "Ders Adı": "Matematik", "Ödev Başlığı": "Kesir çalışma kağıdı",
    "Ödev Son Teslim Tarihi": "30.09.2026 12:00",
    "detail": {"description": "", "attachments": [{"name": "Çalışma kağıdı.pdf", "url": SP_URL}]}}]}}}


def _taranmis_oturum(tmp_path):
    govde = taranmis_pdf(tmp_path / "kaynak.pdf").read_bytes()
    return SahteOturum({"https://ornekokul-my.sharepoint.com/":
                        lambda u, h: SahteYanit(200, govde, {"Content-Type": "application/pdf"})})


def test_ek_esitlemesi_ocr_metnini_yan_dosyaya_ve_ek_oku_ya_tasir(tmp_path):
    kok = _dizin(tmp_path / "kok")
    ozet = ekleri_esitle(kok, VERI, _taranmis_oturum(tmp_path), Butce(float("inf"), 100 * MB),
                         ocr=_katman(kok))
    depo = EkDeposu(kok)
    kayit = depo.kayit(ek_kimligi(SP_URL))
    assert kayit["text"] == "var" and "ocr_ilerleme" not in kayit
    assert f"{ETIKET}\n{MARKDOWN}" in depo.metin_yolu(kayit["id"]).read_text(encoding="utf-8")
    assert ozet["ocr_bu_ay_usd"] > 0
    out = McpRegistry(clients={}, local_search=lambda q, k: [], ek_deposu=depo).dispatch(EK_TOOL, {"id": kayit["id"]})
    assert out.ok and ETIKET in out.text and "OCR ile okundu" in out.text and "# Soru 1" in out.text


def test_dusuk_guvenli_sayfa_etiketiyle_gorunur(tmp_path):
    kok = _dizin(tmp_path / "kok")
    ekleri_esitle(kok, VERI, _taranmis_oturum(tmp_path), Butce(float("inf"), 100 * MB),
                  ocr=_katman(kok, tesseract=SahteTesseract(guven=0.4), tavan=0.0))
    depo = EkDeposu(kok)
    metin = depo.metin_yolu(ek_kimligi(SP_URL)).read_text(encoding="utf-8")
    assert "[PDF s.1 · OCR, güven düşük · Tesseract]" in metin


def test_yarim_ocr_deneme_saymaz_ve_ek_oku_ilerlemeyi_soyler(tmp_path):
    kok = _dizin(tmp_path / "kok")
    cevaplar = [("bekliyor", "1/3"), ("var", "Soru 1 metni")]
    oturum = _taranmis_oturum(tmp_path)
    ekleri_esitle(kok, VERI, oturum, Butce(float("inf"), 100 * MB),
                  metin_cikarici=lambda y, s: cevaplar.pop(0))
    depo = EkDeposu(kok)
    kayit = depo.kayit(ek_kimligi(SP_URL))
    assert (kayit["text"], kayit["ocr_ilerleme"], kayit.get("text_attempts", 0)) == ("bekliyor", "1/3", 0)
    out = McpRegistry(clients={}, local_search=lambda q, k: [], ek_deposu=depo).dispatch(EK_TOOL, {"id": kayit["id"]})
    assert "OCR ile okunuyor (1/3 sayfa okundu)" in out.text
    ekleri_esitle(kok, VERI, oturum, Butce(float("inf"), 100 * MB), metin_cikarici=lambda y, s: cevaplar.pop(0))
    kayit = depo.kayit(ek_kimligi(SP_URL))
    assert (kayit["text"], kayit["text_attempts"]) == ("var", 1) and "ocr_ilerleme" not in kayit


def test_istem_dusuk_guvenli_ocr_sayfasini_kesin_saymaz():
    assert "OCR, güven düşük" in AssistantRuntime.SYSTEM_PROMPT
```

- [ ] **Step 2: Kırmızı olduğunu gör**

Run: `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && DASHBOARD_SECRET_KEY=yerel-test-anahtari-portal-ekleri .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_ocr_baglanti.py`
Expected: FAIL — `FileAdapters.__init__() got an unexpected keyword argument 'ocr'` ve `pdf_ocr` yok.

- [ ] **Step 3: Test bekçisi**

`tests/conftest.py` sonuna:

```python
@pytest.fixture(autouse=True)
def _pdf_ocr_kapali(monkeypatch):
    """OCR of scanned PDFs (src/ocr_katmani.py) is on by default in production.
    In tests it is off unless a test turns it on and hands in a fake reader: a
    scanned PDF in an unrelated test must not reach Claude, write the OCR
    ledger, or spend ~20 s per page in real Tesseract (plan 2026-09-28, Görev 15)."""
    monkeypatch.setenv("ASSISTANT_PDF_OCR", "0")
```

- [ ] **Step 4: `assistant_core`**

`DEFAULT_EXCLUDED_DIRS` içinde `"content/pedagoji",` satırının altına:

```python
    # The OCR page cache (src/ocr_katmani.py): one JSON per page read; the
    # text reaches the index through the PDF it came from, never twice.
    "output/ocr_onbellek",
```

`DEFAULT_EXCLUDED_FILE_PATTERNS` içinde (Görev 9'un `"portal_ekleri.json",` satırının altına):

```python
    # The OCR spend ledger: months, tokens, USD — bookkeeping, not school data.
    "ocr_defteri.json",
```

`AssistantConfig` alanlarının sonuna (`excluded_file_patterns: set[str]` altına):

```python
    # OCR for PDFs whose pdftotext text is empty (src/ocr_katmani.py): on unless
    # ASSISTANT_PDF_OCR=0; seconds of OCR per indexer run. perform_incremental_
    # reindex runs two indexers (main + aile), so 45 s each stays inside the
    # 150 s run_sync reserves after the attachments (run_sync.EK_YEDEK_SURE).
    pdf_ocr: bool = False
    ocr_sure: int = 45
```

`from_project_root`'un `return cls(...)` çağrısına `excluded_file_patterns=excluded_files,` altına:

```python
            pdf_ocr=os.environ.get("ASSISTANT_PDF_OCR", "1") == "1",
            ocr_sure=int(os.environ.get("ASSISTANT_OCR_SURE", "45")),
```

`PdfExtractionError.__init__`:

```python
    def __init__(self, reason: str, ilerleme: str = ""):
        super().__init__(reason)
        self.reason = reason
        # "read/total" textless pages when OCR is part-way (reason "ocr_suruyor").
        self.ilerleme = ilerleme
```

`FileAdapters.__init__`:

```python
    def __init__(self, config: AssistantConfig, ocr: Any = None):
        self.config = config
        # src.ocr_katmani.OcrKatmani, or None (no OCR). The caller sets the
        # deadline (on ocr.saat) before extracting; ocr_her_sayfa reads every
        # textless page (attachments), otherwise only PDFs with no text at all
        # (the general index — a textbook's picture pages are not OCR'd).
        self.ocr = ocr
        self.ocr_son_an: float | None = None
        self.ocr_her_sayfa = False
```

`extract` içindeki PDF dalının tamamı:

```python
        if ext in PDF_EXTENSIONS:
            try:
                text = self._extract_pdf_text(file_path)
                ocr_sonucu = self._pdf_ocr(file_path, text)
            except PdfExtractionError as exc:
                # Not "no text layer" — a timeout, a real failure, or OCR still
                # under way. No manifest entry: retried in full next run (the
                # OCR'd pages come back from its cache).
                return {
                    "text": "",
                    "source_kind": "metadata",
                    "confidence": 0.0,
                    "warnings": [f"pdf_extraction_{exc.reason}"],
                    "extraction_error": exc.reason,
                    "ocr_ilerleme": exc.ilerleme,
                }
            if ocr_sonucu is not None:
                return ocr_sonucu
            return {
                "text": text or self._metadata_only_text(rel_path, file_path, reason="pdf_no_text"),
                "source_kind": "pdf" if text else "metadata",
                "confidence": 0.8 if text else 0.2,
                "warnings": [] if text else ["pdf_no_text"],
            }
```

`_extract_image_text`'in üstüne:

```python
    def _pdf_ocr(self, file_path: Path, text: str) -> dict[str, Any] | None:
        """Pages without a text layer through the OCR layer (plan 2026-09-28,
        Görev 15). None: no OCR configured, nothing to OCR, or the file could
        not be measured — the caller then keeps the plain pdftotext result."""
        if self.ocr is None or self.ocr_son_an is None:
            return None
        if not self.ocr_her_sayfa and text.strip():
            return None
        from src.ocr_katmani import OcrHatasi
        sayfalar = None
        if chr(12) in text:
            sayfalar = text.split(chr(12))
            if sayfalar and not sayfalar[-1].strip():
                sayfalar = sayfalar[:-1]
        try:
            sonuc = self.ocr.pdf_oku(file_path, self.ocr_son_an, sayfa_metinleri=sayfalar)
        except OcrHatasi as exc:
            logger.warning("OCR %s: %s", file_path.name, exc)
            return None
        if sonuc.eksik:
            raise PdfExtractionError("ocr_suruyor", ilerleme=sonuc.ilerleme)
        if not sonuc.ocr_sayfalari:
            return None
        dusuk = bool(sonuc.dusuk_guvenli)
        return {
            "text": sonuc.metin,
            "source_kind": "pdf_ocr",
            "confidence": 0.55 if dusuk else 0.75,
            "warnings": ["ocr"] + (["ocr_dusuk_guven"] if dusuk else []),
        }
```

`AssistantIndexer.__init__`:

```python
    def __init__(self, config: AssistantConfig, ocr: Any = None):
        self.config = config
        if ocr is None and config.pdf_ocr:
            from src.ocr_katmani import OcrKatmani
            ocr = OcrKatmani(config.project_root)
        self.adapters = FileAdapters(config, ocr=ocr)
```

`reindex` içinde `start = time.perf_counter()` satırının altına:

```python
        if self.adapters.ocr is not None:
            # OCR's share of this run: a scan is read page by page until this
            # deadline; the rest is read on a later run (src/ocr_katmani.py).
            self.adapters.ocr_son_an = self.adapters.ocr.saat() + max(0, self.config.ocr_sure)
```

`can_reuse` hesabı:

```python
            can_reuse = bool(
                incremental
                and old_rec
                and old_rec.get("sha256") == sha
                and rel_path in old_chunks_by_path
                # A scan indexed before OCR existed ("pdf_no_text", 3 chunks in
                # the live index on 2026-09-28) is read again once OCR is on,
                # though its sha256 has not changed.
                and not (self.adapters.ocr is not None and ext in PDF_EXTENSIONS
                         and any("pdf_no_text" in (c.get("warnings") or [])
                                 for c in old_chunks_by_path[rel_path]))
            )
```

`SYSTEM_PROMPT`'ta `"- Araç sonuç döndürmediyse eksikliği açıkça söyle. Boşluğu doldurma.\n"` satırının altına:

```python
        "- '[PDF s.N · OCR, güven düşük …]' satırıyla başlayan bir sayfadan aldığın bilgiyi "
        "kesinmiş gibi sunma: OCR ile okunduğunu söyle ve okura sayfayı kendisinin kontrol "
        "etmesini öner.\n"
```

- [ ] **Step 5: Ek eşitlemesi**

`src/portal_ekleri_indir.py`'de `_METIN_NOTU`:

```python
_METIN_NOTU = {METIN_YOK: "(Metin katmanı yok ve OCR okunur metin bulamadı: boş ya da yalnız görsel sayfalar.)",
               METIN_DESTEKLENMIYOR: "(Bu ek türünün metni okunmuyor.)"}
```

`metin_cikar`'ın tamamı:

```python
def metin_cikar(yol: Path, sure: float, ocr: Any = None) -> tuple[str, str]:
    """(text status, text) through the assistant's own FileAdapters: pdftotext
    for a PDF, stdlib zip/XML for a .docx, tesseract for an image only when
    ASSISTANT_ENABLE_OCR=1, as for every other image TEDY indexes.

    With `ocr` (src/ocr_katmani.OcrKatmani), every PDF page without a text
    layer is read by Claude Haiku 4.5's vision, or Tesseract past the monthly
    cap, until `sure` seconds have passed. A scan read part-way is
    METIN_BEKLIYOR with the progress ("read/total") as the second element; the
    pages done are cached and the rest continue on the next run."""
    from src.assistant_core import FileAdapters
    if yol.suffix.lower() not in _METIN_UZANTILARI:
        return METIN_DESTEKLENMIYOR, ""
    ayar = _CikarmaAyari(max_file_size_mb=EK_BOYUT_SINIRI // MB + 1, pdf_max_pages=400,
                         pdf_timeout=max(5, int(sure)),
                         enable_ocr=os.environ.get("ASSISTANT_ENABLE_OCR", "0") == "1")
    adaptor = FileAdapters(ayar, ocr=ocr)
    if ocr is not None:
        adaptor.ocr_son_an = ocr.saat() + max(5.0, sure)
        adaptor.ocr_her_sayfa = True
    sonuc = adaptor.extract(yol, yol.name)
    if sonuc.get("extraction_error") == "ocr_suruyor":
        return METIN_BEKLIYOR, str(sonuc.get("ocr_ilerleme") or "")
    if sonuc.get("extraction_error"):
        return METIN_HATA, ""
    if sonuc.get("source_kind") == "metadata":
        return METIN_YOK, ""
    return METIN_VAR, str(sonuc.get("text") or "")


def _varsayilan_ocr(proje_koku: str | Path) -> Any:
    """The OCR layer the sync uses unless a caller hands one in; none when
    ASSISTANT_PDF_OCR=0 (tests/conftest.py sets it for every test)."""
    if os.environ.get("ASSISTANT_PDF_OCR", "1") == "0":
        return None
    from src.ocr_katmani import OcrKatmani
    return OcrKatmani(proje_koku)
```

`_metni_hazirla`'nın tamamı:

```python
def _metni_hazirla(depo: EkDeposu, kayit: dict[str, Any], sure: float,
                   cikarici: Callable[[Path, float], tuple[str, str]]) -> None:
    yol = depo.dosya_yolu(kayit)
    durum, metin = cikarici(yol, sure)
    if durum == METIN_BEKLIYOR:
        # A scan read part-way: its pages are cached (src/ocr_katmani.py) and
        # the rest continue next run. Not an attempt — METIN_DENEME_SINIRI is
        # for extractions that fail, not for a long book.
        kayit.update(text=METIN_BEKLIYOR, ocr_ilerleme=metin)
        return
    kayit["text_attempts"] = int(kayit.get("text_attempts") or 0) + 1
    kayit.update(text=durum, text_chars=len(metin))
    kayit.pop("ocr_ilerleme", None)
    kaynak = kayit.get("source") if isinstance(kayit.get("source"), dict) else {}
    atomic_json_dump({"id": kayit["id"], "name": kayit.get("name", ""), "title": kaynak.get("title", ""),
                      "section": kaynak.get("section", ""), "course": kaynak.get("course", "")},
                     str(depo.meta_yolu(kayit["id"])))
    if durum != METIN_HATA:
        _atomik_yaz(depo.metin_yolu(kayit["id"]), metin_dosyasi(kayit, durum, metin))
```

`ekleri_esitle` imzası (`metin_cikarici` parametresinden sonra):

```python
                  metin_cikarici: Callable[[Path, float], tuple[str, str]] = metin_cikar,
                  ocr: Any = None) -> dict[str, Any]:
```

gövdenin başına (`depo = EkDeposu(proje_koku)` satırının altına):

```python
    if metin_cikarici is metin_cikar:
        katman = ocr if ocr is not None else _varsayilan_ocr(proje_koku)

        def metin_cikarici(yol: Path, sure: float, _katman: Any = katman) -> tuple[str, str]:
            return metin_cikar(yol, sure, ocr=_katman)
```

dönüş sözlüğüne `"bu_tur_metin": bu_tur["metin"],` satırının altına:

```python
            "ocr_bu_ay_usd": round(OcrDefteri(Path(proje_koku) / DEFTER).harcanan(), 4),
```

ve dosyanın içe aktarmalarına:

```python
from src.ocr_katmani import DEFTER, OcrDefteri
```

- [ ] **Step 6: `ek_oku`**

`src/assistant_tools.py` `from src.portal_ekleri import (...)` satırına `METIN_BEKLIYOR` ekle. `ek_oku_metni` içinde `METIN_YOK` dalı:

```python
    if metin_durumu == METIN_YOK:
        return (f"{bas}\nBu ekin metin katmanı yok ve OCR da okunur metin bulamadı (boş ya da "
                "yalnız görsel sayfalar); içeriğini okuyamıyorum. Okur dosyayı TEDY'de açabilir."), etiket, kimlik
    if metin_durumu == METIN_BEKLIYOR and kayit.get("ocr_ilerleme"):
        return (f"{bas}\nBu ek taranmış; sayfaları OCR ile okunuyor ({kayit['ocr_ilerleme']} sayfa "
                "okundu). Metin sonraki eşitlemelerde tamamlanır; içeriğini şimdilik okuyamıyorum."), etiket, kimlik
```

ve son `return`'den önce (sayfa parçası hazırlandıktan sonra):

```python
    ocr_notu = ("\nNot: bu metin sayfasındaki PDF sayfalarının bir kısmı OCR ile okundu; "
                "'OCR, güven düşük' diye işaretli sayfadaki bilgiyi kesin sayma.") if "· OCR" in parca else ""
    return f"{bas}\nMetin sayfası {n}/{toplam}{pdf}{ocr_notu}\n\n{parca}{kuyruk}", etiket, kimlik
```

(docstring'deki "no text layer (a scan — no OCR, plan decision 2)" ifadesini "no text even after OCR, or OCR still under way (plan decision 2)" yap.)

- [ ] **Step 7: Yeşil olduğunu gör**

Run: `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && DASHBOARD_SECRET_KEY=yerel-test-anahtari-portal-ekleri unshare -rn .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_ocr_baglanti.py tests/test_ocr_katmani.py tests/test_portal_ekleri_esitle.py tests/test_assistant_ek_oku.py tests/test_assistant_docx.py tests/test_portal_ekleri_indeks.py tests/test_assistant_indeks_hijyeni.py tests/test_assistant_core.py`
Expected: PASS, ağsız ad alanında.

- [ ] **Step 8: CLAUDE.md**

**Asistan ve portal ekleri** maddesinin (Görev 13 Step 5) altına — Görev 13 bu görevden sonra koşar; madde yoksa **Asistan ve ödevler** maddesinin altına koy:

```
- **OCR for scanned PDFs** (plan `docs/superpowers/plans/2026-09-28-portal-ekleri.md`, Görev 14–15; `src/ocr_katmani.py`): a PDF page without a text layer (< 20 non-space characters from pdftotext) is rendered by `pdftoppm -scale-to 1568` (Claude downsizes past ~1568 px anyway; ~2,400 input tokens a page) and read by Claude Haiku 4.5 vision (`claude-haiku-4-5`, `OCR_CLAUDE_MODEL`) through `src/claude_api.py` into Markdown with headings, tables and LaTeX kept. A white page (grey stddev < 2) costs nothing. Each page is cached under `output/ocr_onbellek/` by (file sha256, page, engine, `ISTEM_SURUMU`) and read once. Spend is capped at 10 USD a month (`TEDY_OCR_AYLIK_USD`) in `output/ocr_defteri.json`, written from `response.usage` at 1/5 USD per MTok; Claude is called only while one page's worst case (≈ 0.0245 USD) still fits. At the cap, on an API error or a refusal, Tesseract `tur+eng` reads the page; a low-confidence Tesseract page is retried on Claude once the cap allows. Every OCR'd page opens with `[PDF s.N · OCR · <engine> · güven %NN]`, or `[PDF s.N · OCR, güven düşük · <engine>]` below 0.6, and the system prompt tells the model not to present such a page as certain. Attachments: every textless page, inside the sync's budget; a scan read part-way is `text: "bekliyor"` with `ocr_ilerleme` ("12/40"), not a failed attempt, and continues next run; `ek_oku` says so. General index: only PDFs whose pdftotext is empty, `ASSISTANT_OCR_SURE` (45 s) per indexer run; a part-read PDF is `dusen_dosyalar_nedenleri: "ocr_suruyor"` and continues next run; old `pdf_no_text` chunks are re-read without an `INDEX_FORMAT_VERSION` bump. `ASSISTANT_PDF_OCR=0` turns it off (every test runs with it off unless it hands in a fake reader).
```

- [ ] **Step 9: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/portal-ekleri && test "$(git branch --show-current)" = feat/portal-ekleri && echo dal-dogru
git add src/assistant_core.py src/portal_ekleri_indir.py src/assistant_tools.py tests/conftest.py tests/test_ocr_baglanti.py CLAUDE.md
git commit -m "$(cat <<'EOF'
OCR'u ek eşitlemesine, genel indekse ve ek_oku'ya bağla

Eklerde metinsiz her sayfa eşitleme bütçesi içinde, genel indekste
pdftotext'i boş PDF'ler indeksleyici başına 45 s içinde okunur; yarım kalan
sonraki turda sürer ve deneme saymaz. Yan dosya ve ek_oku OCR metnini,
motorunu ve "OCR, güven düşük" etiketini taşır; testlerde OCR kapalıdır.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

## Controller: dağıtım (görev değil; controller yapar)

1. **Birleştir:** ana checkout paylaşımlıdır; birleştirmeyi geçici bir worktree'de yap, dalı doğrula, `main`'i ancak `f7cad72` (ya da o anki `origin/main`) `feat/portal-ekleri`'nin atasıysa ileri sar; atalık korumalı push.
2. **Build ve restart** (`/mnt/thunderbolt/workspaces/TED`'de, `main` güncellendikten sonra): `cd dashboard && npm ci && npm run build; echo "build çıkış: $?"`, sonra `systemctl --user restart ted-dashboard`. `curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8085/api/ekler/0123456789abcdef` → oturumsuz `401`.
3. **İlk gerçek indirme turu, canlı izlenir:** `cd /mnt/thunderbolt/workspaces/TED && flock -n output/.sync.lock .venv/bin/python -m src.portal_ekleri_indir --sure 400 --bayt-mb 400 --indeksle`. Çıktıdaki özetin `indirildi`/`erisilemedi`/`kalan_is` sayılarını beklentiyle karşılaştır (2026-09-28 yoklaması: SharePoint 4 PDF + 1 giriş duvarı, Drive 2 ya da 4, Docs 1 PDF). `kalan_is > 0` ise bir kez daha koş. `output/portal_ekleri.json`'da her `erisilemedi`'nin `reason`'ı okunur olmalı.
4. **Yüzeyler:** tedy.online'da İşler'de bir ödev modalı açılır; ek adı TEDY kopyasını (`/api/ekler/…`) açar, 100 MB'lık PDF'in ilk sayfası tamamı inmeden görünür (Range); "Kaynağında aç" özgünü açar; giriş duvarındaki ek "İndirilemedi — kaynağında aç" der.
5. **Asistan:** "Sosyal Bilgiler ödevimin ekinde ne isteniyor?" → `odev_listesi` + `ek_oku` çağrılır, atıf "<ek adı> · <ödev başlığı>" olur.
6. **Sonraki cron turu:** `output/sync.log`'da `[EKLER]` satırı ve `Completed in …s` < 600; `health.json`'da `ekler`. Aynı turdan sonra süs sayımı (Görev 2 Step 7 betiği, bu kez ham dosyada) `0` olmalı: `run_sync` önceki haftaları temizleyerek yazar.
7. **OCR (Görev 14–15):** 3. adımın `--indeksle` koşusu ve sonraki cron turları taranmış sayfaları okur. `output/ocr_defteri.json`'da bu ayın `usd`/`sayfa`/`girdi_token`/`cikti_token` değerleri görünmeli; sayfa başına ~0,004–0,01 $ beklenir (Haiku 4.5, ~2.400 görsel token'ı). Aşarsa dur ve ölç; tavan 10 $/ay (`TEDY_OCR_AYLIK_USD`, `.env`'e yazmak gerekmez). İndeksin `meta.json`'unda `dusen_dosyalar_nedenleri` içindeki `ocr_suruyor` kayıtları (2026-09-28'de `content/yabanci-dil`'de 3 taranmış PDF vardı) turlar geçtikçe azalmalı; bir taranmış ekte `ocr_ilerleme` artmalı ve sonunda `text: "var"` olmalı. Asistana taranmış bir sayfayı sor: cevap `[PDF s.N · OCR …]` sayfasından gelmeli, düşük güvenliyse bunu söylemeli. `output/sync.log`'da her turun `Completed in …s` değeri < 600 kalmalı.
