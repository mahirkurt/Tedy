"""İstekteki sayfa bağlamı (spec §5.3): doğrulama, başlığın sunucuda çözülmesi, kullanıcı turu."""
import os

import pytest

os.environ["TEST_AUTH_BYPASS"] = "1"

from src import dashboard_api  # noqa: E402
from src.assistant_core import AssistantRuntime  # noqa: E402


class _Kayit:
    def __init__(self):
        self.kwargs = None

    def chat(self, **kwargs):
        self.kwargs = kwargs
        return {"answer": "cevap", "citations": [], "safety_flags": [], "plan_blocks": [],
                "intent": "qa", "session_id": "", "meta": {"model": "m", "degraded": []}}

    def chat_events(self, **kwargs):
        self.kwargs = kwargs
        yield {"event": "answer", "payload": self.chat(**kwargs)}


@pytest.fixture
def istemci(monkeypatch):
    kayit = _Kayit()
    monkeypatch.setattr(dashboard_api, "_assistant_runtime", lambda: kayit)
    monkeypatch.setattr(dashboard_api, "_canli_odevler", lambda: [
        {"homework_key": "hw-1", "normalized_course": "Matematik", "Ödev Başlığı": "s.84 alıştırmalar"}])
    monkeypatch.setattr(dashboard_api, "_canli_sinavlar", lambda: [{"id": "abc123def456", "title": "Fen Bilimleri 1. Sınav"}])
    dashboard_api.app.config["TESTING"] = True
    with dashboard_api.app.test_client() as c:
        c.kayit = kayit
        yield c


SORU = {"messages": [{"role": "user", "content": "Bugün hangisinden başlayayım?"}]}


@pytest.mark.parametrize("uc", ["/api/assistant/chat", "/api/assistant/stream"])
@pytest.mark.parametrize("sayfa", [
    {"ad": "xyz"}, {"ad": 3}, "isler", {"ad": "isler", "oge": {"tur": "gizli", "id": "a"}},
    {"ad": "isler", "oge": {"tur": "odev", "id": ""}}, {"ad": "isler", "oge": {"tur": "odev", "id": "a\nb"}},
    {"ad": "isler", "oge": {"tur": "odev", "id": "x" * 401}},
    # Hashlenemeyen ad ve tür: `in` sözlükte TypeError verip 500'e dönüyordu.
    {"ad": ["isler"]}, {"ad": {"x": 1}}, {"ad": "isler", "oge": {"tur": ["odev"], "id": "a"}},
])
def test_gecersiz_sayfa_akistan_once_400(istemci, uc, sayfa):
    yanit = istemci.post(uc, json={**SORU, "sayfa": sayfa})
    assert yanit.status_code == 400
    assert yanit.get_json()["error"] == "Bilinmeyen sayfa."
    assert istemci.kayit.kwargs is None


def test_sayfa_yoksa_satir_bos(istemci):
    assert istemci.post("/api/assistant/chat", json=SORU).status_code == 200
    assert istemci.kayit.kwargs["sayfa_satiri"] == ""


def test_odev_basligi_sunucudan_cozulur(istemci):
    istemci.post("/api/assistant/stream", json={**SORU, "sayfa": {"ad": "isler", "oge": {"tur": "odev", "id": "hw-1"}}}).get_data()
    assert istemci.kayit.kwargs["sayfa_satiri"] == "Bulunduğu sayfa: İşler (açık: Matematik — s.84 alıştırmalar)"


def test_cozulemeyen_oge_yalniz_sayfa_adi(istemci):
    istemci.post("/api/assistant/chat", json={**SORU, "sayfa": {"ad": "sinavlar", "oge": {"tur": "sinav", "id": "yok"}}})
    assert istemci.kayit.kwargs["sayfa_satiri"] == "Bulunduğu sayfa: Sınavlar"
    istemci.post("/api/assistant/chat", json={**SORU, "sayfa": {"ad": "sinavlar", "oge": {"tur": "sinav", "id": "abc123def456"}}})
    assert istemci.kayit.kwargs["sayfa_satiri"] == "Bulunduğu sayfa: Sınavlar (açık: Fen Bilimleri 1. Sınav)"


def test_satir_kullanici_turunda_sistemde_degil(tmp_path):
    (tmp_path / "output").mkdir()
    rt = AssistantRuntime(tmp_path)
    konusma = rt._build_conversation([{"role": "user", "content": "x"}], "x", "qa", [],
                                     sayfa_satiri="Bulunduğu sayfa: İşler")
    sistem = [m for m in konusma if m["role"] == "system"]
    assert all("Bulunduğu sayfa" not in str(m["content"]) for m in sistem)
    son = konusma[-1]
    assert son["role"] == "user" and "Bulunduğu sayfa: İşler\n" in son["content"]
    assert son["content"].endswith("Soru: x")
