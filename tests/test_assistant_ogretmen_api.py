"""Öğretmen modu uçları (spec §1): istek `ogretmen` alanı, seçici listesi, bozuk skill.

- /api/assistant/stream ve /chat `ogretmen` taşır; yoksa ya da null ise genel; bilinmeyen
  değer 400 (akış açılmadan); geçerli değer çalışma zamanına iletilir.
- GET /api/assistant/ogretmenler seçicinin listesini döner; okur (reader) rolü alamaz.
- Bozuk bir skill asistanı açtırmaz: 503, log'da skill ve neden.
"""
import logging
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["TEST_AUTH_BYPASS"] = "1"

import src.dashboard_api as dashboard_api  # noqa: E402
from src import assistant_skills, subject_themes  # noqa: E402

app = dashboard_api.app
SORU = [{"role": "user", "content": "oran nedir"}]


class _Kaydedici:
    def __init__(self):
        self.cagrilar = []

    @staticmethod
    def _yuk():
        return {"answer": "x", "citations": [], "safety_flags": [], "plan_blocks": [],
                "intent": "qa", "session_id": "", "mode_suggestion": None,
                "meta": {"model": "fake"}}

    def chat(self, **kw):
        self.cagrilar.append(("chat", kw.get("ogretmen")))
        return self._yuk()

    def chat_events(self, **kw):
        self.cagrilar.append(("stream", kw.get("ogretmen")))
        yield {"event": "answer", "payload": self._yuk()}


@pytest.fixture
def istemci(monkeypatch):
    k = _Kaydedici()
    monkeypatch.setattr(dashboard_api, "_assistant_runtime", lambda: k)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c, k


@pytest.mark.parametrize("uc", ["/api/assistant/stream", "/api/assistant/chat"])
@pytest.mark.parametrize("govde,beklenen", [
    ({}, "genel"), ({"ogretmen": None}, "genel"), ({"ogretmen": "genel"}, "genel"),
    ({"ogretmen": "matematik"}, "matematik"), ({"ogretmen": "turkce"}, "turkce"),
])
def test_gecerli_ogretmen_calisma_zamanina_iletilir(istemci, uc, govde, beklenen):
    c, k = istemci
    res = c.post(uc, json={"messages": SORU, **govde})
    res.get_data()                       # the stream's generator runs only while read
    assert res.status_code == 200
    assert k.cagrilar[-1][1] == beklenen


@pytest.mark.parametrize("uc", ["/api/assistant/stream", "/api/assistant/chat"])
@pytest.mark.parametrize("deger", ["tarih", "Matematik", "", 5, ["fen"], "../fen"])
def test_bilinmeyen_ogretmen_400_ve_cagri_yok(istemci, uc, deger):
    c, k = istemci
    res = c.post(uc, json={"messages": SORU, "ogretmen": deger})
    assert res.status_code == 400
    assert res.headers["Content-Type"].startswith("application/json")
    assert res.get_json()["error"] == "Bilinmeyen öğretmen modu."
    assert k.cagrilar == []


@pytest.mark.parametrize("uc", ["/api/assistant/stream", "/api/assistant/chat"])
@pytest.mark.parametrize("govde", [["mesaj"], "sadece bir metin"])
def test_nesne_olmayan_govde_400_ve_cagri_yok(istemci, uc, govde):
    # Final-fix item P8a: a JSON body that is not an object (a list, a bare
    # string) must be refused with 400 before anything else reads it —
    # payload.get(...) on a list/string would otherwise raise AttributeError,
    # surfacing as an unrelated 500.
    c, k = istemci
    res = c.post(uc, json=govde)
    assert res.status_code == 400
    assert res.headers["Content-Type"].startswith("application/json")
    assert res.get_json()["error"] == "Geçersiz istek gövdesi."
    assert k.cagrilar == []


def test_ogretmenler_listesi(istemci):
    c, _ = istemci
    res = c.get("/api/assistant/ogretmenler")
    assert res.status_code == 200
    veri = res.get_json()
    assert veri["varsayilan"] == "genel"
    assert [o["id"] for o in veri["ogretmenler"]] == ["turkce", "fen", "sosyal", "matematik"]
    for o in veri["ogretmenler"]:
        assert o["renk_ailesi"] == subject_themes.family_of(o["ders"])
        assert set(o["karsilama"]) == {"ogrenci", "aile"}
        assert 3 <= len(o["hizli_sorular"]["ogrenci"]) <= 4
        assert o["ogretmen_adi"].endswith(" öğretmeni")


def test_ogretmenler_okura_kapali(istemci, monkeypatch):
    c, _ = istemci
    monkeypatch.setattr(dashboard_api, "TEST_AUTH_BYPASS", False)
    with c.session_transaction() as s:
        s["user_email"] = "murzogluhulya@gmail.com"      # reader: Tedy Books only
    assert c.get("/api/assistant/ogretmenler").status_code == 403


def test_bozuk_skill_listeyi_ve_istegi_503_yapar(istemci, monkeypatch, caplog):
    c, k = istemci

    def bozuk():
        raise assistant_skills.SkillHatasi("fen/SKILL.md: renk_ailesi 'purple', ders 'Fen Bilimleri' için 'teal' olmalı")

    monkeypatch.setattr(assistant_skills, "varsayilan", bozuk)
    with caplog.at_level(logging.ERROR):
        liste = c.get("/api/assistant/ogretmenler")
        istek = c.post("/api/assistant/chat", json={"messages": SORU, "ogretmen": "fen"})
    assert liste.status_code == 503
    assert liste.get_json() == {"error": "Öğretmen modları şu an yüklenemedi."}
    assert istek.status_code == 503
    assert "fen/SKILL.md" in caplog.text        # the log names the skill and the reason
    assert "fen/SKILL.md" not in liste.get_data(as_text=True)   # the reader does not see it
    assert k.cagrilar == []


def test_bozuk_skill_asistani_actirmaz_log_skilli_adlandirir(monkeypatch, caplog):
    monkeypatch.setattr(dashboard_api, "_ASSISTANT_RUNTIME", None)

    def bozuk():
        raise assistant_skills.SkillHatasi("sosyal: references/ eksik: soru-kaliplari.md")

    monkeypatch.setattr(assistant_skills, "varsayilan", bozuk)
    with caplog.at_level(logging.ERROR), pytest.raises(dashboard_api.AssistantUnavailableError):
        dashboard_api._assistant_runtime()
    assert "sosyal: references/ eksik: soru-kaliplari.md" in caplog.text
    assert dashboard_api._ASSISTANT_RUNTIME is None


def test_v1_ogretmen_alanini_dikkate_almaz(monkeypatch):
    alinan = {}

    class _Rt:
        def openai_chat_completion(self, payload):
            alinan["payload"] = payload
            return {"object": "chat.completion", "choices": []}

    monkeypatch.setattr(dashboard_api, "_assistant_runtime", lambda: _Rt())
    app.config["TESTING"] = True
    with app.test_client() as c:
        res = c.post("/v1/chat/completions", json={"messages": SORU, "ogretmen": "tarih"})
    # No 400 here: /v1 has no teacher modes; the runtime ignores the field (tested in
    # test_assistant_ogretmen_modu.py::test_v1_her_zaman_genel).
    assert res.status_code == 200
