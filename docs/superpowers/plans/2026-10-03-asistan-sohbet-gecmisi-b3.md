# Asistan sohbet geçmişi — B3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** TEDY Asistanı sohbeti `output/assistant_sohbetler.sqlite` içinde tutar; istemci `sohbet_id` ve yeni mesajı gönderir; sunucu son 20 mesajı yükler; 20'yi aşan eski turları Haiku 4.5 `sohbet.ozet`'e yazar; aile Işık'ın sohbetini ve ekinin önizlemesini salt okur; sohbet silinince ekleri de silinir.

**Architecture:** `src/assistant_sohbet.py` Flask'a import etmez. Bağlantı işlem başına açılır ve kapanır (WAL, `busy_timeout` 5000). `/stream` ve `/chat` sohbet satırını `generate()` kurulmadan önce yazar; cevap satırı yalnız tamamlanmış `answer` olayından sonra yazılır. Dosya baytları B2'nin `_ekleri_hazirla` çıktısıdır; son 20'ye giren eski ekler de B2'nin 10 tavanına girer. `bagli_sohbet` bu planda dolar. `AssistantRuntime` bu dosyayı kurmaz. `sohbet_id` yoksa dosya açılmaz. `/v1`, `/plan` ve API anahtarı bu dosyaya dokunmaz.

**Tech Stack:** Python 3.12 (stdlib `sqlite3`, Flask), mevcut `EkDeposu` (B2 planı `docs/superpowers/plans/2026-10-03-asistan-dosya-yukleme-b2.md`), React 19 + Carbon, Playwright + `@axe-core/playwright` + IBM Equal Access.

**Spec:** `docs/superpowers/specs/2026-09-28-asistan-ogretmen-modlari-design.md` — **§3**, "Hata ve boşluk durumları" ile "Test"in B3'e düşen maddeleri, §2'deki "B3 kuralıyla aile" cümlesi, ve ekteki "B3'e eklenenler"in üçü (özet yazımı, kaynak seçimi, hassas notun kod denetimi). Sayı yazılmamış olması bu üçüne görevi düşürmez. B4, B5, B6 yok. B2 plan dosyası değiştirilmez.

Bu worktree'nin kodu `c2ff982` üzerindedir: `assistant_uploads.py` henüz yok. Görevler B2 planının adlandırdığı sembolleri tüketir (`EkDeposu`, `_ekleri_hazirla`, `messages[-3:]` varsayılanı, `sohbet_eklerini_sil`). B2 uygulanmadan B3 uygulanmaz.

## Global Constraints

- **Worktree:** `/mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-b2-plan`, dal `cursor/asistan-b2-plan-a843`. Ana checkout'a, `feat/asistan-ogretmen` worktree'sine, `feat/asistan-zengin`'e ve portal dallarına dokunma. `docs/superpowers/plans/2026-10-03-asistan-dosya-yukleme-b2.md` bu planda değişmez.
- **Git:** dosyaları adıyla stage et. `git add -A` / `git add .` yok. Push yok.
- **Testler ücretli bir API'ye ya da ağa hiç gitmez.** `tests/conftest.py` `ANTHROPIC_API_KEY`'i siler. Playwright: `TEDY_E2E_PYTHON=/mnt/thunderbolt/workspaces/TED/.venv/bin/python DASHBOARD_SECRET_KEY=yalniz-test env -u ANTHROPIC_API_KEY npx playwright test <spec>`. Soru gönderen her e2e hem `**/api/assistant/stream` hem `**/api/assistant/chat` rotasını kendisi cevaplar.
- **Python:** yorumlayıcı `/mnt/thunderbolt/workspaces/TED/.venv/bin/python`. `DASHBOARD_SECRET_KEY=yalniz-test`. Gerçek `.env` bağlama. Yeni bağımlılık yok. `sqlite3` stdlib.
- **Pano:** `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-b2-plan/dashboard`. `node_modules` yoksa `npm ci`. Playwright'dan önce `npm run build`.
- **Renk:** elle hex yok, alfa yok, gradyan yok, `color-mix` yok. Yalnız mevcut `--cds-*` ve `--ted-*`.
- **Dil:** okura giden her yeni cümle Türkçe. Yol, istisna adı ve e-posta okura gitmez.
- **Temel sistem bloğu her modda bayt bayt aynı kalır.** Yeni cümle temel isteme girer.
- **Dağıtım bir plan görevi değildir.**
- **`sohbet_id` yoksa depo yok.** Bugünkü öğretmen testleri `sohbet_id` göndermez; 200 kalır ve sqlite dosyası açılmaz.

## Açık kararlar

Ek, sayı vermediği üç maddeyi de B3'e koyar. Özet yazımı, kaynak seçimi ve hassas notun kod denetimi açık karar değildir; aşağıdaki kilitler ve görev 4 onları yazar. Işık'ın not paneli (yalnız `okur_turu == "aile"`, öğrenci 403) ve `/plan`'ın depoyu açmaması da açık karar değildir.

Bilinçli olarak görev dışı kalanlar:

5. **Boş başlık sözcüğü.** İlk soru gelene kadar `baslik` boş kalır. Okur cümlesi yok. Liste `baslik` boş satırı döndürmez. "Yeni sohbet" düğmesinin adı satıra yazılmaz.
7. **Yeniden üret / Daha derine in.** §3'te yok. B2 onları `ekler` dışında bırakır. Bu plan `sohbet_id` de göndermez; satır yazılmaz.

## Kilitlenen adlar

| Ad | Değer | Neden |
|---|---|---|
| Dosya | `output/assistant_sohbetler.sqlite` | Spec yolu. `OUTPUT_DIR` altında. |
| Bağlantı | İşlem başına `sqlite3.connect`, `isolation_level=None`, bitince `close`. `PRAGMA journal_mode=WAL`. `PRAGMA busy_timeout=5000` | Spec: WAL, işlem başına bağlantı, iki gunicorn işçisi. 5000, `src/mcp_server/oauth_store.py` `BUSY_TIMEOUT_MS`. |
| `sohbet` | `id, sahip_email, baslik, ogretmen, olusturma, guncelleme, ozet` | §3 kolonları + ekteki `sohbet.ozet`. `ozet` NULL başlar; 20 mesajı aşınca ürün yazar. |
| `mesaj` | `id, sohbet_id, rol, icerik, atiflar_json, ekler_json, meta_json, ogretmen, zaman, sira` | §3. `meta_json` B3'te `{}`. `sira` ekleme sırasıdır. |
| `ogrenci_notu` | `id, metin, kaynak_sohbet, zaman` | Ek: kısa not, kaynak sohbet, tarih. Tür kolonu yok. |
| Kimlik | `uuid.uuid4().hex`, `^[0-9a-f]{32}$` | B2 ek kimliği ile aynı biçim. `bagli_sohbet` bu dizgiyi tutar. |
| Zaman | UTC `YYYY-MM-DDTHH:MM:SSZ` | B2 `_zaman`. |
| Sıra | `guncelleme DESC, id ASC` | Liste. Spec sıra yazmaz; kolon güncelleme zamanıdır. |
| `sira` | `INTEGER NOT NULL`. Aynı `BEGIN IMMEDIATE` içinde `(SELECT COALESCE(MAX(sira), 0) + 1 FROM mesaj)` | Aynı saniyedeki kullanıcı satırı ile cevabı ekleme sırasını tutar. `id` rastgele uuid'dir; eşitlik anahtarı değildir. |
| Son 20 | `ORDER BY zaman DESC, sira DESC LIMIT n`, sonra çevrilir. `tum_mesajlar` `ORDER BY zaman ASC, sira ASC` | Testler tek `SIMDI` dondurur ve bu sırayı bekler. `id` sıralamaya girmez. |
| Pencere | `_build_conversation(..., pencere: int = 3)`. Depodan gelen çağrı `pencere=20` | Bugün `messages[-3:]` (`assistant_core.py`). B2 varsayılanı 3 kalır. Spec'in 20'si depo yoluna aittir. |
| `sohbet_id` | İstek alanı. Varken istemcinin eski mesajları yok sayılır; son kullanıcı mesajı yeni turdur | Spec: istemci yalnız kimlik + yeni mesaj. Sahte geçmiş içeri girmez. |
| Başlık | İlk kullanıcı metninin `split()` ile birleştirilmiş hali, yalnız `baslik` boşken | "İlk sorudan türetilir, ek model çağrısı yok." Kesme sayısı yok; kesilmez. |
| Aile eki | `okur_turu(email) == "aile"` ise `oku` Işık'ın adresine (`OGRENCI_EMAILS`) düşer | §2 "B3 kuralıyla". Kural: aile Işık'ı okur. Başka ebeveynin dosyası 404. Bağsız dosya da okunur; spec bağ şartı koymaz. |
| Sohbet okuma | Sahip okur. Aile Işık'ın satırını okur (`?kisi=ogrenci` ve `GET /<id>`). Işık bir ebeveynin satırını okumaz. Bir ebeveyn diğerinin satırını okumaz. İkisi de yok olan id ile aynı 404 | Spec'in okuma listesi budur: kendi sohbeti, ve aile için Işık. |
| Not bloğu | Her depolu istekte sarmalayıcı kullanıcı turuna, sistem istemine değil | Ek: önbelleği bozmadan. Sistem bloğu keşli. Blok saklanmaz; 20 turdan düşmez. |
| Sohbet öğretmeni | `mesaj_ekle` `sohbet.ogretmen` yazmaz. Mesaj satırı kendi `ogretmen`'ini tutar. Açılan sohbet `useOgretmen`'i `sohbet.ogretmen` ile kurar | Seçici, `tedy-asistan-ogretmen::<email>` değerinin önüne geçer. Öğretmeni değiştiren yol `PATCH`'tir. |
| İstek başına 10 ek | B2'nin `ISTEK_SINIRI`. Yeni mesajın `ekler`'i ile `son_mesajlar(sid, 19)` içindeki eski kimlikler toplanır. Toplam 10'u aşarsa `mesaj_ekle`'den önce 400 | `_ekleri_hazirla` yalnız yeni mesaja bakar. Yanına konan eski ekler aynı tavana girer. Pencerenin dışında kalacak ek sayılmaz. Aynı kimlik iki kez yazıldıysa iki sayılır. İkinci sabit yok. Cümle B2'nindir: `Bir istekte en fazla 10 dosya olabilir.` |
| Özet yazımı | Cevap satırı yazıldıktan sonra, `tum_mesajlar` 20'yi aştıysa eski turlar `claude-haiku-4-5` ile özetlenir ve `ozet_yaz` kolonu yazar. Mesaj satırı silinmez | Ek eşik sayısı vermez. Eşik, kilitli pencere 20'dir. Ayrı token sayacı yok. `ClaudeClient.DEFAULT_MODEL` (`claude-sonnet-5`) değişmez. Çağrı enjekte edilir; test ağa gitmez. Hata özeti olduğu gibi bırakır, cevap satırını silmez. |
| Kaynak seçimi | Aynı parça ikinci kez konmaz. Pay, bugünkü `TOOL_RESULT_SINIRI` (4000). 20'nin dışındaki araç gövdesi modele açılmaz; yerine `ozet` gider. `_sorguya` ek model çağrısı yapmaz | Ek pay sayısı vermez. Yeni karakter tavanı yok. |
| Hassas not | `hassas_not` yazmadan önce bakar. İstem cümlesi tek başına yetmez | Sözcük listesi spec'te yok. Kilit görev 4'ün token listesidir; ödev cümlesini kesmez. |
| Depo kim açar | Yalnız `sohbet_id` taşıyan `/stream` ve `/chat` | `AssistantRuntime.__init__` açmaz. `hafiza=True` varsayılanı dosya açmaz. `not_deposu` view'dan gelir; None ise `notlar()` çağrılmaz. `/plan` ve `/v1` `SohbetDeposu` kurmaz. |
| Silme sırası | Önce `EkDeposu.sohbet_eklerini_sil`, sonra tek transaction'da mesaj + sohbet | Bağlı dosyayı 30 gün temizliği silmez (`bagli_sohbet is not None`). Dosya önce giderse tekrar silme tamamlar. |

