"""edupedia_kapsam sayfa bulucu (2026-10-05): ilgiye göre pencere, kitap seçimi, elle aralık.

Canlı vaka: FB.7.1.5 (galaksi) 19-24'e, FB.7.1.4 (yıldızların yaşamı) 26-31'e düştü; doğru
bölüm document_id 439'un 34-50 aralığıydı. Bulucu figürleri sayfa numarasına göre sıralayıp en
erken (zayıf) isabeti alıyordu; sayfa metnini hiç aramıyor ve hep listedeki ilk kitabı seçiyordu.
"""
import pytest

from src.mcp_server import kapsam
from tests.test_mcp_kapsam import FakeFed, _build, _responses

KITAPLAR = [
    {"document_id": 439, "title": "Fen Bilimleri 7.Sınıf Ders Kitabı (1.Kitap)", "page_count": 153},
    {"document_id": 473, "title": "Fen Bilimleri 7.Sınıf Ders Kitabı (2.Kitap)", "page_count": 166},
]


def _fig(fid, page, doc=439):
    return {"figure_id": fid, "document_id": doc, "page_no": page, "label": f"G{fid}", "caption": "galaksi"}


def _hit(page, doc=439):
    return {"type": "page", "locator": {"document_id": doc, "page_no": page, "kind": "textbook"}, "snippet": "x"}


def _sayfa_metni(args):
    a, b = (int(x) for x in args["page_range"].split("-"))
    return {"document": {"document_id": args["document_id"]}, "truncated": False,
            "pages": [{"page_no": p, "text": f"sayfa {p}"} for p in range(a, b + 1)]}


# Canlı search_figures sırası (ilgi sırası) — 2026-10-05, "galaksi Samanyolu Andromeda evren ışık yılı gökada".
GALAKSI_FIGURLERI = [_fig(4233, 49), _fig(4232, 49), _fig(4229, 46), _fig(4221, 42), _fig(4234, 49),
                     _fig(4227, 45), _fig(4200, 23), _fig(4260, 65), _fig(4196, 20), _fig(4261, 65),
                     _fig(4222, 42), _fig(4236, 50)]
# Canlı search(q="galaksi", kind="textbook") sırası.
GALAKSI_SAYFALARI = [_hit(p) for p in (49, 47, 46, 13, 51, 48, 23, 50, 52)]


def _fed(figurler, sayfa_isabetleri=None, **over):
    def ara(args):
        isabet = (sayfa_isabetleri or {}).get(args["q"], [])
        return {"results": isabet, "included_outcome_fragment_types": ["outcome"]}
    return FakeFed(_responses({
        ("maarif-mufredat", "list_textbooks"): KITAPLAR,
        ("maarif-mufredat", "search_figures"): {"query": "x", "count": len(figurler), "figures": figurler},
        ("maarif-mufredat", "search"): ara,
        ("maarif-mufredat", "get_document_text"): _sayfa_metni,
        **over,
    }))


def _aralik(body):
    a, b = (int(x) for x in body["cerceve"]["sayfalar"].split("-"))
    return a, b


def test_guclu_kume_en_erken_zayif_isabeti_yener(tmp_path):
    fed = _fed(GALAKSI_FIGURLERI, {"galak*": GALAKSI_SAYFALARI})
    body, _ = _build(tmp_path, fed, konu="galaksi Samanyolu Andromeda evren ışık yılı gökada")
    a, b = _aralik(body)
    assert body["cerceve"]["document_id"] == 439
    assert 40 <= a <= 46 and b >= 50, body["cerceve"]
    assert b - a + 1 <= kapsam.PAGE_WINDOW_MAX
    sayfalar = [p["page_no"] for p in body["kaynak_verisi"]["kitap_sayfalari"]]
    assert sayfalar == list(range(a, b + 1))
    assert all(a <= f["page_no"] <= b for f in body["kaynak_verisi"]["figur_adaylari"])


def test_yalniz_figurle_de_kume_secilir(tmp_path):
    """Sayfa araması hiçbir şey döndürmese de ilgi sırası korunur: 20 ve 23'teki zayıf isabetler
    49'daki üç güçlü figürü yenemez."""
    body, _ = _build(tmp_path, _fed(GALAKSI_FIGURLERI), konu="galaksi Samanyolu Andromeda evren ışık yılı gökada")
    a, b = _aralik(body)
    assert a >= 40 and b >= 49


def test_sayfa_metni_tek_terimle_aranir_ve_kitapla_sinirlanir(tmp_path):
    fed = _fed(GALAKSI_FIGURLERI, {"galak*": GALAKSI_SAYFALARI})
    _build(tmp_path, fed, konu="galaksi Samanyolu Andromeda evren ışık yılı gökada")
    aramalar = fed.called("maarif-mufredat", "search")
    assert 1 <= len(aramalar) <= kapsam.SAYFA_ARAMA_TERIM_MAX
    for _, _, args, _ in aramalar:
        assert " " not in args["q"] and args["kind"] == "textbook"
        assert args["subject"] == "fen-bilimleri-dersi"
    assert aramalar[0][2]["q"] == "galak*"


