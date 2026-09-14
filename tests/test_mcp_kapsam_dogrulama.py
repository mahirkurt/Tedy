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

    def call(self, server, tool, args, beklenen, deadline=None):
        self.calls.append((server, tool, args, beklenen))
        if (server, tool) in self.fail:
            raise FederationError(server, tool, "timeout")
        value = self.responses[(server, tool)]
        return value(args) if callable(value) else value


class FilteringFakeFed:
    """Args-honoring fake: search_learning_outcomes applies the subject/grade filter args the
    way the real maarif-mufredat server does. Per the maarif-mufredat contract, ``subject`` and
    ``grade`` scope the server-side search — so if the query under test still sent them, a row
    that legitimately mismatches the caller's claim would never come back at all, and the
    ders/sinif mismatch this fake exists to prove would be unreachable."""

    def __init__(self, outcomes):
        self.outcomes = outcomes
        self.calls = []

    def configured(self, server):
        return True

    def call(self, server, tool, args, beklenen, deadline=None):
        self.calls.append((server, tool, args, beklenen))
        assert tool == "search_learning_outcomes"
        rows = self.outcomes
        if "subject" in args:
            rows = [r for r in rows if r.get("subject") == args["subject"]]
        if "grade" in args:
            rows = [r for r in rows if r.get("grade") == args["grade"]]
        return {"results": rows, "included_fragment_types": ["outcome"]}


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


def test_run_id_re_rejects_trailing_newline():
    # R3: RUN_ID_RE used "$" which matches just before a trailing "\n" — defeating the strict
    # "12 lowercase hex" invariant.
    assert RUN_ID_RE.match("abcdef012345")
    assert not RUN_ID_RE.match("abcdef012345\n")


def test_save_page_is_atomic_and_leaves_no_temp_file(tmp_path):
    # R4: save_page must write via a temp file + os.replace like save()/atomic_json_dump does,
    # so a crash or concurrent read mid-write never leaves Task 11's ingestion a truncated page.
    store = RunStore(tmp_path)
    run_id = store.new_id()
    store.save_page(run_id, 5, 1, "metin")
    pages_dir = tmp_path / "edupedia_runs" / run_id / "pages"
    assert sorted(p.name for p in pages_dir.iterdir()) == ["5-1.txt"]
    assert store.pages(run_id) == [{"document_id": 5, "page_no": 1, "text": "metin"}]


def test_save_page_crash_mid_write_does_not_corrupt_existing_page(tmp_path, monkeypatch):
    # Proves the atomicity, not just the happy path: a failure during the write must land on a
    # ".tmp" file, never touch the real target, and leave no temp file behind — mirroring
    # atomic_json_dump's write-tmp-then-os.replace-then-cleanup-on-failure contract.
    from pathlib import Path

    store = RunStore(tmp_path)
    run_id = store.new_id()
    store.save_page(run_id, 5, 1, "ilk")
    pages_dir = tmp_path / "edupedia_runs" / run_id / "pages"

    original_write_text = Path.write_text

    def boom(self, *args, **kwargs):
        if self.name.endswith(".tmp"):
            raise OSError("disk full")
        return original_write_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", boom)
    with pytest.raises(OSError):
        store.save_page(run_id, 5, 1, "bozuk")

    assert sorted(p.name for p in pages_dir.iterdir()) == ["5-1.txt"]
    assert store.pages(run_id) == [{"document_id": 5, "page_no": 1, "text": "ilk"}]


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


def test_resolve_subject_rejects_unrelated_singleton():
    # R5: a single search hit with no textual relation to the user's input must not be
    # accepted outright — that is how "matematik" used to resolve to "Görsel Sanatlar Dersi".
    fed = FakeFed({("maarif-mufredat", "list_subjects"):
                   [{"slug": "gorsel-sanatlar-dersi", "name": "Görsel Sanatlar Dersi",
                     "level": "temel-egitim", "grade_count": 8}]})
    with pytest.raises(kapsam.KapsamError) as exc:
        kapsam.resolve_subject(fed, "matematik")
    assert exc.value.status == "belirsiz_ders"
    assert {c["slug"] for c in exc.value.detay["adaylar"]} == {"gorsel-sanatlar-dersi"}


