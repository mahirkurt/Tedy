"""skill_kaynagi ve mod_oner (spec §1 "Modele bağlama"): moda göre ilan edilen iki araç.

- skill_kaynagi yalnız bir öğretmen modunda ilan edilir ve yalnız o öğretmenin references/
  listesindeki bir adı açar; liste dışı ad ve yol geçişi reddedilir.
- mod_oner yalnız genel modda ilan edilir; hiçbir şeyi değiştirmez, okurun akışına bir
  mode_suggestion olayı bırakır.
Her ikisi de öbür modda dispatch() tarafından da reddedilir (aile_kaynak_ara gibi).
"""
import re
from pathlib import Path

import pytest

from src import assistant_skills
from src.assistant_tools import (MOD_GEREKCE_SINIRI, MOD_ONER_TOOL, SKILL_TOOL, ToolOutcome,
                                 build_registry)
from tests.skill_ornegi import KAYNAKLAR, iki_skill, skill_yaz

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _mcp_yok(monkeypatch):
    # No remote server: the registry must not reach the network in these tests.
    for env in ("MUFREDAT_MCP_API_KEY", "EGITIM_KAYNAK_MCP_API_KEY"):
        monkeypatch.delenv(env, raising=False)


@pytest.fixture
def reg(tmp_path):
    return build_registry(lambda q, k: [], skills=iki_skill(tmp_path))


def _adlar(reg, ogretmen):
    return [d["name"] for d in reg.declarations("ogrenci", ogretmen=ogretmen)]


def test_skill_yoksa_hicbir_modda_ogretmen_araci_yok():
    reg = build_registry(lambda q, k: [])
    for ogretmen in ("genel", "matematik"):
        assert not {SKILL_TOOL, MOD_ONER_TOOL} & set(_adlar(reg, ogretmen))


def test_genel_modda_yalniz_mod_oner(reg):
    adlar = _adlar(reg, "genel")
    assert MOD_ONER_TOOL in adlar and SKILL_TOOL not in adlar
    decl = next(d for d in reg.declarations(ogretmen="genel") if d["name"] == MOD_ONER_TOOL)
    assert decl["parameters"]["properties"]["ogretmen"]["enum"] == ["turkce", "matematik"]
    assert decl["parameters"]["required"] == ["ogretmen", "gerekce"]


def test_ogretmen_modunda_yalniz_skill_kaynagi(reg):
    adlar = _adlar(reg, "matematik")
    assert SKILL_TOOL in adlar and MOD_ONER_TOOL not in adlar
    decl = next(d for d in reg.declarations(ogretmen="matematik") if d["name"] == SKILL_TOOL)
    assert decl["parameters"]["properties"]["ad"]["enum"] == sorted(KAYNAKLAR)


def test_mod_araclari_listenin_sonunda(reg):
    # Every mode shares the list up to the teacher tools.
    genel, mat = _adlar(reg, "genel"), _adlar(reg, "matematik")
    assert genel[:-1] == mat[:-1]
    assert genel[-1] == MOD_ONER_TOOL and mat[-1] == SKILL_TOOL


def test_bilinmeyen_modda_ogretmen_araci_yok(reg):
    assert not {SKILL_TOOL, MOD_ONER_TOOL} & set(_adlar(reg, "tarih"))


# ── mod_oner ───────────────────────────────────────────────────────────────

def test_mod_oner_olay_birakir_ve_hicbir_sey_degistirmez(reg):
    out = reg.dispatch(MOD_ONER_TOOL, {"ogretmen": "matematik",
                                       "gerekce": "Bu bir oran-orantı sorusu."}, ogretmen="genel")
    assert out.ok and out.citations == []
    assert "Mod değişmedi" in out.text
    assert out.olay == {"event": "mode_suggestion", "ogretmen": "matematik",
                        "ogretmen_adi": "Matematik öğretmeni",
                        "soru": "Matematik öğretmenine geçelim mi?",
                        "gerekce": "Bu bir oran-orantı sorusu.", "renk_ailesi": "purple"}


def test_mod_oner_ogretmen_modunda_reddedilir(reg):
    out = reg.dispatch(MOD_ONER_TOOL, {"ogretmen": "turkce", "gerekce": "x"}, ogretmen="matematik")
    assert not out.ok and out.olay is None
    assert "yalnız genel modda" in out.error


def test_mod_oner_varsayilan_mod_genel(reg):
    assert reg.dispatch(MOD_ONER_TOOL, {"ogretmen": "turkce", "gerekce": "Bir metin sorusu."}).ok


@pytest.mark.parametrize("args,hata", [
    ({"ogretmen": "tarih", "gerekce": "x"}, "ogretmen şunlardan biri olmalı: turkce, matematik"),
    ({"ogretmen": "genel", "gerekce": "x"}, "ogretmen şunlardan biri olmalı"),
    ({"ogretmen": "matematik", "gerekce": "   "}, "gerekce boş olamaz"),
    ({}, "ogretmen şunlardan biri olmalı"),
])
def test_mod_oner_gecersiz_arguman(reg, args, hata):
    out = reg.dispatch(MOD_ONER_TOOL, args, ogretmen="genel")
    assert not out.ok and hata in out.error


def test_mod_oner_uzun_gerekce_kirpilir(reg):
    out = reg.dispatch(MOD_ONER_TOOL, {"ogretmen": "matematik", "gerekce": "uzun " * 100},
                       ogretmen="genel")
    assert len(out.olay["gerekce"]) <= MOD_GEREKCE_SINIRI
    assert out.olay["gerekce"].endswith("…")


# ── skill_kaynagi ──────────────────────────────────────────────────────────

