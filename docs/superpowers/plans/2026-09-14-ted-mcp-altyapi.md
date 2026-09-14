# mcp.tedy.online altyapısı — Uygulama Planı (alt proje 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Alt proje 2'de yazılan `ted-mcp`'yi hp-ai-node'da loopback'e bağlı bir systemd user servisi olarak çalıştırmak, `.env`'i sırları yazdırmadan hazırlamak, bağımsız bir güvenlik incelemesinden geçtikten sonra `https://mcp.tedy.online`'ı `hp-ai-node` tüneline birleştirerek eklemek ve gerçek bir `tdyM_` anahtarıyla genel uçta `initialize` + `tools/list` kanıtlamak.

**Architecture:** Önce kod (ağsız testli): port kararı (`8087` dolu → `8090`), `.env` hazırlama CLI'si (`env_prep`), izlenen birim dosyası (`ted-mcp.service`), birleştirici Cloudflare rota CLI'si (`tunnel_route`), Cloudflare kenar hız sınırı CLI'si (`edge_ratelimit`, güvenlik incelemesi F4). Sonra, sırayla: **güvenlik kapısı Bölüm A** (S1 düzeltme dalgası + AP2 son incelemesi temiz; kod) → yerel `main` ileri alma + `origin/main` push → `.env` + dashboard yeniden başlatma → servis + loopback doğrulama → **güvenlik kapısı Bölüm B** (dağıtım incelemesi) → kenar hız sınırı → ingress + DNS → genel kabul → Google JavaScript origin (insan adımı). Her üretim adımı `[OPERASYON]` etiketli; ön koşul, beklenen sonuç ve geri alma içerir.

**Tech Stack:** Python 3.12.3 (TED `.venv`), mcp 1.28.1, starlette 1.3.1, uvicorn 0.51.0, requests, pytest; systemd user manager; Cloudflare API v4 (tünel yapılandırması + DNS); curl 8.5.0, jq, dig, doppler CLI.

**Spec:** `docs/superpowers/specs/2026-09-13-edupedia-tedy-orkestrator-design.md` (bağlayıcı; §4.1, §4.2, §6, §7, §10 AP3 satırı, §11, §12b, §14). Biçim ve konvansiyonlar: `docs/superpowers/plans/2026-09-13-ted-mcp-orkestrator-cekirdegi.md`.

## Global Constraints

- Spec §14.2: sözleşme değişikliği gerekirse **önce spec** güncellenir, sonra kod. Bu plan §4.1 portunu değiştirir (Task 1).
- **Sıralama kuralı:** Hiçbir genel DNS kaydı ya da ingress kuralı şu üçü sağlanmadan oluşturulmaz: (1) S1 güvenlik düzeltme dalgası (S1a + S1b) dalda birleşmiş ve kapsamlı yeniden incelemesi temiz; (2) AP2'nin son, tüm-dal incelemesi temiz; (3) Task 9 Bölüm A ve Bölüm B `TEMİZ` (dağıtılan `HEAD` kapının incelediği **H**'dir; sonrasında kimlik yüzeyinde incelenmemiş değişiklik yok). `main`'e ileri alma ve `origin/main` push'u (Task 6) ile dashboard yeniden başlatması (Task 7) Bölüm A'dan sonra gelir. Kenar hız sınırı (Task 10) DNS kaydından **önce** uygulanır; açık pencere oluşmaz. Güvenlik incelemesi raporu: `/mnt/thunderbolt/workspaces/TED/.superpowers/sdd/2026-09-13-ted-mcp-orkestrator-cekirdegi/security-review-auth.md`. Otomatik güvenlik incelemesi eklentisi kullanılamaz; kapı atlanamaz, "geçti" varsayılamaz.
- **Yürütme sırası:** Task 1 → 2 → 3 → 4 → 5 → **9 Bölüm A** → 6 → 7 → 8 → **9 Bölüm B** → 10 → 11 → 12 → 13 → 14. Task 9 belgede numarasının yerinde durur; iki bölümü bu sırayla koşulur. Task 6 ve Task 7'deki üretim adımları **denetleyici onaylı; kapıya bağlıdır**.

**Ek ön koşul (controller ruling, 2026-09-14):** alt proje 5 planının Görev 2'si (`docs/superpowers/plans/2026-09-14-ted-asistan-modul-entegrasyonu.md` — Asistan genel dizininin modül/taslak/run/ilerleme dosyalarını hariç tutması) Görev 6'dan ÖNCE bu dalda commit'lenmiş olmalıdır; aksi hâlde canlı ted-mcp'nin `output/edupedia_runs/` altına yazdığı ders kitabı sayfa metni 15 dakikalık cron yeniden dizinlemesiyle Gemini'ye taşınır. Görev 6 başlamadan `git log --oneline --grep 'Asistan'` ile doğrulanır.
- `ted-mcp` yalnız `127.0.0.1:8090`'a bağlanır; `0.0.0.0` asla. `127.0.0.1:8087` başka bir servise aittir, dokunulmaz.
- Gizli değerler hiçbir koşulda yazdırılmaz, loglanmaz, commit'lenmez; yalnız ADI geçer. Anahtar/başlık dosyaları yalnız `$XDG_RUNTIME_DIR/ted-mcp-sp3/` (mod 700, dosyalar 600) ya da `~/.local/share/ted-backups/` (mod 700, dosyalar 600) altında durur — depo ağacında asla.
- Gizli olmayan dağıtım topolojisi (`TED_MCP_HOST`, `TED_MCP_PORT`, `TED_MCP_PUBLIC_BASE_URL`, `TED_MCP_ALLOWED_HOSTS`, `TED_DASHBOARD_API_URL`) izlenen `ted-mcp.service` `Environment=` satırlarında; `.env` yalnız sırları taşır. `TED_MCP_PROJECT_ROOT` üretimde tanımsızdır.
- `.env` elle düzenlenmez; yalnız `python -m src.mcp_server.env_prep` ile.
- Cloudflare: bölge `tedy.online` ve tünel `hp-ai-node` **adla** çözülür; `.env`'deki `CLOUDFLARE_ZONE_ID`/`CLOUDFLARE_TUNNEL_ID` kullanılmaz (başka kaynaklara ait). Ingress yalnız birleştirilir; hız sınırı bölgedeki tek kurala (Free plan) birleştirilir, ikinci kural açılmaz; her yazımdan önce salt okuma listesi, kuru çalıştırma, `--beklenen-kural` kilidi ve yedek.
- Servis ana checkout'tan çalışır (`/mnt/thunderbolt/workspaces/TED`). Kod görevleri (1–5) worktree'de (`/mnt/thunderbolt/workspaces/TED/.worktrees/ted-mcp-cekirdek`, dal `feat/ted-mcp-cekirdek`) commit'lenir. `keys` CLI'si daima ana checkout'tan çalıştırılır (SQLite'ı çalıştığı checkout'un `output/`'una yazar).
- Her komut bloğu açık bir `cd` ile başlar (ajan kabuğunda çalışma dizini korunmaz).
- Kod yorumları **İngilizce**; kullanıcıya dönen metin ve alan adları **Türkçe** (TED konvansiyonu).
- Tüm testler ağsız geçer: `unshare -rn .venv/bin/python -m pytest -q -p no:cacheprovider`. Paket kurulumu gerekirse yalnız `.venv/bin/python -m pip` (bu plan yeni paket gerektirmez).
- Genel uç kontrolleri `curl --doh-url https://1.1.1.1/dns-query` ile yapılır (yerel çözümleyicinin NXDOMAIN negatif önbelleği yanlış "erişilemiyor" üretmesin).
- Commit'ler yalnız ilgili dosyaları stage eder; `.env`, `output/`, yedekler, anahtar dosyaları asla. Push yalnız Task 6 Step 3 ve Task 14 Step 2'de: hızlı ileri, denetleyici onaylı (kullanıcının "TED'i push et" yetkisi); force-push asla. Commit mesajı sonu: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.

## Ölçülmüş ön durum (2026-09-14) — geri almanın hedefi

- Host bu makinedir (`hp-ai-node`). Ana checkout `main` @ `b1958de`, temiz; `src/mcp_server/` **yok**. Worktree `feat/ted-mcp-cekirdek`: AP2 Task 11 `b6ad3e4` (565 passed, 69 skipped); sırada S1a (F1, F3, R4, R5) → S1b (F2, F5, F6, F7, F8 kısmi, F9, F10, R1, R2) → AP2 Task 12 → AP2 son tüm-dal incelemesi. Plan bunların hepsinin bittiğini varsayar (Task 1 Step 1 denetler).
- Kimlik yüzeyi güvenlik incelemesi (2026-09-14): Critical 0 · High 0 · Medium 2 (F1 olay döngüsü, F2 yönlendirme güveni) · Low 8. S1'in getirdiği ve bu planın kullandığı sözleşmeler: `/oauth/*` gövdesi > 16 384 bayt → **413**; `/mcp` sınırı `TED_MCP_MAX_BODY_BYTES` (vars. 2 097 152); kalıcı DCR (kayıt başına rastgele `client_id`, kesin geri-çağırma listesi, ek URI'ler `TED_MCP_EXTRA_REDIRECT_URIS`); `code_challenge_method` tam `S256`, `code_challenge` `[A-Za-z0-9_-]{43}`; Google girişinden sonra açık Onayla/Reddet adımı; onay sayfalarında CSP; `keys oauth-iptal --email`; SQLite WAL. F4 (hız sınırı) uygulamaya eklenmedi → bu planın Task 5/10'u. Ertelenen minörler: RFC 7009 `/oauth/revoke`, `tdyM_` son kullanma tarihi, R3 (Kelvin işareti), R6 (eşzamanlı yenileme). R4 notu: `output/` modu `0775` (grup yazabilir); denetleyici kararı: dizin modu korunur, yalnız token deposu dosyaları (`ted_mcp_oauth.sqlite3`, `-wal`, `-shm`) `0600`'e sabitlenir.
- Kurulu `~/.config/systemd/user/ted-dashboard.service` (düz dosya): `Type=notify`, `WorkingDirectory=/mnt/thunderbolt/workspaces/TED`, `Environment=PATH=…/.venv/bin:/usr/bin:/bin`, `EnvironmentFile=…/.env`, gunicorn `--bind 0.0.0.0:8085 --workers 2 --worker-class gthread --threads 4 --timeout 360`, `Restart=on-failure`, `RestartSec=5`, `WantedBy=default.target`. Depodaki izlenen `ted-dashboard.service` **sapmış**: `User=`/`Group=` satırları, `--workers 1`, gthread yok, `WantedBy=multi-user.target`. `systemd-analyze --user verify` kurulu birimde çıktı üretmez (rc 0). `ted-mcp` birimi yok. `Linger=yes`.
- Portlar: `0.0.0.0:8085` gunicorn; `127.0.0.1:8087` Docker `climax-sabnzbd` (`climax-acquisition`); 8090–8095 boş.
- `cloudflared.service` sistem servisi (root, yerel ikili, `tunnel run --token …`) → `127.0.0.1` servislerine erişir.
- `.env` mod 600, her satır `AD=değer`, sonda yeni satır, yinelenen ad yok. Var: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_ZONE_ID`, `CLOUDFLARE_TUNNEL_ID` (+5 diğer `CLOUDFLARE_*`), `API_KEYS` (tek etiket: `default`), `MUFREDAT_MCP_API_KEY`, `EGITIM_KAYNAK_MCP_API_KEY`. Yok: `TED_MCP_*`, `TED_DASHBOARD_API_KEY`, `ANAMNESIS_MCP_API_KEY`.
- Cloudflare: `tedy.online` bölgesi (NS gloria/micah); `CLOUDFLARE_API_TOKEN` bölgeyi ve `hp-ai-node` tünelini görür. Tünel sağlıklı, `config_src=cloudflare`, **52** ingress kuralı; `tedy.online` ve `www.tedy.online` → `http://localhost:8085`; son kural `http_status:404`. DNS: `tedy.online`, `www.tedy.online` proxied CNAME → `<tünel-id>.cfargotunnel.com`. `mcp.tedy.online` için DNS kaydı ve ingress kuralı **yok**.
- Araçlar: `doppler`, `jq`, `curl` 8.5.0 (`--doh-url` destekli), `dig`, `systemd-analyze` var; `sqlite3` CLI yok. MCP SDK desteklenen protokoller `2024-11-05`, `2025-03-26`, `2025-06-18`, `2025-11-25`; sunucu sürümü `0.1.0`.
- Kod olguları: `http_app.main()` `TED_MCP_HOST` (vars. `127.0.0.1`) ve `TED_MCP_PORT` (vars. `8087`) okur; `load_env()` `setdefault` kullanır (süreç ortamı kazanır); systemd'de `EnvironmentFile=` aynı adı `Environment=`'ın üstüne yazar. Onay sayfası GSI'yı `data-callback` kipinde kullanır (yönlendirme URI'si gerekmez). `keys._default_store()` `TED_MCP_PROJECT_ROOT`'u yok sayar. Dashboard `API_KEYS`'i yalnız import'ta okur; `/api/exams` `require_auth` ile `tdyK_` Bearer kabul eder.

## Dosya Haritası

| Dosya | Sorumluluk |
|---|---|
| `docs/superpowers/specs/2026-09-13-edupedia-tedy-orkestrator-design.md` (değişir) | §3/§4.1 port ve ölçüm düzeltmeleri, §13 risk satırları, §12b AP3 kayıtları |
| `src/mcp_server/http_app.py` (değişir) | `DEFAULT_HOST`, `DEFAULT_PORT = 8090`; `main()` bunları kullanır |
| `src/mcp_server/env_prep.py` (yeni) | `.env` hazırlama CLI'si: `durum`, `ayarla`, `kaldir`, `dashboard-anahtari`, `dashboard-anahtari-kaldir`; değer yazdırmaz |
| `ted-mcp.service` (yeni, depo kökü) | İzlenen systemd user birimi (loopback, topoloji `Environment=`) |
| `ted-dashboard.service` (değişir) | İzlenen kopya kurulu birimle bayt bayt eşitlenir |
| `src/mcp_server/tunnel_route.py` (yeni) | Cloudflare API istemcisi (`CloudflareApi`) + tünel ingress + DNS: `ekle`, `kaldir`, `dogrula`; adla çözüm, kuru çalıştırma, tek-kural kilidi, yedek |
| `src/mcp_server/edge_ratelimit.py` (yeni) | Bölge `http_ratelimit` aşaması: ted-mcp uçları için IP başına hız sınırı `ekle`/`kaldir`/`dogrula`; Free planda mevcut tek kurala birleştirme |
| `CLAUDE.md` (değişir) | Deployment → `ted-mcp` alt bölümü, dashboard işçi sayısı düzeltmesi, kimlik bilgisi adları, AP2 bölümündeki port |
| `tests/test_mcp_server.py` (değişir) | `main()` bağlanma testi |
| `tests/test_mcp_env_prep.py` (yeni) | env_prep testleri |
| `tests/test_deploy_units.py` (yeni) | İzlenen birim dosyaları testleri |
| `tests/test_mcp_tunnel_route.py` (yeni) | tunnel_route testleri |
| `tests/test_mcp_edge_ratelimit.py` (yeni) | edge_ratelimit testleri |

Yeni test sayısı: Task 1 **+2**, Task 2 **+19**, Task 3 **+5**, Task 4 **+11**, Task 5 **+10** = **+47**.

---

### Task 1: Port kararı — spec §4.1/§12b ve `main()` varsayılanı 8090

**Files:**
- Modify: `docs/superpowers/specs/2026-09-13-edupedia-tedy-orkestrator-design.md`
- Modify: `src/mcp_server/http_app.py:30-36` (constants), `:362-372` (`main`)
- Modify: `CLAUDE.md` (AP2 `ted-mcp` bölümündeki port yorumu)
- Test: `tests/test_mcp_server.py`

**Interfaces:**
- Consumes: AP2'nin tamamı (Task 11 `edupedia_kapsam`, Task 12 `edupedia_kaynak_oku` + CLAUDE.md `ted-mcp` bölümü).
- Produces: `http_app.DEFAULT_HOST: str = "127.0.0.1"`, `http_app.DEFAULT_PORT: int = 8090` (Task 3 testi birim dosyasını bunlarla eşitler).

- [ ] **Step 1: Ön koşul — AP2 + S1 tamam ve taban ölçümü**

Run:
```bash
cd /mnt/thunderbolt/workspaces/TED/.worktrees/ted-mcp-cekirdek
git status --short
git log --oneline | grep -c 'edupedia_kaynak_oku'
test -f tests/test_mcp_kaynak_oku.py && echo kaynak_oku_testi_var
grep -c 'ted-mcp — edupedia orkestratörü' CLAUDE.md
grep -c 'TED_MCP_MAX_BODY_BYTES' src/mcp_server/config.py
grep -rc 'TED_MCP_EXTRA_REDIRECT_URIS' src/mcp_server | grep -v ':0' | wc -l
grep -c 'oauth-iptal' src/mcp_server/keys.py
unshare -rn .venv/bin/python -m pytest -q -p no:cacheprovider 2>&1 | tail -n 1
```
Expected: `git status` boş; `1` ya da fazlası; `kaynak_oku_testi_var`; `1`; `1` ya da fazlası (S1a); `1` ya da fazlası (S1b); `1` ya da fazlası (S1b F8); son satır `B passed, S skipped in …` — `failed`/`error` yok. **B** ve **S**'yi görev raporuna yaz; sonraki görevler bunlara göre ölçer.
Ayrıca denetleyici (controller) kaydında şu üçünün yazılı olduğunu doğrula: S1a kapsamlı incelemesi temiz, S1b kapsamlı incelemesi temiz, AP2 son tüm-dal incelemesi temiz; son incelemenin SHA'sını **R** olarak görev raporuna yaz (Task 9 kullanır).
Herhangi biri tutmazsa DUR: AP3, AP2'nin ve S1 dalgasının tamamlanmasına bağlıdır. Ad sözleşmesi denetleyici tarafından doğrulandı (2026-09-14): S1a `TED_MCP_MAX_BODY_BYTES`; S1b `TED_MCP_EXTRA_REDIRECT_URIS` ve `keys oauth-iptal --email` — yukarıdaki üç `grep` tam bu adları arar.

- [ ] **Step 2: Write the failing test**

`tests/test_mcp_server.py` sonuna ekle:

```python
@pytest.mark.parametrize("env,expected", [
    ({}, ("127.0.0.1", 8090)),
    ({"TED_MCP_HOST": "127.0.0.1", "TED_MCP_PORT": "8093"}, ("127.0.0.1", 8093)),
])
def test_main_binds_loopback_on_spec_port(monkeypatch, env, expected):
    """8087 is taken on hp-ai-node (spec §12b); the process default must be the spec port."""
    import uvicorn

    from src import env_loader

    for name in ("TED_MCP_HOST", "TED_MCP_PORT"):
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(env_loader, "load_env", lambda *a, **k: None)
    sentinel = object()
    monkeypatch.setattr(http_app, "create_app_from_env", lambda: sentinel)
    seen = {}
    monkeypatch.setattr(uvicorn, "run", lambda app, host, port, log_level: seen.update(app=app, host=host, port=port))
    http_app.main()
    assert (seen["host"], seen["port"]) == expected
    assert seen["app"] is sentinel
    assert (http_app.DEFAULT_HOST, http_app.DEFAULT_PORT) == ("127.0.0.1", 8090)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd /mnt/thunderbolt/workspaces/TED/.worktrees/ted-mcp-cekirdek && .venv/bin/python -m pytest tests/test_mcp_server.py -k main_binds -v`
Expected: 2 FAIL — ilki `assert ('127.0.0.1', 8087) == ('127.0.0.1', 8090)`, ikincisi `AttributeError: module 'src.mcp_server.http_app' has no attribute 'DEFAULT_HOST'`.

- [ ] **Step 4: Minimal implementation**

`src/mcp_server/http_app.py` içinde `REALM = "ted-mcp"` satırından hemen sonra ekle:

```python
DEFAULT_HOST = "127.0.0.1"
# 8087 (spec's first choice) is held by another service on hp-ai-node; spec §4.1 and §12b.
DEFAULT_PORT = 8090
```

`main()` içindeki çağrıyı değiştir:

```python
    uvicorn.run(app, host=os.environ.get("TED_MCP_HOST", DEFAULT_HOST),
                port=int(os.environ.get("TED_MCP_PORT", str(DEFAULT_PORT))), log_level="info")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /mnt/thunderbolt/workspaces/TED/.worktrees/ted-mcp-cekirdek && .venv/bin/python -m pytest tests/test_mcp_server.py -v`
Expected: tümü PASS (yeni 2 dahil).

- [ ] **Step 6: Spec'i güncelle**

`docs/superpowers/specs/2026-09-13-edupedia-tedy-orkestrator-design.md` içinde birebir değiştir:

1. `Flask + Gunicorn (1 işçi) systemd **user**` → `Flask + Gunicorn (2 gthread işçisi × 4 iş parçacığı; §12b düzeltmesi) systemd **user**`
2. ` mcp.tedy.online ──► ted-mcp (TED deposu, ayrı ASGI süreci, 127.0.0.1:8087)` → ` mcp.tedy.online ──► ted-mcp (TED deposu, ayrı ASGI süreci, 127.0.0.1:8090)`
3. `   (uvicorn, \`127.0.0.1:8087\`). Genel adlar` → `   (uvicorn, \`127.0.0.1:8090\`; port kararı §12b). Genel adlar`
4. `| TED tek Gunicorn işçisi | Dashboard'da ilerleme/bilet çağrıları hafif; ağır iş ted-mcp'de | Ağır işler dashboard'a girmez |` → `| TED dashboard'u 2 gthread işçisi × 4 iş parçacığı (8 eşzamanlı yuva) | Dashboard'da ilerleme/bilet çağrıları hafif; ağır iş ted-mcp'de | Ağır işler dashboard'a girmez |`
5. ``| Cloudflare tüneli uzaktan yönetiliyor | Yeni hostname'ler yerel config'le eklenemez | `.env`'deki `CLOUDFLARE_API_TOKEN`/`TUNNEL_ID` ile API üzerinden ingress + DNS (alt proje 3) |`` → ``| Cloudflare tüneli uzaktan yönetiliyor | Yeni hostname'ler yerel config'le eklenemez | `CLOUDFLARE_API_TOKEN` ile API üzerinden, bölge (`tedy.online`) ve tünel (`hp-ai-node`) **adla** çözülerek birleştirici ingress + DNS (`src/mcp_server/tunnel_route.py`; alt proje 3, §12b) |``
6. ``| Google OAuth istemcisi yeni origin ister | `mcp.tedy.online` girişi çalışmaz | Google Cloud konsolunda yetkili origin ekleme — insan adımı, alt proje 3'te |`` → ``| Google OAuth istemcisi yeni origin ister | `mcp.tedy.online` girişi çalışmaz | Google Cloud konsolunda yetkili **JavaScript** origin ekleme (yönlendirme URI'si gerekmez) — insan adımı, alt proje 3'te |``

§12b'nin son maddesinden (`- **Token deposu:** … tüketimi JSON'da atomik yapılamaz.`) hemen sonra ekle:

```markdown
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
```

- [ ] **Step 7: CLAUDE.md AP2 bölümündeki portu düzelt**

`CLAUDE.md` içinde birebir değiştir:
- `# Yerel çalıştırma (canlı birim ve tünel alt proje 3'te)` → `# Yerel çalıştırma (canlı birim: Deployment → ted-mcp)`
- `.venv/bin/python -m src.mcp_server.http_app          # 127.0.0.1:8087` → `.venv/bin/python -m src.mcp_server.http_app          # 127.0.0.1:8090`

