"""Tests for dedup correctness and idempotency across all sync functions."""
import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_classroom_service():
    """Build a mock Classroom service matching the patterns used in production."""
    svc = MagicMock()
    svc.courses().courseWork().list().execute.return_value = {"courseWork": []}
    svc.courses().courseWork().create.return_value.execute.return_value = {"id": "cw1"}
    svc.courses().courseWork().patch.return_value.execute.return_value = {"id": "cw1"}
    svc.courses().announcements().create.return_value.execute.return_value = {"id": "ann1"}
    svc.courses().announcements().patch.return_value.execute.return_value = {"id": "ann1"}
    return svc


# ===========================================================================
# TestHashStability
# ===========================================================================

class TestHashStability:
    """Verify compute_hash produces correct, stable, deterministic results."""

    def test_deterministic_across_100_calls(self):
        from src.sync_to_classroom import compute_hash
        item = {"ders": "Matematik", "baslik": "Geometri"}
        hashes = [compute_hash(item) for _ in range(100)]
        assert len(set(hashes)) == 1

    def test_key_order_irrelevant(self):
        from src.sync_to_classroom import compute_hash
        a = {"z": 3, "a": 1, "m": 2}
        b = {"a": 1, "m": 2, "z": 3}
        assert compute_hash(a) == compute_hash(b)

    def test_output_is_16_hex_chars(self):
        from src.sync_to_classroom import compute_hash
        h = compute_hash({"anything": True})
        assert len(h) == 16
        assert all(c in "0123456789abcdef" for c in h)

    def test_any_field_change_produces_different_hash(self):
        from src.sync_to_classroom import compute_hash
        base = {"title": "Odev", "score": 85, "desc": "aciklama"}
        h_base = compute_hash(base)
        for key in base:
            modified = dict(base)
            modified[key] = "CHANGED"
            assert compute_hash(modified) != h_base, f"changing '{key}' should change hash"

    def test_string_input_works(self):
        from src.sync_to_classroom import compute_hash
        h = compute_hash("Merhaba dunya")
        assert isinstance(h, str) and len(h) == 16
        assert compute_hash("Merhaba dunya") == h
        assert compute_hash("Farkli metin") != h


# ===========================================================================
# TestSyncStateRoundTrip
# ===========================================================================

class TestSyncStateRoundTrip:
    """Verify save/load preserves all state data exactly."""

    def test_50_keys_roundtrip(self, tmp_path):
        from src.sync_to_classroom import load_sync_state, save_sync_state
        path = str(tmp_path / "state.json")
        state = {}
        prefixes = ["cw", "mat", "grade", "ann", "eba", "mebi", "sebitv", "ec", "sebit_hw"]
        for i in range(50):
            prefix = prefixes[i % len(prefixes)]
            state[f"{prefix}:course_{i}:item_{i}"] = {
                "classroom_id": f"id_{i}",
                "last_hash": f"hash_{i:016x}",
            }
        save_sync_state(state, path)
        loaded = load_sync_state(path)
        assert loaded == state

    def test_turkish_characters_survive(self, tmp_path):
        from src.sync_to_classroom import load_sync_state, save_sync_state
        path = str(tmp_path / "state_tr.json")
        state = {
            "cw:123:Odev Basligi": {"classroom_id": "x", "last_hash": "a" * 16},
            "mat:456:Turkce - Haftalik Icerik": {"classroom_id": "y", "last_hash": "b" * 16},
            "ann:789:Sinav hazirliklari ile ilgili duyuru": {"classroom_id": "z", "last_hash": "c" * 16},
        }
        save_sync_state(state, path)
        loaded = load_sync_state(path)
        assert loaded == state

    def test_empty_hash_values_survive(self, tmp_path):
        from src.sync_to_classroom import load_sync_state, save_sync_state
        path = str(tmp_path / "state_empty.json")
        state = {
            "cw:c1:test": {"classroom_id": "", "last_hash": ""},
            "ann:c2:test": {"classroom_id": "a", "last_hash": ""},
        }
        save_sync_state(state, path)
        loaded = load_sync_state(path)
        assert loaded == state


# ===========================================================================
# TestIdempotency
# ===========================================================================

