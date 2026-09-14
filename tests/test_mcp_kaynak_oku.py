"""edupedia_kaynak_oku: scoped anamnesis query with an honest local BM25 fallback."""
from pathlib import Path

import pytest

from src.mcp_server.config import load_settings
from src.mcp_server.federation import FederationError
from src.mcp_server.kapsam import KAYNAK_VERISI_NOT
from src.mcp_server.kaynak_oku import PASSAGE_MAX, TRUNCATION_MARKER, KaynakOkuyucu, local_passages
from src.mcp_server.runs import RunStore
from src.mcp_server.tools import Tools


class FakeFed:
    def __init__(self, response=None, configured=True, fail=False):
        self.response, self._configured, self.fail, self.calls = response, configured, fail, []

    def configured(self, server):
        return self._configured

    def call(self, server, tool, args, beklenen, deadline=None):
        self.calls.append((server, tool, args, beklenen))
        if self.fail:
            raise FederationError(server, tool, "timeout")
        return self.response


@pytest.fixture
def runs(tmp_path):
    store = RunStore(tmp_path)
    # A run record as KapsamBuilder writes it: its coverage always names anamnesis.
    store.save("abcdef012345", {"run_id": "abcdef012345", "created_by": "drmahirkurt@gmail.com",
                                "coverage": {"maarif-mufredat": "hit", "anamnesis": "hit"}})
    store.save_page("abcdef012345", 197, 112, "Katı maddelerin tanecikleri düzenlidir.\n\nSıvılar akışkandır.")
    store.save_page("abcdef012345", 197, 113, "Buharlaşma sıvının gaza dönüşmesidir.\n\nYoğuşma tersidir.")
    return store


# A short, un-truncated chunk text: this fixture is shared by tests that are not about truncation
# at all (collection scoping, degraded-but-used, doc_id::idx attribution, kaynak_verisi wrapping).
# Truncation/kesildi behavior gets its own dedicated fixtures below, so this one no longer needs
# padding to exceed PASSAGE_MAX.
CHUNKS = {"query": "q", "collection": "edupedia:run:abcdef012345", "retrieval": {"degraded": False},
          "chunks": [{"doc_id": "edupedia:abcdef012345:kitap/197/112-113", "idx": 2, "score": 0.91,
                      "text": "Buharlaşma sıvının gaza dönüşmesidir."}]}


def test_anamnesis_query_is_collection_scoped(runs):
    fed = FakeFed(CHUNKS)
    body = KaynakOkuyucu(fed, runs).oku("abcdef012345", "buharlaşma nedir", top_k=20)
    server, tool, args, beklenen = fed.calls[0]
    assert (server, tool, beklenen) == ("anamnesis", "hybrid_query", "nesne")
    assert args == {"query": "buharlaşma nedir", "collection": "edupedia:run:abcdef012345", "k": 8,
                    "per_chunk_chars": 800, "max_edges": 0}
    assert body["status"] == "ok" and body["yontem"] == "anamnesis"
    assert body["pasajlar"][0]["ref"] == "edupedia:abcdef012345:kitap/197/112-113::2"
    assert len(body["pasajlar"][0]["metin"]) <= 800
    assert body["pasajlar"][0]["kesildi"] is False
    assert body["coverage"] == {"anamnesis": "hit"}
    assert body["mcp_verified"] is False


@pytest.mark.parametrize("fed,state", [
    (FakeFed(fail=True), "degraded:timeout"),
    (FakeFed(configured=False), "skipped:anahtar yok"),
    (FakeFed({"chunks": [], "retrieval": {"degraded": False}}), "empty"),
])
def test_falls_back_to_local_pages(runs, fed, state):
    body = KaynakOkuyucu(fed, runs).oku("abcdef012345", "buharlaşma")
    assert body["yontem"] == "yerel"
    assert body["coverage"]["anamnesis"] == state
    assert body["pasajlar"][0]["sayfa"] == 113
    assert body["pasajlar"][0]["ref"] == "local:197/113#0"


def test_degraded_anamnesis_retrieval_is_reported_but_used(runs):
    fed = FakeFed({**CHUNKS, "retrieval": {"degraded": True}})
    body = KaynakOkuyucu(fed, runs).oku("abcdef012345", "buharlaşma")
    assert body["yontem"] == "anamnesis"
    assert body["coverage"]["anamnesis"] == "degraded:anamnesis_degraded"


def test_unknown_run_and_empty_question(runs):
    reader = KaynakOkuyucu(FakeFed(CHUNKS), runs)
    assert reader.oku("ffffffffffff", "x")["status"] == "run_bulunamadi"
    assert reader.oku("../../etc", "x")["status"] == "run_bulunamadi"
    assert reader.oku("abcdef012345", "  ")["status"] == "gecersiz_sorgu"


