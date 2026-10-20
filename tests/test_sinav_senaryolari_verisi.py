"""Repodaki MEB senaryo verisi (spec §2.1, §8): yapı değişmezleri ve 2026-10-19'da ölçülmüş gerçekler."""
import json
import re
from pathlib import Path

VERI = json.loads((Path(__file__).resolve().parents[1] / "src" / "sinav_senaryolari.json").read_text(encoding="utf-8"))
DERSLER = {"Din Kültürü", "Fen Bilimleri", "Matematik", "Türkçe", "Sosyal Bilgiler", "İngilizce"}
# İngilizce çıktıları MEB tablosunda "E7.1.R1" (sınıf rakamı harfe bitişik, beceri harfi + sıra) yazılır; öteki beş ders noktalı.
KOD = re.compile(r"^(?:[A-ZÇĞİÖŞÜ]{1,5}(\.[A-ZÇĞİÖŞÜ]{1,5})*\.7\.\d{1,2}(\.\d{1,2})?|E7\.\d{1,2}\.[A-Z]\d{1,2})$")


def test_kaynak_bilgisi():
    k = VERI["kaynak"]
    assert VERI["surum"] == 1
    assert k["sinif"] == 7 and k["donem"] == 1 and k["ogretim_yili"] == "2026-2027"
    assert k["sayfa"].startswith("https://odsgm.meb.gov.tr/")
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", k["meb_guncelleme"])


def test_alti_ders_kanonik_adla():
    assert set(VERI["dersler"]) == DERSLER


def test_yapi_degismezleri():
    for ad, d in VERI["dersler"].items():
        kodlar = [c["kod"] for c in d["ciktilar"]]
        assert kodlar and len(kodlar) == len(set(kodlar)), ad
        assert all(KOD.match(k) for k in kodlar), (ad, [k for k in kodlar if not KOD.match(k)])
        assert d["sinavlar"], ad
        for no, s in d["sinavlar"].items():
            assert no in ("1", "2")
            if s["tur"] == "ulke_geneli":
                assert "Ülke Geneli" in s["not"]
                continue
            assert s["tur"] == "senaryolu" and s["senaryolar"], (ad, no)
            for sen, dagilim in s["senaryolar"].items():
                assert sum(dagilim.values()) >= 1, (ad, no, sen)
                assert set(dagilim) <= set(kodlar), (ad, no, sen)


def test_olculmus_turkce_dorduncu_senaryo():
    tr = VERI["dersler"]["Türkçe"]
    s4 = tr["sinavlar"]["1"]["senaryolar"]["4"]
    assert sum(s4.values()) == 7
    assert s4 == {"T.O.7.4": 1, "T.O.7.5": 2, "T.O.7.7": 1, "T.O.7.21": 1, "T.Y.7.18": 1, "T.Y.7.21": 1}
    assert len(tr["sinavlar"]["1"]["senaryolar"]) == 6
    assert tr["sinavlar"]["2"]["tur"] == "ulke_geneli"
    metin = {c["kod"]: c["metin"] for c in tr["ciktilar"]}
    assert metin["T.O.7.5"] == "Metnin yüzey anlamını belirleyebilme"


def test_olculmus_fen():
    fen = VERI["dersler"]["Fen Bilimleri"]
    assert len(fen["sinavlar"]["1"]["senaryolar"]) == 5
    assert fen["sinavlar"]["1"]["senaryolar"]["1"]["FB.7.2.1"] == 3
    assert next(c for c in fen["ciktilar"] if c["kod"] == "FB.7.1.1")["konu"] == "Türkiye ve Uzay Araştırmaları"
