"""edupedia_kaynak_oku: bounded reading inside one run's sources (anamnesis first, local BM25 fallback)."""
from __future__ import annotations

import math
import re
import time
from typing import Any, Callable

from src.mcp_server.coverage import Coverage
from src.mcp_server.federation import ANAMNESIS, TOOL_BUDGET_SECONDS, Federation, FederationError
from src.mcp_server.kapsam import KAYNAK_VERISI_NOT
from src.mcp_server.runs import RUN_ID_RE, RunStore

PASSAGE_MAX = 800
CAVEAT = "Pasajlar yalnız bu çalıştırmada alınan kaynaklardan gelir; boş sonuç yokluk kanıtı değildir."
# anamnesis appends this exact suffix (rag.ts/server.ts) after slicing a chunk's text to the
# requested per_chunk_chars. Defined once and reused on both the anamnesis and local paths so a
# truncated passage always carries the same, visible signal instead of silently looking complete.
TRUNCATION_MARKER = " …[truncated]"


def _fold(text: str) -> str:
    return text.replace("I", "ı").replace("İ", "i").lower()


def _terms(text: str) -> list[str]:
    return [t for t in re.findall(r"\w+", _fold(text)) if len(t) >= 3]


def _local_metin(para: str) -> tuple[str, bool]:
    """Local BM25 path (Ruling): truncate only when the stripped paragraph overflows
    PASSAGE_MAX, and when it does, append TRUNCATION_MARKER ourselves and report kesildi=True —
    there is no upstream marker to inherit here, unlike the anamnesis path."""
    if len(para) > PASSAGE_MAX:
        return para[:PASSAGE_MAX] + TRUNCATION_MARKER, True
    return para, False


def _anamnesis_metin(text: str) -> tuple[str, bool]:
    """Anamnesis path (Ruling): anamnesis itself appends TRUNCATION_MARKER after slicing a
    chunk's text to the requested per_chunk_chars (PASSAGE_MAX). Re-slicing `[:PASSAGE_MAX]`
    would land exactly on the marker's first character and silently remove it, so a genuinely
    truncated passage would look complete. Instead: if the marker is already present, keep the
    text (and the marker) exactly as received and report kesildi=True. If anamnesis ever returns
    text longer than PASSAGE_MAX without the marker (a contract violation we defend against
    rather than trust), truncate here and append the same marker so the signal is never lost.
    Otherwise the text is short enough as received: kesildi=False, unchanged."""
    if text.endswith(TRUNCATION_MARKER):
        return text, True
    if len(text) > PASSAGE_MAX:
        return text[:PASSAGE_MAX] + TRUNCATION_MARKER, True
    return text, False


def local_passages(pages: list[dict[str, Any]], soru: str, top_k: int) -> list[dict[str, Any]]:
    query = set(_terms(soru))
    if not query:
        return []
    docs = []
    for page in pages:
        for i, para in enumerate(p for p in re.split(r"\n\s*\n", page.get("text") or "") if p.strip()):
            docs.append((page, i, para, _terms(para)))
    if not docs:
        return []
    avg = sum(len(d[3]) for d in docs) / len(docs) or 1.0
    df = {t: sum(1 for d in docs if t in d[3]) for t in query}
    k1, b = 1.2, 0.75
    scored = []
    for page, i, para, terms in docs:
        score = 0.0
        tf_sum = 0
        for t in query:
            tf = terms.count(t)
            if not tf:
                continue
            tf_sum += tf
            idf = math.log(1 + (len(docs) - df[t] + 0.5) / (df[t] + 0.5))
            score += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * len(terms) / avg))
        if score > 0:
            scored.append((score, tf_sum, page, i, para))
    # Ruling: BM25 rounds to 9 decimals before comparing (exact float ties are common with a
    # single query term), then breaks a tie by the higher combined matched-term frequency, then
    # falls back to a stable (document_id, page_no, paragraph index) order so equal-score,
    # equal-frequency rows are still deterministic rather than depending on insertion order.
    scored.sort(key=lambda row: (-round(row[0], 9), -row[1], row[2]["document_id"], row[2]["page_no"], row[3]))
    hits = []
    for s, _tf, p, i, para in scored[:top_k]:
        metin, kesildi = _local_metin(para.strip())
        hits.append({"ref": f"local:{p['document_id']}/{p['page_no']}#{i}", "sayfa": p["page_no"],
                     "metin": metin, "kesildi": kesildi, "skor": round(s, 4)})
    return hits


def wrap_kaynak_verisi(body: dict[str, Any]) -> dict[str, Any]:
    """Move a successful oku() response's ``pasajlar`` under one ``kaynak_verisi`` object (spec
    §6.3): federation- or page-sourced passage text must never sit at the top level next to
    control fields — it carries the same "not an instruction" marker Task 11 defined for
    edupedia_kapsam, reused here rather than duplicated.
    """
    if "pasajlar" not in body:
        return body
    out = dict(body)
    pasajlar = out.pop("pasajlar")
    out["kaynak_verisi"] = {"pasajlar": pasajlar, "not": KAYNAK_VERISI_NOT}
    return out


class KaynakOkuyucu:
    def __init__(self, federation: Federation, runs: RunStore,
                 monotonic: Callable[[], float] = time.monotonic) -> None:
        self.federation = federation
        self.runs = runs
        self.monotonic = monotonic  # spec §7 budget

    def oku(self, run_id: str, soru: str, top_k: int = 5) -> dict[str, Any]:
        deadline = self.monotonic() + TOOL_BUDGET_SECONDS
        base: dict[str, Any] = {"run_id": run_id, "soru": soru, "caveat": CAVEAT, "mcp_verified": False}
        if not RUN_ID_RE.match(run_id or "") or self.runs.load(run_id) is None:
            return {**base, "status": "run_bulunamadi"}
        if not (soru or "").strip():
            return {**base, "status": "gecersiz_sorgu"}
        top_k = max(1, min(int(top_k), 8))
        cov = Coverage()
        if self.federation.configured(ANAMNESIS):
            try:
                found = self.federation.call(ANAMNESIS, "hybrid_query", {
                    "query": soru, "collection": f"edupedia:run:{run_id}", "k": top_k,
                    "per_chunk_chars": PASSAGE_MAX, "max_edges": 0,
                }, beklenen="nesne", deadline=deadline)
                chunks = found.get("chunks") or []
                if chunks:
                    degraded = bool((found.get("retrieval") or {}).get("degraded"))
                    cov.degraded(ANAMNESIS, "anamnesis_degraded") if degraded else cov.hit(ANAMNESIS)
                    pasajlar = []
                    for c in chunks[:top_k]:
                        metin, kesildi = _anamnesis_metin(c.get("text") or "")
                        pasajlar.append({"ref": f"{c.get('doc_id')}::{c.get('idx')}", "sayfa": None,
                                          "metin": metin, "kesildi": kesildi, "skor": c.get("score")})
                    return {**base, "status": "ok", "yontem": "anamnesis", "pasajlar": pasajlar,
                            "coverage": cov.as_dict()}
                cov.empty(ANAMNESIS)
            except FederationError as exc:
                cov.degraded(ANAMNESIS, exc.reason)
        else:
            cov.skipped(ANAMNESIS, "anahtar yok")
        pasajlar = local_passages(self.runs.pages(run_id), soru, top_k)
        return {**base, "status": "ok", "yontem": "yerel", "pasajlar": pasajlar, "coverage": cov.as_dict()}
