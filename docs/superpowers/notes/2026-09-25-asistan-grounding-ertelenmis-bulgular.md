# Asistan müfredat temellendirmesi — ertelenmiş bulgular

Kaynak: `.superpowers/sdd/2026-08-23-assistant-mufredat-grounding/progress.md` (1117 satır). Plan
`docs/superpowers/plans/2026-08-23-assistant-mufredat-grounding.md`, spec
`docs/superpowers/specs/2026-08-23-ai-chat-mufredat-temellendirme-design.md`. Ledger git-dışı karalama alanıydı;
silinmeden önce kalıcı kayıt için buraya taşındı (2026-09-25).

Koşunun kapanışı: 12 görevin tamamı bitti. Controller'ın son doğrulaması: Python 569 geçti / 69 atlandı (ağsız),
Playwright 42 geçti, derleme ve lint çıkış 0, ağaç temiz. Plan kusurlarından 14'ü koşu sırasında onarıldı.

Hiçbir bulgu kritik ya da önemli değildir. Durum sütunu:
- **açık** — 2026-09-25'te `main` kodunda yoklandı, hâlâ duruyor.
- **kapandı** — yoklandı, artık kodda yok.
- **belirsiz** — ilgili kod hâlâ var, ama bulgunun hâlâ geçerli olduğu doğrulanmadı.
- **yoklanmadı** — yalnız ledger kaydı; güncel kodda doğrulanmadı.

## Davranış ve sağlamlık

| # | Bulgu | Yer | Durum |
|---|---|---|---|
| 1 | `MODELS = FAST_MODELS` kopya değil canlı takma ad | `src/assistant_core.py` | kapandı |
| 2 | `empty_gemini_response` dalı log'lamaz; son `RuntimeError` dizgeyi yine taşır | `src/assistant_core.py` | yoklanmadı |
| 3 | İki denemeli döngüden sonra erişilemez `return {}` (gelecek düzenlemeler için tuzak) | `src/mcp_client.py` (şu an satır 350) | belirsiz |
| 4 | `_initialize()` oturum kimliğinin alındığını doğrulamaz; başlık eksikse sonraki RPC kimliksiz gider (sunucu reddeder, hata görünür kalır) | `src/mcp_client.py` | yoklanmadı |
| 5 | Taşıma yolunda HTTP durum kodu denetimi yok | `src/mcp_client.py` | yoklanmadı |
| 6 | `_KIND_BY_TOOL` bilinmeyen araç için sessizce `"mufredat"`a düşer (fail-closed değil); yerel/müfredat sınırı risk altında değil | `src/assistant_tools.py` | yoklanmadı |
| 7 | `sanitize_schema` iç içe nesne/dizi şemalarını düzleştirir (`properties`/`items` düşer), `required`'ı süzmez; bugünkü araçların hepsi düz | `src/assistant_tools.py` | yoklanmadı |
| 8 | `chat_with_tools` sonundaki `return out`, `max_rounds >= 1` için erişilemez | `src/assistant_core.py` | yoklanmadı |
| 9 | `max_rounds <= 0` koruması, model araç önerilmediği hâlde çağrı dönerse `budget_exhausted` ayarlamaz (pratikte erişilemez) | `src/assistant_core.py` | yoklanmadı |
| 10 | `registry.degraded()` `chat()`'in try/except'i dışında çağrılır; hata verirse degrade yerine 500 döner | `src/assistant_core.py` | yoklanmadı |
| 11 | `_generate_plan_summary` / `_deterministic_plan_summary` ölü kod, canlı router çağrısı taşıyor | `src/assistant_core.py` | kapandı |
| 12 | `.cds--skeleton` gerçek Carbon işaretlemesiyle hiç eşleşmez (`.cds--skeleton__text` olmalı) | pano SCSS | kapandı |
| 13 | `CitationChip` düğmeyi popover'a bağlayan `aria-describedby` / `aria-expanded` taşımaz; alıntı parçası ekran okuyucuya ulaşmaz | pano | yoklanmadı |
| 14 | Sınıflandırılmamış kaynak grubu bilinen gruplarla aynı görsel stilde; yalnız başlık metniyle ayrışır | pano | yoklanmadı |
| 15 | `degraded` listesindeki yinelenen sunucu adları tekilleştirilmez (React key çakışması) | pano | yoklanmadı |
| 16 | Akış ortasında kopan istemci arka plandaki `chat()`'i iptal etmez; kimsenin okumayacağı yanıt için Gemini token'ı harcanır | `chat_events()` | yoklanmadı |
| 17 | `chat_events()` çağrısı başına iş parçacığı ilkede sınırsız (üretimde gthread işçi başına 4 ile sınırlar) | `chat_events()` | yoklanmadı |
| 18 | `GeminiClient._get_client()` TOCTOU: eşzamanlı çağrılar ayrı istemci kurar (GIL yarım nesneyi önler; bedel gereksiz kurulum) — takip maddesi | `GeminiClient` | yoklanmadı |

## Test ve kod temizliği

| # | Bulgu | Yer | Durum |
|---|---|---|---|
| 19 | Kullanılmayan `McpToolResult` importu (ve `pytest`) | `tests/test_mcp_client.py` | açık |
| 20 | Kullanılmayan `import json` | `src/assistant_tools.py` | açık |
