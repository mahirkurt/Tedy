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
# Etiket genişliği şablonun ölçülmüş Plex Sans tablosundan (VIZ_EM, em); node'dan bir kez okunur.
HARFLER = "0123456789-−+.,:%/() abcçdefgğhıijklmnoöprsştuüvyzqwxâîûABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZQWX≈"
BOSLUK = 3  # komşu iki etiket arasında en az bu kadar kullanıcı birimi


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
    parcalar = [esc, _blok("function vizEmTablosu("), re.search(r"const VIZ_METIN=[^\n]*", SABLON).group(0),
                "const VIZ_CIZICI=new Map();", "let vizSonG=VIZ_W;", "const NL_W=480, NL_PADX=28;"]
    for ad in ("vizId", "svgFigure", "vizNice", "vizKaydet", "vizMetinGenisligi", "vizGenislik", "vizOznitelik",
               "vizSatirla", "vizSayiEtiketleri", "vizChart", "vizChartSvg", "numOr", "clampNum", "numberLine",
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


def _satir_etiketleri(svg: str) -> dict[float, list[tuple[str, float, float, bool]]]:
    """Ortalanmış etiketler y satırına göre: {y: [(metin, x, font-size, kalın)]}, x sırasıyla."""
    satirlar: dict[float, list] = {}
    for m in re.finditer(r'<text([^>]*text-anchor="middle"[^>]*)>(.*?)</text>', svg, re.S):
        attrs, icerik = m.group(1), m.group(2)
        y = float(re.search(r'\by="([\d.\-]+)"', attrs).group(1))
        x = float(re.search(r'\bx="([\d.\-]+)"', attrs).group(1))
        fs, kalin = float(re.search(r'font-size="([\d.]+)"', attrs).group(1)), 'font-weight="600"' in attrs
        # İki satırlı etiket: her <tspan> kendi satırında (dy birikir).
        parcalar = re.findall(r'<tspan[^>]*dy="([\d.\-]+)"[^>]*>([^<]*)</tspan>', icerik) or [("0", icerik)]
        for dy, metin in parcalar:
            y += float(dy)
            satirlar.setdefault(round(y, 1), []).append((metin, x, fs, kalin))
    return {y: sorted(v, key=lambda e: e[1]) for y, v in satirlar.items()}


def _genislik(em: dict, metin: str, fs: float, kalin: bool = False) -> float:
    return sum(em.get(c, 0.6) for c in metin) * fs * (1.04 if kalin else 1)


def _cakisanlar(em: dict, svg: str) -> list:
    """Aynı satırda komşu iki ortalı etiketin kutuları (ölçülmüş genişlikle) BOSLUK'tan yakınsa çakışır."""
    bulunan = []
    for y, etiketler in _satir_etiketleri(svg).items():
        for (m1, x1, f1, k1), (m2, x2, f2, k2) in zip(etiketler, etiketler[1:]):
            if x2 - x1 < (_genislik(em, m1, f1, k1) + _genislik(em, m2, f2, k2)) / 2 + BOSLUK - 1e-6:
                bulunan.append((y, m1, m2, round(x2 - x1, 1)))
    return bulunan


IFADELER = {
    "sayi_dogrusu": "numberLine({min:-10,max:10,step:1,points:[{value:-3,label:'A'},{value:4,label:'B'}]}, G)",
    "sayi_dogrusu_noktasiz": "numberLine({min:-10,max:10,step:1}, G)",
    "etkilesimli_sayi_dogrusu": "numberLine({min:0,max:20,step:1,interactive:true,value:7}, G)",
    "cubuk": ("vizChart({data:[{label:'Tarım',value:18},{label:'Sanayi',value:27},{label:'Hizmetler',value:41},"
              "{label:'Turizm',value:9},{label:'Madencilik ve taş ocakçılığı',value:3},{label:'Ulaştırma'}]}, G)"),
    "cizgi": ("vizChart({kind:'line',data:['Ocak','Şubat','Mart','Nisan','Mayıs','Haziran','Temmuz','Ağustos',"
              "'Eylül','Ekim','Kasım','Aralık'].map((a,i)=>({label:a,value:(i*37)%90}))}, G)"),
    "cubuk_kisa": "vizChart({data:[{label:'Tarım',value:18},{label:'Sanayi',value:27},{label:'Hizmet',value:41},{label:'Turizm',value:9}]}, G)",
    # Altın örneğin çubuk grafiği (ornekler.gorsel_ornegi c1): masaüstünde dikey sığar.
    "cubuk_ornek": ("vizChart({data:[{label:'Tarım',value:18},{label:'Sanayi',value:27},{label:'Hizmetler',value:41},"
                    "{label:'Turizm',value:9},{label:'Madencilik',value:3},{label:'Ulaştırma'}]}, G)"),
    # İki sözcüklü etiket iki satıra bölünürse dikey sığar.
    "cubuk_iki_satir": ("vizChart({data:[{label:'Hizmet sektörü',value:18},{label:'Tarım alanı',value:27},"
                        "{label:'Sanayi üretimi',value:41},{label:'Turizm geliri',value:9},"
                        "{label:'Maden işleri',value:3},{label:'Ulaşım ağı',value:12}]}, G)"),
    # Yayındaki mat7 "Çekirgenin altı eşit sıçrayışı"na benzer: nokta değerleri her genişlikte okunur.
    "cekirge": "numberLine({min:-6,max:8,step:1,points:[-5,-3,-1,1,3,5,7].map(v=>({value:v}))}, G)",
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
    govde.append(f"sonuc.em={{}}; for(const c of {json.dumps(HARFLER)}) sonuc.em[c]=vizMetinGenisligi(c,1);")
    govde.append("process.stdout.write(JSON.stringify(sonuc));")
    return _calistir("let G;\n" + "\n".join(govde))


def test_genislik_tablosu_olculen_plex_sans(cizimler):
    """VIZ_EM Chromium'da gömülü IBM Plex Sans'tan ölçüldü (getComputedTextLength, 2026-10-23): rakam 0,6 em,
    tire 0,4 em; "-10" 1,6 em. Eski tahmin (her harf 0,6 em) "-10"u 1,8, "Madencilik"i 6,0 em sayıyordu."""
    em = cizimler["em"]
    assert round(_genislik(em, "-10", 12), 1) == 19.2
    assert round(_genislik(em, "Madencilik", 1), 2) == 4.85
    assert em["1"] == 0.6 and em["-"] == 0.4 and em["ı"] == 0.25 and em["m"] == 0.867


@pytest.mark.parametrize("kutu", KUTULAR)
def test_her_cizicinin_metni_her_kutuda_en_az_12_px(cizimler, kutu):
    kucuk = [(ad, metin, round(px, 2)) for ad, html in cizimler[str(kutu)].items()
             for metin, px, _x, _a in _metinler(html, kutu) if px < 12 - 1e-9]
    assert kucuk == [], kucuk


def _tik_etiketleri(svg: str) -> list[str]:
    """Sayı doğrusunun tik etiketleri (ortalı, kalın olmayan, sayı)."""
    return [m for etiketler in _satir_etiketleri(svg).values() for m, _x, _f, kalin in etiketler
            if not kalin and re.fullmatch(r"-?\d+(?:\.\d+)?", m)]


@pytest.mark.parametrize("ad", ["sayi_dogrusu", "etkilesimli_sayi_dogrusu", "cekirge", "cubuk", "cubuk_kisa",
                                "cubuk_ornek", "cubuk_iki_satir", "cizgi", "sim_numberScale"])
@pytest.mark.parametrize("kutu", KUTULAR)
def test_ayni_satirdaki_etiketler_olculmus_genislikle_cakismaz(cizimler, kutu, ad):
    assert _cakisanlar(cizimler["em"], cizimler[str(kutu)][ad]) == []


@pytest.mark.parametrize("kutu", KUTULAR)
def test_sayi_dogrusu_sifiri_ve_uclari_etiketler(cizimler, kutu):
    assert {"-10", "0", "10"} <= set(_tik_etiketleri(cizimler[str(kutu)]["sayi_dogrusu"]))


def test_sayi_dogrusu_sigan_her_etiketi_yazar(cizimler):
    """Seyreltme yalnız gerçekten sığmayanı düşürür: masaüstünde −10…10'un 21 etiketi de sığar; çerçeve 358'in
    kutusunda (~268) ikişer. Eski tahmin masaüstünde ikişer, 358'de beşer yazıyordu."""
    assert len(_tik_etiketleri(cizimler["800"]["sayi_dogrusu"])) == 21
    assert len(_tik_etiketleri(cizimler["800"]["etkilesimli_sayi_dogrusu"])) == 21
    assert _tik_etiketleri(cizimler["268"]["sayi_dogrusu_noktasiz"]) == [str(v) for v in range(-10, 11, 2)]
    dar = _tik_etiketleri(cizimler["198"]["etkilesimli_sayi_dogrusu"])
    assert 4 <= len(dar) < 21 and "0" in dar and "20" in dar


@pytest.mark.parametrize("kutu", KUTULAR)
def test_nokta_degerleri_her_genislikte_okunur(cizimler, kutu):
    """Kanun M5.6 (inceleme kararı): `points`'in değerine denk gelen tik her genişlikte etiketlidir."""
    etiketler = _tik_etiketleri(cizimler[str(kutu)]["cekirge"])
    assert {str(v) for v in (-5, -3, -1, 1, 3, 5, 7)} <= set(etiketler), (kutu, etiketler)
    a_b = _tik_etiketleri(cizimler[str(kutu)]["sayi_dogrusu"])
    assert {"-3", "4"} <= set(a_b), (kutu, a_b)


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
            assert _genislik(cizimler["em"], tspan, 12) <= vw, tspan  # bölünebilen satır kutuya sığar


def test_cubuk_grafik_dikey_sigiyorsa_dikey_kalir(cizimler):
    """İnceleme kararı: eşik ölçülmüş genişlikle; dikey sığıyorsa dikey kalır. Altın örneğin çubuk grafiği
    masaüstünde dikeydir (eski tahminle 1440'ta ~580 px'lik yatay çubuğa dönüyordu)."""
    genis, dar = cizimler["800"]["cubuk_kisa"], cizimler["198"]["cubuk_kisa"]
    assert genis.count('text-anchor="middle"') == 4 and 'viewBox="0 0 480 ' in genis
    assert 'text-anchor="middle"' not in dar and 'viewBox="0 0 198 ' in dar
    ornek = cizimler["800"]["cubuk_ornek"]
    assert ornek.count('text-anchor="middle"') == 7 and ">Madencilik<" in ornek  # 6 etiket + "veri yok"
    # İki sözcüklü etiket iki satıra bölünür, çubuk dikey kalır.
    iki = cizimler["800"]["cubuk_iki_satir"]
    assert iki.count('text-anchor="middle"') == 6 and "<tspan" in iki and ">sektörü<" in iki
    # Tek satıra da iki satıra da sığmayan etiket (28 harf) çubuğu masaüstünde de yataylaştırır.
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
