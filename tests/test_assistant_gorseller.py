"""Görev 4: wider MCP coverage and textbook figures that reach the model and the reader.

No network: fake MCP clients stand in for the servers, and a fake Anthropic
client for the model. The shapes are the real servers' (measured 2026-09-25 with
tools/list and one get_figure call): get_figure answers one JSON text block plus
one ImageContent block; an unknown id answers `{"error": "figure N not found"}`
with no image and no isError; egitim-kaynak answers text/event-stream with no
charset.
"""
import base64
import json
import os
import sys
from types import SimpleNamespace as NS

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["TEST_AUTH_BYPASS"] = "1"

from src.assistant_core import ClaudeClient  # noqa: E402
from src.assistant_tools import (  # noqa: E402
    GOVDE_SINIRI, SINIF_ARACLARI, TOOL_ALLOWLIST, McpRegistry, ToolOutcome,
)
from src.mcp_client import McpClient, McpToolResult  # noqa: E402

# A 1x1 PNG: real bytes, so the endpoint test proves the round trip.
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
PNG_B64 = base64.b64encode(PNG).decode()

# get_figure's metadata block, real field names, invented values.
FIGUR_META = {
    "figure_id": 1875, "document_id": 197,
    "title": "Fen Bilimleri 7.Sınıf Ders Kitabı", "kind": "textbook",
    "subject": "fen-bilimleri-dersi", "grade_or_grades": "7.Sınıf", "page_no": 114,
    "bbox": "48.3,525.0,505.5,728.7", "label": "",
    "caption": "Bitki hücresinin kesit çizimi: hücre duvarı, zar ve çekirdek.",
    "caption_kind": None, "nearby_text": "114 3. ÜNİTE", "mime": "image/png",
    "width": 1025, "height": 457, "n_bytes": 65451,
    "pdf_url": "https://tymm.meb.gov.tr/upload/kitap/ornek.pdf", "hidden": False,
}


def _schema(**props):
    return {"type": "object", "properties": {k: {"type": v} for k, v in props.items()},
            "required": list(props)[:1]}


MAARIF_TOOLS = [
    {"name": "get_curriculum_program", "description": "Öğretim programı.",
     "inputSchema": _schema(subject_slug="string", page_index="boolean")},
    {"name": "get_subject", "description": "Ders bilgisi.", "inputSchema": _schema(slug="string")},
    {"name": "list_videos", "description": "Videolar.", "inputSchema": {
        "type": "object", "properties": {"category": {"anyOf": [{"type": "string"}, {"type": "null"}]}}}},
    {"name": "get_video", "description": "Video.", "inputSchema": _schema(video_id="integer")},
    {"name": "get_figure", "description": "Figür.",
     "inputSchema": _schema(figure_id="integer", include_image="boolean")},
    {"name": "search_learning_outcomes", "description": "Kazanım.",
     "inputSchema": _schema(q="string", grade="string")},
]
EGITIM_TOOLS = [{"name": "kb_get", "description": "Belge aç.",
                 "inputSchema": _schema(doc_id="string", max_chars="integer")}]


class _FakeClient:
    def __init__(self, name, tools, results=None, healthy=True):
        self.name = name
        self._tools = tools
        self.results = results or {}
        self.healthy = healthy
        self.calls = []

    def list_tools(self):
        return self._tools

    def call_tool(self, name, arguments):
        self.calls.append((name, dict(arguments)))
        r = self.results.get(name, McpToolResult(ok=True, text="{}"))
        return r(arguments) if callable(r) else r


def _registry(maarif=None, egitim=None, sinif=None):
    clients = {}
    if maarif is not False:
        clients["maarif-mufredat"] = maarif or _FakeClient("maarif-mufredat", MAARIF_TOOLS)
    if egitim is not False:
        clients["egitim-kaynak"] = egitim or _FakeClient("egitim-kaynak", EGITIM_TOOLS)
    return McpRegistry(clients=clients, local_search=lambda q, k: [], sinif=sinif)


def _figur_sonucu(images=None):
    return McpToolResult(ok=True, text=json.dumps(FIGUR_META, ensure_ascii=False),
                         images=[{"data": PNG_B64, "mimeType": "image/png"}] if images is None else images)


# ── 1. the allowlist and the declarations ─────────────────────────────────────