class TestIdempotencySyncOdevler:
    """sync_odevler: first call adds, second call with same data skips."""

    def test_idempotent(self):
        from src.sync_to_classroom import sync_odevler
        svc = _mock_classroom_service()
        courses = {"Matematik": "c1", "TED Genel": "cg"}
        data = {
            "odevlerim": {
                "homework": {
                    "headers": [],
                    "rows": [
                        {
                            "Ders Adi": "Matematik",
                            "Odev Basligi": "Test Odevi",
                            "Odev Son Teslim Tarihi": "27.02.2026 12:00",
                            "Odev Durumu": "Degerlendirilmemis",
                            "detail": {"description": "Sayfa 10-15", "attachments": []},
                        }
                    ],
                }
            }
        }
        state = {}
        r1 = sync_odevler(svc, courses, data, state)
        assert r1["added"] >= 1

        r2 = sync_odevler(svc, courses, data, state)
        assert r2["added"] == 0
        assert r2["skipped"] >= 1


class TestIdempotencySyncDersIcerikleri:
    """sync_ders_icerikleri: first call adds, second call skips."""

    def test_idempotent(self):
        from src.sync_to_classroom import sync_ders_icerikleri
        svc = _mock_classroom_service()
        courses = {"Turkce": "ct", "TED Genel": "cg"}
        data = {
            "ders_icerikleri": {
                "Turkce": {"tab_id": "t1", "text": "23. Hafta cumle analizi yapacagiz."}
            }
        }
        state = {}
        r1 = sync_ders_icerikleri(svc, courses, data, state)
        assert r1["added"] >= 1

        r2 = sync_ders_icerikleri(svc, courses, data, state)
        assert r2["added"] == 0
        assert r2["skipped"] >= 1


class TestIdempotencySyncNotlar:
    """sync_notlar: first call adds, second call skips."""

    def test_idempotent(self):
        from src.sync_to_classroom import sync_notlar
        svc = _mock_classroom_service()
        courses = {"Matematik": "c1", "TED Genel": "cg"}
        data = {
            "gelisim_raporu": {
                "grades": [
                    {"Ders": "Matematik", "1. Sinav": "85", "2. Sinav": "90"}
                ]
            }
        }
        state = {}
        r1 = sync_notlar(svc, courses, data, state)
        assert r1["added"] >= 1

        r2 = sync_notlar(svc, courses, data, state)
        assert r2["added"] == 0
        assert r2["skipped"] >= 1


class TestIdempotencySyncDuyurular:
    """sync_duyurular: first call adds, second call skips."""

    def test_idempotent(self):
        from src.sync_to_classroom import sync_duyurular
        svc = _mock_classroom_service()
        courses = {"TED Genel": "cg"}
        data = {
            "duyurular": {
                "announcements": [
                    {"e-Posta Baslik": "Okul Duyurusu", "Yayin Tarihi": "08.03.2026"}
                ]
            },
            "takvim": [],
            "takim_calismalari": {},
            "ogep": {},
        }
        state = {}
        r1 = sync_duyurular(svc, courses, data, state)
        assert r1["added"] >= 1

        r2 = sync_duyurular(svc, courses, data, state)
        assert r2["added"] == 0
        assert r2["skipped"] >= 1


class TestIdempotencySyncEbaTextbooks:
    """sync_eba_textbooks: first call adds, second call skips."""

    @patch("src.sync_to_classroom._ensure_materials_accessible")
    @patch("src.sync_to_classroom._load_upload_tracker")
    def test_idempotent(self, mock_tracker, mock_ensure):
        from src.sync_to_classroom import sync_eba_textbooks
        mock_tracker.return_value = {
            "hash1": {
                "title": "Fen 1. Kitap",
                "course": "Fen Bilimleri",
                "driveId": "d1",
                "link": "https://drive.google.com/file/d/d1/view",
            }
        }
        svc = _mock_classroom_service()
        courses = {"Fen Bilimleri": "cf", "TED Genel": "cg"}
        state = {}
        r1 = sync_eba_textbooks(svc, courses, state)
        assert r1["added"] >= 1

        r2 = sync_eba_textbooks(svc, courses, state)
        assert r2["added"] == 0
        assert r2["skipped"] >= 1


class TestIdempotencySyncMebiVideos:
    """sync_mebi_videos: first call adds, second call skips."""

    @patch("src.sync_to_classroom._ensure_materials_accessible")
    @patch("src.sync_to_classroom._load_upload_tracker")
    def test_idempotent(self, mock_tracker, mock_ensure):
        from src.sync_to_classroom import sync_mebi_videos
        mock_tracker.return_value = {
            "uuid1": {
                "course": "Din Kulturu",
                "unit": "Peygamber",
                "topic": "Insanlara Rehber",
                "driveId": "d2",
                "link": "https://drive.google.com/file/d/d2/view",
            }
        }
        svc = _mock_classroom_service()
        courses = {"Din Kulturu": "cd", "TED Genel": "cg"}
        state = {}
        r1 = sync_mebi_videos(svc, courses, state)
        assert r1["added"] >= 1

        r2 = sync_mebi_videos(svc, courses, state)
        assert r2["added"] == 0
        assert r2["skipped"] >= 1


