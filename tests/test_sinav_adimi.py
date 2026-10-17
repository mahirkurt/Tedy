"""run_sync's exam-detection step, the --kuru CLI and the health summary.
Nothing here reaches the model: the step's entry point is patched."""
import json
import time
from datetime import datetime

import src.run_sync as run_sync
import src.sinav_tespiti as st
# Taken at collection, before conftest's autouse fixture replaces st.tespit_et
# with a refusal: the end-to-end test below wants the real one.
from src.sinav_tespiti import tespit_et as GERCEK_TESPIT

BELGE = {"uretildi": "2026-10-16T10:00:00", "surum": st.SURUM,
         "sinavlar": [{"id": "a1", "ders": "Matematik", "tur": "konu_tarama", "baslik": "Matematik KTT",
                       "tarih": "2026-10-20", "saat": None, "hafta": None, "konular": ["Mutlak değer"],
                       "kaynaklar": [{"tur": "ders_karti", "konum": {"hafta": "4. Hafta"}, "alinti": "KTT"}],
                       "ilk_tespit": None, "icerik_surumu": "abc", "degisti": None, "sentetik": False,
                       "taban": None, "son_yayin": "2026-10-05"}],
         "ozet": {"aday": 3, "incelenen": 2, "incelenmedi": 1, "butce_usd": 0.01, "hatalar": []}}


