# edupedia × TEDY — MCP orkestratörü ve kalıcı modül kataloğu (çatı tasarım)

- **Tarih:** 2026-09-13
- **Durum:** Onaylandı (kullanıcı, 2026-09-13) — alt proje planları bu spec'ten türetilir
- **Kapsam türü:** Çatı spec. Üç depoyu ve altı alt projeyi bağlayan sözleşmeleri sabitler; her alt proje
  kendi uygulama planıyla ilerler (bkz. §10).
- **Depolar:** `TED` (orkestratör + katalog + görüntüleyici + Asistan), `CureoPrivate`
  (`plugins/edupedia` + yüzey paketleri), `CureoHub` (yalnız belge/filo kaydı güncellemeleri).

## 1. Amaç

`edupedia`, Türkiye Yüzyılı Maarif Modeli'ne hizalı, tek dosyalık etkileşimli HTML öğrenim modülleri üretir.
Bugün yalnız Claude Code plugin'i olarak ve yalnız iki connector'la (maarif-mufredat, egitim-kaynak) çalışıyor;
çıktı yerel bir HTML dosyası, kalite kapıları istemcide koşuyor.

Bu tasarım üç şeyi aynı anda çözer:

1. **Web yüzeyleri:** claude.ai, Codex, Grok ve Gemini Spark'ta aynı derinlikte çalışmak. Bu yüzeylerde hook,
   alt-ajan ve (Codex/claude.ai dışında) script yok; bu yüzden iş akışının ağırlığı bir **MCP orkestratörüne** taşınır.
2. **Genişletilmiş filo:** müfredat ve OER çekirdeğine ek olarak anamnesis (uzun kaynak), Pexels (atıflı görsel),
   DergiPark / ERIC / OpenAlex (pedagoji kanıtı) ve minimax / comfyui (medya üretimi) sunucu tarafında kullanılır.
3. **Kalıcı katalog ve tam döngü:** modüller **tedy.online**'da, yalnız aile listesine açık bir katalogda yayınlanır;
   Işık'ın sınav ve ödevlerine bağlanır, modül içi ilerleme TED'e geri yazılır, TED Asistanı modülleri kaynak olarak kullanır.

## 2. Kullanıcı kararları (2026-09-13 beyin fırtınası)

| # | Soru | Karar |
|---|---|---|
| K1 | Connector kapsamı | Geniş filo; **ottoman-archives, devlet-arsivleri, tbmm, mevzuat hariç** |
| K2 | Hedef yüzeyler | claude.ai, Codex, Grok, Gemini Spark (web tabanlı) |
| K3 | Bilgi + kapıların taşınması | **MCP-merkezli orkestratör** |
| K4 | Federasyon | **Hibrit** — orkestratör yan filoyu sunucu tarafında çağırır; mufredat ve egitim-kaynak istemcide doğrudan da bağlanabilir |
| K5 | Teslim | **Kalıcı yayın kataloğu** → tedy.online |
| K6 | Görüntüleme | **Kapılı** |
| K7 | Kitle | **Yalnız mevcut aile listesi** (TED `USER_ROLES`) |
| K8 | TED entegrasyon derinliği | **Tam döngü** (katalog + ders bağlamı + ilerleme geri yazımı + Asistan) |
| K9 | Süreç | **Sözleşme önce, alt projeler sırayla** |
| K10 | Orkestratörün yeri | **TED'in içinde** (öneri ayrı servisti; kullanıcı TED'i seçti) |
| K11 | Medya üretimi | **Yalnız ucuz medya otomatik**; pahalı üretim açık onay ister |

Onaylanan tasarım bölümleri: §4 mimari, §5 sözleşmeler, §6–§8 kimlik/federasyon/bütçe, §9–§11 yüzey/test/sıra.

## 3. Mevcut durumdan ölçülmüş olgular

- **TED/tedy.online** tek öğrenci (Işık) için özel bir aile panosudur: Flask + Gunicorn (2 gthread işçisi × 4 iş parçacığı; §12b düzeltmesi) systemd **user**
  servisi, `0.0.0.0:8085`, HP (`hp-ai-node`), uzaktan yönetilen Cloudflare tüneli. Önyüz React 19 + Carbon,
  veri `output/` altında düz JSON. Giriş yalnız Google Sign-In; `USER_ROLES` 6 e-posta (`full` / `reader`).
  Tam yetkili `tdyK_` API anahtarları var. CSP / X-Frame-Options yok; modül bazlı ACL yok. Python 3.12;
  `mcp`, `fastmcp`, `uvicorn` kurulu değil.
- TED Asistanı zaten senkron bir MCP istemcisiyle (`src/mcp_client.py`) maarif-mufredat ve egitim-kaynak'ı kullanır
  (`src/assistant_tools.py` `TOOL_ALLOWLIST`).
- **edupedia 0.10.1:** 9 mod, 16 kapı (`validate_module.py`, 2.337 satır, yalnız stdlib), 17 referans (4.870 satır),
  `module-template.html` 693 KB (471 KB gömülü font, 131 KB motor). Şablonda `MODULE_DATA` yer tutucusu var;
  motor depolamayı `try/catch` ile degrade-safe kullanır; `postMessage` yok.
- Emekli `CureoHub/services/edupedia_site/app/gates/` 16 kapının sunucu tarafı kopyasını ve `run_gates(html)` →
  `quality_gates` sözlüğünü taşır (referans olarak yeniden kullanılabilir).
- Doppler `cureohub/dev_personal`'da mevcut: `MUFREDAT_MCP_API_KEY`, `EGITIM_KAYNAK_MCP_API_KEY`,
  `ANAMNESIS_MCP_API_KEY`, `PEXELS_MCP_API_KEY`, `MINIMAX_MCP_API_KEY`, `COMFYUI_MCP_API_KEY`,
  `TR_LITERATUR_MCP_API_KEY`, `OPENALEX_MCP_API_KEY`. ERIC için statik anahtar yok (sunucu yalnız OAuth;
  upstream `api.ies.ed.gov/eric` herkese açık).
- eric, pexels, minimax, comfyui, tr-literatur, openalex yönlendirme listeleri claude.ai / chatgpt.com / grok.com /
  googleusercontent kapsar; **anamnesis kapsamaz** (statik Bearer).
- Yüzey olguları: Grok özel talimat sınırı 4.000 karakter, özel connector ücretli planlarda; Gemini talimatları Gem'lerde,
  Spark özel uygulama MCP URL'siyle eklenir; Codex `.codex-plugin/plugin.json` + `skills/` + `mcp.json`.
  Web yüzeylerinde MCP prompt/resource desteği tutarlı değildir.

## 4. Mimari

```
 claude.ai · Codex · Grok · Gemini Spark · Claude Code
            │  OAuth 2.1 (Google girişi, aile listesi)
            ▼
 mcp.tedy.online ──► ted-mcp (TED deposu, ayrı ASGI süreci, 127.0.0.1:8090)
            │            ├─ rehber (vendored referanslar)
            │            ├─ bağlam (TED dashboard API'si, yalnız 127.0.0.1, `ted-mcp` etiketli tdyK_ anahtar)
            │            ├─ federasyon istemcileri (src/mcp_client.py) ──► mufredat · egitim-kaynak ·
            │            │                                                anamnesis · pexels · literatur ·
            │            │                                                openalex · minimax · comfyui · ERIC API
            │            ├─ derleyici (MODULE_DATA → module-template.html) + 18 kapı
            │            └─ katalog yazarı (output/modules/)
 modul.tedy.online ──► ted-mcp (host yönlendirmesi) — biletli, CSP'li statik modül sunumu
 tedy.online ────────► ted-dashboard (Flask) — Modüller sayfası, bilet, ilerleme API'si, Asistan
```

### 4.1 Bileşenler