def test_local_passages_rank_by_term_and_fold_turkish_case():
    pages = [{"document_id": 1, "page_no": 5, "text": "Işık kırılır.\n\nSes yayılır."},
             {"document_id": 1, "page_no": 6, "text": "IŞIK hızlıdır ve ışık düz gider."}]
    hits = local_passages(pages, "ışık", top_k=2)
    assert [h["sayfa"] for h in hits] == [6, 5]
    assert local_passages(pages, "uzay", top_k=2) == []


def test_anamnesis_part_doc_id_is_attributed_correctly(runs):
    """Task 11 ingests overflow text as continuation parts '<base>::partN'; a hybrid_query hit
    against one of those parts must still carry its own doc_id (not the base) plus the chunk's
    idx in the ref, so the citation actually points at the part that produced the match."""
    part_chunks = {"chunks": [{"doc_id": "edupedia:abcdef012345:kitap/197/112-113::part2", "idx": 3,
                               "score": 0.7, "text": "Yoğuşma sıvıya dönüşümdür."}],
                  "retrieval": {"degraded": False}}
    body = KaynakOkuyucu(FakeFed(part_chunks), runs).oku("abcdef012345", "yoğuşma nedir")
    assert body["yontem"] == "anamnesis"
    assert body["pasajlar"][0]["ref"] == "edupedia:abcdef012345:kitap/197/112-113::part2::3"


def test_tool_wraps_passages_under_kaynak_verisi(tmp_path, runs):
    """Ruling (spec §6.3): edupedia_kaynak_oku's passages must come back inside one top-level
    kaynak_verisi object carrying the same not-an-instruction marker as edupedia_kapsam, and must
    not also appear as a bare top-level 'pasajlar' key."""
    settings = load_settings({"TED_MCP_PUBLIC_BASE_URL": "https://mcp.tedy.online"}, project_root=tmp_path)
    t = Tools(settings, FakeFed(CHUNKS), runs=runs)
    body = t.kaynak_oku("drmahirkurt@gmail.com", "abcdef012345", "buharlaşma nedir")
    assert "pasajlar" not in body
    assert body["kaynak_verisi"]["not"] == KAYNAK_VERISI_NOT
    assert body["kaynak_verisi"]["pasajlar"][0]["ref"] == "edupedia:abcdef012345:kitap/197/112-113::2"


def test_tool_passthrough_for_error_status_has_no_kaynak_verisi(tmp_path, runs):
    settings = load_settings({"TED_MCP_PUBLIC_BASE_URL": "https://mcp.tedy.online"}, project_root=tmp_path)
    t = Tools(settings, FakeFed(CHUNKS), runs=runs)
    body = t.kaynak_oku("drmahirkurt@gmail.com", "ffffffffffff", "x")
    assert body["status"] == "run_bulunamadi"
    assert "kaynak_verisi" not in body and "pasajlar" not in body


# --- Fix round 1: truncation marker must survive onto the passage (kesildi signal) -----------


def test_anamnesis_marker_present_sets_kesildi_true(runs):
    """anamnesis itself appends TRUNCATION_MARKER after slicing a chunk's text to the requested
    per_chunk_chars (PASSAGE_MAX) — this simulates that real response shape directly, rather than
    re-deriving it, so the marker's exact position (right after the PASSAGE_MAX-th character) is
    pinned down regardless of how the fake source text was built."""
    already_truncated = ("Buharlaşma sıvının gaza dönüşmesidir." + " x" * 600)[:PASSAGE_MAX] + TRUNCATION_MARKER
    fed = FakeFed({"chunks": [{"doc_id": "edupedia:abcdef012345:kitap/197/112-113", "idx": 4,
                               "score": 0.4, "text": already_truncated}],
                   "retrieval": {"degraded": False}})
    body = KaynakOkuyucu(fed, runs).oku("abcdef012345", "buharlaşma")
    pasaj = body["pasajlar"][0]
    assert pasaj["kesildi"] is True
    assert pasaj["metin"] == already_truncated
    assert pasaj["metin"].endswith(TRUNCATION_MARKER)


def test_anamnesis_short_chunk_sets_kesildi_false(runs):
    fed = FakeFed({"chunks": [{"doc_id": "edupedia:abcdef012345:kitap/197/112-113", "idx": 1,
                               "score": 0.5, "text": "Kısa pasaj."}],
                   "retrieval": {"degraded": False}})
    body = KaynakOkuyucu(fed, runs).oku("abcdef012345", "buharlaşma")
    pasaj = body["pasajlar"][0]
    assert pasaj["kesildi"] is False
    assert pasaj["metin"] == "Kısa pasaj."


