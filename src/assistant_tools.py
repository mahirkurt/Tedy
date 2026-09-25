"""Tool registry for the assistant's function-calling loop.

Declarations are built from each server's own inputSchema rather than written
by hand. That is not a style preference: search_learning_outcomes takes `q`
(not `query`), wants `grade` as a string, and only its description says the
canonical form is "5.Sınıf". Measured — a hand-written declaration produced
grade:"6"; the server's schema, descriptions intact, produced grade:"5.Sınıf".
"""
from __future__ import annotations

import base64
import copy
import html
import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable
from zoneinfo import ZoneInfo

from src.course_names import normalize_course
from src.mcp_client import McpClient, McpToolResult
from src import assistant_kitaplar, assistant_modules

logger = logging.getLogger(__name__)

# Gemini-facing name -> (server, MCP tool name).
# Fourteen of the 27 available tools. The rest are not exposed because a large tool
# list bloats every prompt and slows the loop; adding one is a single line.
TOOL_ALLOWLIST: dict[str, tuple[str, str]] = {
    "kazanim_ara":       ("maarif-mufredat", "search_learning_outcomes"),
    "kazanim_listele":   ("maarif-mufredat", "list_learning_outcomes"),
    "mufredat_ara":      ("maarif-mufredat", "search"),
    "kitap_listele":     ("maarif-mufredat", "list_textbooks"),
    "kitap_sayfa":       ("maarif-mufredat", "get_document_text"),
    "figur_ara":         ("maarif-mufredat", "search_figures"),
    "figur_getir":       ("maarif-mufredat", "get_figure"),
    "program_getir":     ("maarif-mufredat", "get_curriculum_program"),
    "ders_bilgisi":      ("maarif-mufredat", "get_subject"),
    "video_listele":     ("maarif-mufredat", "list_videos"),
    "video_getir":       ("maarif-mufredat", "get_video"),
    "oer_ara":           ("egitim-kaynak", "kb_search"),
    "oer_kazanima_gore": ("egitim-kaynak", "kb_for_outcome"),
    "oer_getir":         ("egitim-kaynak", "kb_get"),
}

# Which citation class a server's output belongs to. The distinction is load
# bearing: local files are authoritative for Işık's own data, the curriculum
# server for subject knowledge, and the two must never be blended.
_KIND_BY_TOOL: dict[str, str] = {
    "kitap_sayfa": "kitap",
    "figur_ara": "kitap",
    "figur_getir": "kitap",
    "oer_ara": "oer",
    "oer_kazanima_gore": "oer",
    "oer_getir": "oer",
    "program_getir": "mufredat",
    "ders_bilgisi": "mufredat",
    "video_listele": "mufredat",
    "video_getir": "mufredat",
}

# Curriculum tools that take a `grade` filter. A search the model did not
# scope is scoped to Işık's own grade (`McpRegistry.sinif`): measured
# 2026-09-25, an unscoped outcome search mixed every year's results.
# get_curriculum_program, get_subject, list_videos, get_video and kb_get take
# no `grade` (tools/list, 2026-09-25), so none of them is here.
SINIF_ARACLARI = frozenset({"kazanim_ara", "kazanim_listele", "mufredat_ara",
                            "kitap_listele", "figur_ara"})

# Görev 4's tools. Unlike the first seven, their bodies are shaped to fit
# GOVDE_SINIRI rather than left to chat_with_tools' blind 4,000-character cut.
_YENI_MAARIF = frozenset({"program_getir", "ders_bilgisi", "video_listele", "video_getir"})
_YENI_ARACLAR = _YENI_MAARIF | {"oer_getir"}

# What the Messages API accepts as an image block, and so the only formats
# the figure endpoint serves: a remote server must not pick what the
# dashboard's origin serves (an SVG can carry script).
GORSEL_BICIMLERI = frozenset({"image/png", "image/jpeg", "image/gif", "image/webp"})

# Every pdf_url/source_url in the maarif corpus answers HTTP 500 since MEB
# moved its files in summer 2026 (CureoHub mcp-servers/mufredat-mcp/
# DISCOVERY-UPSTREAM-2026-09.md §2). They are removed before the model reads a
# result, so it cannot hand the reader a dead link.
OLU_BAGLANTILAR = frozenset({"pdf_url", "source_url"})


def _json_parcalari(text: str) -> list[Any] | None:
    """The maarif server answers with one or more JSON values back to back
    (one content block per list item). None when the text is not that."""
    decoder = json.JSONDecoder()
    out: list[Any] = []
    i = 0
    while i < len(text):
        while i < len(text) and text[i].isspace():
            i += 1
        if i >= len(text):
            break
        try:
            value, i = decoder.raw_decode(text, i)
        except ValueError:
            return None
        out.append(value)
    return out or None


def _baglantisiz(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _baglantisiz(v) for k, v in value.items() if k not in OLU_BAGLANTILAR}
    if isinstance(value, list):
        return [_baglantisiz(v) for v in value]
    return value


def _hata_zarfi(parcalar: list[Any]) -> str | None:
    """The maarif server reports a miss as data, not isError: get_figure with an
    unknown id answers `{"error": "figure N not found"}`, get_curriculum_program
    `{"error": "program not found for subject", "subject": …}` (measured
    2026-09-25). Cited as a source, that envelope read as evidence."""
    if len(parcalar) == 1 and isinstance(parcalar[0], dict):
        hata = parcalar[0].get("error")
        if isinstance(hata, str) and hata:
            # The envelope reaches the model as the error text: strip dead links
            # from it as from any other maarif result.
            return json.dumps(_baglantisiz(parcalar[0]), ensure_ascii=False)
    return None


# kb_get with no max_chars returns the whole document; the rest of its
# envelope (licence, caveat, flags) measured ~800 characters, so this keeps
# the body inside GOVDE_SINIRI.
OER_METIN_SINIRI = 2500


def _sigdir(satirlar: list[str], sinir: int, kalan_notu: Callable[[int], str]) -> str:
    """Whole lines up to `sinir` characters; when some do not fit, the note
    saying how many were left out takes their place — a silent cut would
    read as the complete list."""
    out: list[str] = []
    boy = 0
    for i, satir in enumerate(satirlar):
        sonra = len(satirlar) - i - 1
        # This line, plus room for the note if any line would still follow.
        gerek = boy + len(satir) + 1 + (len(kalan_notu(sonra)) + 1 if sonra else 0)
        if gerek > sinir:
            out.append(kalan_notu(len(satirlar) - i))
            break
        out.append(satir)
        boy += len(satir) + 1
    return "\n".join(out)


def _video_listesi_metni(parcalar: list[Any]) -> str:
    """list_videos answers 157 records, 46,539 characters (2026-09-25): as JSON
    the 4,000-character cut kept the first dozen. One line per video, grouped
    by category; `video_getir` gives a video's links and description."""
    videolar = [v for v in parcalar if isinstance(v, dict)]
    kategoriler: dict[str, list[dict[str, Any]]] = {}
    for v in videolar:
        kategoriler.setdefault(str(v.get("category") or "diğer"), []).append(v)
    satirlar = [f"{len(videolar)} video. Bağlantı ve açıklama için `video_getir`'e id ver."]
    for kat, grup in kategoriler.items():
        satirlar.append(f"[{kat}]")
        satirlar.extend(f"#{v.get('id')} {v.get('title', '')}" for v in grup)
    adlar = ", ".join(kategoriler)
    return _sigdir(satirlar, GOVDE_SINIRI,
                   lambda n: f"… {n} satır daha listelenmedi; `category` ile daralt ({adlar}).")


_BASLIK_SAYFA_NO = re.compile(r"\d+$")
_PROGRAM_BOLUMU = re.compile(r"ünite|tema|sınıf", re.IGNORECASE)


def _program_metni(p: dict[str, Any]) -> str:
    """get_curriculum_program's `toc`: every entry's head repeats the page
    number and the programme's running header ("FEN BILIMLERI DERSI ÖĞRETIM
    PROGRAMI151"), and the Fen Bilimleri toc measured 12,134 characters.
    Header dropped, one line per page; when that still does not fit, the unit,
    theme and grade lines are what the reader asks for ("ünite sırası")."""
    toc = p.get("toc")
    if not isinstance(toc, list):
        return json.dumps(_baglantisiz(p), ensure_ascii=False)
    belge = p.get("document") if isinstance(p.get("document"), dict) else {}
    ust = [str(belge.get("title") or p.get("subject") or "Öğretim programı")]
    if belge.get("grade_or_grades"):
        ust.append(f"Sınıflar: {belge['grade_or_grades']}")
    if p.get("page_count"):
        ust.append(f"{p['page_count']} sayfa. Bir sayfanın metni için `kitap_sayfa`.")

    ayrik = []
    for t in toc:
        if not isinstance(t, dict):
            continue
        satirlar = [s.strip() for s in str(t.get("head") or "").split("\n")]
        if satirlar and satirlar[0] == str(t.get("page_no")):
            satirlar = satirlar[1:]
        ayrik.append((t.get("page_no"), satirlar))
    basliklar = [_BASLIK_SAYFA_NO.sub("", s[0]) for _, s in ayrik if s]
    tekrar = max(set(basliklar), key=basliklar.count) if basliklar else None
    if tekrar is not None and basliklar.count(tekrar) < 2:
        tekrar = None

    satirlar = []
    for no, s in ayrik:
        if s and tekrar is not None and _BASLIK_SAYFA_NO.sub("", s[0]) == tekrar:
            s = s[1:]
        metin = " ".join(" ".join(s).split())
        if metin:
            satirlar.append(f"s.{no}: {metin}")
    sinir = GOVDE_SINIRI - sum(len(u) + 1 for u in ust) - 1
    if sum(len(s) + 1 for s in satirlar) > sinir:
        secilen = [s for s in satirlar if _PROGRAM_BOLUMU.search(s)]
        if secilen:
            ust.append(f"Yalnız ünite/tema/sınıf başlıklı sayfalar ({len(secilen)}/{len(satirlar)}):")
            sinir = GOVDE_SINIRI - sum(len(u) + 1 for u in ust) - 1
            satirlar = secilen
    govde = _sigdir(satirlar, sinir, lambda n: f"… {n} sayfa daha; `kitap_sayfa` ya da `mufredat_ara` ile bak.")
    return "\n".join(ust + [govde])


def _figur_bilgisi(parcalar: list[Any] | None) -> dict[str, Any]:
    return parcalar[0] if parcalar and isinstance(parcalar[0], dict) else {}


LOCAL_TOOL = "ogrenci_verisi_ara"
# The homework list as Bugün and İşler show it (portal rows, photo-added ones,
# Işık's own "Yaptım" marks). Declared only when the caller supplies a source.
ODEV_TOOL = "odev_listesi"
ODEV_ATIF = "Ödevlerim · güncel liste"

_GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
_COZULMUS = {"yaptı", "yapti", "yapmadı", "yapmadi", "eksik", "tamamlandı", "tamamlandi"}
_GECMIS_GUN = 14
_BOLUM_SINIRI = 10


def bugun_satiri(simdi: datetime) -> str:
    """"Bugün: Perşembe 24.09.2026 16:10" — the model has no clock of its own."""
    return f"Bugün: {_GUNLER[simdi.weekday()]} {simdi:%d.%m.%Y %H:%M}"


def _teslim(deger: str) -> datetime | None:
    s = str(deger or "").strip()
    for bicim in ("%d.%m.%Y %H:%M", "%d.%m.%Y"):
        try:
            return datetime.strptime(s, bicim)
        except ValueError:
            continue
    return None


def _goreli(teslim: datetime, simdi: datetime) -> str:
    fark = (teslim.date() - simdi.date()).days
    if fark == 0:
        return "bugün"
    if fark == 1:
        return "yarın"
    if fark == -1:
        return "dün"
    return f"{fark} gün sonra" if fark > 0 else f"{-fark} gün önce"


