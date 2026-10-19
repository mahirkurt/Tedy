# MEB konu-soru dağılım senaryoları — uygulama planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 7. sınıfın altı dersine ait MEB ÖDSGM senaryo tablolarını TEDY'ye almak; sınav duyurusundaki senaryoyu tabloyla doğrulayıp sınav kartında göstermek; asistanın senaryo dağılımına uyan örnek yazılı ve alıştırma üretmesini sağlamak.

**Architecture:** Bir betik tabloları (Jina Reader üzerinden LibreOffice HTML) `src/sinav_senaryolari.json`'a çevirir. Saf bir eşleştirici (`src/sinav_senaryo.py`) sınavın sütununu, duyurudaki senaryo cümlesini ve konuları çözer; sınav tespiti (`birlestir`) bunu her kayda `senaryo` bloğu olarak yazar. `/api/exams` bloğu geçirir; Sınavlar kartı gösterir; asistanın `sinav_senaryosu` aracı aynı veriyi kontrol listesi olarak modele verir.

**Tech Stack:** Python 3.12 (stdlib `html.parser`, `requests`), pytest; React 19 + Carbon (`@carbon/react`, `@carbon/icons-react`), node:test, Playwright + axe + IBM Equal Access.

**Spec:** `docs/superpowers/specs/2026-10-19-meb-sinav-senaryolari-design.md`

## Global Constraints

- Kapsam: 7. sınıf, 2026-2027 öğretim yılı, **1. dönem**; dersler (kanonik ad): Türkçe, Matematik, Fen Bilimleri, Sosyal Bilgiler, Din Kültürü, İngilizce.
- Kullanıcı kararı: okulun "1.1"i = MEB "1. Dönem 1. Ortak Yazılı Sınav", "1.2" = "1. Dönem 2. Ortak Yazılı Sınav".
- Ağ yalnız `scripts/odsgm_senaryo_tablolari.py`'de; senkron, pano ve asistan ağa çıkmaz. Testler ağsız koşar (`unshare -rn`).
- `senaryo` bloğu `icerik_surumu`'na **girmez**; `sinavlar.json` `surum` 1'de kalır; blok isteğe bağlıdır.
- Kart: durum ikon + metin (renk değil), Carbon ikonlarının Türkçe adı, yeni renk/gölge/hex yok, cümle düzeni, telefonda denetimler ≥ 44 px.
- Eşleşmeyen konu için "sınavda yok" denmez: "MEB tablosunda karşılığı bulunamadı".
- Asistan örnek sınavı: soru sayısı = senaryo toplamı, çıktı dağılımı birebir, cevap anahtarı ayrı adımda.
- Kullanıcı Türkçe yanıt ister; commit mesajları Türkçe, sonunda `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Çalışma ağacı `.claude/worktrees/sinav-senaryo`, dal `feat/sinav-senaryo`; canlı checkout'a dokunulmaz; staging dosya adıyla.
- Komutlar: Python `env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest …` (çalışma ağacında `.env` → canlı `.env` sembolik bağı ve `dashboard/node_modules` → canlı `dashboard/node_modules` bağı Görev 1'de kurulur); e2e `TEDY_E2E_PORT=8298 TEDY_E2E_PYTHON=/mnt/thunderbolt/workspaces/TED/.venv/bin/python env -u ANTHROPIC_API_KEY npx playwright test tests/e2e/<dosya> --project=`; dosya filtresi **yol** olarak verilir (çalışma ağacının adı her yolda geçtiği için düz ad bütün süiti seçer).

## Rulings made while writing this plan (spec'ten sapmalar)

- **Araç girdisi `sinav_id` değil `ders` + `sinav_no` (+ `senaryo`)**: model sınav kimliğini hiç görmüyor — sabitlenmiş sınav bağlama yalnız başlığıyla girer (`dashboard_api._sayfa_ogesi_basligi` → `title`), `sinavlar` aracının metninde kimlik yok. Araç sınavı dersten (ve no'dan) kendisi bulur. Niyet aynı.
- **`senaryoKaynagi` üst alanı yerine blok kendi `kaynak` (ODSGM adresi) ve `meb_guncelleme` alanını taşır**: kart iki ayrı yerden veri toplamaz; spec §4'ün istediği bilgi aynı.
- **Bölüm yalnız `SinavAyrintisi`'nde (Sınavlar sayfası)**: ölçüldü, `SinavAyrintisi` yalnız `ExamTimeline`'da kullanılıyor; İşler sınavı Sınavlar'a bağlıyor.
- **Görsel taban güncellenmez**: görsel fikstürün sınavları `senaryo` taşımaz, Sınavlar ekranı değişmez; kart yeni e2e'de denetlenir.
- **Altın sorular**: ders başına "tam 3 soru" kapısı "en az 3"e gevşer, Türkçe ve Fen'e birer senaryo vakası eklenir (spec §6.3); CLAUDE.md'deki "12 altın soru" 14 olur.

## Review Focus

- **Duyuru aynı kartta iki sınavdan söz eder, senaryo yalnız birinin cümlesinde**: öteki sınava senaryo yazılmamalı. → Görev 3 `test_baska_sinavin_senaryosu_alinmaz`.
- **Başlık "1. Dönem Yazılı" gibi sınav no'su vermez** (takvimde ölçüldü: "Türkçe · 1. Dönem Yazılı"): blok yazılmamalı, kart bölümü çizilmemeli, asistan uydurmamalı. → Görev 3 `test_sinav_no_cozulmezse_blok_yok`.
- **"4. Senaryo" büyük harfle ya da "4.senaryo" boşluksuz**: cümle bölücü "4." ile "Senaryo"yu ayırmamalı. → Görev 3 `test_buyuk_harfli_senaryo_bolunmez`.
- **Tablo dosyası bozuk/eksik**: tespit sessizce geçmemeli (`hatalar`'a not), asistan aracı bildirilmemeli, kart bölümü çizilmemeli. → Görev 4 `test_tablo_yoksa_not_duser`, Görev 7 `test_tablo_yoksa_arac_bildirilmez`.
- **Duyuru tabloda olmayan bir senaryo numarası verir (7, tabloda 1–6)**: kart ve asistan bunu söylemeli, en yakın senaryoyu sessizce seçmemeli. → Görev 3 `test_senaryo_yok`, Görev 6 e2e "senaryo yok" durumu.

---

### Task 1: Tablo betiği — LibreOffice HTML'den senaryo verisine

**Files:**
- Create: `scripts/odsgm_senaryo_tablolari.py`
- Create: `tests/fixtures/odsgm/ornek_tablo.html`
- Test: `tests/test_odsgm_senaryo_tablolari.py`

**Interfaces:**
- Consumes: —
- Produces: `tablolar(html: str) -> list[list[list[str]]]`; `ders_sayfasi(izgaralar, sinif: int) -> tuple[str, dict]` (kanonik ders adı, `{"ciktilar": [...], "sinavlar": {...}}`); `class YapiHatasi(ValueError)`; `DERS_ADRESLERI: dict[str, str]`; `SAYFA: str`; `main(argv) -> int`. Çıktı dosyası biçimi spec §2.1.

- [ ] **Step 1: Çalışma ağacı bağlarını kur**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-senaryo
ln -sfn /mnt/thunderbolt/workspaces/TED/.env .env
ln -sfn /mnt/thunderbolt/workspaces/TED/dashboard/node_modules dashboard/node_modules
git status --short   # bağlar .gitignore'da olmalı; görünürse DUR ve bildir
```

- [ ] **Step 2: Fikstürü yaz** — `tests/fixtures/odsgm/ornek_tablo.html` (LibreOffice biçimi: iki tablo, 6. ve 7. sınıf; 7. sınıfta birleşik başlıklar, boş hücreler, ülke geneli birleşik sütunu):

```html
<!DOCTYPE html>
<html><head><meta name="generator" content="LibreOffice 7.4.7.2 (Linux)"/></head><body>
<table>
<tr><td colspan="6">6. SINIF TÜRKÇE DERSİ</td></tr>
<tr><td colspan="6">1. DÖNEM ORTAK YAZILI SINAVLAR</td></tr>
<tr><td colspan="6">KONU SORU DAĞILIM TABLOSU</td></tr>
<tr><td rowspan="2">Alan Becerileri</td><td rowspan="2">Öğrenme Çıktıları</td><td colspan="2">1. Dönem 1. Ortak Yazılı Sınav</td><td colspan="2">1. Dönem 2. Ortak Yazılı Sınav</td></tr>
<tr><td>Senaryo 1</td><td>Senaryo 2</td><td>Senaryo 1</td><td>Senaryo 2</td></tr>
<tr><td>OKUMA</td><td>T.O.6.5. Metnin yüzey anlamını belirleyebilme</td><td>2</td><td>1</td><td>1</td><td>1</td></tr>
</table>
<table>
<tr><td colspan="9">7. SINIF TÜRKÇE DERSİ</td></tr>
<tr><td colspan="9">1. DÖNEM ORTAK YAZILI SINAVLAR</td></tr>
<tr><td colspan="9">KONU SORU DAĞILIM TABLOSU</td></tr>
<tr><td rowspan="2">Alan Becerileri</td><td rowspan="2">Öğrenme Çıktıları</td><td colspan="3">1. Dönem 1. Ortak Yazılı Sınav</td><td colspan="4">1. Dönem 2. Ortak Yazılı Sınav</td></tr>
<tr><td>Senaryo 1</td><td>Senaryo 2</td><td>Senaryo 3</td><td colspan="4" rowspan="5">1. Dönem 2. Ortak Yazılı Sınav<br/>Ülke Geneli Ortak Yazılı Sınav</td></tr>
<tr><td rowspan="3">OKUMA</td><td>T.O.7.4. Metinde geçen anlamını bilmediği söz varlığı unsurlarının anlamını tahmin edebilme</td><td>1</td><td></td><td>1</td></tr>
<tr><td>T.O.7.5. Metnin yüzey anlamını belirleyebilme</td><td>1</td><td>2</td><td>2</td></tr>
<tr><td>T.O.7.8. Metnin derin anlamını belirlemeye yönelik üst düzey çıkarımlar yapabilme</td><td></td><td></td><td></td></tr>
<tr><td>YAZMA</td><td>T.Y.7.21. Yazım kuralları ve noktalama işaretlerini uygulayabilme</td><td>1</td><td>1</td><td></td></tr>
</table>
</body></html>
```

- [ ] **Step 3: Başarısız testleri yaz** — `tests/test_odsgm_senaryo_tablolari.py`:

```python
"""ÖDSGM konu-soru dağılım tablosu betiği (spec 2026-10-19 §2): LibreOffice HTML'i ızgaraya,
ızgarayı senaryo verisine çevirir; yapı beklenenden farklıysa yazmayı reddeder."""
from pathlib import Path

import pytest

from scripts.odsgm_senaryo_tablolari import YapiHatasi, ders_sayfasi, tablolar

FIKSTUR = Path(__file__).parent / "fixtures" / "odsgm" / "ornek_tablo.html"


def _html():
    return FIKSTUR.read_text(encoding="utf-8")


def test_izgara_birlesik_hucreleri_cozer():
    t = tablolar(_html())
    assert len(t) == 2
    yedi = t[1]
    # rowspan="2" başlık iki satırda da görünür; colspan senaryo sütunlarına yayılır
    assert yedi[3][0] == yedi[4][0] == "Alan Becerileri"
    assert yedi[3][2:5] == ["1. Dönem 1. Ortak Yazılı Sınav"] * 3
    assert yedi[4][2:5] == ["Senaryo 1", "Senaryo 2", "Senaryo 3"]
    # rowspan="3" alan hücresi sonraki iki veri satırında da var; boş hücre boş kalır
    assert yedi[6][0] == "OKUMA" and yedi[6][1].startswith("T.O.7.5.")
    assert yedi[5][2:5] == ["1", "", "1"]
    # ülke geneli birleşik hücresi veri satırlarına da yayılır
    assert "Ülke Geneli" in yedi[6][5]


def test_yedinci_sinif_sayfasi_senaryo_verisine_cevrilir():
    ders, sayfa = ders_sayfasi(tablolar(_html()), 7)
    assert ders == "Türkçe"
    kodlar = [c["kod"] for c in sayfa["ciktilar"]]
    assert kodlar == ["T.O.7.4", "T.O.7.5", "T.O.7.8", "T.Y.7.21"]
    assert sayfa["ciktilar"][1] == {"kod": "T.O.7.5", "metin": "Metnin yüzey anlamını belirleyebilme",
                                    "alan": "OKUMA", "konu": None}
    birinci = sayfa["sinavlar"]["1"]
    assert birinci["tur"] == "senaryolu"
    assert birinci["senaryolar"] == {"1": {"T.O.7.4": 1, "T.O.7.5": 1, "T.Y.7.21": 1},
                                     "2": {"T.O.7.5": 2, "T.Y.7.21": 1},
                                     "3": {"T.O.7.4": 1, "T.O.7.5": 2}}
    ikinci = sayfa["sinavlar"]["2"]
    assert ikinci["tur"] == "ulke_geneli" and "Ülke Geneli" in ikinci["not"]


def test_istenen_sinif_yoksa_reddeder():
    with pytest.raises(YapiHatasi, match="8. sınıf"):
        ders_sayfasi(tablolar(_html()), 8)


def test_basliksiz_tablo_reddedilir():
    html = _html().replace("Öğrenme Çıktıları", "Açıklama")
    with pytest.raises(YapiHatasi, match="başlık"):
        ders_sayfasi(tablolar(html), 7)


def test_sayi_olmayan_hucre_reddedilir():
    html = _html().replace("<td>1</td><td>2</td><td>2</td>", "<td>1</td><td>iki</td><td>2</td>")
    with pytest.raises(YapiHatasi, match="iki"):
        ders_sayfasi(tablolar(html), 7)


def test_toplami_sifir_senaryo_reddedilir():
    html = (_html().replace("<td>1</td><td></td><td>1</td>", "<td>1</td><td></td><td></td>")
            .replace("<td>1</td><td>2</td><td>2</td>", "<td>1</td><td>2</td><td></td>"))
    with pytest.raises(YapiHatasi, match="Senaryo 3"):
        ders_sayfasi(tablolar(html), 7)


def test_ayni_kod_iki_kez_reddedilir():
    html = _html().replace("T.O.7.8. Metnin derin", "T.O.7.5. Metnin derin")
    with pytest.raises(YapiHatasi, match="T.O.7.5"):
        ders_sayfasi(tablolar(html), 7)


def test_bilinmeyen_ders_reddedilir():
    html = _html().replace("7. SINIF TÜRKÇE DERSİ", "7. SINIF SEÇMELİ ASTRONOMİ DERSİ")
    with pytest.raises(YapiHatasi, match="ders"):
        ders_sayfasi(tablolar(html), 7)
```

- [ ] **Step 4: Kırmızıyı gör**

Run: `env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest -q tests/test_odsgm_senaryo_tablolari.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.odsgm_senaryo_tablolari'`.

- [ ] **Step 5: Betiği yaz** — `scripts/odsgm_senaryo_tablolari.py`:

