from src.data_validator import validate_scraped_data


def test_valid_data_passes():
    data = {
        "ogrenci_profili": {
            "name": "Işık Kurt", "student_no": "1234",
            "class_name": "7-A", "branch": "A", "fields": {},
        },
        "odevlerim": {"homework": {"rows": [
            {"Ders Adı": "Mat", "Ödev Başlığı": "HW"} for _ in range(10)
        ]}},
        "ders_programi": [{"schedule": {"rows": [["", "Mon"]]}}],
        "takvim": [{"title": "E1"}, {"title": "E2"}],
        "gelisim_raporu": {"grades": [
            {"Ders": f"D{i}"} for i in range(11)
        ]},
        "ders_icerikleri": {"T": [1]},
        "takim_calismalari": {"activities": [1]},
        "ogep": {"sessions": {"rows": [1]}},
        "duyurular": {"announcements": [1, 2]},
    }
    result = validate_scraped_data(data, previous_data=None)
    assert result["valid"] is True
    assert len(result["errors"]) == 0


def test_empty_odevlerim_fails():
    data = {
        "odevlerim": {"homework": {"rows": []}},
    }
    result = validate_scraped_data(data, previous_data=None)
    assert result["valid"] is False
    assert any("odevlerim" in e for e in result["errors"])


def test_large_drop_warns():
    prev = {
        "takvim": [{"title": f"E{i}"} for i in range(20)],
    }
    new = {
        "takvim": [{"title": "E1"}],
    }
    result = validate_scraped_data(new, previous_data=prev)
    assert any("takvim" in w for w in result["warnings"])


def test_missing_section_counted():
    data = {}
    result = validate_scraped_data(data, previous_data=None)
    assert result["valid"] is False


def test_section_counts_returned():
    data = {
        "odevlerim": {"homework": {"rows": [
            {"Ders Adı": "M", "Ödev Başlığı": "H"} for _ in range(10)
        ]}},
        "takvim": [{"title": "E1"}, {"title": "E2"}, {"title": "E3"}],
    }
    result = validate_scraped_data(data, previous_data=None)
    assert result["section_counts"]["odevlerim"] == 10
    assert result["section_counts"]["takvim"] == 3


def _profile(**over):
    """A profile shaped exactly as scrape_ogrenci_profili returns it."""
    base = {
        "name": "", "student_no": "", "class_name": "", "branch": "",
        "fields": {}, "photo_data_url": "",
        "profile_url": "https://portal.tedronesans.k12.tr/pages/x",
        "scraped_at": "2026-08-31T00:00:13",
    }
    base.update(over)
    return base


def test_empty_student_profile_is_reported():
    """The portal 404'd the profile page on 2026-08-31 and nothing said so:
    the dict still had its eight keys, so any key-count check called it full.
    The dashboard is about one child; losing their name must not be silent."""
    data = {"ogrenci_profili": _profile()}
    result = validate_scraped_data(data, previous_data=None)

    assert result["section_counts"]["ogrenci_profili"] == 0
    # Critical: it lands in errors, which reddens health, rather than in a
    # warning list that stayed unread while the page 404'd.
    assert any("ogrenci_profili" in e for e in result["errors"])
    assert result["valid"] is False


def test_populated_student_profile_is_quiet():
    data = {"ogrenci_profili": _profile(
        name="Işık Kurt", student_no="1234", class_name="7-A",
        fields={"Doğum Tarihi": "2013"})}
    result = validate_scraped_data(data, previous_data=None)

    assert result["section_counts"]["ogrenci_profili"] > 0
    assert not any("ogrenci_profili" in m
                   for m in result["errors"] + result["warnings"])
