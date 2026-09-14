"""edupedia_kapsam end-to-end over a fake federation: frame, pages, figures, OER, anamnesis, run record."""
import pytest

from src.mcp_server import kapsam
from src.mcp_server.federation import FederationError
from src.mcp_server.runs import RunStore

FULL = "drmahirkurt@gmail.com"
SLUG = "fen-bilimleri-dersi"


class FakeFed:
    def __init__(self, responses, configured=("maarif-mufredat", "egitim-kaynak", "anamnesis"), fail=()):
        self.responses, self._configured, self.fail, self.calls = responses, set(configured), set(fail), []

    def configured(self, server):
        return server in self._configured

    def call(self, server, tool, args, beklenen):
        self.calls.append((server, tool, args, beklenen))
        if (server, tool) in self.fail:
            raise FederationError(server, tool, "timeout")
        value = self.responses[(server, tool)]
        # Some Task 11 tests need a response that depends on the call args (e.g. re-resolving a
        # subject by slug) or a queue consumed one call at a time (multi-part anamnesis ingest);
        # callables cover both without complicating the common static-dict case.
        return value(args) if callable(value) else value

    def called(self, server, tool):
        return [c for c in self.calls if c[0] == server and c[1] == tool]


class SequencedIngestFed(FakeFed):
    """FakeFed whose (anamnesis, ingest_document) responses are consumed one at a time from a
    queue, so a test can prove Task 11 Ruling 4's continuation loop calls exactly the expected
    number of times with the expected offset/doc_id per call."""

    def __init__(self, responses, ingest_queue, **kw):
        super().__init__(responses, **kw)
        self._ingest_queue = list(ingest_queue)

    def call(self, server, tool, args, beklenen):
        if (server, tool) == ("anamnesis", "ingest_document"):
            self.calls.append((server, tool, args, beklenen))
            return self._ingest_queue.pop(0)
        return super().call(server, tool, args, beklenen)


OUTCOME = {"code": "FB.5.4.1.1", "text": "Maddenin hâllerini açıklar.", "subject": SLUG, "grade": "5.Sınıf",
           "document_id": 9, "page_no": 40, "fragment_type": "outcome"}


def _responses(over=None):
    # A plain positional dict, not **kwargs: the override keys are (server, tool) tuples, and
    # Python's ** call-site unpacking requires string keys, so **{(a, b): v} raises TypeError.
    base = {
        ("maarif-mufredat", "list_subjects"): [{"slug": SLUG, "name": "Fen Bilimleri Dersi", "level": "temel-egitim", "grade_count": 6}],
        ("maarif-mufredat", "search_learning_outcomes"): {"results": [OUTCOME], "included_fragment_types": ["outcome"]},
        ("maarif-mufredat", "list_textbooks"): [
            {"document_id": 196, "title": "Fen 5 (boş)", "page_count": 0},
            {"document_id": 197, "title": "Fen Bilimleri 5", "page_count": 240},
        ],
        ("maarif-mufredat", "search_figures"): {"query": "x", "count": 2, "figures": [
            {"figure_id": 11, "document_id": 197, "page_no": 115, "label": "Görsel 4.2", "caption": "Su döngüsü " * 40},
            {"figure_id": 10, "document_id": 197, "page_no": 112, "label": "Görsel 4.1", "caption": "Katı sıvı gaz"},
        ]},
        ("maarif-mufredat", "get_document_text"): {"document": {"document_id": 197}, "total_pages": 240, "returned": 6,
                                                   "truncated": False, "pages": [{"page_no": p, "text": f"sayfa {p} metni"} for p in range(111, 117)]},
        ("egitim-kaynak", "kb_search"): {"status": "ok", "results": [
            {"doc_id": "phet:states", "title": "Maddenin Hâlleri", "passage": "p" * 500, "license": "CC BY-NC 4.0",
             "quote_allowed": True, "source_url": "https://phet", "match_kind": "text"},
            {"doc_id": "wikipedia-tr:Madde", "title": "Madde", "passage": "w" * 500, "license": "CC BY-SA 4.0",
             "quote_allowed": False, "source_url": "https://wiki", "match_kind": "text"},
        ]},
        ("egitim-kaynak", "kb_for_outcome"): {"status": "degraded", "reason": "interim_low_relevance", "results": []},
        ("anamnesis", "ingest_document"): {"doc_id": "x", "collection": "y", "n_chunks": 3},
    }
    if over:
        base.update(over)
    return base


