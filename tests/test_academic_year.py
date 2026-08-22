"""The academic year is derived from the portal's own selectors."""
import json
import pytest

from src.academic_year import (
    YearResolution,
    load_year_state,
    resolve_year,
    save_year_state,
    year_from_donem_code,
    year_from_week_option,
)


class TestYearFromWeekOption:
    def test_autumn_week_starts_the_year(self):
        # observed 2026-08-22: first option of #dp_icerik_secili_hafta
        assert year_from_week_option("14.09.2026 00:00:00") == "2026-2027"

    def test_single_digit_day_parses(self):
        assert year_from_week_option("5.10.2026 00:00:00") == "2026-2027"

    def test_spring_week_belongs_to_the_year_that_began_in_autumn(self):
        assert year_from_week_option("11.01.2027 00:00:00") == "2026-2027"

    def test_august_counts_as_the_new_year(self):
        assert year_from_week_option("31.08.2026 00:00:00") == "2026-2027"

    def test_july_still_belongs_to_the_previous_year(self):
        assert year_from_week_option("15.07.2026 00:00:00") == "2025-2026"

    def test_unparseable_value_returns_none(self):
        assert year_from_week_option("Tamamı") is None
        assert year_from_week_option("") is None


class TestYearFromDonemCode:
    def test_code_start_year_becomes_the_span(self):
        assert year_from_donem_code("202504") == "2025-2026"
        assert year_from_donem_code("202401") == "2024-2025"

    def test_rejects_malformed_codes(self):
        for bad in ("2025", "20250", "abcdef", "", "202500", "202505"):
            assert year_from_donem_code(bad) is None


class TestResolveYear:
    def test_first_detection_initialises(self):
        assert resolve_year("2026-2027", None) == \
            YearResolution("2026-2027", "initialized")

    def test_same_year_is_current(self):
        assert resolve_year("2026-2027", "2026-2027") == \
            YearResolution("2026-2027", "current")

    def test_later_year_is_a_rollover(self):
        assert resolve_year("2026-2027", "2025-2026") == \
            YearResolution("2026-2027", "rollover")

    def test_undetected_holds_the_stored_year(self):
        """A blocked page must never reset the year."""
        assert resolve_year(None, "2026-2027") == \
            YearResolution("2026-2027", "held")

    def test_earlier_year_is_ignored(self):
        """A year cannot un-happen; a stale page must not roll us back."""
        assert resolve_year("2025-2026", "2026-2027") == \
            YearResolution("2026-2027", "ignored_regression")

    def test_nothing_known_at_all(self):
        assert resolve_year(None, None) == YearResolution(None, "unknown")


class TestYearState:
    def test_missing_file_is_empty(self, tmp_path):
        assert load_year_state(str(tmp_path / "nope.json")) == {}

    def test_round_trip(self, tmp_path):
        p = str(tmp_path / "academic_year.json")
        saved = save_year_state(p, "2026-2027", "2025-2026", "week_selector")
        assert saved["year"] == "2026-2027"
        assert saved["previous"] == "2025-2026"
        assert saved["source"] == "week_selector"
        assert saved["grade"] is None
        assert "detected_at" in saved
        assert load_year_state(p) == saved

    def test_corrupted_state_is_empty_not_an_exception(self, tmp_path):
        p = tmp_path / "academic_year.json"
        p.write_text("{not json", encoding="utf-8")
        assert load_year_state(str(p)) == {}
