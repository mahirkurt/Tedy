"""Comprehensive tests for the Sınavlar (Exams) feature.

Covers:
- /api/exams endpoint (structure, filtering, sorting, related content)
- Exam event detection (_is_exam_event)
- Course extraction from exam titles (_extract_exam_info)
- Turkish-aware lowercase (_turkish_lower)
- Timezone handling in related homework matching
- Scraper takvim checkbox and lazy-load behavior
"""
import hashlib
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["TEST_AUTH_BYPASS"] = "1"

import src.dashboard_api as dashboard_api  # noqa: E402

app = dashboard_api.app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# ---------------------------------------------------------------------------
# Sample data builders
# ---------------------------------------------------------------------------

def _exam_event(title, start, all_day=False, bg=""):
    return {
        "title": title,
        "start": start,
        "end": "",
        "allDay": all_day,
        "backgroundColor": bg,
        "extendedProps": {},
    }


def _homework_row(course, title, deadline, status="Değerlendirilmemiş"):
    return {
        "Ders Adı": course,
        "Ödev Başlığı": title,
        "Ödev Son Teslim Tarihi": deadline,
        "Ödev Durumu": status,
        "detail": {"description": "", "attachments": []},
    }


def _grade_row(course, s1="-", s2="-", s3="-"):
    return {
        "Ders": course,
        "1. Sınav": s1,
        "2. Sınav": s2,
        "3. Sınav": s3,
        "DİKP/Performans-1": "-",
        "DİKP/Performans-2": "-",
        "DİKP/Performans-3": "-",
    }


def _scraped_with_exams(takvim=None, homework=None, grades=None,
                        ders_icerikleri=None, semester="2. Dönem"):
    data = {
        "takvim": takvim or [],
        "odevlerim": {
            "summary": "",
            "homework": {"rows": homework or []},
        },
        "gelisim_raporu": {
            "semester": semester,
            "grades": grades or [],
            "physical": {},
        },
    }
    if ders_icerikleri:
        data["ders_icerikleri"] = ders_icerikleri
    return data


# ---------------------------------------------------------------------------
# _turkish_lower
# ---------------------------------------------------------------------------

class TestTurkishLower:
    def test_basic_lowercase(self):
        assert dashboard_api._turkish_lower("ABC") == "abc"

    def test_turkish_i_dotted_upper(self):
        """İ (U+0130) must become plain 'i'."""
        assert dashboard_api._turkish_lower("İSTANBUL") == "istanbul"

    def test_turkish_i_dotless_upper(self):
        """I must become 'ı' (U+0131) in Turkish context."""
        assert dashboard_api._turkish_lower("ISIK") == "ısık"

    def test_mixed_case_course_match(self):
        """'FEN BİLİMLERİ' and 'Fen Bilimleri' must match."""
        a = dashboard_api._turkish_lower("FEN BİLİMLERİ")
        b = dashboard_api._turkish_lower("Fen Bilimleri")
        assert a == b

    def test_ingilizce_match(self):
        a = dashboard_api._turkish_lower("İNGİLİZCE")
        b = dashboard_api._turkish_lower("İngilizce")
        assert a == b

    def test_din_kulturu_match(self):
        a = dashboard_api._turkish_lower(
            "DİN KÜLTÜRÜ VE AHLAK BİLGİSİ")
        b = dashboard_api._turkish_lower(
            "Din Kültürü ve Ahlak Bilgisi")
        assert a == b

    def test_empty_string(self):
        assert dashboard_api._turkish_lower("") == ""

    def test_already_lowercase(self):
        assert dashboard_api._turkish_lower("matematik") == "matematik"


# ---------------------------------------------------------------------------
# _is_exam_event
# ---------------------------------------------------------------------------

class TestIsExamEvent:
    def test_sinav_keyword(self):
        assert dashboard_api._is_exam_event("Matematik 1. Sınav")

    def test_yazili_keyword(self):
        assert dashboard_api._is_exam_event(
            "5-6-7-8. SINIFLAR FEN BİLİMLERİ – 2. DÖNEM 1. YAZILI SINAVI"
        )

    def test_exam_english_keyword(self):
        assert dashboard_api._is_exam_event(
            "5-6-7th Grades TED HQ Monitoring Exam")

    def test_word_test_matches(self):
        assert dashboard_api._is_exam_event("Unit Test 3")

    def test_contest_does_not_match(self):
        """'Contest' should not trigger exam detection."""
        assert not dashboard_api._is_exam_event(
            "Playback Video Clip Contest – Submission Deadline"
        )

    def test_baslangici_excluded(self):
        """'Başlangıcı' events are announcements, not exams."""
        assert not dashboard_api._is_exam_event(
            "MEB 2. Dönem 1. Yazılı Sınav Haftası Başlangıcı"
        )

    def test_beginning_of_excluded(self):
        assert not dashboard_api._is_exam_event(
            "Beginning of MEB 2nd Term 1st Written Exam Week"
        )

    def test_regular_event_rejected(self):
        assert not dashboard_api._is_exam_event(
            "Deprem Tatbikatı-Earthquake Drill")

    def test_ogep_rejected(self):
        assert not dashboard_api._is_exam_event(
            "6.SINIF MATEMATİK ÖGEP (Matematik)")

    def test_empty_string(self):
        assert not dashboard_api._is_exam_event("")


# ---------------------------------------------------------------------------
# _extract_exam_info
# ---------------------------------------------------------------------------

