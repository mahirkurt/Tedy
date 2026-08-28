# TEDY AI Sohbet Modülü — Müfredat Temellendirmesi ve Cevap Arayüzü

- **Tarih:** 2026-08-23
- **Durum:** Onaylandı, implementasyon planı bekliyor
- **Kapsam:** Faz 1. Modül stüdyosu (edupedia'nın 9 üretim modu) Faz 2'ye bırakıldı.

## 1. Problem

Dashboard'daki TEDY Asistan sayfası çalışıyor ama cevap kalitesi üç ayrı yerden
tavanlanıyor. Aşağıdakilerin hepsi bu depoda ölçüldü, tahmin değil.

### 1.1 Ölü model zinciri (canlı arıza)

`GeminiClient.MODELS` = `[gemini-2.5-flash, gemini-2.0-flash, gemini-2.0-flash-lite]`.
Anahtarla ölçüldü: son ikisi **404 NOT_FOUND — "no longer available"**. Kod
`RESOURCE_EXHAUSTED` gördüğünde modeli `_exhausted` kümesine atıp sıradakine
geçiyor; sıradakiler yok. Yani ilk model kotaya takıldığı anda asistan tamamen
düşüyor ve bu, üç basamaklı bir yedeklilik varmış gibi görünen kodun arkasında
gizleniyor.

### 1.2 Atıf zinciri kopuk

`_generate_answer()` sistem promptu modele `[S1]`, `[S2]` satır-içi atıf
yazdırıyor. Frontend'de `stripInlineCitations()` bu işaretleri **regex ile
siliyor**. Sonuç: metin ile sağdaki kaynak paneli arasında hiçbir bağ kurulamıyor;
model doğru atıf yapsa da kullanıcı göremiyor.

### 1.3 Kaynak kalitesi

Yerel korpus Işık'ın okul verisinin yanı sıra EBA'dan indirilmiş ders kitabı
PDF'lerinin ham OCR çıktısını da içeriyor. Üretimde görülen kaynak kartları
`"( ) mi ( ) mik ( ) ri. 7."` gibi parçalar ve hepsi tek tip `%80` güven rozeti
taşıyor. Sayfa/ünite/kazanım yapısı yok, bu yüzden ne modele iyi bağlam veriyor
ne de kullanıcıya doğrulanabilir referans.

### 1.4 Arayüz

- `AssistantChat.tsx` cevabı `<p>{msg.content}</p>` olarak basıyor. Prompt
  "madde işaretleri kullan" diyor; ekranda ham `- ` ve `**` çıkıyor. Depoda
  `utils/markdown.tsx` içinde çalışan bir `renderMarkdown()` var (Tedy Books için
  yazılmış), kullanılmıyor.
- `.ac` blokları 5142 satırlık `ted-theme.scss` monolitinde (~2606–2930).
- Carbon'un 21 AI token'ından **hiçbiri kullanılmıyor** (`--cds-ai-*` sayımı: 0);
  yerine `#edf5ff` / `#0f62fe` sabit hex'leri var.
- Akış yok, mesaj eylemi yok, takip önerisi yok. `max_output_tokens=1200`.

### 1.5 Doküman kayması

`docs/assistant-go-live.md` hâlâ Ollama dönemini anlatıyor
(`ASSISTANT_CHAT_MODEL=qwen2.5-coder:7b`, `ollama pull …`). Kod Gemini'ye
geçtiğinde güncellenmemiş. `.env` de aynı ölü değişkenleri taşıyor.

## 2. Hedefler / hedef olmayanlar

**Hedefler**

1. Konu bilgisinde otoriteyi ham EBA OCR'ından MEB müfredat korpusuna taşımak.
2. Modeli araç çağıran bir döngüye almak; hangi kaynağa bakacağına o karar versin.
3. Atıf zincirini uçtan uca çalışır kılmak (üret → doğrula → tıklanabilir göster).
4. Cevap yüzeyini Carbon'un AI token sistemiyle yeniden kurmak.
5. Model zincirini gerçekten erişilebilir modellerle onarmak.

**Hedef olmayanlar (Faz 2)**

Modül üretimi (MODULE·QUIZ·FLASHCARDS·GAME·EXPLAINER·ASSESSMENT·SERIES·
CURRICULUM·EXAM), 16 kalite kapısı, run-manifest, üretilen HTML'in saklanıp
servis edilmesi. Faz 1'in araç döngüsü ve müfredat temellendirmesi bunların
altyapısıdır; boşa iş yapılmıyor.

**Karar:** Model sağlayıcısı Gemini olarak kalır (kullanıcı kararı — sıfır ek
maliyet). Claude/OpenAI anahtarları ortamda mevcut ama kullanılmayacak.

## 3. Doğrulanmış ön koşullar

Bunlar spec yazılmadan önce canlı ölçüldü.

| Ön koşul | Durum |
|---|---|
| `maarif-mufredat` MCP | `mufredat-mcp v0.3.0`, Bearer ile **200**, 21 araç |
| `egitim-kaynak` MCP | `Eğitim Kaynakları v1.28.1`, Bearer ile **200**, 6 araç |
| `MUFREDAT_MCP_API_KEY` | Sunucu ortamında mevcut (64 karakter) |
| `EGITIM_KAYNAK_MCP_API_KEY` | Sunucu ortamında mevcut (43 karakter) |
| 6. sınıf kapsamı | `list_textbooks(grade:"6")` → Fen Bilimleri 6, 186 sayfa, metin çekilebilir |
| Gemini function calling | `gemini-3.7-flash` ve `gemini-2.5-flash` üzerinde **ölçüldü** |
| Erişilebilir modeller | 3.7/3.6/3.5-flash, `gemini-pro-latest`, `flash-lite-latest`; **2.0-* yok** |
| `--cds-*` köprüsü | `ted-theme.scss` çalışma ağacındaki düzeltmeyle `:root`'ta çözülüyor |

**Kapandı (2026-08-23 ölçümü):** `gemini-3.5-flash`, `gemini-flash-lite-latest`,
`gemini-3.6-flash` ve `gemini-pro-latest` üzerinde function calling ayrıca test
edildi — dördü de doğru araç çağrısı üretti. Yedek zincirinden model çıkarmaya
gerek yok.

**`--cds-*` köprüsü notu:** Carbon `--cds-*` özel özelliklerini yalnız ürettiği
tema kapsamlarında yayar. `--ted-*` takma adları `:root`'ta tanımlıydı, yani
token'ların ÜSTÜNDE — bu yüzden `var(--cds-text-helper, #8d8d8d)` token'ı hiç
görmüyor, fallback'te donuyordu. Çalışma ağacındaki (bu spec'in dışında yapılmış)
düzeltme `:root`'a `theme.theme(themes.$g10)` gömerek bunu onarıyor. **§7'deki AI
token planı bu düzeltmeye bağımlıdır**; o commit edilmeden AI token'ları da
`:root`'ta çözülmez.