def _kok(tmp_path, monkeypatch):
    (tmp_path / "output").mkdir()
    (tmp_path / "output/scraped_data.json").write_text(json.dumps({"takvim": []}), encoding="utf-8")
    monkeypatch.setattr(run_sync, "PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(run_sync, "OUTPUT_DIR", str(tmp_path / "output"))
    return tmp_path


def test_adim_dosyayi_yazar_ozet_doner(tmp_path, monkeypatch):
    kok = _kok(tmp_path, monkeypatch)
    cagri = {}

    def sahte(kok_, veri, taban, simdi, bitis, okuyucu=None):
        cagri.update(kok=kok_, veri=veri, taban=taban, kalan=bitis - time.monotonic())
        return BELGE
    monkeypatch.setattr(st, "tespit_et", sahte)
    ozet = run_sync._sinav_tespiti_adimi(start_time=time.time())
    assert ozet == {**BELGE["ozet"], "sinav": 1, "sure": 45}
    assert json.loads((kok / "output/sinavlar.json").read_text(encoding="utf-8")) == BELGE
    assert cagri["veri"] == {"takvim": []} and cagri["taban"] == [] and 40 < cagri["kalan"] <= 45


def test_adim_sure_kalmadiysa_yine_yazar_model_suresi_sifir(tmp_path, monkeypatch):
    _kok(tmp_path, monkeypatch)
    kalanlar = []
    monkeypatch.setattr(st, "tespit_et", lambda k, v, t, s, bitis, okuyucu=None:
                        kalanlar.append(bitis - time.monotonic()) or BELGE)
    ozet = run_sync._sinav_tespiti_adimi(start_time=time.time() - 590)
    assert ozet["sure"] == 0 and kalanlar[0] <= 0


def test_adim_hatasi_senkronu_bozmaz(tmp_path, monkeypatch):
    _kok(tmp_path, monkeypatch)

    def patla(*a, **k):
        raise RuntimeError("bir şey oldu")
    monkeypatch.setattr(st, "tespit_et", patla)
    assert run_sync._sinav_tespiti_adimi(start_time=time.time()) == {"hata": "bir şey oldu"}
    assert not (tmp_path / "output/sinavlar.json").exists()


def test_uyari_durumu_okunur(tmp_path, monkeypatch):
    kok = _kok(tmp_path, monkeypatch)
    assert run_sync._sinav_uyari_durumu() == {}
    (kok / "output/sinav_uyari_durumu.json").write_text('{"son_tur": "x", "gonderilen": 2}', encoding="utf-8")
    assert run_sync._sinav_uyari_durumu() == {"son_tur": "x", "gonderilen": 2}


def test_kuru_rapor_okunur_metin():
    metin = st.kuru_rapor(BELGE)
    assert "Matematik · konu_tarama · 2026-10-20" in metin
    assert "Konular: Mutlak değer" in metin and "ders_karti" in metin
    assert "aday 3 · incelenen 2 · incelenmedi 1 · bütçe 0.01 USD" in metin


def test_cli_kuru_dosya_yazmaz(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(st, "PROJE_KOKU", tmp_path)
    (tmp_path / "output").mkdir()
    (tmp_path / "output/scraped_data.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(st, "_taban", lambda veri: [])
    monkeypatch.setattr(st, "tespit_et", lambda *a, **k: BELGE)
    assert st.main(["--kuru"]) == 0
    assert "Matematik KTT" in capsys.readouterr().out
    assert not (tmp_path / "output/sinavlar.json").exists()
    assert st.main([]) == 0
    assert (tmp_path / "output/sinavlar.json").exists()


def test_cli_kuru_yardimi_neyin_yine_yazildigini_soyler(capsys, monkeypatch):
    """--kuru skips only sinavlar.json: model calls still happen, so cache and ledger are written."""
    import pytest as _pytest

    import src.env_loader
    monkeypatch.setattr(src.env_loader, "load_env", lambda *a, **k: None)
    with _pytest.raises(SystemExit):
        st.main(["--help"])
    yardim = " ".join(capsys.readouterr().out.split())
    assert "sinavlar.json'a yazmadan (model önbelleği ve bütçe defteri yine yazılır)" in yardim


def _sahte_okuyucu():
    from src.sinav_cikarimi import OkumaSonucu

    class Okuyucu:
        model = "claude-haiku-4-5"

        def oku(self, aday, bugun, zaman_asimi):
            if "KTT" not in aday.metin:
                return OkumaSonucu([], 10, 1)
            return OkumaSonucu([{"ders": "Matematik", "tur": "konu_tarama", "baslik": "Matematik KTT",
                                 "tarih_ifadesi": "15 EKİM PERŞEMBE", "tarih": "", "saat": "",
                                 "konular": ["MUTLAK DEĞER"], "alinti": "15 EKİM PERŞEMBE günü yapılacak olan Matematik KTT"}],
                               100, 10)
    return Okuyucu()


def test_tespit_et_uctan_uca_sahte_okuyucuyla(tmp_path):
    from tests.sinav_fikstur import haftalar_verisi

    belge = GERCEK_TESPIT(tmp_path, haftalar_verisi(), [], datetime(2026, 10, 16, 10), time.monotonic() + 60,
                          okuyucu=_sahte_okuyucu())
    [k] = belge["sinavlar"]
    assert (k["ders"], k["tarih"], k["konular"]) == ("Matematik", "2026-10-15", ["MUTLAK DEĞER"])
    assert len(k["kaynaklar"]) == 2   # 4. ve 5. hafta
    assert belge["ozet"]["aday"] == 3 and belge["ozet"]["incelenmedi"] == 0


def test_dosya_yok_ilk_kurulum_dosya_bozuk_ilk_kurulum_degil(tmp_path):
    """No file is the first install (what is found is silently "already there");
    a file that exists but cannot be read is not — an unreadable record must not
    make every exam read as old news and swallow the "new" alerts."""
    from tests.sinav_fikstur import haftalar_verisi
    simdi = datetime(2026, 10, 16, 10)

    belge = GERCEK_TESPIT(tmp_path, haftalar_verisi(), [], simdi, time.monotonic() + 60,
                          okuyucu=_sahte_okuyucu())
    assert belge["sinavlar"][0]["ilk_tespit"] is None

    (tmp_path / "output").mkdir(exist_ok=True)
    (tmp_path / "output/sinavlar.json").write_text("{bozuk", encoding="utf-8")
    belge = GERCEK_TESPIT(tmp_path, haftalar_verisi(), [], simdi, time.monotonic() + 60,
                          okuyucu=_sahte_okuyucu())
    assert belge["sinavlar"][0]["ilk_tespit"] == simdi.isoformat(timespec="seconds")


# --- erken ilan edilen sınav 45 günden sonra da kalır (son inceleme, Critical) ----------

ERKEN_KART = ("1. YAZILI\nÖğretmen A | 01.10.2026\nSevgili öğrenciler,\n"
              "Matematik 1. yazılı sınavı 20 Kasım Cuma günü yapılacaktır.\n"
              "Konular: Tam sayılar, Rasyonel sayılar.")
ERKEN_ALINTI = "Matematik 1. yazılı sınavı 20 Kasım Cuma günü yapılacaktır."


def _erken_veri():
    return {"ders_icerikleri_haftalar": {"4. Hafta 28 Eyl. - 04 Eki.": {
                "Matematik": {"cards": [ERKEN_KART], "items": [], "text": ""}}},
            "ders_icerikleri": {}, "odevlerim": {"homework": {"rows": []}},
            "duyurular": {"announcements": []}, "takvim": []}


class _ErkenOkuyucu:
    model = "claude-haiku-4-5"

    def __init__(self):
        self.cagrilar = 0

    def oku(self, aday, bugun, zaman_asimi):
        from src.sinav_cikarimi import OkumaSonucu
        self.cagrilar += 1
        return OkumaSonucu([{"ders": "Matematik", "tur": "yazili", "baslik": "Matematik 1. yazılı",
                             "tarih_ifadesi": "20 Kasım Cuma", "tarih": "", "saat": "",
                             "konular": ["Tam sayılar", "Rasyonel sayılar"], "alinti": ERKEN_ALINTI}], 100, 10)


TAKVIM_YAZILI = {"id": "tk-yazili", "course": "Matematik", "title": "Matematik 1. Yazılı",
                 "rawTitle": "Matematik 1. Yazılı", "date": "2026-11-20T09:00:00", "allDay": False}


import pytest  # noqa: E402


@pytest.mark.parametrize("taban", [[], [TAKVIM_YAZILI]], ids=["metin-kaydi", "takvime-bagli"])
def test_erken_ilan_edilen_sinav_45_gun_sonra_silinmez(tmp_path, taban):
    okuyucu = _ErkenOkuyucu()
    ilk = GERCEK_TESPIT(tmp_path, _erken_veri(), taban, datetime(2026, 10, 2, 10), time.monotonic() + 60,
                        okuyucu=okuyucu)
    st.yaz(tmp_path, ilk)
    [k1] = [k for k in ilk["sinavlar"] if k["tarih"] == "2026-11-20"]
    assert k1["konular"] == ["Tam sayılar", "Rasyonel sayılar"]

    # 16 Kasım: the post is 46 days old, the exam four days ahead.
    son = GERCEK_TESPIT(tmp_path, _erken_veri(), taban, datetime(2026, 11, 16, 18), time.monotonic() + 60,
                        okuyucu=okuyucu)
    assert okuyucu.cagrilar == 1   # read from the cache, no second call
    [k2] = [k for k in son["sinavlar"] if k["tarih"] == "2026-11-20"]
    assert k2["id"] == k1["id"]
    assert k2["konular"] == ["Tam sayılar", "Rasyonel sayılar"]
    assert k2["icerik_surumu"] == k1["icerik_surumu"] and k2["degisti"] is None


# --- temizlik A (2026-10-17) -------------------------------------------------------

def test_a14_45_gun_sonra_duzenlenen_ilan_bir_kez_yeniden_okunur(tmp_path):
    """The teacher edits the 01.10 post on 16.11 (a topic added): new text, same position, the
    signature date still 01.10. Past the age limit it would never be read and the exam would
    vanish four days before it is sat; the previous sinavlar.json's future record protects it."""
    okuyucu = _ErkenOkuyucu()
    ilk = GERCEK_TESPIT(tmp_path, _erken_veri(), [], datetime(2026, 10, 2, 10), time.monotonic() + 60,
                        okuyucu=okuyucu)
    st.yaz(tmp_path, ilk)
    duzenli = _erken_veri()
    kart = duzenli["ders_icerikleri_haftalar"]["4. Hafta 28 Eyl. - 04 Eki."]["Matematik"]
    kart["cards"] = [ERKEN_KART + "\nNot: Kesirler de konulara eklendi."]
    son = GERCEK_TESPIT(tmp_path, duzenli, [], datetime(2026, 11, 16, 18), time.monotonic() + 60,
                        okuyucu=okuyucu)
    assert okuyucu.cagrilar == 2
    [k] = [k for k in son["sinavlar"] if k["tarih"] == "2026-11-20"]
    assert k["konular"] == ["Tam sayılar", "Rasyonel sayılar"]


def test_a22_eski_surum_onceki_dosya_ilk_kurulum_sayilmaz(tmp_path):
    from tests.sinav_fikstur import haftalar_verisi
    simdi = datetime(2026, 10, 16, 10)
    (tmp_path / "output").mkdir()
    (tmp_path / "output/sinavlar.json").write_text(
        json.dumps({"surum": st.SURUM - 1, "sinavlar": []}), encoding="utf-8")
    belge = GERCEK_TESPIT(tmp_path, haftalar_verisi(), [], simdi, time.monotonic() + 60,
                          okuyucu=_sahte_okuyucu())
    assert belge["sinavlar"][0]["ilk_tespit"] == simdi.isoformat(timespec="seconds")


def test_a21_bozuk_sinav_suresi_varsayilana_duser(monkeypatch):
    monkeypatch.delenv("TEDY_SINAV_SURE_DENEME", raising=False)
    assert run_sync._ortam_saniyesi("TEDY_SINAV_SURE_DENEME", 45) == 45
    for deger, beklenen in (("30", 30), (" 60 ", 60), ("abc", 45), ("", 45), ("4.5", 45), ("-5", 45)):
        monkeypatch.setenv("TEDY_SINAV_SURE_DENEME", deger)
        assert run_sync._ortam_saniyesi("TEDY_SINAV_SURE_DENEME", 45) == beklenen, deger


def test_a21_bozuk_sinav_suresiyle_ice_aktarma_dusmez():
    import os
    import subprocess
    import sys
    from pathlib import Path
    kok = Path(__file__).resolve().parents[1]
    sonuc = subprocess.run([sys.executable, "-c", "import src.run_sync as r; print(r.SINAV_SURE)"],
                           cwd=kok, env={**os.environ, "TEDY_SINAV_SURE": "kırk beş"},
                           capture_output=True, text=True, timeout=120)
    assert sonuc.returncode == 0, sonuc.stderr[-500:]
    assert sonuc.stdout.strip().splitlines()[-1] == "45"


def test_a22_main_saglikta_sinav_anahtarlarini_yazar(tmp_path, monkeypatch):
    from tests.test_portal_ekleri_sync import _basarili_main

    def sahte_tespit(kok_, veri, taban, simdi, bitis, okuyucu=None):
        # The alert timer's last round, as src/sinav_uyari.py leaves it beside the sync's output.
        (tmp_path / "output/sinav_uyari_durumu.json").write_text(
            '{"son_tur": "2026-10-16T10:00:00", "gonderilen": 1}', encoding="utf-8")
        return BELGE
    monkeypatch.setattr(st, "tespit_et", sahte_tespit)
    out = _basarili_main(tmp_path, monkeypatch, lambda *a, **k: {"toplam": 0}, lambda project_root: {})
    saglik = json.loads((out / "health.json").read_text(encoding="utf-8"))
    assert saglik["sinav_tespiti"]["sinav"] == 1 and saglik["sinav_tespiti"]["aday"] == 3
    assert saglik["sinav_uyari"] == {"son_tur": "2026-10-16T10:00:00", "gonderilen": 1}



def test_d4_iki_ders_sekmesindeki_ayni_ilan_tek_cagri_tek_kayit(tmp_path):
    from tests.sinav_fikstur import KTT_KARTI
    veri = {"ders_icerikleri_haftalar": {"4. Hafta 05 Eki. - 11 Eki.": {
                "Matematik": {"cards": [KTT_KARTI], "items": [], "text": ""},
                "Fen Bilimleri": {"cards": [KTT_KARTI], "items": [], "text": ""}}},
            "ders_icerikleri": {}, "odevlerim": {"homework": {"rows": []}},
            "duyurular": {"announcements": []}, "takvim": []}
    okuyucu = _sahte_okuyucu()
    cagrilar = []
    gercek_oku = okuyucu.oku
    okuyucu.oku = lambda aday, bugun, zaman_asimi: cagrilar.append(aday) or gercek_oku(aday, bugun, zaman_asimi)
    belge = GERCEK_TESPIT(tmp_path, veri, [], datetime(2026, 10, 6, 10), time.monotonic() + 60, okuyucu=okuyucu)
    assert len(cagrilar) == 1
    [k] = belge["sinavlar"]
    assert (k["ders"], k["tarih"]) == ("Matematik", "2026-10-15")
    assert sorted(x["konum"]["ders"] for x in k["kaynaklar"]) == ["Fen Bilimleri", "Matematik"]
