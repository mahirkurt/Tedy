# TEDY Assistant Go-Live Runbook

Bu doküman, dashboard'un gömülü asistanını (`/v1/chat/completions`, `/v1/models`) güvenle
canlıya almak ve doğrulamak için izlenecek tek yazılı yolu tarif eder. Sohbet yolu Gemini
API üzerinden çalışır; yerel bir LLM sunucusuna ihtiyaç duymaz.

## 0) Önkoşullar

Servis ortamında (`.env` veya systemd `Environment=`) şu değişkenler tanımlı olmalı:

| Değişken | Amaç |
|---|---|
| `GEMINI_API_KEY` | Sohbet modeli (Gemini). Yoksa `/v1/chat/completions` **çökmez** — `200` döner, jenerik bir yedek cevap ve `warning:limited_confidence` bayrağıyla (bkz. §11). |
| `MUFREDAT_MCP_API_KEY` | `maarif-mufredat` MCP sunucusu (müfredat/kazanım/ders kitabı araçları). |
| `EGITIM_KAYNAK_MCP_API_KEY` | `egitim-kaynak` MCP sunucusu (OER arama araçları). |
| `DASHBOARD_SECRET_KEY` | Flask session imzası; eksikse API import'ta patlar (bkz. `dashboard_api.py`). |
| `ASSISTANT_API_KEY` | `/v1/models` ve `/v1/chat/completions` için Bearer auth. |

Not: Ollama'ya ihtiyaç **yoktur**. Sohbet yolu (`GeminiClient`) yalnızca Gemini bulut
modellerini çağırır; gömme (embedding) tabanlı vektör arama da şu an devre dışıdır (bkz.
§5) — yani bu iki anahtar dışında yerel bir model sunucusu ayağa kaldırmaya gerek yok.

## 1) Dağıtım: kodu ve arayüzü ana checkout'a al

Servisi besleyen kod ve statik dosyalar bu worktree'de **değil**, ana checkout'ta
(`/mnt/thunderbolt/workspaces/TED`) yaşar:

- `ExecStart=/mnt/thunderbolt/workspaces/TED/.venv/bin/gunicorn ... src.dashboard_api:app`
  — Python kodu `WorkingDirectory=/mnt/thunderbolt/workspaces/TED`'den yüklenir.
- SPA, aynı checkout'un `dashboard-dist/` dizininden sunulur (`dashboard_api.py`'deki
  `DIST_DIR = PROJECT_ROOT / "dashboard-dist"`).

**Ölçülen gerçek:** bu dokümanın anlattığı asistan (Gemini sohbet yolu, MCP araç kaydı,
`meta.degraded`, atıf çipleri, SSE akışı) `feat/assistant-mufredat-grounding` dalında
yaşıyor. Ana checkout şu an `feat/carbon-token-fidelity` dalında duruyor ve bu özelliği
**içermiyor**:

```
git -C /mnt/thunderbolt/workspaces/TED cat-file -e feat/carbon-token-fidelity:src/assistant_tools.py
# -> "fatal: path 'src/assistant_tools.py' exists on disk, but not in 'feat/carbon-token-fidelity'"
git -C /mnt/thunderbolt/workspaces/TED show feat/carbon-token-fidelity:src/dashboard_api.py | grep -c degraded
# -> 0
```