def _sebit_zaman(deger: Any) -> datetime | None:
    """sebit_homework.json's own date shape ("2026-05-18 06:57"), distinct
    from the portal's "DD.MM.YYYY HH:MM" — SEBİT is a different platform with
    its own scrape (src/scrape_sebit_homework.py)."""
    s = str(deger or "").strip()
    for bicim in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, bicim)
        except ValueError:
            continue
    return None


def _sebit_bolumu_metni(veri: Any, simdi: datetime) -> str:
    """SEBİT ödevleri (sebit_homework.json, /api/sebit'in okuduğu dosya) as
    their own section: a different platform with its own progress percentage
    and end date, not the TED portal's homework the sections above cover."""
    veri = veri if isinstance(veri, dict) else {}
    rows = [r for r in (veri.get("homework") or []) if isinstance(r, dict)]
    if not rows:
        return "SEBİT (0): şu an SEBİT'te kayıtlı ödev yok."

    acik = [r for r in rows if not r.get("completed")]
    tamam = [r for r in rows if r.get("completed")]

    def satir(r: dict[str, Any]) -> str:
        ad = " — ".join(x for x in (str(r.get("course") or "").strip(),
                                    str(r.get("title") or "").strip()) if x)
        bitis = _sebit_zaman(r.get("end_date"))
        zaman = (f"bitiş {_GUNLER[bitis.weekday()]} {bitis:%d.%m.%Y %H:%M} ({_goreli(bitis, simdi)})"
                 if bitis else "bitiş tarihi okunamadı")
        ilerleme = r.get("progress")
        yuzde = f" · %{ilerleme:.0f}" if isinstance(ilerleme, (int, float)) else ""
        durum = str(r.get("state_text") or "").strip()
        return f"- {ad} · {zaman}{yuzde}" + (f" · {durum}" if durum else "")

    def sirala(grup: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(grup, key=lambda r: ((_sebit_zaman(r.get("end_date")) is None),
                                            _sebit_zaman(r.get("end_date")) or simdi))

    parcalar = [f"SEBİT — AÇIK ({len(acik)}):\n" + ("\n".join(
        satir(r) for r in sirala(acik)[:_BOLUM_SINIRI]) or "- yok")]
    if tamam:
        parcalar.append(f"SEBİT — TAMAMLANDI ({len(tamam)})")
    return "\n\n".join(parcalar)


def odev_listesi_metni(rows: list[dict[str, Any]], simdi: datetime, sebit: Any = None) -> str:
    """The homework list for the model, in the groups İşler uses.

    Written for a reader, not a parser: the model quotes from it. Work Işık
    marked "Yaptım" is never listed as still to do — that is the mistake the
    smoke test caught — and the open work carries the teacher's instructions.

    `sebit`, when given, is sebit_homework.json's own data (a different
    platform, /api/sebit) and is appended as its own section — the existing
    sections and their order are untouched (plan Görev 3)."""
    bas = bugun_satiri(simdi)
    if not rows:
        metin = f"{bas}\nŞu an portalda kayıtlı ödev yok."
        return metin if sebit is None else metin + "\n\n" + _sebit_bolumu_metni(sebit, simdi)

    yapilacak, yaptim, gecmis, cozulmus = [], [], [], []
    eski = 0
    for r in rows:
        teslim = _teslim(r.get("Ödev Son Teslim Tarihi", ""))
        # A deadline more than two weeks past is history, whatever its status:
        # on 2026-09-24 twelve "Yaptım" rows from March sorted ahead of this
        # week's and pushed it past the cap. They are counted, not hidden.
        if teslim is not None and (simdi - teslim).days > _GECMIS_GUN:
            eski += 1
            continue
        cozuldu = r.get("teacher_resolved")
        if cozuldu is None:
            cozuldu = str(r.get("Ödev Durumu", "")).strip().lower() in _COZULMUS
        if cozuldu:
            cozulmus.append((teslim, r))
        elif r.get("student_marked_done"):
            yaptim.append((teslim, r))
        elif teslim is not None and teslim < simdi:
            gecmis.append((teslim, r))
        else:
            yapilacak.append((teslim, r))

    def satir(teslim: datetime | None, r: dict[str, Any], aciklama: bool = False) -> str:
        ad = " — ".join(x for x in (str(r.get("normalized_course") or r.get("Ders Adı") or "").strip(),
                                    str(r.get("Ödev Başlığı") or "").strip()) if x)
        zaman = (f"teslim {_GUNLER[teslim.weekday()]} {teslim:%d.%m.%Y %H:%M} ({_goreli(teslim, simdi)})"
                 if teslim else "teslim tarihi okunamadı")
        metin = f"- {ad} · {zaman}"
        if aciklama:
            detay = " ".join(str((r.get("detail") or {}).get("description") or "").split())
            if detay:
                kisa = detay if len(detay) <= 240 else detay[:240].rsplit(" ", 1)[0] + " …"
                metin += f"\n  Açıklama: {kisa}"
        return metin

    def sirala(grup):
        return sorted(grup, key=lambda x: (x[0] is None, x[0] or simdi))

    parcalar = [bas + " (portal listesi, Işık'ın \"Yaptım\" işaretleriyle)"]
    parcalar.append(f"YAPILACAK ({len(yapilacak)}):\n" + ("\n".join(
        satir(t, r, aciklama=True) for t, r in sirala(yapilacak)[:_BOLUM_SINIRI]) or "- yok"))
    if yaptim:
        parcalar.append(f"YAPTIM DEDİ, ÖĞRETMEN HENÜZ DEĞERLENDİRMEDİ ({len(yaptim)}):\n"
                        + "\n".join(satir(t, r) for t, r in sirala(yaptim)[:_BOLUM_SINIRI]))
    if gecmis:
        parcalar.append(f"SÜRESİ GEÇTİ, YAPTIM İŞARETİ YOK — son {_GECMIS_GUN} gün ({len(gecmis)}):\n"
                        + "\n".join(satir(t, r) for t, r in sirala(gecmis)[:_BOLUM_SINIRI]))
    if cozulmus:
        dagilim: dict[str, int] = {}
        for _, r in cozulmus:
            d = str(r.get("Ödev Durumu", "")).strip() or "?"
            dagilim[d] = dagilim.get(d, 0) + 1
        parcalar.append(f"ÖĞRETMEN DEĞERLENDİRDİ — son {_GECMIS_GUN} gün: {len(cozulmus)} ödev ("
                        + ", ".join(f"{k} {v}" for k, v in sorted(dagilim.items())) + ")")
    if eski:
        parcalar.append(f"Not (okura aktarma): teslimi {_GECMIS_GUN} günden eski {eski} ödev "
                        "bu listede yok. Yalnız eski ödevler sorulursa `ogrenci_verisi_ara` "
                        "ile bak.")
    metin = "\n\n".join(parcalar)
    return metin if sebit is None else metin + "\n\n" + _sebit_bolumu_metni(sebit, simdi)


# ── Live student data (plan Görev 2) ─────────────────────────────────────────
# Audit 2026-09-25 §2a/§3: the assistant could reach neither /api/schedule nor
# /api/calendar/unified nor /api/content(/weeks); it saw exams only through
# takvim titles and grades without rubrics. Each tool below reads what the
# dashboard page reads, through a callable the runtime is given
# (dashboard_api._canli_*). No callable, no declaration — as with odev_listesi.
PROGRAM_TOOL = "ders_programi"
SINAV_TOOL = "sinavlar"
TAKVIM_TOOL = "takvim"
ICERIK_TOOL = "ders_icerigi"
NOT_TOOL = "notlar"
# Added in Görev 3 (audit §1): EnglishCentral/Achieve3000 progress used to
# reach the model only as raw JSON in the BM25 index. Same wiring — a
# callable source, no source no declaration.
PLATFORM_TOOL = "platform_ilerlemesi"
# Tedy Books search (audit §1: `books/` was outside the file index entirely)
# lives in assistant_kitaplar.py; its own dispatch method below because,
# unlike the five tools above, a search returns several passage-level
# citations rather than one whole-answer citation.
KITAP_TOOL = assistant_kitaplar.TOOL_NAME
# MEBİ/SEBİTV video and content-summary metadata (audit §1: `Görünmez` —
# nothing served either file). Also its own dispatch method, for the same
# reason as KITAP_TOOL.
VIDEO_TOOL = "video_oner"

# chat_with_tools slices every tool_result to 4,000 chars; a body cut there
# loses its end silently, so each body is held under it here.
GOVDE_SINIRI = 3900

_ISTANBUL = ZoneInfo("Europe/Istanbul")


def istanbul_simdi(an: datetime | None = None) -> datetime:
    """Naive Istanbul wall clock. An aware time is converted; a naive one is
    taken as already local. With no argument the real clock is read in
    Istanbul, whatever zone the host runs on (it is Etc/UTC)."""
    if an is None:
        an = datetime.now(timezone.utc)
    if an.tzinfo is None:
        return an
    return an.astimezone(_ISTANBUL).replace(tzinfo=None)


def _katla(metin: Any) -> str:
    # Lazy: assistant_core imports this module when it builds the registry.
    from src.assistant_core import turkce_kucult_katla
    return turkce_kucult_katla(str(metin or "")).strip()


def html_metne(deger: Any) -> str:
    """Plain text from a fragment the portal sends as HTML — the dashboard's
    htmlToText (utils/formatters.ts). Tags become spaces rather than nothing,
    so "<p>a</p><p>b</p>" reads "a b", not "ab"."""
    s = str(deger or "")
    if not s:
        return ""
    if "<" in s or "&" in s:
        s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    return " ".join(s.split())


def _ayni_metin(a: str, b: str) -> bool:
    return " ".join(_katla(a).split()) == " ".join(_katla(b).split())


def aciklama_metni(aciklama: Any, baslik: Any) -> str:
    """A calendar description as text, or "" when it only repeats the title
    (TodaySchedule.tsx altBaslik): the portal sends most as "<p>{title}</p>"."""
    metin = html_metne(aciklama)
    return "" if not metin or _ayni_metin(metin, str(baslik or "")) else metin


def _zaman_oku(deger: Any) -> datetime | None:
    """An ISO time (naive, date-only or with an offset) or "DD.MM.YYYY HH:MM",
    as naive Istanbul wall clock; None when unreadable."""
    s = str(deger or "").strip()
    if not s:
        return None
    try:
        an = datetime.fromisoformat(s)
    except ValueError:
        try:
            an = datetime.strptime(s, "%d.%m.%Y %H:%M")
        except ValueError:
            return None
    return istanbul_simdi(an) if an.tzinfo else an


# The weekly grid, ported from dashboard/src/utils/schedule.ts. It is two
# tables side by side — Mon–Thu and Fri–Sun — each with its own time column,
# because Friday runs on a later bell (measured 2026-09-23: 2nd lesson 08:55
# vs 09:00, ten minutes apart by the 5th). Reading Friday's times from column 0
# puts every lesson five to ten minutes early.

def _gun_anahtari(s: str) -> str:
    """normDay: uppercase, dotted İ folded onto I. The portal writes
    "PAZARTESI" dotless; a Turkish-aware upper would give "PAZARTESİ"."""
    return str(s or "").strip().upper().replace("İ", "I")


def zaman_sutunu(baslik: list[Any], gun_idx: int) -> int:
    """timeColumnFor: the nearest blank header at or before the day's column;
    0 for a single-block grid."""
    for i in range(gun_idx - 1, -1, -1):
        if not str(baslik[i] or "").strip():
            return i
    return 0


def gun_sutunlari(baslik: list[Any], gunler: list[str] | tuple[str, ...]) -> list[tuple[str, int, int]]:
    """dayColumns: (day, lesson column, that day's time column) for each day
    the grid publishes; the pairing means a missing day cannot shift the rest."""
    out: list[tuple[str, int, int]] = []
    for gun in gunler:
        idx = next((i for i, h in enumerate(baslik) if _gun_anahtari(h) == _gun_anahtari(gun)), -1)
        if idx >= 0:
            out.append((gun, idx, zaman_sutunu(baslik, idx)))
    return out


# Cells that sit in a lesson column but are not lessons (TodaySchedule.tsx).
_ARA_HUCRELER = frozenset({"Kahvaltı", "Öğle yemeği", "İkindi Kahvaltısı", "Çıkış"})
_DERS_NO = re.compile(r"(\d+)\. Ders")
_SAAT_ARALIGI = re.compile(r"(\d{2}):(\d{2})\s*-\s*(\d{2}):(\d{2})")


def gunun_dersleri(rows: list[Any], gun: str) -> list[dict[str, Any]]:
    """One day's lessons in order, each with its own block's bell times and
    its name through normalize_course. Break rows are skipped: they are short
    rows whose cells do not line up with the day columns."""
    if not rows or not isinstance(rows[0], list):
        return []
    sutun = gun_sutunlari(rows[0], [gun])
    if not sutun:
        return []
    _, idx, zidx = sutun[0]
    dersler: list[dict[str, Any]] = []
    for row in rows[1:]:
        if not isinstance(row, list):
            continue
        zaman = str((row[zidx] if zidx < len(row) else "") or "")
        icerik = str((row[idx] if idx < len(row) else "") or "")
        if not icerik or icerik in _ARA_HUCRELER:
            continue
        no, saat = _DERS_NO.search(zaman), _SAAT_ARALIGI.search(zaman)
        if not no or not saat:
            continue
        dersler.append({
            "ders_no": int(no.group(1)),
            "baslangic": f"{saat.group(1)}:{saat.group(2)}",
            "bitis": f"{saat.group(3)}:{saat.group(4)}",
            "ders": normalize_course(icerik.split("\n")[0].strip()),
        })
    return dersler


def _gun_coz(gun: Any, simdi: datetime) -> datetime | None:
    """"bugün", "yarın" or a day name -> that date (a day name is its next
    occurrence, today included); None for the whole week. Case and Turkish
    letters do not matter ("PERSEMBE", "perşembe")."""
    s = _katla(gun)
    if not s:
        return None
    bugun = datetime(simdi.year, simdi.month, simdi.day)
    if s == "bugun":
        return bugun
    if s == "yarin":
        return bugun + timedelta(days=1)
    for i, ad in enumerate(_GUNLER):
        if _katla(ad) == s:
            return bugun + timedelta(days=(i - bugun.weekday()) % 7)
    raise ValueError(f"gün anlaşılmadı: {gun!r} — 'bugün', 'yarın' ya da bir gün adı ver")


def _ders_satiri(d: dict[str, Any], simdi: datetime | None = None) -> str:
    satir = f"- {d['ders_no']}. ders {d['baslangic']}–{d['bitis']} {d['ders']}"
    if simdi is not None:
        saat = f"{simdi:%H:%M}"
        if saat >= d["bitis"]:
            satir += " (bitti)"
        elif saat >= d["baslangic"]:
            satir += " (şu an)"
    return satir


def _gun_blogu(rows: list[Any], tarih: datetime, simdi: datetime) -> tuple[str, bool]:
    ad = _GUNLER[tarih.weekday()]
    fark = (tarih.date() - simdi.date()).days
    baslik = f"{ad} {tarih:%d.%m.%Y}" + {0: " (bugün)", 1: " (yarın)"}.get(fark, "")
    dersler = gunun_dersleri(rows, ad)
    if not dersler:
        if tarih.weekday() >= 5:
            return f"{baslik}: hafta sonu, okul yok.", False
        return f"{baslik}: programda ders yok.", False
    bugun_mu = simdi if fark == 0 else None
    return (f"{baslik} — {len(dersler)} ders:\n"
            + "\n".join(_ders_satiri(d, bugun_mu) for d in dersler)), True


_PROGRAM_NOTU = ("Not (okura aktarma): tatiller ve okul etkinlikleri bu tabloda görünmez; "
                 "bir günün tatil olup olmadığı okul takviminden okunur.")


def ders_programi_metni(hafta: Any, gun: Any, simdi: datetime) -> str:
    """The timetable for the model: one day (with its date) or the whole
    week. Raises ValueError for a day it cannot read."""
    bas = bugun_satiri(simdi)
    rows = ((hafta.get("schedule") or {}).get("rows") if isinstance(hafta, dict) else None) or []
    if not rows or not isinstance(rows[0], list) or not gun_sutunlari(rows[0], _GUNLER):
        return f"{bas}\nPortalda okunmuş bir ders programı yok."
    etiket = str(hafta.get("week_label") or "").strip()
    program = (f"Program: {etiket} — okulun haftalık programı her hafta aynıdır."
               if etiket else "Program: okulun haftalık programı (her hafta aynı).")

    tarih = _gun_coz(gun, simdi)
    if tarih is None:
        parcalar = [bas, program]
        for ad in _GUNLER:
            dersler = gunun_dersleri(rows, ad)
            if not dersler and ad in ("Cumartesi", "Pazar"):
                continue
            parcalar.append(f"{ad}:\n" + ("\n".join(_ders_satiri(d) for d in dersler) or "- ders yok"))
        parcalar.append(_PROGRAM_NOTU)
        return _kirp("\n\n".join(parcalar), GOVDE_SINIRI)

    blok, dersli = _gun_blogu(rows, tarih, simdi)
    parcalar = [bas, program, blok]
    if not dersli:
        # "Okul yok" is only half an answer: the next school day is what the
        # reader has to get ready for.
        for i in range(1, 8):
            sonraki = tarih + timedelta(days=i)
            sonraki_blok, var = _gun_blogu(rows, sonraki, simdi)
            if var:
                parcalar.append("Sonraki okul günü: " + sonraki_blok)
                break
    parcalar.append(_PROGRAM_NOTU)
    return _kirp("\n\n".join(parcalar), GOVDE_SINIRI)


def _tarih_yaz(deger: Any, simdi: datetime, tum_gun: bool = False) -> str:
    an = _zaman_oku(deger)
    if an is None:
        return "tarihi yok"
    saatsiz = tum_gun or len(str(deger).strip()) <= 10
    bicim = "%d.%m.%Y" if saatsiz else "%d.%m.%Y %H:%M"
    return f"{_GUNLER[an.weekday()]} {an.strftime(bicim)} ({_goreli(an, simdi)})"


_YAKLASAN_SINIRI = 15
_GECMIS_SINAV_SINIRI = 8


def sinavlar_metni(sinavlar: Any, simdi: datetime) -> str:
    """The exams as /api/exams lists them — upcoming by date, past newest
    first — with course, kind and date. The status is the API's own."""
    bas = bugun_satiri(simdi)
    satirlar = [e for e in (sinavlar or []) if isinstance(e, dict)]
    if not satirlar:
        return f"{bas}\nPortalda kayıtlı sınav yok."
    yaklasan = [e for e in satirlar if e.get("status") == "upcoming"]
    gecmis = [e for e in satirlar if e.get("status") != "upcoming"]

    def satir(e: dict[str, Any], ham_ad: bool) -> str:
        ders = str(e.get("course") or "").strip() or "Ders belirsiz"
        baslik = str(e.get("title") or "").strip()
        tur = baslik.split(" · ", 1)[1] if " · " in baslik else (baslik or "Sınav")
        metin = f"- {ders} — {tur} · {_tarih_yaz(e.get('date'), simdi, bool(e.get('allDay')))}"
        if str(e.get("grade") or "").strip():
            metin += f" · not {e['grade']}"
        ham = " ".join(str(e.get("rawTitle") or "").split())
        if ham_ad and ham and ham != baslik:
            metin += f"\n  Portaldaki adı: {_kirp(ham, 140)}"
        return metin

    parcalar = [bas + " (Sınavlar sayfasının listesi: portal takvimi ve not tablosu)"]
    govde = "\n".join(satir(e, True) for e in yaklasan[:_YAKLASAN_SINIRI]) or "- yok"
    if len(yaklasan) > _YAKLASAN_SINIRI:
        govde += f"\n(+{len(yaklasan) - _YAKLASAN_SINIRI} sınav daha)"
    parcalar.append(f"YAKLAŞAN SINAVLAR ({len(yaklasan)}):\n{govde}")
    govde = "\n".join(satir(e, False) for e in gecmis[:_GECMIS_SINAV_SINIRI]) or "- yok"
    if len(gecmis) > _GECMIS_SINAV_SINIRI:
        govde += f"\n(+{len(gecmis) - _GECMIS_SINAV_SINIRI} eski sınav daha)"
    parcalar.append(f"GEÇMİŞ SINAVLAR ({len(gecmis)}, en yenisi önce):\n{govde}")
    if any(not e.get("date") for e in gecmis):
        # /api/exams synthesises these from graded columns; measured
        # 2026-09-25 the grade table was still 2025-2026's.
        parcalar.append("Not (okura aktarma): tarihi olmayan sınavlar not tablosundan türetildi; "
                        "o tablo önceki bir öğretim yılına ait olabilir, bu yılın sınavı gibi sunma.")
    return _kirp("\n\n".join(parcalar), GOVDE_SINIRI)


# /api/calendar/unified's kinds this tool speaks for. Lessons and homework
# deadlines are left out on purpose: ders_programi and odev_listesi read them
# with the bell times and the "Yaptım" marks this list does not carry.
_TAKVIM_TURLERI = {
    "event": "okul takvimi",
    "private_lesson": "özel ders",
    "sebit": "SEBİT ödevi",
    "ogep": "ÖGEP",
    "team": "takım çalışması",
}
_TAKVIM_VARSAYILAN_GUN = 14
_TAKVIM_EN_COK_GUN = 60
_TAKVIM_SATIR_SINIRI = 40


def _gun_sayisi(deger: Any) -> int:
    try:
        n = int(deger)
    except (TypeError, ValueError):
        return _TAKVIM_VARSAYILAN_GUN
    return max(1, min(_TAKVIM_EN_COK_GUN, n))


def _ne_zaman(bas: datetime, son: datetime, tum_gun: bool) -> str:
    gun = f"{_GUNLER[bas.weekday()]} {bas:%d.%m}"
    if bas.date() != son.date():
        if tum_gun:
            return f"{gun} → {_GUNLER[son.weekday()]} {son:%d.%m}"
        return f"{gun} {bas:%H:%M} → {_GUNLER[son.weekday()]} {son:%d.%m} {son:%H:%M}"
    if tum_gun or (bas.hour, bas.minute) == (0, 0) == (son.hour, son.minute):
        return f"{gun} (tüm gün)"
    if son > bas:
        return f"{gun} {bas:%H:%M}–{son:%H:%M}"
    return f"{gun} {bas:%H:%M}"


def takvim_metni(etkinlikler: Any, simdi: datetime, gun_sayisi: Any = _TAKVIM_VARSAYILAN_GUN) -> str:
    """The unified calendar from today for N days: school events (with their
    description and place), private lessons, SEBİT assignments, ÖGEP and team
    sessions. An event that started earlier and is still running is in."""
    n = _gun_sayisi(gun_sayisi)
    bas = bugun_satiri(simdi)
    pencere_bas = datetime(simdi.year, simdi.month, simdi.day)
    pencere_son = pencere_bas + timedelta(days=n)
    aralik = f"{pencere_bas:%d.%m}–{pencere_son - timedelta(days=1):%d.%m.%Y}"

    secilen: list[tuple[datetime, datetime, dict[str, Any]]] = []
    for e in etkinlikler or []:
        if not isinstance(e, dict) or e.get("type") not in _TAKVIM_TURLERI:
            continue
        basla = _zaman_oku(e.get("start"))
        if basla is None:
            continue
        bitir = _zaman_oku(e.get("end")) or basla
        if bitir < pencere_bas or basla >= pencere_son:
            continue
        secilen.append((basla, bitir, e))
    secilen.sort(key=lambda x: x[0])
    if not secilen:
        return (f"{bas}\nÖnümüzdeki {n} günde ({aralik}) takvimde bir şey yok. "
                "(Dersler ve ödev teslimleri bu listede değil.)")

    satirlar = []
    for basla, bitir, e in secilen[:_TAKVIM_SATIR_SINIRI]:
        baslik = " ".join(str(e.get("title") or "").split()) or "(adsız)"
        tur = e.get("type")
        satir = f"- {_ne_zaman(basla, bitir, bool(e.get('allDay')))} · {baslik} [{_TAKVIM_TURLERI[tur]}]"
        ek = [str(x).strip() for x in (e.get("course") if tur == "sebit" else "",
                                       e.get("status") if tur in ("sebit", "ogep", "team") else "")
              if str(x or "").strip()]
        if ek:
            satir += " (" + ", ".join(ek) + ")"
        aciklama = aciklama_metni(e.get("description"), baslik)
        if aciklama:
            satir += f"\n  {_kirp(aciklama, 240)}"
        yer = html_metne(e.get("location"))
        if yer:
            satir += f"\n  Yer: {_kirp(yer, 100)}"
        satirlar.append(satir)
    if len(secilen) > _TAKVIM_SATIR_SINIRI:
        satirlar.append(f"(+{len(secilen) - _TAKVIM_SATIR_SINIRI} etkinlik daha; daha kısa bir aralık iste)")
    return _kirp(f"{bas}\nÖnümüzdeki {n} gün ({aralik}), {len(secilen)} kayıt:\n"
                 + "\n".join(satirlar)
                 + "\n\nNot (okura aktarma): dersler ve ödev teslimleri bu listede yok.", GOVDE_SINIRI)


# Course content cards carry the portal's own chrome ("Daha fazla oku",
# "Yorum Ekle") and, between "Daha fazla oku" and "Yorum Ekle", the comment
# block: other children's names, like counts and comments. None of it is the
# teacher's content, and the names are not ours to pass on.
_ICERIK_SUSU = re.compile(
    r"^(?:Daha fazla oku|Yorum Ekle|İlk yorum yapan sen olmak ister misin\?|\d+ Yorum yapıldı!)$")


def _temiz_icerik(metin: Any) -> str:
    satirlar: list[str] = []
    yorumda = False
    for ham in str(metin or "").split("\n"):
        s = ham.strip()
        if s == "Daha fazla oku":
            yorumda = True
            continue
        if s == "Yorum Ekle" or not s:
            yorumda = False
            if not s and satirlar and satirlar[-1]:
                satirlar.append("")
            continue
        if yorumda or _ICERIK_SUSU.match(s):
            continue
        satirlar.append(s)
    return "\n".join(satirlar).strip()


def _duz(metin: str) -> str:
    return " ".join(_katla(metin).split())


def icerik_ozeti(kayit: Any) -> str:
    """A course's weekly content, readable: the `text` the portal rendered,
    plus any item, card or table row that text does not already contain
    (cards mostly repeat it). A course whose read failed carries only
    `error` — a Selenium trace — and yields nothing."""
    if not isinstance(kayit, dict):
        return ""
    govde = _temiz_icerik(kayit.get("text"))
    icinde = _duz(govde)
    ekler: list[str] = []

    def ekle(parca: str, madde: bool = False) -> None:
        nonlocal icinde
        if parca and _duz(parca) not in icinde:
            ekler.append(f"- {parca}" if madde else parca)
            icinde += " " + _duz(parca)

    for item in kayit.get("items") or []:
        if isinstance(item, dict):
            item = item.get("title") or item.get("konu") or item.get("text") or ""
        ekle(" ".join(str(item or "").split()), madde=True)
    for kart in kayit.get("cards") or []:
        if isinstance(kart, dict):
            kart = kart.get("text") or ""
        ekle(_temiz_icerik(kart))
    for tablo in kayit.get("tables") or []:
        satirlar = tablo.get("rows") if isinstance(tablo, dict) else tablo
        for r in satirlar or []:
            if isinstance(r, list):
                ekle(" | ".join(str(c).strip() for c in r if str(c or "").strip()))
    return "\n".join(x for x in (govde, *ekler) if x).strip()


def _icerik_var(kayit: Any) -> bool:
    return isinstance(kayit, dict) and any(kayit.get(k) for k in ("text", "items", "cards", "tables"))


def guncel_hafta_dersleri(guncel: Any, o_hafta: Any) -> dict[str, Any]:
    """The open week, course by course: `ders_icerikleri` (what /api/content
    serves) where this run read the course, else that week's entry in
    `ders_icerikleri_haftalar`. Measured 2026-09-25: every course in
    `ders_icerikleri` carried only a Selenium `error` while the same week in
    `ders_icerikleri_haftalar` held all of it."""
    guncel = guncel if isinstance(guncel, dict) else {}
    o_hafta = o_hafta if isinstance(o_hafta, dict) else {}
    dersler: dict[str, Any] = {}
    for ad in [*guncel, *(k for k in o_hafta if k not in guncel)]:
        g, h = guncel.get(ad), o_hafta.get(ad)
        dersler[ad] = g if _icerik_var(g) or h is None else h
    return dersler


def _hafta_no(etiket: Any) -> int | None:
    m = re.match(r"\s*(\d+)\s*\.", str(etiket or ""))
    return int(m.group(1)) if m else None


def _ders_bul(sorgu: Any, adlar: list[str]) -> str | None:
    """A course the reader named -> the canonical name in this week's list:
    through normalize_course ("DKAB" -> "Din Kültürü"), then case- and
    letter-insensitive exact, prefix ("mat") and substring match."""
    q = _katla(normalize_course(str(sorgu or "")))
    if not q:
        return None
    katli = {ad: _katla(ad) for ad in adlar}
    for kosul in (lambda k: k == q, lambda k: k.startswith(q), lambda k: q in k):
        for ad in adlar:
            if kosul(katli[ad]):
                return ad
    return None


def ders_icerigi_metni(kaynak: Any, ders: Any, hafta: Any) -> tuple[str, str]:
    """(body, citation label) for one course's content in a week, or the
    week's course list when no course is named.

    The current week comes from `ders_icerikleri` — the open week, as
    /api/content serves it — and a course whose read failed this run falls
    back to that week's entry in `ders_icerikleri_haftalar`; any other week
    comes from `ders_icerikleri_haftalar` (/api/content/weeks)."""
    kaynak = kaynak if isinstance(kaynak, dict) else {}
    guncel = kaynak.get("guncel") if isinstance(kaynak.get("guncel"), dict) else {}
    haftalar = kaynak.get("haftalar") if isinstance(kaynak.get("haftalar"), dict) else {}
    guncel_etiket = str(kaynak.get("guncel_hafta") or "")
    guncel_no = _hafta_no(guncel_etiket)
    if hafta not in (None, ""):
        try:
            hafta = int(hafta)
        except (TypeError, ValueError):
            raise ValueError(f"hafta bir sayı olmalı: {hafta!r}") from None
    else:
        hafta = None

    if hafta is None or hafta == guncel_no:
        hafta_etiketi, no = guncel_etiket, guncel_no
        dersler = guncel_hafta_dersleri(guncel, haftalar.get(guncel_etiket))
    else:
        bulunan = next((e for e in haftalar if _hafta_no(e) == hafta), None)
        if bulunan is None or not isinstance(haftalar.get(bulunan), dict):
            mevcut = sorted({n for n in map(_hafta_no, haftalar) if n})
            liste = ", ".join(map(str, mevcut)) or "yok"
            return (f"{hafta}. hafta için toplanmış ders içeriği yok. Toplanan haftalar: {liste}.",
                    "Ders içerikleri")
        hafta_etiketi, no, dersler = bulunan, hafta, haftalar[bulunan]

    gruplar: dict[str, list[tuple[str, Any]]] = {}
    for ad, kayit in dersler.items():
        gruplar.setdefault(normalize_course(str(ad)) or str(ad), []).append((str(ad), kayit))
    hafta_adi = hafta_etiketi or "güncel hafta"

    if not str(ders or "").strip():
        satirlar = []
        for kanon, girdiler in gruplar.items():
            ozet = " ".join(" ".join(icerik_ozeti(k).split()) for _, k in girdiler).strip()
            if ozet:
                satirlar.append(f"- {kanon} — {_kirp(ozet, 140)}")
            elif any(isinstance(k, dict) and k.get("error") for _, k in girdiler):
                satirlar.append(f"- {kanon} — portal bu dersin içeriğini okuyamadı")
            else:
                satirlar.append(f"- {kanon} — bu hafta içerik yok")
        metin = (f"{hafta_adi} — ders içerikleri ({len(gruplar)} ders):\n" + "\n".join(satirlar)
                 + "\n\nNot (okura aktarma): bir dersin tamamı için `ders` ver.")
        etiket = f"Ders içerikleri · {no}. hafta" if no else "Ders içerikleri"
        return _kirp(metin, GOVDE_SINIRI), etiket

    hedef = _ders_bul(ders, list(gruplar))
    if hedef is None:
        return (f"'{ders}' adlı ders {hafta_adi} içeriklerinde yok. Bu haftanın dersleri: "
                f"{', '.join(gruplar) or 'yok'}.", "Ders içerikleri")
    girdiler = gruplar[hedef]
    bloklar = []
    for ad, kayit in girdiler:
        ozet = icerik_ozeti(kayit)
        if ozet:
            bloklar.append((f"[{ad}]\n" if len(girdiler) > 1 else "") + ozet)
    if bloklar:
        govde = "\n\n".join(bloklar)
    elif any(isinstance(k, dict) and k.get("error") for _, k in girdiler):
        govde = "Portal bu dersin içeriğini bu hafta okuyamadı."
    else:
        govde = "Bu hafta bu ders için yayımlanmış içerik yok."
    etiket = f"{hedef} · {no}. hafta içeriği" if no else f"{hedef} · ders içeriği"
    return _kirp(f"{hedef} — {hafta_adi}:\n{govde}", GOVDE_SINIRI), etiket


def notlar_metni(kaynak: Any) -> tuple[str, str]:
    """(body, citation label): the gelişim report's grades and outcome levels
    with the term's name. A report from an earlier school year — the portal
    kept showing 2025-2026's "4. Arakarne" well into 2026-2027 — says so
    before anything else, so last year's grade is never read as this year's."""
    kaynak = kaynak if isinstance(kaynak, dict) else {}
    g = kaynak.get("gelisim") if isinstance(kaynak.get("gelisim"), dict) else {}
    yil = str(kaynak.get("ogretim_yili") or "").strip()
    donem = str(g.get("semester") or "").strip()
    etiket = f"Notlar · {donem}" if donem else "Notlar"

    notlar = []
    for r in g.get("grades") or []:
        if not isinstance(r, dict):
            continue
        sutunlar = [f"{k} {v}" for k, v in r.items()
                    if k != "Ders" and str(v or "").strip() not in ("", "-")]
        if sutunlar:
            notlar.append(f"- {str(r.get('Ders') or '').strip()} · " + " · ".join(sutunlar))
    rubrikler = [r for r in g.get("rubrics") or [] if isinstance(r, dict) and r.get("kazanim")]

    if not notlar and not rubrikler:
        yil_ad = f"{yil} öğretim yılı" if yil else "Bu öğretim yılı"
        return f"{yil_ad} için portalda henüz not ya da kazanım düzeyi yok.", etiket

    parcalar = []
    if donem:
        parcalar.append(f"Dönem: {donem}")
    m = re.search(r"(\d{4})\s*-\s*(\d{4})", donem)
    if m and yil and f"{m.group(1)}-{m.group(2)}" != yil:
        parcalar.append(f"ÖNCEKİ ÖĞRETİM YILI: portalın gelişim raporu {m.group(1)}-{m.group(2)} "
                        f"yılını gösteriyor; şu an {yil} öğretim yılı ve bu yıl için not girilmemiş. "
                        "Bu notları bu yılın notu gibi sunma.")
    if notlar:
        parcalar.append(f"NOTLAR ({len(notlar)} ders):\n" + "\n".join(notlar))
    if rubrikler:
        dagilim: dict[str, dict[str, int]] = {}
        for r in rubrikler:
            d = dagilim.setdefault(str(r.get("ders") or "").strip() or "?", {})
            duzey = str(r.get("duzey") or "").strip() or "?"
            d[duzey] = d.get(duzey, 0) + 1
        parcalar.append(f"KAZANIM DÜZEYLERİ ({len(rubrikler)} kazanım):\n" + "\n".join(
            f"{ders}: " + ", ".join(f"{k} {v}" for k, v in sorted(say.items()))
            for ders, say in dagilim.items()))
    metin = "\n\n".join(parcalar)

    if rubrikler:
        ayrinti, kalan = [], len(rubrikler)
        uzunluk = len(metin) + len("\n\nKAZANIMLAR:\n")
        for r in rubrikler:
            satir = (f"- {str(r.get('ders') or '').strip()} · {str(r.get('alan') or '').strip()}: "
                     f"{_kirp(' '.join(str(r['kazanim']).split()), 160)} → {str(r.get('duzey') or '').strip()}")
            if uzunluk + len(satir) + 1 > GOVDE_SINIRI - 40:
                break
            ayrinti.append(satir)
            uzunluk += len(satir) + 1
            kalan -= 1
        if ayrinti:
            metin += "\n\nKAZANIMLAR:\n" + "\n".join(ayrinti)
        if kalan:
            metin += f"\n(+{kalan} kazanım daha)"
    return _kirp(metin, GOVDE_SINIRI), etiket


# EnglishCentral and Achieve3000 carry one scrape timestamp for the whole
# file, never a per-video/per-lesson one — so "last activity" is honestly
# "when this file was last read", not an invented per-item time.
_PLATFORM_SATIR_SINIRI = 8


def _platform_zaman_notu(scraped_at: Any) -> str:
    an = _zaman_oku(scraped_at)
    if an is None:
        return "bu verinin ne zaman okunduğu bilinmiyor"
    return f"bu veri {_GUNLER[an.weekday()]} {an:%d.%m.%Y %H:%M} tarihinde okundu"


def _ec_bolumu(ec: Any) -> str:
    ec = ec if isinstance(ec, dict) else {}
    videolar = [v for v in (ec.get("videos") or []) if isinstance(v, dict)]
    toplam = ec.get("total_videos")
    toplam = toplam if isinstance(toplam, int) else len(videolar)
    tamam = ec.get("completed_videos")
    tamam = tamam if isinstance(tamam, int) else sum(1 for v in videolar if v.get("completed"))
    if not videolar and not toplam:
        return "ENGLISHCENTRAL: portalda kayıtlı video yok."
    eksikler = [v for v in videolar if not v.get("completed")]
    satirlar = "\n".join(
        f"- {str(v.get('title') or '?').strip()} (düzey {v.get('difficulty', '?')})"
        for v in eksikler[:_PLATFORM_SATIR_SINIRI]) or "- yok"
    govde = f"ENGLISHCENTRAL — {tamam}/{toplam} video tamamlandı:\nKALAN VİDEOLAR:\n{satirlar}"
    if len(eksikler) > _PLATFORM_SATIR_SINIRI:
        govde += f"\n(+{len(eksikler) - _PLATFORM_SATIR_SINIRI} video daha)"
    return govde + f"\n({_platform_zaman_notu(ec.get('scraped_at'))}.)"


def _a3k_bolumu(a3k: Any) -> str:
    a3k = a3k if isinstance(a3k, dict) else {}
    dersler = [x for x in (a3k.get("lessons") or [])
              if isinstance(x, dict) and x.get("is_teacher_assigned") is not False]
    hedef = a3k.get("teacher_assigned_count")
    hedef = hedef if isinstance(hedef, int) else len(dersler)
    tamam = a3k.get("teacher_assigned_completed")
    tamam = tamam if isinstance(tamam, int) else sum(1 for x in dersler if x.get("completed"))
    if not dersler and not hedef:
        return "ACHIEVE3000: portalda öğretmenin atadığı ders yok."
    eksikler = [x for x in dersler if not x.get("completed")]
    satirlar = "\n".join(
        f"- {str(x.get('title') or '?').strip()} ({str(x.get('category') or '?').strip()}) "
        f"{x.get('completed_steps', 0)}/{x.get('total_steps', 0)} adım"
        for x in eksikler[:_PLATFORM_SATIR_SINIRI]) or "- yok"
    govde = f"ACHIEVE3000 — {tamam}/{hedef} ders tamamlandı:\nKALAN DERSLER:\n{satirlar}"
    if len(eksikler) > _PLATFORM_SATIR_SINIRI:
        govde += f"\n(+{len(eksikler) - _PLATFORM_SATIR_SINIRI} ders daha)"
    stats = a3k.get("dashboard_stats") if isinstance(a3k.get("dashboard_stats"), dict) else {}
    if stats.get("firstTryScore") is not None:
        govde += f"\nİlk deneme skoru: {stats['firstTryScore']}"
    return govde + f"\n({_platform_zaman_notu(a3k.get('scraped_at'))}.)"


def platform_ilerlemesi_metni(veri: Any) -> str:
    """EnglishCentral and Achieve3000 progress, readable: what is done, what
    is left (with EnglishCentral's difficulty level), and when the data was
    last read — never the raw JSON the BM25 index used to carry (audit §1)."""
    veri = veri if isinstance(veri, dict) else {}
    return _kirp("\n\n".join((_ec_bolumu(veri.get("ec")), _a3k_bolumu(veri.get("a3k")))), GOVDE_SINIRI)


# ── video_oner: MEBİ + SEBİTV discovery catalogs (audit §1: "Görünmez" — no
# route or index reached either file) ────────────────────────────────────────
_VIDEO_SATIR_SINIRI = 12
_KAYNAK_ADI = {"mebi": "MEBİ", "sebitv": "SEBİTV"}


def _ogretim_yili_etiketi(tarih: datetime) -> str:
    """Sept–Aug Turkish school year label for a date, e.g. 18.02.2026 (Şubat,
    okulun ikinci yarısı) -> "2025-2026". Derived, never hardcoded."""
    baslangic = tarih.year if tarih.month >= 9 else tarih.year - 1
    return f"{baslangic}-{baslangic + 1}"


def _katalog_zaman_ifadesi(kaynak: str, toplanma: Any) -> str:
    """Fix round 1 (denetim'in 'sınıf etiketlenir' bulgusu): kayıtların
    sınıf alanı yok (0/769 doğrulandı, gerçek kontrolde), ama var olan tek
    somut kanıt kataloğun kendi toplanma zamanıdır — dosyanın mtime'ı
    (`dashboard_api._kaynak_toplanma_zamani`, içerikte tarih yok). `toplanma`
    okunamazsa tarih iddia edilmez."""
    ad = _KAYNAK_ADI.get(kaynak, kaynak.upper())
    an = _zaman_oku(toplanma)
    if an is None:
        return f"{ad} kataloğunun toplanma zamanı bilinmiyor"
    return f"{ad} kataloğu {_ogretim_yili_etiketi(an)} öğretim yılında ({an:%d.%m.%Y}) toplandı"


_VIDEO_BILDIRIM: dict[str, Any] = {
    "name": VIDEO_TOOL,
    "description": (
        "MEBİ ve SEBİTV video/konu anlatımı kataloğunda konuya göre arama yapar: başlık, ders, "
        "ünite ve (kayıtta varsa) doğrudan bağlantı döner. 'X konusunda video var mı' sorularında "
        "BU aracı kullan. Kataloğun sınıf bilgisi yok — bunu okura söyle, sınıf uydurma; "
        "kataloğun ne zaman toplandığı verilir, o toplanma zamanından çıkan öğretim yılını söyle."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "konu": {"type": "string",
                     "description": "Aranacak konu (ör. 'kesirler', 'fotosentez')."},
            "ders": {"type": "string",
                     "description": "Dersle daraltmak için (ör. 'Matematik'). Boş bırakılırsa tüm derslerde arar."},
        },
        "required": ["konu"],
    },
}


