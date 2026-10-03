"""Alıştırma cevapları ve yalnız sahibine ait günlük; model/ağ yok."""
import os
os.environ["TEST_AUTH_BYPASS"] = "1"

import pytest

from src import dashboard_api
from tests.test_assistant_sohbet_api import (
    AILE, DIGER, ISIK, OKUR, SIMDI, _answer, _giris, _sohbet_deposu, istemci,
)


def _hazir(istemci, soru=None, email=ISIK, ogretmen="matematik"):
    _giris(istemci, email)
    sid = istemci.post("/api/assistant/sohbetler", json={"ogretmen": ogretmen}).get_json()["id"]
    sorular = [soru or {"tur": "kisa_cevap", "soru": "Bir kesir topla", "dogru": "5/6",
                       "kabul_edilenler": ["0.833"], "aciklama": "Paydalar eşitlenir."}] * 3
    depo = _sohbet_deposu()
    aid = depo.alistirma_yaz(sid, email, ogretmen, "Payda", "Matematik", "Kesir",
                             "MAT.7.1.1", "orta", sorular, SIMDI)
    return sid, aid, depo


def test_cevap_ilk_deneme_korunur(istemci):
    _, aid, depo = _hazir(istemci)
    url = f"/api/assistant/alistirmalar/{aid}/cevap"
    bir = istemci.post(url, json={"sira": 1, "cevap": "5/6"})
    assert bir.status_code == 200
    assert bir.get_json() == {"dogru": True, "aciklama": "Paydalar eşitlenir."}
    iki = istemci.post(url, json={"sira": 1, "cevap": "2/5"})
    assert iki.get_json() == bir.get_json()
    assert len(depo.cevaplar(ISIK)) == 1


@pytest.mark.parametrize("body", [{}, {"sira": True, "cevap": "a"},
    {"sira": 0, "cevap": "a"}, {"sira": 4, "cevap": "a"},
    {"sira": 1, "cevap": " "}, {"sira": 1, "cevap": 42}])
def test_gecersiz_cevap_satir_yazmaz(istemci, body):
    _, aid, depo = _hazir(istemci)
    yanit = istemci.post(f"/api/assistant/alistirmalar/{aid}/cevap", json=body)
    assert yanit.status_code == 400
    assert yanit.get_json()["error"] == "Cevap alınamadı."
    assert depo.cevaplar(ISIK) == []


def test_aile_salt_okur_ve_bilinmeyen_kimlik(istemci):
    _, aid, depo = _hazir(istemci)
    _giris(istemci, AILE)
    yanit = istemci.post(f"/api/assistant/alistirmalar/{aid}/cevap", json={"sira": 1, "cevap": "5/6"})
    assert yanit.status_code == 403
    assert yanit.get_json()["error"] == "Bu sohbet salt okunur."
    for kimlik in ("ab" * 16, "bozuk"):
        yok = istemci.post(f"/api/assistant/alistirmalar/{kimlik}/cevap", json={"sira": 1, "cevap": "5/6"})
        assert yok.status_code == 404
        assert yok.get_json()["error"] == "Alıştırma bulunamadı."
    assert depo.cevaplar(ISIK) == []


def test_gecmis_alistirma_sorularinin_cevabini_sizdirmaz(istemci):
    sid, aid, depo = _hazir(istemci)
    mid = depo.mesaj_ekle(sid, "assistant", "Anlattım.", "matematik", [], SIMDI)
    depo.alistirma_bagla(aid, mid)
    _giris(istemci, AILE)
    body = istemci.get(f"/api/assistant/sohbetler/{sid}").get_json()
    quiz = body["mesajlar"][0]["alistirma"][0]
    assert quiz["id"] == aid
    assert set(quiz["sorular"][0]) == {"tur", "soru"}
    assert "5/6" not in str(body) and "Paydalar eşitlenir." not in str(body)


def test_yanlis_analizi_skill_katalogundan(istemci):
    soru = {"tur": "kisa_cevap", "soru": "paydalar toplanir", "dogru": "5/6", "aciklama": "Eşitle."}
    _, aid, _ = _hazir(istemci, soru)
    body = istemci.post(f"/api/assistant/alistirmalar/{aid}/cevap",
                         json={"sira": 1, "cevap": "paydalar toplanir"}).get_json()
    assert body["dogru"] is False
    assert body["yanlis_analizi"]["baslik"] == "Kesirleri toplarken paylar ve paydalar ayrı ayrı toplanır"


