# TEDY Assistant Go-Live Runbook

Bu doküman, dashboard'un gömülü asistanını (`/v1/chat/completions`, `/v1/models`) güvenle
canlıya almak ve doğrulamak için izlenecek tek yazılı yolu tarif eder. Sohbet yolu Gemini
API üzerinden çalışır; yerel bir LLM sunucusuna ihtiyaç duymaz.

## 0) Önkoşullar

Servis ortamında (`.env` veya systemd `Environment=`) şu değişkenler tanımlı olmalı:

| Değişken | Amaç |
|---|---|
| `GEMINI_API_KEY` | Sohbet modeli (Gemini). Yoksa `/v1/chat/completions` `assistant_unavailable` döner. |
| `MUFREDAT_MCP_API_KEY` | `maarif-mufredat` MCP sunucusu (müfredat/kazanım/ders kitabı araçları). |
| `EGITIM_KAYNAK_MCP_API_KEY` | `egitim-kaynak` MCP sunucusu (OER arama araçları). |
| `DASHBOARD_SECRET_KEY` | Flask session imzası; eksikse API import'ta patlar (bkz. `dashboard_api.py`). |
| `ASSISTANT_API_KEY` | `/v1/models` ve `/v1/chat/completions` için Bearer auth. |

Not: Ollama'ya ihtiyaç **yoktur**. Sohbet yolu (`GeminiClient`) yalnızca Gemini bulut
modellerini çağırır; gömme (embedding) tabanlı vektör arama da şu an devre dışıdır (bkz.
§4) — yani bu iki anahtar dışında yerel bir model sunucusu ayağa kaldırmaya gerek yok.

## 1) ⛔ DAĞITIM TUZAĞI — bu adım atlanırsa özellik sessizce ölür

Servis (`~/.config/systemd/user/ted-dashboard.service`) ortamını `EnvironmentFile=.env`'den
alıyor. `MUFREDAT_MCP_API_KEY` ve `EGITIM_KAYNAK_MCP_API_KEY` geliştirme makinesinde
**interaktif kabuk ortamında** duruyor olabilir ama **`.env` içinde değilse** gunicorn onları
hiç göremez: kayıt defteri sıfır müfredat aracıyla açılır, asistan yalnız yerel okul
verisinden (`ogrenci_verisi_ara`) cevap verir ve arayüzü test eden kişiye **sağlıklı
görünür** — çünkü kendi kabuğundan miras aldığı anahtarlarla test etmiştir, üretim onları
görmez. `degraded()` bu durumu bildirir ve arayüzde rozet yanar, ama **rozet arızayı
görünür kılar — gidermez.**

Dağıtımdan önce iki anahtarı `.env`'e ekle (dosya zaten mod 600 ve gitignore'lu), servisi
yeniden başlat ve doğrula:

```bash
systemctl --user restart ted-dashboard
python -c "
from src.assistant_tools import build_registry
reg = build_registry(lambda q, k: [])
print('araçlar:', len(reg.declarations()), '| degraded:', reg.degraded())
"
```

Beklenen: `araçlar: 10 | degraded: []`. `degraded` boş değilse veya araç sayısı 1 (yalnız
`ogrenci_verisi_ara`) ise anahtarlar servise ulaşmıyordur — `.env`'i kontrol et.

## 2) MCP sağlık kontrolü

```bash
python -c "
from src.assistant_tools import build_registry
reg = build_registry(lambda q, k: [])
print('araçlar:', [d['name'] for d in reg.declarations()])
print('degraded:', reg.degraded())
"
```

Beklenen: 10 araç adı (`ogrenci_verisi_ara` + 9 MCP aracı), boş `degraded`.

## 3) Model zinciri kontrolü

```bash
python -c "from src.assistant_core import GeminiClient; print(GeminiClient.FAST_MODELS, GeminiClient.DEEP_MODELS)"
```

`FAST_MODELS` genel sohbet için kullanılan zincir, `DEEP_MODELS` plan modu ve zor sorular
için önce denenen model. Bir model kota/404 hatası verirse `GeminiClient` otomatik olarak
zincirdeki bir sonrakine geçer; `gemini-2.0-*` aileleri API'nin artık 404 döndürmesi
nedeniyle zincirden çıkarıldı (bkz. `assistant_core.py` içindeki yorum). İstek gövdesindeki
`model` alanı **kozmetiktir** — `/v1/chat/completions` onu okumaz, her zaman bu sabit
zincirden seçer; `/v1/models` de yalnız `FAST_MODELS`'i listeler.

## 4) Bilgi tabanı indeksi (reindex)

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

## 5) Servis: neden `gthread`

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

## 6) API smoke test

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

`--model` bayrağı isteğe eklenen etikettir, backend model seçimini etkilemez (§3).

## 7) CureoHub senaryo doğrulaması

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

## 8) Degradasyon beklentisi

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
adıyla degraded ilan eder. Ama **rozet arızayı görünür kılar, gidermez**: §1'deki kontrolü
her dağıtımdan sonra çalıştır.

## 9) Metrikler ve prompt replay

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

## 10) Sorun giderme

- **Auth sorunu:**

  ```bash
  curl -i http://127.0.0.1:8085/v1/models
  curl -i -H "Authorization: Bearer $ASSISTANT_API_KEY" http://127.0.0.1:8085/v1/models
  ```

  İlki `401`, ikincisi `200` dönmeli. İkincisi de `401`/`403` dönüyorsa `ASSISTANT_API_KEY`
  servis ortamında `.env`'deki değerle eşleşmiyordur.

- **Sohbet çalışmıyor / `assistant_unavailable`:** `GEMINI_API_KEY` servis ortamında eksik
  veya geçersizdir — §0.

- **Müfredat/OER araçları yok:** §1'deki dağıtım tuzağı — `.env`'de MCP anahtarlarını
  kontrol et.

- **İndeks bozulması / bayat indeks:**

  ```bash
  python src/reindex_assistant.py --full
  python src/assistant_ops.py verify-index
  ```

- **Servis logları:**

  ```bash
  journalctl --user -u ted-dashboard -f
  ```

## 11) OpenAI-uyumlu istek/yanıt örneği

Request:

```json
{
  "model": "gemini-flash-lite-latest",
  "messages": [
    {"role": "user", "content": "Bu hafta ödev önceliğim ne?"}
  ],
  "temperature": 0.2,
  "session_id": "cureohub-session-1",
  "context_filters": {},
  "plan": false
}
```

`model` alanı yalnız yanıtta yansıtılır (§3) — sunucu tarafında model seçimini etkilemez.

Response (özet):

```json
{
  "object": "chat.completion",
  "choices": [{"message": {"role": "assistant", "content": "..."}}],
  "citations": [{"id": "S1", "path": "..."}],
  "safety_flags": [],
  "plan_blocks": [],
  "meta": {"model": "gemini-flash-lite-latest", "latency_ms": 1234}
}
```
