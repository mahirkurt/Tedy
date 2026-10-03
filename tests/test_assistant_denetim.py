"""B6 karar ve elle değerlendirme sözleşmesi; bütün testler çevrimdışıdır."""
import json
from pathlib import Path

import pytest

from src.assistant_denetim import (
    DENETIM_ISTEMI, DENETIM_MODEL, KURAL_SINIRI, denetim_gerekli,
    denetim_oku, denetim_uygula, ogretmen_kurallari, puanla, sorgu_dar,
)


@pytest.mark.parametrize("ogretmen,cevap,beklenen", [
    ("genel", "kısa", "genel_kisa"),
    ("genel", "a" * 799, "genel_kisa"),
    ("genel", "a" * 800, None),
    ("matematik", "kısa", None),
])
def test_kapi(ogretmen, cevap, beklenen):
    assert denetim_gerekli(ogretmen, cevap, []) == beklenen


def test_hata_cevabi_ogretmende_de_atlanir():
    assert denetim_gerekli("matematik", "yanıt yok", ["yanıt yok"]) == "hata_cevabi"
    assert denetim_gerekli("matematik", "yanıt yok.", ["yanıt yok"]) is None


def test_gercek_skill_sinirlari_kesilmez():
    from src.assistant_skills import yukle, govde_bolumleri

    skills = yukle()
    assert set(skills) == {"turkce", "fen", "sosyal", "matematik"}
    for skill in skills.values():
        kurallar = ogretmen_kurallari(skill.govde)
        assert "cevap anahtarı" in kurallar
        assert "## Maarif" not in kurallar
        assert kurallar.index("## Sınırlar") < kurallar.index("## Ders akışı")
        assert govde_bolumleri(skill)["Sınırlar"].strip() in kurallar
    assert len(govde_bolumleri(skills["turkce"])["Ders akışı"]) > KURAL_SINIRI


def test_uzun_akis_sinir_bolumunu_yutmaz():
    govde = "## Ders akışı\n" + "a" * 1684 + "\n## Maarif Modeli bağı\nGirme.\n"
    govde += "## Sınırlar\ncevap anahtarı yazılmaz.\n"
    kurallar = ogretmen_kurallari(govde)
    assert kurallar.startswith("## Sınırlar\ncevap anahtarı yazılmaz.")
    assert "Maarif" not in kurallar
    assert len(kurallar.split("\n\n", 1)[1]) <= KURAL_SINIRI


def test_karar_oku_cit_filtre_ve_tekrar():
    assert denetim_oku('{"ciddi": false}') == {"ciddi": False}
    ham = 'Ön metin\n```json\n{"ciddi": true, "sorun": ["kaynak", "uydurma", "kaynak"], "cevap": "yeni"}\n```\nSon'
    assert denetim_oku(ham) == {"ciddi": True, "sorun": ["kaynak"], "cevap": "yeni"}


@pytest.mark.parametrize("ham", [
    "bozuk", "[]", '{"ciddi": "false"}', '{"ciddi": 0}', '{}',
    '{"ciddi": true}', '{"ciddi": true, "sorun": [], "cevap": "yeni"}',
    '{"ciddi": true, "sorun": ["kaynak"], "cevap": ""}',
    '{"ciddi": true, "sorun": ["kaynak"], "cevap": 3}',
    '{"ciddi": true, "sorun": "kaynak", "cevap": "yeni"}',
    '{"ciddi": true, "sorun": ["uydurma"], "cevap": "yeni"}',
])
def test_bicim_hatalari(ham):
    with pytest.raises(ValueError):
        denetim_oku(ham)


def test_genel_modda_ogretmen_bakisi_yok():
    ham = '{"ciddi": true, "sorun": ["ogretmen"], "cevap": "yeni"}'
    with pytest.raises(ValueError):
        denetim_oku(ham, ogretmen_bakisi=False)
    ham = '{"ciddi": true, "sorun": ["ogretmen", "hitap"], "cevap": "yeni"}'
    assert denetim_oku(ham, ogretmen_bakisi=False)["sorun"] == ["hitap"]


