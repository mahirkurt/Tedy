# TEDY Asistanı — Projenin Eriştiği Her Kaynağa Tam Bağlam

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Her görev kendi testleriyle kapanır.

**Goal:** Asistan, projenin erişimindeki her belgeyi, dokümanı ve veri tabanını bağlam olarak kullanabilsin — doğru, güncel, sızıntısız ve kaynaklı. Kullanıcı isteği (2026-09-25): "Asistanın bağlamında kullanabilmesi için projenin erişim sağladığı tüm belge, doküman ve veri tabanlarının eksiksiz entegrasyonunu sağla."

**Spec / kanıt:** `docs/superpowers/notes/2026-09-25-asistan-veri-denetimi.md` (salt-okuma denetim; bu planın her görevi oradaki bir bulguya dayanır — önce onu oku).

**Mimari:** Üç kanal var ve üçü de korunur:
1. **Canlı yapısal araçlar**, `odev_listesi` deseni: `AssistantRuntime`, `dashboard_api`'deki fonksiyonları çağırıp panonun gösterdiği veriyi okur. Pano ile asistan aynı şeyi farklı söyleyemez (İ9).
2. **BM25 dosya indeksi** (`ogrenci_verisi_ara`): serbest metin araması için.
3. **MCP araçları:** maarif-mufredat ve egitim-kaynak.

## Global Constraints

- **Çalışma dizini ve dal:** `/mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-tam-baglam`, dal `feat/asistan-tam-baglam`. Ana checkout'a (`/mnt/thunderbolt/workspaces/TED`) dokunma: canlı servis oradan çalışır ve başka oturumlar oraya commit atar. `git push` yok; çıplak `git stash` yok.
- **Testler:**
  - `.venv/bin/python -m pytest -q -p no:cacheprovider`: çalışma ağacında `.venv` yoksa `/mnt/thunderbolt/workspaces/TED/.venv/bin/python`'ı kullan.
  - Pano: `cd dashboard && npm run build && npx playwright test …` (bayat paket tuzağı: e2e her zaman yeni derleme ister).
  - Her komut **ön planda** koşar, arka plan işi yok.
- **Testler ücretli API çağıramaz:** `tests/conftest.py` `ANTHROPIC_API_KEY`'i siler. MCP sunucularına gerçek ağ çağrısı yapan test yok; sahte istemci kullan.
- **Fixture'larda kişisel veri yok:** gerçek biçim, uydurma değer. `output/scraped_data.json`'dan biçim kopyalanır, içerik kopyalanmaz.
- **Güvenlik:** Portal çerezleri, oturum ve anahtar dosyaları, kişi başı ilerleme dosyaları modele asla gitmez.
- **Kaynak disiplini:**
  - Her yeni araç `ToolOutcome.citations` ile kaynak döndürür; `kind` mevcut sınıflardan (`ogrenci`, `mufredat`, `kitap`, `oer`, `modul`) biri ya da açıkça eklenmiş yeni bir sınıftır.
  - Atıf etiketleri okurun tanıyacağı adlar taşır: "Ders programı", "Sınavlar", "Matematik · 3. hafta içeriği". İç yol taşımaz.
- **Araç gövdesi** `chat_with_tools`'un 4.000 karakter kesmesine sığar (gövde ≤ 3.900 karakter).
- **Mevcut desenler:** `odev_listesi` (`src/assistant_tools.py` `ODEV_TOOL`, `odev_listesi_metni`; `dashboard_api._canli_odevler`; `AssistantRuntime(odev_kaynagi=…)`). Yeni canlı araçlar aynı biçimde bağlanır: runtime'a bir çağrılabilir verilir, verilmezse araç ilan edilmez.
- **Stil:** Türkçe kullanıcı metni, İngilizce kod yorumları. Yorum sıklığı ve dili çevredeki koda uyar ("measured …" gerekçeli yorumlar).
- **Commit:** Her görev kendi commit(ler)i. Mesaj sonu: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

---

### Görev 1: İndeks hijyeni, güvenlik ve arama kalitesi

**Files:** `src/assistant_core.py` (retriever: `DEFAULT_INCLUDE_DIRS`, dışlama desenleri, `ASSISTANT_MAX_CHUNKS`, PDF sayfa sınırı, keşif sırası, belirteçleyici), `src/assistant_tools.py` (`_dispatch_local`), yeni `tests/test_assistant_indeks_hijyeni.py`.

