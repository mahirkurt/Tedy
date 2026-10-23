"""Alt metnin dayanağı (Modül Tasarım Kanunu M3.6; KB-10, 2026-10-23).

Alt metindeki özel adlar ve sayılar figürün kendi açıklamasında (caption) ya da çerçeve sayfalarının
metninde geçer. Geçmeyen ad ya da sayı derlemeyi durdurur; yazar gerekçeyi `meta.assets[i].alt_gerekce`'ye
yazarsa derleme uyarıyla geçer. Denetim `edupedia_derle`'de run'ın sayfa metni ve varlık kaydıyla koşar.
"""
import base64
import io
import json

import pytest
from PIL import Image

from src.mcp_server import alt_metin, ornekler
from src.mcp_server.derle_araci import Derleyici
from src.mcp_server.derleme import GomuluVarlik
from src.mcp_server.runs import RunStore
from src.mcp_server.taslak import DraftStore
from src.mcp_server.varliklar import AssetStore

FULL = "drmahirkurt@gmail.com"
RUN_ID = "abcdef012345"
ASSET = "a1b2c3d4e5f60718"
RUN_RECORD = {
    "run_id": RUN_ID, "created_by": FULL,
    "cerceve": {"kind": "textbook", "document_id": 197, "title": "Fen Bilimleri 5", "sayfalar": "111-116"},
    "kazanimlar": [{"code": "FB.5.4.1.1", "text": "Maddenin hâllerini açıklar."}],
    "coverage": {"maarif-mufredat": "hit"},
}
SAYFA = "Kastamonu'nun İnebolu ilçesinden Ankara'ya uzanan yolda halk 1921 kışında cephane taşıdı."
ACIKLAMA = "İstiklal Yolu üzerinde kağnılarla cephane taşıyan halk."
DAYANAKLI = "İnebolu'dan Ankara'ya uzanan İstiklal Yolu'nda kağnılar cephane taşıyor."
BASLIK = "Görsel 1.30: İstiklal Yolu yürüyüşü"


# ── birim: ad ve sayı denetimi ──────────────────────────────────────────────

@pytest.mark.parametrize("alt, kaynak, beklenen", [
    ("Uçuş testindeki KAAN savaş uçağı F-35 ile birlikte gösteriliyor.", "Milli muharip uçak KAAN ilk uçuşunu yaptı.",
     ["F-35"]),
    ("Yürüyen askerler toprak bir yolda kağnıların yanında ilerliyor.", "", []),
    ("Atatürk'ün Samsun'a çıktığı gün kıyıda toplanan halk görülüyor.", "Atatürk 1919'da Samsun'a çıktı.", []),
    ("Atatürk'ün Samsun'a çıktığı gün kıyıda toplanan halk görülüyor.", "", ["Atatürk", "Samsun"]),
    ("TBMM binasının önünde toplanan milletvekilleri görülüyor.", "Meclis binası", ["TBMM"]),
    ("Haritada 1919 ve 1920 yıllarında açılan cepheler işaretli.", "1919 yılında", ["1920"]),
    ("Kâğıt üzerinde 3,5 metre uzunluğunda bir çizgi çizilmiş.", "uzunluğu 3.5 m olan", []),
    ("Haritada İNEBOLU limanı ile Hâkimiyet tepesi gösteriliyor.", "inebolu limanı, hakimiyet tepesi", []),
    ("Kıyıdaki Kemal heykelinin önünde çiçekler duruyor.", "Kemalpaşa ilçesi", []),  # ad öneki yeter
    ("Kıyıdaki Paşa heykelinin önünde çiçekler duruyor.", "Kemalpaşa ilçesi", ["Paşa"]),  # sözcük içi sayılmaz
])
def test_dayanaksiz_adlar(alt, kaynak, beklenen):
    assert alt_metin.dayanaksiz_adlar(alt, kaynak) == beklenen


# ── edupedia_derle ──────────────────────────────────────────────────────────

def _png():
    buf = io.BytesIO()
    Image.new("RGB", (40, 30), (120, 80, 40)).save(buf, format="PNG")
    return buf.getvalue()


def _varlik(aciklama=ACIKLAMA, etiket="Görsel 1.30", alt=""):
    return GomuluVarlik(asset_id=ASSET, tur="image", mime="image/jpeg",
                        data_uri="data:image/jpeg;base64," + base64.b64encode(_png()).decode(), bayt=200,
                        credit="Görsel: T.C. Millî Eğitim Bakanlığı, Türkiye Yüzyılı Maarif Modeli yayını",
                        lisans="MEB yayını — yalnız aile içi eğitim kullanımı", alt=alt, kaynak="mufredat",
                        aciklama=aciklama, etiket=etiket)