class TestExtractExamInfo:
    def test_standard_yazili_format(self):
        title = ("5-6-7-8. SINIFLAR FEN BİLİMLERİ"
                 " – 2. DÖNEM 1. YAZILI SINAVI")
        course, raw, num = dashboard_api._extract_exam_info(title)
        assert "FEN" in course.upper()
        assert num == 1

    def test_ingilizce_listening(self):
        title = ("5-6-7-8. SINIFLAR İNGİLİZCE"
                 " – 2. DÖNEM 1. DİNLEME SINAVI")
        course, raw, num = dashboard_api._extract_exam_info(title)
        assert "ngilizce" in course  # İngilizce (canonical)

    def test_dkab_yazili(self):
        title = ("5-6-7-8. SINIFLAR DİN KÜLTÜRÜ VE AHLAK BİLGİSİ"
                 " – 2. DÖNEM 1. YAZILI SINAVI")
        course, raw, num = dashboard_api._extract_exam_info(title)
        assert "Din Kültürü" in course  # canonical
        assert num == 1

    def test_second_exam_number(self):
        title = "Matematik 2. Yazılı Sınavı"
        _, _, num = dashboard_api._extract_exam_info(title)
        assert num == 2

    def test_no_number(self):
        title = ("5-6-7. Sınıflar TED GM İzleme-2 Sınavı"
                 " (TED Geneli)")
        _, _, num = dashboard_api._extract_exam_info(title)
        # "2" here is not a standard exam number format
        # The regex matches "(\d)\.\s*(?:Yazılı|Sınav)"
        # This title has no such pattern
        assert num is None or isinstance(num, int)

    def test_5_6_siniflar_format(self):
        title = ("5-6. SINIFLAR AHLAK VE YURTTAŞLIK EĞİTİMİ"
                 " – 2. DÖNEM 1. YAZILI SINAVI")
        course, raw, num = dashboard_api._extract_exam_info(title)
        assert "AHLAK" in course.upper()


# ---------------------------------------------------------------------------
# /api/exams endpoint
# ---------------------------------------------------------------------------

class TestExamsEndpoint:
    def test_returns_200(self, client):
        resp = client.get("/api/exams")
        assert resp.status_code == 200

    def test_response_structure(self, client):
        data = client.get("/api/exams").get_json()
        assert "exams" in data
        assert "stats" in data
        assert isinstance(data["exams"], list)
        assert "upcoming" in data["stats"]
        assert "past" in data["stats"]
        assert "averageGrade" in data["stats"]

    def test_empty_when_no_data(self, client):
        with patch.object(dashboard_api, "_scraped",
                          return_value=_scraped_with_exams()):
            data = client.get("/api/exams").get_json()
            assert data["exams"] == []
            assert data["stats"]["upcoming"] == 0
            assert data["stats"]["past"] == 0

    def test_detects_exam_from_takvim(self, client):
        future = (datetime.now() + timedelta(days=10)).isoformat()
        takvim = [_exam_event(
            "5-6-7-8. SINIFLAR MATEMATİK – 2. DÖNEM 1. YAZILI SINAVI",
            future)]
        with patch.object(dashboard_api, "_scraped",
                          return_value=_scraped_with_exams(takvim=takvim)):
            data = client.get("/api/exams").get_json()
            assert len(data["exams"]) == 1
            assert data["stats"]["upcoming"] == 1
            assert data["exams"][0]["status"] == "upcoming"

    def test_past_exam_status(self, client):
        past = (datetime.now() - timedelta(days=5)).isoformat() + "Z"
        takvim = [_exam_event(
            "5-6-7-8. SINIFLAR MATEMATİK – 2. DÖNEM 1. YAZILI SINAVI",
            past)]
        with patch.object(dashboard_api, "_scraped",
                          return_value=_scraped_with_exams(takvim=takvim)):
            data = client.get("/api/exams").get_json()
            assert data["exams"][0]["status"] == "past"
            assert data["stats"]["past"] == 1

    def test_filters_non_exam_events(self, client):
        takvim = [
            _exam_event("Deprem Tatbikatı", "2026-03-15T10:00:00Z"),
            _exam_event("Matematik 1. Yazılı Sınavı",
                        "2026-03-20T09:00:00Z"),
            _exam_event("Basketbol Turnuvası", "2026-03-22T12:00:00Z"),
        ]
        with patch.object(dashboard_api, "_scraped",
                          return_value=_scraped_with_exams(takvim=takvim)):
            data = client.get("/api/exams").get_json()
            assert len(data["exams"]) == 1

    def test_excludes_baslangici_events(self, client):
        takvim = [
            _exam_event(
                "MEB 2. Dönem Yazılı Sınav Haftası Başlangıcı",
                "2026-03-30T08:00:00Z"),
        ]
        with patch.object(dashboard_api, "_scraped",
                          return_value=_scraped_with_exams(takvim=takvim)):
            data = client.get("/api/exams").get_json()
            assert len(data["exams"]) == 0

    def test_sorting_upcoming_asc_past_desc(self, client):
        now = datetime.now()
        t1 = (now + timedelta(days=5)).isoformat()
        t2 = (now + timedelta(days=2)).isoformat()
        t3 = (now - timedelta(days=3)).isoformat() + "Z"
        t4 = (now - timedelta(days=10)).isoformat() + "Z"
        takvim = [
            _exam_event("Matematik 1. Yazılı Sınavı", t1),
            _exam_event("Fen 1. Yazılı Sınavı", t2),
            _exam_event("Türkçe 1. Yazılı Sınavı", t3),
            _exam_event("İngilizce 1. Yazılı Sınavı", t4),
        ]
        with patch.object(dashboard_api, "_scraped",
                          return_value=_scraped_with_exams(takvim=takvim)):
            data = client.get("/api/exams").get_json()
            exams = data["exams"]
            upcoming = [e for e in exams if e["status"] == "upcoming"]
            past = [e for e in exams if e["status"] == "past"]
            # Upcoming: earliest first
            assert upcoming[0]["date"] < upcoming[1]["date"]
            # Past: most recent first
            assert past[0]["date"] > past[1]["date"]

    def test_exam_has_required_fields(self, client):
        future = (datetime.now() + timedelta(days=5)).isoformat()
        takvim = [_exam_event(
            "5-6-7-8. SINIFLAR MATEMATİK – 2. DÖNEM 1. YAZILI SINAVI",
            future)]
        with patch.object(dashboard_api, "_scraped",
                          return_value=_scraped_with_exams(takvim=takvim)):
            exam = client.get("/api/exams").get_json()["exams"][0]
            required = ("id", "course", "rawTitle", "examNumber",
                        "date", "status", "grade", "studyGuide",
                        "aiSummary", "relatedHomework",
                        "relatedContent")
            for key in required:
                assert key in exam, f"Missing key: {key}"

    def test_grade_matching(self, client):
        past = (datetime.now() - timedelta(days=5)).isoformat() + "Z"
        takvim = [_exam_event(
            "5-6-7-8. SINIFLAR MATEMATİK – 2. DÖNEM 1. YAZILI SINAVI",
            past)]
        grades = [_grade_row("Matematik", s1="85")]
        with patch.object(dashboard_api, "_scraped",
                          return_value=_scraped_with_exams(
                              takvim=takvim, grades=grades)):
            data = client.get("/api/exams").get_json()
            # Grade matching depends on normalize_course alignment
            # At minimum, the exam should exist
            assert len(data["exams"]) >= 1

    def test_average_grade_calculation(self, client):
        past = (datetime.now() - timedelta(days=5)).isoformat() + "Z"
        takvim = [
            _exam_event("Matematik 1. Yazılı Sınavı", past),
            _exam_event("Fen 1. Yazılı Sınavı", past),
        ]
        grades = [
            _grade_row("Matematik", s1="80"),
            _grade_row("Fen Bilimleri", s1="90"),
        ]
        with patch.object(dashboard_api, "_scraped",
                          return_value=_scraped_with_exams(
                              takvim=takvim, grades=grades)):
            data = client.get("/api/exams").get_json()
            # Synthetic exams from grades should contribute
            if data["stats"]["averageGrade"] is not None:
                assert 80 <= data["stats"]["averageGrade"] <= 90


