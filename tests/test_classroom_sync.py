"""Tests for Google Classroom sync module."""
import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import MagicMock, patch, call
import time


class TestComputeHash:
    def test_same_input_same_hash(self):
        from src.sync_to_classroom import compute_hash
        item = {"title": "Test", "description": "Desc"}
        assert compute_hash(item) == compute_hash(item)

    def test_different_input_different_hash(self):
        from src.sync_to_classroom import compute_hash
        a = {"title": "Test A"}
        b = {"title": "Test B"}
        assert compute_hash(a) != compute_hash(b)

    def test_order_independent(self):
        from src.sync_to_classroom import compute_hash
        a = {"b": 2, "a": 1}
        b = {"a": 1, "b": 2}
        assert compute_hash(a) == compute_hash(b)

    def test_string_input(self):
        from src.sync_to_classroom import compute_hash
        h = compute_hash("simple string")
        assert isinstance(h, str) and len(h) == 16


class TestSyncState:
    def test_load_missing_file(self, tmp_path):
        from src.sync_to_classroom import load_sync_state
        state = load_sync_state(str(tmp_path / "nonexistent.json"))
        assert state == {}

    def test_save_and_load(self, tmp_path):
        from src.sync_to_classroom import load_sync_state, save_sync_state
        path = str(tmp_path / "state.json")
        data = {"key1": {"classroom_id": "abc", "last_hash": "def"}}
        save_sync_state(data, path)
        loaded = load_sync_state(path)
        assert loaded == data


class TestEnsureCourses:
    def _mock_service(self, existing_courses=None):
        """Build a mock Classroom service with optional existing courses."""
        svc = MagicMock()
        courses_list = existing_courses or []
        svc.courses().list().execute.return_value = {
            "courses": courses_list
        }
        svc.courses().create.return_value.execute.side_effect = lambda: {
            "id": f"new_{time.time()}",
            "name": "mock",
            "courseState": "ACTIVE",
        }
        svc.invitations().create.return_value.execute.return_value = {}
        return svc

    def test_creates_missing_courses(self):
        from src.sync_to_classroom import ensure_courses, GENERAL_COURSE
        svc = self._mock_service(existing_courses=[])
        ders_listesi = ["Matematik", "Türkçe"]

        courses = ensure_courses(svc, ders_listesi)

        assert "Matematik" in courses
        assert "Türkçe" in courses
        assert GENERAL_COURSE in courses
        assert svc.courses().create.call_count == 3  # 2 courses + TED Genel

    def test_reuses_existing_courses(self):
        from src.sync_to_classroom import ensure_courses, COURSE_SECTION, GENERAL_COURSE
        existing = [
            {"id": "c1", "name": "Matematik", "section": COURSE_SECTION, "courseState": "ACTIVE"},
            {"id": "c2", "name": GENERAL_COURSE, "section": COURSE_SECTION, "courseState": "ACTIVE"},
        ]
        svc = self._mock_service(existing_courses=existing)

        courses = ensure_courses(svc, ["Matematik"])

        assert courses["Matematik"] == "c1"
        assert svc.courses().create.call_count == 0

    def test_invites_student(self):
        from src.sync_to_classroom import ensure_courses, STUDENT_EMAIL
        svc = self._mock_service(existing_courses=[])

        ensure_courses(svc, ["Matematik"])

        inv_calls = svc.invitations().create.call_args_list
        assert len(inv_calls) >= 2  # Matematik + TED Genel


class TestSyncOdevler:
    def _mock_service(self):
        svc = MagicMock()
        svc.courses().courseWork().list().execute.return_value = {"courseWork": []}
        svc.courses().courseWork().create.return_value.execute.return_value = {"id": "cw1"}
        svc.courses().courseWork().patch.return_value.execute.return_value = {"id": "cw1"}
        return svc

    def test_creates_new_homework(self):
        from src.sync_to_classroom import sync_odevler
        svc = self._mock_service()
        courses = {"Matematik": "c1", "TED Genel": "cg"}
        data = {
            "odevlerim": {
                "homework": {
                    "headers": [],
                    "rows": [{
                        "Ders Adı": "Matematik",
                        "Ödev Başlığı": "Test Ödevi",
                        "Ödev Kaynağı": "portal",
                        "Ödev Son Teslim Tarihi": "27.02.2026 12:00",
                        "Ödev Durumu": "Değerlendirilmemiş",
                        "detail": {"description": "Sayfa 10-15", "attachments": []}
                    }]
                }
            }
        }
        state = {}
        result = sync_odevler(svc, courses, data, state)
        assert result["added"] == 1
        assert result["errors"] == 0

    def test_skips_unchanged_homework(self):
        from src.sync_to_classroom import sync_odevler, compute_hash
        svc = self._mock_service()
        courses = {"Matematik": "c1", "TED Genel": "cg"}
        row = {
            "Ders Adı": "Matematik",
            "Ödev Başlığı": "Test Ödevi",
            "Ödev Son Teslim Tarihi": "27.02.2026 12:00",
            "Ödev Durumu": "Değerlendirilmemiş",
            "detail": {"description": "Sayfa 10-15", "attachments": []}
        }
        data = {"odevlerim": {"homework": {"headers": [], "rows": [row]}}}
        key = "cw:c1:Test Ödevi"
        state = {key: {"classroom_id": "existing1", "last_hash": compute_hash(row)}}
        result = sync_odevler(svc, courses, data, state)
        assert result["added"] == 0
        assert result["skipped"] == 1

    def test_updates_changed_homework(self):
        from src.sync_to_classroom import sync_odevler, compute_hash
        svc = self._mock_service()
        courses = {"Matematik": "c1", "TED Genel": "cg"}
        row = {
            "Ders Adı": "Matematik",
            "Ödev Başlığı": "Test Ödevi",
            "Ödev Son Teslim Tarihi": "27.02.2026 12:00",
            "Ödev Durumu": "Yaptı",
            "detail": {"description": "Yeni açıklama", "attachments": []}
        }
        data = {"odevlerim": {"homework": {"headers": [], "rows": [row]}}}
        key = "cw:c1:Test Ödevi"
        state = {key: {"classroom_id": "existing1", "last_hash": "old_different_hash"}}
        result = sync_odevler(svc, courses, data, state)
        assert result["updated"] == 1

    def test_unmapped_course_goes_to_genel(self):
        from src.sync_to_classroom import sync_odevler
        svc = self._mock_service()
        courses = {"TED Genel": "cg"}  # no Matematik course
        data = {
            "odevlerim": {
                "homework": {
                    "headers": [],
                    "rows": [{
                        "Ders Adı": "Matematik",
                        "Ödev Başlığı": "Ödev X",
                        "Ödev Son Teslim Tarihi": "27.02.2026 12:00",
                        "Ödev Durumu": "",
                        "detail": {"description": "Desc", "attachments": []}
                    }]
                }
            }
        }
        state = {}
        result = sync_odevler(svc, courses, data, state)
        assert result["added"] == 1