def test_yeni_araclar_izin_listesinde_mcp_adlariyla():
    assert TOOL_ALLOWLIST["program_getir"] == ("maarif-mufredat", "get_curriculum_program")
    assert TOOL_ALLOWLIST["ders_bilgisi"] == ("maarif-mufredat", "get_subject")
    assert TOOL_ALLOWLIST["video_listele"] == ("maarif-mufredat", "list_videos")
    assert TOOL_ALLOWLIST["video_getir"] == ("maarif-mufredat", "get_video")
    assert TOOL_ALLOWLIST["oer_getir"] == ("egitim-kaynak", "kb_get")


def test_yeni_araclar_modele_ilan_edilir():
    adlar = {d["name"] for d in _registry().declarations()}
    assert {"program_getir", "ders_bilgisi", "video_listele", "video_getir", "oer_getir",
            "figur_getir"} <= adlar


def test_yeni_araclarin_semasinda_sinif_yok_ve_sinif_eklenmez():
    # Measured: get_subject, list_videos, get_curriculum_program, get_video and
    # kb_get take no `grade`; adding one would be an argument the server rejects.
    assert not {"program_getir", "ders_bilgisi", "video_listele", "video_getir",
                "oer_getir"} & SINIF_ARACLARI
    maarif = _FakeClient("maarif-mufredat", MAARIF_TOOLS)
    reg = _registry(maarif=maarif, sinif=lambda: "7.Sınıf")
    reg.dispatch("ders_bilgisi", {"slug": "ortaokul-matematik-dersi"})
    assert maarif.calls == [("get_subject", {"slug": "ortaokul-matematik-dersi"})]


@pytest.mark.parametrize("arac,kind", [
    ("program_getir", "mufredat"), ("ders_bilgisi", "mufredat"), ("video_listele", "mufredat"),
    ("video_getir", "mufredat"), ("oer_getir", "oer"),
])
def test_yeni_araclarin_atif_sinifi(arac, kind):
    out = _registry().dispatch(arac, {})
    assert out.ok is True
    assert out.citations[0]["kind"] == kind


def test_yeni_maarif_araclarinda_olu_baglanti_silinir():
    ders = {"slug": "ortaokul-matematik-dersi", "name": "Ortaokul Matematik Dersi",
            "programs": [{"document_id": 35, "title": "Ortaokul Matematik Dersi Öğretim Programı",
                          "pdf_url": "https://tymm.meb.gov.tr/x.pdf",
                          "source_url": "https://tymm.meb.gov.tr/y"}]}
    maarif = _FakeClient("maarif-mufredat", MAARIF_TOOLS, results={
        "get_subject": McpToolResult(ok=True, text=json.dumps(ders, ensure_ascii=False))})
    out = _registry(maarif=maarif).dispatch("ders_bilgisi", {"slug": "ortaokul-matematik-dersi"})
    assert "tymm.meb.gov.tr" not in out.text
    assert "Ortaokul Matematik Dersi Öğretim Programı" in out.text
    assert out.citations[0]["label"] == "MEB müfredatı · Ortaokul Matematik Dersi"


def test_video_listesi_govde_sinirina_sigar_ve_kalanini_soyler():
    videolar = [{"id": i, "category": "sinif-ici-etkinlik-videolari" if i % 2 else "egitim-videolari",
                 "title": f"Örnek video başlığı numara {i}", "url": f"https://tymm.meb.gov.tr/videolar/{i}",
                 "youtube_url": f"https://www.youtube.com/embed/v{i}", "description": "açıklama " * 5}
                for i in range(1, 158)]
    maarif = _FakeClient("maarif-mufredat", MAARIF_TOOLS, results={
        "list_videos": McpToolResult(ok=True, text="\n".join(json.dumps(v, ensure_ascii=False)
                                                             for v in videolar))})
    out = _registry(maarif=maarif).dispatch("video_listele", {})
    assert len(out.text) <= GOVDE_SINIRI
    assert "#1 " in out.text and "Örnek video başlığı numara 1" in out.text
    assert "category" in out.text  # the model is told how to narrow the list
    assert out.citations[0]["label"] == "MEB videoları"


