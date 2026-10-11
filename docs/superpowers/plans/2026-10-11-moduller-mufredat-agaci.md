# Modüller — müfredat ağacı ve içerik yer tutucuları — uygulama planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modüller yüzeyini, 7. sınıfın dört dersinin müfredat haritasına (ders → ünite → ders kitabı alt başlığı) çevirmek; her alt başlıkta modül varsa bağlantı, yoksa "Asistana sor" taşıyan bir yer tutucu olmak.

**Architecture:** Sabitlenmiş salt-okunur müfredat SQLite'ından üretilen, depoda izlenen bir JSON ağacı (`src/mufredat_agaci.json`); yalnız-stdlib bir okuyucu (`src/mufredat_agaci.py`) iki tarafça salt okunur; Flask'ta tek uç (`/api/modules/agac`) ağacı yayınlanmış modül kataloğuyla birleştirir; panoda Carbon `TreeView size="sm"` çizer.

**Tech Stack:** Python 3 (stdlib + sqlite3), Flask, React 19 + `@carbon/react` 1.114.0, Vite, pytest, Playwright.

**Spec:** `docs/superpowers/specs/2026-10-11-moduller-mufredat-agaci-design.md`

**Spec'ten sonra inen merge'e göre güncellendi (342d452).** Üç şey değişti ve plan buna uyarlandı:
`useApi` artık `{ data, loading, iskelet, error, hataTuru }` döndürüyor ve yüzeyler hatayı
`apiHataCumlesi(hataTuru, '<ad>')` ile cümleye çeviriyor (B43); `Modules.tsx` bunu zaten
kullanıyor, Görev 7 o kullanımı **korur**. Talimatname §11.1 tablosu artık S1–S46 ve
değişiklik kaydı S47'yi "gerekmedi" diye anıyor, bu yüzden bu işin sapmaları **S48–S50**.
`Modules.scss` zaten `spacing`, `theme`, `type` `@use` satırlarını taşıyor — Görev 7'de
yeniden eklenmez.

## Global Constraints

Bu bölümdeki her değer spec §0'daki ölçüm tablosundan birebir alınmıştır; gerekçeleri ve kaynakları orada.