Okur cümleleri:

| Durum | HTTP | Metin |
|---|---|---|
| Sohbet yok ya da başkasının | 404 | `Sohbet bulunamadı.` |
| Aile yazması, silmesi, yeniden adlandırması | 403 | `Bu sohbet salt okunur.` |
| `kisi` ogrenci değil | 400 | `Bilinmeyen kişi.` |
| Boş yeni mesaj | 400 | `Mesaj boş olamaz.` |
| PATCH boş başlık | 400 | `Başlık boş olamaz.` |
| Depo hatası | 500 | `Sohbet kaydedilemedi.` |
| Not yok | 404 | `Not bulunamadı.` |
| Öğrenci not ucu | 403 | `Bu notları yalnız aile düzenler.` |
| Hassas not | 400; araçta `ok` False | `Bu not yazılmadı.` |
| Boş liste | — | `Henüz sohbet yok — bir soru sorarak başla` |
| Işık'ın notu | — | `Sohbetlerini ailen de görebilir.` |
| Aile bölümü | — | `Işık'ın sohbetleri` |
| Liste | — | `Sohbetler` |
| Düğme | — | `Yeni sohbet` |
| Not paneli | — | `Asistanın notları` |
| Liste yüklenemedi | — | `Sohbetler yüklenemedi.` |

Bilinmeyen öğretmen B1 cümlesidir: `Bilinmeyen öğretmen modu.`

## File Structure

| Dosya | Durum | Sorumluluk |
|---|---|---|
| `src/assistant_sohbet.py` | yeni | Şema, `sira`, sohbet, mesaj, not, `hassas_not`, `ozet_yaz` |
| `tests/test_assistant_sohbet.py` | yeni | WAL, iki yazıcı, son 20, aynı saniye, öğretmen ezilmez |
| `src/dashboard_api.py` | değişir | Uçlar; akışta kayıt; eski eklerin tavanı; aile ek okuması |
| `src/assistant_uploads.py` | değişir | `EkDeposu.bagla` (B2 dosyası) |
| `src/assistant_core.py` | değişir | `pencere`, özet yazma ve okuma, not bloğu, parça elemesi |
| `src/assistant_tools.py` | değişir | `hafiza_yaz`, `hafiza_duzelt`, `_sorguya` |
| `tests/test_assistant_sohbet_api.py` | yeni | Sahiplik, aile, akış, `/v1` |
| `tests/test_assistant_uploads_api.py` | değişir | B2'nin "başkası 404" testi aile kuralına göre |
| `dashboard/src/components/AssistantChat.tsx` / `.scss` | değişir | Liste, not, salt okuma |
| `dashboard/tests/e2e/asistan-sohbet.spec.ts` | yeni | Liste, aile, Işık notu, axe, IBM |
| `CLAUDE.md` | değişir | B3 maddesi |

---

### Task 1: Depo

**Files:**
- Create: `src/assistant_sohbet.py`
- Test: `tests/test_assistant_sohbet.py`

**Interfaces:**
- Consumes: yok.
- Produces: `SohbetDeposu(yol: Path)`. Metotlar aşağıda. Saat enjekte edilir (`simdi: datetime`).

- [ ] **Step 1: Test**

`tests/test_assistant_sohbet.py`:

```python
"""Sohbet deposu (spec §3). Ağ yok."""
import threading
from datetime import datetime, timezone

import pytest

from src.assistant_sohbet import SohbetDeposu

ISIK = "isikkurtx@gmail.com"
SIMDI = datetime(2026, 10, 3, 8, 0, tzinfo=timezone.utc)


def test_wal_ve_bos_liste(tmp_path):
    depo = SohbetDeposu(tmp_path / "assistant_sohbetler.sqlite")
    assert depo.journal_mode() == "wal"
    assert depo.liste(ISIK) == []


def test_son_yirmi_yeniyi_tutar(tmp_path):
    depo = SohbetDeposu(tmp_path / "assistant_sohbetler.sqlite")
    sid = depo.yarat(ISIK, "genel", SIMDI)
    for i in range(25):
        depo.mesaj_ekle(sid, "user", f"m{i}", "genel", [], SIMDI)
    son = depo.son_mesajlar(sid, 20)
    assert [m["icerik"] for m in son] == [f"m{i}" for i in range(5, 25)]
    assert depo.tum_mesajlar(sid)[0]["icerik"] == "m0"


def test_ayni_saniye_soru_cevap_sirasi(tmp_path):
    depo = SohbetDeposu(tmp_path / "assistant_sohbetler.sqlite")
    sid = depo.yarat(ISIK, "matematik", SIMDI)
    depo.mesaj_ekle(sid, "user", "soru", "matematik", [], SIMDI)
    depo.mesaj_ekle(sid, "assistant", "cevap", "matematik", [], SIMDI)
    assert [m["rol"] for m in depo.son_mesajlar(sid, 20)] == ["user", "assistant"]
    assert [m["rol"] for m in depo.tum_mesajlar(sid)] == ["user", "assistant"]


def test_mesaj_ogretmeni_satiri_ezmez(tmp_path):
    depo = SohbetDeposu(tmp_path / "assistant_sohbetler.sqlite")
    sid = depo.yarat(ISIK, "matematik", SIMDI)
    depo.mesaj_ekle(sid, "user", "soru", "fen", [], SIMDI)
    assert depo.getir(sid)["ogretmen"] == "matematik"
    assert depo.tum_mesajlar(sid)[0]["ogretmen"] == "fen"


def test_iki_yazici(tmp_path):
    yol = tmp_path / "assistant_sohbetler.sqlite"
    depo = SohbetDeposu(yol)
    sid = depo.yarat(ISIK, "genel", SIMDI)
    bariyer = threading.Barrier(2)
    hatalar = []

    def yaz(on):
        try:
            bariyer.wait()
            yerel = SohbetDeposu(yol)
            for i in range(20):
                yerel.mesaj_ekle(sid, "user", f"{on}-{i}", "genel", [], SIMDI)
        except Exception as exc:  # noqa: BLE001 — the assertion is the message
            hatalar.append(exc)

    iplikler = [threading.Thread(target=yaz, args=(n,)) for n in ("a", "b")]
    for t in iplikler:
        t.start()
    for t in iplikler:
        t.join()
    assert hatalar == []
    assert len(SohbetDeposu(yol).tum_mesajlar(sid)) == 40
```

- [ ] **Step 2: FAIL**

`cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-b2-plan && DASHBOARD_SECRET_KEY=yalniz-test /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest tests/test_assistant_sohbet.py -q -p no:cacheprovider`

Expected: FAIL, `ModuleNotFoundError`.

- [ ] **Step 3: Uygula**

`src/assistant_sohbet.py`. Yazma `BEGIN IMMEDIATE`. Okuma da kendi bağlantısında. `journal_mode()` bir bağlantı açar, `PRAGMA journal_mode` okur, kapatır.

