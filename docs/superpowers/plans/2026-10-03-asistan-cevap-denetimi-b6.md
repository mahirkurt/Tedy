# Asistan cevap denetimi — B6 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Öğretmen modundaki her cevap ve genel moddaki uzun cevap, okura gitmeden önce tek bir ucuz denetim çağrısından geçer. Denetim kaynakla çelişkiyi, 7. sınıf seviyesini, anlatan öğretmen kuralını ve hitabı arar. Ciddi bir sorun varsa cevap bir kez, bütün olarak değiştirilir. Çağrı atlanırsa ya da hata verirse taslak durur ve `meta.denetim` bunu söyler. Dört dersin altın soru seti `scripts/asistan_eval.py` ile yalnız elle ve `--onayla` ile koşar; sonuç `output/asistan_eval/` altına yazılır. Test o betiği çalıştırmaz.

**Architecture:** Karar, ayrıştırma ve puan `src/assistant_denetim.py` içindedir. Flask'a import etmez. `AssistantRuntime.chat` atıfı çözdükten sonra, güvenlik son ekinden önce bu kapıyı çağırır. `answer_delta` taslağı akıtır; denetim o deltaları değiştirmez. Sonuç `answer` olayının `payload.answer` alanına yazılır. Sayfa bu alanı zaten okur: `setWriting('')` ve `appendAssistantMessage(data.payload)`. Yeni uç, yeni okur cümlesi ve yeni pano dosyası yoktur. `meta.model` cevap modelidir. `meta.degraded` denetim bayrağı taşımaz. `mesaj_ekle` `meta_json` `'{}'` kalır. B3'ün `_sorguya` fonksiyonuna ikinci bir model eklenmez; değerlendirme seti yalnız daralmayı kaydeder.

**Tech Stack:** Python 3.12, mevcut `ClaudeClient` (Anthropic Messages), `claude-haiku-4-5`, `atomic_json_dump`, `turkce_kucult_katla`. Yeni paket yok.

**Spec:** `docs/superpowers/specs/2026-09-28-asistan-ogretmen-modlari-design.md` — ekteki **B6 (yeni) — cevap denetimi ve değerlendirme seti**. **B6'e eklenenler** diye bir ek yoktur. B3 ekteki sorgu cümlesi ("gerekirse B6'da ölçülerek genişletilir") bu plana ölçüm olarak girer, yeni model çağrısı olarak girmez. B2, B3, B4 ve B5 plan dosyaları değişmez.

Plan dosyaları `26ae406` üzerindedir. Ürün kodu B2, B3, B4 ve B5 uygulanmadan B6 uygulanmaz. Görevler onların adlandırdığı yüzeyi tüketir: `chat`, `chat_events`, `_finalize_citations`, `guidance_suffix`, `_model_hata_cevabi`, `_fallback_answer`, `ClaudeClient.available`, `last_model_used`, `mesaj_ekle`, `_sorguya`.

## Global Constraints

- **Worktree:** `/mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-b2-plan`, dal `cursor/asistan-b2-plan-a843`. Ana checkout'a, `feat/asistan-ogretmen` worktree'sine, `feat/asistan-zengin`'e ve portal dallarına dokunma. `docs/superpowers/plans/2026-10-03-asistan-dosya-yukleme-b2.md`, `docs/superpowers/plans/2026-10-03-asistan-sohbet-gecmisi-b3.md`, `docs/superpowers/plans/2026-10-03-asistan-degerlendirme-sinav-hazirligi-b4.md` ve `docs/superpowers/plans/2026-10-03-asistan-ses-b5.md` değişmez.
- **Git:** dosyaları adıyla stage et. `git add -A` / `git add .` yok. Push yok.
- **Testler ücretli bir API'ye ya da ağa hiç gitmez.** `tests/conftest.py` `ANTHROPIC_API_KEY`'i siler. Hiçbir test `scripts/asistan_eval.py` dosyasına `--onayla` geçirmez. Hiçbir test `messages.create` çağırmaz.
- **Python:** yorumlayıcı `/mnt/thunderbolt/workspaces/TED/.venv/bin/python`. `DASHBOARD_SECRET_KEY=yalniz-test`. Gerçek `.env` bağlama. Yeni bağımlılık yok.
- **Dil:** okura giden her yeni cümle Türkçe. Bu plan yeni okur cümlesi yazmaz. Yol, istisna adı ve e-posta okura ve `meta.denetim` alanına gitmez. İstisna tipi yalnız loga yazılır.
- **Temel sistem bloğu her modda bayt bayt aynı kalır.** Denetim istemi ikinci bir sistem bloğu değildir ve `cache_control` taşımaz. `ClaudeClient.DEFAULT_MODEL` (`claude-sonnet-5`) değişmez.
- **Dağıtım bir plan görevi değildir.**
- **`/v1` ve `/plan` ayrı kapı değildir.** İkisi de `chat` üzerinden geçer. Öğretmen geçmezler; yalnız uzun cevap kapısı onları denetler.

