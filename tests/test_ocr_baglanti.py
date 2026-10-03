"""OCR wired in (plan 2026-09-28-portal-ekleri, Görev 15): the general index reads
scanned PDFs, attachments are read page by page inside the sync budget, ek_oku
and the text sidecar carry the OCR text and its labels. Fake reader only."""
from src.assistant_core import AssistantConfig, AssistantIndexer, AssistantRuntime, FileAdapters, HybridRetriever
from src.assistant_tools import EK_TOOL, McpRegistry
from src.ocr_katmani import OcrKatmani
from src.portal_ekleri import EkDeposu, ek_kimligi
from src.portal_ekleri_indir import MB, Butce, ekleri_esitle, metin_cikar
from tests.sahte_http import SP_URL, SahteOturum, SahteYanit
from tests.sahte_ocr import MARKDOWN, Saat, SahteOkuyucu, SahteTesseract, taranmis_pdf

ETIKET = "[PDF s.1 · OCR · Claude Haiku 4.5 · güven %90]"


def _katman(kok, okuyucu=None, tesseract=None, **kw):
    return OcrKatmani(kok, okuyucu=okuyucu or SahteOkuyucu(), tesseract=tesseract or SahteTesseract(), **kw)


def _adaptor(kok, katman, son=60.0):
    ad = FileAdapters(AssistantConfig.from_project_root(kok), ocr=katman)
    if katman is not None:
        ad.ocr_son_an = katman.saat() + son
    return ad


def test_testlerde_ocr_kapali_uretimde_acik(tmp_path, monkeypatch):
    assert AssistantConfig.from_project_root(tmp_path).pdf_ocr is False       # tests/conftest.py
    monkeypatch.delenv("ASSISTANT_PDF_OCR")
    assert AssistantConfig.from_project_root(tmp_path).pdf_ocr is True
    assert AssistantConfig.from_project_root(tmp_path).ocr_sure == 45


def test_genel_indekste_bos_pdf_ocr_ile_okunur(tmp_path):
    pdf = taranmis_pdf(tmp_path / "tarama.pdf")
    sonuc = _adaptor(tmp_path, _katman(tmp_path)).extract(pdf, "content/yabanci-dil/tarama.pdf")
    assert sonuc["source_kind"] == "pdf_ocr" and sonuc["warnings"] == ["ocr"]
    assert sonuc["text"].startswith(f"{ETIKET}\n{MARKDOWN}")


def test_metin_katmanli_pdf_genel_indekste_ocr_a_gitmez(tmp_path, monkeypatch):
    pdf = taranmis_pdf(tmp_path / "kitap.pdf")
    monkeypatch.setattr(FileAdapters, "_extract_pdf_text",
                        lambda self, yol: "Bu sayfada okunur bir metin katmanı var.\n" + chr(12))
    okuyucu = SahteOkuyucu()
    sonuc = _adaptor(tmp_path, _katman(tmp_path, okuyucu)).extract(pdf, "content/eba/kitap.pdf")
    assert sonuc["source_kind"] == "pdf" and okuyucu.cagrilar == []


def test_ocr_verilmezse_eski_davranis(tmp_path):
    pdf = taranmis_pdf(tmp_path / "tarama.pdf")
    sonuc = _adaptor(tmp_path, None).extract(pdf, "content/x/tarama.pdf")
    assert sonuc["source_kind"] == "metadata" and sonuc["warnings"] == ["pdf_no_text"]


def test_sure_yetmezse_ocr_suruyor_ve_ilerleme(tmp_path):
    pdf = taranmis_pdf(tmp_path / "tarama.pdf", icerikli=2)
    saat = Saat()
    katman = _katman(tmp_path, SahteOkuyucu(saat=saat, adim=10.0), saat=saat)
    sonuc = _adaptor(tmp_path, katman, son=18.0).extract(pdf, "content/x/tarama.pdf")
    assert sonuc["extraction_error"] == "ocr_suruyor" and sonuc["ocr_ilerleme"] == "1/2"


def test_indeks_eski_metinsiz_pdf_kaydini_ocr_ile_yeniler(tmp_path):
    taranmis_pdf(_dizin(tmp_path / "content" / "yabanci-dil") / "tarama.pdf")
    config = AssistantConfig.from_project_root(tmp_path)
    AssistantIndexer(config).reindex(incremental=True)            # conftest: OCR off
    import json
    once = json.loads(config.chunks_path.read_text(encoding="utf-8"))
    assert once[0]["warnings"] == ["pdf_no_text"]
    ix = AssistantIndexer(config, ocr=_katman(tmp_path))
    meta = ix.reindex(incremental=True)
    sonra = json.loads(config.chunks_path.read_text(encoding="utf-8"))
    assert meta["changed_files"] == 1 and sonra[0]["source_kind"] == "pdf_ocr"
    assert HybridRetriever(chunks=sonra).search("Kesirleri topla", top_k=1)[0]["path"] == \
        "content/yabanci-dil/tarama.pdf"


def _dizin(yol):
    yol.mkdir(parents=True, exist_ok=True)
    return yol