```python
"""Assistant chats (spec §3). No Flask."""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

_SEM = """
CREATE TABLE IF NOT EXISTS sohbet (
    id TEXT PRIMARY KEY,
    sahip_email TEXT NOT NULL,
    baslik TEXT NOT NULL DEFAULT '',
    ogretmen TEXT NOT NULL,
    olusturma TEXT NOT NULL,
    guncelleme TEXT NOT NULL,
    ozet TEXT
);
CREATE TABLE IF NOT EXISTS mesaj (
    id TEXT PRIMARY KEY,
    sohbet_id TEXT NOT NULL,
    rol TEXT NOT NULL,
    icerik TEXT NOT NULL,
    atiflar_json TEXT NOT NULL DEFAULT '[]',
    ekler_json TEXT NOT NULL DEFAULT '[]',
    meta_json TEXT NOT NULL DEFAULT '{}',
    ogretmen TEXT NOT NULL,
    zaman TEXT NOT NULL,
    sira INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS mesaj_sohbet_sira ON mesaj(sohbet_id, sira);
CREATE TABLE IF NOT EXISTS ogrenci_notu (
    id TEXT PRIMARY KEY,
    metin TEXT NOT NULL,
    kaynak_sohbet TEXT,
    zaman TEXT NOT NULL
);
"""


def zaman_yazi(an: datetime) -> str:
    if an.tzinfo is None:
        an = an.replace(tzinfo=timezone.utc)
    return an.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class SohbetDeposu:
    def __init__(self, yol: Path):
        self.yol = Path(yol)
        self.yol.parent.mkdir(parents=True, exist_ok=True)
        with self._baglan() as conn:
            conn.executescript(_SEM)

    @contextmanager
    def _baglan(self):
        conn = sqlite3.connect(self.yol, timeout=5, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        try:
            yield conn
        finally:
            conn.close()

    def journal_mode(self) -> str:
        with self._baglan() as conn:
            return conn.execute("PRAGMA journal_mode").fetchone()[0]

    def yarat(self, email: str, ogretmen: str, simdi: datetime) -> str:
        sid = uuid.uuid4().hex
        yazi = zaman_yazi(simdi)
        with self._baglan() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    "INSERT INTO sohbet (id, sahip_email, baslik, ogretmen, olusturma, guncelleme, ozet) "
                    "VALUES (?, ?, '', ?, ?, ?, NULL)",
                    (sid, email, ogretmen, yazi, yazi),
                )
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
        return sid

    def getir(self, sid: str) -> dict | None:
        with self._baglan() as conn:
            row = conn.execute("SELECT * FROM sohbet WHERE id = ?", (sid,)).fetchone()
        return dict(row) if row else None

    def liste(self, email: str) -> list[dict]:
        with self._baglan() as conn:
            rows = conn.execute(
                "SELECT id, baslik, ogretmen, olusturma, guncelleme FROM sohbet "
                "WHERE sahip_email = ? AND baslik <> '' ORDER BY guncelleme DESC, id ASC",
                (email,),
            ).fetchall()
        return [dict(r) for r in rows]

    def mesaj_ekle(self, sid: str, rol: str, icerik: str, ogretmen: str,
                   ekler: list, simdi: datetime, atiflar: list | None = None) -> str:
        mid = uuid.uuid4().hex
        yazi = zaman_yazi(simdi)
        with self._baglan() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    "INSERT INTO mesaj (id, sohbet_id, rol, icerik, atiflar_json, ekler_json, "
                    "meta_json, ogretmen, zaman, sira) VALUES (?, ?, ?, ?, ?, ?, '{}', ?, ?, "
                    "(SELECT COALESCE(MAX(sira), 0) + 1 FROM mesaj))",
                    (mid, sid, rol, icerik, json.dumps(atiflar or [], ensure_ascii=False),
                     json.dumps(ekler, ensure_ascii=False), ogretmen, yazi),
                )
                row = conn.execute("SELECT baslik FROM sohbet WHERE id = ?", (sid,)).fetchone()
                baslik = row["baslik"] if row else ""
                if rol == "user" and not baslik.strip():
                    baslik = " ".join(icerik.split())
                conn.execute(
                    "UPDATE sohbet SET guncelleme = ?, baslik = ? WHERE id = ?",
                    (yazi, baslik, sid),
                )
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
        return mid

    def son_mesajlar(self, sid: str, n: int) -> list[dict]:
        with self._baglan() as conn:
            rows = conn.execute(
                "SELECT * FROM mesaj WHERE sohbet_id = ? ORDER BY zaman DESC, sira DESC LIMIT ?",
                (sid, n),
            ).fetchall()
        return [dict(r) for r in reversed(rows)]

    def tum_mesajlar(self, sid: str) -> list[dict]:
        with self._baglan() as conn:
            rows = conn.execute(
                "SELECT * FROM mesaj WHERE sohbet_id = ? ORDER BY zaman ASC, sira ASC",
                (sid,),
            ).fetchall()
        return [dict(r) for r in rows]

    def guncelle(self, sid: str, baslik: str | None, ogretmen: str | None, simdi: datetime) -> None:
        parca, deger = [], []
        if baslik is not None:
            parca.append("baslik = ?")
            deger.append(baslik)
        if ogretmen is not None:
            parca.append("ogretmen = ?")
            deger.append(ogretmen)
        parca.append("guncelleme = ?")
        deger.append(zaman_yazi(simdi))
        deger.append(sid)
        with self._baglan() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(f"UPDATE sohbet SET {', '.join(parca)} WHERE id = ?", deger)
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise

    def sil(self, sid: str) -> None:
        with self._baglan() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute("DELETE FROM mesaj WHERE sohbet_id = ?", (sid,))
                conn.execute("DELETE FROM sohbet WHERE id = ?", (sid,))
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise

    def ozet_oku(self, sid: str) -> str | None:
        row = self.getir(sid)
        if row is None:
            return None
        return row["ozet"]

    def ozet_yaz(self, sid: str, ozet: str) -> None:
        """Ürün yolu. Yalnız `ozet` kolonunu yazar; mesaj silmez, `ogretmen` değiştirmez."""
        with self._baglan() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute("UPDATE sohbet SET ozet = ? WHERE id = ?", (ozet, sid))
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise

    def not_yaz(self, metin: str, kaynak: str | None, simdi: datetime) -> str:
        nid = uuid.uuid4().hex
        with self._baglan() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    "INSERT INTO ogrenci_notu (id, metin, kaynak_sohbet, zaman) VALUES (?, ?, ?, ?)",
                    (nid, metin, kaynak, zaman_yazi(simdi)),
                )
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
        return nid

    def not_duzelt(self, nid: str, metin: str) -> bool:
        with self._baglan() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                cur = conn.execute(
                    "UPDATE ogrenci_notu SET metin = ? WHERE id = ?", (metin, nid))
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
        return cur.rowcount == 1

    def not_sil(self, nid: str) -> bool:
        with self._baglan() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                cur = conn.execute("DELETE FROM ogrenci_notu WHERE id = ?", (nid,))
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
        return cur.rowcount == 1

    def notlar(self) -> list[dict]:
        with self._baglan() as conn:
            rows = conn.execute(
                "SELECT id, metin, kaynak_sohbet, zaman FROM ogrenci_notu ORDER BY zaman ASC, id ASC"
            ).fetchall()
        return [dict(r) for r in rows]
```

`_baglan` yukarıdaki bağlam yöneticisidir. `with` bitince bağlantı kapanır. `sqlite3.Connection` kendi bağlamı bağlantıyı kapatmaz; metot bağlantıyı döndürmez.

- [ ] **Step 4: PASS**

Aynı pytest. Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/assistant_sohbet.py tests/test_assistant_sohbet.py
git commit -m "feat: asistan sohbet deposunu ekle"
```

---

### Task 2: Sohbet uçları

**Files:**
- Modify: `src/dashboard_api.py` (routes immediately after `assistant_ogretmenler`, or after the B2 upload routes if those exist)
- Test: `tests/test_assistant_sohbet_api.py`

**Interfaces:**
- Consumes: `_require_assistant_access`, `_module_person`, `_istek_ogretmeni`, `okur_turu`, `OGRENCI_EMAILS`, `OUTPUT_DIR`, `SohbetDeposu`.
- Produces the routes below. JSON'da `sahip_email` yoktur.

- [ ] **Step 1: Test**

`ISIK = "isikkurtx@gmail.com"`, `AILE = "drmahirkurt@gmail.com"`, `OKUR = "murzogluhulya@gmail.com"`. Fixture B2'nin `tests/test_assistant_uploads_api.py` kalıbıdır: `TEST_AUTH_BYPASS=1`, `OUTPUT_DIR` tmp, `session user_email`. Depo yolu `Path(OUTPUT_DIR) / "assistant_sohbetler.sqlite"`. Saat `datetime(2026, 10, 3, 8, 0, tzinfo=timezone.utc)` — route `datetime.now` yerine bu sabiti kullanabilsin diye `dashboard_api._asistan_simdi` bir fonksiyon olsun ve test onu değiştirsin.

```python
def test_sahip_yazar_aile_okur_yazamaz(istemci):
    _giris(istemci, ISIK)
    yarat = istemci.post("/api/assistant/sohbetler", json={"ogretmen": "matematik"})
    assert yarat.status_code == 200
    sid = yarat.get_json()["id"]
    assert "sahip_email" not in yarat.get_json()
    mesaj = istemci.post("/api/assistant/sohbetler/" + sid + "/mesaj",
                         json={"icerik": "Payda eşitle", "ogretmen": "matematik"})
    assert mesaj.status_code == 200
    liste = istemci.get("/api/assistant/sohbetler").get_json()["sohbetler"]
    assert liste[0]["baslik"] == "Payda eşitle"
    _giris(istemci, AILE)
    assert istemci.get("/api/assistant/sohbetler").get_json()["sohbetler"] == []
    aile = istemci.get("/api/assistant/sohbetler?kisi=ogrenci")
    assert aile.status_code == 200
    assert aile.get_json()["sohbetler"][0]["id"] == sid
    oku = istemci.get("/api/assistant/sohbetler/" + sid)
    assert oku.status_code == 200
    assert "sahip_email" not in oku.get_json()["sohbet"]
    yaz = istemci.patch("/api/assistant/sohbetler/" + sid, json={"baslik": "X"})
    assert yaz.status_code == 403
    assert yaz.get_json()["error"] == "Bu sohbet salt okunur."
    assert istemci.delete("/api/assistant/sohbetler/" + sid).status_code == 403