## Kilitlenen seçimler

Spec bu davranışları ister, sayı ya da zarf vermez. Görevler aşağıdaki değeri kullanır.

| Seçim | Değer |
|---|---|
| Ne zaman | `ogretmen != "genel"` ise her cevap. `ogretmen == "genel"` ise yalnız `len(cevap) >= 800`. Uzunluk, ilk `_finalize_citations` sonrası, güvenlik son ekinden önceki karakter sayısıdır. Boşluk ve satır sonu sayılır. 799 denetlemez. İkisi de değilse çağrı yoktur. |
| Hata cümlesi | Metin `_model_hata_cevabi()` ya da `_fallback_answer(soru)` ile birebir aynıysa öğretmen modunda da çağrı yoktur. |
| Model yok | `denetle` verilmemiş ve `llm.available` False ise çağrı yoktur. `chat_with_tools` yaması `available` değerini değiştirmez; bugünkü testler Haiku'ya düşmez. |
| Tek çağrı | Model `claude-haiku-4-5`. Araç yok, thinking yok, temperature yok, stream yok, `cache_control` yok. `max_tokens` 2000. `timeout` 30 saniye. Dönüş hem kararı hem, ciddiyse, bütün yeni cevabı taşır. İkinci çağrı yoktur. |
| `_request` yok | Denetim `ClaudeClient._request` kullanmaz. O yol `last_model_used` yazar, `thinking` açar ve `MAX_TOKENS` 16000 kullanır. `meta.model` cevap modeli kalır. |
| Dört bakış | `kaynak`, `seviye`, `ogretmen`, `hitap`. Başka ad silinir. |
| Kaynak | Okurun gördüğü `[Sn]` cümlesi, aynı numaralı snippet ile çelişiyorsa ya da snippet'te olmayan kazanım kodu veya sayfa numarası varsa ciddi. İşaretsiz genel bilgi ciddi değildir. |
| Seviye | Her zaman `7. sınıf`. `_sinif()` okunmaz; kazıma `ortaokul` döndürebilir. Üniversite terimi ya da adımı atlayan çözüm ciddi. Kelime listesi yok. |
| Öğretmen | Önce `## Sınırlar` bölümünün tamamı, sonra `## Ders akışı` bölümünün en çok 1500 karakteri. İkisini birleştirip 1500'de kesmek yasaktır: Türkçe'nin `## Ders akışı` bölümü tek başına 1684 karakterdir ve bu kesim dört skill'de de `cevap anahtarı`ndan önce biter. Yalnız ipucu verip çözümü saklamak, ya da ödevi teslim metni veya cevap anahtarı diye yazmak ciddi. Benzer alıştırma cümlesinin yokluğu tek başına ciddi değildir. `ogretmen == "genel"` ise bu bakış yoktur; model `ogretmen` yazsa da o ad düşer. Liste boş kalırsa biçim hatasıdır. |
| Hitap | `okur == "ogrenci"` ise sen; Işık üçüncü şahıs ise ciddi. `aile` ve `bilinmiyor` ise siz; Işık üçüncü şahıs. Bir cevapta ikisi birden ciddi. |
| Ciddi değil | `{"ciddi": false}`. Cevap değişmez. `durum` `gecti`. |
| Ciddi | `{"ciddi": true, "sorun": ["kaynak"], "cevap": "<bütün metin>"}`. `cevap` taslağın yerine geçer. Taslağın sonuna eklenmez. `durum` `duzeltildi`. |
| Boş veya aynı | `ciddi` true ve `cevap` strip sonrası boşsa `durum` `hata`, `neden` `bos`. Strip sonrası taslakla aynıysa `durum` `hata`, `neden` `ayni`. İkisinde de taslak durur. İkinci çağrı yoktur. |
| Biçim | JSON değilse, `ciddi` true iken `sorun` boşsa ya da `cevap` dizgi değilse `durum` `hata`, `neden` `bicim`. Üç ters tırnaklı çit varsa ilk çitin içi okunur. |
| Çağrı hatası | İstisna yutulur. `durum` `hata`, `neden` `cagri`. Taslak durur. Loga yalnız `type(exc).__name__` yazılır. |
| Atıf | Düzeltme, ilk çözmenin bıraktığı atıf listesiyle yeniden `_finalize_citations` olur. Numara, okurun gördüğü `[S1]` sırasıdır. Havuzda olmayan işaret düşer. `meta.dropped_citations` iki geçişin toplamıdır. |
| Güvenlik | `guidance_suffix` denetimden sonra eklenir. Klinik son ek `Not: Klinik tanı/tedavi önerisi veremem. Bu konuyu okul psikolojik danışmanı veya lisanslı uzmanla değerlendirin.` cümlelerinin ikisidir. Birinci cümlede duran bir test canlı son eki kısaltır. Denetim bu son eki görmez ve silemez. `warning:limited_confidence` okura giden son atıf listesine göre konur. |
| Akış | `answer_delta` taslaktır. Denetim yeni delta ve `answer_reset` yazmaz. `answer` olayının gövdesi `{"payload": <chat dönüşü>}` olur. Sayfa `data.payload` okur. `/chat` aynı nesneyi sarmasız döner. |
| Meta | `meta.denetim` her cevapta vardır. Sayfa bunu okumaz. `degraded` listesine yazılmaz. `mesaj.meta_json` `'{}'` kalır. Kullanım, cevap kullanımına eklenmez. |
| Sorgu | `_sorguya` değişmez. Ek model yoktur. Düşen token, noktanın tokeniyle bütün olarak aynıysa `sorgu_dar` true olur. Alt dizgi sayılmaz: düşen `mi`, `kimyasal` içinde `sorgu_dar` yapmaz. |
| Altın set | Dört ders, derste 3 soru, toplam 12. Her soruda bir `arac`, bir `kaynak`, en az bir `nokta`. Nokta katlandıktan sonra en az 4 karakterdir ve B3'ün düşürdüğü kelimelerden biri değildir. |
| Onay | Argümanda `--onayla` yoksa çıkış kodu 2, dosya yok, istemci yok. Test bu argümanı geçirmez. |
| Kayıt | `output/asistan_eval/<YYYYMMDDTHHMMSSZ>/sonuc.json`. Dizin varsa `-2`, `-3`. `atomic_json_dump`. Önceki koşu silinmez. Bir sorunun hatası diğerini durdurmaz. |

