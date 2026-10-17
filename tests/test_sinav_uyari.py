"""src/sinav_uyari: which alert is due (pure), the wording, the ledger and one
timer round with a fake sender. 2026-10-19 is a Monday."""
import base64
import json
from datetime import date, datetime

import pytest

import src.sinav_uyari as su
import src.web_push as wp
from src.sinav_tespiti import SURUM, yaz as sinavlari_yaz

ISIK = "isikkurtx@gmail.com"
P256 = base64.urlsafe_b64encode(b"\x04" + b"a" * 64).rstrip(b"=").decode()
AUTH = base64.urlsafe_b64encode(b"b" * 16).rstrip(b"=").decode()
ANAHTAR = {"p256dh": P256, "auth": AUTH}


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
        depo.ekle(email, {"endpoint": endpoint, "keys": ANAHTAR, "cihaz": "T"})
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


# --- kayıt başına yalıtım, durum dosyası, çıkış kodu ----------------------------

def test_bozuk_kayit_turu_durdurmaz(kok):
    sinavlari_yaz(kok, {"uretildi": "x", "surum": SURUM, "ozet": {}, "sinavlar": [
        sinav(id="bozuk", saat="9.30"), sinav(id="bozuk2", tarih="bozuk"), sinav(id="bozuk3", tarih=None, hafta="x"),
        {k: v for k, v in sinav().items() if k != "id"}, sinav()]})
    g = Gonderici()
    durum = su.gonder_turu(kok, datetime(2026, 10, 19, 18, 0), gonderici=g)
    assert sorted(e for e, _ in g.cagrilar) == ["https://fcm.googleapis.com/a", "https://web.push.apple.com/b"]
    assert all(y["etiket"] == "s1" for _, y in g.cagrilar)
    assert durum["gonderilen"] == 2
    metin = " | ".join(durum["hatalar"])
    assert "bozuk:" in metin and "bozuk2:" in metin and "bozuk3:" in metin and "?:" in metin
    assert json.loads((kok / su.DURUM).read_text(encoding="utf-8"))["hatalar"] == durum["hatalar"]


def test_planla_bozuk_kaydi_atlar_ve_bildirir():
    hatalar = []
    plan = su.planla([sinav(id="x", saat="9.30"), sinav()], [ISIK], set(), datetime(2026, 10, 19, 18, 0), hatalar)
    assert [b.sinav["id"] for b in plan] == ["s1"]
    assert len(hatalar) == 1 and hatalar[0].startswith("x: ") and len(hatalar[0]) <= 160
    assert [b.sinav["id"] for b in su.planla([sinav(id="x", saat="9.30"), sinav()], [ISIK], set(),
                                             datetime(2026, 10, 19, 18, 0))] == ["s1"]   # hatalar=None


def test_tohumla_bozuk_kaydi_atlar(kok):
    sinavlari_yaz(kok, {"uretildi": "x", "surum": SURUM, "ozet": {}, "sinavlar": [sinav(id="bozuk", saat="9.30"), sinav()]})
    assert su.tohumla(kok, datetime(2026, 10, 19, 18, 0)) == 4
    assert {a[1] for a in su.BildirimDefteri(kok / su.DEFTER).anahtarlar()} == {"s1"}


def test_bildirim_istisnasi_dongu_surer_ve_durum_yazilir(kok, monkeypatch):
    def patla(self, *a, **k):
        raise OSError("disk dolu")
    monkeypatch.setattr(su.BildirimDefteri, "yaz", patla)
    durum = su.gonder_turu(kok, datetime(2026, 10, 19, 18, 0), gonderici=Gonderici())   # raises nothing
    assert durum["gonderilen"] == 0
    assert any("disk dolu" in h for h in durum["hatalar"])
    kayit = json.loads((kok / su.DURUM).read_text(encoding="utf-8"))
    assert any("disk dolu" in h for h in kayit["hatalar"])


def test_tur_disi_istisna_da_duruma_yazilir(kok, monkeypatch):
    def patla(*a, **k):
        raise RuntimeError("depo bozuk")
    monkeypatch.setattr(su, "_alicilar", patla)
    durum = su.gonder_turu(kok, datetime(2026, 10, 19, 18, 0), gonderici=Gonderici())
    kayit = json.loads((kok / su.DURUM).read_text(encoding="utf-8"))
    assert kayit == durum and any("depo bozuk" in h for h in kayit["hatalar"])


