"""src/aksam_bildirim: vadesi gelen olaylar (saf), defter, alıcılar ve bir tur; sahte gönderici, sabit saat.
2026-10-19 bir Pazartesi."""
import base64
import json
import re
from datetime import datetime

import pytest

import src.aksam_bildirim as ab
import src.web_push as wp
from src.aksam_duzeni import VARSAYILAN
from src.aksam_plani import Blok, Plan, PlanDeposu

ISIK = "isikkurtx@gmail.com"
ANNE = "anne@x"
BABA = "baba@x"
P256 = base64.urlsafe_b64encode(b"\x04" + b"a" * 64).rstrip(b"=").decode()
AUTH = base64.urlsafe_b64encode(b"b" * 16).rstrip(b"=").decode()
ANAHTAR = {"p256dh": P256, "auth": AUTH}
GUN = "2026-10-19"


def an(saat, dakika):
    return datetime(2026, 10, 19, saat, dakika)


def blok(id_, bas, bit, durum="bekliyor", ders="Fen", dk=20, adim="ilk 2 soru"):
    return Blok(id_, "calisma", bas, bit, "k-" + id_, ders, "Konu testi", adim, 0, 1, dk, "orta", durum)


def plan(bloklar, durum="akis", sigmayan=None):
    return Plan(GUN, bloklar, [], sigmayan or [], 0, durum)


def duzen(**kw):
    return {**VARSAYILAN, "haber_alacaklar": [ANNE, BABA], **kw}


def turler(olaylar):
    return sorted(o.tur for o in olaylar)


# ---------------------------------------------------------------- saf: olaylar

def test_baslamadi_esikten_once_yok_sonra_var():
    p = plan([blok("a", 17 * 60, 17 * 60 + 20)])
    assert ab.olaylar(p, {}, duzen(), an(17, 14)) == []
    (o,) = ab.olaylar(p, {}, duzen(), an(17, 15))
    assert (o.tur, o.alici, o.blok_id) == ("baslamadi", "aile", None)
    assert o.baslik == "Işık henüz başlamadı"
    assert o.govde == "Saat 17:15; bu akşamın ilk işi Fen."


def test_baslamadi_baslayan_varsa_yok():
    p = plan([blok("a", 17 * 60, 17 * 60 + 20, "suruyor")])
    assert "baslamadi" not in turler(ab.olaylar(p, {}, duzen(), an(17, 16)))


def test_sure_doldu_ve_takildi():
    p = plan([blok("a", 17 * 60, 17 * 60 + 20, "suruyor")])
    g = {"a": {"durum": "suruyor", "basla": "17:00"}}
    assert ab.olaylar(p, g, duzen(), an(17, 19)) == []
    (o,) = ab.olaylar(p, g, duzen(), an(17, 20))
    assert (o.tur, o.alici, o.blok_id, o.baslik) == ("sure_doldu", "ogrenci", "a", "Süre doldu")
    assert o.govde == "Fen için tahmin ettiğin süre bitti. Bitti mi, biraz daha mı?"
    o35 = ab.olaylar(p, g, duzen(), an(17, 35))
    assert turler(o35) == ["sure_doldu"]
    (t,) = [o for o in ab.olaylar(p, g, duzen(), an(17, 36)) if o.tur == "takildi"]
    assert t.alici == "aile" and t.baslik == "Fen bloğu uzadı"
    assert t.govde == "Başlayalı 36 dakika oldu, henüz bitti işaretlenmedi."