`meta.denetim` biçimi:

```json
{"durum": "atlandi", "neden": "genel_kisa", "sorun": [], "model": null}
```

`durum`: `atlandi` | `gecti` | `duzeltildi` | `hata`. `neden`: `genel_kisa` | `hata_cevabi` | `model_yok` | `cagri` | `bicim` | `bos` | `ayni` | `denetim_dili` | `atif_kaybi` | null. `gecti` ve `duzeltildi` için `neden` null. Çağrı olduysa `model` `claude-haiku-4-5`.

Denetim istemi, bayt bayt (2026-10-05 düzeltmesiyle: snippet kısaltılmış baştır, görünmemesi tek başına ciddi değildir; `cevap` okura gösterilecek tam cevaptır, denetim notu yazılmaz. Canlıda Haiku düzeltme yerine eleştirisini yazdı ve o not Fen cevabının yerine geçti. Ayrıca `denetim_uygula` denetçi dili taşıyan ya da — `ogretmen` dışında — taslağın bütün atıflarını düşüren metni reddeder: `denetim_dili`, `atif_kaybi`):

```text
Sen bir denetçisin. Okura yazma; yalnız bir JSON nesnesi yaz.
kaynak: snippet kaynağın yalnız kısaltılmış başıdır; bir bilginin snippet'te görünmemesi tek başına ciddi değildir. [Sn] cümlesi aynı numaralı snippet ile açıkça çelişiyorsa ya da cümledeki kazanım kodu veya sayfa numarası o kaynağın label'ında ve snippet'inde hiç yoksa ciddi. İşaretsiz genel bilgi ciddi değildir.
seviye: anlatım 7. sınıf içindir. Üniversite terimi ya da adımı atlayan çözüm ciddi.
ogretmen: kurallar null ise bu bakış yoktur, sorun listesine ogretmen yazma. Varsa yalnız ipucu verip çözümü saklamak ya da ödevi teslim metni veya cevap anahtarı diye yazmak ciddi. Benzer alıştırma cümlesinin yokluğu tek başına ciddi değildir.
hitap: okur ogrenci ise sen; Işık üçüncü şahıs ise ciddi. okur aile ya da bilinmiyor ise siz ve Işık üçüncü şahıs. İkisi birden ciddi.
Ciddi değilse {"ciddi": false}. Ciddi ise {"ciddi": true, "sorun": ["kaynak"], "cevap": "bütün cevap"}. cevap okura gösterilecek düzeltilmiş tam cevaptır: taslağın [S] işaretlerini korur, taslağın yerine geçer, sonuna eklenmez. cevap'a denetim notu, eleştiri ya da snippet sözü yazma. Yeni [S] numarası uydurma. Snippet'te olmayan olgu ekleme.
```

Kullanıcı gövdesi şu anahtarlarla JSON'dur: `cevap`, `okur`, `ogretmen`, `sinif` (`"7. sınıf"`), `kaynaklar` (`id`, `label`, `snippet`; en çok 8; snippet zaten 400 karakterdedir), `kurallar` (dizgi ya da null).