def test_yabanci_ve_yok_ayni_404(istemci):
    _giris(istemci, AILE)
    sid = istemci.post("/api/assistant/sohbetler", json={}).get_json()["id"]
    _giris(istemci, "ozlem.murzoglu@gmail.com")
    diger = istemci.get("/api/assistant/sohbetler/" + sid)
    _giris(istemci, ISIK)
    yok = istemci.get("/api/assistant/sohbetler/" + "ab" * 16)
    yabanci = istemci.get("/api/assistant/sohbetler/" + sid)
    assert yok.status_code == yabanci.status_code == diger.status_code == 404
    assert yok.get_json() == yabanci.get_json() == diger.get_json() == {"error": "Sohbet bulunamadı."}


def test_okur_403(istemci, monkeypatch):
    monkeypatch.setattr(dashboard_api, "TEST_AUTH_BYPASS", False)
    _giris(istemci, OKUR)
    assert istemci.get("/api/assistant/sohbetler").status_code == 403


def test_bilinmeyen_kisi_400(istemci):
    _giris(istemci, AILE)
    res = istemci.get("/api/assistant/sohbetler?kisi=aile")
    assert res.status_code == 400
    assert res.get_json()["error"] == "Bilinmeyen kişi."
```

`?kisi=ogrenci` çağıran kişi öğrenci ise kendi listesini alır (aynı satırlar). Aile değilse ve öğrenci değilse 404 değil 403: `okur_turu` `bilinmiyor` ise `{"error": "session_required"}` 403. Bypass'ta e-posta yoksa da bu.

- [ ] **Step 2: FAIL**

Aynı pytest komutu `tests/test_assistant_sohbet_api.py`. Expected: FAIL, 404.

- [ ] **Step 3: Uçlar**

Yardımcı:

```python
def _sohbet_deposu():
    from pathlib import Path
    from src.assistant_sohbet import SohbetDeposu
    return SohbetDeposu(Path(OUTPUT_DIR) / "assistant_sohbetler.sqlite")


def _asistan_simdi():
    return datetime.now(timezone.utc)


def _sohbet_erisim(sid):
    """(row, sahip_mi, hata). Başkasının satırı ile yok aynı 404."""
    email = _module_person()
    if not email:
        return None, False, (jsonify({"error": "session_required"}), 403)
    row = _sohbet_deposu().getir(sid)
    if row is None or (
            row["sahip_email"] != email and not (
                okur_turu(email) == "aile" and row["sahip_email"] in OGRENCI_EMAILS)):
        return None, False, (jsonify({"error": "Sohbet bulunamadı."}), 404)
    return row, row["sahip_email"] == email, None
```

`GET /api/assistant/sohbetler`: `_require_assistant_access`. `kisi` yoksa `liste(email)`. `kisi=ogrenci` ise çağıran `aile` ya da `OGRENCI_EMAILS` içindeyse `liste(Işık adresi)`; Işık adresi `next(iter(OGRENCI_EMAILS))`. Başka `kisi` 400. E-posta yok 403 `session_required`.

`POST /api/assistant/sohbetler`: sahip `email`. `ogretmen` için `_istek_ogretmeni`. Yoksa genel. Döner: `{id, baslik, ogretmen, olusturma, guncelleme}`.

`GET /api/assistant/sohbetler/<sid>`: erişim. Döner `{sohbet, mesajlar}`. `mesajlar` `tum_mesajlar`. `sohbet` içinde e-posta yok.

`POST /api/assistant/sohbetler/<sid>/mesaj`: yalnız sahip. Değilse 403 `Bu sohbet salt okunur.` Gövde `icerik` strip boşsa 400 `Mesaj boş olamaz.` `ogretmen` doğrulanır. `mesaj_ekle(..., rol="user", ekler=[])`. Bu uç akışın yerine geçmez; liste testi başlığı buradan kurar. Akış Task 3'te kendi satırını yazar.

`PATCH`: yalnız sahip. `baslik` varsa strip, boşsa 400 `Başlık boş olamaz.` `ogretmen` varsa `_istek_ogretmeni`. İkisi de yoksa 400 `Mesaj boş olamaz.` kullanılmaz; 400 `Başlık boş olamaz.` yalnız boş başlık içindir. İkisi de yoksa gövde 400 `Geçersiz istek gövdesi.` (B1'in bozuk gövde cümlesi).

`DELETE`: yalnız sahip. `sohbet_eklerini_sil` Task 3'te bu rotaya bağlanır. Task 2 yalnız satırları siler. Task 3 dosyayı öne alır.

Hata: `sqlite3.OperationalError` loglanır, okura `Sohbet kaydedilemedi.` 500. `str(exc)` yok.

- [ ] **Step 4: PASS**

Aynı pytest. Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/dashboard_api.py tests/test_assistant_sohbet_api.py
git commit -m "feat: asistan sohbet uçlarını sahibine aç"
```

---

### Task 3: Akış, son 20, ek, silme

**Files:**
- Modify: `src/assistant_core.py` (`_build_conversation` penceresi)
- Modify: `src/assistant_uploads.py` (`EkDeposu.bagla`)
- Modify: `src/dashboard_api.py` (`assistant_stream`, `assistant_chat`, `DELETE`)
- Test: `tests/test_assistant_sohbet_api.py` (ek testler), `tests/test_assistant_yukleme_model.py` (B2 dosyası; pencere testi)

**Interfaces:**
- Consumes: B2 `_ekleri_hazirla` (view içinde, `generate` öncesi), B2 `chat_events` işçi ipliği, `EkDeposu.sohbet_eklerini_sil`.
- Produces: `EkDeposu.bagla(email, kimlik, sohbet_id) -> None`. Meta `bagli_sohbet` null ise dolar; başka sohbetse değişmez. `pencere` varsayılan 3.

- [ ] **Step 1: Testler**

`test_pencere_varsayilan_uc_kalir` B2'nin `test_pencere_disindaki_ek_blok_olmaz` dosyasına dokunmaz. Yeni test `tests/test_assistant_yukleme_model.py` içinde: 21 mesajlık listede ilki ekli, `pencere=20` iken o ek blok olmaz, sondan 20'nci (index 1) ekliyse blok olur. `pencere` verilmezse index 1 de blok olmaz (varsayılan 3, liste 21).

