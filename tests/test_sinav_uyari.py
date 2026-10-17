"""src/sinav_uyari: which alert is due (pure), the wording, the ledger and one
timer round with a fake sender. 2026-10-19 is a Monday."""
import json
from datetime import date, datetime

import pytest

import src.sinav_uyari as su
import src.web_push as wp
from src.sinav_tespiti import SURUM, yaz as sinavlari_yaz

ISIK = "isikkurtx@gmail.com"


def sinav(**kw):
    s = {"id": "s1", "ders": "Matematik", "tur": "konu_tarama", "baslik": "Matematik KTT", "tarih": "2026-10-26",
         "saat": None, "hafta": None, "konular": ["Tam sayılar", "Rasyonel sayılar", "Mutlak değer"],
         "kaynaklar": [], "ilk_tespit": "2026-10-10T09:00:00", "icerik_surumu": "v1", "degisti": None,
         "sentetik": False, "taban": None, "son_yayin": None}
    s.update(kw)
    return s


@pytest.mark.parametrize("simdi,beklenen", [
    (datetime(2026, 10, 19, 17, 59), ["tespit"]),
    (datetime(2026, 10, 19, 18, 0), ["tespit", "gun_7"]),
    (datetime(2026, 10, 24, 18, 5), ["tespit", "gun_7", "gun_2"]),
    (datetime(2026, 10, 25, 19, 0), ["tespit", "gun_7", "gun_2", "aksam"]),
])
def test_vade_hesabi(simdi, beklenen):
    assert su.vadesi_gelen_turler(sinav(), simdi) == beklenen


def test_sessiz_saatte_hicbir_sey_gitmez():
    assert su.vadesi_gelen_turler(sinav(), datetime(2026, 10, 25, 22, 0)) == []
    assert su.vadesi_gelen_turler(sinav(), datetime(2026, 10, 26, 7, 29)) == []
    assert su.vadesi_gelen_turler(sinav(), datetime(2026, 10, 25, 22, 0), sessiz_saat=False) != []


def test_baslamis_sinava_uyari_yok():
    assert su.vadesi_gelen_turler(sinav(saat="09:00"), datetime(2026, 10, 26, 9, 0)) == []
    assert su.vadesi_gelen_turler(sinav(), datetime(2026, 10, 26, 8, 0)) == []        # no time: school starts 08:00
    assert su.vadesi_gelen_turler(sinav(), datetime(2026, 10, 26, 7, 45)) != []


def test_gec_tespitte_eski_hatirlatma_atlanir():
    gec = sinav(ilk_tespit="2026-10-23T10:00:00")
    assert su.vadesi_gelen_turler(gec, datetime(2026, 10, 24, 18, 0)) == ["tespit", "gun_2"]


def test_kurulumda_bulunan_ilk_tespit_bos():
    assert "gun_7" in su.vadesi_gelen_turler(sinav(ilk_tespit=None), datetime(2026, 10, 19, 18, 0))


def test_tarihsiz_ve_sentetik():
    assert su.vadesi_gelen_turler(sinav(tarih=None), datetime(2026, 10, 19, 18, 0)) == ["tespit"]
    assert su.vadesi_gelen_turler(sinav(tarih=None, hafta="2026-10-05"), datetime(2026, 10, 19, 18, 0)) == []
    assert su.vadesi_gelen_turler(sinav(sentetik=True, tarih=None), datetime(2026, 10, 19, 18, 0)) == []


def test_planla_defteri_ve_surumu_dikkate_alir():
    s = sinav()
    simdi = datetime(2026, 10, 24, 18, 5)
    plan = su.planla([s], [ISIK, "anne@x"], {(ISIK, "s1", "tespit", "v1"), (ISIK, "s1", "gun_7", "v1")}, simdi)
    assert [(b.email, b.turler) for b in plan] == [(ISIK, ("gun_2",)), ("anne@x", ("tespit", "gun_7", "gun_2"))]
    yeni = su.planla([sinav(icerik_surumu="v2")], [ISIK], {(ISIK, "s1", "tespit", "v1")}, simdi)
    assert yeni[0].turler == ("tespit", "gun_7", "gun_2")


def test_gun_ifadesi():
    b = date(2026, 10, 19)
    assert [su.gun_ifadesi(date(2026, 10, d), b) for d in (19, 20, 23, 26)] == \
        ["Bugün", "Yarın", "Cuma", "26 Ekim Pazartesi"]


