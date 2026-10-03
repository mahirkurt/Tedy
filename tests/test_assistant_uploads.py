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


def _pdf_sayfalar(n: int) -> bytes:
    govde = [b"%PDF-1.4\n", b"99 0 obj\n<< /Type /Pages /Count 1 >>\nendobj\n"]
    for i in range(1, n + 1):
        govde.append(f"{i} 0 obj\n<< /Type /Page >>\nendobj\n".encode())
    govde.append(b"%%EOF\n")
    return b"".join(govde)


def _pdf_sayfalar_flate(n: int) -> bytes:
    import zlib
    ic = b"\n".join(b"<< /Type /Page >>" for _ in range(n))
    sik = zlib.compress(ic)
    ham = (
        b"%PDF-1.4\n1 0 obj\n<< /Filter /FlateDecode /Length "
        + str(len(sik)).encode() + b" >>\nstream\n" + sik
        + b"\nendstream\nendobj\n%%EOF\n"
    )
    assert b"/Type /Page" not in ham
    return ham


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