def test_mola_bitti_kisa_ve_uzun():
    a = blok("a", 17 * 60, 17 * 60 + 20, "bitti")
    b = blok("b", 17 * 60 + 25, 17 * 60 + 45, ders="Matematik", adim="3 soru")
    p = plan([a, b])
    g = {"a": {"durum": "bitti", "basla": "17:00", "bitti": "17:20"}}
    assert ab.olaylar(p, g, duzen(), an(17, 24)) == []
    (o,) = ab.olaylar(p, g, duzen(), an(17, 25))
    assert (o.tur, o.alici, o.blok_id, o.baslik) == ("mola_bitti", "ogrenci", "a", "Mola bitti")
    assert o.govde == "Sırada Matematik: 3 soru."
    # iki blok bitmişse mola 10 dk
    a2 = blok("a2", 17 * 60 + 25, 17 * 60 + 45, "bitti")
    p2 = plan([a, a2, blok("c", 17 * 60 + 55, 18 * 60 + 15, ders="Türkçe", adim="paragraf")])
    g2 = {"a": {"bitti": "17:20"}, "a2": {"bitti": "17:45"}}
    assert ab.olaylar(p2, g2, duzen(), an(17, 54)) == []
    assert turler(ab.olaylar(p2, g2, duzen(), an(17, 55))) == ["mola_bitti"]


def test_mola_bitti_sonraki_basladiysa_yok():
    a = blok("a", 17 * 60, 17 * 60 + 20, "bitti")
    b = blok("b", 17 * 60 + 25, 17 * 60 + 45, "suruyor")
    g = {"a": {"bitti": "17:20"}, "b": {"basla": "17:26"}}
    assert "mola_bitti" not in turler(ab.olaylar(plan([a, b]), g, duzen(), an(17, 30)))


def test_mola_bitti_planin_siradaki_baslangicinda_yemekte_gitmez():
    """R28 I1: mola, planın sıradaki iş için verdiği başlangıçta biter. 18:28'de biten bloktan sonra yemek
    18:30–19:00; sıradaki 19:00'da. Eskiden "bitiş + 5 dk" 18:33'te yemeğin ortasında gidiyordu."""
    a = blok("a", 18 * 60 + 8, 18 * 60 + 28, "bitti")
    yemek = Blok("y", "yemek", 18 * 60 + 30, 19 * 60, baslik="Yemek")
    b = blok("b", 19 * 60, 19 * 60 + 20, ders="Matematik", adim="3 soru")
    p = plan([a, yemek, b])
    g = {"a": {"durum": "bitti", "basla": "18:08", "bitti": "18:28"}}
    for dakika in (28, 33, 45, 59):
        assert ab.olaylar(p, g, duzen(), an(18, dakika)) == [], dakika
    assert turler(ab.olaylar(p, g, duzen(), an(19, 0))) == ["mola_bitti"]


def test_baslamadi_esigi_ozel_dersten_sonra():
    """R28 C1: 17:00–18:00 özel ders hazır saatini kaplar; "başlamadı" eşiği 18:15 (kartla aynı)."""
    ders = Blok("o", "olay", 17 * 60, 18 * 60, baslik="Özel ders")
    p = plan([ders, blok("a", 18 * 60, 18 * 60 + 20)])
    assert ab.olaylar(p, {}, duzen(), an(17, 15)) == []
    assert ab.olaylar(p, {}, duzen(), an(18, 14)) == []
    assert turler(ab.olaylar(p, {}, duzen(), an(18, 15))) == ["baslamadi"]


def test_sigmiyor():
    p = plan([blok("a", 17 * 60, 17 * 60 + 20, "suruyor")],
             sigmayan=[{"ders": "Türkçe", "baslik": "Kompozisyon", "kalan_dk": 40}])
    (o,) = [o for o in ab.olaylar(p, {"a": {"basla": "17:00"}}, duzen(), an(17, 5)) if o.tur == "sigmiyor"]
    assert o.alici == "aile" and o.baslik == "Bu akşama sığmıyor"
    assert o.govde == "Türkçe: Kompozisyon yarın teslim; plana sığmadı."


def test_sessiz_saatte_olay_yok():
    p = plan([blok("a", 17 * 60, 17 * 60 + 20)], sigmayan=[{"ders": "T", "baslik": "x"}])
    assert ab.olaylar(p, {}, duzen(), an(21, 5)) == []
    assert ab.olaylar(p, {}, duzen(), an(21, 0)) == []
    assert ab.olaylar(p, {}, duzen(), an(7, 29)) == []


