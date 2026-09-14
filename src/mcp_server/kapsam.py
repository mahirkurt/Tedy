"""edupedia_kapsam: verify subject/grade/outcomes against maarif-mufredat, then frame the module.

Contract (edupedia content contract): grade and subject are never inferred from an outcome
code; the authority is what maarif-mufredat returns. Task 11 adds textbook, figures, OER and
anamnesis ingestion on top of this verification layer.
"""
from __future__ import annotations

import re
from typing import Any

from src.mcp_server.federation import MUFREDAT, Federation, FederationError

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
