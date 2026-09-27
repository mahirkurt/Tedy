# Pano Eksiklikleri — Birleşik Takvim, Sınav Listesi ve Sürümlü Figür Adresleri

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Panonun bilinen dört sorununu (birleşik takvimde ders yok, cumartesi özel dersleri yok, `relatedContent` hep boş, önceki yılın notları bu yılın geçmiş sınavı gibi) kapatmak ve asistanın ders kitabı figürü adreslerini müfredat korpusu sürümüne bağlamak.

**Architecture:** Hiçbir düzeltme yeni bir ayrıştırıcı yazmaz; asistanın canlı araçlarının zaten doğru okuduğu kodu (`assistant_tools.gunun_dersleri`, `_temiz_icerik`, `notlar_metni`'nin yıl denetimi) panonun rotaları da kullanır, böylece pano ile asistan aynı veriyi farklı okuyamaz. Figür adresi `?v=<corpus_version>` taşır; sürüm maarif `server_info`'dan süreç içinde süreli önbellekle okunur, uç nokta sürümü tutmayan isteğe Türkçe cümleli 404 döner ve LRU `(sürüm, id)` ile anahtarlanır.

**Tech Stack:** Python 3 / Flask (`src/dashboard_api.py`), `src/assistant_tools.py`, pytest; React 19 + TypeScript + Carbon + SCSS (`dashboard/`), Playwright.

**Spec:** Ayrı bir spec dosyası yok. Kullanıcının onayladığı tasarım aşağıdaki "Onaylı tasarım" bölümünde birebirdir; kapsam odur, fazlası eklenmez.

## Global Constraints

- **Çalışma ağacı ve dal:** yalnız `/mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-tam-baglam`, dal `fix/pano-eksiklikleri`. Her commit'ten önce `git -C /mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-tam-baglam branch --show-current` çıktısı `fix/pano-eksiklikleri` olmalı. Ana checkout `/mnt/thunderbolt/workspaces/TED` başka oturumlarla paylaşılır: oraya dokunma, orada komut koşma.
- **Staging:** dosyaları adıyla ekle (`git add <yol> <yol>`); `git add -A` / `git add .` yok. Çıplak `git stash` yok. `git push` yok.
- **Testler ücretli API'ye ya da ağa asla çıkmaz.** `tests/conftest.py` `ANTHROPIC_API_KEY`'i zaten siliyor. MCP sunucuları yalnız sahte istemcilerle (`_FakeClient`) temsil edilir. Pytest paketi `unshare -rn` altında da geçer; şüphede onunla koş.
- **Python testleri:** `.venv/bin/python -m pytest -q -p no:cacheprovider …` (çalışma ağacının `.venv`'i ana checkout'un `.venv`'ine bağlıdır).
- **Bu çalışma ağacında `.env` yok** (ölçüldü 2026-09-28): `src.dashboard_api` içe aktarılırken `DASHBOARD_SECRET_KEY` yoksa `RuntimeError` atar ve pytest toplama aşamasında düşer. Bu plandaki her pytest, Playwright ve `dashboard_api` içe aktaran Python komutu `DASHBOARD_SECRET_KEY=yerel-test-anahtari-pano-eksiklikleri` önekiyle yazılmıştır; öneki silme. `.env` oluşturma, ana checkout'un `.env`'ine symlink kurma: gerçek anahtarlar (Anthropic dahil) test sunucusuna girmemeli. Playwright'ın `webServer`'ı ortamı devralır.
- **Pano:** `cd dashboard && npm run lint && npm run build`, ardından ilgili Playwright spec'leri. Playwright `dashboard-dist/` paketini sunar, `src`'yi değil: her e2e koşusundan önce `npm run build` ve çıkış kodunu **boru olmadan** oku (`npm run build; echo "build çıkış: $?"`) — `tsc` hatası vite'ı durdurur ve bayat paket yeşil geçer. Başka oturumlarla çakışmamak için `TEDY_E2E_PORT=8296` kullan.
- **Görsel taban çizgisi yalnız fark okunduktan sonra yenilenir:** önce güncellemesiz koş, `test-results/` altındaki `*-actual.png` / `*-expected.png` / `*-diff.png` dosyalarını Read aracıyla aç, değişikliğin yalnız beklenen bölgede olduğunu yaz, sonra `--update-snapshots`.
- **Tüm test koşuları ön planda.** Arka plan kabuk işi yok; yavaş koşu için Bash `timeout` 600000 ms'ye kadar.
- **Carbon token kuralları (CLAUDE.md) her SCSS'e uygulanır:** boşluk/hareket/tip Carbon token'ı (`spacing.$spacing-NN`, `motion.$duration-*`, `@include type.type-style(...)`), el yazısı hex yok, renk aritmetiği yok (alfa, gradyan, `filter`, `color-mix` yok); her istisna gerekçeli `stylelint-disable-next-line`. `npm run lint` (ESLint + stylelint) temiz olmalı.
- **Fixture'larda kişisel veri yok:** biçim `output/scraped_data.json`'dan salt-okunur alınır, değerler uydurulur (öğretmen, öğrenci adı, not yok).
- **Dağıtım bu planın görevi değildir.** Sonda controller ayrı bir adım olarak yapar: main'i ff, push, `npm run build`, `systemctl --user restart ted-dashboard`.
- **Kod stili:** kullanıcıya dönük metin Türkçe, kod yorumları İngilizce ve çevredeki "measured …" gerekçeli üsluba uyar. Commit mesajları Türkçe, sonu: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- **Başlangıç kırmızıları:** Görev 1'in ilk adımı tam Python paketini bir kez koşar ve önceden kırmızı olan testleri not eder; hiçbir görev yeni kırmızı bırakmaz.

## Onaylı tasarım (kapsam)

1. **Birleşik takvim ders çizmiyor.** `_birlesik_takvim` karışık harfli gün adlarını büyük harfli noktasız başlıklarla ("PAZARTESI") eşliyor. Asistanın `ders_programi` aracının kullandığı gün-sütun çözücüsü (`utils/schedule.ts` `dayColumns`'un Python portu; iki blok, cuma kendi zili) yeniden kullanılır. Gerçek iki tablolu biçimle test edilir.
2. **Cumartesi özel dersleri yok.** `_birlesik_takvim`, `_private_lessons_for_week`'i `hafta_sonu=True` olmadan çağırıyor. Hafta sonu dahil edilir. Takvim bileşeni cumartesi/pazar çizmediği için ön yüz değişikliği, Playwright ve görsel taban çizgisi güncellemesi de bu plandadır.
3. **`/api/exams` `relatedContent` hep `[]`.** `_find_related_content` yalnız liste bekliyor; gerçek değer `{tab_id, text, tables, items, cards}`. Kart ve maddeler gerçek biçimden okunur.
4. **Önceki yılın notları bu yılın geçmiş sınavı gibi.** `_sinav_listesi`'nin sentetik geçmiş sınavlarına `notlar` aracının yıl denetimi uygulanır; önceki yılın sentetik sınavları listeden çıkar. Notlar sayfası raporu göstermeye devam eder.
5. **Figür adresleri korpus sürümünü taşır.** Atıf `/api/assistant/figure/<id>?v=<corpus_version>`; sürüm maarif `server_info`'dan, süreç içinde süreli önbellekle; `v` yoksa ya da güncel sürüm değilse 404 + "Bu görsel, müfredat korpusu güncellendiği için değişti; soruyu yeniden sorun."; süreç içi LRU `(sürüm, id)` anahtarlı; SourcePanel adresi `v` ile kurar; CLAUDE.md güncellenir.

## Karara bağlanan belirsizlikler

- **Notlar'daki "önceki yıl" etiketi yok.** Tasarım "mevcut 'önceki yıl' etiketiyle" diyor; planlama sırasında ölçüldü: `dashboard/src/components/GradeTable.tsx` yalnız `Notlar — {semester}` başlığını basıyor ("Notlar — 2025-2026 4. Arakarne"), ayrı bir önceki-yıl işareti yok. Yıl, dönem adının içinde görünür. Kapsam eklenmediği için bu plan Notlar'a etiket **eklemez**; CLAUDE.md bunu olduğu gibi yazar. Etiket isteniyorsa ayrı bir iş.
- **Hafta sonu sütunu uyarlanır.** Takvim cumartesi/pazar sütununu yalnız o haftada o gün bir olay varsa gösterir (efsanedeki "yalnız ekrandaki türler" kuralının aynısı, İ6); gizlenen bir tür sütununu kaybettirmez. Hafta sonu boş bir haftada ızgara bugünkü gibi beş sütundur; böylece mevcut "uzun başlık günü genişletmez" testi (beş başlık) değişmeden geçer.
- **`CitationChip.tsx` figür adresi kurmuyor.** Figür adresini yalnız `SourcePanel.tsx` (`FigureThumb`) kuruyor; `CitationChip` değişmez. Sürümü olmayan bir figür atfı (dağıtımdan önce açılmış bir sekme) adresi `v`'siz kurar; uç nokta 404 verir ve küçük resim "Görsel yüklenemedi" der (`<img>` hata gövdesini okuyamaz; tam cümle doğrudan API istemcisine gider).
- **Sürüm okunamazsa:** `v` yoksa her durumda 404 (sürümü bilmek gerekmez). `v` var ama güncel sürüm okunamıyorsa (maarif kapalı/yapılandırılmamış) cevap mevcut 502 "Ders kitabı görseline şu an ulaşılamadı…" olur; görsel zaten getirilemezdi. Başarısız okuma önbelleğe girmez. TTL 300 s.
- **Takvim sınavlarına not eşleme değişmez.** Tasarım yalnız sentetik sınavları çıkarıyor. Eski yılın raporu açıkken bir takvim sınavı (`N. Sınav`) yine o raporun sütunundan not alabilir; bu plan dokunmaz, controller'a ayrıca bildirildi.
- **Hafta seçimi değişmez.** `_birlesik_takvim` `weeks[-1]` okumaya devam eder (`/api/schedule` `is_current`'i tercih eder); canlı veride tek hafta var ve tablo haftadan haftaya aynı. Kapsam dışı.
- **Bugün'ün `/api/calendar`'ı** (`_private_lessons_for_day`, beş günlük hafta) cumartesi özel dersini yine göstermez; tasarım yalnız birleşik takvimi kapsıyor, dokunulmaz.

## Dosya haritası

| Dosya | Sorumluluk | Görev |
|---|---|---|
| `src/assistant_tools.py` | `gunun_dersleri` alt satırı; `rapor_yili` / `onceki_yil_raporu_mu`; `McpRegistry.korpus_surumu`, figür atfında `corpus_version` | 1, 5, 6 |
| `src/dashboard_api.py` | `_birlesik_takvim` dersleri + hafta sonu; `_current_week_dates` 7 gün; `_find_related_content`; `_guncel_ogretim_yili`, `_sinav_listesi` yıl denetimi; figür ucu `v` denetimi ve `(sürüm, id)` LRU | 1, 2, 4, 5, 6 |
| `dashboard/src/components/CalendarEvents.tsx` | uyarlanan hafta sonu sütunları | 3 |
| `dashboard/src/theme/ted-theme.scss` | ızgara sütun sayısı değişkeni | 3 |
| `dashboard/src/components/SourcePanel.tsx`, `dashboard/src/types.ts` | figür adresi `?v=` | 7 |
| `tests/test_pano_eksiklikleri.py` (yeni) | Görev 1, 2, 5 birim/rota testleri | 1, 2, 5 |
| `tests/test_exams.py` | gerçek biçimli `relatedContent`, yıl denetimli sentetik sınav | 4, 5 |
| `tests/test_assistant_ogrenci_araclari.py` | cumartesi beklentisinin tersine dönmesi | 2 |
| `tests/test_assistant_gorseller.py` | sürüm, 404 cümlesi, `(sürüm, id)` LRU | 6 |
| `dashboard/tests/e2e/takvim.spec.ts`, `_gorsel-fixtures.ts`, `gorsel-regresyon.spec.ts-snapshots/takvim-*.png`, `aria-yapisi.spec.ts-snapshots/takvim.aria.yml` | hafta sonu e2e ve taban çizgileri | 3 |
| `dashboard/tests/e2e/asistan-gorsel-kaynak.spec.ts` | `?v=` adresleri | 7 |
| `CLAUDE.md` | bilinen sorunlar maddesinin kaldırılması; figür kimliği uyarısının yeni davranışla değişmesi | 5, 7 |

---

### Görev 1: Birleşik takvim dersleri asistanın gün-sütun çözücüsüyle okur

**Files:**
- Modify: `src/assistant_tools.py:520-547` (`gunun_dersleri`: `alt` alanı)
- Modify: `src/dashboard_api.py:2339-2352` (`_parse_time_range` silinir), `src/dashboard_api.py:2370-2430` (`_birlesik_takvim` bölüm 1)
- Create: `tests/test_pano_eksiklikleri.py`

**Interfaces:**
- Consumes: `assistant_tools.gunun_dersleri(rows, gun) -> list[dict]` (anahtarlar `ders_no:int`, `baslangic:"HH:MM"`, `bitis:"HH:MM"`, `ders:str`), `dashboard_api.DAY_NAMES: dict[int, str]` (0 → "Pazartesi" … 6 → "Pazar"), `tests.test_assistant_ogrenci_araclari.HAFTA` (gerçek iki bloklu biçim, uydurma değerler).
- Produces: `gunun_dersleri` her derse `alt: str` ekler (hücrenin ikinci satırı, yoksa `""`). `tests/test_pano_eksiklikleri.py` içinde `api` fixture'ı ve `_haftayi_sabitle(api, monkeypatch) -> list[date]` yardımcısı (Pazartesi 21.09.2026'dan başlayan 7 gün); Görev 2 ve 5 bunları kullanır.

- [ ] **Step 1: Başlangıç kırmızılarını kaydet**

Run: `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-tam-baglam && DASHBOARD_SECRET_KEY=yerel-test-anahtari-pano-eksiklikleri .venv/bin/python -m pytest -q -p no:cacheprovider 2>&1 | tail -15`
Expected: özet satırı (~6 dakika). Planlamada aynı komut ölçüldü: `2460 passed, 69 skipped`, kırmızı yok. Farklıysa kırmızı test adlarını görev raporuna yaz; bunlar "önceden kırmızı" sayılır.

- [ ] **Step 2: Başarısız testi yaz**

`tests/test_pano_eksiklikleri.py`:

```python
"""Panonun bilinen dört sorunu (plan docs/superpowers/plans/2026-09-28-pano-eksiklikleri.md).

The assistant's live tools already read the portal's real shapes; the
dashboard's own routes did not. Every fixture here has the real shape of
output/scraped_data.json and invented values — no real names or grades.
"""
import json
import os
import sys
from datetime import date, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["TEST_AUTH_BYPASS"] = "1"

from src import assistant_tools as at  # noqa: E402
# The portal's weekly grid in its real shape: headers empty, upper-case
# dotless day names in rows[0], Mon–Thu and Fri–Sun as two blocks, each with
# its own time column (Friday's later bell). Invented lessons and teachers.
from tests.test_assistant_ogrenci_araclari import HAFTA, SATIRLAR  # noqa: E402

PAZARTESI = date(2026, 9, 21)


def _kopya(x):
    return json.loads(json.dumps(x))


@pytest.fixture
def api(monkeypatch):
    import src.dashboard_api as api
    monkeypatch.setattr(api, "_load_photo_homework_rows", lambda: [])
    monkeypatch.setattr(api, "_load_private_lessons", lambda: [])
    api.app.config["TESTING"] = True
    return api


def _haftayi_sabitle(api, monkeypatch):
    """Pin the unified calendar's week to Mon 21.09.2026 – Sun 27.09.2026."""
    gunler = [PAZARTESI + timedelta(days=i) for i in range(7)]
    monkeypatch.setattr(api, "_current_week_dates", lambda: gunler)
    return gunler


def _birlesik(api):
    with api.app.test_client() as c:
        return c.get("/api/calendar/unified").get_json()["events"]


# ── 1. Lessons: the real two-block grid ──────────────────────────────────────

def test_birlesik_takvim_gercek_iki_bloklu_tablodan_ders_cizer(api, monkeypatch):
    _haftayi_sabitle(api, monkeypatch)
    monkeypatch.setattr(api, "_scraped", lambda: {"ders_programi": [_kopya(HAFTA)]})
    dersler = [e for e in _birlesik(api) if e["type"] == "lesson"]
    # Before: "Pazartesi" in "PAZARTESI" never matched — zero lessons, always.
    assert dersler
    cuma = [(e["start"], e["end"], e["title"]) for e in dersler if e["start"].startswith("2026-09-25")]
    # Friday reads its own block's bell (09:00, not Monday's 08:55).
    assert cuma == [
        ("2026-09-25T08:00:00", "2026-09-25T08:40:00", "Sosyal Bilgiler"),
        ("2026-09-25T09:00:00", "2026-09-25T09:40:00", "Fen Bilimleri"),
        ("2026-09-25T09:50:00", "2026-09-25T10:30:00", "Matematik"),
    ]
    pazartesi = sorted((e["start"], e["title"], e["subtitle"]) for e in dersler
                       if e["start"].startswith("2026-09-21"))
    assert pazartesi[0] == ("2026-09-21T08:00:00", "Türkçe", "Deneme Öğretmen")
    assert pazartesi[1][:2] == ("2026-09-21T08:55:00", "Fransızca")      # normalised name
    assert not any(e["title"] in ("Kahvaltı", "Öğle yemeği", "Çıkış") for e in dersler)
    assert all(e["courseFamily"] for e in dersler)                        # coloured by course


def test_birlesik_takvim_ders_programi_araciyla_ayni_dersleri_verir(api, monkeypatch):
    gunler = _haftayi_sabitle(api, monkeypatch)
    monkeypatch.setattr(api, "_scraped", lambda: {"ders_programi": [_kopya(HAFTA)]})
    dersler = [e for e in _birlesik(api) if e["type"] == "lesson"]
    for i, gun in enumerate(("Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma")):
        tarih = gunler[i].isoformat()
        rota = sorted((e["start"][11:16], e["title"]) for e in dersler if e["start"].startswith(tarih))
        arac = sorted((d["baslangic"], d["ders"]) for d in at.gunun_dersleri(SATIRLAR, gun))
        assert rota == arac, gun


def test_programsiz_birlesik_takvim_ders_uydurmaz(api, monkeypatch):
    _haftayi_sabitle(api, monkeypatch)
    monkeypatch.setattr(api, "_scraped", lambda: {"ders_programi": []})
    assert not [e for e in _birlesik(api) if e["type"] == "lesson"]
```

- [ ] **Step 3: Testin başarısız olduğunu gör**

Run: `DASHBOARD_SECRET_KEY=yerel-test-anahtari-pano-eksiklikleri .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pano_eksiklikleri.py`
Expected: `test_birlesik_takvim_gercek_iki_bloklu_tablodan_ders_cizer` ve `test_birlesik_takvim_ders_programi_araciyla_ayni_dersleri_verir` FAIL (`assert dersler` boş liste / Pazartesi rota `[]`); `test_programsiz_…` PASS.

- [ ] **Step 4: `gunun_dersleri`'ne ikinci satırı ekle**

`src/assistant_tools.py`, `gunun_dersleri` içindeki `dersler.append({...})` bloğunu şununla değiştir:

```python
        satirlar = icerik.split("\n")
        dersler.append({
            "ders_no": int(no.group(1)),
            "baslangic": f"{saat.group(1)}:{saat.group(2)}",
            "bitis": f"{saat.group(3)}:{saat.group(4)}",
            "ders": normalize_course(satirlar[0].strip()),
            # The cell's second line (the teacher, in the portal's grid). The
            # unified calendar shows it as the lesson's subtitle; the
            # ders_programi text never prints it.
            "alt": satirlar[1].strip() if len(satirlar) > 1 else "",
        })
```

- [ ] **Step 5: `_birlesik_takvim`'in ders bölümünü değiştir**

`src/dashboard_api.py`, `_birlesik_takvim` içinde `# 1. Lessons from ders_programi` yorumundan `# 2. Homework deadlines` yorumuna kadar olan bloğun tamamını şununla değiştir:

```python
    # 1. Lessons from ders_programi, read through the assistant's port of
    # utils/schedule.ts dayColumns (assistant_tools.gunun_dersleri): the header
    # row is upper-case dotless Turkish ("PAZARTESI") and holds two blocks,
    # Friday on its own bell. Matching "Pazartesi" against it never succeeded,
    # so until 2026-09-28 this drew no lesson at all.
    from src.assistant_tools import gunun_dersleri
    weeks = data.get("ders_programi", [])
    if weeks:
        latest = weeks[-1]
        rows = latest.get("schedule", {}).get("rows", [])
        for day_idx, day_date in enumerate(week_dates):
            for ders in gunun_dersleri(rows, DAY_NAMES[day_idx]):
                sh, sm = (int(x) for x in ders["baslangic"].split(":"))
                eh, em = (int(x) for x in ders["bitis"].split(":"))
                lesson_name = ders["ders"]
                start_dt = datetime(day_date.year, day_date.month, day_date.day, sh, sm)
                end_dt = datetime(day_date.year, day_date.month, day_date.day, eh, em)
                events.append({
                    "id": _make_id("lesson", day_idx, sh, sm, lesson_name),
                    "title": lesson_name,
                    "type": "lesson",
                    "start": start_dt.isoformat(),
                    "end": end_dt.isoformat(),
                    **_takvim_rengi(lesson_name),
                    "course": lesson_name,
                    "subtitle": ders["alt"],
                })

```

Sonra artık kimsenin çağırmadığı `_parse_time_range` fonksiyonunu (docstring'iyle birlikte, `def _parse_time_range(cell_text):` … `return None`) sil. Doğrula: `grep -n "_parse_time_range" src/*.py tests/*.py` boş dönmeli.

- [ ] **Step 6: Testlerin geçtiğini gör**

Run: `DASHBOARD_SECRET_KEY=yerel-test-anahtari-pano-eksiklikleri .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pano_eksiklikleri.py tests/test_assistant_ogrenci_araclari.py tests/test_pano_tasarim_sistemi.py`
Expected: hepsi PASS.

- [ ] **Step 7: Tam paket**

Run: `DASHBOARD_SECRET_KEY=yerel-test-anahtari-pano-eksiklikleri .venv/bin/python -m pytest -q -p no:cacheprovider 2>&1 | tail -15`
Expected: Step 1'deki önceden kırmızılar dışında kırmızı yok.

- [ ] **Step 8: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-tam-baglam
git branch --show-current   # fix/pano-eksiklikleri olmalı
git add src/assistant_tools.py src/dashboard_api.py tests/test_pano_eksiklikleri.py
git commit -m "$(cat <<'EOF'
Birleşik takvim dersleri asistanın gün-sütun çözücüsüyle okusun

_birlesik_takvim "Pazartesi"yi "PAZARTESI" başlığında aradığı için hiç ders
çizmiyordu. Artık ders_programi aracının kullandığı gunun_dersleri'ni (iki
blok, cuma kendi zili) kullanıyor; kullanılmayan _parse_time_range silindi.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Görev 2: Birleşik takvim hafta sonu özel derslerini verir (arka uç)

**Files:**
- Modify: `src/dashboard_api.py:585-590` (`_private_lessons_for_week` docstring), `src/dashboard_api.py:2339-2343` (`_current_week_dates`), `_birlesik_takvim`'in `# 3. Private lessons` bölümü
- Modify: `tests/test_assistant_ogrenci_araclari.py:340-345`
- Test: `tests/test_pano_eksiklikleri.py`

**Interfaces:**
- Consumes: Görev 1'in `api` fixture'ı ve `_haftayi_sabitle`; `_private_lessons_for_week(week_dates, hafta_sonu=False)`.
- Produces: `_current_week_dates() -> list[date]` artık 7 gün (Pazartesi–Pazar). `/api/calendar/unified` bu haftanın cumartesi/pazar özel derslerini `type: "private_lesson"` olarak döner. Görev 3'ün ön yüzü bu olayları çizer.

- [ ] **Step 1: Başarısız testi yaz**

`tests/test_pano_eksiklikleri.py` sonuna ekle:

```python
# ── 2. Private lessons: the weekend is part of the week ──────────────────────

def _ozel_ders(**kw):
    ders = {"id": "pl1", "course": "Matematik", "teacher": "Deneme Hoca", "is_recurring": True,
            "weekday": "Pazartesi", "date": "", "start_time": "17:00", "end_time": "18:00",
            "active": True}
    ders.update(kw)
    return ders


def test_birlesik_takvim_cumartesi_ve_pazar_ozel_derslerini_verir(api, monkeypatch):
    _haftayi_sabitle(api, monkeypatch)
    monkeypatch.setattr(api, "_scraped", lambda: {})
    monkeypatch.setattr(api, "_load_private_lessons", lambda: [
        _ozel_ders(),
        # Measured 2026-09-25: both of Işık's real private lessons are on Saturday.
        _ozel_ders(id="pl2", course="Fen Bilimleri", weekday="Cumartesi",
                   start_time="12:00", end_time="13:00"),
        _ozel_ders(id="pl3", course="Türkçe", is_recurring=False, weekday="",
                   date="2026-09-27", start_time="10:00", end_time="11:00"),
        # A one-off lesson next Monday is outside this week.
        _ozel_ders(id="pl4", course="İngilizce", is_recurring=False, weekday="",
                   date="2026-09-28", start_time="10:00", end_time="11:00"),
    ])
    ozel = sorted((e["start"], e["course"]) for e in _birlesik(api) if e["type"] == "private_lesson")
    assert ozel == [
        ("2026-09-21T17:00:00", "Matematik"),
        ("2026-09-26T12:00:00", "Fen Bilimleri"),
        ("2026-09-27T10:00:00", "Türkçe"),
    ]


def test_bu_haftanin_tarihleri_pazartesiden_pazara(api):
    gunler = api._current_week_dates()
    assert len(gunler) == 7
    assert gunler[0].weekday() == 0 and gunler[-1].weekday() == 6
    assert all((b - a).days == 1 for a, b in zip(gunler, gunler[1:]))
```

- [ ] **Step 2: Testin başarısız olduğunu gör**

Run: `DASHBOARD_SECRET_KEY=yerel-test-anahtari-pano-eksiklikleri .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pano_eksiklikleri.py -k "hafta_sonu or cumartesi or pazartesiden"`
Expected: `test_birlesik_takvim_cumartesi_ve_pazar_ozel_derslerini_verir` FAIL (yalnız Matematik döner), `test_bu_haftanin_tarihleri_pazartesiden_pazara` FAIL (`len == 5`).

- [ ] **Step 3: Uygula**

`src/dashboard_api.py`:

`_current_week_dates` tamamen şu olur:

```python
def _current_week_dates():
    """The seven dates (Mon–Sun) of the current week. Seven, not five: both
    of Işık's private lessons are on Saturday (measured 2026-09-25), and a
    Mon–Fri week dropped them from the unified calendar."""
    today = datetime.now().date()
    monday = today - timedelta(days=today.weekday())
    return [monday + timedelta(days=i) for i in range(7)]
```

`_birlesik_takvim` içindeki bölüm 3:

```python
    # 3. Private lessons, weekend included (CalendarEvents draws a Saturday or
    # Sunday column in a week that has something on it).
    for pev in _private_lessons_for_week(week_dates, hafta_sonu=True):
        pev.update(_takvim_rengi(pev.get("course", "")))
        events.append(pev)
```

`_private_lessons_for_week` docstring'i:

```python
    """Expand private lesson configs into concrete events for one week.

    `hafta_sonu=True` (with seven `week_dates`) keeps Saturday and Sunday —
    the unified calendar and the assistant's takvim both pass it: measured
    2026-09-25, both of Işık's private lessons are on Saturday. Without it
    only Monday to Friday is expanded (`_private_lessons_for_day`)."""
```

- [ ] **Step 4: Tersine dönen mevcut beklentiyi güncelle**

`tests/test_assistant_ogrenci_araclari.py`, `test_canli_takvim_birlesik_rotanin_etkinliklerini_aciklamayla_verir` içindeki şu iki satırı:

```python
    # Measured 2026-09-25: both real private lessons are on Saturday, which
    # the Mon–Fri week grid never draws; the assistant must still see them.
    assert not any(e.get("course") == "Fen Bilimleri" for e in rota if e["type"] == "private_lesson")
```

şununla değiştir:

```python
    # Measured 2026-09-25: both real private lessons are on Saturday. Since
    # 2026-09-28 the route's week runs to Sunday, so both lists carry it.
    assert any(e.get("course") == "Fen Bilimleri" for e in rota if e["type"] == "private_lesson")
```

(Bir sonraki satır — `canli` için aynı `assert any(...)` — değişmez.)

- [ ] **Step 5: Testlerin geçtiğini gör**

Run: `DASHBOARD_SECRET_KEY=yerel-test-anahtari-pano-eksiklikleri .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pano_eksiklikleri.py tests/test_assistant_ogrenci_araclari.py tests/test_dashboard_api.py tests/test_cross_system_consistency.py`
Expected: hepsi PASS.

- [ ] **Step 6: Tam paket**

Run: `DASHBOARD_SECRET_KEY=yerel-test-anahtari-pano-eksiklikleri .venv/bin/python -m pytest -q -p no:cacheprovider 2>&1 | tail -15`
Expected: önceden kırmızılar dışında kırmızı yok.

- [ ] **Step 7: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-tam-baglam
git branch --show-current   # fix/pano-eksiklikleri
git add src/dashboard_api.py tests/test_pano_eksiklikleri.py tests/test_assistant_ogrenci_araclari.py
git commit -m "$(cat <<'EOF'
Birleşik takvim haftayı pazara kadar okusun, cumartesi özel dersleri görünsün

_current_week_dates yedi gün döner; özel dersler hafta_sonu=True ile açılır.
Işık'ın iki özel dersi de cumartesi olduğu için rota ikisini de hiç
göstermiyordu.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Görev 3: Takvim cumartesi ve pazar sütununu gerektiğinde çizer (ön yüz)

**Files:**
- Modify: `dashboard/src/components/CalendarEvents.tsx` (sabitler, yardımcılar, `days`, filtreler, ızgara)
- Modify: `dashboard/src/theme/ted-theme.scss:1760` ve `:2652-2654` (`grid-template-columns`)
- Modify: `dashboard/tests/e2e/takvim.spec.ts` (yeni test)
- Modify: `dashboard/tests/e2e/_gorsel-fixtures.ts` (`GORSEL['calendar/unified']`)
- Modify (yeniden üretilir): `dashboard/tests/e2e/gorsel-regresyon.spec.ts-snapshots/takvim-masaustu-linux.png`, `takvim-telefon-linux.png`, `dashboard/tests/e2e/aria-yapisi.spec.ts-snapshots/takvim.aria.yml`

**Interfaces:**
- Consumes: `/api/calendar/unified`'ın `UnifiedEvent` biçimi (`dashboard/src/types.ts:107`); Görev 2'den sonra cumartesi/pazar `private_lesson` olayları gelir. Bu görev arka uca bağlı değildir (e2e uç noktayı taklit eder).
- Produces: `.calendar-grid` üzerinde `--calendar-day-count` CSS değişkeni (5, 6 ya da 7); gün başlığı etiketleri `Pzt Sal Çar Per Cum Cmt Paz`.

- [ ] **Step 1: Başarısız e2e testini yaz**

`dashboard/tests/e2e/takvim.spec.ts` sonuna ekle:

```ts
// 2026-09-28: both of Işık's private lessons are on Saturday, and the grid
// drew Monday to Friday only. A weekend day gets a column in a week that has
// something on it; a week with nothing on the weekend stays five columns (İ6,
// like the legend: nothing to read past that is not there).
test.describe('weekend', () => {
  test.use({ timezoneId: 'Europe/Istanbul' })

  test('a Saturday private lesson gets its own column; a bare weekend does not', async ({ page }) => {
    await page.route('**/api/health', r => r.fulfill(json({
      timestamp: '', success: true, scrape_errors: [], duration_seconds: 1,
    })))
    await page.route('**/api/calendar/unified', r => r.fulfill(json({ events: [
      { id: 'l', type: 'lesson', title: 'Matematik', start: '2026-09-24T09:00:00', end: '2026-09-24T09:40:00',
        color: '', course: 'Matematik', courseFamily: 'purple', status: '' },
      { id: 'p', type: 'private_lesson', title: 'Fen Bilimleri · Deneme Hoca',
        start: '2026-09-26T12:00:00', end: '2026-09-26T13:00:00',
        color: '', course: 'Fen Bilimleri', courseFamily: 'teal', status: 'Özel Ders',
        subtitle: 'Özel Ders • Deneme Hoca' },
    ] })))
    await page.clock.setFixedTime(new Date('2026-09-24T10:30:00+03:00'))
    await page.goto('/takvim')

    // Both events are on the grid before anything is counted.
    await expect(page.locator('.calendar-grid .calendar-event')).toHaveCount(2)
    const heads = page.locator('.calendar-grid__header')
    await expect(heads).toHaveCount(7)                 // the corner + Mon–Fri + Sat
    await expect(heads.nth(6)).toContainText('Cmt')
    await expect(heads.nth(6)).toContainText('26 Eyl')
    await expect(page.locator('.calendar-event', { hasText: 'Fen Bilimleri' })).toBeVisible()
    await expect(page.locator('.calendar-nav__label')).toHaveText('21 - 26 Eylül 2026')

    // The next week has nothing on its weekend: five day columns again.
    await page.getByRole('button', { name: 'Sonraki hafta' }).click()
    await expect(page.locator('.calendar-nav__label')).toHaveText('28 Eylül - 2 Ekim 2026')
    await expect(heads).toHaveCount(6)
  })
})
```

- [ ] **Step 2: Derle ve testin başarısız olduğunu gör**

Run:
```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-tam-baglam/dashboard
npm run build; echo "build çıkış: $?"
DASHBOARD_SECRET_KEY=yerel-test-anahtari-pano-eksiklikleri TEDY_E2E_PORT=8296 npx playwright test takvim --reporter=line
```
Expected: build çıkış 0; yeni test FAIL (`.calendar-event` sayısı 1 — cumartesi olayı çizilmiyor); diğer dört takvim testi PASS.

- [ ] **Step 3: `CalendarEvents.tsx`'i değiştir**

1. İçe aktarma satırını genişlet:

```tsx
import { useState, useMemo, useCallback, useRef, useEffect, type CSSProperties } from 'react'
```

2. `const DAY_LABELS = ['Pzt', 'Sal', 'Çar', 'Per', 'Cum'] as const` satırı:

```tsx
const DAY_LABELS = ['Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz'] as const
```

3. `weekDates` ve `weekLabel` fonksiyonları:

```tsx
function weekDates(monday: Date): Date[] {
  return Array.from({ length: 7 }, (_, i) => addDays(monday, i))
}

function weekLabel(first: Date, last: Date): string {
  const mLabel = `${first.getDate()} ${
    first.getMonth() === last.getMonth() ? '' : MONTHS_LONG[first.getMonth()] + ' '
  }`
  return `${mLabel.trim()} - ${last.getDate()} ${MONTHS_LONG[last.getMonth()]} ${last.getFullYear()}`
}
```

4. Bileşende `const days = useMemo(() => weekDates(monday), [monday])` satırını şununla değiştir:

```tsx
  const weekEnd = useMemo(() => {
    const sunday = addDays(monday, 6)
    sunday.setHours(23, 59, 59, 999)
    return sunday
  }, [monday])
  // Monday to Friday always; Saturday and Sunday only in a week that has
  // something on that day. Both of Işık's private lessons are on Saturday
  // (2026-09-28), and an empty weekend column every week is two more columns
  // to read past (İ6). Decided from the dates alone, not from the kinds the
  // reader has hidden, so hiding a kind never takes its day away.
  const days = useMemo(() => {
    const starts = data.events
      .map(ev => parseEventDate(ev.start))
      .filter((d): d is Date => d !== null)
    return weekDates(monday)
      .map((date, dayIndex) => ({ date, dayIndex }))
      .filter(({ date, dayIndex }) => dayIndex < 5 || starts.some(s => isSameDay(s, date)))
  }, [monday, data.events])
```

5. `eventsInWeek` içindeki filtre:

```tsx
      .filter(ev => {
        if (!ev._start) return false
        return ev._start >= monday && ev._start <= weekEnd
      })
  }, [data.events, monday, weekEnd, hiddenTypes])
```

6. `typesInWeek`:

```tsx
  const typesInWeek = useMemo(() => {
    const kinds = new Set<string>()
    for (const ev of data.events) {
      const start = parseEventDate(ev.start)
      if (start && start >= monday && start <= weekEnd) kinds.add(ev.type)
    }
    return kinds
  }, [data.events, monday, weekEnd])
```

(Üstündeki açıklama yorumu olduğu gibi kalır.)

7. `eventsByDay`:

```tsx
  const eventsByDay = useMemo(() => {
    const map: Record<number, typeof eventsInWeek> = {}
    for (let i = 0; i < days.length; i++) map[i] = []
    for (const ev of eventsInWeek) {
      if (!ev._start) continue
      for (let di = 0; di < days.length; di++) {
        if (isSameDay(ev._start, days[di].date)) {
          map[di].push(ev)
          break
        }
      }
    }
    return map
  }, [eventsInWeek, days])
```

8. Gezinme etiketi:

```tsx
        <span className="calendar-nav__label">{weekLabel(days[0].date, days[days.length - 1].date)}</span>
```

9. Izgara açılışı ve başlık satırı:

```tsx
      <div
        className="calendar-grid"
        style={{ '--calendar-day-count': days.length } as CSSProperties}
      >
        {/* Header row */}
        <div className="calendar-grid__header" />
        {days.map(({ date: d, dayIndex }, i) => (
          <div
            key={i}
            className={`calendar-grid__header${isSameDay(d, today) ? ' calendar-grid__header--today' : ''}`}
          >
            <div>{DAY_LABELS[dayIndex]}</div>
            <div>{d.getDate()} {MONTHS_SHORT[d.getMonth()]}</div>
          </div>
        ))}
```

10. Saat satırındaki hücre döngüsünün başı `{days.map((d, di) => {` yerine:

```tsx
            {days.map(({ date: d }, di) => {
```

(Döngünün gövdesi değişmez.)

- [ ] **Step 4: Izgara sütun sayısını değişkene bağla**

`dashboard/src/theme/ted-theme.scss`, `.calendar-grid` kuralında:

```scss
  grid-template-columns: 50px repeat(var(--calendar-day-count, 5), minmax(0, 1fr));
```

ve telefon bloğundaki `.calendar-grid` kuralında:

```scss
    grid-template-columns: 36px repeat(var(--calendar-day-count, 5), minmax(0, 1fr));
```

(`minmax(0, 1fr)` üstündeki açıklama yorumu kalır; `--calendar-day-count` bileşenin satır içi stilinden gelir, varsayılan 5.)

- [ ] **Step 5: Lint, derleme ve takvim testleri**

Run:
```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-tam-baglam/dashboard
npm run lint; echo "lint çıkış: $?"
npm run build; echo "build çıkış: $?"
DASHBOARD_SECRET_KEY=yerel-test-anahtari-pano-eksiklikleri TEDY_E2E_PORT=8296 npx playwright test takvim polish --reporter=line
```
Expected: lint 0, build 0; `takvim.spec.ts` (yeni test dahil 5 test) ve `polish.spec.ts` PASS.

- [ ] **Step 6: Görsel fixture'a gerçek biçimli takvim ekle**

`dashboard/tests/e2e/_gorsel-fixtures.ts`, `GORSEL` nesnesinde `calendar: { events: [] },` satırından hemen önce ekle:

```ts
  // The unified calendar in its real shape. FULL's rows (baslik/tarih/tur)
  // predate it and put nothing on the grid, so the Takvim baseline was an
  // empty week. Thursday's first lessons and a Saturday private lesson, so it
  // shows the weekend column (2026-09-28). Invented teacher.
  'calendar/unified': { events: [
    { id: 'l1', type: 'lesson', title: 'Matematik', start: '2026-09-24T08:00:00', end: '2026-09-24T08:40:00',
      color: '', course: 'Matematik', courseFamily: 'purple', status: '', subtitle: '' },
    { id: 'l2', type: 'lesson', title: 'Türkçe', start: '2026-09-24T09:45:00', end: '2026-09-24T10:25:00',
      color: '', course: 'Türkçe', courseFamily: 'magenta', status: '', subtitle: '' },
    { id: 'p1', type: 'private_lesson', title: 'Fen Bilimleri · Deneme Hoca',
      start: '2026-09-26T12:00:00', end: '2026-09-26T13:00:00', color: '', course: 'Fen Bilimleri',
      courseFamily: 'teal', status: 'Özel Ders', subtitle: 'Özel Ders • Deneme Hoca' },
  ] },
```

- [ ] **Step 7: Farkı oku, sonra taban çizgisini yenile**

Run (güncellemesiz, fark üretmek için):
```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-tam-baglam/dashboard
DASHBOARD_SECRET_KEY=yerel-test-anahtari-pano-eksiklikleri TEDY_E2E_PORT=8296 npx playwright test gorsel-regresyon aria-yapisi -g takvim --reporter=line
```
Expected: `takvim looks as it did (masaustu)`, `(telefon)` ve takvim aria testi FAIL; diğer sayfalar koşmaz (`-g takvim`).

Sonra `find test-results -name 'takvim-*-actual.png' -o -name 'takvim-*-diff.png' -o -name 'takvim-*-expected.png'` ile bulunan PNG'leri Read aracıyla aç. Kabul koşulu, görev raporuna yazılır: fark yalnız "Haftalık Takvim" kartının içinde — perşembe 08:00 ve 09:00 satırlarında Matematik/Türkçe çipleri, 12:00 satırında cumartesi sütununda Fen Bilimleri çipi, "Cmt 26 Eyl" başlığı ve gezinme etiketinde "21 - 26 Eylül 2026". Üst bant, yan menü, efsane dışındaki alanlar değişmemiş olmalı. Aria farkı (test çıktısında) yalnız takvim başlık satırının metnini ve çip adlarını değiştirmeli. Başka bir fark varsa **durma ve bildir**; taban çizgisini yenileme.

Fark kabul edilirse:
```bash
DASHBOARD_SECRET_KEY=yerel-test-anahtari-pano-eksiklikleri TEDY_E2E_PORT=8296 npx playwright test gorsel-regresyon aria-yapisi -g takvim --update-snapshots --reporter=line
DASHBOARD_SECRET_KEY=yerel-test-anahtari-pano-eksiklikleri TEDY_E2E_PORT=8296 npx playwright test gorsel-regresyon aria-yapisi ibm-erisilebilirlik gorunum-kipleri tasarim-denetimi takvim polish --reporter=line
```
Expected: ikinci komutta hepsi PASS (13 sayfa × 2 genişlik görsel regresyon dahil; yalnız takvim dosyaları değişti). `ibm-erisilebilirlik` artık çipli bir takvimi denetliyor; yeni bir ihlal çıkarsa taban çizgisini commit'leme, ihlali rapora yaz (DONE_WITH_CONCERNS).

Webkit/Firefox kuruluysa: `DASHBOARD_SECRET_KEY=yerel-test-anahtari-pano-eksiklikleri TEDY_E2E_PORT=8296 npx playwright test capraz-tarayici --reporter=line` → PASS. Kurulu değilse kurmaya çalışma (bu makinede kurulum takılıyor); raporda "capraz-tarayici koşulmadı: tarayıcı yok" yaz.

- [ ] **Step 8: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-tam-baglam
git branch --show-current   # fix/pano-eksiklikleri
git status --short dashboard/   # yalnız aşağıdaki dosyalar
git add dashboard/src/components/CalendarEvents.tsx dashboard/src/theme/ted-theme.scss \
  dashboard/tests/e2e/takvim.spec.ts dashboard/tests/e2e/_gorsel-fixtures.ts \
  dashboard/tests/e2e/gorsel-regresyon.spec.ts-snapshots/takvim-masaustu-linux.png \
  dashboard/tests/e2e/gorsel-regresyon.spec.ts-snapshots/takvim-telefon-linux.png \
  dashboard/tests/e2e/aria-yapisi.spec.ts-snapshots/takvim.aria.yml
git commit -m "$(cat <<'EOF'
Takvim hafta sonu olayı olan haftada cumartesi/pazar sütunu çizsin

Izgara yalnız pazartesi–cuma çiziyordu; cumartesi özel dersleri hiç
görünmüyordu. Hafta sonu günü yalnız o gün bir olay varsa sütun alır;
takvim taban çizgileri fark okunduktan sonra yenilendi.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Görev 4: `/api/exams` `relatedContent` gerçek içerik biçimini okur

**Files:**
- Modify: `src/dashboard_api.py:1869-1890` (`_find_related_content`)
- Modify: `tests/test_exams.py:445-484` (`TestExamRelatedContent`)

**Interfaces:**
- Consumes: `assistant_tools._temiz_icerik(metin) -> str` (portal kromunu ve yorum bloğunu atar; modül-özel ama aynı paketten yerel içe aktarılır).
- Produces: `relatedContent: list[{"title": str, "type": "ders_icerikleri"}]` — `dashboard/src/types.ts:268` ve `ExamTimeline.tsx` bu biçimi zaten okur; ön yüz değişmez.

Gerçek biçim (salt-okunur ölçüm, 2026-09-28, `output/scraped_data.json`): `ders_icerikleri` 17 dersli bir sözlük; her değer `{tab_id, text, tables, items, cards}`; `cards` ve `items` **dizge** listeleri. Bir kartın ilk satırı başlıktır ("3. Hafta Planımız"); ikinci kart çoğu zaman aynı gönderinin başlıksız tekrarıdır ve `<öğretmen adı> | GG.AA.YYYY` satırıyla başlar. `items` kazanım cümleleridir. Bazı dersler yalnız boş listeler taşır; okunamayan ders yalnız `{tab_id, error}` taşır.

- [ ] **Step 1: Başarısız testleri yaz**

`tests/test_exams.py`'de `class TestExamRelatedContent:` sınıfının tamamını şununla değiştir:

```python
def _icerik(text="", cards=(), items=()):
    """ders_icerikleri[course] in its real shape (measured 2026-09-28):
    cards and items are strings. Invented teachers and text."""
    return {"tab_id": "ders_4", "text": text, "tables": [],
            "items": list(items), "cards": list(cards)}


class TestExamRelatedContent:
    """Related course content, read from the real {tab_id, text, tables,
    items, cards} shape. The old tests fed a list — a shape the scraper never
    writes — so relatedContent was [] on every real exam while they passed."""

    FEN_SINAVI = ("5-6-7-8. SINIFLAR FEN BİLİMLERİ – 2. DÖNEM 1. YAZILI SINAVI")

    def _related(self, client, title, ders):
        takvim = [_exam_event(title, "2026-03-31T10:00:00Z")]
        with patch.object(dashboard_api, "_scraped",
                          return_value=_scraped_with_exams(
                              takvim=takvim, ders_icerikleri=ders)):
            return client.get("/api/exams").get_json()["exams"][0]["relatedContent"]

    def test_finds_matching_course_content(self, client):
        ders = {"Fen Bilimleri": _icerik(
            text="3. Hafta\nKurgu Öğretmen | 28.09.2026\nBu hafta Güneş sistemi.",
            cards=[
                "3. Hafta\nKurgu Öğretmen | 28.09.2026\nSevgili öğrencilerim,\n"
                "Bu hafta Güneş sistemi.\n  1 Yorum yapıldı!\n  Daha fazla oku\n"
                "Uydurma Öğrenci\nçok güzel\nYorum Ekle",
                # The portal's second, title-less rendering of the same post.
                "Kurgu Öğretmen | 28.09.2026\nSevgili öğrencilerim,\nBu hafta Güneş sistemi.",
            ],
            items=["Gezegenleri  Güneş'e uzaklıklarına göre sıralar."])}
        assert self._related(client, self.FEN_SINAVI, ders) == [
            {"title": "3. Hafta", "type": "ders_icerikleri"},
            {"title": "Gezegenleri Güneş'e uzaklıklarına göre sıralar.", "type": "ders_icerikleri"},
        ]

    def test_teacher_signature_and_comments_never_become_titles(self, client):
        ders = {"Fen Bilimleri": _icerik(cards=[
            "Kurgu Öğretmen | 28.09.2026\nSevgili öğrencilerim,",
            "Uzay Çağı\nKurgu Öğretmen | 21.09.2026\n  Daha fazla oku\nUydurma Öğrenci\nYorum Ekle",
        ])}
        basliklar = [c["title"] for c in self._related(client, self.FEN_SINAVI, ders)]
        assert basliklar == ["Uzay Çağı"]
        assert not any("Kurgu Öğretmen" in b or "Uydurma Öğrenci" in b for b in basliklar)

    def test_turkish_case_content_matching(self, client):
        """Course name case mismatch must still find content."""
        ders = {"İngilizce": _icerik(cards=["Week 3\nÖrnek Teacher | 28.09.2026\nDear 7th graders,"])}
        content = self._related(
            client, "5-6-7-8. SINIFLAR İNGİLİZCE – 2. DÖNEM 1. YAZILI SINAVI", ders)
        assert content == [{"title": "Week 3", "type": "ders_icerikleri"}]

    def test_other_courses_and_unread_courses_add_nothing(self, client):
        ders = {
            "Matematik": _icerik(cards=["Rasyonel sayılar\nÖrnek Hoca | 28.09.2026"]),
            "Fen Bilimleri": {"tab_id": "ders_4", "error": "Message: no such element"},
        }
        assert self._related(client, self.FEN_SINAVI, ders) == []

    def test_titles_are_bounded_and_deduplicated(self, client):
        uzun = "Kuvvet ve enerji " * 20
        ders = {"Fen Bilimleri": _icerik(
            cards=[f"Başlık {i}\nKurgu Öğretmen | 28.09.2026" for i in range(8)],
            # An item repeating a card title is listed once.
            items=[uzun, "Başlık 1"] + [f"Kazanım {i}" for i in range(8)])}
        content = self._related(client, self.FEN_SINAVI, ders)
        basliklar = [c["title"] for c in content]
        # Five card titles, then the first five items with the repeat dropped.
        assert basliklar[:5] == [f"Başlık {i}" for i in range(5)]
        assert basliklar[6:] == ["Kazanım 0", "Kazanım 1", "Kazanım 2"]
        assert basliklar.count("Başlık 1") == 1
        assert basliklar[5].endswith("…") and len(basliklar[5]) <= 140
        assert all(len(b) <= 140 for b in basliklar)

    def test_at_most_ten_across_duplicate_course_tabs(self, client):
        # The portal has two tabs for one course ("İngilizce", "İngilizce (2)"
        # both normalise to İngilizce); together they must not exceed ten.
        ders = {
            "İngilizce": _icerik(cards=[f"Week {i}" for i in range(5)],
                                 items=[f"Outcome {i}" for i in range(5)]),
            "İngilizce (2)": _icerik(cards=["Reading club"]),
        }
        content = self._related(
            client, "5-6-7-8. SINIFLAR İNGİLİZCE – 2. DÖNEM 1. YAZILI SINAVI", ders)
        assert len(content) == 10
```

- [ ] **Step 2: Testlerin başarısız olduğunu gör**

Run: `DASHBOARD_SECRET_KEY=yerel-test-anahtari-pano-eksiklikleri .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_exams.py -k RelatedContent`
Expected: `test_other_courses_and_unread_courses_add_nothing` dışında hepsi FAIL (`[] == [...]`).

- [ ] **Step 3: Uygula**

`src/dashboard_api.py`, `_find_related_content` fonksiyonunu tamamen şununla değiştir (üstüne iki sabit):

```python
# A card whose first line is only "<name> | DD.MM.YYYY" is the portal's
# second, title-less rendering of the post before it; the line is a
# teacher's name, not a content title.
_KART_IMZASI = re.compile(r"^.+ \| \d{2}\.\d{2}\.\d{4}$")
_ILGILI_BASLIK_SINIRI = 140


def _find_related_content(exam_course, ders_icerikleri):
    """The exam's course's content in the open week: each card's title (its
    first line, portal chrome and comments dropped) and each item, at most
    five of each and ten in all. ders_icerikleri[course] is
    {tab_id, text, tables, items, cards} with cards and items as strings
    (measured 2026-09-28); this used to branch on a list, a shape the scraper
    never writes, so relatedContent was [] on every exam."""
    from src.assistant_tools import _temiz_icerik
    related = []
    if not isinstance(ders_icerikleri, dict):
        return related

    exam_lower = _turkish_lower(exam_course)
    for course_name, kayit in ders_icerikleri.items():
        if not isinstance(kayit, dict):
            continue
        if _turkish_lower(normalize_course(course_name)) != exam_lower:
            continue
        kart_basliklari = []
        for kart in kayit.get("cards") or []:
            if not isinstance(kart, str):
                continue
            ilk = next((s for s in _temiz_icerik(kart).split("\n") if s.strip()), "")
            if ilk and not _KART_IMZASI.match(ilk):
                kart_basliklari.append(ilk)
        maddeler = [" ".join(m.split()) for m in kayit.get("items") or [] if isinstance(m, str)]
        for baslik in kart_basliklari[:5] + [m for m in maddeler if m][:5]:
            if len(baslik) > _ILGILI_BASLIK_SINIRI:
                baslik = baslik[:_ILGILI_BASLIK_SINIRI - 1].rstrip() + "…"
            if all(r["title"] != baslik for r in related):
                related.append({"title": baslik, "type": "ders_icerikleri"})

    return related[:10]
```


- [ ] **Step 4: Testlerin geçtiğini gör**

Run: `DASHBOARD_SECRET_KEY=yerel-test-anahtari-pano-eksiklikleri .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_exams.py tests/test_assistant_ogrenci_araclari.py`
Expected: hepsi PASS.

- [ ] **Step 5: Canlı biçimle salt-okunur duman denemesi (commit edilmez, kişisel veri kopyalanmaz)**

Run:
```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-tam-baglam
DASHBOARD_SECRET_KEY=yerel-test-anahtari-pano-eksiklikleri .venv/bin/python - <<'EOF'
import json, sys
sys.path.insert(0, ".")
import src.dashboard_api as api
d = json.load(open("/mnt/thunderbolt/workspaces/TED/output/scraped_data.json"))
for ders in ("Matematik", "Fen Bilimleri", "Türkçe"):
    r = api._find_related_content(ders, d.get("ders_icerikleri"))
    print(ders, len(r), all(" | " not in x["title"] for x in r))
EOF
```
Expected: en az bir ders için sayı > 0 ve her satırda `True` (hiçbir başlık öğretmen imzası değil). Yalnız sayıları ve True/False'u rapora yaz; başlık metinlerini yazma.

- [ ] **Step 6: Tam paket**

Run: `DASHBOARD_SECRET_KEY=yerel-test-anahtari-pano-eksiklikleri .venv/bin/python -m pytest -q -p no:cacheprovider 2>&1 | tail -15`
Expected: önceden kırmızılar dışında kırmızı yok.

- [ ] **Step 7: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-tam-baglam
git branch --show-current   # fix/pano-eksiklikleri
git add src/dashboard_api.py tests/test_exams.py
git commit -m "$(cat <<'EOF'
Sınavların ilgili içeriği gerçek ders içeriği biçiminden okunsun

_find_related_content yalnız liste bekliyordu; ders_icerikleri[ders] ise
{tab_id, text, tables, items, cards} sözlüğü, kart ve maddeler dizge. Kart
başlıkları (öğretmen imzası ve yorumlar atılarak) ve maddeler okunuyor;
testler gerçek biçime çevrildi.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Görev 5: Önceki yılın not raporu sentetik geçmiş sınav üretmez; CLAUDE.md'nin bilinen sorunlar maddesi kapanır

**Files:**
- Modify: `src/assistant_tools.py:948-980` (`notlar_metni` yıl denetimi paylaşılan yardımcıya taşınır)
- Modify: `src/dashboard_api.py:914-922` (`_canli_notlar`, yeni `_guncel_ogretim_yili`), `src/dashboard_api.py:1899-2026` (`_sinav_listesi`)
- Modify: `tests/test_exams.py` (`_scraped_with_exams` `semester` parametresi, `TestSyntheticExams`)
- Test: `tests/test_pano_eksiklikleri.py`
- Modify: `CLAUDE.md:186`, `CLAUDE.md:193`

**Interfaces:**
- Consumes: Görev 1–4'ün davranışı (CLAUDE.md onları anlatır).
- Produces: `assistant_tools.rapor_yili(donem: Any) -> str | None`, `assistant_tools.onceki_yil_raporu_mu(donem: Any, ogretim_yili: Any) -> bool`, `dashboard_api._guncel_ogretim_yili() -> str | None`. `_sinav_listesi(data, now=None)` imzası değişmez.

- [ ] **Step 1: Başarısız testleri yaz**

`tests/test_pano_eksiklikleri.py` sonuna ekle:

```python
# ── 4. A report on an earlier school year is not this year's exams ───────────

@pytest.mark.parametrize("donem, yil, beklenen", [
    ("2025-2026 4. Arakarne", "2026-2027", True),
    ("2026-2027 1. Dönem", "2026-2027", False),
    ("2025 - 2026 2. Dönem", "2026-2027", True),
    ("2. Dönem", "2026-2027", False),          # the term names no year
    ("2025-2026 4. Arakarne", None, False),    # the current year is unknown
    ("", "", False),
])
def test_onceki_yil_raporu_mu(donem, yil, beklenen):
    assert at.onceki_yil_raporu_mu(donem, yil) is beklenen


def test_rapor_yili():
    assert at.rapor_yili("2025-2026 4. Arakarne") == "2025-2026"
    assert at.rapor_yili("2. Dönem") is None


def test_guncel_ogretim_yili_dosyadan_okunur(api, monkeypatch):
    monkeypatch.setattr(api, "_load_json",
                        lambda ad: {"year": "2026-2027"} if ad == "academic_year.json" else {})
    assert api._guncel_ogretim_yili() == "2026-2027"
    monkeypatch.setattr(api, "_load_json", lambda ad: {})
    assert api._guncel_ogretim_yili() is None
```

`tests/test_exams.py`'de `_scraped_with_exams` imzasını ve `semester` satırını değiştir:

```python
def _scraped_with_exams(takvim=None, homework=None, grades=None,
                        ders_icerikleri=None, semester="2. Dönem"):
    data = {
        "takvim": takvim or [],
        "odevlerim": {
            "summary": "",
            "homework": {"rows": homework or []},
        },
        "gelisim_raporu": {
            "semester": semester,
```

ve `class TestSyntheticExams:` içine (sınıfın sonuna) ekle:

```python
    # Measured: the portal kept 2025-2026's "4. Arakarne" report well into
    # 2026-2027, and /api/exams listed its graded columns as this year's past
    # exams. The assistant's notlar already makes this check.
    def test_prior_year_report_makes_no_synthetic_exams(self, client):
        grades = [_grade_row("Matematik", s1="85", s2="90")]
        with patch.object(dashboard_api, "_scraped", return_value=_scraped_with_exams(
                grades=grades, semester="2025-2026 4. Arakarne")), \
             patch.object(dashboard_api, "_guncel_ogretim_yili", return_value="2026-2027"):
            data = client.get("/api/exams").get_json()
        assert data["exams"] == []
        assert data["stats"] == {"upcoming": 0, "past": 0, "averageGrade": None}

    def test_prior_year_report_keeps_takvim_exams(self, client):
        past = (datetime.now() - timedelta(days=5)).isoformat() + "Z"
        takvim = [_exam_event("5-6-7-8. SINIFLAR TÜRKÇE – 1. DÖNEM 1. YAZILI SINAVI", past)]
        grades = [_grade_row("Matematik", s1="85")]
        with patch.object(dashboard_api, "_scraped", return_value=_scraped_with_exams(
                takvim=takvim, grades=grades, semester="2025-2026 4. Arakarne")), \
             patch.object(dashboard_api, "_guncel_ogretim_yili", return_value="2026-2027"):
            data = client.get("/api/exams").get_json()
        assert len(data["exams"]) == 1
        assert data["exams"][0]["date"] is not None          # the takvim one, not a synthetic

    def test_current_year_report_still_makes_synthetic_exams(self, client):
        grades = [_grade_row("Matematik", s1="85", s2="90")]
        with patch.object(dashboard_api, "_scraped", return_value=_scraped_with_exams(
                grades=grades, semester="2026-2027 1. Dönem")), \
             patch.object(dashboard_api, "_guncel_ogretim_yili", return_value="2026-2027"):
            data = client.get("/api/exams").get_json()
        assert len(data["exams"]) == 2 and data["stats"]["averageGrade"] == 87.5

    def test_unknown_year_keeps_synthetic_exams(self, client):
        grades = [_grade_row("Matematik", s1="85")]
        with patch.object(dashboard_api, "_scraped", return_value=_scraped_with_exams(
                grades=grades, semester="2025-2026 4. Arakarne")), \
             patch.object(dashboard_api, "_guncel_ogretim_yili", return_value=None):
            data = client.get("/api/exams").get_json()
        assert len(data["exams"]) == 1
```

- [ ] **Step 2: Testlerin başarısız olduğunu gör**

Run: `DASHBOARD_SECRET_KEY=yerel-test-anahtari-pano-eksiklikleri .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pano_eksiklikleri.py tests/test_exams.py -k "onceki or rapor_yili or ogretim_yili or prior_year or current_year or unknown_year"`
Expected: FAIL — `AttributeError: module 'src.assistant_tools' has no attribute 'onceki_yil_raporu_mu'` / `'rapor_yili'`, `dashboard_api` has no attribute `_guncel_ogretim_yili`.

- [ ] **Step 3: Yıl denetimini paylaşılan yardımcıya taşı**

`src/assistant_tools.py`, `def notlar_metni` satırının hemen üstüne:

```python
_DONEM_YILI = re.compile(r"(\d{4})\s*-\s*(\d{4})")


def rapor_yili(donem: Any) -> str | None:
    """The school year a gelişim report's term names ("2025-2026 4. Arakarne"
    -> "2025-2026"); None when the term names none ("2. Dönem")."""
    m = _DONEM_YILI.search(str(donem or ""))
    return f"{m.group(1)}-{m.group(2)}" if m else None


def onceki_yil_raporu_mu(donem: Any, ogretim_yili: Any) -> bool:
    """True when the report names a school year, TEDY knows the current one,
    and they differ. Unknown on either side is not "old": it must not hide
    the grades. notlar_metni and /api/exams (_sinav_listesi) share this."""
    rapor = rapor_yili(donem)
    yil = str(ogretim_yili or "").strip()
    return bool(rapor and yil and rapor != yil)
```

`notlar_metni` içindeki

```python
    m = re.search(r"(\d{4})\s*-\s*(\d{4})", donem)
    if m and yil and f"{m.group(1)}-{m.group(2)}" != yil:
        parcalar.append(f"ÖNCEKİ ÖĞRETİM YILI: portalın gelişim raporu {m.group(1)}-{m.group(2)} "
```

satırlarını şununla değiştir (mesajın geri kalanı aynı kalır):

```python
    if onceki_yil_raporu_mu(donem, yil):
        parcalar.append(f"ÖNCEKİ ÖĞRETİM YILI: portalın gelişim raporu {rapor_yili(donem)} "
```

- [ ] **Step 4: `_guncel_ogretim_yili` ve `_sinav_listesi`**

`src/dashboard_api.py`, `_canli_notlar` fonksiyonunu şu ikisiyle değiştir:

```python
def _guncel_ogretim_yili():
    """The school year TEDY believes it is in (output/academic_year.json's
    `year`, e.g. "2026-2027"), or None when unknown."""
    try:
        yil = _load_json("academic_year.json")
    except (OSError, ValueError):
        return None  # an unknown year labels nothing "old"; it must not hide the grades
    return yil.get("year") if isinstance(yil, dict) else None


def _canli_notlar():
    """The gelişim report /api/grades serves, with the school year TEDY
    believes it is in, so a report still showing last year can say so."""
    return {"gelisim": _scraped().get("gelisim_raporu", {}),
            "ogretim_yili": _guncel_ogretim_yili()}
```

`_sinav_listesi` içinde `grade_lookup = _build_grade_lookup(grades_list)` satırının hemen altına:

```python
    # A report still on an earlier school year — measured: 2025-2026's
    # "4. Arakarne" persisted well into 2026-2027 — is last year's exams, not
    # this year's past ones: no synthetic exams from it (the check the
    # assistant's notlar makes). Notlar still shows the report under its term.
    from src.assistant_tools import onceki_yil_raporu_mu
    onceki_yil = isinstance(gelisim, dict) and onceki_yil_raporu_mu(
        gelisim.get("semester"), _guncel_ogretim_yili())
```

ve `# --- Synthetic exams from grades without takvim events ---` altındaki döngü başını:

```python
    for row in ([] if onceki_yil else grades_list):
```

- [ ] **Step 5: Testlerin geçtiğini gör**

Run: `DASHBOARD_SECRET_KEY=yerel-test-anahtari-pano-eksiklikleri .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pano_eksiklikleri.py tests/test_exams.py tests/test_assistant_ogrenci_araclari.py`
Expected: hepsi PASS (mevcut `test_notlar_eski_yili_acikca_etiketler`, `test_notlar_bu_yilinsa_eski_demez`, `test_canli_icerik_ve_notlar_kaynaklari` dahil — davranış korunuyor).

- [ ] **Step 6: Notlar sayfasının etiketini doğrula (değiştirme)**

Run: `grep -n "semester\|önceki\|Önceki" dashboard/src/components/GradeTable.tsx`
Expected (planlamada ölçüldü): yalnız `Notlar — ${data.semester}` başlığı ve boş durum cümlesi; ayrı bir "önceki yıl" işareti yok. Bu görev Notlar'ı değiştirmez; sonucu rapora yaz.

- [ ] **Step 7: CLAUDE.md**

`CLAUDE.md`'de "Asistan ve kendi verisi (canlı öğrenci araçları)" maddesindeki şu ifadeyi:

```
including weekend private lessons for future weeks — the dashboard's own unified calendar cannot show these; see "Panonun bilinen sorunları" below)
```

şununla değiştir:

```
including weekend private lessons for the weeks ahead — the dashboard's unified calendar shows the current week only)
```

`- **Panonun bilinen sorunları** (found while building …` ile başlayan maddenin **tamamını** (tek satır) şu maddeyle değiştir:

```
- **Unified calendar and exam list** (plan `docs/superpowers/plans/2026-09-28-pano-eksiklikleri.md`, closing the four faults the Görev 2 live tools had found): `/api/calendar/unified` draws lessons through `assistant_tools.gunun_dersleri`, the same Python port of `utils/schedule.ts`'s `dayColumns` the `ders_programi` tool reads — so the upper-case dotless header (`PAZARTESI`) matches and Friday keeps its own bell; the old mixed-case match drew no lesson at all. `_current_week_dates()` is Monday to Sunday and private lessons are expanded with `hafta_sonu=True`, so both Saturday lessons appear; `CalendarEvents` gives Saturday or Sunday a column only in a week that has something on that day (`--calendar-day-count`, decided from dates, so hiding a kind never removes its day), five columns otherwise. `/api/exams`' `relatedContent` reads the real `{tab_id, text, tables, items, cards}` shape (cards and items are strings): each card's first line with the portal chrome dropped — a card that opens with the `<name> | DD.MM.YYYY` line is the portal's title-less second rendering and is skipped — plus each item, ≤ 140 characters, ≤ 10 in all. A gelişim report whose term names a school year other than `academic_year.json`'s (`assistant_tools.onceki_yil_raporu_mu`, the check `notlar` makes) yields no synthetic past exams; an unknown year on either side keeps them. The Notlar page still lists such a report under its term title ("Notlar — 2025-2026 4. Arakarne"); it has no separate "önceki yıl" flag.
```

- [ ] **Step 8: Tam paket**

Run: `DASHBOARD_SECRET_KEY=yerel-test-anahtari-pano-eksiklikleri .venv/bin/python -m pytest -q -p no:cacheprovider 2>&1 | tail -15`
Expected: önceden kırmızılar dışında kırmızı yok.

- [ ] **Step 9: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-tam-baglam
git branch --show-current   # fix/pano-eksiklikleri
git add src/assistant_tools.py src/dashboard_api.py tests/test_pano_eksiklikleri.py tests/test_exams.py CLAUDE.md
git commit -m "$(cat <<'EOF'
Önceki yılın not raporu bu yılın geçmiş sınavı gibi listelenmesin

notlar aracının yıl denetimi onceki_yil_raporu_mu olarak paylaşıldı;
_sinav_listesi başka bir öğretim yılını gösteren rapordan sentetik sınav
üretmiyor. CLAUDE.md'nin "Panonun bilinen sorunları" maddesi kapandı.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Görev 6: Figür ucu korpus sürümünü denetler (arka uç)

**Files:**
- Modify: `src/assistant_tools.py` (içe aktarmalar; `KORPUS_SURUMU_TTL`; `McpRegistry.__init__` sonu; yeni `McpRegistry.korpus_surumu`; `dispatch`'in `figur_getir` dalı)
- Modify: `src/dashboard_api.py:2222-2281` (figür önbelleği ve `assistant_figure`)
- Modify/Test: `tests/test_assistant_gorseller.py`

**Interfaces:**
- Consumes: maarif `server_info` yanıtı — tek bir JSON nesnesi, ölçüldü 2026-09-28: `{"app_version": "0.4.1", "app_revision": "unknown", "source": "tymm.meb.gov.tr", "corpus_version": "1.6", "build_date": "…", "counts": {…}, "entities": {…}}`. Sunucu notları `{result: …}` zarfından söz ettiği için o zarf da kabul edilir.
- Produces: `assistant_tools.KORPUS_SURUMU_TTL: float = 300.0`; `McpRegistry.korpus_surumu() -> str | None`; `McpRegistry.monotonik: Callable[[], float]` (testlerin saati); `figur_getir` atfının `locator["corpus_version"]: str` (okunabildiyse); `dashboard_api.FIGUR_SURUM_DEGISTI: str`; `_FIGUR_ONBELLEGI` anahtarı `tuple[str, int]`. Görev 7 `locator.corpus_version`'ı okur.

- [ ] **Step 1: Mevcut uç nokta testlerini sürümlü adrese çevir ve yeni testleri yaz**

`tests/test_assistant_gorseller.py`'de `# ── 4. the reader's figure endpoint` bölümünde:

`READER = …` satırının altına ekle:

```python
SURUM = "1.6"


def _server_info(surum=SURUM):
    # server_info's real answer (measured 2026-09-28), counts trimmed.
    return McpToolResult(ok=True, text=json.dumps({
        "app_version": "0.4.1", "app_revision": "unknown", "source": "tymm.meb.gov.tr",
        "corpus_version": surum, "build_date": "2026-09-26T00:17:53+00:00",
        "counts": {"textbook": 203}, "entities": {"figure": 53290}}))


def _yol(figure_id, surum=SURUM):
    return f"/api/assistant/figure/{figure_id}?v={surum}"


def _figur_cagrilari(maarif):
    """get_figure calls only: the endpoint also asks server_info."""
    return [c for c in maarif.calls if c[0] == "get_figure"]
```

`figur_env` fixture'ında `results={…}` sözlüğüne `"server_info": _server_info(),` ekle (`"get_figure": …`'dan önce).

Sonra mevcut testlerde şu değişiklikleri yap (başka bir şey değişmez):

| Test | Değişiklik |
|---|---|
| `test_figur_ucu_gorseli_bayt_olarak_dondurur` | `client.get(_yol(12))`; son satır `assert _figur_cagrilari(maarif) == [("get_figure", {"figure_id": 12, "include_image": True})]` |
| `test_figur_ucu_onbellekten_okur` | iki istek `_yol(12)`; `assert len(_figur_cagrilari(maarif)) == 1` |
| `test_figur_onbellegi_64_girdiyle_sinirli` | istekler `_yol(i)` ve `_yol(1)`; `assert (SURUM, 1) not in dashboard_api._FIGUR_ONBELLEGI and (SURUM, 65) in dashboard_api._FIGUR_ONBELLEGI`; `assert len(_figur_cagrilari(maarif)) == 66` |
| `test_bilinmeyen_figur_404` | `_yol(5000)`; `assert (SURUM, 5000) not in dashboard_api._FIGUR_ONBELLEGI` |
| `test_mcp_kapaliyken_502_ve_turkce_cumle` | `_yol(12)`; `assert (SURUM, 12) not in dashboard_api._FIGUR_ONBELLEGI` |
| `test_mufredat_sunucusu_yapilandirilmamissa_502` | `_yol(12)` |
| `test_desteklenmeyen_bicim_sunulmaz` | `_yol(12)` |
| `test_figur_ucu_okura_ve_girissize_kapali` | üç istek `_yol(12)` (`maarif.calls == []` kalır) |
| `test_buyuk_figur_sunulur_ama_onbellege_girmez` | iki istek `_yol(12)`; `assert (SURUM, 12) not in …`; `assert len(_figur_cagrilari(maarif)) == 2` |
| `test_figur_onbellegi_toplam_baytla_sinirli` | istekler `_yol(i)`; `assert list(dashboard_api._FIGUR_ONBELLEGI) == [(SURUM, 3), (SURUM, 4), (SURUM, 5)]` |
| `test_en_buyuk_gecerli_figur_id_sunucuya_sorulur` | `_yol(2147483647)`; `assert _figur_cagrilari(maarif) == [("get_figure", {"figure_id": 2147483647, "include_image": True})]` |
| `test_pano_api_anahtari_figur_ucuna_401` | `_yol(12)` |

`test_sinir_disi_figur_id_rotada_404` değişmez (rota düzeyinde 404, `v`'siz).

Dosyanın sonuna yeni bölüm ekle:

```python
# ── 7. the corpus version travels with every figure URL (2026-09-28) ─────────
# The 1.6 build renumbered figure ids: an id from before it names a different
# picture. A URL now carries the version it was cited under, and the endpoint
# refuses any other.

def test_korpus_surumu_server_info_dan_okunur_ve_sureli_tutulur():
    maarif = _FakeClient("maarif-mufredat", MAARIF_TOOLS, results={"server_info": _server_info()})
    reg = _registry(maarif=maarif)
    saat = [1000.0]
    reg.monotonik = lambda: saat[0]
    assert reg.korpus_surumu() == SURUM
    saat[0] += at_ttl() - 1
    assert reg.korpus_surumu() == SURUM
    assert [c[0] for c in maarif.calls] == ["server_info"]
    saat[0] += 2                                  # past the TTL: asked again
    maarif.results["server_info"] = _server_info("1.7")
    assert reg.korpus_surumu() == "1.7"
    assert [c[0] for c in maarif.calls] == ["server_info", "server_info"]


def at_ttl():
    from src.assistant_tools import KORPUS_SURUMU_TTL
    return KORPUS_SURUMU_TTL


def test_korpus_surumu_result_zarfini_da_okur():
    maarif = _FakeClient("maarif-mufredat", MAARIF_TOOLS, results={"server_info": McpToolResult(
        ok=True, text=json.dumps({"result": {"corpus_version": SURUM}}))})
    assert _registry(maarif=maarif).korpus_surumu() == SURUM


def test_okunamayan_surum_none_ve_onbellege_girmez():
    maarif = _FakeClient("maarif-mufredat", MAARIF_TOOLS, results={
        "server_info": McpToolResult(ok=False, error="timeout")})
    reg = _registry(maarif=maarif)
    assert reg.korpus_surumu() is None
    maarif.results["server_info"] = _server_info()
    assert reg.korpus_surumu() == SURUM           # the failure was not remembered
    assert _registry(maarif=False).korpus_surumu() is None


def test_figur_atfi_korpus_surumunu_tasir():
    maarif = _FakeClient("maarif-mufredat", MAARIF_TOOLS, results={
        "get_figure": _figur_sonucu(), "server_info": _server_info()})
    c = _registry(maarif=maarif).dispatch("figur_getir", {"figure_id": 1875}).citations[0]
    assert c["locator"]["figure_id"] == 1875 and c["locator"]["corpus_version"] == SURUM


def test_surum_okunamazsa_atif_surumsuz_kalir():
    maarif = _FakeClient("maarif-mufredat", MAARIF_TOOLS, results={
        "get_figure": _figur_sonucu(), "server_info": McpToolResult(ok=False, error="timeout")})
    out = _registry(maarif=maarif).dispatch("figur_getir", {"figure_id": 1875})
    assert out.ok and "corpus_version" not in out.citations[0]["locator"]


SURUM_CUMLESI = "Bu görsel, müfredat korpusu güncellendiği için değişti; soruyu yeniden sorun."


@pytest.mark.parametrize("yol", ["/api/assistant/figure/12", "/api/assistant/figure/12?v=",
                                 "/api/assistant/figure/12?v=1.5"])
def test_surumsuz_ya_da_eski_surumlu_istek_404_ve_turkce_cumle(figur_env, yol):
    client, maarif, _ = figur_env
    r = client.get(yol)
    assert r.status_code == 404
    assert r.get_json() == {"error": SURUM_CUMLESI}
    assert dashboard_api.FIGUR_SURUM_DEGISTI == SURUM_CUMLESI
    assert _figur_cagrilari(maarif) == []         # the old id is never looked up


def test_onbellek_surum_ve_id_ile_anahtarlanir(figur_env):
    client, maarif, reg = figur_env
    assert client.get(_yol(12)).status_code == 200
    assert (SURUM, 12) in dashboard_api._FIGUR_ONBELLEGI
    # The corpus moves to 1.7: the cached 1.6 picture is not served for it.
    maarif.results["server_info"] = _server_info("1.7")
    reg._korpus_surumu = None
    assert client.get(_yol(12)).status_code == 404
    assert client.get(_yol(12, "1.7")).status_code == 200
    assert (("1.7", 12) in dashboard_api._FIGUR_ONBELLEGI
            and len(_figur_cagrilari(maarif)) == 2)


def test_surum_okunamazsa_502(figur_env):
    client, maarif, _ = figur_env
    maarif.results["server_info"] = McpToolResult(ok=False, error="timeout")
    r = client.get(_yol(12))
    assert r.status_code == 502
    assert r.get_json() == {"error": dashboard_api.FIGUR_ULASILAMADI}
    assert _figur_cagrilari(maarif) == []
```

- [ ] **Step 2: Testlerin başarısız olduğunu gör**

Run: `DASHBOARD_SECRET_KEY=yerel-test-anahtari-pano-eksiklikleri .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_assistant_gorseller.py`
Expected: FAIL — `korpus_surumu`/`monotonik` yok (`AttributeError`), `FIGUR_SURUM_DEGISTI` yok, önbellek anahtarları tam sayı (`(SURUM, 1) not in` yanlış anlamda geçse bile `(SURUM, 65) in` FAIL), sürümsüz istek 200 döner.

- [ ] **Step 3: `McpRegistry`'ye sürümü ekle**

`src/assistant_tools.py`:

İçe aktarmalara (`import re`'den sonra, alfabetik):

```python
import threading
import time
```

`OLU_BAGLANTILAR = …` tanımının altına:

```python
# How long a corpus_version read from maarif's server_info is trusted, per
# process. The corpus changes only when CureoHub swaps a build in (1.5 -> 1.6
# on 2026-09-27, which renumbered figure ids); five minutes bounds how long
# after such a swap a URL cited under the old build is still accepted.
KORPUS_SURUMU_TTL = 300.0
```

`McpRegistry.__init__`'in sonuna (`self.saat = saat` satırından sonra):

```python
        # maarif's corpus_version (server_info) and when it was read. Every
        # figure citation carries it and /api/assistant/figure checks it, so
        # a figure id from another build is refused, not mis-served.
        self._korpus_surumu: tuple[str, float] | None = None
        self._korpus_kilidi = threading.Lock()
        self.monotonik: Callable[[], float] = time.monotonic
```

`figur_gorseli` metodunun hemen üstüne:

```python
    def korpus_surumu(self) -> str | None:
        """maarif's current corpus_version ("1.6"), read from server_info and
        trusted for KORPUS_SURUMU_TTL seconds. None when the server is not
        configured or gave no version; a failure is not cached, so the next
        request asks again."""
        simdi = self.monotonik()
        with self._korpus_kilidi:
            if self._korpus_surumu and simdi - self._korpus_surumu[1] < KORPUS_SURUMU_TTL:
                return self._korpus_surumu[0]
        client = self.clients.get("maarif-mufredat")
        if client is None:
            return None
        result = client.call_tool("server_info", {})
        if not result.ok:
            return None
        bilgi = _figur_bilgisi(_json_parcalari(result.text))
        if isinstance(bilgi.get("result"), dict):
            # The {result: …} envelope the server's own notes describe.
            bilgi = bilgi["result"]
        surum = str(bilgi.get("corpus_version") or "").strip()
        if not surum:
            return None
        with self._korpus_kilidi:
            self._korpus_surumu = (surum, simdi)
        return surum
```

`dispatch`'in `if name == "figur_getir":` dalında, `caption` ataması bloğunun altına (aynı girinti):

```python
            # The build this id belongs to: the panel asks for
            # /api/assistant/figure/<id>?v=<corpus_version>.
            surum = self.korpus_surumu()
            if surum:
                locator["corpus_version"] = surum
```

- [ ] **Step 4: Uç noktayı değiştir**

`src/dashboard_api.py`, figür bölümünün açıklama yorumunun son cümlesini ve önbellek tanımını şununla değiştir:

```python
# under FIGUR_TOPLAM_SINIRI. Keyed by (corpus version, id): the 1.6 build
# renumbered figure ids (2026-09-27), so an id means a picture only together
# with the build it was cited under. Nothing expires; a new build is a new key.
FIGUR_ONBELLEK_BOYUTU = 64
FIGUR_TEK_SINIRI = 1_500_000
FIGUR_TOPLAM_SINIRI = 16 * 1024 * 1024
_FIGUR_ONBELLEGI: "OrderedDict[tuple[str, int], tuple[bytes, str]]" = OrderedDict()
_FIGUR_KILIDI = threading.Lock()
FIGUR_ULASILAMADI = "Ders kitabı görseline şu an ulaşılamadı; biraz sonra yeniden deneyin."
FIGUR_SURUM_DEGISTI = ("Bu görsel, müfredat korpusu güncellendiği için değişti; "
                       "soruyu yeniden sorun.")
```

(`# A figure id's image never changes: nothing expires.` cümlesi silinir; yerine yukarıdaki üç satır gelir.)

`_figur_yaniti` içindeki yorumu şu olsun: `# Private: behind the sign-in. A day: the URL carries the corpus version, and an (id, version) pair's image never changes.`

`assistant_figure` fonksiyonunun gövdesini (erişim denetiminden sonraki her şey) şununla değiştir:

```python
    access = _require_assistant_access()
    if access is not None:
        return access

    # The URL names the corpus build it was cited under (?v=). Without it, or
    # under another build, the id may name a different picture: say so rather
    # than serve it. Missing needs no lookup; a mismatch needs the current one.
    istenen = request.args.get("v", "").strip()
    if not istenen:
        return jsonify({"error": FIGUR_SURUM_DEGISTI}), 404
    try:
        registry = _assistant_runtime().registry
        guncel = registry.korpus_surumu()
    except AssistantUnavailableError:
        registry, guncel = None, None
    except Exception as exc:  # noqa: BLE001 — a figure the panel cannot load is not a 500
        app.logger.error("assistant figure %s version failed: %s", figure_id, type(exc).__name__)
        registry, guncel = None, None
    if guncel is None:
        return jsonify({"error": FIGUR_ULASILAMADI}), 502
    if istenen != guncel:
        return jsonify({"error": FIGUR_SURUM_DEGISTI}), 404

    anahtar = (guncel, figure_id)
    with _FIGUR_KILIDI:
        kayit = _FIGUR_ONBELLEGI.get(anahtar)
        if kayit is not None:
            _FIGUR_ONBELLEGI.move_to_end(anahtar)
    if kayit is not None:
        return _figur_yaniti(*kayit)

    try:
        durum, veri, mime = registry.figur_gorseli(figure_id)
    except Exception as exc:  # noqa: BLE001 — a figure the panel cannot load is not a 500
        app.logger.error("assistant figure %s failed: %s", figure_id, type(exc).__name__)
        durum, veri, mime = "ulasilamadi", b"", ""

    if durum == "yok":
        return jsonify({"error": "Bu görsel müfredat korpusunda bulunamadı."}), 404
    if durum != "var":
        return jsonify({"error": FIGUR_ULASILAMADI}), 502

    if len(veri) <= FIGUR_TEK_SINIRI:
        with _FIGUR_KILIDI:
            _FIGUR_ONBELLEGI[anahtar] = (veri, mime)
            _FIGUR_ONBELLEGI.move_to_end(anahtar)
            while (len(_FIGUR_ONBELLEGI) > FIGUR_ONBELLEK_BOYUTU
                   or sum(len(v) for v, _ in _FIGUR_ONBELLEGI.values()) > FIGUR_TOPLAM_SINIRI):
                _FIGUR_ONBELLEGI.popitem(last=False)
    return _figur_yaniti(veri, mime)
```

- [ ] **Step 5: Testlerin geçtiğini gör**

Run: `DASHBOARD_SECRET_KEY=yerel-test-anahtari-pano-eksiklikleri .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_assistant_gorseller.py tests/test_assistant_tools.py tests/test_assistant_api.py`
Expected: hepsi PASS.

- [ ] **Step 6: Tam paket (ağsız)**

Run: `DASHBOARD_SECRET_KEY=yerel-test-anahtari-pano-eksiklikleri unshare -rn .venv/bin/python -m pytest -q -p no:cacheprovider 2>&1 | tail -15`
Expected: önceden kırmızılar dışında kırmızı yok (ağsız koşu, hiçbir testin maarif'e gitmediğini de kanıtlar).

- [ ] **Step 7: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-tam-baglam
git branch --show-current   # fix/pano-eksiklikleri
git add src/assistant_tools.py src/dashboard_api.py tests/test_assistant_gorseller.py
git commit -m "$(cat <<'EOF'
Figür ucu korpus sürümünü denetlesin

figur_getir atfı maarif server_info'dan okunan corpus_version'ı taşır
(süreç içinde 300 sn). /api/assistant/figure/<id> v yoksa ya da güncel
sürüm değilse Türkçe cümleyle 404 döner; LRU (sürüm, id) ile anahtarlı.
1.6 yapımı figür kimliklerini yeniden numaralandırmıştı.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Görev 7: Kaynaklar paneli figür adresini sürümle kurar; CLAUDE.md figür notu

**Files:**
- Modify: `dashboard/src/types.ts:207-213` (`FigureLocator`)
- Modify: `dashboard/src/components/SourcePanel.tsx:47-72` (`figureOf`, `FigureThumb`)
- Modify: `dashboard/tests/e2e/asistan-gorsel-kaynak.spec.ts`
- Modify: `CLAUDE.md:187-188`

**Interfaces:**
- Consumes: Görev 6'nın `locator.corpus_version: string` alanı ve uç noktanın `?v=` sözleşmesi.
- Produces: `FigureLocator.corpus_version?: string`; `figureSrc(figure: FigureLocator): string` (SourcePanel içi).

- [ ] **Step 1: e2e spec'i yeni sözleşmeye göre değiştir (başarısız olacak)**

`dashboard/tests/e2e/asistan-gorsel-kaynak.spec.ts`:

1. `FIGURE_CITATION.locator` → `{ tool: 'figur_getir', server: 'maarif-mufredat', args: { figure_id: 1875 }, figure_id: 1875, caption: CAPTION, corpus_version: '1.6' }`
2. `UNCAPTIONED.locator` → `{ tool: 'figur_getir', figure_id: 1876, corpus_version: '1.6' }`
3. `BROKEN.locator` → `{ tool: 'figur_getir', figure_id: 1877, caption: 'Kırık görsel', corpus_version: '1.6' }`
4. `mockFigures` gövdesi:

```ts
  await page.route('**/api/assistant/figure/**', route => {
    const url = new URL(route.request().url())
    requested.push(url.pathname + url.search)
    if (url.pathname.endsWith('/1877')) {
      return route.fulfill({ status: 502, contentType: 'application/json',
        body: JSON.stringify({ error: 'Ders kitabı görseline şu an ulaşılamadı; biraz sonra yeniden deneyin.' }) })
    }
    return route.fulfill({ status: 200, contentType: 'image/png', body: PNG })
  })
```

5. İlk testte `toHaveAttribute('src', '/api/assistant/figure/1875')` → `toHaveAttribute('src', '/api/assistant/figure/1875?v=1.6')`; son beklenti:

```ts
  expect(requested.sort()).toEqual([
    '/api/assistant/figure/1875?v=1.6', '/api/assistant/figure/1876?v=1.6', '/api/assistant/figure/1877?v=1.6'])
```

6. Dosyanın sonuna yeni test:

```ts
// 2026-09-28: a figure id means a picture only together with the corpus build it was cited
// under (the 1.6 build renumbered them), so the URL carries it. A citation from before the
// version existed asks without it; the server answers 404 and the panel says so in words.
test('the figure URL carries the corpus version, encoded; a citation without one asks without it', async ({ page }) => {
  const requested = await mockFigures(page)
  const ODD = { ...FIGURE_CITATION, id: 'S1', label: 'Garip sürüm',
    locator: { tool: 'figur_getir', figure_id: 1879, corpus_version: '1.6/x' }, snippet: '' }
  const NONE = { ...FIGURE_CITATION, id: 'S2', label: 'Sürümsüz',
    locator: { tool: 'figur_getir', figure_id: 1878 }, snippet: '' }
  await page.route('**/api/assistant/stream', route => route.abort())
  await page.route('**/api/assistant/chat', route => route.fulfill(json(answer(
    [ODD, NONE], 'Birinci [S1], ikinci [S2].'))))

  await ask(page, 'iki görsel göster')
  const items = page.locator('.ac__ref-group--kitap .ac__ref-item')
  await expect(items).toHaveCount(2)
  await expect(items.nth(0).locator('img.ac__ref-figure'))
    .toHaveAttribute('src', '/api/assistant/figure/1879?v=1.6%2Fx')
  await expect(items.nth(1).locator('img.ac__ref-figure'))
    .toHaveAttribute('src', '/api/assistant/figure/1878')
  await expect.poll(() => requested.length).toBe(2)
})
```

- [ ] **Step 2: Derle ve başarısız olduğunu gör**

Run:
```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-tam-baglam/dashboard
npm run build; echo "build çıkış: $?"
DASHBOARD_SECRET_KEY=yerel-test-anahtari-pano-eksiklikleri TEDY_E2E_PORT=8296 npx playwright test asistan-gorsel-kaynak --reporter=line
```
Expected: build 0; ilk test ve yeni test FAIL (`src` `?v=` taşımıyor); axe testi PASS.

- [ ] **Step 3: Uygula**

`dashboard/src/types.ts`, `FigureLocator`:

```ts
/** The part of a `figur_getir` citation's locator the Kaynaklar panel reads: the image comes
 *  from `/api/assistant/figure/<figure_id>?v=<corpus_version>` and `caption` is its alt text.
 *  `corpus_version` is the curriculum build the id belongs to; the endpoint refuses any other. */
export interface FigureLocator {
  figure_id: number
  caption?: string
  corpus_version?: string
}
```

`dashboard/src/components/SourcePanel.tsx`, `figureOf` ve `FigureThumb`:

```tsx
/** The figure part of a locator, or null. The value arrives as unchecked JSON, and it becomes a
 *  URL path segment — so only a positive integer id is accepted. The corpus version is a query
 *  value, encoded where the URL is built. */
function figureOf(locator: Record<string, unknown> | undefined): FigureLocator | null {
  const id = locator?.figure_id
  if (typeof id !== 'number' || !Number.isInteger(id) || id <= 0) return null
  const caption = typeof locator?.caption === 'string' ? locator.caption.trim() : ''
  const version = typeof locator?.corpus_version === 'string' ? locator.corpus_version.trim() : ''
  return {
    figure_id: id,
    ...(caption ? { caption } : {}),
    ...(version ? { corpus_version: version } : {}),
  }
}

/** The figure's URL under the corpus build it was cited in. The 1.6 build renumbered figure ids
 *  (2026-09-27), so an id alone can name another picture; without a version the endpoint answers
 *  404 and the thumbnail says "Görsel yüklenemedi". */
function figureSrc(figure: FigureLocator): string {
  const base = `/api/assistant/figure/${figure.figure_id}`
  return figure.corpus_version ? `${base}?v=${encodeURIComponent(figure.corpus_version)}` : base
}
```

`FigureThumb` içinde `src={`/api/assistant/figure/${figure.figure_id}`}` → `src={figureSrc(figure)}`.

`CitationChip.tsx` değişmez: figür adresi kurmuyor (planlamada doğrulandı; `grep -n "figure" dashboard/src/components/CitationChip.tsx` boş).

- [ ] **Step 4: Lint, derleme, e2e**

Run:
```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-tam-baglam/dashboard
npm run lint; echo "lint çıkış: $?"
npm run build; echo "build çıkış: $?"
DASHBOARD_SECRET_KEY=yerel-test-anahtari-pano-eksiklikleri TEDY_E2E_PORT=8296 npx playwright test asistan-gorsel-kaynak asistan-cevap-bicimi assistant-chat --reporter=line
```
Expected: lint 0, build 0, hepsi PASS.

- [ ] **Step 5: CLAUDE.md figür notu**

"Asistan ve müfredat (maarif MCP)" maddesindeki şu cümleyi:

```
**The 1.6 build renumbered document, figure and video ids**: a figure id or `document_id` from before 2026-09-27 (an old chat's citation, a browser-cached `/api/assistant/figure/<id>`, which is served with `max-age=86400`) now names a different item; the dashboard was restarted in the swap window to empty its figure LRU.
```

şununla değiştir:

```
**The 1.6 build renumbered document, figure and video ids**, so an id means an item only together with the corpus build. Since 2026-09-28 a figure is versioned end to end: `figur_getir`'s citation carries `locator.corpus_version` (maarif `server_info`, read by `McpRegistry.korpus_surumu()` and trusted for `KORPUS_SURUMU_TTL` = 300 s per process; a failed read is not cached), `SourcePanel` asks for `/api/assistant/figure/<id>?v=<corpus_version>`, and the endpoint answers 404 "Bu görsel, müfredat korpusu güncellendiği için değişti; soruyu yeniden sorun." when `v` is missing or is not the current build — so a corpus swap needs no dashboard restart, and the day-long browser cache is safe because the build is in the URL. A `document_id` or video id from before 2026-09-27 in an old chat still names a different item; only figures carry the version.
```

"Asistan ve ders kitabı görselleri" maddesindeki şu parçayı:

```
`GET /api/assistant/figure/<id>` (`require_auth` + `_require_assistant_access`, id bounded `1..2147483647`) proxies the bytes through a 64-entry in-process LRU capped at 16 MiB total
```

şununla değiştir:

```
`GET /api/assistant/figure/<id>?v=<corpus_version>` (`require_auth` + `_require_assistant_access`, id bounded `1..2147483647`; `v` checked before anything else — missing or stale is the 404 above, an unreadable current version the 502 below) proxies the bytes through a 64-entry in-process LRU keyed by `(corpus version, id)` and capped at 16 MiB total
```

- [ ] **Step 6: Tam Python paketi (CLAUDE.md'ye bağlı testler için)**

Run: `DASHBOARD_SECRET_KEY=yerel-test-anahtari-pano-eksiklikleri .venv/bin/python -m pytest -q -p no:cacheprovider 2>&1 | tail -15`
Expected: önceden kırmızılar dışında kırmızı yok.

- [ ] **Step 7: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-tam-baglam
git branch --show-current   # fix/pano-eksiklikleri
git add dashboard/src/types.ts dashboard/src/components/SourcePanel.tsx \
  dashboard/tests/e2e/asistan-gorsel-kaynak.spec.ts CLAUDE.md
git commit -m "$(cat <<'EOF'
Kaynaklar paneli figür adresini korpus sürümüyle kursun

SourcePanel /api/assistant/figure/<id>?v=<corpus_version> ister; sürümü
olmayan eski atıf v'siz kalır ve "Görsel yüklenemedi" der. CLAUDE.md'deki
2026-09-27 figür kimliği uyarısı yeni davranışla değişti.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

## Bitiş (controller)

Görevler bittikten sonra, planın görevi olmayan ayrı adım: tam doğrulama (`.venv/bin/python -m pytest -q -p no:cacheprovider`; `cd dashboard && npm run lint && npm run build && DASHBOARD_SECRET_KEY=yerel-test-anahtari-pano-eksiklikleri TEDY_E2E_PORT=8296 npx playwright test`), ardından dağıtım — main'i ff, push, `npm run build`, `systemctl --user restart ted-dashboard`. Dağıtımdan sonra `/takvim`'de bu haftanın dersleri ve cumartesi sütunu, `/api/exams`'de `relatedContent` ve geçmiş sınavlarda 2025-2026 sentetik satırlarının yokluğu, asistanda bir figür atfının `?v=1.6` ile yüklendiği canlıda gözle doğrulanır.