def test_aksam_yok_ve_kapali_okulsuz():
    p = plan([blok("a", 17 * 60, 17 * 60 + 20)])
    assert ab.olaylar(p, {"aksam_yok": True}, duzen(), an(17, 30)) == []
    assert ab.olaylar(plan([], "kapali"), {}, duzen(), an(17, 30)) == []
    assert ab.olaylar(plan([], "okulsuz"), {}, duzen(), an(17, 30)) == []


def test_kopya_alarm_dili_yok():
    p = plan([blok("a", 17 * 60, 17 * 60 + 20, "suruyor"), blok("b", 17 * 60 + 25, 17 * 60 + 45)],
             sigmayan=[{"ders": "Türkçe", "baslik": "Kompozisyon"}])
    g = {"a": {"basla": "17:00"}}
    tum = ab.olaylar(p, g, duzen(), an(17, 40))
    tum += ab.olaylar(plan([blok("a", 17 * 60, 17 * 60 + 20, "bitti"), blok("b", 17 * 60 + 25, 17 * 60 + 45)]),
                      {"a": {"bitti": "17:20"}}, duzen(), an(17, 30))
    assert len(tum) >= 4
    for o in tum:
        assert not re.search(r"geç kaldın|yetiştir|acele|hemen", (o.baslik + " " + o.govde).lower())


# ---------------------------------------------------------------- tur: gönderim

class Gonderici:
    def __init__(self, sonuclar=None):
        self.cagrilar, self.sonuclar = [], sonuclar or {}

    def __call__(self, abonelik, yuk, vapid):
        self.cagrilar.append((abonelik["endpoint"], yuk))
        return self.sonuclar.get(abonelik["endpoint"], wp.GonderimSonucu("ok", 201, ""))

    def gidenler(self):
        return [e for e, _ in self.cagrilar]


EP = {ISIK: "https://fcm.googleapis.com/isik", ANNE: "https://fcm.googleapis.com/anne",
      BABA: "https://fcm.googleapis.com/baba"}


@pytest.fixture
def kok(tmp_path, monkeypatch):
    monkeypatch.setenv("TEDY_AKSAM_PLANI", "1")
    monkeypatch.setenv("TEDY_AKSAM_BILDIRIM", "1")
    monkeypatch.setenv("TEDY_VAPID_PUBLIC", "PUB")
    monkeypatch.setenv("TEDY_VAPID_PRIVATE", "PRIV")
    monkeypatch.setattr(ab, "OGRENCI_EMAILS", frozenset({ISIK}))
    monkeypatch.setattr(ab, "is_full", lambda e: e in (ISIK, ANNE, BABA))
    depo = wp.AbonelikDeposu(tmp_path / wp.ABONELIKLER)
    for email, ep in EP.items():
        depo.ekle(email, {"endpoint": ep, "keys": ANAHTAR, "cihaz": "T"})
    (tmp_path / "output").mkdir(exist_ok=True)
    (tmp_path / "output" / "aksam_duzeni.json").write_text(
        json.dumps({**VARSAYILAN, "haber_alacaklar": [ANNE, BABA]}), encoding="utf-8")
    return tmp_path


def calistir(kok, simdi, p, g=None, gonderici=None):
    if g:
        PlanDeposu(kok).degistir(GUN, lambda gun: gun.update(g))
    gonderici = gonderici or Gonderici()
    durum = ab.tur(simdi, gonderici, kok=kok, plan_kaynagi=lambda s: p)
    return durum, gonderici


def test_kabul_3_baslamadi_tek_sefer(kok):
    p = plan([blok("a", 17 * 60, 17 * 60 + 20)])
    d, g = calistir(kok, an(17, 15), p)
    assert sorted(g.gidenler()) == sorted([EP[ANNE], EP[BABA]])      # Işık'a gitmez
    assert d["gonderilen"] == 2 and not d["olumcul"]
    d2, g2 = calistir(kok, an(17, 16), p)
    assert g2.cagrilar == []
    assert json.loads((kok / ab.DURUM).read_text())["gonderilen"] == 0