1. **`ted-mcp` (orkestratör).** TED deposunda `src/mcp_server/`. Ayrı systemd user birimi `ted-mcp.service`
   (uvicorn, `127.0.0.1:8090`; port kararı §12b). Genel adlar `mcp.tedy.online` (`/mcp`, `/oauth/*`, `/.well-known/*`) ve
   `modul.tedy.online` (`/m/*`, `/taslak/*`) aynı sürece host yönlendirmesiyle gelir. TED'in veri dizinini,
   `USER_ROLES`'u (tek kaynak — `dashboard_api.py`'den yeni `src/roles.py` modülüne taşınır ve iki süreç de
   oradan import eder; `dashboard_api.py` import edilmez, çünkü Flask uygulamasını ve gizli anahtar denetimini
   yan etkiyle kurar), `src/json_utils.py` atomik yazımını ve
   `src/mcp_client.py`'yi paylaşır. **Yalnız araç** sunar.
2. **Modül deposu ve katalog.** Git dışı `output/` altında (üretilmiş, öğrenci adı taşıyabilir): `output/modules/<slug>/v<N>/index.html` + `output/modules/index.json`. Tedy Books'un slug
   doğrulama (`^[a-z0-9]+(?:-[a-z0-9]+)*$`) ve `realpath` yol-taşma korumaları aynen uygulanır. Taslaklar
   `output/edupedia_drafts/<taslak_id>/`, çalıştırmalar `output/edupedia_runs/<run_id>/`.
3. **Korumalı görüntüleyici.** `modul.tedy.online` modülü biletle ve sıkı CSP ile sunar; tedy.online "Modüller"
   sayfası modülü `sandbox="allow-scripts"` iframe'de gösterir.
4. **İlerleme köprüsü.** Modül → `postMessage` → dashboard → `POST /api/modules/<slug>/progress` (oturum) →
   `output/module_progress.json`. Geri yükleme ters yönde `edupedia:restore`.
5. **Asistan.** Katalog künyesi, `verification` iddiaları ve ilerleme özeti indekse girer; yerel `modul_ara` aracı.
6. **Federasyon.** Yan filo sunucu tarafında; ERIC upstream API'si doğrudan (anahtarsız) çağrılır.
7. **edupedia plugin'i.** İnce istemci + tek kaynaktan türetilen yüzey paketleri (§9).

### 4.2 Tek-yazar kuralı

| Dosya | Tek yazar | Okurlar |
|---|---|---|
| `output/modules/index.json`, `output/modules/<slug>/…` | ted-mcp | dashboard, Asistan |
| `output/module_progress.json` | dashboard (Flask) | ted-mcp (`edupedia_ilerleme`), Asistan |
| `output/edupedia_media_ledger.json` | ted-mcp | — |
| `output/ted_mcp_oauth.sqlite3` (istemci/kod/token, yalnız hash) | ted-mcp | — |

İki süreç aynı dosyaya yazmaz; okumalar atomik yazılmış dosyayı görür.

### 4.3 Tipik akış

1. Kullanıcı: "Işık'ın cuma günkü fen sınavı için modül hazırla."
2. `edupedia_rehber('akis')` → araç sırası ve kurallar.
3. `edupedia_baglam(gun=7)` → yaklaşan sınav/ödevler, sınıf.
4. `edupedia_kapsam(ders, sinif, konu)` → doğrulanmış kazanımlar, kitap sayfaları, figür adayları, OER özeti,
   `run_id`, kapsam manifestosu.
5. Gerekirse `edupedia_kaynak_oku`, `edupedia_gorsel`, `edupedia_medya`, `edupedia_pedagoji_kaniti`.
6. Model `MODULE_DATA`'yı yazar (rehber parçalarına göre).
7. `edupedia_derle(run_id, module_data)` → kapı raporu; başarısızsa model düzeltir, tekrar derler.
8. `edupedia_onizle(taslak_id)` (isteğe bağlı) → `edupedia_yayinla(taslak_id, ted_link)`.
9. Modül tedy.online'da Modüller sayfasında ve bağlı sınav kartında görünür; Işık çözer; ilerleme TED'e yazılır.

## 5. Sözleşmeler

### 5.1 Araç yüzeyi (v1, 14 araç)

Büyük içerik (HTML, görsel baytı, tam kitap sayfası) **asla** araç yanıtıyla modele dönmez. Her yanıt
`mcp_verified:false`, uygun yerde `caveat` ve (getirim yapan araçlarda) `coverage` manifestosu taşır.

| Araç | Girdi | Çıktı / davranış |
|---|---|---|
| `edupedia_durum()` | — | sürüm, `app_revision`, kapı sayısı, filo sağlık özeti, bütçe kalanı |
| `edupedia_rehber(bolum?, ara?)` | `bolum` ∈ {`akis`, `modlar`, `segmentler`, `etkilesim`, `pedagoji`, `carbon`, `svg`, `ses`, `mufredat`, `soru`, `sinav`, `zenginlestirme`, `kalite`} (vendored 17 referansın bölüm eşlemesi alt proje 2 planında sabitlenir) veya serbest `ara` | ≤ 8 KB rehber parçası; kaynak vendored referanslar |
| `edupedia_baglam(gun=7)` | gün aralığı | yaklaşan sınav/ödevler (id, ders, konu, tarih), sınıf; yalnız `full` rol |
| `edupedia_kapsam(ders, sinif, konu? , kazanim_kodu?)` | ders + sınıf zorunlu | doğrulanmış kazanımlar (kod+metin), kitap `document_id`+sayfa+kısa alıntı, figür adayları, OER özeti (lisanslı), `run_id`, `coverage` |
| `edupedia_kaynak_oku(run_id, soru, top_k≤8)` | | kapsamı `edupedia:run:<run_id>` ile sınırlı pasajlar (`doc_id::idx` atıflı) |
| `edupedia_gorsel(run_id, istek, tercih?)` | | varlık kimlikleri (`asset_id`, kaynak, lisans/atıf, boyut); zincir: kitap figürü → Pexels → minimax görsel |
| `edupedia_medya(run_id, tur, istek, tahmin=false, onay_belirteci?)` | `tur` ∈ `ses`, `muzik`, `video` | §8 bütçe kuralları; `asset_id` ya da `onay_gerekli` + tahmini maliyet + belirteç |
| `edupedia_pedagoji_kaniti(konu, dil?)` | | ERIC + DergiPark + OpenAlex'ten ≤ 5 kanıt özeti (atıflı) |
| `edupedia_derle(run_id, module_data)` | `module_data` JSON | şema doğrulama → varlık gömme → derleme → 16 kapı; `taslak_id`, kapı raporu, bayt boyutu |
| `edupedia_onizle(taslak_id)` | | `https://tedy.online/moduller/taslak/<taslak_id>` (aile girişi ister) |
| `edupedia_yayinla(taslak_id, ted_link?, slug?)` | yalnız tüm FAIL'siz taslak | katalog kaydı (`slug`, `version`, `url`) |
| `edupedia_katalog(ders?, sinif?, durum?)` | | katalog kayıtları (künye düzeyinde) |
| `edupedia_ilerleme(slug, version?)` | | toplanmış ilerleme özeti |
| `edupedia_kaldir(slug)` | | yumuşak kaldırma (`status: removed`) |

**Hibrit kuralı:** model mufredat / egitim-kaynak'ı doğrudan çağırmış olsa bile `edupedia_derle` bir
`edupedia_kapsam` `run_id`'si ister — müfredat dayanağı orkestratörde kayıtlı olmadan derleme yapılmaz.

### 5.2 MODULE_DATA

- **Şema otoritesi:** `CureoPrivate/plugins/edupedia/skills/carbon-edupedia/references/module-architecture.md §2`
  ve `assets/module-template.html` motoru. İkisi `ted-mcp`'ye **birebir** kopyalanır; kaynağı gösteren
  `PROVENANCE.md` + sha256 ve bir eşitlik testi eşlik eder. Kopyalandıktan sonra **otorite ted-mcp'dir**;
  CureoPrivate'teki referanslar kaldırılır (§9.3).