## 4. Mimari

```
Soru
 └─ AssistantRuntime.chat()
     ├─ Gemini function-calling döngüsü (≤4 tur, süre bütçeli)
     │   ├─ ogrenci_verisi_ara            → yerel HybridRetriever
     │   ├─ kazanim_ara | kazanim_listele → maarif-mufredat MCP
     │   ├─ mufredat_ara                  → maarif-mufredat MCP
     │   ├─ kitap_listele | kitap_sayfa   → maarif-mufredat MCP
     │   ├─ figur_ara | figur_getir       → maarif-mufredat MCP
     │   └─ oer_ara | oer_kazanima_gore   → egitim-kaynak MCP
     └─ Atıf doğrulayıcı → yanıt + kanıtlanmış kaynaklar
```

**Otorite ayrımı (değişmez kural):** Işık'ın kendi verisi (ödev, sınav, not,
program, duyuru) için tek doğru kaynak yerel korpustur. Konu/müfredat/kazanım
bilgisi için tek doğru kaynak MEB MCP'sidir. Model ikisini karıştıramaz; her
atıf hangi sınıftan geldiğini taşır. Bugünkü "her soruya EBA OCR'ı yapıştır"
davranışı böylece ortadan kalkar.

## 5. Yeni bileşenler

### 5.1 `src/mcp_client.py`

