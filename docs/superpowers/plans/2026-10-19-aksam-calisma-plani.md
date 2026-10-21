# Akşam Çalışma Planı Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Işık'ın okul günü akşamlarını ödev yüküne göre kendiliğinden kurulan, dokunuşla ilerleyen, durum değiştikçe yeniden dizilen ve takıldığında aileye haber veren bir çalışma planına çevirmek.

**Architecture:** Yerleşim saf bir Python motorudur (`src/aksam_plani.py`); plan her istekte canlı ödevlerden + o günün dokunuş durumundan **yeniden hesaplanır** (yani "Yaptım", yeni ödev, geç başlama kendiliğinden yansır). Model (Haiku) yalnız ödev başına bir kez süre/zorluk/ilk adım tahmini üretir, önbelleğe alınır ve senkron içinde önceden ısıtılır. Bugün'deki plan kartı, asistanın iki aracı ve her dakika çalışan bildirim turu aynı motoru okur.

**Tech Stack:** Python 3 / Flask / pytest; React 19 + Carbon (`@carbon/react`) + node:test + Playwright; Anthropic SDK (Haiku 4.5) üzerinden `src/claude_api.py`; web push `src/web_push.py`; systemd user timer.

**Spec:** `docs/superpowers/specs/2026-10-19-aksam-calisma-plani-design.md` (onaylı; §9'daki varsayılanlar geçerli).

## Global Constraints

- Saat dilimi Europe/Istanbul; naive `datetime.now()` İstanbul'dur (CLAUDE.md).
- Varsayılan akşam düzeni: ödeve hazır **17:00**, zor iş sonu **19:00**, hafif iş sonu **19:30**, yemek **18:30 / 30 dk**, yatma hazırlığı **20:30**, yatakta **21:00**, "başlamadı" eşiği **15 dk**, "takıldı" eşiği **15 dk**.
- Blok **20 dk** çalışma, **5 dk** mola, iki bloktan sonra **10 dk** mola; tahminlere **%25** tampon; yatma hazırlığından önce en az **15 dk** boş.
- Plana giren ödev: açık (öğretmen kararı yok, `student_marked_done` yok), teslimi **7 gün** içinde ya da en çok **3 gün** geçmiş; teslimi okunamayan en sona, "orta".
- 19:30 sonrası en çok **bir ≤ 10 dk** iş; 20:30 sonrası blok yok.
- Model `claude-haiku-4-5` (`TEDY_PLAN_MODEL` ile değişir), aylık tavan **2 USD** (`TEDY_PLAN_AYLIK_USD`), ödev başına bir çağrı, önbellekli.
- Bayraklar: `TEDY_AKSAM_PLANI=1` (kart + plan uçları + asistan araçları), `TEDY_AKSAM_BILDIRIM=1` (bildirim turu). İkisi de varsayılan kapalı.
- Sessiz saat 21:00–07:30; Işık'a blok başına en çok iki bildirim; ebeveyn olayları akşam başına birer kez.
- Ebeveyn bildirimi yalnız ayardaki açık `haber_alacaklar` listesine; liste boşken gitmez. `okur_turu == "aile"` alıcı seçmez.
- Yalnız okul günleri (`okulGunuMu` kuralı: o günün ders sütunu; program yoksa Pzt–Cum); "Bu akşam plan yok" yalnız `aile` okur türü.
- Kopya: cümle düzeni (S38), "sen" Işık'a / "siz" aileye, alarm dili yok ("geç kaldın", "yetiştiremeyeceksin" yasak), puan/seri/rozet yok; süre yalnız plan bloğunda ve "tahmin" sözcüğüyle.
- Kalıcı durum `fcntl.flock` + `atomic_json_dump`; yeni `output/` dosyaları BM25 indeksinden hariç (`DEFAULT_EXCLUDED_FILE_PATTERNS`).
- Testler canlı model/bildirim çağıramaz (`tests/conftest.py` yeni korumalar); Playwright `env -u ANTHROPIC_API_KEY`.
- Carbon import/prop/ikon bellekten yazılmaz: `carbon` MCP ya da `dashboard/node_modules` ile doğrulanır (talimatname §10); rem ölçüleri, token renkleri, `npm run lint` temiz.

## Review Focus

1. **Gece yarısını aşan ya da akşamı geçmiş açılış** (ör. 22:40'ta sayfa): plan "Bugünlük bu kadar" der, blok üretmez, bildirim gitmez; bir sonraki okul gününün önizlemesini gösterir. → Task 4 testi `test_yatma_sonrasi_blok_yok`, Task 9 testi `test_sessiz_saatte_gonderilmez`.
2. **Takvimde akşam olayı ya da özel ders** (ör. 17:30–18:20): bloklar onunla çakışmaz, olayın etrafına dizilir. → Task 4 testi `test_takvim_olayi_bloklari_boler`.
3. **Aynı ödevin iki işçide aynı anda "Başla"/"Bitti" alması** (iki sekme, iki gunicorn işçisi): durum dosyası bozulmaz, ikinci istek idempotent döner. → Task 5 testi `test_basla_iki_kez_idempotent`.
4. **Ödev metni boş ya da yalnız ek** (açıklama yok): tahmin yedeğe düşer, `ilk_adim` "Ödevin yönergesini ve ekini aç" olur, sayı uydurmaz. → Task 3 testi `test_bos_aciklama_yedek_ilk_adim`.
5. **Ayar dosyası bozuk ya da eski biçim** (`okul_bitisi/odak_sonu/yatma` yalnız): varsayılanlar + eski yatma saati korunur, sayfa düşmez. → Task 1 testi `test_eski_bicim_okunur`.

---

## File Structure

| Dosya | Sorumluluk |
|---|---|
| `src/aksam_duzeni.py` (yeni) | Akşam düzeni şeması, doğrulama, okuma (eski `odak_penceresi.json` biçimini de okur) |
| `src/odev_tahmini.py` (yeni) | Haiku okuyucu, kural tabanlı yedek, `ilk_adim` uydurma kapısı, önbellek + bütçe defteri |
| `src/aksam_plani.py` (yeni) | Saf motor: ödev seçimi, sıralama, parçalama, yerleştirme, taşıma; `PlanDeposu` (günlük dokunuş durumu, flock); çalışma kayıtları ve kalibrasyon |
| `src/aksam_bildirim.py` (yeni) | Her dakikalık tur: olay tespiti, defter, Işık/ebeveyn bildirimleri; CLI `tur` |
| `tedy-aksam-plani.service` / `.timer` (yeni, repo kökü) | Tur zamanlayıcısı (her dakika) |
| `src/dashboard_api.py` | `/api/aksam-duzeni` (GET/PUT), `/api/odak-penceresi` uyumluluk; `/api/plan/*` uçları |
| `src/run_sync.py` | `_tahmin_isitma_adimi` (sınav adımından sonra, 30 s) |
| `src/assistant_tools.py`, `src/assistant_core.py` | `aksam_plani` / `plani_degistir` araçları; `_build_rule_based_plan` yerine motor |
| `dashboard/src/utils/bugun.ts` | `AksamDuzeni` tipi, `duzenCoz`, `duzenGovdesi` (pencere yerine) |
| `dashboard/src/utils/gunSeridi.ts`, `components/DayStrip.*` | "Yol" parçası, ödev zamanı = hazır → zor iş sonu |
| `dashboard/src/components/AksamDuzeniAyari.tsx` (yeni, `OdakPenceresiAyari.tsx` yerine) | Profil kartı |
| `dashboard/src/utils/aksamPlani.ts` (yeni) | Saf istemci mantığı: kart durumu (önizleme/şimdi/mola/bitti), metinler |
| `dashboard/src/hooks/useAksamPlani.ts` (yeni) | `/api/plan/bugun` + dokunuş eylemleri |
| `dashboard/src/components/AksamPlani.tsx` + `.scss` (yeni) | Plan kartı |
| `dashboard/src/components/TodaySchedule.tsx` | Kartı akşam kipinde NextThing yerine koyar |
| `docs/tedy-ui-ux-talimatnamesi.md`, `CLAUDE.md` | S53 sapması, §8.8, yeni madde |

---

### Task 1: Akşam düzeni ayarı (sunucu)

**Files:**
- Create: `src/aksam_duzeni.py`
- Modify: `src/dashboard_api.py:1774-1832` (odak penceresi bloğu)
- Test: `tests/test_aksam_duzeni.py`

**Interfaces:**
- Produces: `VARSAYILAN: dict[str, Any]` = `{"odeve_hazir":"17:00","zor_is_sonu":"19:00","hafif_is_sonu":"19:30","yemek":"18:30","yemek_dk":30,"hazirlik":"20:30","yatma":"21:00","okul_bitisi":"15:45","baslamadi_esik_dk":15,"takildi_esik_dk":15,"haber_alacaklar":[]}`; `dogrula(govde: dict, aile_epostalari: set[str]) -> tuple[dict | None, str | None]`; `oku(yol: Path) -> dict` (her zaman tam sözlük + `"varsayilan": bool`); `dakika(saat: str) -> int`.
- Produces (HTTP): `GET /api/aksam-duzeni` → düzen + `"aile_uyeleri": [{"email","ad"}]` (yalnız `okur_turu=="aile"` tam rollüler); `PUT /api/aksam-duzeni` → düzen ya da 400 cümlesi. Dosya `output/aksam_duzeni.json`.
- Produces: `GET /api/odak-penceresi` artık `{okul_bitisi, odak_sonu: zor_is_sonu, yatma, varsayilan}` döner (eski istemciler kırılmaz); PUT'u eski üç alanı düzene işler.

- [ ] **Step 1: Write the failing tests**

```python
def test_varsayilan_aksam(tmp_path):
    d = oku(tmp_path / "yok.json")
    assert d["odeve_hazir"] == "17:00" and d["yatma"] == "21:00" and d["varsayilan"] is True

def test_sira_zorunlu():
    _, hata = dogrula({**VARSAYILAN, "zor_is_sonu": "16:30"}, set())
    assert hata and "sırayla" in hata

def test_yemek_hazir_ile_hazirlik_arasinda():
    _, hata = dogrula({**VARSAYILAN, "yemek": "20:45"}, set())
    assert hata

def test_haber_alacaklar_yalniz_aile(tmp_path):
    _, hata = dogrula({**VARSAYILAN, "haber_alacaklar": ["yabanci@x.com"]}, {"anne@x.com"})
    assert hata
    d, hata = dogrula({**VARSAYILAN, "haber_alacaklar": ["ANNE@x.com"]}, {"anne@x.com"})
    assert hata is None and d["haber_alacaklar"] == ["anne@x.com"]

def test_eski_bicim_okunur(tmp_path):
    p = tmp_path / "odak_penceresi.json"
    p.write_text('{"okul_bitisi":"15:45","odak_sonu":"16:00","yatma":"22:00"}')
    d = oku(tmp_path / "aksam_duzeni.json", eski=p)
    assert d["yatma"] == "22:00" and d["odeve_hazir"] == "17:00"

def test_bozuk_dosya_varsayilan(tmp_path):
    p = tmp_path / "aksam_duzeni.json"; p.write_text("{bozuk")
    assert oku(p)["varsayilan"] is True
```
Plus API tests (`TEST_AUTH_BYPASS`): PUT then GET round-trip; GET `/api/odak-penceresi` returns `odak_sonu == zor_is_sonu`.

- [ ] **Step 2: Run to verify fail** — `DASHBOARD_SECRET_KEY=t .venv/bin/python -m pytest tests/test_aksam_duzeni.py -q` → ImportError.

- [ ] **Step 3: Implement `src/aksam_duzeni.py` and the routes.** Sıra kuralı: `okul_bitisi <= odeve_hazir < zor_is_sonu <= hafif_is_sonu <= hazirlik < yatma`, yemek `[odeve_hazir, hazirlik - yemek_dk]` içinde, `yemek_dk` 10–60, eşikler 5–60. `oku(yol, eski=None)`: yeni dosya yoksa eski dosyadan `okul_bitisi`/`yatma` alınır, `odak_sonu` yok sayılır. Hata cümleleri Türkçe tek cümle. PUT `atomic_json_dump`. BM25: `aksam_duzeni.json` `DEFAULT_EXCLUDED_FILE_PATTERNS`'e.

- [ ] **Step 4: Run to verify pass** — aynı komut + `tests/test_dashboard_api.py -k odak` → PASS.

- [ ] **Step 5: Commit** — `git commit -m "feat(aksam): akşam düzeni ayarı ve uyumlu odak penceresi"`

---

### Task 2: Profil kartı ve Gün Şeridi akşam düzenini okur

**Files:**
- Modify: `dashboard/src/utils/bugun.ts` (`OdakPenceresi` → `AksamDuzeni`, `pencereCoz` → `duzenCoz`, `pencereGovdesi` → `duzenGovdesi`), `dashboard/src/hooks/useOdakPenceresi.ts` → `useAksamDuzeni.ts` (`/api/aksam-duzeni`), `dashboard/src/utils/gunSeridi.ts`, `dashboard/src/components/DayStrip.tsx/.scss`, `dashboard/src/components/TodaySchedule.tsx`, `dashboard/src/components/StudentProfile.tsx` (kartı değiştir)
- Create: `dashboard/src/components/AksamDuzeniAyari.tsx` (siler: `OdakPenceresiAyari.tsx`)
- Test: `dashboard/tests/bugun.test.ts`, `dashboard/tests/gunSeridi.test.ts`, `dashboard/tests/e2e/odak-penceresi.spec.ts` (→ `aksam-duzeni.spec.ts`)

**Interfaces:**
- Consumes: Task 1 HTTP.
- Produces: `interface AksamDuzeni { okulBitisi, odeveHazir, zorIsSonu, hafifIsSonu, yemek, yemekDk, hazirlik, yatma, baslamadiEsikDk, takildiEsikDk: number; haberAlacaklar: string[] }` (dakikalar); `VARSAYILAN_DUZEN`; `duzenCoz(json): AksamDuzeni`; `windowVoice(…, duzen)` `odakSonu` yerine `zorIsSonu` okur.
- Produces: `ParcaTuru` += `'yol'` (ad "Yol"); `GunGirdisi` += `odeveHazir`; ödev zamanı = `[odeveHazir, zorIsSonu]`; okul bitişi ile ödeve hazır arası `yol`.

- [ ] **Step 1: Failing unit tests** (`gunSeridi.test.ts`):
  `okul sabahı: sabah, okul, yol, ödev zamanı, akşam` → `['sabah 06:42','okul 08:00','yol 15:45','odev 17:00','aksam 19:00']` (odakSonu yerine zorIsSonu 19:00, odeveHazir 17:00, yatma 21:00); `okulsuz gün: ödev hazır saatinden` → `['sabah 07:00','odev 17:00','aksam 19:00']`; `bugun.test.ts`: `duzenCoz({})` varsayılanları verir, `windowVoice(17*60+10,'work',true,VARSAYILAN_DUZEN).eyebrow === 'Şimdi'`, `16*60` → `'Okuldan sonra'`.
- [ ] **Step 2: Run** `cd dashboard && npm run test:birim` → FAIL.
- [ ] **Step 3: Implement.** Okulsuz günde ödev zamanı da `odeveHazir`'dan başlar (§9 S1: yalnız okul günü planlanır ama şerit hafta sonu da ödev dilimini gösterir). Profil kartı: Carbon `TimePicker` × 6 (hazır, zor iş sonu, hafif iş sonu, yemek, hazırlık, yatma), `NumberInput` yemek süresi, `Checkbox` grubu "Haber alacaklar" (GET'teki `aile_uyeleri`), başlık "Akşam Düzeni" (S38 başlık düzeni), yardım metni: "Liste boşken TEDY kimseye haber vermez." ve cihaz notu (§9 S6): "Işık'ın bildirimleri yalnız onun hesabıyla açılmış cihazlara gider." `TimePicker`/`NumberInput`/`Checkbox` prop'ları `carbon` MCP ile doğrulanır.
- [ ] **Step 4: Run** birim testler + `env -u ANTHROPIC_API_KEY npx playwright test aksam-duzeni bugun-duzen today` → PASS; şerit "Yatma 21:00" ve "Ödev zamanı 17:00–19:00" gösterir.
- [ ] **Step 5: Baselines** — `gorsel-regresyon aria-yapisi gorunum-kipleri -g "Bugün|Profil|bugun|profil|kontrast" --update-snapshots=all`, farkı oku.
- [ ] **Step 6: Commit** — `feat(aksam): Profil'de akşam düzeni, şeritte yol ve 17–19 ödev zamanı`

---

### Task 3: Ödev tahmini (Haiku + yedek + kapı + önbellek)

**Files:**
- Create: `src/odev_tahmini.py`
- Modify: `tests/conftest.py` (canlı okuyucu yasak), `src/assistant_core.py` (`DEFAULT_EXCLUDED_FILE_PATTERNS` += `odev_tahmin_*`)
- Test: `tests/test_odev_tahmini.py`

**Interfaces:**
- Consumes: `src/claude_api.istemci/metin`, `src/ocr_katmani.OcrDefteri(yol, tavan, simdi)` (`izin_var()`, `yaz(model, girdi, cikti)`, `harcanan()`).
- Produces: `@dataclass OdevTahmini(dakika: int, zorluk: Literal["zor","orta","kolay"], ilk_adim: str, parcalar: list[str], kaynak: Literal["model","yedek","okur"])`; `odev_metni(satir: dict) -> str` (ders + başlık + açıklama + ek adları); `kural_tahmini(satir: dict, bugun: date) -> OdevTahmini`; `uydurma_kapisi(t: OdevTahmini, metin: str) -> OdevTahmini`; `class TahminDeposu(kok: Path, okuyucu, tavan=2.0, simdi=None)` with `tahmin(satir: dict, bugun: date) -> OdevTahmini` (önbellekten; yoksa yedek, modeli çağırmaz) and `isit(satirlar: list[dict], bugun: date, bitis: float) -> dict` (model çağrıları, bütçe/süre içinde; özet döner); `okur_suresi_yaz(anahtar: str, dakika: int)`.
- Önbellek: `output/odev_tahmin_onbellegi.json`, anahtar `f"{ISTEM_SURUMU}:{model}:{homework_key}:{sha256(odev_metni)[:12]}"`; defter `output/odev_tahmin_defteri.json`; okur düzeltmesi `output/odev_tahmin_okur.json` (`{homework_key: dakika}`, model tahminini ezer, `kaynak="okur"`).

- [ ] **Step 1: Failing tests**

```python
def test_kural_tahmini_yarin_teslim_30dk_orta():
    t = kural_tahmini({"Ödev Son Teslim Tarihi": "20.10.2026 08:00", "Ders Adı": "Matematik"}, date(2026,10,19))
    assert (t.dakika, t.zorluk, t.kaynak) == (30, "orta", "yedek")

def test_kapi_metinde_olmayan_sayiyi_reddeder():
    t = OdevTahmini(25, "zor", "Sayfa 47'deki 5 soruyu çöz", ["…"], "model")
    assert uydurma_kapisi(t, "Kesirler alıştırması, sayfa 32").ilk_adim == YEDEK_ILK_ADIM

def test_kapi_metindeki_sayiyi_kabul():
    t = OdevTahmini(25, "zor", "Sayfa 32'deki ilk 3 soruyu çöz", [], "model")
    assert "32" in uydurma_kapisi(t, "Kesirler, sayfa 32, 1-10 arası").ilk_adim

def test_bos_aciklama_yedek_ilk_adim():
    t = kural_tahmini({"Ödev Başlığı": "", "detail": {"description": ""}}, date(2026,10,19))
    assert t.ilk_adim == "Ödevin yönergesini ve ekini aç"

def test_onbellek_ikinci_cagri_modeli_cagirmaz(tmp_path):
    sahte = SahteOkuyucu(OdevTahmini(40, "zor", "Yönergeyi oku", [], "model"))
    d = TahminDeposu(tmp_path, sahte)
    d.isit([SATIR], BUGUN, bitis=time.monotonic()+30)
    d.isit([SATIR], BUGUN, bitis=time.monotonic()+30)
    assert sahte.cagri == 1 and d.tahmin(SATIR, BUGUN).dakika == 40

def test_tavan_dolunca_cagri_yok(tmp_path): ...  # tavan=0.0 → sahte.cagri == 0, tahmin yedek
def test_okur_suresi_modeli_ezer(tmp_path): ...  # okur_suresi_yaz → kaynak "okur", dakika okurunki
def test_tahmin_dakikasi_sinirli(): ...          # model 0 ya da 400 dk → [5, 120] aralığına kıstırılır
```
- [ ] **Step 2: Run** `.venv/bin/python -m pytest tests/test_odev_tahmini.py -q` → FAIL.
- [ ] **Step 3: Implement.** Model şeması `{dakika:int, zorluk:enum, ilk_adim:str(≤80), parcalar:[str(≤60)] (≤4)}` — `output_config.format` json_schema (sınav okuyucusundaki desen); istem Işık'ın 7. sınıf olduğunu, cömert tahmin ve tek cümlelik, somut ilk adım istediğini söyler. Kapı: `ilk_adim` ve her `parcalar` öğesindeki her sayı `odev_metni` içinde geçmeli; geçmeyen parça düşer, ilk adım `YEDEK_ILK_ADIM = "Ödevin yönergesini ve ekini aç"` olur. Yedek: teslim yarın/bugün 30, 2–3 gün 30, sonrası 20; zorluk "orta". `conftest.py`: `odev_tahmini.ClaudeTahminOkuyucu.oku` çağrılırsa `AssertionError`.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** — `feat(aksam): ödev süre/zorluk/ilk adım tahmini, kapı ve bütçe`

---

### Task 4: Plan motoru (saf)

**Files:**
- Create: `src/aksam_plani.py` (motor bölümü)
- Test: `tests/test_aksam_plani_motor.py`

**Interfaces:**
- Consumes: Task 1 `oku()` sözlüğü, Task 3 `OdevTahmini`.
- Produces:
  - `@dataclass Blok(id: str, tur: Literal["calisma","mola","yemek","olay"], bas: int, bit: int, odev_anahtari: str | None = None, ders: str | None = None, baslik: str = "", adim: str = "", parca: int = 0, parca_sayisi: int = 1, tahmin_dk: int = 0, zorluk: str = "orta", durum: Literal["bekliyor","suruyor","bitti","ertelendi"] = "bekliyor")`; `id` = `sha1(gun|odev_anahtari|parca)[:10]` (aynı ödev parçası yeniden dizilince aynı kimlik).
  - `@dataclass Plan(gun: str, bloklar: list[Blok], tasinan: list[dict], sigmayan: list[dict], planda_olmayan: int, durum: Literal["plansiz","onizleme","akis","bitti","okulsuz","kapali"])`.
  - `planlanacak(satirlar: list[dict], bugun: date) -> tuple[list[dict], int]` (seçilen, dışarıda kalan sayısı).
  - `plan_kur(satirlar, tahmin: Callable[[dict], OdevTahmini], duzen: dict, simdi: datetime, olaylar: list[tuple[int,int,str]], gunluk: dict, okul_gunu: bool, tatil: bool = False) -> Plan`. `gunluk` = Task 5'in o günlük durumu (`{blok_id: {"durum","basla","bitti"}}`, `"ertelenen": [blok_id]`, `"ek_parca": {odev_anahtari: int}`, `"aksam_yok": bool}`).
- Algoritma (yapıcının serbest bırakılmadığı kısım):
  1. Sıralama puanı: `teslim_kademesi` (yarın/bugün/geçmiş=3, 2 gün=2, sonrası=1) × `zorluk_agirligi` (zor 3, orta 2, kolay 1); yaklaşan 7 gün içindeki sınavın dersi +1 kademe; eşitlikte talimatı olan önce, sonra teslim saati.
  2. Ödev süresi = `ceil(tahmin.dakika × kalibrasyon(ders) × 1.25)`; 20 dk'lık parçalara bölünür (son parça ≥ 5 dk), parça adımı `parcalar[i]` ya da `ilk_adim` (ilk parça) / "Kaldığın yerden devam et".
  3. Yerleştirme imleci = `max(odeve_hazir, simdi)`; sürmekte olan blok varsa onun tahmini bitişi. Yemek ve `olaylar` sabit engeldir. Zor/orta parçalar `zor_is_sonu`'na kadar, kolaylar `hafif_is_sonu`'na kadar; `hafif_is_sonu`–`hazirlik - 15` arasına yalnız ≤ 10 dk tek iş; her parçadan sonra 5 dk mola, her iki çalışma bloğunda bir 10 dk.
  4. Bitmiş/sürmekte olan bloklar `gunluk`'tan aynen korunur; ertelenen blok bir kez sona gider.
  5. Sığmayan: teslimi yarından sonraysa `tasinan`, değilse `sigmayan` (taşınmaz).
  6. `aksam_yok` ya da `tatil` → `durum="kapali"`, blok yok; `okul_gunu` False → `"okulsuz"`; `simdi >= hazirlik` → `"bitti"`; `simdi < odeve_hazir` → `"onizleme"`.

- [ ] **Step 1: Failing tests** (her biri sabit `simdi`, sahte `tahmin`):

```python
def test_kabul_1_aksam_dizilimi():
    p = plan_kur(DORT_ODEV, T, VARSAYILAN, dt("2026-10-19 16:30"), [], {}, True)
    calisma = [b for b in p.bloklar if b.tur == "calisma"]
    assert calisma[0].bas == 17*60 and calisma[0].odev_anahtari == "yarin-zor"
    assert any(b.tur == "yemek" and b.bas == 18*60+30 for b in p.bloklar)
    assert sum(1 for b in calisma if b.bas >= 19*60+30) <= 1
    assert all(b.bit <= 20*60+15 for b in calisma)

def test_yaptim_planlanacaktan_cikarir(): ...           # student_marked_done → seçilmez
def test_eski_odev_sayilir_ama_planlanmaz(): ...       # 10 gün geçmiş → planda_olmayan == 1
def test_sigmayan_uzak_teslim_yarina(): ...            # 6 × 60 dk → tasinan dolu, yarın teslim olan sigmayan'da
def test_takvim_olayi_bloklari_boler(): ...            # olay 17:30–18:20 ile hiçbir blok çakışmaz
def test_ertelenen_bir_kez_sona_gider(): ...
def test_suren_blok_korunur_yeniden_dizmede(): ...     # gunluk'ta suruyor olan blok aynı bas/bit
def test_ayni_parca_ayni_kimlik(): ...                 # iki kurulumda blok id'leri eşit
def test_yatma_sonrasi_blok_yok(): ...                 # 22:40 → durum "bitti", bloklar boş
def test_aksam_yok_kapali(): ...
def test_tatil_gunu_kapali(): ...                   # tatil=True → durum "kapali", blok yok
def test_okulsuz_gun(): ...
def test_gec_baslama_imleci_simdiden(): ...            # 17:40'ta hiç Başla yok → ilk blok 17:40
```
- [ ] **Step 2: Run** `.venv/bin/python -m pytest tests/test_aksam_plani_motor.py -q` → FAIL.
- [ ] **Step 3: Implement** motoru (saf; dosya, saat, ağ yok).
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** — `feat(aksam): akşam planı motoru`

---

### Task 5: Plan durumu, kayıtlar, kalibrasyon ve uçlar

**Files:**
- Modify: `src/aksam_plani.py` (depo bölümü), `src/dashboard_api.py` (yeni uçlar), `src/assistant_core.py` (BM25 hariç)
- Test: `tests/test_aksam_plani_api.py`

**Interfaces:**
- Consumes: Task 1, 3, 4; `dashboard_api._canli_odevler()`, `_private_lessons_for_day(date)`, `/api/calendar` olayları, `okulGunuMu` eşdeğeri `assistant_tools.gunun_dersleri`.
- Produces:
  - `class PlanDeposu(kok: Path)`: `gunluk(gun: str) -> dict`; `degistir(gun: str, fn: Callable[[dict], None]) -> dict` (flock `output/aksam_plani.json.lock`, yeniden oku → değiştir → `atomic_json_dump`); 14 günden eski günler budanır.
  - `class CalismaKayitlari(kok: Path)`: `ekle(kayit: dict)` (`output/calisma_kayitlari.jsonl`, flock, eklemeli); `kalibrasyon(ders: str) -> float` (son 10 kaydın `gercek/tahmin` medyanı, [0.5, 2.0]; kayıt < 3 → 1.0).
  - `bugunku_plan(simdi: datetime | None = None) -> Plan` in `dashboard_api` (tek yer; kart, asistan, tur okur). `tatil` = o güne düşen tüm gün takvim olayının başlığında katlanmış "tatil" ya da "bayram" geçmesi (`_tatil_mi(gun, olaylar) -> bool`, testi `test_takvim_tatili_plani_kapatir`).
  - HTTP (oturum + tam rol, bayrak kapalıyken 404 `{"kapali": true}`):
    - `GET /api/plan/bugun` → `{gun, durum, bloklar[], simdiki, siradaki, tasinan[], sigmayan[], planda_olmayan, haber_metni}`; `haber_metni` örn. "17:15'e kadar başlamazsan annene haber gider." (alıcı yoksa `null`).
    - `POST /api/plan/blok/<id>/basla`, `/bitti`, `/simdi-degil`; `bitti` gövdesi `{"tamamlandi": bool}` (son parçada); ilk "Başla" o günün `basladi` zamanını yazar.
    - `PUT /api/plan/odev/<key>/sure` `{dakika: 5..120}` → `TahminDeposu.okur_suresi_yaz`.
    - `POST /api/plan/aksam-yok` `{aktif: bool}` → yalnız `okur_turu=="aile"`, değilse 403 "Bunu yalnız aile değiştirebilir.".
  - "Bitti" + `tamamlandi:true` sunucuda `_isaret_kilidi()` altında "Yaptım" kaydını yazar (aynı `mark-done` yolu, aynı anahtar); `tamamlandi:false` → `ek_parca[odev] += 1` (10 dk).

- [ ] **Step 1: Failing tests** (`TEST_AUTH_BYPASS`, sabit saat `freezegun` yok — `simdi` parametresiyle `bugunku_plan` test edilir, uçlar `_simdi()` yaması ile):

```python
def test_kabul_2_yaptim_yeniden_dizer(api, saat_17_10): ...   # mark-done sonrası GET'te o ödev yok, süren blok aynı
def test_basla_iki_kez_idempotent(api): ...                    # ikinci POST 200, durum tek "suruyor", basla zamanı değişmez
def test_bitti_tamamlandi_yaptim_yazar(api): ...               # homework_student_done.json'da anahtar var
def test_bitti_tamamlanmadi_ek_parca(api): ...                 # yeni 10 dk'lık parça sıradaki
def test_simdi_degil_ikinci_kez_409(api): ...                  # gövde "Bu bloğu bir kez erteledin."
def test_aksam_yok_ogrenci_403(api_ogrenci): ...
def test_kayit_ve_kalibrasyon(tmp_path): ...                   # 3 kayıt gerçek=2×tahmin → 2.0; 1 kayıt → 1.0
def test_bayrak_kapali_404(api): ...
def test_okuyucu_reddedilir(api_okuyucu): ...                  # default-deny
```
- [ ] **Step 2: Run** `DASHBOARD_SECRET_KEY=t .venv/bin/python -m pytest tests/test_aksam_plani_api.py -q` → FAIL.
- [ ] **Step 3: Implement.** Her dokunuş bir `CalismaKayitlari` satırı yazar (`{gun, odev_anahtari, ders, tahmin_dk, basla, bitti, durum}`); kalibrasyon yalnız `bitti` satırlarından. Yeni dosyalar BM25 hariç listesine.
- [ ] **Step 4: Run** → PASS; `tests/test_dashboard_api.py` ve `tests/test_sebit_pasif.py` hâlâ PASS.
- [ ] **Step 5: Commit** — `feat(aksam): plan durumu, çalışma kayıtları ve plan uçları`

---

### Task 6: Tahminleri senkronda ısıt

**Files:**
- Modify: `src/run_sync.py` (`_tahmin_isitma_adimi`, sınav adımından hemen sonra), `tests/conftest.py`
- Test: `tests/test_run_sync_tahmin.py`

**Interfaces:**
- Consumes: Task 3 `TahminDeposu.isit`, Task 4 `planlanacak`.
- Produces: `_tahmin_isitma_adimi(baslangic: float) -> dict` — `TEDY_AKSAM_PLANI` kapalıyken `{"atlandi": "bayrak"}`; bütçe `min(30, baslangic + 600 - 150 - now)`, 5 s altında atlanır; asla istisna fırlatmaz (`{"hata": …}`); `health.json`'a `aksam_plani` alanı: `{isitilan, yedekte, harcanan_usd, hata}`.

- [ ] **Step 1: Failing tests** — bayrak kapalıyken atlar; sahte depo ile `isit` bir kez çağrılır; `isit` istisna fırlatırsa adım `{"hata": ...}` döner ve senkron sürer; `conftest` gerçek adımı varsayılan olarak sahteyle değiştirir (`_canli_tahmin_isitma_yok`).
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS (+ `tests/test_run_sync*.py`).
- [ ] **Step 5: Commit** — `feat(aksam): senkron içinde ödev tahminlerini ısıt`

---

### Task 7: Bugün'de plan kartı

**Files:**
- Create: `dashboard/src/utils/aksamPlani.ts`, `dashboard/src/hooks/useAksamPlani.ts`, `dashboard/src/components/AksamPlani.tsx`, `AksamPlani.scss`, `dashboard/tests/aksamPlani.test.ts`, `dashboard/tests/e2e/aksam-plani.spec.ts`
- Modify: `dashboard/src/components/TodaySchedule.tsx`, `dashboard/tests/e2e/_bugun-fixtures.ts` (plan taklidi), görsel/aria tabanları

**Interfaces:**
- Consumes: Task 5 HTTP (`/api/plan/bugun`, `basla`, `bitti`, `simdi-degil`, `odev/<key>/sure`, `aksam-yok`); `utils/odevYaptim.ts` değil — tamamlama sunucuda (Task 5).
- Produces: `kartDurumu(plan: PlanYaniti, simdiMin: number): {tur: 'onizleme'|'calisma'|'mola'|'bekliyor'|'bitti'|'kapali'|'yok', baslik: string, alt: string, kalanDk?: number}` (saf); `useAksamPlani()` → `{plan, iskelet, hata, basla(id), bitti(id, tamamlandi?), simdiDegil(id), sureDuzelt(key, dk), aksamYok(aktif)}`; olay `tedy:plan-guncellendi` (ve `tedy:homework-updated` dinler).

- [ ] **Step 1: Failing unit tests** (`aksamPlani.test.ts`): önizleme metni "Bu akşam 3 iş · 17:00'de başlıyor"; süren blokta `kalanDk` doğru; mola sonrası `tur:'bekliyor'` ve başlık sıradaki adım; `durum:'bitti'` → "Bugünlük bu kadar"; süre metni her zaman "tahmin 20 dk" biçiminde ("tahmin" sözcüğü zorunlu); kopyada yasak ifadeler yok (`/geç kaldın|yetiştiremeyeceksin/` eşleşmez).
- [ ] **Step 2: Run** `npm run test:birim` → FAIL.
- [ ] **Step 3: Implement.** Kart: görünümün tek ders paneli (NextThing'in panel stili, `--ted-subject-*`); başlık şimdiki adım (`heading-04`, sayfanın en büyük metni); altında ders işareti + "tahmin 20 dk" (`Rakamli`); düğmeler Carbon `Button` lg: **Başla** (primary), **Bitti** (primary, süren blokta), **Şimdi değil** (ghost; ertelendiyse yerine metin "Bu bloğu bir kez erteledin."); son parçada "Bitti" → aynı kart içinde soru "Ödevin tamamı bitti mi?" **Evet** / **Biraz kaldı**; mola: "Mola · 5 dk" + kalan; alt satır "Sırada: …"; Carbon `Accordion` "Bu akşamın tamamı" (kapalı); `haber_metni` kartta `helper` tonda; "Yarına kaldı: …" ve "Planda olmayan N eski ödev · İşler'de" tek satır; aile için "Bu akşam plan yok" `Toggle` (yalnız `student === false`). Süre düzeltme: tahmin metnine tıklayınca `NumberInput` (5–120). `TodaySchedule`: bayrak/uç 404 dönerse eski akış aynen; `onizleme` iken NextThing'in yerine önizleme satırı, akış/mola/bekliyor iken NextThing ve "Ayrıca" yerine kart; okul kartı (`.today-now`) 17:00'den önce değişmez. Telefonda her denetim ≥ 44 px; odak kipi yalnız kartı bırakır. Bütün Carbon import/prop'ları `carbon` MCP ile doğrulanır.
- [ ] **Step 4: e2e** (`aksam-plani.spec.ts`, sabit saat + uç taklidi): 16:30 önizleme; 17:05 kart "Başla"→"Bitti"→mola; son parça "Evet" isteği `tamamlandi:true` gönderir; ikinci "Şimdi değil" yerine metin; uç 404 → NextThing görünür; axe + IBM denetimi kartta temiz; 390 px yatay kayma yok.
- [ ] **Step 5: Run** `npm run lint && npm run test:birim && env -u ANTHROPIC_API_KEY npx playwright test aksam-plani bugun-duzen today tasarim-denetimi ibm-erisilebilirlik ekran-4k` → PASS; tabanları `--update-snapshots=all` ile Bugün için yenile, farkı oku.
- [ ] **Step 6: Commit** — `feat(aksam): Bugün'de akşam plan kartı`

---

### Task 8: Asistan araçları

**Files:**
- Modify: `src/assistant_tools.py` (`AKSAM_TOOL = "aksam_plani"`, `PLAN_DEGISTIR_TOOL = "plani_degistir"`, bildirimler, dispatch), `src/assistant_core.py` (runtime'a `plan_kaynagi`/`plan_yazici`; `study_plan`'ın `plan_blocks`'u motordan; `_build_rule_based_plan` silinir), `src/dashboard_api.py` (bağlama), `dashboard/src/asistan/olayEslemesi.ts` (`ARAC_ETIKETI`), sistem istemi yönlendirme satırı
- Test: `tests/test_assistant_aksam_plani.py`, `tests/test_asistan_adim_etiketleri.py` (mevcut), `test_system_prompt_routing_names_every_declared_tool_exactly_once` (mevcut)

**Interfaces:**
- Consumes: Task 5 `bugunku_plan`, `PlanDeposu.degistir`, `TahminDeposu.okur_suresi_yaz`.
- Produces: `aksam_plani` (parametresiz; okunur metin: şimdi, sırada, kalan bloklar saatleriyle, taşınan/sığmayan); `plani_degistir(islem: "sona_al"|"one_al"|"sure"|"yarina_at", odev: str, dakika?: int)` → `ToolOutcome` metni. Kurallar: `sona_al/one_al` blok başına bir kez (Task 4 `ertelenen`); `yarina_at` teslimi yarın olan işte reddedilir ("Bu ödev yarın teslim; bu akşamdan çıkaramam."); `okur=="aile"` iki kuralı da aşar ve kayda `asan: "aile"` yazar. Araçlar yalnız `odev_kaynagi` ve bayrak varken bildirilir. `ARAC_ETIKETI`: `aksam_plani: "Akşam planına bakılıyor"`, `plani_degistir: "Plan düzenleniyor"`.
- `plan_blocks` (eski kart için) motor bloklarından: `{type:"homework", title:"<ders>: <başlık>", day, estimated_minutes, actions:[adim], rationale:"tahmin"}`.

- [ ] **Step 1: Failing tests** — ogrenci `yarina_at` yarın teslimli işte reddedilir, aile kabul edilir; ikinci `sona_al` reddedilir; `sure` okur düzeltmesini yazar ve sonraki `aksam_plani` metni yeni süreyi gösterir; bayrak kapalıyken araçlar bildirilmez; `plan_blocks` motordan gelir ve `Yaptım` işaretli ödevi içermez; etiket testi iki aracı tanır.
- [ ] **Step 2–4:** Run → FAIL → implement → PASS (`tests/test_assistant_*.py -q` tamamı).
- [ ] **Step 5: Commit** — `feat(aksam): asistan planı okur ve Işık'ın isteğiyle düzenler`

---

### Task 9: Bildirim turu ve zamanlayıcı

**Files:**
- Create: `src/aksam_bildirim.py`, `tedy-aksam-plani.service`, `tedy-aksam-plani.timer`, `tests/test_aksam_bildirim.py`
- Modify: `tests/conftest.py` (gerçek gönderici yasak), `src/run_sync.py` health (`aksam_bildirim` durum dosyasını okur)

**Interfaces:**
- Consumes: Task 5 `bugunku_plan`, `PlanDeposu`; `web_push.AbonelikDeposu.kisinin(email)`, `web_push.gonder(abonelik, yuk, vapid)`, `vapid_ayarlari()`; `roles.OGRENCI_EMAILS`; Task 1 `haber_alacaklar`, eşikler.
- Produces: `olaylar(plan: Plan, gunluk: dict, duzen: dict, simdi: datetime) -> list[Olay]` (saf); `@dataclass Olay(tur: Literal["sure_doldu","mola_bitti","baslamadi","takildi","sigmiyor"], alici: Literal["ogrenci","aile"], blok_id: str | None, baslik: str, govde: str)`; `tur(simdi=None, gonderici=web_push.gonder) -> dict`; CLI `python -m src.aksam_bildirim tur`; defter `output/aksam_bildirim_defteri.jsonl` anahtarı `(gun, tur, blok_id, email)`; durum `output/aksam_bildirim_durumu.json` (her tur yazılır).
- Metinler (değişmez kopya):
  - `sure_doldu` (Işık): başlık "Süre doldu", gövde "{ders} için tahmin ettiğin süre bitti. Bitti mi, biraz daha mı?"
  - `mola_bitti` (Işık): "Mola bitti", "Sırada {ders}: {adım}."
  - `baslamadi` (aile): "Işık henüz başlamadı", "Saat {HH:MM}; bu akşamın ilk işi {ders}."
  - `takildi` (aile): "{ders} bloğu uzadı", "Başlayalı {N} dakika oldu, henüz bitti işaretlenmedi."
  - `sigmiyor` (aile): "Bu akşama sığmıyor", "{ders}: {başlık} yarın teslim; plana sığmadı."

- [ ] **Step 1: Failing tests** (sahte gönderici, sabit saat):

```python
def test_kabul_3_baslamadi_tek_sefer(): ...      # 17:15'te Başla yok → aile alıcılarına 1; Işık'a 0; 17:16'da tekrar 0
def test_kabul_4_takildi(): ...                  # 17:00 başla, tahmin 20 → 17:36'da 1 aile bildirimi
def test_sure_doldu_ve_mola_bitti_isik(): ...    # Işık'a blok başına en çok 2
def test_alici_listesi_bos_aileye_yok(): ...
def test_sessiz_saatte_gonderilmez(): ...        # 21:05 → 0
def test_bayrak_kapali_hic_gonderilmez(): ...
def test_aksam_yok_hicbir_sey(): ...
def test_kopya_alarm_dili_yok(): ...             # bütün metinlerde /geç kaldın|yetiştir/ yok
def test_olu_cihaz_silinir(): ...                # gonder → olu → depodan silinir, tur sürer
```
- [ ] **Step 2: Run** `.venv/bin/python -m pytest tests/test_aksam_bildirim.py -q` → FAIL.
- [ ] **Step 3: Implement.** Unit dosyaları `tedy-sinav-uyari.*`'nın kopyası: `OnCalendar=*:*:00`, `Persistent=false`, `TimeoutStartSec=50`, `Environment=TZ=Europe/Istanbul`. Kurulum **yapılmaz** (kullanıcı onayıyla, rollout'ta).
- [ ] **Step 4: Run** → PASS (+ `tests/test_sinav_uyari*.py` hâlâ PASS).
- [ ] **Step 5: Commit** — `feat(aksam): Işık'a ve aileye plan bildirimleri, dakikalık tur`

---

### Task 10: Belgeler

**Files:**
- Modify: `docs/tedy-ui-ux-talimatnamesi.md` (§11'e **S53** "Akşam planında süre tahmini": kural, sapma, gerekçe, sınama; §8.8 Gün Şeridi'ne "Yol" ve 17–19), `docs/frontend-surface-designs.md` (Bugün akşam kipi), `CLAUDE.md` (yeni "Akşam çalışma planı" maddesi: dosyalar, bayraklar, rollout, geri dönüş; "Focus window" maddesi akşam düzenine güncellenir; unit kurulum komutları Deployment'a)
- Test: `tests/test_pano_talimatname_borclari.py` (S53 adlandırıldı), `.venv/bin/python -m pytest -q` tamamı

- [ ] **Step 1:** Belgeleri yaz; S53 metni NextThing'in süre yasağının değişmediğini söyler.
- [ ] **Step 2: Run** tam süit: `DASHBOARD_SECRET_KEY=t .venv/bin/python -m pytest -q` ve `cd dashboard && npm run lint && npm run test:birim` → PASS.
- [ ] **Step 3: Commit** — `docs(aksam): S53, Gün Şeridi ve CLAUDE.md`

---

## Rollout (uygulama sonrası, her adım kullanıcı onayıyla)

1. Birleştir, derle, `ted-dashboard` yeniden başlat; `.env`'e `TEDY_AKSAM_PLANI=1` (`env_prep ayarla`). Kart açılır, bildirim yok.
2. Bir hafta: `output/calisma_kayitlari.jsonl` ile tahmin/gerçek oranı okunur, aileye özet.
3. Profil'de "Haber alacaklar" aileyle doldurulur; Işık'ın iPhone/iPad'inde TEDY ana ekrana eklenip bildirim açılır.
4. `TEDY_AKSAM_BILDIRIM=1`, unit'ler kurulur (`install … && systemctl --user enable --now tedy-aksam-plani.timer`).
5. Geri dönüş: timer `disable --now`, bayraklar `0`, `ted-dashboard` yeniden başlat — Bugün eski akışa döner.