- **Eklenen alanlar:**
  - `meta.assets: [{asset_id, slot}]` — derlemede `data:` URI olarak gömülür.
  - `meta.tedLink: {kind: "exam" | "homework", id}` — isteğe bağlı.
  - `meta.attributions` — **derleyici üretir**, model yazmaz (PhET, Pexels, egitim-kaynak, MEB kitap atıfları).
  - Mevcut `verification` bloğu (G-VERIFY) aynen.

### 5.3 Katalog kaydı (`output/modules/index.json`)

```json
{
  "slug": "fen5-maddenin-halleri", "version": 2, "status": "active",
  "title": "...", "subject": "Fen Bilimleri", "gradeLevel": "5. Sınıf", "mode": "QUIZ",
  "outcomes": ["FB.5.4.1.1"], "frame_source": {"kind": "textbook", "document_id": 197, "pages": "112-120"},
  "gates": {"pass": 16, "warn": 0, "fail": 0}, "coverage": {"maarif-mufredat": "hit", "...": "..."},
  "ted_link": {"kind": "exam", "id": "..."}, "run_id": "...", "bytes": 712345,
  "created_by": "drmahirkurt@gmail.com", "created_at": "2026-09-13T18:00:00Z"
}
```

Sürümler değişmez (immutable); yeni yayın `version+1` üretir. `removed` kayıt dosyayı silmez.

### 5.4 Görüntüleme bileti

- Dashboard (oturum, `full` rol): `GET /api/modules/<slug>/v<N>/ticket` → `{url, exp}`.
- Bilet: `HMAC-SHA256(EDUPEDIA_TICKET_SECRET, email|slug|version|exp)`, TTL 10 dk.
  `url = https://modul.tedy.online/m/<slug>/v<N>?t=<bilet>&e=<exp>&u=<email-hash>`.
- Taslak önizleme aynı mekanizmayla `/taslak/<taslak_id>`.
- `modul.tedy.online` yanıt başlıkları:
  - `Content-Security-Policy: default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; font-src data:; media-src data:; connect-src 'none'; frame-ancestors https://tedy.online; base-uri 'none'; form-action 'none'`
  - `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Cache-Control: private, no-store`,
    `X-Robots-Tag: noindex`.
- Geçersiz/süresi dolmuş bilet → 403, gövdede yalnız "Bağlantının süresi doldu; tedy.online'dan yeniden açın".

### 5.5 İlerleme köprüsü (v1)

**Modül → ebeveyn:**

```json
{"type": "edupedia:progress", "v": 1, "slug": "...", "version": 2,
 "segmentId": "q1", "event": "answer", "correct": true, "attempts": 1, "xp": 15, "ts": 1789400000000}
```

`event` ∈ `answer`, `segment_complete`, `module_complete`, `ready`.

**Ebeveyn → modül:** `{"type": "edupedia:restore", "v": 1, "state": {...}}` (yalnız `ready` alındıktan sonra).

**Doğrulama (dashboard):** iframe `sandbox="allow-scripts"` ve `allow-same-origin` **olmadan** yüklenir; bu yüzden
`event.origin === "null"` görünür. Kabul koşulu: `event.source === iframe.contentWindow` **ve** `slug`/`version`
iframe'in açtığı modülle eşleşir **ve** şema geçerli. Diğer her mesaj yok sayılır.

**Kayıt:** `POST /api/modules/<slug>/progress` (oturum; yalnız `full`), sunucu şemayı yeniden doğrular,
sürüm başına toplar (deneme sayısı, doğru oranı, tamamlanma, son erişim).

**Motor değişikliği:** şablon motoru olayları yayar ve `edupedia:restore`'u uygular; `window.parent === window`
iken (bağımsız açılış) köprü sessizce kapalıdır. Yeni bir kapı (`G-BRIDGE`) köprünün yalnız bu iki mesaj tipini
ve yalnız `window.parent`'a gönderdiğini denetler. (Kapı sayısı: mevcut 16 + `G-BRIDGE` + `G-ATTRIB` (§7) = **18**.)

## 6. Kimlik ve güvenlik

### 6.1 OAuth 2.1 (mcp.tedy.online)

- RFC 8414 AS metadata, RFC 9728 PRM (`/.well-known/oauth-protected-resource` + `/mcp` yol ekli varyant),
  401'de `WWW-Authenticate: Bearer resource_metadata=…`.
- `redirect_uri` güveni origin düzeyinde değil, **kesin geri-çağırma URI'si** düzeyindedir (bir origin'in başka
  bir yolu sorgu dizesini, dolayısıyla kodu, başkasına verebilir). Varsayılan liste:
  `https://claude.ai/api/mcp/auth_callback`, `https://claude.com/api/mcp/auth_callback`,
  `https://chatgpt.com/connector_platform_oauth_redirect`, `https://grok.com/connectors/oauth/callback`
  (belgeden alındı, canlı bağlantıyla doğrulanmadı — alt proje 6'da doğrulanır); Gemini için yalnız
  `https://oauth-redirect.googleusercontent.com/r/user_bound_custom-mcp-<rakamlar>-<genel host, noktalar _>`;
  loopback `http://127.0.0.1`, `http://localhost`, `http://[::1]` (her port, her yol; RFC 8252). Ek kesin URI'ler
  `TED_MCP_EXTRA_REDIRECT_URIS` (virgülle ayrılmış; loopback dışında yalnız `https`). `https://vscode.dev/redirect`
  ve `https://insiders.vscode.dev/redirect` varsayılan listede **yoktur**: kodu `state`'in seçtiği başka bir host'a
  (ör. `*.github.dev`) iletirler (ölçüldü, 2026-09-14); gerekirse yalnız `TED_MCP_EXTRA_REDIRECT_URIS` ile eklenir
  (VS Code masaüstü loopback kullanır). Her URI kanonik olmalıdır (yalnız ASCII; boşluk/kontrol karakteri,
  userinfo, fragment, büyük harf şema/host, loopback dışı açık port yok; yeniden serileştirince kendisi) ve sorgusunda `code`, `state`, `iss`, `error`, `error_description`, `error_uri` bulunamaz.
- DCR açık ve **kalıcıdır**: her kayıt rastgele bir `client_id` alır; `redirect_uris` (1–5) ve `client_name`
  (≤ 100 karakter; kontrol, biçim (ör. bidi yön denetimi, sıfır genişlikli birleştirici), vekil ve satır/paragraf
  ayırıcı karakter içeremez) saklanır. Tavan **50000** kayıt: tavanda yeni kayıt gelince önce hiç kod üretmemiş
  ve yaşı `2 × FORM_TTL_SECONDS`'ı (20 dk; giriş ve karar adımlarının ikisini de kapsar) aşan **en eski** kayıtlar
  yer açacak kadar silinir; kod üretmiş istemci asla silinmez; silinebilecek kayıt yoksa kayıt
  `400 invalid_client_metadata` ile reddedilir. Kayıt selinde asıl savunma kenardaki hız sınırıdır (alt proje 3:
  IP başına 10 sn'de 60 istek ≈ dakikada 360): tek bir IP 20 dakikalık taban içinde en çok ~7200 istemci
  kaydedebilir, bu tavanın çok altındadır, dolayısıyla tek kaynaklı kilitlenme mümkün değildir; depolama maliyeti
  önemsizdir.
  `/oauth/authorize` ve `/oauth/token` yalnız kayıtlı `client_id` kabul eder (aksi `invalid_client`);
  `redirect_uri` kayıtlı URI'lerden biriyle tam eşit olmalıdır (loopback'te port hariç), aksi hata sayfası —
  yönlendirme yapılmaz.
- `/oauth/authorize`: TED'in `GOOGLE_CLIENT_ID`'si ile Google Sign-In; `id_token` sunucuda doğrulanır;
  e-posta `USER_ROLES`'ta **ve** rol `full` değilse reddedilir. Girişten sonra kod **otomatik üretilmez**: ikinci
  sayfa istemci adını, doğrulanmış tam `redirect_uri`'yi ve e-postayı gösterir; kod yalnız **Onayla** ile üretilir
  (rol burada yeniden denetlenir), **Reddet** kayıtlı adrese `error=access_denied` gönderir. Giriş ve karar
  formlarının imzalı durumları tek kullanımlıktır. Onay sayfaları istek başına CSP taşır
  (`default-src 'none'`; Google Identity Services için yalnız `accounts.google.com`; `form-action 'self'
  <issuer origin> <doğrulanmış redirect origin>`; `frame-ancestors 'none'`) ve `X-Frame-Options: DENY`,
  `Referrer-Policy: no-referrer`, `Cache-Control: no-store`.
  `TED_MCP_EXTRA_FORM_ACTION_ORIGINS` (virgülle ayrılmış, varsayılan boş) `form-action` yönergesinin sonuna ek kesin
  `https` origin'ler ekler: her giriş kanonik bir origin olmalıdır (küçük harf `https://host[:port]`; yol, sorgu,
  fragment, userinfo, joker, sondaki `/` ve açık `:443` yok; loopback ve `http` yok) ve geçersiz tek bir giriş
  sunucunun başlamasını durdurur. Ayar yalnız formun yönlendirme zincirini açar; kodun gideceği adres kesin
  `redirect_uri` listesiyle sınırlı kalır.