def _ders_eslesir(v_ders: Any, hedef: Any) -> bool:
    a = _katla(normalize_course(str(v_ders or "")))
    b = _katla(normalize_course(str(hedef or "")))
    return bool(a) and bool(b) and (b in a or a in b)


def _video_metin_alanlari(v: dict[str, Any]) -> str:
    return " ".join(str(v.get(k) or "") for k in ("topic", "unit", "subSubject", "title", "course"))


def _video_puanla(v: dict[str, Any], q_tokens: list[str]) -> int:
    metin = _katla(_video_metin_alanlari(v))
    return sum(1 for t in q_tokens if t and t in metin)


def _video_satiri(v: dict[str, Any], kaynak: str) -> str:
    konu = str(v.get("topic") or v.get("title") or "").strip() or "adsız"
    if kaynak == "sebitv":
        baslik = str(v.get("title") or "").strip()
        if baslik and baslik != konu:
            konu = f"{konu} — {baslik}"
    ders = str(v.get("course") or "").strip()
    unite = str(v.get("unit") or "").strip()
    tur = "MEBİ videosu" if kaynak == "mebi" else "SEBİTV içeriği"
    satir = f"- {konu}"
    if ders:
        satir += f" · {ders}"
    if unite:
        satir += f" ({unite})"
    satir += f" [{tur}]"
    # A link only when the catalog itself carries one — MEBİ's cdnUrl. SEBİTV
    # entries never carry a link; none is built from resourceId/code.
    baglanti = str(v.get("cdnUrl") or "").strip() if kaynak == "mebi" else ""
    if baglanti:
        satir += f"\n  Bağlantı: {baglanti}"
    return satir


