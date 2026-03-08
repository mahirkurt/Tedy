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
        assert normalize_course("İngilizce (Literature)") == "İngilizce"

    def test_ingilizce_literature_canonical(self):
        assert normalize_course("İngilizce Literature") == "İngilizce"

    def test_bilisim_from_full(self):
        assert normalize_course("Bilişim Teknolojileri") == "Bilişim"

    def test_ahlak_from_egitimi(self):
        assert normalize_course("Ahlak ve Yurttaşlık Eğitimi") == "Ahlak ve Yurttaşlık"


class TestNormalizeCourseParenFallback:
    """Parenthesized suffix stripping fallback."""

    def test_strip_classroom_suffix(self):
        assert normalize_course("Matematik (i-403 (İngilizce))") == "Matematik"

    def test_strip_classroom_fen(self):
        assert normalize_course("Fen Bilimleri (i-322 (Fen Lab))") == "Fen Bilimleri"

    def test_double_paren_literature(self):
        """İngilizce (Literature) with classroom suffix should resolve to İngilizce."""
        assert normalize_course("İngilizce (Literature) (i-403 (İngilizce))") == "İngilizce"

    def test_double_paren_language(self):
        """İngilizce (Language) with classroom suffix should resolve to İngilizce."""
        assert normalize_course("İngilizce (Language) (i-403 (İngilizce))") == "İngilizce"

    def test_double_paren_fransizca(self):
        """İkinci Yabancı Dil (Fransızca) with classroom suffix should resolve to Fransızca."""
        assert normalize_course("İkinci Yabancı Dil (Fransızca) (i-326)") == "Fransızca"


class TestNormalizeCourseEbaSuffixes:
    """EBA tracker files append '(Yeni Müfredat)' to course names."""

    def test_fen_yeni_mufredat(self):
        assert normalize_course("Fen Bilimleri (Yeni Müfredat)") == "Fen Bilimleri"

    def test_matematik_yeni_mufredat(self):
        assert normalize_course("Matematik (Yeni Müfredat)") == "Matematik"

    def test_sosyal_yeni_mufredat(self):
        assert normalize_course("Sosyal Bilgiler (Yeni Müfredat)") == "Sosyal Bilgiler"

    def test_turkce_yeni_mufredat(self):
        assert normalize_course("Türkçe (Yeni Müfredat)") == "Türkçe"


class TestNormalizeCourseScheduleFullPaths:
    """All course names from ders_programi (with room codes)."""

    def test_ahlak_with_room(self):
        assert normalize_course("Ahlak ve Yurttaşlık (i-435 (Türkçe))") == "Ahlak ve Yurttaşlık"

    def test_beden_with_room(self):
        assert normalize_course("Beden Eğitimi ve Spor (Büyük Spor Salonu)") == "Beden Eğitimi"

    def test_bilisim_with_room(self):
        assert normalize_course("Bilişim Teknolojileri (i-420 (PC Lab))") == "Bilişim"

    def test_dkab_with_room(self):
        assert normalize_course("Din Kültürü ve Ahlak Bilgisi (i-409 (Sosyal Bilgiler))") == "Din Kültürü"

    def test_gorsel_with_room(self):
        assert normalize_course("Görsel Sanatlar (i-422 (Görsel Sanatlar))") == "Görsel Sanatlar"

    def test_muzik_with_room(self):
        assert normalize_course("Müzik (i-110)") == "Müzik"

    def test_sosyal_with_room(self):
        assert normalize_course("Sosyal Bilgiler (i-407 (Sosyal Bilgiler))") == "Sosyal Bilgiler"

    def test_turkce_with_room(self):
        assert normalize_course("Türkçe (i-433 (Türkçe))") == "Türkçe"

    def test_matematik_various_rooms(self):
        assert normalize_course("Matematik (i-403 (İngilizce))") == "Matematik"
        assert normalize_course("Matematik (i-405 (İngilizce))") == "Matematik"
        assert normalize_course("Matematik (i-430 (Matemetik))") == "Matematik"

    def test_ingilizce_bare_with_room(self):
        assert normalize_course("İngilizce (i-403 (İngilizce))") == "İngilizce"


class TestNormalizeCourseUnknown:
    """Unknown names pass through unchanged."""

    def test_unknown_course(self):
        assert normalize_course("Robotik Kulübü") == "Robotik Kulübü"

    def test_empty_string(self):
        assert normalize_course("") == ""

    def test_genel(self):
        assert normalize_course("Genel") == "Genel"

    def test_pdr(self):
        assert normalize_course("PDR") == "PDR"

    def test_sinif_ogretmeni(self):
        assert normalize_course("Sınıf Öğretmeni") == "Sınıf Öğretmeni"


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