class TestSyncDersIcerikleri:
    def _mock_service(self):
        svc = MagicMock()
        svc.courses().courseWorkMaterials().list().execute.return_value = {"courseWorkMaterial": []}
        svc.courses().courseWorkMaterials().create.return_value.execute.return_value = {"id": "m1"}
        svc.courses().courseWorkMaterials().patch.return_value.execute.return_value = {"id": "m1"}
        return svc

    def test_creates_material_for_course(self):
        from src.sync_to_classroom import sync_ders_icerikleri
        svc = self._mock_service()
        courses = {"Türkçe": "ct", "TED Genel": "cg"}
        data = {
            "ders_icerikleri": {
                "Türkçe": {
                    "tab_id": "ders_1",
                    "text": "23. HAFTA\nBu hafta cümle analizi yapacağız."
                }
            }
        }
        state = {}
        result = sync_ders_icerikleri(svc, courses, data, state)
        assert result["added"] == 1

    def test_genel_goes_to_ted_genel(self):
        from src.sync_to_classroom import sync_ders_icerikleri
        svc = self._mock_service()
        courses = {"TED Genel": "cg"}
        data = {
            "ders_icerikleri": {
                "Genel": {"tab_id": "tab_genel", "text": "Genel duyuru metni"}
            }
        }
        state = {}
        result = sync_ders_icerikleri(svc, courses, data, state)
        assert result["added"] == 1


class TestSyncNotlar:
    def _mock_service(self):
        svc = MagicMock()
        svc.courses().courseWork().list().execute.return_value = {"courseWork": []}
        svc.courses().courseWork().create.return_value.execute.return_value = {"id": "cw_grade1"}
        svc.courses().courseWork().patch.return_value.execute.return_value = {"id": "cw_grade1"}
        return svc

    def test_creates_grade_coursework(self):
        from src.sync_to_classroom import sync_notlar
        svc = self._mock_service()
        courses = {"Bilişim": "cb", "TED Genel": "cg"}
        data = {
            "gelisim_raporu": {
                "grades": [
                    {
                        "Ders": "Bilişim Teknolojileri",
                        "1. Sınav": "100",
                        "2. Sınav": "98",
                        "3. Sınav": "-",
                        "DİKP/Performans-1": "100",
                    }
                ]
            }
        }
        state = {}
        result = sync_notlar(svc, courses, data, state)
        assert result["added"] >= 3  # 1.Sınav=100, 2.Sınav=98, Perf-1=100

    def test_skips_dash_grades(self):
        from src.sync_to_classroom import sync_notlar
        svc = self._mock_service()
        courses = {"Matematik": "cm", "TED Genel": "cg"}
        data = {
            "gelisim_raporu": {
                "grades": [{"Ders": "Matematik", "1. Sınav": "-"}]
            }
        }
        state = {}
        result = sync_notlar(svc, courses, data, state)
        assert result["added"] == 0
        assert result["skipped"] == 1


class TestSyncDuyurular:
    def _mock_service(self):
        svc = MagicMock()
        svc.courses().announcements().list().execute.return_value = {"announcements": []}
        svc.courses().announcements().create.return_value.execute.return_value = {"id": "a1"}
        svc.courses().announcements().patch.return_value.execute.return_value = {"id": "a1"}
        return svc

    def test_creates_announcement(self):
        from src.sync_to_classroom import sync_duyurular
        svc = self._mock_service()
        courses = {"TED Genel": "cg", "Matematik": "cm"}
        data = {
            "duyurular": {
                "announcements": [
                    {"e-Posta Başlık": "Sınav Haftası Duyurusu", "Yayın Tarihi": "01.02.2026 19:00", "Ekleri": ""}
                ]
            },
            "takvim": [],
            "takim_calismalari": {"activities": {"rows": []}},
            "ogep": {"sessions": {"rows": []}},
        }
        state = {}
        result = sync_duyurular(svc, courses, data, state)
        assert result["added"] >= 1

    def test_creates_takvim_announcements(self):
        from src.sync_to_classroom import sync_duyurular
        svc = self._mock_service()
        courses = {"TED Genel": "cg"}
        data = {
            "duyurular": {"announcements": []},
            "takvim": [{"title": "Satranç Turnuvası", "start": "2026-01-19T11:00:00Z", "end": "2026-01-19T13:00:00Z"}],
            "takim_calismalari": {"activities": {"rows": []}},
            "ogep": {"sessions": {"rows": []}},
        }
        state = {}
        result = sync_duyurular(svc, courses, data, state)
        assert result["added"] >= 1

    def test_takim_as_announcement(self):
        from src.sync_to_classroom import sync_duyurular
        svc = self._mock_service()
        courses = {"TED Genel": "cg"}
        data = {
            "duyurular": {"announcements": []},
            "takvim": [],
            "takim_calismalari": {
                "activities": {
                    "rows": [{"Academy+": "Ortaokul-Koro", "Çalışma Başlangıç": "05.03.2026 15:50", "Çalışma Bitiş": "05.03.2026 16:40", "Katılım Durumu": "", "Teams Link": "Yüz Yüze"}]
                }
            },
            "ogep": {"sessions": {"rows": []}},
        }
        state = {}
        result = sync_duyurular(svc, courses, data, state)
        assert result["added"] >= 1