def test_kisa_ad():
    assert su.kisa_ad(sinav()) == "Matematik KTT"
    assert su.kisa_ad(sinav(baslik="Irregular Verbs Quiz", ders="İngilizce")) == "İngilizce Irregular Verbs Quiz"
    assert su.kisa_ad(sinav(baslik="Özdebir GİS · İzleme Sınavı", ders="Genel")) == "Özdebir GİS · İzleme Sınavı"


def test_metin_isik_ve_aile():
    s = sinav(konular=["Tam sayılar", "Rasyonel sayılar", "Mutlak değer", "Oran"])
    baslik, govde = su.metin_kur(s, "ogrenci", ("gun_7",), datetime(2026, 10, 19, 18, 0))
    assert baslik == "Sınav: Matematik KTT · 26 Ekim Pazartesi"
    assert govde == "26 Ekim Pazartesi Matematik KTT var — Tam sayılar, Rasyonel sayılar, Mutlak değer … Bugün 10 dakikayla başla?"
    _, aile = su.metin_kur(s, "aile", ("gun_2",), datetime(2026, 10, 24, 18, 0))
    assert aile == "Işık'ın Pazartesi Matematik KTT sınavı var. Konular: Tam sayılar, Rasyonel sayılar, Mutlak değer …"


def test_metin_aksam_ve_degisti():
    _, govde = su.metin_kur(sinav(), "ogrenci", ("aksam",), datetime(2026, 10, 25, 19, 0))
    assert govde.startswith("Yarın Matematik KTT var") and govde.endswith("Çantanı hazırla, erken uyu.")
    baslik, _ = su.metin_kur(sinav(degisti="2026-10-20T08:00:00"), "aile", ("tespit",), datetime(2026, 10, 20, 8, 5))
    assert baslik.startswith("Sınav güncellendi: Matematik KTT")


def test_kacan_aksam_sabah_bugun_metniyle():
    s = sinav(saat="10:00")
    turler = tuple(su.vadesi_gelen_turler(s, datetime(2026, 10, 26, 7, 30)))
    assert "aksam" in turler
    baslik, govde = su.metin_kur(s, "ogrenci", turler, datetime(2026, 10, 26, 7, 30))
    assert "· Bugün" in baslik and govde.startswith("Bugün Matematik KTT var") and govde.endswith("Başarılar!")


def test_metin_tarihsiz_ve_sinav_sozcugu_tekrarlanmaz():
    _, govde = su.metin_kur(sinav(tarih=None, hafta="2026-10-26", konular=[]), "aile", ("tespit",),
                            datetime(2026, 10, 20, 9, 0))
    assert govde == "Işık'ın Matematik KTT sınavı duyuruldu (26 Ekim haftası)."
    _, govde = su.metin_kur(sinav(baslik="Özdebir GİS · İzleme Sınavı", ders="Genel", konular=[]), "aile",
                            ("gun_7",), datetime(2026, 10, 19, 18, 0))
    assert govde == "Işık'ın 26 Ekim Pazartesi Özdebir GİS · İzleme Sınavı var."


def test_uzun_konular_yuk_siniri():
    s = sinav(baslik="X" * 2000, konular=[f"Konu {i} " + "y" * 200 for i in range(30)])
    baslik, govde = su.metin_kur(s, "ogrenci", ("gun_7",), datetime(2026, 10, 19, 18, 0))
    assert len(baslik) <= 80 and len(govde) <= 300
    assert "X…" in baslik and govde.count("Konu ") == 3 and govde.count("…") >= 4   # ad + 3 konu kesildi
    yuk = json.dumps({"baslik": baslik, "govde": govde, "etiket": "s1", "url": "/sinavlar?sinav=s1"},
                     ensure_ascii=False).encode()
    assert len(yuk) < 4096


def test_defter_anahtarlari(tmp_path):
    d = su.BildirimDefteri(tmp_path / "d.jsonl")
    assert d.anahtarlar() == set()
    d.yaz(ISIK, sinav(), ("tespit", "gun_7"), datetime(2026, 10, 19, 18, 0))
    with (tmp_path / "d.jsonl").open("a", encoding="utf-8") as f:
        f.write("bozuk satır\n")
    assert d.anahtarlar() == {(ISIK, "s1", "tespit", "v1"), (ISIK, "s1", "gun_7", "v1")}


# --- bir tur ---------------------------------------------------------------------