- `resource` verilirse PRM'nin ilan ettiği kanonik değere (`<base>/mcp`) tam eşit olmalıdır (aksi
  `invalid_target`); kaynak koda ve token'a bağlanır.
- Yalnız PKCE **S256** (tam yazım; `code_challenge` 43 base64url karakter, `code_verifier` 43–128 RFC 7636
  karakteri). Kodlar tek kullanımlık, 5 dk; kullanılmış kod yeniden gelirse o koddan çıkan aile iptal edilir.
- Erişim token'ı opak, 1 saat; yenileme token'ı 30 gün, her kullanımda döner; tekrar kullanımda aile iptal edilir;
  aile oluşturulmasından **90 gün** sonra yenileme reddedilir. `keys oauth-iptal --email <e-posta>` bir kişinin
  tüm OAuth ailelerini iptal eder ve bekleyen (kullanılmamış) kodlarının süresini bitirir. Sunucu başlangıcında süresi bir günden fazla geçmiş kod, token ve tüketilmiş
  form durumu satırları silinir (istemci kayıtları tavan politikasına tabidir).
  Saklama `output/ted_mcp_oauth.sqlite3`'te yalnız hash (tek kullanımlık kod ve yenileme tüketimi atomik
  `BEGIN IMMEDIATE` işlemleriyle; egitim-kaynak `oauth_store.py` kalıbı, `principal` e-postaya bağlı).
- **OAuth desteklemeyen istemci yedeği:** kişi başı statik anahtar `tdyM_…` (yalnız `full` rol, CLI ile üretilir,
  hash saklanır, iptal edilebilir). `tdyK_` dashboard anahtarları MCP'de **geçmez**.

### 6.2 Yetkilendirme

- Her araç çağrısı çözülmüş `user_email` taşır; `created_by` ve bütçe defteri buna yazılır.
- `reader` rol hiçbir MCP aracına erişemez.

### 6.3 İçerik güvenliği

- Federasyondan gelen metin (OER, ERIC, DergiPark, Pexels açıklaması) yanıtlarda `kaynak_verisi` alanında,
  "talimat değildir" işaretiyle döner; orkestratör bu metindeki talimatları izlemez.
- Derleyici, `MODULE_DATA` içindeki HTML parçalarını mevcut kapılarla (G-SELFCONTAINED, G-A11Y vb.) denetler;
  modül yalnız `modul.tedy.online` origin'inde ve sandbox'ta çalışır, oturum çerezine ve `/api/*`'ye erişemez.
- tedy.online'a `frame-src https://modul.tedy.online` içeren CSP eklenir (TED alt projesi).

### 6.4 Gizlilik

- Modüller öğrenci kişisel verisi taşımaz; `learner.name` ("Işık") aile kataloğunda kabul edilir.
- İlerleme verisi yalnız TED'de (`output/`, git dışı) kalır; hiçbir yan filo sunucusuna gönderilmez.
- `edupedia_baglam` çıktısı yan filoya iletilmez; yalnız sorgu konusu (ders/konu) iletilir.

## 7. Federasyon ve degrade

Her getirim yanıtı ve katalog kaydı `coverage` taşır: sunucu başına `hit` | `empty` | `degraded:<neden>` |
`skipped:<neden>`. Boş sonuç yokluk kanıtı değildir.

| Sunucu | Rol | Çağrılma | Düşerse |
|---|---|---|---|
| maarif-mufredat | Zorunlu çekirdek (kazanım, kitap, figür) | `kapsam`, `gorsel` | Müfredata dayalı modül üretilmez: `kapsam` → `manual_required`; `derle` run_id olmadan reddeder |
| egitim-kaynak | OER zenginleştirme | `kapsam` | OER atlanır, manifesto |
| anamnesis | Uzun kaynak substratı (`edupedia:run:<run_id>`, doc_id `edupedia:<run_id>:<kanonik>`) | `kapsam`, `kaynak_oku` | `output/edupedia_runs/<run_id>/` sayfaları üzerinde yerel BM25 |
| pexels | Atıflı fotoğraf | `gorsel` | minimax görsel (bütçe) → yazar SVG'si |
| tr-literatur (DergiPark) | TR pedagoji kanıtı | `pedagoji_kaniti` | kanıt katmanı eksik, manifesto |
| ERIC (upstream API) | ABD pedagoji kanıtı | `pedagoji_kaniti` | aynı |
| openalex | Genel akademik kanıt | `pedagoji_kaniti` | aynı |
| minimax | Ucuz medya (ses, görsel) + onaylı video/müzik | `gorsel`, `medya` | medya eklenmez |
| comfyui | Pahalı GPU üretimi | `medya` (onaylı) | medya eklenmez |

- **Anahtarlar:** Doppler `cureohub/dev_personal` → TED `.env` (hazırlama betiği; değer asla depoya ya da loga girmez).
  Yeni env adları: `ANAMNESIS_MCP_API_KEY`, `PEXELS_MCP_API_KEY`, `MINIMAX_MCP_API_KEY`, `COMFYUI_MCP_API_KEY`,
  `TR_LITERATUR_MCP_API_KEY`, `OPENALEX_MCP_API_KEY`, `EDUPEDIA_TICKET_SECRET`, `EDUPEDIA_MEDIA_MONTHLY_USD`.
- **Zaman:** çağrı başına 25 sn, araç başına toplam 60 sn; paralel fan-out iş parçacığı havuzuyla; comfyui video
  asenkron iş kimliğiyle.
- **Lisans:** egitim-kaynak `quote_allowed=false` kaynaktan uzun alıntı yok; PhET CC BY-NC ve Pexels atıfları
  derleyicinin ürettiği `meta.attributions` ile altbilgiye girer; MEB kitabı için kısa ve sayfa atıflı alıntı.
  Yeni kapı `G-ATTRIB`: kullanılan her lisanslı varlığın atıfı altbilgide var (toplam 18 kapı, bkz. §5.5).
- Okul öncesi `D<n>` kodları egitim-kaynak'ta bilinçli olarak `outcome_code_unknown` döner (2026-09-13 R64);
  `kapsam` bunu degrade olarak işaretler, mufredat dayanağı etkilenmez.

## 8. Medya bütçesi