## Kilitlenen adlar

| Ad | Değer | Neden |
|---|---|---|
| Modül | `src/assistant_denetim.py` | Saf karar. Flask yok. |
| `denetim_gerekli` | `(ogretmen, cevap, hata_metinleri) -> str \| None` | None ise çağrı var. Aksi `genel_kisa` ya da `hata_cevabi`. |
| `ogretmen_kurallari` | `(govde: str) -> str` | `## Sınırlar` bütün, sonra `## Ders akışı` en çok 1500. |
| `denetim_oku` | `(ham: str) -> dict` | Biçim hatasında `ValueError`. |
| `denetim_uygula` | `(cevap, karar) -> tuple[str, dict]` | Tek geçiş. |
| `puanla` | `(soru, cevap, cagrilar, atiflar) -> dict` | Ücretli çağrı yok. |
| `sorgu_dar` | `(dusen: list[str], noktalar: list[str]) -> bool` | Bütün token. |
| Model | `DENETIM_MODEL = "claude-haiku-4-5"` | B3 `OZET_MODEL` ile aynı kimlik. |
| Eşik | `UZUN_CEVAP = 800` | Spec sayı vermez. |
| Kural payı | `KURAL_SINIRI = 1500` | Yalnız `## Ders akışı` kesilir. `## Sınırlar` kesilmez. |
| Kaynak payı | `DENETIM_KAYNAK = 8` | `retrieval_k` ile aynı tavan. |
| Çağrı tavanı | `DENETIM_MAX_TOKENS = 2000`, `DENETIM_TIMEOUT_S = 30` | `_request` tavanı değil. |
| Betik | `scripts/asistan_eval.py` | Spec adı. |
| Sorular | `src/assistant_eval/sorular.json` | Skill dizinine konmaz. `kaynaklar` listesi bozulmaz. |
| Test | `tests/test_assistant_denetim.py` | Pytest. Ağa gitmez. |
| Kayıt | `output/asistan_eval/<damga>/sonuc.json` | `output/` zaten yok sayılır. |

Okur cümleleri:

| Durum | Metin |
|---|---|
| Denetim | Yeni cümle yok. Taslak ya da düzeltilmiş cevap durur. |
| Etiket | `Son yanıtı … yazdı` yine `meta.model` okur. Haiku bu satıra yazılmaz. |
| Bozulma | `meta.degraded` denetim için kullanılmaz. |

## File Structure

| Dosya | Durum | Sorumluluk |
|---|---|---|
| `src/assistant_denetim.py` | yeni | Kapı, istem, ayrıştırma, uygulama, puan, sorgu bayrağı |
| `src/assistant_eval/sorular.json` | yeni | 12 altın soru |
| `src/assistant_core.py` | değişir | `chat` içinde tek çağrı; delta yok |
| `scripts/asistan_eval.py` | yeni | Onaysız çıkış; onaylı kayıt |
| `tests/test_assistant_denetim.py` | yeni | Kapı, akış, şema, onaysız betik |
| `CLAUDE.md` | değişir | B6 maddesi, B5 maddesinin altı |

---

### Task 1: Kapı, ayrıştırma, puan

**Files:**
- Create: `src/assistant_denetim.py`
- Test: `tests/test_assistant_denetim.py`

**Interfaces:**
- Produces: `denetim_gerekli`, `ogretmen_kurallari`, `denetim_oku`, `denetim_uygula`, `puanla`, `sorgu_dar`, `DENETIM_ISTEMI`, `DENETIM_MODEL`.

- [ ] **Step 1: Test**

`tests/test_assistant_denetim.py`. Ağ yok. İçe aktarma `src.assistant_denetim`.

`denetim_gerekli("genel", "kısa", [])` `genel_kisa` döner. 799 karakter `genel_kisa`, 800 karakter None. `denetim_gerekli("matematik", "kısa", [])` None. Hata metinleri kümesinde birebir duran metin `hata_cevabi` döner.

`ogretmen_kurallari` dört gerçek skill gövdesiyle ölçülür. `assistant_skills.yukle()` `turkce`, `fen`, `sosyal` ve `matematik` döner. Her `skill.govde` için özet `cevap anahtarı` taşır, `## Maarif` taşımaz, `## Sınırlar` `## Ders akışı`ndan önce gelir. Dört satırlık bir gövde bu iddiayı taşımaz: Türkçe'nin `## Ders akışı` bölümü tek başına 1684 karakterdir. Aynı uzunlukta bir `## Ders akışı`, ardından `cevap anahtarı` yazan bir `## Sınırlar` da özette `cevap anahtarı` bırakır. 1500 karakterlik birleşik kesim bırakmaz. `## Maarif Modeli bağı` özete girmez.

