""".docx text through the assistant's FileAdapters (plan 2026-09-28-portal-ekleri,
Görev 4): stdlib zipfile + word/document.xml, no new dependency."""
import zipfile

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
