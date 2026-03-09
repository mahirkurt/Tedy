from src.data_validator import validate_scraped_data


def test_valid_data_passes():
    data = {
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
