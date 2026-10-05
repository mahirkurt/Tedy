"""Assistant chats (spec §3). No Flask."""
from __future__ import annotations

import json
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from src.assistant_alistirma import SON_CALISILAN, calisilan_konular, hafta_araligi, zayif_konular

_SEM = """
CREATE TABLE IF NOT EXISTS sohbet (
    id TEXT PRIMARY KEY,
    sahip_email TEXT NOT NULL,
    baslik TEXT NOT NULL DEFAULT '',
    ogretmen TEXT NOT NULL,
    olusturma TEXT NOT NULL,
    guncelleme TEXT NOT NULL,
    ozet TEXT
);
CREATE TABLE IF NOT EXISTS mesaj (
    id TEXT PRIMARY KEY,
    sohbet_id TEXT NOT NULL,
    rol TEXT NOT NULL,
    icerik TEXT NOT NULL,
    atiflar_json TEXT NOT NULL DEFAULT '[]',
    ekler_json TEXT NOT NULL DEFAULT '[]',
    meta_json TEXT NOT NULL DEFAULT '{}',
    kartlar_json TEXT NOT NULL DEFAULT '{}',
    ogretmen TEXT NOT NULL,
    zaman TEXT NOT NULL,
    sira INTEGER NOT NULL,
    istek_id TEXT
);
CREATE INDEX IF NOT EXISTS mesaj_sohbet_sira ON mesaj(sohbet_id, sira);
CREATE TABLE IF NOT EXISTS ogrenci_notu (
    id TEXT PRIMARY KEY,
    metin TEXT NOT NULL,
    kaynak_sohbet TEXT,
    zaman TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS alistirma (
    id TEXT PRIMARY KEY, sohbet_id TEXT NOT NULL, mesaj_id TEXT,
    sahip_email TEXT NOT NULL, ogretmen TEXT NOT NULL, baslik TEXT NOT NULL,
    ders TEXT NOT NULL, konu TEXT NOT NULL, kazanim_kodu TEXT, zorluk TEXT NOT NULL,
    sorular_json TEXT NOT NULL, zaman TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS alistirma_mesaj ON alistirma(mesaj_id);
CREATE TABLE IF NOT EXISTS alistirma_cevap (
    id TEXT PRIMARY KEY, alistirma_id TEXT NOT NULL, sira INTEGER NOT NULL,
    ders TEXT NOT NULL, konu TEXT NOT NULL, kazanim_kodu TEXT,
    dogru INTEGER NOT NULL, zaman TEXT NOT NULL,
    UNIQUE (alistirma_id, sira)
);
CREATE TABLE IF NOT EXISTS calisma_degerlendirme (
    id TEXT PRIMARY KEY, sohbet_id TEXT NOT NULL, ek_id TEXT NOT NULL,
    ogretmen TEXT NOT NULL, guclu_yanlar TEXT NOT NULL, duzeyler TEXT NOT NULL,
    sonraki_adim TEXT NOT NULL, okur TEXT NOT NULL, zaman TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS calisilan_konu (
    id TEXT PRIMARY KEY, sohbet_id TEXT NOT NULL, mesaj_id TEXT NOT NULL,
    sahip_email TEXT NOT NULL, ogretmen TEXT NOT NULL, kazanim_kodu TEXT NOT NULL,
    sayfa_basligi TEXT NOT NULL, zaman TEXT NOT NULL
);
"""


def zaman_yazi(an: datetime) -> str:
    if an.tzinfo is None:
        an = an.replace(tzinfo=timezone.utc)
    return an.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def hassas_not(metin: str) -> bool:
    katli = metin.replace("İ", "i").replace("I", "ı").casefold()
    tokenlar = set(re.findall(r"[^\W\d_]+", katli, flags=re.UNICODE))
    yasak = {"sağlık", "saglik", "hastalık", "hastalik", "hasta", "ilaç", "ilac",
             "tedavi", "teşhis", "teshis", "tanı", "tani", "boşanma", "bosanma"}
    return bool(tokenlar & yasak) or "@" in metin or re.search(r"\d{10}", metin) is not None


