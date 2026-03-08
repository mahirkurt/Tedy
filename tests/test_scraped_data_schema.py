"""Schema validation tests for output/scraped_data.json."""
import sys
import os
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DATA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "output", "scraped_data.json"
)

REQUIRED_TOP_LEVEL_KEYS = [
    "scraped_at",
    "ders_programi",
    "odevlerim",
    "takim_calismalari",
    "takvim",
    "ders_icerikleri",
    "ogep",
    "gelisim_raporu",
    "duyurular",
]


@pytest.fixture(scope="module")
def scraped_data():
    if not os.path.exists(DATA_PATH):
        pytest.skip("output/scraped_data.json not found")
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


class TestTopLevelStructure:
    def test_is_dict(self, scraped_data):
        assert isinstance(scraped_data, dict)

    @pytest.mark.parametrize("key", REQUIRED_TOP_LEVEL_KEYS)
    def test_required_key_present(self, scraped_data, key):
        assert key in scraped_data, f"Missing top-level key: {key}"

    def test_scraped_at_is_string(self, scraped_data):
        assert isinstance(scraped_data["scraped_at"], str)

    def test_scraped_at_looks_like_iso(self, scraped_data):
        ts = scraped_data["scraped_at"]
        # Basic check: contains date separator and time separator
        assert "T" in ts or " " in ts, f"scraped_at does not look like ISO timestamp: {ts}"

    def test_no_sinavlar_key(self, scraped_data):
        assert "sinavlar" not in scraped_data, (
            "sinavlar should not be a top-level key (exam data is within gelisim_raporu)"
        )


class TestDersProgrami:
    def test_is_list(self, scraped_data):
        assert isinstance(scraped_data["ders_programi"], list)

    def test_non_empty(self, scraped_data):
        assert len(scraped_data["ders_programi"]) > 0

    def test_each_entry_has_week_label(self, scraped_data):
        for i, entry in enumerate(scraped_data["ders_programi"]):
            assert "week_label" in entry, f"ders_programi[{i}] missing week_label"
            assert isinstance(entry["week_label"], str)

    def test_each_entry_has_schedule(self, scraped_data):
        for i, entry in enumerate(scraped_data["ders_programi"]):
            assert "schedule" in entry, f"ders_programi[{i}] missing schedule"
            assert isinstance(entry["schedule"], dict)

    def test_schedule_has_rows(self, scraped_data):
        for i, entry in enumerate(scraped_data["ders_programi"]):
            schedule = entry["schedule"]
            assert "rows" in schedule, f"ders_programi[{i}].schedule missing rows"
            assert isinstance(schedule["rows"], list)

    def test_schedule_has_headers(self, scraped_data):
        for i, entry in enumerate(scraped_data["ders_programi"]):
            schedule = entry["schedule"]
            assert "headers" in schedule, f"ders_programi[{i}].schedule missing headers"
            assert isinstance(schedule["headers"], list)

    def test_each_entry_has_screenshot(self, scraped_data):
        for i, entry in enumerate(scraped_data["ders_programi"]):
            assert "screenshot" in entry, f"ders_programi[{i}] missing screenshot"
            assert isinstance(entry["screenshot"], str)

    def test_rows_are_lists(self, scraped_data):
        for i, entry in enumerate(scraped_data["ders_programi"]):
            for j, row in enumerate(entry["schedule"]["rows"]):
                assert isinstance(row, list), (
                    f"ders_programi[{i}].schedule.rows[{j}] is not a list"
                )


class TestOdevlerim:
    def test_is_dict(self, scraped_data):
        assert isinstance(scraped_data["odevlerim"], dict)

    def test_has_homework_key(self, scraped_data):
        assert "homework" in scraped_data["odevlerim"]

    def test_homework_is_dict(self, scraped_data):
        assert isinstance(scraped_data["odevlerim"]["homework"], dict)

    def test_homework_has_rows(self, scraped_data):
        hw = scraped_data["odevlerim"]["homework"]
        assert "rows" in hw, "odevlerim.homework missing rows"
        assert isinstance(hw["rows"], list)

    def test_has_summary(self, scraped_data):
        assert "summary" in scraped_data["odevlerim"]
        assert isinstance(scraped_data["odevlerim"]["summary"], str)


class TestTakimCalismalari:
    def test_is_dict(self, scraped_data):
        assert isinstance(scraped_data["takim_calismalari"], dict)

    def test_has_activities(self, scraped_data):
        assert "activities" in scraped_data["takim_calismalari"]

    def test_activities_is_dict(self, scraped_data):
        assert isinstance(scraped_data["takim_calismalari"]["activities"], dict)

    def test_activities_has_rows(self, scraped_data):
        act = scraped_data["takim_calismalari"]["activities"]
        assert "rows" in act, "takim_calismalari.activities missing rows"
        assert isinstance(act["rows"], list)


class TestTakvim:
    def test_is_list(self, scraped_data):
        assert isinstance(scraped_data["takvim"], list)

    def test_entries_are_dicts(self, scraped_data):
        for i, entry in enumerate(scraped_data["takvim"]):
            assert isinstance(entry, dict), f"takvim[{i}] is not a dict"

    def test_entries_have_title(self, scraped_data):
        for i, entry in enumerate(scraped_data["takvim"]):
            assert "title" in entry, f"takvim[{i}] missing title"

    def test_entries_have_start(self, scraped_data):
        for i, entry in enumerate(scraped_data["takvim"]):
            assert "start" in entry, f"takvim[{i}] missing start"


class TestDersIcerikleri:
    def test_is_dict(self, scraped_data):
        assert isinstance(scraped_data["ders_icerikleri"], dict)

    def test_non_empty(self, scraped_data):
        assert len(scraped_data["ders_icerikleri"]) > 0


class TestOgep:
    def test_is_dict(self, scraped_data):
        assert isinstance(scraped_data["ogep"], dict)

    def test_has_sessions(self, scraped_data):
        assert "sessions" in scraped_data["ogep"]

    def test_sessions_is_dict(self, scraped_data):
        assert isinstance(scraped_data["ogep"]["sessions"], dict)

    def test_sessions_has_rows(self, scraped_data):
        sessions = scraped_data["ogep"]["sessions"]
        assert "rows" in sessions, "ogep.sessions missing rows"
        assert isinstance(sessions["rows"], list)


class TestGelisimRaporu:
    def test_is_dict(self, scraped_data):
        assert isinstance(scraped_data["gelisim_raporu"], dict)

    def test_non_empty(self, scraped_data):
        assert len(scraped_data["gelisim_raporu"]) > 0


class TestDuyurular:
    def test_is_dict(self, scraped_data):
        assert isinstance(scraped_data["duyurular"], dict)

    def test_has_announcements(self, scraped_data):
        assert "announcements" in scraped_data["duyurular"]

    def test_announcements_is_list(self, scraped_data):
        assert isinstance(scraped_data["duyurular"]["announcements"], list)
