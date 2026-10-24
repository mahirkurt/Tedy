"""Yazar SVG'si metin taşımaz (Modül Tasarım Kanunu M5.6; KB-48, 2026-10-24).

Şablonun çizdiği SVG viewBox'ı kutunun genişliğine kurar ve metni ≥ 12 px tutar (KB-5). Yazarın kendi çizdiği
SVG'de — `visual.kind:"svg"`'nin `ref`'i, etiketli şemanın `base`'i, `hotspot`'un `svg`'si — viewBox yazarındır:
şablon onu kutuya göre kuramaz, metni büyütürse yazarın şekilleriyle çakışır ve viewBox'ın dışına taşar. Bu
yüzden derleyici yazar SVG'sindeki metin öğesini (`<text>`, `<tspan>`, `<textPath>`, `<foreignObject>`) reddeder
ve yazarı adı etiketli şemanın `labels`'ına (numaralı iğne + liste) ya da gövde metnine/altyazıya yönlendirir.
Ölçüm (2026-10-23, Chromium, `fontSize × CTM.a`): altın QUIZ örneğinin diyagramında metin çerçeve 288'de 6,1 px,
358'de 8,3 px. Tarayıcıdaki ölçüm `dashboard/tests/e2e/modul-svg-metni.spec.ts`'tedir.
"""
import json
import re

import pytest

from src.mcp_server import derleme, gates, ornekler, rehber
from src.mcp_server.derleme import DerlemeHatasi

ORIGIN = "https://tedy.online"
SEKIL = ('<rect x="20" y="30" width="120" height="120" fill="var(--viz-2)" stroke="var(--viz-axis)" '
         'stroke-width="2"/>')
YAZAR_SVG = ('<svg viewBox="0 0 480 200" role="img" aria-labelledby="yt yd"><title id="yt">Üç kutu</title>'
             '<desc id="yd">Yan yana üç kutu.</desc>' + SEKIL + "{icerik}</svg>")


def _teach(data):
    return next(s for s in data["segments"] if s["type"] == "teach")


def _svgli_modul(icerik: str) -> dict:
    data = ornekler.ornek("MODULE")
    _teach(data)["visual"] = {"kind": "svg", "caption": "Şekil 1 — Üç kutu.", "ref": YAZAR_SVG.format(icerik=icerik)}
    return data


def _hatalar(data) -> list[str]:
    with pytest.raises(DerlemeHatasi) as exc:
        derleme.derle(data, {}, ORIGIN)
    assert exc.value.status == "sema_hatasi"
    return exc.value.detay["hatalar"]


@pytest.mark.parametrize("icerik", [
    '<text x="80" y="178" font-size="15">Katı</text>',
    '<text x="80" y="178"><tspan>Katı</tspan></text>',
    '<TEXT x="80" y="178">Katı</TEXT>',
    '<svg:text x="80" y="178">Katı</svg:text>',
    '<path id="yol" d="M0 0 H200"/><textPath href="#yol">Katı</textPath>',
    '<foreignObject x="0" y="0" width="200" height="40"><p>Katı</p></foreignObject>',
])
def test_yazar_svgsindeki_metin_ogesi_reddedilir_ve_yazar_yonlendirilir(icerik):
    hatalar = _hatalar(_svgli_modul(icerik))
    svg_hatasi = [h for h in hatalar if "KB-48" in h]
    assert len(svg_hatasi) == 1, hatalar
    mesaj = svg_hatasi[0]
    assert mesaj.startswith("MODULE_DATA.segments[") and ".visual.ref" in mesaj
    # Yönlendirme: etiketli şemanın labels'ı ya da gövde metni; neden: viewBox yazarındır, 12 px (M5.6).
    for parca in ("labels", "gövde metni", "M5.6", "12 px"):
        assert parca in mesaj, (parca, mesaj)