def test_resolve_subject_accepts_related_singleton():
    # The lone candidate's folded name contains the folded user input ("fen bilimleri" is a
    # substring of "fen bilimleri ve teknoloji dersi"), so it is accepted — this exercises the
    # singleton-shortcut relatedness check itself, not the earlier exact-name-match branch.
    fed = FakeFed({("maarif-mufredat", "list_subjects"):
                   [{"slug": "fen-bilimleri-ve-teknoloji-dersi", "name": "Fen Bilimleri ve Teknoloji Dersi",
                     "level": "temel-egitim", "grade_count": 8}]})
    assert kapsam.resolve_subject(fed, "Fen Bilimleri") == {
        "slug": "fen-bilimleri-ve-teknoloji-dersi", "name": "Fen Bilimleri ve Teknoloji Dersi",
    }


def _slo(results):
    return {("maarif-mufredat", "search_learning_outcomes"): {"results": results, "included_fragment_types": ["outcome"]}}


def test_verify_outcomes_by_code_uses_mcp_authority_and_reports_mismatch():
    row = {"code": "FB.6.3.1.1", "text": "Fotosentez…", "subject": "fen-bilimleri-dersi", "grade": "6.Sınıf",
           "document_id": 50, "page_no": 12, "fragment_type": "outcome"}
    fed = FakeFed(_slo([row, {**row, "code": "FB.6.3.1.2"}]))
    out = kapsam.verify_outcomes(fed, "fen-bilimleri-dersi", "5.Sınıf", None, "FB.6.3.1.1")
    assert [k["code"] for k in out["kazanimlar"]] == ["FB.6.3.1.1"]
    assert out["uyusmazlik"] == [{"alan": "sinif", "verilen": "5.Sınıf", "mufredat": "6.Sınıf"}]
    # R1: the by-code query must NOT scope by subject (or grade) — a filtering server would
    # otherwise exclude any row that doesn't already match the caller's claim, making a real
    # ders/sinif mismatch unreachable.
    assert fed.calls[0][2] == {"q": "FB.6.3.1.1", "limit": 10, "distinct_codes": True}


def test_verify_outcomes_by_code_subject_mismatch_survives_server_side_filtering():
    # R1: with a fed that actually filters by args the way a real server would, a valid code
    # belonging to a DIFFERENT subject than claimed must come back as a "ders" uyusmazlik —
    # never as kazanim_dogrulanamadi (which is what a subject-filtered query would produce).
    row = {"code": "FB.6.3.1.1", "text": "Fotosentez…", "subject": "fen-bilimleri-dersi", "grade": "6.Sınıf",
           "document_id": 50, "page_no": 12, "fragment_type": "outcome"}
    fed = FilteringFakeFed([row])
    out = kapsam.verify_outcomes(fed, "sosyal-bilgiler-dersi", "6.Sınıf", None, "FB.6.3.1.1")
    assert [k["code"] for k in out["kazanimlar"]] == ["FB.6.3.1.1"]
    assert out["uyusmazlik"] == [{"alan": "ders", "verilen": "sosyal-bilgiler-dersi", "mufredat": "fen-bilimleri-dersi"}]
    assert "subject" not in fed.calls[0][2]


def test_verify_outcomes_by_code_grade_mismatch_survives_server_side_filtering():
    row = {"code": "FB.6.3.1.1", "text": "Fotosentez…", "subject": "fen-bilimleri-dersi", "grade": "6.Sınıf",
           "document_id": 50, "page_no": 12, "fragment_type": "outcome"}
    fed = FilteringFakeFed([row])
    out = kapsam.verify_outcomes(fed, "fen-bilimleri-dersi", "5.Sınıf", None, "FB.6.3.1.1")
    assert out["uyusmazlik"] == [{"alan": "sinif", "verilen": "5.Sınıf", "mufredat": "6.Sınıf"}]
    assert "grade" not in fed.calls[0][2]


def test_verify_outcomes_code_not_found():
    fed = FakeFed(_slo([{"code": "FB.5.1.1.1", "text": "x", "subject": "fen-bilimleri-dersi", "grade": "5.Sınıf",
                         "document_id": 1, "page_no": 1, "fragment_type": "outcome"}]))
    with pytest.raises(kapsam.KapsamError) as exc:
        kapsam.verify_outcomes(fed, "fen-bilimleri-dersi", "5.Sınıf", None, "FB.9.9.9.9")
    assert exc.value.status == "kazanim_dogrulanamadi"