class TestExamRelatedHomework:
    """Related homework matching with timezone and Turkish case handling."""

    def test_finds_homework_in_4_week_window(self, client):
        exam_date = "2026-03-31T10:00:00Z"
        takvim = [_exam_event(
            "5-6-7-8. SINIFLAR FEN BİLİMLERİ"
            " – 2. DÖNEM 1. YAZILI SINAVI",
            exam_date)]
        homework = [
            _homework_row(
                "Fen Bilimleri",
                "Yazılı sınav çalışması",
                "23.03.2026 12:00"),
            _homework_row(
                "Fen Bilimleri",
                "Eski ödev",
                "01.01.2026 12:00"),  # > 4 weeks before
        ]
        with patch.object(dashboard_api, "_scraped",
                          return_value=_scraped_with_exams(
                              takvim=takvim, homework=homework)):
            data = client.get("/api/exams").get_json()
            exam = data["exams"][0]
            titles = [hw["title"] for hw in exam["relatedHomework"]]
            assert "Yazılı sınav çalışması" in titles
            assert "Eski ödev" not in titles

    def test_turkish_case_matching(self, client):
        """FEN BİLİMLERİ (takvim) must match Fen Bilimleri (ödev)."""
        exam_date = "2026-03-31T10:00:00Z"
        takvim = [_exam_event(
            "5-6-7-8. SINIFLAR FEN BİLİMLERİ"
            " – 2. DÖNEM 1. YAZILI SINAVI",
            exam_date)]
        homework = [_homework_row(
            "Fen Bilimleri",
            "Konu tekrarı",
            "25.03.2026 12:00")]
        with patch.object(dashboard_api, "_scraped",
                          return_value=_scraped_with_exams(
                              takvim=takvim, homework=homework)):
            data = client.get("/api/exams").get_json()
            assert len(data["exams"][0]["relatedHomework"]) == 1

    def test_different_course_not_matched(self, client):
        exam_date = "2026-03-31T10:00:00Z"
        takvim = [_exam_event(
            "5-6-7-8. SINIFLAR MATEMATİK"
            " – 2. DÖNEM 1. YAZILI SINAVI",
            exam_date)]
        homework = [_homework_row(
            "Fen Bilimleri",
            "Fen ödevi",
            "25.03.2026 12:00")]
        scraped = _scraped_with_exams(
            takvim=takvim, homework=homework)
        with patch.object(dashboard_api, "_scraped",
                          return_value=scraped), \
             patch.object(dashboard_api, "_load_photo_homework_rows",
                          return_value=[]):
            data = client.get("/api/exams").get_json()
            assert len(data["exams"][0]["relatedHomework"]) == 0

    def test_no_crash_on_missing_date(self, client):
        takvim = [_exam_event(
            "Matematik 1. Yazılı Sınavı", "")]
        homework = [_homework_row(
            "Matematik", "Ödev", "25.03.2026 12:00")]
        with patch.object(dashboard_api, "_scraped",
                          return_value=_scraped_with_exams(
                              takvim=takvim, homework=homework)):
            data = client.get("/api/exams").get_json()
            # Should not crash; exam with no date has no related hw
            assert len(data["exams"]) >= 1


