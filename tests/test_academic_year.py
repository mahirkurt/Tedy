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
    detect_academic_year,
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


class FakeOption:
    def __init__(self, value, text=""):
        self._value, self.text = value, text

    def get_attribute(self, name):
        return self._value if name == "value" else None


class FakeSelect:
    def __init__(self, el_id, options):
        self.el_id, self._options = el_id, options

    def find_elements(self, _by, tag):
        return self._options if tag == "option" else []


class FakeDriver:
    """Serves selects per URL, the way the portal serves pages."""

    def __init__(self, pages):
        self.pages, self.current_url, self.visited = pages, "", []

    def get(self, url):
        self.current_url = url
        self.visited.append(url)

    def find_elements(self, _by, value):
        for sel in self.pages.get(self.current_url, []):
            if sel.el_id == value:
                return [sel]
        return []


BASE = "https://portal.tedronesans.k12.tr"
HOME = f"{BASE}/pages/ogrenci/"
GELISIM = f"{BASE}/pages/ogrenci_istekler/p_gelisim_raporum"

# Fixture spanning two academic years: July 2026 (2025-2026) and Sept 2026 (2026-2027)
WEEKS_TWO_YEARS = FakeSelect("dp_icerik_secili_hafta", [
    FakeOption("21.09.2026 00:00:00"),   # 2026-2027
    FakeOption("15.07.2026 00:00:00"),   # earliest, maps to 2025-2026
    FakeOption("28.09.2026 00:00:00"),   # 2026-2027
])

# Fixture with all weeks in the same year (all Sept 2026 = 2026-2027)
WEEKS_SAME_YEAR = FakeSelect("dp_icerik_secili_hafta", [
    FakeOption("21.09.2026 00:00:00"),
    FakeOption("14.09.2026 00:00:00"),   # earliest within same year, not first
    FakeOption("28.09.2026 00:00:00"),
])

DONEMS = FakeSelect("genel_icerik_dp_ilgili_donem", [
    FakeOption("202401"), FakeOption("202504"), FakeOption("202502"),
])


class TestDetectAcademicYear:
    def test_week_selector_wins(self):
        d = FakeDriver({HOME: [WEEKS_TWO_YEARS], GELISIM: [DONEMS]})
        assert detect_academic_year(d, BASE) == ("2026-2027", "week_selector")

    def test_latest_week_defines_the_year_regardless_of_order(self):
        """max() is load-bearing: picks the latest span (2026-2027 over 2025-2026).

        See the comment at the max(weeks) call site: this is a deliberate
        divergence from the spec's literal "earliest option" wording,
        chosen because it degrades safely when a stale prior-year option
        leaks into the selector (see
        test_stale_previous_year_option_does_not_suppress_detection below).
        """
        d = FakeDriver({HOME: [WEEKS_TWO_YEARS]})
        year, _ = detect_academic_year(d, BASE)
        assert year == "2026-2027"

    def test_latest_within_same_year_regardless_of_order(self):
        """When all weeks are in the same year, the result is unambiguous
        regardless of which one happens to be earliest/latest/first."""
        d = FakeDriver({HOME: [WEEKS_SAME_YEAR]})
        year, _ = detect_academic_year(d, BASE)
        assert year == "2026-2027"

    def test_stale_previous_year_option_does_not_suppress_detection(self):
        """A leaked prior-year option in the week selector must not make
        detection report the OLD year - that would equal the stored year
        on every run (resolve_year -> "current"), permanently and silently
        hiding a real rollover. This is exactly what min() would do here;
        max() reports the new year instead."""
        d = FakeDriver({HOME: [WEEKS_TWO_YEARS]})
        year, _ = detect_academic_year(d, BASE)
        assert year != "2025-2026"
        assert year == "2026-2027"

    def test_falls_back_to_highest_donem_code(self):
        d = FakeDriver({HOME: [], GELISIM: [DONEMS]})
        assert detect_academic_year(d, BASE) == ("2025-2026", "donem_selector")

    def test_no_signal_returns_none(self):
        d = FakeDriver({HOME: [], GELISIM: []})
        assert detect_academic_year(d, BASE) == (None, "none")

    def test_does_not_visit_gelisim_when_home_answers(self):
        """Detection runs every sync; don't load a page we don't need."""
        d = FakeDriver({HOME: [WEEKS_TWO_YEARS], GELISIM: [DONEMS]})
        detect_academic_year(d, BASE)
        assert GELISIM not in d.visited

    def test_find_elements_error_is_not_fatal(self):
        """find_elements exceptions on the element are caught."""
        class Boom(FakeDriver):
            def find_elements(self, _by, value):
                raise RuntimeError("stale element")
        assert detect_academic_year(Boom({}), BASE) == (None, "none")

    def test_driver_get_error_is_not_fatal(self):
        """driver.get() exceptions (redirect, 404, etc.) are caught."""
        class BoomOnGet(FakeDriver):
            def get(self, url):
                raise RuntimeError("page not found")
        assert detect_academic_year(BoomOnGet({}), BASE) == (None, "none")
