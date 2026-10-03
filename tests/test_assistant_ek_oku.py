"""The assistant and portal attachments (plan 2026-09-28-portal-ekleri, Görev 10):
ek_oku pages an attachment's text inside the 4,000-char tool-result cut,
odev_listesi names attachments with their ids, BM25 hits carry the sidecar label."""
import json
from datetime import datetime

from src.assistant_tools import (EK_TOOL, GOVDE_SINIRI, McpRegistry, build_registry,
                                 odev_listesi_metni)
from src.portal_ekleri import METIN_ONEKI, EkDeposu, ek_kimligi

SIMDI = datetime(2026, 9, 24, 16, 10)
SP_URL = "https://ornekokul-my.sharepoint.com/:b:/g/personal/ogretmen_ornekokul_k12_tr/EaBcDeFgHiJ?e=AbC123"
KIMLIK = ek_kimligi(SP_URL)
FF = chr(12)
GOVDE = FF.join(f"Sayfa {i} başlığı\n" + ("Bumerang kitabındaki soruyu cevapla. " * 70) for i in range(1, 5))


def _depo(tmp_path, **kayit):
    depo = EkDeposu(tmp_path)
    depo.dizin.mkdir(parents=True, exist_ok=True)
    (depo.dizin / f"{KIMLIK}.pdf").write_bytes(b"%PDF-1.7")
    temel = {"id": KIMLIK, "status": "indirildi", "file": f"{KIMLIK}.pdf", "ext": ".pdf", "text": "var",
             "name": "Sayfa 12-13.pdf", "source": {"section": "odevler", "title": "Kitap okuma ödevi"}}
    depo.yaz({KIMLIK: {**temel, **kayit}})
    depo.metin_yolu(KIMLIK).write_text(
        f"{METIN_ONEKI}Sayfa 12-13.pdf · Kitap okuma ödevi · Sosyal Bilgiler\n\n{GOVDE}\n", encoding="utf-8")
    depo.meta_yolu(KIMLIK).write_text(json.dumps(
        {"id": KIMLIK, "name": "Sayfa 12-13.pdf", "title": "Kitap okuma ödevi"}), encoding="utf-8")
    return depo


def _reg(depo, **kw):
    return McpRegistry(clients={}, local_search=kw.pop("local_search", lambda q, k: []), ek_deposu=depo, **kw)


def test_arac_yalniz_depo_verilince_ilan_edilir(tmp_path):
    assert EK_TOOL not in {d["name"] for d in build_registry(lambda q, k: []).declarations()}
    assert EK_TOOL in {d["name"] for d in _reg(_depo(tmp_path)).declarations()}
    out = build_registry(lambda q, k: []).dispatch(EK_TOOL, {"id": KIMLIK})
    assert not out.ok and "bilinmeyen araç" in out.error


def test_ilk_sayfa_sinir_altinda_devamini_soyler(tmp_path):
    out = _reg(_depo(tmp_path)).dispatch(EK_TOOL, {"id": KIMLIK})
    assert out.ok and len(out.text) <= GOVDE_SINIRI
    assert out.text.startswith("Ek: Sayfa 12-13.pdf · Kitap okuma ödevi\nMetin sayfası 1/")
    assert "PDF s.1" in out.text and f"(Devamı: ek_oku id={KIMLIK} sayfa=2)" in out.text
    assert METIN_ONEKI not in out.text and FF not in out.text
    atif = out.citations[0]
    assert atif["label"] == "Sayfa 12-13.pdf · Kitap okuma ödevi" and atif["kind"] == "ogrenci"
    assert "content/" not in atif["label"] and atif["locator"]["id"] == KIMLIK


def test_son_sayfa_ve_aralik_disi(tmp_path):
    reg = _reg(_depo(tmp_path))
    ilk = reg.dispatch(EK_TOOL, {"id": KIMLIK}).text
    toplam = int(ilk.split("Metin sayfası 1/")[1].split()[0])
    son = reg.dispatch(EK_TOOL, {"id": f"ek:{KIMLIK}", "sayfa": toplam})
    assert son.ok and "(Ekin sonu.)" in son.text
    disari = reg.dispatch(EK_TOOL, {"id": KIMLIK, "sayfa": toplam + 1})
    assert not disari.ok and "metin sayfası var" in disari.error