@pytest.mark.parametrize("durum,kod", [
    ({"hatalar": ["sinavlar.json yok"]}, 1),
    ({"hatalar": ["VAPID ayarlı değil"]}, 1),
    ({"hatalar": [], "kapali": True}, 0),
    ({"hatalar": ["500: boom"]}, 0),
    ({"hatalar": []}, 0),
])
def test_main_calismayan_tur_icin_hata_kodu(durum, kod, monkeypatch, capsys):
    import src.env_loader as el
    monkeypatch.setattr(el, "load_env", lambda *a, **k: None)
    monkeypatch.setattr(su, "gonder_turu", lambda kok, simdi, gonderici=None: durum)
    assert su.main(["gonder"]) == kod
    assert json.loads(capsys.readouterr().out) == durum


# --- bozuk abonelik deposu durum dosyasında görünür (son inceleme, Important 3) -------------

def test_bozuk_depo_durumda_hata(kok):
    (kok / wp.ABONELIKLER).write_text("{bozuk", encoding="utf-8")
    durum = su.gonder_turu(kok, datetime(2026, 10, 19, 18, 0), gonderici=Gonderici())
    assert durum["abone_kisi"] == 0
    assert any("abonelik deposu okunamadı" in h for h in durum["hatalar"])
    assert any("abonelik deposu okunamadı" in h
               for h in json.loads((kok / su.DURUM).read_text(encoding="utf-8"))["hatalar"])


def test_yakinda_kenara_alinan_depo_durumda_hata(kok):
    (kok / "output/bildirim_abonelikleri.json.bozuk-20261019093000").write_text("{bozuk", encoding="utf-8")
    durum = su.gonder_turu(kok, datetime(2026, 10, 19, 18, 0), gonderici=Gonderici())
    assert durum["gonderilen"] == 2          # the round itself still runs
    assert any("kenara alındı" in h and "19.10 09:30" in h for h in durum["hatalar"])
    # A day later the old backup no longer reads as news.
    durum = su.gonder_turu(kok, datetime(2026, 10, 20, 18, 0), gonderici=Gonderici())
    assert not any("kenara alındı" in h for h in durum["hatalar"])


# --- temizlik B: gönderim yalıtımı, bekleyen kuyruk, hatalar, çıkış kodu ------------------

ISIK_2 = "https://web.push.apple.com/isik-ipad"


def _ikinci_cihaz(kok, email=ISIK, endpoint=ISIK_2):
    wp.AbonelikDeposu(kok / wp.ABONELIKLER).ekle(email, {"endpoint": endpoint, "keys": ANAHTAR, "cihaz": "iPad"})


def _bekleyen(kok):
    try:
        return json.loads((kok / su.BEKLEYEN).read_text(encoding="utf-8"))["kayitlar"]
    except FileNotFoundError:
        return []


class Patlayan(Gonderici):
    def __init__(self, patlayanlar, sonuclar=None):
        super().__init__(sonuclar)
        self.patlayanlar = set(patlayanlar)

    def __call__(self, abonelik, yuk, vapid):
        if abonelik["endpoint"] in self.patlayanlar:
            self.cagrilar.append((abonelik["endpoint"], yuk))
            raise RuntimeError("bağlantı koptu")
        return super().__call__(abonelik, yuk, vapid)


def test_b8_gonderici_istisnasi_cihaz_hatasi_sayilir_dongu_surer(kok):
    _ikinci_cihaz(kok)
    g = Patlayan({"https://fcm.googleapis.com/a"})
    durum = su.gonder_turu(kok, datetime(2026, 10, 19, 18, 0), gonderici=g)
    assert sorted(e for e, _ in g.cagrilar) == ["https://fcm.googleapis.com/a", "https://web.push.apple.com/b",
                                                ISIK_2]
    assert durum["gonderilen"] == 2                          # Işık (via the iPad) and anne
    assert any("bağlantı koptu" in h for h in durum["hatalar"])
    g2 = Gonderici()
    su.gonder_turu(kok, datetime(2026, 10, 19, 18, 10), gonderici=g2)
    assert [e for e, _ in g2.cagrilar] == ["https://fcm.googleapis.com/a"]   # only the failed device


def test_b9_kismi_hata_defter_ve_bekleyen_kayit(kok):
    _ikinci_cihaz(kok)
    g = Gonderici({"https://fcm.googleapis.com/a": wp.GonderimSonucu("hata", 503, "geçici")})
    durum = su.gonder_turu(kok, datetime(2026, 10, 19, 18, 0), gonderici=g)
    assert (ISIK, "s1", "tespit", "v1") in su.BildirimDefteri(kok / su.DEFTER).anahtarlar()
    assert _bekleyen(kok) == [{"email": ISIK, "endpoint": "https://fcm.googleapis.com/a", "sinav_id": "s1",
                               "turler": ["tespit", "gun_7"], "icerik_surumu": "v1", "deneme": 1}]
    assert durum["bekleyen"] == 1