**Ne yapar:** Streamable-HTTP MCP sunucularına konuşan asgari, bağımlılıksız
istemci.

**Neden yeni bağımlılık yok:** Resmî `mcp` Python SDK'sı async-öncelikli; Flask
sync worker'larıyla çakışır. Protokolün ihtiyacımız olan yüzeyi dar —
`initialize` → `notifications/initialized` → `tools/list` → `tools/call` — ve
`requests` + satır bazlı SSE ayrıştırmayla karşılanır.

**Arayüz:**

```python
class McpClient:
    def __init__(self, name: str, url: str, api_key: str,
                 timeout: float = 25.0) -> None: ...
    def list_tools(self) -> list[dict]: ...          # önbellekli
    def call_tool(self, name: str, arguments: dict) -> McpToolResult: ...
    @property
    def healthy(self) -> bool: ...

@dataclass
class McpToolResult:
    ok: bool
    text: str                # birleştirilmiş text içerik blokları
    images: list[dict]       # ImageContent blokları (figur_getir)
    error: str | None
```

**Bağımlılıkları:** `requests`, stdlib. Başka yok.

**Davranış kuralları:**
- Oturum kimliği (`mcp-session-id`) worker başına önbelleklenir, TTL 10 dk.
- Sunucu oturumu düşürürse (404 / `session` hatası) bir kez yeniden `initialize`
  edip çağrıyı tekrarlar; ikinci kez düşerse `ok=False` döner.
- Yanıt hem düz JSON hem `text/event-stream` gelebilir (ölçüldü: mufredat düz
  JSON, egitim-kaynak SSE) — ikisi de ayrıştırılır.
- `list_tools()` süreç ömrü boyunca önbelleklenir; şema her istekte çekilmez.

### 5.2 `src/assistant_tools.py`

**Ne yapar:** MCP araç şemalarını Gemini fonksiyon tanımlarına çevirir ve yerel
araçları aynı sözleşmeye sokar.

**Neden şemayı okumak, elle yazmak değil:** Ölçüldü — `search_learning_outcomes`
parametresi `query` değil `q`, ve `grade` tamsayı değil **string**. Bunlar sert
hatalardır: yanlış ad ile çağrı reddedilir.

**Düzeltme (2026-08-24 ölçümü).** Bu spec ilk yazıldığında `grade`'in kanonik
biçiminin `"5.Sınıf"` olduğu ve bunun yalnız `description` alanında yazdığı
iddia edilmişti. Canlı doğrulama bunu zayıflattı: o örnek yalnız
`list_learning_outcomes`'un açıklamasında var, `search_learning_outcomes`'ta yok,
ve sunucu `"6"` ile `"6.Sınıf"` için **bayt bayt aynı** sonucu döndürüyor — yani
biçim normalleştiriliyor ve sessiz boş-sonuç riski yok. Açıklamaları birebir
korumak yine doğru tasarımdır (kaynak şema tek doğruluk kaynağıdır ve `q`/`query`
hatası gerçektir), ama `grade` örneği bu gerekçenin kanıtı değildi.

**Çevirici ince kalır (2026-08-23 ölçümü):** MCP şemaları Pydantic tarzı
`anyOf: [{type:string},{type:null}]` kullanıyor ve kurulu `google-genai` bunu
olduğu gibi **kabul ediyor** — ham `inputSchema` doğrudan `FunctionDeclaration`
parametresi olarak geçirilebiliyor. Bu yüzden katman bir yeniden yazıcı değil,
bir **sanitizer**'dır: `title` gürültüsünü atar, `description`'ı birebir korur,
ve SDK ileride katılaşırsa `anyOf` daraltmasını tek yerde yapar.

**Arayüz:**

```python
TOOL_ALLOWLIST: dict[str, str]   # gemini_adı -> "sunucu:mcp_araç_adı"

def build_declarations(registry: McpRegistry) -> list[FunctionDeclaration]: ...
def dispatch(name: str, args: dict, ctx: ToolContext) -> ToolOutcome: ...
```