- [ ] **Step 8: Kalan 8087 başvurusu yok**

Run: `cd /mnt/thunderbolt/workspaces/TED/.worktrees/ted-mcp-cekirdek && grep -rn '8087' src tests CLAUDE.md ted-dashboard.service docs/superpowers/specs; echo "rc=$?"`
Expected: tam bir eşleşme — spec §12b "Port (alt proje 3 …)" maddesinin ilk satırı (``§4.1'deki `127.0.0.1:8087` hp-ai-node'da …``); `src`, `tests`, `CLAUDE.md`, `ted-dashboard.service` içinde eşleşme yok. (Tarihsel AP2 planı bilinçli olarak dokunulmadan kalır.)

Run: `cd /mnt/thunderbolt/workspaces/TED/.worktrees/ted-mcp-cekirdek && unshare -rn .venv/bin/python -m pytest -q -p no:cacheprovider 2>&1 | tail -n 1`
Expected: `B+2 passed, S skipped`.

- [ ] **Step 9: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.worktrees/ted-mcp-cekirdek
git add docs/superpowers/specs/2026-09-13-edupedia-tedy-orkestrator-design.md src/mcp_server/http_app.py tests/test_mcp_server.py CLAUDE.md
git commit -m "fix(ted-mcp): port 8090 (8087 hp-ai-node'da dolu), spec §4.1/§12b alt proje 3 kararları

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: `.env` hazırlama CLI'si — `env_prep` (değer asla yazdırılmaz)

**Files:**
- Create: `src/mcp_server/env_prep.py`
- Test: `tests/test_mcp_env_prep.py`

**Interfaces:**
- Consumes: yok (yalnız stdlib).
- Produces:
  - `env_prep.TOPOLOGY: tuple[str, ...]` = `("TED_MCP_HOST", "TED_MCP_PORT", "TED_MCP_PUBLIC_BASE_URL", "TED_MCP_ALLOWED_HOSTS", "TED_DASHBOARD_API_URL")` — birimin **zorunlu** `Environment=` adları (Task 3 testi).
  - `env_prep.UNIT_ONLY: tuple[str, ...]` = `TOPOLOGY + ("TED_MCP_PROJECT_ROOT", "TED_MCP_MAX_BODY_BYTES", "TED_MCP_EXTRA_REDIRECT_URIS")` — `.env`'de bulunmaması gereken gizli olmayan adlar.
  - `env_prep.parse(lines: list[str]) -> dict[str, list[str]]`, `set_value(lines, name, value, replace=False) -> list[str]`, `remove_value(lines, name) -> list[str]`, `add_dashboard_key(lines, label, key) -> list[str]`, `remove_dashboard_key(lines, label) -> list[str]`, `status(lines) -> tuple[list[str], bool]`, `main(argv=None, stdin=None, out=None) -> int`.
  - CLI: `python -m src.mcp_server.env_prep [--env PATH] {durum | ayarla AD (--uret | --stdin) [--degistir] | kaldir AD | dashboard-anahtari [--etiket ted-mcp] | dashboard-anahtari-kaldir [--etiket ted-mcp]}`. Çıkış kodları: 0 başarı, 1 `durum` hazır değil, 2 reddedildi (dosya değişmez).
  - `durum` satır biçimi: `TAMAM|EKSIK|HATA|VAR|YOK <AD>[: açıklama]`; sıra: yinelenen ad hataları, `TED_MCP_FORM_SECRET`, `TED_DASHBOARD_API_KEY`, `ANAMNESIS_MCP_API_KEY`, `MUFREDAT_MCP_API_KEY`, `EGITIM_KAYNAK_MCP_API_KEY`, `UNIT_ONLY` ihlalleri.

- [ ] **Step 1: Write the failing test**

`tests/test_mcp_env_prep.py`:

```python
"""env_prep: .env edits for ted-mcp that never print a value and keep both parsers in agreement."""
import io
import os
import stat

import pytest

from src.mcp_server import env_prep

OLD_KEY = "tdyK_" + "o" * 43


def _env(tmp_path, text):
    path = tmp_path / ".env"
    path.write_text(text, encoding="utf-8")
    os.chmod(path, 0o600)
    return path


def _run(path, *argv, stdin=""):
    out = io.StringIO()
    rc = env_prep.main(["--env", str(path), *argv], stdin=io.StringIO(stdin), out=out)
    return rc, out.getvalue()


def _values(path):
    return env_prep.parse(path.read_text(encoding="utf-8").splitlines(keepends=True))


def test_generated_secret_is_written_but_never_printed(tmp_path, capsys):
    path = _env(tmp_path, "DASHBOARD_SECRET_KEY=abc\n")
    rc, out = _run(path, "ayarla", "TED_MCP_FORM_SECRET", "--uret")
    assert rc == 0 and out == "yazıldı: TED_MCP_FORM_SECRET\n"
    secret = _values(path)["TED_MCP_FORM_SECRET"][0]
    assert len(secret) == 64 and secret not in out + capsys.readouterr().err
    assert _values(path)["DASHBOARD_SECRET_KEY"] == ["abc"]
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_existing_name_is_refused_unless_replace(tmp_path):
    original = "TED_MCP_FORM_SECRET=" + "a" * 64 + "\n"
    path = _env(tmp_path, original)
    assert _run(path, "ayarla", "TED_MCP_FORM_SECRET", "--uret")[0] == 2
    assert path.read_text() == original
    assert _run(path, "ayarla", "TED_MCP_FORM_SECRET", "--uret", "--degistir")[0] == 0
    assert "a" * 64 not in path.read_text()


def test_stdin_value_is_validated(tmp_path):
    path = _env(tmp_path, "")
    assert _run(path, "ayarla", "ANAMNESIS_MCP_API_KEY", "--stdin", stdin="anm_live-KEY.1\n")[0] == 0
    assert _values(path)["ANAMNESIS_MCP_API_KEY"] == ["anm_live-KEY.1"]
    for bad in ("", "has space", 'quo"te', "a#b", "$HOME"):
        assert _run(path, "ayarla", "MINIMAX_MCP_API_KEY", "--stdin", stdin=bad)[0] == 2
    assert "MINIMAX_MCP_API_KEY" not in path.read_text()


@pytest.mark.parametrize("name", env_prep.UNIT_ONLY)
def test_unit_only_names_are_refused(tmp_path, name):
    path = _env(tmp_path, "")
    assert _run(path, "ayarla", name, "--stdin", stdin="127.0.0.1\n")[0] == 2
    assert path.read_text() == ""


def test_dashboard_key_is_appended_without_touching_existing_entries(tmp_path, capsys):
    path = _env(tmp_path, f"API_KEYS=default:{OLD_KEY}\nGEMINI_API_KEY=g\n")
    rc, out = _run(path, "dashboard-anahtari")
    assert rc == 0
    values = _values(path)
    new_key = values["TED_DASHBOARD_API_KEY"][0]
    assert new_key.startswith("tdyK_") and len(new_key) == 48
    assert values["API_KEYS"] == [f"default:{OLD_KEY},ted-mcp:{new_key}"]
    assert values["GEMINI_API_KEY"] == ["g"]
    assert new_key not in out + capsys.readouterr().err
    assert _run(path, "dashboard-anahtari")[0] == 2


def test_dashboard_key_removal_restores_previous_state(tmp_path):
    original = f"API_KEYS=default:{OLD_KEY}\n"
    path = _env(tmp_path, original)
    assert _run(path, "dashboard-anahtari")[0] == 0
    assert _run(path, "dashboard-anahtari-kaldir")[0] == 0
    assert path.read_text() == original
    assert _run(path, "dashboard-anahtari-kaldir")[0] == 2


def test_status_reports_names_only(tmp_path):
    path = _env(tmp_path, "")
    _run(path, "ayarla", "TED_MCP_FORM_SECRET", "--uret")
    _run(path, "dashboard-anahtari")
    rc, out = _run(path, "durum")
    assert rc == 0
    assert out.splitlines() == ["TAMAM TED_MCP_FORM_SECRET", "TAMAM TED_DASHBOARD_API_KEY",
                                "YOK ANAMNESIS_MCP_API_KEY", "YOK MUFREDAT_MCP_API_KEY",
                                "YOK EGITIM_KAYNAK_MCP_API_KEY"]
    for found in _values(path).values():
        assert found[0] not in out


@pytest.mark.parametrize("text,flag", [
    ("TED_MCP_FORM_SECRET=" + "a" * 64 + "\nTED_MCP_PORT=8090\n", "HATA TED_MCP_PORT"),
    ("TED_MCP_FORM_SECRET=short\n", "HATA TED_MCP_FORM_SECRET"),
    ("TED_MCP_FORM_SECRET=" + "a" * 64 + "\nTED_MCP_FORM_SECRET=" + "b" * 64 + "\n", "HATA TED_MCP_FORM_SECRET: 2 kez"),
    (f"TED_MCP_FORM_SECRET={'a' * 64}\nTED_DASHBOARD_API_KEY={OLD_KEY}\nAPI_KEYS=default:{OLD_KEY}\n",
     "HATA TED_DASHBOARD_API_KEY"),
])
def test_status_fails_on_misconfiguration(tmp_path, text, flag):
    rc, out = _run(_env(tmp_path, text), "durum")
    assert rc == 1 and flag in out


def test_symlinked_env_is_updated_through_the_link(tmp_path):
    real = _env(tmp_path, "A=1\n")
    worktree = tmp_path / "wt"
    worktree.mkdir()
    link = worktree / ".env"
    link.symlink_to(real)
    assert _run(link, "ayarla", "TED_MCP_FORM_SECRET", "--uret")[0] == 0
    assert link.is_symlink()
    assert "TED_MCP_FORM_SECRET=" in real.read_text()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /mnt/thunderbolt/workspaces/TED/.worktrees/ted-mcp-cekirdek && .venv/bin/python -m pytest tests/test_mcp_env_prep.py -v`
Expected: toplama hatası — `ModuleNotFoundError: No module named 'src.mcp_server.env_prep'`.

- [ ] **Step 3: Create `src/mcp_server/env_prep.py`**

```python
"""Prepare TED's .env for ted-mcp without ever printing a secret value.

    .venv/bin/python -m src.mcp_server.env_prep durum
    .venv/bin/python -m src.mcp_server.env_prep ayarla TED_MCP_FORM_SECRET --uret
    doppler secrets get ANAMNESIS_MCP_API_KEY --plain --project cureohub --config dev_personal \
      | .venv/bin/python -m src.mcp_server.env_prep ayarla ANAMNESIS_MCP_API_KEY --stdin
    .venv/bin/python -m src.mcp_server.env_prep dashboard-anahtari --etiket ted-mcp
    .venv/bin/python -m src.mcp_server.env_prep kaldir TED_MCP_FORM_SECRET
    .venv/bin/python -m src.mcp_server.env_prep dashboard-anahtari-kaldir --etiket ted-mcp

The file is read by two parsers that disagree on edge cases: src/env_loader.py (first
occurrence wins, no quoting) and systemd EnvironmentFile= (last occurrence wins, quotes and
escapes). Values are therefore unquoted and restricted to a safe alphabet, and duplicates are
reported. Writes are atomic, keep mode 0600 and follow a symlinked .env (git worktrees link
it) instead of replacing the link with a regular file.
"""
from __future__ import annotations

import argparse
import contextlib
import os
import re
import secrets
import sys
import tempfile
from pathlib import Path
from typing import TextIO

PROJECT_ROOT = Path(__file__).resolve().parents[2]

OPTIONAL = ("ANAMNESIS_MCP_API_KEY", "MUFREDAT_MCP_API_KEY", "EGITIM_KAYNAK_MCP_API_KEY")
# Non-secret deployment settings live in ted-mcp.service Environment= lines. systemd lets
# EnvironmentFile= override Environment=, so any of these in .env would silently beat the unit.
TOPOLOGY = ("TED_MCP_HOST", "TED_MCP_PORT", "TED_MCP_PUBLIC_BASE_URL", "TED_MCP_ALLOWED_HOSTS",
            "TED_DASHBOARD_API_URL")
UNIT_ONLY = TOPOLOGY + ("TED_MCP_PROJECT_ROOT", "TED_MCP_MAX_BODY_BYTES", "TED_MCP_EXTRA_REDIRECT_URIS")
DASHBOARD_KEY_LABEL = "ted-mcp"
MIN_FORM_SECRET_BYTES = 32

_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
_VALUE_RE = re.compile(r"^[A-Za-z0-9._~+/=-]+$")
_LABEL_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class EnvPrepError(Exception):
    pass


def _name_of(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    return stripped.split("=", 1)[0].strip()


def parse(lines: list[str]) -> dict[str, list[str]]:
    """Every value per name in file order; duplicates are kept so they can be reported."""
    found: dict[str, list[str]] = {}
    for line in lines:
        name = _name_of(line)
        if name is not None:
            found.setdefault(name, []).append(line.strip().split("=", 1)[1].strip())
    return found


def _first(values: dict[str, list[str]], name: str) -> str:
    return (values.get(name) or [""])[0]


def _append(lines: list[str], new_line: str) -> list[str]:
    out = list(lines)
    if out and not out[-1].endswith("\n"):
        out[-1] += "\n"
    return out + [new_line]


def set_value(lines: list[str], name: str, value: str, replace: bool = False) -> list[str]:
    if not _NAME_RE.match(name):
        raise EnvPrepError(f"geçersiz ad: {name}")
    if name in UNIT_ONLY:
        raise EnvPrepError(f"{name} .env'e yazılmaz; ted-mcp.service Environment= satırında durur")
    if not _VALUE_RE.match(value):
        raise EnvPrepError(f"{name}: değer boş ya da izin verilmeyen karakter içeriyor")
    indexes = [i for i, line in enumerate(lines) if _name_of(line) == name]
    if len(indexes) > 1:
        raise EnvPrepError(f"{name} birden fazla kez tanımlı; önce elle tekilleştirin")
    if indexes and not replace:
        raise EnvPrepError(f"{name} zaten tanımlı; değiştirmek için --degistir")
    if indexes:
        out = list(lines)
        out[indexes[0]] = f"{name}={value}\n"
        return out
    return _append(lines, f"{name}={value}\n")


def remove_value(lines: list[str], name: str) -> list[str]:
    out = [line for line in lines if _name_of(line) != name]
    if len(out) == len(lines):
        raise EnvPrepError(f"{name} tanımlı değil")
    return out


def _entries(values: dict[str, list[str]]) -> list[str]:
    if len(values.get("API_KEYS", [])) > 1:
        raise EnvPrepError("API_KEYS birden fazla kez tanımlı; önce elle tekilleştirin")
    return [e.strip() for e in _first(values, "API_KEYS").split(",") if e.strip()]


def _label(entry: str) -> str:
    # Mirrors dashboard_api._load_api_keys: "label:key", or a bare key labelled "default".
    return entry.split(":", 1)[0].strip() if ":" in entry else "default"


def _key(entry: str) -> str:
    return entry.split(":", 1)[1].strip() if ":" in entry else entry


def _with_api_keys(lines: list[str], entries: list[str]) -> list[str]:
    indexes = [i for i, line in enumerate(lines) if _name_of(line) == "API_KEYS"]
    if not entries:
        return [line for i, line in enumerate(lines) if i not in indexes]
    new_line = "API_KEYS=" + ",".join(entries) + "\n"
    if indexes:
        out = list(lines)
        out[indexes[0]] = new_line
        return out
    return _append(lines, new_line)


def add_dashboard_key(lines: list[str], label: str, key: str) -> list[str]:
    if not _LABEL_RE.match(label):
        raise EnvPrepError(f"geçersiz etiket: {label}")
    if not key.startswith("tdyK_") or not _VALUE_RE.match(key):
        raise EnvPrepError("dashboard anahtarı tdyK_ ile başlamalı")
    entries = _entries(parse(lines))
    if any(_label(e) == label for e in entries):
        raise EnvPrepError(f"API_KEYS içinde '{label}' etiketi zaten var")
    lines = set_value(lines, "TED_DASHBOARD_API_KEY", key)
    return _with_api_keys(lines, entries + [f"{label}:{key}"])


def remove_dashboard_key(lines: list[str], label: str) -> list[str]:
    values = parse(lines)
    entries = _entries(values)
    removed = {_key(e) for e in entries if _label(e) == label}
    if not removed:
        raise EnvPrepError(f"API_KEYS içinde '{label}' etiketi yok")
    lines = _with_api_keys(lines, [e for e in entries if _label(e) != label])
    if _first(values, "TED_DASHBOARD_API_KEY") in removed:
        lines = remove_value(lines, "TED_DASHBOARD_API_KEY")
    return lines


def status(lines: list[str]) -> tuple[list[str], bool]:
    """Readiness report with names and verdicts only — never a value."""
    values = parse(lines)
    report: list[str] = []
    for name, found in values.items():
        if len(found) > 1:
            report.append(f"HATA {name}: {len(found)} kez tanımlı (env_loader ilkini, systemd sonuncuyu alır)")
    secret = _first(values, "TED_MCP_FORM_SECRET")
    if not secret:
        report.append("EKSIK TED_MCP_FORM_SECRET")
    elif len(secret.encode("utf-8")) < MIN_FORM_SECRET_BYTES:
        report.append(f"HATA TED_MCP_FORM_SECRET: {MIN_FORM_SECRET_BYTES} bayttan kısa")
    else:
        report.append("TAMAM TED_MCP_FORM_SECRET")
    dash = _first(values, "TED_DASHBOARD_API_KEY")
    try:
        labelled = [_key(e) for e in _entries(values) if _label(e) == DASHBOARD_KEY_LABEL]
    except EnvPrepError:
        labelled = []
    if not dash:
        report.append("EKSIK TED_DASHBOARD_API_KEY")
    elif not dash.startswith("tdyK_") or labelled != [dash]:
        report.append(f"HATA TED_DASHBOARD_API_KEY: API_KEYS içindeki '{DASHBOARD_KEY_LABEL}' girdisiyle eşleşmiyor")
    else:
        report.append("TAMAM TED_DASHBOARD_API_KEY")
    for name in OPTIONAL:
        report.append(f"{'VAR' if _first(values, name) else 'YOK'} {name}")
    for name in UNIT_ONLY:
        if name in values:
            report.append(f"HATA {name}: .env'de olmamalı (ted-mcp.service Environment=)")
    ok = not any(row.startswith(("HATA", "EKSIK")) for row in report)
    return report, ok


def read_env(path: Path) -> list[str]:
    real = Path(os.path.realpath(path))
    if not real.exists():
        return []
    return real.read_text(encoding="utf-8").splitlines(keepends=True)


def write_env(path: Path, lines: list[str]) -> None:
    real = Path(os.path.realpath(path))
    fd, tmp = tempfile.mkstemp(prefix=".env.", suffix=".tmp", dir=real.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.writelines(lines)
        os.chmod(tmp, 0o600)
        os.replace(tmp, real)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)
        raise


def main(argv: list[str] | None = None, stdin: TextIO | None = None, out: TextIO | None = None) -> int:
    stdin = sys.stdin if stdin is None else stdin
    out = sys.stdout if out is None else out
    parser = argparse.ArgumentParser(description="ted-mcp .env hazırlığı (değerler asla yazdırılmaz)")
    parser.add_argument("--env", type=Path, default=PROJECT_ROOT / ".env")
    sub = parser.add_subparsers(dest="komut", required=True)
    sub.add_parser("durum")
    ayarla = sub.add_parser("ayarla")
    ayarla.add_argument("ad")
    source = ayarla.add_mutually_exclusive_group(required=True)
    source.add_argument("--uret", action="store_true", help="secrets.token_hex(32)")
    source.add_argument("--stdin", action="store_true", help="değeri standart girdinin ilk satırından oku")
    ayarla.add_argument("--degistir", action="store_true")
    kaldir = sub.add_parser("kaldir")
    kaldir.add_argument("ad")
    for name in ("dashboard-anahtari", "dashboard-anahtari-kaldir"):
        sub.add_parser(name).add_argument("--etiket", default=DASHBOARD_KEY_LABEL)
    args = parser.parse_args(argv)

    lines = read_env(args.env)
    if args.komut == "durum":
        report, ok = status(lines)
        for row in report:
            print(row, file=out)
        return 0 if ok else 1
    try:
        if args.komut == "ayarla":
            value = secrets.token_hex(32) if args.uret else stdin.readline().strip()
            new = set_value(lines, args.ad, value, replace=args.degistir)
            message = f"yazıldı: {args.ad}"
        elif args.komut == "kaldir":
            new = remove_value(lines, args.ad)
            message = f"kaldırıldı: {args.ad}"
        elif args.komut == "dashboard-anahtari":
            new = add_dashboard_key(lines, args.etiket, f"tdyK_{secrets.token_urlsafe(32)}")
            message = f"yazıldı: TED_DASHBOARD_API_KEY ve API_KEYS içindeki '{args.etiket}' girdisi"
        else:
            new = remove_dashboard_key(lines, args.etiket)
            message = f"kaldırıldı: API_KEYS içindeki '{args.etiket}' girdisi"
    except EnvPrepError as exc:
        print(f"hata: {exc}", file=sys.stderr)
        return 2
    write_env(args.env, new)
    print(message, file=out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /mnt/thunderbolt/workspaces/TED/.worktrees/ted-mcp-cekirdek && .venv/bin/python -m pytest tests/test_mcp_env_prep.py -v`
Expected: 19 PASS.

Run: `cd /mnt/thunderbolt/workspaces/TED/.worktrees/ted-mcp-cekirdek && unshare -rn .venv/bin/python -m pytest -q -p no:cacheprovider 2>&1 | tail -n 1`
Expected: `B+21 passed, S skipped`.

- [ ] **Step 5: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.worktrees/ted-mcp-cekirdek
git add src/mcp_server/env_prep.py tests/test_mcp_env_prep.py
git commit -m "feat(ted-mcp): env_prep — .env hazırlığı, değer yazdırmadan; topoloji adları .env'de reddedilir

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: İzlenen systemd birimleri (`ted-mcp.service`, `ted-dashboard.service` eşitleme) ve CLAUDE.md dağıtım bölümü

TED birim dosyalarını depo kökünde izler (`ted-dashboard.service`); `ted-mcp.service` aynı konvansiyonla eklenir. Kurulum operasyonu Task 8'dedir; bu görev yalnız izlenen dosyaları ve onları sabitleyen testi üretir.

**Files:**
- Create: `ted-mcp.service`
- Modify: `ted-dashboard.service` (kurulu birimle bayt bayt eşit)
- Modify: `CLAUDE.md` (Deployment bölümü, Required Credentials satırı)
- Test: `tests/test_deploy_units.py`