`denetim_oku('{"ciddi": false}')` `ciddi` False verir. `denetim_oku` üç ters tırnaklı `json` çitinin içini okur. `ciddi` true, `sorun` `["kaynak", "uydurma", "kaynak"]` ise sorun `["kaynak"]` olur. `ogretmen` genel kapısında elenir: `ogretmen_bakisi` False iken `["ogretmen"]` `ValueError` verir. Boş `cevap`, dizgi olmayan `cevap` ve `{"ciddi": true}` `ValueError` verir.

`denetim_uygula("taslak", {"ciddi": false})` metni ve `durum == "gecti"` verir. Ciddi `cevap` `"yeni"` ise metin `"yeni"`, `durum` `duzeltildi`. `"taslak"` ile aynı ya da `"  "` ise metin taslak kalır, `durum` `hata`, `neden` sırasıyla `ayni` ve `bos`.

`puanla` bir soru, cevap `"Payda eşitlenir, sonuç 5/6."`, çağrı `[{"name": "kazanim_ara"}]`, atıf `[{"label": "Kesirler", "snippet": "payda", "locator": {"tool": "kazanim_ara"}}]` ile `arac_tamam`, `kaynak_tamam` ve `nokta_tamam` true verir. Araç adı yoksa `arac_tamam` false. `kaynak` katlanmış etiket, snippet ya da `locator.tool` içinde yoksa `kaynak_tamam` false. Nokta cevapta yoksa `nokta_tamam` false ve `eksik_noktalar` o noktayı taşır.

`sorgu_dar(["neden"], ["neden"])` true. `sorgu_dar(["neden"], ["payda"])` false. `sorgu_dar(["mi"], ["kimyasal"])` false.

`DENETIM_ISTEMI` kilitlenen metinle birebir aynıdır. `DENETIM_MODEL` `claude-haiku-4-5`.

- [ ] **Step 2: FAIL**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-b2-plan
DASHBOARD_SECRET_KEY=yalniz-test /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest tests/test_assistant_denetim.py
```

Expected: FAIL, modül yok.

- [ ] **Step 3: Uygula**

Kilitlenen kapı. `ogretmen_kurallari` önce `## Sınırlar` bölümünün tamamını yazar, sonra `## Ders akışı` bölümünden en çok `KURAL_SINIRI` karakter alır. Başka başlık yok. JSON ayrıştırma, tek uygulama, `turkce_kucult_katla` ile puan ve bütün token `sorgu_dar`. `puanla` ağa gitmez.

- [ ] **Step 4: PASS**

