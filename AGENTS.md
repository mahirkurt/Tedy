# TEDY Repo Çalışma Rehberi

Bu dosya depo kökünden aşağıdaki tüm dizinlerde geçerlidir. Daha alt düzeyde
bir `AGENTS.md` varsa kendi kapsamı için bu rehberi geçersiz kılar.

## Projenin Amacı ve Gerçek Giriş Noktaları

TEDY; okul portalları ile eğitim platformlarından veri toplayan, üretilen JSON
durumunu öğrenci paneli ve asistan için kullanan bir Python otomasyon
uygulamasıdır. Flask API aynı zamanda React panelini ve yerel/hibrit eğitim
asistanını sunar. Google Classroom, Calendar ve Drive yazma yolu yoktur.

- `src/run_sync.py`: güncel tarama orkestratörü; portal bölümlerini ve ayrı
  platform tarayıcılarını çalıştırır, `output/health.json` yazar ve asistan
  indeksini best-effort yeniler. Dış Workspace yazması yoktur.
- `src/dashboard_api.py`: Flask API, auth, JSON veri erişimi, asistan uçları,
  Tedy Books ve `dashboard-dist/` içindeki SPA için üretim giriş noktasıdır.
- `dashboard/src/main.tsx`, `dashboard/src/App.tsx`, `dashboard/src/routes.ts`:
  React 19 + Vite + Carbon Design System panelinin bootstrap, kabuk ve rota
  kaynaklarıdır.
- `src/main.py`: yalnız iskelet/smoke girişidir; üretim uygulaması değildir.

Önce `README.md`, bu dosyayı ve `CLAUDE.md`yi oku; önemli bir iddiayı
manifest, giriş noktası ve testlerle doğrula. Kod ile dokümantasyon çelişirse
çalıştırılabilir kodu esas al ve sapmayı bildir.

## Dizin Haritası

- `src/`: tarayıcılar, doğrulama, Flask API ve asistan.
- `dashboard/src/`: TypeScript/React bileşenleri, hook'lar, context, `utils/` ve
  tema; `dashboard/src/asistan/` canlı asistan arayüzüdür (Carbon AI Chat
  uyarlayıcısı; tek asistan arayüzü budur).
- `tests/`: Python birim, şema, idempotency, auth ve API testleri.
- `dashboard/tests/e2e/`: Playwright API ve gerçek tarayıcı akışları; tasarım
  denetimleri (axe, IBM Equal Access, görsel, ARIA, 4K, dokunma hedefi) ve
  depoya işlenmiş PNG tabanları da buradadır.
- `dashboard/tests/*.test.ts`: `node:test` birim testleri (`npm run test:birim`).
- `books/`: Markdown bölüm dosyaları ve isteğe bağlı `book.json` manifestleri;
  yayın sözleşmesi için `books/README.md`yi izle.
- `docs/`: tasarım/uygulama planları ve operasyon runbook'ları. Tarihli planı
  mevcut durum kanıtı sayma.
- `output/`: çalışma zamanı verisi, tracker, ekran görüntüsü ve loglar. Üretilir,
  özeldir ve Git'e eklenmez.

## Kurulum ve Komutlar

Python en az 3.9 ister (`pyproject.toml`); test takımı `tomllib` kullandığı için
3.11+ gerektirir, `.venv` 3.12'dir. Yerel akış `.venv` kullanır. `requirements.txt` şu an
tam üretim bağımlılık envanteri değildir; temiz kurulumun yalnız bu dosyayla
çalışacağını varsayma ve paket değişikliği için önce onay al.

```bash
# Hedefli ve tam Python doğrulaması
pytest tests/test_dashboard_api.py
pytest

# Panel geliştirme ve statik doğrulama
cd dashboard && npm run dev       # :3000, /api -> :8085
cd dashboard && npm run lint
cd dashboard && npm run build     # çıktı: dashboard-dist/

# E2E; önce güncel üretim bundle'ını oluştur
cd dashboard && npm run build
cd dashboard && env -u ANTHROPIC_API_KEY npx playwright test  # test Flask sunucusu: :8286 (TEDY_E2E_PORT)
cd dashboard && npm run test:birim   # node:test; dashboard-dist'te Carbon AI'lı demet ister

# Tedy Books sözleşmesi
python src/check_books.py
python src/check_books.py <slug>
```

