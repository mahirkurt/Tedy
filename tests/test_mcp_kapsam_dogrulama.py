"""Run store and curriculum verification (subject slug, grade, outcome authority)."""
import json

import pytest

from src.mcp_server import kapsam
from src.mcp_server.federation import FederationError
from src.mcp_server.runs import RUN_ID_RE, RunStore


class FakeFed:
    def __init__(self, responses, fail=()):
        self.responses = responses
        self.fail = set(fail)
        self.calls = []

    def configured(self, server):
        return True

    def call(self, server, tool, args, beklenen):
        self.calls.append((server, tool, args, beklenen))
        if (server, tool) in self.fail:
            raise FederationError(server, tool, "timeout")
        value = self.responses[(server, tool)]
        return value(args) if callable(value) else value


SUBJECTS = [
    {"slug": "fen-bilimleri-dersi", "name": "Fen Bilimleri Dersi", "level": "temel-egitim", "grade_count": 6},
    {"slug": "fen-lisesi-fizik", "name": "Fizik (Fen Lisesi)", "level": "ortaogretim", "grade_count": 4},
]


def test_run_store_round_trip(tmp_path):
    store = RunStore(tmp_path)
    run_id = store.new_id()
    assert RUN_ID_RE.match(run_id)
    store.save(run_id, {"created_by": "a@b", "ders": "x"})
    assert store.load(run_id) == {"created_by": "a@b", "ders": "x"}
    store.save_page(run_id, 197, 113, "ikinci")
    store.save_page(run_id, 197, 112, "birinci")
    assert store.pages(run_id) == [
        {"document_id": 197, "page_no": 112, "text": "birinci"},
        {"document_id": 197, "page_no": 113, "text": "ikinci"},
    ]
    assert store.load("../etc") is None
    assert store.load("ffffffffffff") is None
    assert json.loads((tmp_path / "edupedia_runs" / run_id / "run.json").read_text(encoding="utf-8"))["ders"] == "x"


@pytest.mark.parametrize("raw,expected", [
    ("5", "5.Sınıf"), (5, "5.Sınıf"), ("5. sınıf", "5.Sınıf"), ("5.Sınıf", "5.Sınıf"), ("12", "12.Sınıf"),
    ("0", None), ("13", None), ("beşinci", None), ("", None),
])
def test_normalize_grade(raw, expected):
    assert kapsam.normalize_grade(raw) == expected


def test_resolve_subject_exact_name_wins_over_partial():
    fed = FakeFed({("maarif-mufredat", "list_subjects"): SUBJECTS})
    assert kapsam.resolve_subject(fed, "Fen Bilimleri") == {"slug": "fen-bilimleri-dersi", "name": "Fen Bilimleri Dersi"}
    assert fed.calls[0][2] == {"q": "Fen Bilimleri"} and fed.calls[0][3] == "liste"


def test_resolve_subject_accepts_slug_and_reports_ambiguity_and_absence():
    fed = FakeFed({("maarif-mufredat", "list_subjects"): SUBJECTS})
    assert kapsam.resolve_subject(fed, "fen-lisesi-fizik")["slug"] == "fen-lisesi-fizik"
    with pytest.raises(kapsam.KapsamError) as exc:
        kapsam.resolve_subject(fed, "fen")
    assert exc.value.status == "belirsiz_ders"
    assert {c["slug"] for c in exc.value.detay["adaylar"]} == {"fen-bilimleri-dersi", "fen-lisesi-fizik"}
    empty = FakeFed({("maarif-mufredat", "list_subjects"): []})
    with pytest.raises(kapsam.KapsamError) as exc:
        kapsam.resolve_subject(empty, "Astroloji")
    assert exc.value.status == "ders_bulunamadi"


def test_resolve_subject_federation_failure_is_manual_required():
    fed = FakeFed({}, fail={("maarif-mufredat", "list_subjects")})
    with pytest.raises(kapsam.KapsamError) as exc:
        kapsam.resolve_subject(fed, "Fen Bilimleri")
    assert exc.value.status == "manual_required"
    assert exc.value.detay["neden"] == "timeout"


def _slo(results):
    return {("maarif-mufredat", "search_learning_outcomes"): {"results": results, "included_fragment_types": ["outcome"]}}


def test_verify_outcomes_by_code_uses_mcp_authority_and_reports_mismatch():
    row = {"code": "FB.6.3.1.1", "text": "Fotosentez…", "subject": "fen-bilimleri-dersi", "grade": "6.Sınıf",
           "document_id": 50, "page_no": 12, "fragment_type": "outcome"}
    fed = FakeFed(_slo([row, {**row, "code": "FB.6.3.1.2"}]))
    out = kapsam.verify_outcomes(fed, "fen-bilimleri-dersi", "5.Sınıf", None, "FB.6.3.1.1")
    assert [k["code"] for k in out["kazanimlar"]] == ["FB.6.3.1.1"]
    assert out["uyusmazlik"] == [{"alan": "sinif", "verilen": "5.Sınıf", "mufredat": "6.Sınıf"}]
    assert fed.calls[0][2] == {"q": "FB.6.3.1.1", "subject": "fen-bilimleri-dersi", "limit": 10, "distinct_codes": True}


def test_verify_outcomes_code_not_found():
    fed = FakeFed(_slo([{"code": "FB.5.1.1.1", "text": "x", "subject": "fen-bilimleri-dersi", "grade": "5.Sınıf",
                         "document_id": 1, "page_no": 1, "fragment_type": "outcome"}]))
    with pytest.raises(kapsam.KapsamError) as exc:
        kapsam.verify_outcomes(fed, "fen-bilimleri-dersi", "5.Sınıf", None, "FB.9.9.9.9")
    assert exc.value.status == "kazanim_dogrulanamadi"


def test_verify_outcomes_by_topic_filters_grade_and_trims_text():
    long_text = "a" * 900
    fed = FakeFed(_slo([
        {"code": "FB.5.4.1.1", "text": long_text, "subject": "fen-bilimleri-dersi", "grade": "5.Sınıf",
         "document_id": 7, "page_no": 30, "fragment_type": "outcome"},
    ]))
    out = kapsam.verify_outcomes(fed, "fen-bilimleri-dersi", "5.Sınıf", "maddenin halleri", None)
    assert out["kazanimlar"][0]["code"] == "FB.5.4.1.1"
    assert len(out["kazanimlar"][0]["text"]) == 400
    assert fed.calls[0][2] == {"q": "maddenin halleri", "subject": "fen-bilimleri-dersi", "grade": "5.Sınıf",
                               "limit": 8, "distinct_codes": True}


def test_verify_outcomes_requires_topic_or_code():
    with pytest.raises(kapsam.KapsamError) as exc:
        kapsam.verify_outcomes(FakeFed({}), "fen-bilimleri-dersi", "5.Sınıf", None, None)
    assert exc.value.status == "konu_veya_kazanim_gerekli"