- Defter `output/edupedia_media_ledger.json`: `{ts, user, run_id, server, tur, tahmini_usd, sonuc}`.
- Aylık tavan `EDUPEDIA_MEDIA_MONTHLY_USD` (varsayılan **10**).
- **Otomatik (tavan içinde):** minimax seslendirme (modül başına ≤ 3.000 karakter), minimax görsel (modül başına ≤ 2).
- **Açık onaylı:** minimax müzik ve video, comfyui her şey. Akış: `edupedia_medya(..., tahmin=true)` →
  `{onay_gerekli, tahmini_usd, onay_belirteci}` (15 dk, kullanıcı + run_id'ye bağlı) → kullanıcı onaylar →
  `edupedia_medya(..., onay_belirteci)`.
- Tavan aşılırsa `budget_exceeded` + kalan tutar; sessiz düşüş yok.
- **Ses klonlama ve ses tasarımı hiçbir koşulda çağrılmaz.**
- **Varsayım:** fiyat tablosu (`src/mcp_server/pricing.json`) sağlayıcı belgelerinden elle girilir; hiçbir sunucu
  gerçek maliyet döndürmediği için defter **tahmindir** ve bu `edupedia_durum`'da açıkça yazar.

## 9. Yüzey paketleri ve plugin

### 9.1 Tek kaynak

- Derin rehberin tek kaynağı `ted-mcp` (`src/mcp_server/rehber/`, vendored referanslardan).
- Her yüzey yalnız **başlangıç talimatı** taşır: `CureoPrivate/plugins/edupedia/surfaces/bootstrap.md`,
  ≤ 3.500 karakter. İçerik: `edupedia_rehber('akis')` ile başla; araç sırasını izle; HTML'i kendin yazma;
  `edupedia_yayinla` sonucu olmadan "yayınlandı" deme; kapsam manifestosunu ve kapı raporunu kullanıcıya bildir;
  medya onayını kullanıcıdan al.

### 9.2 Yüzeyler

| Yüzey | Türetilen paket (`surfaces/<yüzey>/`) | Kurulum |
|---|---|---|
| claude.ai | skill zip (`SKILL.md` = bootstrap) | Skill yükle + custom connector `https://mcp.tedy.online/mcp` |
| Codex | `.codex-plugin/plugin.json` + `skills/edupedia/SKILL.md` + `mcp.json` | plugin kur; OAuth |
| Grok | `grok-workspace.md` (bootstrap) | Workspace talimatı + grok.com/connectors → Custom |
| Gemini Spark | `gemini-gem.md` (bootstrap) | Gem talimatı + Spark Connected Apps → custom app |
| Claude Code | ince plugin | `/plugin install edupedia@cureonics-marketplace` |

Paketler bir üretim betiğiyle `bootstrap.md`'den türetilir; `check_drift` bayatlığı yakalar.

### 9.3 CureoPrivate edupedia 1.0.0

- `fleet.yaml`: `tedy` (`https://mcp.tedy.online/mcp`, interaktif OAuth, `auth_env: null`) + isteğe bağlı doğrudan
  `maarif-mufredat` ve `egitim-kaynak`.
- **Kaldırılır:** yerel `validate_module.py` kopyası ve testleri, `module-auditor` ajanı, PostToolUse doğrulama
  hook'u, 17 referansın plugin kopyası, `build_claude_ai_skill.py`'nin eski gövdesi (yeni üretim betiğiyle değişir).
- **Kalır:** SessionStart preflight (yalnız `tedy` sağlığı), 5 komut (orkestratör akışına işaret eden kısa metinler).
- Sürüm **0.10.1 → 1.0.0** (kırıcı: yayın yolu ve connector'lar değişti). Sürüm üç yerde senkron.
- CureoHub `CLAUDE.md` `edupedia_site` maddesindeki "plugin yayınlamaz" ifadesi yeni duruma göre güncellenir.

## 10. Alt projeler ve sıra

| # | Alt proje | Depo | Çıktı / kabul |
|---|---|---|---|
| 1 | Bu çatı spec | TED | Kullanıcı onayı |
| 2 | Orkestratör çekirdeği | TED | `durum`, `rehber`, `baglam`, `kapsam`, `kaynak_oku` + OAuth + vendored şablon/kapılar; ağsız pytest yeşil |
| 3 | `mcp.tedy.online` altyapısı | TED + Cloudflare | Tünel ingress, DNS, Google OAuth origin, `.env` hazırlama, `ted-mcp.service`; gerçek token'la `initialize` + `tools/list` |
| 4 | Derleme, kapılar, medya, yayın + katalog/görüntüleyici/ilerleme | TED | `derle`, `gorsel`, `medya`, `pedagoji_kaniti`, `onizle`, `yayinla`, `katalog`, `ilerleme`, `kaldir`; `modul.tedy.online`; Modüller sayfası; köprü; G-BRIDGE + G-ATTRIB |
| 5 | Asistan entegrasyonu | TED | indeks + `modul_ara`; Asistan yayınlanan modülü bulur |
| 6 | Plugin 1.0.0 + yüzey paketleri | CureoPrivate (+ CureoHub belge) | dört yüzeyde bağlan + bir modül üret |

Her alt proje `writing-plans` ile kendi planını alır. 3 ve 4'ün altyapı adımları, uygulandıkları alt projenin
planında yer alır.

## 11. Test stratejisi

- **TED pytest, ağsız** (`unshare -rn pytest`): araçlar sahte `McpClient` ile; OAuth akışı (DCR, S256, rol reddi,
  yenileme dönüşü, tekrar kullanım iptali); bilet HMAC ve süresi; `modul.tedy.online` başlıkları; ilerleme ucunun
  rol ve şema denetimi; bütçe defteri ve onay belirteci; degrade kuralları (her sunucu için `coverage`); tek-yazar
  kuralı; slug/yol-taşma.
- **Golden derleme testleri:** her mod için bir `MODULE_DATA` fixture'ı → derlenen HTML 18 kapıdan geçer;
  vendored motor/şema sha256'sı `PROVENANCE.md` ile eşit.
- **Playwright:** Modüller sayfası render; iframe biletle açılır; `postMessage` ilerleme olayı kaydedilir;
  `edupedia:restore` önceki cevabı geri getirir; yabancı kaynaklı mesaj yok sayılır. TEDY tuzaklarına karşı:
  her mutasyon kontrolünden önce `npm run build` ve çıkış kodu (boru olmadan) okunur; her yokluk iddiasından önce
  yüzeyin kendi elemanının varlığı kanıtlanır; `waitForTimeout` yasak.
- **Canlı uçtan uca (alt proje 4 sonu):** gerçek OAuth token'ıyla `initialize` + `tools/list`; gerçek bir sınavdan
  QUIZ modülü üret → yayınla → biletle aç → bir cevap ver → `module_progress.json`'da gör → (alt proje 5) Asistan
  bulur.
- **Yüzey kabulü (alt proje 6):** claude.ai, Codex, Grok, Gemini Spark'ın her birinde connector ekle, bir modül üret,
  yayın bağlantısını aç.

## 12. Kapsam dışı

- Çok kullanıcılı hesaplar, paylaşım anahtarları, herkese açık katalog.
- egitim-kaynak Faz 2 hizalaması, `kb_patterns` içeriği, okul öncesi kısa kazanım kapı kalibrasyonu.
- ottoman-archives, devlet-arsivleri, tbmm, mevzuat.
- Ses klonlama / ses tasarımı.
- `CureoHub/services/edupedia_site`'ın yeniden canlandırılması (yalnız kapı kodu referans).
- TED'in mevcut tarama ve dashboard işlevlerinde, bu entegrasyonun gerektirmediği değişiklikler.

## 12b. Plan aşamasında yapılan spec güncellemeleri (2026-09-13)

- **`edupedia_baglam` veri yolu:** `src/dashboard_api.py` import edilemez (import sırasında `os.chdir`,
  `load_env`, `DASHBOARD_SECRET_KEY` yoksa `RuntimeError`, Flask `app` kurulumu). Sınav listesi `/api/exams` içinde
  takvim + not tablosu + içerik haritası + zenginleştirme önbelleğinden türetildiği için çoğaltmak ~200 satırlık
  ikinci bir kaynak yaratır. **Karar:** `ted-mcp`, dashboard'un kendi `/api/exams`, `/api/homework`,
  `/api/student/profile` uçlarını yalnız `http://127.0.0.1:8085` üzerinden `ted-mcp` etiketli bir `tdyK_` anahtarla
  (`TED_DASHBOARD_API_KEY`) okur. Dashboard düşerse `baglam` → `degraded:dashboard_unreachable`; akışın geri kalanı
  etkilenmez. Anahtar yalnız `.env`'de, yalnız loopback'te kullanılır.
- **Token deposu:** JSON yerine SQLite (`output/ted_mcp_oauth.sqlite3`) — tek kullanımlık kod ve yenileme
  tüketimi JSON'da atomik yapılamaz.
- **OAuth yönlendirme güveni ve açık onay (2026-09-14, kimlik yüzeyi güvenlik incelemesi, S1b):** §6.1'deki origin
  izin listesi kesin geri-çağırma URI listesiyle değiştirildi (Grok URI'si canlı doğrulanana dek belgeye dayanır);
  DCR kalıcı ve istemci başına `client_id`'li oldu; Google girişinden sonra açık Onayla/Reddet adımı, tek
  kullanımlık form durumları, onay sayfası CSP'si, PKCE sınırları, kod yeniden kullanımında aile iptali,
  `resource` bağlama, 90 günlük aile ömrü, `keys oauth-iptal` ve başlangıç temizliği eklendi.
- **S1b inceleme düzeltmesi (2026-09-14):** `https://vscode.dev/redirect` ve `https://insiders.vscode.dev/redirect`
  varsayılan geri-çağırma listesinden çıkarıldı. Canlı ölçüm: `code=probe123` ve hedefi
  `https://attacker-probe-7q9x.github.dev/steal` olan bir `state` ile iki sayfa da `302` ile kodu o host'a iletti
  (`vscode://` ve loopback'e de iletir); açık DCR ile herkes bu URI'yi "Visual Studio Code" adıyla kaydedip gerçek
  bir Microsoft adresi gösteren onay sayfası üretebildiği için Onayla adımı korumaz. Yalnız
  `TED_MCP_EXTRA_REDIRECT_URIS` ile eklenebilir. Aynı incelemede DCR tavanı 500'den 50000'e çıkarıldı ve "24 saatten
  eski" temizliği yerine `2 × FORM_TTL_SECONDS` (20 dakika; iki onay adımının tamamı) taban yaşını aşmış kodsuz en
  eski kayıtların tahliyesi getirildi (ölçüm: 499 anonim kayıt 4,5 sn'de tavanı doldurup yeni bağlayıcı kurulumunu
  24 saat engelliyordu; kenar hız sınırıyla tek bir IP taban içinde en çok ~7200 kayıt yapabilir).
- **`edupedia_baglam` okul portalı başlıkları (SP2 son inceleme, 2026-09-14):** `edupedia_baglam`, sınav ve
  ödev başlıklarını TED'in kendi okul portalı verisinden üst düzeyde döner. Bu, §6.3 kapsamındaki federasyon
  metni değil TED verisidir ve bilinçli olarak `kaynak_verisi` içine sarılmaz (kabul edilen artık risk:
  öğretmenin yazdığı bir başlık düşük risklidir).
- **§7 zaman bütçesinin uygulanışı (SP2 son inceleme, 2026-09-14):** araç gövdeleri 16 iş parçacıklı ayrı bir
  sınırlayıcıda çalışır; kimlik doğrulama, token ve depo yolları böylece her zaman iş parçacığı bulur. Her araç
  60 sn'lik bir son tarih hesaplar ve her federasyon çağrısının zaman aşımı kalan bütçeyle sınırlanır (en çok
  25 sn); bütçenin karşılayamadığı çağrı yapılmaz ve `degraded:zaman_asimi` olarak bildirilir.
- **Port (alt proje 3, 2026-09-14):** §4.1'deki `127.0.0.1:8087` hp-ai-node'da Docker `climax-sabnzbd` kapsayıcısı
  (`climax-acquisition`) tarafından tutuluyor (ölçüm 2026-09-14); 8090–8095 boş. **Karar:** `ted-mcp`
  `127.0.0.1:8090`'a bağlanır. Kod varsayılanı (`http_app.DEFAULT_PORT`) ile izlenen birim dosyası
  (`ted-mcp.service`, `Environment=TED_MCP_PORT=8090`) aynı değeri taşır; `tests/test_deploy_units.py` ikisini eşitler.
- **Topoloji ile sırların ayrımı (alt proje 3):** Gizli olmayan değerler (`TED_MCP_HOST`, `TED_MCP_PORT`,
  `TED_MCP_PUBLIC_BASE_URL`, `TED_MCP_ALLOWED_HOSTS`, `TED_DASHBOARD_API_URL`) izlenen birimin `Environment=`
  satırlarındadır; `.env` yalnız sırları taşır (`TED_MCP_FORM_SECRET`, `TED_DASHBOARD_API_KEY` ve `API_KEYS`'teki
  `ted-mcp:` girdisi, filo anahtarları). systemd'de `EnvironmentFile=` aynı adı `Environment=`'ın üstüne yazdığından
  topoloji adları `.env`'de bulunmaz; `python -m src.mcp_server.env_prep durum` bunu denetler. `TED_MCP_PROJECT_ROOT`
  üretimde tanımsızdır, çünkü `keys` CLI'si kökü kodun konumundan alır ve servis aynı kökü kullanmalıdır.
- **Cloudflare (alt proje 3):** `.env`'deki `CLOUDFLARE_ZONE_ID` ve `CLOUDFLARE_TUNNEL_ID` `cureonics.com` bölgesine
  ve eski `pi-dashboard` tüneline aittir (ölçüm 2026-09-14). `mcp.tedy.online` rotası `src/mcp_server/tunnel_route.py`
  ile eklenir: bölge ve tünel adla çözülür; ingress birleştirilir (yeni kural catch-all'dan hemen önce, mevcut kurallar
  düşmez); yazmadan önce kuru çalıştırma farkı, kural sayısı kilidi ve "tam bir eklenen, sıfır silinen" kilidi; tüm
  yapılandırmanın yedeği; DNS `mcp.tedy.online` → `<tünel-id>.cfargotunnel.com` proxied CNAME. CureoHub
  `scripts/sync_hp_tunnel_ingress.py` yeniden kullanılmadı: kaldırma kipi yok, DNS hatasında çıkış kodu 0, bölgeyi adla
  çözmüyor, üç yabancı env dosyasını yüklüyor.
- **Google origin (alt proje 3):** Onay sayfası GSI'yı JavaScript geri çağrı kipinde kullanır (`data-callback`;
  `data-login_uri` yok). Google Cloud konsolunda yalnız **Authorized JavaScript origin** `https://mcp.tedy.online`
  eklenir; yönlendirme URI'si gerekmez. Canlı kabul bu insan adımına bağlı değildir: CLI'yle `full` rol için üretilmiş
  gerçek bir `tdyM_` anahtarıyla (§6.1 yedeği) yapılır.
- **Tek-yazar notu (alt proje 3):** `keys` CLI'si servisle aynı SQLite dosyasına yazar; SQLite işlemleriyle güvenlidir
  ve §4.2'nin JSON dosyaları için koyduğu kuralı değiştirmez (CLI `ted-mcp`'nin parçasıdır).
- **Güvenlik kapısı (alt proje 3):** Otomatik güvenlik incelemesi kullanılamadığından kimlik yüzeyinin ayrı bir gözden
  geçirenle incelenmesi temiz çıkmadan hiçbir genel DNS kaydı ya da ingress kuralı oluşturulmaz.
- **Ölçüm düzeltmesi (alt proje 3):** §3'teki "Gunicorn (1 işçi)" yanlıştı; kurulu birim `--workers 2 --worker-class
  gthread --threads 4` (ölçüm 2026-09-14). Depodaki izlenen `ted-dashboard.service` kopyası da kurulu birimle eşitlenir.
- **Onay sayfası `form-action` ek origin'leri (alt proje 3, 2026-09-14):** `TED_MCP_EXTRA_FORM_ACTION_ORIGINS`
  eklendi (varsayılan boş; varsayılan CSP bayt bayt aynı). Gerekçe: alt proje 6'nın canlı yüzey kabulünde bir
  geri-çağırma sayfası kodu `form-action`'da adı geçmeyen başka bir origin'e yeniden yönlendirebilir (Chrome
  `form-action`'ı yönlendirme zinciri boyunca uygular) ve onay gönderimi engellenir; ayar bunun canlı oturumda
  yapılandırmayla giderilmesini sağlar. Girişler `TED_MCP_EXTRA_REDIRECT_URIS` gibi kapalı-başarısızlıkla doğrulanır;
  ayar gizli değildir ve `.env`'e değil birim dosyasına yazılır.
- **Canlı kabul (alt proje 3, 2026-09-15):** Güvenlik kapısı TEMİZ — implementer olmayan bağımsız gözden geçiren
  (Bölüm A kod, Bölüm B dağıtım), son inceleme `8eb51e4`, dağıtılan `40cf244`; ertelenen düşük bulgular (RFC 7009
  `/oauth/revoke`, `tdyM_` son kullanma, R3, R6) SDD defterinde denetleyici `Ruling:` satırlarıyla kayıtlı. anamnesis:
  anahtar yapılandırıldı, `hit`. Kenar hız sınırı dal A (`/oauth/register|authorize|token`, `/mcp`; IP başına 10 sn'de
  60; sayım `cf.colo.id` + `ip.src`, IPv6 /64 gruplaması Cloudflare belgesinde belirtilmiyor — belirsiz, tek kaynak
  iddiası yalnız IPv4 için; dağıtık kayıt seli denetleyici `Ruling:` satırıyla kabul; yedek
  `tedy.online-ratelimit-20260915T073956Z-0028.json`). `hp-ai-node` ingress 52 → 53 kural, `mcp.tedy.online` →
  `http://127.0.0.1:8090`, proxied CNAME (yedek `hp-ai-node-config-20260915T074557Z-2faa.json`). Genel uçta: PRM 200,
  `/mcp` kimliksiz 401 + `WWW-Authenticate`, `/oauth/token` 16 385 bayt → 413, CORS `https://claude.ai` 204, kenar hız
  sınırı 429, `tdyM_` anahtarıyla `initialize` (`2025-06-18`, `TEDY edupedia` `0.1.0`) + `tools/list` beş araç; test
  anahtarı `sp3-kabul-20260914` iptal edildi. Google JavaScript origin: bekliyor (insan adımı).

### Alt proje 4 plan güncellemeleri (2026-09-14)

Kaynak: `docs/superpowers/plans/2026-09-14-ted-mcp-derleme-yayin-katalog.md` → "Plan kararları". §14.2 gereği
bu maddeler uygulanmadan önce denetleyici tarafından onaylanır (kullanıcı süreç yönetimini denetleyiciye devretti).

- **§3 / §4.2 / §13 — dashboard süreçleri:** `ted-dashboard` 2 gunicorn işçi süreci × 4 iş parçacığıdır. Tek-yazar
  (dashboard) `output/module_progress.json`'ı iki süreçten yazar; oku-değiştir-yaz `fcntl.flock` yan kilidiyle
  (`output/module_progress.json.lock`) sıralanır, dosya atomik değiştirilir.
- **§4.1 — port:** `ted-mcp` loopback portu `8090`'dır (8087 ilgisiz bir Docker konteynerinde; alt proje 3 taşır).
- **§5.1 — araç imzaları:** `edupedia_medya(run_id, tur, istek, tahmin=false, onay_belirteci?, is_kimligi?)` —
  `is_kimligi` asenkron video yoklamasıdır; araç sayısı 14 kalır. `edupedia_derle` `module_data`'yı nesne veya JSON
  metni olarak kabul eder; UTF-8 JSON olarak **≤ 400.000 bayt**, üstü `cok_buyuk`. İkili içerik araç çağrısıyla
  gelmez; varlıklara yalnız `asset_id` ile başvurulur. `/mcp` istek gövdesi sınırı (`TED_MCP_MAX_BODY_BYTES`, S1a) ≥ 2.097.152 bayttır.
- **§5.1 — hibrit kuralı:** `edupedia_derle` `curriculum` ve `verification` bloklarını zorunlu tutar;
  `verification.frame_source.document_id` çalıştırmanın `textbook` çerçevesiyle, `curriculum.outcomes[].code`
  çalıştırmanın doğrulanmış kazanımlarıyla eşleşir. Koşullu kapılar hiçbir zaman sessizce atlanmaz.
- **§5.2 — motor ve varlıklar:** vendored şablon değişmez; motor farkları `src/mcp_server/sablon.py` çapa
  yamalarıdır (ilerleme köprüsü, `visual.kind: image|video`, segment `audio`, varlık bloğu, atıf altbilgisi).
  `meta.assets[].slot` = `<teachSegmentId>.visual` | `<teachSegmentId>.audio`. Veriler motor script'inden önce
  `<script type="application/json" id="edupedia-varliklar">` bloğunda `data:` URI olarak gömülür; gömülü ham toplam
  ≤ 2.400.000 bayt, görsel başına ≤ 400.000 bayt (en uzun kenar 1280 px JPEG). `MODULE_DATA` derlemede çıplak
  anahtarlı JS nesne literali olarak yazılır.
- **§5.3 — katalog:** `output/modules/index.json` = `{"surum": 1, "moduller": [kayıt, …]}`; kayda `taslak_id`,
  `sha256`, `removed_at`, `removed_by` eklenir. `edupedia_yayinla`'nın `url`'si
  `https://tedy.online/moduller/<slug>/v<N>`'dir. `EXAM` modu yayınlanmaz (telif). `taslak` slug'ı ayrılmıştır;
  slug ≤ 60 karakter, sürüm 1–9999.
- **§5.4 — bilet:** doğrulayıcı e-postayı görmediği için MAC `u = sha256(küçük_harf(email))[:32]` üzerinden kurulur:
  modül `HMAC-SHA256(EDUPEDIA_TICKET_SECRET, "m|<slug>|v<N>|<u>|<exp>")`, taslak
  `HMAC-SHA256(EDUPEDIA_TICKET_SECRET, "t|<taslak_id>|<u>|<exp>")`. ted-mcp `u`'nun güncel `full` roster üyesine ait
  olduğunu da denetler; TTL içinde yeniden kullanım kabul edilir. Doğrulama sırası: yol biçimi → bilet → kayıt.
  Kaldırılmış veya bulunmayan modül 404.
- **§5.5 — köprü:** `answer` olayına `item` (0–999) eklenir; v1'de `answer` yalnız soru setlerinden (mcq,
  checkpoint karma soruları) gelir, diğer etkileşimler `segment_complete` üretir. `edupedia:restore.state` =
  `{"answers": ["<segmentId>#<item>", …], "done": ["<segmentId>", …], "xp": <int>}`; motor ilk tamamlanmamış
  segmente konumlanır. Modül `slug`/`version`'ı kendi URL yolundan (`/m/<slug>/v<N>`) okur; `postMessage` hedef
  origin'i derleme sabiti `EDUPEDIA_PARENT_ORIGIN` (varsayılan `https://tedy.online`); modül `restore`'u yalnız
  `event.source === window.parent` ve `event.origin === EDUPEDIA_PARENT_ORIGIN` iken uygular. Dashboard ayrıca
  `event.origin === "null"` ister. İlerleme kişi başına saklanır; MCP'ye yalnız toplamlar döner.