def _build(tmp_path, fed, **kw):
    runs = RunStore(tmp_path)
    return kapsam.KapsamBuilder(fed, runs, clock=lambda: 1_800_000_000.0).build(FULL, "Fen Bilimleri", "5", **kw), runs


def test_happy_path_frames_textbook_pages_figures_oer_and_ingests(tmp_path):
    fed = FakeFed(_responses())
    body, runs = _build(tmp_path, fed, konu="maddenin halleri")
    assert body["status"] == "ok"
    assert body["ders"] == {"slug": SLUG, "name": "Fen Bilimleri Dersi"}
    assert body["cerceve"] == {"kind": "textbook", "document_id": 197, "title": "Fen Bilimleri 5", "sayfalar": "111-116"}
    assert fed.called("maarif-mufredat", "get_document_text")[0][2] == {"document_id": 197, "page_range": "111-116", "max_chars": 60000}
    assert [p["page_no"] for p in body["kitap_sayfalari"]] == list(range(111, 117))
    assert [f["figure_id"] for f in body["figur_adaylari"]] == [10, 11]
    assert len(body["figur_adaylari"][1]["aciklama"]) == 200
    assert len(body["oer"][0]["pasaj"]) == 300 and len(body["oer"][1]["pasaj"]) == 160
    assert body["oer"][1]["alinti_izni"] is False

    ingest = fed.called("anamnesis", "ingest_document")[0][2]
    assert ingest["collection"] == f"edupedia:run:{body['run_id']}"
    assert ingest["doc_id"] == f"edupedia:{body['run_id']}:kitap/197/111-116"
    assert len(ingest["doc_id"].encode()) <= 56
    assert "=== Sayfa 111 ===" in ingest["text"] and ingest["ttl_hours"] == 168

    assert body["coverage"] == {"maarif-mufredat": "hit", "egitim-kaynak": "hit", "anamnesis": "hit"}
    record = runs.load(body["run_id"])
    assert record["created_by"] == FULL and record["cerceve"]["document_id"] == 197
    assert len(runs.pages(body["run_id"])) == 6
    assert body["mcp_verified"] is False and body["caveat"] and body["sonraki_adim"]


def test_anamnesis_failure_degrades_but_keeps_local_pages(tmp_path):
    fed = FakeFed(_responses(), fail={("anamnesis", "ingest_document")})
    body, runs = _build(tmp_path, fed, konu="maddenin halleri")
    assert body["status"] == "ok"
    assert body["coverage"]["anamnesis"] == "degraded:timeout"
    assert len(runs.pages(body["run_id"])) == 6


def test_anamnesis_unconfigured_is_skipped(tmp_path):
    fed = FakeFed(_responses(), configured=("maarif-mufredat", "egitim-kaynak"))
    body, _ = _build(tmp_path, fed, konu="maddenin halleri")
    assert body["coverage"]["anamnesis"] == "skipped:anahtar yok"
    assert not fed.called("anamnesis", "ingest_document")


def test_no_textbook_with_pages_falls_back_to_program_frame(tmp_path):
    fed = FakeFed(_responses({("maarif-mufredat", "list_textbooks"): [{"document_id": 196, "title": "x", "page_count": 0}]}))
    body, _ = _build(tmp_path, fed, konu="maddenin halleri")
    assert body["cerceve"]["kind"] == "program"
    assert body["cerceve"]["document_id"] == 9
    assert body["kitap_sayfalari"] == []
    assert not fed.called("maarif-mufredat", "get_document_text")


