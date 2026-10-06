"""Evdeki modelin arka plan işleri: sohbet başlığı ve eski turların özeti (2026-10-06). Ağ yok."""
import json
from datetime import datetime, timezone

import pytest

from src import yerel_llm as yl
from src.assistant_sohbet import SohbetDeposu

SIMDI = datetime(2026, 10, 6, 8, 0, tzinfo=timezone.utc)
UZUN = "Fen dersinde yıldızların yaşam döngüsünü anlamakta zorlanıyorum, süpernova ne demek?"


def _depo(tmp_path):
    return SohbetDeposu(tmp_path / "s.sqlite")


def _sohbet(depo, *turlar):
    sid = depo.yarat("isik@example.test", "fen", SIMDI)
    for rol, metin in turlar:
        depo.mesaj_ekle(sid, rol, metin, "fen", [], SIMDI)
    return sid


def test_baslik_karsilastir_ve_degistir(tmp_path):
    depo = _depo(tmp_path)
    sid = _sohbet(depo, ("user", UZUN))
    assert depo.baslik_oner(sid, UZUN, "Yıldızların yaşam döngüsü") is True
    assert depo.getir(sid)["baslik"] == "Yıldızların yaşam döngüsü"
    assert depo.baslik_oner(sid, UZUN, "Başka") is False  # başlık artık beklenen değil
    assert depo.getir(sid)["baslik"] == "Yıldızların yaşam döngüsü"


def test_ilk_cevaptan_sonra_uzun_soruya_kisa_baslik(tmp_path):
    from src.assistant_core import baslik_oner

    depo = _depo(tmp_path)
    sid = _sohbet(depo, ("user", UZUN), ("assistant", "Süpernova, büyük kütleli bir yıldızın patlamasıdır."))
    istemler = []
    baslik_oner(depo, sid, tamamla=lambda p: istemler.append(p) or '**Başlık:** "Süpernova ve yıldız yaşamı"')
    assert depo.getir(sid)["baslik"] == "Süpernova ve yıldız yaşamı"
    assert "6 kelime" in istemler[0] and UZUN in istemler[0]


@pytest.mark.parametrize("turlar,yeniden_adlandir", [
    ((("user", "Kesir nasıl toplanır?"), ("assistant", "Paydalar eşitlenir.")), False),  # kısa soru zaten başlık
    ((("user", UZUN), ("assistant", "a"), ("user", "devam"), ("assistant", "b")), False),  # ilk tur değil
    ((("user", UZUN), ("assistant", "a")), True),                                         # kullanıcı adlandırdı
    ((("user", UZUN),), False),                                                           # cevap yok
])
def test_baslik_yalniz_gerektiginde_uretilir(tmp_path, turlar, yeniden_adlandir):
    from src.assistant_core import baslik_oner

    depo = _depo(tmp_path)
    sid = _sohbet(depo, *turlar)
    if yeniden_adlandir:
        depo.guncelle(sid, "Benim başlığım", None, SIMDI)
    baslik_oner(depo, sid, tamamla=lambda p: pytest.fail("üretilmemeli"))


def test_baslik_uretilemezse_eski_kalir(tmp_path):
    from src.assistant_core import baslik_oner

    depo = _depo(tmp_path)
    sid = _sohbet(depo, ("user", UZUN), ("assistant", "a"))
    baslik_oner(depo, sid, tamamla=lambda p: "")
    assert depo.getir(sid)["baslik"] == UZUN


def _yerel_akis(monkeypatch, metin, gorulen=None):
    monkeypatch.setenv("ASSISTANT_YEREL_LLM", "1")

    def istek(url, govde, zaman_asimi):
        if gorulen is not None:
            gorulen.append(govde)
        return iter([json.dumps({"message": {"content": metin}, "done": False}),
                     json.dumps({"message": {"content": ""}, "done": True})])
    monkeypatch.setattr(yl, "_istek", istek)


def test_ozet_once_yerel_modelle(tmp_path, monkeypatch):
    from src import assistant_core

    depo = _depo(tmp_path)
    sid = _sohbet(depo, *[(("user", "assistant")[i % 2], f"tur {i} " + "x" * 3000) for i in range(24)])
    gorulen = []
    _yerel_akis(monkeypatch, "yerel özet", gorulen)
    monkeypatch.setattr(assistant_core.ClaudeClient, "available", property(lambda self: pytest.fail("Haiku'ya gitmemeli")))
    assistant_core.eski_turleri_ozetle(depo, sid)
    assert depo.ozet_oku(sid) == "yerel özet"
    istem = gorulen[0]["messages"][-1]["content"]
    assert "tur 0" in istem and len(istem) < 4 * 1300 + 2000  # her eski tur 1200 karakterle sınırlı


def test_ozet_yerel_duserse_haikuya_doner(tmp_path, monkeypatch):
    from src import assistant_core

    depo = _depo(tmp_path)
    sid = _sohbet(depo, *[(("user", "assistant")[i % 2], f"tur {i}") for i in range(24)])
    monkeypatch.setenv("ASSISTANT_YEREL_LLM", "1")
    monkeypatch.setattr(yl, "_istek", lambda *a: (_ for _ in ()).throw(OSError("mbp yok")))
    haiku = []
    monkeypatch.setattr(assistant_core, "_haiku_ozet", lambda prompt: haiku.append(prompt) or "haiku özeti")
    monkeypatch.setattr(assistant_core.ClaudeClient, "available", property(lambda self: True))
    assistant_core.eski_turleri_ozetle(depo, sid)
    assert depo.ozet_oku(sid) == "haiku özeti" and len(haiku) == 1


def test_panel_isleri_yerel_acikken_arka_planda_ve_tekil(monkeypatch):
    from src import dashboard_api

    monkeypatch.setenv("ASSISTANT_YEREL_LLM", "1")
    calisan = []
    import threading
    birak = threading.Event()

    def yavas(*a):
        calisan.append(threading.current_thread().name)
        birak.wait(5)

    f1 = dashboard_api._yerel_is_planla(("ozet", "s1"), yavas)
    f2 = dashboard_api._yerel_is_planla(("ozet", "s1"), yavas)  # aynı iş beklerken ikincisi kuyruğa girmez
    assert f1 is not None and f2 is None
    birak.set()
    f1.result(timeout=5)
    assert calisan and calisan[0].startswith("yerel-llm")
    assert dashboard_api._yerel_is_planla(("ozet", "s1"), lambda: None) is not None  # bittikten sonra yine olur