Aynı pytest. Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/assistant_denetim.py tests/test_assistant_denetim.py
git commit -m "feat: cevap denetiminin kararını ekle"
```

---

### Task 2: chat içine tek çağrı

**Files:**
- Modify: `src/assistant_core.py`
- Modify: `tests/test_assistant_denetim.py`

**Interfaces:**
- Consumes: `denetim_gerekli`, `denetim_oku`, `denetim_uygula`, `ogretmen_kurallari`, `DENETIM_ISTEMI`, `DENETIM_MODEL`.
- Produces: `chat(..., denetle=None)` dönüşünde `meta.denetim`. `chat_events` aynı payload'ı `answer` olayında verir.

- [ ] **Step 1: Test**

Aynı dosyaya eklenir. `AssistantRuntime` kurulur. `declarations` ve `degraded` boş yama alır. `chat_with_tools` `on_delta("taslak ")` çağırır ve `ToolLoopResult(text="taslak [S1].", citations=[{"kind": "mufredat", "label": "Payda", "locator": {}, "snippet": "Payda eşitlenir.", "confidence": 0.9}])` döner. `denetle` sayaç tutar ve `'{"ciddi": true, "sorun": ["kaynak"], "cevap": "Payda eşitlenir [S1]."}'` döner.

`chat_events` olay adları `answer_delta`, sonra `answer` olur. Delta metni `taslak ` olur. `answer` sonrası başka delta yoktur. `answer` gövdesi `payload` taşır. `payload.answer` `Payda eşitlenir [S1].` olur. `payload.meta.model` Haiku değildir. `payload.meta.denetim.durum` `duzeltildi`, `sorun` `["kaynak"]`, `model` `claude-haiku-4-5`. `denetle` bir kez çağrılır. `llm.last_model_used` değişmez.

Ayrı test: `denetle` `RuntimeError` yükseltir. Cevap taslak kalır. `durum` `hata`, `neden` `cagri`. `str(payload)` içinde istisna adı yoktur. Sayaç 1.

Ayrı test: dönüş `'{"ciddi": false}'`. Cevap taslak. `durum` `gecti`. Sayaç 1.

Ayrı test: `ogretmen` verilmez, metin `kisa`. `denetle` 0 kez. `durum` `atlandi`, `neden` `genel_kisa`.

Ayrı test: `ogretmen="matematik"`, metin `kisa`, `denetle` verilmez, `llm.available` False. Sayaç diye bir istemci çağrısı yoktur. `neden` `model_yok`. Cevap değişmez.

Ayrı test: `chat_with_tools` `text=""` döner. Cevap `_fallback_answer` olur. `denetle` 0 kez. `neden` `hata_cevabi`.

Ayrı test: güvenlik bayrağı `risk:clinical_request` üreten kullanıcı metni ve ciddi düzeltme. Son metin `SafetyPolicy.guidance_suffix(["risk:clinical_request"])` ile biter. Bu dönüş iki cümledir: `Not: Klinik tanı/tedavi önerisi veremem. Bu konuyu okul psikolojik danışmanı veya lisanslı uzmanla değerlendirin.` Yalnız birinci cümleyi arayan test canlı son eki kısaltır. Denetimin gördüğü `cevap` bu son eki içermez.

Ayrı test: düzeltme `[S9]` ekler. İşaret düşer. `dropped_citations`, ilk geçişteki düşenle bu düşenin toplamıdır.

- [ ] **Step 2: FAIL**

Aynı pytest. Expected: FAIL, `denetle` parametresi yok.

- [ ] **Step 3: Uygula**

`chat` içinde sıra şudur. Araç döngüsü biter, boş metin yedek cümleye döner, `_finalize_citations` çalışır. `denetim_gerekli` None değilse `meta.denetim` `atlandi` olur ve `denetle` çağrılmaz. None ise ve `denetle` yoksa ve `llm.available` False ise `neden` `model_yok`. Aksi halde bir çağrı. Verilen `denetle(istem, kullanici_json)` ham dizgi döner. Varsayılan çağrı `messages.create` kullanır: `model` `DENETIM_MODEL`, `max_tokens` 2000, `timeout` 30, sistem `DENETIM_ISTEMI`, tek kullanıcı mesajı. Araç, thinking, temperature, stream ve `cache_control` yoktur. `last_model_used` ve `loop.usage` yazılmaz. `denetim_oku` `ValueError` ise `bicim`. Başka istisna `cagri`. `denetim_uygula` metni değiştirirse aynı atıf listesiyle ikinci `_finalize_citations`. Sonra boş atıf listesine `warning:limited_confidence`. Sonra `guidance_suffix`. Klinik bayrakta bu, danışman cümlesini de içeren canlı son ektir; birinci cümlede kesilmez. `on_delta` bu arada çağrılmaz.

`kurallar`, `ogretmen != "genel"` ise `ogretmen_kurallari(skill.govde)`. Genel modda null. `kaynaklar` çözülmüş atıfların ilk 8'i: `id`, `label`, `snippet`.

`_write_metric` gövdesine `denetim` olarak yalnız `durum` girer. Cevap metni loga girmez.

`study_plan` ve `openai_chat_completion` yeni argüman geçirmez. Öğretmenleri `genel` kalır.

- [ ] **Step 4: PASS**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-b2-plan
DASHBOARD_SECRET_KEY=yalniz-test /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest \
  tests/test_assistant_denetim.py tests/test_assistant_core.py tests/test_assistant_hitap.py \
  tests/test_assistant_ogretmen_modu.py
```

Expected: PASS. Kısa genel cevaplar `genel_kisa` taşır; eski anahtarlar (`degraded`, `dropped_citations`, `ogretmen`) durur.

- [ ] **Step 5: Commit**

```bash
git add src/assistant_core.py tests/test_assistant_denetim.py
git commit -m "feat: cevap okura gitmeden önce bir kez denetlenir"
```

---

### Task 3: Altın soru seti ve elle koşan betik

**Files:**
- Create: `src/assistant_eval/sorular.json`
- Create: `scripts/asistan_eval.py`
- Modify: `tests/test_assistant_denetim.py`

**Interfaces:**
- Consumes: `puanla`, `sorgu_dar`, B3 `_sorguya`, `atomic_json_dump`.
- Produces: `sorulari_yukle`, `sonuc_yaz`, `main`.

- [ ] **Step 1: Test**

`sorulari_yukle` dört ders görür: `turkce`, `fen`, `sosyal`, `matematik`. Her birinde 3 soru. Her soruda `id`, `soru`, `arac`, `kaynak`, `noktalar`. `id` `<ders>-1` biçimindedir. `arac` şunlardan biridir: `kazanim_ara`, `kitap_sayfa`, `skill_kaynagi`. Her nokta katlandıktan sonra en az 4 karakterdir ve şu kelimelerden biri değildir: `nedir`, `nelerdir`, `nasıl`, `nasil`, `neden`, `niçin`, `nicin`, `kim`, `kimdir`, `hangi`, `kaç`, `kac`, `mı`, `mi`, `mu`, `mü`. Toplam 12.