def test_etiketli_semanin_tabaninda_ve_hotspotta_metin_reddedilir():
    data = ornekler.ornek("MODULE")
    data["segments"].append({"type": "diagram", "id": "d9", "title": "Hücre", "viewBox": "0 0 480 300",
                             "base": SEKIL + '<text x="250" y="150">Çekirdek</text>',
                             "labels": [{"x": 250, "y": 150, "text": "Çekirdek"}]})
    _teach(data)["visual"] = {"kind": "labeled", "base": SEKIL + "<text>Zar</text>",
                              "labels": [{"x": 80, "y": 90, "text": "Zar"}]}
    data["segments"].append({"type": "hotspot", "id": "h9", "title": "Bul",
                             "svg": '<svg viewBox="0 0 480 200" role="img" aria-label="Kutular">'
                                    '<g data-spot="a">' + SEKIL + '</g><text x="10" y="20">A</text></svg>',
                             "spots": [{"id": "a", "label": "Kutu", "info": "Kutu bu."}]})
    yollar = sorted(h.split(":")[0] for h in _hatalar(data) if "KB-48" in h)
    teach = data["segments"].index(_teach(data))
    n = len(data["segments"])
    assert yollar == sorted([f"MODULE_DATA.segments[{teach}].visual.base", f"MODULE_DATA.segments[{n - 2}].base",
                             f"MODULE_DATA.segments[{n - 1}].svg"])


def test_govdeye_gomulu_svgdeki_metin_ve_dizi_ogelerine_bolunmus_etiket_reddedilir():
    data = ornekler.ornek("MODULE")
    _teach(data)["body"] = ["<p>Bak:</p><svg viewBox='0 0 100 20'><te", "xt x='0' y='15'>Katı</text></svg>"]
    hatalar = [h for h in _hatalar(data) if "KB-48" in h]
    assert len(hatalar) == 1 and ".body[*]" in hatalar[0], hatalar


def test_kacisli_metin_ve_benzer_adli_ogeler_metin_sayilmaz():
    # `&lt;text&gt;` ekranda düz yazıdır (innerHTML öğe kurmaz); <textarea> ve title/desc SVG metni değildir.
    # HTML ayrıştırıcısı `<` ile öğe adı arasında boşluk tanımaz: "a < text" düzyazıdır, öğe değil (inceleme, Küçük 7).
    data = _svgli_modul("")
    _teach(data)["body"] = ["<p>SVG'de &lt;text&gt; öğesi yazı çizer.</p>", "<p><textarea-yok></textarea-yok></p>",
                            "<p>If a &lt; b then a < text length.</p>"]
    html = derleme.derle(data, {}, ORIGIN)
    assert not [r for r in gates.run_gates(html).values() if r["status"] == "FAIL"]


def test_metinsiz_yazar_svgsi_derlenir_ve_kapilardan_gecer():
    data = _svgli_modul('<circle cx="80" cy="90" r="9" fill="var(--viz-1)"/>')
    html = derleme.derle(data, {}, ORIGIN)
    rapor = gates.run_gates(html)
    assert [k for k, r in rapor.items() if r["status"] == "FAIL"] == []
    assert rapor["G-SVG"]["status"] != "FAIL"


@pytest.mark.parametrize("mode", ornekler.MODES)
def test_altin_ornekler_yazar_svgsinde_metin_tasimaz(mode):
    data = ornekler.ornek(mode)
    metin = json.dumps(data, ensure_ascii=False)
    assert not re.search(r"<\s*(?:[a-z]+:)?(?:text|tspan|textpath|foreignobject)\b", metin, re.I)
    assert derleme.girdi_hatalari(data) == []


def test_altin_ornek_iki_yonlendirmeyi_de_gosterir():
    """Altın örnek iki yolu da taşır: metinsiz `visual.kind:"svg"` (adlar altyazıda ve gövdede) ve etiketli şema
    (adlar `labels`'ta, numaralı iğneyle)."""
    data = ornekler.ornek("MODULE")
    teach = [s for s in data["segments"] if s["type"] == "teach"]
    gorseller = {s["id"]: s.get("visual", {}) for s in teach}
    assert gorseller["t1"]["kind"] == "svg"
    assert all(ad in gorseller["t1"]["caption"].lower() for ad in ("katı", "sıvı", "gaz"))
    assert gorseller["t3"]["kind"] == "labeled"
    assert [L["text"] for L in gorseller["t3"]["labels"]] == ["Güneş", "Bulut", "Deniz ya da göl", "Buharlaşma",
                                                              "Yağış", "Toplanma"]


