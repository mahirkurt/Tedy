""".docx text through the assistant's FileAdapters (plan 2026-09-28-portal-ekleri,
Görev 4): stdlib zipfile + word/document.xml, no new dependency.

Fix round 1 adds three regression tests for defects a reviewer verified in
the original implementation (see /tmp/test_a_dtd_after_4k.py,
/tmp/test_c_ziplie.py, /tmp/test_d_bad_encoding.py): a DTD/entity gate that
only scanned the first 4096 bytes, a zip-bomb cap that trusted the archive's
own declared (and forgeable) uncompressed size, and a narrow except clause
that let an XML-declared unknown encoding's LookupError escape."""
import struct
import time
import tracemalloc
import zipfile
import zlib

import src.assistant_core as core
from src.assistant_core import AssistantConfig, FileAdapters

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def docx_yaz(yol, govde_xml):
    xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           f'<w:document xmlns:w="{W}"><w:body>{govde_xml}</w:body></w:document>')
    with zipfile.ZipFile(yol, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("word/document.xml", xml)
    return yol


def _adaptor(tmp_path):
    return FileAdapters(AssistantConfig.from_project_root(tmp_path))


def _boyut_yalanli_zip(yol, veri: bytes, yalan_boyut: int = 10):
    """A single-entry zip ("word/document.xml") whose declared uncompressed
    size — in both the local file header and the central directory — is
    `yalan_boyut`, while the entry's real deflate stream decompresses to the
    full `veri`. Mirrors the reviewer's throwaway script
    (/tmp/test_c_ziplie.py): ZipFile.writestr always computes the true size,
    so a lying entry has to be built by hand with struct, the way a hostile
    archive would be."""
    co = zlib.compressobj(9, zlib.DEFLATED, -15)
    compressed = co.compress(veri) + co.flush()
    crc = zlib.crc32(veri) & 0xFFFFFFFF
    filename = b"word/document.xml"
    mtime, mdate = 0, 0x21
    local_header = struct.pack(
        "<4sHHHHHIIIHH", b"PK\x03\x04", 20, 0, 8, mtime, mdate, crc,
        len(compressed), yalan_boyut, len(filename), 0,
    )
    local_record = local_header + filename + compressed
    central_header = struct.pack(
        "<4sHHHHHHIIIHHHHHII", b"PK\x01\x02", 20, 20, 0, 8, mtime, mdate,
        crc, len(compressed), yalan_boyut, len(filename), 0, 0, 0, 0, 0, 0,
    )
    central_record = central_header + filename
    cd_offset = len(local_record)
    eocd = struct.pack(
        "<4sHHHHIIH", b"PK\x05\x06", 0, 0, 1, 1, len(central_record), cd_offset, 0,
    )
    with open(yol, "wb") as f:
        f.write(local_record)
        f.write(central_record)
        f.write(eocd)
    return yol


def test_paragraflar_sekme_ve_satir_sonu_okunur(tmp_path):
    yol = docx_yaz(tmp_path / "odev.docx",
                   "<w:p><w:r><w:t>Bumerang kitabı çalışması</w:t></w:r></w:p>"
                   "<w:p><w:r><w:t>Soru 1</w:t><w:tab/><w:t>(10 puan)</w:t><w:br/>"
                   "<w:t xml:space=\"preserve\">Açıkla.</w:t></w:r></w:p>"
                   "<w:p></w:p>")
    sonuc = _adaptor(tmp_path).extract(yol, "content/portal-ekleri/odev.docx")
    assert sonuc["source_kind"] == "docx"
    assert sonuc["text"] == "Bumerang kitabı çalışması\n\nSoru 1\t(10 puan)\nAçıkla."


def test_bozuk_docx_metadata_olur_cop_metin_degil(tmp_path):
    yol = tmp_path / "bozuk.docx"
    yol.write_bytes(b"PK" + b"0" * 200)
    sonuc = _adaptor(tmp_path).extract(yol, "content/portal-ekleri/bozuk.docx")
    assert sonuc["source_kind"] == "metadata" and sonuc["warnings"] == ["docx_no_text"]
    assert "PK00" not in sonuc["text"]


def test_document_xml_yoksa_metadata(tmp_path):
    yol = tmp_path / "bos.docx"
    with zipfile.ZipFile(yol, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
    assert _adaptor(tmp_path).extract(yol, "x.docx")["source_kind"] == "metadata"


def test_asiri_buyuk_document_xml_okunmaz(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "DOCX_XML_SINIRI", 10)
    yol = docx_yaz(tmp_path / "buyuk.docx", "<w:p><w:r><w:t>uzun metin</w:t></w:r></w:p>")
    assert _adaptor(tmp_path).extract(yol, "x.docx")["source_kind"] == "metadata"


def test_dtd_tasiyan_document_xml_ayristirilmaz(tmp_path):
    # An attachment is someone else's file: entity expansion ("billion laughs")
    # or an external entity must never run. A real .docx declares no DTD.
    xml = ('<?xml version="1.0"?><!DOCTYPE w:document [<!ENTITY a "Bumerang">]>'
           f'<w:document xmlns:w="{W}"><w:body><w:p><w:r><w:t>&a;</w:t></w:r></w:p></w:body></w:document>')
    yol = tmp_path / "dtd.docx"
    with zipfile.ZipFile(yol, "w") as z:
        z.writestr("word/document.xml", xml)
    sonuc = _adaptor(tmp_path).extract(yol, "x.docx")
    assert sonuc["source_kind"] == "metadata" and "Bumerang" not in sonuc["text"]


def test_dtd_4096_bayttan_sonra_da_yakalanir(tmp_path):
    # Fix round 1, risk (a) — reviewer /tmp/test_a_dtd_after_4k.py: the
    # original gate scanned only veri[:4096]. A long leading XML comment
    # pushes the real "<!DOCTYPE"/"<!ENTITY" text past byte 4096, and the
    # entity was expanded by ElementTree.fromstring.
    dolgu = "<!--" + ("x" * 4300) + "-->"
    xml = (
        '<?xml version="1.0"?>' + dolgu
        + '<!DOCTYPE w:document [<!ENTITY a "PWNED_ENTITY_EXPANDED">]>'
        + f'<w:document xmlns:w="{W}"><w:body><w:p><w:r><w:t>&a;</w:t></w:r></w:p></w:body></w:document>'
    )
    yol = tmp_path / "dtd_4096_sonra.docx"
    with zipfile.ZipFile(yol, "w") as z:
        z.writestr("word/document.xml", xml)
    sonuc = _adaptor(tmp_path).extract(yol, "x.docx")
    assert sonuc["source_kind"] == "metadata"
    assert "PWNED_ENTITY_EXPANDED" not in sonuc["text"]


def test_zip_boyut_yalani_erken_durup_metadata_olur(tmp_path, monkeypatch):
    # Fix round 1, risk (c) — reviewer /tmp/test_c_ziplie.py: the cap
    # trusted ZipInfo.file_size, which is declared by the archive's own
    # central directory. A tiny declared size whose real deflate stream
    # decompresses to something far larger passed the pre-check, and
    # arsiv.read() then materialised the whole thing before ElementTree
    # ever saw it. Here the real content IS valid, parseable XML, so
    # without the fix this would return real (huge) text, not metadata.
    monkeypatch.setattr(core, "DOCX_XML_SINIRI", 1024 * 1024)  # 1 MiB cap
    onek = (
        '<?xml version="1.0"?>'
        f'<w:document xmlns:w="{W}"><w:body><w:p><w:r>'
        '<w:t xml:space="preserve">'
    )
    sonek = "</w:t></w:r></w:p></w:body></w:document>"
    gercek_boyut = 8 * 1024 * 1024  # 8x the (monkeypatched) 1 MiB cap
    dolgu = "A" * (gercek_boyut - len(onek) - len(sonek))
    xml = (onek + dolgu + sonek).encode("ascii")
    yol = _boyut_yalanli_zip(tmp_path / "sisirilmis.docx", xml)

    tracemalloc.start()
    try:
        t0 = time.monotonic()
        sonuc = _adaptor(tmp_path).extract(yol, "x.docx")
        sure = time.monotonic() - t0
        _, tepe = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert sonuc["source_kind"] == "metadata"
    assert sure < 1.0
    # The real payload is 8 MiB; a bounded read that stops as soon as the
    # 1 MiB cap is exceeded never gets near half of that.
    assert tepe < len(xml) / 2


def test_bilinmeyen_kodlama_metadata_olur_hata_firlatmaz(tmp_path):
    # Fix round 1, risk (d) — reviewer /tmp/test_d_bad_encoding.py: an
    # XML-declared encoding name Python's codec registry does not know
    # makes ElementTree.fromstring raise LookupError, which the original
    # except tuple did not include — it would have escaped _extract_docx_text
    # and, with no per-file guard in reindex(), aborted the whole index
    # update over one bad attachment.
    xml = '<?xml version="1.0" encoding="totally-bogus-encoding"?><a>x</a>'
    yol = tmp_path / "kodlama.docx"
    with zipfile.ZipFile(yol, "w") as z:
        z.writestr("word/document.xml", xml.encode("ascii"))
    sonuc = _adaptor(tmp_path).extract(yol, "x.docx")  # must not raise
    assert sonuc["source_kind"] == "metadata"