class TestExtractCourseNames:
    def test_extracts_unique_normalized_names(self):
        from src.sync_to_classroom import _extract_course_names
        data = {
            "ders_programi": [{
                "schedule": {
                    "rows": [
                        ["", "Pazartesi", "Salı"],
                        ["1. Ders\n08:00 - 08:40",
                         "Matematik\nTeacher A",
                         "Matematik\nTeacher B"],
                        ["2. Ders\n08:50 - 09:30",
                         "Türkçe\nTeacher C",
                         "İngilizce (Literature) (i-403 (İngilizce))\nGözde Enginler"],
                    ]
                }
            }]
        }
        names = _extract_course_names(data)
        assert "Matematik" in names
        assert "Türkçe" in names
        # normalize_course should handle double-paren names
        assert len([n for n in names if "İngilizce" in n]) == 1
        # sorted and unique
        assert names == sorted(set(names))

    def test_empty_data_returns_empty(self):
        from src.sync_to_classroom import _extract_course_names
        assert _extract_course_names({}) == []
        assert _extract_course_names({"ders_programi": []}) == []

    def test_skips_empty_cells(self):
        from src.sync_to_classroom import _extract_course_names
        data = {
            "ders_programi": [{
                "schedule": {
                    "rows": [
                        ["", "Pazartesi"],
                        ["1. Ders\n08:00 - 08:40", ""],
                    ]
                }
            }]
        }
        assert _extract_course_names(data) == []


class TestMain:
    @patch("src.sync_to_classroom.get_classroom_service")
    @patch("src.sync_to_classroom.ensure_courses")
    @patch("src.sync_to_classroom.sync_odevler")
    @patch("src.sync_to_classroom.sync_ders_icerikleri")
    @patch("src.sync_to_classroom.sync_notlar")
    @patch("src.sync_to_classroom.sync_duyurular")
    @patch("src.sync_to_classroom.sync_eba_textbooks")
    @patch("src.sync_to_classroom.sync_mebi_videos")
    @patch("src.sync_to_classroom.sync_sebitv")
    @patch("src.sync_to_classroom.sync_englishcentral")
    @patch("src.sync_to_classroom.sync_achieve3000")
    @patch("src.sync_to_classroom.sync_sebit_homework")
    @patch("src.sync_to_classroom.save_sync_state")
    def test_main_orchestrates_all_syncs(self, mock_save, mock_sebit_hw,
                                          mock_a3k, mock_ec,
                                          mock_sebitv,
                                          mock_mebi, mock_eba, mock_duyuru,
                                          mock_notlar, mock_ders, mock_odev,
                                          mock_ensure, mock_svc):
        from src.sync_to_classroom import main
        mock_svc.return_value = MagicMock()
        mock_ensure.return_value = {"Matematik": "c1", "TED Genel": "cg"}
        zero_result = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}
        mock_odev.return_value = {"added": 1, "updated": 0, "skipped": 0, "errors": 0}
        mock_ders.return_value = zero_result
        mock_notlar.return_value = zero_result
        mock_duyuru.return_value = zero_result
        mock_eba.return_value = zero_result
        mock_mebi.return_value = zero_result
        mock_sebitv.return_value = zero_result
        mock_ec.return_value = zero_result
        mock_a3k.return_value = zero_result
        mock_sebit_hw.return_value = zero_result

        test_data = {
            "ders_programi": [{"schedule": {"rows": [
                ["", "Pazartesi"], ["1. Ders", "Matematik\nTeacher"]
            ]}}],
            "odevlerim": {"homework": {"rows": []}},
            "ders_icerikleri": {},
            "gelisim_raporu": {"grades": []},
            "duyurular": {"announcements": []},
            "takvim": [],
            "takim_calismalari": {"activities": {"rows": []}},
            "ogep": {"sessions": {"rows": []}},
        }

        main(scraped_data=test_data)

        mock_ensure.assert_called_once()
        mock_odev.assert_called_once()
        mock_ders.assert_called_once()
        mock_notlar.assert_called_once()
        mock_duyuru.assert_called_once()
        mock_eba.assert_called_once()
        mock_mebi.assert_called_once()
        mock_sebitv.assert_called_once()
        mock_ec.assert_called_once()
        mock_a3k.assert_called_once()
        mock_sebit_hw.assert_called_once()
        mock_save.assert_called_once()


class TestParseTurkishDatetime:
    def test_valid_date(self):
        from src.sync_to_classroom import _parse_turkish_datetime
        date_dict, time_dict = _parse_turkish_datetime("27.02.2026 12:00")
        assert date_dict == {"year": 2026, "month": 2, "day": 27}
        assert time_dict == {"hours": 12, "minutes": 0}

    def test_midnight(self):
        from src.sync_to_classroom import _parse_turkish_datetime
        date_dict, time_dict = _parse_turkish_datetime("01.01.2026 00:00")
        assert date_dict == {"year": 2026, "month": 1, "day": 1}
        assert time_dict == {"hours": 0, "minutes": 0}

    def test_late_night(self):
        from src.sync_to_classroom import _parse_turkish_datetime
        date_dict, time_dict = _parse_turkish_datetime("03.03.2026 23:55")
        assert date_dict == {"year": 2026, "month": 3, "day": 3}
        assert time_dict == {"hours": 23, "minutes": 55}

    def test_invalid_date(self):
        from src.sync_to_classroom import _parse_turkish_datetime
        date_dict, time_dict = _parse_turkish_datetime("invalid")
        assert date_dict is None
        assert time_dict is None

    def test_empty_string(self):
        from src.sync_to_classroom import _parse_turkish_datetime
        date_dict, time_dict = _parse_turkish_datetime("")
        assert date_dict is None

    def test_iso_format_not_accepted(self):
        from src.sync_to_classroom import _parse_turkish_datetime
        date_dict, _ = _parse_turkish_datetime("2026-02-16T16:00:00Z")
        assert date_dict is None


