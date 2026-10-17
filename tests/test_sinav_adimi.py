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