Akış testi, runtime spy ile. Spy `chat_events` gövdeyi kaydeder ve `answer` üretir. `generate` içinde `_module_person` None döner (B2'nin `inspect.stack` kalıbı: çerçeve `generate` ve dosya `dashboard_api.py`).

```python
def test_akis_yirmiyi_yukler_yarim_cevabi_yazmaz(istemci, monkeypatch):
    _giris(istemci, ISIK)
    sid = istemci.post("/api/assistant/sohbetler", json={}).get_json()["id"]
    for i in range(21):
        istemci.post(f"/api/assistant/sohbetler/{sid}/mesaj",
                     json={"icerik": f"eski{i}", "ogretmen": "genel"})
    gorulen = {}

    class _K:
        def chat_events(self, **kw):
            gorulen.update(kw)
            yield {"event": "answer", "payload": {
                "answer": "tamam", "citations": [], "safety_flags": [],
                "plan_blocks": [], "intent": "qa", "session_id": "",
                "mode_suggestion": None, "meta": {"ogretmen": "genel"}}}
    monkeypatch.setattr(dashboard_api, "_assistant_runtime", lambda: _K())
    res = istemci.post("/api/assistant/stream", json={
        "sohbet_id": sid,
        "messages": [
            {"role": "user", "content": "sahte geçmiş"},
            {"role": "user", "content": "yeni soru"},
        ],
    })
    assert "event: answer" in res.get_data().decode()
    icerikler = [m["content"] for m in gorulen["messages"] if isinstance(m, dict)]
    assert "sahte geçmiş" not in icerikler
    assert icerikler[0] == "eski2"          # 21 eski + yeni = 22; son 20 eski2'den başlar
    assert icerikler[-1] == "yeni soru"
    assert gorulen["pencere"] == 20
    depo = _sohbet_deposu()
    roller = [m["rol"] for m in depo.tum_mesajlar(sid)]
    assert roller[-2:] == ["user", "assistant"]


def test_akis_koparsa_cevap_satiri_yok(istemci, monkeypatch):
    _giris(istemci, ISIK)
    sid = istemci.post("/api/assistant/sohbetler", json={}).get_json()["id"]

    class _K:
        def chat_events(self, **kw):
            raise RuntimeError("koptu")
            yield {}
    monkeypatch.setattr(dashboard_api, "_assistant_runtime", lambda: _K())
    istemci.post("/api/assistant/stream", json={
        "sohbet_id": sid, "messages": [{"role": "user", "content": "kaldı"}]})
    roller = [m["rol"] for m in _sohbet_deposu().tum_mesajlar(sid)]
    assert roller == ["user"]


def test_v1_ve_plansiz_depo_acmadi(istemci, tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard_api, "OUTPUT_DIR", str(tmp_path))
    # /v1 api_key_only. Bypass anahtarsız 401 bırakır; depo dosyası yine yok.
    istemci.post("/v1/chat/completions", json={"messages": [{"role": "user", "content": "x"}]})
    assert not (tmp_path / "assistant_sohbetler.sqlite").exists()


def test_plan_depo_acmadi(istemci, tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard_api, "OUTPUT_DIR", str(tmp_path))
    gorulen = {}

    class _K:
        def study_plan(self, **kw):
            gorulen.update(kw)
            return {"blocks": []}

    monkeypatch.setattr(dashboard_api, "_assistant_runtime", lambda: _K())
    _giris(istemci, ISIK)
    res = istemci.post("/api/assistant/plan", json={
        "messages": [{"role": "user", "content": "plan"}]})
    assert res.status_code == 200
    assert "sohbet_id" not in gorulen
    assert gorulen.get("hafiza") is not True
    assert not (tmp_path / "assistant_sohbetler.sqlite").exists()


def test_sohbet_id_yoksa_dosya_yok(istemci, tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard_api, "OUTPUT_DIR", str(tmp_path))

    class _K:
        def chat_events(self, **kw):
            yield {"event": "answer", "payload": {
                "answer": "tamam", "citations": [], "safety_flags": [],
                "plan_blocks": [], "intent": "qa", "session_id": "",
                "mode_suggestion": None, "meta": {"ogretmen": "genel"}}}
        def chat(self, **kw):
            return {"answer": "tamam", "citations": [], "safety_flags": [],
                    "plan_blocks": [], "intent": "qa", "session_id": "",
                    "mode_suggestion": None, "meta": {"ogretmen": "genel"}}

    monkeypatch.setattr(dashboard_api, "_assistant_runtime", lambda: _K())
    _giris(istemci, ISIK)
    istemci.post("/api/assistant/stream", json={
        "messages": [{"role": "user", "content": "x"}]})
    istemci.post("/api/assistant/chat", json={
        "messages": [{"role": "user", "content": "x"}]})
    assert not (tmp_path / "assistant_sohbetler.sqlite").exists()


def test_eski_ekler_on_tavanina_girer(istemci, monkeypatch):
    _giris(istemci, ISIK)
    sid = istemci.post("/api/assistant/sohbetler", json={}).get_json()["id"]
    depo = _sohbet_deposu()
    for i in range(9):
        depo.mesaj_ekle(sid, "user", f"eski{i}", "genel", ["ab" * 15 + f"{i:02x}"], SIMDI)
    cagrildi = {"n": 0}

    class _K:
        def chat_events(self, **kw):
            cagrildi["n"] += 1
            yield {"event": "answer", "payload": {
                "answer": "tamam", "citations": [], "safety_flags": [],
                "plan_blocks": [], "intent": "qa", "session_id": "",
                "mode_suggestion": None, "meta": {}}}
    monkeypatch.setattr(dashboard_api, "_assistant_runtime", lambda: _K())
    res = istemci.post("/api/assistant/stream", json={
        "sohbet_id": sid,
        "messages": [{"role": "user", "content": "yeni", "ekler": ["cd" * 16, "ef" * 16]}],
    })
    assert res.status_code == 400
    assert res.get_json()["error"] == "Bir istekte en fazla 10 dosya olabilir."
    assert cagrildi["n"] == 0
    assert [m["icerik"] for m in depo.tum_mesajlar(sid)] == [f"eski{i}" for i in range(9)]
```

`SIMDI`, görev 1'deki saattir; bu test dosyası aynı adı tanımlar. `ab` * 15 + iki hex, 32 karakterlik kimliktir. Dokuz eski ek + iki yeni ek = 11. Sayım `mesaj_ekle`'den önce bittiği için onuncu satır yazılmaz ve model çağrılmaz.

`test_eski_ekler_tavanda_modele_gider`: sekiz eski ek + iki yeni ek 200'dür. Spy'a giden mesajlardaki `ek_govde` toplamı 10'dur. Kimlikler B2'nin yükleme testinin kaydettiği yolla durur; `oku` baytı bulur. Dokuz artı iki, yukarıdaki test, modele gitmez.

`study_plan` bugün `hafiza` almaz. Spy `**kw` ile durur. Rota depoyu açmaz ve `hafiza=True` geçirmez. `messages` gövdesi bugünkü `/api/assistant/plan` alanıdır. Spy `_assistant_runtime`'ın yerine geçtiği için kurucuyu ölçmez. Kurucuyu görev 4'teki `test_runtime_hafiza_varsayilani_dosya_acmaz` ölçer.

Silme: Işık bir ek yükler (B2 `POST /api/assistant/uploads`), stream o ekle gider, `bagli_sohbet` sid olur, `DELETE` sonrası meta dosyası yoktur ve `GET` sohbet 404'tür.

`bagla` birim testi `tests/test_assistant_uploads.py`: null iken dolar; başka sid varken değişmez.

- [ ] **Step 2: FAIL**

`tests/test_assistant_sohbet_api.py` ve `tests/test_assistant_yukleme_model.py`. Expected: FAIL.

- [ ] **Step 3: Uygula**

`bagla`: `oku` ile meta. `bagli_sohbet` None ise `sohbet_id` yaz, `atomic_json_dump` (`src/json_utils.py`). `id` anahtarını diske yazma (B2 `oku` onu okurken ekler).

`_build_conversation`: parametre `pencere: int = 3`, mevcut parametrelerden sonra, varsayılanlı. Döngü `messages[-pencere:]`. `chat` bu parametreyi kwargs ile alır ve iletir. Varsayılan 3.

`assistant_stream` / `assistant_chat`, view içinde, B2'nin `email = _module_person()` ve `_ekleri_hazirla` satırlarının yanında:

- `sohbet_id` yoksa bugünkü yol. `_sohbet_deposu` çağrılmaz. `pencere` gönderilmez. `AssistantRuntime` da dosyayı kurmaz.
- Varsa `_sohbet_erisim`. Sahip değilse 403, gövdeyi açmadan (SSE değil).
- Son kullanıcı mesajı: listedeki son `role==user`. Yoksa ya da metin strip boşsa 400 `Mesaj boş olamaz.` Önceki istemci mesajları atılır.
- Tavan, `_ekleri_hazirla`'dan önce: `son_mesajlar(sid, 19)` satırlarında `json.loads(ekler_json)` ile yeni mesajın `ekler` listesi toplanır. Toplam `ISTEK_SINIRI`'yi (10) aşarsa 400 `Bir istekte en fazla 10 dosya olabilir.` `mesaj_ekle` yok, model yok. 19, yeni satırın yirminci olacağı içindir; bu pencereden düşecek en eski satırın ekleri sayılmaz. Sohbette 19'dan az satır varsa hepsi sayılır. Aynı kimlik iki kez geçtiyse iki sayılır. İkinci bir sabit yok.
- `_ekleri_hazirla([o mesaj], email)` — B2, view içinde, yalnız yeni mesaj. Eski eklerin baytları bunun yanında, aynı view'da, `oku` ile `ek_govde`'ye konur ve yukarıdaki sayıma dahildir.
- `mesaj_ekle` kullanıcı satırı. `sohbet.ogretmen` değişmez. `ekler` alanı `ek_govde` varsa `[{id, ad, tur}, ...]` (`meta["id"]`, `meta["ad"]`, `meta["tur"]`), yoksa `[]`.
- Her id için `EkDeposu(OUTPUT_DIR).bagla(email, id, sid)`.
- `son_mesajlar(sid, 20)` model listesi olur. `content` kolonu `content`, `role` `rol`. Ekli kullanıcı mesajına `ekler` id listesi ve `ek_govde` yeniden konur (B2 bloğu `pencere=20` içinde kalsın). `ek_govde` diskten `oku` ile, view içinde, `generate` öncesi.
- `chat_events(..., messages=hazir, pencere=20, sahip_email=email)`. `generate` `_module_person` çağırmaz.
- Döngü `answer` görünce, view'ın `generate` fonksiyonunda, payload `answer` ve `citations` ile asistan satırı yazılır. İstisna, `error` olayı ya da gövde kapanması asistan satırı yazmaz. Kullanıcı satırı zaten yazılmıştır.
- `/chat` aynı kayıt kuralı: kullanıcı satırı `runtime.chat` öncesi, asistan satırı dönüşten sonra. Yarım cevap yok; `/chat` tek yanıt döner.

`DELETE`: sahip kontrolünden sonra `sohbet_eklerini_sil(sid)`, sonra `depo.sil`. Aile 403.

`study_plan` ve `openai_chat_completion` depo çağırmaz. `openai_chat_completions` rotası da çağırmaz.

- [ ] **Step 4: PASS, komşu**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-b2-plan
DASHBOARD_SECRET_KEY=yalniz-test /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest \
  tests/test_assistant_sohbet.py tests/test_assistant_sohbet_api.py \
  tests/test_assistant_yukleme_model.py tests/test_assistant_uploads.py \
  tests/test_assistant_ogretmen_api.py tests/test_assistant_ogretmen_modu.py \
  -q -p no:cacheprovider
```

Expected: PASS. `sohbet_id` siz öğretmen testleri 200.

- [ ] **Step 5: Commit**

```bash
git add src/assistant_core.py src/assistant_uploads.py src/dashboard_api.py \
  tests/test_assistant_sohbet_api.py tests/test_assistant_yukleme_model.py \
  tests/test_assistant_uploads.py
git commit -m "feat: sohbet akışına son yirmi turu bağla"
```

---

### Task 4: Aile eki, not, özet yazımı, kaynak seçimi

**Files:**
- Modify: `src/dashboard_api.py` (`assistant_upload_oku`, not uçları, cevap satırından sonra özet)
- Modify: `src/assistant_sohbet.py` (`hassas_not`, `ozet_yaz` görev 1'de)
- Modify: `src/assistant_tools.py`, `src/assistant_core.py`
- Test: `tests/test_assistant_uploads_api.py`, `tests/test_assistant_sohbet_api.py`, `tests/test_assistant_sohbet.py`, `tests/test_assistant_core.py`

**Interfaces:**
- Consumes: `OGRENCI_EMAILS`, `okur_turu`, `EkDeposu.oku`, `TOOL_RESULT_SINIRI`.
- Produces: `hafiza_yaz` `{metin: string}`, `hafiza_duzelt` `{id, metin}`, `hassas_not`, `eski_turleri_ozetle`, `_sorguya`, `_parcayi_ele`. İlan yalnız `okur` `ogrenci` ya da `aile` iken, `hafiza=True` iken ve `not_deposu` verilmişken. `study_plan` ve `openai_chat_completion` depo kurmaz.

- [ ] **Step 1: Test**

B2 `test_baskasi_ve_yok_ayni_404`: `DIGER` (`drmahirkurt@gmail.com`) ailedir ve Işık'ın dosyasını **okur** (200, aynı bayt). Yeni iddia: `ozlem.murzoglu@gmail.com` Işık'ın dosyasını okur; Işık, Özlem'in dosyasını okuyamaz (404 `Dosya bulunamadı.`); yok olan id 404, aynı gövde. Okur rolü 403 kalır.

Not: aile `POST /api/assistant/notlar` yok. Model aracı yazar. HTTP:

- `GET /api/assistant/notlar` aile 200, öğrenci 403 `Bu notları yalnız aile düzenler.`
- `PATCH /api/assistant/notlar/<id>` `{metin}` aile, boş metin 400 `Mesaj boş olamaz.`
- `DELETE` aile. Öğrenci 403. Yok 404 `Not bulunamadı.`

Araç testi, depo tmp, `dispatch("hafiza_yaz", {"metin": "Paydada zorlanıyor"}, okur="ogrenci", hafiza=True, not_deposu=depo)`. Satır var. `okur="bilinmiyor"` yazmaz, `ok` False. `hafiza=False` yazmaz. `not_deposu` verilmezse yazmaz ve sqlite dosyası açılmaz.

Hassas not, aynı depoda, yazmadan önce `hassas_not`. Şunlar satır yazmaz, `ok` False, hata `Bu not yazılmadı.`: `İlaç kullanıyor`, `Boşanma konuşuldu`, `05321112233`, `veli@example.com`. Şunlar yazılır: `Paydada zorlanıyor`, `Üçüncü soruyu yarım bırakıyor`, `sınav notu düşük`. Aile `PATCH` ile aynı metinleri gönderir: hassas olan 400 `Bu not yazılmadı.`, ödev cümlesi 200.

Özet ürün yolu. `tamamla` enjekte edilir; varsayılan `claude-haiku-4-5` çağrısı testte kurulmaz.

```python
def test_yirmi_asimi_ozeti_yazar_mesaji_silmez(tmp_path):
    depo = SohbetDeposu(tmp_path / "assistant_sohbetler.sqlite")
    sid = depo.yarat(ISIK, "genel", SIMDI)
    for i in range(21):
        depo.mesaj_ekle(sid, "user", f"m{i}", "genel", [], SIMDI)
    gorulen = {}

    def tamamla(prompt):
        gorulen["prompt"] = prompt
        return "kısa özet"

    from src.assistant_core import eski_turleri_ozetle
    eski_turleri_ozetle(depo, sid, tamamla)
    assert depo.ozet_oku(sid) == "kısa özet"
    assert len(depo.tum_mesajlar(sid)) == 21
    assert "user: m0" in gorulen["prompt"]
    assert "user: m20" not in gorulen["prompt"]


def test_yirmi_asmazsa_ozet_yok(tmp_path):
    depo = SohbetDeposu(tmp_path / "assistant_sohbetler.sqlite")
    sid = depo.yarat(ISIK, "genel", SIMDI)
    for i in range(20):
        depo.mesaj_ekle(sid, "user", f"m{i}", "genel", [], SIMDI)

    def tamamla(prompt):
        raise AssertionError("çağrılmamalı")

    from src.assistant_core import eski_turleri_ozetle
    eski_turleri_ozetle(depo, sid, tamamla)
    assert depo.ozet_oku(sid) is None


def test_ozet_hatasi_cevap_satirini_birakir(tmp_path):
    depo = SohbetDeposu(tmp_path / "assistant_sohbetler.sqlite")
    sid = depo.yarat(ISIK, "genel", SIMDI)
    for i in range(22):
        depo.mesaj_ekle(sid, "user", f"m{i}", "genel", [], SIMDI)

    def tamamla(prompt):
        raise RuntimeError("ağ yok")

    from src.assistant_core import eski_turleri_ozetle
    eski_turleri_ozetle(depo, sid, tamamla)
    assert depo.ozet_oku(sid) is None
    assert len(depo.tum_mesajlar(sid)) == 22
```

Akış testi: cevap satırı yazıldıktan sonra view `eski_turleri_ozetle` çağırır. 21 eski kullanıcı satırı varken tamamlanan bir `answer`, `ozet`'i stub'ın metnine eşitler ve asistan satırını silmez. Stub patlarsa asistan satırı durur, `ozet` NULL kalır. `pencere=20` çağrısında dolu `ozet` sarmalayıcı kullanıcı metnini `Önceki özet:\n` ile başlatır. NULL ise o satır yoktur.

Kaynak seçimi, ağ yok:

```python
def test_sorgu_soru_ekini_dusurur():
    from src.assistant_tools import _sorguya
    assert _sorguya("Payda neden eşitlenir?") == "Payda eşitlenir"
    assert _sorguya("Paydada zorlanıyor") == "Paydada zorlanıyor"


def test_ayni_parca_ikinci_kez_konmaz():
    from src.assistant_core import _parcayi_ele
    assert _parcayi_ele({"Payda eşittir."}, "Payda eşittir.\n\nYeni satır") == "Yeni satır"
    assert _parcayi_ele({"Payda eşittir."}, "Payda eşittir.") == "Aynı parça zaten duruyor."
```

```python
def test_runtime_hafiza_varsayilani_dosya_acmaz(tmp_path):
    from src.assistant_core import AssistantRuntime
    rt = AssistantRuntime(tmp_path)
    assert not (tmp_path / "output" / "assistant_sohbetler.sqlite").exists()
    rt.chat(messages=[{"role": "user", "content": "x"}], hafiza=True)
    assert not (tmp_path / "output" / "assistant_sohbetler.sqlite").exists()
```

`chat` anahtarsızdır (`tests/conftest.py` `ANTHROPIC_API_KEY`'i siler). Dönüş "şu an yanıt veremiyor" yolu olabilir; dosya yine yoktur. Bu test runtime'ı spy ile değiştirmez.

İstem: `SYSTEM_PROMPT` içinde B2'nin `## Yüklenen dosya` bölümünden hemen sonra:

```text
## Öğrenci notu
- `hafiza_yaz` ve `hafiza_duzelt` Işık hakkında kısa not tutar: zorlandığı konu, tercih ettiği anlatım, hedef.
- Sağlık, aile içi ve üçüncü kişi bilgisi yazma.
- Not, sistem istemine değil, kullanıcı turundaki bloğa konur.
```

İki öğretmen modunda bu temel blok bayt bayt aynı kalır (`tests/test_assistant_ogretmen_modu.py` bunu zaten ölçer).

Not bloğu: depolu istekte sarmalayıcıda `Öğrenci notları:\n` ve her not `- metin`. Sistem mesajına eklenmez. `/plan` çağrısında bu blok yoktur.

- [ ] **Step 2: FAIL**

`tests/test_assistant_uploads_api.py`, `tests/test_assistant_sohbet.py`, `tests/test_assistant_sohbet_api.py` ve `tests/test_assistant_core.py`. Expected: FAIL. `_sorguya`, `_parcayi_ele` ve runtime testi `tests/test_assistant_core.py` içindedir. `hassas_not` ile özet testleri `tests/test_assistant_sohbet.py` içindedir.

- [ ] **Step 3: Uygula**

`assistant_upload_oku`: sahip `oku` bulursa onu döner. Bulamazsa ve `okur_turu(email) == "aile"` ise her `OGRENCI_EMAILS` adresi için `oku`. İlki döner. Yoksa 404 `Dosya bulunamadı.`

Not uçları `_require_assistant_access` + aile kapısı. Depo `notlar`, `not_duzelt`, `not_sil`.

`hassas_not(metin) -> bool` `src/assistant_sohbet.py` içindedir. Harf olmayanla ayrılmış parçalar token'dır. Katlanırken `İ` → `i`, `I` → `ı`, sonra `casefold`. Şu token'lardan biri varsa True: `sağlık`, `saglik`, `hastalık`, `hastalik`, `hasta`, `ilaç`, `ilac`, `tedavi`, `teşhis`, `teshis`, `tanı`, `tani`, `boşanma`, `bosanma`. Ayrıca `@` ya da art arda 10 rakam varsa True. `tanım` ve `üçüncü` tek başına yetmez. `not_yaz` True ise satır yazmaz, `""` döner. `not_duzelt` True ise güncellemez, False döner. HTTP önce bu kapıya bakar: hassas 400 `Bu not yazılmadı.`; yok 404.

`build_registry` / `McpRegistry`: opsiyonel `not_deposu=None`. None ise araç ilan edilmez ve `notlar()` çağrılmaz (bugünkü test kayıtları değişmez). `AssistantRuntime.__init__` `SohbetDeposu` kurmaz. `hafiza` varsayılanı True kalsa da depo argümanı yoksa dosya açılmaz.

`declarations(..., hafiza: bool = True)`: `hafiza` ve `okur in ("ogrenci", "aile")` ve `not_deposu is not None` ise iki aracı ekler. `dispatch` aynı kapıyı ve `hassas_not`'u tekrarlar; kapalıysa ya da hassassa yazmaz.

`chat(..., hafiza: bool = True, sohbet_id: str = "", not_deposu=None)`: `hafiza` ve `not_deposu` birlikte varsa `notlar()` metinlerini `_build_conversation`'a verir. İkisi birden yoksa depo kurulmaz. `hafiza_yaz` `kaynak_sohbet=sohbet_id or None`.

`/stream` ve `/chat` yalnız `sohbet_id` varken depoyu kurar, `hafiza=True` ve `not_deposu` geçirir. `sohbet_id` yoksa bu argümanlar geçmez. `study_plan` ve `openai_chat_completion` `SohbetDeposu` kurmaz, `not_deposu` geçirmez.

Özet: `OZET_MODEL = "claude-haiku-4-5"` `assistant_core.py` içindedir. `eski_turleri_ozetle(depo, sid, tamamla)` mesaj sayısı 20'den büyükse, son 20'nin dışında kalan turları `tamamla`'ya verir. İstemi şudur: eski turları kısa özete indir; yüklenen eklerin adını ve kimliğini, çözülen soruları ve açık kalan işleri koru; eski araç gövdesini olduğu gibi taşıma, kaynağın adını koru; yalnız özet metnini yaz. Her eski tur `rol: icerik` satırıdır. Varsa önceki `ozet` istemin başındadır. Dönüş `ozet_yaz` ile yazılır. `tamamla` verilmezse tek çağrı `OZET_MODEL` iledir; Sonnet değişmez. İstisna yutulur, tipi loglanır, `ozet` değişmez. Eski turun `ekler_json` değeri isteme `ad` ve `id` ile yazılır. View bu fonksiyonu asistan satırı yazıldıktan sonra çağırır; `answer` olayı Haiku'yu beklemez. Okuma: depolu istek `ozet_oku`. NULL değilse sarmalayıcıya, sisteme değil.

Kaynak seçimi:

- `_parcayi_ele(onceki: set[str], govde: str) -> str` gövdeyi `\n\n` ile böler, `onceki`'de olan parçayı düşürür, kalanı geri verir, kalan yoksa `Aynı parça zaten duruyor.` `chat_with_tools` her başarılı araç gövdesinde, `_sonuc_icerigi`'nden önce bunu çağırır. Araç adı başına biriken küme bu istektir. `tool_result` yine döner; API eksik sonuç kabul etmez. `TOOL_RESULT_SINIRI` (4000) durur. Yeni bir karakter tavanı yazılmaz. Bu, spec'in vermediği pay sayısının yerine konan kilitir.
- Uzun sohbet: `mesaj.meta_json` `{}` kalır, araç gövdesi satıra yazılmaz. 20'nin dışındaki gövde bir sonraki istekte açılmaz. Onun yerine `ozet` gider. İkinci bir özet modeli yok.
- `_sorguya(metin)` `?` ve `!` siler, `split()` eder, katlanmış token şunlardansa düşürür: `nedir`, `nelerdir`, `nasıl`, `nasil`, `neden`, `niçin`, `nicin`, `kim`, `kimdir`, `hangi`, `kaç`, `kac`, `mı`, `mi`, `mu`, `mü`. Kalan boşsa, `?` silinmiş özgün metin kalır. Ek model çağrısı yok. Yalnız `_dispatch_local` ve `_dispatch_aile_kaynak` aramadan önce uygular.

- [ ] **Step 4: PASS**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-b2-plan
DASHBOARD_SECRET_KEY=yalniz-test /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest \
  tests/test_assistant_uploads_api.py tests/test_assistant_sohbet.py \
  tests/test_assistant_sohbet_api.py tests/test_assistant_core.py \
  tests/test_assistant_ogretmen_modu.py tests/test_assistant_yerel_kaynaklar.py \
  -q -p no:cacheprovider
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/dashboard_api.py src/assistant_core.py src/assistant_tools.py \
  tests/test_assistant_uploads_api.py tests/test_assistant_sohbet_api.py
git commit -m "feat: aile notunu, özeti ve kaynak seçimini bağla"
```

---

### Task 5: Liste, not paneli, salt okuma

**Files:**
- Modify: `dashboard/src/components/AssistantChat.tsx`
- Modify: `dashboard/src/components/AssistantChat.scss`
- Create: `dashboard/tests/e2e/asistan-sohbet.spec.ts`

**Interfaces:**
- Consumes: `GET/POST/PATCH/DELETE /api/assistant/sohbetler`, `GET /api/assistant/sohbetler/<id>`, `GET/PATCH/DELETE /api/assistant/notlar`. `useSession().student`.
- Produces: masaüstünde solda `Sohbetler`; `34rem` altında kapalı, `Sohbetler` düğmesi alttan paneli açar. Bu sınır `dashboard/src/theme/ted-theme.scss` içindeki mevcut `34rem`.

- [ ] **Step 1: e2e**

`dashboard/tests/e2e/asistan-sohbet.spec.ts`. `sabitAc` `mock` ile akışı keser. Sohbet rotaları `sabitAc`'ten **sonra** kaydedilir (Playwright son rotayı kullanır).

```ts
const SOHBET = {
  id: 'ab'.repeat(16), baslik: 'Payda eşitle', ogretmen: 'matematik',
  olusturma: '2026-10-03T08:00:00Z', guncelleme: '2026-10-03T08:00:00Z',
}
const MESAJLAR = [
  { id: 'cd'.repeat(16), rol: 'user', icerik: 'Payda neden eşitlenir?',
    atiflar_json: '[]', ekler_json: '[]', ogretmen: 'matematik', zaman: '2026-10-03T08:00:00Z' },
  { id: 'ef'.repeat(16), rol: 'assistant', icerik: 'Paydalar toplanmaz.',
    atiflar_json: '[]', ekler_json: '[]', ogretmen: 'matematik', zaman: '2026-10-03T08:01:00Z' },
]

test('desktop lists the chat and loads it', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await sabitAc(page, '/asistan', 1440, 900)
  await page.route('**/api/assistant/sohbetler?*', r => r.fulfill(json({ sohbetler: [] })))
  await page.route('**/api/assistant/sohbetler', r => r.fulfill(json({ sohbetler: [SOHBET] })))
  await page.route(`**/api/assistant/sohbetler/${SOHBET.id}`, r => r.fulfill(json({
    sohbet: SOHBET, mesajlar: MESAJLAR,
  })))
  await page.goto('/asistan')
  await expect(page.getByRole('heading', { name: 'Sohbetler' })).toBeVisible()
  await page.getByRole('button', { name: 'Payda eşitle' }).click()
  await expect(page.getByText('Paydalar toplanmaz.')).toBeVisible()
})

