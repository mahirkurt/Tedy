"""Assistant uploads (spec §2). Type from leading bytes. No Flask, no Pillow."""
from __future__ import annotations

import base64
import json
import re
import uuid
import zipfile
import zlib
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path

from src.json_utils import atomic_json_dump
from src.module_ticket import email_hash

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


_OTUZ = timedelta(days=30)


def _zaman(an: datetime) -> str:
    if an.tzinfo is None:
        an = an.replace(tzinfo=timezone.utc)
    return an.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _an(metin: str) -> datetime | None:
    try:
        return datetime.strptime(metin, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


class EkDeposu:
    def __init__(self, output_dir: Path):
        self.kok = Path(output_dir) / "assistant_uploads"

    def _dizin(self, email: str) -> Path:
        return self.kok / email_hash(email)

    def kaydet(self, email: str, ad: str, tur: str, boyut: int,
               icerik: bytes, simdi: datetime) -> dict:
        self.temizlik(simdi)
        kimlik = uuid.uuid4().hex
        dizin = self._dizin(email)
        dizin.mkdir(parents=True, exist_ok=True)
        gecici = dizin / f"{kimlik}.part"
        gecici.write_bytes(icerik)
        hedef = dizin / kimlik
        gecici.replace(hedef)
        meta = {
            "sahip_email": email,
            "ad": ad_temizle(ad),
            "tur": tur,
            "boyut": boyut,
            "zaman": _zaman(simdi),
            "bagli_sohbet": None,
        }
        try:
            atomic_json_dump(meta, str(dizin / f"{kimlik}.json"))
        except BaseException:
            hedef.unlink(missing_ok=True)
            raise
        return {"id": kimlik, "ad": meta["ad"], "tur": tur, "boyut": boyut}

    def oku(self, email: str, kimlik: str) -> tuple[dict, bytes] | None:
        if not isinstance(kimlik, str) or not KIMLIK_RE.fullmatch(kimlik):
            return None
        dizin = self._dizin(email)
        meta_yol, veri_yol = dizin / f"{kimlik}.json", dizin / kimlik
        try:
            meta = json.loads(meta_yol.read_text(encoding="utf-8"))
            veri = veri_yol.read_bytes()
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(meta, dict) or meta.get("sahip_email") != email:
            return None
        meta["id"] = kimlik
        return meta, veri

    def _meta_dosyalari(self):
        if not self.kok.is_dir():
            return
        for kisi in self.kok.iterdir():
            if not kisi.is_dir():
                continue
            for yol in kisi.glob("*.json"):
                yield yol

    def temizlik(self, simdi: datetime) -> int:
        if simdi.tzinfo is None:
            simdi = simdi.replace(tzinfo=timezone.utc)
        silinen = 0
        for yol in list(self._meta_dosyalari()):
            try:
                meta = json.loads(yol.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(meta, dict) or meta.get("bagli_sohbet") is not None:
                continue
            an = _an(meta.get("zaman"))
            if an is None or simdi - an < _OTUZ:
                continue
            kimlik = yol.stem
            if not KIMLIK_RE.fullmatch(kimlik):
                continue
            yol.unlink(missing_ok=True)
            (yol.parent / kimlik).unlink(missing_ok=True)
            silinen += 1
        return silinen

    def sohbet_eklerini_sil(self, sohbet_id: str) -> int:
        if not sohbet_id:
            return 0
        silinen = 0
        for yol in list(self._meta_dosyalari()):
            try:
                meta = json.loads(yol.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(meta, dict) or meta.get("bagli_sohbet") != sohbet_id:
                continue
            kimlik = yol.stem
            yol.unlink(missing_ok=True)
            if KIMLIK_RE.fullmatch(kimlik):
                (yol.parent / kimlik).unlink(missing_ok=True)
            silinen += 1
        return silinen


def atif(meta: dict) -> dict:
    return {
        "kind": "yuklenen-dosya",
        "label": meta["ad"],
        "locator": {"upload_id": meta["id"], "tur": meta["tur"]},
        "snippet": TUR_ETIKETI[meta["tur"]],
        "confidence": 0.9,
    }


def icerik_bloku(tur: str, icerik: bytes) -> dict | None:
    if tur == "gorsel":
        return {"type": "image", "source": {
            "type": "base64", "media_type": "image/jpeg",
            "data": base64.b64encode(icerik).decode("ascii")}}
    if tur == "pdf":
        return {"type": "document", "source": {
            "type": "base64", "media_type": "application/pdf",
            "data": base64.b64encode(icerik).decode("ascii")}}
    metin = icerik.decode("utf-8")
    if not metin.strip():
        return None
    return {"type": "text", "text": metin}
