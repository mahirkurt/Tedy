"""Assistant uploads (spec §2). Type from leading bytes. No Flask, no Pillow."""
from __future__ import annotations

import re
import zipfile
import zlib
import xml.etree.ElementTree as ET
from io import BytesIO
from pathlib import Path

MIB = 1024 * 1024
SINIR = {"gorsel": 12 * MIB, "pdf": 10 * MIB, "docx": 5 * MIB, "txt": 5 * MIB}
MESAJ_SINIRI = 4
ISTEK_SINIRI = 10
SAYFA_SINIRI = 50
KIMLIK_RE = re.compile(r"^[0-9a-f]{32}$")
_SAYFA = re.compile(br"/Type\s*/Page(?!s)\b")
TUR_ETIKETI = {"gorsel": "Görsel", "pdf": "PDF", "docx": "Word", "txt": "Metin"}
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_CUMLE_413 = {
    "gorsel": "Görsel 12 MB sınırını aşıyor.",
    "pdf": "PDF 10 MB sınırını aşıyor.",
    "docx": "Dosya 5 MB sınırını aşıyor.",
    "txt": "Dosya 5 MB sınırını aşıyor.",
}


class YuklemeHatasi(ValueError):
    def __init__(self, status: int, cumle: str):
        super().__init__(cumle)
        self.status = status
        self.cumle = cumle


def ad_temizle(ad: str) -> str:
    ad = Path(str(ad or "")).name.replace("\x00", "").strip()
    return (ad or "dosya")[:180]


def tur_tespit(veri: bytes) -> str:
    if veri.startswith(b"\xff\xd8\xff") or veri.startswith(b"\x89PNG\r\n\x1a\n"):
        return "gorsel"
    if veri.startswith((b"GIF87a", b"GIF89a")):
        return "gorsel"
    if len(veri) >= 12 and veri[:4] == b"RIFF" and veri[8:12] == b"WEBP":
        return "gorsel"
    if veri.startswith(b"%PDF-"):
        return "pdf"
    if veri.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
        try:
            with zipfile.ZipFile(BytesIO(veri)) as zf:
                if "word/document.xml" in zf.namelist():
                    return "docx"
        except zipfile.BadZipFile:
            pass
        raise YuklemeHatasi(415, "Bu dosya biçimi okunamadı.")
    # HEIC/HEIF and other ISO BMFF boxes are valid UTF-8 (NUL + ASCII) but not text.
    if len(veri) >= 12 and veri[4:8] == b"ftyp":
        raise YuklemeHatasi(415, "Bu dosya biçimi okunamadı.")
    try:
        veri.decode("utf-8")
    except UnicodeDecodeError:
        raise YuklemeHatasi(415, "Bu dosya biçimi okunamadı.") from None
    return "txt"


def _pdf_metinleri(veri: bytes) -> list[bytes]:
    parcalar = [veri]
    bas = 0
    while True:
        i = veri.find(b"stream", bas)
        if i < 0:
            break
        if i + 6 < len(veri) and veri[i + 6:i + 7] not in (b"\n", b"\r"):
            bas = i + 6
            continue
        sozluk_basi = veri.rfind(b"<<", max(0, i - 8192), i)
        sozluk = veri[sozluk_basi:i] if sozluk_basi >= 0 else b""
        veri_bas = i + 8 if veri[i + 6:i + 8] == b"\r\n" else i + 7
        son = veri.find(b"endstream", veri_bas)
        if son < 0:
            break
        ham = veri[veri_bas:son]
        if ham.endswith(b"\r\n"):
            ham = ham[:-2]
        elif ham.endswith((b"\n", b"\r")):
            ham = ham[:-1]
        bas = son + len(b"endstream")
        if b"/FlateDecode" not in sozluk:
            continue
        try:
            parcalar.append(zlib.decompress(ham))
        except zlib.error:
            continue
    return parcalar


def pdf_sayfa_sayisi(veri: bytes) -> int:
    return sum(len(_SAYFA.findall(parca)) for parca in _pdf_metinleri(veri))


def sinir_denetle(tur: str, veri: bytes) -> None:
    if len(veri) > SINIR[tur]:
        raise YuklemeHatasi(413, _CUMLE_413[tur])
    if tur == "pdf" and pdf_sayfa_sayisi(veri) > SAYFA_SINIRI:
        raise YuklemeHatasi(413, "PDF 50 sayfa sınırını aşıyor.")


def docx_metni(veri: bytes) -> str:
    try:
        with zipfile.ZipFile(BytesIO(veri)) as zf:
            xml = zf.read("word/document.xml")
        kok = ET.fromstring(xml)
    except (zipfile.BadZipFile, KeyError, ET.ParseError):
        raise YuklemeHatasi(415, "Bu Word dosyası okunamadı.") from None
    paragraflar = []
    for p in kok.iter(f"{_W}p"):
        metin = "".join(t.text or "" for t in p.iter(f"{_W}t"))
        if metin:
            paragraflar.append(metin)
    return "\n".join(paragraflar)


def txt_metni(veri: bytes) -> str:
    try:
        return veri.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise YuklemeHatasi(415, "Bu metin UTF-8 olarak okunamadı.") from None