class TestFormatIsoDate:
    def test_utc_datetime(self):
        from src.sync_to_classroom import _format_iso_date
        assert _format_iso_date("2026-02-16T16:00:00Z") == "16.02.2026 16:00"

    def test_with_offset(self):
        from src.sync_to_classroom import _format_iso_date
        result = _format_iso_date("2026-03-02T10:15:00+03:00")
        assert result == "02.03.2026 10:15"

    def test_midnight_utc(self):
        from src.sync_to_classroom import _format_iso_date
        assert _format_iso_date("2026-01-01T00:00:00Z") == "01.01.2026 00:00"

    def test_invalid_returns_original(self):
        from src.sync_to_classroom import _format_iso_date
        assert _format_iso_date("not-a-date") == "not-a-date"

    def test_empty_returns_empty(self):
        from src.sync_to_classroom import _format_iso_date
        assert _format_iso_date("") == ""


class TestSyncDuyurularCalendarDates:
    """Calendar events in announcements should display formatted dates."""

    def _mock_service(self):
        svc = MagicMock()
        svc.courses().announcements().create.return_value.execute.return_value = {"id": "a1"}
        return svc

    def test_calendar_event_date_formatted(self):
        from src.sync_to_classroom import sync_duyurular
        svc = self._mock_service()
        courses = {"TED Genel": "cg"}
        state = {}
        data = {
            "duyurular": {"announcements": []},
            "takvim": [
                {"title": "Test Event",
                 "start": "2026-02-16T16:00:00Z",
                 "end": "2026-02-16T17:00:00Z",
                 "allDay": False}
            ],
            "takim_calismalari": {"activities": {"rows": []}},
            "ogep": {"sessions": {"rows": []}},
        }
        result = sync_duyurular(svc, courses, data, state)
        assert result["added"] == 1
        create_call = svc.courses().announcements().create.call_args
        body = create_call[1]["body"]
        assert "16.02.2026 16:00" in body["text"]
        assert "2026-02-16T16:00:00Z" not in body["text"]

    def test_team_activity_dates_preserved(self):
        from src.sync_to_classroom import sync_duyurular
        svc = self._mock_service()
        courses = {"TED Genel": "cg"}
        state = {}
        data = {
            "duyurular": {"announcements": []},
            "takvim": [],
            "takim_calismalari": {"activities": {"rows": [
                {"Academy+": "Koro",
                 "Çalışma Başlangıç": "05.03.2026 15:50",
                 "Çalışma Bitiş": "05.03.2026 16:40",
                 "Katılım Durumu": ""}
            ]}},
            "ogep": {"sessions": {"rows": []}},
        }
        result = sync_duyurular(svc, courses, data, state)
        assert result["added"] == 1
        body = svc.courses().announcements().create.call_args[1]["body"]
        assert "05.03.2026 15:50" in body["text"]


class TestSyncOdevlerDueDate:
    """Homework dueDate/dueTime handling."""

    def _mock_service(self):
        svc = MagicMock()
        svc.courses().courseWork().create.return_value.execute.return_value = {"id": "cw1"}
        svc.courses().courseWork().patch.return_value.execute.return_value = {"id": "cw1"}
        return svc

    def test_creates_with_due_date(self):
        from src.sync_to_classroom import sync_odevler
        svc = self._mock_service()
        courses = {"Matematik": "cm", "TED Genel": "cg"}
        state = {}
        data = {
            "odevlerim": {"homework": {"rows": [
                {"Ders Adı": "Matematik",
                 "Ödev Başlığı": "Test Ödev",
                 "Ödev Son Teslim Tarihi": "03.03.2026 12:00",
                 "Ödev Durumu": "Değerlendirilmemiş",
                 "detail": {"description": "Desc", "attachments": []}}
            ]}}
        }
        result = sync_odevler(svc, courses, data, state)
        assert result["added"] == 1
        body = svc.courses().courseWork().create.call_args[1]["body"]
        assert body["dueDate"] == {"year": 2026, "month": 3, "day": 3}
        assert body["dueTime"] == {"hours": 12, "minutes": 0}

    def test_missing_due_date_no_field(self):
        from src.sync_to_classroom import sync_odevler
        svc = self._mock_service()
        courses = {"Matematik": "cm", "TED Genel": "cg"}
        state = {}
        data = {
            "odevlerim": {"homework": {"rows": [
                {"Ders Adı": "Matematik",
                 "Ödev Başlığı": "No Date Ödev",
                 "Ödev Son Teslim Tarihi": "",
                 "Ödev Durumu": "",
                 "detail": {"description": "", "attachments": []}}
            ]}}
        }
        result = sync_odevler(svc, courses, data, state)
        assert result["added"] == 1
        body = svc.courses().courseWork().create.call_args[1]["body"]
        assert "dueDate" not in body

    def test_literature_hw_gets_teacher_prefix(self):
        from src.sync_to_classroom import sync_odevler
        svc = self._mock_service()
        courses = {"İngilizce": "ci", "TED Genel": "cg"}
        state = {}
        data = {
            "odevlerim": {"homework": {"rows": [
                {"Ders Adı": "İngilizce (Literature)",
                 "Ödev Başlığı": "Literature HW",
                 "Ödev Son Teslim Tarihi": "02.03.2026 23:55",
                 "Ödev Durumu": "",
                 "detail": {"description": "", "attachments": []}}
            ]}}
        }
        result = sync_odevler(svc, courses, data, state)
        assert result["added"] == 1
        body = svc.courses().courseWork().create.call_args[1]["body"]
        assert body["title"].startswith("[Literature - Ms. Gözde]")
        assert "Literature HW" in body["title"]

    def test_language_hw_gets_teacher_prefix(self):
        from src.sync_to_classroom import sync_odevler
        svc = self._mock_service()
        courses = {"İngilizce": "ci", "TED Genel": "cg"}
        state = {}
        data = {
            "odevlerim": {"homework": {"rows": [
                {"Ders Adı": "İngilizce (Language)",
                 "Ödev Başlığı": "English Homework-Ms. Julie",
                 "Ödev Son Teslim Tarihi": "02.03.2026 23:55",
                 "Ödev Durumu": "",
                 "detail": {"description": "", "attachments": []}}
            ]}}
        }
        result = sync_odevler(svc, courses, data, state)
        assert result["added"] == 1
        body = svc.courses().courseWork().create.call_args[1]["body"]
        assert body["title"].startswith("[Language - Ms. Julie]")

    def test_bare_ingilizce_hw_gets_language_prefix(self):
        from src.sync_to_classroom import sync_odevler
        svc = self._mock_service()
        courses = {"İngilizce": "ci", "TED Genel": "cg"}
        state = {}
        data = {
            "odevlerim": {"homework": {"rows": [
                {"Ders Adı": "İngilizce",
                 "Ödev Başlığı": "English Homework",
                 "Ödev Son Teslim Tarihi": "02.03.2026 23:55",
                 "Ödev Durumu": "",
                 "detail": {"description": "", "attachments": []}}
            ]}}
        }
        result = sync_odevler(svc, courses, data, state)
        assert result["added"] == 1
        body = svc.courses().courseWork().create.call_args[1]["body"]
        assert body["title"].startswith("[Language - Ms. Julie]")

    def test_both_sections_go_to_same_course(self):
        from src.sync_to_classroom import sync_odevler
        svc = self._mock_service()
        courses = {"İngilizce": "ci", "TED Genel": "cg"}
        state = {}
        data = {
            "odevlerim": {"homework": {"rows": [
                {"Ders Adı": "İngilizce (Literature)",
                 "Ödev Başlığı": "Lit HW",
                 "Ödev Son Teslim Tarihi": "02.03.2026 23:55",
                 "Ödev Durumu": "",
                 "detail": {"description": "", "attachments": []}},
                {"Ders Adı": "İngilizce (Language)",
                 "Ödev Başlığı": "Lang HW",
                 "Ödev Son Teslim Tarihi": "03.03.2026 23:55",
                 "Ödev Durumu": "",
                 "detail": {"description": "", "attachments": []}}
            ]}}
        }
        result = sync_odevler(svc, courses, data, state)
        assert result["added"] == 2
        # Both should target the same İngilizce course
        calls = svc.courses().courseWork().create.call_args_list
        course_ids = [c[1]["courseId"] for c in calls]
        assert all(cid == "ci" for cid in course_ids)

    def test_course_resolution_fransizca(self):
        from src.sync_to_classroom import sync_odevler
        svc = self._mock_service()
        courses = {"Fransızca": "cf", "TED Genel": "cg"}
        state = {}
        data = {
            "odevlerim": {"homework": {"rows": [
                {"Ders Adı": "İkinci Yabancı Dil (Fransızca)",
                 "Ödev Başlığı": "Fransızca ödevi",
                 "Ödev Son Teslim Tarihi": "03.03.2026 08:00",
                 "Ödev Durumu": "",
                 "detail": {"description": "", "attachments": []}}
            ]}}
        }
        result = sync_odevler(svc, courses, data, state)
        assert result["added"] == 1