**Davranış:**
1. **Dışlananlar:**
   - `*.log` ve `*.log.*`
   - `portal_cookies.json` ve adında `cookie` geçen her dosya
   - `portal_architecture.json`
   - `book_progress.json`, `module_progress.json`, `homework_first_seen.json`
   - `*.pid`, `crontab*`, `.sync_zamanlama.json`
   - `saat_dilimi_gocu_yedek/`, `crontab_yedek/`, `mebi_quiz_discovery/`, `archive/`
   - yolunda `yedek` ya da `backup` geçen her dizin
   - `content/pedagoji/` (Görev 5'te ayrı bir aile bölümüne taşınır).
2. **Keşif sırası:** `output/` önce, sonra `content/`. Tavan varsayılanı 30.000 parça. Tavana ulaşılırsa düşen dosyalar `logger.warning` ile adlarıyla söylenir ve reindex özetine `dusen_dosyalar` olarak girer; sessiz düşme yok.
3. **PDF sayfa sınırı:** 120 → 400 (`ASSISTANT_PDF_MAX_PAGES` ortam değişkeniyle değişir).
4. **Türkçe belirteçleme:** Önce Türkçe küçük harf (`İ`→`i`, `I`→`ı`), sonra aksan katlama (`ı→i ş→s ğ→g ü→u ö→o ç→c`). İndeks ve sorgu aynı fonksiyondan geçer. Kalıcı indeks biçim sürümü artar, eski indeks yeniden kurulur.
5. **Tam metin:** `ogrenci_verisi_ara` modele her isabetin tam parça metnini verir (isabet başına ≤ 1.200 karakter, toplam ≤ 3.900). Atıf `snippet`'i 260 karakter kalır.
6. **Sınıf etiketi:** `content/eba` ve `content/sebitv` parçalarının dosya adından sınıf çıkarılır ("Matematik 6 1. Kitap.pdf" → 6). Atıf etiketi "6. sınıf · Matematik 6 1. Kitap" olur. Çıkarılamıyorsa etiket değişmez.

**Doğrulama:** `pytest tests/test_assistant_indeks_hijyeni.py` şunları gösterir:
- dışlanan her örnek dosya indekse girmiyor;
- tavanda `output/` dosyası düşmüyor ve düşen dosya uyarı veriyor;
- "İngilizce" ile "ingilizce", "ısı" ile "isi" aynı belirteçleri veriyor;
- tam metin dönüyor;
- sınıf etiketi doğru.

Mevcut asistan testleri yeşil kalır.

### Görev 2: Öğrenci verisi — canlı yapısal araçlar ve düzeltilmiş biçimlendirici

**Files:** `src/assistant_tools.py`, `src/assistant_core.py` (`_fmt_scraped_data`, runtime kurulumu), `src/dashboard_api.py` (yalnız çağrılabilir okuma fonksiyonlarını dışa açmak için küçük çıkarımlar; rota davranışı değişmez), yeni `tests/test_assistant_ogrenci_araclari.py`.

**Araçlar** (hepsi salt-okuma; kaynak `odev_listesi` gibi runtime'a verilir):
- **`ders_programi(gun?: "bugün" | "yarın" | gün adı)`**
  - `/api/schedule` verisinden gün gün dersleri saatleriyle döndürür.
  - Tablo iki bloktan oluşur (Pzt–Per ve Cum–Paz), her bloğun kendi saat sütunu var; mantık `dashboard/src/utils/schedule.ts` (`dayColumns`) ile aynı olmalı ve Python'da yazılır.
  - "bugün/yarın" Istanbul tarihine göre çözülür; hafta sonu "okul yok" der.
- **`sinavlar()`:** `/api/exams`'ın mantığıyla yaklaşan ve geçmiş sınavları döndürür: ders, tarih, tür. Aynı fonksiyon yeniden kullanılır, kopyalanmaz.
- **`takvim(gun_sayisi?: int = 14)`:** `/api/calendar/unified`'ın birleşik etkinlikleri. Portal takvimi, özel dersler, SEBİT ödevleri ve ÖGEP/takım etkinlikleri, bugünden ileri N gün.
- **`ders_icerigi(ders?: str, hafta?: int)`:**
  - Güncel hafta `ders_icerikleri`'nden gelir; diğer haftalar `ders_icerikleri_haftalar`'dan.
  - Dönen içerik: dersin `text`, `items`, `cards` alanlarının okunur özeti.
  - Ders adları `normalize_course` ile eşlenir.
  - `ders` verilmezse güncel haftadaki derslerin listesi döner.
- **`notlar()`:** `gelisim_raporu` notları ve kazanım düzeyi `rubrics`, dönem adıyla birlikte. Eski yıl/dönem açıkça etiketlenir.

**Biçimlendirici:** `_fmt_scraped_data` diskteki gerçek biçimlere göre düzeltilir, böylece BM25 de bu verileri bulur:
- ders programı `rows`'tan
- ders içerikleri sözlükleri ve haftalar
- rubrikler
- takvim açıklamaları (`htmlToText` eşdeğeri; başlığı tekrarlıyorsa atılır)
- `ek_sayfalar` (yalnız `empty` olmayanlar)
- profil (sınıf, şube, okul; e-posta ve kimlik numarası yok)

**Ayrıca:** `ogrenci_verisi_ara` açıklaması artık doğruyu söyler. Ders programı ve sınav soruları yeni araçlara yönlendirilir.

**Doğrulama:** `pytest tests/test_assistant_ogrenci_araclari.py` gerçek biçimde, uydurma değerli fixture'larla şunları gösterir:
- iki bloklu tabloda Cuma saatleri doğru;
- "yarın" Istanbul'a göre çözülüyor;
- sınavlar `/api/exams` ile aynı listeyi veriyor;
- `ders_icerigi` belirli bir haftayı döndürüyor;
- biçimlendirici çıktısında ders programı satırları ve ders içeriği metni var.

### Görev 3: Diğer yerel kaynaklar — SEBİT, Tedy Books, platform ilerlemesi, videolar

**Files:** `src/assistant_tools.py`, `src/assistant_core.py`, yeni `src/assistant_kitaplar.py` (Tedy Books arama), yeni `tests/test_assistant_yerel_kaynaklar.py`.

- **SEBİT ödevleri:** `odev_listesi` artık `sebit_homework.json`'daki ödevleri de ayrı bir "SEBİT" bölümünde gösterir. `/api/sebit` mantığını kullanır.
- **`kitap_ara(sorgu, kitap?)`:** `books/<slug>/*.md` bölümlerinde arama yapar ve eşleşen pasajı kitap ve bölüm adıyla döndürür.
  - Bölüm eşlemesi `_book_chapters` / manifest ile aynıdır.
  - Atıf `kind: "tedy-kitap"`. Frontend bu sınıfı "Tedy Books" grubunda gösterir.
- **`platform_ilerlemesi()`:** EnglishCentral ve Achieve3000 ilerlemesini okunur özet olarak verir: tamamlanan, son etkinlik, düzey. Ham JSON gitmez.
- **`video_oner(konu, ders?)`:** `mebi_videos_discovered.json` ve `sebitv_discovered.json` üst verisinde arar ve başlık, ders, ünite, sınıf ve bağlantı döndürür. Bağlantı yalnız üst veride varsa verilir, uydurulmaz. Sınıf etiketlenir.

**Doğrulama:** `pytest tests/test_assistant_yerel_kaynaklar.py`, uydurma fixture'larla.

### Görev 4: MCP kapsamı ve görseller

**Files:** `src/assistant_tools.py` (`TOOL_ALLOWLIST`, `_KIND_BY_TOOL`, `ToolOutcome.images`), `src/assistant_core.py` (`chat_with_tools` araç sonucu içeriği), `src/dashboard_api.py` (yeni `GET /api/assistant/figure/<int:figure_id>`), `dashboard/src/components/SourcePanel.tsx` + SCSS, `dashboard/src/types.ts`; testler `tests/test_assistant_gorseller.py`, e2e `dashboard/tests/e2e/asistan-gorsel-kaynak.spec.ts`.

1. **İzin listesine eklenecekler:**
   - `program_getir` → `get_curriculum_program`
   - `ders_bilgisi` → `get_subject`
   - `video_listele` → `list_videos`
   - `video_getir` → `get_video`
   - `oer_getir` → `kb_get`

   Kind değerleri: program ve ders için `mufredat`, video için `mufredat`, oer için `oer`.
2. **Görseller:**
   - `ToolOutcome.images` alanı eklenir: `[{data, mimeType}]`, MCP sonucundaki görseller.
   - `chat_with_tools` görsel taşıyan bir sonucu `tool_result.content` içinde liste olarak gönderir: metin bloğu ve en çok 2 görsel bloğu (`{"type":"image","source":{"type":"base64","media_type":…,"data":…}}`). Model figürü görür.
   - Tek görsel 1,5 MB base64'ü aşarsa gönderilmez; metinde "görsel çok büyük" yazar.
3. **Arayüz:**
   - `figur_getir` atfının `locator`'ı `figure_id` taşır.
   - Yeni uç `GET /api/assistant/figure/<id>`: `require_auth`, yalnız full rol. `get_figure` üzerinden görseli bayt olarak döndürür; süreç içi LRU önbellek, 64 girdi.
   - `SourcePanel`, `figure_id` taşıyan kaynakta küçük bir görsel gösterir (`<img alt>` = figür başlığı; yoksa "Ders kitabı görseli").
4. **İstem:** `figur_ara`/`figur_getir` yönlendirmesi günceldir. Yeni araçlar kısa satırlarla anlatılır.

**Doğrulama:**
- pytest: görsel bloğun `tool_result`'a girdiği, büyük görselin elendiği ve yeni araçların ilan edildiği gösterilir.
- e2e: sahte `/api/assistant/chat` + sahte figür ucu ile `SourcePanel` görseli gösterir; axe ve IBM denetimleri yeşil kalır.

### Görev 5: Aileye özel pedagoji kaynağı

**Files:** `src/assistant_core.py`, `src/assistant_tools.py`, testler `tests/test_assistant_aile_kaynaklari.py`.

- `content/pedagoji/` için ayrı bir BM25 bölümü kurulur (aynı retriever sınıfı, ayrı indeks dizini).
- Araç `aile_kaynak_ara(sorgu)` yalnız okur `aile` iken ilan edilir. `declarations()` okuru parametre olarak alır; `chat()` okuru iletir. Öğrenciye (`ogrenci`) ve bilinmeyene ilan edilmez, çağrılsa bile reddedilir.
- Atıf `kind: "aile-kaynak"`.

**Doğrulama:** Öğrenci okurunun araç listesinde `aile_kaynak_ara` yok ve çağrısı reddediliyor; aile okurunda var ve sonuç dönüyor.

### Görev 6: İstem, reindex, belgeler ve canlı doğrulama

**Files:** `src/assistant_core.py` (`SYSTEM_PROMPT` "Hangi araca ne zaman uzanırsın"), `CLAUDE.md` (Asistan bölümleri), `docs/frontend-surface-designs.md` (Asistan §4.10 + değişiklik kaydı).

- İstem her yeni araca tek satırla yönlendirir. Mevcut istem testleri yeşil kalır, yeni yönlendirmeler için test eklenir.
- `src/reindex_assistant.py` çalışma ağacında test verisiyle koşar ve özet `dusen_dosyalar: []` verir.
- **Canlı doğrulama** (gerçek model, ücretli, en çok 6 çağrı, controller koşar, implementer koşmaz):
  - "yarın hangi dersler var"
  - "fen sınavım ne zaman"
  - "bu hafta matematikte ne işlediniz"
  - "Hobbit'te Bilbo ejderhayla nasıl konuşuyor"
  - "EnglishCentral'da ne durumdayım"
  - bir figür sorusu

  Her birinde doğru araç çağrılır ve cevap kaynaklıdır.

### Görev 7: 7. sınıf kitapları ve görselleri uçtan uca

**Bağımlılık:** CureoHub korpus göçü canlıya alınmış olmalı (`server_info.corpus_version` 1.5'ten büyük).

- Canlı doğrulama:
  - `kitap_listele` 7. sınıf için en az 17 kitap döndürür.
  - Bir 7. sınıf matematik sorusunda asistan kitap sayfasını `kitap_sayfa` ile okuyup kitabın adıyla atıf yapar.
  - Bir figür sorusunda görsel modele ulaşır ve Kaynaklar panelinde görünür.
- Bayat istem cümlesi temizlenir: "sınıfın kitabı korpusta yoksa" satırı kalır, ama kapsam notu CLAUDE.md'de güncellenir.

## Kapanış kriteri

- Tüm pytest ve Playwright süitleri yeşil.
- Denetimin boşluk listesindeki her madde ya kapandı ya da gerekçesiyle ertelendi; kapanış raporu denetim notuna eklenir.
- Canlı doğrulama çıktıları kapanış raporunda yer alır.