@pytest.fixture
def kok(tmp_path, monkeypatch):
    monkeypatch.setenv("TEDY_SINAV_UYARI", "1")
    monkeypatch.setenv("TEDY_VAPID_PUBLIC", "PUB")
    monkeypatch.setenv("TEDY_VAPID_PRIVATE", "PRIV")
    monkeypatch.setattr(su, "is_full", lambda e: e in (ISIK, "anne@x"))
    monkeypatch.setattr(su, "okur_turu", lambda e: "ogrenci" if e == ISIK else "aile")
    sinavlari_yaz(tmp_path, {"uretildi": "x", "surum": SURUM, "sinavlar": [sinav()], "ozet": {}})
    depo = wp.AbonelikDeposu(tmp_path / wp.ABONELIKLER)
    for email, endpoint in ((ISIK, "https://fcm.googleapis.com/a"), ("anne@x", "https://web.push.apple.com/b"),
                            ("yabanci@x", "https://fcm.googleapis.com/c")):
        depo.ekle(email, {"endpoint": endpoint, "keys": {"p256dh": "p", "auth": "a"}, "cihaz": "T"})
    return tmp_path


class Gonderici:
    def __init__(self, sonuclar=None):
        self.cagrilar, self.sonuclar = [], sonuclar or {}

    def __call__(self, abonelik, yuk, vapid):
        self.cagrilar.append((abonelik["endpoint"], yuk))
        return self.sonuclar.get(abonelik["endpoint"], wp.GonderimSonucu("ok", 201, ""))


def test_tur_gonderir_deftere_yazar_tekrarlamaz(kok):
    g = Gonderici()
    durum = su.gonder_turu(kok, datetime(2026, 10, 19, 18, 0), gonderici=g)
    assert sorted(e for e, _ in g.cagrilar) == ["https://fcm.googleapis.com/a", "https://web.push.apple.com/b"]
    yuk = dict(g.cagrilar)["https://fcm.googleapis.com/a"]
    assert yuk["etiket"] == "s1" and yuk["url"] == "/sinavlar?sinav=s1" and "Bugün 10 dakikayla" in yuk["govde"]
    assert durum["gonderilen"] == 2 and durum["kapali"] is False
    assert json.loads((kok / su.DURUM).read_text(encoding="utf-8"))["gonderilen"] == 2
    g2 = Gonderici()
    su.gonder_turu(kok, datetime(2026, 10, 19, 18, 10), gonderici=g2)
    assert g2.cagrilar == []


def test_bayrak_kapaliyken_gonderim_yok(kok, monkeypatch):
    monkeypatch.setenv("TEDY_SINAV_UYARI", "0")
    g = Gonderici()
    assert su.gonder_turu(kok, datetime(2026, 10, 19, 18, 0), gonderici=g)["kapali"] is True
    assert g.cagrilar == []


def test_olu_abonelik_silinir_hata_tekrar_denenir(kok):
    g = Gonderici({"https://fcm.googleapis.com/a": wp.GonderimSonucu("olu", 410, "gone"),
                   "https://web.push.apple.com/b": wp.GonderimSonucu("hata", 500, "boom")})
    durum = su.gonder_turu(kok, datetime(2026, 10, 19, 18, 0), gonderici=g)
    assert durum["olu_silinen"] == 1 and durum["hatalar"]
    assert wp.AbonelikDeposu(kok / wp.ABONELIKLER).kisinin(ISIK) == []
    assert su.BildirimDefteri(kok / su.DEFTER).anahtarlar() == set()
    g2 = Gonderici()
    su.gonder_turu(kok, datetime(2026, 10, 19, 18, 10), gonderici=g2)
    assert [e for e, _ in g2.cagrilar] == ["https://web.push.apple.com/b"]


def test_kisiyi_tohumla_eski_tespitleri_gondermez(kok):
    assert su.kisiyi_tohumla(kok, ISIK, datetime(2026, 10, 19, 18, 0)) == 2   # tespit + gun_7
    g = Gonderici()
    su.gonder_turu(kok, datetime(2026, 10, 19, 18, 5), gonderici=g)
    assert [e for e, _ in g.cagrilar] == ["https://web.push.apple.com/b"]
    g2 = Gonderici()
    su.gonder_turu(kok, datetime(2026, 10, 24, 18, 0), gonderici=g2)
    assert sorted(e for e, _ in g2.cagrilar) == ["https://fcm.googleapis.com/a", "https://web.push.apple.com/b"]


def test_tohumla_herkesi_isaretler(kok):
    assert su.tohumla(kok, datetime(2026, 10, 19, 23, 0)) == 4   # 2 kişi × (tespit, gun_7); sessiz saat yok sayılır
    g = Gonderici()
    su.gonder_turu(kok, datetime(2026, 10, 20, 9, 0), gonderici=g)
    assert g.cagrilar == []
