"""Dosya yükleme türü ve metin çıkarımı (spec §2).

Tür ilk baytlardan gelir. Uzantı ve istemci MIME'ı okunmaz. Ağ yok.
"""
import io
import zipfile

import pytest

from src.assistant_uploads import (
    SINIR, YuklemeHatasi, ad_temizle, docx_metni, sinir_denetle, tur_tespit, txt_metni,
)


def _docx(metin: str) -> bytes:
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body><w:p><w:r><w:t>{metin}</w:t></w:r></w:p></w:body></w:document>"
    ).encode()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("word/document.xml", xml)
    return buf.getvalue()


@pytest.mark.parametrize("bas, tur", [
    (b"\xff\xd8\xff\x00", "gorsel"),
    (b"\x89PNG\r\n\x1a\n", "gorsel"),
    (b"GIF89a", "gorsel"),
    (b"RIFF\x00\x00\x00\x00WEBP", "gorsel"),
    (b"%PDF-1.7", "pdf"),
])
def test_sihirli_bayt(bas, tur):
    assert tur_tespit(bas) == tur


def test_uzanti_ve_mime_okunmaz():
    assert tur_tespit(b"%PDF-1.4 sahte.docx") == "pdf"


def test_heic_415():
    with pytest.raises(YuklemeHatasi) as hata:
        tur_tespit(b"\x00\x00\x00\x18ftypheic" + b"\x00" * 8)
    assert hata.value.status == 415
    assert hata.value.cumle == "Bu dosya biçimi okunamadı."
    assert "heic" not in hata.value.cumle.lower()


def test_docx_olmayan_zip_415():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("readme.txt", "merhaba")
    with pytest.raises(YuklemeHatasi) as hata:
        tur_tespit(buf.getvalue())
    assert hata.value.status == 415


def test_docx_metni_paragrafdan_gelir():
    veri = _docx("Paydalar toplanmaz.")
    assert tur_tespit(veri) == "docx"
    assert docx_metni(veri) == "Paydalar toplanmaz."


def test_bozuk_docx_415():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("word/document.xml", b"<degil")
    with pytest.raises(YuklemeHatasi) as hata:
        docx_metni(buf.getvalue())
    assert hata.value.status == 415
    assert hata.value.cumle == "Bu Word dosyası okunamadı."


def test_txt_bomlu_ve_bomsuz():
    assert txt_metni("ölçü".encode()) == "ölçü"
    assert txt_metni(b"\xef\xbb\xbfmerhaba") == "merhaba"
    assert tur_tespit("not".encode()) == "txt"


def test_txt_utf8_degilse_415():
    with pytest.raises(YuklemeHatasi) as hata:
        txt_metni(b"\xff\xfe\x00")
    assert hata.value.status == 415
    assert hata.value.cumle == "Bu metin UTF-8 olarak okunamadı."


@pytest.mark.parametrize("tur, fazlalik", [
    ("gorsel", b"\xff\xd8\xff"),
    ("pdf", b"%PDF-"),
    ("txt", b"a"),
])
def test_sinir_asimi_413_ve_cumle_yol_tasimaz(tur, fazlalik):
    veri = fazlalik + b"\x00" * SINIR[tur]
    with pytest.raises(YuklemeHatasi) as hata:
        sinir_denetle(tur, veri)
    assert hata.value.status == 413
    assert "/" not in hata.value.cumle and "Error" not in hata.value.cumle


def test_sinirin_kendisi_kabul():
    sinir_denetle("txt", b"a" * SINIR["txt"])


