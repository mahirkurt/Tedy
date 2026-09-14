"""edupedia_kapsam: verify subject/grade/outcomes against maarif-mufredat, then frame the module.

Contract (edupedia content contract): grade and subject are never inferred from an outcome
code; the authority is what maarif-mufredat returns. Task 11 adds textbook, figures, OER and
anamnesis ingestion on top of this verification layer.
"""
from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from typing import Any, Callable

from src.mcp_server.coverage import Coverage
from src.mcp_server.federation import ANAMNESIS, EGITIM_KAYNAK, MUFREDAT, Federation, FederationError
from src.mcp_server.runs import RunStore

OUTCOME_TEXT_MAX = 400


class KapsamError(Exception):
    def __init__(self, status: str, **detay: Any) -> None:
        super().__init__(status)
        self.status = status
        self.detay = detay


def _fold(text: str) -> str:
    return text.replace("I", "ı").replace("İ", "i").lower().strip()


def normalize_grade(sinif: str | int) -> str | None:
    m = re.search(r"\d+", str(sinif))
    if not m:
        return None
    n = int(m.group(0))
    return f"{n}.Sınıf" if 1 <= n <= 12 else None


def _mufredat(federation: Federation, tool: str, args: dict[str, Any], beklenen: str) -> Any:
    try:
        return federation.call(MUFREDAT, tool, args, beklenen=beklenen)
    except FederationError as exc:
        raise KapsamError("manual_required", sunucu=MUFREDAT, arac=tool, neden=exc.reason) from exc


def _related(wanted: str, candidate: dict[str, Any]) -> bool:
    """R5: a lone search hit is only accepted if the user's input and the candidate's folded
    name/slug actually overlap — otherwise a single unrelated hit (e.g. "matematik" turning up
    only "Görsel Sanatlar Dersi") would resolve silently with zero similarity check."""
    cand_name = _fold(candidate.get("name", ""))
    cand_slug = _fold(candidate.get("slug", ""))
    if wanted and (wanted in cand_name or cand_name in wanted):
        return True
    return bool(wanted) and (wanted in cand_slug or cand_slug in wanted)


def resolve_subject(federation: Federation, ders: str) -> dict[str, str]:
    subjects = _mufredat(federation, "list_subjects", {"q": ders}, "liste")
    wanted = _fold(ders)
    for s in subjects:
        if s.get("slug") == ders.strip():
            return {"slug": s["slug"], "name": s["name"]}
    exact = [s for s in subjects if _fold(s.get("name", "")) in (wanted, f"{wanted} dersi")]
    if len(exact) == 1:
        return {"slug": exact[0]["slug"], "name": exact[0]["name"]}
    if len(subjects) == 1 and _related(wanted, subjects[0]):
        return {"slug": subjects[0]["slug"], "name": subjects[0]["name"]}
    if not subjects:
        raise KapsamError("ders_bulunamadi", ders=ders)
    raise KapsamError("belirsiz_ders", ders=ders,
                      adaylar=[{"slug": s["slug"], "name": s["name"], "level": s.get("level")} for s in subjects[:10]])


def _outcome(row: dict[str, Any]) -> dict[str, Any]:
    return {"code": row.get("code"), "text": (row.get("text") or "")[:OUTCOME_TEXT_MAX],
            "subject": row.get("subject"), "grade": row.get("grade"),
            "document_id": row.get("document_id"), "page_no": row.get("page_no")}