`main([])` 2 döner. `tmp` altında `asistan_eval` dizini yoktur. Sahte `calistir` 0 kez çağrılır. `load_env` çağrılmaz. Dosya olarak `python scripts/asistan_eval.py` de 2 döner; `src` içe aktarılmaz.

`sonuc_yaz(kok, satirlar, sha, simdi=datetime(2026, 10, 3, 9, 45, tzinfo=timezone.utc), calistir_sayisi=12)` `kok/20261003T094500Z/sonuc.json` yazar. `ozet.soru` 12. `sorular_sha256` verilen sha. Aynı damgaya ikinci yazış `20261003T094500Z-2` olur. Birinci dosya durur. Yazış `atomic_json_dump` iledir.

Puan satırı şunları taşır: `id`, `ogretmen`, `arac_tamam`, `kaynak_tamam`, `nokta_tamam`, `eksik_noktalar`, `cagrilan_araclar`, `denetim`, `sorgu_dar`, `dusen_tokenler`, `cevap`. `denetim` chat dönüşündeki `meta.denetim` nesnesidir.

`_sorguya("Payda neden eşitlenir?")` düşen tokeni `neden` yapar. Nokta `["neden"]` ise `sorgu_dar` true, nokta `["payda"]` ise false. Bu test `_sorguya`'yı çağırır, modeli çağırmaz.

- [ ] **Step 2: FAIL**

Aynı pytest. Expected: FAIL, soru dosyası yok.

- [ ] **Step 3: Uygula**

`src/assistant_eval/sorular.json` aşağıdaki gövdedir. `surum` 1.

```json
{
  "surum": 1,
  "dersler": {
    "matematik": [
      {"id": "matematik-1", "soru": "1/2 + 1/3 işlemini adım adım çöz.", "arac": "kazanim_ara", "kaynak": "kesir", "noktalar": ["payda"]},
      {"id": "matematik-2", "soru": "3x = 12 denkleminde x kaçtır? İki tarafa aynı işlemi uygulayarak çöz.", "arac": "kitap_sayfa", "kaynak": "denklem", "noktalar": ["iki taraf"]},
      {"id": "matematik-3", "soru": "Bir dairenin çevresi ile alanı aynı mıdır?", "arac": "skill_kaynagi", "kaynak": "daire", "noktalar": ["çevre", "alan"]}
    ],
    "fen": [
      {"id": "fen-1", "soru": "Sindirim nerede başlar?", "arac": "kazanim_ara", "kaynak": "sindirim", "noktalar": ["ağız"]},
      {"id": "fen-2", "soru": "Enerji harcanınca yok olur mu?", "arac": "kitap_sayfa", "kaynak": "enerji", "noktalar": ["dönüş"]},
      {"id": "fen-3", "soru": "Tuzlu su bir bileşik midir?", "arac": "kazanim_ara", "kaynak": "karışım", "noktalar": ["karışım"]}
    ],
    "turkce": [
      {"id": "turkce-1", "soru": "Bağlaç olan de bitişik mi yazılır?", "arac": "skill_kaynagi", "kaynak": "bağlaç", "noktalar": ["ayrı"]},
      {"id": "turkce-2", "soru": "Konu ile ana fikir aynı mıdır?", "arac": "kazanim_ara", "kaynak": "ana fikir", "noktalar": ["ana fikir"]},
      {"id": "turkce-3", "soru": "Fiilimsi kip eki alır mı?", "arac": "kitap_sayfa", "kaynak": "fiilimsi", "noktalar": ["fiilimsi"]}
    ],
    "sosyal": [
      {"id": "sosyal-1", "soru": "Kanunları kim yapar?", "arac": "kazanim_ara", "kaynak": "kanun", "noktalar": ["TBMM"]},
      {"id": "sosyal-2", "soru": "Tarihte bir olayın tek nedeni olur mu?", "arac": "kitap_sayfa", "kaynak": "neden", "noktalar": ["birden çok"]},
      {"id": "sosyal-3", "soru": "Demokrasi yalnız oy vermek midir?", "arac": "skill_kaynagi", "kaynak": "demokrasi", "noktalar": ["kuvvetler"]}
    ]
  }
}
```

`scripts/asistan_eval.py` modül başında yalnız stdlib alır. `src` içe aktarımı fonksiyonun içindedir. Dosya olarak açılışta (`__name__ == "__main__"`) ve yalnız `--onayla` varken, bu içe aktarımdan önce proje kökü `sys.path`'e girer: `Path(__file__).resolve().parents[1]`. Ardından `src.env_loader.load_env()` çağrılır. Kök yoksa `src` içe aktarılamaz. `load_env` yoksa `ClaudeClient` anahtarı görmez ve on iki cevap bağlantı hata cümlesi olur. `--onayla` yokken ikisi de olmaz.