def test_gecersiz_ve_bilinmeyen_kimlik(tmp_path):
    reg = _reg(_depo(tmp_path))
    assert "16 karakterlik" in reg.dispatch(EK_TOOL, {"id": "../x"}).error
    assert "böyle bir ek yok" in reg.dispatch(EK_TOOL, {"id": "0123456789abcdef"}).error


def test_durumlar_durustce_soylenir(tmp_path):
    out = _reg(_depo(tmp_path, status="erisilemedi", reason="kaynak giriş istiyor; paylaşım herkese açık değil")
               ).dispatch(EK_TOOL, {"id": KIMLIK})
    assert out.ok and "indirilemedi" in out.text and "giriş istiyor" in out.text
    assert "metin katmanı yok" in _reg(_depo(tmp_path, text="yok")).dispatch(EK_TOOL, {"id": KIMLIK}).text
    assert ".xlsx" in _reg(_depo(tmp_path, text="desteklenmiyor", ext=".xlsx")).dispatch(EK_TOOL, {"id": KIMLIK}).text
    assert "henüz çıkarılmadı" in _reg(_depo(tmp_path, text="bekliyor")).dispatch(EK_TOOL, {"id": KIMLIK}).text


def test_bm25_isabeti_yan_meta_etiketini_tasir(tmp_path):
    satirlar = [{"path": f"content/portal-ekleri/{KIMLIK}.txt", "chunk_index": 0, "text": "Bumerang",
                 "snippet": "Bumerang", "confidence": 0.8},
                {"path": "content/portal-ekleri/0123456789abcdef.txt", "chunk_index": 0, "text": "x",
                 "snippet": "x", "confidence": 0.5}]
    out = _reg(_depo(tmp_path), local_search=lambda q, k: satirlar).dispatch("ogrenci_verisi_ara", {"query": "Bumerang"})
    assert [a["label"] for a in out.citations] == ["Sayfa 12-13.pdf · Kitap okuma ödevi", "Portal eki"]


def _hw(ekler):
    return {"Ders Adı": "Sosyal Bilgiler", "normalized_course": "Sosyal Bilgiler",
            "Ödev Başlığı": "Kitap okuma ödevi", "Ödev Son Teslim Tarihi": "25.09.2026 12:00",
            "Ödev Durumu": "Değerlendirilmemiş", "detail": {"description": "Sayfa 12-13", "attachments": ekler}}


def test_odev_listesi_ekleri_kimlikleriyle_listeler():
    duvar = SP_URL.replace("EaBcDe", "EzYxWv")
    metin = odev_listesi_metni([_hw([
        {"name": "Sayfa 12-13.pdf", "url": SP_URL, "id": KIMLIK, "status": "indirildi"},
        {"name": "Kitap sayfaları", "url": duvar, "id": ek_kimligi(duvar), "status": "erisilemedi"},
        {"name": "Konu videosu", "url": "https://www.youtube.com/watch?v=x", "id": None, "status": "baglanti"}])], SIMDI)
    assert (f"Ekler: Sayfa 12-13.pdf [ek:{KIMLIK}]; Kitap sayfaları [ek:{ek_kimligi(duvar)} · indirilemedi]; "
            "Konu videosu (bağlantı)") in metin


def test_zenginlestirilmemis_satirda_kimlik_url_den_turetilir():
    metin = odev_listesi_metni([_hw([{"name": "Sayfa 12-13.pdf", "url": SP_URL}])], SIMDI)
    assert f"[ek:{KIMLIK}]" in metin


def test_calisan_asistan_araci_her_zaman_bagli(tmp_path):
    from src.assistant_core import AssistantRuntime
    (tmp_path / "output").mkdir()
    assert EK_TOOL in {d["name"] for d in AssistantRuntime(tmp_path).registry.declarations()}