def test_ocr_defteri_ve_onbellegi_indekse_girmez(tmp_path):
    ix = AssistantIndexer(AssistantConfig.from_project_root(tmp_path))
    assert ix._is_excluded_file("output/ocr_defteri.json")
    assert ix._is_excluded_file("output/ocr_defteri.json.lock")
    assert ix._is_excluded_dir("output/ocr_onbellek/ab")


def test_ek_metni_ocr_ile_cikar(tmp_path):
    pdf = taranmis_pdf(tmp_path / "ek.pdf")
    durum, metin = metin_cikar(pdf, 30.0, ocr=_katman(tmp_path))
    assert durum == "var" and metin.startswith(f"{ETIKET}\n{MARKDOWN}")


def test_yarim_ek_metni_bekliyor_ve_ilerleme(tmp_path):
    pdf = taranmis_pdf(tmp_path / "ek.pdf", icerikli=2)
    saat = Saat()
    katman = _katman(tmp_path, SahteOkuyucu(saat=saat, adim=10.0), saat=saat)
    # The 5 s floor is too little for a Claude call (15 s) or Tesseract (10 s):
    # nothing is read, nothing is lost, and the next run starts again.
    assert metin_cikar(pdf, 0.0, ocr=katman) == ("bekliyor", "0/2")


VERI = {"odevlerim": {"homework": {"rows": [{
    "Ders Adı": "Matematik", "Ödev Başlığı": "Kesir çalışma kağıdı",
    "Ödev Son Teslim Tarihi": "30.09.2026 12:00",
    "detail": {"description": "", "attachments": [{"name": "Çalışma kağıdı.pdf", "url": SP_URL}]}}]}}}


def _taranmis_oturum(tmp_path):
    govde = taranmis_pdf(tmp_path / "kaynak.pdf").read_bytes()
    return SahteOturum({"https://ornekokul-my.sharepoint.com/":
                        lambda u, h: SahteYanit(200, govde, {"Content-Type": "application/pdf"})})


def test_ek_esitlemesi_ocr_metnini_yan_dosyaya_ve_ek_oku_ya_tasir(tmp_path):
    kok = _dizin(tmp_path / "kok")
    ozet = ekleri_esitle(kok, VERI, _taranmis_oturum(tmp_path), Butce(float("inf"), 100 * MB),
                         ocr=_katman(kok))
    depo = EkDeposu(kok)
    kayit = depo.kayit(ek_kimligi(SP_URL))
    assert kayit["text"] == "var" and "ocr_ilerleme" not in kayit
    assert f"{ETIKET}\n{MARKDOWN}" in depo.metin_yolu(kayit["id"]).read_text(encoding="utf-8")
    assert ozet["ocr_bu_ay_usd"] > 0
    out = McpRegistry(clients={}, local_search=lambda q, k: [], ek_deposu=depo).dispatch(EK_TOOL, {"id": kayit["id"]})
    assert out.ok and ETIKET in out.text and "OCR ile okundu" in out.text and "# Soru 1" in out.text


def test_dusuk_guvenli_sayfa_etiketiyle_gorunur(tmp_path):
    kok = _dizin(tmp_path / "kok")
    ekleri_esitle(kok, VERI, _taranmis_oturum(tmp_path), Butce(float("inf"), 100 * MB),
                  ocr=_katman(kok, tesseract=SahteTesseract(guven=0.4), tavan=0.0))
    depo = EkDeposu(kok)
    metin = depo.metin_yolu(ek_kimligi(SP_URL)).read_text(encoding="utf-8")
    assert "[PDF s.1 · OCR, güven düşük · Tesseract]" in metin


def test_yarim_ocr_deneme_saymaz_ve_ek_oku_ilerlemeyi_soyler(tmp_path):
    kok = _dizin(tmp_path / "kok")
    cevaplar = [("bekliyor", "1/3"), ("var", "Soru 1 metni")]
    oturum = _taranmis_oturum(tmp_path)
    ekleri_esitle(kok, VERI, oturum, Butce(float("inf"), 100 * MB),
                  metin_cikarici=lambda y, s: cevaplar.pop(0))
    depo = EkDeposu(kok)
    kayit = depo.kayit(ek_kimligi(SP_URL))
    assert (kayit["text"], kayit["ocr_ilerleme"], kayit.get("text_attempts", 0)) == ("bekliyor", "1/3", 0)
    out = McpRegistry(clients={}, local_search=lambda q, k: [], ek_deposu=depo).dispatch(EK_TOOL, {"id": kayit["id"]})
    assert "OCR ile okunuyor (1/3 sayfa okundu)" in out.text
    ekleri_esitle(kok, VERI, oturum, Butce(float("inf"), 100 * MB), metin_cikarici=lambda y, s: cevaplar.pop(0))
    kayit = depo.kayit(ek_kimligi(SP_URL))
    assert (kayit["text"], kayit["text_attempts"]) == ("var", 1) and "ocr_ilerleme" not in kayit


def test_istem_dusuk_guvenli_ocr_sayfasini_kesin_saymaz():
    assert "OCR, güven düşük" in AssistantRuntime.SYSTEM_PROMPT
