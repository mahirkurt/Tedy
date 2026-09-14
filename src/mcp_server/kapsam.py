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


def resolve_subject(federation: Federation, ders: str) -> dict[str, str]:
    subjects = _mufredat(federation, "list_subjects", {"q": ders}, "liste")
    wanted = _fold(ders)
    for s in subjects:
        if s.get("slug") == ders.strip():
            return {"slug": s["slug"], "name": s["name"]}
    exact = [s for s in subjects if _fold(s.get("name", "")) in (wanted, f"{wanted} dersi")]
    if len(exact) == 1:
        return {"slug": exact[0]["slug"], "name": exact[0]["name"]}
    if len(subjects) == 1:
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
        body = _mufredat(federation, "search_learning_outcomes",
                         {"q": kazanim_kodu, "subject": slug, "limit": 10, "distinct_codes": True}, "nesne")
        rows = [r for r in body.get("results") or [] if r.get("code") == kazanim_kodu.strip()]
        if not rows:
            raise KapsamError("kazanim_dogrulanamadi", kazanim_kodu=kazanim_kodu, ders=slug)
    elif konu:
        body = _mufredat(federation, "search_learning_outcomes",
                         {"q": konu, "subject": slug, "grade": grade, "limit": 8, "distinct_codes": True}, "nesne")
        rows = [r for r in body.get("results") or [] if r.get("grade") in (None, grade)]
    else:
        raise KapsamError("konu_veya_kazanim_gerekli")
    kazanimlar = [_outcome(r) for r in rows]
    uyusmazlik = []
    if kazanimlar:
        first = kazanimlar[0]
        if first["grade"] and first["grade"] != grade:
            uyusmazlik.append({"alan": "sinif", "verilen": grade, "mufredat": first["grade"]})
        if first["subject"] and first["subject"] != slug:
            uyusmazlik.append({"alan": "ders", "verilen": slug, "mufredat": first["subject"]})
    return {"kazanimlar": kazanimlar, "uyusmazlik": uyusmazlik}