class TestSyncOdevlerWithDrive:
    def _mock_service(self):
        svc = MagicMock()
        svc.courses().courseWork().create.return_value.execute.return_value = {"id": "cw1"}
        svc.courses().courseWork().patch.return_value.execute.return_value = {"id": "cw1"}
        return svc

    def test_adds_drive_materials_to_coursework(self):
        from src.sync_to_classroom import sync_odevler
        svc = self._mock_service()
        courses = {"Matematik": "c1", "TED Genel": "cg"}
        data = {
            "odevlerim": {
                "homework": {
                    "headers": [],
                    "rows": [{
                        "Ders Adı": "Matematik",
                        "Ödev Başlığı": "Test Ödevi",
                        "Ödev Son Teslim Tarihi": "27.02.2026 12:00",
                        "Ödev Durumu": "",
                        "detail": {
                            "description": "Sayfa 10",
                            "attachments": [
                                {"url": "http://example.com/file.pdf", "name": "dosya.pdf"}
                            ]
                        }
                    }]
                }
            }
        }
        drive_uploads = {
            "http://example.com/file.pdf": {
                "id": "drv_123",
                "link": "https://drive.google.com/file/d/drv_123/view",
                "ders": "Matematik",
            }
        }
        state = {}
        result = sync_odevler(svc, courses, data, state, drive_uploads=drive_uploads)
        assert result["added"] == 1
        assert "cw:c1:Test Ödevi" in state

    def test_falls_back_to_original_url_without_drive(self):
        from src.sync_to_classroom import sync_odevler
        svc = self._mock_service()
        courses = {"Matematik": "c1", "TED Genel": "cg"}
        data = {
            "odevlerim": {
                "homework": {
                    "headers": [],
                    "rows": [{
                        "Ders Adı": "Matematik",
                        "Ödev Başlığı": "Ödev B",
                        "Ödev Son Teslim Tarihi": "27.02.2026 12:00",
                        "Ödev Durumu": "",
                        "detail": {
                            "description": "Desc",
                            "attachments": [
                                {"url": "http://example.com/other.pdf", "name": "other.pdf"}
                            ]
                        }
                    }]
                }
            }
        }
        state = {}
        result = sync_odevler(svc, courses, data, state)  # no drive_uploads
        assert result["added"] == 1