- **§6.3 — dashboard CSP:** `Content-Security-Policy: frame-src https://modul.tedy.online https://accounts.google.com`.
- **§7 — atıf ve filo:** MEB kitap/sayfa atfı öğrenci yüzeyine değil `sourceCitation`/`verification`'a yazılır
  (G-VOICE öğrenci yüzeyinde `ders kitab…` ve `sayfa <n>` kalıplarını yasaklar); `G-ATTRIB` gömülü her varlığın
  atfını ve `license` taşıyan her `grounding` kaynağını altbilgide arar. tr-literatur'un genel adı yoktur; ted-mcp
  `TR_LITERATUR_MCP_URL` (varsayılan `http://127.0.0.1:8327/mcp`) kullanır. comfyui yalnız minimax yapılandırılmamışken
  onaylı yedektir.
- **§8 — bütçe:** defter kaydına `miktar` eklenir (modül başı ses karakteri ve görsel sayısı sınırı); fiyat kalemi
  `dogrulandi: false` ise otomatik yol kapalıdır ve onay istenir.

### Alt proje 5 plan güncellemeleri (2026-09-14)

Kaynak: `docs/superpowers/plans/2026-09-14-ted-asistan-modul-entegrasyonu.md` → "Plan kararları". §14.2 gereği
bu maddeler uygulanmadan önce denetleyici tarafından onaylanır (kullanıcı süreç yönetimini denetleyiciye devretti).

