"""Müfredat ağacı okuyucusu ve şeması (spec §2)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import mufredat_agaci as ma  # noqa: E402


def _agac(**ustune):
    """Geçerli bir asgari ağaç; testler tek alanı bozar."""
    taban = {
        "surum": 1, "korpus_surumu": "1.6", "sinif": "7. Sınıf",
        "dersler": [{
            "ders": "Fen Bilimleri", "slug": "fen",
            "program": {"document_id": 54, "sayfa": "146-183"},
            "kitaplar": [{"document_id": 439, "kisa": "1. Kitap",
                          "sayfa_kaymasi": 1, "kayma_uyumu": "21/23"}],
            "uniteler": [{
                "no": 3, "ad": "Vücudumuzdaki Sistemler", "program_sayfa": 156,
                "konular": [{
                    "id": "fen-u3-sindirim-sisteminin-sagligi",
                    "ad": "Sindirim Sisteminin Sağlığı",
                    "ad_kaynak": "SİNDİRİM SİSTEMİNİN SAĞLIĞI",
                    "kitap": 439, "sayfa": [97, 101], "sayfa_kaynak": "icindekiler",
                    "kazanimlar": ["FB.7.3.2"], "kazanim_kaynak": "metin-ortusmesi",
                }],
            }],
        }],
        "kapsam": {"fen": {"konu": 1, "sayfasi_olan": 1, "kazanimi_eslenen": 1}},
    }
    taban.update(ustune)
    return taban


def test_gecerli_agac_hatasiz():
    assert ma.dogrula(_agac()) == []


def test_konular_dersi_uniteyi_ve_konuyu_birlikte_verir():
    ders, unite, konu = next(iter(ma.konular(_agac())))
    assert (ders["slug"], unite["no"], konu["id"]) == ("fen", 3, "fen-u3-sindirim-sisteminin-sagligi")


def test_konu_bul_bilinmeyen_kimlikte_none():
    assert ma.konu_bul(_agac(), "fen-u9-olmayan") is None


# Review Focus 1: geçerli JSON ama şema dışı.
@pytest.mark.parametrize("bozma", [
    {"dersler": {}},
    {"dersler": [{"ders": "Fen", "slug": "fen", "uniteler": {}}]},
    {"surum": "1"},
])
def test_sema_disi_govde_hata_listesi_dondurur(bozma):
    assert ma.dogrula(_agac(**bozma)) != []


def test_sayfa_kaynak_yok_iken_sayfa_alani_varsa_reddedilir():
    agac = _agac()
    konu = agac["dersler"][0]["uniteler"][0]["konular"][0]
    konu["sayfa_kaynak"] = "yok"
    assert "sayfa" in konu  # kurgu hâlâ sayfa taşıyor
    assert ma.dogrula(agac) != []  # bu yasak


def test_bilinmeyen_kazanim_kaynagi_reddedilir():
    agac = _agac()
    agac["dersler"][0]["uniteler"][0]["konular"][0]["kazanim_kaynak"] = "kod-sirasi"
    assert ma.dogrula(agac) != []


def test_oku_eksik_dosyada_yok_der(tmp_path):
    assert ma.oku(tmp_path / "olmayan.json") == ("yok", None)


def test_oku_bozuk_dosyada_bozuk_der(tmp_path):
    yol = tmp_path / "a.json"
    yol.write_text("{ bu json degil", encoding="utf-8")
    assert ma.oku(yol) == ("bozuk", None)


def test_oku_sema_disi_dosyayi_bozuk_sayar(tmp_path):
    yol = tmp_path / "a.json"
    yol.write_text(json.dumps(_agac(dersler={})), encoding="utf-8")
    assert ma.oku(yol)[0] == "bozuk"


def test_oku_gecerli_dosyayi_dondurur(tmp_path):
    yol = tmp_path / "a.json"
    yol.write_text(json.dumps(_agac()), encoding="utf-8")
    durum, agac = ma.oku(yol)
    assert durum == "ok" and agac["dersler"][0]["slug"] == "fen"
