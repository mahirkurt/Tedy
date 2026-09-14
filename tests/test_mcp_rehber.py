"""Guide sections from vendored references: mapping integrity, part size, navigation, search."""
import re

import pytest

from src.mcp_server import rehber, vendor_sync


def test_every_mapped_heading_exists_in_vendor():
    for bolum, sources in rehber.SECTIONS.items():
        for filename, numbers in sources:
            text = (vendor_sync.VENDOR_DIR / filename).read_text(encoding="utf-8")
            present = {h for h, _ in rehber.split_sections(text)}
            for number in numbers:
                assert any(re.match(rf"##\s+{re.escape(number)}(\.|\s)", h) for h in present), (bolum, filename, number)


@pytest.mark.parametrize("bolum", sorted(rehber.SECTIONS))
def test_each_section_resolves_to_bounded_parts(bolum):
    first = rehber.guide(bolum)
    assert first["status"] == "ok"
    assert first["toplam_parca"] >= 1
    assert first["metin"].strip()
    for n in range(1, first["toplam_parca"] + 1):
        part = rehber.guide(bolum, parca=n)
        assert len(part["metin"].encode("utf-8")) <= rehber.PART_MAX_BYTES
        assert part["kaynaklar"]


def test_akis_starts_with_build_workflow_and_warns_about_plugin_paths():
    part = rehber.guide("akis")
    assert "İnşa iş akışı" in part["metin"]
    assert "edupedia_derle" in part["uyari"]


def test_part_navigation_and_out_of_range():
    first = rehber.guide("carbon")
    if first["toplam_parca"] > 1:
        assert first["sonraki_parca"] == 2
    bad = rehber.guide("carbon", parca=first["toplam_parca"] + 1)
    assert bad["status"] == "gecersiz_parca"


def test_unknown_section_lists_valid_sections():
    body = rehber.guide("yok-boyle-bolum")
    assert body["status"] == "gecersiz_bolum"
    assert body["bolumler"] == sorted(rehber.SECTIONS)


def test_split_sections_skips_table_of_contents():
    text = "# T\n\n## İçindekiler\n- a\n\n## 1. Bir\nx\n\n## 2. İki\ny\n"
    assert [h for h, _ in rehber.split_sections(text)] == ["## 1. Bir", "## 2. İki"]


def test_search_finds_mcq_segment_and_folds_turkish_case():
    hits = rehber.search("MCQ çoktan seçmeli")
    assert hits["status"] == "ok"
    assert any("mcq" in h["baslik"].lower() for h in hits["sonuclar"])
    upper = rehber.search("İNŞA İŞ AKIŞI")
    assert any("İnşa iş akışı" in h["baslik"] for h in upper["sonuclar"])


def test_search_empty_query():
    assert rehber.search("  ")["status"] == "gecersiz_sorgu"
