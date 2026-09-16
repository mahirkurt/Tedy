"""Claim summary stored in taslak.json for the TED Assistant (plan SP5 K-S4)."""
import json

from src import module_store as ms
from src.mcp_server import derleme, ornekler
from src.mcp_server.derle_araci import Derleyici
from src.mcp_server.runs import RunStore
from src.mcp_server.taslak import DraftStore

FULL = "drmahirkurt@gmail.com"
RUN_ID = "abcdef012345"
RUN_RECORD = {
    "run_id": RUN_ID, "created_by": FULL,
    "cerceve": {"kind": "textbook", "document_id": 197, "title": "Fen Bilimleri 5", "sayfalar": "111-116"},
    "kazanimlar": [{"code": "FB.5.4.1.1", "text": "Maddenin hâllerini açıklar."}],
    "coverage": {"maarif-mufredat": "hit"},
}


def test_summary_is_bounded_json_native_and_keeps_both_grounding_kinds():
    data = ornekler.ornek("QUIZ")
    data["verification"]["claims"].append({"claim": "  OER\nkaynaklı   iddia ", "verdict": "supported",
                                           "grounding": {"source": "PhET Colorado", "license": "CC BY 4.0"}})
    data["verification"]["claims"].append({"claim": 5})
    data["verification"]["claims"].extend({"claim": f"iddia {i}", "grounding": {}} for i in range(40))

    ozet = derleme.dogrulama_ozeti(data)

    json.dumps(ozet)
    assert ozet["surum"] == 1 and len(ozet["iddialar"]) == derleme.DOGRULAMA_MAX_IDDIA
    assert ozet["iddialar"][0] == {"iddia": "Madde katı, sıvı ve gaz hâllerinde bulunur.", "karar": "supported",
                                   "dayanak": {"document_id": 197, "page": 112}}
    assert ozet["iddialar"][2] == {"iddia": "OER kaynaklı iddia", "karar": "supported",
                                   "dayanak": {"kaynak": "PhET Colorado", "lisans": "CC BY 4.0"}}
    assert ozet["iddialar"][3] == {"iddia": "iddia 0", "karar": None, "dayanak": {}}


def test_summary_tolerates_malformed_blocks_and_caps_length():
    assert derleme.dogrulama_ozeti({}) == {"surum": 1, "iddialar": []}
    assert derleme.dogrulama_ozeti({"verification": {"claims": "x"}}) == {"surum": 1, "iddialar": []}
    rows = derleme.dogrulama_ozeti({"verification": {"claims": [
        {"claim": "a" * 1000, "grounding": {"document_id": True, "page": "3", "source": "", "license": 7}}]}})["iddialar"]
    assert len(rows[0]["iddia"]) == derleme.DOGRULAMA_MAX_METIN and rows[0]["dayanak"] == {}


def test_derle_writes_the_summary_into_the_immutable_draft_record(tmp_path):
    runs = RunStore(tmp_path)
    runs.save(RUN_ID, RUN_RECORD)
    derleyici = Derleyici(runs, DraftStore(tmp_path), "https://tedy.online", "https://tedy.online",
                          clock=lambda: 1_800_000_000.0)

    body = derleyici.derle(FULL, RUN_ID, ornekler.ornek("QUIZ"))

    assert body["status"] == "ok"
    record = ms.read_draft(tmp_path, body["taslak_id"])
    assert record["dogrulama"] == derleme.dogrulama_ozeti(ornekler.ornek("QUIZ"))
    assert [row["dayanak"].get("page") for row in record["dogrulama"]["iddialar"]] == [112, 114]