def test_gunluk_sahibe_ve_istanbul_haftasina_gore(istemci):
    _, aid, _ = _hazir(istemci)
    for sira, cevap in enumerate(["5/6", "yanlış", "yanlış"], 1):
        assert istemci.post(f"/api/assistant/alistirmalar/{aid}/cevap", json={"sira": sira, "cevap": cevap}).status_code == 200
    body = istemci.get("/api/assistant/ogrenme-gunlugu").get_json()
    assert body["zayif"][0]["kazanim_kodu"] == "MAT.7.1.1"
    assert body["hafta"] == {"baslangic": "2026-09-28", "sohbet": [{"ogretmen": "matematik", "sayi": 1}],
                              "alistirma": 1, "puan": {"dogru": 1, "toplam": 3}}
    _giris(istemci, AILE)
    assert istemci.get("/api/assistant/ogrenme-gunlugu").get_json()["zayif"] == []
    _giris(istemci, OKUR)
    assert istemci.get("/api/assistant/ogrenme-gunlugu").status_code == 403


def test_cevap_kaydi_tum_alistirmalari_baglar_ve_atfi_yazar(istemci):
    sid, aid, depo = _hazir(istemci)
    aid2 = depo.alistirma_yaz(sid, ISIK, "matematik", "İkinci", "Matematik", "Kesir", None,
                             "orta", depo.alistirma_getir(aid)["sorular"], SIMDI)
    ctx = {"depo": depo, "sid": sid, "sahip_email": ISIK, "alistirma_kimlikleri": [aid, aid2]}
    payload = {**_answer(), "citations": [{"kind": "kitap", "label": "Kesirler sayfa 12",
                                          "locator": {"tool": "kitap_sayfa", "args": {}}}]}
    dashboard_api._sohbet_cevap_kaydet(ctx, payload, "matematik")
    mid = depo.tum_mesajlar(sid)[0]["id"]
    assert {a["id"] for a in depo.alistirmalar(mid)} == {aid, aid2}
    assert depo.gunluk(ISIK, SIMDI)["calisilan"][0]["sayfa_basligi"] == "Kesirler sayfa 12"
    dashboard_api._sohbet_cevap_kaydet({**ctx, "alistirma_kimlikleri": []}, payload, "genel")
    assert len(depo.gunluk(ISIK, SIMDI)["calisilan"]) == 1


def test_runtime_quiz_ilan_ve_kimlikleri_request_ile_tasinir(istemci, tmp_path, monkeypatch):
    from src.assistant_core import AssistantRuntime, ToolLoopResult
    sid, aid, depo = _hazir(istemci)
    runtime = AssistantRuntime(tmp_path)
    body = {k: depo.alistirma_getir(aid)[k] for k in ("baslik", "ders", "konu", "kazanim_kodu", "zorluk", "sorular")}
    kimlikler = []
    def loop(**kwargs):
        assert "alistirma_olustur" in {d["name"] for d in kwargs["declarations"]}
        outcomes = [kwargs["dispatch"]("alistirma_olustur", body) for _ in range(2)]
        assert all(o.ok for o in outcomes)
        return ToolLoopResult(text="Alıştırmalar hazır.", olaylar=[outcomes[0].olay])
    monkeypatch.setattr(runtime.llm, "chat_with_tools", loop)
    args = dict(messages=[{"role": "user", "content": "Kesir alıştırması"}], okur="ogrenci",
                ogretmen="matematik", sohbet_id=sid, not_deposu=depo,
                sahip_email=ISIK, alistirma_kimlikleri=kimlikler)
    payload = runtime.chat(**args)
    assert payload["quiz"]["id"] == kimlikler[0] and len(kimlikler) == 2
    assert "dogru" not in str(payload["quiz"])
    events = list(runtime.chat_events(**args))
    assert len(kimlikler) == 4
    assert len([e for e in events if e["event"] == "quiz"]) == 1