def test_ikinci_kitaptaki_konu_bulunur(tmp_path):
    figurler = [_fig(9001, 82, doc=473), _fig(9002, 83, doc=473), _fig(9003, 20, doc=439)]
    body, _ = _build(tmp_path, _fed(figurler, {"elektrik*": [_hit(84, doc=473), _hit(82, doc=473)]}),
                     konu="elektrik devresi")
    assert body["cerceve"]["document_id"] == 473
    assert "2.Kitap" in body["cerceve"]["title"]
    a, b = _aralik(body)
    assert a <= 82 and b >= 84


def test_elle_sayfa_araligi_bulucuyu_atlar(tmp_path):
    fed = _fed(GALAKSI_FIGURLERI, {"galak*": GALAKSI_SAYFALARI})
    body, runs = _build(tmp_path, fed, konu="yıldızların yaşamı", sayfalar="34-50")
    assert body["cerceve"]["sayfalar"] == "34-50" and body["cerceve"]["document_id"] == 439
    assert body["cerceve"]["secim"] == "elle"
    assert fed.called("maarif-mufredat", "get_document_text")[0][2]["page_range"] == "34-50"
    assert not fed.called("maarif-mufredat", "search")
    assert [p["page_no"] for p in body["kaynak_verisi"]["kitap_sayfalari"]] == list(range(34, 51))
    assert all(34 <= f["page_no"] <= 50 for f in body["kaynak_verisi"]["figur_adaylari"])
    assert runs.load(body["run_id"])["girdi"]["sayfalar"] == "34-50"


def test_elle_aralik_ve_kitap_secilebilir(tmp_path):
    body, _ = _build(tmp_path, _fed(GALAKSI_FIGURLERI), konu="x", sayfalar="80-84", kitap_id=473)
    assert body["cerceve"]["document_id"] == 473 and body["cerceve"]["sayfalar"] == "80-84"


@pytest.mark.parametrize("sayfalar", ["50-34", "0-5", "1-26", "abc", "34", "34-", "-3-4"])
def test_bicimsiz_elle_aralik_cagri_yapmadan_reddedilir(tmp_path, sayfalar):
    fed = _fed(GALAKSI_FIGURLERI)
    body, _ = _build(tmp_path, fed, konu="x", sayfalar=sayfalar)
    assert body["status"] == "gecersiz_sayfalar"
    assert fed.calls == []


@pytest.mark.parametrize("kw,durum", [
    ({"sayfalar": "150-160"}, "gecersiz_sayfalar"),
    ({"sayfalar": "10-12", "kitap_id": 999}, "gecersiz_kitap"),
])
def test_kitaba_uymayan_elle_secim_reddedilir(tmp_path, kw, durum):
    body, _ = _build(tmp_path, _fed(GALAKSI_FIGURLERI), konu="x", **kw)
    assert body["status"] == durum
    assert "run_id" not in body


@pytest.mark.parametrize("metin,beklenen", [
    ("galaksi Samanyolu Andromeda evren ışık yılı gökada", ["galak*", "samanyol*", "andromeda*"]),
    ("Yıldızların yaşamını açıklayarak yapılandırabilme a) Yıldızların yaşamını inceleyerek",
     ["yıldız*", "yaşam*"]),
    ("yıldız yıldızların Yıldızları", ["yıldız*"]),
    ("elektrik devresi seri paralel", ["elektrik*", "devre*", "seri*"]),
    ("ve ile bir", []),
])
def test_arama_terimleri(metin, beklenen):
    assert kapsam.arama_terimleri(metin) == beklenen


def test_yavas_filoda_sayfa_aramasi_sonraki_adimlari_yemez(tmp_path):
    from tests.test_mcp_kapsam import _timed_build

    _, _, log = _timed_build(tmp_path, lambda tool, args: 9.0, konu="maddenin halleri")
    assert "search" not in [c["tool"] for c in log]
    _, _, hizli = _timed_build(tmp_path / "h", lambda tool, args: 0.5, konu="maddenin halleri")
    assert [c["tool"] for c in hizli].count("search") == 2  # "maddenin", "halleri"


def test_arac_sayfalar_ve_kitap_id_yi_gecirir(tmp_path):
    from src.mcp_server import server, tools
    from src.mcp_server.config import load_settings

    settings = load_settings({"TED_MCP_PUBLIC_BASE_URL": "https://mcp.tedy.online"}, project_root=tmp_path)
    mcp = server.build_server(tools.Tools(settings, None))
    arac = mcp._tool_manager.get_tool("edupedia_kapsam")
    sema = arac.parameters["properties"]
    assert {"sayfalar", "kitap_id"} <= set(sema)
