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


def test_numbers_follow_the_answer_not_the_tools(runtime):
    """Live 2026-09-24: three tools returned sources, the answer cited only the
    third, and the reader saw a lone chip reading "3". Chips are numbered in
    the order the reader meets them."""
    text, cites, _ = runtime._finalize_citations(
        "Yalnız bu [S3].", [_cite(label="A"), _cite(label="B"), _cite(label="C")])
    assert text == "Yalnız bu [S1]."
    assert [(c["id"], c["label"]) for c in cites] == [("S1", "C")]


def test_renumbering_keeps_each_marker_on_its_source(runtime):
    text, cites, _ = runtime._finalize_citations(
        "Önce [S2], sonra [S1], yine [S2].", [_cite(label="A"), _cite(label="B")])
    assert text == "Önce [S1], sonra [S2], yine [S1]."
    assert [(c["id"], c["label"]) for c in cites] == [("S1", "B"), ("S2", "A")]


def test_a_source_repeated_in_one_section_is_marked_once(runtime):
    """Live 2026-09-25: an answer drawn wholly from odev_listesi carried a
    chip reading "1" after every sentence and list item — six identical
    chips in one screen. The first marker already ties the section to its
    source; the prompt asks for exactly that and the model did not comply."""
    text, cites, _ = runtime._finalize_citations(
        "En yakın teslim Pazartesi [S1].\n\n"
        "1. **Matematik** — işlemsiz kabul edilmiyor [S1].\n"
        "2. **Türkçe** — ilk derste kontrol edilecek [S1].",
        [_cite()])
    assert text == (
        "En yakın teslim Pazartesi [S1].\n\n"
        "1. **Matematik** — işlemsiz kabul edilmiyor.\n"
        "2. **Türkçe** — ilk derste kontrol edilecek.")
    assert len(cites) == 1


def test_a_new_section_marks_its_source_again(runtime):
    """A heading — or a bold line standing as one — starts a section the
    reader may jump to, so its first sentence names its source again."""
    text, _, _ = runtime._finalize_citations(
        "### Bugün\nA [S1]. B [S1].\n\n**Sonra:**\nC [S1].\n\n### Yarın\nD [S1].",
        [_cite()])
    assert text == "### Bugün\nA [S1]. B.\n\n**Sonra:**\nC [S1].\n\n### Yarın\nD [S1]."


def test_only_a_marker_repeating_the_one_before_it_goes(runtime):
    text, _, _ = runtime._finalize_citations(
        "A [S1]. B [S2]. C [S1]. D [S1].", [_cite(label="A"), _cite(label="B")])
    assert text == "A [S1]. B [S2]. C [S1]. D."