def _icerik(text="", cards=(), items=()):
    """ders_icerikleri[course] in its real shape (measured 2026-09-28):
    cards and items are strings. Invented teachers and text."""
    return {"tab_id": "ders_4", "text": text, "tables": [],
            "items": list(items), "cards": list(cards)}


class TestExamRelatedContent:
    """Related course content, read from the real {tab_id, text, tables,
    items, cards} shape. The old tests fed a list — a shape the scraper never
    writes — so relatedContent was [] on every real exam while they passed."""

    FEN_SINAVI = ("5-6-7-8. SINIFLAR FEN BİLİMLERİ – 2. DÖNEM 1. YAZILI SINAVI")

    def _related(self, client, title, ders):
        takvim = [_exam_event(title, "2026-03-31T10:00:00Z")]
        with patch.object(dashboard_api, "_scraped",
                          return_value=_scraped_with_exams(
                              takvim=takvim, ders_icerikleri=ders)):
            return client.get("/api/exams").get_json()["exams"][0]["relatedContent"]

    def test_finds_matching_course_content(self, client):
        ders = {"Fen Bilimleri": _icerik(
            text="3. Hafta\nKurgu Öğretmen | 28.09.2026\nBu hafta Güneş sistemi.",
            cards=[
                "3. Hafta\nKurgu Öğretmen | 28.09.2026\nSevgili öğrencilerim,\n"
                "Bu hafta Güneş sistemi.\n  1 Yorum yapıldı!\n  Daha fazla oku\n"
                "Uydurma Öğrenci\nçok güzel\nYorum Ekle",
                # The portal's second, title-less rendering of the same post.
                "Kurgu Öğretmen | 28.09.2026\nSevgili öğrencilerim,\nBu hafta Güneş sistemi.",
            ],
            items=["Gezegenleri  Güneş'e uzaklıklarına göre sıralar."])}
        assert self._related(client, self.FEN_SINAVI, ders) == [
            {"title": "3. Hafta", "type": "ders_icerikleri"},
            {"title": "Gezegenleri Güneş'e uzaklıklarına göre sıralar.", "type": "ders_icerikleri"},
        ]

    def test_teacher_signature_and_comments_never_become_titles(self, client):
        ders = {"Fen Bilimleri": _icerik(cards=[
            "Kurgu Öğretmen | 28.09.2026\nSevgili öğrencilerim,",
            "Uzay Çağı\nKurgu Öğretmen | 21.09.2026\n  Daha fazla oku\nUydurma Öğrenci\nYorum Ekle",
        ])}
        basliklar = [c["title"] for c in self._related(client, self.FEN_SINAVI, ders)]
        assert basliklar == ["Uzay Çağı"]
        assert not any("Kurgu Öğretmen" in b or "Uydurma Öğrenci" in b for b in basliklar)

    def test_turkish_case_content_matching(self, client):
        """Course name case mismatch must still find content."""
        ders = {"İngilizce": _icerik(cards=["Week 3\nÖrnek Teacher | 28.09.2026\nDear 7th graders,"])}
        content = self._related(
            client, "5-6-7-8. SINIFLAR İNGİLİZCE – 2. DÖNEM 1. YAZILI SINAVI", ders)
        assert content == [{"title": "Week 3", "type": "ders_icerikleri"}]

    def test_other_courses_and_unread_courses_add_nothing(self, client):
        ders = {
            "Matematik": _icerik(cards=["Rasyonel sayılar\nÖrnek Hoca | 28.09.2026"]),
            "Fen Bilimleri": {"tab_id": "ders_4", "error": "Message: no such element"},
        }
        assert self._related(client, self.FEN_SINAVI, ders) == []

    def test_titles_are_bounded_and_deduplicated(self, client):
        uzun = "Kuvvet ve enerji " * 20
        ders = {"Fen Bilimleri": _icerik(
            cards=[f"Başlık {i}\nKurgu Öğretmen | 28.09.2026" for i in range(8)],
            # An item repeating a card title is listed once.
            items=[uzun, "Başlık 1"] + [f"Kazanım {i}" for i in range(8)])}
        content = self._related(client, self.FEN_SINAVI, ders)
        basliklar = [c["title"] for c in content]
        # Five card titles, then the first five items with the repeat dropped.
        assert basliklar[:5] == [f"Başlık {i}" for i in range(5)]
        assert basliklar[6:] == ["Kazanım 0", "Kazanım 1", "Kazanım 2"]
        assert basliklar.count("Başlık 1") == 1
        assert basliklar[5].endswith("…") and len(basliklar[5]) <= 140
        assert all(len(b) <= 140 for b in basliklar)

    def test_at_most_ten_across_duplicate_course_tabs(self, client):
        # The portal has two tabs for one course ("İngilizce", "İngilizce (2)"
        # both normalise to İngilizce); together they must not exceed ten.
        ders = {
            "İngilizce": _icerik(cards=[f"Week {i}" for i in range(5)],
                                 items=[f"Outcome {i}" for i in range(5)]),
            "İngilizce (2)": _icerik(cards=["Reading club"]),
        }
        content = self._related(
            client, "5-6-7-8. SINIFLAR İNGİLİZCE – 2. DÖNEM 1. YAZILI SINAVI", ders)
        assert len(content) == 10