def _video_etiket(v: dict[str, Any], kaynak: str) -> str:
    konu = str(v.get("topic") or v.get("title") or "adsız").strip()
    ders = str(v.get("course") or "").strip()
    tur = "MEBİ" if kaynak == "mebi" else "SEBİTV"
    return f"{tur} · {ders} · {konu}" if ders else f"{tur} · {konu}"


def video_oner_metni(veri: Any, konu: Any, ders: Any = None) -> tuple[str, list[dict[str, Any]]]:
    """(body, citations): MEBİ and SEBİTV catalog rows whose topic, unit,
    sub-subject, title or course matches `konu`, optionally narrowed by
    `ders`. A link is only ever copied from the catalog's own field, never
    built from an id."""
    konu = str(konu or "").strip()
    q_tokens = [t for t in _katla(konu).split() if t]
    if not q_tokens:
        return "Aranacak bir konu verilmedi.", []

    veri = veri if isinstance(veri, dict) else {}
    aday: list[tuple[int, str, dict[str, Any]]] = []
    for kaynak in ("mebi", "sebitv"):
        for v in veri.get(kaynak) or []:
            if not isinstance(v, dict):
                continue
            if ders and not _ders_eslesir(v.get("course"), ders):
                continue
            puan = _video_puanla(v, q_tokens)
            if puan > 0:
                aday.append((puan, kaynak, v))
    if not aday:
        return f"'{konu}' konusunda kayıtlı video ya da içerik bulunamadı.", []

    aday.sort(key=lambda x: -x[0])
    secilenler = aday[:_VIDEO_SATIR_SINIRI]
    satirlar = [_video_satiri(v, kaynak) for _, kaynak, v in secilenler]
    # Only the catalogs actually represented among the results get a
    # sentence — a sentence about a catalog that matched nothing is noise.
    kaynaklar_gorulen = sorted({kaynak for _, kaynak, _ in secilenler})
    zaman_ifadeleri = [_katalog_zaman_ifadesi(k, veri.get(f"{k}_toplanma")) for k in kaynaklar_gorulen]
    sinif_notu = "Not (okura aktarma): " + "; ".join(zaman_ifadeleri) + "; kayıtlarda sınıf bilgisi yok."
    metin = (f"'{konu}' için {len(aday)} kayıt (ilk {len(secilenler)}):\n"
            + "\n".join(satirlar) + "\n\n" + sinif_notu)
    max_puan = secilenler[0][0] or 1
    citations = [{
        "kind": "ogrenci",
        "label": _video_etiket(v, kaynak),
        "locator": {"tool": VIDEO_TOOL, "kaynak": kaynak,
                    "uuid": v.get("uuid"), "resourceId": v.get("resourceId")},
        "snippet": _video_satiri(v, kaynak)[:400],
        "confidence": round(min(1.0, puan / max_puan), 4),
    } for puan, kaynak, v in secilenler]
    return _kirp(metin, GOVDE_SINIRI), citations