def test_kabul_4_takildi(kok):
    p = plan([blok("a", 17 * 60, 17 * 60 + 20, "suruyor")])
    gunluk = {"a": {"durum": "suruyor", "basla": "17:00"}}
    _, g = calistir(kok, an(17, 35), p, gunluk)
    assert sorted(g.gidenler()) == [EP[ISIK]]                         # yalnız "Süre doldu"
    _, g = calistir(kok, an(17, 36), p, gunluk)
    assert sorted(g.gidenler()) == sorted([EP[ANNE], EP[BABA]])
    assert all(y["baslik"] == "Fen bloğu uzadı" for _, y in g.cagrilar)
    _, g = calistir(kok, an(17, 40), p, gunluk)
    assert g.cagrilar == []                                           # ikisi de akşam başına bir kez


def test_takildi_ikinci_blok_icin_tekrarlanmaz(kok):
    g1 = {"a": {"durum": "suruyor", "basla": "17:00"}}
    calistir(kok, an(17, 40), plan([blok("a", 1020, 1040, "suruyor")]), g1)
    g2 = {"b": {"durum": "suruyor", "basla": "17:50"}}
    _, g = calistir(kok, an(18, 30), plan([blok("b", 1070, 1090, "suruyor")]), g2)
    assert [y["baslik"] for _, y in g.cagrilar if y["baslik"].endswith("uzadı")] == []


def test_sure_doldu_ve_mola_bitti_isik_en_cok_iki(kok):
    a = blok("a", 1020, 1040, "suruyor")
    ga = {"a": {"durum": "suruyor", "basla": "17:00"}}
    toplam = []
    for dk in (20, 21, 22):
        _, g = calistir(kok, an(17, dk), plan([a]), ga)
        toplam += [y["baslik"] for e, y in g.cagrilar if e == EP[ISIK]]
    ab_ = blok("a", 1020, 1040, "bitti")
    b = blok("b", 1045, 1065, ders="Matematik", adim="3 soru")
    gb = {"a": {"durum": "bitti", "basla": "17:00", "bitti": "17:22"}}
    for dk in (26, 27, 28, 30):
        _, g = calistir(kok, an(17, dk), plan([ab_, b]), gb)
        toplam += [y["baslik"] for e, y in g.cagrilar if e == EP[ISIK]]
    assert toplam == ["Süre doldu", "Mola bitti"]


def test_alici_listesi_bos_aileye_yok(kok):
    (kok / "output" / "aksam_duzeni.json").write_text(
        json.dumps({**VARSAYILAN, "haber_alacaklar": []}), encoding="utf-8")
    p = plan([blok("a", 1020, 1040, "suruyor")], sigmayan=[{"ders": "T", "baslik": "x"}])
    _, g = calistir(kok, an(17, 40), p, {"a": {"durum": "suruyor", "basla": "17:00"}})
    assert g.gidenler() == [EP[ISIK]]                                 # yalnız "Süre doldu"


def test_aileden_cikan_ve_ogrenci_alici_olmaz(kok, monkeypatch):
    (kok / "output" / "aksam_duzeni.json").write_text(
        json.dumps({**VARSAYILAN, "haber_alacaklar": [ANNE, BABA, ISIK]}), encoding="utf-8")
    monkeypatch.setattr(ab, "is_full", lambda e: e in (ISIK, BABA))   # anne aileden çıktı
    p = plan([blok("a", 1020, 1040)])
    _, g = calistir(kok, an(17, 15), p)
    assert g.gidenler() == [EP[BABA]]


def test_sessiz_saatte_gonderilmez(kok):
    p = plan([blok("a", 1020, 1040)], sigmayan=[{"ders": "T", "baslik": "x"}])
    d, g = calistir(kok, an(21, 5), p)
    assert g.cagrilar == [] and d["gonderilen"] == 0


@pytest.mark.parametrize("acik", [{"TEDY_AKSAM_BILDIRIM": "0"}, {"TEDY_AKSAM_PLANI": "0"},
                                  {"TEDY_AKSAM_BILDIRIM": ""}])