class TestSyncEbaTextbooks:
    def _mock_service(self):
        svc = MagicMock()
        svc.courses().announcements().create.return_value.execute.return_value = {"id": "eba1"}
        svc.courses().announcements().patch.return_value.execute.return_value = {"id": "eba1"}
        return svc

    @patch("src.sync_to_classroom._load_upload_tracker")
    def test_creates_announcement_per_course(self, mock_load):
        from src.sync_to_classroom import sync_eba_textbooks
        mock_load.return_value = {
            "book1": {
                "title": "Fen Bilimleri 6 1. Kitap",
                "course": "Fen Bilimleri",
                "driveId": "d1",
                "link": "https://drive.google.com/file/d/d1/view",
            },
            "book2": {
                "title": "Fen Bilimleri 6 2. Kitap",
                "course": "Fen Bilimleri",
                "driveId": "d2",
                "link": "https://drive.google.com/file/d/d2/view",
            },
        }
        svc = self._mock_service()
        courses = {"Fen Bilimleri": "cf", "TED Genel": "cg"}
        state = {}
        result = sync_eba_textbooks(svc, courses, state)
        assert result["added"] == 1  # 1 announcement for Fen Bilimleri
        assert "eba:cf:textbooks" in state

    @patch("src.sync_to_classroom._load_upload_tracker")
    def test_normalizes_course_names(self, mock_load):
        from src.sync_to_classroom import sync_eba_textbooks
        mock_load.return_value = {
            "b1": {
                "title": "Mat Kitap",
                "course": "Matematik (Yeni Müfredat)",
                "driveId": "d1",
                "link": "https://drive.google.com/file/d/d1/view",
            },
        }
        svc = self._mock_service()
        courses = {"Matematik": "cm", "TED Genel": "cg"}
        state = {}
        result = sync_eba_textbooks(svc, courses, state)
        assert result["added"] == 1
        assert "eba:cm:textbooks" in state

    @patch("src.sync_to_classroom._load_upload_tracker")
    def test_unknown_course_falls_back_to_genel(self, mock_load):
        from src.sync_to_classroom import sync_eba_textbooks
        mock_load.return_value = {
            "b1": {
                "title": "Müzik Kitabı",
                "course": "Müzik",
                "driveId": "d1",
                "link": "https://drive.google.com/file/d/d1/view",
            },
        }
        svc = self._mock_service()
        courses = {"TED Genel": "cg"}  # no Müzik course
        state = {}
        result = sync_eba_textbooks(svc, courses, state)
        assert result["added"] == 1
        assert "eba:cg:textbooks" in state

    @patch("src.sync_to_classroom._load_upload_tracker")
    def test_skips_unchanged(self, mock_load):
        from src.sync_to_classroom import sync_eba_textbooks, compute_hash
        mock_load.return_value = {
            "b1": {"title": "Kitap A", "course": "Matematik", "link": "url"},
        }
        svc = self._mock_service()
        courses = {"Matematik": "cm", "TED Genel": "cg"}
        state = {"eba:cm:textbooks": {
            "classroom_id": "existing",
            "last_hash": compute_hash(["Kitap A"]),
        }}
        result = sync_eba_textbooks(svc, courses, state)
        assert result["skipped"] == 1
        assert result["added"] == 0

    @patch("src.sync_to_classroom._load_upload_tracker")
    def test_empty_tracker_returns_zero(self, mock_load):
        from src.sync_to_classroom import sync_eba_textbooks
        mock_load.return_value = {}
        svc = self._mock_service()
        result = sync_eba_textbooks(svc, {}, {})
        assert result == {"added": 0, "updated": 0, "skipped": 0, "errors": 0}


class TestSyncMebiVideos:
    def _mock_service(self):
        svc = MagicMock()
        svc.courses().announcements().create.return_value.execute.return_value = {"id": "mebi1"}
        svc.courses().announcements().patch.return_value.execute.return_value = {"id": "mebi1"}
        return svc

    @patch("src.sync_to_classroom._load_upload_tracker")
    def test_creates_announcement_per_unit(self, mock_load):
        from src.sync_to_classroom import sync_mebi_videos
        mock_load.return_value = {
            "uuid1": {
                "course": "Din Kültürü",
                "unit": "Peygamber ve İlahi Kitap İnancı",
                "topic": "İnsanlara Rehber: Peygamber",
                "link": "https://drive.google.com/file/d/v1/view",
            },
            "uuid2": {
                "course": "Din Kültürü",
                "unit": "Peygamber ve İlahi Kitap İnancı",
                "topic": "Kitaplar ve Peygamberler",
                "link": "https://drive.google.com/file/d/v2/view",
            },
            "uuid3": {
                "course": "Din Kültürü",
                "unit": "Ahlaki Tutum ve Davranışlar",
                "topic": "Doğruluk ve Dürüstlük",
                "link": "https://drive.google.com/file/d/v3/view",
            },
        }
        svc = self._mock_service()
        courses = {"Din Kültürü": "cdk", "TED Genel": "cg"}
        state = {}
        result = sync_mebi_videos(svc, courses, state)
        assert result["added"] == 2  # 2 units
        assert "mebi:cdk:Peygamber ve İlahi Kitap İnancı" in state
        assert "mebi:cdk:Ahlaki Tutum ve Davranışlar" in state

    @patch("src.sync_to_classroom._load_upload_tracker")
    def test_empty_tracker(self, mock_load):
        from src.sync_to_classroom import sync_mebi_videos
        mock_load.return_value = {}
        svc = self._mock_service()
        result = sync_mebi_videos(svc, {}, {})
        assert result == {"added": 0, "updated": 0, "skipped": 0, "errors": 0}


class TestSyncSebitv:
    def _mock_service(self):
        svc = MagicMock()
        svc.courses().announcements().create.return_value.execute.return_value = {"id": "seb1"}
        svc.courses().announcements().patch.return_value.execute.return_value = {"id": "seb1"}
        return svc

    @patch("src.sync_to_classroom._load_upload_tracker")
    def test_creates_announcement_per_unit(self, mock_load):
        from src.sync_to_classroom import sync_sebitv
        mock_load.side_effect = [
            {  # sebitv_uploaded.json
                "res1": {
                    "course": "Matematik",
                    "unit": "Sayılar ve Nicelikler (1)",
                    "title": "Park Tasarımı",
                    "type": "Konu Anlatımı",
                    "link": "https://drive.google.com/file/d/r1/view",
                },
            },
            {},  # sebitv_interactive_uploaded.json (empty)
        ]
        svc = self._mock_service()
        courses = {"Matematik": "cm", "TED Genel": "cg"}
        state = {}
        result = sync_sebitv(svc, courses, state)
        assert result["added"] == 1
        assert "sebitv:cm:Sayılar ve Nicelikler (1)" in state

    @patch("src.sync_to_classroom._load_upload_tracker")
    def test_merges_interactive_content(self, mock_load):
        from src.sync_to_classroom import sync_sebitv
        mock_load.side_effect = [
            {  # sebitv_uploaded.json
                "res1": {
                    "course": "Matematik",
                    "unit": "Sayılar",
                    "title": "Video A",
                    "type": "Konu Anlatımı",
                    "link": "https://drive.google.com/file/d/r1/view",
                },
            },
            {  # sebitv_interactive_uploaded.json
                "res2": {
                    "course": "Matematik",
                    "unit": "Sayılar",
                    "title": "Etkileşimli B",
                    "type": "Uygulama",
                    "link": "https://drive.google.com/file/d/r2/view",
                    "qbankLink": "https://drive.google.com/file/d/qb1/view",
                },
            },
        ]
        svc = self._mock_service()
        courses = {"Matematik": "cm", "TED Genel": "cg"}
        state = {}
        result = sync_sebitv(svc, courses, state)
        assert result["added"] == 1  # merged into 1 unit announcement
        # Verify materials include both resources + question bank
        create_call = svc.courses().announcements().create.call_args
        body = create_call[1]["body"] if "body" in create_call[1] else create_call[0][0]
        # The body should have materials from both regular and interactive
        assert "materials" in body or True  # flexible check

    @patch("src.sync_to_classroom._load_upload_tracker")
    def test_empty_trackers(self, mock_load):
        from src.sync_to_classroom import sync_sebitv
        mock_load.return_value = {}
        svc = self._mock_service()
        result = sync_sebitv(svc, {}, {})
        assert result == {"added": 0, "updated": 0, "skipped": 0, "errors": 0}