def _pdf_sayfalar(n: int, akis: bytes = b"") -> bytes:
    # Minimal real PDF: a catalog, page tree and cross-reference table. The old
    # regex fixture lacked these and accepted files no PDF reader could open.
    nesneler = [b"<< /Type /Catalog /Pages 2 0 R >>",
                f"<< /Type /Pages /Count {n} /Kids [".encode()
                + b" ".join(f"{i + 3} 0 R".encode() for i in range(n)) + b"] >>"]
    for i in range(n):
        nesneler.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100]"
                        + (f" /Contents {n + 3} 0 R".encode() if akis else b"") + b" >>")
    if akis:
        nesneler.append(b"<< /Filter /FlateDecode /Length " + str(len(akis)).encode()
                        + b" >>\nstream\n" + akis + b"\nendstream")
    sonuc = bytearray(b"%PDF-1.4\n")
    yerler = [0]
    for i, nesne in enumerate(nesneler, 1):
        yerler.append(len(sonuc))
        sonuc.extend(f"{i} 0 obj\n".encode() + nesne + b"\nendobj\n")
    xref = len(sonuc)
    sonuc.extend(f"xref\n0 {len(yerler)}\n0000000000 65535 f \n".encode())
    for yer in yerler[1:]:
        sonuc.extend(f"{yer:010d} 00000 n \n".encode())
    sonuc.extend(f"trailer\n<< /Size {len(yerler)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(sonuc)


def _pdf_sayfalar_flate(n: int) -> bytes:
    import zlib
    # A compressed content stream mentioning page-looking text must not add
    # fake pages to the page-tree count or expand in the application worker.
    return _pdf_sayfalar(n, zlib.compress(b"/Type /Page " * 1000))


def test_pdf_50_sayfa_kabul_51_413():
    sinir_denetle("pdf", _pdf_sayfalar(50))
    with pytest.raises(YuklemeHatasi) as hata:
        sinir_denetle("pdf", _pdf_sayfalar(51))
    assert hata.value.status == 413
    assert hata.value.cumle == "PDF 50 sayfa sınırını aşıyor."


def test_pdf_sayfa_flate_akista_da_sayilir():
    sinir_denetle("pdf", _pdf_sayfalar_flate(50))
    with pytest.raises(YuklemeHatasi) as hata:
        sinir_denetle("pdf", _pdf_sayfalar_flate(51))
    assert hata.value.cumle == "PDF 50 sayfa sınırını aşıyor."


def test_pdf_boy_sayfadan_once():
    veri = b"%PDF-" + b"\x00" * SINIR["pdf"]
    with pytest.raises(YuklemeHatasi) as hata:
        sinir_denetle("pdf", veri)
    assert hata.value.cumle == "PDF 10 MB sınırını aşıyor."


def test_ad_yol_degil():
    assert ad_temizle("../../etc/passwd") == "passwd"
    assert ad_temizle("") == "dosya"
    assert len(ad_temizle("a" * 500)) == 180


from datetime import datetime, timedelta, timezone

from src.assistant_uploads import EkDeposu
from src.module_ticket import email_hash

FULL = "isikkurtx@gmail.com"
DIGER = "drmahirkurt@gmail.com"
SIMDI = datetime(2026, 10, 3, 6, 0, tzinfo=timezone.utc)


def test_kayit_ozet_dizinde_ve_meta_alani(tmp_path):
    depo = EkDeposu(tmp_path)
    kayit = depo.kaydet(FULL, "../not.txt", "txt", 5, b"merhaba", SIMDI)
    assert kayit["ad"] == "not.txt" and kayit["tur"] == "txt" and kayit["boyut"] == 5
    dizin = tmp_path / "assistant_uploads" / email_hash(FULL)
    assert (dizin / kayit["id"]).read_bytes() == b"merhaba"
    meta, icerik = depo.oku(FULL, kayit["id"])
    assert icerik == b"merhaba"
    assert meta["sahip_email"] == FULL and meta["bagli_sohbet"] is None
    assert meta["zaman"] == "2026-10-03T06:00:00Z"
    assert FULL not in str(dizin)


def test_baskasinin_kimligi_yok_sayilir(tmp_path):
    depo = EkDeposu(tmp_path)
    kayit = depo.kaydet(FULL, "a.txt", "txt", 1, b"a", SIMDI)
    assert depo.oku(DIGER, kayit["id"]) is None
    assert depo.oku(FULL, "a" * 32) is None
    assert depo.oku(FULL, "../" + kayit["id"]) is None


def test_baglanmamis_otuz_gunde_silinir_baglanan_kalir(tmp_path):
    depo = EkDeposu(tmp_path)
    eski = SIMDI - timedelta(days=30)
    genc = SIMDI - timedelta(days=29)
    gitti = depo.kaydet(FULL, "eski.txt", "txt", 1, b"e", eski)
    kalir = depo.kaydet(FULL, "genc.txt", "txt", 1, b"g", genc)
    bagli = depo.kaydet(FULL, "bagli.txt", "txt", 1, b"b", eski)
    meta_yol = tmp_path / "assistant_uploads" / email_hash(FULL) / f"{bagli['id']}.json"
    import json
    meta = json.loads(meta_yol.read_text())
    meta["bagli_sohbet"] = "sohbet-1"
    meta_yol.write_text(json.dumps(meta))
    assert depo.temizlik(SIMDI) == 1
    assert depo.oku(FULL, gitti["id"]) is None
    assert depo.oku(FULL, kalir["id"]) is not None
    assert depo.oku(FULL, bagli["id"]) is not None


def test_sohbet_silme_yalniz_o_sohbetin_ekini_siler(tmp_path):
    depo = EkDeposu(tmp_path)
    bir = depo.kaydet(FULL, "a.txt", "txt", 1, b"a", SIMDI)
    iki = depo.kaydet(DIGER, "b.txt", "txt", 1, b"b", SIMDI)
    import json
    for email, kayit, sohbet in ((FULL, bir, "s1"), (DIGER, iki, "s2")):
        yol = tmp_path / "assistant_uploads" / email_hash(email) / f"{kayit['id']}.json"
        meta = json.loads(yol.read_text())
        meta["bagli_sohbet"] = sohbet
        yol.write_text(json.dumps(meta))
    assert depo.sohbet_eklerini_sil("") == 0
    assert depo.sohbet_eklerini_sil("s1") == 1
    assert depo.oku(FULL, bir["id"]) is None
    assert depo.oku(DIGER, iki["id"]) is not None
