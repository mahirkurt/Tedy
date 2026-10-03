"""Assistant chats (spec §3). No Flask."""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

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
    ogretmen TEXT NOT NULL,
    zaman TEXT NOT NULL,
    sira INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS mesaj_sohbet_sira ON mesaj(sohbet_id, sira);
CREATE TABLE IF NOT EXISTS ogrenci_notu (
    id TEXT PRIMARY KEY,
    metin TEXT NOT NULL,
    kaynak_sohbet TEXT,
    zaman TEXT NOT NULL
);
"""


def zaman_yazi(an: datetime) -> str:
    if an.tzinfo is None:
        an = an.replace(tzinfo=timezone.utc)
    return an.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class SohbetDeposu:
    def __init__(self, yol: Path):
        self.yol = Path(yol)
        self.yol.parent.mkdir(parents=True, exist_ok=True)
        with self._baglan() as conn:
            conn.executescript(_SEM)

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
                   ekler: list, simdi: datetime, atiflar: list | None = None) -> str:
        mid = uuid.uuid4().hex
        yazi = zaman_yazi(simdi)
        with self._baglan() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    "INSERT INTO mesaj (id, sohbet_id, rol, icerik, atiflar_json, ekler_json, "
                    "meta_json, ogretmen, zaman, sira) VALUES (?, ?, ?, ?, ?, ?, '{}', ?, ?, "
                    "(SELECT COALESCE(MAX(sira), 0) + 1 FROM mesaj))",
                    (mid, sid, rol, icerik, json.dumps(atiflar or [], ensure_ascii=False),
                     json.dumps(ekler, ensure_ascii=False), ogretmen, yazi),
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