def test_program_icindekiler_sinirda_uniteleri_korur():
    toc = [{"page_no": n, "head": f"{n}\nFEN BILIMLERI DERSI ÖĞRETIM PROGRAMI{n}\nAra sayfa metni {n} uzun uzun"}
           for n in range(1, 200)]
    toc.insert(150, {"page_no": 151, "head": "151\nFEN BILIMLERI DERSI ÖĞRETIM PROGRAMI151\n7. SINIF\n1. ÜNİTE: UZAY ÇAĞI"})
    program = {"subject": "fen-bilimleri-dersi",
               "document": {"document_id": 7, "title": "Fen Bilimleri Dersi Öğretim Programı",
                            "pdf_url": "https://tymm.meb.gov.tr/x.pdf"},
               "page_count": 234, "toc": toc}
    maarif = _FakeClient("maarif-mufredat", MAARIF_TOOLS, results={
        "get_curriculum_program": McpToolResult(ok=True, text=json.dumps(program, ensure_ascii=False))})
    out = _registry(maarif=maarif).dispatch("program_getir", {"subject_slug": "fen-bilimleri-dersi"})
    assert len(out.text) <= GOVDE_SINIRI
    assert "ÜNİTE: UZAY ÇAĞI" in out.text and "s.151" in out.text
    assert "FEN BILIMLERI DERSI ÖĞRETIM PROGRAMI151" not in out.text  # the run header is noise
    assert "tymm.meb.gov.tr" not in out.text
    assert out.citations[0]["label"] == "Öğretim programı · Fen Bilimleri Dersi Öğretim Programı"


def test_oer_getir_varsayilan_uzunluk_siniri_ve_etiket():
    belge = {"status": "ok", "doc_id": "phet:ornek", "title": "Kesir Oluştur", "license": "CC BY 4.0",
             "text": "metin", "truncated": True}
    egitim = _FakeClient("egitim-kaynak", EGITIM_TOOLS, results={
        "kb_get": McpToolResult(ok=True, text=json.dumps(belge, ensure_ascii=False))})
    reg = _registry(egitim=egitim)
    out = reg.dispatch("oer_getir", {"doc_id": "phet:ornek"})
    assert egitim.calls[0][1]["max_chars"] <= GOVDE_SINIRI - 1000
    assert out.citations[0]["label"] == "Açık eğitsel kaynak · Kesir Oluştur"
    reg.dispatch("oer_getir", {"doc_id": "phet:ornek", "max_chars": 500})
    assert egitim.calls[1][1]["max_chars"] == 500


# ── 2. figures: from the MCP result into the outcome ─────────────────────────

def test_figur_getir_gorseli_ve_figure_id_tasir():
    maarif = _FakeClient("maarif-mufredat", MAARIF_TOOLS, results={"get_figure": _figur_sonucu()})
    out = _registry(maarif=maarif).dispatch("figur_getir", {"figure_id": 1875})
    assert out.ok is True
    assert out.images == [{"data": PNG_B64, "mimeType": "image/png"}]
    c = out.citations[0]
    assert c["kind"] == "kitap"
    assert c["locator"]["figure_id"] == 1875
    assert c["locator"]["caption"] == FIGUR_META["caption"]
    assert c["label"] == "Fen Bilimleri 7.Sınıf Ders Kitabı · s.114 · görsel"
    # The picture travels to the model only; a citation is JSON for the reader.
    assert PNG_B64 not in json.dumps(out.citations)
    assert "tymm.meb.gov.tr" not in out.text


def test_bilinmeyen_figur_hata_olarak_doner():
    maarif = _FakeClient("maarif-mufredat", MAARIF_TOOLS, results={
        "get_figure": McpToolResult(ok=True, text='{"error": "figure 9 not found"}')})
    out = _registry(maarif=maarif).dispatch("figur_getir", {"figure_id": 9})
    assert out.ok is False and "not found" in (out.error or "")


def test_gorselsiz_arac_sonucunda_images_bos():
    assert _registry().dispatch("ders_bilgisi", {"slug": "x"}).images == []
    assert ToolOutcome(ok=True).images == []


# ── 3. figures: from the outcome into the model's tool_result ─────────────────

def _cevap(*bloklar, stop="end_turn"):
    return NS(content=list(bloklar), stop_reason=stop, model="claude-sonnet-5",
              usage=NS(input_tokens=1, output_tokens=1, cache_read_input_tokens=0,
                       cache_creation_input_tokens=0))


class _Sahte:
    def __init__(self, *cevaplar):
        self.cevaplar = list(cevaplar)
        self.istekler = []
        self.messages = self

    def create(self, **kw):
        self.istekler.append({**kw, "messages": list(kw["messages"])})
        return self.cevaplar.pop(0)