- **§4.1 madde 5 / §10 satır 5 — modül indeksi:** Asistan'ın modül indeksi dosyasız ve süreç içidir
  (`src/assistant_modules.py`). Belgeler `output/modules/index.json` künyesi, taslak kaydındaki `dogrulama` özeti
  ve `ProgressStore.summary` toplamlarından kurulur; `index.json` ve `output/module_progress.json`'ın stat imzası
  (`st_ino`, `st_size`, `st_mtime_ns`) değişince ya da anlık görüntü 60 sn'yi aşınca yeniden kurulur. Yayın,
  kaldırma ve ilerleme yazımı böylece süreç yeniden başlatılmadan görünür; `AssistantRuntime.reindex()` indeksi
  zorla yeniler. Asistan'ın genel dosya indeksi `output/modules/**`, `output/edupedia_drafts/**`,
  `output/edupedia_runs/**`, `module_progress.json`, `*.lock`, `edupedia_media_ledger.json` ve
  `ted_mcp_oauth.sqlite3*`'ü okumaz.
- **§4.2 — okurlar:** Asistan ayrıca `output/edupedia_drafts/<taslak_id>/taslak.json`'ın okurudur. Asistan hiçbir
  modül, ilerleme ya da indeks dosyası yazmaz; iki gunicorn süreci arasında kilit gerekmez.