def verify_outcomes(federation: Federation, slug: str, grade: str, konu: str | None,
                    kazanim_kodu: str | None) -> dict[str, Any]:
    if kazanim_kodu:
        # R1: no subject or grade filter here. Per the maarif-mufredat contract, "subject" and
        # "grade" scope the server-side search — filtering on the caller's own claim would make
        # a genuine ders/sinif mismatch unreachable, since a mismatching row would never be
        # returned in the first place. The exact code match below is what narrows the result.
        code = kazanim_kodu.strip()
        body = _mufredat(federation, "search_learning_outcomes",
                         {"q": kazanim_kodu, "limit": 10, "distinct_codes": True}, "nesne")
        rows = [r for r in body.get("results") or [] if r.get("code") == code]
        if not rows:
            raise KapsamError("kazanim_dogrulanamadi", kazanim_kodu=kazanim_kodu, ders=slug)
        kazanimlar = [_outcome(r) for r in rows]
        uyusmazlik = []
        authority = kazanimlar[0]
        if authority["grade"] and authority["grade"] != grade:
            uyusmazlik.append({"alan": "sinif", "verilen": grade, "mufredat": authority["grade"]})
        if authority["subject"] and authority["subject"] != slug:
            uyusmazlik.append({"alan": "ders", "verilen": slug, "mufredat": authority["subject"]})
    elif konu:
        # R2: keep the subject scope (that part of the query is legitimate) but drop the grade
        # filter — otherwise a topic that only exists at another grade is indistinguishable from
        # one that does not exist at all.
        body = _mufredat(federation, "search_learning_outcomes",
                         {"q": konu, "subject": slug, "limit": 8, "distinct_codes": True}, "nesne")
        rows = body.get("results") or []
        at_grade = [r for r in rows if r.get("grade") == grade]
        kazanimlar = [_outcome(r) for r in at_grade]
        uyusmazlik = []
        if kazanimlar:
            authority = kazanimlar[0]
            if authority["subject"] and authority["subject"] != slug:
                uyusmazlik.append({"alan": "ders", "verilen": slug, "mufredat": authority["subject"]})
        else:
            # Topic exists but only at other grades: report each distinct other grade once.
            # "konu_sinifi" (not "sinif") — Task 11's KapsamBuilder auto-corrects "sinif"
            # entries to the mufredat grade, which is right for a code (which pins exactly one
            # grade) but would silently switch the user's explicit grade to an arbitrary other
            # grade found for a topic; "konu_sinifi" surfaces the information without that.
            other_grades = list(dict.fromkeys(
                r.get("grade") for r in rows if r.get("grade") and r.get("grade") != grade
            ))
            uyusmazlik = [{"alan": "konu_sinifi", "verilen": grade, "mufredat": g} for g in other_grades]
    else:
        raise KapsamError("konu_veya_kazanim_gerekli")
    return {"kazanimlar": kazanimlar, "uyusmazlik": uyusmazlik}


PAGE_WINDOW = 6
FIGURE_MAX = 6
OER_MAX = 5
# Task 11 Ruling 4: cap on multi-part anamnesis ingest before giving up and reporting a
# degraded (not failed) coverage row — an unbounded loop could otherwise spin forever on a
# document whose window cap never catches up.
INGEST_MAX_PARTS = 8
CAVEAT = ("Müfredat ve ders kitabı verileri maarif-mufredat korpusundan, açık kaynaklar egitim-kaynak'tan gelir; "
          "boş sonuç yokluk kanıtı değildir. MODULE_DATA'daki her olgusal iddia kitap sayfasına dayandırılmalıdır.")
NEXT_STEP = ("Derin okuma için edupedia_kaynak_oku(run_id, soru); MODULE_DATA verification.frame_source için "
             "cerceve.document_id ve sayfaları kullan; segment kurgusu için edupedia_rehber('segmentler').")


def anamnesis_doc_id(run_id: str, document_id: int, first: int, last: int) -> str:
    doc_id = f"edupedia:{run_id}:kitap/{document_id}/{first}-{last}"
    if len(doc_id.encode("utf-8")) <= 56:
        return doc_id
    return f"edupedia:{run_id}:k{document_id}"[:56]


def _part_doc_id(base_doc_id: str, part: int) -> str:
    """Continuation doc_id for a multi-part anamnesis ingest (Task 11 Ruling 4): '<base>::part<n>'.

    The base is truncated (on a byte boundary) so the whole id still fits anamnesis' 56-byte
    doc_id ceiling — ``anamnesis_doc_id`` may already return a string right at that limit, and
    appending a suffix to it unconditionally would blow past it.
    """
    suffix = f"::part{part}"
    limit = 56 - len(suffix.encode("utf-8"))
    truncated = base_doc_id.encode("utf-8")[:limit].decode("utf-8", errors="ignore")
    return f"{truncated}{suffix}"