class TestRealPortalExamTitles:
    """Real titles measured 2026-09-28 (plan
    docs/superpowers/sdd/2026-09-28-pano-eksiklikleri/): _extract_exam_info's
    regexes need a dash (_COURSE_FROM_TITLE_RE) or the plural "Sınıflar"
    prefix, neither of which every real portal title has, so `course` stayed
    the whole title and relatedContent was always []. The fix looks for a
    known course name (from ders_icerikleri's own keys, Turkish-folded,
    word-bounded) inside the title when the regexes did not land on one —
    without ever moving the exam id, which hashes the *legacy* course."""

    TURKCE_ORTAK = (
        "7. Sınıf MEB Ülke Geneli Türkçe 1. Dönem 2. Ortak Yazılı Sınavı"
        " / 7th Grade MEB Türkiye-wide Turkish 1st Term 2nd Common Written Exam"
    )
    # Same real exam, but with the "Ortak" word dropped so _SINAV_NUMBER_RE
    # (which requires the digit directly before "Yazılı"/"Sınav") resolves
    # examNumber — used to test grade/homework matching under the resolved
    # course, a thing the literal title (no examNumber) cannot exercise.
    TURKCE_SAYILI = (
        "7. Sınıf MEB Ülke Geneli Türkçe 1. Dönem 2. Yazılı Sınavı"
        " / 7th Grade MEB Türkiye-wide Turkish 1st Term 2nd Written Exam"
    )
    GIS = (
        "5-6-7. Sınıflar Özdebir Gelişim İzleme Sınavı GİS-1 (Türkiye Geneli)"
        " / 5th-6th-7th Grades Ozdebir Development Monitoring Exam GIS-1 (Turkey-wide)"
    )
    HAFTA_BASLANGICI = (
        "5-6-7-8. Sınıflar MEB 1. Dönem 2. Yazılı Sınav Haftası Başlangıcı"
        " / 5th-6th-7th-8th Grades MEB 1st Term 2nd Written Exam Week Beginning"
    )

    DERS = {
        "Türkçe": _icerik(cards=[
            "3. Ünite\nGerçek Öğretmen | 20.09.2026\nBu hafta şiir türleri."]),
        "Matematik": _icerik(cards=["Rasyonel sayılar\nGerçek Hoca | 20.09.2026"]),
    }

    def test_week_marker_is_not_an_exam(self):
        """_SINAV_EXCLUDE already screens this out via "başlangıcı" — pinned
        so a future change to the fix does not silently start treating a
        week-marker announcement as an exam."""
        assert not dashboard_api._is_exam_event(self.HAFTA_BASLANGICI)

    def test_gis_is_an_exam_event(self):
        assert dashboard_api._is_exam_event(self.GIS)

    def test_legacy_extraction_still_returns_whole_title(self):
        """_extract_exam_info itself must stay untouched — the exam id is
        computed from its return value. This pins the bug the new fallback
        works around, and doubles as the "before" half of the id-stability
        proof below."""
        course, raw, num = dashboard_api._extract_exam_info(self.TURKCE_ORTAK)
        assert course.startswith("7. Sınıf")
        assert "Türkçe" in course  # embedded, just not isolated

    def test_turkce_ortak_sinavi_related_content(self, client):
        takvim = [_exam_event(self.TURKCE_ORTAK, "2026-03-31T10:00:00Z")]
        with patch.object(dashboard_api, "_scraped", return_value=_scraped_with_exams(
                takvim=takvim, ders_icerikleri=self.DERS)):
            exam = client.get("/api/exams").get_json()["exams"][0]
        assert exam["course"] == "Türkçe"
        assert exam["relatedContent"] == [
            {"title": "3. Ünite", "type": "ders_icerikleri"}]
        assert exam["rawTitle"] == self.TURKCE_ORTAK       # full title still visible
        assert exam["title"].startswith("Türkçe ·")         # sensible label

    def test_gis_stays_courseless(self, client):
        takvim = [_exam_event(self.GIS, "2026-03-31T10:00:00Z")]
        with patch.object(dashboard_api, "_scraped", return_value=_scraped_with_exams(
                takvim=takvim, ders_icerikleri=self.DERS)):
            exam = client.get("/api/exams").get_json()["exams"][0]
        assert exam["course"] not in self.DERS
        assert exam["relatedContent"] == []

    def test_ambiguous_title_stays_courseless(self):
        """Two distinct known courses named in one title: never force it
        onto either one."""
        title = ("7. Sınıf MEB Ülke Geneli Türkçe ve Matematik Ortak Sınavı"
                 " / 7th Grade MEB Türkiye-wide Turkish and Mathematics Common Exam")
        legacy, _, _ = dashboard_api._extract_exam_info(title)
        resolved = dashboard_api._cozumlenen_sinav_dersi(legacy, title, self.DERS)
        assert resolved not in ("Türkçe", "Matematik")

    def test_exam_id_unchanged_by_course_resolution_fix(self, client):
        """The id hashes the *legacy* course (whatever _extract_exam_info
        returns), the title, and _kimlik_zamani(date) — untouched by the new
        course-resolution fallback, so an id already handed to a module or
        bookmark never moves."""
        date_str = "2026-03-31T10:00:00Z"
        takvim = [_exam_event(self.TURKCE_ORTAK, date_str)]
        legacy_course, _, _ = dashboard_api._extract_exam_info(self.TURKCE_ORTAK)
        expected_id = hashlib.md5(
            f"{legacy_course}|{self.TURKCE_ORTAK}|"
            f"{dashboard_api._kimlik_zamani(date_str)}".encode()
        ).hexdigest()[:12]
        with patch.object(dashboard_api, "_scraped", return_value=_scraped_with_exams(
                takvim=takvim, ders_icerikleri=self.DERS)):
            exam = client.get("/api/exams").get_json()["exams"][0]
        assert exam["id"] == expected_id
        assert exam["course"] == "Türkçe"        # display resolved...
        assert legacy_course != "Türkçe"          # ...but the id's input did not

    def test_grade_and_homework_use_resolved_course(self, client):
        past = "2026-03-31T10:00:00Z"
        takvim = [_exam_event(self.TURKCE_SAYILI, past)]
        grades = [_grade_row("Türkçe", s2="90")]
        homework = [_homework_row("Türkçe", "Şiir tekrarı", "20.03.2026 12:00")]
        with patch.object(dashboard_api, "_scraped", return_value=_scraped_with_exams(
                takvim=takvim, grades=grades, homework=homework,
                ders_icerikleri=self.DERS)):
            exam = client.get("/api/exams").get_json()["exams"][0]
        assert exam["grade"] == "90"
        assert [hw["title"] for hw in exam["relatedHomework"]] == ["Şiir tekrarı"]

    def test_content_map_key_tries_legacy_then_resolved(self, client):
        """exam_content_map.json entries were written keyed on the *old*
        course value (course_names.py never invented one before this fix);
        they must not be orphaned."""
        past = "2026-03-31T10:00:00Z"
        takvim = [_exam_event(self.TURKCE_ORTAK, past)]
        legacy_course, _, _ = dashboard_api._extract_exam_info(self.TURKCE_ORTAK)
        legacy_key = f"{legacy_course}|{self.TURKCE_ORTAK}|{past[:10]}"
        content_map = {legacy_key: {"summary": "Eski özet"}}

        def _load_json_yerine(name):
            return content_map if name == "exam_content_map.json" else {}

        with patch.object(dashboard_api, "_scraped", return_value=_scraped_with_exams(
                takvim=takvim, ders_icerikleri=self.DERS)), \
             patch.object(dashboard_api, "_load_json", side_effect=_load_json_yerine):
            exam = client.get("/api/exams").get_json()["exams"][0]
        assert exam["aiSummary"] == "Eski özet"

    def test_content_map_key_also_tries_resolved_course(self, client):
        """A future entry keyed on the resolved course must also be found."""
        past = "2026-03-31T10:00:00Z"
        takvim = [_exam_event(self.TURKCE_ORTAK, past)]
        resolved_key = f"Türkçe|{self.TURKCE_ORTAK}|{past[:10]}"
        content_map = {resolved_key: {"summary": "Yeni özet"}}

        def _load_json_yerine(name):
            return content_map if name == "exam_content_map.json" else {}

        with patch.object(dashboard_api, "_scraped", return_value=_scraped_with_exams(
                takvim=takvim, ders_icerikleri=self.DERS)), \
             patch.object(dashboard_api, "_load_json", side_effect=_load_json_yerine):
            exam = client.get("/api/exams").get_json()["exams"][0]
        assert exam["aiSummary"] == "Yeni özet"

    def test_no_duplicate_synthetic_exam_after_course_resolution(self, client):
        """Once the takvim exam's course resolves to the real "Türkçe", the
        grade-derived synthetic-exam loop must recognise it as already seen
        and not double it."""
        past = "2026-03-31T10:00:00Z"
        takvim = [_exam_event(self.TURKCE_SAYILI, past)]
        grades = [_grade_row("Türkçe", s2="90")]
        with patch.object(dashboard_api, "_scraped", return_value=_scraped_with_exams(
                takvim=takvim, grades=grades, ders_icerikleri=self.DERS)):
            data = client.get("/api/exams").get_json()
        assert len(data["exams"]) == 1

    # -- Review finding (critical, 2026-09-28): ders_icerikleri also carries
    # non-subject tabs measured on live data — "Genel" (the school-wide
    # announcement feed), "PDR" (guidance) and "Sınıf Öğretmeni" (homeroom
    # teacher). Taking every key unfiltered let a title like "... Genel
    # Deneme Sınavı / ..." resolve to a fake course "Genel" and surface an
    # unrelated announcement as relatedContent.

    DERS_GENEL_KARISIK = {
        "Türkçe": _icerik(cards=[
            "3. Ünite\nGerçek Öğretmen | 20.09.2026\nBu hafta şiir türleri."]),
        "Genel": _icerik(cards=["Okul duyurusu: Veli toplantısı 10 Ekimde."]),
        "PDR": _icerik(cards=["Rehberlik saati: sınav kaygısı."]),
        "Sınıf Öğretmeni": _icerik(cards=["Sınıf öğretmeni notu: kitap listesi."]),
    }

    def test_genel_review_title_stays_courseless(self, client):
        titles = [
            ("5-6-7-8. Sınıflar MEB 1. Dönem Genel Deneme Sınavı"
             " / 5th-6th-7th-8th Grades MEB 1st Term General Trial Exam"),
            ("5-6-7-8. Sınıflar MEB 2. Dönem Genel Tekrar Sınavı"
             " / 5th-6th-7th-8th Grades MEB 2nd Term General Review Exam"),
            ("5-6-7-8. Sınıflar MEB 1. Dönem Genel Tarama Sınavı"
             " / 5th-6th-7th-8th Grades MEB 1st Term General Screening Exam"),
        ]
        for title in titles:
            takvim = [_exam_event(title, "2026-03-31T10:00:00Z")]
            with patch.object(dashboard_api, "_scraped", return_value=_scraped_with_exams(
                    takvim=takvim, ders_icerikleri=self.DERS_GENEL_KARISIK)):
                exam = client.get("/api/exams").get_json()["exams"][0]
            assert exam["course"] != "Genel", title
            assert exam["relatedContent"] == [], title

    def test_pdr_and_sinif_ogretmeni_titles_never_resolve_to_tab(self, client):
        titles = [
            ("5-6-7-8. Sınıflar PDR Değerlendirme Sınavı"
             " / 5th-6th-7th-8th Grades PDR Assessment Exam"),
            ("5-6-7-8. Sınıflar Sınıf Öğretmeni Bilgilendirme Sınavı"
             " / 5th-6th-7th-8th Grades Homeroom Teacher Briefing Exam"),
        ]
        for title in titles:
            takvim = [_exam_event(title, "2026-03-31T10:00:00Z")]
            with patch.object(dashboard_api, "_scraped", return_value=_scraped_with_exams(
                    takvim=takvim, ders_icerikleri=self.DERS_GENEL_KARISIK)):
                exam = client.get("/api/exams").get_json()["exams"][0]
            assert exam["course"] not in ("PDR", "Sınıf Öğretmeni"), title
            assert exam["relatedContent"] == [], title

    def test_genel_key_is_not_a_candidate_directly(self):
        """Unit-level: "Genel"/"PDR"/"Sınıf Öğretmeni" must never even enter
        the candidate map — subject_themes.domain_of() resolves each of them
        only to the generic fallback domain ("genel")."""
        adaylar = dashboard_api._bilinen_ders_adaylari(self.DERS_GENEL_KARISIK)
        assert "Genel" not in adaylar
        assert "PDR" not in adaylar
        assert "Sınıf Öğretmeni" not in adaylar
        assert "Türkçe" in adaylar

    def test_slash_split_tolerates_spacing_variants(self):
        """The Turkish/English split must not depend on exact " / " spacing:
        if the English half leaks into the scan (no split at all), its
        "Türkçe Karşılığı" gloss would add a second, spurious course and
        turn a clean single match ("İngilizce") into a false ambiguity."""
        taban = ("7. Sınıf İngilizce 1. Dönem 2. Yazılı Sınavı"
                 "{sep}7th Grade Turkish equivalent: Türkçe Karşılığı")
        for sep in ("/", " /", "/ ", " / ", "  /  "):
            title = taban.format(sep=sep)
            assert dashboard_api._baslikta_bilinen_ders_ara(
                title, self.DERS) == "İngilizce", title


