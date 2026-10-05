"""Karma arama arayıcıda ve runtime'da (2026-10-05). Gömme sahte; ağ yok (conftest)."""
from pathlib import Path

import numpy as np
import pytest

from src import assistant_vektor as av
from src.assistant_core import AssistantRuntime, HybridRetriever

EKSEN = ("galaksi", "öfke", "kesir", "uyku", "sinir", "payda", "yıldız", "evren")


def _vektor(metin):
    v = np.zeros(len(EKSEN), dtype=np.float32)
    for i, k in enumerate(EKSEN):
        if k in metin.lower():
            v[i] = 1.0
    # "sinir" (an angry child) means the same as "öfke": the paraphrase the fake embedder understands.
    if v[EKSEN.index("sinir")]:
        v[EKSEN.index("öfke")] = 1.0
    v[-1] += 0.01
    return v / np.linalg.norm(v)


def _sahte_gom(cagrilar=None):
    def gom(adres, model, metinler, zaman_asimi):
        if cagrilar is not None:
            cagrilar.append(adres)
        return [_vektor(m).tolist() for m in metinler]
    return gom


DOLGU = " Bu paragraf parçayı anlamlı uzunluğa getiren açıklayıcı bir dolgu cümlesi taşır."
PARCALAR = [
    {"chunk_id": "a", "path": "content/eba/fen.md", "chunk_index": 0, "text": "Galaksiler yıldızlardan oluşur." + DOLGU},
    {"chunk_id": "b", "path": "content/pedagoji/ofke.md", "chunk_index": 0, "text": "Öfke nöbetinde çocuğa sakin kalın." + DOLGU},
    {"chunk_id": "c", "path": "content/eba/mat.md", "chunk_index": 0, "text": "Kesirlerde payda eşitlenir." + DOLGU},
]


def _retriever(agirlik=3.0, sorgu=None):
    matris = np.vstack([_vektor(p["text"]) for p in PARCALAR])
    return HybridRetriever(PARCALAR, vektorler=(np.arange(len(PARCALAR)), matris),
                           sorgu_gom=sorgu or _vektor, vektor_agirligi=agirlik)


def test_sozcugu_paylasmayan_soru_vektorle_bulunur():
    soru = "çocuğum sinirlenince ne yapmalıyım"
    assert HybridRetriever(PARCALAR).search(soru, top_k=3) == []
    sonuc = _retriever().search(soru, top_k=3)
    assert sonuc[0]["chunk_id"] == "b"
    assert sonuc[0]["vector"] > 0.5 and sonuc[0]["bm25"] == 0.0


def test_soru_gomulemezse_bm25_aynen_doner():
    bm25 = HybridRetriever(PARCALAR).search("payda", top_k=3)
    karma = _retriever(sorgu=lambda q: None).search("payda", top_k=3)
    assert [r["chunk_id"] for r in karma] == [r["chunk_id"] for r in bm25] == ["c"]
    assert karma[0]["score"] == bm25[0]["score"]


def test_agirlik_sifirsa_vektor_hic_sorulmaz():
    sonuc = _retriever(agirlik=0.0, sorgu=lambda q: pytest.fail("gömülmemeli")).search("payda", top_k=3)
    assert [r["chunk_id"] for r in sonuc] == ["c"]


def test_yol_filtresi_vektor_isabetine_de_uygulanir():
    sonuc = _retriever().search("sinirlenmek", top_k=3, context_filters={"path_prefixes": ["content/eba"]})
    assert "b" not in [r["chunk_id"] for r in sonuc]


def _proje(kok: Path):
    (kok / "content" / "eba").mkdir(parents=True)
    (kok / "content" / "pedagoji").mkdir(parents=True)
    (kok / "output").mkdir()
    (kok / "content" / "eba" / "fen.md").write_text("# Uzay\n\nGalaksiler milyarlarca yıldızdan oluşur." + DOLGU, encoding="utf-8")
    (kok / "content" / "eba" / "bos.md").write_text("." * 400, encoding="utf-8")
    (kok / "content" / "pedagoji" / "ofke.md").write_text("# Öfke\n\nÖfke nöbetinde ebeveyn sakin kalmalıdır." + DOLGU, encoding="utf-8")


def test_reindex_vektorleri_doldurur_ve_arama_kullanir(tmp_path, monkeypatch):
    _proje(tmp_path)
    monkeypatch.setenv("ASSISTANT_ENABLE_EMBEDDINGS", "1")
    cagrilar = []
    monkeypatch.setattr(av, "ollama_gom", _sahte_gom(cagrilar))
    rt = AssistantRuntime(tmp_path, skills={})
    stats = rt.reindex(incremental=False)
    assert stats["vektor"]["vektorlu"] == 1 and stats["vektor"]["eksik"] == 0  # boş şablon gömülmez
    assert stats["aile_kaynagi"]["vektor"]["vektorlu"] == 1
    assert set(cagrilar) <= {"http://mbp.lan:11434", "http://pi.lan:11434"}  # toplu gömme HP'de değil
    sorgu = []
    monkeypatch.setattr(av, "ollama_gom", _sahte_gom(sorgu))
    sonuc = rt._aile_search("çocuğum çok sinirli", 3)
    assert sonuc and sonuc[0]["path"] == "content/pedagoji/ofke.md"
    assert sorgu[0] == "http://127.0.0.1:11434"  # soru HP'nin yerel Ollama'sında


def test_kapaliyken_vektor_ne_yazilir_ne_sorulur(tmp_path):
    _proje(tmp_path)
    rt = AssistantRuntime(tmp_path, skills={})
    stats = rt.reindex(incremental=False)
    assert "vektor" not in stats
    assert not (rt.config.chunks_path.parent / av.ANAHTAR_DOSYASI).exists()
    assert rt._local_search("galaksiler", 3)[0]["path"] == "content/eba/fen.md"


def test_gomme_hatasi_reindexi_dusurmez(tmp_path, monkeypatch):
    _proje(tmp_path)
    monkeypatch.setenv("ASSISTANT_ENABLE_EMBEDDINGS", "1")

    def bozuk(*a, **k):
        raise OSError("düğüm yok")
    monkeypatch.setattr(av, "ollama_gom", bozuk)
    rt = AssistantRuntime(tmp_path, skills={})
    stats = rt.reindex(incremental=False)
    assert stats["chunks_indexed"] >= 1 and stats["vektor"]["eksik"] == 1
    assert rt._local_search("galaksiler", 3)[0]["path"] == "content/eba/fen.md"  # BM25'e döner


def test_ic_raporlar_ve_playwright_indekse_girmez(tmp_path):
    rt = AssistantRuntime(tmp_path, skills={})
    for yol in ("output/assistant_metrics_report.json", "output/assistant_metrics_report_latest.json",
                "output/assistant_postdeploy_status.json", "output/assistant_validate_report.json",
                "output/cureohub_validation.json", "output/.saat_dilimi_gocu.json", "output/classroom_courses.json",
                "output/uploaded_files.json", "output/playwright/.playwright-cli/page-x.yml"):
        assert not rt.indexer.is_path_currently_included(yol), yol
    for yol in ("output/scraped_data.json", "output/eba_textbooks_uploaded.json", "content/eba/x.pdf"):
        assert rt.indexer.is_path_currently_included(yol), yol
