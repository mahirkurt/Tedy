"""Hitap: the assistant speaks to whoever is asking, in one voice.

Live smoke test, 2026-09-24: asked "Bu hafta hangi ödevlerim var?", the answer
opened "Bu hafta önünde şu ödevler var Işık" and two paragraphs later said
"Işık zaten 'Yaptım' demiş" — second person and third person in one answer.
The model could not know who was asking. The dashboard is used by Işık and by
the family; the session knows which, and now the model does too.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["TEST_AUTH_BYPASS"] = "1"

import src.dashboard_api as dashboard_api  # noqa: E402
from src.assistant_core import AssistantRuntime, ToolLoopResult  # noqa: E402
from src.roles import okur_turu  # noqa: E402

app = dashboard_api.app
ISIK = "isikkurtx@gmail.com"
AILE = "drmahirkurt@gmail.com"
BODY = {"messages": [{"role": "user", "content": "ödevlerim"}]}


def test_okur_turu_rosterdan():
    assert okur_turu(ISIK) == "ogrenci"
    assert okur_turu(" IsikKurtX@gmail.com ") == "ogrenci"
    assert okur_turu(AILE) == "aile"
    assert okur_turu("murzogluhulya@gmail.com") == "bilinmiyor"   # reader: never reaches the assistant
    assert okur_turu(None) == "bilinmiyor"
    assert okur_turu("yabanci@example.com") == "bilinmiyor"


@pytest.fixture
def rt(tmp_path):
    (tmp_path / "output").mkdir()
    return AssistantRuntime(tmp_path)


def _soru_turu(rt, **kw):
    return rt._build_conversation([{"role": "user", "content": "ödevlerim"}],
                                  "ödevlerim", "qa", [], **kw)[-1]["content"]


def test_konusma_soranin_kim_oldugunu_soyler(rt):
    assert "Soran: Işık\n" in _soru_turu(rt, okur="ogrenci")
    assert "Soran: Işık'ın ailesinden biri" in _soru_turu(rt, okur="aile")
    assert "Soran: bilinmiyor" in _soru_turu(rt)


def test_sistem_istemi_hitabi_tarif_eder(rt):
    p = rt._system_prompt()
    assert "## Hitap" in p
    assert "'sen'" in p and "'siz'" in p
    assert "Bir cevap boyunca hitabı değiştirme" in p


def test_sistem_istemi_genel_bilgiyi_resmi_kalipla_bildirtmez(rt):
    """The old rule made the model write "Bu bilgi genel matematik bilgisidir,
    Işık'ın kaydından veya doğrudan bir kaynak satırından alınmamıştır." to
    Işık directly — third person, and a form's wording."""
    p = rt._system_prompt()
    assert "Işık'ın kaydından veya müfredat kaynağından gelmediğini belirt" not in p
    assert "alınmamıştır" in p          # named, as the pattern not to use


def test_chat_soranı_modele_iletir(rt, monkeypatch):
    gorulen = {}

    def yakala(*, messages, **kwargs):
        gorulen["son"] = messages[-1]["content"]
        return ToolLoopResult(text="tamam")

    monkeypatch.setattr(rt.registry, "declarations", lambda: [])
    monkeypatch.setattr(rt.llm, "chat_with_tools", yakala)
    rt.chat(messages=BODY["messages"], session_id="s", okur="aile")
    assert "Soran: Işık'ın ailesinden biri" in gorulen["son"]


class _Kaydedici:
    def __init__(self):
        self.okurlar = []

    @staticmethod
    def _yuk():
        return {"answer": "x", "citations": [], "safety_flags": [], "plan_blocks": [],
                "intent": "qa", "session_id": "", "meta": {"model": "fake"}}

    def chat(self, **kw):
        self.okurlar.append(("chat", kw.get("okur")))
        return self._yuk()

    def chat_events(self, **kw):
        self.okurlar.append(("stream", kw.get("okur")))
        yield {"event": "answer", "payload": self._yuk()}

    def study_plan(self, **kw):
        self.okurlar.append(("plan", kw.get("okur")))
        return self._yuk()


@pytest.fixture
def istemci(monkeypatch):
    k = _Kaydedici()
    monkeypatch.setattr(dashboard_api, "TEST_AUTH_BYPASS", False)
    monkeypatch.setattr(dashboard_api, "_assistant_runtime", lambda: k)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c, k


def _vur(c):
    c.post("/api/assistant/chat", json=BODY)
    c.post("/api/assistant/plan", json=BODY)
    c.post("/api/assistant/stream", json=BODY).get_data()   # the generator runs only while read


@pytest.mark.parametrize("eposta,beklenen", [(ISIK, "ogrenci"), (AILE, "aile")])
def test_her_uc_soranı_oturumdan_bilir(istemci, eposta, beklenen):
    c, k = istemci
    with c.session_transaction() as s:
        s["user_email"] = eposta
    _vur(c)
    # "stream" too: decided inside the request, before the generator outlives the session.
    assert sorted(k.okurlar) == [("chat", beklenen), ("plan", beklenen), ("stream", beklenen)]


def test_auth_me_ogrenciyi_bildirir(istemci):
    c, _ = istemci
    for eposta, ogrenci in ((ISIK, True), (AILE, False)):
        with c.session_transaction() as s:
            s["user_email"] = eposta
        assert c.get("/api/auth/me").get_json()["student"] is ogrenci


# ── the other oddities in the same live answers (2026-09-24) ─────────────────

def test_odev_suresi_tahmin_ettirilmez(rt):
    """Asked for the week's homework, the model wrote "(yaklaşık 30-40 dk)" next
    to each one — the prompt told it to put an estimated time on every step.
    Nothing says how long homework takes; the constitution forbids the guess
    (İ3: a total is a wall for a reader who overestimates time)."""
    p = rt._system_prompt()
    assert "her adıma tahmini süre yaz" not in p
    assert "ne kadar süreceğini tahmin etme" in p
    assert "10 dakikayla başla" in p          # a time box, offered instead


def test_ayni_kaynak_her_maddede_tekrarlanmaz(rt):
    """The family's answer put the same [S1] after all seven lines of one list."""
    assert "her maddeye tekrar etme" in rt._system_prompt()


def test_eski_odev_notu_okura_degil_modele():
    """"14 günden eski 12 ödev daha listede görünmüyor" reached the reader: the
    note was for the model."""
    from datetime import datetime
    from src.assistant_tools import odev_listesi_metni
    eski = {"Ders Adı": "Matematik", "Ödev Başlığı": "Sayfa 1",
            "Ödev Son Teslim Tarihi": "01.03.2026 23:59", "student_marked_done": True}
    metin = odev_listesi_metni([eski], datetime(2026, 9, 24, 16, 10))
    assert "okura aktarma" in metin