# What the source was, for "… okunamadı" when it fails.
_OKUNAMADI = {
    PROGRAM_TOOL: "ders programı",
    SINAV_TOOL: "sınav listesi",
    TAKVIM_TOOL: "takvim",
    ICERIK_TOOL: "ders içerikleri",
    NOT_TOOL: "notlar",
    PLATFORM_TOOL: "platform ilerlemesi",
}

_OGRENCI_BILDIRIMLERI: dict[str, dict[str, Any]] = {
    PROGRAM_TOOL: {
        "name": PROGRAM_TOOL,
        "description": (
            "Işık'ın haftalık ders programı, Bugün ve Dersler sayfalarının okuduğu tablodan: "
            "günün dersleri sırasıyla, her biri kendi zil saatiyle (Cuma'nın zili farklıdır). "
            "'Bugün/yarın hangi dersler var', 'Cuma ilk ders ne', 'kaçta biter' soruları için "
            "BU aracı kullan. 'bugün' ve 'yarın' İstanbul tarihine göre çözülür."
        ),
        "parameters": {"type": "object", "properties": {"gun": {
            "type": "string",
            "description": "'bugün', 'yarın' ya da gün adı (ör. 'Cuma'). Boş bırakılırsa bütün hafta."}}},
    },
    SINAV_TOOL: {
        "name": SINAV_TOOL,
        "description": (
            "Işık'ın sınavları, Sınavlar ve İşler sayfalarının listesiyle aynı: yaklaşanlar "
            "(ders, tür, tarih-saat) ve geçmişler (varsa notuyla). Sınav tarihi ve 'hangi "
            "sınavlar var' soruları için BU aracı kullan."
        ),
        "parameters": {"type": "object", "properties": {}},
    },
    TAKVIM_TOOL: {
        "name": TAKVIM_TOOL,
        "description": (
            "Okul takvimi ve Işık'ın ajandası, Takvim sayfasının birleşik listesinden, bugünden "
            "itibaren: okul etkinlikleri (açıklama ve yeriyle), özel dersler, SEBİT ödevleri, "
            "ÖGEP ve takım çalışmaları. Tatil, tören, gezi, veli toplantısı, özel ders "
            "soruları için BU aracı kullan. Dersler ve ödev teslimleri bu listede yoktur."
        ),
        "parameters": {"type": "object", "properties": {"gun_sayisi": {
            "type": "integer",
            "description": "Bugünden itibaren kaç gün (1–60, varsayılan 14)."}}},
    },
    ICERIK_TOOL: {
        "name": ICERIK_TOOL,
        "description": (
            "Öğretmenlerin portalda yayımladığı haftalık ders içeriği (Dersler sayfası): o "
            "hafta işlenen konu, öğretmenin notu ve maddeleri. `ders` verilmezse o haftanın "
            "ders listesi döner; `hafta` verilmezse güncel hafta."
        ),
        "parameters": {"type": "object", "properties": {
            "ders": {"type": "string", "description": "Ders adı (ör. 'Matematik', 'Fen')."},
            "hafta": {"type": "integer", "description": "Öğretim yılının kaçıncı haftası (ör. 3)."}}},
    },
    NOT_TOOL: {
        "name": NOT_TOOL,
        "description": (
            "Işık'ın gelişim raporu (Notlar sayfası): derslere göre sınav ve performans "
            "notları ile kazanım düzeyleri, dönem adıyla. Rapor önceki öğretim yılına aitse "
            "sonuç bunu açıkça söyler."
        ),
        "parameters": {"type": "object", "properties": {}},
    },
    PLATFORM_TOOL: {
        "name": PLATFORM_TOOL,
        "description": (
            "Işık'ın dil/okuma platformlarındaki ilerlemesi (Platform İlerleme kartı): "
            "EnglishCentral'da tamamlanan/kalan video (düzeyleriyle) ve Achieve3000'de "
            "öğretmenin atadığı derslerden tamamlanan/kalan, ilk deneme skoruyla. Veri en son "
            "ne zaman okunduysa onu söyler. 'EnglishCentral/Achieve3000'de ne durumdayım' gibi "
            "sorularda BU aracı kullan."
        ),
        "parameters": {"type": "object", "properties": {}},
    },
}


