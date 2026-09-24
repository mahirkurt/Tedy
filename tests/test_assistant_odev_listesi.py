"""odev_listesi: the assistant reads homework from the list Bugün and İşler show.

Live smoke test, 2026-09-24: asked "Bu hafta hangi ödevlerim var?", the
assistant listed the week's Matematik homework that Işık had marked "Yaptım"
two days earlier, and could not find the due date of the Matematik homework
that was actually open. It had only the BM25 text index, which knows nothing
of the student's marks. This tool hands it the same rows /api/homework serves,
grouped the way the page groups them.
"""
import os
from datetime import datetime

os.environ["TEST_AUTH_BYPASS"] = "1"

from src.assistant_tools import ODEV_TOOL, build_registry, odev_listesi_metni  # noqa: E402

SIMDI = datetime(2026, 9, 24, 16, 10)   # Perşembe


def _hw(ders, baslik, teslim, durum="Değerlendirilmemiş", yaptim=False, cozuldu=False, aciklama=""):
    return {"Ders Adı": ders, "normalized_course": ders, "Ödev Başlığı": baslik,
            "Ödev Son Teslim Tarihi": teslim, "Ödev Durumu": durum,
            "student_marked_done": yaptim, "teacher_resolved": cozuldu,
            "detail": {"description": aciklama, "attachments": []}}


ROWS = [
    _hw("Matematik", "2. HAFTA HAFTA SONU ÖDEVİ", "28.09.2026 12:00", aciklama="Test 2, sayfa 11-12"),
    _hw("Fransızca", "S1 Les verbes", "28.09.2026 08:55"),
    _hw("Matematik", "2. HAFTA HAFTA İÇİ ÖDEVİ", "25.09.2026 12:00", yaptim=True),
    _hw("Türkçe", "Okuma günlüğü", "20.09.2026 23:59"),
    _hw("İngilizce", "Unit 1", "18.09.2026 08:00", durum="Yaptı", cozuldu=True),
]


def _bolum(metin, baslik):
    """The lines under one heading, up to the next blank line."""
    basla = metin.index(baslik)
    son = metin.find("\n\n", basla)
    return metin[basla: son if son != -1 else None]


def test_bugunun_tarihi_ve_kaynak_basta():
    metin = odev_listesi_metni(ROWS, SIMDI)
    assert metin.startswith("Bugün: Perşembe 24.09.2026 16:10")


def test_yapilacaklar_teslime_gore_sirali_ve_goreli_gun():
    yap = _bolum(odev_listesi_metni(ROWS, SIMDI), "YAPILACAK")
    assert yap.index("S1 Les verbes") < yap.index("HAFTA SONU")
    assert "Pazartesi 28.09.2026 08:55 (4 gün sonra)" in yap
    assert "Test 2, sayfa 11-12" in yap          # what to do, not only the title


def test_yaptim_denen_is_yapilacaklarda_yok():
    metin = odev_listesi_metni(ROWS, SIMDI)
    assert "HAFTA İÇİ" not in _bolum(metin, "YAPILACAK")
    assert "HAFTA İÇİ" in _bolum(metin, "YAPTIM")


def test_suresi_gecen_ve_ogretmenin_degerlendirdigi_ayri():
    metin = odev_listesi_metni(ROWS, SIMDI)
    assert "Okuma günlüğü" in _bolum(metin, "SÜRESİ GEÇTİ")
    assert "Unit 1" not in _bolum(metin, "YAPILACAK")
    assert "ÖĞRETMEN DEĞERLENDİRDİ" in metin


def test_bos_liste_bunu_soyler():
    assert "portalda kayıtlı ödev yok" in odev_listesi_metni([], SIMDI)


def test_arac_yalniz_kaynak_verilince_sunulur():
    assert ODEV_TOOL not in [d["name"] for d in build_registry(lambda q, k: []).declarations()]
    reg = build_registry(lambda q, k: [], odev_kaynagi=lambda: ROWS)
    decl = next(d for d in reg.declarations() if d["name"] == ODEV_TOOL)
    assert decl["parameters"] == {"type": "object", "properties": {}}


def test_arac_sonucu_okunur_atifla_doner():
    reg = build_registry(lambda q, k: [], odev_kaynagi=lambda: ROWS)
    out = reg.dispatch(ODEV_TOOL, {})
    assert out.ok and "S1 Les verbes" in out.text
    atif = out.citations[0]
    # A reader sees this label in the source panel: a name, not a file.
    assert atif["kind"] == "ogrenci" and atif["label"] == "Ödevlerim · güncel liste"


def test_kaynak_okunamazsa_modele_hata_olarak_gider():
    def patlak():
        raise OSError("disk")
    out = build_registry(lambda q, k: [], odev_kaynagi=patlak).dispatch(ODEV_TOOL, {})
    assert not out.ok and "ödev listesi okunamadı" in out.error


def test_canli_odevler_isaretleri_uygular_ve_hicbir_seye_yazmaz(monkeypatch):
    import src.dashboard_api as api
    satir = {"Ders Adı": "Matematik", "Ödev Başlığı": "Hafta içi",
             "Ödev Son Teslim Tarihi": "25.09.2026 12:00", "Ödev Durumu": "Değerlendirilmemiş"}
    anahtar = api._homework_row_key(dict(satir))
    monkeypatch.setattr(api, "_scraped", lambda: {"odevlerim": {"homework": {"rows": [satir]}}})
    monkeypatch.setattr(api, "_load_photo_homework_rows", lambda: [])
    monkeypatch.setattr(api, "_load_student_done_marks", lambda: {anahtar: "2026-09-22T17:26:17"})

    def yazma(*a, **k):
        raise AssertionError("asistanın okuması hiçbir dosyaya yazmamalı")
    monkeypatch.setattr(api, "atomic_json_dump", yazma)
    monkeypatch.setattr(api, "_save_student_done_marks", yazma)

    rows = api._canli_odevler()
    assert rows[0]["student_marked_done"] is True
    assert rows[0]["teacher_resolved"] is False


def test_konusmada_bugunun_tarihi_var(tmp_path):
    from src.assistant_core import AssistantRuntime
    (tmp_path / "output").mkdir()
    rt = AssistantRuntime(tmp_path)
    konusma = rt._build_conversation([{"role": "user", "content": "ödevlerim"}], "ödevlerim", "qa", [])
    assert "Bugün:" in konusma[-1]["content"]
    assert "`odev_listesi`" in konusma[0]["content"]


def test_eski_yaptimlar_bu_haftakini_itmez():
    """Live data 2026-09-24: twelve photo-added rows from March, all marked
    "Yaptım", sorted ahead of this week's and pushed it past the cap."""
    eski = [_hw("Matematik", f"Sayfa {i}", f"{i:02d}.03.2026 23:59", yaptim=True) for i in range(1, 13)]
    metin = odev_listesi_metni([*eski, *ROWS], SIMDI)
    assert "HAFTA İÇİ" in _bolum(metin, "YAPTIM")
    assert "Sayfa 1 " not in metin
    assert "14 günden eski 12 ödev" in metin     # left out, and said so


def test_uzun_aciklama_kesildigini_belli_eder():
    uzun = _hw("Türkçe", "Test", "28.09.2026 12:00", aciklama="kelime " * 100)
    satir = _bolum(odev_listesi_metni([uzun], SIMDI), "YAPILACAK")
    assert satir.rstrip().endswith("…")