@pytest.mark.parametrize("karar,yeni,durum,neden", [
    ({"ciddi": False}, "taslak", "gecti", None),
    ({"ciddi": True, "sorun": ["kaynak"], "cevap": "yeni"}, "yeni", "duzeltildi", None),
    ({"ciddi": True, "sorun": ["kaynak"], "cevap": " taslak "}, "taslak", "hata", "ayni"),
    ({"ciddi": True, "sorun": ["kaynak"], "cevap": "  "}, "taslak", "hata", "bos"),
])
def test_tek_duzeltme(karar, yeni, durum, neden):
    cevap, meta = denetim_uygula("taslak", karar)
    assert cevap == yeni
    assert meta["durum"] == durum
    assert meta["neden"] == neden
    assert meta["model"] == DENETIM_MODEL


def test_puan_kaynak_arac_ve_nokta_ayri():
    soru = {"arac": "kazanim_ara", "kaynak": "kesir", "noktalar": ["payda"]}
    cagrilar = [{"name": "kazanim_ara"}]
    atiflar = [{"label": "KESİRLER", "snippet": "payda", "locator": {"tool": "kazanim_ara"}}]
    puan = puanla(soru, "Payda eşitlenir, sonuç 5/6.", cagrilar, atiflar)
    assert all(puan[k] for k in ("arac_tamam", "kaynak_tamam", "nokta_tamam"))
    assert puan["cagrilan_araclar"] == ["kazanim_ara"]
    assert not puanla(soru, "Payda", [], atiflar)["arac_tamam"]
    assert not puanla(soru, "Payda", cagrilar, [])["kaynak_tamam"]
    eksik = puanla(soru, "Sonuç 5/6.", cagrilar, atiflar)
    assert not eksik["nokta_tamam"]
    assert eksik["eksik_noktalar"] == ["payda"]


@pytest.mark.parametrize("atif", [
    {"label": "", "snippet": "Kesirlerde", "locator": {}},
    {"label": "", "snippet": "", "locator": {"tool": "kesir"}},
])
def test_puan_snippet_ve_arac_kaynagi(atif):
    assert puanla({"arac": "a", "kaynak": "kesir", "noktalar": ["payda"]},
                  "Payda", [{"name": "a"}], [atif])["kaynak_tamam"]


@pytest.mark.parametrize("dusen,noktalar,beklenen", [
    (["neden"], ["neden"], True), (["neden"], ["payda"], False),
    (["mi"], ["kimyasal"], False), (["ÇOK"], ["birden çok"], True),
])
def test_sorgu_butun_token(dusen, noktalar, beklenen):
    assert sorgu_dar(dusen, noktalar) is beklenen


def test_kilitli_istem():
    plan = Path(__file__).resolve().parents[1] / "docs/superpowers/plans/2026-10-03-asistan-cevap-denetimi-b6.md"
    beklenen = plan.read_text().split("```text\n", 1)[1].split("\n```", 1)[0]
    assert DENETIM_ISTEMI == beklenen
    assert DENETIM_MODEL == "claude-haiku-4-5"


def test_altin_soru_semasi():
    from scripts.asistan_eval import sorulari_yukle
    from src.assistant_core import turkce_kucult_katla

    dersler = sorulari_yukle()
    assert set(dersler) == {"turkce", "fen", "sosyal", "matematik"}
    dusen = {"nedir", "nelerdir", "nasil", "neden", "nicin", "kim", "kimdir",
             "hangi", "kac", "mi", "mu"}
    for ders, sorular in dersler.items():
        assert len(sorular) == 3
        for i, soru in enumerate(sorular, 1):
            assert soru["id"] == f"{ders}-{i}"
            assert set(soru) == {"id", "soru", "arac", "kaynak", "noktalar"}
            assert soru["arac"] in {"kazanim_ara", "kitap_sayfa", "skill_kaynagi"}
            assert soru["kaynak"] and soru["soru"] and soru["noktalar"]
            for nokta in soru["noktalar"]:
                katli = turkce_kucult_katla(nokta)
                assert len(katli) >= 4 and katli not in dusen


def test_eval_onaysiz_istemci_ve_dosya_yok(tmp_path, monkeypatch):
    from scripts import asistan_eval

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(asistan_eval, "kos", lambda **kw: pytest.fail("onaysız koşu"))
    assert asistan_eval.main([]) == 2
    assert not (tmp_path / "output").exists()


