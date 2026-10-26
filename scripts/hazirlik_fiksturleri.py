"""Pano e2e fikstürleri modelin kendisinden üretilir (plan Görev 8): elle yazılmış, şekli varsayılmış fikstür
yüzeyi boş çizdirir ve testi boşuna geçirir. Girdiler: gerçek senaryo tablosu, gerçek Fen haritası
(src/kitap_haritalari/fen-bilimleri.json), 2026-10-25'e sabitlenmiş örnek sınav kayıtları.

    env -u ANTHROPIC_API_KEY .venv/bin/python -I scripts/hazirlik_fiksturleri.py      # dashboard/tests/e2e/fixtures/hazirlik/*.json
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

from src import sinav_kilavuzu as sk  # noqa: E402
from src.sinav_senaryo import tablo_oku  # noqa: E402

HEDEF = KOK / "dashboard" / "tests" / "e2e" / "fixtures" / "hazirlik"
BUGUN = date(2026, 10, 25)
# Kişisel olmayan örnek ad: depoya gerçek çocuk adı girmez (gerçek API oturumdaki kişinin gösterim adını döner).
ISARET_SAHIBI = "Deneme Öğrenci"
DUYURU = "Sınav, İstanbul İl MEB tarafından belirlenen 2. senaryoya göre uygulanacaktır."


def _kayit(tablo, ders, no, *, durum, senaryo, tarih, status, sid, konular=(), duyuruda=()):
    dt = tablo["dersler"][ders]
    sinav = dt["sinavlar"][str(no)]
    kesin = durum in sk.KESIN_DURUMLAR
    d = sinav.get("senaryolar", {}).get(str(senaryo), {}) if kesin else {}
    dagilim = [{"kod": c["kod"], "metin": c["metin"], "soru": d[c["kod"]], "duyuruda": c["kod"] in duyuruda}
               for c in dt["ciktilar"] if c["kod"] in d]
    blok = {"durum": durum, "ders": ders, "sinav_no": no, "donem": 1, "anilan": [senaryo] if senaryo else [],
            "cumle": DUYURU if kesin else None, "senaryo": senaryo if kesin else None,
            "toplam": sum(d.values()) if d else None, "dagilim": dagilim, "eslesen_konu_sayisi": len(konular),
            "eslesmeyen_konular": [], "senaryo_disi_konular": [], "adaylar": [],
            "senaryo_sayisi": len(sinav.get("senaryolar", {})), "kaynak": tablo["kaynak"]["sayfa"],
            "meb_guncelleme": tablo["kaynak"]["meb_guncelleme"]}
    return {"id": sid, "course": ders, "title": f"{ders} {no}. Yazılı", "date": tarih, "status": status,
            "konular": list(konular), "senaryo": blok}


def fiksturler() -> dict[str, dict]:
    tablo = tablo_oku()
    harita = sk.harita_oku("fen-bilimleri")
    if tablo is None or harita is None:
        raise SystemExit("senaryo tablosu ya da Fen haritası okunamadı")
    fen_konulari = ("Uzay araştırmaları için geliştirilen teknolojileri karşılaştırabilme",
                    "Uzay araştırmalarının yol açabileceği problemleri çözebilme",
                    "Fiziksel anlamda yapılan işin bağlı olduğu faktörlere ilişkin bilimsel çıkarım yapabilme")
    sinavlar = [
        _kayit(tablo, "Fen Bilimleri", 1, durum="dogrulandi", senaryo=2, tarih="2026-11-03", status="upcoming",
               sid="fen11", konular=fen_konulari, duyuruda=("FB.7.1.1", "FB.7.1.3", "FB.7.2.1")),
        _kayit(tablo, "Türkçe", 1, durum="dogrulandi", senaryo=4, tarih="2026-10-22", status="past", sid="tr11"),
        _kayit(tablo, "Türkçe", 2, durum="ulke_geneli", senaryo=None, tarih="2027-01-05", status="upcoming", sid="tr12"),
    ]
    taban = dict(tablo=tablo, haritalar={"fen-bilimleri": harita}, sinavlar=sinavlar, bugun=BUGUN,
                 isaretler={"fen-bilimleri": {"FB.7.2.1": "tekrar"}}, isaret_sahibi=ISARET_SAHIBI)
    g = sk.Girdiler(**taban)
    olasi = sk.Girdiler(**{**taban, "sinavlar": sinavlar[1:]})
    k12 = sk.Girdiler(**{**taban, "kitap_denetimi": {"fen-bilimleri": {"denetlendi": "2026-10-25", "kitaplar": [
        {"pdf_url": harita["kitaplar"][0]["pdf_url"], "sha256": "0" * 64}]}}})
    eksik = json.loads(json.dumps(harita))
    eksik["eslesme"].pop("FB.7.1.3")
    eksik["eslesmedi"] = ["FB.7.1.3"]
    bulunamadi = sk.Girdiler(**{**taban, "haritalar": {"fen-bilimleri": eksik}})
    acik = {"ebeveyn": False, "isaret": True}
    return {
        "genel": sk.genel_bakis(g),
        "fen-bilimleri-1": sk.ders_ozeti(g, "fen-bilimleri", 1),
        "fen-bilimleri-2": sk.ders_ozeti(g, "fen-bilimleri", 2),
        "fen-bilimleri-1-kilavuz": sk.kilavuz(g, "fen-bilimleri", 1, None, acik),
        "fen-bilimleri-1-kilavuz-ebeveyn": sk.kilavuz(g, "fen-bilimleri", 1, None, {"ebeveyn": True, "isaret": True}),
        "fen-bilimleri-1-olasi": sk.ders_ozeti(olasi, "fen-bilimleri", 1),
        "fen-bilimleri-1-olasi-kilavuz": sk.kilavuz(olasi, "fen-bilimleri", 1, None, acik),
        # Duyuru yokken okurun seçtiği 3. senaryo (K8: sayılar "3. senaryoda" diye nitelenir).
        "fen-bilimleri-1-secilen-kilavuz": sk.kilavuz(olasi, "fen-bilimleri", 1, 3, acik),
        "fen-bilimleri-1-k12-kilavuz": sk.kilavuz(k12, "fen-bilimleri", 1, None, acik),
        "fen-bilimleri-1-bulunamadi-kilavuz": sk.kilavuz(bulunamadi, "fen-bilimleri", 1, None, acik),
        "matematik-1": sk.ders_ozeti(g, "matematik", 1),
        "matematik-1-kilavuz": sk.kilavuz(g, "matematik", 1, None, acik),
    }


def yaz(hedef: Path = HEDEF) -> list[Path]:
    hedef.mkdir(parents=True, exist_ok=True)
    yollar = []
    for ad, veri in fiksturler().items():
        yol = hedef / f"{ad}.json"
        yol.write_text(json.dumps(veri, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        yollar.append(yol)
    return yollar


if __name__ == "__main__":
    for y in yaz():
        print(y.relative_to(KOK))