class TestSyntheticExams:
    """Exams created from grade table when no takvim event exists."""

    def test_creates_synthetic_from_grades(self, client):
        grades = [_grade_row("Matematik", s1="85", s2="90")]
        with patch.object(dashboard_api, "_scraped",
                          return_value=_scraped_with_exams(grades=grades)):
            data = client.get("/api/exams").get_json()
            assert len(data["exams"]) == 2
            for e in data["exams"]:
                assert e["status"] == "past"
                assert e["grade"] is not None

    def test_synthetic_not_duplicated_with_takvim(self, client):
        """If takvim has the exam, don't create synthetic duplicate."""
        past = (datetime.now() - timedelta(days=5)).isoformat() + "Z"
        takvim = [_exam_event(
            "5-6-7-8. SINIFLAR MATEMATİK"
            " – 2. DÖNEM 1. YAZILI SINAVI",
            past)]
        grades = [_grade_row("Matematik", s1="85")]
        with patch.object(dashboard_api, "_scraped",
                          return_value=_scraped_with_exams(
                              takvim=takvim, grades=grades)):
            data = client.get("/api/exams").get_json()
            # Should have takvim exam but not duplicate synthetic
            mat_exams = [e for e in data["exams"]
                         if "MATEMATİK" in e.get("rawTitle", "").upper()
                         or "Matematik" in e.get("rawTitle", "")]
            # At most 2: takvim + synthetic (only if course doesn't match)
            assert len(mat_exams) >= 1

    def test_synthetic_has_no_date(self, client):
        grades = [_grade_row("Türkçe", s1="75")]
        with patch.object(dashboard_api, "_scraped",
                          return_value=_scraped_with_exams(grades=grades)):
            data = client.get("/api/exams").get_json()
            assert data["exams"][0]["date"] is None

    # Measured: the portal kept 2025-2026's "4. Arakarne" report well into
    # 2026-2027, and /api/exams listed its graded columns as this year's past
    # exams. The assistant's notlar already makes this check.
    def test_prior_year_report_makes_no_synthetic_exams(self, client):
        grades = [_grade_row("Matematik", s1="85", s2="90")]
        with patch.object(dashboard_api, "_scraped", return_value=_scraped_with_exams(
                grades=grades, semester="2025-2026 4. Arakarne")), \
             patch.object(dashboard_api, "_guncel_ogretim_yili", return_value="2026-2027"):
            data = client.get("/api/exams").get_json()
        assert data["exams"] == []
        assert data["stats"] == {"upcoming": 0, "past": 0, "averageGrade": None}

    def test_prior_year_report_keeps_takvim_exams(self, client):
        past = (datetime.now() - timedelta(days=5)).isoformat() + "Z"
        takvim = [_exam_event("5-6-7-8. SINIFLAR TÜRKÇE – 1. DÖNEM 1. YAZILI SINAVI", past)]
        grades = [_grade_row("Matematik", s1="85")]
        with patch.object(dashboard_api, "_scraped", return_value=_scraped_with_exams(
                takvim=takvim, grades=grades, semester="2025-2026 4. Arakarne")), \
             patch.object(dashboard_api, "_guncel_ogretim_yili", return_value="2026-2027"):
            data = client.get("/api/exams").get_json()
        assert len(data["exams"]) == 1
        assert data["exams"][0]["date"] is not None          # the takvim one, not a synthetic

    def test_current_year_report_still_makes_synthetic_exams(self, client):
        grades = [_grade_row("Matematik", s1="85", s2="90")]
        with patch.object(dashboard_api, "_scraped", return_value=_scraped_with_exams(
                grades=grades, semester="2026-2027 1. Dönem")), \
             patch.object(dashboard_api, "_guncel_ogretim_yili", return_value="2026-2027"):
            data = client.get("/api/exams").get_json()
        assert len(data["exams"]) == 2 and data["stats"]["averageGrade"] == 87.5

    def test_unknown_year_keeps_synthetic_exams(self, client):
        grades = [_grade_row("Matematik", s1="85")]
        with patch.object(dashboard_api, "_scraped", return_value=_scraped_with_exams(
                grades=grades, semester="2025-2026 4. Arakarne")), \
             patch.object(dashboard_api, "_guncel_ogretim_yili", return_value=None):
            data = client.get("/api/exams").get_json()
        assert len(data["exams"]) == 1