KONUSMA = [{"role": "system", "content": "S"}, {"role": "user", "content": "hücreyi göster"}]
BILDIRIM = [{"name": "figur_getir", "description": "d",
             "parameters": {"type": "object", "properties": {"figure_id": {"type": "integer"}}}}]


def _dongu(outcome):
    sahte = _Sahte(_cevap(NS(type="tool_use", id="t1", name="figur_getir", input={"figure_id": 1}),
                          stop="tool_use"),
                   _cevap(NS(type="text", text="Görselde hücre var [S1].")))
    c = ClaudeClient(api_key="test", client=sahte)
    out = c.chat_with_tools(KONUSMA, BILDIRIM, lambda ad, g: outcome)
    return out, sahte.istekler[1]["messages"][-1]["content"][0]


def _figur_outcome(images):
    return ToolOutcome(ok=True, text="figür metadata", images=images, citations=[{
        "kind": "kitap", "label": "Kitap · s.1 · görsel", "locator": {"figure_id": 1},
        "snippet": "", "confidence": 0.9}])


def test_gorsel_tool_result_icinde_image_blogu_olarak_gider():
    out, sonuc = _dongu(_figur_outcome([{"data": PNG_B64, "mimeType": "image/png"}]))
    assert sonuc["type"] == "tool_result" and sonuc["is_error"] is False
    icerik = sonuc["content"]
    assert isinstance(icerik, list)
    assert icerik[0]["type"] == "text" and icerik[0]["text"].startswith("[S1] Kitap · s.1 · görsel")
    assert icerik[1] == {"type": "image",
                         "source": {"type": "base64", "media_type": "image/png", "data": PNG_B64}}
    assert out.text == "Görselde hücre var [S1]."
    # The panel's citation never carries the picture.
    assert PNG_B64 not in json.dumps(out.citations)


def test_en_cok_iki_gorsel_gider():
    gorseller = [{"data": PNG_B64, "mimeType": "image/png"}] * 3
    _, sonuc = _dongu(_figur_outcome(gorseller))
    assert [b["type"] for b in sonuc["content"]] == ["text", "image", "image"]


def test_buyuk_gorsel_elenir_ve_metinde_soylenir():
    buyuk = {"data": "A" * 1_500_001, "mimeType": "image/png"}
    _, sonuc = _dongu(_figur_outcome([buyuk]))
    icerik = sonuc["content"]
    assert [b["type"] for b in icerik] == ["text"]
    assert "görsel çok büyük" in icerik[0]["text"]


def test_buyuk_gorsel_elenince_kucugu_yine_gider():
    buyuk = {"data": "A" * 1_500_001, "mimeType": "image/png"}
    _, sonuc = _dongu(_figur_outcome([buyuk, {"data": PNG_B64, "mimeType": "image/png"}]))
    assert [b["type"] for b in sonuc["content"]] == ["text", "image"]
    assert "görsel çok büyük" in sonuc["content"][0]["text"]


def test_gorselsiz_sonuc_eskisi_gibi_duz_metin():
    _, sonuc = _dongu(_figur_outcome([]))
    assert isinstance(sonuc["content"], str) and sonuc["content"].startswith("[S1]")


def test_gorselli_sonucta_metin_yine_4000de_kesilir():
    o = _figur_outcome([{"data": PNG_B64, "mimeType": "image/png"}])
    o.text = "x" * 10_000
    _, sonuc = _dongu(o)
    assert len(sonuc["content"][0]["text"]) <= 4000


# ── 4. the reader's figure endpoint ───────────────────────────────────────────

import src.dashboard_api as dashboard_api  # noqa: E402

FULL = "isikkurtx@gmail.com"
READER = "murzogluhulya@gmail.com"


@pytest.fixture
def figur_env(monkeypatch):
    maarif = _FakeClient("maarif-mufredat", MAARIF_TOOLS, results={
        "get_figure": lambda args: (_figur_sonucu() if args["figure_id"] < 1000
                                    else McpToolResult(ok=True, text=json.dumps(
                                        {"error": f"figure {args['figure_id']} not found"})))})
    reg = _registry(maarif=maarif)
    monkeypatch.setattr(dashboard_api, "_assistant_runtime", lambda: NS(registry=reg))
    monkeypatch.setattr(dashboard_api, "TEST_AUTH_BYPASS", True)
    dashboard_api._FIGUR_ONBELLEGI.clear()
    dashboard_api.app.config["TESTING"] = True
    with dashboard_api.app.test_client() as client:
        yield client, maarif, reg
    dashboard_api._FIGUR_ONBELLEGI.clear()