def test_b9_bekleyen_yalniz_o_cihaza_ayni_uyariyla_denenir_basarida_silinir(kok):
    _ikinci_cihaz(kok)
    su.gonder_turu(kok, datetime(2026, 10, 19, 18, 0), gonderici=Gonderici(
        {"https://fcm.googleapis.com/a": wp.GonderimSonucu("hata", 503, "geçici")}))
    g = Gonderici()
    durum = su.gonder_turu(kok, datetime(2026, 10, 19, 18, 10), gonderici=g)
    [(endpoint, yuk)] = g.cagrilar
    assert endpoint == "https://fcm.googleapis.com/a"
    assert yuk["etiket"] == "s1" and yuk["url"] == "/sinavlar?sinav=s1"
    assert "Bugün 10 dakikayla" in yuk["govde"]
    assert _bekleyen(kok) == [] and durum["bekleyen_gonderilen"] == 1 and durum["bekleyen"] == 0
    g3 = Gonderici()
    su.gonder_turu(kok, datetime(2026, 10, 19, 18, 20), gonderici=g3)
    assert g3.cagrilar == []


def test_b9_alti_denemede_silinir(kok):
    _ikinci_cihaz(kok)
    hep_hata = {"https://fcm.googleapis.com/a": wp.GonderimSonucu("hata", 503, "geçici")}
    su.gonder_turu(kok, datetime(2026, 10, 19, 18, 0), gonderici=Gonderici(hep_hata))
    denemeler = []
    for dk in range(10, 70, 10):
        g = Gonderici(hep_hata)
        su.gonder_turu(kok, datetime(2026, 10, 19, 18, dk) if dk < 60 else datetime(2026, 10, 19, 19, 0),
                       gonderici=g)
        denemeler.append(len(g.cagrilar))
    assert denemeler == [1, 1, 1, 1, 1, 0]                   # 1 first try + 5 retries = 6 attempts
    assert _bekleyen(kok) == []


def test_b9_cihaz_olunce_silinir(kok):
    _ikinci_cihaz(kok)
    su.gonder_turu(kok, datetime(2026, 10, 19, 18, 0), gonderici=Gonderici(
        {"https://fcm.googleapis.com/a": wp.GonderimSonucu("hata", 503, "geçici")}))
    durum = su.gonder_turu(kok, datetime(2026, 10, 19, 18, 10), gonderici=Gonderici(
        {"https://fcm.googleapis.com/a": wp.GonderimSonucu("olu", 410, "gone")}))
    assert _bekleyen(kok) == [] and durum["olu_silinen"] == 1
    assert [c["abonelik"]["endpoint"] for c in wp.AbonelikDeposu(kok / wp.ABONELIKLER).kisinin(ISIK)] == [ISIK_2]


def test_b9_sessiz_saatte_beklenir_sinav_baslayinca_silinir(kok):
    _ikinci_cihaz(kok)
    su.gonder_turu(kok, datetime(2026, 10, 19, 18, 0), gonderici=Gonderici(
        {"https://fcm.googleapis.com/a": wp.GonderimSonucu("hata", 503, "geçici")}))
    g = Gonderici()
    su.gonder_turu(kok, datetime(2026, 10, 19, 23, 0), gonderici=g)
    assert g.cagrilar == [] and _bekleyen(kok)[0]["deneme"] == 1          # quiet: kept, not counted
    g = Gonderici()
    su.gonder_turu(kok, datetime(2026, 10, 26, 8, 5), gonderici=g)       # the exam began at 08:00
    assert g.cagrilar == [] and _bekleyen(kok) == []


def test_b9_cihaz_depodan_kalkinca_ya_da_surum_degisince_silinir(kok):
    _ikinci_cihaz(kok)
    hata = {"https://fcm.googleapis.com/a": wp.GonderimSonucu("hata", 503, "geçici")}
    su.gonder_turu(kok, datetime(2026, 10, 19, 18, 0), gonderici=Gonderici(hata))
    wp.AbonelikDeposu(kok / wp.ABONELIKLER).sil(ISIK, "https://fcm.googleapis.com/a")
    g = Gonderici()
    su.gonder_turu(kok, datetime(2026, 10, 19, 18, 10), gonderici=g)
    assert g.cagrilar == [] and _bekleyen(kok) == []