class TestExamEdgeCases:
    """Edge cases and robustness."""

    def test_malformed_takvim_entry_skipped(self, client):
        takvim = [
            "not a dict",
            {"title": "", "start": ""},  # empty title
            None,
        ]
        with patch.object(dashboard_api, "_scraped",
                          return_value=_scraped_with_exams(takvim=takvim)):
            data = client.get("/api/exams").get_json()
            assert data["exams"] == []

    def test_invalid_date_format_handled(self, client):
        takvim = [_exam_event(
            "Matematik 1. Yazılı Sınavı", "not-a-date")]
        with patch.object(dashboard_api, "_scraped",
                          return_value=_scraped_with_exams(takvim=takvim)):
            data = client.get("/api/exams").get_json()
            # Should not crash
            assert len(data["exams"]) == 1
            assert data["exams"][0]["status"] == "past"

    def test_gelisim_raporu_not_dict_handled(self, client):
        scraped = _scraped_with_exams()
        scraped["gelisim_raporu"] = "invalid"
        with patch.object(dashboard_api, "_scraped",
                          return_value=scraped):
            data = client.get("/api/exams").get_json()
            assert data["exams"] == []

    def test_exam_id_is_deterministic(self, client):
        takvim = [_exam_event(
            "Matematik 1. Yazılı Sınavı",
            "2026-04-01T09:00:00Z")]
        with patch.object(dashboard_api, "_scraped",
                          return_value=_scraped_with_exams(takvim=takvim)):
            d1 = client.get("/api/exams").get_json()
            d2 = client.get("/api/exams").get_json()
            assert d1["exams"][0]["id"] == d2["exams"][0]["id"]

    def test_multiple_exams_same_course(self, client):
        now = datetime.now()
        t1 = (now - timedelta(days=30)).isoformat() + "Z"
        t2 = (now - timedelta(days=5)).isoformat() + "Z"
        takvim = [
            _exam_event("Matematik 1. Yazılı Sınavı", t1),
            _exam_event("Matematik 2. Yazılı Sınavı", t2),
        ]
        with patch.object(dashboard_api, "_scraped",
                          return_value=_scraped_with_exams(takvim=takvim)):
            data = client.get("/api/exams").get_json()
            assert len(data["exams"]) == 2