```python
"""MEB ÖDSGM konu-soru dağılım tablolarını src/sinav_senaryolari.json'a çevirir (spec 2026-10-19 §2).

Elle koşulur; senkron ağa çıkmaz. Her ders bir LibreOffice HTML dışa aktarımıdır (meb.ai kısa
bağlantısı). Bu makine MEB'e TLS'te takıldığı için (spec §1) sayfalar Jina Reader'dan ham HTML
olarak alınır; --dosya ile tarayıcıdan kaydedilmiş HTML okunur.

    .venv/bin/python scripts/odsgm_senaryo_tablolari.py
    .venv/bin/python scripts/odsgm_senaryo_tablolari.py --dosya Türkçe=/tmp/tr.html --meb-guncelleme 2026-09-10T17:27
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

CIKTI = KOK / "src" / "sinav_senaryolari.json"
SAYFA = "https://odsgm.meb.gov.tr/www/1donem-konu-soru-dagilim-tablolari-2026-2027/icerik/1724"
SAYFA_BASLIGI = "1. Dönem Konu Soru Dağılım Tabloları (2026-2027)"
OGRETIM_YILI = "2026-2027"
DONEM = 1
OKUYUCU = "https://r.jina.ai/"
DERS_ADRESLERI = {
    "Din Kültürü": "https://meb.ai/ankmeb1",
    "Fen Bilimleri": "https://meb.ai/ankmeb2",
    "Matematik": "https://meb.ai/ankmeb3",
    "Türkçe": "https://meb.ai/ankmeb4",
    "Sosyal Bilgiler": "https://meb.ai/ankmeb5",
    "İngilizce": "https://meb.ai/ankmeb6",
}
# Tablo başlığındaki ad → TEDY'nin kanonik ders adı (course_names.normalize_course ile aynı).
_BASLIK_DERSLERI = (("DİN KÜLTÜRÜ", "Din Kültürü"), ("FEN BİLİMLERİ", "Fen Bilimleri"),
                    ("MATEMATİK", "Matematik"), ("TÜRKÇE", "Türkçe"),
                    ("SOSYAL BİLGİLER", "Sosyal Bilgiler"), ("İNGİLİZCE", "İngilizce"))
_CIKTI_BASLIKLARI = ("Öğrenme Çıktıları", "Kazanımlar", "Kazanım")
_KOD = re.compile(r"^([A-ZÇĞİÖŞÜ]{1,5}(?:\.[A-ZÇĞİÖŞÜ]{1,5})*\.(\d{1,2})\.\d{1,2}(?:\.\d{1,2})?)\.?\s+(\S.*)$")
_SINAV = re.compile(r"Dönem\s*(\d)\s*\.\s*Ortak")
_SENARYO = re.compile(r"^Senaryo\s*(\d{1,2})$")
_GUNCELLEME = re.compile(r"Güncelleme\s*:\s*(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2})")


class YapiHatasi(ValueError):
    """Tablo beklenen yapıda değil; dosya yazılmaz."""


class _Tablolar(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tablolar: list[list[list[tuple[str, int, int]]]] = []
        self._derinlik = 0
        self._satir: list[tuple[str, int, int]] | None = None
        self._hucre: list | None = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "table":
            self._derinlik += 1
            if self._derinlik == 1:
                self.tablolar.append([])
        elif tag == "tr" and self._derinlik == 1:
            self._satir = []
            self.tablolar[-1].append(self._satir)
        elif tag in ("td", "th") and self._satir is not None:
            self._hucre = ["", int(a.get("colspan") or 1), int(a.get("rowspan") or 1)]
        elif tag == "br" and self._hucre is not None:
            self._hucre[0] += " "

    def handle_endtag(self, tag):
        if tag == "table":
            self._derinlik -= 1
        elif tag in ("td", "th") and self._hucre is not None and self._satir is not None:
            metin, cs, rs = self._hucre
            self._satir.append((" ".join(metin.split()), cs, rs))
            self._hucre = None

    def handle_data(self, data):
        if self._hucre is not None:
            self._hucre[0] += data


def _izgara(satirlar: list[list[tuple[str, int, int]]]) -> list[list[str]]:
    izgara: list[list[str]] = []
    bekleyen: dict[tuple[int, int], str] = {}
    for r, satir in enumerate(satirlar):
        cikti: list[str] = []
        c = i = 0
        while True:
            if (r, c) in bekleyen:
                cikti.append(bekleyen.pop((r, c)))
                c += 1
            elif i < len(satir):
                metin, cs, rs = satir[i]
                i += 1
                for dc in range(cs):
                    cikti.append(metin)
                    for dr in range(1, rs):
                        bekleyen[(r + dr, c + dc)] = metin
                c += cs
            elif any(k[0] == r for k in bekleyen):
                cikti.append("")
                c += 1
            else:
                break
        izgara.append(cikti)
    return izgara


def tablolar(html: str) -> list[list[list[str]]]:
    p = _Tablolar()
    p.feed(html)
    return [_izgara(t) for t in p.tablolar]


def _ders(baslik: str) -> str:
    for parca, ad in _BASLIK_DERSLERI:
        if parca in baslik:
            return ad
    raise YapiHatasi(f"tablo başlığındaki ders tanınmadı: {baslik!r}")


def ders_sayfasi(izgaralar: list[list[list[str]]], sinif: int) -> tuple[str, dict]:
    isaret = f"{sinif}. SINIF"
    izgara = next((g for g in izgaralar if any(isaret in h for r in g[:3] for h in r)), None)
    if izgara is None:
        raise YapiHatasi(f"{sinif}. sınıf tablosu yok")
    ders = _ders(next(h for r in izgara[:3] for h in r if isaret in h))
    h = next((i for i, r in enumerate(izgara) if any(x in _CIKTI_BASLIKLARI for x in r)), None)
    if h is None or h + 1 >= len(izgara):
        raise YapiHatasi("başlık satırı (Öğrenme Çıktıları) bulunamadı")
    ust, alt = izgara[h], izgara[h + 1]
    cikti_s = next(i for i, x in enumerate(ust) if x in _CIKTI_BASLIKLARI)
    alan_s = next((i for i, x in enumerate(ust) if x.startswith("Alan Becerileri") or x == "Öğrenme Alanı"), None)
    konu_s = next((i for i, x in enumerate(ust) if x.startswith("Konu")), None)

    sutunlar: dict[int, tuple[str, str | None]] = {}   # sütun → (sınav no, senaryo no | None=ülke geneli)
    ulke_notu: dict[str, str] = {}
    for c in range(cikti_s + 1, len(ust)):
        m = _SINAV.search(ust[c])
        if not m:
            continue
        no = m.group(1)
        alt_metin = alt[c] if c < len(alt) else ""
        s = _SENARYO.match(alt_metin)
        if s:
            sutunlar[c] = (no, s.group(1))
        elif "Ülke Geneli" in alt_metin:
            sutunlar[c] = (no, None)
            ulke_notu[no] = alt_metin[:200]
        else:
            raise YapiHatasi(f"{ust[c]!r} altında senaryo başlığı yok: {alt_metin!r}")
    if not sutunlar:
        raise YapiHatasi("başlık satırında ortak yazılı sütunu yok")

    ciktilar: list[dict] = []
    senaryolar: dict[str, dict[str, dict[str, int]]] = {}
    for r in izgara[h + 2:]:
        if cikti_s >= len(r):
            continue
        m = _KOD.match(r[cikti_s])
        if not m:
            continue
        kod, kod_sinifi, metin = m.group(1), m.group(2), m.group(3).strip()
        if kod_sinifi != str(sinif):
            raise YapiHatasi(f"{kod}: {sinif}. sınıf kodu değil")
        if any(c["kod"] == kod for c in ciktilar):
            raise YapiHatasi(f"{kod} iki kez geçiyor")
        ciktilar.append({"kod": kod, "metin": metin,
                         "alan": (r[alan_s] or None) if alan_s is not None else None,
                         "konu": (r[konu_s] or None) if konu_s is not None else None})
        for c, (no, sen) in sutunlar.items():
            if sen is None:
                continue
            hucre = r[c].strip() if c < len(r) else ""
            if not hucre:
                continue
            if not hucre.isdigit():
                raise YapiHatasi(f"{kod} · {no}. yazılı Senaryo {sen}: sayı değil: {hucre!r}")
            senaryolar.setdefault(no, {}).setdefault(sen, {})
            if int(hucre) > 0:
                senaryolar[no][sen][kod] = int(hucre)
    if not ciktilar:
        raise YapiHatasi("hiç öğrenme çıktısı okunamadı")

    sinavlar: dict[str, dict] = {}
    for no in sorted({n for n, _ in sutunlar.values()}):
        if no in ulke_notu:
            sinavlar[no] = {"tur": "ulke_geneli", "not": ulke_notu[no]}
            continue
        adlar = sorted({s for n, s in sutunlar.values() if n == no and s}, key=int)
        sen = {s: senaryolar.get(no, {}).get(s, {}) for s in adlar}
        for s, dagilim in sen.items():
            if sum(dagilim.values()) < 1:
                raise YapiHatasi(f"{no}. yazılı Senaryo {s}: toplam soru 0")
        sinavlar[no] = {"tur": "senaryolu", "senaryolar": sen}
    return ders, {"ciktilar": ciktilar, "sinavlar": sinavlar}


def _getir(adres: str) -> str:
    import requests

    yanit = requests.get(OKUYUCU + adres, headers={"X-Return-Format": "html"}, timeout=90)
    yanit.raise_for_status()
    yanit.encoding = "utf-8"
    return yanit.text


def main(argv: list[str] | None = None) -> int:
    from src.json_utils import atomic_json_dump

    p = argparse.ArgumentParser(description="ÖDSGM senaryo tablolarını src/sinav_senaryolari.json'a çevirir")
    p.add_argument("--sinif", type=int, default=7)
    p.add_argument("--dosya", action="append", default=[], help="DERS=yol (tarayıcıdan kaydedilmiş HTML)")
    p.add_argument("--meb-guncelleme", help="YYYY-MM-DDTHH:MM (verilmezse ÖDSGM sayfasından okunur)")
    p.add_argument("--cikti", type=Path, default=CIKTI)
    a = p.parse_args(argv)
    dosyalar = dict(x.split("=", 1) for x in a.dosya)

    guncelleme = a.meb_guncelleme
    if not guncelleme:
        m = _GUNCELLEME.search(_getir(SAYFA))
        if not m:
            print("hata: ÖDSGM sayfasında güncelleme tarihi bulunamadı; --meb-guncelleme ver", file=sys.stderr)
            return 1
        g, ay, y, sa, dk = m.groups()
        guncelleme = f"{y}-{ay}-{g}T{sa}:{dk}"

    dersler: dict[str, dict] = {}
    for ad, adres in DERS_ADRESLERI.items():
        html = Path(dosyalar[ad]).read_text(encoding="utf-8") if ad in dosyalar else _getir(adres)
        try:
            okunan, sayfa = ders_sayfasi(tablolar(html), a.sinif)
        except YapiHatasi as hata:
            print(f"hata: {ad}: {hata} — dosya yazılmadı", file=sys.stderr)
            return 1
        if okunan != ad:
            print(f"hata: {adres} {okunan} tablosu çıktı, {ad} bekleniyordu — dosya yazılmadı", file=sys.stderr)
            return 1
        dersler[ad] = {"adres": adres, "sha256": hashlib.sha256(html.encode("utf-8")).hexdigest(), **sayfa}

    atomic_json_dump({"surum": 1,
                      "kaynak": {"sayfa": SAYFA, "baslik": SAYFA_BASLIGI, "meb_guncelleme": guncelleme,
                                 "alindi": date.today().isoformat(), "ogretim_yili": OGRETIM_YILI,
                                 "donem": DONEM, "sinif": a.sinif},
                      "dersler": dersler}, str(a.cikti))
    for ad, d in dersler.items():
        ozet = ", ".join(f"{no}. yazılı: " + (f"{len(s['senaryolar'])} senaryo" if s["tur"] == "senaryolu" else "ülke geneli")
                         for no, s in d["sinavlar"].items())
        print(f"{ad}: {len(d['ciktilar'])} çıktı · {ozet}")
    print(f"yazıldı: {a.cikti}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Yeşili gör**

Run: `env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest -q tests/test_odsgm_senaryo_tablolari.py`
Expected: 8 passed.

- [ ] **Step 7: Commit**

```bash
git add scripts/odsgm_senaryo_tablolari.py tests/fixtures/odsgm/ornek_tablo.html tests/test_odsgm_senaryo_tablolari.py
git commit -m "feat(sinav): ÖDSGM senaryo tablosu betiği — LibreOffice HTML'den senaryo verisine

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Gerçek tablolar — `src/sinav_senaryolari.json`

**Files:**
- Create: `src/sinav_senaryolari.json` (betik üretir)
- Test: `tests/test_sinav_senaryolari_verisi.py`

**Interfaces:**
- Consumes: Görev 1 `main`.
- Produces: `src/sinav_senaryolari.json` (spec §2.1 biçimi; `dersler` anahtarları: Din Kültürü, Fen Bilimleri, Matematik, Türkçe, Sosyal Bilgiler, İngilizce).

- [ ] **Step 1: Başarısız veri testlerini yaz** — `tests/test_sinav_senaryolari_verisi.py`:

```python
"""Repodaki MEB senaryo verisi (spec §2.1, §8): yapı değişmezleri ve 2026-10-19'da ölçülmüş gerçekler."""
import json
import re
from pathlib import Path

VERI = json.loads((Path(__file__).resolve().parents[1] / "src" / "sinav_senaryolari.json").read_text(encoding="utf-8"))
DERSLER = {"Din Kültürü", "Fen Bilimleri", "Matematik", "Türkçe", "Sosyal Bilgiler", "İngilizce"}
KOD = re.compile(r"^[A-ZÇĞİÖŞÜ]{1,5}(\.[A-ZÇĞİÖŞÜ]{1,5})*\.7\.\d{1,2}(\.\d{1,2})?$")


def test_kaynak_bilgisi():
    k = VERI["kaynak"]
    assert VERI["surum"] == 1
    assert k["sinif"] == 7 and k["donem"] == 1 and k["ogretim_yili"] == "2026-2027"
    assert k["sayfa"].startswith("https://odsgm.meb.gov.tr/")
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", k["meb_guncelleme"])


def test_alti_ders_kanonik_adla():
    assert set(VERI["dersler"]) == DERSLER


def test_yapi_degismezleri():
    for ad, d in VERI["dersler"].items():
        kodlar = [c["kod"] for c in d["ciktilar"]]
        assert kodlar and len(kodlar) == len(set(kodlar)), ad
        assert all(KOD.match(k) for k in kodlar), (ad, [k for k in kodlar if not KOD.match(k)])
        assert d["sinavlar"], ad
        for no, s in d["sinavlar"].items():
            assert no in ("1", "2")
            if s["tur"] == "ulke_geneli":
                assert "Ülke Geneli" in s["not"]
                continue
            assert s["tur"] == "senaryolu" and s["senaryolar"], (ad, no)
            for sen, dagilim in s["senaryolar"].items():
                assert sum(dagilim.values()) >= 1, (ad, no, sen)
                assert set(dagilim) <= set(kodlar), (ad, no, sen)


def test_olculmus_turkce_dorduncu_senaryo():
    tr = VERI["dersler"]["Türkçe"]
    s4 = tr["sinavlar"]["1"]["senaryolar"]["4"]
    assert sum(s4.values()) == 7
    assert s4 == {"T.O.7.4": 1, "T.O.7.5": 2, "T.O.7.7": 1, "T.O.7.21": 1, "T.Y.7.18": 1, "T.Y.7.21": 1}
    assert len(tr["sinavlar"]["1"]["senaryolar"]) == 6
    assert tr["sinavlar"]["2"]["tur"] == "ulke_geneli"
    metin = {c["kod"]: c["metin"] for c in tr["ciktilar"]}
    assert metin["T.O.7.5"] == "Metnin yüzey anlamını belirleyebilme"


def test_olculmus_fen():
    fen = VERI["dersler"]["Fen Bilimleri"]
    assert len(fen["sinavlar"]["1"]["senaryolar"]) == 5
    assert fen["sinavlar"]["1"]["senaryolar"]["1"]["FB.7.2.1"] == 3
    assert next(c for c in fen["ciktilar"] if c["kod"] == "FB.7.1.1")["konu"] == "Türkiye ve Uzay Araştırmaları"
```