def test_bayrak_kapali_hic_gonderilmez(kok, monkeypatch, acik):
    for k, v in acik.items():
        monkeypatch.setenv(k, v)
    d, g = calistir(kok, an(17, 30), plan([blok("a", 1020, 1040)]))
    assert g.cagrilar == [] and d["kapali"] is True and not d["olumcul"]
    assert json.loads((kok / ab.DURUM).read_text())["kapali"] is True


def test_aksam_yok_hicbir_sey(kok):
    p = plan([blok("a", 1020, 1040)], sigmayan=[{"ders": "T", "baslik": "x"}])
    _, g = calistir(kok, an(17, 30), p, {"aksam_yok": True})
    assert g.cagrilar == []


def test_olu_cihaz_silinir_tur_surer(kok):
    p = plan([blok("a", 1020, 1040)])
    gonderici = Gonderici({EP[ANNE]: wp.GonderimSonucu("olu", 410, "gone")})
    d, _ = calistir(kok, an(17, 15), p, gonderici=gonderici)
    assert d["olu_silinen"] == 1 and d["gonderilen"] == 1
    depo = wp.AbonelikDeposu(kok / wp.ABONELIKLER)
    assert depo.kisinin(ANNE) == [] and len(depo.kisinin(BABA)) == 1


def test_gecici_hata_ertesi_dakika_yeniden_denenir(kok):
    p = plan([blok("a", 1020, 1040)])
    hata = Gonderici({EP[ANNE]: wp.GonderimSonucu("hata", 503, "x")})
    d, _ = calistir(kok, an(17, 15), p, gonderici=hata)
    assert d["gonderilen"] == 1 and not d["olumcul"] and d["hatalar"]   # Baba aldı, Anne almadı
    _, g = calistir(kok, an(17, 16), p)
    assert g.gidenler() == [EP[ANNE]]                                   # yalnız Anne yeniden
    _, g = calistir(kok, an(17, 17), p)
    assert g.cagrilar == []


def test_istisna_firlatan_gonderici_turu_dusurmez(kok):
    def patlak(abonelik, yuk, vapid):
        raise RuntimeError("ağ")
    d, _ = calistir(kok, an(17, 15), plan([blok("a", 1020, 1040)]), gonderici=patlak)
    assert d["gonderilen"] == 0 and not d["olumcul"] and d["hatalar"]


def test_plan_hatasi_olumcul_ve_durum_yazilir(kok):
    def bozuk(s):
        raise ValueError("plan yok")
    d = ab.tur(an(17, 15), Gonderici(), kok=kok, plan_kaynagi=bozuk)
    assert d["olumcul"] is True
    assert json.loads((kok / ab.DURUM).read_text())["olumcul"] is True


def test_vapid_yoksa_olumcul(kok, monkeypatch):
    monkeypatch.delenv("TEDY_VAPID_PUBLIC")
    d, _ = calistir(kok, an(17, 15), plan([blok("a", 1020, 1040)]))
    assert d["olumcul"] is True and ab.KOK_VAPID_YOK in d["hatalar"]


def test_main_cikis_kodlari(kok, monkeypatch):
    monkeypatch.setattr(ab, "tur", lambda *a, **k: {"olumcul": False})
    assert ab.main(["tur"]) == 0
    monkeypatch.setattr(ab, "tur", lambda *a, **k: {"olumcul": True})
    assert ab.main(["tur"]) == 1
    assert ab.main(["x"]) == 2


def test_varsayilan_gonderici_testte_yasak(kok):
    with pytest.raises(BaseException) as e:
        wp.gonder({}, {}, None)
    assert type(e.value).__name__ == "GercekPushYasak" and not isinstance(e.value, Exception)


def test_gercek_gondericiye_ulasan_tur_testi_dusurur(kok):
    # gonderici verilmez: tur web_push.gonder'e düşer; koruma `except Exception`'a takılmaz.
    with pytest.raises(BaseException) as e:
        ab.tur(an(17, 15), None, kok=kok, plan_kaynagi=lambda s: plan([blok("a", 1020, 1040)]))
    assert type(e.value).__name__ == "GercekPushYasak"