def test_b9_surum_degisince_bekleyen_duser(kok):
    _ikinci_cihaz(kok)
    su.gonder_turu(kok, datetime(2026, 10, 19, 18, 0), gonderici=Gonderici(
        {"https://fcm.googleapis.com/a": wp.GonderimSonucu("hata", 503, "geçici")}))
    sinavlari_yaz(kok, {"uretildi": "x", "surum": SURUM, "ozet": {}, "sinavlar": [sinav(icerik_surumu="v2")]})
    g = Gonderici()
    su.gonder_turu(kok, datetime(2026, 10, 19, 18, 10), gonderici=g)
    assert _bekleyen(kok) == []
    assert all(y["etiket"] == "s1" for _, y in g.cagrilar)             # v2 goes to everyone as a new version
    assert len(g.cagrilar) == 3


def test_b9_bekleyen_yazilamazsa_olumcul_cikis_1(kok, monkeypatch, capsys):
    _ikinci_cihaz(kok)

    def patla(self, *a, **k):
        raise OSError("disk dolu")
    monkeypatch.setattr(su.BekleyenKuyruk, "_yaz", patla)
    durum = su.gonder_turu(kok, datetime(2026, 10, 19, 18, 0), gonderici=Gonderici(
        {"https://fcm.googleapis.com/a": wp.GonderimSonucu("hata", 503, "geçici")}))
    assert durum["olumcul"] is True
    assert any("bekleyen" in h and "disk dolu" in h for h in durum["hatalar"])
    import src.env_loader as el
    monkeypatch.setattr(el, "load_env", lambda *a, **k: None)
    monkeypatch.setattr(su, "gonder_turu", lambda kok, simdi, gonderici=None: durum)
    assert su.main(["gonder"]) == 1


def test_b5_tur_gecersiz_kayitli_ucu_gondermez_siler(kok):
    import src.web_push as _wp
    yol = kok / _wp.ABONELIKLER
    veri = json.loads(yol.read_text(encoding="utf-8"))
    veri["kisiler"][ISIK].append({"abonelik": {"endpoint": "https://evil.example/x", "keys": ANAHTAR},
                                  "cihaz": "?", "eklendi": "2026-10-01T00:00:00"})
    yol.write_text(json.dumps(veri), encoding="utf-8")
    g = Gonderici()
    durum = su.gonder_turu(kok, datetime(2026, 10, 19, 18, 0), gonderici=g)
    assert "https://evil.example/x" not in [e for e, _ in g.cagrilar]
    assert durum["gecersiz_silinen"] == 1 and durum["gonderilen"] == 2
    assert "https://evil.example/x" not in [c["abonelik"]["endpoint"] for c in
                                            wp.AbonelikDeposu(yol).kisinin(ISIK)]


def test_b10_olumcul_once_bes_benzersiz_ve_toplam(kok, monkeypatch):
    def planla(sinavlar, alicilar, gonderilmis, simdi, hatalar=None):
        hatalar.extend(["x: bozuk"] * 4 + [f"k{i}: bozuk" for i in range(6)])
        raise RuntimeError("beklenmedik")
    monkeypatch.setattr(su, "planla", planla)
    durum = su.gonder_turu(kok, datetime(2026, 10, 19, 18, 0), gonderici=Gonderici())
    assert durum["hatalar"][0].startswith("tur: RuntimeError: beklenmedik")
    assert len(durum["hatalar"]) == 5 and len(set(durum["hatalar"])) == 5
    assert durum["hatalar"][1] == "x: bozuk"
    assert durum["hata_sayisi"] == 11 and durum["olumcul"] is True


@pytest.mark.parametrize("ortam,mesaj", [("belge", su.KOK_SINAVLAR_YOK), ("vapid", su.KOK_VAPID_YOK)])
def test_b10_b13_belge_ya_da_vapid_yok_olumcul(kok, monkeypatch, ortam, mesaj):
    if ortam == "belge":
        (kok / "output/sinavlar.json").unlink()
    else:
        monkeypatch.delenv("TEDY_VAPID_PRIVATE")
    (kok / wp.ABONELIKLER).write_text("{bozuk", encoding="utf-8")      # a non-fatal error must not lead
    g = Gonderici()
    durum = su.gonder_turu(kok, datetime(2026, 10, 19, 18, 0), gonderici=g)
    assert g.cagrilar == [] and durum["hatalar"][0] == mesaj and durum["olumcul"] is True
    assert json.loads((kok / su.DURUM).read_text(encoding="utf-8"))["hatalar"][0] == mesaj


