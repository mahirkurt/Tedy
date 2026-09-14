"""edupedia_kaynak_oku: scoped anamnesis query with an honest local BM25 fallback."""
from pathlib import Path

import pytest

from src.mcp_server.config import load_settings
from src.mcp_server.federation import FederationError
from src.mcp_server.kapsam import KAYNAK_VERISI_NOT
from src.mcp_server.kaynak_oku import KaynakOkuyucu, local_passages
from src.mcp_server.runs import RunStore
from src.mcp_server.tools import Tools


class FakeFed:
    def __init__(self, response=None, configured=True, fail=False):
        self.response, self._configured, self.fail, self.calls = response, configured, fail, []

    def configured(self, server):
        return self._configured

    def call(self, server, tool, args, beklenen):
        self.calls.append((server, tool, args, beklenen))
        if self.fail:
            raise FederationError(server, tool, "timeout")
        return self.response


@pytest.fixture
def runs(tmp_path):
    store = RunStore(tmp_path)
    store.save("abcdef012345", {"run_id": "abcdef012345", "created_by": "drmahirkurt@gmail.com"})
    store.save_page("abcdef012345", 197, 112, "Katı maddelerin tanecikleri düzenlidir.\n\nSıvılar akışkandır.")
    store.save_page("abcdef012345", 197, 113, "Buharlaşma sıvının gaza dönüşmesidir.\n\nYoğuşma tersidir.")
    return store


CHUNKS = {"query": "q", "collection": "edupedia:run:abcdef012345", "retrieval": {"degraded": False},
          "chunks": [{"doc_id": "edupedia:abcdef012345:kitap/197/112-113", "idx": 2, "score": 0.91,
                      "text": "Buharlaşma sıvının gaza dönüşmesidir." + " x" * 600}]}


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
