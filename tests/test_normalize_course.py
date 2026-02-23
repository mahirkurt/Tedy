"""Tests for course name normalization."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.sync_to_google import normalize_course


class TestNormalizeCourse:
    """Exact alias matches."""

    def test_canonical_name_unchanged(self):
        assert normalize_course("Matematik") == "Matematik"

    def test_fransizca_from_ikinci_yabanci_dil(self):
        assert normalize_course("İkinci Yabancı Dil") == "Fransızca"

    def test_fransizca_from_full_name(self):
        assert normalize_course("İkinci Yabancı Dil (Fransızca)") == "Fransızca"

    def test_fransizca_from_tab_name(self):
        assert normalize_course("2. Yabancı Dil (F)") == "Fransızca"

    def test_din_kulturu_from_full(self):
        assert normalize_course("Din Kültürü ve Ahlak Bilgisi") == "Din Kültürü"

    def test_din_kulturu_from_dkab(self):
        assert normalize_course("DKAB") == "Din Kültürü"

    def test_beden_egitimi_from_spor(self):
        assert normalize_course("Beden Eğitimi ve Spor") == "Beden Eğitimi"

    def test_ingilizce_from_language(self):
        assert normalize_course("İngilizce (Language)") == "İngilizce"

    def test_ingilizce_from_language_tab(self):
        assert normalize_course("İngilizce Language") == "İngilizce"

    def test_ingilizce_from_tab_2(self):
        assert normalize_course("İngilizce (2)") == "İngilizce"

    def test_ingilizce_literature_from_parens(self):
        assert normalize_course("İngilizce (Literature)") == "İngilizce Literature"

    def test_bilisim_from_full(self):
        assert normalize_course("Bilişim Teknolojileri") == "Bilişim"


class TestNormalizeCourseParenFallback:
    """Parenthesized suffix stripping fallback."""

    def test_strip_classroom_suffix(self):
        assert normalize_course("Matematik (i-403 (İngilizce))") == "Matematik"

    def test_strip_classroom_fen(self):
        assert normalize_course("Fen Bilimleri (i-322 (Fen Lab))") == "Fen Bilimleri"


class TestNormalizeCourseUnknown:
    """Unknown names pass through unchanged."""

    def test_unknown_course(self):
        assert normalize_course("Robotik Kulübü") == "Robotik Kulübü"

    def test_empty_string(self):
        assert normalize_course("") == ""

    def test_genel(self):
        assert normalize_course("Genel") == "Genel"


class TestTakvimKeywords:
    """Verify takvim keyword classification covers all canonical course names."""

    def test_all_canonical_names_present(self):
        from src.sync_to_google import TAKVIM_DERS_KEYWORDS
        for name in ["matematik", "türkçe", "fen", "sosyal",
                      "din kültürü", "ingilizce", "français", "fransızca",
                      "bilişim", "görsel", "müzik", "beden",
                      "ahlak", "english", "literature"]:
            assert name in TAKVIM_DERS_KEYWORDS, f"Missing: {name}"


from src.sync_to_google import parse_week_range


class TestParseWeekRange:
    def test_basic_parse(self):
        start, end = parse_week_range("20. Hafta 02 Şub. - 08 Şub.")
        assert start is not None
        assert start.month == 2
        assert start.day == 2
        assert end.day == 8

    def test_uses_current_year(self):
        from datetime import datetime
        start, end = parse_week_range("20. Hafta 02 Şub. - 08 Şub.")
        assert start.year == datetime.now().year
