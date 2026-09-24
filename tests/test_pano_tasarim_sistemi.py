"""Tedy Tasarım Sistemi v3 on the dashboard (vendor/references/tedy-integration.md).

The module template is held to the system by its gates, and the dashboard's
colours by test_ders_renkleri (every hex a Carbon palette step). These pin the
rest of what the system says about the dashboard, where it can be measured:

- no colour arithmetic: no rgba/alpha colour, gradient, colour filter or
  color-mix — every colour is a token or a named palette step (§1);
- the brand navy only on the band: header, login hero (§1 "Eylem rengi değildir");
- no hand-written hex in a stylesheet: a role token, or `colors.$…` by name;
- no subject colour on a Tag: a Carbon Tag in magenta, purple, teal, cyan or
  blue reads as a course (§3.1 "Panoda");
- calendar events coloured by their course, never by a meaning colour: every
  homework red and every private lesson orange was a colour doing a category's
  job (§3.1 "Ayrılmış renkler").

Tedy Books is out of scope on purpose: the reading room is its own world
(docs/frontend-surface-designs.md §4.11), with cloth and paper the system does
not describe. So is Carbon for AI's own gradient on the assistant: it is
Carbon's, not ours.
"""
import os
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("TEST_AUTH_BYPASS", "1")

DASH = ROOT / "dashboard" / "src"
THEME = DASH / "theme" / "ted-theme.scss"
BOOKS_HEADER = "   Tedy Books\n"


def _pano_stilleri() -> list[tuple[str, str]]:
    tema = THEME.read_text(encoding="utf-8")
    kesim = tema.index(BOOKS_HEADER)
    kesim = tema.rindex("/*", 0, kesim)
    out = [("ted-theme.scss", tema[:kesim])]
    for p in sorted((DASH / "components").glob("*.scss")):
        if not p.name.startswith("BookReader"):
            out.append((p.name, p.read_text(encoding="utf-8")))
    return out


def _yorumsuz(metin: str) -> str:
    """Comments blanked out, every offset and line number kept."""
    metin = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), metin, flags=re.S)
    return re.sub(r"(?m)(^|[ \t])//[^\n]*", lambda m: " " * len(m.group(0)), metin)


def _bildirimler(ad: str, metin: str):
    """(file:line, declaration) — whole declarations, so one split over two
    lines is read as one."""
    temiz = _yorumsuz(metin)
    for m in re.finditer(r"[^;{}]+", temiz):
        kod = " ".join(m.group(0).split())
        if kod:
            satir = temiz.count("\n", 0, m.start() + len(m.group(0)) - len(m.group(0).lstrip())) + 1
            yield f"{ad}:{satir}", kod


def _secici(temiz: str, konum: int) -> str:
    """The selector chain of the rule blocks around `konum`, outermost first
    (comments blanked) — a nested `&::before` is read with its parent."""
    zincir, derinlik, i = [], 0, konum
    while i > 0:
        i -= 1
        if temiz[i] == "}":
            derinlik += 1
        elif temiz[i] == "{":
            if derinlik == 0:
                bas = max(temiz.rfind(";", 0, i), temiz.rfind("}", 0, i), temiz.rfind("{", 0, i)) + 1
                zincir.append(" ".join(temiz[bas:i].split()))
            else:
                derinlik -= 1
    return " > ".join(reversed(zincir)) or ":root"


# Shadows are the one place alpha is part of the token itself (the Tedy layer
# defines --tedy-shadow-card that way); they are declared once, as tokens.
GOLGE_TANIMI = re.compile(r"^--ted-shadow-[a-z-]+:")
# Carbon for AI's own treatment, drawn by Carbon's mixins and AI tokens.
CARBON_AI = re.compile(r"ai\.ai-|theme\.\$ai-")


def test_pano_renk_aritmetigi_yapmaz():
    ihlal = []
    for ad, metin in _pano_stilleri():
        for yer, kod in _bildirimler(ad, metin):
            if GOLGE_TANIMI.match(kod) or CARBON_AI.search(kod):
                continue
            if re.search(r"\brgba?\(|\bhsla?\(|gradient\(|color-mix\(|filter:\s*(grayscale|brightness|saturate)", kod):
                ihlal.append(f"{yer}  {kod}")
    assert not ihlal, "renk aritmetiği:\n" + "\n".join(ihlal)


MARKA_YERI = re.compile(r"cds--header|dashboard-header|login-page__hero|^:root$|^:root >|^html|app-root")


def test_marka_laciverdi_yalniz_bantta():
    ihlal = []
    for ad, metin in _pano_stilleri():
        temiz = _yorumsuz(metin)
        for m in re.finditer(r"var\(--ted-color-brand-primary(-hover)?\)", temiz):
            secici = _secici(temiz, m.start())
            if not MARKA_YERI.search(secici):
                satir = temiz.count("\n", 0, m.start()) + 1
                ihlal.append(f"{ad}:{satir}  {secici}")
    assert not ihlal, "marka laciverdi bant dışında:\n" + "\n".join(ihlal)


def test_stilde_elle_yazilmis_hex_yok():
    ihlal = []
    for ad, metin in _pano_stilleri():
        for yer, kod in _bildirimler(ad, metin):
            if re.search(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?\b", kod):
                ihlal.append(f"{yer}  {kod}")
    assert not ihlal, "elle yazılmış hex (rol token'ı ya da colors.$… kullan):\n" + "\n".join(ihlal)


DERS_AILESI = r"(blue|teal|purple|magenta|cyan)"


def test_ders_rengi_etiket_olmaz():
    ihlal = []
    for p in sorted(DASH.rglob("*.tsx")):
        metin = p.read_text(encoding="utf-8")
        for m in re.finditer(rf'type="{DERS_AILESI}"|tagType:\s*\'{DERS_AILESI}\'', metin):
            satir = metin.count("\n", 0, m.start()) + 1
            ihlal.append(f"{p.relative_to(DASH)}:{satir}  {m.group(0)}")
    assert not ihlal, "ders ailesi renginde Carbon Tag:\n" + "\n".join(ihlal)


# ── calendar events (backend) ────────────────────────────────────────────────

@pytest.fixture
def api():
    import src.dashboard_api as api
    return api


def test_takvim_olayi_dersinin_rengini_tasir(api):
    from src import subject_themes
    ev = api._takvim_rengi("Matematik")
    assert ev == {"color": subject_themes.role("purple", "accent"), "courseFamily": "purple"}
    assert api._takvim_rengi("Fransızca")["courseFamily"] == "blue"


def test_derssiz_olay_notr_gri(api):
    from src import subject_themes
    assert api._takvim_rengi("") == {"color": subject_themes.role("gray", "accent"),
                                     "courseFamily": "gray"}


def test_takvimde_anlam_rengi_yok(api):
    """Every homework was #da1e28 and every private lesson #ff832b."""
    from src import subject_themes
    ayrilmis = {"#da1e28", "#fa4d56", "#ff832b", "#f1c21b", "#24a148", "#198038"}
    for ders in ("Matematik", "Türkçe", "Fen Bilimleri", "Din Kültürü", "", "PDR"):
        assert api._takvim_rengi(ders)["color"].lower() not in ayrilmis
    assert not hasattr(api, "_UNIFIED_COLORS")
    assert subject_themes.family_of("Beden Eğitimi") == "gray"