- **§5.1 / §5.3 — iddia özeti:** `edupedia_derle` taslak kaydına
  `dogrulama: {"surum": 1, "iddialar": [{"iddia", "karar", "dayanak": {"document_id", "page"} | {"kaynak", "lisans"}}]}`
  (≤ 20 iddia, iddia ≤ 300 karakter) yazar. Katalog kaydı değişmez. Asistan özeti yalnız taslak `sha256`'sı
  katalog kaydınınkiyle eşitken kullanır; aksi hâlde `iddia_durumu: "uyusmazlik"`, özet yoksa `"kayit_yok"`.
- **§5 — `modul_ara` ve modül atfı:** `modul_ara(sorgu?, ders?, sinif?)` durumları `ok`, `eslesme_yok`,
  `modul_yok`, `katalog_yok`, `katalog_okunamadi`; yalnız etkin kayıtların slug başına en yüksek sürümü; taslak ve
  kaldırılmış sürüm dönmez; modele gösterilen gövde (atıf işaret satırları + JSON) ≤ 3.900 karakter. Atıf `{"kind": "modul", "label", "locator": {"slug",
  "version"}, "snippet", "confidence"}`; arayüz bağlantıyı yalnız doğrulanmış `/moduller/<slug>/v<N>` rotasına
  kurar ve bilet o rota açılırken alınır (§5.4). Asistan bilet ya da `modul.tedy.online` URL'si üretmez.
- **§6.3 — içerik güvenliği:** `modul_ara`'da iddia dayanaklarının `kaynak` ve `lisans` metinleri tek üst düzey
  `kaynak_verisi` nesnesinde döner; künye, iddia cümleleri, kitap dayanağı ve ilerleme toplamları TED içeriğidir.
  Gömülü varlık atıfları Asistan'a verilmez. Model metnine giren serbest metinde `[S<n>]` → `(S<n>)`.
- **§6.4 — gizlilik ve LLM bağlamı:** ilerleme Asistan'ın LLM bağlamına yalnız sürüm başı toplam
  (`cevaplanan_soru`, `dogru_orani`, `tamamlandi_mi`, `son_erisim_gunu`) olarak ve yalnız oturumlu `full` rollü kişi
  soruyorsa girer; `tdyK_` API anahtarı, `ASSISTANT_API_KEY` ile `/v1/*` ve test atlatması ilerleme almaz. Atıflar
  ilerleme taşımaz. Yan filo aracına ilerleme alan adlarını taşıyan argümanla çağrı yapılmaz; başka sözcüklerle
  yeniden yazılmış ilerleme bu denetimle yakalanmaz (kabul edilen kalan risk, sistem istemi kuralıyla azaltılır).
- **§11 — alt proje 5 testleri:** ağsız modül indeksi, dürüst durumlar, geçersizleşme (gerçek `CatalogWriter` ile),
  gizlilik ve içerik güvenliği; Playwright: modül atfı → `/moduller/<slug>/v<N>` → bilet yalnız açılışta; canlı:
  Asistan alt proje 4'te yayınlanan modülü bulur ve biletle açar.

## 13. Varsayımlar ve riskler

| Risk / varsayım | Etki | Azaltma |
|---|---|---|
| TED dashboard'u 2 gthread işçisi × 4 iş parçacığı (8 eşzamanlı yuva) | Dashboard'da ilerleme/bilet çağrıları hafif; ağır iş ted-mcp'de | Ağır işler dashboard'a girmez |
| Cloudflare tüneli uzaktan yönetiliyor | Yeni hostname'ler yerel config'le eklenemez | `CLOUDFLARE_API_TOKEN` ile API üzerinden, bölge (`tedy.online`) ve tünel (`hp-ai-node`) **adla** çözülerek birleştirici ingress + DNS (`src/mcp_server/tunnel_route.py`; alt proje 3, §12b) |
| Google OAuth istemcisi yeni origin ister | `mcp.tedy.online` girişi çalışmaz | Google Cloud konsolunda yetkili **JavaScript** origin ekleme (yönlendirme URI'si gerekmez) — insan adımı, alt proje 3'te |
| Grok özel connector ücretli plan | Grok yüzeyi plan gerektirir | Kurulum belgesinde açıkça yazılır |
| Medya fiyatları tahmini | Bütçe gerçek faturadan sapabilir | `pricing.json` elle; `edupedia_durum`'da "tahmin" etiketi |
| anamnesis `STRICT_COLLECTION` | Kapsamsız çağrı reddedilir | Her çağrı `edupedia:run:<run_id>` koleksiyonuyla |
| Vendored şablon/kapılar sapar | Kapılar ile motor uyuşmaz | sha256 eşitlik testi + `PROVENANCE.md`; güncelleme tek yönlü ted-mcp'ye |
| TED'in amacı genişliyor | Aile panosu artık bir üretim hattı da taşır | Tek-yazar kuralı, ayrı süreç, ayrı hostname'ler; `USER_ROLES` tek kaynak |
| TED `main` origin'den 1 commit önde | — | Bu spec yerel commit; push kullanıcı kararı |

## 14. Kabul ölçütleri (çatı)

1. Kullanıcı bu spec'i onaylar.
2. §5 sözleşmeleri, alt proje planlarında değiştirilmeden kullanılır; değişiklik gerekirse önce bu spec güncellenir.
3. Alt proje 4 sonunda canlı uçtan uca akış (§11) kanıtlanır.
4. Alt proje 6 sonunda dört yüzeyin her birinde bir modül üretilip tedy.online'da açılır.
