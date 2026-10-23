"""SVG metni her genişlikte ekranda en az 12 px (Modül Tasarım Kanunu M5.6; KB-5, 2026-10-23).

Şablonun çizicileri viewBox'ı kutunun genişliğine (kök boyuna indirgenmiş px, en çok 480) kurar; bir
kullanıcı birimi ekranda en az 1 CSS px olur. Burada çiziciler node'da verilen kutu genişlikleriyle
koşturulur ve her metnin ekrandaki boyu `font-size × (kutu / viewBox genişliği)` olarak hesaplanır.
Tarayıcıdaki asıl ölçüm (`fontSize × getScreenCTM().a`) `dashboard/tests/e2e/modul-svg-metni.spec.ts`'tedir.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

SABLON = Path("src/mcp_server/vendor/assets/module-template.html").read_text(encoding="utf-8")
# §6.1: çerçeve 272 (bugün ekran 320), 288 ve 358 (KB-31 sonrası), 342 (ekran 390) ile masaüstü ve 4K;
# kutu, çerçeveden sahne ve figür dolgusu düşülmüş genişliktir (ör. çerçeve 288 → ~214).
KUTULAR = (180, 198, 214, 268, 284, 400, 480, 800)
HARF = 0.6


def _blok(ad: str) -> str:
    bas = SABLON.index(ad)
    i = SABLON.index("{", bas)
    derinlik = 0
    for j in range(i, len(SABLON)):
        if SABLON[j] == "{":
            derinlik += 1
        elif SABLON[j] == "}":
            derinlik -= 1
            if derinlik == 0:
                return SABLON[bas:j + 1]
    raise AssertionError(ad)


def _calistir(govde: str):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node yok")
    esc = re.search(r"const esc = s => [^\n]*", SABLON).group(0)
    parcalar = [esc, re.search(r"const VIZ_METIN=[^\n]*", SABLON).group(0), "const VIZ_CIZICI=new Map();",
                "let vizSonG=VIZ_W;", "const NL_W=480, NL_PADX=28;"]
    for ad in ("vizId", "svgFigure", "vizNice", "vizKaydet", "vizMetinGenisligi", "vizGenislik", "vizOznitelik",
               "vizSatirla", "vizSeyrelt", "vizChart", "vizChartSvg", "numOr", "clampNum", "numberLine",
               "numberLineCiz", "fractionBar", "labeledFigure"):
        parcalar.append(_blok(f"function {ad}("))
    parcalar.append(_blok("const SIM_PRESETS = {") + ";")
    parcalar.append(govde)
    cikti = subprocess.run([node, "-e", "\n".join(parcalar)], capture_output=True, text=True, check=True, timeout=60)
    return json.loads(cikti.stdout)


def _metinler(svg: str, kutu: float) -> list[tuple[str, float, float, str]]:
    """(metin, ekrandaki px, x, text-anchor) — kutu genişliğinde çizilen SVG'nin her <text>'i."""
    vw = float(re.search(r'viewBox="[\d.\-]+ [\d.\-]+ ([\d.]+) ', svg).group(1))
    olcek = kutu / vw
    out = []
    for m in re.finditer(r"<text([^>]*)>(.*?)</text>", svg, re.S):
        attrs, icerik = m.group(1), re.sub(r"<[^>]+>", " ", m.group(2)).strip()
        fs = float(re.search(r'font-size="([\d.]+)"', attrs).group(1))
        x = re.search(r'\bx="([\d.\-]+)"', attrs)
        anchor = re.search(r'text-anchor="(\w+)"', attrs)
        out.append((icerik, fs * olcek, float(x.group(1)) if x else 0.0, anchor.group(1) if anchor else "start"))
    return out


IFADELER = {
    "sayi_dogrusu": "numberLine({min:-10,max:10,step:1,points:[{value:-3,label:'A'},{value:4,label:'B'}]}, G)",
    "etkilesimli_sayi_dogrusu": "numberLine({min:0,max:20,step:1,interactive:true,value:7}, G)",
    "cubuk": ("vizChart({data:[{label:'Tarım',value:18},{label:'Sanayi',value:27},{label:'Hizmetler',value:41},"
              "{label:'Turizm',value:9},{label:'Madencilik ve taş ocakçılığı',value:3},{label:'Ulaştırma'}]}, G)"),
    "cizgi": ("vizChart({kind:'line',data:['Ocak','Şubat','Mart','Nisan','Mayıs','Haziran','Temmuz','Ağustos',"
              "'Eylül','Ekim','Kasım','Aralık'].map((a,i)=>({label:a,value:(i*37)%90}))}, G)"),
    "cubuk_kisa": "vizChart({data:[{label:'Tarım',value:18},{label:'Sanayi',value:27},{label:'Hizmet',value:41},{label:'Turizm',value:9}]}, G)",
    "kesir": "fractionBar({addends:[1,2,3],den:8}, G)",
    "oran": "fractionBar({ratio:[2,3],labels:['Kız','Erkek']}, G)",
    "sema": "labeledFigure({viewBox:'0 0 480 300',labels:[{x:250,y:150,text:'a'},{x:110,y:110,text:'b'}]}, G)",
}


@pytest.fixture(scope="module")
def cizimler():
    govde = ["const sonuc={};"]
    for kutu in KUTULAR:
        govde.append(f"G={kutu}; sonuc[{kutu}]={{}};")
        for ad, ifade in IFADELER.items():
            govde.append(f"sonuc[{kutu}][{json.dumps(ad)}]=String({ifade});")
        for preset, deger in (("numberScale", "{value:13}"), ("pendulum", "{length:2.2, angle:75}"),
                              ("projectile", "{speed:20, angle:45}")):
            govde.append(f"(function(){{ const svg={{innerHTML:''}}; SIM_PRESETS.{preset}(svg, {deger}, {{}}, "
                         f"vizGenislik(G)); sonuc[{kutu}]['sim_{preset}']=`<svg viewBox=\"0 0 ${{vizGenislik(G)}} 240\">`"
                         f"+svg.innerHTML+'</svg>'; }})();")
    govde.append("process.stdout.write(JSON.stringify(sonuc));")
    return _calistir("let G;\n" + "\n".join(govde))


@pytest.mark.parametrize("kutu", KUTULAR)
def test_her_cizicinin_metni_her_kutuda_en_az_12_px(cizimler, kutu):
    kucuk = [(ad, metin, round(px, 2)) for ad, html in cizimler[str(kutu)].items()
             for metin, px, _x, _a in _metinler(html, kutu) if px < 12 - 1e-9]
    assert kucuk == [], kucuk


@pytest.mark.parametrize("kutu", KUTULAR)
def test_sayi_dogrusu_etiketleri_cakismaz_ve_sifir_ile_uclar_etiketlidir(cizimler, kutu):
    metinler = [(m, x) for m, _px, x, a in _metinler(cizimler[str(kutu)]["sayi_dogrusu"], kutu)
                if a == "middle" and re.fullmatch(r"-?\d+", m)]
    degerler = [int(m) for m, _x in metinler]
    assert {-10, 0, 10} <= set(degerler), degerler
    for (m1, x1), (m2, x2) in zip(metinler, metinler[1:]):
        assert x2 - x1 >= (len(m1) + len(m2)) / 2 * 12 * HARF, (kutu, m1, m2)


def test_genis_kutuda_sayi_dogrusu_her_tam_sayiyi_yazar_dar_kutuda_seyreltir(cizimler):
    def sayilar(kutu, ad="etkilesimli_sayi_dogrusu"):
        return [m for m, _p, _x, a in _metinler(cizimler[str(kutu)][ad], kutu) if a == "middle"]
    assert len(sayilar(800)) == 21  # 0..20, masaüstünde seyreltme yok
    assert 4 <= len(sayilar(198)) < 21 and "0" in sayilar(198) and "20" in sayilar(198)


@pytest.mark.parametrize("kutu", (180, 198, 214, 268))
def test_dar_kutuda_cubuk_etiketi_cubugun_ustune_iner(cizimler, kutu):
    svg = cizimler[str(kutu)]["cubuk"]
    assert 'text-anchor="middle"' not in svg  # x ekseni etiketi yok: yatay çubuk
    for etiket in ("Tarım", "Hizmetler", "Ulaştırma"):
        assert f">{etiket}<" in svg
    assert "veri yok" in svg  # eksik değer 0 çizilmez (B52)
    vw = float(re.search(r'viewBox="0 0 ([\d.]+) ', svg).group(1))
    for tspan in re.findall(r"<tspan[^>]*>([^<]*)</tspan>", svg):
        if " " in tspan:
            assert len(tspan) * 12 * HARF <= vw, tspan  # bölünebilen satır kutuya sığar


def test_genis_kutuda_cubuk_grafik_dikey_kalir_dar_kutuda_yataylasir(cizimler):
    genis, dar = cizimler["800"]["cubuk_kisa"], cizimler["198"]["cubuk_kisa"]
    assert genis.count('text-anchor="middle"') == 4 and 'viewBox="0 0 480 260"' in genis
    assert 'text-anchor="middle"' not in dar and 'viewBox="0 0 198 ' in dar
    # Etiketi sütununa sığmayan çubuk geniş ekranda da yataydır (28 harflik etiket).
    assert 'text-anchor="middle"' not in cizimler["800"]["cubuk"]


@pytest.mark.parametrize("kutu", KUTULAR)
def test_kutu_kaydi_ve_genislik_ozniteligi(cizimler, kutu):
    for ad in ("sayi_dogrusu", "cubuk", "kesir", "sema"):
        svg = cizimler[str(kutu)][ad]
        assert re.search(r'data-viz="v[0-9a-z]+" data-viz-g="%d"' % kutu, svg), ad
        vw = float(re.search(r'viewBox="[\d.]+ [\d.]+ ([\d.]+) ', svg).group(1))
        # Şablonun kendi çizimi kutuya kurulur; etiketli şemanın viewBox'ı yazarındır (480).
        assert vw == (480 if ad == "sema" else min(480, kutu)), (ad, vw)


def test_gozlemciler_bolum_ve_genislik_degisiminde_kurar():
    # İçerik değişince boyamadan önce (MutationObserver), sahne genişliği değişince bir sonraki karede
    # (ResizeObserver + requestAnimationFrame: gözlemci döngüsü hatası olmadan) yeniden kurulur.
    blok = _blok("(function vizGozlemcileri(){")
    assert "new MutationObserver" in blok and "childList:true,subtree:true" in blok
    assert "new ResizeObserver" in blok and "requestAnimationFrame" in blok
    assert "VIZ_CIZICI.clear();" in _blok("function render(){")


def test_gorsel_ornegi_kapilardan_gecer_ve_her_cizici_turunu_tasir():
    """e2e'nin derlediği altın örnek (ornekler.gorsel_ornegi): her çizici türü, raster figür ve ses; FAIL yok."""
    from src.mcp_server import derleme, gates, ornekler
    data, varliklar = ornekler.gorsel_ornegi()
    rapor = gates.run_gates(derleme.derle(data, varliklar, "https://tedy.online"))
    assert sorted(g for g, v in rapor.items() if v["status"] == "FAIL") == []
    turler = {s["type"] for s in data["segments"]} | {s.get("visual", {}).get("kind") for s in data["segments"]}
    assert {"numberline", "chart", "fraction", "diagram", "sim"} <= turler
    assert {s["simType"] for s in data["segments"] if s["type"] == "sim"} == {"numberScale", "pendulum", "projectile"}