@pytest.fixture
def ortam(tmp_path):
    runs = RunStore(tmp_path)
    runs.save(RUN_ID, RUN_RECORD)
    runs.save_page(RUN_ID, 197, 112, SAYFA)
    return runs, tmp_path


def _derleyici(ortam, varlik):
    runs, tmp_path = ortam
    return Derleyici(runs, DraftStore(tmp_path), "https://tedy.online", "https://tedy.online",
                     assets=lambda run_id: {varlik.asset_id: varlik}, clock=lambda: 1_800_000_000.0)


def _modul(**alanlar):
    data = ornekler.ornek("QUIZ")
    teach = next(s for s in data["segments"] if s["type"] == "teach")
    teach.pop("visual", None)
    data["meta"]["assets"] = [{"asset_id": ASSET, "slot": f"{teach['id']}.visual", "baslik": BASLIK, **alanlar}]
    return data


def test_kaynakta_gecen_adlar_derlenir(ortam):
    body = _derleyici(ortam, _varlik()).derle(FULL, RUN_ID, _modul(alt=DAYANAKLI))
    assert body["status"] == "ok", body
    assert "uyarilar" not in body


def test_kaynakta_gecmeyen_ad_derlemeyi_durdurur(ortam):
    alt = "Uçuş testindeki KAAN savaş uçağı İnebolu limanının üzerinden geçiyor."
    body = _derleyici(ortam, _varlik()).derle(FULL, RUN_ID, _modul(alt=alt))
    assert body["status"] == "alt_metin_dayanaksiz", body
    assert any("meta.assets[0].alt" in h and "«KAAN»" in h for h in body["hatalar"]), body
    assert "alt_gerekce" in body["not"]
    assert not list((ortam[1] / "edupedia_drafts").glob("*")) if (ortam[1] / "edupedia_drafts").exists() else True


def test_gerekce_yazilirsa_uyariyla_derlenir(ortam):
    alt = "Uçuş testindeki KAAN savaş uçağı İnebolu limanının üzerinden geçiyor."
    gerekce = "Kitap uçağı yalnız 'milli muharip uçak' diye anıyor; adı KAAN'dır."
    body = _derleyici(ortam, _varlik()).derle(FULL, RUN_ID, _modul(alt=alt, alt_gerekce=gerekce))
    assert body["status"] == "ok", body
    assert any("«KAAN»" in u and gerekce in u for u in body["uyarilar"]), body
    kayit = DraftStore(ortam[1]).load(body["taslak_id"])
    assert kayit["uyarilar"] == body["uyarilar"]


def test_sus_gorseli_denetlenmez(ortam):
    body = _derleyici(ortam, _varlik(aciklama="")).derle(FULL, RUN_ID, _modul(alt=""))
    assert body["status"] == "ok", body


def test_eski_varlik_kaydi_kendi_alt_metnine_dayanir(ortam):
    # Alanlardan önce kaydedilmiş varlık yalnız 200 karakterlik `alt` taşır; dayanak odur.
    eski = _varlik(aciklama="", etiket="", alt="KAAN milli muharip uçağı")
    alt = "Uçuş testindeki KAAN savaş uçağı İnebolu limanının üzerinden geçiyor."
    assert _derleyici(ortam, eski).derle(FULL, RUN_ID, _modul(alt=alt))["status"] == "ok"


def test_etiketsiz_baslik_uyari_verir(ortam):
    # Altyazı kitaptaki adıyladır (M3.7): kitap figürünün etiketi başlıkta yoksa yazar uyarılır.
    data = _modul(alt=DAYANAKLI)
    data["meta"]["assets"][0]["baslik"] = "İstiklal Yolu yürüyüşü"
    body = _derleyici(ortam, _varlik()).derle(FULL, RUN_ID, data)
    assert body["status"] == "ok"
    assert any("baslik" in u and "Görsel 1.30" in u for u in body["uyarilar"]), body


# ── varlık kaydı ve edupedia_gorsel ─────────────────────────────────────────

def test_varlik_kaydi_tam_aciklamayi_ve_etiketi_tutar(ortam):
    runs, _ = ortam
    store = AssetStore(runs)
    uzun = "Kağnı " * 120
    rec = store.save(RUN_ID, _png(), "image", "mufredat", "MEB", "Görsel: MEB", uzun, FULL,
                     aciklama=uzun, etiket="Görsel 1.30")
    assert rec["aciklama"] == uzun.strip()[:2000] and len(rec["aciklama"]) > 200
    assert rec["etiket"] == "Görsel 1.30"
    gomulu = store.gomulu(RUN_ID)[rec["asset_id"]]
    assert gomulu.aciklama == rec["aciklama"] and gomulu.etiket == "Görsel 1.30"
    assert json.loads((runs.root / RUN_ID / "assets" / f"{rec['asset_id']}.json").read_text())["alt"] == uzun[:200]