class TestIdempotencySyncSebitv:
    """sync_sebitv: first call adds, second call skips."""

    @patch("src.sync_to_classroom._ensure_materials_accessible")
    @patch("src.sync_to_classroom._load_upload_tracker")
    def test_idempotent(self, mock_tracker, mock_ensure):
        from src.sync_to_classroom import sync_sebitv
        # _load_upload_tracker is called twice (sebitv + interactive)
        mock_tracker.side_effect = [
            {
                "hash1": {
                    "course": "Matematik",
                    "unit": "Sayilar",
                    "title": "Park Tasarimi",
                    "type": "Konu Anlatimi",
                    "driveId": "d3",
                    "link": "https://drive.google.com/file/d/d3/view",
                }
            },
            {},  # sebitv_interactive_uploaded.json (empty)
        ]
        svc = _mock_classroom_service()
        courses = {"Matematik": "cm", "TED Genel": "cg"}
        state = {}
        r1 = sync_sebitv(svc, courses, state)
        assert r1["added"] >= 1

        # Reset side_effect for second call
        mock_tracker.side_effect = [
            {
                "hash1": {
                    "course": "Matematik",
                    "unit": "Sayilar",
                    "title": "Park Tasarimi",
                    "type": "Konu Anlatimi",
                    "driveId": "d3",
                    "link": "https://drive.google.com/file/d/d3/view",
                }
            },
            {},
        ]
        r2 = sync_sebitv(svc, courses, state)
        assert r2["added"] == 0
        assert r2["skipped"] >= 1


class TestIdempotencySyncEnglishcentral:
    """sync_englishcentral: first call adds, second call skips."""

    @patch("src.sync_to_classroom._load_upload_tracker")
    def test_idempotent(self, mock_tracker):
        from src.sync_to_classroom import sync_englishcentral
        mock_tracker.return_value = {
            "videos": [
                {"title": "Test Video", "completed": True, "url": "https://ec.com/1"},
                {"title": "Other Video", "completed": False, "started": True, "url": "https://ec.com/2"},
            ],
            "total_videos": 2,
            "completed_videos": 1,
            "scraped_at": "2026-03-08T10:00:00",
        }
        svc = _mock_classroom_service()
        courses = {"\u0130ngilizce": "ci", "TED Genel": "cg"}
        state = {}
        r1 = sync_englishcentral(svc, courses, state)
        assert r1["added"] >= 1

        r2 = sync_englishcentral(svc, courses, state)
        assert r2["added"] == 0
        assert r2["skipped"] >= 1


class TestIdempotencySyncSebitHomework:
    """sync_sebit_homework: first call adds, second call skips."""

    @patch("src.sync_to_classroom._load_upload_tracker")
    def test_idempotent(self, mock_tracker):
        from src.sync_to_classroom import sync_sebit_homework
        mock_tracker.return_value = {
            "homework": [
                {
                    "course": "Matematik",
                    "title": "Odev 1",
                    "completed": True,
                    "progress": 100,
                    "teacher": "Test Ogretmen",
                    "start_date": "01.03.2026",
                    "end_date": "08.03.2026",
                    "state": 0,
                },
                {
                    "course": "Matematik",
                    "title": "Odev 2",
                    "completed": False,
                    "progress": 0,
                    "teacher": "Test Ogretmen",
                    "start_date": "05.03.2026",
                    "end_date": "12.03.2026",
                    "state": 0,
                },
            ],
            "scraped_at": "2026-03-08T10:00:00",
        }
        svc = _mock_classroom_service()
        courses = {"Matematik": "cm", "TED Genel": "cg"}
        state = {}
        r1 = sync_sebit_homework(svc, courses, state)
        assert r1["added"] >= 1

        r2 = sync_sebit_homework(svc, courses, state)
        assert r2["added"] == 0
        assert r2["skipped"] >= 1


# ===========================================================================
# TestCalendarIdempotency
# ===========================================================================