`main(argv)` `--onayla` yoksa 2 döner ve hiçbir şey yazmaz. Varsa `kos` on iki soruyu sırayla çağırır. Her çağrı `runtime.chat(messages=[{"role": "user", "content": soru}], ogretmen=ders, okur="ogrenci", mod_onerisi=False)`. `sohbet_id` geçmez. Depo açılmaz. Bir soru istisna verirse satırın `cevap` alanı `""`, `denetim.durum` `hata`, `denetim.neden` `cagri` olur ve döngü sürer.

Düşen token: soru işaretleri silinmiş `split()` ile `_sorguya(soru).split()` arasındaki, katlanmış halde ikincide olmayan tokenler. `sorgu_dar` Görev 1'in fonksiyonudur. `_sorguya` yeniden yazılmaz.

`sonuc.json` anahtarları: `surum` `"1"`, `zaman`, `model` (cevap modeli), `denetim_model` `claude-haiku-4-5`, `sorular_sha256` (dosya baytlarının sha256'sı), `sorular` (on iki satır), `ozet` (`soru`, `arac_tamam`, `kaynak_tamam`, `nokta_tamam`). Cevap satırı kayıtta durur. `output/` altındadır.

`if __name__ == "__main__"` önce argv'ye bakar. `--onayla` varsa kökü ekler, `load_env()` çağırır, sonra `raise SystemExit(main(sys.argv[1:]))`. Yoksa yalnız `main` çalışır ve 2 döner. Test `--onayla` geçirmez.

- [ ] **Step 4: PASS**

Aynı pytest. Expected: PASS. Komut satırında `--onayla` yoktur.

- [ ] **Step 5: Commit**

```bash
git add src/assistant_eval/sorular.json scripts/asistan_eval.py tests/test_assistant_denetim.py
git commit -m "feat: ders başına altın soru setini ekle"
```

---

### Task 4: CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`, B5 maddesinin hemen altı. B5 maddesi `- **Asistan ses (B5)**` ile başlar.

- [ ] **Step 1: Madde**

```markdown
- **Asistan cevap denetimi (B6)** (spec B6 bölümü, plan `docs/superpowers/plans/2026-10-03-asistan-cevap-denetimi-b6.md`): a teacher-mode answer, and a genel answer of at least 800 characters, passes once through `claude-haiku-4-5` before the reader sees it. The check covers source consistency, 7th-grade level, the explaining-teacher rules, and address. A serious finding replaces the whole answer once. A skip or an error keeps the draft and sets `meta.denetim`. The draft still streams on `answer_delta`; the checked text arrives on the `answer` event's `payload`. `meta.model` stays the answer model. `scripts/asistan_eval.py` runs the 12 golden questions only with `--onayla` and writes `output/asistan_eval/<stamp>/sonuc.json`. Tests never pass `--onayla`. `_sorguya` gains no second model; the run only records `sorgu_dar`.
```

- [ ] **Step 2: Son kapı**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-b2-plan
DASHBOARD_SECRET_KEY=yalniz-test /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest \
  tests/test_assistant_denetim.py tests/test_assistant_core.py
git diff --check -- CLAUDE.md docs/superpowers/plans/2026-10-03-asistan-cevap-denetimi-b6.md
```

Expected: pytest 0. `git diff --check` boş.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: cevap denetimi planını CLAUDE.md'ye yaz"
```

## Kapsam denetimi

| Spec | Görev |
|---|---|
| Öğretmen modunda ve uzun cevapta ucuz denetim | 1, 2 |
| Uzunluğun sayısı, 800 | 1, 2 |
| Kaynak, 7. sınıf, anlatan öğretmen, hitap | 1, 2 |
| `## Sınırlar` içindeki `cevap anahtarı` özette durur | 1 |
| Klinik son ek danışman cümlesini de taşır | 2 |
| Betik, dosya olarak ve `--onayla` sonrası kök ve `load_env` | 3 |
| Ciddiyse bir kez bütün cevap değişir | 1, 2 |
| Taslak akarken sonuç `answer` olayında | 2 |
| Atlama ya da hata: taslak durur, meta işaretlenir | 1, 2 |
| `meta.model` cevap modeli kalır, okur cümlesi eklenmez | 2 |
| Ders başına altın soru: kaynak, araç, içerik noktası | 3 |
| `scripts/asistan_eval.py`, elle, açık onay | 3 |
| `output/asistan_eval/` altında sürümlü kayıt | 3 |
| Testler betiği koşmaz | 3 |
| B3 sorgu cümlesi ölçülür, model eklenmez | 1, 3 |
| Sunucu TTS/STT, yeni uç | yok |