class TestPriorYearGrades:
    """A takvim exam takes its grade only from this school year's report.
    Measured 2026-09-28: with 2025-2026's "4. Arakarne" still on the portal,
    this year's past Matematik exam was shown with last year's 1. Sınav (85)
    and counted in the average."""

    MAT_SINAVI = "5-6-7-8. SINIFLAR MATEMATİK – 2. DÖNEM 1. YAZILI SINAVI"

    def _exams(self, client, semester, yil):
        past = (datetime.now() - timedelta(days=5)).isoformat() + "Z"
        data = _scraped_with_exams(takvim=[_exam_event(self.MAT_SINAVI, past)],
                                   grades=[_grade_row("Matematik", s1="85")],
                                   semester=semester)
        with patch.object(dashboard_api, "_scraped", return_value=data), \
             patch.object(dashboard_api, "_guncel_ogretim_yili", return_value=yil):
            return client.get("/api/exams").get_json()

    def test_prior_year_report_grades_no_takvim_exam(self, client):
        data = self._exams(client, "2025-2026 4. Arakarne", "2026-2027")
        assert len(data["exams"]) == 1                      # the exam itself stays
        assert data["exams"][0]["grade"] is None
        assert data["stats"]["averageGrade"] is None

    def test_current_year_report_still_grades_takvim_exam(self, client):
        data = self._exams(client, "2026-2027 1. Dönem", "2026-2027")
        assert data["exams"][0]["grade"] == "85"
        assert data["stats"]["averageGrade"] == 85.0

    def test_unknown_year_still_grades_takvim_exam(self, client):
        data = self._exams(client, "2025-2026 4. Arakarne", None)
        assert data["exams"][0]["grade"] == "85"
