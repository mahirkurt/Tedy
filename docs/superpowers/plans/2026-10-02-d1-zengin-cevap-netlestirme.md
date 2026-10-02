# D1 — Zengin cevap ve netleştirme Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Asistanın cevaplarına beş blok türü (kavram, örnek, adımlar, sonuç, hata), KaTeX ile çizilen formüller ve kaydırılabilir tablolar eklemek. Ayrıca soru belirsiz olduğunda asistanın seçenek düğmeleriyle netleştirme sorabilmesini sağlayan `netlestir` aracını eklemek.

**Architecture:** Model Markdown yazmaya devam eder. Panonun `utils/markdown.tsx` sohbet işleyicisi `:::ad … :::` bloklarını, `$…$`/`$$…$$` formüllerini ve boru tablolarını React öğelerine çevirir. KaTeX yalnız formül içeren bir cevapta dinamik `import()` ile yüklenir. `netlestir`, B1'in olay mekanizmasını kullanan sonlandırıcı bir araçtır:
- yalnız başına çağrıldığı turda döngüyü bitirir;
- `clarify` SSE olayını ve `netlestirme` yük alanını üretir.

`mod_onerisi` bayrağı `etkilesimli` adını alır: `/plan` ve `/v1`'de hem `mod_oner` hem `netlestir` bildirilmez.

**Tech Stack:** Python 3.12 (Flask, Anthropic SDK 1.x, pytest), React 19 + Vite + Carbon v11, KaTeX 0.16 (yeni bağımlılık), Playwright.

**Spec:** `docs/superpowers/specs/2026-10-02-asistan-zengin-cevap-yukleme-onyuz-design.md` — bölüm "D1 — Zengin cevap ve netleştirme".

## Global Constraints

- Çalışma ağacı: yalnız `/mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-zengin`, dal `feat/asistan-zengin`. Her commit'ten önce `test "$(git branch --show-current)" = feat/asistan-zengin && echo dal-dogru` → `dal-dogru`. Ana checkout'a yazma, orada git komutu koşma.
- D3a'nın tamamlanmış olması gerekir (`--ted-subject-panel`, `--ted-subject-panel-border` CSS değişkenleri bu plana girdi).
- Python testleri: `DASHBOARD_SECRET_KEY=yerel-test .venv/bin/python -m pytest -q -p no:cacheprovider …`. Tam paket: arkadan, log sonuna `EXIT=$?` yazarak başlat; önde `timeout 590 bash -c 'until grep -q "^EXIT=" LOG; do sleep 15; done'` ile bekle; bekleyen koşu varken tur bitirme.
- Testler ücretli API'ye ve ağa çıkmaz (`tests/conftest.py` `ANTHROPIC_API_KEY`'i siler). Sahte istemciler mevcut testlerdeki desenle yazılır.
- Pano: `npm run lint` temiz; `npm run build; echo "build çıkış: $?"` (borusuz); her Playwright koşusundan önce build. Playwright: `env -u ANTHROPIC_API_KEY TEDY_E2E_PORT=8301 DASHBOARD_SECRET_KEY=yerel-test npx playwright test …`. Soru gönderen her e2e testi hem `**/api/assistant/stream` hem `**/api/assistant/chat` uçlarını kendisi cevaplar (CLAUDE.md).
- Görsel taban çizgisi yalnız fark okunduktan sonra (Read ile `*-actual/-expected/-diff.png`), sonra `--update-snapshots`. Yeni PNG'lerin her birini Read ile aç ve raporda tek satırla betimle.
- Carbon token kuralları: boşluk/tip/hareket Carbon token'ı; renk rol token'ı ya da `--ted-subject-*`; el yazısı hex, alfa, gradyan, `filter`, `color-mix` yok.
- Temel sistem bloğu her modda bayt bayt aynı kalır (`tests/test_assistant_ogretmen_modu.py`).
- "## Hangi araca ne zaman uzanırsın" bölümünde her araç tam bir kez geçer (`tests/test_assistant_core.py`). `netlestir` bu bölüme girmez; kendi bölümü olur.
- Kullanıcıya dönük metin Türkçe. Kod yorumları İngilizce, çevredeki "measured …" üslubunda. `\u`/`\x` kaçışı yazma.
- Staging adla; `git add -A` yok; çıplak `git stash` yok; `git push` yok. Commit mesajları Türkçe, son satır `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Dosya haritası

| Dosya | Değişim | Sorumluluk |
|---|---|---|
| `src/assistant_tools.py` | değişir | `NETLESTIR_TOOL`, `SONLANDIRICI_ARACLAR`, bildirim, `_dispatch_netlestir`; `mod_onerisi` → `etkilesimli` |
| `src/assistant_core.py` | değişir | döngüde sonlandırıcı araç; `netlestirme` yükü; `## Biçim` ve `## Netleştirme` istemi; `etkilesimli` |
| `src/dashboard_api.py` | değişir | `mod_onerisi=` çağrıları → `etkilesimli=` (varsa) |
| `tests/test_assistant_netlestir.py` | yeni | araç, döngü, yük, akış |
| `tests/test_assistant_bicim_istemi.py` | yeni | istem kuralları |
| `tests/test_assistant_ogretmen_*.py` | değişir | `mod_onerisi` → `etkilesimli` |
| `dashboard/package.json`, `package-lock.json` | değişir | `katex` |
| `dashboard/src/utils/markdown.tsx` | değişir | `kutu` bloğu, formül, tablo bölgesi |
| `dashboard/src/components/Formul.tsx` | yeni | KaTeX'i tembel yükleyip çizen bileşen |
| `dashboard/src/components/NetlestirmeSecenekleri.tsx` | yeni | seçenek düğmeleri |
| `dashboard/src/components/AssistantChat.tsx`, `.scss` | değişir | `clarify` olayı, mesaj alanı, düğmeler, blok stilleri |
| `dashboard/src/types.ts` | değişir | `Netlestirme`, `AssistantResponse.netlestirme` |
| `dashboard/tests/e2e/asistan-zengin-cevap.spec.ts` | yeni | bloklar, formül, tablo, ekran görüntüleri, a11y |
| `dashboard/tests/e2e/asistan-netlestirme.spec.ts` | yeni | düğmeler, akış ve /chat |
| `CLAUDE.md` | değişir | "How an answer is set" maddesi |

---

### Task 1: `netlestir` aracı ve sonlandırıcı döngü