- [ ] **Step 2: Kırmızıyı gör**

Run: `env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest -q tests/test_sinav_senaryolari_verisi.py`
Expected: FAIL — `FileNotFoundError: … src/sinav_senaryolari.json` (toplama hatası).

- [ ] **Step 3: Betiği gerçek kaynakta koştur** (ağ gerekir; `unshare` YOK)

```bash
/mnt/thunderbolt/workspaces/TED/.venv/bin/python scripts/odsgm_senaryo_tablolari.py
```
Expected: altı satır ("Türkçe: N çıktı · 1. yazılı: 6 senaryo, 2. yazılı: ülke geneli" gibi) ve `yazıldı: …/src/sinav_senaryolari.json`.
Betik bir dersi reddederse (`hata: <ders>: …`): o dersin gerçek HTML'ini `/tmp/odsgm-<ders>.html`'e indir (`curl -s -H 'X-Return-Format: html' https://r.jina.ai/<adres>`), reddedilen satırın biçimini Görev 1 fikstürüne yeni bir satır olarak ekle, Görev 1 testine o biçimi kapsayan bir test yaz (kırmızıyı gör), kuralı **en dar** biçimde genişlet, yeşili gör; sapmayı defterde `Ruling:` olarak kaydet. Uyduran ya da hücre atlayan bir "düzeltme" yapma.

- [ ] **Step 4: Yeşili gör ve dosyayı oku**

Run: `env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest -q tests/test_sinav_senaryolari_verisi.py tests/test_odsgm_senaryo_tablolari.py`
Expected: 13 passed. Ardından `python3 -c "import json;d=json.load(open('src/sinav_senaryolari.json'));print({k:{n:(len(s['senaryolar']) if s['tur']=='senaryolu' else 'ülke') for n,s in v['sinavlar'].items()} for k,v in d['dersler'].items()})"` çıktısını rapora yaz.

- [ ] **Step 5: Commit**

```bash
git add src/sinav_senaryolari.json tests/test_sinav_senaryolari_verisi.py
git commit -m "feat(sinav): 7. sınıf 1. dönem MEB senaryo tabloları (ÖDSGM, 10.09.2026)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Eşleştirici — `src/sinav_senaryo.py`

**Files:**
- Create: `src/sinav_senaryo.py`
- Test: `tests/test_sinav_senaryo.py`

**Interfaces:**
- Consumes: `src/sinav_senaryolari.json` (Görev 2); `src.sinav_tarihi.katla`; `src.course_names.normalize_course`.
- Produces:
  - `TABLO: Path`; `tablo_oku(yol: Path | None = None) -> dict | None`
  - `sutun_coz(kayit: dict, tablo: dict, bugun: date) -> tuple[str, int] | None`
  - `senaryo_cumlesi(metin: str, alinti: str, tek: bool) -> tuple[list[int], str | None]`
  - `konu_eslestir(konu: str, ciktilar: list[dict]) -> list[str]`
  - `senaryo_blogu(kayit: dict, metinler: list[tuple[str, str, bool]], tablo: dict, bugun: date) -> dict | None` — blok alanları: `durum, ders, sinav_no, donem, anilan, cumle, senaryo, toplam, dagilim[{kod,metin,soru,duyuruda}], eslesen_konu_sayisi, eslesmeyen_konular, senaryo_disi_konular, adaylar, senaryo_sayisi, kaynak, meb_guncelleme` (+ `not` yalnız `ulke_geneli`)
  - `ozet(blok: dict) -> str` (tek satır, `sinavlar` aracı için)
  - `arac_metni(tablo: dict, sinavlar: list[dict], args: dict) -> tuple[str, str]` (gövde, atıf etiketi); geçersiz girdi `ValueError`

- [ ] **Step 1: Başarısız testleri yaz** — `tests/test_sinav_senaryo.py`:

```python
"""Sınav ↔ MEB senaryosu eşleştirici (spec 2026-10-19 §3, §6.1). Gerçek tablo dosyasıyla."""
from datetime import date

import pytest

from src import sinav_senaryo as ss

TABLO = ss.tablo_oku()
BUGUN = date(2026, 10, 19)
TR_METIN = (
    "6. Hafta Planımız\nEda Şen | 19.10.2026\nSevgili Öğrencilerimiz,\n\nDerslerimize, geçtiğimiz hafta "
    "kontrol edemediğimiz ödevlerinizin kontrolü ile başlıyoruz. Ardından MEB kitabımızda yer alan "
    "\"Gençliğin Kıymeti\" metni üzerinden söz varlığı ve düşünceyi geliştirme yolları çalışmalarımızı "
    "tamamlayacağız. 22 Ekim Perşembe Günü 1.1 Ara Değerlendirme Sınavınızı gerçekleştireceğiz. "
    "Sınavınızın içeriği, MEB konu soru dağılım tablosu 4. senaryo ağırlıklı olacaktır. Konu "
    "başlıklarınız aşağıdaki gibidir:\n\nMetnin yüzey anlamını belirleyebilme\nMetinde geçen anlamını "
    "bilmediği söz varlığı unsurlarının anlamını tahmin edebilme")
TR_ALINTI = ("22 Ekim Perşembe Günü 1.1 Ara Değerlendirme Sınavınızı gerçekleştireceğiz. Sınavınızın "
             "içeriği, MEB konu soru dağılım tablosu 4. senaryo ağırlıklı olacaktır.")
TR_KONULAR = ["Metnin yüzey anlamını belirleyebilme",
              "Metinde geçen anlamını bilmediği söz varlığı unsurlarının anlamını tahmin edebilme"]


def kayit(ders="Türkçe", tur="ortak_sinav", baslik="1.1 Ara Değerlendirme Sınavı", tarih="2026-10-22",
          konular=()):
    return {"id": "x", "ders": ders, "tur": tur, "baslik": baslik, "tarih": tarih, "hafta": None,
            "konular": list(konular)}


def test_tablo_okunur_ve_bozuk_dosya_none(tmp_path):
    assert TABLO is not None and "Türkçe" in TABLO["dersler"]
    bozuk = tmp_path / "t.json"
    bozuk.write_text("{", encoding="utf-8")
    assert ss.tablo_oku(bozuk) is None
    bozuk.write_text('{"surum": 2, "dersler": {}}', encoding="utf-8")
    assert ss.tablo_oku(bozuk) is None


@pytest.mark.parametrize("baslik,tarih,beklenen", [
    ("1.1 Ara Değerlendirme Sınavı", "2026-10-22", ("Türkçe", 1)),
    ("1.2 Ara Değerlendirme Sınavı", "2026-12-10", ("Türkçe", 2)),
    ("Türkçe 2. Yazılı", "2026-12-10", ("Türkçe", 2)),
    ("Birinci ortak sınav", "2026-11-03", ("Türkçe", 1)),
    ("1. Dönem 1. Yazılı", "2026-11-03", ("Türkçe", 1)),
    ("2.1 Ara Değerlendirme Sınavı", "2027-03-10", None),     # 2. dönem: tablo 1. dönem
    ("1. Yazılı", "2027-03-10", None),                         # tarihten 2. dönem
])
def test_sutun_cozumu(baslik, tarih, beklenen):
    assert ss.sutun_coz(kayit(baslik=baslik, tarih=tarih), TABLO, BUGUN) == beklenen


def test_sinav_no_cozulmezse_blok_yok():
    k = kayit(baslik="Türkçe · 1. Dönem Yazılı", tarih="2027-01-05")
    assert ss.sutun_coz(k, TABLO, BUGUN) is None
    assert ss.senaryo_blogu(k, [], TABLO, BUGUN) is None


def test_kisa_sinav_ve_konu_tarama_eslesmez():
    assert ss.sutun_coz(kayit(tur="kisa_sinav"), TABLO, BUGUN) is None
    assert ss.sutun_coz(kayit(tur="konu_tarama"), TABLO, BUGUN) is None
    assert ss.sutun_coz(kayit(ders="Bilişim"), TABLO, BUGUN) is None


@pytest.mark.parametrize("metin,beklenen", [
    ("Sınavınız MEB tablosu 4. senaryo ağırlıklı olacaktır.", [4]),
    ("Sınav senaryo 3 üzerinden yapılacak.", [3]),
    ("Sınav dördüncü senaryoya göre hazırlanacak.", [4]),
    ("3. ve 4. senaryolardan sorular gelecek.", [3, 4]),
    ("Sınav 4.senaryo ile yapılacak.", [4]),
    ("Sınavda 22 soru olacak, senaryo yok.", []),
])
def test_senaryo_kaliplari(metin, beklenen):
    assert ss.senaryo_cumlesi(metin, metin, True)[0] == beklenen


def test_buyuk_harfli_senaryo_bolunmez():
    metin = "Yarın sınav var. Sınavın içeriği MEB tablosu 4. Senaryo ağırlıklı olacaktır."
    sayilar, cumle = ss.senaryo_cumlesi(metin, "Yarın sınav var.", False)
    assert sayilar == [4]
    assert cumle == "Sınavın içeriği MEB tablosu 4. Senaryo ağırlıklı olacaktır."


def test_baska_sinavin_senaryosu_alinmaz():
    metin = ("12 Kasım'da Fen kısa sınavı var. 22 Ekim Perşembe günü 1.1 Ara Değerlendirme Sınavınızı "
             "yapacağız. Sınav 3. senaryo ağırlıklı olacaktır.")
    assert ss.senaryo_cumlesi(metin, "12 Kasım'da Fen kısa sınavı var.", False) == ([], None)
    sayilar, cumle = ss.senaryo_cumlesi(metin, "22 Ekim Perşembe günü 1.1 Ara Değerlendirme", False)
    assert sayilar == [3] and cumle == "Sınav 3. senaryo ağırlıklı olacaktır."


def test_konu_eslestirme():
    tr = TABLO["dersler"]["Türkçe"]["ciktilar"]
    assert ss.konu_eslestir("Metnin yüzey anlamını belirleyebilme", tr) == ["T.O.7.5"]
    assert ss.konu_eslestir("T.O.7.21 söz varlığı", tr) == ["T.O.7.21"]
    assert ss.konu_eslestir("Osmanlı Devleti'nin kuruluşu", tr) == []
    fen = TABLO["dersler"]["Fen Bilimleri"]["ciktilar"]
    # çıktı metni değil konu adı: o konunun bütün çıktıları
    assert set(ss.konu_eslestir("Uzayda Neler Var?", fen)) == {"FB.7.1.4", "FB.7.1.5"}


def test_gercek_turkce_vakasi_dogrulandi():
    blok = ss.senaryo_blogu(kayit(konular=TR_KONULAR), [(TR_METIN, TR_ALINTI, True)], TABLO, BUGUN)
    assert blok["durum"] == "dogrulandi"
    assert (blok["senaryo"], blok["toplam"], blok["anilan"]) == (4, 7, [4])
    assert blok["cumle"] == "Sınavınızın içeriği, MEB konu soru dağılım tablosu 4. senaryo ağırlıklı olacaktır."
    assert blok["eslesen_konu_sayisi"] == 2 and blok["eslesmeyen_konular"] == []
    duyuruda = {d["kod"] for d in blok["dagilim"] if d["duyuruda"]}
    assert duyuruda == {"T.O.7.4", "T.O.7.5"}
    assert {d["kod"] for d in blok["dagilim"]} == {"T.O.7.4", "T.O.7.5", "T.O.7.7", "T.O.7.21", "T.Y.7.18", "T.Y.7.21"}
    assert blok["kaynak"].startswith("https://odsgm.meb.gov.tr/") and blok["meb_guncelleme"]


def test_kismen():
    blok = ss.senaryo_blogu(kayit(konular=TR_KONULAR + ["Metnin derin anlamını belirlemeye yönelik üst düzey çıkarımlar yapabilme"]),
                            [(TR_METIN, TR_ALINTI, True)], TABLO, BUGUN)
    assert blok["durum"] == "kismen"
    assert blok["senaryo_disi_konular"] == ["Metnin derin anlamını belirlemeye yönelik üst düzey çıkarımlar yapabilme"]


def test_senaryo_yok():
    metin = "1.1 sınavı 9. senaryo ağırlıklı olacaktır."
    blok = ss.senaryo_blogu(kayit(), [(metin, metin, True)], TABLO, BUGUN)
    assert blok["durum"] == "senaryo_yok" and blok["anilan"] == [9] and blok["senaryo_sayisi"] == 6
    assert blok["senaryo"] is None and blok["dagilim"] == []


def test_ulke_geneli():
    blok = ss.senaryo_blogu(kayit(baslik="1.2 Ara Değerlendirme", tarih="2026-12-10"), [], TABLO, BUGUN)
    assert blok["durum"] == "ulke_geneli" and "Ülke Geneli" in blok["not"]


def test_belirtilmedi_adaylarla_ve_adaysiz():
    blok = ss.senaryo_blogu(kayit(konular=["Metnin derin anlamını belirlemeye yönelik basit çıkarımlar yapabilme"]),
                            [], TABLO, BUGUN)
    assert blok["durum"] == "belirtilmedi" and blok["senaryo_sayisi"] == 6
    s = TABLO["dersler"]["Türkçe"]["sinavlar"]["1"]["senaryolar"]
    assert blok["adaylar"] == sorted(int(n) for n, d in s.items() if "T.O.7.7" in d)
    blok = ss.senaryo_blogu(kayit(konular=["Osmanlı'nın kuruluşu"]), [], TABLO, BUGUN)
    assert blok["adaylar"] == [] and blok["eslesmeyen_konular"] == ["Osmanlı'nın kuruluşu"]


