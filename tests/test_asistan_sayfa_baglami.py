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


# --- Sınav Hazırlığı kılavuzu (spec 2026-10-25 §3.3, plan Görev 12, D11) ---------------------------------------------
# Kılavuz "Asistana sor" ile sınavı VE senaryoyu bağlam yapar; model gördüğü satırda senaryoyu okur. Başlık
# istemcinin etiketinden değil sunucunun kendi verisinden ve doğrulanmış alanlardan kurulur.

def _kilavuz(oge_ek, kimlik="abc123def456"):
    return {**SORU, "sayfa": {"ad": "sinavlar", "oge": {"tur": "sinav", "id": kimlik, **oge_ek}}}


def _satir(istemci, govde):
    yanit = istemci.post("/api/assistant/chat", json=govde)
    assert yanit.status_code == 200
    return istemci.kayit.kwargs["sayfa_satiri"]


@pytest.fixture
def kayitli_sinav(monkeypatch):
    monkeypatch.setattr(dashboard_api, "_canli_sinavlar", lambda: [
        {"id": "abc123def456", "title": "1.1 Ara Değerlendirme Sınavı",
         "senaryo": {"ders": "Fen Bilimleri", "sinav_no": 1}}])


def test_kilavuz_senaryosu_sinav_kaydi_varken_satira_girer(istemci, kayitli_sinav):
    satir = _satir(istemci, _kilavuz({"kip": "kesin", "senaryo": 2}))
    assert satir == "Bulunduğu sayfa: Sınavlar (açık: Fen Bilimleri · 1. yazılı · 2. senaryo)"
    # Kayıt başlığı kaybolmaz: senaryosuz istek eskisi gibi kayıt başlığıyla çözülür.
    assert _satir(istemci, _kilavuz({})) == "Bulunduğu sayfa: Sınavlar (açık: 1.1 Ara Değerlendirme Sınavı)"


def test_kilavuz_sinav_kaydi_yokken_ders_yazili_senaryo_kurulur(istemci):
    satir = _satir(istemci, _kilavuz({"kip": "kesin", "senaryo": 2}, "hazirlik:fen-bilimleri:1:2"))
    assert satir == "Bulunduğu sayfa: Sınavlar (açık: Fen Bilimleri · 1. yazılı · 2. senaryo)"
    satir = _satir(istemci, _kilavuz({"kip": "kesin", "senaryo": 4}, "hazirlik:turkce:2:4"))
    assert satir == "Bulunduğu sayfa: Sınavlar (açık: Türkçe · 2. yazılı · 4. senaryo)"


def test_kilavuz_alan_yoksa_kimlikteki_senaryo_okunur(istemci):
    assert _satir(istemci, _kilavuz({}, "hazirlik:fen-bilimleri:1:3")) \
        == "Bulunduğu sayfa: Sınavlar (açık: Fen Bilimleri · 1. yazılı · 3. senaryo)"
    assert _satir(istemci, _kilavuz({}, "hazirlik:fen-bilimleri:1:olasi")) \
        == "Bulunduğu sayfa: Sınavlar (açık: Fen Bilimleri · 1. yazılı · bütün senaryolar (olası))"


def test_olasi_kipte_senaryo_bu_senaryo_diye_sunulmaz(istemci, kayitli_sinav):
    """K8: duyurulmamış senaryo ("olası") hiçbir zaman kesinmiş gibi yazılmaz."""
    assert _satir(istemci, _kilavuz({"kip": "olasi", "senaryo": 3})) \
        == "Bulunduğu sayfa: Sınavlar (açık: Fen Bilimleri · 1. yazılı · 3. senaryo (olası))"
    assert _satir(istemci, _kilavuz({"kip": "olasi", "senaryo": None})) \
        == "Bulunduğu sayfa: Sınavlar (açık: Fen Bilimleri · 1. yazılı · bütün senaryolar (olası))"
    assert _satir(istemci, _kilavuz({"kip": "ulke_geneli"}, "hazirlik:fen-bilimleri:2:olasi")) \
        == "Bulunduğu sayfa: Sınavlar (açık: Fen Bilimleri · 2. yazılı · ülke geneli)"


def test_etiket_sunucuya_guvenilmez(istemci):
    govde = _kilavuz({"kip": "kesin", "senaryo": 2, "etiket": "Fen Bilimleri · 1. yazılı · 9. senaryo"},
                     "hazirlik:fen-bilimleri:1:2")
    assert _satir(istemci, govde).endswith("2. senaryo)")


def test_cozulemeyen_kilavuz_kimligi_yalniz_sayfa_adi(istemci):
    for kimlik in ("hazirlik:yok-ders:1:2", "hazirlik:fen-bilimleri:3:2", "hazirlik:fen-bilimleri:x:2", "hazirlik:fen-bilimleri"):
        assert _satir(istemci, _kilavuz({}, kimlik)) == "Bulunduğu sayfa: Sınavlar"


@pytest.mark.parametrize("ek", [
    {"kip": "gizli", "senaryo": 2}, {"kip": ["kesin"], "senaryo": 2}, {"kip": "kesin", "senaryo": "2"},
    {"kip": "kesin", "senaryo": 0}, {"kip": "kesin", "senaryo": 100}, {"kip": "kesin", "senaryo": True},
    {"kip": "kesin", "senaryo": 2.5}, {"senaryo": 2},
])
def test_gecersiz_kilavuz_alanlari_400(istemci, ek):
    yanit = istemci.post("/api/assistant/chat", json=_kilavuz(ek, "hazirlik:fen-bilimleri:1:2"))
    assert yanit.status_code == 400 and yanit.get_json()["error"] == "Bilinmeyen sayfa."
    assert istemci.kayit.kwargs is None


def test_kilavuz_alanlari_yalniz_sinav_ogesinde(istemci):
    govde = {**SORU, "sayfa": {"ad": "isler", "oge": {"tur": "odev", "id": "hw-1", "kip": "kesin", "senaryo": 2}}}
    assert istemci.post("/api/assistant/chat", json=govde).status_code == 400