def test_rehber_ve_arac_yazara_yazar_svgsinin_metin_tasimadigini_soyler(tmp_path):
    import anyio

    from src.mcp_server import server, tools
    from src.mcp_server.config import load_settings

    toplam = rehber.guide("svg")["toplam_parca"]
    svg = "\n".join(rehber.guide("svg", parca=n)["metin"] for n in range(1, toplam + 1))
    assert "KB-48" in svg and "`labels`" in svg
    # İskelet ve arketipler artık yazarı SVG'ye metin yazmaya çağırmaz.
    assert not re.search(r'<text (?:class="viz-muted" )?x="…"', svg)
    assert "`line` + `text`" not in svg

    class _Fed:
        def configured(self, name):
            return False

    mcp = server.build_server(tools.Tools(load_settings({}, project_root=tmp_path), _Fed()))
    derle = {t.name: t for t in anyio.run(mcp.list_tools)}["edupedia_derle"].description
    for parca in ("<text>", "labels", "gövde metni"):
        assert parca in derle, parca


def test_data_uri_svg_reddedilir():
    """`data:image/svg+xml` ikinci bir yazar SVG'sidir ve metni de taşıyabilir; ikili içerik `meta.assets`'ten gelir
    (inceleme, Küçük 7). Yüzde kodlu ve base64 biçimi de yakalanır."""
    for govde in ("<p>Bak</p><img alt='üç kutu' src=\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg'"
                  "%3E%3Ctext y='15'%3EKat%C4%B1%3C/text%3E%3C/svg%3E\">",
                  "<svg viewBox='0 0 100 20' role='img' aria-label='x'><image href='DATA:image/SVG+xml;base64,PHN2Zz4="
                  "' width='100' height='20'/></svg>"):
        data = ornekler.ornek("MODULE")
        _teach(data)["body"] = [govde]
        hatalar = [h for h in derleme.girdi_hatalari(data) if "KB-48" in h]
        assert len(hatalar) == 1 and "data:image/svg+xml" in hatalar[0], hatalar
        assert "meta.assets" in hatalar[0]


def test_hotspot_svgsindeki_metin_hotspota_ozgu_iletiyle_reddedilir():
    """Hotspot'ta `labels` yoktur; bölgenin adı `spots[].label`'dadır ve soruda yazılır. SVG'ye yazılan ad hem 12 px'in
    altına düşer hem cevabı gösterir (inceleme, Küçük 8)."""
    data = ornekler.ornek("MODULE")
    data["segments"].append({"type": "hotspot", "id": "h9", "title": "Bul",
                             "svg": '<svg viewBox="0 0 480 200" role="img" aria-label="Kutular"><g data-spot="a">'
                                    + SEKIL + '</g><text x="10" y="20">Kutu</text></svg>',
                             "spots": [{"id": "a", "label": "Kutu", "info": "Kutu bu."}]})
    hatalar = [h for h in derleme.girdi_hatalari(data) if "KB-48" in h]
    assert len(hatalar) == 1 and hatalar[0].startswith(f"MODULE_DATA.segments[{len(data['segments']) - 1}].svg"), hatalar
    assert "spots[].label" in hatalar[0] and "cevab" in hatalar[0] and "labels'ına" not in hatalar[0]


# ── Yayın anı (inceleme, Önemli 3): eski şablonla derlenmiş taslak yayınlanmaz ─────────────────────────────