**Interfaces:**
- Consumes: Task 1 `http_app.DEFAULT_HOST`, `http_app.DEFAULT_PORT`; Task 2 `env_prep.TOPOLOGY`, `env_prep.UNIT_ONLY`.
- Produces: `ted-mcp.service` (Task 8 bunu `~/.config/systemd/user/`'a kopyalar). Birim ortamı: `TED_MCP_HOST=127.0.0.1`, `TED_MCP_PORT=8090`, `TED_MCP_PUBLIC_BASE_URL=https://mcp.tedy.online`, `TED_MCP_ALLOWED_HOSTS=mcp.tedy.online`, `TED_DASHBOARD_API_URL=http://127.0.0.1:8085`.

- [ ] **Step 1: Write the failing test**

`tests/test_deploy_units.py`:

```python
"""Tracked systemd user units: loopback-only ted-mcp on the spec port, no drift toward system-unit syntax."""
from pathlib import Path

import pytest

from src.mcp_server import env_prep, http_app

ROOT = Path(__file__).resolve().parents[1]
TED = "/mnt/thunderbolt/workspaces/TED"


def _directives(name):
    section, rows, pending = "", [], ""
    for raw in (ROOT / name).read_text(encoding="utf-8").splitlines():
        line = pending + raw.strip()
        if line.endswith("\\"):
            pending = line[:-1] + " "
            continue
        pending = ""
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("["):
            section = line.strip("[]")
            continue
        key, _, value = line.partition("=")
        rows.append((section, key.strip(), value.strip()))
    return rows


def _environment(rows):
    return dict(v.split("=", 1) for s, k, v in rows if s == "Service" and k == "Environment")


@pytest.mark.parametrize("name", ["ted-dashboard.service", "ted-mcp.service"])
def test_units_are_user_units_run_from_the_main_checkout(name):
    rows = _directives(name)
    keys = {(s, k) for s, k, _ in rows}
    assert ("Service", "User") not in keys and ("Service", "Group") not in keys
    assert ("Install", "WantedBy", "default.target") in rows
    assert ("Service", "WorkingDirectory", TED) in rows
    assert ("Service", "EnvironmentFile", f"{TED}/.env") in rows
    assert ("Service", "Restart", "on-failure") in rows


def test_ted_mcp_binds_loopback_on_the_code_default_port():
    rows = _directives("ted-mcp.service")
    env = _environment(rows)
    assert env["TED_MCP_HOST"] == http_app.DEFAULT_HOST == "127.0.0.1"
    assert int(env["TED_MCP_PORT"]) == http_app.DEFAULT_PORT
    assert "0.0.0.0" not in (ROOT / "ted-mcp.service").read_text(encoding="utf-8")
    assert "TED_MCP_PROJECT_ROOT" not in env
    exec_start = next(v for s, k, v in rows if k == "ExecStart")
    assert exec_start == f"{TED}/.venv/bin/python -m src.mcp_server.http_app"


def test_ted_mcp_public_host_is_allowed_and_dashboard_url_matches_dashboard_bind():
    env = _environment(_directives("ted-mcp.service"))
    assert env["TED_MCP_PUBLIC_BASE_URL"] == "https://mcp.tedy.online"
    assert env["TED_MCP_ALLOWED_HOSTS"].split(",") == ["mcp.tedy.online"]
    dash_exec = next(v for s, k, v in _directives("ted-dashboard.service") if k == "ExecStart")
    port = dash_exec.split("--bind", 1)[1].split()[0].rsplit(":", 1)[1]
    assert env["TED_DASHBOARD_API_URL"] == f"http://127.0.0.1:{port}"


def test_unit_sets_topology_and_nothing_the_env_file_may_override():
    env = _environment(_directives("ted-mcp.service"))
    assert set(env_prep.TOPOLOGY) <= set(env)
    assert set(env) - {"PATH", "PYTHONUNBUFFERED"} <= set(env_prep.UNIT_ONLY)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /mnt/thunderbolt/workspaces/TED/.worktrees/ted-mcp-cekirdek && .venv/bin/python -m pytest tests/test_deploy_units.py -v`
Expected: 5 FAIL — `ted-dashboard.service` parametresi `("Service", "User")` / `WantedBy` iddiasında; diğer dördü `FileNotFoundError: … ted-mcp.service`.

- [ ] **Step 3: Create `ted-mcp.service`**

```ini
[Unit]
Description=TED MCP orchestrator (edupedia, uvicorn, loopback only)
After=network.target
StartLimitIntervalSec=120
StartLimitBurst=5

[Service]
Type=simple
WorkingDirectory=/mnt/thunderbolt/workspaces/TED
Environment=PATH=/mnt/thunderbolt/workspaces/TED/.venv/bin:/usr/bin:/bin
Environment=PYTHONUNBUFFERED=1
Environment=TED_MCP_HOST=127.0.0.1
Environment=TED_MCP_PORT=8090
Environment=TED_MCP_PUBLIC_BASE_URL=https://mcp.tedy.online
Environment=TED_MCP_ALLOWED_HOSTS=mcp.tedy.online
Environment=TED_DASHBOARD_API_URL=http://127.0.0.1:8085
EnvironmentFile=/mnt/thunderbolt/workspaces/TED/.env
ExecStart=/mnt/thunderbolt/workspaces/TED/.venv/bin/python -m src.mcp_server.http_app
Restart=on-failure
RestartSec=5
UMask=0077

[Install]
WantedBy=default.target
```

`StartLimit*`: eksik sır gibi kalıcı bir başlatma hatası 5 sn arayla sonsuz yeniden başlatma döngüsüne dönmesin (varsayılan 10 sn/5 deneme `RestartSec=5` ile hiç tetiklenmez).

- [ ] **Step 4: Replace `ted-dashboard.service` with the installed unit verbatim**

`ted-dashboard.service` dosyasının tüm içeriği (ölçülen kurulu birim, 2026-09-14):

```ini
[Unit]
Description=TED Dashboard (Gunicorn)
After=network.target

[Service]
Type=notify
WorkingDirectory=/mnt/thunderbolt/workspaces/TED
Environment=PATH=/mnt/thunderbolt/workspaces/TED/.venv/bin:/usr/bin:/bin
EnvironmentFile=/mnt/thunderbolt/workspaces/TED/.env
ExecStart=/mnt/thunderbolt/workspaces/TED/.venv/bin/gunicorn \
    --bind 0.0.0.0:8085 \
    --workers 2 \
    --worker-class gthread \
    --threads 4 \
    --timeout 360 \
    --access-logfile - \
    --error-logfile - \
    src.dashboard_api:app
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
```

Run: `cd /mnt/thunderbolt/workspaces/TED/.worktrees/ted-mcp-cekirdek && diff ted-dashboard.service /home/mahirkurt/.config/systemd/user/ted-dashboard.service && echo ESIT`
Expected: `ESIT`.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /mnt/thunderbolt/workspaces/TED/.worktrees/ted-mcp-cekirdek && .venv/bin/python -m pytest tests/test_deploy_units.py -v`
Expected: 5 PASS.

Run: `cd /mnt/thunderbolt/workspaces/TED/.worktrees/ted-mcp-cekirdek && systemd-analyze --user verify ted-mcp.service; echo "rc=$?"`
Expected: yalnız `rc=0` (çıktı yok).

- [ ] **Step 6: CLAUDE.md dağıtım bölümü**

`CLAUDE.md` içinde birebir değiştir:

``- **Gunicorn**: binds `0.0.0.0:8085`, 1 worker (see `ted-dashboard.service`), WSGI entry `src.dashboard_api:app` `` → ``- **Gunicorn**: binds `0.0.0.0:8085`, 2 `gthread` workers × 4 threads (see `ted-dashboard.service`), WSGI entry `src.dashboard_api:app` ``

`- **Cron**: `*/15 * * * *` runs `run_sync.py` with 600s timeout, logs to `output/sync.log`` satırından hemen sonra (ve `## Architecture`'dan önce) ekle:

````markdown
- **Tracked unit files**: `ted-dashboard.service` and `ted-mcp.service` at the repo root are the source of truth; after editing one, `install -m 644 <file> ~/.config/systemd/user/` and `systemctl --user daemon-reload`.

### ted-mcp (edupedia orchestrator)

A second systemd user service, loopback only, published as `mcp.tedy.online` on the same `hp-ai-node` tunnel.
Runbook and rollback: `docs/superpowers/plans/2026-09-14-ted-mcp-altyapi.md`.

```bash
systemctl --user status ted-mcp
journalctl --user -u ted-mcp -f
curl -s http://127.0.0.1:8090/health                   # {"status": "ok", "version": "0.1.0"}
.venv/bin/python -m src.mcp_server.env_prep durum      # .env readiness — names and verdicts only
.venv/bin/python -m src.mcp_server.keys oauth-iptal --email <e-posta>   # kill switch for one person's OAuth grants
```

- **Bind**: `127.0.0.1:8090` (8087 is taken on hp-ai-node). Non-secret settings (`TED_MCP_HOST`, `TED_MCP_PORT`,
  `TED_MCP_PUBLIC_BASE_URL`, `TED_MCP_ALLOWED_HOSTS`, `TED_DASHBOARD_API_URL`, and if ever needed
  `TED_MCP_MAX_BODY_BYTES` / `TED_MCP_EXTRA_REDIRECT_URIS`) live in the unit's `Environment=` lines and must never
  appear in `.env`: systemd lets `EnvironmentFile=` override `Environment=`.
- **Secrets in `.env`**: `TED_MCP_FORM_SECRET`, `TED_DASHBOARD_API_KEY` plus its `ted-mcp:` entry in `API_KEYS`
  (the dashboard reads `API_KEYS` only at start — restart it after a change), `ANAMNESIS_MCP_API_KEY`. Change them
  with `env_prep`, never by hand; it follows the worktree's `.env` symlink.
- **Trap**: the `keys` CLI writes `output/ted_mcp_oauth.sqlite3` under the checkout it runs from. Run it from
  `/mnt/thunderbolt/workspaces/TED`, the service's working directory, and leave `TED_MCP_PROJECT_ROOT` unset.
````

Required Credentials satırında birebir değiştir: ``optional `MUFREDAT_MCP_API_KEY` / `EGITIM_KAYNAK_MCP_API_KEY`. Generate`` → ``optional `MUFREDAT_MCP_API_KEY` / `EGITIM_KAYNAK_MCP_API_KEY`; for ted-mcp `TED_MCP_FORM_SECRET`, `TED_DASHBOARD_API_KEY`, `ANAMNESIS_MCP_API_KEY` (see Deployment → ted-mcp). Generate``

- [ ] **Step 7: Full offline gate**

Run: `cd /mnt/thunderbolt/workspaces/TED/.worktrees/ted-mcp-cekirdek && unshare -rn .venv/bin/python -m pytest -q -p no:cacheprovider 2>&1 | tail -n 1`
Expected: `B+26 passed, S skipped`.

- [ ] **Step 8: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.worktrees/ted-mcp-cekirdek
git add ted-mcp.service ted-dashboard.service tests/test_deploy_units.py CLAUDE.md
git commit -m "feat(ted-mcp): izlenen ted-mcp.service (loopback 8090), ted-dashboard.service kurulu birimle eşitlendi

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: Birleştirici Cloudflare tünel rotası — `tunnel_route`

CureoHub `scripts/sync_hp_tunnel_ingress.py` yeniden kullanılmaz (spec §12b gerekçesi: kaldırma kipi yok, DNS hatasında rc 0, bölgeyi adla çözmez, CureoHub env zincirini yükler). Bu görev ağsızdır; canlı çağrılar Task 11'dedir.

**Files:**
- Create: `src/mcp_server/tunnel_route.py`
- Test: `tests/test_mcp_tunnel_route.py`

**Interfaces:**
- Consumes: `src.env_loader.load_env` (yalnız `CLOUDFLARE_API_TOKEN` için).
- Produces:
  - `tunnel_route.RouteError(Exception)`.
  - `tunnel_route.CloudflareApi(token: str, session=None, base=API_BASE, timeout=20.0)` — `call(method, path, params=None, body=None, missing_ok=False) -> Any` (`success: false` → `RouteError`, mesajda token yok; `missing_ok` ve HTTP 404 → `None`), `zone(name) -> (zone_id, account_id)`, `tunnel_id(account_id, name) -> str`, `tunnel_config(account_id, tunnel_id) -> dict`, `put_tunnel_config(account_id, tunnel_id, config) -> None`, `dns_records(zone_id, name) -> list[dict]`, `create_cname(zone_id, name, target) -> dict`, `delete_dns_record(zone_id, record_id) -> None`. Task 5 `call` ve `zone`'u kullanır.
  - `tunnel_route.default_api() -> CloudflareApi` (`.env`'den token).
  - Saf işlevler: `add_rule(ingress, hostname, service)`, `remove_rule(ingress, hostname)`, `change_summary(old, new) -> (added, removed)`, `ingress_diff(old, new) -> str`, `dns_state(records, hostname, target) -> "yok" | "doğru"`.
  - CLI: `python -m src.mcp_server.tunnel_route --bolge B --tunel T --host H {ekle --servis S --beklenen-kural N [--uygula --yedek-dizini D] | kaldir --beklenen-kural N [--uygula --yedek-dizini D] | dogrula --servis S --durum var|yok [--yedek DOSYA]}`. Çıkış: 0 başarı/kuru çalıştırma, 1 `dogrula` başarısız, 2 reddedildi (yazım yok ya da yazım yarıda kesildi — mesaj yedeği işaret eder).

- [ ] **Step 1: Write the failing test**

`tests/test_mcp_tunnel_route.py`:

```python
"""tunnel_route: merge-only ingress edits with a one-rule interlock, DNS never clobbered, token never printed."""
import io
import json

import pytest

from src.mcp_server import tunnel_route as tr

HOST, SERVICE = "mcp.tedy.online", "http://127.0.0.1:8090"
TUNNEL = "0123abcd-0000-4000-8000-000000000000"
TARGET = f"{TUNNEL}.cfargotunnel.com"
CATCH_ALL = {"service": "http_status:404"}
ARGS = ["--bolge", "tedy.online", "--tunel", "hp-ai-node", "--host", HOST]


def _ingress(n_hostnames=51):
    rules = [{"hostname": "tedy.online", "service": "http://localhost:8085", "originRequest": {}}]
    rules += [{"hostname": f"h{i}.example.com", "service": f"http://localhost:{9000 + i}"} for i in range(n_hostnames - 1)]
    return rules + [CATCH_ALL]


class FakeApi:
    def __init__(self, ingress, records=()):
        self.config = {"ingress": [dict(r) for r in ingress], "warp-routing": {"enabled": False}}
        self.records = [dict(r) for r in records]
        self.calls = []

    def zone(self, name):
        self.calls.append(("zone", name))
        return "zone-tedy", "acct-1"

    def tunnel_id(self, account_id, name):
        self.calls.append(("tunnel_id", account_id, name))
        return TUNNEL

    def tunnel_config(self, account_id, tunnel_id):
        self.calls.append(("tunnel_config",))
        return json.loads(json.dumps(self.config))

    def put_tunnel_config(self, account_id, tunnel_id, config):
        self.calls.append(("put_tunnel_config",))
        self.config = json.loads(json.dumps(config))

    def dns_records(self, zone_id, name):
        self.calls.append(("dns_records", zone_id, name))
        return [dict(r) for r in self.records]

    def create_cname(self, zone_id, name, target):
        self.calls.append(("create_cname", zone_id, name, target))
        self.records.append({"id": "rec-1", "type": "CNAME", "name": name, "content": target, "proxied": True})

    def delete_dns_record(self, zone_id, record_id):
        self.calls.append(("delete_dns_record", zone_id, record_id))
        self.records = [r for r in self.records if r["id"] != record_id]

    def writes(self):
        return [c[0] for c in self.calls if c[0] in ("put_tunnel_config", "create_cname", "delete_dns_record")]


def _run(api, *argv, clock=lambda: 1789430400.0):
    out = io.StringIO()
    rc = tr.main([*ARGS, *argv], api=api, out=out, clock=clock)
    return rc, out.getvalue()


def test_add_rule_inserts_before_catch_all_and_keeps_every_other_rule():
    old = _ingress()
    new = tr.add_rule(old, HOST, SERVICE)
    assert len(new) == 53
    assert new[:51] == old[:51] and new[-1] == CATCH_ALL
    assert new[51] == {"hostname": HOST, "service": SERVICE}
    assert tr.change_summary(old, new) == ([{"hostname": HOST, "service": SERVICE}], [])
    assert tr.add_rule(new, HOST, SERVICE) == new


def test_add_rule_refuses_conflicts_and_missing_catch_all():
    with pytest.raises(tr.RouteError):
        tr.add_rule(_ingress()[:-1], HOST, SERVICE)
    with pytest.raises(tr.RouteError):
        tr.add_rule(tr.add_rule(_ingress(), HOST, "http://127.0.0.1:9999"), HOST, SERVICE)


def test_remove_rule_is_the_exact_inverse():
    old = _ingress()
    assert tr.remove_rule(tr.add_rule(old, HOST, SERVICE), HOST) == old
    with pytest.raises(tr.RouteError):
        tr.remove_rule(old, HOST)


def test_dry_run_reports_one_added_rule_and_writes_nothing():
    api = FakeApi(_ingress())
    rc, out = _run(api, "ekle", "--servis", SERVICE, "--beklenen-kural", "52")
    assert rc == 0
    assert "ingress: 52 kural -> 53 kural" in out
    assert f'eklenen: 1 {{"hostname": "{HOST}", "service": "{SERVICE}"}}' in out
    assert "\nsilinen: 0\n" in out
    assert "fark: +4 satır, -0 satır" in out
    assert f"dns: {HOST} CNAME {TARGET} (proxied) -> oluşturulacak" in out
    assert out.rstrip().endswith("KURU ÇALIŞTIRMA: hiçbir şey yazılmadı")
    assert api.writes() == []


def test_apply_writes_ingress_then_dns_and_snapshots_the_old_config(tmp_path):
    api = FakeApi(_ingress())
    rc, out = _run(api, "ekle", "--servis", SERVICE, "--beklenen-kural", "52", "--uygula", "--yedek-dizini", str(tmp_path))
    assert rc == 0 and out.rstrip().endswith("UYGULANDI")
    assert api.writes() == ["put_tunnel_config", "create_cname"]
    assert api.config["ingress"] == tr.add_rule(_ingress(), HOST, SERVICE)
    assert api.config["warp-routing"] == {"enabled": False}
    assert api.records == [{"id": "rec-1", "type": "CNAME", "name": HOST, "content": TARGET, "proxied": True}]
    snapshots = list(tmp_path.glob("hp-ai-node-config-*.json"))
    assert len(snapshots) == 1 and snapshots[0].stat().st_mode & 0o777 == 0o600
    assert json.loads(snapshots[0].read_text())["ingress"] == _ingress()


def test_apply_refuses_when_rule_count_drifted_or_backup_dir_missing(tmp_path):
    drifted = FakeApi(_ingress(52))
    assert _run(drifted, "ekle", "--servis", SERVICE, "--beklenen-kural", "52", "--uygula",
                "--yedek-dizini", str(tmp_path))[0] == 2
    no_backup = FakeApi(_ingress())
    assert _run(no_backup, "ekle", "--servis", SERVICE, "--beklenen-kural", "52", "--uygula")[0] == 2
    assert drifted.writes() == [] and no_backup.writes() == []


def test_foreign_dns_record_is_never_overwritten(tmp_path):
    api = FakeApi(_ingress(), records=[{"id": "x", "type": "A", "name": HOST, "content": "192.0.2.1", "proxied": False}])
    rc, _ = _run(api, "ekle", "--servis", SERVICE, "--beklenen-kural", "52", "--uygula", "--yedek-dizini", str(tmp_path))
    assert rc == 2 and api.writes() == []


def test_remove_deletes_dns_before_ingress_and_restores_the_pre_state(tmp_path):
    api = FakeApi(_ingress())
    _run(api, "ekle", "--servis", SERVICE, "--beklenen-kural", "52", "--uygula", "--yedek-dizini", str(tmp_path / "a"))
    api.calls.clear()
    rc, out = _run(api, "kaldir", "--beklenen-kural", "53", "--uygula", "--yedek-dizini", str(tmp_path / "b"))
    assert rc == 0 and "fark: +0 satır, -4 satır" in out
    assert api.writes() == ["delete_dns_record", "put_tunnel_config"]
    assert api.config["ingress"] == _ingress() and api.records == []


def test_verify_against_snapshot_catches_any_other_change(tmp_path):
    api = FakeApi(_ingress())
    _run(api, "ekle", "--servis", SERVICE, "--beklenen-kural", "52", "--uygula", "--yedek-dizini", str(tmp_path))
    snapshot = next(tmp_path.glob("*.json"))
    rc, out = _run(api, "dogrula", "--servis", SERVICE, "--durum", "var", "--yedek", str(snapshot))
    assert rc == 0 and "ingress: 53 kural" in out and out.rstrip().endswith("DOĞRULANDI")
    api.config["ingress"][0]["service"] = "http://localhost:9999"
    rc, out = _run(api, "dogrula", "--servis", SERVICE, "--durum", "var", "--yedek", str(snapshot))
    assert rc == 1 and "SORUN yedeğe göre sapma" in out


def test_verify_absent_state():
    api = FakeApi(_ingress())
    rc, out = _run(api, "dogrula", "--servis", SERVICE, "--durum", "yok")
    assert rc == 0 and f"{HOST}: yok" in out and "dns: yok" in out
    rc, out = _run(api, "dogrula", "--servis", SERVICE, "--durum", "var")
    assert rc == 1 and "DOĞRULANAMADI" in out


class FakeResponse:
    def __init__(self, status, payload):
        self.status_code, self._payload = status, payload

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, response):
        self.response, self.requests = response, []

    def request(self, method, url, **kw):
        self.requests.append((method, url, kw))
        return self.response


def test_api_resolves_by_name_handles_missing_and_hides_the_token():
    ok = FakeSession(FakeResponse(200, {"success": True, "result": [{"id": "z1", "account": {"id": "a1"}}]}))
    assert tr.CloudflareApi("secret-token-value", session=ok).zone("tedy.online") == ("z1", "a1")
    method, url, kw = ok.requests[0]
    assert (method, url, kw["params"]) == ("GET", "https://api.cloudflare.com/client/v4/zones", {"name": "tedy.online"})
    denied = tr.CloudflareApi("secret-token-value", session=FakeSession(
        FakeResponse(403, {"success": False, "errors": [{"code": 10000, "message": "Authentication error"}]})))
    with pytest.raises(tr.RouteError) as exc:
        denied.tunnel_id("a1", "hp-ai-node")
    assert "10000" in str(exc.value) and "secret-token-value" not in str(exc.value)
    missing = tr.CloudflareApi("t", session=FakeSession(
        FakeResponse(404, {"success": False, "errors": [{"code": 10003, "message": "not found"}]})))
    assert missing.call("GET", "/zones/z1/rulesets/phases/http_ratelimit/entrypoint", missing_ok=True) is None
    with pytest.raises(tr.RouteError):
        tr.CloudflareApi("")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /mnt/thunderbolt/workspaces/TED/.worktrees/ted-mcp-cekirdek && .venv/bin/python -m pytest tests/test_mcp_tunnel_route.py -v`
Expected: toplama hatası — `ModuleNotFoundError: No module named 'src.mcp_server.tunnel_route'`.

- [ ] **Step 3: Create `src/mcp_server/tunnel_route.py`**

```python
"""Add or remove one hostname route on a remotely managed Cloudflare tunnel — merge-only.

    .venv/bin/python -m src.mcp_server.tunnel_route --bolge tedy.online --tunel hp-ai-node \
        --host mcp.tedy.online ekle --servis http://127.0.0.1:8090 --beklenen-kural 52
    ...  ekle --servis http://127.0.0.1:8090 --beklenen-kural 52 --uygula --yedek-dizini ~/.local/share/ted-backups
    ...  dogrula --servis http://127.0.0.1:8090 --durum var --yedek <yedek.json>
    ...  kaldir --beklenen-kural 53 [--uygula --yedek-dizini DIR]

The zone and the tunnel are resolved by name; CLOUDFLARE_ZONE_ID / CLOUDFLARE_TUNNEL_ID in
TED's .env belong to other resources and are never read. Without --uygula nothing is written.
With --uygula the tool refuses anything other than exactly one added rule (ekle) or one removed
rule (kaldir), never overwrites or deletes a DNS record it did not expect, snapshots the full
tunnel configuration first and re-reads what it wrote. Only CLOUDFLARE_API_TOKEN is read from
the environment, and it is never printed.
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable, TextIO

import requests

API_BASE = "https://api.cloudflare.com/client/v4"
Rule = dict[str, Any]


class RouteError(Exception):
    pass


def _norm(rule: Rule) -> Rule:
    # The API may echo empty defaults (e.g. originRequest: {}); they carry no routing meaning.
    return {k: v for k, v in rule.items() if v not in ({}, [], None)}


def _canon(rule: Rule) -> str:
    return json.dumps(_norm(rule), sort_keys=True, ensure_ascii=False)


def _is_catch_all(rule: Rule) -> bool:
    return not rule.get("hostname") and not rule.get("path")


def add_rule(ingress: list[Rule], hostname: str, service: str) -> list[Rule]:
    """Insert {hostname, service} just before the trailing catch-all; other rules are untouched."""
    if not ingress or not _is_catch_all(ingress[-1]):
        raise RouteError("ingress'in son kuralı catch-all değil; elle incelenmeli")
    wanted = {"hostname": hostname, "service": service}
    existing = [r for r in ingress if r.get("hostname") == hostname]
    if not existing:
        return list(ingress[:-1]) + [wanted, ingress[-1]]
    if [_norm(r) for r in existing] == [wanted]:
        return list(ingress)
    raise RouteError(f"{hostname} için farklı bir kural zaten var; elle incelenmeli")


def remove_rule(ingress: list[Rule], hostname: str) -> list[Rule]:
    kept = [r for r in ingress if r.get("hostname") != hostname]
    if len(kept) == len(ingress):
        raise RouteError(f"{hostname} için ingress kuralı yok")
    return kept


def change_summary(old: list[Rule], new: list[Rule]) -> tuple[list[Rule], list[Rule]]:
    """(added, removed), comparing normalised rules as multisets."""
    remaining = [_canon(r) for r in old]
    added: list[Rule] = []
    for rule in new:
        key = _canon(rule)
        if key in remaining:
            remaining.remove(key)
        else:
            added.append(_norm(rule))
    return added, [json.loads(k) for k in remaining]


def ingress_diff(old: list[Rule], new: list[Rule]) -> str:
    def lines(rules: list[Rule]) -> list[str]:
        return (json.dumps(rules, indent=2, sort_keys=True, ensure_ascii=False) + "\n").splitlines(keepends=True)

    return "".join(difflib.unified_diff(lines(old), lines(new), fromfile="mevcut", tofile="onerilen"))


def dns_state(records: list[dict[str, Any]], hostname: str, target: str) -> str:
    """'yok' or 'doğru'; any other record set raises, so a foreign record is never touched."""
    if not records:
        return "yok"
    if (len(records) == 1 and records[0].get("type") == "CNAME"
            and records[0].get("content") == target and records[0].get("proxied") is True):
        return "doğru"
    kinds = [(r.get("type"), r.get("proxied")) for r in records]
    raise RouteError(f"{hostname} için beklenmeyen DNS kaydı {kinds}; elle incelenmeli")


class CloudflareApi:
    def __init__(self, token: str, session: Any = None, base: str = API_BASE, timeout: float = 20.0) -> None:
        if not token:
            raise RouteError("CLOUDFLARE_API_TOKEN tanımlı değil")
        self._headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        self._session = session if session is not None else requests.Session()
        self._base = base
        self._timeout = timeout

    def call(self, method: str, path: str, params: dict[str, str] | None = None, body: Any = None,
             missing_ok: bool = False) -> Any:
        try:
            resp = self._session.request(method, self._base + path, headers=self._headers,
                                         params=params, json=body, timeout=self._timeout)
        except requests.RequestException as exc:
            raise RouteError(f"{method} {path}: {type(exc).__name__}") from None
        if missing_ok and resp.status_code == 404:
            return None
        try:
            data = resp.json()
        except ValueError:
            raise RouteError(f"{method} {path}: JSON olmayan yanıt (HTTP {resp.status_code})") from None
        if not isinstance(data, dict) or not data.get("success"):
            errors = data.get("errors") if isinstance(data, dict) else None
            summary = [(e.get("code"), e.get("message")) for e in errors or [] if isinstance(e, dict)]
            raise RouteError(f"{method} {path}: HTTP {resp.status_code} {summary}")
        return data.get("result")

    def zone(self, name: str) -> tuple[str, str]:
        zones = self.call("GET", "/zones", params={"name": name}) or []
        if len(zones) != 1:
            raise RouteError(f"bölge bulunamadı ya da birden fazla: {name}")
        return zones[0]["id"], zones[0]["account"]["id"]

    def tunnel_id(self, account_id: str, name: str) -> str:
        tunnels = self.call("GET", f"/accounts/{account_id}/cfd_tunnel", params={"name": name, "is_deleted": "false"}) or []
        matches = [t for t in tunnels if t.get("name") == name]
        if len(matches) != 1:
            raise RouteError(f"tünel bulunamadı ya da birden fazla: {name}")
        return matches[0]["id"]

    def tunnel_config(self, account_id: str, tunnel_id: str) -> dict[str, Any]:
        result = self.call("GET", f"/accounts/{account_id}/cfd_tunnel/{tunnel_id}/configurations") or {}
        config = result.get("config")
        if not isinstance(config, dict) or not isinstance(config.get("ingress"), list):
            raise RouteError("tünel yapılandırması okunamadı (uzaktan yönetilen bir tünel mi?)")
        return config

    def put_tunnel_config(self, account_id: str, tunnel_id: str, config: dict[str, Any]) -> None:
        self.call("PUT", f"/accounts/{account_id}/cfd_tunnel/{tunnel_id}/configurations", body={"config": config})

    def dns_records(self, zone_id: str, name: str) -> list[dict[str, Any]]:
        return list(self.call("GET", f"/zones/{zone_id}/dns_records", params={"name": name}) or [])

    def create_cname(self, zone_id: str, name: str, target: str) -> dict[str, Any]:
        return self.call("POST", f"/zones/{zone_id}/dns_records", body={
            "type": "CNAME", "name": name, "content": target, "proxied": True, "ttl": 1,
            "comment": "ted-mcp (alt proje 3)"})

    def delete_dns_record(self, zone_id: str, record_id: str) -> None:
        self.call("DELETE", f"/zones/{zone_id}/dns_records/{record_id}")


def default_api() -> CloudflareApi:
    from src.env_loader import load_env

    load_env()
    return CloudflareApi(os.environ.get("CLOUDFLARE_API_TOKEN", "").strip())


def write_snapshot(directory: Path, stem: str, payload: Any, now: float) -> Path:
    directory = directory.expanduser()
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = directory / f"{stem}-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime(now))}.json"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")
    return path


def _put_and_confirm(api: CloudflareApi, account_id: str, tunnel_id: str, config: dict[str, Any],
                     ingress: list[Rule]) -> None:
    api.put_tunnel_config(account_id, tunnel_id, {**config, "ingress": ingress})
    reread = api.tunnel_config(account_id, tunnel_id)["ingress"]
    if [_norm(r) for r in reread] != [_norm(r) for r in ingress]:
        raise RouteError("ingress yazıldı ama yeniden okunan kurallar beklenenden farklı; yedekle karşılaştırın")


def _print_plan(out: TextIO, args: argparse.Namespace, zone_id: str, tunnel_id: str,
                old: list[Rule], new: list[Rule], dns_line: str) -> None:
    added, removed = change_summary(old, new)
    diff = ingress_diff(old, new)
    plus = sum(1 for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++"))
    minus = sum(1 for line in diff.splitlines() if line.startswith("-") and not line.startswith("---"))
    print(f"bölge: {args.bolge} ({zone_id})", file=out)
    print(f"tünel: {args.tunel} ({tunnel_id})", file=out)
    print(f"ingress: {len(old)} kural -> {len(new)} kural", file=out)
    print(" ".join([f"eklenen: {len(added)}", *(_canon(r) for r in added)]), file=out)
    print(" ".join([f"silinen: {len(removed)}", *(_canon(r) for r in removed)]), file=out)
    print(f"fark: +{plus} satır, -{minus} satır", file=out)
    print(f"dns: {dns_line}", file=out)
    print(diff, end="", file=out)


def _verify(args: argparse.Namespace, out: TextIO, current: list[Rule], records: list[dict[str, Any]],
            target: str) -> int:
    problems: list[str] = []
    mine = [_norm(r) for r in current if r.get("hostname") == args.host]
    if args.durum == "var" and mine != [{"hostname": args.host, "service": args.servis}]:
        problems.append(f"ingress: {args.host} tam bir kez ve {args.servis} ile bulunmalı")
    if args.durum == "yok" and mine:
        problems.append(f"ingress: {args.host} kuralı hâlâ var")
    if not current or not _is_catch_all(current[-1]):
        problems.append("ingress: son kural catch-all değil")
    try:
        dns = dns_state(records, args.host, target)
    except RouteError as exc:
        problems.append(str(exc))
        dns = "beklenmeyen"
    wanted = "doğru" if args.durum == "var" else "yok"
    if dns != wanted:
        problems.append(f"dns: beklenen {wanted}, bulunan {dns}")
    if args.yedek is not None:
        snapshot = json.loads(args.yedek.expanduser().read_text(encoding="utf-8"))["ingress"]
        if args.durum == "var":
            expected = add_rule(snapshot, args.host, args.servis)
        elif any(r.get("hostname") == args.host for r in snapshot):
            expected = remove_rule(snapshot, args.host)
        else:
            expected = snapshot
        if [_norm(r) for r in current] != [_norm(r) for r in expected]:
            extra, missing = change_summary(expected, current)
            problems.append(f"yedeğe göre sapma: fazla {len(extra)}, eksik {len(missing)} kural (sıra da karşılaştırılır)")
    print(f"ingress: {len(current)} kural", file=out)
    print(f"{args.host}: {'var' if mine else 'yok'}", file=out)
    print(f"dns: {dns}", file=out)
    for problem in problems:
        print(f"SORUN {problem}", file=out)
    print("DOĞRULANAMADI" if problems else "DOĞRULANDI", file=out)
    return 1 if problems else 0


def main(argv: list[str] | None = None, api: CloudflareApi | None = None, out: TextIO | None = None,
         clock: Callable[[], float] = time.time) -> int:
    out = sys.stdout if out is None else out
    parser = argparse.ArgumentParser(description="Cloudflare tüneline tek hostname rotasını birleştirerek ekle/kaldır")
    parser.add_argument("--bolge", required=True, help="DNS bölgesi adı, örn. tedy.online")
    parser.add_argument("--tunel", required=True, help="tünel adı, örn. hp-ai-node")
    parser.add_argument("--host", required=True, help="yayınlanacak hostname")
    sub = parser.add_subparsers(dest="komut", required=True)
    ekle = sub.add_parser("ekle")
    ekle.add_argument("--servis", required=True)
    kaldir = sub.add_parser("kaldir")
    for command in (ekle, kaldir):
        command.add_argument("--beklenen-kural", type=int, required=True)
        command.add_argument("--uygula", action="store_true")
        command.add_argument("--yedek-dizini", type=Path)
    dogrula = sub.add_parser("dogrula")
    dogrula.add_argument("--servis", required=True)
    dogrula.add_argument("--durum", choices=("var", "yok"), required=True)
    dogrula.add_argument("--yedek", type=Path)
    args = parser.parse_args(argv)

    try:
        api = api if api is not None else default_api()
        zone_id, account_id = api.zone(args.bolge)
        tunnel_id = api.tunnel_id(account_id, args.tunel)
        target = f"{tunnel_id}.cfargotunnel.com"
        config = api.tunnel_config(account_id, tunnel_id)
        old = config["ingress"]
        records = api.dns_records(zone_id, args.host)
        if args.komut == "dogrula":
            return _verify(args, out, old, records, target)

        adding = args.komut == "ekle"
        new = add_rule(old, args.host, args.servis) if adding else remove_rule(old, args.host)
        dns = dns_state(records, args.host, target)
        action = {(True, "yok"): "oluşturulacak", (True, "doğru"): "zaten doğru",
                  (False, "doğru"): "silinecek", (False, "yok"): "zaten yok"}[(adding, dns)]
        _print_plan(out, args, zone_id, tunnel_id, old, new, f"{args.host} CNAME {target} (proxied) -> {action}")
        if len(old) != args.beklenen_kural:
            raise RouteError(f"kural sayısı değişmiş: ölçülen {len(old)}, beklenen {args.beklenen_kural}")
        if not args.uygula:
            print("KURU ÇALIŞTIRMA: hiçbir şey yazılmadı", file=out)
            return 0
        added, removed = change_summary(old, new)
        if (len(added), len(removed)) != ((1, 0) if adding else (0, 1)):
            raise RouteError(f"kilit: {len(added)} eklenen, {len(removed)} silinen kural; tam bir değişiklik bekleniyordu")
        if args.yedek_dizini is None:
            raise RouteError("--uygula için --yedek-dizini zorunlu")
        print(f"yedek: {write_snapshot(args.yedek_dizini, f'{args.tunel}-config', config, clock())}", file=out)
        if adding:
            _put_and_confirm(api, account_id, tunnel_id, config, new)
            print("ingress: yazıldı ve yeniden okunarak doğrulandı", file=out)
            if dns == "yok":
                api.create_cname(zone_id, args.host, target)
        else:
            for record in records if dns == "doğru" else []:
                api.delete_dns_record(zone_id, record["id"])
            _put_and_confirm(api, account_id, tunnel_id, config, new)
            print("ingress: yazıldı ve yeniden okunarak doğrulandı", file=out)
        final = dns_state(api.dns_records(zone_id, args.host), args.host, target)
        wanted = "doğru" if adding else "yok"
        if final != wanted:
            raise RouteError(f"dns: beklenen {wanted}, bulunan {final}")
        print(f"dns: {final}", file=out)
        print("UYGULANDI", file=out)
        return 0
    except RouteError as exc:
        print(f"hata: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /mnt/thunderbolt/workspaces/TED/.worktrees/ted-mcp-cekirdek && .venv/bin/python -m pytest tests/test_mcp_tunnel_route.py -v`
Expected: 11 PASS. (Fark sayımı 52 kurallık girişte önceden ölçüldü: ekleme `+4/-0`, kaldırma `+0/-4`.)

Run: `cd /mnt/thunderbolt/workspaces/TED/.worktrees/ted-mcp-cekirdek && unshare -rn .venv/bin/python -m pytest -q -p no:cacheprovider 2>&1 | tail -n 1`
Expected: `B+37 passed, S skipped`.

- [ ] **Step 5: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.worktrees/ted-mcp-cekirdek
git add src/mcp_server/tunnel_route.py tests/test_mcp_tunnel_route.py
git commit -m "feat(ted-mcp): tunnel_route — adla çözülen, birleştirici ingress + DNS, kuru çalıştırma ve tek-kural kilidi

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: Kenar hız sınırı — `edge_ratelimit` (güvenlik incelemesi F4)

F4 uygulamaya eklenmedi (uvicorn `X-Forwarded-For`'a loopback'ten güvenir; tek süreç durumu tutar); doğru katman Cloudflare'dir. Bölgenin `http_ratelimit` aşamasında **tek** kural: `/oauth/register`, `/oauth/authorize`, `/oauth/token`, `/mcp`, `/mcp/` yollarına IP başına 10 sn'de 60 istek; aşımda `block` (429), 10 sn. Free planda (bölge başına tek hız sınırı kuralı, ifadelerde yalnız yol alanı, dönem ve ceza 10 sn) varsayılan ifade yalnız yola dayanır; bu yollar bölgede yalnız ted-mcp'de anlamlıdır. `--host-kosulu` bayrağı ücretli planlarda ifadeye `http.host` ekleyebilir; bu plan onu kullanmaz (denetleyici kararı: yalnız yol). Bölgede zaten bir kural varsa ve plan Free ise yeni koşul o kurala `or` ile **birleştirilir**. Mevcut kuralın eylemi, eşiği ve dönemi korunur. MCP istemcileri meydan okuma çözemediği için eylem `block` değilse, kural kapalıysa ya da 10 sn'lik eşik 30'un altındaysa araç otomatik olarak durur ve karar denetleyiciye kalır. Ağsızdır; canlı çağrılar Task 10'dadır.

**Files:**
- Create: `src/mcp_server/edge_ratelimit.py`
- Modify: `CLAUDE.md` (ted-mcp alt bölümüne Cloudflare maddesi)
- Test: `tests/test_mcp_edge_ratelimit.py`

**Interfaces:**
- Consumes: Task 4 `tunnel_route.CloudflareApi.call(..., missing_ok=True)`, `CloudflareApi.zone(name)`, `tunnel_route.default_api()`, `tunnel_route.write_snapshot(directory, stem, payload, now)`, `tunnel_route.RouteError`.
- Produces:
  - Sabitler: `PATHS`, `REF = "ted-mcp-hiz-siniri"`, `DEFAULT_THRESHOLD = 60`, `PERIOD = 10`, `TIMEOUT = 10`, `MIN_MERGE_PER_10S = 30`.
  - Saf işlevler: `our_expression(host=None) -> str`, `new_rule(threshold, host=None) -> dict`, `writable(rule) -> dict`, `find_ours(rules, host=None) -> (index, "ayrı" | "birleşik") | None`, `add_limit(rules, plan, threshold, host=None) -> (rules, "oluştur" | "birleştir")`, `remove_limit(rules, host=None) -> rules`, `essence(rule) -> tuple`, `describe(rule) -> str`.
  - CLI: `python -m src.mcp_server.edge_ratelimit --bolge B [--host-kosulu H] {ekle --beklenen-kural N [--esik 60] [--uygula --yedek-dizini D] | kaldir --beklenen-kural N [--uygula --yedek-dizini D] | dogrula}`. Çıkış kodları `tunnel_route` ile aynı.
  - API: `GET /zones/{id}` (`plan.legacy_id`), `GET|PUT /zones/{id}/rulesets/phases/http_ratelimit/entrypoint` (`PUT` gövdesi `{"rules": [...]}`; giriş kural kümesi yoksa oluşturur).

- [ ] **Step 1: Write the failing test**

`tests/test_mcp_edge_ratelimit.py`:

```python
"""edge_ratelimit: one per-IP block rule for ted-mcp's paths, merged into a Free plan's single rule when present."""
import io
import json

import pytest

from src.mcp_server import edge_ratelimit as edge
from src.mcp_server.tunnel_route import RouteError

ENTRY = "/zones/zone-tedy/rulesets/phases/http_ratelimit/entrypoint"
EXISTING = {"id": "r1", "version": "3", "last_updated": "2026-01-01T00:00:00Z", "action": "block",
            "expression": '(http.request.uri.path eq "/api/auth/login")', "description": "login", "enabled": True,
            "ratelimit": {"characteristics": ["ip.src", "cf.colo.id"], "period": 10, "requests_per_period": 50,
                          "mitigation_timeout": 10}}


class FakeApi:
    def __init__(self, plan="free", rules=None):
        self.plan, self.rules, self.puts = plan, rules, []

    def zone(self, name):
        return "zone-tedy", "acct-1"

    def call(self, method, path, params=None, body=None, missing_ok=False):
        if (method, path) == ("GET", "/zones/zone-tedy"):
            return {"plan": {"legacy_id": self.plan}}
        if (method, path) == ("GET", ENTRY):
            if self.rules is None:
                assert missing_ok
                return None
            return {"id": "rs1", "rules": json.loads(json.dumps(self.rules))}
        if (method, path) == ("PUT", ENTRY):
            self.puts.append(body["rules"])
            self.rules = [{**r, "id": r.get("id", f"new{i}"), "version": "1"} for i, r in enumerate(body["rules"])]
            return {"id": "rs1", "rules": self.rules}
        raise AssertionError((method, path))


def _run(api, *argv, clock=lambda: 1789430400.0):
    out = io.StringIO()
    rc = edge.main(["--bolge", "tedy.online", *argv], api=api, out=out, clock=clock)
    return rc, out.getvalue()


def test_expression_covers_exactly_the_public_oauth_and_mcp_paths():
    assert edge.our_expression() == (
        '(http.request.uri.path in {"/oauth/register" "/oauth/authorize" "/oauth/token" "/mcp" "/mcp/"})')
    assert edge.our_expression("mcp.tedy.online").startswith('(http.host eq "mcp.tedy.online" and ')


def test_empty_phase_creates_one_block_rule():
    rules, mode = edge.add_limit([], "free", 60)
    assert mode == "oluştur" and rules == [edge.new_rule(60)]
    assert rules[0]["action"] == "block" and rules[0]["ref"] == edge.REF
    assert rules[0]["ratelimit"] == {"characteristics": ["ip.src", "cf.colo.id"], "period": 10,
                                     "requests_per_period": 60, "mitigation_timeout": 10}


def test_free_plan_single_rule_is_merged_and_unmerge_restores_it():
    rules, mode = edge.add_limit([EXISTING], "free", 60)
    assert mode == "birleştir" and len(rules) == 1
    assert rules[0]["expression"] == f"({EXISTING['expression']}) or {edge.our_expression()}"
    assert rules[0]["id"] == "r1" and "version" not in rules[0] and rules[0]["ratelimit"] == EXISTING["ratelimit"]
    assert edge.find_ours(rules) == (0, "birleşik")
    assert edge.remove_limit(rules) == [edge.writable(EXISTING)]


@pytest.mark.parametrize("change", [
    {"action": "managed_challenge"},
    {"enabled": False},
    {"ratelimit": {**EXISTING["ratelimit"], "requests_per_period": 20}},
])
def test_merge_refuses_rules_that_would_break_mcp_clients(change):
    with pytest.raises(RouteError):
        edge.add_limit([{**EXISTING, **change}], "free", 60)


def test_existing_limit_or_undecidable_rule_sets_are_refused():
    with pytest.raises(RouteError):
        edge.add_limit([edge.new_rule(60)], "free", 60)
    with pytest.raises(RouteError):
        edge.add_limit([EXISTING, {**EXISTING, "id": "r2"}], "pro", 60)
    with pytest.raises(RouteError):
        edge.add_limit([EXISTING], "pro", 60)


def test_dry_run_prints_the_plan_and_writes_nothing():
    api = FakeApi()
    rc, out = _run(api, "ekle", "--beklenen-kural", "0")
    assert rc == 0
    assert "bölge: tedy.online (zone-tedy), plan: free" in out
    assert "http_ratelimit kuralı: 0" in out and "işlem: oluştur" in out
    assert f"  sonra: ted-mcp-hiz-siniri: block 60/10s, zaman aşımı 10s, açık=True, ifade={edge.our_expression()}" in out
    assert out.rstrip().endswith("KURU ÇALIŞTIRMA: hiçbir şey yazılmadı")
    assert api.puts == []


def test_apply_snapshots_writes_rereads_and_verifies(tmp_path):
    api = FakeApi()
    rc, out = _run(api, "ekle", "--beklenen-kural", "0", "--uygula", "--yedek-dizini", str(tmp_path))
    assert rc == 0 and out.rstrip().endswith("UYGULANDI")
    assert api.puts == [[edge.new_rule(60)]]
    snapshot = next(tmp_path.glob("tedy.online-ratelimit-*.json"))
    assert snapshot.stat().st_mode & 0o777 == 0o600
    assert json.loads(snapshot.read_text()) == {"zone": "tedy.online", "rules": []}
    rc, out = _run(api, "dogrula")
    assert rc == 0 and "ted-mcp kuralı: ayrı" in out and out.rstrip().endswith("DOĞRULANDI")


def test_count_drift_is_refused_and_merge_then_remove_round_trips(tmp_path):
    api = FakeApi(rules=[EXISTING])
    assert _run(api, "ekle", "--beklenen-kural", "0", "--uygula", "--yedek-dizini", str(tmp_path / "a"))[0] == 2
    assert api.puts == []
    assert _run(api, "ekle", "--beklenen-kural", "1", "--uygula", "--yedek-dizini", str(tmp_path / "b"))[0] == 0
    assert _run(api, "dogrula")[0] == 0
    assert _run(api, "kaldir", "--beklenen-kural", "1", "--uygula", "--yedek-dizini", str(tmp_path / "c"))[0] == 0
    assert [edge.essence(r) for r in api.rules] == [edge.essence(EXISTING)]
    assert _run(api, "dogrula")[0] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /mnt/thunderbolt/workspaces/TED/.worktrees/ted-mcp-cekirdek && .venv/bin/python -m pytest tests/test_mcp_edge_ratelimit.py -v`
Expected: toplama hatası — `ModuleNotFoundError: No module named 'src.mcp_server.edge_ratelimit'`.

- [ ] **Step 3: Create `src/mcp_server/edge_ratelimit.py`**

```python
"""Per-IP edge rate limit for ted-mcp's public endpoints (security review F4), merge-aware.

    .venv/bin/python -m src.mcp_server.edge_ratelimit --bolge tedy.online ekle --beklenen-kural 0
    ...  ekle --beklenen-kural 0 --uygula --yedek-dizini ~/.local/share/ted-backups
    ...  dogrula
    ...  kaldir --beklenen-kural 1 [--uygula --yedek-dizini DIR]

One block rule on the zone's http_ratelimit phase. A Free zone allows a single rate-limiting rule,
so an existing rule gets our condition OR-ed into its expression instead of a second rule. Its
action, threshold and period stay as they are. The merge is refused when the result would break MCP
clients (challenge actions, disabled rule, a threshold below MIN_MERGE_PER_10S). Dry run by default;
--uygula snapshots the phase, writes with PUT and re-reads what it wrote.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any, Callable, TextIO

from src.mcp_server import tunnel_route
from src.mcp_server.tunnel_route import CloudflareApi, RouteError

PATHS = ("/oauth/register", "/oauth/authorize", "/oauth/token", "/mcp", "/mcp/")
REF = "ted-mcp-hiz-siniri"
DESCRIPTION = "ted-mcp: /oauth/* ve /mcp için IP başına hız sınırı (alt proje 3, güvenlik incelemesi F4)"
DEFAULT_THRESHOLD = 60
PERIOD = 10
TIMEOUT = 10
MIN_MERGE_PER_10S = 30
WRITABLE = ("id", "ref", "action", "action_parameters", "expression", "description", "enabled", "ratelimit", "logging")


def our_expression(host: str | None = None) -> str:
    paths = " ".join(f'"{p}"' for p in PATHS)
    condition = f"http.request.uri.path in {{{paths}}}"
    return f'(http.host eq "{host}" and {condition})' if host else f"({condition})"


def new_rule(threshold: int, host: str | None = None) -> dict[str, Any]:
    return {"ref": REF, "description": DESCRIPTION, "expression": our_expression(host), "action": "block",
            "ratelimit": {"characteristics": ["ip.src", "cf.colo.id"], "period": PERIOD,
                          "requests_per_period": threshold, "mitigation_timeout": TIMEOUT},
            "enabled": True}


def writable(rule: dict[str, Any]) -> dict[str, Any]:
    # Read-only fields (version, last_updated, …) must not be sent back on PUT.
    return {k: rule[k] for k in WRITABLE if k in rule}


def _suffix(host: str | None) -> str:
    return f") or {our_expression(host)}"


def find_ours(rules: list[dict[str, Any]], host: str | None = None) -> tuple[int, str] | None:
    for i, rule in enumerate(rules):
        expression = rule.get("expression") or ""
        if rule.get("ref") == REF or expression == our_expression(host):
            return i, "ayrı"
        if expression.startswith("(") and expression.endswith(_suffix(host)):
            return i, "birleşik"
    return None


def essence(rule: dict[str, Any]) -> tuple:
    limit = rule.get("ratelimit") or {}
    return (rule.get("ref"), rule.get("description"), rule.get("expression"), rule.get("action"),
            rule.get("enabled", True), tuple(sorted(limit.get("characteristics") or [])), limit.get("period"),
            limit.get("requests_per_period"), limit.get("mitigation_timeout"))


def describe(rule: dict[str, Any]) -> str:
    limit = rule.get("ratelimit") or {}
    return (f"{rule.get('ref') or rule.get('id')}: {rule.get('action')} "
            f"{limit.get('requests_per_period')}/{limit.get('period')}s, zaman aşımı {limit.get('mitigation_timeout')}s, "
            f"açık={rule.get('enabled', True)}, ifade={rule.get('expression')}")


def add_limit(rules: list[dict[str, Any]], plan: str, threshold: int,
              host: str | None = None) -> tuple[list[dict[str, Any]], str]:
    rules = [writable(r) for r in rules]
    if find_ours(rules, host) is not None:
        raise RouteError("ted-mcp hız sınırı zaten var; dogrula kullanın")
    if not rules:
        return [new_rule(threshold, host)], "oluştur"
    if plan != "free" or len(rules) != 1:
        raise RouteError(f"{len(rules)} mevcut kural, plan {plan}: otomatik karar yok; elle incelenmeli")
    rule = rules[0]
    limit = rule.get("ratelimit") or {}
    per_10s = limit.get("requests_per_period", 0) * 10 / max(int(limit.get("period") or 10), 1)
    if rule.get("action") != "block":
        raise RouteError(f"mevcut kuralın eylemi '{rule.get('action')}'; MCP istemcileri meydan okuma çözemez — elle karar")
    if rule.get("enabled") is False:
        raise RouteError("mevcut kural kapalı; birleştirme koruma sağlamaz — elle karar")
    if per_10s < MIN_MERGE_PER_10S:
        raise RouteError(f"mevcut eşik 10 sn'de {per_10s:g} < {MIN_MERGE_PER_10S}; MCP patlamalarını keser — elle karar")
    return [{**rule, "expression": f"({rule['expression']}) or {our_expression(host)}"}], "birleştir"


def remove_limit(rules: list[dict[str, Any]], host: str | None = None) -> list[dict[str, Any]]:
    rules = [writable(r) for r in rules]
    found = find_ours(rules, host)
    if found is None:
        raise RouteError("ted-mcp hız sınırı yok")
    i, kind = found
    if kind == "ayrı":
        return rules[:i] + rules[i + 1:]
    expression = rules[i]["expression"]
    return rules[:i] + [{**rules[i], "expression": expression[1:-len(_suffix(host))]}] + rules[i + 1:]


def _entry(zone_id: str) -> str:
    return f"/zones/{zone_id}/rulesets/phases/http_ratelimit/entrypoint"


def _read_rules(api: CloudflareApi, zone_id: str) -> list[dict[str, Any]]:
    entry = api.call("GET", _entry(zone_id), missing_ok=True)
    return list((entry or {}).get("rules") or [])


def _verify(args: argparse.Namespace, out: TextIO, rules: list[dict[str, Any]]) -> int:
    problems: list[str] = []
    found = find_ours(rules, args.host_kosulu)
    if found is None:
        problems.append("ted-mcp hız sınırı yok")
    else:
        i, kind = found
        rule = rules[i]
        limit = rule.get("ratelimit") or {}
        print(f"ted-mcp kuralı: {kind}", file=out)
        if rule.get("action") != "block":
            problems.append(f"eylem '{rule.get('action')}', block bekleniyordu")
        if rule.get("enabled") is False:
            problems.append("kural kapalı")
        if sorted(limit.get("characteristics") or []) != ["cf.colo.id", "ip.src"]:
            problems.append("sayım özellikleri ip.src + cf.colo.id değil")
    for problem in problems:
        print(f"SORUN {problem}", file=out)
    print("DOĞRULANAMADI" if problems else "DOĞRULANDI", file=out)
    return 1 if problems else 0


def main(argv: list[str] | None = None, api: CloudflareApi | None = None, out: TextIO | None = None,
         clock: Callable[[], float] = time.time) -> int:
    out = sys.stdout if out is None else out
    parser = argparse.ArgumentParser(description="ted-mcp uçları için Cloudflare kenar hız sınırı (birleştirme bilinçli)")
    parser.add_argument("--bolge", required=True)
    parser.add_argument("--host-kosulu", default=None, help="yalnız ücretli planda: ifadeye http.host ekler")
    sub = parser.add_subparsers(dest="komut", required=True)
    ekle = sub.add_parser("ekle")
    ekle.add_argument("--esik", type=int, default=DEFAULT_THRESHOLD)
    kaldir = sub.add_parser("kaldir")
    for command in (ekle, kaldir):
        command.add_argument("--beklenen-kural", type=int, required=True)
        command.add_argument("--uygula", action="store_true")
        command.add_argument("--yedek-dizini", type=Path)
    sub.add_parser("dogrula")
    args = parser.parse_args(argv)

    try:
        api = api if api is not None else tunnel_route.default_api()
        zone_id, _ = api.zone(args.bolge)
        plan = str(((api.call("GET", f"/zones/{zone_id}") or {}).get("plan") or {}).get("legacy_id") or "bilinmiyor")
        rules = _read_rules(api, zone_id)
        print(f"bölge: {args.bolge} ({zone_id}), plan: {plan}", file=out)
        print(f"http_ratelimit kuralı: {len(rules)}", file=out)
        for rule in rules:
            print(f"  mevcut: {describe(rule)}", file=out)
        if args.komut == "dogrula":
            return _verify(args, out, rules)
        if args.komut == "ekle":
            new, mode = add_limit(rules, plan, args.esik, args.host_kosulu)
        else:
            new, mode = remove_limit(rules, args.host_kosulu), "kaldır"
        print(f"işlem: {mode}", file=out)
        for rule in new:
            print(f"  sonra: {describe(rule)}", file=out)
        if len(rules) != args.beklenen_kural:
            raise RouteError(f"kural sayısı değişmiş: ölçülen {len(rules)}, beklenen {args.beklenen_kural}")
        if not args.uygula:
            print("KURU ÇALIŞTIRMA: hiçbir şey yazılmadı", file=out)
            return 0
        if args.yedek_dizini is None:
            raise RouteError("--uygula için --yedek-dizini zorunlu")
        snapshot = tunnel_route.write_snapshot(args.yedek_dizini, f"{args.bolge}-ratelimit",
                                               {"zone": args.bolge, "rules": rules}, clock())
        print(f"yedek: {snapshot}", file=out)
        api.call("PUT", _entry(zone_id), body={"rules": new})
        if [essence(r) for r in _read_rules(api, zone_id)] != [essence(r) for r in new]:
            raise RouteError("kurallar yazıldı ama yeniden okunan küme beklenenden farklı; yedekle karşılaştırın")
        print("UYGULANDI", file=out)
        return 0
    except RouteError as exc:
        print(f"hata: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /mnt/thunderbolt/workspaces/TED/.worktrees/ted-mcp-cekirdek && .venv/bin/python -m pytest tests/test_mcp_edge_ratelimit.py tests/test_mcp_tunnel_route.py -v`
Expected: 10 + 11 PASS.

- [ ] **Step 5: CLAUDE.md Cloudflare maddesi**

`CLAUDE.md`'deki `### ted-mcp (edupedia orchestrator)` bölümünün son maddesinden (`- **Trap**: the `keys` CLI …`) sonra ekle:

````markdown
- **Cloudflare** (all dry-run unless `--uygula`; zone and tunnel resolved by name — `.env`'s `CLOUDFLARE_ZONE_ID` /
  `CLOUDFLARE_TUNNEL_ID` belong to other resources):

  ```bash
  .venv/bin/python -m src.mcp_server.tunnel_route --bolge tedy.online --tunel hp-ai-node --host mcp.tedy.online \
    dogrula --servis http://127.0.0.1:8090 --durum var      # ingress rule + proxied CNAME
  .venv/bin/python -m src.mcp_server.edge_ratelimit --bolge tedy.online dogrula   # per-IP edge limit on /oauth/* and /mcp
  ```
````

- [ ] **Step 6: Full offline gate**

Run: `cd /mnt/thunderbolt/workspaces/TED/.worktrees/ted-mcp-cekirdek && unshare -rn .venv/bin/python -m pytest -q -p no:cacheprovider 2>&1 | tail -n 1`
Expected: `B+47 passed, S skipped` — `failed`/`error` yok.

- [ ] **Step 7: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.worktrees/ted-mcp-cekirdek
git add src/mcp_server/edge_ratelimit.py tests/test_mcp_edge_ratelimit.py CLAUDE.md
git commit -m "feat(ted-mcp): edge_ratelimit — /oauth/* ve /mcp için Cloudflare kenar hız sınırı, Free planda mevcut kurala birleştirme

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: [OPERASYON] Kodu yerel `main`'e al ve `origin/main`'e gönder (denetleyici onaylı; kapıya bağlı)

Servis ana checkout'tan çalışır; AP2 + S1 + AP3 kodu orada olmadan Task 7–14 yapılamaz. Bu görev **denetleyici onaylıdır ve kapıya bağlıdır**: yalnız Task 9 Bölüm A `TEMİZ` kaydedildikten sonra koşulur (kullanıcının "kalan tüm aşamaları tamamla" ve "TED'i push et" yetkisi). Yalnız hızlı ileri alma ve normal push; force-push asla.

**Files:** yok (git durumu).

**Interfaces:**
- Consumes: Task 1–5 commit'leri; Task 1 Step 1 **B**, **S**; Task 9 Bölüm A kararı ve kapının incelediği dal ucu **H**.
- Produces: `/mnt/thunderbolt/workspaces/TED` ve `origin/main` @ **H**; önceki yerel `main` SHA'sı **M0** ve önceki `origin/main` SHA'sı **O0** (Task 7 geri alması **M0**'ı kullanır); ana checkout test sayıları **BM/SM**.

- [ ] **Step 1: Kapı ve dal hazır**

Run:
```bash
cd /mnt/thunderbolt/workspaces/TED/.worktrees/ted-mcp-cekirdek
git status --short
git rev-parse HEAD
unshare -rn .venv/bin/python -m pytest -q -p no:cacheprovider 2>&1 | tail -n 1
.venv/bin/python -m src.mcp_server.vendor_sync --check; echo "rc=$?"
```
Expected: boş; SHA Task 9 Bölüm A'da kaydedilen **H** ile aynı; `B+47 passed, S skipped`; `rc=0`. Denetleyici kaydında Task 9 Bölüm A `TEMİZ` yoksa ya da SHA ≠ **H** ise DUR.

- [ ] **Step 2: Ön koşul — yerel ve uzak `main` hızlı ileri alınabilir**

Run:
```bash
git -C /mnt/thunderbolt/workspaces/TED status --short
git -C /mnt/thunderbolt/workspaces/TED rev-parse HEAD
git -C /mnt/thunderbolt/workspaces/TED fetch origin
git -C /mnt/thunderbolt/workspaces/TED rev-parse origin/main
git -C /mnt/thunderbolt/workspaces/TED merge-base --is-ancestor main feat/ted-mcp-cekirdek && echo yerel-ileri-alinabilir
git -C /mnt/thunderbolt/workspaces/TED merge-base --is-ancestor origin/main feat/ted-mcp-cekirdek && echo uzak-ileri-alinabilir
```
Expected: boş; yerel `main` SHA'sı (ölçülen `b1958de…`; **M0** olarak kaydet); fetch hatasız; `origin/main` SHA'sı (**O0** olarak kaydet); `yerel-ileri-alinabilir`; `uzak-ileri-alinabilir`. Biri tutmazsa DUR (birleştirme commit'i ve force-push bu planın dışındadır).

- [ ] **Step 3: Hızlı ileri alma ve push (denetleyici onaylı; kapıya bağlı)**

Run:
```bash
git -C /mnt/thunderbolt/workspaces/TED merge --ff-only feat/ted-mcp-cekirdek
git -C /mnt/thunderbolt/workspaces/TED push origin main
git -C /mnt/thunderbolt/workspaces/TED rev-parse HEAD origin/main
```
Expected: `Fast-forward`; push çıktısında `<O0 kısa>..<H kısa>  main -> main`; son komutun iki satırı da **H**.

Not: çalışan dashboard eski kodu (**M0**) belleğinde tutar; Task 7 Step 8'deki yeniden başlatma `src/roles.py` çıkarımını üretimde etkinleştirir.

Geri alma: `main` ve `origin/main` geri sarılmaz, force-push yapılmaz. Dashboard'un önceki koda dönmesi Task 7 "Geri alma — dashboard kodu" ile yapılır; `main` üzerindeki düzeltme denetleyicinin hazırladığı `git revert` commit'leriyle incelenip normal push'la gider.

- [ ] **Step 4: Ana checkout'ta ağsız test kapısı**

Run:
```bash
cd /mnt/thunderbolt/workspaces/TED
test -f src/mcp_server/edge_ratelimit.py && test -f ted-mcp.service && echo kod_var
unshare -rn .venv/bin/python -m pytest -q -p no:cacheprovider 2>&1 | tail -n 1
```
Expected: `kod_var`; `failed`/`error` yok. (Ana checkout, git dışı veri dizinleri yüzünden worktree'den farklı skip sayısı verebilir; sayıları **BM/SM** olarak yaz.)

---

### Task 7: [OPERASYON] `.env` hazırlığı ve dashboard'un yeniden başlatılması (denetleyici onaylı; kapıya bağlı)

Yalnız Task 9 Bölüm A `TEMİZ` kaydedildikten ve Task 6 tamamlandıktan sonra. Dashboard yeniden başlatması `src/roles.py` çıkarımını üretimde etkinleştirir; yeniden başlatmadan önce ve sonra `/` ve `/api` sağlığı yakalanıp karşılaştırılır.

**Files:** `/mnt/thunderbolt/workspaces/TED/.env` (git dışı; yalnız `env_prep` ile).

**Interfaces:**
- Consumes: Task 2 `env_prep`; Task 6 ana checkout @ **H**, **M0**, **BM/SM**.
- Produces: `.env`'de `TED_MCP_FORM_SECRET`, `TED_DASHBOARD_API_KEY` + `API_KEYS` içinde `ted-mcp:` girdisi, alınabildiyse `ANAMNESIS_MCP_API_KEY`; **ANM** = `yazıldı` | `atlandı` (Task 8 Step 10b ve Task 14 kullanır); yeniden başlatılmış dashboard; `$XDG_RUNTIME_DIR/ted-mcp-sp3/` altında `default.h` ve `dash.h` (Bearer başlık dosyaları, 600) ve önce/sonra sağlık kayıtları.

- [ ] **Step 1: Ön koşul**

Run:
```bash
cd /mnt/thunderbolt/workspaces/TED
git rev-parse HEAD
stat -c '%a' .env
.venv/bin/python -m src.mcp_server.env_prep durum; echo "rc=$?"
grep -E '^API_KEYS=' .env | sed -E 's/^API_KEYS=//' | tr ',' '\n' | sed -E 's/:.*$//'
systemctl --user is-active ted-dashboard
```
Expected (ilk satır **H**):
```
<H>
600
EKSIK TED_MCP_FORM_SECRET
EKSIK TED_DASHBOARD_API_KEY
YOK ANAMNESIS_MCP_API_KEY
VAR MUFREDAT_MCP_API_KEY
VAR EGITIM_KAYNAK_MCP_API_KEY
rc=1
default
active
```
Denetleyici kaydında Task 9 Bölüm A `TEMİZ` olmalı. `HATA` satırı ya da `default` dışında bir etiket varsa DUR — denetleyici kararı (elle tekilleştirme bu planın kapsamı dışında).

- [ ] **Step 2: Yedek (depo dışı)**

Run:
```bash
install -d -m 700 ~/.local/share/ted-backups
install -m 600 /mnt/thunderbolt/workspaces/TED/.env ~/.local/share/ted-backups/env-pre-sp3-20260914
stat -c '%a %n' ~/.local/share/ted-backups ~/.local/share/ted-backups/env-pre-sp3-20260914
```
Expected: `700 …/ted-backups` ve `600 …/env-pre-sp3-20260914`.

- [ ] **Step 3: Form sırrı**

Run: `cd /mnt/thunderbolt/workspaces/TED && .venv/bin/python -m src.mcp_server.env_prep ayarla TED_MCP_FORM_SECRET --uret`
Expected: `yazıldı: TED_MCP_FORM_SECRET`

- [ ] **Step 4: `ted-mcp` etiketli dashboard anahtarı**

Run: `cd /mnt/thunderbolt/workspaces/TED && .venv/bin/python -m src.mcp_server.env_prep dashboard-anahtari --etiket ted-mcp`
Expected: `yazıldı: TED_DASHBOARD_API_KEY ve API_KEYS içindeki 'ted-mcp' girdisi`

- [ ] **Step 5: anamnesis anahtarı — Doppler'dan alma denemesi**

`env_prep` değeri yürütme anında Doppler'dan almayı dener. Alınamaz ya da reddedilirse ted-mcp anahtarsız başlar ve anamnesis spec §7'ye göre dürüstçe `skipped:anahtar yok` olarak degrade olur; bu dal Task 8 Step 10b'de sınanır, Task 14 kullanıcıya anahtar ekleme eylemini bildirir.

Run:
```bash
cd /mnt/thunderbolt/workspaces/TED
set -o pipefail
doppler secrets get ANAMNESIS_MCP_API_KEY --plain --project cureohub --config dev_personal \
  | .venv/bin/python -m src.mcp_server.env_prep ayarla ANAMNESIS_MCP_API_KEY --stdin; echo "rc=$?"
```
Expected: `yazıldı: ANAMNESIS_MCP_API_KEY` ve `rc=0` → **ANM** = `yazıldı`. Doppler hata verirse `env_prep` boş değeri reddeder (`hata: ANAMNESIS_MCP_API_KEY: değer boş …`, `rc` ≠ 0) ve dosya değişmez → **ANM** = `atlandı`, devam.

- [ ] **Step 6: `.env` doğrulaması (yeniden başlatmadan önce)**

Run:
```bash
cd /mnt/thunderbolt/workspaces/TED
.venv/bin/python -m src.mcp_server.env_prep durum; echo "rc=$?"
stat -c '%a' .env
git status --short
```
Expected:
```
TAMAM TED_MCP_FORM_SECRET
TAMAM TED_DASHBOARD_API_KEY
VAR ANAMNESIS_MCP_API_KEY
VAR MUFREDAT_MCP_API_KEY
VAR EGITIM_KAYNAK_MCP_API_KEY
rc=0
600
```
(`git status` boş; **ANM** = `atlandı` ise üçüncü satır `YOK ANAMNESIS_MCP_API_KEY`.)

- [ ] **Step 7: Yeniden başlatma öncesi sağlık kaydı (8085)**

Run:
```bash
W="$XDG_RUNTIME_DIR/ted-mcp-sp3"; install -d -m 700 "$W"
cd /mnt/thunderbolt/workspaces/TED
( umask 077
  .venv/bin/python -c 'import os; from src.env_loader import load_env; load_env(); es=[e.strip() for e in os.environ["API_KEYS"].split(",") if e.strip()]; ks=[(e.split(":",1)[1] if ":" in e else e).strip() for e in es if (e.split(":",1)[0].strip() if ":" in e else "default")=="default"]; print("Authorization: Bearer " + ks[0])' > "$W/default.h"
  .venv/bin/python -c 'import os; from src.env_loader import load_env; load_env(); print("Authorization: Bearer " + os.environ["TED_DASHBOARD_API_KEY"])' > "$W/dash.h" )
systemctl --user show ted-dashboard -p MainPID -p ExecMainStartTimestamp > "$W/dash-once.txt"
for u in / /api/health /api/exams; do printf '%s ' "$u"; curl -sS -o /dev/null -w '%{http_code}\n' -H @"$W/default.h" "http://127.0.0.1:8085$u"; done | tee "$W/dash-once-kodlar.txt"
curl -sS -H @"$W/default.h" http://127.0.0.1:8085/api/health | jq -c 'keys' | tee "$W/dash-once-saglik.txt"
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8085/api/health
curl -sS -o /dev/null -w '%{http_code}\n' -H @"$W/dash.h" http://127.0.0.1:8085/api/health
curl -sS --doh-url https://1.1.1.1/dns-query -o /dev/null -w '%{http_code}\n' https://tedy.online/
```
Expected: `/ 200`, `/api/health 200`, `/api/exams 200`; `/api/health` anahtar listesi (JSON dizisi — kaydedildi); kimliksiz `401`; yeni `ted-mcp` anahtarıyla `401` (henüz yüklenmedi — yeniden başlatmanın gerekliliğinin kanıtı); `tedy.online` `200`.

- [ ] **Step 8: [OPERASYON] Dashboard'u yeniden başlat ve karşılaştır (kısa kesinti; denetleyici onaylı, kapıya bağlı)**

Run:
```bash
W="$XDG_RUNTIME_DIR/ted-mcp-sp3"
systemctl --user restart ted-dashboard && systemctl --user is-active ted-dashboard
curl -sS -o /dev/null --retry 10 --retry-connrefused --retry-delay 1 -w '%{http_code}\n' http://127.0.0.1:8085/
for u in / /api/health /api/exams; do printf '%s ' "$u"; curl -sS -o /dev/null -w '%{http_code}\n' -H @"$W/default.h" "http://127.0.0.1:8085$u"; done > "$W/dash-sonra-kodlar.txt"
diff "$W/dash-once-kodlar.txt" "$W/dash-sonra-kodlar.txt" && echo KODLAR_AYNI
curl -sS -H @"$W/default.h" http://127.0.0.1:8085/api/health | jq -c 'keys' > "$W/dash-sonra-saglik.txt"
diff "$W/dash-once-saglik.txt" "$W/dash-sonra-saglik.txt" && echo SAGLIK_ANAHTARLARI_AYNI
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8085/api/exams
curl -sS -o /dev/null -w '%{http_code}\n' -H @"$W/dash.h" http://127.0.0.1:8085/api/exams
systemctl --user show ted-dashboard -p MainPID -p ExecMainStartTimestamp | diff -q - "$W/dash-once.txt" >/dev/null || echo YENI_SUREC
ps -o args= -p "$(systemctl --user show ted-dashboard -p MainPID --value)" | grep -c -- '--worker-class gthread --threads 4'
journalctl --user -u ted-dashboard --since "5 min ago" --no-pager | grep -ciE 'Traceback|ImportError|ModuleNotFoundError'
curl -sS --doh-url https://1.1.1.1/dns-query -o /dev/null -w '%{http_code}\n' https://tedy.online/
```
Expected: `active`; `200`; `KODLAR_AYNI`; `SAGLIK_ANAHTARLARI_AYNI`; `401`; `200`; `YENI_SUREC`; `1`; `0`; `200`.
Herhangi bir sapma (kod farkı, sağlık anahtarlarında fark, iz kaydı) → DUR ve "Geri alma — dashboard kodu"nu uygula. (Sağlık anahtarlarındaki fark yalnız veri kaynaklıysa — ör. aynı dakikada çalışan tarama — denetleyici kararıyla kabul edilebilir; kaydet.)

- [ ] **Step 9: `.env` değişikliği testlere sızmıyor**

Run: `cd /mnt/thunderbolt/workspaces/TED && unshare -rn .venv/bin/python -m pytest -q -p no:cacheprovider 2>&1 | tail -n 1`
Expected: Task 6 Step 4 ile aynı `BM passed, SM skipped`.

**Geri alma — `.env` (Task 7):**
```bash
cd /mnt/thunderbolt/workspaces/TED
.venv/bin/python -m src.mcp_server.env_prep dashboard-anahtari-kaldir --etiket ted-mcp
.venv/bin/python -m src.mcp_server.env_prep kaldir TED_MCP_FORM_SECRET
.venv/bin/python -m src.mcp_server.env_prep kaldir ANAMNESIS_MCP_API_KEY   # yalnız ANM = yazıldı ise
systemctl --user restart ted-dashboard
```
Beklenen: `durum` Step 1'deki çıktıya döner; `API_KEYS` etiketleri yalnız `default`. (`.env` bu arada başka biçimde değişmediyse `cmp ~/.local/share/ted-backups/env-pre-sp3-20260914 .env` sessiz kalır.)

**Geri alma — dashboard kodu (force-push YOK):** `main` ve `origin/main` olduğu gibi kalır; dashboard geçici bir **M0** worktree'sinden çalıştırılırken denetleyici `main` üzerinde `git revert` commit'lerini hazırlar.
```bash
M0=<Task 6 Step 2'deki önceki main SHA>
T=/mnt/thunderbolt/workspaces/TED
WT=$T/.worktrees/dashboard-geri-M0
git -C "$T" worktree add --detach "$WT" "$M0"
for d in .env .venv output content dashboard-dist; do ln -s "$T/$d" "$WT/$d"; done
rm -rf "$WT/books" && ln -s "$T/books" "$WT/books"          # git dışı bölüm dosyaları da görünsün
install -d -m 700 ~/.config/systemd/user/ted-dashboard.service.d
printf '[Service]\nWorkingDirectory=%s\n' "$WT" > ~/.config/systemd/user/ted-dashboard.service.d/geri-al-M0.conf
systemctl --user daemon-reload && systemctl --user restart ted-dashboard
systemctl --user show ted-dashboard -p WorkingDirectory
W="$XDG_RUNTIME_DIR/ted-mcp-sp3"
for u in / /api/health /api/exams; do printf '%s ' "$u"; curl -sS -o /dev/null --retry 10 --retry-connrefused --retry-delay 1 -w '%{http_code}\n' -H @"$W/default.h" "http://127.0.0.1:8085$u"; done | diff "$W/dash-once-kodlar.txt" - && echo ONCEKI_KOD_SAGLIKLI
```
Beklenen: `WorkingDirectory=/mnt/thunderbolt/workspaces/TED/.worktrees/dashboard-geri-M0`; `ONCEKI_KOD_SAGLIKLI`. (Dashboard `PROJECT_ROOT`'u kendi dosya konumundan alır; `output/`, `dashboard-dist/`, `content/`, `books/` bağlantıları ana checkout'un verisini gösterir.)
Düzeltme `main`'e normal push'la girdikten sonra geçici düzeni kaldır:
```bash
T=/mnt/thunderbolt/workspaces/TED; WT=$T/.worktrees/dashboard-geri-M0
rm ~/.config/systemd/user/ted-dashboard.service.d/geri-al-M0.conf
systemctl --user daemon-reload && systemctl --user restart ted-dashboard
for d in .env .venv output content dashboard-dist books; do rm "$WT/$d"; done   # yalnız bağlantılar; hedefler kalır
git -C "$T" worktree remove --force "$WT"
```

---

### Task 8: [OPERASYON] `ted-mcp.service` kurulumu ve loopback doğrulaması (genel yayın YOK)

**Files:** `~/.config/systemd/user/ted-mcp.service` (izlenen dosyanın kopyası); `output/ted_mcp_oauth.sqlite3` ve `-wal`/`-shm` dosya izinleri (`output/` dizin modu değişmez).

**Interfaces:**
- Consumes: Task 3 `ted-mcp.service`; Task 7 `.env`.
- Produces: etkin ve çalışan `ted-mcp` (`127.0.0.1:8090`); `$XDG_RUNTIME_DIR/ted-mcp-sp3/key` ve `auth.h` (etiket `sp3-kabul-20260914`, Task 12'de iptal edilir); Task 9 Bölüm B incelemesine giden kanıt çıktıları (Step 3–13 çıktılarını görev raporuna yapıştır, anahtar değerleri hariç).

- [ ] **Step 1: Ön koşul**

Run:
```bash
cd /mnt/thunderbolt/workspaces/TED
ss -ltn 'sport = :8090' | tail -n +2 | wc -l
ss -ltn 'sport = :8087' | tail -n +2 | awk '{print $4}'
systemctl --user cat ted-mcp 2>&1 | head -n 1
diff ted-dashboard.service ~/.config/systemd/user/ted-dashboard.service && echo ESIT
.venv/bin/python -m src.mcp_server.env_prep durum >/dev/null; echo "durum_rc=$?"
stat -c '%a %U' output
```
Expected: `0`; `127.0.0.1:8087`; `No files found for ted-mcp.service.`; `ESIT`; `durum_rc=0`; `775 mahirkurt` (denetleyici kararı: dizin modu korunur).

- [ ] **Step 2: `output/` dizin modu değişmez (denetleyici kararı, R4)**

`output/` `775` kalır (dashboard, tarama cron'u ve Asistan aynı dizini kullanır). R4'ün etki alanı token deposuna daraltılır: `output/ted_mcp_oauth.sqlite3` ile S1a'nın WAL kipinin ürettiği `-wal` / `-shm` dosyaları Step 4'te `0600`'e sabitlenir ve Step 12'de yeniden doğrulanır. Birimdeki `UMask=0077` ve SQLite'ın yan dosyalara ana dosyanın iznini vermesi yeni oluşan dosyaları da `0600` tutar. Bu adımda komut yok.

- [ ] **Step 3: Birimi kur, doğrula, başlat**

Run:
```bash
install -m 644 /mnt/thunderbolt/workspaces/TED/ted-mcp.service ~/.config/systemd/user/ted-mcp.service
systemd-analyze --user verify ~/.config/systemd/user/ted-mcp.service; echo "verify_rc=$?"
systemctl --user daemon-reload
systemctl --user enable --now ted-mcp
curl -sS --retry 20 --retry-connrefused --retry-delay 1 http://127.0.0.1:8090/health; echo
systemctl --user is-active ted-mcp; systemctl --user is-enabled ted-mcp
```
Expected: `verify_rc=0` (başka çıktı yok); `Created symlink …/default.target.wants/ted-mcp.service → …/ted-mcp.service.`; `{"status":"ok","version":"0.1.0"}`; `active`; `enabled`.
Sağlık gelmezse: `journalctl --user -u ted-mcp -n 50 --no-pager` (değer içermez; eksik sır `ValueError: TED_MCP_FORM_SECRET …` biçiminde görünür).

- [ ] **Step 4: Yalnız loopback, dosya izinleri**

Run:
```bash
cd /mnt/thunderbolt/workspaces/TED
ss -ltnp 'sport = :8090' | tail -n +2 | awk '{print $4}'
curl -sS -o /dev/null --max-time 3 -w '%{http_code}\n' "http://$(hostname -I | awk '{print $1}'):8090/health"; echo "curl_rc=$?"
for f in output/ted_mcp_oauth.sqlite3 output/ted_mcp_oauth.sqlite3-wal output/ted_mcp_oauth.sqlite3-shm; do [ -e "$f" ] && chmod 600 "$f"; done
find output -maxdepth 1 -name 'ted_mcp_oauth.sqlite3*' ! -perm 600 | wc -l
stat -c '%a %n' output/ted_mcp_oauth.sqlite3*
```
Expected: yalnız `127.0.0.1:8090`; `000` ve `curl_rc=7`; `0`; her satır `600 output/ted_mcp_oauth.sqlite3…` (ana dosya her zaman; `-wal`/`-shm` yalnız açık bağlantı varken görünür).

- [ ] **Step 5: Kimliksiz `/mcp` → 401 ve doğru meydan okuma**

Run:
```bash
curl -sS -D - -o /dev/null -X POST -H 'Host: mcp.tedy.online' -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  http://127.0.0.1:8090/mcp | tr -d '\r' | grep -iE '^(HTTP|www-authenticate)'
```
Expected:
```
HTTP/1.1 401 Unauthorized
www-authenticate: Bearer realm="ted-mcp", resource_metadata="https://mcp.tedy.online/.well-known/oauth-protected-resource"
```
(S1b `error="invalid_token"` gibi bir ek parametre koyduysa `realm` ve `resource_metadata` değerleri yine birebir bu olmalı.)

- [ ] **Step 6: PRM ve AS metadata**

Run:
```bash
for p in /.well-known/oauth-protected-resource /.well-known/oauth-protected-resource/mcp /.well-known/oauth-authorization-server; do
  curl -sS -H 'Host: mcp.tedy.online' "http://127.0.0.1:8090$p" | jq -c .; done
```
Expected (AP2 + S1 sözleşmesi; alan sırası uygulamanın yazdığı sıradır):
```
{"resource":"https://mcp.tedy.online/mcp","authorization_servers":["https://mcp.tedy.online"],"bearer_methods_supported":["header"],"scopes_supported":["edupedia"]}
{"resource":"https://mcp.tedy.online/mcp","authorization_servers":["https://mcp.tedy.online"],"bearer_methods_supported":["header"],"scopes_supported":["edupedia"]}
{"issuer":"https://mcp.tedy.online","authorization_endpoint":"https://mcp.tedy.online/oauth/authorize","token_endpoint":"https://mcp.tedy.online/oauth/token","registration_endpoint":"https://mcp.tedy.online/oauth/register","response_types_supported":["code"],"grant_types_supported":["authorization_code","refresh_token"],"code_challenge_methods_supported":["S256"],"token_endpoint_auth_methods_supported":["none"],"scopes_supported":["edupedia"]}
```
S1 bir alan eklediyse (ör. RFC 9207 `authorization_response_iss_parameter_supported`) fazla alan kabul edilir; yukarıdaki değerlerin her biri aynen bulunmalı ve `code_challenge_methods_supported` yalnız `["S256"]` olmalı.

- [ ] **Step 7: Gövde sınırları (S1a F3) → 413**

Run:
```bash
head -c 16385 /dev/zero | tr '\0' a | curl -sS -o /dev/null -w '%{http_code}\n' -X POST -H 'Host: mcp.tedy.online' \
  -H 'Content-Type: application/x-www-form-urlencoded' --data-binary @- http://127.0.0.1:8090/oauth/token
head -c 40000 /dev/zero | tr '\0' a | curl -sS -o /dev/null -w '%{http_code}\n' -X POST -H 'Host: mcp.tedy.online' \
  -H 'Content-Type: application/x-www-form-urlencoded' -H 'Transfer-Encoding: chunked' --data-binary @- http://127.0.0.1:8090/oauth/token
curl -sS -o /dev/null -w '%{http_code}\n' -X POST -H 'Host: mcp.tedy.online' -H 'Content-Type: application/x-www-form-urlencoded' \
  --data 'grant_type=authorization_code&code=x' http://127.0.0.1:8090/oauth/token
```
Expected: `413` (Content-Length ile), `413` (akışla), `400` (sınır altı, geçersiz istek).

- [ ] **Step 8: Kalıcı DCR ve kesin geri-çağırma listesi (S1b F2)**

Run:
```bash
W="$XDG_RUNTIME_DIR/ted-mcp-sp3"; install -d -m 700 "$W"
curl -sS -o "$W/reg-loopback.json" -w '%{http_code}\n' -X POST -H 'Host: mcp.tedy.online' -H 'Content-Type: application/json' \
  --data '{"redirect_uris":["https://claude.ai/api/mcp/auth_callback"],"client_name":"sp3-loopback"}' \
  http://127.0.0.1:8090/oauth/register
jq -c '{client_id_var: (.client_id | type == "string" and length > 0), redirect_uris}' "$W/reg-loopback.json"
curl -sS -o /dev/null -w '%{http_code}\n' -X POST -H 'Host: mcp.tedy.online' -H 'Content-Type: application/json' \
  --data '{"redirect_uris":["https://claude.ai/any/other/path"]}' http://127.0.0.1:8090/oauth/register
```
Expected: `201`; `{"client_id_var":true,"redirect_uris":["https://claude.ai/api/mcp/auth_callback"]}`; `400`.

- [ ] **Step 9: Test anahtarı, HostGuard, `initialize` + `tools/list`**

Run (anahtar yalnız dosyaya gider):
```bash
W="$XDG_RUNTIME_DIR/ted-mcp-sp3"; install -d -m 700 "$W"
cd /mnt/thunderbolt/workspaces/TED && ( umask 077
  .venv/bin/python -m src.mcp_server.keys olustur --etiket sp3-kabul-20260914 --email drmahirkurt@gmail.com | tail -n 1 > "$W/key"
  printf 'Authorization: Bearer %s\n' "$(cat "$W/key")" > "$W/auth.h" )
grep -c '^tdyM_' "$W/key"
.venv/bin/python -m src.mcp_server.keys listele | grep -c $'^sp3-kabul-20260914\tdrmahirkurt@gmail.com\t[0-9]*\taktif$'
```
Expected: `1`, `1`.

Run:
```bash
W="$XDG_RUNTIME_DIR/ted-mcp-sp3"
M=(-sS -X POST -H @"$W/auth.h" -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' -H 'MCP-Protocol-Version: 2025-06-18')
curl "${M[@]}" -H 'Host: evil.example' -w '\n%{http_code}\n' --data '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' http://127.0.0.1:8090/mcp
curl "${M[@]}" -H 'Host: mcp.tedy.online' --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"sp3-kabul","version":"0"}}}' \
  http://127.0.0.1:8090/mcp | tr -d '\r' | sed -n 's/^data: //p' | jq -c '{protocolVersion: .result.protocolVersion, name: .result.serverInfo.name, version: .result.serverInfo.version}'
curl "${M[@]}" -H 'Host: mcp.tedy.online' --data '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  http://127.0.0.1:8090/mcp | tr -d '\r' | sed -n 's/^data: //p' | jq -c '[.result.tools[].name] | sort'
```
Expected:
```
{"error": "host_not_allowed"}
400
{"protocolVersion":"2025-06-18","name":"TEDY edupedia","version":"0.1.0"}
["edupedia_baglam","edupedia_durum","edupedia_kapsam","edupedia_kaynak_oku","edupedia_rehber"]
```

- [ ] **Step 10: `edupedia_durum` ve `edupedia_baglam` (dashboard anahtarı uçtan uca)**

Run:
```bash
W="$XDG_RUNTIME_DIR/ted-mcp-sp3"
M=(-sS -X POST -H @"$W/auth.h" -H 'Host: mcp.tedy.online' -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' -H 'MCP-Protocol-Version: 2025-06-18')
curl "${M[@]}" --data '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"edupedia_durum","arguments":{}}}' http://127.0.0.1:8090/mcp \
  | tr -d '\r' | sed -n 's/^data: //p' | jq -r '.result.content[0].text' | jq -c '{status, kullanici, dashboard_anahtari, filo}'
curl "${M[@]}" --data '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"edupedia_baglam","arguments":{"gun":7}}}' http://127.0.0.1:8090/mcp \
  | tr -d '\r' | sed -n 's/^data: //p' | jq -r '.result.content[0].text' | jq -c '{status, coverage}'
```
Expected:
```
{"status":"ok","kullanici":{"email":"drmahirkurt@gmail.com","rol":"full"},"dashboard_anahtari":true,"filo":{"maarif-mufredat":"yapılandırılmış","egitim-kaynak":"yapılandırılmış","anamnesis":"yapılandırılmış"}}
{"status":"ok","coverage":{"tedy-dashboard":"hit"}}
```
(`coverage` önümüzdeki 7 günde kayıt yoksa `"empty"` da kabul; `tedy-dashboard` için `degraded:*` ya da `skipped:*` → DUR: dashboard anahtarı çalışmıyor. **ANM** = `atlandı` ise ilk satırda `"anamnesis":"anahtar yok"` beklenir — Step 10b'nin dalıdır, hata değildir.)

- [ ] **Step 10b: anamnesis dürüst degrade yolu (spec §7)**

Ağsız sözleşme testleri — anahtar yokken `skipped:anahtar yok` üretimi ve `edupedia_kaynak_oku`'nun yerel BM25 yedeği:

Run: `cd /mnt/thunderbolt/workspaces/TED && unshare -rn .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_mcp_kaynak_oku.py tests/test_mcp_kapsam.py tests/test_mcp_server.py 2>&1 | tail -n 1`
Expected: `failed`/`error` yok.

Canlı durum (filo sağlığını gerçekten yoklar):
```bash
W="$XDG_RUNTIME_DIR/ted-mcp-sp3"
M=(-sS -X POST -H @"$W/auth.h" -H 'Host: mcp.tedy.online' -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' -H 'MCP-Protocol-Version: 2025-06-18')
curl "${M[@]}" --data '{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"edupedia_durum","arguments":{"canli":true}}}' http://127.0.0.1:8090/mcp \
  | tr -d '\r' | sed -n 's/^data: //p' | jq -r '.result.content[0].text' | jq -c '{anamnesis_filo: .filo.anamnesis, anamnesis_coverage: .coverage.anamnesis}'
```
Expected:
- **ANM** = `yazıldı`: `{"anamnesis_filo":"yapılandırılmış","anamnesis_coverage":"hit"}` (anamnesis sunucusu o an düşükse `"degraded:<neden>"` — kaydet; DUR değil).
- **ANM** = `atlandı`: `{"anamnesis_filo":"anahtar yok","anamnesis_coverage":"skipped:anahtar yok"}`. Servis anahtarsız sağlıklı çalışır (Step 3, 9, 11 geçti); Task 14 kullanıcıya anahtar ekleme eylemini bildirir.

Not: kodun ürettiği neden metni `anahtar yok`'tur (`Coverage.skipped`, boşluklu); denetleyici metnindeki `skipped:anahtar_yok` aynı durumu anlatır.

- [ ] **Step 11: Yeniden başlatma dayanıklılığı**

Run:
```bash
systemctl --user restart ted-mcp
curl -sS --retry 20 --retry-connrefused --retry-delay 1 http://127.0.0.1:8090/health; echo
W="$XDG_RUNTIME_DIR/ted-mcp-sp3"
curl -sS -o /dev/null -w '%{http_code}\n' -X POST -H @"$W/auth.h" -H 'Host: mcp.tedy.online' -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' --data '{"jsonrpc":"2.0","id":5,"method":"tools/list"}' http://127.0.0.1:8090/mcp
```
Expected: `{"status":"ok","version":"0.1.0"}`, `200` (anahtar SQLite'ta kalıcı).

- [ ] **Step 12: Loglarda sır yok; token deposu dosyaları 600**

Run:
```bash
journalctl --user -u ted-mcp --since today --no-pager | grep -cE 'tdyM_|tdyK_|Bearer |access_token|refresh_token|code_verifier|TED_MCP_FORM_SECRET='
cd /mnt/thunderbolt/workspaces/TED
for f in output/ted_mcp_oauth.sqlite3 output/ted_mcp_oauth.sqlite3-wal output/ted_mcp_oauth.sqlite3-shm; do [ -e "$f" ] && chmod 600 "$f"; done
find output -maxdepth 1 -name 'ted_mcp_oauth.sqlite3*' ! -perm 600 | wc -l
stat -c '%a' output
```
Expected: `0`; `0`; `775` (dizin modu değişmedi).

- [ ] **Step 13: Dağıtılan SHA**

Run: `git -C /mnt/thunderbolt/workspaces/TED rev-parse HEAD`
Expected: tam SHA, Task 9 Bölüm A'daki **H** ile aynı; **D** olarak görev raporuna yaz (Task 9 Bölüm B kullanır).

**Geri alma (Task 8):**
```bash
systemctl --user disable --now ted-mcp
rm ~/.config/systemd/user/ted-mcp.service
systemctl --user daemon-reload
ss -ltn 'sport = :8090' | tail -n +2 | wc -l      # 0
```

---

### Task 9: GÜVENLİK KAPISI — Bölüm A (kod; Task 6'dan önce) ve Bölüm B (dağıtım; Task 10'dan önce)

Kimlik yüzeyinin bağımsız incelemesi yapıldı: `/mnt/thunderbolt/workspaces/TED/.superpowers/sdd/2026-09-13-ted-mcp-orkestrator-cekirdegi/security-review-auth.md` (Critical 0 · High 0 · Medium 2 · Low 8). **Bölüm A**, düzeltmelerin incelenen kodda kapandığını kanıtlar. `main`'e ileri alma ve push (Task 6) ile dashboard yeniden başlatmasının (Task 7) ön koşuludur. **Bölüm B**, dağıtımın kendisini inceler ve hiçbir genel DNS/ingress kaydından (Task 10–11) önce gelir. Belgede Task 9 numarası yerinde durur; yürütme sırası Global Constraints'tedir. Denetleyici her iki bölümü **implementer olmayan** bir gözden geçirenle koşar (salt okuma). Otomatik güvenlik incelemesi kullanılamaz; bölümler atlanamaz, "geçti" varsayılamaz.

**Files:** yok (inceleme; kararlar denetleyici kaydına ve SDD defterine, Task 14'te spec §12b'ye).

**Interfaces:**
- Consumes: Task 1 Step 1 **R**; SDD defteri `/mnt/thunderbolt/workspaces/TED/.superpowers/sdd/2026-09-13-ted-mcp-orkestrator-cekirdegi/progress.md`; S1a/S1b raporları ve kapsamlı yeniden inceleme sonuçları; Bölüm B için Task 7–8 kanıtları ve Task 8 Step 13 **D**.
- Produces: Bölüm A kararı ve incelenen dal ucu **H** (Task 6–8 kullanır); Bölüm B kararı (Task 10–11 kullanır).

#### Bölüm A — kod kapısı (Task 5 bittikten sonra, Task 6'dan önce)

- [ ] **Step 1: Düzeltme dalgası ve son inceleme temiz**

Denetleyici kaydında (SDD defteri) üçünün de `temiz` sonucu yazılı olmalı: S1a kapsamlı yeniden incelemesi, S1b kapsamlı yeniden incelemesi, AP2 son tüm-dal incelemesi (SHA **R**). Biri eksikse ya da açık bulgu taşıyorsa DUR.

- [ ] **Step 2: İncelenen dal ucu; kimlik yüzeyinde incelenmemiş değişiklik yok**

Run:
```bash
cd /mnt/thunderbolt/workspaces/TED/.worktrees/ted-mcp-cekirdek
git status --short
git rev-parse HEAD
git merge-base --is-ancestor <R> HEAD && echo icerir
git diff --stat <R> HEAD -- src/mcp_server/http_app.py src/mcp_server/oauth_store.py src/mcp_server/oauth_redirect.py \
  src/mcp_server/google_identity.py src/mcp_server/keys.py src/mcp_server/server.py src/mcp_server/config.py src/roles.py
git diff <R> HEAD -- src/mcp_server/http_app.py | grep -E '^[+-][^+-]'
```
Expected: boş; SHA (**H** olarak kaydet); `icerir`; `--stat` yalnız `src/mcp_server/http_app.py`'yi gösterir; değişen satırlar yalnız Task 1'in `DEFAULT_HOST`/`DEFAULT_PORT` sabitleri, yorumu ve `main()` içindeki `uvicorn.run(...)` iki satırıdır. Başka herhangi bir kimlik yüzeyi değişikliği → o fark için kapsamlı yeniden inceleme, sonra bu adım yeniden.

- [ ] **Step 3: Bulgu kapanış tablosu ve ertelenen düşük bulgular**

Gözden geçiren her satırı kapatan commit ve testle (S1 raporlarından) doldurur; canlı kanıt Bölüm B'dedir:

| Bulgu | Beklenen durum | Kanıt |
|---|---|---|
| F1 (Medium) Google doğrulaması olay döngüsünde | Kapalı (iş parçacığı, JWT ön-kontrolü, sertifika önbelleği, ≤ 5 sn) | S1a testi + commit |
| F2 (Medium) origin düzeyinde yönlendirme güveni | Kapalı (kesin liste, kalıcı DCR, açık Onayla, spec §6.1 güncel) | S1b testi (canlı: Task 8 Step 8) |
| F3 gövde sınırı | Kapalı | S1a testi (canlı: Task 8 Step 7, 413) |
| F4 hız sınırı | **Task 10'da kenarda, DNS'ten önce** | Task 10 |
| F5, F6, F7, F9, F10, R1, R2 | Kapalı | S1b testleri |
| F8 kısmi (`oauth-iptal`, 90 gün aile ömrü, temizlik) | Kapalı | S1b testi |
| R4 SQLite WAL / token deposu izinleri | Kapalı: WAL (S1a); `output/ted_mcp_oauth.sqlite3` ve `-wal`/`-shm` 600; `output/` dizin modu denetleyici kararıyla korunur | S1a testi (canlı: Task 8 Step 4 ve 12) |
| R5 HostGuard ayrıştırma | Kapalı | S1a testi (canlı: Task 8 Step 9) |
| Ertelenen: RFC 7009 `/oauth/revoke`, `tdyM_` son kullanma, R3 Unicode kök liste katlaması, R6 eşzamanlı yenilemede aile iptali | SDD defterinde denetleyici `Ruling:` satırı | Aşağıdaki komut |

Run:
```bash
L=/mnt/thunderbolt/workspaces/TED/.superpowers/sdd/2026-09-13-ted-mcp-orkestrator-cekirdegi/progress.md
for pat in 'RFC 7009' 'tdyM_ son kullanma' '(R3)' '(R6)'; do printf '%s: ' "$pat"; grep -F "$pat" "$L" | grep -c '^Ruling:'; done
```
Expected: dört satırın her birinde sayı ≥ 1 (ölçüm 2026-09-14: `3`, `3`, `1`, `2`). Kullanıcıdan ayrıca yazılı kabul istenmez; bu `Ruling:` satırları Task 14'te kullanıcıya bildirilir.

- [ ] **Step 4: Bölüm A kararı**

`TEMİZ` yalnız şu durumda: Step 1–2 tutar; Step 3'te F1, F2 ve tüm "Kapalı" satırları kanıtlı; dört ertelenen düşük bulgunun defterde denetleyici `Ruling:` satırı var; hiçbir incelemede açık Critical/High/Medium yok; kalan her Low ya düzeltilmiş ya da defterde denetleyici `Ruling:` satırıyla ertelenmiş.

Kaydet (denetleyici kaydı): gözden geçiren, tarih, **R**, **H**, karar.

#### Bölüm B — dağıtım incelemesi (Task 8 bittikten sonra, Task 10'dan önce)

- [ ] **Step 5: Dağıtılan kod = incelenen kod**

Run: `git -C /mnt/thunderbolt/workspaces/TED rev-parse HEAD origin/main`
Expected: iki satır da **H**; Task 8 Step 13 **D** = **H**. Değilse DUR.

- [ ] **Step 6: Dağıtım incelemesi (bu planın yüzeyi)**

Kapsam: `ted-mcp.service`, `src/mcp_server/env_prep.py`, `src/mcp_server/tunnel_route.py`, `src/mcp_server/edge_ratelimit.py`, Task 7–8 çıktıları. Her madde evet/hayır + kanıt:

- D1: Süreç yalnız `127.0.0.1:8090`'ı dinler; LAN adresinden bağlantı reddedilir (Task 8 Step 4). Birimde `0.0.0.0` yok (R7).
- D2: `TED_MCP_FORM_SECRET` `secrets.token_hex(32)` ile üretildi (64 hex = 32 rastgele bayt, R7); git dışı.
- D3: Sır hiçbir yerde yazdırılmadı/loglanmadı: `.env` 600; yedek 700/600 depo dışında; `$XDG_RUNTIME_DIR/ted-mcp-sp3/` 700/600; journal taraması `0` (Task 8 Step 12); üç CLI'nin testleri değer/token yazdırmadığını sabitler.
- D4: Topoloji birimde, `.env`'de yok (`env_prep durum` rc 0); `TED_MCP_PROJECT_ROOT` tanımsız; `keys` CLI ana checkout'tan çalıştı.
- D5: `output/ted_mcp_oauth.sqlite3` ve var olan `-wal`/`-shm` dosyaları 600 (Task 8 Step 4 ve 12); `output/` `775` bilinçli olarak korunur (denetleyici kararı; R4'ün etki alanı token deposuna daraltıldı).
- D6: Metadata yapılandırılmış taban URL'den gelir, `Host` başlığından değil (Task 8 Step 6).
- D7: Canlı sözleşmeler: 413 (Step 7), kesin DCR listesi (Step 8), HostGuard 400 (Step 9), `tdyK_` MCP'de geçmez (AP2 testi).
- D8: Cloudflare araçları yalnız birleştirir; kural sayısı ve tek-değişiklik kilidi, yazım öncesi yedek, yeniden okuma doğrulaması, yabancı DNS kaydına dokunmama; ingress servisi `http://127.0.0.1:8090`; hız sınırı ifadesi yalnız yola dayanır ve birleştirme meydan okuma eylemli / kapalı / sıkı kurallarda otomatik durur.
- D9: Task 13 Google konsolunda yalnız `https://mcp.tedy.online` JavaScript origin'ini ekler; güvenilmeyen betik çalıştıran hiçbir origin eklenmez (R7).
- D10: Dashboard yeniden başlatmasının önce/sonra kodları ve sağlık anahtarları aynı (Task 7 Step 7–8); anamnesis anahtarı yoksa servis sağlıklı ve `skipped:anahtar yok` dürüstçe bildirilir (Task 8 Step 10b).

- [ ] **Step 7: Bölüm B kararı**

`TEMİZ` yalnız Step 5 tutarsa ve D1–D10'un hepsi "evet" ise.

`TEMİZ DEĞİL` (A ya da B) → düzeltme dalda TDD ile yapılır (sözleşme değişiyorsa önce spec, §14.2) → kapsamlı yeniden inceleme → Bölüm A yeniden (yeni **H**) → Task 6 Step 1–4 (hızlı ileri + push) → dashboard kodu değiştiyse Task 7 Step 7–9 → Task 8 Step 3–13 → Bölüm B yeniden.

Kaydet (denetleyici kaydı): gözden geçiren, tarih, **D**, karar.

---

### Task 10: [OPERASYON] Kenar hız sınırı — DNS kaydından önce

**Files:** Cloudflare `tedy.online` bölgesi `http_ratelimit` aşaması; yedek `~/.local/share/ted-backups/tedy.online-ratelimit-<zaman>.json`.

**Interfaces:**
- Consumes: Task 5 `edge_ratelimit`; Task 9 Bölüm A + B `TEMİZ`.
- Produces: `dogrula` → `DOĞRULANDI`; yedek dosya yolu **RL_YEDEK**; seçilen dal (**A** oluştur / **B** birleştir / **C** ücretli plan).

- [ ] **Step 1: Ön koşul**

Task 9 Bölüm A ve Bölüm B kayıtları `TEMİZ`; `git -C /mnt/thunderbolt/workspaces/TED rev-parse HEAD` = **D**; `curl -sS http://127.0.0.1:8090/health` → `{"status":"ok","version":"0.1.0"}`.

- [ ] **Step 2: Salt okuma — mevcut kuralları listele ve kuru çalıştır**

Run: `cd /mnt/thunderbolt/workspaces/TED && .venv/bin/python -m src.mcp_server.edge_ratelimit --bolge tedy.online ekle --beklenen-kural 0; echo "rc=$?"`

Dal **A** (beklenen; bölgede hız sınırı kuralı yok):
```
bölge: tedy.online (<bölge-id>), plan: free
http_ratelimit kuralı: 0
işlem: oluştur
  sonra: ted-mcp-hiz-siniri: block 60/10s, zaman aşımı 10s, açık=True, ifade=(http.request.uri.path in {"/oauth/register" "/oauth/authorize" "/oauth/token" "/mcp" "/mcp/"})
KURU ÇALIŞTIRMA: hiçbir şey yazılmadı
rc=0
```

Dal **B** (`http_ratelimit kuralı: 1` ve `hata: kural sayısı değişmiş: ölçülen 1, beklenen 0`, `rc=2`): `mevcut:` satırını kaydet, `--beklenen-kural 1` ile yeniden kuru çalıştır. Beklenen `işlem: birleştir` ve tek `sonra:` satırı: mevcut kuralın eylemi/eşiği/dönemi aynen, `ifade=(<mevcut ifade>) or (http.request.uri.path in {…})`. Birleştirme mevcut kuralın sayacını ve eşiğini ted-mcp yollarıyla paylaştırır; **DUR — kuru çalıştırma çıktısı (`mevcut:` ve `sonra:` satırları) denetleyiciye gösterilir; uygulama kararı yürütme anında denetleyicinindir** (tedy.online bölgesindeki tüm hostname'ler TED'e aittir). Araç `hata: mevcut kuralın eylemi …` / `… kapalı …` / `… eşik …` ile reddederse otomatik DUR — denetleyici kararı (mevcut kuralı değiştirmek bu planın kapsamı dışında).

Dal **C** (`plan:` `free` değil): ifade yine **yalnız yola** dayanır (denetleyici kararı; `--host-kosulu` kullanılmaz). Kural yoksa dal A gibi uygulanır; mevcut kural varsa araç reddeder → otomatik DUR, denetleyici kararı.

- [ ] **Step 3: Uygula**

Run (Step 2'de geçerli olan bayraklarla, ör. dal A):
```bash
cd /mnt/thunderbolt/workspaces/TED
.venv/bin/python -m src.mcp_server.edge_ratelimit --bolge tedy.online ekle --beklenen-kural 0 --uygula --yedek-dizini ~/.local/share/ted-backups; echo "rc=$?"
```
Expected: Step 2'deki plan satırları, ardından `yedek: /home/mahirkurt/.local/share/ted-backups/tedy.online-ratelimit-<YYYYMMDDTHHMMSSZ>.json`, `UYGULANDI`, `rc=0`. Yolu **RL_YEDEK** olarak kaydet.
`hata: PUT /zones/…/entrypoint: HTTP 400 [...]` (ör. planın izin vermediği alan) → tek `PUT` başarısız olduğu için hiçbir şey değişmedi; hata kodlarını kaydet, DUR.

- [ ] **Step 4: Doğrula (salt okuma)**

Run: `cd /mnt/thunderbolt/workspaces/TED && .venv/bin/python -m src.mcp_server.edge_ratelimit --bolge tedy.online dogrula; echo "rc=$?"`
Expected: `http_ratelimit kuralı: 1`, `mevcut:` satırı Step 2'deki `sonra:` ile aynı, `ted-mcp kuralı: ayrı` (A/C) ya da `birleşik` (B), `DOĞRULANDI`, `rc=0`.

- [ ] **Step 5: İşlevsel kanıt (ifade yola dayandığı için `tedy.online` üzerinden, DNS'ten önce; tüm dallar)**

Run:
```bash
curl -sS --doh-url https://1.1.1.1/dns-query --parallel --parallel-max 10 -o /dev/null -w '%{http_code}\n' \
  $(printf 'https://tedy.online/mcp %.0s' $(seq 1 90)) | LC_ALL=C sort | uniq -c
curl -sS --doh-url https://1.1.1.1/dns-query -o /dev/null -w '%{http_code}\n' https://tedy.online/
```
Expected: ilk komutta en az bir `… 429` satırı (diğer satırlar dashboard'un `/mcp` yanıt kodudur); ikinci komut `200` (kural yalnız eşleşen yolları engeller). 429 görünmezse 10 sn bekleyip 150 istekle bir kez tekrarla; yine yoksa DUR (Cloudflare panosu → Security → Events'te kuralı incele).

**Geri alma (Task 10):**
```bash
cd /mnt/thunderbolt/workspaces/TED
.venv/bin/python -m src.mcp_server.edge_ratelimit --bolge tedy.online kaldir --beklenen-kural 1            # kuru: "işlem: kaldır"
.venv/bin/python -m src.mcp_server.edge_ratelimit --bolge tedy.online kaldir --beklenen-kural 1 --uygula --yedek-dizini ~/.local/share/ted-backups
.venv/bin/python -m src.mcp_server.edge_ratelimit --bolge tedy.online dogrula     # "SORUN ted-mcp hız sınırı yok", rc=1 (hedef durum)
```
Dal A'da sonuç `http_ratelimit kuralı: 0`; dal B'de `mevcut:` satırı Task 10 Step 2'de kaydedilen satırla birebir aynı (RL_YEDEK'teki `rules` ile de karşılaştırılabilir: `jq -c '.rules' <RL_YEDEK>`).

---

### Task 11: [OPERASYON] Cloudflare ingress kuralı ve DNS — `mcp.tedy.online` genel yayına açılır

**Files:** Cloudflare `hp-ai-node` tünel yapılandırması; `tedy.online` DNS; yedek `~/.local/share/ted-backups/hp-ai-node-config-<zaman>.json`.

**Interfaces:**
- Consumes: Task 4 `tunnel_route`; Task 9 Bölüm A + B `TEMİZ`; Task 10 `DOĞRULANDI`.
- Produces: 53 ingress kuralı (yeni kural catch-all'dan hemen önce), proxied CNAME; yedek yolu **TR_YEDEK** (ölçülmüş ön durumun tam kopyası — geri almanın hedefi).

- [ ] **Step 1: Ön koşul ve ön durum**

Run:
```bash
cd /mnt/thunderbolt/workspaces/TED
.venv/bin/python -m src.mcp_server.edge_ratelimit --bolge tedy.online dogrula | tail -n 1
curl -sS http://127.0.0.1:8090/health; echo
curl -sS --doh-url https://1.1.1.1/dns-query -o /dev/null -w '%{http_code}\n' https://tedy.online/
curl -sS --doh-url https://1.1.1.1/dns-query -o /dev/null -w '%{http_code}\n' https://www.tedy.online/
dig @1.1.1.1 +short mcp.tedy.online | wc -l
```
Expected: `DOĞRULANDI`; `{"status":"ok","version":"0.1.0"}`; `200`; `www` için kod (ölçüp **WWW0** olarak kaydet); `0`.

- [ ] **Step 2: Kuru çalıştırma (salt okuma)**

Run: `cd /mnt/thunderbolt/workspaces/TED && .venv/bin/python -m src.mcp_server.tunnel_route --bolge tedy.online --tunel hp-ai-node --host mcp.tedy.online ekle --servis http://127.0.0.1:8090 --beklenen-kural 52; echo "rc=$?"`
Expected:
```
bölge: tedy.online (<bölge-id>)
tünel: hp-ai-node (<tünel-id>)
ingress: 52 kural -> 53 kural
eklenen: 1 {"hostname": "mcp.tedy.online", "service": "http://127.0.0.1:8090"}
silinen: 0
fark: +4 satır, -0 satır
dns: mcp.tedy.online CNAME <tünel-id>.cfargotunnel.com (proxied) -> oluşturulacak
--- mevcut
+++ onerilen
@@ … @@
   …
+  {
+    "hostname": "mcp.tedy.online",
+    "service": "http://127.0.0.1:8090"
+  },
   …
KURU ÇALIŞTIRMA: hiçbir şey yazılmadı
rc=0
```
(`+` satırlarının `{`/`},` sırası difflib hizalamasına göre dönebilir; sayı `+4/-0` olmalıdır.)
DUR koşulları: kural sayısı 52 değil (`hata: kural sayısı değişmiş`); `silinen` ≠ 0; `fark` eksi ≠ 0; `dns` `oluşturulacak` dışında; herhangi bir `hata:`.

- [ ] **Step 3: Uygula (genel yayın anı)**

Run:
```bash
cd /mnt/thunderbolt/workspaces/TED
.venv/bin/python -m src.mcp_server.tunnel_route --bolge tedy.online --tunel hp-ai-node --host mcp.tedy.online \
  ekle --servis http://127.0.0.1:8090 --beklenen-kural 52 --uygula --yedek-dizini ~/.local/share/ted-backups; echo "rc=$?"
```
Expected: Step 2 raporu (son satır hariç), ardından:
```
yedek: /home/mahirkurt/.local/share/ted-backups/hp-ai-node-config-<YYYYMMDDTHHMMSSZ>.json
ingress: yazıldı ve yeniden okunarak doğrulandı
dns: doğru
UYGULANDI
rc=0
```
Yolu **TR_YEDEK** olarak kaydet. `hata:` ingress yazımından sonra gelirse (ör. DNS izni yok) ingress kuralı DNS'siz durur — zararsızdır (hostname çözülmez); hata kodunu kaydet ve Geri alma'yı uygula.

- [ ] **Step 4: Doğrula — diğer 52 kural birebir, sıra dahil**

Run: `cd /mnt/thunderbolt/workspaces/TED && .venv/bin/python -m src.mcp_server.tunnel_route --bolge tedy.online --tunel hp-ai-node --host mcp.tedy.online dogrula --servis http://127.0.0.1:8090 --durum var --yedek <TR_YEDEK>; echo "rc=$?"`
Expected:
```
ingress: 53 kural
mcp.tedy.online: var
dns: doğru
DOĞRULANDI
rc=0
```

- [ ] **Step 5: Yayılım ve genel sağlık**

Run:
```bash
dig @1.1.1.1 +short mcp.tedy.online
curl -sS --doh-url https://1.1.1.1/dns-query --retry 12 --retry-delay 5 --retry-all-errors https://mcp.tedy.online/health; echo
curl -sS --doh-url https://1.1.1.1/dns-query -o /dev/null -w '%{http_code}\n' https://tedy.online/
curl -sS --doh-url https://1.1.1.1/dns-query -o /dev/null -w '%{http_code}\n' https://www.tedy.online/
```
Expected: bir ya da daha fazla Cloudflare anycast IP'si; `{"status":"ok","version":"0.1.0"}`; `200`; **WWW0**.

**Geri alma (Task 11):**
```bash
cd /mnt/thunderbolt/workspaces/TED
T=(--bolge tedy.online --tunel hp-ai-node --host mcp.tedy.online)
.venv/bin/python -m src.mcp_server.tunnel_route "${T[@]}" kaldir --beklenen-kural 53
#   beklenen: "silinen: 1 {…mcp.tedy.online…}", "fark: +0 satır, -4 satır", "dns: … -> silinecek", KURU ÇALIŞTIRMA
.venv/bin/python -m src.mcp_server.tunnel_route "${T[@]}" kaldir --beklenen-kural 53 --uygula --yedek-dizini ~/.local/share/ted-backups
#   beklenen: "ingress: yazıldı ve yeniden okunarak doğrulandı", "dns: yok", UYGULANDI (DNS önce silinir, sonra ingress)
.venv/bin/python -m src.mcp_server.tunnel_route "${T[@]}" dogrula --servis http://127.0.0.1:8090 --durum yok --yedek <TR_YEDEK>
#   beklenen: "ingress: 52 kural", "mcp.tedy.online: yok", "dns: yok", DOĞRULANDI  (ölçülmüş ön durumla birebir)
```

---

### Task 12: [OPERASYON] Genel kabul — gerçek `tdyM_` anahtarıyla `initialize` + `tools/list`, sonra test anahtarının iptali

**Files:** yok (canlı ölçüm); `$XDG_RUNTIME_DIR/ted-mcp-sp3/` sonunda silinir.

**Interfaces:**
- Consumes: Task 8 `auth.h` (etiket `sp3-kabul-20260914`); Task 10–11.
- Produces: AP3 §10 kabul kanıtı (adım çıktıları görev raporuna, anahtar değerleri hariç); iptal edilmiş test anahtarı.

Tüm komutlarda `C=(-sS --doh-url https://1.1.1.1/dns-query)` kullanılır; her blok kendi başında tanımlar.

- [ ] **Step 1: PRM ve AS metadata, Cloudflare meydan okuması yok**

Run:
```bash
C=(-sS --doh-url https://1.1.1.1/dns-query); B=https://mcp.tedy.online
for p in /.well-known/oauth-protected-resource /.well-known/oauth-protected-resource/mcp /.well-known/oauth-authorization-server; do
  echo "== $p"; curl "${C[@]}" -i "$B$p" | tr -d '\r' | grep -iE '^(HTTP/|content-type:|cf-mitigated:|\{)'; done
```
Expected: her yol için `HTTP/2 200`, `content-type: application/json`, `cf-mitigated:` satırı yok ve tek satırlık JSON gövdesi Task 8 Step 6'daki karşılığıyla birebir aynı (Starlette `JSONResponse` zaten sıkıştırılmış yazar).

- [ ] **Step 2: Kimliksiz `/mcp` → 401**

Run:
```bash
C=(-sS --doh-url https://1.1.1.1/dns-query)
curl "${C[@]}" -D - -o /dev/null -X POST -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' https://mcp.tedy.online/mcp | tr -d '\r' | grep -iE '^(HTTP|www-authenticate)'
```
Expected:
```
HTTP/2 401
www-authenticate: Bearer realm="ted-mcp", resource_metadata="https://mcp.tedy.online/.well-known/oauth-protected-resource"
```

- [ ] **Step 3: `initialize` + `tools/list` (AP3 kabulü)**

Run:
```bash
W="$XDG_RUNTIME_DIR/ted-mcp-sp3"; C=(-sS --doh-url https://1.1.1.1/dns-query)
M=(-X POST -H @"$W/auth.h" -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' -H 'MCP-Protocol-Version: 2025-06-18')
curl "${C[@]}" "${M[@]}" --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"sp3-kabul","version":"0"}}}' \
  https://mcp.tedy.online/mcp | tr -d '\r' | sed -n 's/^data: //p' | jq -c '{protocolVersion: .result.protocolVersion, name: .result.serverInfo.name, version: .result.serverInfo.version}'
curl "${C[@]}" "${M[@]}" --data '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  https://mcp.tedy.online/mcp | tr -d '\r' | sed -n 's/^data: //p' | jq -c '[.result.tools[].name] | sort'
```
Expected:
```
{"protocolVersion":"2025-06-18","name":"TEDY edupedia","version":"0.1.0"}
["edupedia_baglam","edupedia_durum","edupedia_kapsam","edupedia_kaynak_oku","edupedia_rehber"]
```

- [ ] **Step 4: CORS**

Run:
```bash
C=(-sS --doh-url https://1.1.1.1/dns-query)
curl "${C[@]}" -o /dev/null -D - -X OPTIONS https://mcp.tedy.online/mcp -H 'Origin: https://claude.ai' \
  -H 'Access-Control-Request-Method: POST' -H 'Access-Control-Request-Headers: authorization, content-type, mcp-protocol-version' \
  | tr -d '\r' | grep -iE '^(HTTP|access-control-)' | LC_ALL=C sort
curl "${C[@]}" -o /dev/null -D - -X OPTIONS https://mcp.tedy.online/mcp -H 'Origin: https://claude.ai.evil.example' \
  -H 'Access-Control-Request-Method: POST' | tr -d '\r' | grep -ciE '^access-control-allow-origin'
curl "${C[@]}" -o /dev/null -D - -X POST https://mcp.tedy.online/mcp -H 'Origin: https://claude.ai' -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  | tr -d '\r' | grep -iE '^(HTTP|access-control-allow-origin|access-control-expose-headers)'
```
Expected:
```
HTTP/2 204
access-control-allow-headers: authorization, content-type, mcp-session-id, mcp-protocol-version
access-control-allow-methods: GET, POST, DELETE, OPTIONS
access-control-allow-origin: https://claude.ai
access-control-expose-headers: mcp-session-id, www-authenticate
access-control-max-age: 600
0
HTTP/2 401
access-control-allow-origin: https://claude.ai
access-control-expose-headers: mcp-session-id, www-authenticate
```
(Yanıtta `vary` başlığı `Origin` içerir; Cloudflare ek `vary` değerleri ekleyebilir.)

- [ ] **Step 5: Genel uçta gövde sınırı → 413**

Run:
```bash
head -c 16385 /dev/zero | tr '\0' a | curl -sS --doh-url https://1.1.1.1/dns-query -o /dev/null -w '%{http_code}\n' -X POST \
  -H 'Content-Type: application/x-www-form-urlencoded' --data-binary @- https://mcp.tedy.online/oauth/token
```
Expected: `413`.

- [ ] **Step 6: Onay sayfası (kalıcı DCR, S256, kesin liste)**

Run:
```bash
W="$XDG_RUNTIME_DIR/ted-mcp-sp3"; C=(-sS --doh-url https://1.1.1.1/dns-query); B=https://mcp.tedy.online
curl "${C[@]}" -o "$W/reg.json" -w '%{http_code}\n' -X POST -H 'Content-Type: application/json' \
  --data '{"redirect_uris":["https://claude.ai/api/mcp/auth_callback"],"client_name":"sp3-kabul"}' "$B/oauth/register"
CID=$(jq -r .client_id "$W/reg.json")
Q="response_type=code&client_id=$CID&redirect_uri=https%3A%2F%2Fclaude.ai%2Fapi%2Fmcp%2Fauth_callback&code_challenge=E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM&state=sp3"
curl "${C[@]}" -D "$W/az.h" -o "$W/az.html" -w '%{http_code}\n' "$B/oauth/authorize?$Q&code_challenge_method=S256"
grep -o 'data-client_id="[^"]*"' "$W/az.html"; grep -c 'sp3-kabul' "$W/az.html"; grep -c 'https://claude.ai/api/mcp/auth_callback' "$W/az.html"
tr -d '\r' < "$W/az.h" | grep -iE '^(x-frame-options|content-security-policy)' | sed -E 's/(content-security-policy: ).*(frame-ancestors [^;]*).*/\1… \2 …/I'
curl "${C[@]}" -o /dev/null -w '%{http_code}\n' "$B/oauth/authorize?$Q&code_challenge_method=s256"
curl "${C[@]}" -o /dev/null -w '%{http_code}\n' -X POST -H 'Content-Type: application/json' \
  --data '{"redirect_uris":["https://claude.ai/any/other/path"]}' "$B/oauth/register"
```
Expected: `201`; `200`; `data-client_id="343043757928-mivqip09orvrf73m7kj9b0atohgin2ho.apps.googleusercontent.com"`; `1` ya da fazlası; `1` ya da fazlası; `x-frame-options: DENY` ve `content-security-policy: … frame-ancestors 'none' …`; `400` (küçük harf `s256`); `400` (listede olmayan yol). Bu adım bir DCR kaydı bırakır (kod üretmediği için 24 saat sonra temizlenebilir).

- [ ] **Step 7: Kenar hız sınırı işlevsel kanıtı (`mcp.tedy.online` üzerinden)**

Run:
```bash
curl -sS --doh-url https://1.1.1.1/dns-query --parallel --parallel-max 10 -o /dev/null -w '%{http_code}\n' \
  $(printf 'https://mcp.tedy.online/mcp %.0s' $(seq 1 90)) | LC_ALL=C sort | uniq -c
curl -sS --doh-url https://1.1.1.1/dns-query https://mcp.tedy.online/health; echo
```
Expected: `… 401` satırı ve en az bir `… 429` satırı (GET kimliksiz → 401; eşik aşımı → 429); `/health` kuralın dışındadır → `{"status":"ok","version":"0.1.0"}`. 429 yoksa 10 sn bekleyip 150 istekle bir kez tekrarla; yine yoksa DUR.

- [ ] **Step 8: Test anahtarının iptali**

Run:
```bash
W="$XDG_RUNTIME_DIR/ted-mcp-sp3"
cd /mnt/thunderbolt/workspaces/TED && .venv/bin/python -m src.mcp_server.keys iptal --etiket sp3-kabul-20260914
.venv/bin/python -m src.mcp_server.keys listele | grep -c $'^sp3-kabul-20260914\t.*\tiptal$'
curl -sS --doh-url https://1.1.1.1/dns-query --retry 6 --retry-delay 5 -o /dev/null -w '%{http_code}\n' -X POST -H @"$W/auth.h" \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  --data '{"jsonrpc":"2.0","id":9,"method":"tools/list"}' https://mcp.tedy.online/mcp
rm -rf "$W"; test ! -e "$W" && echo temizlendi
```
Expected: `iptal edildi: sp3-kabul-20260914`; `1`; `401` (`--retry` Step 7'nin 10 sn'lik 429 cezasını bekler); `temizlendi`.

- [ ] **Step 9: Son taramalar**

Run:
```bash
journalctl --user -u ted-mcp --since today --no-pager | grep -cE 'tdyM_|tdyK_|Bearer |access_token|refresh_token|code_verifier|TED_MCP_FORM_SECRET='
curl -sS --doh-url https://1.1.1.1/dns-query -o /dev/null -w '%{http_code}\n' https://tedy.online/
systemctl --user is-active ted-mcp ted-dashboard
```
Expected: `0`; `200`; `active` iki kez.

---

### Task 13: [İNSAN] Google Cloud Console — Authorized JavaScript origin `https://mcp.tedy.online`

API yok; operatör (Mahir) yapar. Canlı kabul (Task 12) buna bağlı değildir; OAuth ile bağlanan istemciler (claude.ai, ChatGPT, Grok, Gemini — alt proje 6) buna bağlıdır. Yönlendirme URI'si **eklenmez**: onay sayfası GSI'yı JavaScript geri çağrı kipinde kullanır.

- [ ] **Step 1: Konsol adımları**

1. `https://console.cloud.google.com/apis/credentials` adresini, TED'in OAuth istemcisinin bulunduğu projede aç (proje numarası `343043757928`). Yeni arayüzde yol: **Google Auth Platform → Clients**.
2. İstemci kimliği `343043757928-mivqip09orvrf73m7kj9b0atohgin2ho.apps.googleusercontent.com` olan **Web application** istemcisine tıkla.
3. **Authorized JavaScript origins** → **+ ADD URI** → `https://mcp.tedy.online` (sonda `/` yok, yol yok, port yok).
4. Mevcut origin'lere (`https://tedy.online` vb.) ve **Authorized redirect URIs** listesine dokunma. Güvenilmeyen betik çalıştırabilecek hiçbir origin ekleme (güvenlik incelemesi R7).
5. **SAVE**. Google'ın notuna göre ayarın yayılması 5 dakika ile birkaç saat sürebilir.

- [ ] **Step 2: Doğrulama (tarayıcı; gizli pencere)**

1. Bir DCR istemcisi al (istemci kimliği gizli değildir):
   ```bash
   curl -sS --doh-url https://1.1.1.1/dns-query -X POST -H 'Content-Type: application/json' \
     --data '{"redirect_uris":["https://claude.ai/api/mcp/auth_callback"],"client_name":"sp3-origin-kontrol"}' \
     https://mcp.tedy.online/oauth/register | jq -r .client_id
   ```
2. Tarayıcıda aç (`<CID>` yerine yukarıdaki değer): `https://mcp.tedy.online/oauth/authorize?response_type=code&client_id=<CID>&redirect_uri=https%3A%2F%2Fclaude.ai%2Fapi%2Fmcp%2Fauth_callback&code_challenge=E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM&code_challenge_method=S256&state=sp3-origin`
3. Beklenen: "edupedia'yı TEDY hesabına bağla" sayfası, `sp3-origin-kontrol` adı ve tam `redirect_uri` görünür; **"Google ile devam et"** düğmesi çizilir. DevTools → Console'da `[GSI_LOGGER]: The given origin is not allowed for the given client ID` hatası ve `accounts.google.com` için CSP ihlali **yok**. Hata varsa yayılmayı bekleyip yeniden dene; saatler sonra sürüyorsa Step 1'deki origin yazımını kontrol et.
4. İsteğe bağlı uçtan uca kanıt (kod üretmeden): Google düğmesiyle `reader` rolündeki bir aile hesabıyla (ör. `mahirkurtmd@gmail.com`) giriş yap → sunucu reddeder ("Bu hesap TEDY edupedia bağlantısını onaylayamaz." ya da S1b'nin rol reddi sayfası), Onayla adımı açılmaz, `claude.ai`'ye yönlendirme olmaz. Bu, Google kimliğinin sunucuda doğrulandığını ve rol kapısını birlikte kanıtlar. `full` hesapla Onayla'ya **basma** (kullanılmayan kod üretir).

Sonucu (tarih, doğrulama kanıtı) denetleyici kaydına yaz. Geri alma: aynı ekranda `https://mcp.tedy.online` satırını sil ve kaydet.

---

### Task 14: Kapanış kaydı — spec §12b

**Files:**
- Modify: `docs/superpowers/specs/2026-09-13-edupedia-tedy-orkestrator-design.md` (§12b)

**Interfaces:**
- Consumes: Task 9 Bölüm A/B kararları (gözden geçiren, **R**, **H**, **D**), SDD defterindeki ertelenen düşük bulgu `Ruling:` satırları, Task 7 **ANM** ve Task 8 Step 10b sonucu, Task 10 dalı ve **RL_YEDEK** dosya adı, Task 11 **TR_YEDEK** dosya adı, Task 12 sonuçları, Task 13 durumu.
- Produces: kalıcı canlı kabul kaydı ve denetleyicinin kullanıcıya son raporunun satırları.

- [ ] **Step 1: §12b'ye ekle (değerleri kayıttan birebir doldur; boş kalan alan olmaz)**

Worktree'de, §12b'nin son maddesinden sonra:

```markdown
- **Canlı kabul (alt proje 3, <Task 12 tarihi>):** Güvenlik kapısı TEMİZ — <gözden geçiren>, son inceleme <R kısa SHA>,
  dağıtılan <D kısa SHA>; ertelenen düşük bulgular (RFC 7009 `/oauth/revoke`, `tdyM_` son kullanma, R3, R6) SDD defterinde
  denetleyici `Ruling:` satırlarıyla kayıtlı. anamnesis: <anahtar yapılandırıldı, `hit` | anahtar yok, `skipped:anahtar yok` — ekleme bekliyor>.
  Kenar hız sınırı dal <A|B|C>
  (`/oauth/register|authorize|token`, `/mcp`; IP başına 10 sn'de <eşik>; yedek `<RL_YEDEK dosya adı>`).
  `hp-ai-node` ingress 52 → 53 kural, `mcp.tedy.online` → `http://127.0.0.1:8090`, proxied CNAME (yedek
  `<TR_YEDEK dosya adı>`). Genel uçta: PRM 200, `/mcp` kimliksiz 401 + `WWW-Authenticate`, `/oauth/token` 16 385 bayt
  → 413, CORS `https://claude.ai` 204, `tdyM_` anahtarıyla `initialize` (`2025-06-18`, `TEDY edupedia` `0.1.0`) +
  `tools/list` beş araç; test anahtarı `sp3-kabul-20260914` iptal edildi. Google JavaScript origin: <eklendi ve
  doğrulandı <tarih> | bekliyor>.
```

- [ ] **Step 1b: Kullanıcıya son rapor satırları**

Denetleyicinin kullanıcıya son raporuna şu satırlar girer (değerler kayıttan):
1. Ertelenen dört düşük bulgunun denetleyici kararları — her biri SDD defterindeki `Ruling:` satırından tek cümleyle: RFC 7009 `/oauth/revoke` ucu ve `tdyM_` son kullanma tarihi (F8'in ertelenen kısmı), R3 kök liste e-postasında Unicode katlaması (sömürülemez), R6 eşzamanlı yenilemede aile iptali (spec §6.1 gereği değişmez). Kaynak: `grep -F -e 'RFC 7009' -e '(R3)' -e '(R6)' /mnt/thunderbolt/workspaces/TED/.superpowers/sdd/2026-09-13-ted-mcp-orkestrator-cekirdegi/progress.md | grep '^Ruling:'`.
2. **ANM** = `atlandı` ise: "Kullanıcı eylemi: `ANAMNESIS_MCP_API_KEY` eksik — ted-mcp çalışıyor, anamnesis `skipped:anahtar yok` ile dürüstçe degrade. Eklemek için: `cd /mnt/thunderbolt/workspaces/TED && doppler secrets get ANAMNESIS_MCP_API_KEY --plain --project cureohub --config dev_personal | .venv/bin/python -m src.mcp_server.env_prep ayarla ANAMNESIS_MCP_API_KEY --stdin && systemctl --user restart ted-mcp`; doğrulama Task 8 Step 10b (`hit`)."
3. Task 13 bekliyorsa: "Kullanıcı eylemi: Google Cloud Console'da `https://mcp.tedy.online` Authorized JavaScript origin'i (Task 13)."

- [ ] **Step 2: Commit, ana checkout'a ileri alma ve push (denetleyici onaylı; Task 6 ile aynı yetki)**

```bash
cd /mnt/thunderbolt/workspaces/TED/.worktrees/ted-mcp-cekirdek
git add docs/superpowers/specs/2026-09-13-edupedia-tedy-orkestrator-design.md
git commit -m "docs(spec): alt proje 3 canlı kabul kaydı — mcp.tedy.online yayında

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git -C /mnt/thunderbolt/workspaces/TED merge --ff-only feat/ted-mcp-cekirdek   # denetleyici onaylı; yalnız belge — yeniden başlatma gerekmez
git -C /mnt/thunderbolt/workspaces/TED push origin main                        # hızlı ileri; force-push asla
```

---

## Tam geri alma — ölçülmüş ön duruma dönüş (2026-09-14)

Sıra önemlidir: önce genel erişim kapanır, sonra kimlik, sonra süreç, sonra sırlar. Her komut kendi görevinin "Geri alma" bloğunun beklenen çıktılarını üretir.

1. **Genel erişimi kapat (Task 11 geri alma):** `tunnel_route … kaldir --beklenen-kural 53` kuru → `--uygula --yedek-dizini ~/.local/share/ted-backups` → `dogrula --durum yok --yedek <TR_YEDEK>` → `ingress: 52 kural`, `mcp.tedy.online: yok`, `dns: yok`, `DOĞRULANDI`. TR_YEDEK kaybolduysa `dogrula --durum yok` (yedeksiz) en az kural yokluğunu ve DNS yokluğunu kanıtlar.
2. **Kenar hız sınırını kaldır (Task 10 geri alma):** `edge_ratelimit --bolge tedy.online kaldir --beklenen-kural 1` kuru → `--uygula --yedek-dizini …` → `dogrula` → `SORUN ted-mcp hız sınırı yok` (hedef durum). Dal B'de kalan `mevcut:` satırı Task 10 Step 2'de kaydedilenle birebir aynı.
3. **Tüm kimlikleri geçersiz kıl:**
   ```bash
   cd /mnt/thunderbolt/workspaces/TED
   for e in $(.venv/bin/python -c 'from src import roles; print(" ".join(sorted(roles.FULL_ACCESS_EMAILS)))'); do
     .venv/bin/python -m src.mcp_server.keys oauth-iptal --email "$e"; done
   .venv/bin/python -m src.mcp_server.keys listele      # her satır "iptal" olmalı; değilse: keys iptal --etiket <etiket>
   ```
4. **Süreci durdur (Task 8 geri alma):** `systemctl --user disable --now ted-mcp`; `rm ~/.config/systemd/user/ted-mcp.service`; `systemctl --user daemon-reload`; `ss -ltn 'sport = :8090' | tail -n +2 | wc -l` → `0`. Token deposunu kenara al: `mv /mnt/thunderbolt/workspaces/TED/output/ted_mcp_oauth.sqlite3* ~/.local/share/ted-backups/`.
5. **Sırları kaldır (Task 7 geri alma):** `env_prep dashboard-anahtari-kaldir --etiket ted-mcp`, `env_prep kaldir TED_MCP_FORM_SECRET`, (Task 7 Step 5 yazdıysa) `env_prep kaldir ANAMNESIS_MCP_API_KEY`; `systemctl --user restart ted-dashboard`; `env_prep durum` → Task 7 Step 1 çıktısı; eski `ted-mcp` dashboard anahtarıyla `/api/exams` → `401`.
6. **Google origin (isteğe bağlı, Task 13 geri alma):** konsolda `https://mcp.tedy.online` satırını sil.
7. **Kod:** `main` ve `origin/main` geri sarılmaz, force-push yapılmaz. Kodun `main`'de kalması zararsızdır (birim kurulu değil, rota yok). Dashboard'un önceki koda dönmesi gerekiyorsa Task 7 "Geri alma — dashboard kodu" (geçici **M0** worktree'si + birim drop-in'i) uygulanır; kalıcı düzeltme denetleyicinin hazırladığı `git revert` commit'leriyle normal push'la gider, ardından drop-in ve geçici worktree kaldırılır.

Ön durum doğrulaması: `dig @1.1.1.1 +short mcp.tedy.online` boş; `https://tedy.online/` `200`; `systemctl --user cat ted-mcp` → `No files found`; `.env` adları "Ölçülmüş ön durum" listesiyle aynı (`env_prep durum` Task 7 Step 1 çıktısı); `API_KEYS` etiketleri yalnız `default`.

---

## Plan sonu — alt proje 3 kabul ölçütleri

1. Kod görevleri (1–5) worktree'de ağsız testlerle yeşil: `B+47 passed, S skipped`, `failed`/`error` yok; spec §4.1 portu `8090` ve §12b AP3 kayıtları mevcut.
2. `ted-mcp` systemd user servisi etkin, yalnız `127.0.0.1:8090`'da; `.env` `env_prep durum` rc 0; journal'da sır yok; token deposu dosyaları 600 (`output/` 775 korunur); anamnesis ya `hit` ya da dürüst `skipped:anahtar yok` (Task 8 Step 10b).
3. Güvenlik kapısı: Bölüm A `TEMİZ` (S1a + S1b kapsamlı yeniden incelemeleri ve AP2 son tüm-dal incelemesi temiz; ertelenen dört düşük bulgunun SDD defterinde denetleyici `Ruling:` satırı var) `main` ileri alma/push ve dashboard yeniden başlatmasından **önce**; Bölüm B `TEMİZ` (D1–D10 evet) hiçbir genel DNS/ingress kaydından **önce**.
4. Kenar hız sınırı `DOĞRULANDI` ve işlevsel olarak 429 üretti; DNS kaydından **önce** uygulandı.
5. `hp-ai-node` ingress 53 kural, önceki 52 kural sıra dahil birebir; `tedy.online` `200`.
6. Genel uçta: PRM 200; `/mcp` kimliksiz 401 + doğru `WWW-Authenticate`; `/oauth/token` 16 385 bayt → 413; CORS `https://claude.ai` 204; gerçek `tdyM_` anahtarıyla `initialize` + `tools/list` beş AP2 aracını döndürdü; test anahtarı iptal edildi ve 401 alıyor.
7. Google Authorized JavaScript origin eklendi ve onay sayfasında GSI hatasız çiziliyor (Task 13) — ya da "bekliyor" olarak kayıtlı ve alt proje 6 öncesi kapatılacak.
8. Spec §12b'de canlı kabul kaydı (Task 14); `main` ve `origin/main` hızlı ileri alınmış, force-push yok.
9. Dashboard yeniden başlatmasının önce/sonra `/` ve `/api` kodları ve sağlık anahtarları aynı (Task 7 Step 7–8).
10. Kullanıcıya son rapor ertelenen düşük bulgu kararlarını ve gerekiyorsa anamnesis anahtarı ile Google origin eylemlerini bildirir (Task 14 Step 1b).