def gorunen_kartlar(payload: dict | None) -> dict:
    """Only the two reader-facing interaction schemas may survive a retry.

    No arbitrary response/model metadata or extra nested keys are copied.
    """
    if not isinstance(payload, dict):
        return {}
    sonuc = {}
    netlestirme = payload.get("netlestirme")
    if isinstance(netlestirme, dict):
        soru, secenekler = netlestirme.get("soru"), netlestirme.get("secenekler")
        if (isinstance(soru, str) and 0 < len(soru.strip()) <= 140
                and isinstance(secenekler, list) and 2 <= len(secenekler) <= 4
                and all(isinstance(s, str) and 0 < len(s.strip()) <= 60 for s in secenekler)):
            sonuc["netlestirme"] = {"soru": soru.strip(), "secenekler": [s.strip() for s in secenekler]}
    oneri = payload.get("odev_onerisi")
    if (isinstance(oneri, dict) and isinstance(oneri.get("ek_id"), str)
            and re.fullmatch(r"[0-9a-f]{32}", oneri["ek_id"])
            and isinstance(oneri.get("adaylar"), list)):
        adaylar = []
        for aday in oneri["adaylar"][:20]:
            if not isinstance(aday, dict):
                continue
            temiz = {alan: aday[alan][:sinir] for alan, sinir in (
                ("ders", 120), ("baslik", 280), ("teslim", 80), ("aciklama", 4000))
                if isinstance(aday.get(alan), str)}
            if len(temiz) != 4:
                continue
            eksik = aday.get("eksik") if isinstance(aday.get("eksik"), list) else []
            temiz["eksik"] = [alan for alan in ("ders", "baslik", "teslim") if alan in eksik]
            adaylar.append(temiz)
        if adaylar:
            sonuc["odev_onerisi"] = {"ek_id": oneri["ek_id"], "adaylar": adaylar}
            if isinstance(oneri.get("photo_hash"), str) and re.fullmatch(r"[0-9a-f]{16}", oneri["photo_hash"]):
                sonuc["odev_onerisi"]["photo_hash"] = oneri["photo_hash"]
    return sonuc