def test_figur_ucu_gorseli_bayt_olarak_dondurur(figur_env):
    client, maarif, _ = figur_env
    r = client.get("/api/assistant/figure/12")
    assert r.status_code == 200
    assert r.mimetype == "image/png"
    assert r.data == PNG
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert maarif.calls == [("get_figure", {"figure_id": 12, "include_image": True})]


def test_figur_ucu_onbellekten_okur(figur_env):
    client, maarif, _ = figur_env
    assert client.get("/api/assistant/figure/12").status_code == 200
    assert client.get("/api/assistant/figure/12").data == PNG
    assert len(maarif.calls) == 1


def test_figur_onbellegi_64_girdiyle_sinirli(figur_env):
    client, maarif, _ = figur_env
    for i in range(1, 66):
        assert client.get(f"/api/assistant/figure/{i}").status_code == 200
    assert len(dashboard_api._FIGUR_ONBELLEGI) == 64
    assert 1 not in dashboard_api._FIGUR_ONBELLEGI and 65 in dashboard_api._FIGUR_ONBELLEGI
    client.get("/api/assistant/figure/1")
    assert len(maarif.calls) == 66  # the evicted one is fetched again


def test_bilinmeyen_figur_404(figur_env):
    client, _, _ = figur_env
    r = client.get("/api/assistant/figure/5000")
    assert r.status_code == 404
    assert 5000 not in dashboard_api._FIGUR_ONBELLEGI


def test_mcp_kapaliyken_502_ve_turkce_cumle(figur_env, monkeypatch):
    client, maarif, _ = figur_env
    maarif.results["get_figure"] = McpToolResult(ok=False, error="timeout")
    r = client.get("/api/assistant/figure/12")
    assert r.status_code == 502
    hata = r.get_json()["error"]
    assert "ulaşılamadı" in hata or "ulaşamadı" in hata
    assert 12 not in dashboard_api._FIGUR_ONBELLEGI


def test_mufredat_sunucusu_yapilandirilmamissa_502(figur_env, monkeypatch):
    client, _, _ = figur_env
    reg = _registry(maarif=False)
    monkeypatch.setattr(dashboard_api, "_assistant_runtime", lambda: NS(registry=reg))
    assert client.get("/api/assistant/figure/12").status_code == 502


def test_desteklenmeyen_bicim_sunulmaz(figur_env):
    # A remote server must not choose what the dashboard's origin serves: an
    # SVG could carry script.
    client, maarif, _ = figur_env
    maarif.results["get_figure"] = _figur_sonucu(images=[
        {"data": base64.b64encode(b"<svg onload='x'/>").decode(), "mimeType": "image/svg+xml"}])
    assert client.get("/api/assistant/figure/12").status_code == 502


def test_figur_ucu_okura_ve_girissize_kapali(figur_env, monkeypatch):
    client, maarif, _ = figur_env
    monkeypatch.setattr(dashboard_api, "TEST_AUTH_BYPASS", False)
    assert client.get("/api/assistant/figure/12").status_code == 401
    with client.session_transaction() as sess:
        sess["user_email"] = READER
    assert client.get("/api/assistant/figure/12").status_code == 403
    assert maarif.calls == []
    with client.session_transaction() as sess:
        sess["user_email"] = FULL
    assert client.get("/api/assistant/figure/12").status_code == 200


# ── 5. the OER server's text reaches the model as Turkish, not mojibake ───────

def test_sse_yaniti_utf8_olarak_okunur():
    """Measured 2026-09-25: egitim-kaynak answers text/event-stream with no
    charset; requests then decodes the body as ISO-8859-1 and every Turkish
    letter in kb_search/kb_get reached the model as mojibake ("OluÅtur")."""
    govde = 'data: {"jsonrpc":"2.0","id":1,"result":{"title":"Kesir Oluştur"}}\n\n'.encode("utf-8")
    resp = NS(headers={"content-type": "text/event-stream"}, content=govde,
              text=govde.decode("iso-8859-1"))
    assert McpClient._decode(resp)["result"]["title"] == "Kesir Oluştur"


