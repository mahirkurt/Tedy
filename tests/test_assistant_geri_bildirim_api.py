import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

os.environ["TEST_AUTH_BYPASS"] = "1"

from src import dashboard_api  # noqa: E402

ISIK, AILE, DIGER = "student@example.test", "parent@example.test", "other@example.test"
SIMDI = datetime(2026, 10, 8, 9, 0, tzinfo=timezone.utc)


class _Rt:
    def chat(self, **kwargs):
        return {"answer": "cevap", "citations": [], "safety_flags": [], "plan_blocks": [], "intent": "qa",
                "session_id": "", "meta": {"model": "m", "degraded": []}}

    def chat_events(self, **kwargs):
        yield {"event": "answer", "payload": self.chat(**kwargs)}


@pytest.fixture
def istemci(monkeypatch, tmp_path):
    monkeypatch.setattr(dashboard_api, "OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(dashboard_api, "TEST_AUTH_BYPASS", True)
    monkeypatch.setattr(dashboard_api, "USER_ROLES", {ISIK: "full", AILE: "full", DIGER: "full"})
    monkeypatch.setattr(dashboard_api, "OGRENCI_EMAILS", {ISIK}, raising=False)
    monkeypatch.setattr(dashboard_api, "okur_turu", lambda e: "ogrenci" if e == ISIK else "aile")
    monkeypatch.setattr(dashboard_api, "_asistan_simdi", lambda: SIMDI, raising=False)
    monkeypatch.setattr(dashboard_api, "_assistant_runtime", lambda: _Rt())
    monkeypatch.setattr(dashboard_api, "_sohbet_ozetle", lambda sohbet: None)
    dashboard_api.app.config["TESTING"] = True
    with dashboard_api.app.test_client() as c:
        yield c


def _giris(c, email):
    with c.session_transaction() as ses:
        ses["user_email"] = email


def _cevapli_sohbet(c):
    _giris(c, ISIK)
    sid = c.post("/api/assistant/sohbetler", json={"ogretmen": "genel"}).get_json()["id"]
    rid = "0123456789abcdef0123456789abcdef"
    yuk = c.post("/api/assistant/chat", json={"sohbet_id": sid, "request_id": rid,
                                               "messages": [{"role": "user", "content": "soru"}]}).get_json()
    return sid, rid, yuk


def test_cevap_mesaj_id_tasir_tekrar_da(istemci):
    sid, rid, yuk = _cevapli_sohbet(istemci)
    assert len(yuk["mesaj_id"]) == 32
    tekrar = istemci.post("/api/assistant/chat", json={"sohbet_id": sid, "request_id": rid,
                                                       "messages": [{"role": "user", "content": "soru"}]}).get_json()
    assert tekrar["mesaj_id"] == yuk["mesaj_id"]
    akis = istemci.post("/api/assistant/stream", json={"sohbet_id": sid, "request_id": rid,
                                                       "messages": [{"role": "user", "content": "soru"}]}).get_data(as_text=True)
    assert f'"mesaj_id": "{yuk["mesaj_id"]}"' in akis


def test_put_delete_ve_gecmiste_deger(istemci, tmp_path):
    sid, _, yuk = _cevapli_sohbet(istemci)
    uc = f"/api/assistant/mesajlar/{yuk['mesaj_id']}/geri-bildirim"
    r = istemci.put(uc, json={"deger": "olumsuz", "kategori": "Anlamadım", "metin": "hızlı"})
    assert r.status_code == 200 and r.get_json() == {"deger": "olumsuz", "kategori": "Anlamadım", "metin": "hızlı"}
    mesajlar = istemci.get(f"/api/assistant/sohbetler/{sid}").get_json()["mesajlar"]
    assert [m.get("geri_bildirim") for m in mesajlar] == [None, {"deger": "olumsuz", "kategori": "Anlamadım", "metin": "hızlı"}]
    kayit = [json.loads(s) for s in (tmp_path / "assistant_geri_bildirim.jsonl").read_text().splitlines()]
    assert kayit[-1]["deger"] == "olumsuz" and kayit[-1]["metin_uzunlugu"] == 5 and "metin" not in kayit[-1]
    assert istemci.delete(uc).status_code == 204
    assert istemci.delete(uc).status_code == 404


@pytest.mark.parametrize("govde", [{"deger": "iyi"}, {"deger": "olumsuz", "kategori": "Başka"},
                                   {"deger": "olumsuz", "metin": "x" * 501}, ["olumlu"]])
def test_gecersiz_govde_400(istemci, govde):
    _, _, yuk = _cevapli_sohbet(istemci)
    assert istemci.put(f"/api/assistant/mesajlar/{yuk['mesaj_id']}/geri-bildirim", json=govde).status_code == 400


def test_sahiplik(istemci, monkeypatch):
    sid, _, yuk = _cevapli_sohbet(istemci)
    uc = f"/api/assistant/mesajlar/{yuk['mesaj_id']}/geri-bildirim"
    _giris(istemci, AILE)
    r = istemci.put(uc, json={"deger": "olumlu"})
    assert r.status_code == 403 and r.get_json()["error"] == "Bu sohbet salt okunur."
    assert all(m.get("geri_bildirim") is None for m in istemci.get(f"/api/assistant/sohbetler/{sid}").get_json()["mesajlar"])
    monkeypatch.setattr(dashboard_api, "okur_turu", lambda e: {ISIK: "ogrenci", AILE: "aile"}.get(e, "bilinmiyor"))
    _giris(istemci, DIGER)
    assert istemci.put(uc, json={"deger": "olumlu"}).status_code == 404
    _giris(istemci, ISIK)
    assert istemci.put("/api/assistant/mesajlar/" + "f" * 32 + "/geri-bildirim", json={"deger": "olumlu"}).status_code == 404
    assert istemci.put("/api/assistant/mesajlar/x/geri-bildirim", json={"deger": "olumlu"}).status_code == 404


def test_kullanici_mesajina_geri_bildirim_yok(istemci):
    sid, _, _ = _cevapli_sohbet(istemci)
    kullanici = istemci.get(f"/api/assistant/sohbetler/{sid}").get_json()["mesajlar"][0]["id"]
    assert istemci.put(f"/api/assistant/mesajlar/{kullanici}/geri-bildirim", json={"deger": "olumlu"}).status_code == 404


def test_gunluk_aileye_ogrencinin_ozeti(istemci):
    _, _, yuk = _cevapli_sohbet(istemci)
    istemci.put(f"/api/assistant/mesajlar/{yuk['mesaj_id']}/geri-bildirim",
                json={"deger": "olumsuz", "kategori": "Yanlış bilgi", "metin": "kesir yanlış"})
    _giris(istemci, AILE)
    ozet = istemci.get("/api/assistant/ogrenme-gunlugu").get_json()["geri_bildirim"]
    assert ozet["hafta"] == {"olumlu": 0, "olumsuz": 1}
    assert ozet["son_olumsuz"][0]["metin"] == "kesir yanlış"
