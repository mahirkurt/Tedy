"""Final whole-branch review, finding 4 (minor, taken):

`chat_with_tools` prefixes `[S#] label` marker lines onto a tool's body before
its own 4,000-char tool-result cut (`ClaudeClient._sonuc_icerigi`), but bodies
for `ogrenci_verisi_ara`, `kitap_ara` and `aile_kaynak_ara` are sized to 3,900
chars *without* the marks. With >=8 citations the marks alone add well over
100 chars, so `(marks + body)[:4000]` used to cut the tail of the last hit's
text with no visible marker — the model (and the reader who trusts its
citation) could not tell the content had been truncated mid-sentence.

Fix: `_sonuc_icerigi` truncates the combined marks+body so it never exceeds
4,000 chars, and any actual cut leaves a visible "…[kesildi]" marker instead
of silently dropping the tail.
"""
import os

os.environ["TEST_AUTH_BYPASS"] = "1"

from src.assistant_core import ClaudeClient  # noqa: E402


def _marks(n):
    citations = [{"label": f"output/uzun_dosya_adi_{i}.txt"} for i in range(n)]
    return "\n".join(f"[S{i + 1}] {c['label']}" for i, c in enumerate(citations))


def test_marks_plus_body_over_4000_is_cut_with_a_visible_marker():
    marks = _marks(8)
    body_text = "x" * 3900  # the existing GOVDE_SINIRI/_YEREL_TOPLAM_SINIRI budget
    combined = f"{marks}\n{body_text}"
    # Sanity: this is exactly the overflow the finding names — marks pushed
    # the already-budgeted body past the outer 4,000-char cut.
    assert len(combined) > 4000

    sonuc = ClaudeClient._sonuc_icerigi(combined, None)

    assert isinstance(sonuc, str)
    assert len(sonuc) <= 4000
    assert "kesildi" in sonuc  # a visible marker, not a silent cut
    # Every citation mark must survive: only the tail of the body text is
    # ever cut, never a source marker the model would need to write [Sn] for.
    for i in range(8):
        assert f"[S{i + 1}]" in sonuc


def test_short_result_is_unaffected_by_the_new_cut_marker():
    original = "[S1] output/a.txt\nkısa metin"
    sonuc = ClaudeClient._sonuc_icerigi(original, None)
    assert sonuc == original
    assert "kesildi" not in sonuc


def test_cut_marker_coexists_with_image_notes():
    """The pre-existing image-overflow note (e.g. "görsel çok büyük") must
    still appear in full — the new body-truncation marker must not crowd it
    out, and vice versa."""
    marks = _marks(8)
    body_text = "y" * 3900
    combined = f"{marks}\n{body_text}"
    buyuk = {"data": "A" * 1_500_001, "mimeType": "image/png"}

    sonuc = ClaudeClient._sonuc_icerigi(combined, [buyuk])

    assert isinstance(sonuc, list)
    metin = sonuc[0]["text"]
    assert len(metin) <= 4000
    assert "görsel çok büyük" in metin
    assert "kesildi" in metin
