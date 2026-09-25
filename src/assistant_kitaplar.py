"""Tedy Books search for the assistant (plan Görev 3, docs/superpowers/notes/
2026-09-25-asistan-veri-denetimi.md §1: `books/` was invisible to the
assistant — not in `DEFAULT_INCLUDE_DIRS` — even though it is the one
collection the reader actually reads cover to cover).

Which .md file belongs to which chapter id is decided in exactly one place,
`dashboard_api._book_chapters()`/`_book_load()`; this module does not
duplicate that matching. It is handed the already-matched chapters (title +
body text, front matter already stripped by `_book_split_front_matter()`)
through a source callable — the same "no source, no tool" wiring every other
live tool in `assistant_tools.py` uses — and only adds a small BM25 search
over each chapter's paragraphs, tokenized the same way the file index is
(`turkce_kucult_katla`), so a query folds case and Turkish accents exactly as
the rest of the assistant does.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

TOOL_NAME = "kitap_ara"

# chat_with_tools slices every tool_result to 4,000 chars (assistant_tools.
# GOVDE_SINIRI); kept independently here so this module has no import-time
# dependency on assistant_tools (which imports this module).
GOVDE_SINIRI = 3900
_PASAJ_SINIRI = 500          # a single passage's own cap, so one long
                              # paragraph cannot crowd out the rest
_PARAGRAF_MIN_UZUNLUK = 20    # a scene break or a single short verse line
                              # is not worth ranking on its own
_TOP_K = 5

DECLARATION: dict[str, Any] = {
    "name": TOOL_NAME,
    "description": (
        "Tedy Books'taki kitapların bölüm metinlerinde arama yapar; en iyi "
        "eşleşen pasajları kitap ve bölüm adıyla döner. Kitapta geçen bir "
        "olay, karakter, alıntı ya da konu sorulduğunda BU aracı kullan — "
        "kitabın metnini hatırlayarak ya da uydurarak anlatma. `kitap` "
        "verilmezse bütün kitaplarda arar."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "sorgu": {
                "type": "string",
                "description": "Aranacak ifade (ör. 'Bilbo'nun yüzüğü bulması').",
            },
            "kitap": {
                "type": "string",
                "description": (
                    "Kitap adı ya da bir kısmı (ör. 'Hobbit'). Boş bırakılırsa "
                    "tüm kitaplarda arar."
                ),
            },
        },
        "required": ["sorgu"],
    },
}


def _katla(metin: Any) -> str:
    # Lazy, exactly like assistant_tools._katla: assistant_core imports
    # assistant_tools (which imports this module) while it builds the
    # registry, so a module-level import here would be circular.
    from src.assistant_core import turkce_kucult_katla
    return turkce_kucult_katla(str(metin or "")).strip()


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", _katla(text))


def _kirp(metin: str, sinir: int) -> str:
    if len(metin) <= sinir:
        return metin
    if sinir <= 2:
        return metin[:sinir]
    govde = sinir - 2
    kesik = metin[:govde].rsplit(" ", 1)[0]
    return (kesik or metin[:govde]) + " …"


@dataclass(frozen=True)
class _Pasaj:
    kitap_slug: str
    kitap_baslik: str
    bolum_id: str
    bolum_baslik: str
    sira: int
    metin: str


def _paragraflara_ayir(metin: str) -> list[str]:
    parcalar = [re.sub(r"\s+", " ", p).strip()
               for p in re.split(r"\n\s*\n", str(metin or "")) if p.strip()]
    return [p for p in parcalar if len(p) >= _PARAGRAF_MIN_UZUNLUK]


def _pasajlari_derle(kitaplar: list[dict[str, Any]] | None) -> list[_Pasaj]:
    """Flatten the source's {slug, title, chapters:[{id, title, text}]} shape
    into one paragraph per passage. A malformed entry is skipped rather than
    raising — one bad chapter must not take the whole search down."""
    out: list[_Pasaj] = []
    for kitap in kitaplar or []:
        if not isinstance(kitap, dict):
            continue
        slug = str(kitap.get("slug") or "").strip()
        baslik = str(kitap.get("title") or slug or "Kitap").strip()
        for bolum in kitap.get("chapters") or []:
            if not isinstance(bolum, dict):
                continue
            bolum_id = str(bolum.get("id") or "").strip()
            bolum_baslik = str(bolum.get("title") or bolum_id or "Bölüm").strip()
            for i, p in enumerate(_paragraflara_ayir(bolum.get("text"))):
                out.append(_Pasaj(slug, baslik, bolum_id, bolum_baslik, i, p))
    return out


def _kitaba_gore_suz(pasajlar: list[_Pasaj], kitap: Any) -> list[_Pasaj]:
    q = _katla(kitap)
    if not q:
        return pasajlar
    return [p for p in pasajlar if q in _katla(p.kitap_baslik) or q in _katla(p.kitap_slug)]


def _en_iyi_pasajlar(pasajlar: list[_Pasaj], sorgu: str, top_k: int = _TOP_K) -> list[tuple[_Pasaj, float]]:
    """A small BM25 over the passage list — the same k1/b as HybridRetriever
    (assistant_core.py), reimplemented locally rather than shared: this
    corpus is a few chapters, not the file index, and the two must stay free
    to diverge without a cross-module contract."""
    q_tokens = _tokenize(sorgu)
    if not q_tokens or not pasajlar:
        return []
    tokenized = [_tokenize(p.metin) for p in pasajlar]
    doc_len = [len(t) for t in tokenized]
    avg_len = (sum(doc_len) / len(doc_len)) if doc_len else 1.0
    df: dict[str, int] = {}
    for toks in tokenized:
        for t in set(toks):
            df[t] = df.get(t, 0) + 1
    n = max(1, len(pasajlar))
    k1, b = 1.2, 0.75

    scored: list[tuple[float, int]] = []
    for i, toks in enumerate(tokenized):
        if not toks:
            continue
        tf: dict[str, int] = {}
        for t in toks:
            tf[t] = tf.get(t, 0) + 1
        score = 0.0
        for q in q_tokens:
            fq = tf.get(q, 0)
            if fq == 0:
                continue
            dfq = df.get(q, 0)
            idf = math.log(1 + (n - dfq + 0.5) / (dfq + 0.5))
            denom = fq + k1 * (1 - b + b * (doc_len[i] / avg_len if avg_len else 1))
            score += idf * ((fq * (k1 + 1)) / denom)
        if score > 0:
            scored.append((score, i))
    scored.sort(key=lambda x: -x[0])
    return [(pasajlar[i], s) for s, i in scored[:max(1, top_k)]]


def kitap_ara_metni(kitaplar: list[dict[str, Any]] | None, sorgu: Any,
                    kitap: Any = None) -> tuple[str, list[dict[str, Any]]]:
    """(body, citations) for the model: the best-matching passages, each
    quoted under its book and chapter title. `citations` carries one entry
    per passage, `kind: "tedy-kitap"` — SourcePanel groups it under its own
    "Tedy Books" heading, never mixed with the MEB textbook ('kitap') group."""
    sorgu = str(sorgu or "").strip()
    if not sorgu:
        return "Aranacak bir ifade verilmedi.", []

    pasajlar = _pasajlari_derle(kitaplar)
    if not pasajlar:
        return "Tedy Books'ta henüz okunabilir bir bölüm yok.", []

    if kitap:
        secili = _kitaba_gore_suz(pasajlar, kitap)
        if not secili:
            mevcut = sorted({p.kitap_baslik for p in pasajlar})
            return (f"'{kitap}' adlı kitap Tedy Books'ta yok. Mevcut kitaplar: "
                    + (", ".join(mevcut) or "yok") + "."), []
        pasajlar = secili

    en_iyiler = _en_iyi_pasajlar(pasajlar, sorgu)
    if not en_iyiler:
        return f"'{sorgu}' için Tedy Books'ta eşleşen pasaj bulunamadı.", []

    max_skor = en_iyiler[0][1] or 1.0
    parcalar: list[str] = []
    citations: list[dict[str, Any]] = []
    toplam = 0
    for pasaj, skor in en_iyiler:
        etiket = f"{pasaj.kitap_baslik} · {pasaj.bolum_baslik}"
        alinti = _kirp(pasaj.metin, _PASAJ_SINIRI)
        blok = f"[{etiket}]\n{alinti}"
        ayrac = 2 if parcalar else 0
        if toplam + ayrac + len(blok) > GOVDE_SINIRI:
            break
        parcalar.append(blok)
        toplam += ayrac + len(blok)
        citations.append({
            "kind": "tedy-kitap",
            "label": etiket,
            "locator": {"tool": TOOL_NAME, "slug": pasaj.kitap_slug,
                       "bolum": pasaj.bolum_id, "sira": pasaj.sira},
            "snippet": alinti[:400],
            "confidence": round(min(1.0, skor / max_skor), 4),
        })
    metin = "\n\n".join(parcalar) or "Tedy Books'ta eşleşen pasaj bulunamadı."
    return metin, citations
