"""Portal attachments in the BM25 index (plan 2026-09-28-portal-ekleri, Görev 9):
only the extracted <id>.txt, never the binaries, sidecars, part files or tracker."""
import json

from src.assistant_core import (INDEX_FORMAT_VERSION, AssistantConfig, AssistantIndexer,
                                HybridRetriever, _fmt_scraped_data)
from src.portal_ekleri import METIN_ONEKI

KIMLIK = "a1b2c3d4e5f60718"


def _yaz(kok, rel, veri="veri"):
    yol = kok / rel
    yol.parent.mkdir(parents=True, exist_ok=True)
    (yol.write_bytes if isinstance(veri, bytes) else yol.write_text)(veri)
    return yol


def _indeksleyici(kok, monkeypatch):
    for k in ("ASSISTANT_INCLUDE_DIRS", "ASSISTANT_EXCLUDED_DIRS", "ASSISTANT_EXCLUDED_FILES", "ASSISTANT_MAX_CHUNKS"):
        monkeypatch.delenv(k, raising=False)
    return AssistantIndexer(AssistantConfig.from_project_root(kok))


def test_yalniz_metin_yan_dosyasi_indekslenir(tmp_path, monkeypatch):
    ix = _indeksleyici(tmp_path, monkeypatch)
    alinir = f"content/portal-ekleri/{KIMLIK}.txt"
    for rel in (f"content/portal-ekleri/{KIMLIK}.pdf", f"content/portal-ekleri/{KIMLIK}.docx",
                f"content/portal-ekleri/{KIMLIK}.meta.json", f"content/portal-ekleri/{KIMLIK}.bin",
                f"content/portal-ekleri/.parca/{KIMLIK}.part", f"content/portal-ekleri/alt/{KIMLIK}.txt",
                "output/portal_ekleri.json", "output/portal_ekleri.json.tmp"):
        assert ix._is_excluded_file(rel), rel
        assert not ix.is_path_currently_included(rel), rel
    assert not ix._is_excluded_file(alinir) and ix.is_path_currently_included(alinir)
    assert INDEX_FORMAT_VERSION == 3


def test_ekler_icerikte_ders_kitaplarindan_once_kesfedilir(tmp_path, monkeypatch):
    _yaz(tmp_path, "content/eba/Matematik 7 1. Kitap.md", "kitap")
    _yaz(tmp_path, f"content/portal-ekleri/{KIMLIK}.txt", "ek")
    _yaz(tmp_path, "output/scraped_data.json", "{}")
    sira = [p.relative_to(tmp_path).as_posix() for p in _indeksleyici(tmp_path, monkeypatch)._discover_files()]
    assert sira.index("output/scraped_data.json") < sira.index(f"content/portal-ekleri/{KIMLIK}.txt") \
        < sira.index("content/eba/Matematik 7 1. Kitap.md")


def test_izleyici_gecici_dosyasi_parcalara_girmez(tmp_path, monkeypatch):
    """EkDeposu.yaz goes through atomic_json_dump, which writes
    portal_ekleri.json.tmp and then renames. A killed run leaves the .tmp,
    and an unknown extension is read as text — so the exclusion has to
    cover portal_ekleri.json.* and a reindex must not keep the body."""
    govde = "paylasimadresi izleyicigecicigovde kx9q"
    _yaz(tmp_path, "output/portal_ekleri.json.tmp", govde)
    _yaz(tmp_path, "output/not.txt", "okul notu duruyor")
    ix = _indeksleyici(tmp_path, monkeypatch)
    ix.reindex(incremental=False)
    parcalar = json.loads(ix.config.chunks_path.read_text(encoding="utf-8"))
    assert govde not in "\n".join(str(p.get("text") or "") for p in parcalar)
    assert "output/portal_ekleri.json.tmp" not in {p["path"] for p in parcalar}
    assert any(p["path"] == "output/not.txt" for p in parcalar)


def test_ek_metni_adiyla_ve_icerigiyle_bulunur(tmp_path, monkeypatch):
    _yaz(tmp_path, f"content/portal-ekleri/{KIMLIK}.txt",
         f"{METIN_ONEKI}Sayfa 12-13.pdf · Kitap okuma ödevi · Sosyal Bilgiler\n\n"
         "Soru 1: Bumerang kitabının 12. sayfasındaki haritayı açıkla.\n")
    _yaz(tmp_path, f"content/portal-ekleri/{KIMLIK}.pdf", b"%PDF-1.7 ikili")
    ix = _indeksleyici(tmp_path, monkeypatch)
    meta = ix.reindex(incremental=False)
    parcalar = json.loads(ix.config.chunks_path.read_text(encoding="utf-8"))
    yollar = {p["path"] for p in parcalar}
    assert f"content/portal-ekleri/{KIMLIK}.txt" in yollar
    assert f"content/portal-ekleri/{KIMLIK}.pdf" not in yollar and meta["dusen_dosyalar"] == []
    bulunan = HybridRetriever(chunks=parcalar).search("Bumerang haritası", top_k=3)
    assert bulunan and bulunan[0]["path"] == f"content/portal-ekleri/{KIMLIK}.txt"


def test_odev_paragrafi_ek_adlarini_tasir():
    veri = {"odevlerim": {"homework": {"rows": [{
        "Ders Adı": "Sosyal Bilgiler", "Ödev Başlığı": "Kitap okuma ödevi",
        "detail": {"description": "Sayfa 12-13", "attachments": [
            {"name": "Sayfa 12-13.pdf", "url": "https://ornek.edu.tr/a.pdf"},
            {"name": "Konu videosu", "url": "https://www.youtube.com/watch?v=x"}]}}]}}}
    assert "Ekler: Sayfa 12-13.pdf; Konu videosu" in _fmt_scraped_data(veri)