Flask geliştirme sunucusu `python src/dashboard_api.py` ile `:8085` üzerinde
başlar. Üretimde Gunicorn, `src.dashboard_api:app` WSGI girişini kullanır;
depo içindeki `ted-dashboard.service` ile kurulu systemd tanımının aynı
olduğunu canlı işlem öncesinde ayrıca doğrula.

## Kod ve Veri Sözleşmeleri

- Python'da mevcut 4 boşluk, `snake_case` ve küçük, hedefli fonksiyon stilini;
  TypeScript'te strict ayarları ve mevcut ESLint kurallarını koru.
- Yeni panel rotasını `dashboard/src/routes.ts` üzerinden tanımla ve bileşen
  eşlemesini `App.tsx` ile uyumlu tut. Rotanın `secondary`, `readerAccess`
  (varsayılan ret), `offPortal` ve `showInNav` bayraklarını bilinçli seç; sayfayı
  `asistan/sayfaBaglami.ts` içindeki `SAYFA_YOLLARI`'na (arka uçtaki
  `SAYFA_ADLARI`'nın aynası) ve tasarım denetimlerinin sayfa listelerine ekle.
  Carbon bileşenlerini ve mevcut tema tokenlarını yeniden kullan.
- İstemci API çağrılarında oturum çerezleri için `credentials: 'include'`
  sözleşmesini koru. Genel veri okumalarında `useApi<T>` örüntüsünü izle.
- Kritik JSON tracker/durum yazımlarında `src/json_utils.py` içindeki atomik
  yazma yolunu kullan. Mevcut idempotency ve hash tabanlı değişiklik takibini
  bozma.
- Ders adları panele giderken `normalize_course()` (`src/course_names.py`)
  kullan; portalın ham adlarını toplama katmanında gereksiz yere dönüştürme.
- Orkestratör seviyesinde bağımsız scraper hataları izole edilebilir; iç
  fonksiyonlara kanıtsız geniş `try/except` katmanları ekleme.
- `src/discover_*.py` dosyaları araştırma aracıdır, üretim akışına kendiliğinden
  bağlama. HTML, ekran görüntüsü veya oturum verisini rapora dökme.

## Tasarım

Panel ya da edupedia modülü arayüzüne dokunan her iş
`docs/tedy-ui-ux-talimatnamesi.md`'nin §0'ıyla başlar: kim neyi hangi sırayla
okur, öncelik sırası ve belge haritası oradadır. Bileşen seçimi §4, Carbon'dan
bilinçli sapmalar §11 (S1…), "bitti" tanımı ve kapılar §12, ölçülmüş borçlar §13.

- Öncelik: anayasa D1–D4 ve İ1–İ9 (`docs/frontend-design-principles.md`) >
  talimatname > yüzey tasarımları (`docs/frontend-surface-designs.md`) >
  bileşen rehberi (`docs/carbon-bilesen-rehberi.md`) >
  `.claude/skills/tedy-carbon/SKILL.md` > `.claude/skills/carbon-builder/`
  (IBM, vendorlu, değiştirilmez) > Carbon'un genel rehberi. Bir Carbon önerisi
  ölçülmüş ya da kullanıcının seçtiği TEDY kuralını sessizce ezmez; çelişkiyi
  §11'e yaz.
- Carbon'a ait bileşen, prop, ikon adı ya da içe aktarma yolunu ezberden yazma:
  `carbon` MCP'sine sor (`code_search` + `filters.component_type: "React"`,
  `docs_search` ve `anchor_url` ile atıf) ya da `dashboard/node_modules`'ta
  doğrula. Değişen `.tsx`/`.scss` için `code_audit` (`framework: "react"`,
  `ibmProducts: "no"`) danışma amaçlıdır; protokol talimatname §10'dadır.
- Her UI değişikliği testiyle gelir. Kasıtlı görsel değişiklikte farkı oku,
  sonra tabanları güncelle; axe ve IBM Equal Access temiz, telefonda dokunma
  hedefi ≥ 44 px, yatay kaydırma yok.
- `dashboard-dist/` ana checkout'ta canlı servis edilir: ana checkout'ta
  `npm run build` tedy.online'ı hemen değiştirir. Denemeyi worktree'de derle.

## Kimlik Doğrulama ve Gizlilik