- Veritabanı **yalnız** şu URI ile açılır: `file:/home/mahirkurt/mcp-data/mufredat/mufredat.sqlite?mode=ro&immutable=1` (salt okunur, değişmez). Başka bir yol, başka bir kip yazılmaz.
- `output/modules/` altına **yazılmaz** — orada tek yazar ted-mcp (`CLAUDE.md` "Tek yazar").
- `src/mufredat_agaci.py` **yalnız stdlib** kullanır; `src/mcp_server` ya da `src/dashboard_api` import etmez (`src/module_store.py` ile aynı kural).
- Program belgeleri ve 7. sınıf sayfa aralıkları: Matematik 24 (115–172), Türkçe 51 (126–161), Fen 54 (146–183), Sosyal 100 (93–122) — `scripts/skill_unite_haritasi.py` `DERSLER` tablosundan, yeniden ölçülmez.
- 7. sınıf ders kitapları: Fen 439/473, Matematik 346/506, Türkçe 460/340, Sosyal 491/361.
- Basılı → PDF sayfa kayması beklenen değerler: doc 439 **+1**, doc 473 **+1**, doc 346 **0**, doc 506 **0**. Üretici bunları **türetir**, sabit yazmaz; test türetilen değeri bu beklentiyle karşılaştırır.
- Eşikler: kayma uyumu < %80 → o kitabın konuları `sayfa_kaynak: "yok"`. Bir dersin konularının %60'ından çoğu başlıksız → o ders **hiç** yazılmaz.
- `kazanim_kaynak` yalnız `"metin-ortusmesi"` ya da `"eslenmedi"`. Kod sırasına göre eşleme yasak.
- Türkçe konuları **kazanım kodu taşımaz** (kazanım beceriye kodlu).
- `id` biçimi `<ders slug>-u<ünite no>-<konu slug'ı>`; **sırasal sayı kullanılmaz**; alfabe `src/module_store.py` `SLUG_RE` ile aynı.
- Carbon: `TreeView size="sm"` + `TreeNode`; `TreeNode.label` ReactNode, `href` prop'u vardır (yerel 1.114.0 `.d.ts`). `preview__*` / `unstable_*` API kullanılmaz.
- Telefonda (md kırılımı 672 px altı) her TEDY denetimi ≥ 44 px. Carbon'un ağaç düğümü sm 32 / xs 24 px olduğu için örtme zorunlu (sapma S48).
- Yeni ölçüler **`rem`**; ikonlar `size={…}` ile mevcut kuralı olan boylardan (4K kuralı).
- Görünür etiketler cümle düzeninde; `text-transform: uppercase` ve büyük harf kaynak dizgisi yasak.
- Playwright **anahtar ortamda yokken** koşar. Worktree-izole oturumda `env -u ANTHROPIC_API_KEY npx
  playwright test …` biçimi koruma tarafından reddedilir (ölçüldü, bu worktree'de); çalışan biçim alt
  kabuktur: `(unset ANTHROPIC_API_KEY; npx playwright test …)`. Ana checkout'ta `env -u` de çalışır.
- Hiçbir Carbon adı (bileşen, prop, ikon, içe aktarma yolu) ezberden yazılmaz: Carbon MCP ya da `dashboard/node_modules` ile doğrulanır (talimatname §10).

## Review Focus

Spec'in ima ettiği ama hiçbir görevin testinin kendiliğinden yoklamadığı beş girdi sınıfı. Her satırın testi, kodun sahibi olan göreve eklenmiştir.

1. **Geçerli JSON ama şema dışı ağaç** (`konular` bir sözlük, `uniteler` eksik, `no` dize) — uç 500 vermemeli, `hata: "harita_okunamadi"` dönmeli. → Görev 1 (okuyucu reddeder) + Görev 5 (uç dönüşü).
2. **Bir ünitede aynı adlı iki konu** — `id` çakışması sessizce bir konuyu yutmamalı; `-2` eki ve `kapsam`a kayıt. → Görev 4.
3. **Bozuk sayfa aralığı** (ters sıralı, sıfır/negatif, kitabın `page_count`'unu aşan) — `sayfa` yazılmamalı, `sayfa_kaynak: "yok"` olmalı. → Görev 4.
4. **Yetkisiz çağrı** — okur rolü ve API anahtarı `/api/modules/agac`'ı alamamalı (varsayılan-reddet). → Görev 5.
5. **Kötü konu kimliği asistan bağlamında** — bilinmeyen kimlik `""` (400 değil), 400 karakterden uzun ya da denetim karakteri taşıyan kimlik 400. → Görev 6.

---

### Task 1: Ağaç okuyucusu ve şema doğrulaması

Yalnız-stdlib okuyucu. Üretici de, uç da bunu kullanır; bu yüzden önce gelir.

**Files:**
- Create: `src/mufredat_agaci.py`
- Create: `tests/test_mufredat_agaci.py`

**Interfaces:**
- Consumes: hiçbir şey (yalnız stdlib).
- Produces:
  - `AGAC_ADI: str = "mufredat_agaci.json"`
  - `agac_yolu(kok: Path | str) -> Path` — `<kok>/mufredat_agaci.json`
  - `KAZANIM_KAYNAKLARI: tuple[str, ...] = ("metin-ortusmesi", "eslenmedi")`
  - `SAYFA_KAYNAKLARI: tuple[str, ...] = ("icindekiler", "yok")`
  - `dogrula(payload: Any) -> list[str]` — şema hatalarının listesi; boş liste = geçerli
  - `oku(yol: Path | str) -> tuple[str, dict | None]` — `("ok", agac)` | `("yok", None)` | `("bozuk", None)`
  - `konular(agac: dict) -> Iterator[tuple[dict, dict, dict]]` — (ders, ünite, konu)
  - `konu_bul(agac: dict, konu_id: str) -> tuple[dict, dict, dict] | None`

- [ ] **Step 1: Write the failing test**

`tests/test_mufredat_agaci.py`:

```python
"""Müfredat ağacı okuyucusu ve şeması (spec §2)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import mufredat_agaci as ma  # noqa: E402


def _agac(**ustune):
    """Geçerli bir asgari ağaç; testler tek alanı bozar."""
    taban = {
        "surum": 1, "korpus_surumu": "1.6", "sinif": "7. Sınıf",
        "dersler": [{
            "ders": "Fen Bilimleri", "slug": "fen",
            "program": {"document_id": 54, "sayfa": "146-183"},
            "kitaplar": [{"document_id": 439, "kisa": "1. Kitap",
                          "sayfa_kaymasi": 1, "kayma_uyumu": "21/23"}],
            "uniteler": [{
                "no": 3, "ad": "Vücudumuzdaki Sistemler", "program_sayfa": 156,
                "konular": [{
                    "id": "fen-u3-sindirim-sisteminin-sagligi",
                    "ad": "Sindirim Sisteminin Sağlığı",
                    "ad_kaynak": "SİNDİRİM SİSTEMİNİN SAĞLIĞI",
                    "kitap": 439, "sayfa": [97, 101], "sayfa_kaynak": "icindekiler",
                    "kazanimlar": ["FB.7.3.2"], "kazanim_kaynak": "metin-ortusmesi",
                }],
            }],
        }],
        "kapsam": {"fen": {"konu": 1, "sayfasi_olan": 1, "kazanimi_eslenen": 1}},
    }
    taban.update(ustune)
    return taban


def test_gecerli_agac_hatasiz():
    assert ma.dogrula(_agac()) == []


def test_konular_dersi_uniteyi_ve_konuyu_birlikte_verir():
    ders, unite, konu = next(iter(ma.konular(_agac())))
    assert (ders["slug"], unite["no"], konu["id"]) == ("fen", 3, "fen-u3-sindirim-sisteminin-sagligi")


def test_konu_bul_bilinmeyen_kimlikte_none():
    assert ma.konu_bul(_agac(), "fen-u9-olmayan") is None


# Review Focus 1: geçerli JSON ama şema dışı.
@pytest.mark.parametrize("bozma", [
    {"dersler": {}},
    {"dersler": [{"ders": "Fen", "slug": "fen", "uniteler": {}}]},
    {"surum": "1"},
])
def test_sema_disi_govde_hata_listesi_dondurur(bozma):
    assert ma.dogrula(_agac(**bozma)) != []


def test_sayfa_kaynak_yok_iken_sayfa_alani_varsa_reddedilir():
    agac = _agac()
    konu = agac["dersler"][0]["uniteler"][0]["konular"][0]
    konu["sayfa_kaynak"] = "yok"
    assert "sayfa" in konu  # kurgu hâlâ sayfa taşıyor
    assert ma.dogrula(agac) != []  # bu yasak


def test_bilinmeyen_kazanim_kaynagi_reddedilir():
    agac = _agac()
    agac["dersler"][0]["uniteler"][0]["konular"][0]["kazanim_kaynak"] = "kod-sirasi"
    assert ma.dogrula(agac) != []


def test_oku_eksik_dosyada_yok_der(tmp_path):
    assert ma.oku(tmp_path / "olmayan.json") == ("yok", None)


def test_oku_bozuk_dosyada_bozuk_der(tmp_path):
    yol = tmp_path / "a.json"
    yol.write_text("{ bu json degil", encoding="utf-8")
    assert ma.oku(yol) == ("bozuk", None)


def test_oku_sema_disi_dosyayi_bozuk_sayar(tmp_path):
    yol = tmp_path / "a.json"
    yol.write_text(json.dumps(_agac(dersler={})), encoding="utf-8")
    assert ma.oku(yol)[0] == "bozuk"


def test_oku_gecerli_dosyayi_dondurur(tmp_path):
    yol = tmp_path / "a.json"
    yol.write_text(json.dumps(_agac()), encoding="utf-8")
    durum, agac = ma.oku(yol)
    assert durum == "ok" and agac["dersler"][0]["slug"] == "fen"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `unshare -rn .venv/bin/python -m pytest -q tests/test_mufredat_agaci.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.mufredat_agaci'`

- [ ] **Step 3: Write minimal implementation**

`src/mufredat_agaci.py`:

```python
"""Müfredat ağacı (7. sınıf ders → ünite → ders kitabı alt başlığı) okuyucusu ve şeması.

Dosya `scripts/mufredat_agaci.py` tarafından üretilir, elle düzenlenmez (spec §2). Burada
yalnız okuma ve şema doğrulaması vardır: pano `src/mcp_server`'ı, ted-mcp `src/dashboard_api`'yi
import etmediği için bu modül **yalnız stdlib** kullanır (`src/module_store.py` ile aynı kural).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterator

AGAC_ADI = "mufredat_agaci.json"
KAZANIM_KAYNAKLARI = ("metin-ortusmesi", "eslenmedi")
SAYFA_KAYNAKLARI = ("icindekiler", "yok")
# module_store.SLUG_RE ile aynı alfabe: kimlik iki yere sızıyor (localStorage, asistan bağlamı).
KIMLIK_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def agac_yolu(kok: Path | str) -> Path:
    return Path(kok) / AGAC_ADI


def _tam_sayi(deger: Any) -> bool:
    return isinstance(deger, int) and not isinstance(deger, bool)


def _konu_hatalari(konu: Any, nerede: str) -> list[str]:
    if not isinstance(konu, dict):
        return [f"{nerede}: konu sözlük değil"]
    hatalar = []
    for alan in ("id", "ad", "ad_kaynak"):
        if not isinstance(konu.get(alan), str) or not konu[alan].strip():
            hatalar.append(f"{nerede}: {alan} boş ya da dize değil")
    if isinstance(konu.get("id"), str) and not KIMLIK_RE.fullmatch(konu["id"]):
        hatalar.append(f"{nerede}: id slug alfabesinde değil")
    if konu.get("sayfa_kaynak") not in SAYFA_KAYNAKLARI:
        hatalar.append(f"{nerede}: sayfa_kaynak bilinmiyor")
    if konu.get("kazanim_kaynak") not in KAZANIM_KAYNAKLARI:
        hatalar.append(f"{nerede}: kazanim_kaynak bilinmiyor")
    # Sayfa uydurulmaz: kaynak "yok" ise alan hiç bulunmaz (spec §2.1).
    if konu.get("sayfa_kaynak") == "yok" and "sayfa" in konu:
        hatalar.append(f"{nerede}: sayfa_kaynak 'yok' ama sayfa alanı var")
    if konu.get("sayfa_kaynak") == "icindekiler":
        sayfa = konu.get("sayfa")
        if (not isinstance(sayfa, list) or len(sayfa) != 2 or not all(_tam_sayi(s) for s in sayfa)
                or sayfa[0] < 1 or sayfa[1] < sayfa[0]):
            hatalar.append(f"{nerede}: sayfa [başlangıç, bitiş] değil")
    if not isinstance(konu.get("kazanimlar"), list) or not all(
            isinstance(k, str) for k in konu["kazanimlar"]):
        hatalar.append(f"{nerede}: kazanimlar dize listesi değil")
    if not _tam_sayi(konu.get("kitap")):
        hatalar.append(f"{nerede}: kitap belge kimliği değil")
    return hatalar


def dogrula(payload: Any) -> list[str]:
    """Şema hatalarının listesi; boş liste geçerli demektir."""
    if not isinstance(payload, dict):
        return ["gövde sözlük değil"]
    hatalar = []
    if payload.get("surum") != 1:
        hatalar.append("surum 1 değil")
    for alan in ("korpus_surumu", "sinif"):
        if not isinstance(payload.get(alan), str) or not payload[alan].strip():
            hatalar.append(f"{alan} boş ya da dize değil")
    if not isinstance(payload.get("kapsam"), dict):
        hatalar.append("kapsam sözlük değil")
    dersler = payload.get("dersler")
    if not isinstance(dersler, list):
        return hatalar + ["dersler liste değil"]
    kimlikler: set[str] = set()
    for ders in dersler:
        if not isinstance(ders, dict):
            hatalar.append("ders sözlük değil")
            continue
        slug = ders.get("slug")
        if not isinstance(slug, str) or not KIMLIK_RE.fullmatch(slug or ""):
            hatalar.append("ders slug'ı geçersiz")
            slug = "?"
        if not isinstance(ders.get("ders"), str) or not ders["ders"].strip():
            hatalar.append(f"{slug}: ders adı boş")
        if not isinstance(ders.get("kitaplar"), list):
            hatalar.append(f"{slug}: kitaplar liste değil")
        uniteler = ders.get("uniteler")
        if not isinstance(uniteler, list):
            hatalar.append(f"{slug}: uniteler liste değil")
            continue
        for unite in uniteler:
            if not isinstance(unite, dict):
                hatalar.append(f"{slug}: ünite sözlük değil")
                continue
            if not _tam_sayi(unite.get("no")):
                hatalar.append(f"{slug}: ünite no tam sayı değil")
            if not isinstance(unite.get("ad"), str) or not unite["ad"].strip():
                hatalar.append(f"{slug}: ünite adı boş")
            konular = unite.get("konular")
            if not isinstance(konular, list):
                hatalar.append(f"{slug}/{unite.get('no')}: konular liste değil")
                continue
            for konu in konular:
                nerede = f"{slug}/{unite.get('no')}"
                hatalar.extend(_konu_hatalari(konu, nerede))
                kimlik = konu.get("id") if isinstance(konu, dict) else None
                if isinstance(kimlik, str):
                    if kimlik in kimlikler:
                        hatalar.append(f"{nerede}: id yinelendi ({kimlik})")
                    kimlikler.add(kimlik)
    return hatalar


def oku(yol: Path | str) -> tuple[str, dict | None]:
    """("ok", ağaç) | ("yok", None) | ("bozuk", None). Hiçbir durumda yükseltmez."""
    try:
        metin = Path(yol).read_text(encoding="utf-8")
    except FileNotFoundError:
        return "yok", None
    except OSError:
        return "bozuk", None
    try:
        payload = json.loads(metin)
    except ValueError:
        return "bozuk", None
    if dogrula(payload):
        return "bozuk", None
    return "ok", payload


def konular(agac: dict) -> Iterator[tuple[dict, dict, dict]]:
    for ders in agac.get("dersler") or []:
        for unite in ders.get("uniteler") or []:
            for konu in unite.get("konular") or []:
                yield ders, unite, konu


def konu_bul(agac: dict, konu_id: str) -> tuple[dict, dict, dict] | None:
    return next((ucu for ucu in konular(agac) if ucu[2].get("id") == konu_id), None)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `unshare -rn .venv/bin/python -m pytest -q tests/test_mufredat_agaci.py`
Expected: PASS (13 test)

- [ ] **Step 5: Commit**

```bash
git add src/mufredat_agaci.py tests/test_mufredat_agaci.py
git commit -m "feat(moduller): müfredat ağacı okuyucusu ve şeması

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: Üreticinin saf ayrıştırıcıları

İçindekiler satırı, başlık harf düzeni, kayma türetimi, konu slug'ı. DB'ye dokunmaz; altın metinle sınanır.

**Files:**
- Create: `scripts/mufredat_agaci.py` (yalnız saf yardımcılar; DB katmanı Görev 3'te eklenir)
- Create: `tests/test_mufredat_agaci_ayristirici.py`

**Interfaces:**
- Consumes: hiçbir şey (yalnız stdlib). `konu_slug` alfabesi Görev 1'in `KIMLIK_RE`'siyle
  yapıca aynıdır ama import edilmez; uyumu Görev 1'in `dogrula`'sı zorlar.
- Produces:
  - `nokta_onculu(satir: str) -> tuple[str, int] | None`
  - `baslik_duzeni(metin: str) -> str`
  - `harf_katla(metin: str) -> str`
  - `kayma_bul(adaylar: list[tuple[int, int]]) -> tuple[int | None, str]` — `(kayma, "21/23")`
  - `konu_slug(ad: str) -> str`
  - `OCR_DUZELTME: dict[str, str]`

- [ ] **Step 1: Write the failing test**

`tests/test_mufredat_agaci_ayristirici.py`:

```python
"""Üreticinin saf ayrıştırıcıları (spec §2.2, §2.3). Veritabanına dokunmaz."""
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK / "scripts"))

import mufredat_agaci as u  # noqa: E402  (scripts/mufredat_agaci.py)


# Ölçülmüş gerçek satırlar: doc 439 s.8 ve doc 346 s.7 (spec §0).
@pytest.mark.parametrize("satir,beklenen", [
    ("Sindirim Sisteminin Sağlığı  .....................................................96",
     ("Sindirim Sisteminin Sağlığı", 96)),
    ("TAM SAYILAR.................................................................................17",
     ("TAM SAYILAR", 17)),
    ("1. Sindirim Sistemi  ..................................................................89 ",
     ("1. Sindirim Sistemi", 89)),
])
def test_nokta_onculu_ad_ve_sayfayi_ayirir(satir, beklenen):
    assert u.nokta_onculu(" ".join(satir.split())) == beklenen


@pytest.mark.parametrize("satir", [
    "KÜRESELLEŞMEN İN İNSAN VE TOPLUM HAYATINA ETK İSİ ...............",  # numara kopuk
    "İÇİNDEKİLER",
    "",
    "Sözlük ... 149",  # üç noktadan az
])
def test_nokta_onculu_eslesmeyen_satirda_none(satir):
    assert u.nokta_onculu(satir) is None


# Türkçe harf tuzağı: str.title() 'İ'yi 'i'+birleşen noktaya, 'I'yı 'i'ye çevirir.
@pytest.mark.parametrize("ham,beklenen", [
    ("TAM SAYILAR", "Tam Sayılar"),
    ("SİNDİRİM SİSTEMİNİN SAĞLIĞI", "Sindirim Sisteminin Sağlığı"),
    ("IŞIĞIN KIRILMASI", "Işığın Kırılması"),
    ("MİLLÎ MESELELER VE TÜRK TOPLUMU", "Millî Meseleler ve Türk Toplumu"),
    ("Sindirim Sisteminin Sağlığı", "Sindirim Sisteminin Sağlığı"),
])
def test_baslik_duzeni(ham, beklenen):
    assert u.baslik_duzeni(ham) == beklenen


def test_baslik_duzeni_harf_araligi_bozulmasini_duzeltir():
    assert u.baslik_duzeni("SOSY AL BİLİMLER") == "Sosyal Bilimler"


def test_kayma_bul_modu_ve_uyumu_dondurur():
    # (basılı, gövdede bulunan) çiftleri: 21 tanesi +1, biri -2, biri +2 (doc 439 ölçümü).
    adaylar = [(n, n + 1) for n in range(10, 31)] + [(40, 38), (50, 52)]
    assert u.kayma_bul(adaylar) == (1, "21/23")


def test_kayma_bul_uyum_esigin_altindaysa_kaymasiz():
    adaylar = [(10, 11), (20, 25), (30, 37), (40, 44), (50, 59)]
    kayma, uyum = u.kayma_bul(adaylar)
    assert kayma is None and uyum == "1/5"


def test_kayma_bul_bos_listede_kaymasiz():
    assert u.kayma_bul([]) == (None, "0/0")


def test_konu_slug_turkce_harfleri_katlar():
    assert u.konu_slug("Sindirim Sisteminin Sağlığı") == "sindirim-sisteminin-sagligi"
    assert u.konu_slug("IŞIĞIN KIRILMASI") == "isigin-kirilmasi"


def test_konu_slug_noktalamayi_duser_ve_tireyi_sadelestirir():
    assert u.konu_slug("1. Tema — Ölçme ve Değerlendirme!") == "1-tema-olcme-ve-degerlendirme"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `unshare -rn .venv/bin/python -m pytest -q tests/test_mufredat_agaci_ayristirici.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'mufredat_agaci'`

- [ ] **Step 3: Write minimal implementation**

`scripts/mufredat_agaci.py`:

```python
"""7. sınıf müfredat ağacını üretir: ders → ünite → ders kitabı alt başlığı.

Çıktı `src/mufredat_agaci.json`; elle düzenlenmez. Tek kaynak sabitlenmiş salt-okunur
müfredat veritabanıdır (spec §0). `output/modules/` altına yazılmaz — orada tek yazar ted-mcp.

Kullanım:
    .venv/bin/python scripts/mufredat_agaci.py tumu --sinif 7
"""
from __future__ import annotations

import collections
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

URI = "file:/home/mahirkurt/mcp-data/mufredat/mufredat.sqlite?mode=ro&immutable=1"

# Program PDF'lerinin metin katmanındaki harf aralığı bozulmaları; skill_unite_haritasi.py'daki
# OCR_DUZELTME ile aynı gerekçe, ders kitabı başlıklarında ölçülen biçimler.
OCR_DUZELTME = {"SOSY AL": "SOSYAL", "DÜNY A": "DÜNYA", "YAŞAY AN": "YAŞAYAN",
                "KÜL TÜRÜ": "KÜLTÜRÜ", "ETK İSİ": "ETKİSİ", "ÜLKEM İZİN": "ÜLKEMİZİN",
                "DEVLETİ ’NİN": "DEVLETİ’NİN"}
# Başlık düzeninde küçük kalan bağlaçlar (Türkçe yazım).
KUCUK_KALAN = {"ve", "ile", "veya", "ya", "da", "de", "ki"}
NOKTA_ONCULU = re.compile(r"^(?P<ad>.*?[^\s.])\s*\.{4,}\s*(?P<s>\d{1,3})$")
KAYMA_UYUM_ESIGI = 0.80


def nokta_onculu(satir: str) -> tuple[str, int] | None:
    """"Ad ....... 96" satırını (ad, 96) yapar; eşleşmezse None."""
    eslesme = NOKTA_ONCULU.match(" ".join((satir or "").split()))
    return (eslesme.group("ad"), int(eslesme.group("s"))) if eslesme else None


def harf_katla(metin: str) -> str:
    """Karşılaştırma için harf dizisi: Türkçe İ/I önce çevrilir, sonra küçültülüp aksan atılır."""
    metin = (metin or "").replace("İ", "i").replace("I", "ı").replace("ı", "i").lower()
    metin = unicodedata.normalize("NFKD", metin)
    metin = "".join(ch for ch in metin if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]", "", metin)


def _sozcuk_duzeni(sozcuk: str) -> str:
    """Türkçe'ye duyarlı tek sözcük: 'I' → 'ı', 'İ' → 'i'; str.title() bunu bozar."""
    if not sozcuk:
        return sozcuk
    bas = sozcuk[0].replace("I", "I").replace("i", "İ")
    govde = sozcuk[1:].replace("I", "ı").replace("İ", "i").lower()
    return (bas if bas.isupper() or not bas.isalpha() else bas.upper()) + govde


def baslik_duzeni(metin: str) -> str:
    """Kitaptaki büyük harfli başlığı okunabilir başlık düzenine çevirir (spec §2.3)."""
    metin = " ".join((metin or "").split())
    for yanlis, dogru in OCR_DUZELTME.items():
        metin = metin.replace(yanlis, dogru)
    sozcukler = metin.split(" ")
    cikti = []
    for sira, sozcuk in enumerate(sozcukler):
        duzenli = _sozcuk_duzeni(sozcuk)
        if sira and duzenli.lower() in KUCUK_KALAN:
            duzenli = duzenli.lower()
        cikti.append(duzenli)
    return " ".join(cikti)


def konu_slug(ad: str) -> str:
    """module_store.SLUG_RE alfabesinde kimlik gövdesi."""
    katlanmis = (ad or "").replace("İ", "i").replace("I", "ı").replace("ı", "i").lower()
    katlanmis = unicodedata.normalize("NFKD", katlanmis)
    katlanmis = "".join(ch for ch in katlanmis if not unicodedata.combining(ch))
    return re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9]+", "-", katlanmis)).strip("-")


def kayma_bul(adaylar: list[tuple[int, int]]) -> tuple[int | None, str]:
    """(basılı, gövdede bulunan) çiftlerinden basılı→PDF kaymasının modunu türetir.

    Kayma uydurulmaz: uyum oranı KAYMA_UYUM_ESIGI'nin altındaysa kayma None döner ve
    çağıran o kitabın bütün konularını `sayfa_kaynak: "yok"` yazar (spec §2.2).
    """
    if not adaylar:
        return None, "0/0"
    sayac = collections.Counter(bulunan - basili for basili, bulunan in adaylar)
    kayma, adet = sayac.most_common(1)[0]
    uyum = f"{adet}/{len(adaylar)}"
    return (kayma if adet / len(adaylar) >= KAYMA_UYUM_ESIGI else None), uyum
```

- [ ] **Step 4: Run test to verify it passes**

Run: `unshare -rn .venv/bin/python -m pytest -q tests/test_mufredat_agaci_ayristirici.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/mufredat_agaci.py tests/test_mufredat_agaci_ayristirici.py
git commit -m "feat(moduller): üreticinin saf ayrıştırıcıları (içindekiler, başlık düzeni, kayma)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: Üreticinin veritabanı katmanı

Program ünitelerini, kazanımları, kitapları ve sayfa metinlerini okur. DB makineye bağlı olduğu için bu testler DB yokken atlanır; Görev 2'nin ayrıştırıcı testleri atlanmaz.

**Files:**
- Modify: `scripts/mufredat_agaci.py` (DB katmanı eklenir)
- Create: `tests/test_mufredat_agaci_db.py`

**Interfaces:**
- Consumes: Görev 2'nin `harf_katla`, `nokta_onculu`.
- Produces:
  - `DERSLER: dict[str, Ders]` — `Ders` adlandırılmış demet: `(ad, subject_slug, program_id, sayfa_araligi, unite_deseni, kazanim_deseni, kitaplar)`
  - `baglan() -> sqlite3.Connection`
  - `program_uniteleri(baglanti, ders) -> list[dict]` — `{"no", "ad", "program_sayfa"}`
  - `program_kazanimlari(baglanti, ders) -> list[dict]` — `{"kod", "unite_no", "metin"}`
  - `kitap_sayfalari(baglanti, document_id) -> dict[int, str]`
  - `icindekiler_satirlari(baglanti, document_id) -> list[tuple[str, int]]`

- [ ] **Step 1: Write the failing test**

`tests/test_mufredat_agaci_db.py`:

```python
"""Üreticinin veritabanı katmanı. DB makineye bağlı; yoksa atlanır (spec §6.1)."""
import sqlite3
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK / "scripts"))

import mufredat_agaci as u  # noqa: E402


def _db_var() -> bool:
    try:
        u.baglan().execute("select 1 from document limit 1").fetchone()
        return True
    except sqlite3.Error:
        return False


pytestmark = pytest.mark.skipif(not _db_var(), reason="müfredat veritabanı bu makinede yok")


@pytest.fixture(scope="module")
def baglanti():
    return u.baglan()


def test_dort_ders_tanimli():
    assert set(u.DERSLER) == {"turkce", "matematik", "fen", "sosyal"}


def test_her_dersin_kitaplari_yedinci_sinif_ders_kitabi(baglanti):
    for slug, ders in u.DERSLER.items():
        for kitap_id in ders.kitaplar:
            satir = baglanti.execute(
                "select kind, grades_csv from document where id=?", (kitap_id,)).fetchone()
            assert satir is not None, f"{slug}: {kitap_id} yok"
            assert satir[0] == "textbook" and "7.Sınıf" in (satir[1] or "")


def test_fen_program_uniteleri_yedi_unite(baglanti):
    # src/assistant_skills/fen/references/unite-haritasi.md: 7 ünite, ilki "Uzay Çağı" s.146.
    uniteler = u.program_uniteleri(baglanti, u.DERSLER["fen"])
    assert len(uniteler) == 7
    assert uniteler[0]["no"] == 1 and "Uzay Çağı" in uniteler[0]["ad"]
    assert uniteler[0]["program_sayfa"] == 146


def test_fen_kazanimlari_unite_numarasini_kodundan_tasir(baglanti):
    kazanimlar = u.program_kazanimlari(baglanti, u.DERSLER["fen"])
    kodlar = {k["kod"] for k in kazanimlar}
    assert "FB.7.3.2" in kodlar
    assert next(k for k in kazanimlar if k["kod"] == "FB.7.3.2")["unite_no"] == 3


def test_icindekiler_satirlari_fen_ve_matematikte_dolu(baglanti):
    # Ölçüldü (spec §0): Fen 1 → 37, Mat 1 → 33 nokta öncüllü satır.
    assert len(u.icindekiler_satirlari(baglanti, 439)) >= 30
    assert len(u.icindekiler_satirlari(baglanti, 346)) >= 30


def test_icindekiler_satirlari_turkce_ve_sosyalde_bos(baglanti):
    # Ölçüldü (spec §0): iki sütunlu düzen, sayfa numarası başlıktan kopuk → 0 eşleşme.
    assert u.icindekiler_satirlari(baglanti, 460) == []
    assert u.icindekiler_satirlari(baglanti, 491) == []


def test_kitap_sayfalari_metin_dondurur(baglanti):
    sayfalar = u.kitap_sayfalari(baglanti, 439)
    assert len(sayfalar) > 100 and isinstance(sayfalar[10], str)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_mufredat_agaci_db.py`
Expected: FAIL — `AttributeError: module 'mufredat_agaci' has no attribute 'baglan'`
(DB bu makinede yoksa: tüm testler SKIPPED — o hâlde bu görev atlanıp Görev 4'ün altın verili kısmına geçilir ve durum rapor edilir.)

- [ ] **Step 3: Write minimal implementation**

`scripts/mufredat_agaci.py` sonuna ekle:

```python
import sqlite3  # noqa: E402  (dosya başındaki import bloğuna taşınır)
from typing import NamedTuple  # noqa: E402


class Ders(NamedTuple):
    ad: str
    subject_slug: str
    program_id: int
    sayfa_araligi: tuple[int, int]
    unite_deseni: str
    kazanim_deseni: str
    kitaplar: tuple[int, ...]


# Program kimlikleri, sayfa aralıkları ve desenler scripts/skill_unite_haritasi.py'ın DERSLER
# tablosundan birebir alındı (orada "ölçüldü 2026-09-27"); yeniden ölçülmez. Kitap kimlikleri
# 2026-10-11'de ölçüldü (spec §0).
DERSLER = {
    "matematik": Ders("Matematik", "ortaokul-matematik-dersi", 24, (115, 172),
                      r"^\s*(\d+)\.\s*TEMA:\s*(.+)$", r"^MAT\.7\.(\d+)\.(\d+)$", (346, 506)),
    "fen": Ders("Fen Bilimleri", "fen-bilimleri-dersi", 54, (146, 183),
                r"^\s*(\d+)\.\s*ÜNİTE:\s*(.+)$", r"^FB\.7\.(\d+)\.(\d+)$", (439, 473)),
    "sosyal": Ders("Sosyal Bilgiler", "sosyal-bilgiler-dersi", 100, (93, 122),
                   r"^\s*(\d+)\.\s*ÖĞRENME ALANI:\s*(.+)$", r"^SB\.7\.(\d+)\.(\d+)$", (491, 361)),
    "turkce": Ders("Türkçe", "ortaokul-turkce-dersi", 51, (126, 161),
                   r"^\s*(\d+)\.\s*TEMA:\s*(.+)$", r"^(T\.[DOKY]|DYS\.(?:DO|KY))\.7\.(\d+)$",
                   (460, 340)),
}
ICINDEKILER_ARAMA_SINIRI = 14


def baglan() -> sqlite3.Connection:
    return sqlite3.connect(URI, uri=True)


def _program_sayfalari(baglanti: sqlite3.Connection, ders: Ders) -> list[tuple[int, str]]:
    ilk, son = ders.sayfa_araligi
    return list(baglanti.execute(
        "select page_no, text from document_page where document_id=? and page_no between ? and ?"
        " order by page_no", (ders.program_id, ilk, son)))


def program_uniteleri(baglanti: sqlite3.Connection, ders: Ders) -> list[dict]:
    """Programın 7. sınıf sayfalarındaki ünite/tema başlıkları, görüldükleri sayfayla."""
    desen = re.compile(ders.unite_deseni)
    gorulen: dict[int, dict] = {}
    for sayfa_no, metin in _program_sayfalari(baglanti, ders):
        for satir in (metin or "").splitlines():
            eslesme = desen.match(" ".join(satir.split()))
            if not eslesme:
                continue
            no = int(eslesme.group(1))
            if no not in gorulen:
                gorulen[no] = {"no": no, "ad": baslik_duzeni(eslesme.group(2).strip(" :")),
                               "program_sayfa": sayfa_no}
    return [gorulen[no] for no in sorted(gorulen)]


def program_kazanimlari(baglanti: sqlite3.Connection, ders: Ders) -> list[dict]:
    """7. sınıf kazanımları. `unite_no`, kodun ortasındaki sayıdır; Türkçe'de None."""
    desen = re.compile(ders.kazanim_deseni)
    cikti: dict[str, dict] = {}
    satirlar = baglanti.execute(
        "select lo.code, lo.text from learning_outcome lo join subject s on s.id = lo.subject_id"
        " where s.slug = ? and lo.grade_label like '%7%' and lo.fragment_type = 'outcome'",
        (ders.subject_slug,))
    for kod, metin in satirlar:
        eslesme = desen.match(kod or "")
        if not eslesme or kod in cikti:
            continue
        gruplar = eslesme.groups()
        # Türkçe deseni beceri alanı + sıra verir; ünite numarası taşımaz.
        unite_no = int(gruplar[0]) if len(gruplar) == 2 and gruplar[0].isdigit() else None
        cikti[kod] = {"kod": kod, "unite_no": unite_no, "metin": " ".join((metin or "").split())}
    return [cikti[kod] for kod in sorted(cikti)]


def kitap_sayfalari(baglanti: sqlite3.Connection, document_id: int) -> dict[int, str]:
    return {no: (metin or "") for no, metin in baglanti.execute(
        "select page_no, text from document_page where document_id=?", (document_id,))}


def icindekiler_satirlari(baglanti: sqlite3.Connection, document_id: int) -> list[tuple[str, int]]:
    """Kitabın ilk sayfalarındaki nokta öncüllü içindekiler satırları, görüldükleri sırada."""
    cikti: list[tuple[str, int]] = []
    for _, metin in baglanti.execute(
            "select page_no, text from document_page where document_id=? and page_no<=? order by page_no",
            (document_id, ICINDEKILER_ARAMA_SINIRI)):
        for satir in (metin or "").splitlines():
            ayristi = nokta_onculu(satir)
            if ayristi and len(harf_katla(ayristi[0])) >= 8:
                cikti.append(ayristi)
    return cikti
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_mufredat_agaci_db.py tests/test_mufredat_agaci_ayristirici.py`
Expected: PASS (DB yoksa `tests/test_mufredat_agaci_db.py` SKIPPED, ayrıştırıcı PASS)

- [ ] **Step 5: Commit**

```bash
git add scripts/mufredat_agaci.py tests/test_mufredat_agaci_db.py
git commit -m "feat(moduller): üreticinin veritabanı katmanı (program üniteleri, kazanımlar, içindekiler)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: Üretici — konu üretimi, eşik, dosya yazımı

Parçaları birleştirir, `src/mufredat_agaci.json`'ı yazar, kapsam raporunu basar.

**Files:**
- Modify: `scripts/mufredat_agaci.py` (montaj + CLI)
- Create: `tests/test_mufredat_agaci_uretim.py`
- Create: `src/mufredat_agaci.json` (üreticinin çıktısı, commit'lenir)

**Interfaces:**
- Consumes: Görev 1 `src.mufredat_agaci.dogrula`; Görev 2 `kayma_bul`, `baslik_duzeni`, `konu_slug`; Görev 3 `DERSLER`, `baglan`, `program_uniteleri`, `program_kazanimlari`, `kitap_sayfalari`, `icindekiler_satirlari`.
- Produces:
  - `KONU_ESIGI: float = 0.60`
  - `gecersiz_sayfa(sayfa, sayfa_sayisi) -> bool`
  - `kimlik_ver(ders_slug, unite_no, ad, kullanilan: set[str]) -> tuple[str, bool]` — `(id, cakisti)`
  - `kazanim_esle(konu_metni, kazanimlar) -> tuple[list[str], str]`
  - `kitap_kaymasi(baglanti, kitap_id) -> tuple[int | None, str]`
  - `aparat_mi(ad) -> bool`
  - `ders_uret(baglanti, slug) -> tuple[dict | None, dict]` — `(ders kaydı | None, kapsam)`
  - `agac_uret(baglanti, sluglar) -> dict`
  - `main(argv) -> int`

- [ ] **Step 1: Write the failing test**

`tests/test_mufredat_agaci_uretim.py`:

```python
"""Üretim montajı: kimlik kararlılığı, bozuk sayfa, eşik, kayma kapısı (spec §2.2, §6.1)."""
import sqlite3
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK / "scripts"))

import mufredat_agaci as u  # noqa: E402
from src import mufredat_agaci as ma  # noqa: E402


# Review Focus 2: aynı ünitede aynı adlı iki konu.
def test_kimlik_cakismasi_sessizce_yutmaz():
    kullanilan: set[str] = set()
    birinci, cakisti1 = u.kimlik_ver("fen", 3, "Sindirim Sisteminin Sağlığı", kullanilan)
    ikinci, cakisti2 = u.kimlik_ver("fen", 3, "Sindirim Sisteminin Sağlığı", kullanilan)
    assert birinci == "fen-u3-sindirim-sisteminin-sagligi"
    assert ikinci == "fen-u3-sindirim-sisteminin-sagligi-2"
    assert (cakisti1, cakisti2) == (False, True)


def test_kimlik_sirasal_sayi_tasimaz():
    kullanilan: set[str] = set()
    kimlik, _ = u.kimlik_ver("fen", 3, "Dolaşım Sistemi", kullanilan)
    assert kimlik == "fen-u3-dolasim-sistemi"


# Review Focus 3: bozuk sayfa aralığı.
@pytest.mark.parametrize("sayfa", [[101, 97], [0, 5], [-3, 2], [150, 400], None, [97]])
def test_gecersiz_sayfa_reddedilir(sayfa):
    assert u.gecersiz_sayfa(sayfa, 153) is True


def test_gecerli_sayfa_kabul_edilir():
    assert u.gecersiz_sayfa([97, 101], 153) is False


def test_kazanim_eslenmeyince_kaynak_eslenmedi_olur():
    kodlar, kaynak = u.kazanim_esle("bambaşka bir metin", [
        {"kod": "FB.7.3.2", "unite_no": 3, "metin": "sindirim sisteminin sağlığı için bilgi toplayabilme"}])
    assert kodlar == [] and kaynak == "eslenmedi"


def test_kazanim_metin_ortusmesiyle_eslenir():
    kodlar, kaynak = u.kazanim_esle(
        "Sindirim sisteminin sağlığı için yapılması gerekenler",
        [{"kod": "FB.7.3.2", "unite_no": 3,
          "metin": "Sindirim sisteminin sağlığı için yapılması gerekenler konusunda bilgi toplayabilme"}])
    assert kodlar == ["FB.7.3.2"] and kaynak == "metin-ortusmesi"


def _db_var() -> bool:
    try:
        u.baglan().execute("select 1 from document limit 1").fetchone()
        return True
    except sqlite3.Error:
        return False


canli = pytest.mark.skipif(not _db_var(), reason="müfredat veritabanı bu makinede yok")


# Bugünün ölçümü kapıya dönüşür (spec §6.1).
@canli
@pytest.mark.parametrize("kitap_id,beklenen_kayma", [(439, 1), (473, 1), (346, 0), (506, 0)])
def test_turetilen_kayma_olculen_degerle_ayni(kitap_id, beklenen_kayma):
    baglanti = u.baglan()
    kayma, uyum = u.kitap_kaymasi(baglanti, kitap_id)
    assert kayma == beklenen_kayma, f"{kitap_id}: kayma {kayma}, uyum {uyum}"


@canli
def test_turkce_konulari_kazanim_kodu_tasimaz():
    baglanti = u.baglan()
    ders, _ = u.ders_uret(baglanti, "turkce")
    if ders is None:
        pytest.skip("Türkçe eşiğe takıldı; yüzey 'haritası henüz hazır değil' der")
    for unite in ders["uniteler"]:
        for konu in unite["konular"]:
            assert konu["kazanimlar"] == [] and konu["kazanim_kaynak"] == "eslenmedi"


@canli
def test_uretilen_agac_semaya_uyar():
    baglanti = u.baglan()
    agac = u.agac_uret(baglanti, list(u.DERSLER))
    assert ma.dogrula(agac) == []


@canli
def test_depodaki_dosya_semaya_uyar():
    durum, agac = ma.oku(ma.agac_yolu(KOK / "src"))
    assert durum == "ok" and agac is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_mufredat_agaci_uretim.py`
Expected: FAIL — `AttributeError: module 'mufredat_agaci' has no attribute 'kimlik_ver'`

- [ ] **Step 3: Write minimal implementation**

`scripts/mufredat_agaci.py` sonuna ekle:

```python
import argparse  # noqa: E402  (dosya başındaki import bloğuna taşınır)
import json  # noqa: E402

from src import mufredat_agaci as ma  # noqa: E402

KONU_ESIGI = 0.60
# Eşleme için anlamsız olan içindekiler satırları: ünite içi konu değil, kitap aparatı.
APARAT = ("on degerlendirme", "unite sonu degerlendirme", "neler biliyoruz", "neler ogrendik",
          "baslayalim", "ogrenelim", "kitabimizi taniyalim", "sozluk", "kaynakca",
          "cevap anahtari", "icindekiler", "iz birakanlar", "kendimi degerlendiriyorum",
          "olcme ve degerlendirme sorulari", "uretim vakti", "oz degerlendirme formlari")
# Kazanım eşlemesi için gereken en az örtüşme: kazanımın içerik sözcüklerinin bu oranı
# konunun adında geçmeli. Altındaysa eşleme yapılmaz (uydurma yerine boşluk).
ORTUSME_ESIGI = 0.60
DURAK = {"ve", "ile", "icin", "bir", "bu", "o", "gerekenler", "konusunda", "yonelik", "uzerinde",
         "iliskin", "hareketle", "gercek", "yasam", "durumlari", "durumlarinda", "yapilmasi"}


def aparat_mi(ad: str) -> bool:
    return harf_katla(ad) in {harf_katla(a) for a in APARAT}


def gecersiz_sayfa(sayfa: object, sayfa_sayisi: int) -> bool:
    """Bozuk aralık sessizce yazılmaz: sayfa uydurmamak kuralının aritmetik yüzü (spec §2.1)."""
    if not isinstance(sayfa, list) or len(sayfa) != 2:
        return True
    if not all(isinstance(s, int) and not isinstance(s, bool) for s in sayfa):
        return True
    bas, son = sayfa
    return bas < 1 or son < bas or son > sayfa_sayisi


def kimlik_ver(ders_slug: str, unite_no: int, ad: str, kullanilan: set[str]) -> tuple[str, bool]:
    """`<ders>-u<no>-<ad slug'ı>`; sırasal sayı yok. Çakışmada `-2`, `-3`… ve çakıştı bayrağı."""
    taban = f"{ders_slug}-u{unite_no}-{konu_slug(ad)}"
    if taban not in kullanilan:
        kullanilan.add(taban)
        return taban, False
    sira = 2
    while f"{taban}-{sira}" in kullanilan:
        sira += 1
    kimlik = f"{taban}-{sira}"
    kullanilan.add(kimlik)
    return kimlik, True


def _icerik_sozcukleri(metin: str) -> set[str]:
    sozcukler = {harf_katla(s) for s in (metin or "").split()}
    return {s for s in sozcukler if len(s) >= 4 and s not in {harf_katla(d) for d in DURAK}}


def kazanim_esle(konu_metni: str, kazanimlar: list[dict]) -> tuple[list[str], str]:
    """Kanıta dayalı eşleme: kazanımın içerik sözcüklerinin konu adında örtüşme oranı.

    Kod sırasına göre eşleme YASAK (spec §3): Fen'de 1:1 görünmesi Matematik'te yanlış olur.
    Örtüşme eşiğin altındaysa boş liste ve "eslenmedi" döner.
    """
    konu = _icerik_sozcukleri(konu_metni)
    if not konu:
        return [], "eslenmedi"
    esleşen = []
    for kazanim in kazanimlar:
        hedef = _icerik_sozcukleri(kazanim["metin"])
        if hedef and len(hedef & konu) / len(hedef) >= ORTUSME_ESIGI:
            esleşen.append(kazanim["kod"])
    return (sorted(esleşen), "metin-ortusmesi") if esleşen else ([], "eslenmedi")


def kitap_kaymasi(baglanti: sqlite3.Connection, kitap_id: int) -> tuple[int | None, str]:
    """İçindekilerdeki basılı numara ↔ başlığın gövdede geçtiği sayfadan kaymayı türetir."""
    satirlar = icindekiler_satirlari(baglanti, kitap_id)
    sayfalar = {no: harf_katla(metin) for no, metin in kitap_sayfalari(baglanti, kitap_id).items()}
    adaylar: list[tuple[int, int]] = []
    for ad, basili in satirlar:
        anahtar = harf_katla(ad)
        for fark in (0, 1, -1, 2, -2, 3, -3):
            aday = basili + fark
            if anahtar and anahtar in sayfalar.get(aday, ""):
                adaylar.append((basili, aday))
                break
    return kayma_bul(adaylar)


def _kitap_konulari(baglanti: sqlite3.Connection, kitap_id: int) -> list[tuple[str, int]]:
    return [(ad, basili) for ad, basili in icindekiler_satirlari(baglanti, kitap_id)
            if not aparat_mi(ad)]


def ders_uret(baglanti: sqlite3.Connection, slug: str) -> tuple[dict | None, dict]:
    """Bir dersin kaydı ve kapsamı. Eşiğe takılırsa (None, kapsam) — yarım yazılmaz (spec §2.2)."""
    ders = DERSLER[slug]
    uniteler = program_uniteleri(baglanti, ders)
    kazanimlar = program_kazanimlari(baglanti, ders)
    kitaplar, konular_ham = [], []
    for kitap_id in ders.kitaplar:
        kayma, uyum = kitap_kaymasi(baglanti, kitap_id)
        sayfa_sayisi = len(kitap_sayfalari(baglanti, kitap_id))
        kitaplar.append({"document_id": kitap_id,
                         "kisa": f"{ders.kitaplar.index(kitap_id) + 1}. Kitap",
                         "sayfa_kaymasi": kayma, "kayma_uyumu": uyum})
        for ad, basili in _kitap_konulari(baglanti, kitap_id):
            konular_ham.append((kitap_id, ad, basili, kayma, sayfa_sayisi))

    kullanilan: set[str] = set()
    cakisma = 0
    unite_konulari: dict[int, list[dict]] = {u["no"]: [] for u in uniteler}
    for kitap_id, ad, basili, kayma, sayfa_sayisi in konular_ham:
        duzgun = baslik_duzeni(ad)
        kodlar, kaynak = kazanim_esle(duzgun, kazanimlar)
        # Ünite ataması: Türkçe'de kazanım yok → kitabın içindekiler sırası; diğerlerinde kodun
        # ortasındaki ünite numarası (spec §3).
        unite_no = next((k["unite_no"] for k in kazanimlar if k["kod"] in kodlar
                         and k["unite_no"] is not None), None)
        if unite_no is None or unite_no not in unite_konulari:
            continue
        sayfa = None if kayma is None else [basili + kayma, basili + kayma]
        if sayfa is not None and gecersiz_sayfa(sayfa, sayfa_sayisi):
            sayfa = None
        kimlik, cakisti = kimlik_ver(slug, unite_no, duzgun, kullanilan)
        cakisma += int(cakisti)
        konu = {"id": kimlik, "ad": duzgun, "ad_kaynak": " ".join(ad.split()),
                "kitap": kitap_id, "kazanimlar": kodlar, "kazanim_kaynak": kaynak}
        if sayfa is None:
            konu["sayfa_kaynak"] = "yok"
        else:
            konu["sayfa"], konu["sayfa_kaynak"] = sayfa, "icindekiler"
        unite_konulari[unite_no].append(konu)

    toplam = sum(len(k) for k in unite_konulari.values())
    beklenen = max(len(konular_ham), 1)
    kapsam = {"konu": toplam, "sayfasi_olan": sum(
        1 for k in unite_konulari.values() for konu in k if konu["sayfa_kaynak"] == "icindekiler"),
        "kazanimi_eslenen": sum(1 for k in unite_konulari.values() for konu in k
                                if konu["kazanim_kaynak"] == "metin-ortusmesi"),
        "kitap_satiri": len(konular_ham), "kimlik_cakismasi": cakisma}
    if toplam / beklenen < KONU_ESIGI:
        kapsam["yazilmadi"] = "konu_esigi"
        return None, kapsam
    kayit = {"ders": ders.ad, "slug": slug,
             "program": {"document_id": ders.program_id,
                         "sayfa": f"{ders.sayfa_araligi[0]}-{ders.sayfa_araligi[1]}"},
             "kitaplar": kitaplar,
             "uniteler": [{**unite, "konular": unite_konulari[unite["no"]]} for unite in uniteler]}
    return kayit, kapsam


def agac_uret(baglanti: sqlite3.Connection, sluglar: list[str]) -> dict:
    dersler, kapsam = [], {}
    for slug in sluglar:
        kayit, ders_kapsami = ders_uret(baglanti, slug)
        kapsam[slug] = ders_kapsami
        if kayit is not None:
            dersler.append(kayit)
    surum = baglanti.execute(
        "select value from manifest where key like '%version%' limit 1").fetchone()
    return {"surum": 1, "korpus_surumu": str(surum[0]) if surum else "bilinmiyor",
            "sinif": "7. Sınıf", "dersler": dersler, "kapsam": kapsam}


def main(argv: list[str] | None = None) -> int:
    ayristirici = argparse.ArgumentParser(description="7. sınıf müfredat ağacını üretir.")
    ayristirici.add_argument("ders", choices=[*DERSLER, "tumu"])
    ayristirici.add_argument("--sinif", default="7")
    ayristirici.add_argument("--cikti", default=str(
        Path(__file__).resolve().parents[1] / "src" / ma.AGAC_ADI))
    secenekler = ayristirici.parse_args(argv)
    if secenekler.sinif != "7":
        print("Bu dalda yalnız 7. sınıf üretilir (spec §1).", file=sys.stderr)
        return 2
    sluglar = list(DERSLER) if secenekler.ders == "tumu" else [secenekler.ders]
    agac = agac_uret(baglan(), sluglar)
    hatalar = ma.dogrula(agac)
    if hatalar:
        print("Üretilen ağaç şemaya uymuyor:", file=sys.stderr)
        for hata in hatalar[:20]:
            print(f"  {hata}", file=sys.stderr)
        return 1
    Path(secenekler.cikti).write_text(
        json.dumps(agac, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for slug, kapsam in agac["kapsam"].items():
        print(f"{slug:<10} {kapsam}")
    yazilmayan = [s for s, k in agac["kapsam"].items() if k.get("yazilmadi")]
    if yazilmayan:
        print(f"Eşiğe takılan ders(ler): {', '.join(yazilmayan)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest -q tests/test_mufredat_agaci_uretim.py tests/test_mufredat_agaci_ayristirici.py tests/test_mufredat_agaci.py`
Expected: PASS

- [ ] **Step 5: Üreticiyi koş ve kapsam raporunu oku**

Run: `.venv/bin/python scripts/mufredat_agaci.py tumu --sinif 7`

Her ders için `konu`, `sayfasi_olan`, `kazanimi_eslenen`, `kitap_satiri`, `kimlik_cakismasi` satırını oku. Beklenen: Fen ve Matematik `sayfasi_olan > 0`; Türkçe ve Sosyal `sayfasi_olan == 0` (ölçüldü: içindekilerinde nokta öncüllü satır yok). Bir ders `yazilmadi: "konu_esigi"` ile çıkarsa komut 1 döner — bu bir **başarısızlık değil**, spec §2.2'nin istediği davranıştır; o dersi raporla ve devam et.

- [ ] **Step 6: Commit**

```bash
git add scripts/mufredat_agaci.py tests/test_mufredat_agaci_uretim.py src/mufredat_agaci.json
git commit -m "feat(moduller): müfredat ağacı üreticisi ve üretilen ağaç

Turetilen kayma, olculen degerlerle test altinda: doc 439/473 +1, doc 346/506 0.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: `/api/modules/agac` ucu

**Files:**
- Modify: `src/dashboard_api.py` (ağaç önbelleği + uç; `modules_list`'in hemen altına)
- Modify: `tests/test_dashboard_api.py`

**Interfaces:**
- Consumes: Görev 1 `src.mufredat_agaci.{agac_yolu, oku, konular}`; `module_store.{read_catalog, latest_active}`.
- Produces:
  - `MUFREDAT_AGACI_PATH: str` (modül düzeyi, testler `monkeypatch`'ler)
  - `_mufredat_agaci() -> tuple[str, dict | None]` — stat imzalı önbellek
  - `_agac_modul_eslemesi(agac, rows) -> dict[str, dict]` — konu id → modül kartı
  - uç: `GET /api/modules/agac` → `{"hazir": [...], "dersler": [...], "kapsam": {...}, "hata": None | "harita_okunamadi"}`

- [ ] **Step 1: Write the failing test**

`tests/test_dashboard_api.py` sonuna ekle:

```python
# ── Müfredat ağacı ucu (spec §4) ────────────────────────────────────────────

_AGAC_GOVDESI = {
    "surum": 1, "korpus_surumu": "1.6", "sinif": "7. Sınıf",
    "dersler": [{
        "ders": "Matematik", "slug": "matematik",
        "program": {"document_id": 24, "sayfa": "115-172"},
        "kitaplar": [{"document_id": 346, "kisa": "1. Kitap",
                      "sayfa_kaymasi": 0, "kayma_uyumu": "35/35"}],
        "uniteler": [{
            "no": 1, "ad": "Sayılar ve Nicelikler", "program_sayfa": 115,
            "konular": [
                {"id": "matematik-u1-tam-sayilar", "ad": "Tam Sayılar",
                 "ad_kaynak": "TAM SAYILAR", "kitap": 346, "sayfa": [17, 24],
                 "sayfa_kaynak": "icindekiler", "kazanimlar": ["MAT.7.1.1"],
                 "kazanim_kaynak": "metin-ortusmesi"},
                {"id": "matematik-u1-mutlak-deger", "ad": "Mutlak Değer",
                 "ad_kaynak": "MUTLAK DEĞER", "kitap": 346,
                 "sayfa_kaynak": "yok", "kazanimlar": [],
                 "kazanim_kaynak": "eslenmedi"},
            ],
        }],
    }],
    "kapsam": {"matematik": {"konu": 2, "sayfasi_olan": 1, "kazanimi_eslenen": 1}},
}


@pytest.fixture
def agac_dosyasi(tmp_path, monkeypatch):
    def yaz(govde):
        yol = tmp_path / "mufredat_agaci.json"
        yol.write_text(json.dumps(govde) if not isinstance(govde, str) else govde, encoding="utf-8")
        monkeypatch.setattr(dashboard_api, "MUFREDAT_AGACI_PATH", str(yol))
        # Önbellek stat imzalı: yol değişince imza da değişir, elle temizlemek gerekmez.
        return yol
    return yaz


def test_agac_ucu_dersleri_ve_kapsami_dondurur(client, agac_dosyasi):
    agac_dosyasi(_AGAC_GOVDESI)
    govde = client.get("/api/modules/agac").get_json()
    assert govde["hata"] is None
    assert [d["slug"] for d in govde["dersler"]] == ["matematik"]
    assert govde["kapsam"]["matematik"]["konu"] == 2


def test_agac_ucu_yayinlanmis_modulu_kazanimiyla_konuya_bagliyor(client, agac_dosyasi):
    agac_dosyasi(_AGAC_GOVDESI)
    govde = client.get("/api/modules/agac").get_json()
    konular = govde["dersler"][0]["uniteler"][0]["konular"]
    tam_sayilar = next(k for k in konular if k["id"] == "matematik-u1-tam-sayilar")
    mutlak = next(k for k in konular if k["id"] == "matematik-u1-mutlak-deger")
    # output/modules/index.json'daki mat7-tam-sayilar MAT.7.1.1 taşıyor.
    assert tam_sayilar["modul"]["slug"] == "mat7-tam-sayilar"
    assert mutlak["modul"] is None


def test_agac_ucu_hazir_listesinde_agaca_eslenmeyen_modul_de_var(client, agac_dosyasi):
    agac_dosyasi(_AGAC_GOVDESI)
    govde = client.get("/api/modules/agac").get_json()
    sluglar = {m["slug"] for m in govde["hazir"]}
    # Fen ve Sosyal modülleri bu ağaçta hiç yok ama listede görünmeli (spec §4).
    assert "mat7-tam-sayilar" in sluglar and len(sluglar) >= 1


# Review Focus 1: geçerli JSON ama şema dışı → 500 değil.
@pytest.mark.parametrize("govde", ['{ bu json degil', '{"surum": 1, "dersler": {}}', '{}'])
def test_agac_ucu_bozuk_dosyada_500_vermiyor(client, agac_dosyasi, govde):
    agac_dosyasi(govde)
    yanit = client.get("/api/modules/agac")
    assert yanit.status_code == 200
    payload = yanit.get_json()
    assert payload["dersler"] == [] and payload["hata"] == "harita_okunamadi"
    assert payload["kapsam"] == {}


def test_agac_ucu_dosya_yokken_de_hazir_listesi_veriyor(client, tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard_api, "MUFREDAT_AGACI_PATH", str(tmp_path / "yok.json"))
    payload = client.get("/api/modules/agac").get_json()
    assert payload["hata"] == "harita_okunamadi" and isinstance(payload["hazir"], list)


# Review Focus 4: yetkisiz çağrı.
def test_agac_ucu_oturumsuz_cagriyi_reddediyor(client_no_auth):
    assert client_no_auth.get("/api/modules/agac").status_code in (401, 403)


def test_agac_ucu_okur_rolunde_reddediyor(client, monkeypatch):
    monkeypatch.setattr(dashboard_api, "TEST_AUTH_BYPASS", False)
    with client.session_transaction() as oturum:
        oturum["user"] = {"email": next(
            e for e, r in dashboard_api.USER_ROLES.items() if r == "reader")}
    assert client.get("/api/modules/agac").status_code == 403
```

- [ ] **Step 2: Run test to verify it fails**

Run: `TEST_AUTH_BYPASS=1 .venv/bin/python -m pytest -q tests/test_dashboard_api.py -k agac_ucu`
Expected: FAIL — 404 (rota yok) / `AttributeError: MUFREDAT_AGACI_PATH`

- [ ] **Step 3: Write minimal implementation**

`src/dashboard_api.py`, `modules_list`'in hemen altına:

```python
# ── Müfredat ağacı (spec §4) ────────────────────────────────────────────────
# Dosya depoda izlenir ve `scripts/mufredat_agaci.py` tarafından üretilir; burada yalnız okunur.
MUFREDAT_AGACI_PATH = str(mufredat_agaci.agac_yolu(os.path.dirname(os.path.abspath(__file__))))
_AGAC_ONBELLEGI: dict[str, Any] = {"imza": None, "durum": "yok", "agac": None}
_AGAC_KILIDI = threading.Lock()


def _agac_imzasi(yol):
    """src.assistant_modules._stat ile aynı desen: atomik değiştirilen dosyayı stat ile izler."""
    try:
        st = os.stat(yol)
    except OSError:
        return None
    return (st.st_ino, st.st_size, st.st_mtime_ns)


def _mufredat_agaci():
    """("ok", ağaç) | ("yok", None) | ("bozuk", None). Dosya değişince kendini yeniler —
    gunicorn'un iki işçisi de yeniden başlatılmadan yeni ağacı görür."""
    yol = MUFREDAT_AGACI_PATH
    imza = _agac_imzasi(yol)
    onbellek = _AGAC_ONBELLEGI
    if onbellek["imza"] == imza and imza is not None:
        return onbellek["durum"], onbellek["agac"]
    with _AGAC_KILIDI:
        imza = _agac_imzasi(yol)
        if _AGAC_ONBELLEGI["imza"] == imza and imza is not None:
            return _AGAC_ONBELLEGI["durum"], _AGAC_ONBELLEGI["agac"]
        durum, agac = mufredat_agaci.oku(yol)
        _AGAC_ONBELLEGI.update({"imza": imza, "durum": durum, "agac": agac})
        return durum, agac


def _modul_sayfa_ortusmesi(row, konu):
    """Modülün frame_source sayfaları ile konunun sayfa aralığının kesişim uzunluğu."""
    sayfa = konu.get("sayfa")
    kaynak = row.get("frame_source") or {}
    if not isinstance(sayfa, list) or len(sayfa) != 2:
        return 0
    eslesme = re.match(r"^(\d+)(?:\s*-\s*(\d+))?$", str(kaynak.get("pages") or "").strip())
    if not eslesme:
        return 0
    bas = int(eslesme.group(1))
    son = int(eslesme.group(2) or bas)
    return max(0, min(son, sayfa[1]) - max(bas, sayfa[0]) + 1)


def _agac_modul_eslemesi(agac, rows):
    """Konu kimliği → modül kartı. Bir modül yalnız BİR konuya bağlanır: sayfa örtüşmesi en iyi
    olana, o da yoksa sıradaki ilkine (spec §3.1). Aynı modül iki satırda görünmez."""
    eslesme = {}
    for row in rows:
        kodlar = {k for k in (row.get("outcomes") or []) if isinstance(k, str)}
        if not kodlar:
            continue
        adaylar = [konu for _, _, konu in mufredat_agaci.konular(agac)
                   if kodlar & set(konu.get("kazanimlar") or [])]
        adaylar = [k for k in adaylar if k["id"] not in eslesme]
        if not adaylar:
            continue
        en_iyi = max(adaylar, key=lambda konu: _modul_sayfa_ortusmesi(row, konu))
        eslesme[en_iyi["id"]] = {key: row.get(key) for key in _MODULE_CARD_FIELDS}
    return eslesme


@app.route("/api/modules/agac")
@require_auth
def modules_agac():
    rows = module_store.latest_active(module_store.read_catalog(OUTPUT_DIR))
    hazir = [{key: row.get(key) for key in _MODULE_CARD_FIELDS} for row in rows]
    durum, agac = _mufredat_agaci()
    if durum != "ok" or agac is None:
        # D3: harita okunamazsa hazır modül listesi çalışmaya devam eder, 500 verilmez.
        return jsonify({"hazir": hazir, "dersler": [], "kapsam": {}, "hata": "harita_okunamadi"})
    eslesme = _agac_modul_eslemesi(agac, rows)
    dersler = []
    for ders in agac["dersler"]:
        uniteler = []
        for unite in ders["uniteler"]:
            konular = [{**konu, "modul": eslesme.get(konu["id"])} for konu in unite["konular"]]
            uniteler.append({**unite, "konular": konular,
                             "hazir_sayisi": sum(1 for k in konular if k["modul"])})
        dersler.append({**ders, "uniteler": uniteler,
                        "konu_sayisi": sum(len(u["konular"]) for u in uniteler),
                        "hazir_sayisi": sum(u["hazir_sayisi"] for u in uniteler)})
    return jsonify({"hazir": hazir, "dersler": dersler, "kapsam": agac["kapsam"], "hata": None})
```

İçe aktarma: `src/dashboard_api.py:48`'deki mevcut demete `mufredat_agaci` eklenir —
`from src import assistant_skills, module_progress, module_store, module_ticket, mufredat_agaci, subject_themes`.
`re` (satır 9) ve `threading` (satır 13) zaten içe aktarılmıştır, tekrar edilmez.
`_MODULE_CARD_FIELDS` (satır 4705) bu kodun üstünde tanımlıdır ve `created_at` ile `gates`
alanlarını da taşır — kart gövdesi `types.ts`'teki `ModuleCard` ile birebir eşleşir.

- [ ] **Step 4: Run tests to verify they pass**

Run: `TEST_AUTH_BYPASS=1 .venv/bin/python -m pytest -q tests/test_dashboard_api.py -k agac_ucu`
Expected: PASS (8 test)

- [ ] **Step 5: Run the whole API suite for regressions**

Run: `TEST_AUTH_BYPASS=1 .venv/bin/python -m pytest -q tests/test_dashboard_api.py`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/dashboard_api.py tests/test_dashboard_api.py
git commit -m "feat(moduller): /api/modules/agac ucu, stat imzalı önbellek ve modül eşlemesi

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: Asistan bağlamında `konu` öğesi

**Files:**
- Modify: `src/dashboard_api.py:1010` (`SAYFA_OGE_TURLERI`) ve `_sayfa_ogesi_basligi`
- Modify: `dashboard/src/asistan/sayfaBaglami.ts` (`AcikOge['tur']` birleşimi)
- Modify: `tests/test_dashboard_api.py`

**Interfaces:**
- Consumes: Görev 1 `konu_bul`; Görev 5 `_mufredat_agaci`.
- Produces: `SAYFA_OGE_TURLERI` artık `"konu"` içerir; `AcikOge['tur']` birleşimi `'konu'` içerir.

- [ ] **Step 1: Write the failing test**

`tests/test_dashboard_api.py`'ye ekle:

```python
def test_konu_turu_sayfa_oge_turlerinde():
    assert "konu" in dashboard_api.SAYFA_OGE_TURLERI


def test_konu_basligi_dersi_ve_konuyu_adlandiriyor(agac_dosyasi):
    agac_dosyasi(_AGAC_GOVDESI)
    baslik = dashboard_api._sayfa_ogesi_basligi("konu", "matematik-u1-tam-sayilar")
    assert baslik == "Matematik · Tam Sayılar"


# Review Focus 5: kötü konu kimliği.
def test_konu_basligi_bilinmeyen_kimlikte_bos(agac_dosyasi):
    agac_dosyasi(_AGAC_GOVDESI)
    assert dashboard_api._sayfa_ogesi_basligi("konu", "matematik-u9-olmayan") == ""


def test_konu_basligi_harita_okunamazken_bos(client, tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard_api, "MUFREDAT_AGACI_PATH", str(tmp_path / "yok.json"))
    assert dashboard_api._sayfa_ogesi_basligi("konu", "matematik-u1-tam-sayilar") == ""


def test_istek_sayfasi_konu_ogesini_kabul_ediyor(agac_dosyasi):
    agac_dosyasi(_AGAC_GOVDESI)
    satir, hata = dashboard_api._istek_sayfasi(
        {"sayfa": {"ad": "moduller", "oge": {"tur": "konu", "id": "matematik-u1-tam-sayilar"}}})
    assert hata is None and "Matematik · Tam Sayılar" in satir


@pytest.mark.parametrize("kimlik", ["x" * 401, "konu\nid", ""])
def test_istek_sayfasi_bozuk_konu_kimligini_400_yapiyor(kimlik):
    _, hata = dashboard_api._istek_sayfasi(
        {"sayfa": {"ad": "moduller", "oge": {"tur": "konu", "id": kimlik}}})
    assert hata is not None and hata[1] == 400
```

- [ ] **Step 2: Run test to verify it fails**

Run: `TEST_AUTH_BYPASS=1 .venv/bin/python -m pytest -q tests/test_dashboard_api.py -k konu`
Expected: FAIL — `assert "konu" in ("odev", "sinav", "etkinlik", "ders_haftasi")`

- [ ] **Step 3: Write minimal implementation**

`src/dashboard_api.py`:

```python
SAYFA_OGE_TURLERI = ("odev", "sinav", "etkinlik", "ders_haftasi", "konu")
```

`_sayfa_ogesi_basligi`'nın `try` gövdesine, `ders_haftasi` dalının ardına:

```python
        elif tur == "konu":
            durum, agac = _mufredat_agaci()
            bulunan = mufredat_agaci.konu_bul(agac, kimlik) if durum == "ok" and agac else None
            if bulunan:
                ders, _, konu = bulunan
                return f"{ders['ders']} · {konu['ad']}"
```

`dashboard/src/asistan/sayfaBaglami.ts`:

```ts
export interface AcikOge { tur: 'odev' | 'sinav' | 'etkinlik' | 'ders_haftasi' | 'konu'; id: string; etiket: string }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `TEST_AUTH_BYPASS=1 .venv/bin/python -m pytest -q tests/test_dashboard_api.py -k konu`
Expected: PASS

- [ ] **Step 5: Type-check the frontend change**

Run: `cd dashboard && npx tsc --noEmit`
Expected: hata yok

- [ ] **Step 6: Commit**

```bash
git add src/dashboard_api.py tests/test_dashboard_api.py dashboard/src/asistan/sayfaBaglami.ts
git commit -m "feat(moduller): asistan bağlamına konu öğesi

Sunucu basligi kendi verisinden cozer; istemcinin etiketine guvenmez.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 7: Modüller yüzeyi

**Files:**
- Modify: `dashboard/src/components/Modules.tsx` (ağaç + hazır liste)
- Create: `dashboard/src/components/MufredatAgaci.tsx` (ağaç bileşeni; `Modules.tsx` şişmesin)
- Modify: `dashboard/src/components/Modules.scss`
- Modify: `dashboard/src/types.ts` (ağaç tipleri)
- Create: `dashboard/src/hooks/useAcikDallar.ts` (localStorage, İ5)
- Modify: `dashboard/tests/e2e/_gorsel-fixtures.ts` (`modules/agac` sabit verisi)
- Create: `dashboard/tests/e2e/moduller-agac.spec.ts`

**Interfaces:**
- Consumes: Görev 5'in uç gövdesi; Görev 6'nın `AcikOge` birleşimi; `SubjectLabel`, `EmptyLine`, `useApi`, `useDar`, `useFocusMode`, `asistanaSor`.
- Produces: `types.ts`'te `MufredatKonu`, `MufredatUnite`, `MufredatDers`, `MufredatAgacYaniti`; `useAcikDallar()` → `{ acik: Set<string>, degistir: (id: string) => void }`.

- [ ] **Step 1: Carbon adlarını doğrula**

Run (Carbon MCP): `code_search` → `"TreeView TreeNode"` with `filters.component_type = "React"`; `code_search` → `"ContainedList ContainedListItem"` with `filters.component_type = "React"`.
Ayrıca yerelden doğrula:
```bash
cd dashboard && grep -n "TreeView\|TreeNode" node_modules/@carbon/react/lib/index.d.ts | head
```
Expected: `TreeView` ve `TreeNode` dışa aktarımları var, `preview__` öneki yok. **Herhangi bir prop adı bu adımda doğrulanmadan yazılmaz** (talimatname §10).

- [ ] **Step 2: Write the failing test**

`dashboard/tests/e2e/_gorsel-fixtures.ts`'in `GORSEL` nesnesine ekle (mevcut `modules:` satırının hemen altına):

```ts
  'modules/agac': {
    hazir: [{ created_at: '2026-09-19T19:32:46+00:00', gates: { fail: 0, pass: 17, warn: 0 },
      gradeLevel: '7. Sınıf', mode: 'MODULE', outcomes: ['MAT.7.1.1'], slug: 'mat7-tam-sayilar',
      subject: 'Matematik', ted_link: null, title: 'Tam Sayılar: Sıfırın İki Yanı', version: 1 }],
    dersler: [{
      ders: 'Matematik', slug: 'matematik', program: { document_id: 24, sayfa: '115-172' },
      kitaplar: [{ document_id: 346, kisa: '1. Kitap', sayfa_kaymasi: 0, kayma_uyumu: '35/35' }],
      konu_sayisi: 2, hazir_sayisi: 1,
      uniteler: [{
        no: 1, ad: 'Sayılar ve Nicelikler', program_sayfa: 115, hazir_sayisi: 1,
        konular: [
          { id: 'matematik-u1-tam-sayilar', ad: 'Tam Sayılar', ad_kaynak: 'TAM SAYILAR',
            kitap: 346, sayfa: [17, 24], sayfa_kaynak: 'icindekiler',
            kazanimlar: ['MAT.7.1.1'], kazanim_kaynak: 'metin-ortusmesi',
            modul: { slug: 'mat7-tam-sayilar', version: 1, title: 'Tam Sayılar: Sıfırın İki Yanı',
              subject: 'Matematik', gradeLevel: '7. Sınıf', mode: 'MODULE',
              outcomes: ['MAT.7.1.1'], ted_link: null, created_at: null,
              gates: { pass: 17, warn: 0, fail: 0 } } },
          { id: 'matematik-u1-mutlak-deger', ad: 'Mutlak Değer', ad_kaynak: 'MUTLAK DEĞER',
            kitap: 346, sayfa_kaynak: 'yok', kazanimlar: [], kazanim_kaynak: 'eslenmedi',
            modul: null },
        ],
      }],
    }],
    kapsam: { matematik: { konu: 2, sayfasi_olan: 1, kazanimi_eslenen: 1 } },
    hata: null,
  },
```

`dashboard/tests/e2e/moduller-agac.spec.ts`:

```ts
import { test, expect } from '@playwright/test'
import { sabitAc } from './_gorsel-yardim'

test.describe('Modüller — müfredat ağacı', () => {
  test('hazır modül listesi ve ağaç birlikte çiziliyor', async ({ page }) => {
    await sabitAc(page, '/moduller', 1440, 900)
    await expect(page.getByRole('link', { name: /Tam Sayılar: Sıfırın İki Yanı/ })).toBeVisible()
    await expect(page.getByRole('tree', { name: 'Tüm müfredat' })).toBeVisible()
  })

  test('ünite kapalı başlar, açılınca konular görünür', async ({ page }) => {
    await sabitAc(page, '/moduller', 1440, 900)
    const ders = page.getByRole('treeitem', { name: /Matematik/ })
    await expect(ders).toHaveAttribute('aria-expanded', 'false')
    await ders.click()
    const unite = page.getByRole('treeitem', { name: /Sayılar ve Nicelikler/ })
    await expect(unite).toBeVisible()
    await unite.click()
    await expect(page.getByRole('treeitem', { name: /Mutlak Değer/ })).toBeVisible()
  })

  test('hazır olmayan konu "Hazır değil" diyor, sayfa uydurmuyor', async ({ page }) => {
    await sabitAc(page, '/moduller', 1440, 900)
    await page.getByRole('treeitem', { name: /Matematik/ }).click()
    await page.getByRole('treeitem', { name: /Sayılar ve Nicelikler/ }).click()
    const yaprak = page.getByRole('treeitem', { name: /Mutlak Değer/ })
    await expect(yaprak).toContainText('Hazır değil')
    await expect(yaprak).toContainText('1. Kitap')
    await expect(yaprak).not.toContainText('s.')
  })

  test('modülü olan konu bağlantıdır (yeni sekme çalışır)', async ({ page }) => {
    await sabitAc(page, '/moduller', 1440, 900)
    await page.getByRole('treeitem', { name: /Matematik/ }).click()
    await page.getByRole('treeitem', { name: /Sayılar ve Nicelikler/ }).click()
    await expect(page.getByRole('treeitem', { name: /Tam Sayılar/ }).locator('a'))
      .toHaveAttribute('href', '/moduller/mat7-tam-sayilar/v1')
  })

  test('açık dallar sayfa yenilenince kalıyor (İ5)', async ({ page }) => {
    await sabitAc(page, '/moduller', 1440, 900)
    await page.getByRole('treeitem', { name: /Matematik/ }).click()
    await page.reload()
    await expect(page.getByRole('treeitem', { name: /Matematik/ }))
      .toHaveAttribute('aria-expanded', 'true')
  })

  test('harita okunamazsa hazır liste kalıyor, cümle açıklıyor (D3)', async ({ page }) => {
    await page.route('**/api/modules/agac', r => r.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify({ hazir: [], dersler: [], kapsam: {}, hata: 'harita_okunamadi' }),
    }))
    await sabitAc(page, '/moduller', 1440, 900)
    await expect(page.getByText('Müfredat haritası şu an okunamıyor.')).toBeVisible()
    await expect(page.getByRole('tree')).toHaveCount(0)
  })
})
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd dashboard && (unset ANTHROPIC_API_KEY; npx playwright test moduller-agac)`
Expected: FAIL — `getByRole('tree')` bulunamıyor

- [ ] **Step 4: Add the tree types**

`dashboard/src/types.ts`, `ModuleCard`'ın altına:

```ts
export interface MufredatKonu {
  id: string
  ad: string
  ad_kaynak: string
  kitap: number
  sayfa?: [number, number]
  sayfa_kaynak: 'icindekiler' | 'yok'
  kazanimlar: string[]
  kazanim_kaynak: 'metin-ortusmesi' | 'eslenmedi'
  modul: ModuleCard | null
}

export interface MufredatUnite {
  no: number
  ad: string
  program_sayfa: number
  konular: MufredatKonu[]
  hazir_sayisi: number
}

export interface MufredatKitap {
  document_id: number
  kisa: string
  sayfa_kaymasi: number | null
  kayma_uyumu: string
}

export interface MufredatDers {
  ders: string
  slug: string
  kitaplar: MufredatKitap[]
  uniteler: MufredatUnite[]
  konu_sayisi: number
  hazir_sayisi: number
}

export interface MufredatAgacYaniti {
  hazir: ModuleCard[]
  dersler: MufredatDers[]
  kapsam: Record<string, Record<string, number | string>>
  hata: 'harita_okunamadi' | null
}
```

- [ ] **Step 5: Write the open-branch hook**

`dashboard/src/hooks/useAcikDallar.ts`:

```ts
import { useCallback, useState } from 'react'

/** Açık dallar kişi başına kalır (İ5: seçim kullanıcı değiştirene dek sürer).
 *  localStorage okunamayan ortamlarda (gizli pencere, kapatılmış site verisi) sessizce boş
 *  küme ile çalışır — sayfa yine çizilir. */
const ANAHTAR = 'tedy-mufredat-acik'

function yukle(): Set<string> {
  try {
    const ham = window.localStorage.getItem(ANAHTAR)
    const dizi = ham ? (JSON.parse(ham) as unknown) : []
    return new Set(Array.isArray(dizi) ? dizi.filter((d): d is string => typeof d === 'string') : [])
  } catch {
    return new Set()
  }
}

export function useAcikDallar(): { acik: Set<string>; degistir: (id: string) => void } {
  const [acik, setAcik] = useState<Set<string>>(yukle)
  const degistir = useCallback((id: string) => {
    setAcik(onceki => {
      const sonraki = new Set(onceki)
      if (!sonraki.delete(id)) sonraki.add(id)
      try {
        window.localStorage.setItem(ANAHTAR, JSON.stringify([...sonraki]))
      } catch { /* depolama yoksa oturum içi kalır */ }
      return sonraki
    })
  }, [])
  return { acik, degistir }
}
```

- [ ] **Step 6: Write the tree component**

`dashboard/src/components/MufredatAgaci.tsx`:

```tsx
import { TreeView, TreeNode } from '@carbon/react'
import { useNavigate } from 'react-router-dom'
import { asistanaSor } from '../asistan/sayfaBaglami'
import { useAcikDallar } from '../hooks/useAcikDallar'
import SubjectLabel from './SubjectLabel'
import type { MufredatDers, MufredatKonu } from '../types'

/** Dal etiketi: "25 konu · 1 hazır" — sayı katlanmış içeriğin büyüklüğünü söyler
 *  (yüzey tasarımları §2.5), cümle düzeninde (S38). */
function sayac(konu: number, hazir: number): string {
  return `${konu} konu · ${hazir} hazır`
}

/** Yaprağın üst veri satırı. Sayfa yalnız kaynağı varsa yazılır — yoksa uydurulmaz (D4). */
function ustVeri(konu: MufredatKonu, kitapAdi: string): string {
  const parcalar = [kitapAdi]
  if (konu.sayfa) parcalar.push(`s.${konu.sayfa[0]}–${konu.sayfa[1]}`)
  parcalar.push(...konu.kazanimlar)
  parcalar.push(konu.modul ? 'Hazır' : 'Hazır değil')
  return parcalar.join(' · ')
}

export default function MufredatAgaci({ dersler }: { dersler: MufredatDers[] }) {
  const gezin = useNavigate()
  const { acik, degistir } = useAcikDallar()

  // Yaprağın tek eylemi düğümün etkinleştirilmesidir: ARIA ağacında treeitem içine düğme konmaz.
  function konuyaGit(ders: MufredatDers, konu: MufredatKonu) {
    if (konu.modul) {
      gezin(`/moduller/${konu.modul.slug}/v${konu.modul.version}`)
      return
    }
    const karsilandi = asistanaSor({
      tur: 'konu', id: konu.id, etiket: `${ders.ders} · ${konu.ad}`,
    })
    if (!karsilandi) gezin('/asistan?sayfa=moduller')
  }

  return (
    <TreeView className="module-tree" label="Tüm müfredat" size="sm">
      {dersler.map(ders => (
        <TreeNode
          key={ders.slug}
          id={ders.slug}
          label={
            <span className="module-tree__dal">
              <SubjectLabel course={ders.ders} />
              <span className="module-tree__sayac">{sayac(ders.konu_sayisi, ders.hazir_sayisi)}</span>
            </span>
          }
          isExpanded={acik.has(ders.slug)}
          onToggle={() => degistir(ders.slug)}
        >
          {ders.uniteler.length === 0 ? (
            <TreeNode id={`${ders.slug}-yok`} label="Bu dersin haritası henüz hazır değil." />
          ) : ders.uniteler.map(unite => {
            const dalId = `${ders.slug}-u${unite.no}`
            return (
              <TreeNode
                key={dalId}
                id={dalId}
                label={
                  <span className="module-tree__dal">
                    <span>{unite.no}. {unite.ad}</span>
                    <span className="module-tree__sayac">
                      {sayac(unite.konular.length, unite.hazir_sayisi)}
                    </span>
                  </span>
                }
                isExpanded={acik.has(dalId)}
                onToggle={() => degistir(dalId)}
              >
                {unite.konular.map(konu => {
                  const kitap = ders.kitaplar.find(k => k.document_id === konu.kitap)
                  return (
                    <TreeNode
                      key={konu.id}
                      id={konu.id}
                      label={
                        <span className="module-tree__yaprak">
                          <span className="module-tree__ad">{konu.ad}</span>
                          <span className="module-tree__ust-veri">
                            {ustVeri(konu, kitap?.kisa ?? '')}
                          </span>
                        </span>
                      }
                      href={konu.modul ? `/moduller/${konu.modul.slug}/v${konu.modul.version}` : undefined}
                      onSelect={(olay: React.MouseEvent | React.KeyboardEvent) => {
                        olay.preventDefault()
                        konuyaGit(ders, konu)
                      }}
                    />
                  )
                })}
              </TreeNode>
            )
          })}
        </TreeNode>
      ))}
    </TreeView>
  )
}
```

- [ ] **Step 7: Rewrite the page**

`dashboard/src/components/Modules.tsx`'in `Modules()` gövdesini değiştir (`ModuleViewerRoute` ve `DraftViewerRoute` **dokunulmaz**):

```tsx
export default function Modules() {
  const { data, loading, iskelet, error, hataTuru } = useApi<MufredatAgacYaniti>(
    '/api/modules/agac', { hazir: [], dersler: [], kapsam: {}, hata: null })
  // B43: ham fetch metni okura gitmez; tür cümleye çevrilir (merge 342d452 ile gelen kalıp).
  const hata = apiHataCumlesi(hataTuru ?? 'sunucu', 'Modüller')
  const navigate = useNavigate()
  const dar = useDar()
  const { focusMode } = useFocusMode()
  const hazir = Array.isArray(data.hazir) ? data.hazir : []
  const dersler = Array.isArray(data.dersler) ? data.dersler : []
  return (
    <div className="dashboard-card modules">
      <h2 className="dashboard-card__title"><Education size={20} />Modüller</h2>
      {/* S36/B48: eşik geçmeden iskelet çizilmez — bir kare yanıp sönen iskelet gürültüdür. */}
      {iskelet && <div aria-busy="true"><SkeletonText paragraph lineCount={3} /></div>}
      {!loading && error && (
        <InlineNotification kind="error" role="alert" lowContrast hideCloseButton statusIconDescription="Hata"
          title={hata.baslik} subtitle={hata.ayrinti} />
      )}
      {!loading && !error && (
        <>
          {hazir.length === 0
            ? <EmptyLine label="Hazır olanlar">Henüz yayınlanmış modül yok.</EmptyLine>
            : (
              <ContainedList className="module-hazir" kind="on-page" size="lg" label="Hazır olanlar">
                {hazir.map(m => (
                  <ContainedListItem key={`${m.slug}-${m.version}`}>
                    <a className="module-hazir__bag" href={`/moduller/${m.slug}/v${m.version}`}
                      onClick={(e: React.MouseEvent) => {
                        e.preventDefault(); navigate(`/moduller/${m.slug}/v${m.version}`)
                      }}>
                      <SubjectLabel course={m.subject}>
                        <span className="module-hazir__ad">{m.title ?? m.slug}</span>
                      </SubjectLabel>
                    </a>
                    {m.mode && MODE_LABEL[m.mode] && (
                      <Tag type="cool-gray" size={dar ? 'md' : 'sm'}>{MODE_LABEL[m.mode]}</Tag>
                    )}
                  </ContainedListItem>
                ))}
              </ContainedList>
            )}
          {/* Odak kipinde ağaç çizilmez: yalnız yapılabilen iş kalır (İ1). */}
          {!focusMode && (data.hata === 'harita_okunamadi'
            ? <EmptyLine label="Tüm müfredat">Müfredat haritası şu an okunamıyor.</EmptyLine>
            : dersler.length > 0 && <MufredatAgaci dersler={dersler} />)}
        </>
      )}
    </div>
  )
}
```

İçe aktarmaları güncelle: `ContainedList`, `ContainedListItem` `@carbon/react`'ten;
`import { useFocusMode } from '../contexts/focusMode'` (`HomeworkTracker.tsx:18` ile aynı yol);
`import MufredatAgaci from './MufredatAgaci'`; `import SubjectLabel from './SubjectLabel'`
(varsayılan dışa aktarım); `MufredatAgacYaniti` `../types`'tan;
`import { apiHataCumlesi } from '../utils/apiHatasi'` (`Modules.tsx` bunu zaten içe aktarıyor). `EmptyLine`'ın imzası
`{ children, label? }` — `label` bölümü adlandırır.

- [ ] **Step 8: Write the stylesheet**

`dashboard/src/components/Modules.scss`'e ekle (yalnız rol token'ı; elle hex yok):

```scss
// Müfredat ağacı (spec §5). Carbon'un ağaç düğümü sm 32 px ve etiketi üç noktayla keser;
// ikisi de TEDY'de örtülür — sapmalar talimatname §11 S48 ve S49.
.module-tree {
  margin-block-start: spacing.$spacing-06;
}

.module-tree__dal,
.module-tree__yaprak {
  display: flex;
  min-width: 0;
}

.module-tree__dal {
  align-items: center;
  gap: spacing.$spacing-03;
  justify-content: space-between;
  width: 100%;
}

.module-tree__yaprak {
  flex-direction: column;
}

.module-tree__sayac,
.module-tree__ust-veri {
  @include type.type-style('label-01');

  color: theme.$text-secondary;
}

// S49: etiket kırpılmaz, sarar. Kırpılan bir konu adı satırın anlamını yok eder (D4).
.module-tree :where(.cds--tree-node__label) {
  white-space: normal;
}

@media (max-width: 671px) {
  // S48: telefonda dokunma hedefi ≥ 44 px; Carbon'un iki boyu 32 ve 24 px (B79).
  .module-tree :where(.cds--tree-node__label) {
    min-height: 2.75rem;
  }
}
```

`spacing`, `theme`, `type` `@use` satırları `Modules.scss`'in ilk üç satırında **zaten
vardır** (doğrulandı); yeniden eklenmez.

- [ ] **Step 9: Run the tests to verify they pass**

Run: `cd dashboard && (unset ANTHROPIC_API_KEY; npx playwright test moduller-agac)`
Expected: PASS (6 test)

Run: `cd dashboard && npx tsc --noEmit && npm run lint && npm run lint:css`
Expected: temiz

- [ ] **Step 10: Commit**

```bash
git add dashboard/src/components/Modules.tsx dashboard/src/components/MufredatAgaci.tsx \
  dashboard/src/components/Modules.scss dashboard/src/types.ts \
  dashboard/src/hooks/useAcikDallar.ts dashboard/tests/e2e/_gorsel-fixtures.ts \
  dashboard/tests/e2e/moduller-agac.spec.ts
git commit -m "feat(moduller): müfredat ağacı yüzeyi (Carbon TreeView)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 8: Telefon ölçümü, sapmalar ve belge kapıları

**Files:**
- Modify: `dashboard/src/components/Modules.scss` (ölçüm S50'yi gerektirirse)
- Modify: `docs/tedy-ui-ux-talimatnamesi.md` (§11.1 tablosuna S48–S50)
- Modify: `docs/frontend-surface-designs.md` (§4.12 Modüller)
- Modify: `CLAUDE.md` ("Modüller (edupedia)" maddesi)
- Modify: `dashboard/tests/e2e/*.aria.yml`, `*-snapshots/` (fark okunarak)

**Interfaces:**
- Consumes: Görev 7'nin yüzeyi.
- Produces: belge kayıtları; güncellenmiş anlık görüntüler.

- [ ] **Step 1: 390 px'te yana kaydırmayı ölç**

Run: `cd dashboard && (unset ANTHROPIC_API_KEY; npx playwright test tasarim-denetimi d3b-dokunma)`

Üç düzey açıkken 390 px'te `document.scrollingElement.scrollWidth > clientWidth` oluyor mu, ve her ağaç düğümü ≥ 44 px mi? Sonucu not et.

- [ ] **Step 2: Girintiyi yalnız ölçüm gerektiriyorsa daralt**

Yana kaydırma **varsa** `Modules.scss`'e ekle ve ölçülen değeri yaz:

```scss
@media (max-width: 671px) {
  // S50: Carbon'un düzey başına girintisi 390 px'te üçüncü düzeyde yana kaydırma yapıyordu
  // (ölçüldü). Girinti telefonda daraltılır; masaüstünde Carbon'un kendi değeri kalır.
  .module-tree :where(.cds--tree-node) {
    --cds-tree-node-indent: #{spacing.$spacing-05};
  }
}
```

Yana kaydırma **yoksa** bu adım atlanır ve S50 yazılmaz — spec §5.4 bunu açıkça izin veriyor. Hangisi olduğunu commit mesajında yaz.

- [ ] **Step 3: Sapmaları talimatnameye yaz**

Numaralar **S48, S49, S50**: §11.1 tablosu bugün S1–S46'dır ve değişiklik kaydı S47'yi
"B79 için gerekmedi" diye anar, bu yüzden S47 atlanır. Yazmadan önce tablonun son satırına
bak — araya başka bir sapma indiyse numaraları kaydır ve bu plandaki her geçişi düzelt.

`docs/tedy-ui-ux-talimatnamesi.md` §11.1 tablosunun sonuna, mevcut satırların biçimiyle
(tablo satırı, madde değil) ve §11.1'in girişindeki "Tablo 46 satırdır (S1–S46)" cümlesini
güncelleyerek:

```markdown
- **S48 — ağaç düğümü telefonda 44 px.** Carbon'un ağaç düğümü sm 32 / xs 24 px
  (bileşen rehberi §1.39); TEDY telefonda ≥ 44 px istiyor (B79). `md` altında
  `.module-tree .cds--tree-node__label` örtülür. Kapı: `d3b-dokunma.spec.ts`.
- **S49 — ağaç etiketi kırpılmaz, sarar.** Carbon taşmayı üç nokta ile keser ve bileşen
  rehberi bunu "tercih edilmez" diye işaretler; kırpılan bir konu adı satırın anlamını yok
  eder (D4). `white-space: normal`. Kapı: `moduller-agac.spec.ts`.
- **S50 — ağaç girintisi telefonda daraltılır.** Carbon'un düzey başına girintisi 390 px'te
  üçüncü düzeyde yana kaydırma yapıyordu (ölçüldü, Adım 1); `md` altında girinti
  `$spacing-05`'e çekilir, masaüstünde Carbon'un kendi değeri kalır. Kapı:
  `tasarim-denetimi.spec.ts` (yana kaydırma yok).
```

**Adım 1'in ölçümü yana kaydırma göstermediyse** S50 satırı hiç yazılmaz ve Adım 2 atlanır;
spec §5.4 bunu açıkça izin veriyor. Hangi dalın geçerli olduğunu commit mesajına yaz.

- [ ] **Step 4: Yüzey tasarımına §4.12 ekle**

`docs/frontend-surface-designs.md`'de `### 4.11 Tedy Books` bölümünün ardına:

```markdown
### 4.12 Modüller

İki bölüm: **Hazır olanlar** (`ContainedList kind="on-page" size="lg"`, katalogdaki bütün
yayınlanmış modüller — ağaca eşlenmeyen biri de) ve **Tüm müfredat** (`TreeView size="sm"`,
ders → ünite → ders kitabı alt başlığı). Hepsi kapalı başlar; okurun açtığı dallar
`localStorage` `tedy-mufredat-acik` ile kalır (İ5). Odak kipinde ağaç çizilmez (İ1).

Yaprağın tek eylemi düğümün etkinleştirilmesidir — ARIA ağacında `treeitem` içine düğme
konmaz: modülü olan yaprak bağlantıdır (B58), olmayan konuyu asistana bağlam olarak
sabitler (B78). Sayfa aralığı yalnız kaynağı varsa yazılır; yoksa yalnız kitap adı görünür
ve sayfa uydurulmaz (D4). "Hazır değil" düz ikincil metindir — `Tag` değil (B45), durum
rengi değil (yokluk hata değildir).

Harita okunamazsa hazır modül listesi kalır ve ağaç yerine bir cümle durur (D3). Eşiğe
takılıp üretilmeyen bir ders ağaçta yine listelenir ve "Bu dersin haritası henüz hazır
değil." der — sessizce eksilmez.

Veri: `src/mufredat_agaci.json` (üretilir, elle düzenlenmez) + `/api/modules/agac`.
Tasarım: `superpowers/specs/2026-10-11-moduller-mufredat-agaci-design.md`. Sapmalar:
talimatname S48–S50.
```

`docs/frontend-surface-designs.md` §1'deki ikincil sayfa listesini ve "Değişiklik kaydı"nı da güncelle.

- [ ] **Step 5: CLAUDE.md'yi güncelle**

"Modüller (edupedia)" maddesinin başına, mevcut cümleyi koruyarak:

```markdown
- **Modüller (edupedia)**: `/moduller` iki bölümdür — yayınlanmış modüllerin listesi ve
  `src/mufredat_agaci.json`'dan çizilen müfredat ağacı (7. sınıf, dört ders: ders → ünite →
  ders kitabı alt başlığı), `/api/modules/agac` ile birlikte sunulur (Carbon `TreeView
  size="sm"`; sapmalar S48–S50). Ağaç `scripts/mufredat_agaci.py tumu --sinif 7` ile sabitlenmiş
  salt-okunur müfredat DB'sinden üretilir, elle düzenlenmez ve `output/modules/` altına
  yazılmaz. Ölçüldü 2026-10-11: içindekiler nokta öncüllü satırları Fen'de 37+35,
  Matematik'te 33+33 tutuyor, Türkçe ve Sosyal'de 0 (iki sütunlu düzen) — bu yüzden
  Türkçe/Sosyal konularında sayfa aralığı üretilmez (`sayfa_kaynak: "yok"`) ve yüzey yalnız
  kitabı adlandırır. Basılı → PDF kayması kitap başına sabit ve türetilir (doc 439/473 +1,
  346/506 0; test bu değerleri kapı yapar). Türkçe kazanımı temaya değil beceriye kodlu
  olduğundan tema metnine kazanım atanmaz. Modülü olmayan konu "Asistana sor" taşır
  (`tur: 'konu'`; sunucu başlığı `mufredat_agaci.json`'dan kendisi çözer).
```

- [ ] **Step 6: Anlık görüntüleri ve ARIA ağacını güncelle**

Run: `cd dashboard && (unset ANTHROPIC_API_KEY; npx playwright test gorsel-regresyon aria-yapisi --update-snapshots)`

**Farkı oku.** Beklenen: yalnız `/moduller` 1440 ve 390 değişmiş, `.aria.yml`'de `tree`/`treeitem` rolleri eklenmiş. Başka bir sayfa değişmişse dur ve nedenini bul — başka sayfanın değişmesi bu işin kapsamında değil.

- [ ] **Step 7: Bütün kapıları koş**

```bash
cd /mnt/thunderbolt/workspaces/TED
unshare -rn .venv/bin/python -m pytest -q
cd dashboard && npx tsc --noEmit && npm run lint && npm run lint:css && npm run test:birim
(unset ANTHROPIC_API_KEY; npx playwright test)
```
Expected: hepsi PASS. `tests/test_mufredat_agaci_db.py` ve canlı üretim testleri DB'siz makinede SKIPPED.

- [ ] **Step 8: Commit**

```bash
git add docs/tedy-ui-ux-talimatnamesi.md docs/frontend-surface-designs.md CLAUDE.md \
  dashboard/src/components/Modules.scss dashboard/tests/e2e
git commit -m "docs(moduller): S48-S50 sapmaları, yüzey tasarımı §4.12 ve anlık görüntüler

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```