MCP_SERVERS = {
    "maarif-mufredat": ("https://mufredat.cureonics.com/mcp",
                        "MUFREDAT_MCP_API_KEY"),
    "egitim-kaynak": ("https://egitim-kaynak.cureonics.com/mcp",
                      "EGITIM_KAYNAK_MCP_API_KEY"),
}


@dataclass
class ToolOutcome:
    ok: bool
    text: str = ""
    citations: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    # MCP image content, [{data (base64), mimeType}] — for the model's eyes
    # only: chat_with_tools puts up to two in the tool_result. Never copied
    # into a citation; the reader's panel fetches /api/assistant/figure/<id>.
    images: list[dict[str, Any]] = field(default_factory=list)


def sanitize_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """MCP inputSchema -> a declaration parameter block.

    Becomes the tool's `input_schema` on the Messages API (Claude, since
    2026-09-24). A sanitiser rather than a rewriter: it drops `title` noise and
    collapses anyOf[T, null] to T, keeping every description byte-for-byte and
    the element type of every array. Doing it in one place means a model that
    stops accepting some construct needs one fix.
    """
    props: dict[str, Any] = {}
    for key, spec in (schema.get("properties") or {}).items():
        if "anyOf" in spec:
            non_null = [a for a in spec["anyOf"] if a.get("type") != "null"]
            base = dict(non_null[0]) if non_null else {"type": "string"}
        else:
            base = {"type": spec.get("type", "string")}
        clean: dict[str, Any] = {"type": base.get("type", "string")}
        if spec.get("description"):
            clean["description"] = spec["description"]
        if spec.get("enum"):
            clean["enum"] = spec["enum"]
        if clean["type"] == "array":
            # An array without `items` is what took the assistant down: from
            # 2026-09-22 every model answered 400 INVALID_ARGUMENT
            # "…[include_fragments].items: missing field", because this kept
            # only type/description/enum and dropped the element type.
            items = base.get("items") or spec.get("items") or {}
            item = {"type": items.get("type", "string")} if isinstance(items, dict) else {"type": "string"}
            if isinstance(items, dict) and items.get("enum"):
                item["enum"] = items["enum"]
            clean["items"] = item
        props[key] = clean
    return {
        "type": "object",
        "properties": props,
        "required": list(schema.get("required") or []),
    }


# ogrenci_verisi_ara's tool body (task-1 brief §5): the model gets the full
# chunk text, not the 260-char citation snippet — capped per hit so one huge
# chunk cannot crowd out the rest, and in total so the whole body fits inside
# chat_with_tools' 4,000-char per-result truncation (assistant_core.py
# ChatClient.chat_with_tools slices tool_result content to [:4000]).
_YEREL_ISABET_SINIRI = 1200
_YEREL_TOPLAM_SINIRI = 3900


def _kirp(metin: str, sinir: int) -> str:
    if len(metin) <= sinir:
        return metin
    if sinir <= 2:
        return metin[:sinir]
    govde = sinir - 2  # reserve room for the " …" suffix itself
    kesik = metin[:govde].rsplit(" ", 1)[0]
    return (kesik or metin[:govde]) + " …"


def _yerel_tam_metin(rows: list[dict[str, Any]]) -> str:
    """Each hit's full chunk text (not the snippet), joined; per-hit and
    total budgets both enforced so the model reads more than a 260-char
    fragment without the body blowing past chat_with_tools' cutoff."""
    parcalar: list[str] = []
    toplam = 0
    for r in rows:
        parca = str(r.get("text") or r.get("snippet") or "").strip()
        if not parca:
            continue
        parca = _kirp(parca, _YEREL_ISABET_SINIRI)
        ayrac = 2 if parcalar else 0  # "\n\n" between hits
        if toplam + ayrac + len(parca) > _YEREL_TOPLAM_SINIRI:
            kalan = _YEREL_TOPLAM_SINIRI - toplam - ayrac
            if kalan > 0:
                parcalar.append(_kirp(parca, kalan))
            break
        parcalar.append(parca)
        toplam += ayrac + len(parca)
    return "\n\n".join(parcalar) or "(kayıt yok)"


# content/eba and content/sebitv filenames carry the grade as a bare digit
# token, e.g. "Matematik 6 1. Kitap.pdf" (6 = grade, "1." = volume number —
# the trailing period on "1." is what tells the two apart: isdigit() is
# False for "1."). Unmatched filenames keep their plain basename label.
_SINIF_ETIKETLI_DIZINLER = ("content/eba/", "content/sebitv/")


def _sinif_etiketi_dosyadan(dosya_adi: str) -> str | None:
    kok = os.path.splitext(dosya_adi)[0]
    for token in kok.split():
        if token.isdigit():
            n = int(token)
            if 1 <= n <= 12:
                return f"{n}. sınıf"
    return None


def _yerel_isabet_etiketi(path: str) -> str:
    base = os.path.basename(path) or "okul verisi"
    if path.startswith(_SINIF_ETIKETLI_DIZINLER):
        sinif = _sinif_etiketi_dosyadan(base)
        if sinif:
            baslik = os.path.splitext(base)[0]
            return f"{sinif} · {baslik}"
    return base


