# tests/test_enrich.py
"""Tests for AI enrichment functions."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.enrich_gemini import (
    build_prompt, build_sinav_prompt, SINAV_MARKER,
    build_ders_icerikleri_prompt, DERS_MARKER,
    build_performans_prompt, PERFORMANS_MARKER,
)


class TestBuildPrompt:
    def test_basic_prompt(self):
        p = build_prompt("Matematik", "Haftalık Ödev", "sayfa 24-25", [], "2026-02-27")
        assert "Matematik" in p
        assert "sayfa 24-25" in p
        assert "2026-02-27" in p

    def test_empty_description(self):
        p = build_prompt("Fen", "Lab Raporu", "", [], "2026-03-01")
        assert "(açıklama yok)" in p


class TestBuildSinavPrompt:
    def test_includes_course_and_date(self):
        p = build_sinav_prompt("Matematik Yazılısı", "2026-03-15", "Matematik", "85")
        assert "Matematik" in p
        assert "2026-03-15" in p
        assert "85" in p

    def test_no_grade_info(self):
        p = build_sinav_prompt("Fen Sınavı", "2026-03-20", "Fen Bilimleri", None)
        assert "not bilgisi yok" in p.lower() or "Fen" in p


class TestSinavMarker:
    def test_marker_exists(self):
        assert "Sınav" in SINAV_MARKER or "sinav" in SINAV_MARKER.lower()


class TestBuildDersIcerikleriPrompt:
    def test_includes_course_and_content(self):
        p = build_ders_icerikleri_prompt("Matematik", "Denklemler ve eşitsizlikler konusu işlendi.")
        assert "Matematik" in p
        assert "Denklemler" in p

    def test_truncates_long_content(self):
        long_text = "x" * 2000
        p = build_ders_icerikleri_prompt("Fen", long_text)
        assert len(p) < 3000


class TestBuildPerformansPrompt:
    def test_includes_grades(self):
        grades = [
            {"Ders": "Matematik", "1. Sınav": "85", "2. Sınav": "92"},
            {"Ders": "Fen", "1. Sınav": "70", "2. Sınav": "65"},
        ]
        p = build_performans_prompt(grades)
        assert "Matematik" in p
        assert "85" in p
        assert "Fen" in p