def test_b11_tur_istisnasi_cikis_1(kok, monkeypatch, capsys):
    monkeypatch.setattr(su, "_alicilar", lambda depo: (_ for _ in ()).throw(RuntimeError("depo bozuk")))
    import src.env_loader as el
    monkeypatch.setattr(el, "load_env", lambda *a, **k: None)
    monkeypatch.setattr(su, "gonder_turu", lambda k, simdi, gonderici=None, _g=su.gonder_turu: _g(kok, simdi, Gonderici()))
    assert su.main(["gonder"]) == 1
    assert json.loads(capsys.readouterr().out)["olumcul"] is True


def test_b11_siradan_cihaz_hatasi_cikis_0(kok, monkeypatch, capsys):
    import src.env_loader as el
    monkeypatch.setattr(el, "load_env", lambda *a, **k: None)
    g = Gonderici({"https://web.push.apple.com/b": wp.GonderimSonucu("hata", 500, "boom")})
    monkeypatch.setattr(su, "gonder_turu", lambda k, simdi, gonderici=None, _g=su.gonder_turu: _g(kok, simdi, g))
    assert su.main(["gonder"]) == 0


def test_b13_tur_sessiz_saatte_gondermez_durum_yazar(kok):
    g = Gonderici()
    durum = su.gonder_turu(kok, datetime(2026, 10, 19, 23, 0), gonderici=g)
    assert g.cagrilar == [] and durum["gonderilen"] == 0
    assert json.loads((kok / su.DURUM).read_text(encoding="utf-8"))["son_tur"] == "2026-10-19T23:00:00"
    assert su.BildirimDefteri(kok / su.DEFTER).anahtarlar() == set()


def test_b13_kacan_aksam_defterle_yalniz_aksam_vadeliyken(kok):
    """Exam Monday 26th; tespit, gun_7 and gun_2 already sent. Sunday's 19:00 reminder was missed
    (machine off); Monday 07:40 the round sends it with today's wording, once."""
    defter = su.BildirimDefteri(kok / su.DEFTER)
    for tur in ("tespit", "gun_7", "gun_2"):
        defter.yaz(ISIK, sinav(), (tur,), datetime(2026, 10, 24, 18, 0))
    plan = su.planla([sinav()], [ISIK], defter.anahtarlar(), datetime(2026, 10, 25, 18, 59))
    assert plan == []                                                    # not due yet: no text at all
    [b] = su.planla([sinav()], [ISIK], defter.anahtarlar(), datetime(2026, 10, 26, 7, 40))
    assert b.turler == ("aksam",)
    baslik, govde = su.metin_kur(b.sinav, "ogrenci", b.turler, datetime(2026, 10, 26, 7, 40))
    assert "Bugün" in baslik and "Başarılar" in govde
    defter.yaz(ISIK, sinav(), b.turler, datetime(2026, 10, 26, 7, 40))
    assert su.planla([sinav()], [ISIK], defter.anahtarlar(), datetime(2026, 10, 26, 7, 50)) == []


def test_b13_bu_haftaki_hafta_yalniz_sinav(kok):
    hafta = sinav(id="h1", tarih=None, hafta="2026-10-19", icerik_surumu="h")
    sinavlari_yaz(kok, {"uretildi": "x", "surum": SURUM, "ozet": {}, "sinavlar": [hafta]})
    g = Gonderici()
    su.gonder_turu(kok, datetime(2026, 10, 21, 9, 0), gonderici=g)
    [yuk] = [y for e, y in g.cagrilar if e == "https://fcm.googleapis.com/a"]
    assert yuk["baslik"].startswith("Yeni sınav:") and "19 Ekim haftası" in yuk["govde"]
    g2 = Gonderici()
    su.gonder_turu(kok, datetime(2026, 10, 26, 9, 0), gonderici=g2)       # the week is over
    assert g2.cagrilar == []


# --- B12: birim dosyaları ------------------------------------------------------------

def _birim(ad):
    from pathlib import Path
    satirlar = (Path(__file__).resolve().parents[1] / ad).read_text(encoding="utf-8").splitlines()
    return [s.strip() for s in satirlar if s.strip() and not s.strip().startswith("#")]