def test_skill_kaynagi_etkin_ogretmenin_notunu_acar(reg):
    out = reg.dispatch(SKILL_TOOL, {"ad": "kavram-yanilgilari.md"}, ogretmen="matematik")
    assert out.ok and out.citations == []
    assert out.text.startswith("kavram-yanilgilari.md · sayfa 1/1\n\n")
    assert "Paydalar toplanmaz" in out.text
    assert "Devamı" not in out.text


def test_skill_kaynagi_genel_modda_reddedilir(reg):
    out = reg.dispatch(SKILL_TOOL, {"ad": "kavram-yanilgilari.md"}, ogretmen="genel")
    assert not out.ok and "yalnız bir öğretmen modunda" in out.error


@pytest.mark.parametrize("ad", ["../SKILL.md", "../../turkce/SKILL.md", "/etc/passwd", "SKILL.md",
                                "references/unite-haritasi.md", "unite-haritasi", "", None, 5])
def test_skill_kaynagi_liste_disini_ve_yol_gecisini_reddeder(reg, ad):
    out = reg.dispatch(SKILL_TOOL, {"ad": ad}, ogretmen="matematik")
    assert not out.ok
    assert out.error == "ad şunlardan biri olmalı: " + ", ".join(sorted(KAYNAKLAR))


def test_skill_kaynagi_sayfa_sayfa(tmp_path):
    uzun = "\n\n".join(f"Paragraf {i}: " + "kelime " * 80 for i in range(40))
    skill_yaz(tmp_path, kaynaklar={**KAYNAKLAR, "unite-haritasi.md": uzun})
    from src import assistant_skills
    reg = build_registry(lambda q, k: [], skills=assistant_skills.yukle(tmp_path))
    ilk = reg.dispatch(SKILL_TOOL, {"ad": "unite-haritasi.md"}, ogretmen="matematik")
    toplam = int(ilk.text.split("\n", 1)[0].rsplit("/", 1)[1])
    assert toplam > 1
    assert "(Devamı: skill_kaynagi ad='unite-haritasi.md' sayfa=2)" in ilk.text
    son = reg.dispatch(SKILL_TOOL, {"ad": "unite-haritasi.md", "sayfa": toplam}, ogretmen="matematik")
    assert son.ok and "Devamı" not in son.text
    assert "Paragraf 39:" in son.text
    for sayfa in (0, toplam + 1):
        out = reg.dispatch(SKILL_TOOL, {"ad": "unite-haritasi.md", "sayfa": sayfa}, ogretmen="matematik")
        assert not out.ok and f"sayfa 1–{toplam}" in out.error
    for sayfa in ("2", 2.0, True):
        assert not reg.dispatch(SKILL_TOOL, {"ad": "unite-haritasi.md", "sayfa": sayfa},
                                ogretmen="matematik").ok


def test_tooloutcome_olay_varsayilan_bos():
    assert ToolOutcome(ok=True).olay is None


# ── final-fix item 9: TS fixtures pinned to the Python shapes ──────────────
#
# A simple regex/key-set comparison — not a general JS parser — good enough
# for these small, hand-written object literals. It must fail the moment
# either side (the TS fixture or the Python shape) gains or loses a key.

def _ust_seviye_anahtarlar(kaynak: str, baslangic_isareti: str) -> set:
    """The top-level keys of the object literal whose first '{' follows
    `baslangic_isareti`, found by brace-depth counting so nested objects
    (karsilama/hizli_sorular) do not leak their own keys into the result."""
    start = kaynak.index(baslangic_isareti)
    brace_start = kaynak.index("{", start)
    depth, i = 0, brace_start
    while i < len(kaynak):
        if kaynak[i] == "{":
            depth += 1
        elif kaynak[i] == "}":
            depth -= 1
            if depth == 0:
                break
        i += 1
    govde = kaynak[brace_start + 1:i]

    parcalar, derinlik, basi = [], 0, 0
    for j, ch in enumerate(govde):
        if ch in "{[(":
            derinlik += 1
        elif ch in "}])":
            derinlik -= 1
        elif ch == "," and derinlik == 0:
            parcalar.append(govde[basi:j])
            basi = j + 1
    parcalar.append(govde[basi:])

    anahtarlar = set()
    for parca in parcalar:
        m = re.match(r"\s*([a-zA-Z_][a-zA-Z0-9_]*)", parca)
        if m:
            anahtarlar.add(m.group(1))
    return anahtarlar


def test_e2e_ogretmenler_fikstürü_python_seciciyle_ayni_anahtarlari_tasir():
    kaynak = (ROOT / "dashboard" / "tests" / "e2e" / "_gorsel-fixtures.ts").read_text("utf-8")
    ts_anahtarlar = _ust_seviye_anahtarlar(kaynak, "const ogretmen = (")

    skiller = assistant_skills.varsayilan()
    assert skiller, "gerçek skiller yüklenemedi — karşılaştırma anlamsız olurdu"
    py_anahtarlar = set(next(iter(skiller.values())).secici_ozeti())
    assert all(set(s.secici_ozeti()) == py_anahtarlar for s in skiller.values())

    assert ts_anahtarlar == py_anahtarlar


def test_e2e_oneri_fikstürü_mod_oner_olayiyla_ayni_anahtarlari_tasir(reg):
    kaynak = (ROOT / "dashboard" / "tests" / "e2e" / "carbon-asistan-ogretmen.spec.ts").read_text("utf-8")
    ts_anahtarlar = _ust_seviye_anahtarlar(kaynak, "const ONERI = {")

    out = reg.dispatch(MOD_ONER_TOOL, {"ogretmen": "matematik", "gerekce": "x"}, ogretmen="genel")
    assert out.ok
    py_anahtarlar = set(out.olay) - {"event"}

    assert ts_anahtarlar == py_anahtarlar
