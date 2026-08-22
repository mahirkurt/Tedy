"""The portal sometimes explains an absence instead of serving data.

Three flavours: it redirects to an unauthorized page, it prints a
"module closed" banner, or it renders a table's empty state. None of
these is a scrape failure, and none should be reported as one.
"""
import pytest

from src.scrape_all import (
    PortalUnavailable,
    detect_portal_block,
    parse_gelisim_rubrics,
)
from src.data_validator import validate_scraped_data


BASE = "https://portal.tedronesans.k12.tr"


class TestDetectPortalBlock:
    def test_unauthorized_redirect(self):
        block = detect_portal_block(
            f"{BASE}/hata/yetkisiz_giris",
            "Yetkiniz bulunmamaktadır! 🔐 Detaylı bilgi için...",
        )
        assert block is not None
        assert block[0] == "yetkisiz"

    def test_module_closed_banner(self):
        block = detect_portal_block(
            f"{BASE}/pages/ogrenci_istekler/p_haftalik_ders_hazirlik_programim",
            "Portal > Öğrenci İşlemleri\nAkademi Modülü kısa bir süre "
            "erişime kapalıdır.\nV 1.3.7",
        )
        assert block is not None
        assert block[0] == "modul_kapali"

    def test_healthy_page_is_not_blocked(self):
        assert detect_portal_block(
            f"{BASE}/pages/ogrenci_istekler/p_gelisim_raporum",
            "Gelişim Raporları Hakkında ... Beden Eğitimi ve Spor",
        ) is None

    def test_unavailable_carries_reason(self):
        err = PortalUnavailable("yetkisiz", "Akademik Takvim: yetki yok")
        assert err.reason == "yetkisiz"
        assert "Akademik Takvim" in str(err)


RUBRIC_HTML = """
<div class="row">
  <div class="col-md-12 gelisim_raporu_dersler">
    <div class="card mobil_gelisim_raporu_dersler">
      <div class="card-header">Beden Eğitimi ve Spor</div>
      <div class="card-body p-0">
        <table class="table table-striped">
          <tr><td>OYUN VE HÜCUM OYUNLARI</td><td></td></tr>
          <tr><td>Takım oyunlarında strateji uygular.</td>
              <td>Kazanımın Üstünde</td></tr>
          <tr><td>Kurallara uyar.</td><td>Kazanım Düzeyinde</td></tr>
        </table>
      </div>
    </div>
  </div>
  <div class="col-md-12 gelisim_raporu_dersler">
    <div class="card mobil_gelisim_raporu_dersler">
      <div class="card-header">Görsel Sanatlar</div>
      <table class="table table-striped">
        <tr><td>SINIF İÇİ TUTUM</td><td></td></tr>
        <tr><td>Derse ilgilidir.</td><td>Kazanım Düzeyinde</td></tr>
      </table>
    </div>
  </div>
</div>
"""


class TestParseGelisimRubrics:
    def test_captures_course_group_and_level(self):
        rubrics = parse_gelisim_rubrics(RUBRIC_HTML)
        assert rubrics == [
            {"ders": "Beden Eğitimi ve Spor",
             "alan": "OYUN VE HÜCUM OYUNLARI",
             "kazanim": "Takım oyunlarında strateji uygular.",
             "duzey": "Kazanımın Üstünde"},
            {"ders": "Beden Eğitimi ve Spor",
             "alan": "OYUN VE HÜCUM OYUNLARI",
             "kazanim": "Kurallara uyar.",
             "duzey": "Kazanım Düzeyinde"},
            {"ders": "Görsel Sanatlar",
             "alan": "SINIF İÇİ TUTUM",
             "kazanim": "Derse ilgilidir.",
             "duzey": "Kazanım Düzeyinde"},
        ]

    def test_group_header_row_is_not_an_assessment(self):
        assert all(r["duzey"] for r in parse_gelisim_rubrics(RUBRIC_HTML))

    def test_header_row_is_not_an_assessment(self):
        """Club rubrics label their columns with <th> inside the body."""
        html = """
        <div class="card mobil_gelisim_raporu_dersler">
          <div class="card-header">Kulüp</div>
          <table class="table table-bordered">
            <tr><td>Ölçme Değerlendirme: ...</td></tr>
            <tr><th>Beceri Alanı</th><th>Düzey</th></tr>
            <tr><td>Özgünlük ve yaratıcı düşünme</td>
                <td>İlerleme Gösteriyor</td></tr>
          </table>
        </div>
        """
        assert parse_gelisim_rubrics(html) == [{
            "ders": "Kulüp", "alan": "",
            "kazanim": "Özgünlük ve yaratıcı düşünme",
            "duzey": "İlerleme Gösteriyor",
        }]

    def test_page_without_rubrics_yields_nothing(self):
        assert parse_gelisim_rubrics("<div><table><tr><td>x</td></tr>"
                                     "</table></div>") == []


class TestValidatorRespectsExplainedAbsence:
    def _data(self, **over):
        data = {
            "odevlerim": {"homework": {"rows": []}},
            "ders_programi": [],
            "takvim": [],
            "gelisim_raporu": {"grades": [], "rubrics": []},
            "ders_icerikleri": {"a": [1]},
            "takim_calismalari": {"activities": []},
            "ogep": {"sessions": {"rows": []}},
            "duyurular": {"announcements": []},
        }
        data.update(over)
        return data

    def test_unexplained_emptiness_is_still_an_error(self):
        result = validate_scraped_data(self._data(), None)
        assert any("ders_programi" in e for e in result["errors"])

    def test_portal_blocked_section_is_not_an_error(self):
        result = validate_scraped_data(
            self._data(), None,
            unavailable={"ders_programi": {"reason": "modul_kapali",
                                           "detail": "Akademi Modülü kapalı"}},
        )
        assert not any("ders_programi" in e for e in result["errors"])
        assert any("ders_programi" in w and "modul_kapali" in w
                   for w in result["warnings"])

    def test_explicit_empty_state_is_not_an_error(self):
        data = self._data(
            odevlerim={"homework": {"rows": [], "empty_state": True}})
        result = validate_scraped_data(data, None)
        assert not any("odevlerim" in e for e in result["errors"])

    def test_takim_calismalari_counts_rows_not_dict_keys(self):
        """activities is an extract_table result, not a list of activities."""
        from src.data_validator import _count_section
        data = self._data(takim_calismalari={"activities": {
            "headers": ["Academy+", "Çalışma Başlangıç"],
            "rows": [{"Academy+": "Robotik"}, {"Academy+": "Satranç"}],
            "empty_state": False,
        }})
        assert _count_section("takim_calismalari", data) == 2

    def test_takim_calismalari_still_counts_a_plain_list(self):
        from src.data_validator import _count_section
        data = self._data(takim_calismalari={"activities": [{"a": 1}]})
        assert _count_section("takim_calismalari", data) == 1

    def test_rubrics_count_toward_gelisim_raporu(self):
        data = self._data(gelisim_raporu={
            "grades": [],
            "rubrics": [{"ders": "Müzik"}] * 6,
        })
        result = validate_scraped_data(data, None)
        assert result["section_counts"]["gelisim_raporu"] == 6
        assert not any("gelisim_raporu" in e for e in result["errors"])