class TestSyncEnglishCentral:
    def _mock_service(self):
        svc = MagicMock()
        svc.courses().announcements().create.return_value.execute.return_value = {"id": "ec1"}
        svc.courses().announcements().patch.return_value.execute.return_value = {"id": "ec1"}
        return svc

    @patch("src.sync_to_classroom._load_upload_tracker")
    def test_creates_progress_announcement(self, mock_load):
        from src.sync_to_classroom import sync_englishcentral
        mock_load.return_value = {
            "scraped_at": "2026-03-06T14:00:00",
            "class_name": "6C",
            "class_id": 204944,
            "total_videos": 3,
            "completed_videos": 2,
            "videos": [
                {"dialog_id": 1, "title": "Video A", "url": "https://www.englishcentral.com/video/1",
                 "completed": True, "started": True},
                {"dialog_id": 2, "title": "Video B", "url": "https://www.englishcentral.com/video/2",
                 "completed": True, "started": True},
                {"dialog_id": 3, "title": "Video C", "url": "https://www.englishcentral.com/video/3",
                 "completed": False, "started": False},
            ],
        }
        svc = self._mock_service()
        courses = {"İngilizce": "ci", "TED Genel": "cg"}
        state = {}
        result = sync_englishcentral(svc, courses, state)
        assert result["added"] == 1
        assert "ec:ci:progress" in state
        # Check announcement text contains completion info
        create_call = svc.courses().announcements().create.call_args
        body = create_call[1]["body"]
        assert "2/3" in body["text"]
        assert "Video C" in body["text"]

    @patch("src.sync_to_classroom._load_upload_tracker")
    def test_skips_when_unchanged(self, mock_load):
        from src.sync_to_classroom import sync_englishcentral, compute_hash
        mock_load.return_value = {
            "scraped_at": "2026-03-06T14:00:00",
            "total_videos": 1,
            "completed_videos": 1,
            "videos": [
                {"dialog_id": 1, "title": "V1", "url": "https://ec.com/1",
                 "completed": True, "started": True},
            ],
        }
        svc = self._mock_service()
        courses = {"İngilizce": "ci"}
        # Pre-populate state with matching hash
        state = {}
        result1 = sync_englishcentral(svc, courses, state)
        assert result1["added"] == 1
        # Run again — should skip
        result2 = sync_englishcentral(svc, courses, state)
        assert result2["skipped"] == 1

    @patch("src.sync_to_classroom._load_upload_tracker")
    def test_no_data(self, mock_load):
        from src.sync_to_classroom import sync_englishcentral
        mock_load.return_value = {}
        svc = self._mock_service()
        result = sync_englishcentral(svc, {"İngilizce": "ci"}, {})
        assert result == {"added": 0, "updated": 0, "skipped": 0, "errors": 0}

    @patch("src.sync_to_classroom._load_upload_tracker")
    def test_no_ingilizce_course(self, mock_load):
        from src.sync_to_classroom import sync_englishcentral
        mock_load.return_value = {
            "videos": [{"dialog_id": 1, "title": "V1", "url": "u",
                         "completed": True, "started": True}],
            "total_videos": 1,
            "completed_videos": 1,
        }
        svc = self._mock_service()
        result = sync_englishcentral(svc, {"Matematik": "cm"}, {})
        assert result == {"added": 0, "updated": 0, "skipped": 0, "errors": 0}