**Beyaz liste (10 araç).** 27 aracın hepsi açılmaz; prompt'u şişirir ve döngüyü
yavaşlatır.

| Gemini adı | Arka uç |
|---|---|
| `ogrenci_verisi_ara` | yerel `HybridRetriever` |
| `kazanim_ara` | `maarif-mufredat:search_learning_outcomes` |
| `kazanim_listele` | `maarif-mufredat:list_learning_outcomes` |
| `mufredat_ara` | `maarif-mufredat:search` |
| `kitap_listele` | `maarif-mufredat:list_textbooks` |
| `kitap_sayfa` | `maarif-mufredat:get_document_text` |
| `figur_ara` | `maarif-mufredat:search_figures` |
| `figur_getir` | `maarif-mufredat:get_figure` |
| `oer_ara` | `egitim-kaynak:kb_search` |
| `oer_kazanima_gore` | `egitim-kaynak:kb_for_outcome` |

Gerisi ihtiyaç çıktıkça beyaz listeye eklenir; kod değişikliği tek satır.

### 5.3 `src/assistant_core.py` değişiklikleri

**`GeminiClient`**

```python
FAST_MODELS = ["gemini-3.7-flash", "gemini-3.5-flash",
               "gemini-2.5-flash", "gemini-flash-lite-latest"]
DEEP_MODELS = ["gemini-pro-latest"]          # tükenirse FAST'e düşer
```

- `chat_with_tools(convo, declarations, dispatch, max_rounds=4)` eklenir.
- `max_output_tokens`: sohbet 2048, plan 8192 (model tavanı 65536).
- 404 alınan model kalıcı olarak devre dışı bırakılır ve **loglanır** — bugün
  sessizce yutuluyor.

**`AssistantRuntime.chat()`**

Akış: niyet sınıflandır → katman seç → araç döngüsünü çalıştır → atıfları
doğrula → yanıtı kur.

**Katman seçimi deterministiktir, modele bırakılmaz:**

- `intent ∈ {study_plan, grade_analysis, exam_solving}` → **derin**
- Kullanıcı "daha derine in" eylemini tetikledi → **derin**
- Diğer her durum → **hızlı**

Böylece maliyet ve gecikme öngörülebilir kalır; aynı soru aynı katmanı seçer.

**`_validate_citations()` (yeni)**

Model `[S1]` işaretlerini yazar. Backend her işareti gerçek bir kaynağa çözer.
Çözülmeyen işaret **metinden düşürülür** ve `meta.dropped_citations` sayacına
yazılır. Sessiz yutma yok; frontend artık atıf silmez.

## 6. Veri sözleşmeleri

### 6.1 Kaynak (citation) şeması

```jsonc
{
  "id": "S1",
  "kind": "ogrenci" | "mufredat" | "kitap" | "oer",
  "label": "Fen Bilimleri 6 · s.42",   // kullanıcıya gösterilen
  "locator": {                          // kind'a göre değişir
    "outcome_code": "FB.6.2.1",         // mufredat
    "document_id": 213, "page": 42,     // kitap
    "path": "output/scraped_data.json", // ogrenci
    "doc_id": "...", "license": "..."   // oer
  },
  "snippet": "…",
  "confidence": 0.0-1.0
}
```

`kind` alanı zorunlu. Frontend kaynakları buna göre gruplar; bugünkü tek tip
`%80` rozeti kalkar.

### 6.2 Yanıt zarfı (mevcut alanlar korunur, eklenenler)

```jsonc
{
  "answer": "…",
  "citations": [ /* §6.1 */ ],
  "safety_flags": [ … ],
  "plan_blocks": [ … ],
  "intent": "qa" | "study_plan" | …,
  "meta": {
    "model": "gemini-3.7-flash",
    "tier": "fast" | "deep",
    "tool_calls": [ {"name": "...", "ms": 812, "ok": true} ],
    "dropped_citations": 0,
    "degraded": ["mufredat_unreachable"],   // boş dizi = tam yetenek
    "budget_exhausted": false,
    "latency_ms": 4210
  }
}
```

`/v1/chat/completions` OpenAI-uyumlu ucu bu alanları bugünkü gibi geçirmeye
devam eder; sözleşme genişliyor, kırılmıyor.