Panel, Google Identity credential'ını Flask tarafında doğrular, hesap
allowlist'ini uygular ve kullanıcı durumunu Flask session çerezinde tutar.
`require_auth` hem session hem yapılandırılmış API anahtarını kabul eder;
asistanın `/v1/*` uçları ayrı bearer anahtarı ister. Yeni özel API uçlarını
sunucu tarafında koru; yalnız UI gizlemesine güvenme.

- `TEST_AUTH_BYPASS=1` yalnız otomatik yerel test içindir; üretim komutuna veya
  kalıcı yapılandırmaya koyma.
- `.env`, portal çerezleri ve API anahtarlarını okuma gerekmiyorsa açma;
  değerlerini hiçbir çıktı, test fixture'ı, doküman veya commit'e taşıma.
- `output/` öğrenci profili, not, ödev, program, oturum ve aktivite verisi
  içerebilir. Sorunu mümkünse şema, sayaç ve redakte edilmiş örneklerle incele;
  ham kayıtları veya kişisel tanımlayıcıları yanıtta gösterme.
- Loglara credential, bearer token, cookie, kişisel e-posta veya ham model
  bağlamı yazma. Kitap/telifli içeriği de gereksiz yere toplu kopyalama.

## Değişiklik ve Operasyon Disiplini

Her işte önce `git status --short --branch` çalıştır. Bu checkout dosya izin
bitlerinden kaynaklanan geniş mode-only diff gösterebilir; içerik farkı ile
izin farkını ayır ve kullanıcı istemedikçe bunları normalize etme. İlgisiz
değişiklikleri koru; `git add .`, reset veya toplu temizlik kullanma.

Cron/systemd değişikliği, servis yeniden başlatma, paket ekleme/kaldırma ve
üretim deploy'u için açık onay al.

Değişiklikten sonra riske uygun en dar testi, ardından ilgili lint/build/test
kapısını çalıştır. UI değişikliklerinde Playwright veya gerçek tarayıcıyla
etkileşimi doğrula. Doküman değişikliklerinde en azından
`git diff --check -- <dosya>` kullan. Commit istenirse yalnız hedef dosyaları
adıyla stage et ve `feat:`, `fix:`, `docs:`, `chore:` gibi mevcut Conventional
Commit biçimini kullan.

## Cursor Cloud specific instructions

- Kurulum `.venv` ve `dashboard/node_modules` üretir, ardından `npm run build`
  ile `dashboard-dist/` oluşur. Kilit dosyası `dashboard/package-lock.json`;
  `IBM_TELEMETRY_DISABLED=true npm ci` kullan (telemetri kapalı olmak zorunda;
  `dashboard/tests/paket-telemetri.test.ts` demette telemetri ucu arar).
- API, `DASHBOARD_SECRET_KEY` olmadan import sırasında düşer. Kurulum, `.env`
  yoksa yalnız yerel bir anahtar yazar (gitignored, mode 600). Var olan `.env`
  dosyasının üzerine yazma. Boş `DASHBOARD_SECRET_KEY` export etme:
  `load_env()` zaten set edilmiş bir değişkeni değiştirmez, boş değer `.env`'i ezer.
- Geliştirme sunucuları: `DASHBOARD_COOKIE_SECURE=0 .venv/bin/python src/dashboard_api.py`
  (`:8085`, üretim demeti) ve `cd dashboard && npm run dev` (`:3000`, `/api`
  8085'e gider). Oturumsuz `GET /api/auth/me` 401 döner; bu, API'nin ayakta
  olduğunun işaretidir.
- `pytest` bu `.env` ile çalışır. Panel kapıları `cd dashboard && npm run lint`,
  `npm run build` ve `npm run test:birim`. Playwright Chromium
  `npx playwright install chromium` ile kurulur; `capraz-tarayici` projeleri için
  `npx playwright install webkit firefox` da gerekir. Playwright'ı
  `env -u ANTHROPIC_API_KEY` ile çalıştır.
- Portal taraması (`src/run_sync.py`) `PORTAL_USERNAME` / `PORTAL_PASSWORD` ister
  ve bulut geliştirme döngüsünün parçası değildir. Asistan `ANTHROPIC_API_KEY`
  ister; testler bu anahtarı bilerek siler.
- Uygulama `TZ`'yi `src/env_loader.py` içinde `Europe/Istanbul` yapar. VM saati
  UTC kalabilir.