**Files:**
- Modify: `src/assistant_tools.py` (sabitler ~satır 446-455; `declarations` ~1621; `_ogretmen_bildirimleri` ~1706; `dispatch` ~1792; `_dispatch_mod_oner` ~1965'in yanına yeni metot)
- Modify: `src/assistant_core.py` (`ClaudeClient.chat_with_tools` ~509-690; `chat()` imzası ~2387, yük ~2481; `chat_events` ~2555; `/plan` ~2719 ve `/v1` ~2768 çağrıları)
- Modify: `mod_onerisi` geçen bütün test ve kaynak dosyaları (yeniden adlandırma)
- Test: `tests/test_assistant_netlestir.py`

**Interfaces:**
- Produces:
  - `assistant_tools.NETLESTIR_TOOL = "netlestir"`, `assistant_tools.SONLANDIRICI_ARACLAR = {NETLESTIR_TOOL}`, `NETLESTIR_SORU_SINIRI = 140`, `NETLESTIR_SECENEK_SINIRI = 60`.
  - `McpRegistry.declarations(okur, ogretmen=GENEL, etkilesimli=True)` ve `McpRegistry.dispatch(..., etkilesimli=True, ...)` (eski `mod_onerisi` adı kalkar).
  - Başarılı `netlestir` sonucu `ToolOutcome(ok=True, text="Seçenekler okura gösterildi.", olay={"event": "clarify", "soru": str, "secenekler": list[str]})`.
  - `AssistantRuntime.chat(..., etkilesimli: bool = True)`; yükte `"netlestirme": {"soru", "secenekler"} | None`.
  - SSE: `event: clarify`, `data: {"event":"clarify","soru":…,"secenekler":[…]}`.

- [ ] **Step 1: `mod_onerisi`'yi `etkilesimli` olarak yeniden adlandır (davranış aynı)**

```bash
grep -rln "mod_onerisi" src tests | tee /tmp/d1-yeniden-ad.txt
xargs sed -i 's/mod_onerisi/etkilesimli/g' < /tmp/d1-yeniden-ad.txt
grep -rn "mod_onerisi" src tests || echo "kalmadı"
DASHBOARD_SECRET_KEY=yerel-test .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_assistant_ogretmen_modu.py tests/test_assistant_ogretmen_api.py tests/test_assistant_ogretmen_araclari.py
```

Expected: "kalmadı" ve testler PASS. Yorumlarda "mod_onerisi=False (/v1, /plan) withholds mod_oner" gibi geçen cümleleri "etkilesimli=False (/v1, /plan) withholds the interactive tools (mod_oner, netlestir)" anlamına getir.

- [ ] **Step 2: Başarısız testleri yaz**

`tests/test_assistant_netlestir.py`. Sahte Claude yanıtları için `tests/test_assistant_ogretmen_modu.py`'deki `_Sahte` / `_SahteAkis` yardımcılarını oku ve aynı biçimde yerel yardımcılar yaz: içerik blokları `type` / `text` / `id` / `name` / `input` öznitelikli `SimpleNamespace`, `usage` alanı. Yardımcıyı import etme; bu dosyaya kopyala.

```python
"""netlestir (D1, spec "netlestir aracı"): a terminating, interactive-only tool.

- Declared only when etkilesimli is true (/stream, /chat), in every mode.
- A valid call alone in its round ends the loop: answer = round text + question;
  the clarify event carries the question and 2–4 options.
- Called beside another tool it is refused (not dispatched) and the loop goes on.
- Invalid arguments are a HATA result; the loop goes on.
"""
from types import SimpleNamespace

import pytest

from src import assistant_skills
from src.assistant_core import ClaudeClient
from src.assistant_tools import (NETLESTIR_TOOL, SONLANDIRICI_ARACLAR, McpRegistry,
                                 ToolOutcome)

GECERLI = {"soru": "Kesirlerin hangi yönüyle başlayalım?",
           "secenekler": ["Karşılaştırma", "Toplama", "Ondalık gösterim"]}


def _metin(t):
    return SimpleNamespace(type="text", text=t)


def _arac(ad, girdi, kimlik="tu_1"):
    return SimpleNamespace(type="tool_use", id=kimlik, name=ad, input=girdi)


def _yanit(*bloklar):
    return SimpleNamespace(content=list(bloklar), stop_reason="tool_use",
                           usage=SimpleNamespace(input_tokens=1, output_tokens=1,
                                                 cache_read_input_tokens=0,
                                                 cache_creation_input_tokens=0))


class _Senaryo:
    """ClaudeClient._request stand-in: returns scripted responses in order."""

    def __init__(self, *yanitlar):
        self.yanitlar = list(yanitlar)
        self.istekler = []

    def __call__(self, system, turns, tier, usage, tools=None, tool_choice=None, on_delta=None):
        self.istekler.append({"turns": [dict(t) for t in turns], "tool_choice": tool_choice})
        yanit = self.yanitlar.pop(0)
        if on_delta is not None:
            for b in yanit.content:
                if getattr(b, "type", "") == "text" and b.text:
                    on_delta(b.text)
        return yanit


def _istemci(monkeypatch, senaryo):
    c = ClaudeClient.__new__(ClaudeClient)
    c.available = True
    monkeypatch.setattr(c, "_request", senaryo, raising=False)
    return c


def _dispatch(ad, args):
    if ad == NETLESTIR_TOOL:
        return McpRegistry._dispatch_netlestir(None, args)
    return ToolOutcome(ok=True, text="kayıt", citations=[])


DECL = [{"name": NETLESTIR_TOOL, "parameters": {"type": "object"}},
        {"name": "odev_listesi", "parameters": {"type": "object"}}]


def test_netlestir_sonlandirici_kumede():
    assert SONLANDIRICI_ARACLAR == {NETLESTIR_TOOL}


@pytest.mark.parametrize("args,hata", [
    ({}, "soru"),
    ({"soru": "x" * 141, "secenekler": ["a", "b"]}, "soru"),
    ({"soru": "Hangisi?", "secenekler": ["a"]}, "secenek"),
    ({"soru": "Hangisi?", "secenekler": ["a", "b", "c", "d", "e"]}, "secenek"),
    ({"soru": "Hangisi?", "secenekler": ["a", ""]}, "secenek"),
    ({"soru": "Hangisi?", "secenekler": ["a", "x" * 61]}, "secenek"),
    ({"soru": "Hangisi?", "secenekler": ["a", "A"]}, "secenek"),
    ({"soru": "Hangisi?", "secenekler": "a,b"}, "secenek"),
])
def test_gecersiz_arguman_hata(args, hata):
    sonuc = McpRegistry._dispatch_netlestir(None, args)
    assert not sonuc.ok and hata in sonuc.error.lower()


def test_gecerli_cagri_olay_uretir():
    sonuc = McpRegistry._dispatch_netlestir(None, dict(GECERLI))
    assert sonuc.ok
    assert sonuc.olay == {"event": "clarify", **GECERLI}


def test_yalniz_netlestir_dongüyu_bitirir(monkeypatch):
    s = _Senaryo(_yanit(_metin("Önce bir şey sorayım."), _arac(NETLESTIR_TOOL, dict(GECERLI))))
    c = _istemci(monkeypatch, s)
    akis, sifirlama = [], []
    out = c.chat_with_tools(messages=[{"role": "user", "content": "kesirleri anlat"}],
                            declarations=DECL, dispatch=_dispatch, tier="medium",
                            on_delta=akis.append, on_reset=lambda: sifirlama.append(1))
    assert len(s.istekler) == 1
    assert out.text == "Önce bir şey sorayım.\n\n" + GECERLI["soru"]
    assert "".join(akis) == out.text
    assert not sifirlama
    assert out.olaylar == [{"event": "clarify", **GECERLI}]


def test_metinsiz_netlestir_yalniz_soruyu_doner(monkeypatch):
    s = _Senaryo(_yanit(_arac(NETLESTIR_TOOL, dict(GECERLI))))
    out = _istemci(monkeypatch, s).chat_with_tools(
        messages=[{"role": "user", "content": "kesir"}], declarations=DECL,
        dispatch=_dispatch, tier="medium")
    assert out.text == GECERLI["soru"]
    assert len(s.istekler) == 1


def test_baska_aracla_birlikte_reddedilir_dongu_surer(monkeypatch):
    s = _Senaryo(
        _yanit(_arac(NETLESTIR_TOOL, dict(GECERLI), "tu_1"), _arac("odev_listesi", {}, "tu_2")),
        _yanit(_metin("Cevap.")),
    )
    cagrilan = []

    def izle(ad, args):
        cagrilan.append(ad)
        return _dispatch(ad, args)

    out = _istemci(monkeypatch, s).chat_with_tools(
        messages=[{"role": "user", "content": "x"}], declarations=DECL, dispatch=izle,
        tier="medium")
    assert cagrilan == ["odev_listesi"]
    assert out.text == "Cevap."
    assert out.olaylar == []
    sonuclar = s.istekler[1]["turns"][-1]["content"]
    ret = next(r for r in sonuclar if r["tool_use_id"] == "tu_1")
    assert ret["is_error"] and "yalnız başına" in str(ret["content"])


def test_gecersiz_netlestir_hata_alir_dongu_surer(monkeypatch):
    s = _Senaryo(_yanit(_arac(NETLESTIR_TOOL, {"soru": "?", "secenekler": ["a"]})),
                 _yanit(_metin("Düz cevap.")))
    out = _istemci(monkeypatch, s).chat_with_tools(
        messages=[{"role": "user", "content": "x"}], declarations=DECL,
        dispatch=_dispatch, tier="medium")
    assert out.text == "Düz cevap."
    assert out.olaylar == []


def test_etkilesimsiz_bildirilmez_ve_reddedilir(tmp_path):
    reg = McpRegistry.__new__(McpRegistry)
    reg.skills = {}
    adlar = [d["name"] for d in reg._ogretmen_bildirimleri(assistant_skills.GENEL, etkilesimli=False)]
    assert NETLESTIR_TOOL not in adlar
    adlar = [d["name"] for d in reg._ogretmen_bildirimleri(assistant_skills.GENEL, etkilesimli=True)]
    assert NETLESTIR_TOOL in adlar
```

`McpRegistry`'nin `__new__` ile kurulup `_ogretmen_bildirimleri`'nin çalışabilmesi için gereken alanları mevcut koddan oku. `skills` dışında bir alan gerekiyorsa testte onu da ver. Gerekirse `_ogretmen_bildirimleri` yerine `declarations()` kullan. Yük (`chat()`) ve akış (`chat_events`) için iki test daha ekle; `tests/test_assistant_ogretmen_modu.py`'deki `mode_suggestion` yük ve akış testlerini model al:

- `chat()` sonucu `payload["netlestirme"] == GECERLI`;
- `chat_events` akışında `{"event": "clarify", **GECERLI}` olayı tam bir kez çıkar.

- [ ] **Step 3: Başarısız olduklarını gör**

Run: `DASHBOARD_SECRET_KEY=yerel-test .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_assistant_netlestir.py`
Expected: FAIL. `ImportError: cannot import name 'NETLESTIR_TOOL'`.

- [ ] **Step 4: Aracı ekle**

`src/assistant_tools.py`, `OLAY_ARACLARI = {MOD_ONER_TOOL}` satırının hemen altına:

```python
# netlestir (D1): a clarifying question with 2–4 options for the reader to tap.
# A *terminating* tool — alone in its round it ends the answer (the question is
# the answer); beside another tool it is refused. Interactive surfaces only
# (/stream, /chat): /plan and /v1 have no buttons to press.
NETLESTIR_TOOL = "netlestir"
SONLANDIRICI_ARACLAR = {NETLESTIR_TOOL}
NETLESTIR_SORU_SINIRI = 140
NETLESTIR_SECENEK_SINIRI = 60
```

`_ogretmen_bildirimleri(self, ogretmen, etkilesimli=True)` dönüşüne, mod araçlarından **önce** (mod aracı listenin sonunda kalsın diye; B1'in önbellek kuralı) şunu ekle. Yalnız `etkilesimli` doğruysa:

```python
{
    "name": NETLESTIR_TOOL,
    "description": (
        "Soru birden çok anlamlı yöne gidebiliyorsa okura 2–4 kısa seçenek sun; okur birine "
        "dokununca soru o yönde sürer. Soru konuşmadan anlaşılıyorsa çağırma. Bu turda başka "
        "araç çağırma: netlestir çağrıldığında cevabın biter ve soru okura gösterilir."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "soru": {"type": "string", "maxLength": NETLESTIR_SORU_SINIRI,
                     "description": "Okura sorulacak tek kısa soru."},
            "secenekler": {"type": "array", "minItems": 2, "maxItems": 4,
                           "items": {"type": "string", "maxLength": NETLESTIR_SECENEK_SINIRI},
                           "description": "2–4 kısa seçenek; 'Başka bir şey' ekleme, arayüz ekler."},
        },
        "required": ["soru", "secenekler"],
    },
}
```

Mevcut kodda `_ogretmen_bildirimleri` mod aracını hangi sırayla eklediğine bak. Hedef sıra: önce `netlestir`, sonra mod aracı (`mod_oner` ya da `skill_kaynagi`). `tests/test_assistant_ogretmen_modu.py`'deki "mod araçları listenin sonunda" testi yeşil kalmalı.

`dispatch()` içinde `if name == MOD_ONER_TOOL:` satırından önce:

```python
        if name == NETLESTIR_TOOL:
            if not etkilesimli:
                return ToolOutcome(ok=False, error="netlestir bu istekte kapalı.")
            return self._dispatch_netlestir(args or {})
```

`_dispatch_mod_oner`'in yanına:

```python
    def _dispatch_netlestir(self, args: dict[str, Any]) -> ToolOutcome:
        soru = args.get("soru")
        if not isinstance(soru, str) or not soru.strip() \
                or len(soru.strip()) > NETLESTIR_SORU_SINIRI:
            return ToolOutcome(ok=False, error=(
                f"soru 1–{NETLESTIR_SORU_SINIRI} karakterlik bir metin olmalı."))
        secenekler = args.get("secenekler")
        if not isinstance(secenekler, list) or not 2 <= len(secenekler) <= 4:
            return ToolOutcome(ok=False, error="secenekler 2–4 öğelik bir liste olmalı.")
        temiz: list[str] = []
        for s in secenekler:
            if not isinstance(s, str) or not s.strip() \
                    or len(s.strip()) > NETLESTIR_SECENEK_SINIRI:
                return ToolOutcome(ok=False, error=(
                    f"her secenek 1–{NETLESTIR_SECENEK_SINIRI} karakterlik bir metin olmalı."))
            if turkce_kucult_katla(s.strip()) in {turkce_kucult_katla(t) for t in temiz}:
                return ToolOutcome(ok=False, error="secenekler birbirinin aynı olmamalı.")
            temiz.append(s.strip())
        return ToolOutcome(ok=True, text="Seçenekler okura gösterildi.", citations=[],
                           olay={"event": "clarify", "soru": soru.strip(), "secenekler": temiz})
```

`turkce_kucult_katla`'nın gerçek yerini `grep -rn "def turkce_kucult_katla" src` ile bul ve oradan import et. `ToolOutcome`'un `citations` alanı zorunlu değilse argümanı kaldır.

- [ ] **Step 5: Döngüde sonlandırıcı davranış**

`src/assistant_core.py`, `chat_with_tools` içinde `from src.assistant_tools import OLAY_ARACLARI, ToolOutcome` satırını `from src.assistant_tools import OLAY_ARACLARI, SONLANDIRICI_ARACLAR, ToolOutcome` yap.

`son_tur = ...` hesabından hemen önce:

```python
            # netlestir alone in its round ends the answer (D1); its text is
            # kept, not reset, because the question continues it.
            sonlandirici = (len(uses) == 1
                            and getattr(uses[0], "name", "") in SONLANDIRICI_ARACLAR)
```

`elif round_text:` dalını `elif round_text and not sonlandirici:` yap. Bu sayede yalnız `netlestir` çağıran turun metni sıfırlanmaz.

Çağrı döngüsünde (`for use in uses:`), bütçe denetiminden sonra ve `raw = use.input`'tan önce:

```python
                if getattr(use, "name", "") in SONLANDIRICI_ARACLAR and len(uses) > 1:
                    # Refused, not run: the question would end the answer while
                    # the other call's result is still owed to the model.
                    results.append({"type": "tool_result", "tool_use_id": use.id,
                                    "is_error": True,
                                    "content": "HATA: netlestir yalnız başına çağrılır; bu turda "
                                               "başka araç da çağırdın. Önce gerekeni bitir."})
                    out.tool_calls.append({"name": use.name, "ms": 0, "ok": False})
                    continue
```

Aynı döngüde, `outcome` hesaplandıktan ve `out.tool_calls.append(...)` satırından sonra:

```python
                if sonlandirici and outcome.ok and outcome.olay:
                    out.olaylar.append(dict(outcome.olay))
                    soru = str(outcome.olay.get("soru", ""))
                    onceki = self._birlestir(kept_text, round_text)
                    if on_delta is not None:
                        on_delta(("\n\n" if onceki else "") + soru)
                    out.text = self._birlestir(onceki, soru)
                    return out
```

`sonlandirici` doğru ama çağrı başarısızsa (geçersiz argüman) normal yol devam eder: `HATA:` sonucu modele gider ve döngü sürer. O turun metni sıfırlanmamıştı. Bu durumda sıfırlamayı burada yap; böylece taslak, sonraki turun cevabıyla karışmaz:

```python
                if sonlandirici and not outcome.ok:
                    if round_text and on_reset is not None:
                        on_reset()
                    kept_text = ""
```

`_birlestir(a, b)`'nin boş bir tarafı nasıl ele aldığını oku. Test, `"Önce bir şey sorayım.\n\n" + soru` bekliyor; ayırıcı bundan farklıysa testi değil kodu ona uydur.

- [ ] **Step 6: Yük ve akış**

`chat()` içinde `"mode_suggestion": next(...)` girdisinin altına:

```python
            # netlestir's question and options (D1); the stream sends the same as `clarify`.
            "netlestirme": next(
                ({k: v for k, v in o.items() if k != "event"} for o in loop.olaylar
                 if o.get("event") == "clarify"), None),
```

`chat_events`'teki `announcing` sarmalayıcısı `outcome.olay`'ı zaten olay adıyla kuyruğa koyuyor. `clarify` olayının SSE'ye `event: clarify` olarak çıktığını Step 2'deki akış testiyle doğrula. `/plan` (~2719) ve `/v1` (~2768) çağrılarının `etkilesimli=False` taşıdığını denetle (Step 1'deki yeniden adlandırmadan sonra).

- [ ] **Step 7: Testleri koş**

Run: `DASHBOARD_SECRET_KEY=yerel-test .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_assistant_netlestir.py tests/test_assistant_ogretmen_modu.py tests/test_assistant_ogretmen_api.py tests/test_assistant_core.py`
Expected: PASS.

Ardından tam paketi arkadan koş (Global Constraints'teki biçimle). Beklenen: `EXIT=0`.

- [ ] **Step 8: Commit**

```bash
test "$(git branch --show-current)" = feat/asistan-zengin && echo dal-dogru
git add src/assistant_tools.py src/assistant_core.py tests/test_assistant_netlestir.py
xargs git add < /tmp/d1-yeniden-ad.txt
git status --short
git commit -m "D1: netlestir aracı, sonlandırıcı döngü ve etkilesimli bayrağı

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: İstem — zengin biçim ve netleştirme kuralları

**Files:**
- Modify: `src/assistant_core.py` (`SYSTEM_PROMPT` içindeki `## Biçim` bölümü, ~satır 2303-2325)
- Test: `tests/test_assistant_bicim_istemi.py`

**Interfaces:**
- Consumes: Task 1 (`netlestir` adı).
- Produces: istemde `## Biçim` (blok sözlüğü, formül, tablo) ve `## Netleştirme` bölümleri. Pano Task 3'te tam bu sözlüğü (`kavram`, `ornek`, `adimlar`, `sonuc`, `hata`) işler.

- [ ] **Step 1: Başarısız testi yaz**

`tests/test_assistant_bicim_istemi.py`:

```python
"""The answer's format rules (D1): the closed block vocabulary, math and tables,
and when to clarify. The dashboard renders exactly these names; a block the
prompt teaches and the renderer does not know would print as plain text."""
from src.assistant_core import AssistantRuntime

P = AssistantRuntime.SYSTEM_PROMPT
BICIM = P.split("## Biçim\n", 1)[1].split("\n## ", 1)[0]


def test_bes_blok_adi_ogretilir():
    for ad in ("kavram", "ornek", "adimlar", "sonuc", "hata"):
        assert f":::{ad}" in BICIM, ad
    assert "\n:::\n" in BICIM or "`:::`" in BICIM  # kapanış satırı öğretilir


def test_formul_ve_ondalik_virgul():
    assert "$" in BICIM and "$$" in BICIM
    assert "{,}" in BICIM


def test_tablo_artik_serbest_ama_sinirli():
    assert "Tablo" in BICIM or "tablo" in BICIM
    assert "4 sütun" in BICIM and "6 satır" in BICIM
    assert "Tablo, yatay çizgi" not in BICIM  # eski yasak cümlesi gitti


def test_simdi_ve_not_korunur():
    assert "**Şimdi:**" in BICIM and "**Not:**" in BICIM


def test_netlestirme_bolumu():
    bolum = P.split("## Netleştirme\n", 1)[1].split("\n## ", 1)[0]
    assert "`netlestir`" in bolum
    assert "iki" in bolum  # art arda ikiden fazla netleştirme sorma
```

- [ ] **Step 2: Başarısız olduğunu gör**

Run: `DASHBOARD_SECRET_KEY=yerel-test .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_assistant_bicim_istemi.py`
Expected: FAIL.

- [ ] **Step 3: `## Biçim`'in son maddesini değiştir, yeni maddeleri ve `## Netleştirme` bölümünü ekle**

`"- Tablo, yatay çizgi (---), alıntı bloğu ve emoji kullanma.\n\n"` satırını şununla değiştir:

```python
        "- Bloklar: içerik gerektiriyorsa şu beş bloktan birini kullan; başka ad uydurma. Blok "
        "`:::ad` satırıyla açılır, tek başına `:::` satırıyla kapanır; iç içe blok yok.\n"
        "  - `:::kavram` — bir tanım ya da kural (bir iki cümle).\n"
        "  - `:::ornek` — somut bir örnek.\n"
        "  - `:::adimlar` — çözüm ya da yöntem adımları; içi numaralı liste (1. 2. 3.).\n"
        "  - `:::sonuc` — bir hesabın ya da karşılaştırmanın sonucu (tek satır).\n"
        "  - `:::hata` — sık yapılan bir yanlış ve doğrusu.\n"
        "  Bir cevapta en çok bir `sonuc` ve bir `hata` kullan. Kısa bir cevapta blok kullanma.\n"
        "- Matematik: her sayısal ifade, kesir, üs ve denklem `$…$` içinde (ör. `$\\frac{3}{4}$`, "
        "`$2^3$`); ayrı satırdaki uzun ifade `$$…$$`. Ondalık virgülü `0{,}75` diye yaz. Para "
        "ya da düz metindeki dolar işaretini `\\$` diye yaz.\n"
        "- Tablo yalnız karşılaştırma için: Markdown boru tablosu, en çok 4 sütun ve 6 satır. "
        "Yatay çizgi (---), alıntı bloğu ve emoji kullanma.\n\n"

        "## Netleştirme\n"
        "- Soru birden çok anlamlı yöne gidebiliyorsa (ör. 'kesirleri anlat': karşılaştırma mı, "
        "toplama mı, ondalık gösterim mi?) cevaplamadan önce `netlestir` ile tek kısa soru ve "
        "2–4 seçenek sun. Arayüz 'Başka bir şey' seçeneğini kendisi ekler.\n"
        "- Soru konuşmadan anlaşılıyorsa sorma. Art arda ikiden fazla netleştirme sorma; ikinci "
        "netleştirmeden sonra en olası anlamı seçip cevapla ve bunu bir cümleyle söyle.\n"
        "- `netlestir`'i başka bir araçla aynı turda çağırma; çağırdığında cevabın biter.\n\n"
```

Python dizesinde `\\frac` ve `\\$` çift ters bölüyle yazılır; çıktıda tek ters bölü görünür. Bu `\u`/`\x` kaçışı değildir, yasağa girmez.

- [ ] **Step 4: Testleri koş**

Run: `DASHBOARD_SECRET_KEY=yerel-test .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_assistant_bicim_istemi.py tests/test_assistant_core.py tests/test_assistant_ogretmen_modu.py`
Expected: PASS. `test_assistant_core.py`'deki `## Biçim` ve yönlendirme sayım testleri yeşil kalır, çünkü `netlestir` "Hangi araca" bölümünde değildir.

- [ ] **Step 5: Commit**

```bash
test "$(git branch --show-current)" = feat/asistan-zengin && echo dal-dogru
git add src/assistant_core.py tests/test_assistant_bicim_istemi.py
git commit -m "D1: istemde blok sözlüğü, formül, tablo ve netleştirme kuralları

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Panoda bloklar, formül ve tablo

**Files:**
- Modify: `dashboard/package.json`, `dashboard/package-lock.json` (`npm install katex@^0.16`)
- Create: `dashboard/src/components/Formul.tsx`
- Modify: `dashboard/src/utils/markdown.tsx` (`Block` türü ~satır 20-26, `parseBlocks` ~40-178, `INLINE_RE`/`renderInline` ~234-316, `renderSohbet` ~329-412)
- Modify: `dashboard/src/components/AssistantChat.scss` (sona ekle)
- Test: `dashboard/tests/e2e/asistan-zengin-cevap.spec.ts`

**Interfaces:**
- Consumes: Task 2'nin blok adları; D3a'nın `--ted-subject-panel`, `--ted-subject-panel-border`, `--ted-subject-accent`, `--ted-subject-text`.
- Produces:
  - `Block`'a `{ kind: 'kutu'; ad: KutuAdi; children: Block[] }` ve `{ kind: 'formul'; tex: string }`; `type KutuAdi = 'kavram' | 'ornek' | 'adimlar' | 'sonuc' | 'hata'`.
  - `Formul` bileşeni: `default function Formul({ tex, blok }: { tex: string; blok: boolean })`.
  - CSS sınıfları: `.ac-kutu`, `.ac-kutu--<ad>`, `.ac-kutu__etiket`, `.ac-adimlar`, `.ac-adim`, `.ac-adim__no`, `.ac-formul`, `.ac-md__table-wrap`.

- [ ] **Step 1: Başarısız e2e testini yaz**

`dashboard/tests/e2e/asistan-zengin-cevap.spec.ts`. Mevcut `asistan-cevap-bicimi.spec.ts`'yi oku ve onun cevap yerleştirme desenini kullan: sabit yanıt hem `/stream` hem `/chat` ile verilir, sayfa `sabitAc` ile açılır, soru gönderilir. Fikstür cevabı:

```ts
const CEVAP = [
  '$\\frac{3}{4}$ daha büyük. Paydaları eşitleyince iki kesri aynı parçalarla sayarız.',
  '',
  ':::kavram',
  'Payda, bütünün kaç eş parçaya bölündüğünü; pay, kaç tanesini aldığımızı söyler.',
  ':::',
  '',
  ':::adimlar',
  '1. Ortak payda: 4 ile 3\'ün ortak katı **12**.',
  '2. $\\frac{3}{4} = \\frac{9}{12}$ ve $\\frac{2}{3} = \\frac{8}{12}$',
  '3. Paylar karşılaştırılır: $9 > 8$.',
  ':::',
  '',
  ':::sonuc',
  '$\\frac{3}{4} > \\frac{2}{3}$',
  ':::',
  '',
  '| | 3/4 | 2/3 |',
  '|---|---|---|',
  '| 12\'lik | 9/12 | 8/12 |',
  '| Ondalık | $0{,}75$ | $0{,}67$ |',
  '',
  ':::hata',
  '"3 ve 2\'ye bakarım" demek: paydalar farklıyken pay tek başına karşılaştırılamaz.',
  ':::',
  '',
  ':::bilinmeyen',
  'Bu düz paragraf olarak görünür.',
  ':::',
  '',
  'Fiyatı 5 \\$ değil, 5 TL.',
  '',
  '**Şimdi:** $\\frac{5}{6}$ ile $\\frac{7}{9}$\'u sen karşılaştır.',
].join('\n')
```

Sınanacaklar:

- (a) Bloklar: `.ac-kutu--kavram`, `.ac-kutu--sonuc`, `.ac-kutu--hata` görünür. Etiket metinleri sırasıyla "Kavram", "Sonuç", "Sık yapılan hata".
- (b) Adımlar: `.ac-adimlar .ac-adim` sayısı 3; ilk adımın numarası "1".
- (c) Formüller: `.ac-formul .katex` görünür ve sayısı en az 8.
- (d) Tablo: `.ac-md__table-wrap` bir `role="region"` taşır, erişilebilir adı "Tablo" ve `tabindex="0"`; tablo 3 satırdır.
- (e) Bilinmeyen blok: "Bu düz paragraf olarak görünür." bir `p` içinde görünür ve `.ac-kutu` içinde değildir.
- (f) Kaçış: "5 $ değil" metni görünür; orada formül yoktur.
- (g) Taşma: 390 px'te `document.documentElement.scrollWidth === 390`.
- (h) Ekran görüntüleri: Genel modda ve Matematik modunda (`localStorage` `tedy-asistan-ogretmen::test@tedy.online` = `matematik`), 1440 ve 390 px. Görüntü adları `zengin-cevap-<genel|matematik>-<masaustu|telefon>.png`; `fullPage: true`, `animations: 'disabled'`, `maxDiffPixelRatio: 0.002`.
- (i) Erişilebilirlik: axe (WCAG 2.2 AA + best-practice) ve IBM Equal Access ihlal yok, iki modda da. `asistan-ogretmen-gorsel.spec.ts`'deki axe/IBM kurulumunu kopyala.
- (j) Akış: aynı cevap `answer_delta` parçalarıyla gelirken (sahte SSE gövdesinde `:::adimlar` açık, kapanmamış bir ara durum) taslakta `.ac-msg--writing .ac-adimlar` görünür; son `answer` olayından sonra tek bir yanıt kalır.

Formül görünümünü beklemek için `await expect(page.locator('.ac-formul .katex').first()).toBeVisible()` kullan (KaTeX tembel yüklenir).

- [ ] **Step 2: Başarısız olduğunu gör**

```bash
cd dashboard && npm run build; echo "build çıkış: $?"
env -u ANTHROPIC_API_KEY TEDY_E2E_PORT=8301 DASHBOARD_SECRET_KEY=yerel-test npx playwright test asistan-zengin-cevap
```

Expected: FAIL (`.ac-kutu--kavram` yok).

- [ ] **Step 3: KaTeX'i kur ve `Formul` bileşenini yaz**

```bash
cd dashboard && npm install katex@^0.16 && npm install -D @types/katex
```

`@types/katex` gereksizse (`katex` kendi türlerini taşıyorsa) kurma. `node_modules/katex/package.json`'da `"types"` alanına bak.

`dashboard/src/components/Formul.tsx`:

```tsx
import { useEffect, useRef, useState } from 'react'

// KaTeX loads only when an answer carries math (D1): import() keeps it and its
// fonts out of the first page bundle. Until it arrives — or if it fails — the
// TeX source shows as code, so the reader never sees nothing.
type Katex = typeof import('katex')
let yukleniyor: Promise<Katex> | null = null
function katexYukle(): Promise<Katex> {
  yukleniyor ??= Promise.all([import('katex'), import('katex/dist/katex.min.css')])
    .then(([m]) => (m as unknown as { default?: Katex }).default ?? (m as unknown as Katex))
  return yukleniyor
}

export default function Formul({ tex, blok }: { tex: string; blok: boolean }) {
  const ref = useRef<HTMLSpanElement>(null)
  const [cizildi, setCizildi] = useState(false)

  useEffect(() => {
    let iptal = false
    katexYukle().then(katex => {
      if (iptal || !ref.current) return
      try {
        // trust: false — no \href/\url/\includegraphics from model text.
        katex.render(tex, ref.current, {
          displayMode: blok, throwOnError: false, output: 'htmlAndMathml',
          trust: false, strict: 'ignore', maxSize: 10, maxExpand: 100,
        })
        setCizildi(true)
      } catch {
        setCizildi(false)
      }
    }).catch(() => setCizildi(false))
    return () => { iptal = true }
  }, [tex, blok])

  const Kap = blok ? 'div' : 'span'
  return (
    <Kap className={`ac-formul${blok ? ' ac-formul--blok' : ''}`}>
      <span ref={ref} />
      {!cizildi && <code className="ac-formul__kaynak">{tex}</code>}
    </Kap>
  )
}
```

- [ ] **Step 4: İşaretleyiciye blok, formül ve tablo bölgesini ekle**

`dashboard/src/utils/markdown.tsx`:

(a) `Block` birleşimine ekle:

```ts
  | { kind: 'kutu'; ad: KutuAdi; children: Block[] }
  | { kind: 'formul'; tex: string }
```

Dosyanın başına ekle:

```ts
export type KutuAdi = 'kavram' | 'ornek' | 'adimlar' | 'sonuc' | 'hata'
const KUTULAR: ReadonlySet<string> = new Set(['kavram', 'ornek', 'adimlar', 'sonuc', 'hata'])
const KUTU_ACILIS_RE = /^:::\s*([a-zçğıöşü]+)\s*$/
const KUTU_KAPANIS_RE = /^:::\s*$/
const BLOK_FORMUL_RE = /^\$\$(.+)\$\$$/
```

(b) `parseBlocks(markdown, sohbet)` satır döngüsünün başında, yalnız `sohbet` iken:

- `KUTU_ACILIS_RE`'ye uyan bir satır, eldeki paragrafı boşaltır (`flushParagraph()`). Ardından bir sonraki `KUTU_KAPANIS_RE` satırına ya da metnin sonuna kadarki satırları toplar; akışta kapanmamış blok sona kadar sürer. İç metin `parseBlocks(ic, true)` ile ayrıştırılır; iç içe `:::` satırları düz metin sayılır, çünkü iç ayrıştırmada `:::` açılışı yoktur. Bunu sağlamak için `parseBlocks`'a üçüncü bir `icte = false` parametresi ekle; iç çağrı `true` geçer ve iç çağrıda açılış tanınmaz.
- Ad `KUTULAR`'daysa `{ kind: 'kutu', ad, children }` eklenir. Değilse `children` blokları olduğu gibi (sarmalayıcısız) eklenir.
- Tek başına `$$…$$` satırı `{ kind: 'formul', tex }` olur. Çok satırlı `$$` (açılış satırı `$$`, sonra satırlar, kapanış `$$`) da tek formül olur.

(c) `INLINE_RE`'ye en başa bir dal ekle: `(?<!\\)\$(?!\$)[^$\n]+?(?<!\\)\$`. Ardından `renderInline` içinde, bu desene uyan belirteç için `<Formul key={key} tex={token.slice(1, -1)} blok={false} />` döndür. `\$` dizisi ekranda `$` olarak görünür: `pushText` aşamasında `\\$` → `$`. Kitap (`kitap`) biçiminde formül işlenmez; yalnız `sohbet`. `renderInline`'a bu ayrımı taşıyacak bir parametre gerekiyorsa ekle.

(d) `renderSohbet` içinde:

```tsx
      case 'kutu': {
        const ETIKET: Record<KutuAdi, string> = {
          kavram: 'Kavram', ornek: 'Örnek', adimlar: 'Adımlar', sonuc: 'Sonuç', hata: 'Sık yapılan hata',
        }
        if (block.ad === 'adimlar') {
          const liste = block.children.find(b => b.kind === 'list' && b.ordered)
          if (liste && liste.kind === 'list') {
            return (
              <ol key={key} className="ac-adimlar" aria-label="Adımlar">
                {liste.items.map((item, i) => (
                  <li key={`${key}-${i}`} className="ac-adim">
                    <span className="ac-adim__no" aria-hidden="true">{i + 1}</span>
                    <div className="ac-adim__govde">{renderInline(item.text, `${key}-${i}`, renderToken)}</div>
                  </li>
                ))}
              </ol>
            )
          }
        }
        return (
          <div key={key} className={`ac-kutu ac-kutu--${block.ad}`}>
            <span className="ac-kutu__etiket">{ETIKET[block.ad]}</span>
            {renderSohbet(block.children, renderToken)}
          </div>
        )
      }
      case 'formul':
        return <Formul key={key} tex={block.tex} blok />
```

`list` bloğunun gerçek alan adlarını (`ordered`, `items`, `item.text`) dosyadan oku; farklıysa ona uyarla.

Mevcut `case 'table':` dönüşünü sar:

```tsx
          <div key={key} className="ac-md__table-wrap" role="region" aria-label="Tablo" tabIndex={0}>
            <table className="ac-md__table">…</table>
          </div>
```

- [ ] **Step 5: Stiller**

`dashboard/src/components/AssistantChat.scss` sonuna:

```scss
// ─── Zengin cevap blokları (D1, 2026-10-02) ───────────────────────────────────
// Genel: nötr Tedy rolleri. Öğretmen modu: o dersin paneli (İ8: bir cevapta
// kavram/örnek kutuları küçük kartlardır; büyük yüzey öğretmen panelidir).
// Sonuç ve hata her modda durum rengindedir.
.ac-kutu {
  margin-block: spacing.$spacing-04;
  padding: spacing.$spacing-04 spacing.$spacing-05;
  border-inline-start: 3px solid var(--cds-border-strong-01);
  background: var(--cds-layer-02);
}

.ac-kutu__etiket {
  display: block;
  margin-block-end: spacing.$spacing-02;
  color: var(--cds-text-secondary);
  @include type.type-style('label-01');
  text-transform: uppercase;
}

.ac-kutu--ornek {
  border: 1px solid var(--cds-border-subtle-01);
  background: var(--cds-layer-01);
}

.ac-kutu--sonuc {
  border-inline-start-color: var(--cds-support-success);
  background: var(--cds-notification-background-success);
  @include type.type-style('heading-compact-01');
}

.ac-kutu--hata {
  border-inline-start-color: var(--cds-support-warning);
  background: var(--cds-notification-background-warning);
}

.ac[data-ogretmen]:not([data-ogretmen='genel']) {
  .ac-kutu--kavram {
    border-inline-start-color: var(--ted-subject-accent);
    background: var(--ted-subject-panel);
  }

  .ac-kutu--kavram .ac-kutu__etiket {
    color: var(--ted-subject-text);
  }

  .ac-adim__no {
    background: var(--ted-subject-accent);
  }
}

.ac-adimlar {
  display: grid;
  gap: spacing.$spacing-03;
  margin-block: spacing.$spacing-04;
}

.ac-adim {
  display: flex;
  gap: spacing.$spacing-04;
  align-items: flex-start;
  padding: spacing.$spacing-04;
  border: 1px solid var(--cds-border-subtle-01);
  background: var(--cds-layer-01);
}

.ac-adim__no {
  display: inline-flex;
  flex: none;
  align-items: center;
  justify-content: center;
  inline-size: spacing.$spacing-06;
  block-size: spacing.$spacing-06;
  background: var(--cds-button-primary);
  color: var(--cds-text-on-color);
  @include type.type-style('label-02');
}

.ac-formul--blok {
  display: block;
  margin-block: spacing.$spacing-04;
  overflow-x: auto;
}

.ac-formul__kaynak {
  @include type.type-style('code-02');
}

.ac-md__table-wrap {
  overflow-x: auto;
  margin-block: spacing.$spacing-04;

  &:focus-visible {
    outline: 2px solid var(--cds-focus);
  }
}
```

`--cds-notification-background-success/warning` token adlarının Carbon v11'de var olduğunu `grep -rn "notification-background-success" dashboard/node_modules/@carbon/styles/scss | head -2` ile doğrula. Yoksa en yakın Carbon rol token'ını seç ve raporda yaz. `.ac-kutu--sonuc` gibi yeşil zeminli bir kutuda metin kontrastı axe/IBM'den geçmeli.

- [ ] **Step 6: Testleri koş ve görselleri oku**

```bash
cd dashboard && npm run lint; echo "lint: $?"; npm run build; echo "build çıkış: $?"
env -u ANTHROPIC_API_KEY TEDY_E2E_PORT=8301 DASHBOARD_SECRET_KEY=yerel-test npx playwright test asistan-zengin-cevap --update-snapshots
env -u ANTHROPIC_API_KEY TEDY_E2E_PORT=8301 DASHBOARD_SECRET_KEY=yerel-test npx playwright test asistan-zengin-cevap asistan-cevap-bicimi asistan-ogretmen tasarim-denetimi ibm-erisilebilirlik
```

Dört yeni PNG'yi Read ile aç, her biri için raporda bir satır yaz. `asistan-cevap-bicimi` taban çizgisi değişirse (ör. tablo artık bir bölge içinde olduğu için), farkı oku ve gerekçesini yaz; ancak ondan sonra güncelle.

- [ ] **Step 7: Commit**

```bash
test "$(git branch --show-current)" = feat/asistan-zengin && echo dal-dogru
git add dashboard/package.json dashboard/package-lock.json dashboard/src/components/Formul.tsx \
  dashboard/src/utils/markdown.tsx dashboard/src/components/AssistantChat.scss \
  dashboard/tests/e2e/asistan-zengin-cevap.spec.ts
git add dashboard/tests/e2e/asistan-zengin-cevap.spec.ts-snapshots/*.png
git status --short   # değişen başka taban çizgisi varsa adıyla ekle
git commit -m "D1: panoda kavram/örnek/adımlar/sonuç/hata blokları, KaTeX formül, kaydırılan tablo

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Netleştirme düğmeleri

**Files:**
- Modify: `dashboard/src/types.ts` (`ModOnerisi` yanına)
- Create: `dashboard/src/components/NetlestirmeSecenekleri.tsx`
- Modify: `dashboard/src/components/AssistantChat.tsx` (`ChatMessage` ~43, `TOOL_LABEL` ~81-100, `appendAssistantMessage` ~351, akış döngüsü ~436, mesaj çizimi ~622)
- Modify: `dashboard/src/components/AssistantChat.scss`
- Test: `dashboard/tests/e2e/asistan-netlestirme.spec.ts`

**Interfaces:**
- Consumes: Task 1'in `clarify` olayı ve `netlestirme` yük alanı (`{soru: string, secenekler: string[]}`).
- Produces:
  - `types.ts`: `export interface Netlestirme { soru: string; secenekler: string[] }`, `AssistantResponse.netlestirme?: Netlestirme | null`.
  - `NetlestirmeSecenekleri`: `default function NetlestirmeSecenekleri({ secenekler, etkin, onSec, onBaska }: { secenekler: string[]; etkin: boolean; onSec: (s: string) => void; onBaska: () => void })`. Kökü `div.ac-netlestirme[role="group"][aria-label="Seçenekler"]`.

- [ ] **Step 1: Başarısız e2e testini yaz**

`dashboard/tests/e2e/asistan-netlestirme.spec.ts`. `asistan-ogretmen.spec.ts`'deki SSE sahteleme yardımcılarını kullan. Senaryo: kullanıcı "kesirleri anlat" sorar; akış `tool_start` (`netlestir`), `tool_end`, `clarify` (`{soru:'Kesirlerin hangi yönüyle başlayalım?', secenekler:['Karşılaştırma','Toplama','Ondalık gösterim']}`) ve `answer` (yanıt metni soru, `netlestirme` alanı aynı) gönderir.

Sınanacaklar:
- (a) Cevabın altında `role="group"` "Seçenekler" içinde dört düğme vardır: üç seçenek ve sonda "Başka bir şey yaz…".
- (b) "Toplama"ya tıklanınca yeni bir kullanıcı mesajı "Toplama" görünür ve isteğin `messages` dizisinin son öğesi `{role:'user', content:'Toplama'}` olur. İstek gövdesini `page.route` içinde yakala.
- (c) Tıklamadan sonra eski seçenek düğmeleri devre dışıdır (`toBeDisabled`).
- (d) "Başka bir şey yaz…" yazma alanına odaklanır (`toBeFocused`) ve mesaj göndermez.
- (e) Aynı senaryo yalnız `/chat` ile de çalışır: akış 500 döner, `/chat` yükünde `netlestirme` var.
- (f) İlerleme satırı `tool_start` sırasında "Seçenekler hazırlanıyor" yazar.
- (g) Telefon (390 px) ekran görüntüsü `netlestirme-telefon.png` alınır ve axe/IBM temizdir.

- [ ] **Step 2: Başarısız olduğunu gör**

```bash
cd dashboard && npm run build; echo "build çıkış: $?"
env -u ANTHROPIC_API_KEY TEDY_E2E_PORT=8301 DASHBOARD_SECRET_KEY=yerel-test npx playwright test asistan-netlestirme
```

Expected: FAIL.

- [ ] **Step 3: Tür, bileşen ve bağlama**

`types.ts`:

```ts
/** netlestir's question: the stream's `clarify` event, or the answer's field (D1). */
export interface Netlestirme {
  soru: string
  secenekler: string[]
}
```

`AssistantResponse`'a `netlestirme?: Netlestirme | null` ekle.

`dashboard/src/components/NetlestirmeSecenekleri.tsx`:

```tsx
import { Button } from '@carbon/react'

// netlestir's options (D1): tapping one sends it as the reader's next message.
// "Başka bir şey yaz…" is always last and only moves focus to the input.
// Disabled once a newer message exists — the question has been answered.
export default function NetlestirmeSecenekleri({
  secenekler, etkin, onSec, onBaska,
}: {
  secenekler: string[]
  etkin: boolean
  onSec: (s: string) => void
  onBaska: () => void
}) {
  return (
    <div className="ac-netlestirme" role="group" aria-label="Seçenekler">
      {secenekler.map(s => (
        <Button key={s} kind="tertiary" size="sm" disabled={!etkin} onClick={() => onSec(s)}>
          {s}
        </Button>
      ))}
      <Button kind="ghost" size="sm" disabled={!etkin} onClick={onBaska}
        className="ac-netlestirme__baska">
        Başka bir şey yaz…
      </Button>
    </div>
  )
}
```

`AssistantChat.tsx` değişiklikleri:
- `ChatMessage`'a `netlestirme?: Netlestirme | null` ekle.
- `TOOL_LABEL`'a `netlestir: 'Seçenekler hazırlanıyor'` ekle.
- `appendAssistantMessage(payload, oneri, netlestirme: Netlestirme | null = null)` içinde `netlestirme: payload.netlestirme ?? netlestirme` ata.
- Akış döngüsünde `let netlestirme: Netlestirme | null = null` tanımla; `name === 'clarify'` olayında `netlestirme = data as unknown as Netlestirme` yap; `answer` olayında bunu `appendAssistantMessage`'a geçir.
- Mesaj çiziminde `ModOnerisi`'nin yanına şunu ekle:

```tsx
                  {msg.netlestirme && msg.netlestirme.secenekler.length > 0 && (
                    <NetlestirmeSecenekleri
                      secenekler={msg.netlestirme.secenekler}
                      etkin={!loading && msg.id === messages[messages.length - 1]?.id}
                      onSec={s => void submit('chat', s)}
                      onBaska={() => textareaRef.current?.focus()} />
                  )}
```

`submit`'in ilk parametresi ve `forcedPrompt` davranışını oku; seçilen metin kullanıcı mesajı olarak gitmeli.

`AssistantChat.scss`:

```scss
.ac-netlestirme {
  display: flex;
  flex-wrap: wrap;
  gap: spacing.$spacing-03;
  margin-block-start: spacing.$spacing-04;

  .cds--btn {
    max-inline-size: 100%;
    min-inline-size: 0;
  }
}

.ac[data-ogretmen]:not([data-ogretmen='genel']) .ac-netlestirme {
  --cds-button-tertiary: var(--ted-subject-accent);
  --cds-button-tertiary-hover: var(--ted-subject-text);
}
```

- [ ] **Step 4: Testleri koş ve görseli oku**

```bash
cd dashboard && npm run lint; echo "lint: $?"; npm run build; echo "build çıkış: $?"
env -u ANTHROPIC_API_KEY TEDY_E2E_PORT=8301 DASHBOARD_SECRET_KEY=yerel-test npx playwright test asistan-netlestirme --update-snapshots
env -u ANTHROPIC_API_KEY TEDY_E2E_PORT=8301 DASHBOARD_SECRET_KEY=yerel-test npx playwright test asistan-netlestirme asistan-ogretmen asistan-zengin-cevap tasarim-denetimi ibm-erisilebilirlik
```

PNG'yi Read ile aç ve raporda betimle.

- [ ] **Step 5: Commit**

```bash
test "$(git branch --show-current)" = feat/asistan-zengin && echo dal-dogru
git add dashboard/src/types.ts dashboard/src/components/NetlestirmeSecenekleri.tsx \
  dashboard/src/components/AssistantChat.tsx dashboard/src/components/AssistantChat.scss \
  dashboard/tests/e2e/asistan-netlestirme.spec.ts dashboard/tests/e2e/asistan-netlestirme.spec.ts-snapshots/*.png
git commit -m "D1: netleştirme seçenek düğmeleri

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Belgeler ve son kapı

**Files:**
- Modify: `CLAUDE.md` ("How an answer is set" maddesi; B1 maddesindeki `mod_onerisi` adı)

- [ ] **Step 1: CLAUDE.md**

"How an answer is set" maddesinde "no tables, rules, quotes or emoji" ifadesini kaldır ve maddenin sonuna şunu ekle:

> Since D1 (2026-10-02, plan `docs/superpowers/plans/2026-10-02-d1-zengin-cevap-netlestirme.md`) the prompt also teaches a closed block vocabulary — `:::kavram`, `:::ornek`, `:::adimlar` (a numbered list rendered as step cards), `:::sonuc`, `:::hata` — closed by a lone `:::`, plus `$…$`/`$$…$$` math (KaTeX, loaded by `import()` only when an answer has math; until then, or on failure, the TeX source shows as code; `trust: false`) and pipe tables of at most 4 columns, scrolled inside a named, focusable region on a phone. An unknown block name renders as plain paragraphs; an unclosed block fills progressively while streaming. In a teacher mode `kavram` sits on `--ted-subject-panel`; `sonuc`/`hata` are status colours in every mode. `netlestir(soru, secenekler 2–4)` is a terminating tool: alone in its round it ends the answer (text = the round's text + the question, streamed, no reset) and emits `clarify` / payload `netlestirme`, rendered as option buttons plus "Başka bir şey yaz…"; beside another tool it is refused and not run. It and `mod_oner` are declared only when `etkilesimli` is true (`/stream`, `/chat`); `/plan` and `/v1` pass `etkilesimli=False` (formerly `mod_onerisi`).

B1 maddesinde geçen `mod_onerisi` adlarını `etkilesimli` yap.

- [ ] **Step 2: Son kapı**

```bash
(DASHBOARD_SECRET_KEY=yerel-test .venv/bin/python -m pytest -q -p no:cacheprovider > /tmp/d1-py.log 2>&1; echo "EXIT=$?" >> /tmp/d1-py.log) &
timeout 590 bash -c 'until grep -q "^EXIT=" /tmp/d1-py.log; do sleep 15; done'; tail -3 /tmp/d1-py.log
cd dashboard && npm run lint; echo "lint: $?"; npm run build; echo "build çıkış: $?"
env -u ANTHROPIC_API_KEY TEDY_E2E_PORT=8301 DASHBOARD_SECRET_KEY=yerel-test npx playwright test
```

Beklenen: Python `EXIT=0`; lint 0; build 0; Playwright tam paket yeşil.

- [ ] **Step 3: Commit**

```bash
test "$(git branch --show-current)" = feat/asistan-zengin && echo dal-dogru
git add CLAUDE.md
git commit -m "D1: CLAUDE.md — zengin cevap ve netleştirme

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
