"""Citation resolution: markers the model emits must map to real sources."""
import pytest
from src.assistant_core import AssistantRuntime


@pytest.fixture
def runtime(tmp_path):
    (tmp_path / "output").mkdir()
    return AssistantRuntime(tmp_path)


def _cite(kind="mufredat", label="MEB", snippet="s"):
    return {"kind": kind, "label": label, "locator": {},
            "snippet": snippet, "confidence": 0.9}


def test_markers_are_numbered_in_the_order_the_tools_returned(runtime):
    text, cites, dropped = runtime._finalize_citations(
        "Önce [S1] sonra [S2].", [_cite(label="A"), _cite(label="B")])

    assert [c["id"] for c in cites] == ["S1", "S2"]
    assert [c["label"] for c in cites] == ["A", "B"]
    assert dropped == 0
    assert text == "Önce [S1] sonra [S2]."


def test_a_marker_with_no_source_behind_it_is_removed(runtime):
    """The old code deleted every marker in the frontend, so a correct citation
    could never reach the reader. Now only unresolvable ones go."""
    text, cites, dropped = runtime._finalize_citations(
        "Gerçek [S1] ama uydurma [S7].", [_cite()])

    assert "[S7]" not in text
    assert "[S1]" in text
    assert dropped == 1


def test_uncited_sources_are_dropped_from_the_panel(runtime):
    """A source the answer never refers to is noise in the sidebar."""
    _, cites, _ = runtime._finalize_citations("Yalnız [S1].",
                                              [_cite(label="A"), _cite(label="B")])
    assert [c["label"] for c in cites] == ["A"]


def test_repeated_marker_keeps_one_source_entry(runtime):
    _, cites, dropped = runtime._finalize_citations("[S1] ve yine [S1].", [_cite()])
    assert len(cites) == 1 and dropped == 0


def test_answer_without_markers_keeps_no_sources(runtime):
    text, cites, dropped = runtime._finalize_citations("Atıfsız cevap.", [_cite()])
    assert text == "Atıfsız cevap." and cites == [] and dropped == 0


def test_removing_a_marker_does_not_leave_double_spaces(runtime):
    text, _, _ = runtime._finalize_citations("Bir [S9] iki.", [])
    assert text == "Bir iki."


def test_every_surviving_citation_carries_its_kind(runtime):
    _, cites, _ = runtime._finalize_citations(
        "[S1] [S2]", [_cite(kind="ogrenci"), _cite(kind="kitap")])
    assert [c["kind"] for c in cites] == ["ogrenci", "kitap"]