def test_ozet_ve_arac_metni():
    blok = ss.senaryo_blogu(kayit(konular=TR_KONULAR), [(TR_METIN, TR_ALINTI, True)], TABLO, BUGUN)
    assert ss.ozet(blok) == "4. senaryo doğrulandı · 7 soru"
    sinav = {"id": "x", "course": "Türkçe", "title": "1.1 Ara Değerlendirme Sınavı", "date": "2026-10-22",
             "status": "upcoming", "senaryo": blok}
    govde, etiket = ss.arac_metni(TABLO, [sinav], {"ders": "Türkçe"})
    assert "T.O.7.5 → 2 soru" in govde and "Toplam 7 soru" in govde and "(duyuruda)" in govde
    assert etiket == "MEB konu-soru dağılım tablosu · Türkçe 7 · 1. yazılı"
    govde, _ = ss.arac_metni(TABLO, [], {"ders": "Fen", "sinav_no": 1, "senaryo": 2})
    assert "Senaryo 2" in govde and "Toplam" in govde
    govde, _ = ss.arac_metni(TABLO, [], {"ders": "Fen Bilimleri", "sinav_no": 1})
    assert govde.count("Senaryo ") >= 5
    assert len(govde) <= 3900
    with pytest.raises(ValueError, match="sinav_no"):
        ss.arac_metni(TABLO, [], {"ders": "Fen Bilimleri"})
    with pytest.raises(ValueError, match="tablosunda yok"):
        ss.arac_metni(TABLO, [], {"ders": "Bilişim", "sinav_no": 1})
```

- [ ] **Step 2: Kırmızıyı gör**

Run: `env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest -q tests/test_sinav_senaryo.py`
Expected: FAIL — `ImportError: cannot import name 'sinav_senaryo' from 'src'`.

- [ ] **Step 3: Eşleştiriciyi yaz** — `src/sinav_senaryo.py`:

```python
"""MEB konu-soru dağılım senaryoları: tablo okuma ve sınav ↔ senaryo eşleştirme (spec 2026-10-19 §3).

Saf işlevler; ağ ve dosya yazımı yok. Tablo `scripts/odsgm_senaryo_tablolari.py`'nin ürettiği
src/sinav_senaryolari.json'dur."""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from src.course_names import normalize_course
from src.sinav_tarihi import katla

TABLO = Path(__file__).with_name("sinav_senaryolari.json")
SURUM = 1
HARIC_TURLER = frozenset({"kisa_sinav", "konu_tarama"})
PENCERE = 400
CUMLE_SINIRI = 300
ESIK = 0.6
GOVDE_SINIRI = 3900

_DONEM_SINAV = re.compile(r"(?<![\d.])([12])\s*\.\s*([12])(?![\d.])")
_SINAV_NO = re.compile(r"\b([12])\s*\.?\s*(?:ortak\s+)?(?:yazili|sinav)")
_SOZCUK_NO = re.compile(r"\b(birinci|ikinci)\s+(?:ortak\s+)?(?:yazili|sinav)")
_DONEM = re.compile(r"\b([12])\s*\.?\s*donem")
_SIRA = {"birinci": 1, "ikinci": 2, "ucuncu": 3, "dorduncu": 4, "besinci": 5, "altinci": 6,
         "yedinci": 7, "sekizinci": 8, "dokuzuncu": 9, "onuncu": 10}
_LISTE = r"\d{1,2}\s*\.?(?:\s*(?:,|ve|veya|ile)\s*\d{1,2}\s*\.?)*"
_ONCE = re.compile(rf"(?<![\d.])({_LISTE})\s*senaryo")
_SONRA = re.compile(r"senaryo\w*\s+(\d{1,2}(?:\s*(?:,|ve|veya)\s*\d{1,2})*)(?![\d.])")
_SOZCUK = re.compile(r"\b(" + "|".join(_SIRA) + r")\s+senaryo")
_TARIH_IFADESI = re.compile(r"\b\d{1,2}\s+(ocak|subat|mart|nisan|mayis|haziran|temmuz|agustos|eylul|ekim|kasim|aralik)\b"
                            r"|\b\d{1,2}[./]\d{1,2}[./]\d{2,4}\b")
# Cümle sonu: rakam olmayan bir karakterden sonra gelen nokta/ünlem/soru + boşluk + büyük harf ya da
# rakam; ya da satır sonu. "4. Senaryo"daki nokta rakamdan sonra geldiği için bölmez.
_CUMLE_AYIR = re.compile(r"(?<=\D[.!?])\s+(?=[A-ZÇĞİÖŞÜ0-9])|\n+")
_DURAK = frozenset({"ile", "ve", "veya", "icin", "ilgili", "yonelik", "olan", "gibi", "bir", "bu", "da", "de"})
_KOD_ONEKI = re.compile(r"^[a-z]{1,5}(?:\.[a-z]{1,5})*\.\d{1,2}\.\d{1,2}(?:\.\d{1,2})?\.?\s*")


