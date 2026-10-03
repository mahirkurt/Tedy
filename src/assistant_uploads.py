"""Assistant uploads (spec §2). Type from leading bytes. No Flask, no Pillow."""
from __future__ import annotations

import base64
import json
import re
import uuid
import zipfile
import fcntl
import subprocess
import tempfile
from contextlib import contextmanager
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
DOCX_XML_SINIRI = 8 * MIB
KISI_KOTASI = 200 * MIB
PDFINFO_SURESI = 10
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
    if not veri:
        raise YuklemeHatasi(400, "Boş dosya gönderildi.")
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
    if any(c < 32 and c not in (9, 10, 13) for c in veri):
        raise YuklemeHatasi(415, "Bu dosya biçimi okunamadı.")
    return "txt"


def pdf_sayfa_sayisi(veri: bytes) -> int:
    # Let Poppler parse the page tree, including compressed object streams.
    # Never decompress arbitrary PDF streams inside a Gunicorn worker.
    with tempfile.NamedTemporaryFile(suffix=".pdf") as dosya:
        dosya.write(veri)
        dosya.flush()
        try:
            sonuc = subprocess.run(["pdfinfo", dosya.name], capture_output=True,
                                    text=True, timeout=PDFINFO_SURESI)
        except (subprocess.TimeoutExpired, OSError):
            raise YuklemeHatasi(415, "Bu PDF okunamadı.") from None
    if sonuc.returncode == 0:
        sayfa = re.search(r"^Pages:\s+([0-9]+)\s*$", sonuc.stdout, re.MULTILINE)
        if sayfa and int(sayfa.group(1)) > 0:
            return int(sayfa.group(1))
    raise YuklemeHatasi(415, "Bu PDF okunamadı.")


def sinir_denetle(tur: str, veri: bytes) -> None:
    if len(veri) > SINIR[tur]:
        raise YuklemeHatasi(413, _CUMLE_413[tur])
    if tur == "pdf" and pdf_sayfa_sayisi(veri) > SAYFA_SINIRI:
        raise YuklemeHatasi(413, "PDF 50 sayfa sınırını aşıyor.")


def docx_metni(veri: bytes) -> str:
    try:
        with zipfile.ZipFile(BytesIO(veri)) as zf:
            if sum(info.file_size for info in zf.infolist()) > DOCX_XML_SINIRI:
                raise YuklemeHatasi(413, "Açılan Word içeriği 8 MB sınırını aşıyor.")
            with zf.open("word/document.xml") as kaynak:
                xml = kaynak.read(DOCX_XML_SINIRI + 1)
            if len(xml) > DOCX_XML_SINIRI:
                raise YuklemeHatasi(413, "Açılan Word içeriği 8 MB sınırını aşıyor.")
        # OOXML needs no DTD. Removing NUL also detects UTF-16/32 markup.
        if re.search(br"<!\s*(?:DOCTYPE|ENTITY)\b", xml.replace(b"\x00", b""), re.I):
            raise YuklemeHatasi(415, "Bu Word dosyası okunamadı.")
        kok = ET.fromstring(xml)
    except (zipfile.BadZipFile, KeyError, ET.ParseError, RuntimeError):
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


@contextmanager
def _kilit(dizin: Path):
    dizin.mkdir(parents=True, exist_ok=True)
    with (dizin / ".lock").open("a+") as kilit:
        fcntl.flock(kilit, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(kilit, fcntl.LOCK_UN)


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
        with _kilit(dizin):
            toplam = sum(p.stat().st_size for p in dizin.iterdir() if KIMLIK_RE.fullmatch(p.name))
            if toplam + len(icerik) > KISI_KOTASI:
                raise YuklemeHatasi(507, "Yükleme alanın doldu; kullanmadığın dosyaları silebilirsin.")
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
                "son_kullanim": _zaman(simdi),
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

    def sil(self, email: str, kimlik: str) -> bool:
        if not isinstance(kimlik, str) or not KIMLIK_RE.fullmatch(kimlik):
            return False
        dizin = self._dizin(email)
        if not dizin.is_dir():
            return False
        with _kilit(dizin):
            if self.oku(email, kimlik) is None:
                return False
            (dizin / f"{kimlik}.json").unlink(missing_ok=True)
            (dizin / kimlik).unlink(missing_ok=True)
        return True

    def dokun(self, email: str, kimlik: str, simdi: datetime) -> None:
        if not isinstance(kimlik, str) or not KIMLIK_RE.fullmatch(kimlik):
            return
        dizin = self._dizin(email)
        if not dizin.is_dir():
            return
        with _kilit(dizin):
            bulunan = self.oku(email, kimlik)
            if bulunan is None:
                return
            meta = bulunan[0]
            meta.pop("id", None)
            meta["son_kullanim"] = _zaman(simdi)
            atomic_json_dump(meta, str(dizin / f"{kimlik}.json"))

    def _meta_dosyalari(self):
        if not self.kok.is_dir():
            return
        for kisi in self.kok.iterdir():
            if not kisi.is_dir():
                continue
            for yol in kisi.glob("*.json"):
                yield yol

    def bagla(self, email: str, kimlik: str, sohbet_id: str) -> None:
        if not isinstance(kimlik, str) or not KIMLIK_RE.fullmatch(kimlik):
            return
        with _kilit(self._dizin(email)):
            bulunan = self.oku(email, kimlik)
            if bulunan is None:
                return
            meta, _veri = bulunan
            if meta.get("bagli_sohbet") is None:
                meta["bagli_sohbet"] = sohbet_id
                meta.pop("id", None)
                atomic_json_dump(meta, str(self._dizin(email) / f"{kimlik}.json"))

    def temizlik(self, simdi: datetime) -> int:
        if simdi.tzinfo is None:
            simdi = simdi.replace(tzinfo=timezone.utc)
        silinen = 0
        for yol in list(self._meta_dosyalari()):
            with _kilit(yol.parent):
                try:
                    meta = json.loads(yol.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                if not isinstance(meta, dict) or meta.get("bagli_sohbet") is not None:
                    continue
                an = _an(meta.get("son_kullanim") or meta.get("zaman"))
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
            with _kilit(yol.parent):
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