class TestCalendarIdempotency:
    """Verify Calendar sync dedup via upsert_event and sync_takvim."""

    def _mock_cal_service(self):
        svc = MagicMock()
        svc.events().insert.return_value.execute.return_value = {"id": "ev1"}
        return svc

    def test_upsert_event_existing_returns_exists(self):
        from src.sync_to_google import upsert_event
        svc = self._mock_cal_service()
        event_body = {
            "summary": "Matematik",
            "start": {"dateTime": "2026-03-09T08:00:00+03:00"},
            "end": {"dateTime": "2026-03-09T08:40:00+03:00"},
        }
        existing = {("Matematik", "2026-03-09T08:00:00"): "ev_existing"}
        result = upsert_event(svc, "cal_id", event_body, existing)
        assert result == "exists"
        svc.events().insert.assert_not_called()

    def test_upsert_event_new_returns_added(self):
        from src.sync_to_google import upsert_event
        svc = self._mock_cal_service()
        event_body = {
            "summary": "Turkce",
            "start": {"dateTime": "2026-03-09T09:00:00+03:00"},
            "end": {"dateTime": "2026-03-09T09:40:00+03:00"},
        }
        existing = {}
        result = upsert_event(svc, "cal_id", event_body, existing)
        assert result == "added"

    def test_sync_takvim_skips_ogep_titles(self):
        from src.sync_to_google import sync_takvim
        svc = self._mock_cal_service()
        # Use the exact Turkish key the source code reads:
        #   "ÖGEP (Öğrenci Gelişim Programı)"
        # The sync_takvim filter uses substring match on title and
        # also checks "ögep" in title.lower().
        data = {
            "takvim": [
                {
                    "title": "Bilim \u015eenli\u011fi",
                    "start": "2026-03-10T10:00:00+03:00",
                    "end": "2026-03-10T11:00:00+03:00",
                    "allDay": False,
                },
                {
                    "title": "\u00d6GEP Etkinli\u011fi",
                    "start": "2026-03-11T14:00:00+03:00",
                    "end": "2026-03-11T15:00:00+03:00",
                    "allDay": False,
                },
            ],
            "ogep": {
                "sessions": {
                    "rows": [
                        {"\u00d6GEP (\u00d6\u011frenci Geli\u015fim Program\u0131)": "\u00d6GEP Etkinli\u011fi"}
                    ]
                }
            },
        }
        existing = {}
        added = sync_takvim(svc, data, "cal_id", existing)
        # Only "Bilim Senligi" should be added; "OGEP Etkinligi" is skipped
        assert added == 1

    def test_sync_takvim_second_call_adds_zero(self):
        from src.sync_to_google import sync_takvim
        svc = self._mock_cal_service()
        data = {
            "takvim": [
                {
                    "title": "Veli Toplantisi",
                    "start": "2026-03-12T18:00:00+03:00",
                    "end": "2026-03-12T19:00:00+03:00",
                    "allDay": False,
                },
            ],
            "ogep": {},
        }
        existing = {}
        added1 = sync_takvim(svc, data, "cal_id", existing)
        assert added1 == 1

        # After first call, the event is now in existing_events
        existing[("Veli Toplantisi", "2026-03-12T18:00:00")] = "ev_inserted"
        added2 = sync_takvim(svc, data, "cal_id", existing)
        assert added2 == 0


# ===========================================================================
# TestDedupKeyFormats
# ===========================================================================