def test_no_figure_hits_means_no_page_fetch(tmp_path):
    fed = FakeFed(_responses({("maarif-mufredat", "search_figures"): {"query": "x", "count": 0, "figures": []}}))
    body, _ = _build(tmp_path, fed, konu="maddenin halleri")
    assert body["cerceve"]["sayfalar"] is None
    assert "sayfa" in body["cerceve"]["not"]
    assert not fed.called("maarif-mufredat", "get_document_text")


def test_textbook_step_failure_degrades_mufredat_but_keeps_verified_outcomes(tmp_path):
    fed = FakeFed(_responses(), fail={("maarif-mufredat", "list_textbooks")})
    body, runs = _build(tmp_path, fed, konu="maddenin halleri")
    assert body["status"] == "ok"
    assert body["kazanimlar"][0]["code"] == "FB.5.4.1.1"
    assert body["coverage"]["maarif-mufredat"] == "degraded:timeout"
    assert body["cerceve"]["kind"] is None and "list_textbooks" in body["cerceve"]["not"]
    assert runs.load(body["run_id"])["coverage"]["maarif-mufredat"] == "degraded:timeout"


def test_egitim_kaynak_failure_is_degraded(tmp_path):
    fed = FakeFed(_responses(), fail={("egitim-kaynak", "kb_search")})
    body, _ = _build(tmp_path, fed, konu="maddenin halleri")
    assert body["oer"] == [] and body["coverage"]["egitim-kaynak"] == "degraded:timeout"


def test_outcome_code_adds_kb_for_outcome(tmp_path):
    fed = FakeFed(_responses())
    body, _ = _build(tmp_path, fed, kazanim_kodu="FB.5.4.1.1")
    assert fed.called("egitim-kaynak", "kb_for_outcome")[0][2] == {"outcome_code": "FB.5.4.1.1", "top_k": 3}
    assert body["kazanim_eslesmesi"] == {"status": "degraded", "reason": "interim_low_relevance", "sonuc_sayisi": 0}


@pytest.mark.parametrize("sinif,status", [("13", "gecersiz_sinif"), ("abc", "gecersiz_sinif")])
def test_invalid_grade(tmp_path, sinif, status):
    runs = RunStore(tmp_path)
    body = kapsam.KapsamBuilder(FakeFed(_responses()), runs).build(FULL, "Fen Bilimleri", sinif, konu="x")
    assert body["status"] == status
    assert not (tmp_path / "edupedia_runs").exists()


def test_verification_error_passes_status_without_run(tmp_path):
    fed = FakeFed(_responses(), fail={("maarif-mufredat", "list_subjects")})
    body, _ = _build(tmp_path, fed, konu="x")
    assert body["status"] == "manual_required"
    assert body["coverage"] == {"maarif-mufredat": "degraded:timeout"}
    assert "run_id" not in body
    assert not (tmp_path / "edupedia_runs").exists()


def test_anamnesis_doc_id_stays_within_limit():
    long_id = kapsam.anamnesis_doc_id("abcdef012345", 123456789, 100000, 100005)
    assert len(long_id.encode()) <= 56


# --- Task 11 Ruling 2: a by-code "ders" mismatch reframes with the CORRECTED subject ---------

