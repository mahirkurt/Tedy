"""Suite-wide guard: no test reaches the paid model API by accident.

Since 2026-09-24 TEDY calls Claude (assistant, homework photo, book
translation) with ANTHROPIC_API_KEY. That key can be present in a developer's
shell and, once configured, in .env — which src.env_loader copies into
os.environ at import. A test that forgot to inject a fake would then make a
real, billed request. Tests that exercise Claude pass a fake client or set the
variable themselves.
"""
import pytest


@pytest.fixture(autouse=True)
def _gercek_claude_anahtari_yok(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