class KapsamBuilder:
    def __init__(self, federation: Federation, runs: RunStore, clock: Callable[[], float] = time.time) -> None:
        self.federation = federation
        self.runs = runs
        self.clock = clock

    def build(self, email: str, ders: str, sinif: str | int, konu: str | None = None,
              kazanim_kodu: str | None = None) -> dict[str, Any]:
        cov = Coverage()
        grade = normalize_grade(sinif)
        if grade is None:
            return {"status": "gecersiz_sinif", "sinif": str(sinif), "mcp_verified": False}
        try:
            subject = resolve_subject(self.federation, ders)
            verified = verify_outcomes(self.federation, subject["slug"], grade, konu, kazanim_kodu)
            for row in verified["uyusmazlik"]:
                if row["alan"] == "sinif":
                    # A code pins exactly one grade, so the verified grade replaces the caller's.
                    grade = row["mufredat"]
                elif row["alan"] == "ders":
                    # Task 11 Ruling 2: a by-code "ders" mismatch means the code genuinely belongs
                    # to another subject. Re-resolve that subject (resolve_subject's exact-slug
                    # branch, since row["mufredat"] is already a curriculum slug) so the textbook/
                    # figure/OER framing below uses the CORRECT subject. uyusmazlik itself still
                    # reports the mismatch unchanged, for transparency.
                    subject = resolve_subject(self.federation, row["mufredat"])
                # "konu_sinifi" (Task 11 Ruling 3): the topic exists only at OTHER grades. Unlike
                # a code match this does not pin one authoritative grade, so it is only carried
                # in the response — correcting `grade` here would silently swap the user's
                # explicit grade for an arbitrary other grade the topic happened to appear at.
        except KapsamError as exc:
            if exc.status == "manual_required":
                cov.degraded(MUFREDAT, exc.detay.get("neden", "hata"))
            else:
                cov.hit(MUFREDAT)
            return {"status": exc.status, **exc.detay, "coverage": cov.as_dict(), "mcp_verified": False}
        cov.hit(MUFREDAT)
        run_id = self.runs.new_id()
        query = konu or (verified["kazanimlar"][0]["text"][:120] if verified["kazanimlar"] else subject["name"])

        try:
            cerceve, pages, figures = self._frame(run_id, subject["slug"], grade, query, verified["kazanimlar"])
        except KapsamError as exc:
            cov.degraded(MUFREDAT, exc.detay.get("neden", "hata"))
            cerceve = {"kind": None, "document_id": None, "title": None, "sayfalar": None,
                       "not": f"Ders kitabı çerçevesi alınamadı ({exc.detay.get('arac')}); kazanımlar doğrulandı."}
            pages, figures = [], []
        self._ingest(cov, run_id, cerceve, pages)
        oer, eslesme = self._oer(cov, konu or query, kazanim_kodu)

        body: dict[str, Any] = {
            "status": "ok", "run_id": run_id, "ders": subject, "sinif": grade,
            "kazanimlar": verified["kazanimlar"], "uyusmazlik": verified["uyusmazlik"],
            "cerceve": cerceve,
            "kitap_sayfalari": [{"page_no": p["page_no"], "ozet": (p.get("text") or "")[:400]} for p in pages],
            "figur_adaylari": figures, "oer": oer,
        }
        if eslesme is not None:
            body["kazanim_eslesmesi"] = eslesme
        body.update({"coverage": cov.as_dict(), "caveat": CAVEAT, "sonraki_adim": NEXT_STEP, "mcp_verified": False})
        self.runs.save(run_id, {
            "run_id": run_id, "created_by": email,
            "created_at": datetime.fromtimestamp(self.clock(), timezone.utc).isoformat(timespec="seconds"),
            "girdi": {"ders": ders, "sinif": str(sinif), "konu": konu, "kazanim_kodu": kazanim_kodu},
            "ders": subject, "sinif": grade, "kazanimlar": verified["kazanimlar"], "cerceve": cerceve,
            "coverage": cov.as_dict(),
        })
        return body

    def _frame(self, run_id: str, slug: str, grade: str, query: str,
               kazanimlar: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
        books = [b for b in _mufredat(self.federation, "list_textbooks", {"subject": slug, "grade": grade, "limit": 20}, "liste")
                 if int(b.get("page_count") or 0) > 0]
        if not books:
            doc = kazanimlar[0]["document_id"] if kazanimlar else None
            return ({"kind": "program", "document_id": doc, "title": None, "sayfalar": None,
                     "not": "Bu ders ve sınıf için tam metinli ders kitabı yok; çerçeve öğretim programıdır."}, [], [])
        book = books[0]
        doc_id = int(book["document_id"])
        found = _mufredat(self.federation, "search_figures",
                          {"query": query, "subject": slug, "grade": grade, "document_id": doc_id, "limit": 12}, "nesne")
        figs = sorted((f for f in found.get("figures") or [] if f.get("page_no")), key=lambda f: (f["page_no"], f["figure_id"]))
        figures = [{"figure_id": f["figure_id"], "page_no": f["page_no"], "etiket": f.get("label") or "",
                    "aciklama": (f.get("caption") or f.get("snippet") or "")[:200]} for f in figs[:FIGURE_MAX]]
        cerceve: dict[str, Any] = {"kind": "textbook", "document_id": doc_id, "title": book.get("title"), "sayfalar": None}
        if not figs:
            cerceve["not"] = "Figür aramasında sayfa isabeti yok; sayfa penceresi seçilmedi, kitapta konuyu elle doğrula."
            return cerceve, [], figures
        first = max(1, figs[0]["page_no"] - 1)
        last = min(int(book["page_count"]), first + PAGE_WINDOW - 1)
        text = _mufredat(self.federation, "get_document_text",
                         {"document_id": doc_id, "page_range": f"{first}-{last}", "max_chars": 60000}, "nesne")
        if text.get("error"):
            cerceve["not"] = f"Sayfa metni alınamadı: {text.get('error')}"
            return cerceve, [], figures
        pages = [p for p in text.get("pages") or [] if isinstance(p, dict)]
        for p in pages:
            self.runs.save_page(run_id, doc_id, int(p["page_no"]), p.get("text") or "")
        cerceve["sayfalar"] = f"{first}-{last}"
        return cerceve, pages, figures

    def _ingest(self, cov: Coverage, run_id: str, cerceve: dict[str, Any], pages: list[dict[str, Any]]) -> None:
        if not self.federation.configured(ANAMNESIS):
            cov.skipped(ANAMNESIS, "anahtar yok")
            return
        if not pages:
            cov.skipped(ANAMNESIS, "alınacak sayfa yok")
            return
        first, last = pages[0]["page_no"], pages[-1]["page_no"]
        text = "\n\n".join(f"=== Sayfa {p['page_no']} ===\n{p.get('text') or ''}" for p in pages)
        base_doc_id = anamnesis_doc_id(run_id, cerceve["document_id"], first, last)
        args: dict[str, Any] = {
            "text": text, "doc_id": base_doc_id, "collection": f"edupedia:run:{run_id}",
            "title": cerceve.get("title") or "ders kitabı", "source": "maarif-mufredat", "ttl_hours": 168,
        }
        # Task 11 Ruling 4 (honest partial ingest): anamnesis' ingest_document truncates a
        # document that overflows its embedding window and reports a non-null `next_offset`
        # (self-host/anamnesis-mcp/src/rag.ts ingestDocument, ~L338; server.ts TRUNCATION_NOTE
        # ~L54-58). Its input schema (server.ts ~L154-168, additionalProperties=false) accepts a
        # resume `offset` and no other continuation field, and names '<doc_id>::part2' as the
        # convention for the resumed doc_id. We keep calling with the SAME text/collection/
        # title/source/ttl_hours, only adding `offset` and bumping the part-suffixed doc_id,
        # until next_offset comes back null or we hit INGEST_MAX_PARTS.
        try:
            for part in range(1, INGEST_MAX_PARTS + 1):
                result = self.federation.call(ANAMNESIS, "ingest_document", args, beklenen="nesne")
                next_offset = result.get("next_offset")
                if next_offset is None:
                    cov.hit(ANAMNESIS)
                    return
                args = {**args, "doc_id": _part_doc_id(base_doc_id, part + 1), "offset": next_offset}
            cov.degraded(ANAMNESIS, "kismi_alim")
        except FederationError as exc:
            cov.degraded(ANAMNESIS, exc.reason)

    def _oer(self, cov: Coverage, query: str, kazanim_kodu: str | None) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        if not self.federation.configured(EGITIM_KAYNAK):
            cov.skipped(EGITIM_KAYNAK, "anahtar yok")
            return [], None
        try:
            found = self.federation.call(EGITIM_KAYNAK, "kb_search", {"q": query, "top_k": OER_MAX}, beklenen="nesne")
        except FederationError as exc:
            cov.degraded(EGITIM_KAYNAK, exc.reason)
            return [], None
        oer = [{
            "doc_id": r.get("doc_id"), "baslik": r.get("title"),
            "pasaj": (r.get("passage") or "")[: 300 if r.get("quote_allowed") else 160],
            "lisans": r.get("license"), "alinti_izni": bool(r.get("quote_allowed")),
            "kaynak_url": r.get("source_url"), "eslesme": r.get("match_kind"),
        } for r in (found.get("results") or [])[:OER_MAX]]
        cov.hit(EGITIM_KAYNAK) if oer else cov.empty(EGITIM_KAYNAK)
        eslesme = None
        if kazanim_kodu:
            try:
                match = self.federation.call(EGITIM_KAYNAK, "kb_for_outcome",
                                             {"outcome_code": kazanim_kodu, "top_k": 3}, beklenen="nesne")
                eslesme = {"status": match.get("status"), "reason": match.get("reason"),
                           "sonuc_sayisi": len(match.get("results") or [])}
            except FederationError as exc:
                eslesme = {"status": "degraded", "reason": exc.reason, "sonuc_sayisi": 0}
        return oer, eslesme