def test_eval_dosya_onaysiz_src_import_etmez(tmp_path):
    import os
    import subprocess
    import sys

    betik = Path(__file__).resolve().parents[1] / "scripts/asistan_eval.py"
    assert betik.is_file()
    env = {k: v for k, v in os.environ.items() if k not in {"PYTHONPATH", "ANTHROPIC_API_KEY"}}
    run = subprocess.run([sys.executable, "-v", str(betik)], cwd=tmp_path, env=env,
                         capture_output=True, text=True, timeout=10)
    assert run.returncode == 2
    assert "import 'src" not in run.stderr
    assert not list(tmp_path.iterdir())


def test_sonuc_atomik_surumlu_yazilir(tmp_path, monkeypatch):
    from datetime import datetime, timezone
    from scripts import asistan_eval
    from src import json_utils

    yazilar = []
    gercek = json_utils.atomic_json_dump

    def kaydet(veri, yol, **kw):
        yazilar.append(yol)
        return gercek(veri, yol, **kw)

    monkeypatch.setattr(json_utils, "atomic_json_dump", kaydet)
    simdi = datetime(2026, 10, 3, 9, 45, tzinfo=timezone.utc)
    satirlar = [{"arac_tamam": True, "kaynak_tamam": False, "nokta_tamam": True}]
    bir = asistan_eval.sonuc_yaz(tmp_path, satirlar, "abc", simdi=simdi,
                                calistir_sayisi=12, model="cevap-modeli")
    ilk = bir.read_bytes()
    iki = asistan_eval.sonuc_yaz(tmp_path, [], "def", simdi=simdi, calistir_sayisi=0)
    assert bir == tmp_path / "20261003T094500Z/sonuc.json"
    assert iki == tmp_path / "20261003T094500Z-2/sonuc.json"
    assert bir.read_bytes() == ilk
    veri = json.loads(ilk)
    assert veri["surum"] == "1"
    assert veri["sorular_sha256"] == "abc"
    assert veri["model"] == "cevap-modeli"
    assert veri["denetim_model"] == DENETIM_MODEL
    assert veri["ozet"] == {"soru": 12, "arac_tamam": 1, "kaynak_tamam": 0, "nokta_tamam": 1}
    assert len(yazilar) == 2


def test_sorgu_dar_b3_isleviyle():
    from scripts.asistan_eval import dusen_tokenleri

    dusen = dusen_tokenleri("Payda neden eşitlenir?")
    assert dusen == ["neden"]
    assert sorgu_dar(dusen, ["neden"])
    assert not sorgu_dar(dusen, ["payda"])


def test_eval_kosu_bir_hatayla_durmaz(tmp_path):
    from scripts import asistan_eval
    from types import SimpleNamespace

    class SahteRuntime:
        llm = SimpleNamespace(model="cevap-modeli")

        def __init__(self):
            self.cagrilar = []

        def chat(self, **kw):
            self.cagrilar.append(kw)
            assert kw["okur"] == "ogrenci"
            assert kw["etkilesimli"] is False
            assert "sohbet_id" not in kw
            if len(self.cagrilar) == 1:
                raise RuntimeError("sızmaması gereken hata")
            return {"answer": "Payda eşitlenir.", "citations": [], "meta": {
                "model": "cevap-modeli", "tool_calls": [{"name": "kazanim_ara"}],
                "denetim": {"durum": "gecti", "neden": None, "sorun": [], "model": DENETIM_MODEL},
            }}

    runtime = SahteRuntime()
    yol = asistan_eval.kos(runtime=runtime, kok=tmp_path)
    sonuc = json.loads(yol.read_text())
    assert len(runtime.cagrilar) == 12
    assert sonuc["ozet"]["soru"] == 12
    assert len(sonuc["sorular_sha256"]) == 64
    ilk, ikinci = sonuc["sorular"][:2]
    assert ilk["cevap"] == ""
    assert ilk["denetim"]["durum"] == "hata"
    assert ilk["denetim"]["neden"] == "cagri"
    assert ikinci["denetim"]["durum"] == "gecti"
    assert set(ikinci) == {"id", "ogretmen", "arac_tamam", "kaynak_tamam", "nokta_tamam",
                          "eksik_noktalar", "cagrilan_araclar", "denetim", "sorgu_dar",
                          "dusen_tokenler", "cevap"}
    assert "sızmaması" not in yol.read_text()