class McpRegistry:
    def __init__(self, clients: dict[str, McpClient],
                 local_search: Callable[[str, int], list[dict[str, Any]]],
                 unconfigured: list[str] | None = None,
                 module_index: Any = None,
                 odev_kaynagi: Callable[[], list[dict[str, Any]]] | None = None,
                 sinif: Callable[[], str | None] | None = None,
                 program_kaynagi: Callable[[], Any] | None = None,
                 sinav_kaynagi: Callable[[], Any] | None = None,
                 takvim_kaynagi: Callable[[], Any] | None = None,
                 icerik_kaynagi: Callable[[], Any] | None = None,
                 not_kaynagi: Callable[[], Any] | None = None,
                 sebit_kaynagi: Callable[[], Any] | None = None,
                 platform_kaynagi: Callable[[], Any] | None = None,
                 kitap_kaynagi: Callable[[], list[dict[str, Any]]] | None = None,
                 video_kaynagi: Callable[[], Any] | None = None,
                 saat: Callable[[], datetime] | None = None) -> None:
        self.clients = clients
        # Işık's grade in the corpus's form ("7.Sınıf"), read when asked so a
        # new school year needs no restart. None, or a None answer, means
        # unknown: no grade is then invented.
        self.sinif = sinif
        self.local_search = local_search
        # Servers that were configured (named in MCP_SERVERS) but had no API
        # key. They are not in `clients` — there is nothing to call — but
        # they must still be reportable, or an unset env var looks exactly
        # like a healthy system with nothing to say.
        self.unconfigured = list(unconfigured or [])
        # Published edupedia modules (src/assistant_modules.py). Local and read-only; None keeps
        # the registry usable in tests and tools that have no catalog.
        self.module_index = module_index
        # The rows /api/homework serves (src/dashboard_api._canli_odevler).
        # None in tests and tools with no dashboard: the tool is not declared.
        self.odev_kaynagi = odev_kaynagi
        # sebit_homework.json (/api/sebit), appended to odev_listesi as its
        # own section (plan Görev 3). Optional even when odev_kaynagi is
        # given: its absence never blanks the TED portal homework list.
        self.sebit_kaynagi = sebit_kaynagi
        # The live student-data sources (dashboard_api._canli_*), one per
        # tool; each absent source leaves its tool undeclared.
        self.ogrenci_kaynaklari: dict[str, Callable[[], Any] | None] = {
            PROGRAM_TOOL: program_kaynagi,
            SINAV_TOOL: sinav_kaynagi,
            TAKVIM_TOOL: takvim_kaynagi,
            ICERIK_TOOL: icerik_kaynagi,
            NOT_TOOL: not_kaynagi,
            PLATFORM_TOOL: platform_kaynagi,
        }
        # Tedy Books' matched chapters (dashboard_api._canli_kitaplar) and the
        # MEBİ/SEBİTV discovery catalogs (dashboard_api._canli_videolar).
        # Neither fits ogrenci_kaynaklari's one-citation-per-call shape — a
        # search returns several passage-level citations — so each keeps its
        # own dispatch method below.
        self.kitap_kaynagi = kitap_kaynagi
        self.video_kaynagi = video_kaynagi
        # The clock "bugün"/"yarın" are read against; read in Istanbul either
        # way. Tests pin it; production reads the real one.
        self.saat = saat

    def degraded(self) -> list[str]:
        unhealthy = {n for n, c in self.clients.items() if not c.healthy}
        modules = set(self.module_index.degraded()) if self.module_index is not None else set()
        return sorted(unhealthy | set(self.unconfigured) | modules)

    def declarations(self) -> list[dict[str, Any]]:
        decls: list[dict[str, Any]] = [{
            "name": LOCAL_TOOL,
            "description": self._yerel_aciklama(),
            "parameters": {
                "type": "object",
                "properties": {"query": {
                    "type": "string",
                    "description": "Aranacak ifade (ör. 'matematik ödevi', 'sınav tarihleri')."}},
                "required": ["query"],
            },
        }]
        if self.odev_kaynagi is not None:
            sebit_notu = (" SEBİT ödevleri de ayrı bir bölümde bu listededir."
                         if self.sebit_kaynagi is not None else "")
            decls.append({
                "name": ODEV_TOOL,
                "description": (
                    "Işık'ın ödev listesi, Bugün ve İşler sayfalarının gösterdiği haliyle: "
                    "yapılacaklar (teslim zamanı ve öğretmenin talimatıyla), Işık'ın 'Yaptım' "
                    "dedikleri, süresi geçenler." + sebit_notu + " Ödev sorularında (ne var, ne "
                    "zaman teslim, neyi yaptı) önce BU aracı kullan — ödevin durumu için tek "
                    "güvenilir kaynak."
                ),
                "parameters": {"type": "object", "properties": {}},
            })
        for ad, kaynak in self.ogrenci_kaynaklari.items():
            if kaynak is not None:
                decls.append(copy.deepcopy(_OGRENCI_BILDIRIMLERI[ad]))
        if self.kitap_kaynagi is not None:
            decls.append(dict(assistant_kitaplar.DECLARATION))
        if self.video_kaynagi is not None:
            decls.append(dict(_VIDEO_BILDIRIM))
        if self.module_index is not None:
            decls.append(dict(assistant_modules.DECLARATION))
        for local_name, (server, mcp_name) in TOOL_ALLOWLIST.items():
            client = self.clients.get(server)
            if client is None:
                continue
            spec = next((t for t in client.list_tools()
                         if t.get("name") == mcp_name), None)
            if spec is None:
                logger.warning("MCP %s does not expose %s", server, mcp_name)
                continue
            description = spec.get("description", "")
            sinif = self._sinif()
            if sinif and local_name in SINIF_ARACLARI:
                description += (f"\n\nIşık {sinif} öğrencisi: `grade` vermezsen "
                                f"'{sinif}' kullanılır. Önceki yılın konusu için sınıfı açıkça ver.")
            decls.append({
                "name": local_name,
                "description": description,
                "parameters": sanitize_schema(spec.get("inputSchema") or {}),
            })
        return decls

    def _yerel_aciklama(self) -> str:
        """What the text index really holds, and — for each live tool this
        registry declares — the tool to use instead. Until 2026-09-25 it
        promised the timetable, exams and course content, none of which the
        index held in readable form (audit §2a)."""
        metin = ("Işık'ın okul verisinin metin indeksinde arama yapar: ödev açıklamaları ve "
                 "eski ödevler, duyurular, portalın ek sayfaları, ders içerikleri (geçmiş "
                 "haftalar dahil), okul takvimi, ders programı, notlar ve kazanım düzeyleri. "
                 "Son eşitlemedeki metni gösterir; Işık'ın 'Yaptım' işaretlerini bilmez. "
                 "Işık'a özel, başka bir aracın kapsamadığı sorular için kullan — konu/müfredat "
                 "bilgisi için değil.")
        yonlendirme = [(self.odev_kaynagi, "ödevlerin durumu → `odev_listesi`")] + [
            (self.ogrenci_kaynaklari[ad], not_) for ad, not_ in (
                (PROGRAM_TOOL, "ders programı → `ders_programi`"),
                (SINAV_TOOL, "sınav tarihleri → `sinavlar`"),
                (TAKVIM_TOOL, "etkinlik, tatil, özel ders → `takvim`"),
                (ICERIK_TOOL, "bir haftanın ders içeriği → `ders_icerigi`"),
                (NOT_TOOL, "notlar ve kazanım düzeyleri → `notlar`"),
                (PLATFORM_TOOL, "EnglishCentral/Achieve3000 ilerlemesi → `platform_ilerlemesi`"))]
        varsa = [not_ for kaynak, not_ in yonlendirme if kaynak is not None]
        if varsa:
            metin += " Güncel ve düzenli hâlleri için önce kendi aracını kullan: " + "; ".join(varsa) + "."
        return metin

    def _sinif(self) -> str | None:
        try:
            return (self.sinif() or None) if self.sinif is not None else None
        except Exception:  # noqa: BLE001 — an unknown grade is a normal state
            return None

    def dispatch(self, name: str, args: dict[str, Any], ilerleme_izni: bool = False) -> ToolOutcome:
        if name == LOCAL_TOOL:
            return self._dispatch_local(args)
        if name == ODEV_TOOL and self.odev_kaynagi is not None:
            return self._dispatch_odev()
        if self.ogrenci_kaynaklari.get(name) is not None:
            return self._dispatch_ogrenci(name, args or {})
        if name == KITAP_TOOL and self.kitap_kaynagi is not None:
            return self._dispatch_kitap(args or {})
        if name == VIDEO_TOOL and self.video_kaynagi is not None:
            return self._dispatch_video(args or {})
        if name == assistant_modules.TOOL_NAME:
            return self._dispatch_modules(args, ilerleme_izni is True)
        if name not in TOOL_ALLOWLIST:
            return ToolOutcome(ok=False, error=f"bilinmeyen araç: {name}")
        if assistant_modules.contains_progress(args):
            # Spec §6.4: module progress never leaves TED. This catches keys copied verbatim from
            # modul_ara's output; a paraphrase is not caught (plan K-S6, accepted residual risk).
            return ToolOutcome(ok=False, error=(
                "ilerleme verisi yan filo sunucularına gönderilmez; bu alanları argümandan çıkar"))

        server, mcp_name = TOOL_ALLOWLIST[name]
        client = self.clients.get(server)
        if client is None:
            return ToolOutcome(ok=False, error=f"sunucu yapılandırılmadı: {server}")

        sinif = self._sinif()
        if sinif and name in SINIF_ARACLARI and not args.get("grade"):
            args = {**args, "grade": sinif}

        if name == "oer_getir" and args.get("max_chars") is None:
            args = {**args, "max_chars": OER_METIN_SINIRI}

        result: McpToolResult = client.call_tool(mcp_name, args)
        if not result.ok:
            return ToolOutcome(ok=False, error=result.error or "araç hatası")

        text = result.text
        parcalar = _json_parcalari(text) if server == "maarif-mufredat" else None
        if name == "oer_getir":
            parcalar = _json_parcalari(text)
            belge = _figur_bilgisi(parcalar)
            if belge.get("status") == "not_found":
                return ToolOutcome(ok=False, error=f"belge bulunamadı: {args.get('doc_id')}")
            parcalar = None  # licence and source_url stay: OER links are live
        if parcalar is not None:
            hata = _hata_zarfi(parcalar)
            if hata is not None:
                return ToolOutcome(ok=False, error=hata)
            if name == "video_listele":
                text = _video_listesi_metni(parcalar)
            elif name == "program_getir" and isinstance(parcalar[0], dict):
                text = _program_metni(parcalar[0])
            elif name in _YENI_MAARIF:
                text = _kirp("\n".join(json.dumps(_baglantisiz(p), ensure_ascii=False)
                                       for p in parcalar), GOVDE_SINIRI)
            else:
                text = "\n".join(json.dumps(_baglantisiz(p), ensure_ascii=False, indent=2)
                                 for p in parcalar)
        elif name in _YENI_ARACLAR:
            text = _kirp(text, GOVDE_SINIRI)

        kind = _KIND_BY_TOOL.get(name, "mufredat")
        locator: dict[str, Any] = {"tool": name, "args": args, "server": server}
        if name == "figur_getir":
            # What the reader's panel needs to show the figure: its id for
            # /api/assistant/figure/<id>, and the caption as the image's alt.
            figur = _figur_bilgisi(parcalar)
            figure_id = figur.get("figure_id", args.get("figure_id"))
            try:
                locator["figure_id"] = int(figure_id)
            except (TypeError, ValueError):
                pass
            if isinstance(figur.get("caption"), str) and figur["caption"].strip():
                locator["caption"] = figur["caption"].strip()
        return ToolOutcome(
            ok=True,
            text=text,
            citations=[{
                "kind": kind,
                "label": self._label(kind, name, args, parcalar or _json_parcalari(text)),
                "locator": locator,
                # A figure's caption, not its metadata JSON: the panel shows
                # the snippet to the reader.
                "snippet": locator.get("caption") or text[:400],
                "confidence": 0.9,
            }],
            images=list(result.images or []),
        )

    def figur_gorseli(self, figure_id: int) -> tuple[str, bytes, str]:
        """One textbook figure's bytes for the reader's panel
        (/api/assistant/figure/<id>). Returns (durum, veri, mime): durum is
        "var", "yok" (the corpus has no such figure) or "ulasilamadi" (server
        unconfigured, unreachable, or it answered something unusable)."""
        client = self.clients.get("maarif-mufredat")
        if client is None:
            return "ulasilamadi", b"", ""
        result = client.call_tool("get_figure", {"figure_id": int(figure_id), "include_image": True})
        if not result.ok:
            durum = "yok" if "not found" in (result.error or "").lower() else "ulasilamadi"
            return durum, b"", ""
        if not result.images:
            # Measured: an unknown id is ok=True, `{"error": "… not found"}`, no image.
            return "yok", b"", ""
        gorsel = result.images[0]
        mime = str(gorsel.get("mimeType") or "")
        if mime not in GORSEL_BICIMLERI:
            return "ulasilamadi", b"", ""
        try:
            veri = base64.b64decode(str(gorsel.get("data") or ""), validate=True)
        except (ValueError, TypeError):
            return "ulasilamadi", b"", ""
        return ("var", veri, mime) if veri else ("ulasilamadi", b"", "")

    def _dispatch_local(self, args: dict[str, Any]) -> ToolOutcome:
        query = str(args.get("query", "")).strip()
        try:
            rows = self.local_search(query, 8)
        except Exception as exc:
            # local_search is caller-supplied and, unlike the MCP path,
            # carries no contract against raising. A failure here must not
            # take the whole dispatch() call down with it — and must not be
            # swallowed either, per "sessiz arıza yok".
            logger.error("local_search failed for %r: %s", query, exc)
            return ToolOutcome(ok=False, error=f"yerel arama hatası: {exc}")

        rows = [r for r in rows if isinstance(r, dict)]
        citations = []
        for r in rows:
            try:
                confidence = float(r.get("confidence", 0.0) or 0.0)
            except (TypeError, ValueError):
                confidence = 0.0
            citations.append({
                "kind": "ogrenci",
                "label": _yerel_isabet_etiketi(str(r.get("path", ""))),
                "locator": {"path": r.get("path", ""),
                            "chunk_index": r.get("chunk_index", 0)},
                # The citation panel keeps the short snippet (≤260 chars, set
                # by the retriever) — only the model's own tool body gets the
                # full chunk text below.
                "snippet": str(r.get("snippet", ""))[:400],
                "confidence": confidence,
            })
        text = _yerel_tam_metin(rows)
        return ToolOutcome(ok=True, text=text, citations=citations)

    def _dispatch_odev(self) -> ToolOutcome:
        try:
            rows = self.odev_kaynagi() or []
        except Exception as exc:  # noqa: BLE001 — told to the model, never raised through the loop
            logger.error("odev_listesi failed: %s", type(exc).__name__)
            return ToolOutcome(ok=False, error=f"ödev listesi okunamadı: {type(exc).__name__}")
        sebit = None
        if self.sebit_kaynagi is not None:
            try:
                sebit = self.sebit_kaynagi()
            except Exception as exc:  # noqa: BLE001 — SEBİT is a bonus section; its failure must not blank the TED portal list
                logger.error("sebit_odevleri source failed: %s", type(exc).__name__)
                sebit = None
        metin = _kirp(odev_listesi_metni(rows, datetime.now(), sebit=sebit), GOVDE_SINIRI)
        return ToolOutcome(ok=True, text=metin, citations=[{
            "kind": "ogrenci",
            "label": ODEV_ATIF,
            "locator": {"tool": ODEV_TOOL},
            "snippet": metin[:400],
            "confidence": 1.0,
        }])

    def _dispatch_kitap(self, args: dict[str, Any]) -> ToolOutcome:
        try:
            kitaplar = self.kitap_kaynagi() or []
        except Exception as exc:  # noqa: BLE001 — told to the model, never raised through the loop
            logger.error("kitap_ara source failed: %s", type(exc).__name__)
            return ToolOutcome(ok=False, error=f"Tedy Books okunamadı: {type(exc).__name__}")
        try:
            metin, citations = assistant_kitaplar.kitap_ara_metni(
                kitaplar, args.get("sorgu", ""), args.get("kitap"))
        except Exception as exc:  # noqa: BLE001 — told to the model, never raised through the loop
            logger.error("kitap_ara failed: %s", type(exc).__name__)
            return ToolOutcome(ok=False, error=f"kitap araması hatası: {type(exc).__name__}")
        return ToolOutcome(ok=True, text=metin, citations=citations)

    def _dispatch_video(self, args: dict[str, Any]) -> ToolOutcome:
        try:
            veri = self.video_kaynagi()
        except Exception as exc:  # noqa: BLE001 — told to the model, never raised through the loop
            logger.error("video_oner source failed: %s", type(exc).__name__)
            return ToolOutcome(ok=False, error=f"video kataloğu okunamadı: {type(exc).__name__}")
        try:
            metin, citations = video_oner_metni(veri, args.get("konu", ""), args.get("ders"))
        except Exception as exc:  # noqa: BLE001 — told to the model, never raised through the loop
            logger.error("video_oner failed: %s", type(exc).__name__)
            return ToolOutcome(ok=False, error=f"video araması hatası: {type(exc).__name__}")
        return ToolOutcome(ok=True, text=metin, citations=citations)

    def _dispatch_ogrenci(self, name: str, args: dict[str, Any]) -> ToolOutcome:
        try:
            veri = self.ogrenci_kaynaklari[name]()
        except Exception as exc:  # noqa: BLE001 — told to the model, never raised through the loop
            logger.error("%s source failed: %s", name, type(exc).__name__)
            return ToolOutcome(ok=False, error=f"{_OKUNAMADI[name]} okunamadı: {type(exc).__name__}")
        simdi = istanbul_simdi(self.saat() if self.saat is not None else None)
        try:
            if name == PROGRAM_TOOL:
                metin, etiket = ders_programi_metni(veri, args.get("gun"), simdi), "Ders programı"
            elif name == SINAV_TOOL:
                metin, etiket = sinavlar_metni(veri, simdi), "Sınavlar"
            elif name == TAKVIM_TOOL:
                metin, etiket = takvim_metni(veri, simdi, args.get("gun_sayisi", _TAKVIM_VARSAYILAN_GUN)), "Takvim"
            elif name == ICERIK_TOOL:
                metin, etiket = ders_icerigi_metni(veri, args.get("ders"), args.get("hafta"))
            elif name == NOT_TOOL:
                metin, etiket = notlar_metni(veri)
            else:
                metin, etiket = platform_ilerlemesi_metni(veri), "Platform ilerlemesi"
        except ValueError as exc:     # an argument the model can correct
            return ToolOutcome(ok=False, error=str(exc))
        except Exception as exc:  # noqa: BLE001 — a data shape nobody expected
            logger.error("%s formatting failed: %s", name, type(exc).__name__)
            return ToolOutcome(ok=False, error=f"{_OKUNAMADI[name]} okunamadı: {type(exc).__name__}")
        metin = _kirp(metin, GOVDE_SINIRI)
        return ToolOutcome(ok=True, text=metin, citations=[{
            "kind": "ogrenci",
            "label": etiket,
            "locator": {"tool": name, "args": dict(args)},
            "snippet": metin[:400],
            "confidence": 1.0,
        }])

    def _dispatch_modules(self, args: dict[str, Any], ilerleme_izni: bool) -> ToolOutcome:
        if self.module_index is None:
            return ToolOutcome(ok=False, error="modül kataloğu bağlanmadı")
        try:
            text, citations = self.module_index.ara(
                sorgu=args.get("sorgu", ""), ders=args.get("ders"), sinif=args.get("sinif"),
                ilerleme_izni=ilerleme_izni)
        except Exception as exc:  # noqa: BLE001 — reported to the model, never raised through the loop
            logger.error("modul_ara failed: %s", type(exc).__name__)
            return ToolOutcome(ok=False, error=f"modül araması hatası: {type(exc).__name__}")
        return ToolOutcome(ok=True, text=text, citations=citations)

    @staticmethod
    def _label(kind: str, tool: str, args: dict[str, Any],
               parcalar: list[Any] | None = None) -> str:
        ilk = _figur_bilgisi(parcalar)
        if tool == "figur_getir":
            if ilk.get("title") and ilk.get("page_no"):
                return f"{ilk['title']} · s.{ilk['page_no']} · görsel"
            return "Ders kitabı görseli"
        if tool == "program_getir":
            belge = ilk.get("document") if isinstance(ilk.get("document"), dict) else {}
            return f"Öğretim programı · {belge['title']}" if belge.get("title") else "Öğretim programı"
        if tool == "ders_bilgisi" and ilk.get("name"):
            return f"MEB müfredatı · {ilk['name']}"
        if tool == "video_listele":
            return "MEB videoları"
        if tool == "video_getir":
            return f"MEB videosu · {ilk['title']}" if ilk.get("title") else "MEB videosu"
        if tool == "oer_getir" and ilk.get("title"):
            return f"Açık eğitsel kaynak · {ilk['title']}"
        if kind == "kitap":
            doc = args.get("document_id")
            page = args.get("page") or args.get("page_range")
            # The book's name, not its corpus number: "Ders kitabı #213" told
            # the reader nothing.
            belge = parcalar[0].get("document") if parcalar and isinstance(parcalar[0], dict) else None
            baslik = belge.get("title") if isinstance(belge, dict) else None
            if baslik and page:
                return f"{baslik} · s.{page}"
            if doc and page:
                return f"Ders kitabı #{doc} · s.{page}"
            return "Ders kitabı"
        if kind == "oer":
            return "Açık eğitsel kaynak"
        subject = args.get("subject") or args.get("q") or ""
        return f"MEB müfredatı · {subject}" if subject else "MEB müfredatı"


