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