def test_b12_servis_birimi():
    birim = _birim("tedy-sinav-uyari.service")
    assert "Type=oneshot" in birim
    assert "Environment=TZ=Europe/Istanbul" in birim
    assert "TimeoutStartSec=600" in birim
    [calistir] = [s for s in birim if s.startswith("ExecStart=")]
    assert calistir.endswith(" -m src.sinav_uyari gonder") and "/.venv/bin/python" in calistir


def test_b12_zamanlayici_on_dakikada_bir():
    assert "OnCalendar=*:0/10" in _birim("tedy-sinav-uyari.timer")


# --- temizlik B düzeltme 1 -------------------------------------------------------------------

def test_d1_olu_cihaz_silinemezse_basarili_cihaz_tekrar_almaz(kok, monkeypatch):
    _ikinci_cihaz(kok)

    def patla(self, endpoint):
        raise OSError("salt okunur")
    monkeypatch.setattr(wp.AbonelikDeposu, "endpoint_sil", patla)
    olu = {"https://fcm.googleapis.com/a": wp.GonderimSonucu("olu", 410, "gone")}
    g = Gonderici(olu)
    durum = su.gonder_turu(kok, datetime(2026, 10, 19, 18, 0), gonderici=g)
    assert (ISIK, "s1", "tespit", "v1") in su.BildirimDefteri(kok / su.DEFTER).anahtarlar()
    assert durum["olumcul"] is True and any("salt okunur" in h for h in durum["hatalar"])
    g2 = Gonderici(olu)
    su.gonder_turu(kok, datetime(2026, 10, 19, 18, 10), gonderici=g2)
    assert [e for e, _ in g.cagrilar + g2.cagrilar].count(ISIK_2) == 1


def test_d1_bekleyen_ve_yeni_plan_ayni_turda_tek_bildirim(kok):
    _ikinci_cihaz(kok)
    su.gonder_turu(kok, datetime(2026, 10, 24, 17, 50), gonderici=Gonderici(
        {"https://fcm.googleapis.com/a": wp.GonderimSonucu("hata", 503, "geçici")}))
    assert _bekleyen(kok)[0]["turler"] == ["tespit", "gun_7"]
    g = Gonderici()
    su.gonder_turu(kok, datetime(2026, 10, 24, 18, 0), gonderici=g)      # gun_2 falls due now
    assert [e for e, _ in g.cagrilar].count("https://fcm.googleapis.com/a") == 1
    assert _bekleyen(kok) == []


def test_d1_yeni_plan_cihaza_ulasmazsa_yeniden_kuyruga_girer(kok):
    _ikinci_cihaz(kok)
    hata = {"https://fcm.googleapis.com/a": wp.GonderimSonucu("hata", 503, "geçici")}
    su.gonder_turu(kok, datetime(2026, 10, 24, 17, 50), gonderici=Gonderici(hata))
    su.gonder_turu(kok, datetime(2026, 10, 24, 18, 0), gonderici=Gonderici(hata))
    [k] = _bekleyen(kok)
    assert (k["turler"], k["deneme"]) == (["gun_2"], 1)                 # the newer alert, a fresh budget


def test_d1_bekleyen_istisnasinda_kayit_kalir_deneme_artar(kok, monkeypatch):
    _ikinci_cihaz(kok)
    su.gonder_turu(kok, datetime(2026, 10, 19, 18, 0), gonderici=Gonderici(
        {"https://fcm.googleapis.com/a": wp.GonderimSonucu("hata", 503, "geçici")}))
    monkeypatch.setattr(su, "vadesi_gelen_turler", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("bozuk")))
    durum = su.gonder_turu(kok, datetime(2026, 10, 19, 18, 10), gonderici=Gonderici())
    [k] = _bekleyen(kok)
    assert k["deneme"] == 2 and any("bekleyen s1" in h for h in durum["hatalar"])


def test_d1_kuyruk_birlesmesi_yeni_turleri_ve_taze_butceyi_alir(tmp_path):
    kuyruk = su.BekleyenKuyruk(tmp_path / "b.json")
    temel = {"email": ISIK, "endpoint": "https://fcm.googleapis.com/a", "sinav_id": "s1", "icerik_surumu": "v1"}
    kuyruk.ekle([{**temel, "turler": ["tespit", "gun_7"], "deneme": 1}])
    kayitlar = kuyruk.oku()
    kayitlar[0]["deneme"] = 4
    kuyruk._yaz(kayitlar)
    kuyruk.ekle([{**temel, "turler": ["gun_2"], "deneme": 1}])
    assert kuyruk.oku() == [{**temel, "turler": ["gun_2"], "deneme": 1}]