class SohbetDeposu:
    def __init__(self, yol: Path):
        self.yol = Path(yol)
        self.yol.parent.mkdir(parents=True, exist_ok=True)
        with self._baglan() as conn:
            conn.executescript(_SEM)
            conn.execute("BEGIN IMMEDIATE")
            try:
                kolonlar = {r["name"] for r in conn.execute("PRAGMA table_info(mesaj)")}
                if "istek_id" not in kolonlar:
                    conn.execute("ALTER TABLE mesaj ADD COLUMN istek_id TEXT")
                if "kartlar_json" not in kolonlar:
                    conn.execute("ALTER TABLE mesaj ADD COLUMN kartlar_json TEXT NOT NULL DEFAULT '{}'")
                conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS mesaj_istek_rol "
                             "ON mesaj(sohbet_id, istek_id, rol) WHERE istek_id IS NOT NULL")
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise

    @contextmanager
    def _baglan(self):
        conn = sqlite3.connect(self.yol, timeout=5, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        try:
            yield conn
        finally:
            conn.close()

    def journal_mode(self) -> str:
        with self._baglan() as conn:
            return conn.execute("PRAGMA journal_mode").fetchone()[0]

    def yarat(self, email: str, ogretmen: str, simdi: datetime) -> str:
        sid = uuid.uuid4().hex
        yazi = zaman_yazi(simdi)
        with self._baglan() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    "INSERT INTO sohbet (id, sahip_email, baslik, ogretmen, olusturma, guncelleme, ozet) "
                    "VALUES (?, ?, '', ?, ?, ?, NULL)",
                    (sid, email, ogretmen, yazi, yazi),
                )
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
        return sid

    def getir(self, sid: str) -> dict | None:
        with self._baglan() as conn:
            row = conn.execute("SELECT * FROM sohbet WHERE id = ?", (sid,)).fetchone()
        return dict(row) if row else None

    def liste(self, email: str) -> list[dict]:
        with self._baglan() as conn:
            rows = conn.execute(
                "SELECT id, baslik, ogretmen, olusturma, guncelleme FROM sohbet "
                "WHERE sahip_email = ? AND baslik <> '' ORDER BY guncelleme DESC, id ASC",
                (email,),
            ).fetchall()
        return [dict(r) for r in rows]

    def mesaj_ekle(self, sid: str, rol: str, icerik: str, ogretmen: str,
                   ekler: list, simdi: datetime, atiflar: list | None = None,
                   istek_id: str | None = None, kartlar: dict | None = None,
                   meta: dict | None = None) -> str:
        mid = uuid.uuid4().hex
        yazi = zaman_yazi(simdi)
        with self._baglan() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                if istek_id:
                    onceki = conn.execute(
                        "SELECT id FROM mesaj WHERE sohbet_id = ? AND istek_id = ? AND rol = ?",
                        (sid, istek_id, rol),
                    ).fetchone()
                    if onceki:
                        conn.execute("COMMIT")
                        return onceki["id"]
                conn.execute(
                    "INSERT INTO mesaj (id, sohbet_id, rol, icerik, atiflar_json, ekler_json, "
                    "meta_json, ogretmen, zaman, sira, istek_id, kartlar_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, "
                    "(SELECT COALESCE(MAX(sira), 0) + 1 FROM mesaj), ?, ?)",
                    (mid, sid, rol, icerik, json.dumps(atiflar or [], ensure_ascii=False),
                     json.dumps(ekler, ensure_ascii=False), json.dumps(meta or {}, ensure_ascii=False),
                     ogretmen, yazi, istek_id,
                     json.dumps(gorunen_kartlar(kartlar) if rol == "assistant" else {}, ensure_ascii=False)),
                )
                row = conn.execute("SELECT baslik FROM sohbet WHERE id = ?", (sid,)).fetchone()
                baslik = row["baslik"] if row else ""
                if rol == "user" and not baslik.strip():
                    baslik = " ".join(icerik.split())
                conn.execute(
                    "UPDATE sohbet SET guncelleme = ?, baslik = ? WHERE id = ?",
                    (yazi, baslik, sid),
                )
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
        return mid

    def istek_mesajlari(self, sid: str, istek_id: str) -> list[dict]:
        with self._baglan() as conn:
            rows = conn.execute(
                "SELECT * FROM mesaj WHERE sohbet_id = ? AND istek_id = ? ORDER BY sira",
                (sid, istek_id),
            ).fetchall()
        return [dict(row) for row in rows]

    def son_mesajlar(self, sid: str, n: int) -> list[dict]:
        with self._baglan() as conn:
            rows = conn.execute(
                "SELECT * FROM mesaj WHERE sohbet_id = ? ORDER BY zaman DESC, sira DESC LIMIT ?",
                (sid, n),
            ).fetchall()
        return [dict(r) for r in reversed(rows)]

    def tum_mesajlar(self, sid: str) -> list[dict]:
        with self._baglan() as conn:
            rows = conn.execute(
                "SELECT * FROM mesaj WHERE sohbet_id = ? ORDER BY zaman ASC, sira ASC",
                (sid,),
            ).fetchall()
        return [dict(r) for r in rows]

    def guncelle(self, sid: str, baslik: str | None, ogretmen: str | None, simdi: datetime) -> None:
        parca, deger = [], []
        if baslik is not None:
            parca.append("baslik = ?")
            deger.append(baslik)
        if ogretmen is not None:
            parca.append("ogretmen = ?")
            deger.append(ogretmen)
        parca.append("guncelleme = ?")
        deger.append(zaman_yazi(simdi))
        deger.append(sid)
        with self._baglan() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(f"UPDATE sohbet SET {', '.join(parca)} WHERE id = ?", deger)
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise

    def sil(self, sid: str) -> None:
        with self._baglan() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute("DELETE FROM alistirma_cevap WHERE alistirma_id IN "
                             "(SELECT id FROM alistirma WHERE sohbet_id = ?)", (sid,))
                conn.execute("DELETE FROM alistirma WHERE sohbet_id = ?", (sid,))
                conn.execute("DELETE FROM calisma_degerlendirme WHERE sohbet_id = ?", (sid,))
                conn.execute("DELETE FROM calisilan_konu WHERE sohbet_id = ?", (sid,))
                conn.execute("DELETE FROM mesaj WHERE sohbet_id = ?", (sid,))
                conn.execute("DELETE FROM sohbet WHERE id = ?", (sid,))
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise

    def ozet_oku(self, sid: str) -> str | None:
        row = self.getir(sid)
        if row is None:
            return None
        return row["ozet"]

    def ozet_yaz(self, sid: str, ozet: str) -> None:
        """Ürün yolu. Yalnız `ozet` kolonunu yazar; mesaj silmez, `ogretmen` değiştirmez."""
        with self._baglan() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute("UPDATE sohbet SET ozet = ? WHERE id = ?", (ozet, sid))
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise

    def not_yaz(self, metin: str, kaynak: str | None, simdi: datetime) -> str:
        if hassas_not(metin):
            return ""
        nid = uuid.uuid4().hex
        with self._baglan() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    "INSERT INTO ogrenci_notu (id, metin, kaynak_sohbet, zaman) VALUES (?, ?, ?, ?)",
                    (nid, metin, kaynak, zaman_yazi(simdi)),
                )
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
        return nid

    def not_duzelt(self, nid: str, metin: str) -> bool:
        if hassas_not(metin):
            return False
        with self._baglan() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                cur = conn.execute(
                    "UPDATE ogrenci_notu SET metin = ? WHERE id = ?", (metin, nid))
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
        return cur.rowcount == 1

    def not_sil(self, nid: str) -> bool:
        with self._baglan() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                cur = conn.execute("DELETE FROM ogrenci_notu WHERE id = ?", (nid,))
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
        return cur.rowcount == 1

    def notlar(self) -> list[dict]:
        with self._baglan() as conn:
            rows = conn.execute(
                "SELECT id, metin, kaynak_sohbet, zaman FROM ogrenci_notu ORDER BY zaman ASC, id ASC"
            ).fetchall()
        return [dict(r) for r in rows]

    def alistirma_yaz(self, sid: str, sahip_email: str, ogretmen: str, baslik: str,
                     ders: str, konu: str, kazanim_kodu: str | None, zorluk: str,
                     sorular: list[dict], simdi: datetime) -> str:
        aid = uuid.uuid4().hex
        kod = (kazanim_kodu or "").strip() or None
        with self._baglan() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    "INSERT INTO alistirma (id, sohbet_id, mesaj_id, sahip_email, ogretmen, "
                    "baslik, ders, konu, kazanim_kodu, zorluk, sorular_json, zaman) "
                    "VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (aid, sid, sahip_email, ogretmen, baslik, ders, konu, kod, zorluk,
                     json.dumps(sorular, ensure_ascii=False), zaman_yazi(simdi)))
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
        return aid

    @staticmethod
    def _alistirma_satiri(row) -> dict:
        sonuc = dict(row)
        sonuc["sorular"] = json.loads(sonuc.pop("sorular_json"))
        return sonuc

    def alistirma_getir(self, aid: str) -> dict | None:
        with self._baglan() as conn:
            row = conn.execute("SELECT * FROM alistirma WHERE id = ?", (aid,)).fetchone()
        return self._alistirma_satiri(row) if row else None

    def alistirmalar(self, mid: str) -> list[dict]:
        with self._baglan() as conn:
            rows = conn.execute("SELECT * FROM alistirma WHERE mesaj_id = ? ORDER BY zaman, id", (mid,)).fetchall()
        return [self._alistirma_satiri(row) for row in rows]

    def alistirma_bagla(self, aid: str, mid: str) -> None:
        with self._baglan() as conn:
            conn.execute("UPDATE alistirma SET mesaj_id = ? WHERE id = ?", (mid, aid))

    def cevap_yaz(self, aid: str, sira: int, dogru: bool, simdi: datetime) -> dict:
        with self._baglan() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO alistirma_cevap "
                    "(id, alistirma_id, sira, ders, konu, kazanim_kodu, dogru, zaman) "
                    "SELECT ?, id, ?, ders, konu, kazanim_kodu, ?, ? FROM alistirma WHERE id = ?",
                    (uuid.uuid4().hex, sira, int(dogru), zaman_yazi(simdi), aid))
                row = conn.execute("SELECT * FROM alistirma_cevap WHERE alistirma_id = ? AND sira = ?", (aid, sira)).fetchone()
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
        return dict(row) if row else {}

    def cevaplar(self, sahip_email: str) -> list[dict]:
        with self._baglan() as conn:
            rows = conn.execute(
                "SELECT c.* FROM alistirma_cevap c JOIN alistirma a ON a.id = c.alistirma_id "
                "WHERE a.sahip_email = ? ORDER BY c.zaman, c.id", (sahip_email,)).fetchall()
        return [dict(row) for row in rows]

    def degerlendirme_yaz(self, sid: str, ek_id: str, ogretmen: str, guclu_yanlar: str,
                         duzeyler: str, sonraki_adim: str, okur: str, simdi: datetime) -> str:
        did = uuid.uuid4().hex
        with self._baglan() as conn:
            conn.execute(
                "INSERT INTO calisma_degerlendirme (id, sohbet_id, ek_id, ogretmen, guclu_yanlar, "
                "duzeyler, sonraki_adim, okur, zaman) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (did, sid, ek_id, ogretmen, guclu_yanlar, duzeyler, sonraki_adim, okur, zaman_yazi(simdi)))
        return did

    def calisilan_yaz(self, sid: str, mid: str, sahip_email: str, ogretmen: str,
                     atiflar: list[dict], simdi: datetime) -> None:
        if ogretmen == "genel":
            return
        konular = calisilan_konular(atiflar)
        if not konular:
            return
        with self._baglan() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                for konu in konular:
                    conn.execute(
                        "INSERT INTO calisilan_konu (id, sohbet_id, mesaj_id, sahip_email, "
                        "ogretmen, kazanim_kodu, sayfa_basligi, zaman) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (uuid.uuid4().hex, sid, mid, sahip_email, ogretmen,
                         konu["kazanim_kodu"], konu["sayfa_basligi"], zaman_yazi(simdi)))
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise

    def gunluk(self, sahip_email: str, simdi: datetime) -> dict:
        bas, son = hafta_araligi(simdi)
        aralik = (sahip_email, zaman_yazi(bas), zaman_yazi(son))
        with self._baglan() as conn:
            calisilan = conn.execute(
                "SELECT * FROM calisilan_konu WHERE sahip_email = ? ORDER BY zaman DESC, rowid DESC LIMIT ?",
                (sahip_email, SON_CALISILAN)).fetchall()
            degerlendirmeler = conn.execute(
                "SELECT d.* FROM calisma_degerlendirme d JOIN sohbet s ON s.id = d.sohbet_id "
                "WHERE s.sahip_email = ? ORDER BY d.zaman DESC, d.rowid DESC", (sahip_email,)).fetchall()
            sohbetler = conn.execute(
                "SELECT ogretmen, COUNT(*) AS sayi FROM sohbet "
                "WHERE sahip_email = ? AND guncelleme >= ? AND guncelleme < ? GROUP BY ogretmen ORDER BY ogretmen",
                aralik).fetchall()
            alistirma = conn.execute(
                "SELECT COUNT(*) FROM alistirma WHERE sahip_email = ? AND zaman >= ? AND zaman < ?", aralik).fetchone()[0]
            puan = conn.execute(
                "SELECT COALESCE(SUM(c.dogru), 0) AS dogru, COUNT(*) AS toplam FROM alistirma_cevap c "
                "JOIN alistirma a ON a.id = c.alistirma_id WHERE a.sahip_email = ? AND c.zaman >= ? AND c.zaman < ?",
                aralik).fetchone()
        return {
            "zayif": zayif_konular(self.cevaplar(sahip_email)),
            "calisilan": [dict(row) for row in calisilan],
            "degerlendirmeler": [dict(row) for row in degerlendirmeler],
            "hafta": {"baslangic": bas.astimezone(ZoneInfo("Europe/Istanbul")).date().isoformat(),
                      "sohbet": [dict(row) for row in sohbetler], "alistirma": alistirma, "puan": dict(puan)},
        }
