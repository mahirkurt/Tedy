"""Suite-wide guards: no test reaches the paid model API or the live schedule.

Since 2026-09-24 TEDY calls Claude (assistant, homework photo, book
translation) with ANTHROPIC_API_KEY. That key can be present in a developer's
shell and, once configured, in .env — which src.env_loader copies into
os.environ at import. A test that forgot to inject a fake would then make a
real, billed request. Tests that exercise Claude pass a fake client or set the
variable themselves.

run_sync.main() records every attempt in output/.sync_zamanlama.json, the
file cron's 5-minute ticks read to decide whether to run (15 minutes normally,
5 after a failed portal login). Measured 2026-09-25: the rollover tests call
main() and wrote that file in the live checkout. Every test gets its own.
"""
import sys

import pytest


@pytest.fixture(autouse=True)
def _gercek_claude_anahtari_yok(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


@pytest.fixture(autouse=True)
def _canli_sync_zamanlamasi_yok(tmp_path, monkeypatch):
    run_sync = sys.modules.get("src.run_sync")
    if run_sync is not None:
        monkeypatch.setattr(run_sync, "ZAMANLAMA_PATH", str(tmp_path / ".sync_zamanlama.json"))


@pytest.fixture(autouse=True)
def _canli_ek_indirmesi_yok(monkeypatch):
    """run_sync.main() downloads portal attachments since 2026-09-28 (plan
    portal-ekleri, Görev 7). A test that drives main() must never reach
    SharePoint or Drive, nor write content/portal-ekleri: the step's network
    entry point refuses here, and _ekleri_esitle_adimi turns that into
    {"hata": …} as it does any failure. Tests of the step patch it again on
    purpose; tests of ekleri_esitle import the function by name at
    collection, which this does not touch."""
    import src.portal_ekleri_indir as indir

    def _yasak(*a, **k):
        raise RuntimeError("testte gerçek ek indirmesi yok")
    monkeypatch.setattr(indir, "ekleri_esitle", _yasak)


@pytest.fixture(autouse=True)
def _pdf_ocr_kapali(monkeypatch):
    """OCR of scanned PDFs (src/ocr_katmani.py) is on by default in production.
    In tests it is off unless a test turns it on and hands in a fake reader: a
    scanned PDF in an unrelated test must not reach Claude, write the OCR
    ledger, or spend ~20 s per page in real Tesseract (plan 2026-09-28, Görev 15)."""
    monkeypatch.setenv("ASSISTANT_PDF_OCR", "0")


@pytest.fixture(autouse=True)
def _vektor_gommesi_kapali(monkeypatch):
    """Hybrid search (src/assistant_vektor.py) is on in production through .env, which
    dashboard_api loads at import. In tests it is off, and the real embed call fails loudly, so a
    reindex or search can never reach mbp/Pi/HP's Ollama; a test that wants vectors turns it on and
    hands in a fake (2026-10-05)."""
    from src import assistant_vektor

    monkeypatch.setenv("ASSISTANT_ENABLE_EMBEDDINGS", "0")

    def _yasak(*a, **k):
        raise RuntimeError("testte gerçek gömme çağrısı yok")
    monkeypatch.setattr(assistant_vektor, "ollama_gom", _yasak)