Yani `.env`'e anahtar eklemek ve servisi restart etmek **tek başına yeterli değil**: ana
checkout'taki kod hâlâ eskiyse, §2'deki `curl` doğrulaması `meta.degraded` alanı
bulunmadığı için hata verir (ya da bir ara sürümde alan `None` döner) — ikisi de "sorun
yok, degradasyon yok" anlamına **gelmez**; "yeni kod henüz dağıtılmadı" anlamına gelir
(bkz. §2'nin doğrulama notu). Her şey "başarılı" görünse bile kod eskiyse ortada yeni
asistan yoktur — MCP araçları, atıf çipleri, kaynak paneli, SSE akışının hiçbiri o kodda
yok.

Bu dalın ana checkout'a hangi yolla (`git merge`, rebase, cherry-pick) ve hangi hedef
dala alınacağı — `feat/carbon-token-fidelity` mi, `main` mı — **kullanıcının kararıdır**;
bu doküman karar vermez. Adımlar (yaz, çalıştırma — ana checkout'a girmek ve
`npm run build` çalıştırmak bu runbook'un yetkisinde değil):

```bash
cd /mnt/thunderbolt/workspaces/TED
git merge feat/assistant-mufredat-grounding
cd dashboard && npm run build
cd ..
```

`npm run build` (`tsc -b && vite build`) `dashboard-dist/`'i günceller; SPA statik
dosyaları oradan sunulur — derlenmezse arayüz eski kalır, backend'in kabul ettiği yeni
uç noktalar (ör. `/v1/chat/completions`'ın SSE varyantı) olsa bile arayüz onları hiç
çağırmaz. Ancak bundan sonra §2'deki `.env` anahtarları + restart + doğrulama adımına geç.

## 2) ⛔ DAĞITIM TUZAĞI — bu adım atlanırsa özellik sessizce ölür

Servis (`~/.config/systemd/user/ted-dashboard.service`) ortamını `EnvironmentFile=.env`'den
alıyor. `MUFREDAT_MCP_API_KEY` ve `EGITIM_KAYNAK_MCP_API_KEY` geliştirme makinesinde
**interaktif kabuk ortamında** duruyor olabilir ama **`.env` içinde değilse** gunicorn onları
hiç göremez: kayıt defteri sıfır müfredat aracıyla açılır, asistan yalnız yerel okul
verisinden (`ogrenci_verisi_ara`) cevap verir ve arayüzü test eden kişiye **sağlıklı
görünür** — çünkü kendi kabuğundan miras aldığı anahtarlarla test etmiştir, üretim onları
görmez. `degraded()` bu durumu bildirir ve arayüzde rozet yanar, ama **rozet arızayı
görünür kılar — gidermez.**

Dağıtımdan önce iki anahtarı `.env`'e ekle (dosya zaten mod 600 ve gitignore'lu), servisi
yeniden başlat ve doğrula.

### Doğrulama — asıl kanıt servise sormaktır

Servisi yeniden başlat, sonra **çalışan servise gerçek bir istek at** ve yanıtın
`meta.degraded` alanına bak. Bu, servisin fiilen gördüğü ortamı ölçer — hangi kabuktan
çalıştırdığın önemli değildir:

```bash
systemctl --user daemon-reload
systemctl --user restart ted-dashboard
curl -s -H "Authorization: Bearer $ASSISTANT_API_KEY" -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"merhaba"}],"session_id":"deploy-check"}' \
  http://127.0.0.1:8085/v1/chat/completions \
  | python -c "import json,sys; print('degraded:', json.load(sys.stdin)['meta']['degraded'])"
```

Beklenen: `degraded: []`. Boş değilse `.env`'i kontrol et, tekrar başlat, tekrar dene.

**`meta.degraded` alanı hiç yoksa** (yukarıdaki `python -c` `KeyError` ile patlarsa) **veya
`degraded: None` dönerse, bu "degradasyon yok, her şey sağlıklı" demek DEĞİLDİR** —
çalışan kodun bu alanı henüz üretmediği, yani §1'deki gibi ana checkout'un hâlâ eski
(bu özelliği içermeyen) bir dalda olduğu anlamına gelir. Önce §1'i tekrar kontrol et.

**⚠️ Bir yerel `python -c "from src.assistant_tools import build_registry; ..."` çağrısı
bunun yerine geçmez — tuzağın kendisine düşer.** `src/assistant_tools.py` hiçbir yerde
`.env`'i yüklemiyor (`load_env()` çağrısı orada yok — yalnız `dashboard_api.py`,
`reindex_assistant.py` ve scraper script'lerinde var). Bu yüzden `build_registry()`'yi
çıplak çalıştırdığında yalnız komutu çalıştıran kabuğun ortamına bakar, `.env`'e değil.
Ölçüldü: bu repoda `.env`'de iki MCP anahtarı da **yok**, ama normal bir interaktif
kabukta (kendi kabuğunda kalıcı export edilmişse) bu komut yine de `araçlar: 10 |
degraded: []` basar — tam olarak, bu dokümanın az yukarıda uyardığı "kendi kabuğundan
miras aldığın anahtarlarla test etme" hatasının kendisini doğrulama adımı sanıp geçersin.

Yerel bir ön-kontrol istiyorsan (örn. deploy'dan önce, servise erişemeden), kabuktan miras
alınan değerleri **açıkça temizleyerek** çalıştır — aksi hâlde kontrol kabuğun ortamını
ölçer, `.env`'i değil:

```bash
env -u MUFREDAT_MCP_API_KEY -u EGITIM_KAYNAK_MCP_API_KEY python -c "
from src.assistant_tools import build_registry
reg = build_registry(lambda q, k: [])
print('araçlar:', len(reg.declarations()), '| degraded:', reg.degraded())
"
```

Bu, sistemin `.env` dosyasının kendisinde ne olduğuna en yakın yerel tahmindir, ama yine
de bir tahmindir — asıl kanıt yukarıdaki HTTP kontrolüdür.

## 3) MCP sağlık kontrolü (araç adları)

`/v1/chat/completions` yalnız `degraded` listesini döner, hangi araçların yüklendiğini
değil. Araç adlarını görmek istersen aynı `env -u` uyarısı burada da geçerlidir — bu komut
da `.env`'i değil, çalıştırıldığı kabuğun ortamını okur:

```bash
env -u MUFREDAT_MCP_API_KEY -u EGITIM_KAYNAK_MCP_API_KEY python -c "
from src.assistant_tools import build_registry
reg = build_registry(lambda q, k: [])
print('araçlar:', [d['name'] for d in reg.declarations()])
print('degraded:', reg.degraded())
"
```

Beklenen (iki anahtar da gerçekten mevcutsa): 10 araç adı (`ogrenci_verisi_ara` + 9 MCP
aracı), boş `degraded`. Go-live kararı için §2'deki HTTP kontrolüne güven; bu komut yalnız
hangi araçların tanımlandığını incelemek için bir geliştirici aracıdır.

## 4) Model zinciri kontrolü

```bash
python -c "from src.assistant_core import GeminiClient; print(GeminiClient.FAST_MODELS, GeminiClient.DEEP_MODELS)"
```

`FAST_MODELS` genel sohbet için kullanılan zincir, `DEEP_MODELS` plan modu ve zor sorular
için önce denenen model. Bir model kota/404 hatası verirse `GeminiClient` otomatik olarak
zincirdeki bir sonrakine geçer; `gemini-2.0-*` aileleri API'nin artık 404 döndürmesi
nedeniyle zincirden çıkarıldı (bkz. `assistant_core.py` içindeki yorum). İstek gövdesindeki
`model` alanı **kozmetiktir** — `/v1/chat/completions` onu okumaz, her zaman bu sabit
zincirden seçer; `/v1/models` de yalnız `FAST_MODELS`'i listeler.

## 5) Bilgi tabanı indeksi (reindex)

```bash
python src/reindex_assistant.py --full
python src/assistant_ops.py verify-index --max-age-minutes 180
```

Beklenen çıktı dosyaları: `output/assistant_index/manifest.json`, `chunks.json`,
`meta.json`. `files_indexed > 0` ve `chunks_indexed > 0` olmalı.

**Ölçülen gerçek:** bu koddaki gömme (embedding) tabanlı vektör arama şu an tamamen devre
dışı — `reindex()` her chunk için `embedded_chunks_new`'i artırmadan geçer ve meta dosyasına
`"embeddings_enabled": false`, `"embed_model": null` yazar; retrieval salt BM25 (anahtar
kelime) üzerinden çalışır. Hiçbir adımda Ollama çağrılmaz. Bu yüzden
`assistant_ops.py verify-index --require-embeddings` bu haliyle **her zaman başarısız olur**
(`embedded_chunks<=0`) — go-live gate'i olarak kullanma; yukarıdaki `--require-embeddings`'siz
komut yeterli doğrulamadır.

## 6) Servis: neden `gthread`

Servis dosyası `--workers 2 --worker-class gthread --threads 4` kullanıyor (varsayılan
senkron worker değil). Gerekçe ölçüldü: sync worker'da uzun süren bir SSE isteği tek worker'ı
tamamen bloklar — eşzamanlı bir `/api/health` isteği ~4.5s beklerdi. `gthread` + 4 thread ile
eşzamanlı slot sayısı 2'den 8'e çıkıyor; aynı senaryoda `/api/health` **0.015s**'de dönüyor.
8'den fazla eşzamanlı uzun istek hâlâ kuyruğa girer, ama bu ailenin trafiği için kabul
edilebilir.

Servis dosyası zaten bu haliyle düzenli (`~/.config/systemd/user/ted-dashboard.service`),
ama henüz **uygulanmadı** — şu an çalışan gunicorn süreçleri hâlâ eski `--workers 2` (thread'siz)
komut satırıyla ayakta. Değişikliği devreye almak için:

```bash
systemctl --user daemon-reload
systemctl --user restart ted-dashboard
journalctl --user -u ted-dashboard -f
```

### Geri alma

`.env`'e yanlış bir anahtar girildiyse veya `gthread` restart'ı sorun çıkardıysa (servis
ayağa kalkmıyor, sürekli crash-loop):

```bash
# 1) .env'i önceki hâline döndür (yedeğin yoksa eklediğin satırları elle çıkar)
# 2) unit dosyasını eski (thread'siz) hâline döndür:
#    --workers 2 --worker-class gthread --threads 4  ->  --workers 2
# 3) uygula:
systemctl --user daemon-reload
systemctl --user restart ted-dashboard
systemctl --user status ted-dashboard
journalctl --user -u ted-dashboard -n 50 --no-pager
```

`gthread`'e geri dönmek zorunlu değil — `sync` worker ile servis yine çalışır, yalnız §6'nın
başındaki eşzamanlılık kazanımını kaybedersin (uzun bir SSE isteği sırasında diğer istekler
yeniden bloklanır).

## 7) API smoke test

```bash
python src/assistant_ops.py smoke \
  --base-url http://127.0.0.1:8085 \
  --api-key "$ASSISTANT_API_KEY" \
  --timeout 240
```

Doğrular:

- `/v1/models` keysiz `401`
- `/v1/models` key ile `200`
- `/v1/chat/completions` minimal payload `200`
- `plan=true` çağrısında `plan_blocks` dolu

`--model` bayrağı isteğe eklenen etikettir, backend model seçimini etkilemez (§4).

## 8) CureoHub senaryo doğrulaması

```bash
python src/assistant_ops.py validate-cureohub \
  --base-url http://127.0.0.1:8085 \
  --api-key "$ASSISTANT_API_KEY" \
  --timeout 90 \
  --output output/cureohub_validation.json
```

Kontrol edilenler:

- Okul verisi sorusunda citation (`ogrenci_verisi_ara` çağrılmış olmalı — bu kontrolün
  anlamlı geçmesi için `output/scraped_data.json`'da gerçek veri olması gerekir; boş/taze
  olmayan bir ortamda bu senaryo yanlış-negatif verebilir, bu bir dağıtım arızası değildir)
- Plan modunda plan blocks
- Kaynak-yok durumda limited-confidence sinyali
- Riskli içerikte safety flag

## 9) Degradasyon beklentisi

MCP anahtarlarından biri veya ikisi de servise ulaşmıyorsa asistan çökmez: çalışmaya devam
eder, yalnız yerel okul verisiyle (`ogrenci_verisi_ara`) yanıt verir ve arayüzde rozet
gösterir. Ölçülen log çıktısı (iki anahtar da kapalıyken):

```
MCP maarif-mufredat disabled: MUFREDAT_MCP_API_KEY not set
MCP egitim-kaynak disabled: EGITIM_KAYNAK_MCP_API_KEY not set
araçlar: ['ogrenci_verisi_ara']
degraded: ['egitim-kaynak', 'maarif-mufredat']
```

Bu bir arıza değil, tasarlanmış davranıştır — sistem sağlıklı numarası yapmaz, her sunucuyu
adıyla degraded ilan eder. Ama **rozet arızayı görünür kılar, gidermez**: §2'deki kontrolü
her dağıtımdan sonra çalıştır.

## 10) Metrikler ve prompt replay

```bash
python src/assistant_ops.py metrics \
  --metrics-path output/assistant_metrics.jsonl \
  --output output/assistant_metrics_report.json \
  --balanced-gate
```

`--balanced-gate` şu eşikleri kontrol eder: p95 gecikme ≤10s, citation coverage ≥%75,
kritik (`risk:*`) safety flag sayısı 0. Az sayıda/sentetik kayıtla (ör. taze bir ortamda
birkaç smoke-test isteği) bu kapı beklenen şekilde başarısız olabilir — gerçek trafik
biriktikçe anlamlı hale gelir.

Bir prompt setini tekrar oynatıp regresyon karşılaştırması için:

```bash
python src/assistant_ops.py replay \
  --base-url http://127.0.0.1:8085 \
  --api-key "$ASSISTANT_API_KEY" \
  --prompt-set docs/assistant_prompt_set.json \
  --tag <deney-etiketi> \
  --timeout 90
```

Rapor `output/assistant_eval_<tag>.json` altına yazılır.

## 11) Sorun giderme

- **Auth sorunu:**

  ```bash
  curl -i http://127.0.0.1:8085/v1/models
  curl -i -H "Authorization: Bearer $ASSISTANT_API_KEY" http://127.0.0.1:8085/v1/models
  ```

  İlki `401`, ikincisi `200` dönmeli. İkincisi de `401`/`403` dönüyorsa `ASSISTANT_API_KEY`
  servis ortamında `.env`'deki değerle eşleşmiyordur.

- **`GEMINI_API_KEY` eksik/geçersiz — gerçek belirti (ölçüldü):** `/v1/chat/completions`
  **çökmez**, `200 OK` döner; içerik jenerik bir yedek metindir ("Şu anda bu soruya cevap
  üretemedim. Soruyu biraz daha belirgin (ders/konu/tarih) biçimde tekrar gönderir misin?")
  ve `safety_flags` içinde `warning:limited_confidence` bulunur, `meta.model` `"gemini"`
  (gerçek bir model adı değil) olarak kalır. Sebep: `GeminiClient.chat_with_tools`
  `RuntimeError("gemini_no_api_key")` fırlatır, `AssistantRuntime.chat` bunu geniş bir
  `except Exception` ile yakalayıp yedek cevaba düşer (`assistant_core.py`, `chat()` —
  `except Exception as exc:` bloğu). Bu belirtiyi "sorun yok" sanma — "cevap üretemedim"
  jenerik metni + `warning:limited_confidence` bayrağı görüyorsan `GEMINI_API_KEY`'i
  kontrol et.

  `assistant_unavailable` (`503`) **ayrı ve çok daha nadir bir durumdur**: yalnız
  `AssistantRuntime`'ın kendisi kurulamazsa (ör. import hatası) oluşur — eksik
  `GEMINI_API_KEY` runtime kurulumunu bozmaz, yalnızca `GeminiClient.available`'ı
  `False` yapar.

- **Müfredat/OER araçları yok:** §2'deki dağıtım tuzağı — `.env`'de MCP anahtarlarını
  kontrol et (HTTP tabanlı doğrulamayı kullan, kabuktan çalıştırılan çıplak `build_registry`
  kontrolünü değil).

- **İndeks bozulması / bayat indeks:**

  ```bash
  python src/reindex_assistant.py --full
  python src/assistant_ops.py verify-index
  ```

- **Servis logları:**

  ```bash
  journalctl --user -u ted-dashboard -f
  ```

## 12) OpenAI-uyumlu istek/yanıt örneği

Request:

```json
{
  "model": "bu-alan-göz-ardı-edilir",
  "messages": [
    {"role": "user", "content": "Bu hafta ödev önceliğim ne?"}
  ],
  "temperature": 0.2,
  "session_id": "cureohub-session-1",
  "context_filters": {},
  "plan": false
}
```

**`model` alanı sunucu tarafında hiç okunmaz** (§4) — `openai_chat_completion` içinde
`request_data.get("model")` çağrısı yoktur. Ölçüldü: `"model": "totally-bogus-model-xyz"`
gönderildiğinde yanıt `gemini-3.7-flash` ile geldi; istekteki değerle hiçbir ilişkisi yok.
Yanıttaki `model`/`meta.model` isteğin *kopyası* değil, `GeminiClient`'ın o çağrı için
**gerçekten seçtiği** modeldir (§4'teki sabit `FAST_MODELS`/`DEEP_MODELS` zincirinden).

Response (özet — `meta.model` gerçek seçim, yukarıdaki istekteki `model` değeriyle
karıştırılmamalı):

```json
{
  "object": "chat.completion",
  "choices": [{"message": {"role": "assistant", "content": "..."}}],
  "citations": [{"id": "S1", "path": "..."}],
  "safety_flags": [],
  "plan_blocks": [],
  "meta": {"model": "gemini-3.7-flash", "latency_ms": 1234}
}
```
