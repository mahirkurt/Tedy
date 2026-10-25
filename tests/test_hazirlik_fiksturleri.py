"""Pano fikstürleri modelden üretilmiş hâliyle aynı olmalı (plan Görev 8): model ya da harita değişince bu test düşer
ve `scripts/hazirlik_fiksturleri.py` yeniden koşulur."""
import json

from scripts.hazirlik_fiksturleri import HEDEF, fiksturler


def test_pano_fiksturleri_guncel():
    beklenen = fiksturler()
    assert sorted(p.stem for p in HEDEF.glob("*.json")) == sorted(beklenen)
    for ad, veri in beklenen.items():
        assert json.loads((HEDEF / f"{ad}.json").read_text(encoding="utf-8")) == json.loads(json.dumps(veri)), ad