def tablo_oku(yol: Path | None = None) -> dict | None:
    try:
        veri = json.loads(Path(yol or TABLO).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(veri, dict) or veri.get("surum") != SURUM or not isinstance(veri.get("dersler"), dict) \
            or not isinstance(veri.get("kaynak"), dict):
        return None
    return veri


def _gun(deger: Any) -> date | None:
    try:
        return date.fromisoformat(str(deger)[:10]) if deger else None
    except ValueError:
        return None


def _donem_ayi(ay: int) -> int | None:
    if ay >= 9 or ay == 1:
        return 1
    if 2 <= ay <= 6:
        return 2
    return None


def sutun_coz(kayit: dict, tablo: dict, bugun: date) -> tuple[str, int] | None:
    if kayit.get("tur") in HARIC_TURLER:
        return None
    ders = kayit.get("ders")
    if ders not in tablo["dersler"]:
        return None
    b = katla(kayit.get("baslik") or "")
    donem = no = None
    m = _DONEM_SINAV.search(b)
    if m:
        donem, no = int(m.group(1)), int(m.group(2))
    else:
        m = _SINAV_NO.search(b)
        if m:
            no = int(m.group(1))
        else:
            m = _SOZCUK_NO.search(b)
            if m:
                no = 1 if m.group(1) == "birinci" else 2
        d = _DONEM.search(b)
        if d:
            donem = int(d.group(1))
    if no is None:
        return None
    if donem is None:
        gun = _gun(kayit.get("tarih")) or _gun(kayit.get("hafta")) or bugun
        donem = _donem_ayi(gun.month)
    if donem != tablo["kaynak"]["donem"] or str(no) not in tablo["dersler"][ders]["sinavlar"]:
        return None
    return ders, no


def _sayilar(katli: str) -> list[int]:
    bulunan: list[int] = []
    for m in _ONCE.finditer(katli):
        bulunan += [int(x) for x in re.findall(r"\d{1,2}", m.group(1))]
    for m in _SONRA.finditer(katli):
        bulunan += [int(x) for x in re.findall(r"\d{1,2}", m.group(1))]
    for m in _SOZCUK.finditer(katli):
        bulunan.append(_SIRA[m.group(1)])
    return [s for s in dict.fromkeys(bulunan) if 1 <= s <= 10]


def _cumleler(metin: str) -> list[str]:
    return [c.strip() for c in _CUMLE_AYIR.split(metin or "") if c and c.strip()]


def senaryo_cumlesi(metin: str, alinti: str, tek: bool) -> tuple[list[int], str | None]:
    cumleler = _cumleler(metin)
    if tek:
        aday = cumleler
    else:
        ilk = katla((_cumleler(alinti) or [""])[0])[:40]
        bas = next((i for i, c in enumerate(cumleler) if ilk and ilk in katla(c)), None)
        if bas is None:
            aday = _cumleler(alinti)
        else:
            aday, uzunluk = [], 0
            for i, c in enumerate(cumleler[bas:]):
                if i > 0 and (_TARIH_IFADESI.search(katla(c)) or uzunluk >= PENCERE):
                    break
                aday.append(c)
                uzunluk += len(c)
    sayilar: list[int] = []
    cumle = None
    for c in aday:
        bulunan = _sayilar(katla(c))
        if bulunan:
            sayilar += [s for s in bulunan if s not in sayilar]
            cumle = cumle or c[:CUMLE_SINIRI]
    return sorted(sayilar), cumle


def _kokler(metin: str) -> set[str]:
    return {s[:5] for s in re.findall(r"[a-z0-9]+", katla(metin)) if len(s) >= 3 and s not in _DURAK}


def _puan(a: str, b: str) -> float:
    x, y = _KOD_ONEKI.sub("", katla(a)), _KOD_ONEKI.sub("", katla(b))
    if len(min(x, y, key=len)) >= 10 and (x in y or y in x):
        return 1.0
    ka, kb = _kokler(x), _kokler(y)
    return 2 * len(ka & kb) / (len(ka) + len(kb)) if ka and kb else 0.0


def konu_eslestir(konu: str, ciktilar: list[dict]) -> list[str]:
    k = katla(konu)
    kodlar = [c["kod"] for c in ciktilar
              if re.search(rf"(?<![\w.]){re.escape(katla(c['kod']))}(?!\d)", k)]
    if kodlar:
        return kodlar
    en, puan = None, 0.0
    for c in ciktilar:
        p = _puan(konu, c["metin"])
        if p > puan:
            en, puan = [c["kod"]], p
    if en and puan >= ESIK:
        return en
    gruplar: dict[str, list[str]] = {}
    for c in ciktilar:
        if c.get("konu"):
            gruplar.setdefault(c["konu"], []).append(c["kod"])
    en, puan = None, 0.0
    for ad, kodlar in gruplar.items():
        p = _puan(konu, ad)
        if p > puan:
            en, puan = kodlar, p
    return list(en) if en and puan >= ESIK else []


def senaryo_blogu(kayit: dict, metinler: list[tuple[str, str, bool]], tablo: dict, bugun: date) -> dict | None:
    sutun = sutun_coz(kayit, tablo, bugun)
    if sutun is None:
        return None
    ders, no = sutun
    dt = tablo["dersler"][ders]
    sinav = dt["sinavlar"][str(no)]
    anilan: list[int] = []
    cumle = None
    for metin, alinti, tek in metinler:
        sayilar, c = senaryo_cumlesi(metin, alinti, tek)
        anilan += [s for s in sayilar if s not in anilan]
        cumle = cumle or c
    anilan.sort()
    eslesme = {konu: konu_eslestir(konu, dt["ciktilar"]) for konu in kayit.get("konular") or []}
    eslesen = {konu: set(kodlar) for konu, kodlar in eslesme.items() if kodlar}
    blok = {"durum": None, "ders": ders, "sinav_no": no, "donem": tablo["kaynak"]["donem"], "anilan": anilan,
            "cumle": cumle, "senaryo": None, "toplam": None, "dagilim": [],
            "eslesen_konu_sayisi": len(eslesen),
            "eslesmeyen_konular": [k for k, kodlar in eslesme.items() if not kodlar],
            "senaryo_disi_konular": [], "adaylar": [], "senaryo_sayisi": 0,
            "kaynak": tablo["kaynak"]["sayfa"], "meb_guncelleme": tablo["kaynak"]["meb_guncelleme"]}
    if sinav["tur"] == "ulke_geneli":
        blok.update(durum="ulke_geneli", **{"not": sinav["not"]})
        return blok
    senaryolar = sinav["senaryolar"]
    blok["senaryo_sayisi"] = len(senaryolar)
    if anilan:
        gecerli = [n for n in anilan if str(n) in senaryolar]
        if not gecerli:
            blok["durum"] = "senaryo_yok"
            return blok
        n = gecerli[0]
        dagilim = senaryolar[str(n)]
        duyuruda = set().union(*eslesen.values()) if eslesen else set()
        blok.update(senaryo=n, toplam=sum(dagilim.values()),
                    dagilim=[{"kod": c["kod"], "metin": c["metin"], "soru": dagilim[c["kod"]],
                              "duyuruda": c["kod"] in duyuruda} for c in dt["ciktilar"] if c["kod"] in dagilim])
        blok["senaryo_disi_konular"] = [k for k, kodlar in eslesen.items() if not kodlar & set(dagilim)]
        blok["durum"] = "kismen" if blok["senaryo_disi_konular"] else "dogrulandi"
        return blok
    if eslesen:
        blok["adaylar"] = sorted(int(n) for n, d in senaryolar.items()
                                 if all(kodlar & set(d) for kodlar in eslesen.values()))
    blok["durum"] = "belirtilmedi"
    return blok


def _liste(sayilar: list[int]) -> str:
    parca = [f"{s}." for s in sayilar]
    return parca[0] if len(parca) == 1 else ", ".join(parca[:-1]) + " ve " + parca[-1]


def ozet(blok: dict) -> str:
    d = blok.get("durum")
    if d == "dogrulandi":
        return f"{blok['senaryo']}. senaryo doğrulandı · {blok['toplam']} soru"
    if d == "kismen":
        return f"{blok['senaryo']}. senaryo · {blok['toplam']} soru · bazı konular senaryoda yok"
    if d == "senaryo_yok":
        return f"duyuru {_liste(blok['anilan'])} senaryo diyor; tabloda yok (1–{blok['senaryo_sayisi']})"
    if d == "ulke_geneli":
        return "ülke genelinde ortak sınav; senaryo yok"
    adaylar = f"; uyumlu: {_liste(blok['adaylar'])}" if blok.get("adaylar") else ""
    return f"senaryo belirtilmedi ({blok['senaryo_sayisi']} senaryo{adaylar})"


def _dagilim_satirlari(dt: dict, dagilim: dict[str, int], duyuruda: set[str]) -> list[str]:
    satirlar = []
    for c in dt["ciktilar"]:
        if c["kod"] in dagilim:
            isaret = " (duyuruda)" if c["kod"] in duyuruda else ""
            satirlar.append(f"- {c['kod']} → {dagilim[c['kod']]} soru · {c['metin']}{isaret}")
    return satirlar


def arac_metni(tablo: dict, sinavlar: list[dict], args: dict) -> tuple[str, str]:
    ham = str(args.get("ders") or "").strip()
    ders = normalize_course(ham) or ham
    if ders == "Fen":
        ders = "Fen Bilimleri"
    if ders not in tablo["dersler"]:
        raise ValueError(f"'{ham}' MEB senaryo tablosunda yok; bu ders için senaryo verilemez. "
                         f"Tabloda olanlar: {', '.join(tablo['dersler'])}.")
    dt = tablo["dersler"][ders]
    no = args.get("sinav_no")
    senaryo = args.get("senaryo")
    sinav = next((e for e in sinavlar if isinstance(e, dict) and e.get("status") == "upcoming"
                  and e.get("course") == ders and isinstance(e.get("senaryo"), dict)
                  and (no is None or e["senaryo"].get("sinav_no") == no)), None)
    blok = sinav["senaryo"] if sinav else None
    no = no or (blok or {}).get("sinav_no")
    if no is None:
        raise ValueError("Hangi yazılı? sinav_no olarak 1 ya da 2 ver.")
    if str(no) not in dt["sinavlar"]:
        raise ValueError(f"{ders} için {no}. yazılı tabloda yok.")
    k = tablo["kaynak"]
    gun = k["meb_guncelleme"][:10].split("-")
    satirlar = [f"{ders} · 7. sınıf · {k['donem']}. Dönem {no}. Ortak Yazılı "
                f"(MEB konu-soru dağılım tablosu, güncelleme {gun[2]}.{gun[1]}.{gun[0]})"]
    if sinav:
        satirlar.append(f"Sınav: {sinav.get('title')} · {str(sinav.get('date') or 'tarih belirsiz')[:10]}")
        satirlar.append(f"Durum: {ozet(blok)}.")
        if blok.get("cumle"):
            satirlar.append(f"Duyurunun cümlesi: “{blok['cumle']}”")
        if blok.get("eslesmeyen_konular"):
            satirlar.append("MEB tablosunda karşılığı bulunamayan konu: " + "; ".join(blok["eslesmeyen_konular"]))
    sinav_tablosu = dt["sinavlar"][str(no)]
    if sinav_tablosu["tur"] == "ulke_geneli":
        satirlar.append("Bu sınav ülke genelinde ortak yapılır; MEB bu sınav için senaryo vermiyor.")
        return "\n".join(satirlar), f"MEB konu-soru dağılım tablosu · {ders} 7 · {no}. yazılı"
    senaryolar = sinav_tablosu["senaryolar"]
    duyuruda = {d["kod"] for d in (blok or {}).get("dagilim", []) if d.get("duyuruda")}
    secilen = senaryo or (blok or {}).get("senaryo")
    if secilen is not None:
        if str(secilen) not in senaryolar:
            raise ValueError(f"{ders} {no}. yazılıda {secilen}. senaryo yok (1–{len(senaryolar)}).")
        dagilim = senaryolar[str(secilen)]
        satirlar.append(f"Senaryo {secilen} · {sum(dagilim.values())} soru. Yazılacak dağılım:")
        satirlar += _dagilim_satirlari(dt, dagilim, duyuruda)
        satirlar.append(f"Toplam {sum(dagilim.values())} soru. Örnek sınavda soru sayısı ve dağılım bu listeye birebir uyar.")
    else:
        adaylar = (blok or {}).get("adaylar") or []
        if adaylar:
            satirlar.append(f"Duyurudaki konularla uyumlu senaryolar (tahmin): {_liste(adaylar)}")
        satirlar.append("Senaryolar:")
        for n in sorted(senaryolar, key=int):
            d = senaryolar[n]
            satirlar.append(f"- Senaryo {n} · {sum(d.values())} soru: "
                            + ", ".join(f"{kod}" + (f" ({s})" if s > 1 else "") for kod, s in d.items()))
        satirlar.append("Toplam soru sayıları yukarıda; hangi senaryonun kullanılacağı belli değil.")
    govde = "\n".join(satirlar)
    if len(govde) > GOVDE_SINIRI:
        govde = govde[:GOVDE_SINIRI - 1] + "…"
    return govde, f"MEB konu-soru dağılım tablosu · {ders} 7 · {no}. yazılı"
```

- [ ] **Step 4: Yeşili gör**

Run: `env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest -q tests/test_sinav_senaryo.py`
Expected: hepsi PASS. Bir parametre kırmızıysa kural ile testi spec §3'e karşı oku; testi gevşetme, kodu düzelt (gerekirse defterde `Ruling:`).

- [ ] **Step 5: Commit**

```bash
git add src/sinav_senaryo.py tests/test_sinav_senaryo.py
git commit -m "feat(sinav): sınav ↔ MEB senaryosu eşleştirici

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Tespite bağlanış — `sinavlar.json`'da `senaryo` bloğu

**Files:**
- Modify: `src/sinav_tespiti.py` (`birlestir`, `tespit_et`, `kuru_rapor`)
- Test: `tests/test_sinav_tespiti_senaryo.py`

**Interfaces:**
- Consumes: Görev 3 `tablo_oku`, `senaryo_blogu`.
- Produces: `birlestir(taban, bulgular, onceki, simdi, senaryolar: dict | None = None)`; kayıtlarda isteğe bağlı `senaryo` anahtarı; `tespit_et` özetinin `hatalar`'ında tablo okunamazsa `"senaryo tablosu okunamadı"`.

- [ ] **Step 1: Başarısız testleri yaz** — `tests/test_sinav_tespiti_senaryo.py`:

```python
"""Tespit, sınav kaydına MEB senaryo bloğunu yazar (spec §3.5)."""
from datetime import date, datetime

from src import sinav_senaryo, sinav_tespiti
from src.sinav_cikarimi import Bulgu
from src.sinav_kaynaklari import Aday
from src.sinav_tespiti import birlestir, kuru_rapor

SIMDI = datetime(2026, 10, 19, 10, 0)
TABLO = sinav_senaryo.tablo_oku()
METIN = ("22 Ekim Perşembe Günü 1.1 Ara Değerlendirme Sınavınızı gerçekleştireceğiz. Sınavınızın içeriği, "
         "MEB konu soru dağılım tablosu 4. senaryo ağırlıklı olacaktır. Konu başlıklarınız:\n"
         "Metnin yüzey anlamını belirleyebilme")
ALINTI = "22 Ekim Perşembe Günü 1.1 Ara Değerlendirme Sınavınızı gerçekleştireceğiz."


def _bulgu():
    aday = Aday(METIN, "Türkçe", date(2026, 10, 19), "ders_karti",
                [{"bolum": "ders_icerikleri_haftalar", "hafta": "6. Hafta", "ders": "Türkçe", "sira": 1}])
    return Bulgu("Türkçe", "ortak_sinav", "1.1 Ara Değerlendirme Sınavı", date(2026, 10, 22), None, None,
                 ["Metnin yüzey anlamını belirleyebilme"], ALINTI, aday)


def test_blok_yazilir_ve_icerik_surumu_degismez():
    duz = birlestir([], [_bulgu()], None, SIMDI)
    ile = birlestir([], [_bulgu()], None, SIMDI, senaryolar=TABLO)
    assert "senaryo" not in duz[0]
    assert ile[0]["senaryo"]["durum"] == "dogrulandi" and ile[0]["senaryo"]["senaryo"] == 4
    assert ile[0]["icerik_surumu"] == duz[0]["icerik_surumu"]


def test_sutun_cozulmezse_anahtar_yazilmaz():
    b = _bulgu()
    b = Bulgu(b.ders, "kisa_sinav", "Büyük Quiz", b.tarih, None, None, [], b.alinti, b.aday)
    assert "senaryo" not in birlestir([], [b], None, SIMDI, senaryolar=TABLO)[0]


def test_tablo_yoksa_not_duser(tmp_path, monkeypatch):
    class Okuyucu:
        def oku(self, *a, **k):
            raise AssertionError("model çağrılmamalı")
    monkeypatch.setattr(sinav_senaryo, "tablo_oku", lambda yol=None: None)
    belge = sinav_tespiti.tespit_et(tmp_path, {}, [], SIMDI, bitis=0.0, okuyucu=Okuyucu())
    assert belge["ozet"]["hatalar"][0] == "senaryo tablosu okunamadı"


def test_kuru_rapor_senaryo_satiri():
    belge = {"sinavlar": birlestir([], [_bulgu()], None, SIMDI, senaryolar=TABLO), "ozet": {}}
    assert "  Senaryo: dogrulandi · Türkçe 1. yazılı · 4. senaryo · 7 soru" in kuru_rapor(belge).splitlines()
```

- [ ] **Step 2: Kırmızıyı gör**

Run: `env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest -q tests/test_sinav_tespiti_senaryo.py`
Expected: FAIL — `TypeError: birlestir() got an unexpected keyword argument 'senaryolar'` (ve tablo testi için `hatalar[0]` uyuşmazlığı).
Not: `test_tablo_yoksa_not_duser` boş veriyle `tespit_et`'i çağırır; aday yoksa model çağrılmaz. `SinavCikarici` boş listeyle de bir okuyucu nesnesi ister; testin `Okuyucu`'su bunu karşılar. Bu çağrı `tmp_path`'e (önbellek/defter) yazabilir — sorun değil.

- [ ] **Step 3: `src/sinav_tespiti.py`'yi değiştir**

İçe aktarmalara ekle:

```python
from collections import Counter

from src import sinav_senaryo
```

`birlestir` imzası ve gövdesi — imza:

```python
def birlestir(taban: list[dict], bulgular: list[Bulgu], onceki: dict | None, simdi: datetime,
              senaryolar: dict | None = None) -> list[dict]:
```

Fonksiyonun başında (`kayitlar = []` satırından sonra):

```python
    # Each record's findings, for the MEB scenario sentence (spec 2026-10-19 §3.5): the full candidate
    # text is in hand only here. A text that yielded a single finding is searched whole.
    kayit_bulgulari: dict[int, list[Bulgu]] = {}
    aday_sayisi = Counter(id(b.aday) for b in bulgular)
```

İki döngüde `_ekle(eslesen, b)` ve `_ekle(hedef, b)` satırlarının hemen ardından sırasıyla:

```python
        kayit_bulgulari.setdefault(id(eslesen), []).append(b)
```
```python
        kayit_bulgulari.setdefault(id(hedef), []).append(b)
```

`for k in kalan:` döngüsünde `k["icerik_surumu"] = _surum(k)` satırından sonra:

```python
        if senaryolar is not None:
            metinler = [(b.aday.metin, b.alinti, aday_sayisi[id(b.aday)] == 1)
                        for b in kayit_bulgulari.get(id(k), [])]
            blok = sinav_senaryo.senaryo_blogu(k, metinler, senaryolar, bugun)
            if blok is not None:
                k["senaryo"] = blok   # not part of icerik_surumu: no new alert (spec §3.5)
```

`tespit_et` içinde `kayitlar = birlestir(...)` satırını ve dönüşü değiştir:

```python
    tablo = sinav_senaryo.tablo_oku()
    kayitlar = birlestir(taban, sonuc.bulgular, onceki, simdi, senaryolar=tablo)
    hatalar = (["senaryo tablosu okunamadı"] if tablo is None else []) + list(sonuc.hatalar)
    return {"uretildi": simdi.isoformat(timespec="seconds"), "surum": SURUM, "sinavlar": kayitlar,
            "ozet": {"aday": sonuc.aday, "incelenen": sonuc.incelenen, "incelenmedi": sonuc.incelenmedi,
                     "butce_usd": sonuc.butce_usd, "hatalar": hatalar[:5]}}
```

`kuru_rapor`'da kaynak döngüsünden sonra (aynı `for k` içinde):

```python
        s = k.get("senaryo")
        if isinstance(s, dict):
            satirlar.append(f"  Senaryo: {s.get('durum')} · {s.get('ders')} {s.get('sinav_no')}. yazılı"
                            + (f" · {s['senaryo']}. senaryo · {s['toplam']} soru" if s.get("senaryo") else "")
                            + (f" · uyumlu {s['adaylar']}" if s.get("adaylar") else ""))
```

- [ ] **Step 4: Yeşili gör ve eski testleri koştur**

Run: `env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest -q tests/test_sinav_tespiti_senaryo.py tests/test_sinav_tespiti.py`
Expected: hepsi PASS.

- [ ] **Step 5: Commit**

```bash
git add src/sinav_tespiti.py tests/test_sinav_tespiti_senaryo.py
git commit -m "feat(sinav): tespit, sınav kaydına MEB senaryo bloğunu yazar

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: API ve `sinavlar` aracı satırı

**Files:**
- Modify: `src/dashboard_api.py` (`_kayittan_sinav`, `_sinav_api_listesi`'nin yedek dalı)
- Modify: `src/assistant_tools.py` (`sinavlar_metni`)
- Test: `tests/test_sinav_senaryo_api.py`

**Interfaces:**
- Consumes: Görev 4'ün kayıttaki `senaryo` bloğu; Görev 3 `ozet`.
- Produces: `/api/exams` her sınavda `senaryo: dict | null`; `sinavlar` aracının yaklaşan sınav satırında `MEB senaryosu: <ozet> — ayrıntı için sinav_senaryosu`.

- [ ] **Step 1: Başarısız testleri yaz** — `tests/test_sinav_senaryo_api.py`:

```python
"""/api/exams senaryo bloğunu geçirir; sinavlar aracı özetini yazar (spec §4, §6)."""
from datetime import datetime

from src import dashboard_api
from src.assistant_tools import sinavlar_metni

BLOK = {"durum": "dogrulandi", "ders": "Türkçe", "sinav_no": 1, "donem": 1, "anilan": [4], "cumle": "4. senaryo",
        "senaryo": 4, "toplam": 7, "dagilim": [], "eslesen_konu_sayisi": 2, "eslesmeyen_konular": [],
        "senaryo_disi_konular": [], "adaylar": [], "senaryo_sayisi": 6,
        "kaynak": "https://odsgm.meb.gov.tr/x", "meb_guncelleme": "2026-09-10T17:27"}


def _belge(senaryo):
    k = {"id": "a1", "ders": "Türkçe", "tur": "ortak_sinav", "baslik": "1.1 Ara Değerlendirme Sınavı",
         "tarih": "2026-10-22", "saat": None, "hafta": None, "konular": [], "kaynaklar": [],
         "sentetik": False, "taban": None, "son_yayin": "2026-10-19", "icerik_surumu": "x",
         "ilk_tespit": None, "degisti": None}
    if senaryo is not None:
        k["senaryo"] = senaryo
    return {"surum": 1, "uretildi": "2026-10-19T00:00:00", "sinavlar": [k], "ozet": {"incelenmedi": 0}}


def test_api_blogu_gecirir(monkeypatch):
    monkeypatch.setattr(dashboard_api, "_sinavlar_belgesi", lambda: _belge(BLOK))
    e = dashboard_api._sinav_api_listesi({}, now=datetime(2026, 10, 19, 10))["exams"][0]
    assert e["senaryo"] == BLOK


def test_api_blok_yoksa_null(monkeypatch):
    monkeypatch.setattr(dashboard_api, "_sinavlar_belgesi", lambda: _belge(None))
    assert dashboard_api._sinav_api_listesi({}, now=datetime(2026, 10, 19, 10))["exams"][0]["senaryo"] is None
    monkeypatch.setattr(dashboard_api, "_sinavlar_belgesi", lambda: None)
    eski = dashboard_api._sinav_api_listesi({"takvim": []}, now=datetime(2026, 10, 19, 10))
    assert all(e["senaryo"] is None for e in eski["exams"])


def test_sinavlar_araci_ozet_satiri():
    e = {"course": "Türkçe", "title": "1.1 Ara Değerlendirme Sınavı", "rawTitle": "1.1 Ara Değerlendirme Sınavı",
         "date": "2026-10-22", "allDay": True, "status": "upcoming", "konular": [], "kaynaklar": [], "senaryo": BLOK}
    metin = sinavlar_metni([e], datetime(2026, 10, 19, 10))
    assert "MEB senaryosu: 4. senaryo doğrulandı · 7 soru — ayrıntı için sinav_senaryosu" in metin
```

- [ ] **Step 2: Kırmızıyı gör**

Run: `env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest -q tests/test_sinav_senaryo_api.py`
Expected: FAIL — `KeyError: 'senaryo'` ve özet satırı yok.

- [ ] **Step 3: Kodu değiştir**

`src/dashboard_api.py` `_kayittan_sinav` içindeki `e.update({...})` sözlüğüne bir anahtar ekle:

```python
        "senaryo": k["senaryo"] if isinstance(k.get("senaryo"), dict) else None,
```

`_sinav_api_listesi`'nin `belge is None` dalındaki `e.update({...})` sözlüğüne:

```python
                      "senaryo": None,
```

`src/assistant_tools.py`: dosyanın üst içe aktarmalarına `from src import sinav_senaryo` ekle. `sinavlar_metni` içindeki `satir()` işlevinde, `if ham_ad:` bloğunun sonunda (kaynak satırından sonra):

```python
            s = e.get("senaryo")
            if isinstance(s, dict):
                metin += f"\n  MEB senaryosu: {sinav_senaryo.ozet(s)} — ayrıntı için {SENARYO_TOOL}"
```

ve modül sabitlerine (`SINAV_TOOL = "sinavlar"` satırının altına):

```python
# MEB konu-soru dağılım senaryoları (spec 2026-10-19 §6): declared beside `sinavlar` when the
# scenario table is readable.
SENARYO_TOOL = "sinav_senaryosu"
```

- [ ] **Step 4: Yeşili gör ve komşu testleri koştur**

Run: `env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest -q tests/test_sinav_senaryo_api.py tests/test_asistan_adim_etiketleri.py`
Expected: `test_sinav_senaryo_api.py` 3 passed. `test_asistan_adim_etiketleri.py` **kırmızı** (yeni `SENARYO_TOOL` adının etiketi yok) — bu Görev 7'de kapanır; burada rapora yaz, düzeltme.

- [ ] **Step 5: Commit**

```bash
git add src/dashboard_api.py src/assistant_tools.py tests/test_sinav_senaryo_api.py
git commit -m "feat(sinav): /api/exams senaryo bloğunu geçirir, sınav listesi özetini yazar

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Kart — "MEB konu-soru dağılımı" bölümü

**Files:**
- Modify: `dashboard/src/types.ts` (`SinavSenaryosu`, `ExamItem.senaryo`)
- Create: `dashboard/src/utils/sinavSenaryosu.ts`
- Test: `dashboard/tests/sinavSenaryosu.test.ts`
- Modify: `dashboard/src/components/SinavKarti.tsx`, `dashboard/src/components/SinavKarti.scss`, `dashboard/src/components/ExamTimeline.tsx` (`hasDetails`)
- Test: `dashboard/tests/e2e/sinav-senaryo.spec.ts`

**Interfaces:**
- Consumes: `/api/exams` `senaryo` bloğu (Görev 5); `asistan/sayfaBaglami.ts` `asistanaSor`.
- Produces: `senaryoGorunumu(s: SinavSenaryosu) -> { ikon: 'onay' | 'uyari' | null; cumleler: string[]; satirlar: { metin: string; duyuruda: boolean }[]; dugme: string | null; kaynak: string }`; `siraListesi(sayilar: number[]) -> string`; `MebSenaryoBolumu` (SinavKarti.tsx içinde, dışa aktarılmaz).

- [ ] **Step 1: Tipleri ekle** — `dashboard/src/types.ts`, `ExamItem`'dan önce:

```ts
/** MEB konu-soru dağılım senaryosu (spec 2026-10-19 §3.4); src/sinav_senaryo.py yazar. */
export interface SinavSenaryosu {
  durum: 'dogrulandi' | 'kismen' | 'senaryo_yok' | 'ulke_geneli' | 'belirtilmedi'
  ders: string
  sinav_no: number
  anilan: number[]
  cumle: string | null
  senaryo: number | null
  toplam: number | null
  dagilim: { kod: string; metin: string; soru: number; duyuruda: boolean }[]
  eslesen_konu_sayisi: number
  eslesmeyen_konular: string[]
  senaryo_disi_konular: string[]
  adaylar: number[]
  senaryo_sayisi: number
  not?: string
  kaynak: string
  meb_guncelleme: string
}
```

ve `ExamItem` içine (`tarihBelirsiz?` satırından sonra):

```ts
  /** MEB senaryo doğrulaması; sütun çözülemediyse null. */
  senaryo?: SinavSenaryosu | null
```

- [ ] **Step 2: Başarısız birim testlerini yaz** — `dashboard/tests/sinavSenaryosu.test.ts`:

```ts
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { senaryoGorunumu } from '../src/utils/sinavSenaryosu.ts'
import type { SinavSenaryosu } from '../src/types.ts'

const TABAN: SinavSenaryosu = {
  durum: 'dogrulandi', ders: 'Türkçe', sinav_no: 1, anilan: [4], cumle: '4. senaryo ağırlıklı',
  senaryo: 4, toplam: 7,
  dagilim: [
    { kod: 'T.O.7.4', metin: 'Söz varlığı', soru: 1, duyuruda: true },
    { kod: 'T.O.7.5', metin: 'Metnin yüzey anlamını belirleyebilme', soru: 2, duyuruda: true },
    { kod: 'T.Y.7.21', metin: 'Yazım kuralları', soru: 1, duyuruda: false },
  ],
  eslesen_konu_sayisi: 2, eslesmeyen_konular: [], senaryo_disi_konular: [], adaylar: [], senaryo_sayisi: 6,
  kaynak: 'https://odsgm.meb.gov.tr/x', meb_guncelleme: '2026-09-10T17:27',
}

test('doğrulandı: onay, tek cümle, açılır liste', () => {
  const g = senaryoGorunumu(TABAN)
  assert.equal(g.ikon, 'onay')
  assert.deepEqual(g.cumleler, ['Duyurudaki 4. senaryo MEB tablosunda var: 7 soru. Duyurudaki 2 konu bu senaryoda.'])
  assert.equal(g.dugme, 'Senaryonun 3 çıktısını göster')
  assert.deepEqual(g.satirlar[1], { metin: '2 soru · T.O.7.5 Metnin yüzey anlamını belirleyebilme', duyuruda: true })
  assert.equal(g.kaynak, 'MEB, 10.09.2026')
})

test('birden çok senaryo anıldı', () => {
  const g = senaryoGorunumu({ ...TABAN, anilan: [3, 4], senaryo: 3 })
  assert.equal(g.cumleler[0], 'Duyuru 3. ve 4. senaryo diyor; 3. senaryo MEB tablosunda var: 7 soru. Duyurudaki 2 konu bu senaryoda.')
})

test('kısmen: uyarı ve senaryo dışı konu', () => {
  const g = senaryoGorunumu({ ...TABAN, durum: 'kismen', eslesen_konu_sayisi: 3, senaryo_disi_konular: ['Derin anlam'] })
  assert.equal(g.ikon, 'uyari')
  assert.deepEqual(g.cumleler, [
    'Duyurudaki 4. senaryo MEB tablosunda var: 7 soru. Duyurudaki 2 konu bu senaryoda.',
    'Şu konu 4. senaryoda yok: Derin anlam.',
  ])
})

test('senaryo yok', () => {
  const g = senaryoGorunumu({ ...TABAN, durum: 'senaryo_yok', anilan: [9], senaryo: null, toplam: null, dagilim: [] })
  assert.equal(g.ikon, 'uyari')
  assert.deepEqual(g.cumleler, ['Duyuru 9. senaryo diyor; MEB tablosunda bu sınav için 1–6 var.'])
  assert.equal(g.dugme, null)
})

test('ülke geneli', () => {
  const g = senaryoGorunumu({ ...TABAN, durum: 'ulke_geneli', anilan: [], senaryo: null, dagilim: [], senaryo_sayisi: 0 })
  assert.equal(g.ikon, null)
  assert.deepEqual(g.cumleler, ['Bu sınav ülke genelinde ortak yapılır; senaryo yok.'])
})

test('belirtilmedi: tahmin etiketi, tekil ve çoğul', () => {
  const b = { ...TABAN, durum: 'belirtilmedi' as const, anilan: [], senaryo: null, toplam: null, dagilim: [] }
  assert.deepEqual(senaryoGorunumu({ ...b, adaylar: [] }).cumleler,
    ['Duyuruda senaryo belirtilmedi · MEB tablosunda 6 senaryo var.'])
  assert.deepEqual(senaryoGorunumu({ ...b, adaylar: [4] }).cumleler[1],
    'Duyurudaki konular 4. senaryoyla uyumlu (TEDY’nin tahmini).')
  assert.deepEqual(senaryoGorunumu({ ...b, adaylar: [2, 3, 4] }).cumleler[1],
    'Duyurudaki konular 2., 3. ve 4. senaryolarla uyumlu (TEDY’nin tahmini).')
})

test('eşleşmeyen konu cümlesi', () => {
  const g = senaryoGorunumu({ ...TABAN, eslesmeyen_konular: ['Osmanlı'] })
  assert.equal(g.cumleler.at(-1), 'MEB tablosunda karşılığı bulunamayan konu: Osmanlı.')
})
```

- [ ] **Step 3: Kırmızıyı gör**

Run: `cd dashboard && node --test tests/sinavSenaryosu.test.ts`
Expected: FAIL — modül bulunamadı (`Cannot find module …/utils/sinavSenaryosu.ts`).

- [ ] **Step 4: Saf biçimlendiriciyi yaz** — `dashboard/src/utils/sinavSenaryosu.ts`:

```ts
import type { SinavSenaryosu } from '../types'

export interface SenaryoGorunumu {
  ikon: 'onay' | 'uyari' | null
  cumleler: string[]
  satirlar: { metin: string; duyuruda: boolean }[]
  dugme: string | null
  kaynak: string
}

/** [3] → "3.", [3, 4] → "3. ve 4.", [2, 3, 4] → "2., 3. ve 4." */
export function siraListesi(sayilar: number[]): string {
  const p = sayilar.map(s => `${s}.`)
  return p.length <= 1 ? (p[0] ?? '') : `${p.slice(0, -1).join(', ')} ve ${p.at(-1)}`
}

function mebTarihi(iso: string): string {
  const [y, a, g] = iso.slice(0, 10).split('-')
  return `MEB, ${g}.${a}.${y}`
}

/** Kartın "MEB konu-soru dağılımı" bölümü, bloktan (spec 2026-10-19 §5). Saf: test edilir. */
export function senaryoGorunumu(s: SinavSenaryosu): SenaryoGorunumu {
  const cumleler: string[] = []
  let ikon: SenaryoGorunumu['ikon'] = null
  let dugme: string | null = null
  if (s.durum === 'dogrulandi' || s.durum === 'kismen') {
    const ic = s.eslesen_konu_sayisi - s.senaryo_disi_konular.length
    const bas = s.anilan.length > 1
      ? `Duyuru ${siraListesi(s.anilan)} senaryo diyor; ${s.senaryo}. senaryo MEB tablosunda var: ${s.toplam} soru.`
      : `Duyurudaki ${s.senaryo}. senaryo MEB tablosunda var: ${s.toplam} soru.`
    cumleler.push(ic > 0 ? `${bas} Duyurudaki ${ic} konu bu senaryoda.` : bas)
    if (s.durum === 'kismen') cumleler.push(`Şu konu ${s.senaryo}. senaryoda yok: ${s.senaryo_disi_konular.join('; ')}.`)
    ikon = s.durum === 'kismen' ? 'uyari' : 'onay'
    dugme = `Senaryonun ${s.dagilim.length} çıktısını göster`
  } else if (s.durum === 'senaryo_yok') {
    ikon = 'uyari'
    cumleler.push(`Duyuru ${siraListesi(s.anilan)} senaryo diyor; MEB tablosunda bu sınav için 1–${s.senaryo_sayisi} var.`)
  } else if (s.durum === 'ulke_geneli') {
    cumleler.push('Bu sınav ülke genelinde ortak yapılır; senaryo yok.')
  } else {
    cumleler.push(`Duyuruda senaryo belirtilmedi · MEB tablosunda ${s.senaryo_sayisi} senaryo var.`)
    if (s.adaylar.length > 0) {
      const ek = s.adaylar.length > 1 ? 'senaryolarla' : 'senaryoyla'
      cumleler.push(`Duyurudaki konular ${siraListesi(s.adaylar)} ${ek} uyumlu (TEDY’nin tahmini).`)
    }
  }
  if (s.eslesmeyen_konular.length > 0) {
    cumleler.push(`MEB tablosunda karşılığı bulunamayan konu: ${s.eslesmeyen_konular.join('; ')}.`)
  }
  return {
    ikon, cumleler, dugme, kaynak: mebTarihi(s.meb_guncelleme),
    satirlar: s.dagilim.map(d => ({ metin: `${d.soru} soru · ${d.kod} ${d.metin}`, duyuruda: d.duyuruda })),
  }
}
```

Run: `cd dashboard && node --test tests/sinavSenaryosu.test.ts` → Expected: 7 passed.

- [ ] **Step 5: Başarısız e2e'yi yaz** — `dashboard/tests/e2e/sinav-senaryo.spec.ts`:

```ts
import { test, expect, type Page } from '@playwright/test'
import { createRequire } from 'node:module'
import AxeBuilder from '@axe-core/playwright'
import { mock, LIVE } from './_audit-fixtures'

test.use({ timezoneId: 'Europe/Istanbul', locale: 'tr-TR' })

const ACE = createRequire(import.meta.url).resolve('accessibility-checker-engine/ace.js')
const BLOK = {
  durum: 'dogrulandi', ders: 'Türkçe', sinav_no: 1, anilan: [4],
  cumle: 'Sınavınızın içeriği, MEB konu soru dağılım tablosu 4. senaryo ağırlıklı olacaktır.',
  senaryo: 4, toplam: 7,
  dagilim: [
    { kod: 'T.O.7.4', metin: 'Metinde geçen anlamını bilmediği söz varlığı unsurlarının anlamını tahmin edebilme', soru: 1, duyuruda: true },
    { kod: 'T.O.7.5', metin: 'Metnin yüzey anlamını belirleyebilme', soru: 2, duyuruda: true },
    { kod: 'T.Y.7.21', metin: 'Yazım kuralları ve noktalama işaretlerini uygulayabilme', soru: 1, duyuruda: false },
  ],
  eslesen_konu_sayisi: 2, eslesmeyen_konular: [], senaryo_disi_konular: [], adaylar: [], senaryo_sayisi: 6,
  kaynak: 'https://odsgm.meb.gov.tr/www/1donem-konu-soru-dagilim-tablolari-2026-2027/icerik/1724',
  meb_guncelleme: '2026-09-10T17:27',
}
const sinav = (senaryo: Record<string, unknown>) => ({ exams: { exams: [{
  id: 'tr11', course: 'Türkçe', title: '1.1 Ara Değerlendirme Sınavı', rawTitle: '1.1 Ara Değerlendirme Sınavı',
  courseColor: '#9f1853', examNumber: null, date: '2026-10-22', endDate: null, allDay: true, status: 'upcoming',
  grade: null, relatedHomework: [], relatedContent: [], tur: 'ortak_sinav',
  konular: ['Metnin yüzey anlamını belirleyebilme'], kaynaklar: [], senaryo,
}], stats: { upcoming: 1, past: 0, averageGrade: null } } })

async function ac(page: Page, senaryo: Record<string, unknown>) {
  await mock(page, { ...LIVE, ...sinav(senaryo) })
  await page.goto('/sinavlar')
  await page.getByRole('button', { name: 'Detaylar' }).first().click()
  await page.locator('.meb-senaryo').waitFor()
}

test('doğrulandı: cümle, ikon adı, liste klavyeyle açılır', async ({ page }) => {
  await ac(page, BLOK)
  const b = page.locator('.meb-senaryo')
  await expect(b).toContainText('Duyurudaki 4. senaryo MEB tablosunda var: 7 soru. Duyurudaki 2 konu bu senaryoda.')
  await expect(b.getByLabel('Doğrulandı')).toBeVisible()
  const dugme = b.getByRole('button', { name: 'Senaryonun 3 çıktısını göster' })
  await dugme.focus()
  await page.keyboard.press('Enter')
  await expect(b.getByRole('button', { name: 'Çıktıları gizle' })).toHaveAttribute('aria-expanded', 'true')
  await expect(b.locator('.meb-senaryo__liste li')).toHaveCount(3)
  await expect(b.locator('.meb-senaryo__liste li').nth(1)).toContainText('2 soru · T.O.7.5')
  await expect(b.locator('.meb-senaryo__liste .meb-senaryo__etiket')).toHaveCount(2)
  await expect(b.getByRole('link', { name: 'MEB tablosu (MEB, 10.09.2026)' })).toBeVisible()
  const axe = await new AxeBuilder({ page }).include('.meb-senaryo')
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa', 'best-practice']).analyze()
  expect(axe.violations).toEqual([])
  await page.addScriptTag({ path: ACE })
  const ihlal = await page.evaluate(async () => {
    // @ts-expect-error — `ace` is the injected engine's global
    const rapor = await new window.ace.Checker().check(document.querySelector('.meb-senaryo'), ['IBM_Accessibility'])
    return rapor.results.filter((s: { value: string[] }) => s.value[0] === 'VIOLATION' && s.value[1] === 'FAIL')
      .map((s: { ruleId: string }) => s.ruleId)
  })
  expect(ihlal).toEqual([])
})

test('kısmen', async ({ page }) => {
  await ac(page, { ...BLOK, durum: 'kismen', eslesen_konu_sayisi: 3, senaryo_disi_konular: ['Derin anlam'] })
  await expect(page.locator('.meb-senaryo')).toContainText('Şu konu 4. senaryoda yok: Derin anlam.')
  await expect(page.locator('.meb-senaryo').getByLabel('Uyarı')).toBeVisible()
})

test('senaryo yok', async ({ page }) => {
  await ac(page, { ...BLOK, durum: 'senaryo_yok', anilan: [9], senaryo: null, toplam: null, dagilim: [] })
  await expect(page.locator('.meb-senaryo')).toContainText('Duyuru 9. senaryo diyor; MEB tablosunda bu sınav için 1–6 var.')
  await expect(page.locator('.meb-senaryo').getByRole('button', { name: /çıktısını göster/ })).toHaveCount(0)
})

test('ülke geneli', async ({ page }) => {
  await ac(page, { ...BLOK, durum: 'ulke_geneli', anilan: [], senaryo: null, dagilim: [], senaryo_sayisi: 0, not: 'Ülke Geneli' })
  await expect(page.locator('.meb-senaryo')).toContainText('Bu sınav ülke genelinde ortak yapılır; senaryo yok.')
})

test('belirtilmedi: tahmin etiketli', async ({ page }) => {
  await ac(page, { ...BLOK, durum: 'belirtilmedi', anilan: [], senaryo: null, toplam: null, dagilim: [], adaylar: [3, 4] })
  const b = page.locator('.meb-senaryo')
  await expect(b).toContainText('Duyuruda senaryo belirtilmedi · MEB tablosunda 6 senaryo var.')
  await expect(b).toContainText('Duyurudaki konular 3. ve 4. senaryolarla uyumlu (TEDY’nin tahmini).')
})

test('telefonda asistana sor Asistan sayfasına götürür', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await ac(page, BLOK)
  const dugme = page.locator('.meb-senaryo').getByRole('button', { name: 'Örnek sınav için asistana sor' })
  expect((await dugme.boundingBox())!.height).toBeGreaterThanOrEqual(44)
  await dugme.click()
  await expect(page).toHaveURL(/\/asistan\?sayfa=sinavlar/)
})

test('blok yoksa bölüm yok', async ({ page }) => {
  const veri = sinav({})
  await mock(page, { ...LIVE, exams: { ...veri.exams, exams: [{ ...veri.exams.exams[0], senaryo: null }] } })
  await page.goto('/sinavlar')
  await page.getByRole('button', { name: 'Detaylar' }).first().click()
  await expect(page.locator('.exam-card__details')).toContainText('Konular')
  await expect(page.locator('.meb-senaryo')).toHaveCount(0)
})
```

- [ ] **Step 6: Kırmızıyı gör**

Run: `cd dashboard && IBM_TELEMETRY_DISABLED=true npm run build && TEDY_E2E_PORT=8298 TEDY_E2E_PYTHON=/mnt/thunderbolt/workspaces/TED/.venv/bin/python env -u ANTHROPIC_API_KEY npx playwright test tests/e2e/sinav-senaryo.spec.ts --project=`
Expected: FAIL — `.meb-senaryo` bulunamıyor ("blok yoksa bölüm yok" testi geçebilir; geri kalanlar zaman aşımıyla düşer).

- [ ] **Step 7: Kartı yaz** — `dashboard/src/components/SinavKarti.tsx`:

İçe aktarmaları güncelle:

```tsx
import { useId, useState, type MouseEvent, type ReactNode } from 'react'
import { Button, ContainedList, ContainedListItem, Link as CarbonLink, Tag } from '@carbon/react'
import { CheckmarkFilled, WarningAltFilled } from '@carbon/icons-react'
import { asistanaSor } from '../asistan/sayfaBaglami'
import { senaryoGorunumu } from '../utils/sinavSenaryosu'
```

(`useNavigate` zaten içe aktarılıyor; `MouseEvent, ReactNode` tip içe aktarması bu satıra taşınır.)

Dosyaya `SinavAyrintisi`'den önce ekle:

```tsx
/** MEB konu-soru dağılımı (spec 2026-10-19 §5): senaryo doğrulaması ya da tahmini; durum ikon + metin. */
function MebSenaryoBolumu({ exam }: { exam: ExamItem }) {
  const [acik, setAcik] = useState(false)
  const listeId = useId()
  const gezin = useNavigate()
  if (!exam.senaryo) return null
  const g = senaryoGorunumu(exam.senaryo)
  const sor = () => {
    const karsilandi = asistanaSor({ tur: 'sinav', id: exam.id, etiket: `${exam.course} — ${exam.title}` })
    if (!karsilandi) gezin('/asistan?sayfa=sinavlar')
  }
  return (
    <div className="exam-card__section meb-senaryo">
      <div className="exam-card__section-title">MEB konu-soru dağılımı</div>
      {g.cumleler.map((c, i) => (
        <p key={i} className="meb-senaryo__cumle">
          {i === 0 && g.ikon === 'onay' && <CheckmarkFilled size={16} aria-label="Doğrulandı" className="meb-senaryo__ikon" />}
          {i === 0 && g.ikon === 'uyari' && <WarningAltFilled size={16} aria-label="Uyarı" className="meb-senaryo__ikon" />}
          {c}
        </p>
      ))}
      {g.dugme && (
        <>
          <Button kind="ghost" size="sm" aria-expanded={acik} aria-controls={listeId} onClick={() => setAcik(!acik)}>
            {acik ? 'Çıktıları gizle' : g.dugme}
          </Button>
          {acik && (
            <ul id={listeId} className="meb-senaryo__liste">
              {g.satirlar.map(s => (
                <li key={s.metin}>
                  <span>{s.metin}</span>
                  {s.duyuruda && <Tag type="gray" size="sm" className="meb-senaryo__etiket">duyuruda</Tag>}
                </li>
              ))}
            </ul>
          )}
        </>
      )}
      <p className="meb-senaryo__alt">
        <CarbonLink href={exam.senaryo.kaynak} target="_blank" rel="noreferrer" size="sm">MEB tablosu ({g.kaynak})</CarbonLink>
      </p>
      <Button kind="ghost" size="sm" onClick={sor}>Örnek sınav için asistana sor</Button>
    </div>
  )
}
```

`SinavAyrintisi` içinde erken dönüş koşuluna ve gövdeye bölümü ekle:

```tsx
  if (konular.length === 0 && kaynaklar.length === 0 && !exam.tarihBelirsiz && !exam.senaryo) return null
```

ve "Konular" bölümünün kapanışından hemen sonra, "Kaynaklar" bölümünden önce:

```tsx
      <MebSenaryoBolumu exam={exam} />
```

`dashboard/src/components/ExamTimeline.tsx` `hasDetails` koşuluna:

```tsx
    || (exam.kaynaklar?.length ?? 0) > 0 || !!exam.tarihBelirsiz || !!exam.senaryo
```

`dashboard/src/components/SinavKarti.scss` sonuna:

```scss
.meb-senaryo {
  &__cumle {
    @include type.type-style('body-compact-01');
    display: flex;
    gap: spacing.$spacing-03;
    align-items: flex-start;
    margin: 0 0 spacing.$spacing-03;
  }

  &__ikon {
    flex: none;
    margin-block-start: spacing.$spacing-01;
    fill: var(--cds-icon-secondary);
  }

  &__liste {
    margin: spacing.$spacing-03 0;
    padding: 0;
    list-style: none;

    li {
      @include type.type-style('body-compact-01');
      display: flex;
      flex-wrap: wrap;
      gap: spacing.$spacing-03;
      align-items: center;
    }

    li + li {
      margin-block-start: spacing.$spacing-03;
    }
  }

  &__alt {
    @include type.type-style('helper-text-01');
    margin: spacing.$spacing-03 0;
    color: var(--cds-text-secondary);
  }

  @media (max-width: 671px) {
    .cds--btn {
      min-block-size: 3rem;
    }
  }
}
```

- [ ] **Step 8: Yeşili gör, lint, derleme, komşu e2e**

```bash
cd dashboard
npm run lint
IBM_TELEMETRY_DISABLED=true npm run build
npm run test:birim
TEDY_E2E_PORT=8298 TEDY_E2E_PYTHON=/mnt/thunderbolt/workspaces/TED/.venv/bin/python env -u ANTHROPIC_API_KEY npx playwright test tests/e2e/sinav-senaryo.spec.ts tests/e2e/sinav-uyari.spec.ts tests/e2e/gorsel-regresyon.spec.ts tests/e2e/aria-yapisi.spec.ts --project=
```
Expected: lint temiz; derleme tamam; birim testleri yeşil; e2e hepsi geçer (görsel ve aria tabanları değişmemeli — değişirse DUR ve nedenini rapora yaz).

- [ ] **Step 9: Commit**

```bash
git add dashboard/src/types.ts dashboard/src/utils/sinavSenaryosu.ts dashboard/tests/sinavSenaryosu.test.ts \
        dashboard/src/components/SinavKarti.tsx dashboard/src/components/SinavKarti.scss \
        dashboard/src/components/ExamTimeline.tsx dashboard/tests/e2e/sinav-senaryo.spec.ts
git commit -m "feat(pano): sınav kartında MEB konu-soru dağılımı bölümü

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Asistan — `sinav_senaryosu` aracı ve örnek sınav kuralı

**Files:**
- Modify: `src/assistant_tools.py` (bildirim, çalıştırma, `McpRegistry.__init__`, `build_registry`, `arac_ozeti` gerekmez)
- Modify: `src/assistant_core.py` (`AssistantRuntime.__init__` ve `build_registry` çağrısı; `SYSTEM_PROMPT` yönlendirme + "## Örnek sınav")
- Modify: `src/dashboard_api.py` (`AssistantRuntime(...)` çağrısına `senaryo_tablosu=`)
- Modify: `src/assistant_skills/{turkce,fen,sosyal,matematik}/SKILL.md` ("Araç kullanımı" maddesi)
- Modify: `dashboard/src/asistan/olayEslemesi.ts` (`ARAC_ETIKETI`), `dashboard/src/types.ts` (`CitationKind`), `dashboard/src/components/SourcePanel.tsx` (grup)
- Modify: `tests/test_assistant_core.py` (yerel araç listesi 30 → 31), `tests/test_assistant_skills_icerik.py` (`GERCEK_ARACLAR`)
- Test: `tests/test_assistant_sinav_senaryosu.py`

**Interfaces:**
- Consumes: Görev 3 `arac_metni`, `tablo_oku`; Görev 5 `SENARYO_TOOL`; `ogrenci_kaynaklari[SINAV_TOOL]`.
- Produces: araç `sinav_senaryosu(ders: str, sinav_no?: int, senaryo?: int)`; atıf türü `meb-tablo`; `McpRegistry(..., senaryo_tablosu: Callable[[], dict | None] | None = None)`; `build_registry(..., senaryo_tablosu=...)`; `AssistantRuntime(..., senaryo_tablosu=...)`.

- [ ] **Step 1: Başarısız testleri yaz** — `tests/test_assistant_sinav_senaryosu.py`:

```python
"""Asistanın MEB senaryo aracı (spec 2026-10-19 §6)."""
from src import sinav_senaryo
from src.assistant_core import AssistantRuntime
from src.assistant_tools import SENARYO_TOOL, build_registry

TABLO = sinav_senaryo.tablo_oku()


def _kayit(sinavlar=(), tablo=TABLO):
    return build_registry(lambda q, k: [], sinav_kaynagi=lambda: list(sinavlar), senaryo_tablosu=lambda: tablo)


def _adlar(reg, **kw):
    return {d["name"] for d in reg.declarations(**kw)}


def test_genel_ve_ogretmen_modunda_bildirilir():
    reg = _kayit()
    assert SENARYO_TOOL in _adlar(reg)
    assert SENARYO_TOOL in _adlar(reg, ogretmen="turkce")


def test_tablo_yoksa_arac_bildirilmez():
    assert SENARYO_TOOL not in _adlar(_kayit(tablo=None))
    assert SENARYO_TOOL not in _adlar(build_registry(lambda q, k: [], senaryo_tablosu=lambda: TABLO))  # sinavlar yok


def test_arac_kontrol_listesi_ve_atif():
    sonuc = _kayit().dispatch(SENARYO_TOOL, {"ders": "Türkçe", "sinav_no": 1, "senaryo": 4})
    assert sonuc.ok
    assert "T.O.7.5 → 2 soru" in sonuc.text and "Toplam 7 soru" in sonuc.text
    assert sonuc.citations[0]["kind"] == "meb-tablo"
    assert sonuc.citations[0]["label"] == "MEB konu-soru dağılım tablosu · Türkçe 7 · 1. yazılı"


def test_gecersiz_girdi_modele_hata_olarak_doner():
    sonuc = _kayit().dispatch(SENARYO_TOOL, {"ders": "Fen Bilimleri"})
    assert not sonuc.ok and "sinav_no" in sonuc.error


def test_istem_ornek_sinav_kurali():
    p = AssistantRuntime.SYSTEM_PROMPT
    assert "## Örnek sınav" in p
    bolum = p.split("## Örnek sınav", 1)[1]
    for parca in ("`sinav_senaryosu`", "cevap anahtarını", "`alistirma_olustur`", "`netlestir`", "MEB senaryosu ayrıca"):
        assert parca in bolum, parca
```

- [ ] **Step 2: Kırmızıyı gör**

Run: `env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest -q tests/test_assistant_sinav_senaryosu.py`
Expected: FAIL — `build_registry() got an unexpected keyword argument 'senaryo_tablosu'`.

- [ ] **Step 3: Aracı yaz** — `src/assistant_tools.py`:

`_OGRENCI_BILDIRIMLERI` sözlüğünden sonra modül düzeyine:

```python
_SENARYO_BILDIRIMI = {
    "name": SENARYO_TOOL,
    "description": (
        "MEB'in 7. sınıf 1. dönem ortak yazılı konu-soru dağılım tablosu: bir dersin 1. ya da 2. "
        "yazılısında senaryoların hangi öğrenme çıktısından kaç soru içerdiği; yaklaşan sınav o derse "
        "aitse duyurunun andığı senaryonun doğrulaması. Örnek sınav, deneme ya da yazılıya hazırlık "
        "istendiğinde ÖNCE bu aracı çağır ve dönen dağılıma birebir uy."
    ),
    "parameters": {"type": "object", "properties": {
        "ders": {"type": "string", "description": "Ders adı (ör. 'Türkçe', 'Fen Bilimleri')."},
        "sinav_no": {"type": "integer", "description": "1 ya da 2 (okulun 1.1 sınavı 1, 1.2 sınavı 2)."},
        "senaryo": {"type": "integer", "description": "Senaryo numarası; verilmezse duyurununki ya da hepsi."}},
        "required": ["ders"]},
}
```

`McpRegistry.__init__` imzasına (`sinav_kaynagi` parametresinin yanına) `senaryo_tablosu: Callable[[], Any] | None = None` ekle ve gövdede `self.senaryo_tablosu = senaryo_tablosu` ata (yorum: "MEB scenario table (src/sinav_senaryo.tablo_oku); None or an unreadable table leaves sinav_senaryosu undeclared."). `build_registry` imzasına aynı parametreyi ekle ve `McpRegistry(...)` çağrısına `senaryo_tablosu=senaryo_tablosu` geçir (`sinav_kaynagi`'nin geçirildiği satırın yanına).

Yardımcı yöntem (`_dispatch_ogrenci`'den önce):

```python
    def _senaryo_tablosu(self) -> dict | None:
        if self.senaryo_tablosu is None or self.ogrenci_kaynaklari.get(SINAV_TOOL) is None:
            return None
        try:
            return self.senaryo_tablosu()
        except Exception as exc:  # noqa: BLE001 — an unreadable table is "no tool", never a crash
            logger.error("senaryo tablosu okunamadı: %s", type(exc).__name__)
            return None

    def _dispatch_senaryo(self, args: dict[str, Any]) -> ToolOutcome:
        tablo = self._senaryo_tablosu()
        if tablo is None:
            return ToolOutcome(ok=False, error="MEB senaryo tablosu okunamadı")
        try:
            sinavlar = self.ogrenci_kaynaklari[SINAV_TOOL]() or []
        except Exception as exc:  # noqa: BLE001 — the table alone still answers
            logger.error("%s source failed: %s", SINAV_TOOL, type(exc).__name__)
            sinavlar = []
        try:
            metin, etiket = sinav_senaryo.arac_metni(tablo, sinavlar, args)
        except ValueError as exc:
            return ToolOutcome(ok=False, error=str(exc))
        metin = _kirp(metin, GOVDE_SINIRI)
        return ToolOutcome(ok=True, text=metin, citations=[{
            "kind": "meb-tablo", "label": etiket,
            "locator": {"tool": SENARYO_TOOL, "args": dict(args)},
            "snippet": metin[:400], "confidence": 1.0}])
```

`declarations()` içinde öğrenci araçları döngüsünden hemen sonra:

```python
        if self._senaryo_tablosu() is not None:
            decls.append(copy.deepcopy(_SENARYO_BILDIRIMI))
```

`dispatch()` içinde `if self.ogrenci_kaynaklari.get(name) is not None:` satırından önce:

```python
        if name == SENARYO_TOOL and self._senaryo_tablosu() is not None:
            return self._dispatch_senaryo(args or {})
```

`_yerel_aciklama` değişmez (araç öğrenci verisi değil, tablo).

- [ ] **Step 4: Çalışma zamanına bağla**

`src/assistant_core.py` `AssistantRuntime.__init__` imzasına `senaryo_tablosu: Callable[[], Any] | None = None` ekle (`sinav_kaynagi` yanına) ve `build_registry(...)` çağrısına `senaryo_tablosu=senaryo_tablosu,` geçir.

`src/dashboard_api.py` `AssistantRuntime(...)` çağrısına (`sinav_kaynagi=_canli_sinavlar,` satırının altına):

```python
                senaryo_tablosu=sinav_senaryo.tablo_oku,
```

ve dosyanın içe aktarmalarına `from src import sinav_senaryo` (diğer `src` içe aktarmalarının yanına).

- [ ] **Step 5: İstem** — `src/assistant_core.py` `SYSTEM_PROMPT`:

"## Hangi araca ne zaman uzanırsın" bölümündeki `"Sınav tarihleri → \`sinavlar\`. "` metnini şöyle değiştir:

```python
        "Sınav tarihleri → `sinavlar`. MEB ortak yazılı konu-soru dağılımı, bir senaryonun hangi "
        "çıktıdan kaç soru içerdiği, örnek sınav ve deneme → `sinav_senaryosu`. "
```

Yeni bölüm, "## Uydurma yasağı" bölümünün **arkasına**, onu izleyen "## Yüklenen dosya" başlığının hemen önüne eklenir. Yer önemli: `test_system_prompt_routing_names_every_declared_tool_exactly_once` her araç adını yalnız "## Hangi araca ne zaman uzanırsın" ile "## Uydurma yasağı" arasında sayar; yeni bölüm o aralığa girerse `sinav_senaryosu`, `netlestir` ve `alistirma_olustur` iki kez sayılır.

```python
        "## Örnek sınav\n"
        "- 'örnek sınav', 'deneme', 'prova', 'yazılıya hazırla' denince önce `sinav_senaryosu`'nu çağır.\n"
        "- Yazılı kâğıdı: soru sayısı senaryonun toplamı; her çıktıdan aracın kontrol listesindeki kadar soru, "
        "ne eksik ne fazla. Her sorunun altına ölçtüğü çıktının kodunu ve kısa adını yaz. Biçim MEB ortak "
        "yazılısı gibi, çoğu açık uçlu; öğretmen modundaysan o dersin soru kalıplarını kullan. Kâğıtta "
        "cevap anahtarını yazma.\n"
        "- Kâğıdın sonunda iki öneri yaz: 'Cevapları göster' denince anahtarı ayrı bir mesajda ver; "
        "'Aynı konulardan hızlı alıştırma' denince aynı çıktılardan `alistirma_olustur` ile kart üret. "
        "Kâğıda yazılmış cevabın fotoğrafı gelirse değerlendirme aracını kullan.\n"
        "- Senaryo belli değilse: tek uyumlu aday varsa onu kullan ve söyle; 2–4 aday varsa "
        "`netlestir` ile sor; aday yoksa hangi senaryoyu istediğini sor, kendin seçme.\n"
        "- Duyurunun andığı senaryo tabloda yoksa ya da sınav ülke genelinde ortaksa bunu açıkça söyle; "
        "senaryo uydurma.\n"
        "- Senaryonun duyuruda geçmeyen çıktılarını öğretmenin sözü gibi değil, 'MEB senaryosu ayrıca "
        "şunları kapsıyor' diye sun.\n\n"
```

- [ ] **Step 6: Beceriler** — dört `src/assistant_skills/<id>/SKILL.md` dosyasında "## Araç kullanımı" bölümünün son maddesinden sonra:

```markdown
- Yazılı provası: Işık bir yazılıya örnek sınav ya da deneme isterse önce `sinav_senaryosu` ile MEB senaryosunun soru dağılımını al; kâğıdı o dağılımla ve bu dersin soru kalıplarıyla yaz (genel istemin "Örnek sınav" kuralı).
```

`tests/test_assistant_skills_icerik.py` `GERCEK_ARACLAR` kümesine `at.SENARYO_TOOL` ekle.

- [ ] **Step 7: Arayüz**

`dashboard/src/asistan/olayEslemesi.ts` `ARAC_ETIKETI`'ne (`sinavlar` girdisinin yanına):

```ts
  sinav_senaryosu: 'MEB senaryo tablosuna bakılıyor',
```

`dashboard/src/types.ts` `CitationKind` birliğine `| 'meb-tablo'` ekle. `dashboard/src/components/SourcePanel.tsx` `GROUP_ORDER` dizisinde `'ogrenci'`'den sonra `'meb-tablo'`, `GROUP_TITLE`'a `'meb-tablo': 'MEB tabloları',`.

`tests/test_assistant_core.py::test_system_prompt_routing_names_every_declared_tool_exactly_once`: `yerel_araclar` demetine `"sinav_senaryosu"` ekle, `assert len(tum_araclar) == 30` → `31`.

- [ ] **Step 8: Yeşili gör, komşu testler**

```bash
env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest -q \
  tests/test_assistant_sinav_senaryosu.py tests/test_assistant_core.py tests/test_asistan_adim_etiketleri.py \
  tests/test_assistant_skills_icerik.py tests/test_assistant_ogretmen_modu.py tests/test_sinav_senaryo_api.py
cd dashboard && npm run lint && npx tsc -b && npm run test:birim
```
Expected: hepsi yeşil (Görev 5'te kırmızı kalan adım etiketi testi dahil).

- [ ] **Step 9: Commit**

```bash
git add src/assistant_tools.py src/assistant_core.py src/dashboard_api.py \
        src/assistant_skills/turkce/SKILL.md src/assistant_skills/fen/SKILL.md \
        src/assistant_skills/sosyal/SKILL.md src/assistant_skills/matematik/SKILL.md \
        dashboard/src/asistan/olayEslemesi.ts dashboard/src/types.ts dashboard/src/components/SourcePanel.tsx \
        tests/test_assistant_sinav_senaryosu.py tests/test_assistant_core.py tests/test_assistant_skills_icerik.py
git commit -m "feat(asistan): sinav_senaryosu aracı ve örnek sınav kuralı

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Altın sorular, belgeler ve tam doğrulama

**Files:**
- Modify: `src/assistant_eval/sorular.json`, `tests/test_assistant_denetim.py` (ders başına "== 3" → ">= 3")
- Modify: `CLAUDE.md`
- Test: tam süitler

**Interfaces:**
- Consumes: Görev 1–7.
- Produces: —

- [ ] **Step 1: Altın sorular** — `src/assistant_eval/sorular.json`'da `turkce` listesinin sonuna:

```json
{"id": "turkce-4", "soru": "Türkçe 1. yazılı için 4. senaryoya uygun örnek sınav hazırla.", "arac": "sinav_senaryosu", "kaynak": "MEB konu-soru", "noktalar": ["T.O.7.5"]}
```

`fen` listesinin sonuna:

```json
{"id": "fen-4", "soru": "Fen Bilimleri 1. yazılı için örnek sınav hazırla.", "arac": "sinav_senaryosu", "kaynak": "MEB konu-soru", "noktalar": ["senaryo"]}
```

`tests/test_assistant_denetim.py` satır ~139: `assert len(sorular) == 3` → `assert len(sorular) >= 3`.

Run: `env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest -q tests/test_assistant_denetim.py` → Expected: PASS. (`--onayla` ile ücretli canlı koşu YAPILMAZ.)

- [ ] **Step 2: CLAUDE.md** — "Asistan değerlendirme ve sınava hazırlık (B4)" maddesinden sonra yeni madde:

```markdown
- **MEB konu-soru dağılım senaryoları (2026-10-19)** (spec `docs/superpowers/specs/2026-10-19-meb-sinav-senaryolari-design.md`): `src/sinav_senaryolari.json` 7. sınıf 1. dönem altı dersin ÖDSGM tablolarıdır (çıktı → senaryo başına soru sayısı; Türkçe 2. yazılı "ülke geneli", senaryosuz); `scripts/odsgm_senaryo_tablolari.py` üretir, elle düzenlenmez. Bu makine `meb.gov.tr`/`meb.ai`'ye TLS'te takılır (ölçüldü: HP, mbp, Pi; Türk Telekom), betik sayfaları Jina Reader'dan ham HTML olarak alır (`--dosya` ile tarayıcıdan kaydedilmiş HTML). Okulun "1.1"i = MEB "1. Dönem 1. Ortak Yazılı" (kullanıcı kararı). Tespit (`birlestir`) her ortak yazılı/yazılı/deneme kaydına `senaryo` bloğu yazar (`src/sinav_senaryo.py`): duyurudaki "4. senaryo" cümlesi sınavın kendi cümlesinden sonraki tarihe kadar aranır, konular çıktı kodu/metni/konu adıyla eşlenir; durumlar `dogrulandi`/`kismen`/`senaryo_yok`/`ulke_geneli`/`belirtilmedi` (uyumlu adaylar tahmin). Blok `icerik_surumu`'na girmez (bildirim yok). Kart: Sınavlar ayrıntısında "MEB konu-soru dağılımı". Asistan: `sinav_senaryosu(ders, sinav_no, senaryo)` kontrol listesi verir; istemin "## Örnek sınav" kuralı yazılı kâğıdı dağılıma birebir, cevap anahtarı ayrı adımda ister.
```

ve "`scripts/asistan_eval.py` 12 altın soruyu" ifadesini "14 altın soruyu" yap.

- [ ] **Step 3: Tam doğrulama**

```bash
unshare -rn env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest -q -p no:cacheprovider > /tmp/senaryo-pytest.log 2>&1; tail -3 /tmp/senaryo-pytest.log
cd dashboard && npm run lint && IBM_TELEMETRY_DISABLED=true npm run build && npm run test:birim
TEDY_E2E_PORT=8298 TEDY_E2E_PYTHON=/mnt/thunderbolt/workspaces/TED/.venv/bin/python env -u ANTHROPIC_API_KEY npx playwright test --project= --reporter=line > /tmp/senaryo-e2e.log 2>&1; tail -3 /tmp/senaryo-e2e.log
```
Expected: Python süiti kırmızısız; lint, derleme, birim yeşil; e2e kırmızısız. Kırmızı varsa adıyla rapora yaz.

- [ ] **Step 4: Kuru koşu (canlı veri, dosya yazmaz)** — kullanıcı onayı gerekmez çünkü önbellekli metinler için model çağrısı yok ya da bütçe tavanı içinde; yine de sonucu raporla:

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-senaryo
env -u ANTHROPIC_API_KEY /mnt/thunderbolt/workspaces/TED/.venv/bin/python -c "import pathlib, src.dashboard_api as api, src.sinav_tespiti as st; api.OUTPUT_DIR = '/mnt/thunderbolt/workspaces/TED/output'; st.PROJE_KOKU = pathlib.Path('/mnt/thunderbolt/workspaces/TED'); raise SystemExit(st.main(['--kuru', '--sure', '120']))" > /tmp/senaryo-kuru.txt 2>&1; grep -n "Senaryo:" /tmp/senaryo-kuru.txt
```
Expected: Türkçe "1.1 Ara Değerlendirme Sınavı" için `Senaryo: dogrulandi · Türkçe 1. yazılı · 4. senaryo · 7 soru`. Çıkış kodu 2 ise canlı senkron kilidi tutuyordur; bitince yeniden dene.

- [ ] **Step 5: Commit**

```bash
git add src/assistant_eval/sorular.json tests/test_assistant_denetim.py CLAUDE.md
git commit -m "docs(sinav): MEB senaryo entegrasyonu belgelendi, altın sorulara iki vaka

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