def test_verify_outcomes_by_code_unknown_code_still_raises_without_subject_grade_filter():
    # Even though the query no longer scopes by subject/grade (so a real server would search
    # more broadly), a code that genuinely does not exist must still raise — the local
    # exact-code filter is what does the work, not the (now absent) server-side filter args.
    row = {"code": "FB.5.1.1.1", "text": "x", "subject": "fen-bilimleri-dersi", "grade": "5.Sınıf",
           "document_id": 1, "page_no": 1, "fragment_type": "outcome"}
    fed = FilteringFakeFed([row])
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
    # R2: the topic query keeps the subject scope but must NOT scope by grade — otherwise a
    # topic that only exists at another grade is indistinguishable from one that doesn't exist.
    assert fed.calls[0][2] == {"q": "maddenin halleri", "subject": "fen-bilimleri-dersi",
                               "limit": 8, "distinct_codes": True}


def test_verify_outcomes_by_topic_other_grade_reported_once_per_distinct_grade():
    # R2 (revised): a topic that exists only at other grades yields one uyusmazlik entry per
    # distinct other grade, using "konu_sinifi" (not "sinif") — Task 11's KapsamBuilder
    # auto-corrects the grade for "sinif" entries, which is right for a code (which pins
    # exactly one grade) but would be wrong here: it would silently switch the user's explicit
    # grade to an arbitrary other grade found for the topic.
    rows = [
        {"code": "FB.6.4.1.1", "text": "Maddenin halleri (6. sınıf)", "subject": "fen-bilimleri-dersi",
         "grade": "6.Sınıf", "document_id": 7, "page_no": 30, "fragment_type": "outcome"},
        {"code": "FB.7.4.1.1", "text": "Maddenin halleri (7. sınıf)", "subject": "fen-bilimleri-dersi",
         "grade": "7.Sınıf", "document_id": 8, "page_no": 40, "fragment_type": "outcome"},
        {"code": "FB.7.4.1.2", "text": "Maddenin halleri (tekrar)", "subject": "fen-bilimleri-dersi",
         "grade": "7.Sınıf", "document_id": 9, "page_no": 41, "fragment_type": "outcome"},
    ]
    fed = FilteringFakeFed(rows)
    out = kapsam.verify_outcomes(fed, "fen-bilimleri-dersi", "5.Sınıf", "maddenin halleri", None)
    assert out["kazanimlar"] == []
    assert out["uyusmazlik"] == [
        {"alan": "konu_sinifi", "verilen": "5.Sınıf", "mufredat": "6.Sınıf"},
        {"alan": "konu_sinifi", "verilen": "5.Sınıf", "mufredat": "7.Sınıf"},
    ]
    assert "grade" not in fed.calls[0][2]


def test_verify_outcomes_by_topic_present_at_grade_ignores_other_grades():
    # R2: when rows DO exist at the requested grade, other grades are not noise — no entries.
    rows = [
        {"code": "FB.5.4.1.1", "text": "Maddenin halleri (5. sınıf)", "subject": "fen-bilimleri-dersi",
         "grade": "5.Sınıf", "document_id": 7, "page_no": 30, "fragment_type": "outcome"},
        {"code": "FB.6.4.1.1", "text": "Maddenin halleri (6. sınıf)", "subject": "fen-bilimleri-dersi",
         "grade": "6.Sınıf", "document_id": 8, "page_no": 40, "fragment_type": "outcome"},
    ]
    fed = FilteringFakeFed(rows)
    out = kapsam.verify_outcomes(fed, "fen-bilimleri-dersi", "5.Sınıf", "maddenin halleri", None)
    assert [k["code"] for k in out["kazanimlar"]] == ["FB.5.4.1.1"]
    assert out["uyusmazlik"] == []


def test_verify_outcomes_requires_topic_or_code():
    with pytest.raises(kapsam.KapsamError) as exc:
        kapsam.verify_outcomes(FakeFed({}), "fen-bilimleri-dersi", "5.Sınıf", None, None)
    assert exc.value.status == "konu_veya_kazanim_gerekli"