# ── 6. the prompt names the new tools ─────────────────────────────────────────

def test_istem_yeni_araclari_ve_figur_yonlendirmesini_anlatir():
    from src.assistant_core import AssistantRuntime
    istem = AssistantRuntime.SYSTEM_PROMPT
    for arac in ("program_getir", "ders_bilgisi", "video_listele", "video_getir", "oer_getir"):
        assert f"`{arac}`" in istem
    satir = next(s for s in istem.splitlines() if "`figur_getir`" in s)
    assert "`figur_ara`" in satir and "Kaynaklar" in satir


def test_figur_atfinin_ozeti_baslik_metnidir_json_degil():
    maarif = _FakeClient("maarif-mufredat", MAARIF_TOOLS, results={"get_figure": _figur_sonucu()})
    c = _registry(maarif=maarif).dispatch("figur_getir", {"figure_id": 1875}).citations[0]
    assert c["snippet"] == FIGUR_META["caption"]


# ── Fix round 1 ───────────────────────────────────────────────────────────────

def test_hata_zarfindaki_olu_baglanti_modele_gitmez():
    zarf = {"error": "program not found for subject", "subject": "turkce-dersi",
            "pdf_url": "https://tymm.meb.gov.tr/x.pdf", "source_url": "https://tymm.meb.gov.tr/y"}
    maarif = _FakeClient("maarif-mufredat", MAARIF_TOOLS, results={
        "get_curriculum_program": McpToolResult(ok=True, text=json.dumps(zarf))})
    out = _registry(maarif=maarif).dispatch("program_getir", {"subject_slug": "turkce-dersi"})
    assert out.ok is False
    assert "program not found" in out.error and "tymm.meb.gov.tr" not in out.error


def test_buyuk_figur_sunulur_ama_onbellege_girmez(figur_env):
    client, maarif, _ = figur_env
    buyuk = b"\x89PNG" + b"0" * dashboard_api.FIGUR_TEK_SINIRI
    maarif.results["get_figure"] = _figur_sonucu(images=[
        {"data": base64.b64encode(buyuk).decode(), "mimeType": "image/png"}])
    r = client.get("/api/assistant/figure/12")
    assert r.status_code == 200 and r.data == buyuk
    assert 12 not in dashboard_api._FIGUR_ONBELLEGI
    client.get("/api/assistant/figure/12")
    assert len(maarif.calls) == 2  # not cached, so fetched again


def test_figur_onbellegi_toplam_baytla_sinirli(figur_env, monkeypatch):
    client, _, _ = figur_env
    monkeypatch.setattr(dashboard_api, "FIGUR_TOPLAM_SINIRI", 3 * len(PNG))
    for i in range(1, 6):
        assert client.get(f"/api/assistant/figure/{i}").status_code == 200
    assert list(dashboard_api._FIGUR_ONBELLEGI) == [3, 4, 5]


@pytest.mark.parametrize("yol", ["/api/assistant/figure/0",
                                 "/api/assistant/figure/2147483648",
                                 "/api/assistant/figure/99999999999999999999999"])
def test_sinir_disi_figur_id_rotada_404(figur_env, yol):
    client, maarif, _ = figur_env
    assert client.get(yol).status_code == 404
    assert maarif.calls == []


def test_en_buyuk_gecerli_figur_id_sunucuya_sorulur(figur_env):
    client, maarif, _ = figur_env
    assert client.get("/api/assistant/figure/2147483647").status_code == 404  # fake: not found
    assert maarif.calls == [("get_figure", {"figure_id": 2147483647, "include_image": True})]


def test_pano_api_anahtari_figur_ucuna_401(figur_env, monkeypatch):
    # A dashboard integration key passes require_auth but is not assistant
    # access: the figure endpoint follows /api/assistant/stream.
    client, maarif, _ = figur_env
    monkeypatch.setattr(dashboard_api, "TEST_AUTH_BYPASS", False)
    monkeypatch.setattr(dashboard_api, "API_KEYS", [("entegrasyon", "tdyK_test")])
    monkeypatch.setattr(dashboard_api, "ASSISTANT_API_KEY", "asst_test")
    r = client.get("/api/assistant/figure/12", headers={"Authorization": "Bearer tdyK_test"})
    assert r.status_code == 401
    assert maarif.calls == []