def _yayin_ortami(tmp_path):
    from src.mcp_server.derle_araci import Derleyici
    from src.mcp_server.katalog import CatalogWriter, Yayinci
    from src.mcp_server.runs import RunStore
    from src.mcp_server.taslak import DraftStore

    runs = RunStore(tmp_path)
    runs.save("abcdef012345", {
        "run_id": "abcdef012345", "created_by": "drmahirkurt@gmail.com",
        "cerceve": {"kind": "textbook", "document_id": 197, "title": "Fen Bilimleri 5", "sayfalar": "111-116"},
        "kazanimlar": [{"code": "FB.5.4.1.1", "text": "Maddenin hâllerini açıklar."}],
        "coverage": {"maarif-mufredat": "hit"},
    })
    drafts = DraftStore(tmp_path)
    derleyici = Derleyici(runs, drafts, "https://tedy.online", "https://tedy.online", clock=lambda: 1_800_000_000.0)
    yayinci = Yayinci(drafts, CatalogWriter(tmp_path, clock=lambda: 1_800_000_000.0), "https://tedy.online")
    return drafts, derleyici, yayinci


def test_taslak_kaydi_sablonun_parmak_izini_tasir(tmp_path):
    import json as _json

    from src.mcp_server import sablon
    from src.mcp_server.vendor_sync import VENDOR_DIR

    drafts, derleyici, _ = _yayin_ortami(tmp_path)
    taslak_id = derleyici.derle("drmahirkurt@gmail.com", "abcdef012345", ornekler.ornek("QUIZ"))["taslak_id"]
    beklenen = _json.loads((VENDOR_DIR / "PROVENANCE.json").read_text(encoding="utf-8"))["files"][
        "assets/module-template.html"]
    assert sablon.sablon_parmak_izi() == beklenen
    assert drafts.load(taslak_id)["sablon_parmak_izi"] == beklenen


@pytest.mark.parametrize("parmak_izi", [None, "0" * 64])
def test_eski_sablonla_derlenmis_taslak_yayinlanmaz(tmp_path, parmak_izi):
    from src.json_utils import atomic_json_dump
    from src import module_store as ms

    drafts, derleyici, yayinci = _yayin_ortami(tmp_path)
    taslak_id = derleyici.derle("drmahirkurt@gmail.com", "abcdef012345", ornekler.ornek("QUIZ"))["taslak_id"]
    kayit = drafts.load(taslak_id)
    if parmak_izi is None:
        kayit.pop("sablon_parmak_izi")
    else:
        kayit["sablon_parmak_izi"] = parmak_izi
    atomic_json_dump(kayit, str(ms.draft_dir(tmp_path, taslak_id) / ms.DRAFT_RECORD))
    govde = yayinci.yayinla("drmahirkurt@gmail.com", taslak_id)
    assert govde["status"] == "sablon_eski", govde
    assert "yeniden derle" in govde["not"] and "edupedia_derle" in govde["not"]
    assert not (tmp_path / "modules" / "index.json").exists()


def test_yazar_svg_metni_tasiyan_sakli_taslak_yayinlanmaz(tmp_path):
    """Kuraldan önce derlenmiş (ya da elle bozulmuş) bir taslağın MODULE_DATA'sı yayında yeniden taranır."""
    from src.mcp_server import sablon

    drafts, derleyici, yayinci = _yayin_ortami(tmp_path)
    taslak_id = derleyici.derle("drmahirkurt@gmail.com", "abcdef012345", ornekler.ornek("QUIZ"))["taslak_id"]
    kayit = drafts.load(taslak_id)
    html = drafts.html_bytes(taslak_id).decode("utf-8")
    bas = html.index(sablon.MODULE_DATA_START)
    eski = html[:bas] + html[bas:].replace('role="img"', 'role="img"><text x="80" y="178">Katı</text', 1)
    assert eski != html
    yeni_id = drafts.new_id()
    drafts.save(yeni_id, eski, {k: v for k, v in kayit.items() if k not in ("taslak_id", "bayt", "sha256")})
    govde = yayinci.yayinla("drmahirkurt@gmail.com", yeni_id)
    assert govde["status"] == "yazar_svg_metni", govde
    assert "KB-48" in govde["not"] and "yeniden derle" in govde["not"]
    assert yayinci.yayinla("drmahirkurt@gmail.com", taslak_id)["status"] == "ok"