## 7. Arayüz

### 7.1 Dosya ayrımı

`.ac*` kuralları `ted-theme.scss`'ten çıkarılıp
`dashboard/src/components/AssistantChat.scss`'e taşınır ve bileşenden import
edilir. Üzerinde çalıştığımız kodun hedefli iyileştirmesi: 5142 satırlık monolit
bu iş için elverişsiz. Diğer bileşenlerin kuralları taşınmaz — kapsam dışı.

### 7.2 Carbon AI token eşlemesi

Otorite: kurulu `@carbon/themes@11.69.0` (21 AI token) ve
`@carbon/styles/scss/utilities/_ai-gradient.scss` mixin'leri. Figma kütüphaneleri
token **değerinin** kaynağı değildir (Carbon doktrini); ayrıca ölçüldü:
`pqtFy76S5yq9EwRru3bNXT` dosyasında `libraries_added_to_file: []`, yani
`search_design_system` bu kopyalarda boş dönüyor.

| Yüzey | Token / mixin |
|---|---|
| Asistan mesaj balonu | `@include ai-gradient('left', 40%)`; `ai-aura-start-sm` → `ai-aura-end`, kapanış `ai-border-strong` |
| AI paneli kenarlığı | `linear-gradient(ai-border-start → ai-border-end)` border-box |
| Composer | `inset` gölge `ai-inner-shadow`; odakta `ai-border-strong` |
| Panel yükseltisi | `ai-drop-shadow` |
| Atıf popover'ı | `@include ai-popover-gradient()`, `ai-popover-background`, `ai-popover-caret-bottom`, `ai-popover-shadow-outer-01/02` |
| Düşünme iskeleti | `ai-skeleton-background`, `ai-skeleton-element-background` |
| Kaynak kartı hover | `ai-aura-hover-start/-end/-background` |

Sabit `#edf5ff` / `#0f62fe` kalkar. Beklenen sonuç: `--cds-ai-*` kullanımı 0 → 16 (21 AI token'ın 16'sı; kalan 5'i
veri tablosu ve tam-tablo gradyanı için, bu sayfada karşılığı yok).

### 7.3 Davranış

- **Markdown render:** mevcut `renderMarkdown()` yeniden kullanılır. HTML
  enjeksiyonu yok (React düğümü üretir).
- **Atıf çipleri:** `[S1]` silinmez, tıklanabilir çipe dönüşür. Tıklama →
  kaynak kartı vurgulanır + Carbon AI popover'ında pasaj açılır.
  `stripInlineCitations()` **kaldırılır**.
- **Kaynak paneli:** `kind`'a göre gruplanır, gerçek etiketle
  ("MEB Kazanımı · FB.6.2.1", "Fen Bilimleri 6 · s.42", "Işık'ın ödevleri").
- **Mesaj eylemleri:** kopyala · yeniden üret · "daha derine in" (derin katman).
- **Araç ilerlemesi:** "Kazanım aranıyor…" → "Ders kitabı s.42 okunuyor…" →
  yanıt. Araç döngüsü beklemeyi uzatıyor; ne yapıldığını göstermek hem güven
  hem DEHB-dostu tasarım (görünür süre, yürütücü işlev dışsallaştırma) açısından
  gerekli.
- **Degradasyon rozeti:** `meta.degraded` boş değilse yanıtın üstünde nötr bir
  uyarı ("müfredat kaynağına ulaşılamadı — yalnız okul verisiyle yanıtlandı").

### 7.4 Akış (SSE) ve operasyon

İlerleme olayları SSE ile taşınır: `tool_start`, `tool_end`, `answer_delta`,
`done`. **Yalnız son tur token bazında akıtılır** — araç turları akıtılmaz,
çünkü ara turların çıktısı kullanıcıya değil modele gider. Ara turlar yalnız
`tool_start`/`tool_end` olayları üretir. Gunicorn şu an **2 sync worker**; bir akış bir worker'ı kilitler ve
ikinci bir istek dashboard'u durdurur. Servis dosyası
`~/.config/systemd/user/ted-dashboard.service` şu şekilde değişir:

```
--worker-class gthread --threads 4
```

`--timeout 360` korunur. Bu tek satır olmadan SSE üretimde güvenli değil.

## 8. Pedagojik katman

Sistem promptu edupedia'nın `references/adhd-pedagogy.md` ilkeleriyle yeniden
yazılır — bunlar Işık'ın profiline doğrudan uyuyor:

- **Parçalama:** cevaplar 3–6 dakikada tüketilebilir birimlere bölünür.
- **Yürütücü işlev dışsallaştırma:** açık hedef, sıralı adım, tahmini süre.
- **Anında geri bildirim / gecikme itimi:** ödül ve ilerleme gecikmesiz görünür.
- **Çoklu temsil:** uygun olduğunda `figur_ara`/`figur_getir` ile ders
  kitabının kendi şeması çağrılır.

Kaynak-sadakati kuralı edupedia'dan alınır: **kazanım kodu, kitap adı, sayfa
numarası asla uydurulmaz**; yalnız araç çıktısından gelir. Kaynak yetersizse
model eksikliği beyan eder, doldurmaz.

## 9. Hata ve degradasyon matrisi

| Arıza | Davranış |
|---|---|
| MCP ulaşılamıyor | Yalnız yerel korpusla yanıt; `meta.degraded += "mufredat_unreachable"`; kullanıcıya rozet |
| MCP şema reddi | Hata modele geri beslenir, **bir** düzeltme turu; yine olmazsa aracı bırakır ve beyan eder |
| Araç turu bütçesi doldu | Eldeki kanıtla yanıt; `meta.budget_exhausted = true` |
| Gemini modeli 404 | Kalıcı devre dışı + log; sıradaki modele geç |
| Gemini zinciri tükendi | Mevcut fail-safe metni; artık gerçekten erişilebilir modellerle |
| Atıf çözülemedi | İşaret metinden düşer; `meta.dropped_citations` artar |

Ortak kural: hiçbir arıza uydurmaya yol açmaz ve hiçbiri sessiz kalmaz.

## 10. Test

| Test | Kapsam |
|---|---|
| `tests/test_mcp_client.py` | Oturum kurulumu, SSE + düz JSON ayrıştırma, oturum düşünce yeniden başlatma, zaman aşımı. Sahte sunucu; ağ yok |
| `tests/test_assistant_tools.py` | `inputSchema` → `FunctionDeclaration` çevirisi. **Regresyon:** `q` (≠`query`) ve `grade: string` (≠int) vakası sabitlenir |
| `tests/test_assistant_citations.py` | Orphan `[S3]` düşüyor, gerçek atıf korunuyor, `dropped_citations` sayıyor |
| `tests/test_assistant_models.py` | 404 alan model kalıcı devre dışı; zincir sıradakine geçiyor |
| Playwright | Markdown render, atıf çipi tıklaması, kaynak gruplaması, degradasyon rozeti |

Canlı MCP'ye bağlı testler `@pytest.mark.live` ile işaretlenir ve varsayılanda
atlanır (CI'da anahtar yok).

## 11. Temizlik kalemleri

Bu işin doğrudan yolundaki ölü/yanıltıcı yapılandırma:

- `.env`: `ASSISTANT_CHAT_MODEL`, `ASSISTANT_CHAT_FALLBACK_MODEL`,
  `ASSISTANT_OLLAMA_*` — Gemini yolu bunları hiç okumuyor.
- `docs/assistant-go-live.md`: Ollama dönemini anlatıyor; Gemini + MCP gerçeğine
  göre güncellenir.
- `AssistantChat.tsx`: `stripInlineCitations()` kaldırılır (§7.3).

Bunların dışında refactor yapılmaz.

## 12. Faz 2 sınırı

Modül stüdyosu ayrı bir spec'e gider: 9 üretim modu, `validate_module.py`'nin 16
kalite kapısı, run-manifest sözleşmesi, üretilen tek-dosya HTML'in saklanması ve
servis edilmesi. Faz 1'in araç döngüsü, müfredat temellendirmesi ve atıf
sözleşmesi Faz 2'nin de altyapısıdır.
