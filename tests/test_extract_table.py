"""extract_table must not mistake a DataTables empty-state row for data.

When a portal table has no records, DataTables renders a single spanning
cell ("Tabloda herhangi bir veri mevcut değil") instead of a data row.
Emitting that as a row gives every downstream consumer an object whose
real fields are all missing.
"""
from src.scrape_all import extract_table


class FakeCell:
    def __init__(self, text, colspan=None):
        self.text = text
        self._colspan = colspan

    def get_attribute(self, name):
        return self._colspan if name == "colspan" else None


class FakeRow:
    def __init__(self, cells):
        self._cells = cells

    def find_elements(self, _by, tag):
        return self._cells if tag == "td" else []


class FakeTable:
    def __init__(self, headers, rows):
        self._headers = [FakeCell(h) for h in headers]
        self._rows = rows

    def find_elements(self, _by, tag):
        if tag == "th":
            return self._headers
        if tag == "tr":
            return self._rows
        return []


OGEP_HEADERS = [
    "ÖGEP (Öğrenci Gelişim Programı)",
    "Çalışma Başlangıç",
    "Çalışma Bitiş",
    "Katılım Durumu",
]
EMPTY_TEXT = "Tabloda herhangi bir veri mevcut değil"


def test_empty_state_row_is_dropped():
    table = FakeTable(
        OGEP_HEADERS,
        [FakeRow([FakeCell(EMPTY_TEXT, colspan="4")])],
    )
    assert extract_table(None, table)["rows"] == []


def test_empty_state_row_without_colspan_attribute_is_dropped():
    """Some renderings omit colspan; a lone cell under many headers is
    still a spanning row, never a record."""
    table = FakeTable(OGEP_HEADERS, [FakeRow([FakeCell(EMPTY_TEXT)])])
    assert extract_table(None, table)["rows"] == []


def test_real_rows_survive():
    table = FakeTable(OGEP_HEADERS, [FakeRow([
        FakeCell("Matematik Etüt"),
        FakeCell("15.09.2026 14:00"),
        FakeCell("15.09.2026 15:00"),
        FakeCell("Katıldı"),
    ])])
    assert extract_table(None, table)["rows"] == [{
        "ÖGEP (Öğrenci Gelişim Programı)": "Matematik Etüt",
        "Çalışma Başlangıç": "15.09.2026 14:00",
        "Çalışma Bitiş": "15.09.2026 15:00",
        "Katılım Durumu": "Katıldı",
    }]


def test_single_column_table_keeps_its_rows():
    """A genuinely one-column table must not be mistaken for an empty state."""
    table = FakeTable(["Duyuru"], [FakeRow([FakeCell("Veli toplantısı")])])
    assert extract_table(None, table)["rows"] == [{"Duyuru": "Veli toplantısı"}]


def test_headerless_table_drops_spanning_row():
    table = FakeTable([], [FakeRow([FakeCell(EMPTY_TEXT, colspan="3")])])
    assert extract_table(None, table)["rows"] == []
