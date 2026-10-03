"""Fotoğraf önerisi yalnız request sahibinin görselinden; kayıt/LLM ağı yok."""
import hashlib

import pytest

from src.assistant_core import AssistantRuntime, ToolLoopResult
from src.assistant_tools import build_registry

KIMLIK = "ab" * 16


def _kaynak(data, mime):
    assert data == b"jpeg" and mime == "image/jpeg"
    return [{"ders_adi": "Matematik", "odev_basligi": "Kesirler", "son_teslim_tarihi": "", "aciklama": "Sayfa 3"}]


def _oku(kimlik):
    return ({"tur": "gorsel", "id": kimlik}, b"jpeg")


def test_bildirim_ve_cagri_kapisi():
    reg = build_registry(lambda q, k: [], foto_odev_kaynagi=_kaynak)
    for okur in ("ogrenci", "aile"):
        assert "odev_fotograftan" in {d["name"] for d in reg.declarations(okur)}
    for okur, interaktif in (("bilinmiyor", True), ("ogrenci", False)):
        assert "odev_fotograftan" not in {d["name"] for d in reg.declarations(okur, mod_onerisi=interaktif)}
        assert not reg.dispatch("odev_fotograftan", {"ek_id": KIMLIK}, okur=okur,
                                mod_onerisi=interaktif, ek_okuyucu=_oku).ok


def test_oneri_tarih_uydurmaz_yazmaz(tmp_path):
    reg = build_registry(lambda q, k: [], foto_odev_kaynagi=_kaynak)
    out = reg.dispatch("odev_fotograftan", {"ek_id": KIMLIK}, okur="ogrenci", ek_okuyucu=_oku)
    assert out.ok and out.olay["event"] == "odev_onerisi"
    assert out.olay["adaylar"] == [{"ders": "Matematik", "baslik": "Kesirler", "teslim": "",
                                     "aciklama": "Sayfa 3", "eksik": ["teslim"]}]
    assert out.olay["photo_hash"] == hashlib.sha256(b"jpeg").hexdigest()[:16]
    assert not (tmp_path / "photo_homework.json").exists()


@pytest.mark.parametrize("kimlik,oku", [("../x", _oku), (KIMLIK, lambda _: None),
    (KIMLIK, lambda _: ({"tur": "pdf"}, b"pdf"))])
def test_gecersiz_ek_extractor_cagirmaz(kimlik, oku):
    def kaynak(*a):
        pytest.fail("extractor should not run")
    reg = build_registry(lambda q, k: [], foto_odev_kaynagi=kaynak)
    assert not reg.dispatch("odev_fotograftan", {"ek_id": kimlik}, okur="ogrenci", ek_okuyucu=oku).ok


def test_extractor_hatasi_sizmaz():
    def kaynak(*a):
        raise RuntimeError("private traceback secret")
    reg = build_registry(lambda q, k: [], foto_odev_kaynagi=kaynak)
    out = reg.dispatch("odev_fotograftan", {"ek_id": KIMLIK}, okur="ogrenci", ek_okuyucu=_oku)
    assert not out.ok and "private" not in out.error


def test_runtime_oneri_yuku_ve_request_okuyucusu(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "offline-test")
    runtime = AssistantRuntime(tmp_path, foto_odev_kaynagi=_kaynak)
    gorulen = []
    def loop(**kwargs):
        out = kwargs["dispatch"]("odev_fotograftan", {"ek_id": KIMLIK})
        assert out.ok
        gorulen.append(out.olay)
        return ToolLoopResult(text="Teslim tarihi okunamadı.", olaylar=[out.olay])
    monkeypatch.setattr(runtime.llm, "chat_with_tools", loop)
    monkeypatch.setattr(runtime, "_write_metric", lambda e: None)
    payload = runtime.chat(messages=[{"role": "user", "content": "Ödeve ekle"}], okur="ogrenci", ek_okuyucu=_oku)
    assert payload["odev_onerisi"]["ek_id"] == KIMLIK
    events = list(runtime.chat_events(messages=[{"role": "user", "content": "Ödeve ekle"}], okur="ogrenci", ek_okuyucu=_oku))
    assert any(e["event"] == "odev_onerisi" for e in events)
    assert len(gorulen) == 2