test('the open chat teacher beats localStorage', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('tedy-asistan-ogretmen::test@tedy.online', 'genel')
  })
  await page.setViewportSize({ width: 1440, height: 900 })
  await sabitAc(page, '/asistan', 1440, 900)
  await page.route('**/api/assistant/sohbetler?*', r => r.fulfill(json({ sohbetler: [] })))
  await page.route('**/api/assistant/sohbetler', r => r.fulfill(json({ sohbetler: [SOHBET] })))
  await page.route(`**/api/assistant/sohbetler/${SOHBET.id}`, r => r.fulfill(json({
    sohbet: SOHBET, mesajlar: MESAJLAR,
  })))
  await page.goto('/asistan')
  await page.getByRole('button', { name: 'Payda eşitle' }).click()
  await expect(page.locator('input[name="ac-ogretmen"][value="matematik"]')).toBeChecked()
})

test('an empty list uses the spec sentence', async ({ page }) => {
  // Varsayılan e2e kullanıcısı ailedir: kendi listesi ve Işık bölümü, aynı cümle iki kez.
  await sabitAc(page, '/asistan', 1440, 900)
  await page.route('**/api/assistant/sohbetler**', r => r.fulfill(json({ sohbetler: [] })))
  await page.goto('/asistan')
  await expect(page.getByRole('heading', { name: "Işık'ın sohbetleri" })).toBeVisible()
  await expect(page.getByText('Henüz sohbet yok — bir soru sorarak başla')).toHaveCount(2)
})