def build_registry(local_search: Callable[[str, int], list[dict[str, Any]]],
                   module_index: Any = None,
                   odev_kaynagi: Callable[[], list[dict[str, Any]]] | None = None,
                   sinif: Callable[[], str | None] | None = None,
                   program_kaynagi: Callable[[], Any] | None = None,
                   sinav_kaynagi: Callable[[], Any] | None = None,
                   takvim_kaynagi: Callable[[], Any] | None = None,
                   icerik_kaynagi: Callable[[], Any] | None = None,
                   not_kaynagi: Callable[[], Any] | None = None,
                   sebit_kaynagi: Callable[[], Any] | None = None,
                   platform_kaynagi: Callable[[], Any] | None = None,
                   kitap_kaynagi: Callable[[], list[dict[str, Any]]] | None = None,
                   video_kaynagi: Callable[[], Any] | None = None,
                   saat: Callable[[], datetime] | None = None) -> McpRegistry:
    """Wire the configured servers. A server with no key is simply absent —
    its tools are not declared — but it is still named by degraded(), so an
    unset env var never looks like a healthy system with nothing to say."""
    clients: dict[str, McpClient] = {}
    unconfigured: list[str] = []
    for name, (url, env_key) in MCP_SERVERS.items():
        key = os.environ.get(env_key, "").strip()
        if not key:
            logger.warning("MCP %s disabled: %s not set", name, env_key)
            unconfigured.append(name)
            continue
        clients[name] = McpClient(name=name, url=url, api_key=key)
    return McpRegistry(clients=clients, local_search=local_search,
                       unconfigured=unconfigured, module_index=module_index,
                       odev_kaynagi=odev_kaynagi, sinif=sinif,
                       program_kaynagi=program_kaynagi, sinav_kaynagi=sinav_kaynagi,
                       takvim_kaynagi=takvim_kaynagi, icerik_kaynagi=icerik_kaynagi,
                       not_kaynagi=not_kaynagi, sebit_kaynagi=sebit_kaynagi,
                       platform_kaynagi=platform_kaynagi, kitap_kaynagi=kitap_kaynagi,
                       video_kaynagi=video_kaynagi, saat=saat)
