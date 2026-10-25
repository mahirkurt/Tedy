"""Pano fikstürleri modelden üretilmiş hâliyle aynı olmalı (plan Görev 8): model ya da harita değişince bu test düşer
ve `scripts/hazirlik_fiksturleri.py` yeniden koşulur."""
import json

from scripts.hazirlik_fiksturleri import HEDEF, fiksturler


def test_pano_fiksturleri_guncel():
    beklenen = fiksturler()
    assert sorted(p.stem for p in HEDEF.glob("*.json")) == sorted(beklenen)
    for ad, veri in beklenen.items():
        assert json.loads((HEDEF / f"{ad}.json").read_text(encoding="utf-8")) == json.loads(json.dumps(veri)), ad


def test_ebeveyn_fiksturunde_isaret_sahibi_dolu():
    """Pano ebeveyn özetinde işaretlerin kime ait olduğunu çizer; fikstür bu yolu boş bırakmamalı."""
    ebeveyn = json.loads((HEDEF / "fen-bilimleri-1-kilavuz-ebeveyn.json").read_text(encoding="utf-8"))
    assert ebeveyn["ebeveyn"]["isaret_sahibi"] == ebeveyn["isaret_sahibi"] == "Deneme Öğrenci"