def test_anamnesis_overlong_chunk_without_marker_is_capped_defensively(runs):
    """Contract-violation defense: if anamnesis ever returned text longer than PASSAGE_MAX without
    its own marker, we truncate here ourselves and still surface kesildi=True rather than let an
    oversized, unmarked blob look like a complete, untruncated passage."""
    unmarked_overlong = "Buharlaşma sıvının gaza dönüşmesidir." + " x" * 600
    fed = FakeFed({"chunks": [{"doc_id": "edupedia:abcdef012345:kitap/197/112-113", "idx": 5,
                               "score": 0.3, "text": unmarked_overlong}],
                   "retrieval": {"degraded": False}})
    body = KaynakOkuyucu(fed, runs).oku("abcdef012345", "buharlaşma")
    pasaj = body["pasajlar"][0]
    assert pasaj["kesildi"] is True
    assert pasaj["metin"] == unmarked_overlong[:PASSAGE_MAX] + TRUNCATION_MARKER


def test_local_long_paragraph_sets_kesildi_true_with_marker():
    long_para = "kelime " * 200  # far longer than PASSAGE_MAX
    pages = [{"document_id": 1, "page_no": 9, "text": long_para}]
    hits = local_passages(pages, "kelime", top_k=1)
    assert hits[0]["kesildi"] is True
    assert hits[0]["metin"] == long_para.strip()[:PASSAGE_MAX] + TRUNCATION_MARKER


def test_local_short_paragraph_sets_kesildi_false():
    pages = [{"document_id": 1, "page_no": 9, "text": "Kısa paragraf kelime."}]
    hits = local_passages(pages, "kelime", top_k=1)
    assert hits[0]["kesildi"] is False
    assert hits[0]["metin"] == "Kısa paragraf kelime."


def test_anamnesis_and_local_passages_share_the_same_passage_keys(runs):
    anamnesis_body = KaynakOkuyucu(FakeFed(CHUNKS), runs).oku("abcdef012345", "buharlaşma nedir")
    local_body = KaynakOkuyucu(FakeFed(fail=True), runs).oku("abcdef012345", "buharlaşma")
    assert anamnesis_body["yontem"] == "anamnesis" and local_body["yontem"] == "yerel"
    assert set(anamnesis_body["pasajlar"][0]) == set(local_body["pasajlar"][0])
    assert set(anamnesis_body["pasajlar"][0]) == {"ref", "sayfa", "metin", "kesildi", "skor"}


# --- SP2 final review F1: spec §7 per-tool budget over a real Federation ----------------------

import json  # noqa: E402

from src.mcp_client import McpToolResult  # noqa: E402
from src.mcp_server import federation  # noqa: E402


class Clock:
    def __init__(self, now=7000.0):
        self.now = now

    def __call__(self):
        return self.now


def _timed_reader(tmp_path, runs, clock):
    log = []

    class Client:
        def __init__(self, name, url, api_key, **_):
            pass

        def call_tool(self, tool, arguments, timeout=None):
            log.append({"tool": tool, "timeout": timeout})
            return McpToolResult(ok=True, text=json.dumps(CHUNKS))

    settings = load_settings({"TED_MCP_PUBLIC_BASE_URL": "https://mcp.tedy.online", "ANAMNESIS_MCP_API_KEY": "k"},
                             project_root=tmp_path)
    fed = federation.Federation(settings, client_factory=Client, monotonic=clock)
    return KaynakOkuyucu(fed, runs, monotonic=clock), log


def test_anamnesis_query_timeout_is_capped_by_the_tool_budget(tmp_path, runs):
    reader, log = _timed_reader(tmp_path, runs, Clock())
    body = reader.oku("abcdef012345", "buharlaşma nedir")
    assert body["yontem"] == "anamnesis"
    assert log == [{"tool": "hybrid_query", "timeout": federation.CALL_TIMEOUT_SECONDS}]


def test_budget_cut_anamnesis_still_returns_local_passages(tmp_path, runs):
    clock = Clock()

    class SlowRuns(RunStore):
        def load(self, run_id):
            clock.now += 59.5  # a stalled disk read eats the budget before the fleet call
            return runs.load(run_id)

        def pages(self, run_id):
            return runs.pages(run_id)

    reader, log = _timed_reader(tmp_path, SlowRuns(tmp_path), clock)
    body = reader.oku("abcdef012345", "buharlaşma")
    assert log == []
    assert body["status"] == "ok" and body["yontem"] == "yerel"
    assert body["coverage"] == {"anamnesis": "degraded:zaman_asimi"}
    assert body["pasajlar"][0]["ref"] == "local:197/113#0"