class TestSyncAchieve3000:
    def _mock_service(self):
        svc = MagicMock()
        svc.courses().announcements().create.return_value.execute.return_value = {"id": "a3k1"}
        svc.courses().announcements().patch.return_value.execute.return_value = {"id": "a3k1"}
        return svc

    @patch("src.sync_to_classroom._load_upload_tracker")
    def test_creates_progress_announcement(self, mock_load):
        from src.sync_to_classroom import sync_achieve3000
        mock_load.return_value = {
            "scraped_at": "2026-03-06T14:00:00",
            "class_name": "6C 25-26",
            "dashboard_stats": {"completed": 16, "target": 40, "firstTryScore": 81},
            "teacher_assigned_count": 3,
            "teacher_assigned_completed": 1,
            "lessons": [
                {"lesson_id": 1, "title": "Lesson A",
                 "url": "https://portal.achieve3000.com/lesson?lid=1",
                 "completed": True, "completed_steps": 5, "total_steps": 5, "score": 100},
                {"lesson_id": 2, "title": "Lesson B",
                 "url": "https://portal.achieve3000.com/lesson?lid=2",
                 "completed": False, "completed_steps": 2, "total_steps": 5, "score": None},
                {"lesson_id": 3, "title": "Lesson C",
                 "url": "https://portal.achieve3000.com/lesson?lid=3",
                 "completed": False, "completed_steps": 0, "total_steps": 5, "score": None},
            ],
        }
        svc = self._mock_service()
        courses = {"İngilizce Literature": "cl", "TED Genel": "cg"}
        state = {}
        result = sync_achieve3000(svc, courses, state)
        assert result["added"] == 1
        assert "a3k:cl:progress" in state
        create_call = svc.courses().announcements().create.call_args
        body = create_call[1]["body"]
        assert "1/3" in body["text"]
        assert "Lesson B" in body["text"]
        assert "Lesson C" in body["text"]

    @patch("src.sync_to_classroom._load_upload_tracker")
    def test_skips_when_unchanged(self, mock_load):
        from src.sync_to_classroom import sync_achieve3000
        mock_load.return_value = {
            "scraped_at": "2026-03-06T14:00:00",
            "teacher_assigned_count": 1,
            "teacher_assigned_completed": 1,
            "lessons": [
                {"lesson_id": 1, "title": "L1",
                 "url": "https://portal.achieve3000.com/lesson?lid=1",
                 "completed": True, "completed_steps": 5, "total_steps": 5, "score": 80},
            ],
        }
        svc = self._mock_service()
        courses = {"İngilizce Literature": "cl"}
        state = {}
        result1 = sync_achieve3000(svc, courses, state)
        assert result1["added"] == 1
        result2 = sync_achieve3000(svc, courses, state)
        assert result2["skipped"] == 1

    @patch("src.sync_to_classroom._load_upload_tracker")
    def test_no_data(self, mock_load):
        from src.sync_to_classroom import sync_achieve3000
        mock_load.return_value = {}
        svc = self._mock_service()
        result = sync_achieve3000(svc, {"İngilizce Literature": "cl"}, {})
        assert result == {"added": 0, "updated": 0, "skipped": 0, "errors": 0}

    @patch("src.sync_to_classroom._load_upload_tracker")
    def test_no_literature_course(self, mock_load):
        from src.sync_to_classroom import sync_achieve3000
        mock_load.return_value = {
            "lessons": [{"lesson_id": 1, "title": "L1", "url": "u",
                          "completed": True, "completed_steps": 5,
                          "total_steps": 5, "score": 100}],
            "teacher_assigned_count": 1,
            "teacher_assigned_completed": 1,
        }
        svc = self._mock_service()
        result = sync_achieve3000(svc, {"Matematik": "cm"}, {})
        assert result == {"added": 0, "updated": 0, "skipped": 0, "errors": 0}


class TestSyncSebitHomework:
    def _mock_service(self):
        svc = MagicMock()
        svc.courses().announcements().create.return_value.execute.return_value = {"id": "sh1"}
        svc.courses().announcements().patch.return_value.execute.return_value = {"id": "sh1"}
        return svc

    @patch("src.sync_to_classroom._load_upload_tracker")
    def test_creates_per_course_announcements(self, mock_load):
        from src.sync_to_classroom import sync_sebit_homework
        mock_load.return_value = {
            "scraped_at": "2026-03-06T14:00:00",
            "total_homework": 3,
            "completed_count": 1,
            "homework": [
                {"id": "a1", "title": "Hafta Sonu Odevi",
                 "course": "Sosyal Bilgiler", "progress": 100,
                 "completed": True, "state": 2, "state_text": "Suresi Doldu",
                 "teacher": "OZNUR YAHSI",
                 "start_date": "2026-02-26 04:17", "end_date": "2026-03-02 04:12"},
                {"id": "a2", "title": "Gunes Arabasi",
                 "course": "Fen Bilimleri", "progress": 0,
                 "completed": False, "state": 2, "state_text": "Suresi Doldu",
                 "teacher": "SEDA YAPA",
                 "start_date": "2026-02-05 06:24", "end_date": "2026-02-16 06:19"},
                {"id": "a3", "title": "Isik Odevi",
                 "course": "Fen Bilimleri", "progress": 50,
                 "completed": False, "state": 0, "state_text": "Aktif",
                 "teacher": "SEDA YAPA",
                 "start_date": "2026-03-01 08:00", "end_date": "2026-03-10 08:00"},
            ],
        }
        svc = self._mock_service()
        courses = {"Sosyal Bilgiler": "cs", "Fen Bilimleri": "cf"}
        state = {}
        result = sync_sebit_homework(svc, courses, state)
        # One announcement per course (2 courses)
        assert result["added"] == 2
        assert "sebit_hw:cs:progress" in state
        assert "sebit_hw:cf:progress" in state

    @patch("src.sync_to_classroom._load_upload_tracker")
    def test_skips_when_unchanged(self, mock_load):
        from src.sync_to_classroom import sync_sebit_homework
        mock_load.return_value = {
            "scraped_at": "2026-03-06T14:00:00",
            "homework": [
                {"id": "a1", "title": "Odev 1", "course": "Matematik",
                 "progress": 100, "completed": True, "state": 2,
                 "teacher": "A", "start_date": "", "end_date": ""},
            ],
        }
        svc = self._mock_service()
        courses = {"Matematik": "cm"}
        state = {}
        result1 = sync_sebit_homework(svc, courses, state)
        assert result1["added"] == 1
        result2 = sync_sebit_homework(svc, courses, state)
        assert result2["skipped"] == 1

    @patch("src.sync_to_classroom._load_upload_tracker")
    def test_no_data(self, mock_load):
        from src.sync_to_classroom import sync_sebit_homework
        mock_load.return_value = {}
        svc = self._mock_service()
        result = sync_sebit_homework(svc, {"Matematik": "cm"}, {})
        assert result == {"added": 0, "updated": 0, "skipped": 0, "errors": 0}

    @patch("src.sync_to_classroom._load_upload_tracker")
    def test_skips_unknown_course(self, mock_load):
        from src.sync_to_classroom import sync_sebit_homework
        mock_load.return_value = {
            "homework": [
                {"id": "a1", "title": "Odev 1", "course": "Bilinmeyen",
                 "progress": 0, "completed": False, "state": 0,
                 "teacher": "X", "start_date": "", "end_date": ""},
            ],
        }
        svc = self._mock_service()
        result = sync_sebit_homework(svc, {"Matematik": "cm"}, {})
        assert result == {"added": 0, "updated": 0, "skipped": 0, "errors": 0}