class TestDedupKeyFormats:
    """Verify dedup key patterns in the state dict after sync calls."""

    def test_odevler_key_format(self):
        from src.sync_to_classroom import sync_odevler
        svc = _mock_classroom_service()
        courses = {"Matematik": "c1", "TED Genel": "cg"}
        data = {
            "odevlerim": {
                "homework": {
                    "headers": [],
                    "rows": [
                        {
                            "Ders Ad\u0131": "Matematik",
                            "\u00d6dev Ba\u015fl\u0131\u011f\u0131": "Geometri \u00d6devi",
                            "\u00d6dev Son Teslim Tarihi": "",
                            "\u00d6dev Durumu": "",
                            "detail": {"description": "", "attachments": []},
                        }
                    ],
                }
            }
        }
        state = {}
        sync_odevler(svc, courses, data, state)
        assert any(k.startswith("cw:c1:") for k in state), f"keys: {list(state.keys())}"

    def test_ders_icerikleri_key_format(self):
        from src.sync_to_classroom import sync_ders_icerikleri
        svc = _mock_classroom_service()
        courses = {"Turkce": "ct", "TED Genel": "cg"}
        data = {
            "ders_icerikleri": {
                "Turkce": {"tab_id": "t1", "text": "Hafta icerigi"}
            }
        }
        state = {}
        sync_ders_icerikleri(svc, courses, data, state)
        matching = [k for k in state if k.startswith("mat:ct:")]
        assert len(matching) == 1
        assert "Haftalik Icerik" in matching[0] or "Haftalık İçerik" in matching[0]

    def test_notlar_key_format(self):
        from src.sync_to_classroom import sync_notlar
        svc = _mock_classroom_service()
        courses = {"Matematik": "c1", "TED Genel": "cg"}
        data = {
            "gelisim_raporu": {
                "grades": [{"Ders": "Matematik", "1. Sinav": "90"}]
            }
        }
        state = {}
        sync_notlar(svc, courses, data, state)
        matching = [k for k in state if k.startswith("grade:c1:")]
        assert len(matching) == 1
        assert "1. Sinav" in matching[0]

    def test_duyurular_key_format(self):
        from src.sync_to_classroom import sync_duyurular
        svc = _mock_classroom_service()
        courses = {"TED Genel": "cg"}
        data = {
            "duyurular": {
                "announcements": [
                    {"e-Posta Baslik": "Bilgi", "Yayin Tarihi": "01.03.2026"}
                ]
            },
            "takvim": [],
            "takim_calismalari": {},
            "ogep": {},
        }
        state = {}
        sync_duyurular(svc, courses, data, state)
        assert any(k.startswith("ann:cg:") for k in state), f"keys: {list(state.keys())}"

    @patch("src.sync_to_classroom._ensure_materials_accessible")
    @patch("src.sync_to_classroom._load_upload_tracker")
    def test_eba_key_format(self, mock_tracker, mock_ensure):
        from src.sync_to_classroom import sync_eba_textbooks
        mock_tracker.return_value = {
            "h1": {
                "title": "Kitap A",
                "course": "Fen Bilimleri",
                "driveId": "d1",
                "link": "https://link",
            }
        }
        svc = _mock_classroom_service()
        courses = {"Fen Bilimleri": "cf", "TED Genel": "cg"}
        state = {}
        sync_eba_textbooks(svc, courses, state)
        assert "eba:cf:textbooks" in state

    @patch("src.sync_to_classroom._ensure_materials_accessible")
    @patch("src.sync_to_classroom._load_upload_tracker")
    def test_mebi_key_format(self, mock_tracker, mock_ensure):
        from src.sync_to_classroom import sync_mebi_videos
        mock_tracker.return_value = {
            "u1": {
                "course": "Matematik",
                "unit": "Geometri",
                "topic": "Ucgenler",
                "driveId": "d2",
                "link": "https://link",
            }
        }
        svc = _mock_classroom_service()
        courses = {"Matematik": "cm", "TED Genel": "cg"}
        state = {}
        sync_mebi_videos(svc, courses, state)
        assert "mebi:cm:Geometri" in state

    @patch("src.sync_to_classroom._ensure_materials_accessible")
    @patch("src.sync_to_classroom._load_upload_tracker")
    def test_sebitv_key_format(self, mock_tracker, mock_ensure):
        from src.sync_to_classroom import sync_sebitv
        mock_tracker.side_effect = [
            {
                "h1": {
                    "course": "Matematik",
                    "unit": "Sayilar",
                    "title": "Sayi Dogru",
                    "type": "Video",
                    "driveId": "d3",
                    "link": "https://link",
                }
            },
            {},
        ]
        svc = _mock_classroom_service()
        courses = {"Matematik": "cm", "TED Genel": "cg"}
        state = {}
        sync_sebitv(svc, courses, state)
        assert "sebitv:cm:Sayilar" in state

    @patch("src.sync_to_classroom._load_upload_tracker")
    def test_englishcentral_key_format(self, mock_tracker):
        from src.sync_to_classroom import sync_englishcentral
        mock_tracker.return_value = {
            "videos": [{"title": "V1", "completed": True, "url": "https://ec/1"}],
            "total_videos": 1,
            "completed_videos": 1,
            "scraped_at": "2026-03-08T10:00:00",
        }
        svc = _mock_classroom_service()
        courses = {"\u0130ngilizce": "ci", "TED Genel": "cg"}
        state = {}
        sync_englishcentral(svc, courses, state)
        assert "ec:ci:progress" in state

    @patch("src.sync_to_classroom._load_upload_tracker")
    def test_sebit_homework_key_format(self, mock_tracker):
        from src.sync_to_classroom import sync_sebit_homework
        mock_tracker.return_value = {
            "homework": [
                {
                    "course": "Matematik",
                    "title": "HW1",
                    "completed": False,
                    "progress": 0,
                    "teacher": "T",
                    "start_date": "01.03.2026",
                    "end_date": "08.03.2026",
                    "state": 0,
                }
            ],
            "scraped_at": "2026-03-08",
        }
        svc = _mock_classroom_service()
        courses = {"Matematik": "cm", "TED Genel": "cg"}
        state = {}
        sync_sebit_homework(svc, courses, state)
        assert "sebit_hw:cm:progress" in state