def test_metinler_sinirlanir():
    uzun = "Çok uzun ders adı " * 10
    p = plan([blok("a", 1020, 1040, "suruyor", ders=uzun, adim=uzun)], sigmayan=[{"ders": uzun, "baslik": uzun}])
    g = {"a": {"basla": "17:00"}}
    for o in ab.olaylar(p, g, duzen(), an(17, 40)):
        assert len(o.baslik) <= 80 and len(o.govde) <= 300 and "…" in (o.baslik + o.govde)
    sirada = plan([blok("a", 1020, 1040, "bitti"), blok("b", 1045, 1065, ders=uzun, adim=uzun)])
    (m,) = ab.olaylar(sirada, {"a": {"bitti": "17:20"}}, duzen(), an(17, 30))
    assert len(m.govde) <= 300 and "…" in m.govde
    assert len(ab._ders(uzun, "x")) <= 30


def test_baslamadi_saati_gonderim_anidir():
    p = plan([blok("a", 1020, 1040)])
    (o,) = ab.olaylar(p, {}, duzen(), an(17, 42))
    assert o.govde == "Saat 17:42; bu akşamın ilk işi Fen."


def test_sigmiyor_bos_baslik_yedegi():
    p = plan([blok("a", 1020, 1040, "suruyor")], sigmayan=[{"ders": "Türkçe", "baslik": "  "}])
    (o,) = [o for o in ab.olaylar(p, {"a": {"basla": "17:00"}}, duzen(), an(17, 5)) if o.tur == "sigmiyor"]
    assert o.govde == "Türkçe: bir ödev yarın teslim; plana sığmadı." and "  " not in o.govde


def test_defter_kilit_altinda_yeniden_denetler(tmp_path):
    d = ab.Defter(tmp_path / "d.jsonl")
    o = ab.Olay("baslamadi", "aile", None, "b", "g")
    assert d.yaz(GUN, o, ANNE, an(17, 15)) is True
    assert d.yaz(GUN, o, ANNE, an(17, 16)) is False
    assert len((tmp_path / "d.jsonl").read_text().splitlines()) == 1


def test_alici_epostalari_normallestirilir(kok, monkeypatch):
    monkeypatch.setattr(ab, "is_full", lambda e: e in (ISIK, ANNE))
    a = ab.alicilar({"haber_alacaklar": ["  ANNE@x ", "anne@x", ISIK.upper(), 5]})
    assert a == {"ogrenci": [ISIK], "aile": [ANNE]}


def test_saglik_aksam_bildirim_durumu(tmp_path, monkeypatch):
    import src.run_sync as rs
    monkeypatch.setattr(rs, "OUTPUT_DIR", str(tmp_path))
    assert rs._aksam_bildirim_durumu() == {}                       # dosya yok
    (tmp_path / "aksam_bildirim_durumu.json").write_text("{bozuk", encoding="utf-8")
    assert rs._aksam_bildirim_durumu() == {}
    (tmp_path / "aksam_bildirim_durumu.json").write_text("[1]", encoding="utf-8")
    assert rs._aksam_bildirim_durumu() == {}
    (tmp_path / "aksam_bildirim_durumu.json").write_text('{"gonderilen": 2}', encoding="utf-8")
    assert rs._aksam_bildirim_durumu() == {"gonderilen": 2}
    import inspect
    assert '"aksam_bildirim": _aksam_bildirim_durumu()' in inspect.getsource(rs)


def test_birim_dosyalari():
    from pathlib import Path
    kok = Path(__file__).resolve().parents[1]
    svc = (kok / "tedy-aksam-plani.service").read_text()
    tmr = (kok / "tedy-aksam-plani.timer").read_text()
    assert "Environment=TZ=Europe/Istanbul" in svc and "TimeoutStartSec=50" in svc
    assert "-m src.aksam_bildirim tur" in svc
    assert "OnCalendar=*:*:00" in tmr and "Persistent=false" in tmr