def test_ders_mismatch_by_code_reframes_with_corrected_subject(tmp_path):
    math_slug = "matematik-dersi"

    def list_subjects(args):
        q = args.get("q")
        if q == "Matematik":
            return [{"slug": math_slug, "name": "Matematik Dersi", "level": "temel-egitim", "grade_count": 8}]
        if q == SLUG:
            return [{"slug": SLUG, "name": "Fen Bilimleri Dersi", "level": "temel-egitim", "grade_count": 6}]
        return []

    fed = FakeFed(_responses({("maarif-mufredat", "list_subjects"): list_subjects}))
    runs = RunStore(tmp_path)
    body = kapsam.KapsamBuilder(fed, runs, clock=lambda: 1_800_000_000.0).build(
        FULL, "Matematik", "5", kazanim_kodu="FB.5.4.1.1")

    assert body["status"] == "ok"
    # The response's ders field carries the CORRECTED subject (from the outcome's own curriculum
    # slug), not the caller's original (wrong) claim.
    assert body["ders"] == {"slug": SLUG, "name": "Fen Bilimleri Dersi"}
    # uyusmazlik itself is returned unchanged — it still reports the caller's original claim.
    assert body["uyusmazlik"] == [{"alan": "ders", "verilen": math_slug, "mufredat": SLUG}]
    # Framing (textbook/figures) used the CORRECTED subject, not the caller's claim.
    assert body["cerceve"]["kind"] == "textbook" and body["cerceve"]["document_id"] == 197
    assert fed.called("maarif-mufredat", "list_textbooks")[0][2]["subject"] == SLUG
    assert fed.called("maarif-mufredat", "search_figures")[0][2]["subject"] == SLUG


# --- Task 11 Ruling 3: "konu_sinifi" is carried in the response but never changes the grade ---

def test_topic_only_at_other_grade_does_not_change_grade(tmp_path):
    other_grade_outcome = {**OUTCOME, "code": "FB.6.4.1.1", "grade": "6.Sınıf"}
    fed = FakeFed(_responses({
        ("maarif-mufredat", "search_learning_outcomes"):
            {"results": [other_grade_outcome], "included_fragment_types": ["outcome"]},
    }))
    body, _ = _build(tmp_path, fed, konu="maddenin halleri")
    assert body["status"] == "ok"
    assert body["sinif"] == "5.Sınıf"  # unchanged despite the topic only existing at 6.Sınıf
    assert body["uyusmazlik"] == [{"alan": "konu_sinifi", "verilen": "5.Sınıf", "mufredat": "6.Sınıf"}]
    assert body["kazanimlar"] == []


# --- Task 11 Ruling 4: honest partial anamnesis ingest (multi-part continuation) ---------------

def test_ingest_continues_with_offset_and_part_suffix_until_next_offset_null(tmp_path):
    fed = SequencedIngestFed(_responses(), ingest_queue=[
        {"doc_id": "x", "collection": "y", "n_chunks": 3, "next_offset": 60000},
        {"doc_id": "x::part2", "collection": "y", "n_chunks": 1, "next_offset": None},
    ])
    body, _ = _build(tmp_path, fed, konu="maddenin halleri")
    calls = fed.called("anamnesis", "ingest_document")
    assert len(calls) == 2
    first_args, second_args = calls[0][2], calls[1][2]
    assert "offset" not in first_args
    assert first_args["doc_id"] == f"edupedia:{body['run_id']}:kitap/197/111-116"
    assert second_args["offset"] == 60000
    assert second_args["doc_id"] == f"edupedia:{body['run_id']}:kitap/197/111-116::part2"
    assert len(second_args["doc_id"].encode()) <= 56
    # continuation calls keep the same text/collection/title/source/ttl_hours
    for key in ("text", "collection", "title", "source", "ttl_hours"):
        assert second_args[key] == first_args[key]
    assert body["coverage"]["anamnesis"] == "hit"


def test_ingest_gives_up_after_max_parts_and_degrades(tmp_path):
    fed = SequencedIngestFed(_responses(), ingest_queue=[
        {"doc_id": "x", "collection": "y", "n_chunks": 1, "next_offset": 100 * n} for n in range(1, 9)
    ])
    body, _ = _build(tmp_path, fed, konu="maddenin halleri")
    calls = fed.called("anamnesis", "ingest_document")
    assert len(calls) == kapsam.INGEST_MAX_PARTS == 8
    assert body["coverage"]["anamnesis"] == "degraded:kismi_alim"