test('phone hides the list until Sohbetler', async ({ page }) => {
  await sabitAc(page, '/asistan', 390, 844)
  await page.route('**/api/assistant/sohbetler**', r => {
    const url = r.request().url()
    if (url.includes('kisi=')) return r.fulfill(json({ sohbetler: [] }))
    return r.fulfill(json({ sohbetler: [SOHBET] }))
  })
  await page.goto('/asistan')
  await expect(page.getByRole('heading', { name: 'Sohbetler' })).toBeHidden()
  await page.getByRole('button', { name: 'Sohbetler' }).click()
  await expect(page.getByRole('heading', { name: 'Sohbetler' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Payda eşitle' })).toBeVisible()
})

test('family section is read only and has no student note', async ({ page }) => {
  await sabitAc(page, '/asistan', 1440, 900)
  await page.route('**/api/assistant/sohbetler**', r => {
    const url = r.request().url()
    if (url.includes('kisi=ogrenci')) return r.fulfill(json({ sohbetler: [SOHBET] }))
    return r.fulfill(json({ sohbetler: [] }))
  })
  await page.route('**/api/assistant/notlar', r => r.fulfill(json({
    notlar: [{ id: 'aa'.repeat(16), metin: 'Paydada zorlanıyor', kaynak_sohbet: null, zaman: '2026-10-03T08:00:00Z' }],
  })))
  await page.goto('/asistan')
  await expect(page.getByRole('heading', { name: "Işık'ın sohbetleri" })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Sil' })).toHaveCount(0)
  await expect(page.getByText('Sohbetlerini ailen de görebilir.')).toHaveCount(0)
  await expect(page.getByRole('heading', { name: 'Asistanın notları' })).toBeVisible()
  await expect(page.getByText('Paydada zorlanıyor')).toBeVisible()
})

test('Işık sees the family note and no notes panel', async ({ page }) => {
  await sabitAc(page, '/asistan', 1440, 900)
  await page.route('**/api/auth/me', r => r.fulfill(json({
    email: 'isikkurtx@gmail.com', name: 'Işık Kurt', picture: '', role: 'full', student: true,
  })))
  await page.route('**/api/assistant/sohbetler*', r => r.fulfill(json({ sohbetler: [] })))
  await page.goto('/asistan')
  await expect(page.getByText('Sohbetlerini ailen de görebilir.')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Asistanın notları' })).toHaveCount(0)
})
```

Gönderim testi: `Yeni sohbet` POST'u 200 döner, sonra Gönder `sohbet_id` taşır ve `messages` tek kullanıcı mesajıdır. Akış SSE `answer` döner; `/chat` sayacı 0. `sabitAc`'in stream abort'u bu testte `page.route` ile ezilir.

Axe + IBM, B2 `asistan-yukleme.spec.ts` içindeki süzgeçle: `aria_id_unique` ve `cds--ai-label|cds--toggletip` ihlal sayılmaz. Liste doluyken `scrollWidth - innerWidth <= 0`.

- [ ] **Step 2: FAIL**

`cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-b2-plan/dashboard && npm run build && TEDY_E2E_PYTHON=/mnt/thunderbolt/workspaces/TED/.venv/bin/python DASHBOARD_SECRET_KEY=yalniz-test env -u ANTHROPIC_API_KEY npx playwright test asistan-sohbet.spec.ts`

Expected: FAIL, `Sohbetler` yok. `npm ci` gerekirse önce o.

- [ ] **Step 3: Arayüz**

Durum: `sohbetId`, `liste`, `isikListe` (yalnız `!student`), `notlar` (yalnız `!student`), `hataListe`.

İlk yüklemede `GET /api/assistant/sohbetler`. Aile ayrıca `?kisi=ogrenci` ve `GET /api/assistant/notlar`. İkisi de `credentials: 'include'`. Hata cümlesi `Sohbetler yüklenemedi.` Boş kendi listesi spec cümlesi. Boş Işık listesi aynı cümle, bölüm başlığı durur.

`Yeni sohbet` POST, dönen `id` seçilir, mesajlar karşılama satırına iner. Başlık boşken satır çizilmez.

Satır düğmesi başlığı açar: `GET .../<id>`, mesajlar `rol`/`icerik` ile çizilir. Dönüşteki `sohbet.ogretmen` seçiciye yazılır: `ogretmen.sec(sohbet.ogretmen)`. `useOgretmen` anahtarı `tedy-asistan-ogretmen::<email>` yalnız seçili sohbet yokken geçerlidir. Seçili sohbetin öğretmeni onu ezer. Seçiciyi elle değiştirmek `PATCH` ile `sohbet.ogretmen` yazar; gönderim `mesaj_ekle` üzerinden bu kolonu değiştirmez. Kendi satırında `Yeniden adlandır` (`TextInput`, Enter PATCH) ve `Sil` (DELETE). Işık satırında ikisi de yok. Seçili Işık sohbetinde `#ac-input` `disabled`, yanında `Bu sohbet salt okunur.`

Gönder, seçili kendi sohbetinde: gövde `{sohbet_id, ogretmen, messages: [{role:'user', content, ekler?}]}`. Tek mesaj. `sohbet_id` yoksa önce POST, sonra aynı gövde. B2'nin plan / yeniden üret / daha derine yolları `sohbet_id` koymaz.

Işık'ın ekranında, liste ile yazma alanı arasında kalıcı paragraf: `Sohbetlerini ailen de görebilir.`

Not paneli: başlık `Asistanın notları`. Satırda metin, `Düzelt` (PATCH), `Sil` (DELETE). Öğrencide panel yok.

`34rem` altında `.ac-sohbetler` `display` ile gizlenmez; `visibility`/`translate` kullanma. Kapalıyken DOM'da `hidden` (erişilebilir adı da gizli). Açıkken sayfanın altında, `position: fixed`, `inset-inline: 0`, `inset-block-end: 0`, `max-block-size: 70vh`, zemin `var(--cds-layer)`. Masaüstünde solda, sohbet sütununun yanında, `hidden` değil.

- [ ] **Step 4: PASS ve görsel**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-b2-plan/dashboard
npm run lint
npm run build
TEDY_E2E_PYTHON=/mnt/thunderbolt/workspaces/TED/.venv/bin/python DASHBOARD_SECRET_KEY=yalniz-test env -u ANTHROPIC_API_KEY npx playwright test asistan-sohbet.spec.ts
TEDY_E2E_PYTHON=/mnt/thunderbolt/workspaces/TED/.venv/bin/python DASHBOARD_SECRET_KEY=yalniz-test env -u ANTHROPIC_API_KEY npx playwright test asistan-ogretmen-gorsel.spec.ts --update-snapshots
```

Liste asistan karesini değiştirir. Yalnız değişen PNG'lere bak; `dashboard/tests/e2e` dizinini toplu ekleme.

- [ ] **Step 5: Commit**

```bash
git add dashboard/src/components/AssistantChat.tsx dashboard/src/components/AssistantChat.scss \
  dashboard/tests/e2e/asistan-sohbet.spec.ts \
  dashboard/tests/e2e/asistan-ogretmen-gorsel.spec.ts-snapshots
git commit -m "feat: asistan sayfasına sohbet listesini ekle"
```

---

### Task 6: CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`, B2 maddesinin hemen altı. B2 maddesi `- **Asistan dosya yükleme (B2)**` ile başlar. O madde yoksa B1 maddesinin (`- **Asistanın öğretmen modları (B1, 2026-09-28)**`) hemen altı; B2 maddesi gelince bu madde onun altında kalır.

- [ ] **Step 1: Madde**

```markdown
- **Asistan sohbet geçmişi (B3)** (spec §3, plan `docs/superpowers/plans/2026-10-03-asistan-sohbet-gecmisi-b3.md`): `output/assistant_sohbetler.sqlite` (WAL, connection per transaction, busy_timeout 5000). `GET/POST /api/assistant/sohbetler`, `GET/PATCH/DELETE /api/assistant/sohbetler/<id>`, `?kisi=ogrenci` for Işık's chats. Family is read-only (`Bu sohbet salt okunur.`). `/stream` and `/chat` with `sohbet_id` save the user row before `generate()`, load the last 20 in insert order (`sira`, not the uuid), and save the assistant row only after the `answer` event. The chat's `ogretmen` loads the selector and `mesaj_ekle` does not overwrite it. Historical attachments inside that window count toward the 10-file cap. No `sohbet_id` means today's path and no database. `AssistantRuntime` does not create the file, including when `hafiza` defaults on. `/v1`, `/plan` and API keys never open the file. `DELETE` calls `EkDeposu.sohbet_eklerini_sil` then drops the rows. Family `GET /api/assistant/uploads/<id>` reads Işık's file. `hafiza_yaz` / `hafiza_duzelt` and `GET/PATCH/DELETE /api/assistant/notlar` (family only). `hassas_not` refuses the locked health, family and identifier patterns before a write. Past 20 messages the product writes `ozet` with `claude-haiku-4-5` and does not delete messages. Source selection drops a repeated piece, keeps the existing 4000-character tool cap, and rewrites the search query without a model call.
```

- [ ] **Step 2: Son kapı**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-b2-plan
DASHBOARD_SECRET_KEY=yalniz-test /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest \
  tests/test_assistant_sohbet.py tests/test_assistant_sohbet_api.py \
  tests/test_assistant_uploads_api.py tests/test_assistant_ogretmen_api.py \
  -q -p no:cacheprovider
git diff --check -- CLAUDE.md docs/superpowers/plans/2026-10-03-asistan-sohbet-gecmisi-b3.md
cd dashboard && npm run lint && npm run build
TEDY_E2E_PYTHON=/mnt/thunderbolt/workspaces/TED/.venv/bin/python DASHBOARD_SECRET_KEY=yalniz-test env -u ANTHROPIC_API_KEY npx playwright test asistan-sohbet.spec.ts
```

Expected: pytest `0 failed`, `git diff --check` boş, lint, build ve Playwright 0.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: asistan sohbet geçmişini CLAUDE.md'ye yaz"
```

## Kapsam denetimi

| Spec | Görev |
|---|---|
| sqlite, WAL, işlem başına bağlantı, şema | 1 |
| GET/POST/PATCH/DELETE, kendi sohbeti, `?kisi=ogrenci`, yazma sahibine | 2, 5 |
| Son 20, aynı saniyede ekleme sırası, kopan akışta yarım cevap yok, başlık ilk sorudan | 1, 3 |
| Sohbet öğretmeni seçiciyi kurar; `mesaj_ekle` kolonu ezmez | 1, 5 |
| Eski ekler 10 tavanına girer | 3 |
| `sohbet_id` yoksa dosya yok; runtime `hafiza` varsayılanında dosya açmaz | 3, 4 |
| Sohbet silinince ekler | 3 (`sohbet_eklerini_sil`, dosya önce) |
| `bagli_sohbet` dolar | 3 (`bagla`) |
| Aile ek URL'si | 4 |
| Okur asistana giremez; `/v1`, `/plan` ve API anahtarı depoya dokunmaz | 2, 3, 4 |
| Boş liste cümlesi | 5 |
| Masaüstü liste, telefon paneli, Yeni sohbet, yeniden adlandır, sil | 5 |
| Işık notu; aile bölümü salt okunur | 5 |
| `ogrenci_notu`, `hafiza_yaz` / `hafiza_duzelt`, aile paneli | 4, 5 |
| Özet yazımı (`claude-haiku-4-5`), mesaj tablosu durur, okuma | 4 |
| Kaynak seçimi (tekrar, pay, eski gövde, `_sorguya`) | 4 |
| Hassas notun kod denetimi | 4 |
| Eşzamanlı iki yazıcı, sahiplik, aile salt okuma | 1, 2 |
| Boş başlık gizli; Yeniden üret / Daha derine in `sohbet_id` göndermez | açık karar 5 ve 7 |
| B4–B6 | yok |
